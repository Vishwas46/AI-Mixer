#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# web_server.py
# FastAPI backend for the AI-Mixer web application.
# Provides REST endpoints for audio analysis, mashup creation, and file management.
# Long-running tasks (analysis, mashup generation) run in background threads
# with progress tracking via polling or Server-Sent Events (SSE).
# -----------------------------------------------------------------------------

import json
import os
import uuid
import threading
import time
import io
import sys
import contextlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    JSONResponse,
    FileResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
import re
import logging

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ai-mixer")

# ---------------------------------------------------------------------------
# Project module imports
# ---------------------------------------------------------------------------
from audio_analyzer import analyze_audio_local, analyze_vocal_presence
from creative_remix import (
    run_single_mashup_mode,
    run_dj_set_mode,
    curate_setlist,
    create_continuous_mix_from_setlist,
)
from kannada_mashup_analyzer import (
    analyze_kannada_track_for_mashup,
    plan_kannada_mashup,
    generate_mashup_report,
    analyze_mashup_compatibility,
    cluster_tracks_for_mashup,
)
from youtube_downloader import (
    download_from_youtube,
    get_video_info,
    is_valid_youtube_url,
)
from rekordbox_exporter import (
    generate_rekordbox_xml,
    generate_serato_crates,
    export_analysis_json,
)
from sandalwood_mixer import (
    create_sandalwood_mashup,
    create_pallavi_medley,
)
from sandalwood_enhancements import (
    validate_audio_file,
    batch_validate_audio,
    detect_singer,
    extract_vocal_features,
    get_singer_eq_profile,
    analyze_era_from_audio,
    generate_transition_preview,
    generate_track_preview,
    set_custom_cue_point,
    get_custom_cue_points,
    delete_custom_cue_point,
    merge_cue_points,
    KANNADA_SINGER_PROFILES,
    FILM_ERA_PROFILES,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONGS_DIR = os.path.join(BASE_DIR, "songs")
OUTPUT_DIR = os.path.join(BASE_DIR, "remix_outputs")
ANALYSIS_CACHE_PATH = os.path.join(BASE_DIR, "analysis_cache.json")

# ---------------------------------------------------------------------------
# Ensure required directories exist
# ---------------------------------------------------------------------------
os.makedirs(SONGS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(title="AI-Mixer", version="1.0.0")

# CORS configuration - restrict in production
# For local development, allow localhost origins
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Maximum upload size (100MB)
MAX_UPLOAD_SIZE = 100 * 1024 * 1024


def validate_safe_path(base_dir: str, filename: str) -> str:
    """
    Validate that a filename doesn't escape the base directory.
    Returns the safe absolute path or raises HTTPException.
    """
    # Remove any path components from filename
    safe_name = os.path.basename(filename)
    # Remove any null bytes or other dangerous characters
    safe_name = re.sub(r'[\x00-\x1f\x7f]', '', safe_name)
    # Build the full path
    full_path = os.path.abspath(os.path.join(base_dir, safe_name))
    # Verify it's still within base_dir
    if not full_path.startswith(os.path.abspath(base_dir)):
        raise HTTPException(status_code=400, detail="Invalid filename - path traversal detected")
    return full_path


def validate_filename(filename: str) -> str:
    """Validate and sanitize a filename."""
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    # Only allow safe characters
    safe_name = re.sub(r'[^\w\s\-\.\(\)]', '_', os.path.basename(filename))
    if not safe_name or safe_name.startswith('.'):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return safe_name

app.mount("/remix_outputs", StaticFiles(directory=OUTPUT_DIR), name="remix_outputs")

# ---------------------------------------------------------------------------
# In-memory task store
# ---------------------------------------------------------------------------
# Each task: {
#   "task_id": str,
#   "status": "pending" | "running" | "completed" | "failed",
#   "progress": int (0-100),
#   "log": list[str],
#   "result": any,
#   "error": str | None,
#   "created_at": str,
# }
_tasks: dict[str, dict] = {}
_tasks_lock = threading.Lock()

# ---------------------------------------------------------------------------
# In-memory mashup plan store (for Plan → Approve → Create flow)
# ---------------------------------------------------------------------------
_mashup_plans: dict[str, dict] = {}
_plans_lock = threading.Lock()


def _create_task() -> dict:
    """Create a new task entry and return it."""
    task_id = str(uuid.uuid4())
    task = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "log": [],
        "result": None,
        "error": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    with _tasks_lock:
        _tasks[task_id] = task
    return task


def _get_task(task_id: str) -> Optional[dict]:
    with _tasks_lock:
        return _tasks.get(task_id)


class _LogCapture(io.TextIOBase):
    """A writable stream that captures lines and appends them to a task's log."""

    def __init__(self, task: dict):
        self._task = task
        self._buffer = ""

    def write(self, text: str) -> int:
        if not text:
            return 0
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            stripped = line.rstrip()
            if stripped:
                with _tasks_lock:
                    self._task["log"].append(stripped)
                # Heuristic: look for percentage-like patterns to update progress
                self._try_update_progress(stripped)
        return len(text)

    def flush(self):
        if self._buffer.strip():
            with _tasks_lock:
                self._task["log"].append(self._buffer.strip())
            self._buffer = ""

    def _try_update_progress(self, line: str):
        """Try to infer progress from common log patterns."""
        lower = line.lower()
        # Step-based progress updates based on analysis stages
        if "base analysis" in lower:
            self._task["progress"] = 10
        elif "vocal analysis" in lower:
            self._task["progress"] = 20
        elif "beat grid" in lower:
            self._task["progress"] = 30
        elif "tala detection" in lower:
            self._task["progress"] = 40
        elif "scale" in lower and "analysis" in lower:
            self._task["progress"] = 45
        elif "hook" in lower and "drop" in lower:
            self._task["progress"] = 50
        elif "harmonic rhythm" in lower:
            self._task["progress"] = 55
        elif "spectral analysis" in lower:
            self._task["progress"] = 60
        elif "percussion" in lower:
            self._task["progress"] = 65
        elif "section classification" in lower:
            self._task["progress"] = 70
        elif "emotional" in lower:
            self._task["progress"] = 75
        elif "phrase boundary" in lower:
            self._task["progress"] = 80
        elif "vocal-free" in lower:
            self._task["progress"] = 85
        elif "cue point" in lower:
            self._task["progress"] = 90
        elif "transition recommendation" in lower:
            self._task["progress"] = 95
        elif "complete" in lower or "exporting" in lower:
            self._task["progress"] = 98


def _run_in_background(task: dict, fn, *args, **kwargs):
    """Run *fn* in a background thread, capturing stdout into the task log."""

    def _worker():
        task["status"] = "running"
        capture = _LogCapture(task)
        old_stdout = sys.stdout
        sys.stdout = capture
        try:
            result = fn(*args, **kwargs)
            capture.flush()
            task["result"] = result
            task["status"] = "completed"
            task["progress"] = 100
        except Exception as exc:
            capture.flush()
            task["status"] = "failed"
            task["error"] = str(exc)
        finally:
            sys.stdout = old_stdout

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Analysis cache helpers
# ---------------------------------------------------------------------------

def _load_analysis_cache() -> dict:
    if os.path.exists(ANALYSIS_CACHE_PATH):
        with open(ANALYSIS_CACHE_PATH, "r") as f:
            return json.load(f)
    return {}


def _save_analysis_cache(cache: dict):
    with open(ANALYSIS_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=4, default=str)


def _is_deep_analysis(entry: dict) -> bool:
    """Check if cached analysis is the full 17-step Kannada deep analysis."""
    deep_keys = {'tala', 'beat_grid', 'scale', 'section_classification'}
    return deep_keys.issubset(entry.keys())


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    filename: Optional[str] = Field(None, min_length=1, max_length=255)
    filenames: Optional[list[str]] = Field(None, max_length=100)

    @field_validator('filename', 'filenames', mode='before')
    @classmethod
    def validate_no_path_traversal(cls, v):
        if v is None:
            return v
        if isinstance(v, list):
            for f in v:
                if '..' in f or f.startswith('/'):
                    raise ValueError('Invalid filename - path traversal not allowed')
        elif isinstance(v, str):
            if '..' in v or v.startswith('/'):
                raise ValueError('Invalid filename - path traversal not allowed')
        return v


class KannadaAnalyzeRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)

    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        if '..' in v or v.startswith('/'):
            raise ValueError('Invalid filename')
        return v


class SingleMashupRequest(BaseModel):
    songA: str = Field(..., min_length=1, max_length=255)
    songB: str = Field(..., min_length=1, max_length=255)
    output_name: str = Field(..., min_length=1, max_length=200)

    @field_validator('songA', 'songB', 'output_name')
    @classmethod
    def validate_no_traversal(cls, v):
        if '..' in v or v.startswith('/'):
            raise ValueError('Invalid filename')
        return v


class DJSetRequest(BaseModel):
    songs_dir: str = Field("songs/", max_length=255)
    mix_style: str = Field("relaxed", pattern="^(relaxed|energetic|pro)$")


class SandalwoodMashupRequest(BaseModel):
    filenames: list[str] = Field(..., min_length=2, max_length=50)
    style: str = Field("energetic", pattern="^(energetic|smooth|showcase)$")
    duration: int = Field(10, ge=1, le=60)

    @field_validator('filenames')
    @classmethod
    def validate_filenames(cls, v):
        for f in v:
            if '..' in f or f.startswith('/'):
                raise ValueError('Invalid filename')
        return v


class SandalwoodPlanRequest(BaseModel):
    """Request for generating a clustering plan (Plan → Approve → Create flow)."""
    filenames: list[str] = Field(..., min_length=2, max_length=50)
    duration: int = Field(15, ge=1, le=60)

    @field_validator('filenames')
    @classmethod
    def validate_filenames(cls, v):
        for f in v:
            if '..' in f or f.startswith('/'):
                raise ValueError('Invalid filename')
        return v


class SandalwoodCreateRequest(BaseModel):
    """Request to create mashups from an approved plan."""
    plan_id: str = Field(..., min_length=1, max_length=100)
    groups: list[dict] = Field(...)

    @field_validator('plan_id')
    @classmethod
    def validate_plan_id(cls, v):
        if '..' in v or '/' in v:
            raise ValueError('Invalid plan_id')
        return v


class YouTubeDownloadRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=500)

    @field_validator('url')
    @classmethod
    def validate_youtube_url(cls, v):
        youtube_patterns = [
            r'(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+',
            r'(https?://)?(www\.)?youtu\.be/[\w-]+',
            r'(https?://)?(www\.)?youtube\.com/shorts/[\w-]+',
            r'(https?://)?music\.youtube\.com/watch\?v=[\w-]+',
        ]
        for pattern in youtube_patterns:
            if re.match(pattern, v):
                return v
        raise ValueError('Invalid YouTube URL')


class BatchAnalyzeRequest(BaseModel):
    filenames: list[str] = Field(..., min_length=1, max_length=100)

    @field_validator('filenames')
    @classmethod
    def validate_filenames(cls, v):
        for f in v:
            if '..' in f or f.startswith('/'):
                raise ValueError('Invalid filename')
        return v


class BatchMashupRequest(BaseModel):
    """Request for batch mashup creation."""
    combinations: list[dict] = Field(..., min_length=1, max_length=50)
    mode: str = Field("single", pattern="^(single|djset)$")


class ExportRequest(BaseModel):
    """Request for DJ software export."""
    filenames: list[str] = Field(..., min_length=1, max_length=100)
    format: str = Field("rekordbox", pattern="^(rekordbox|serato|json)$")
    playlist_name: Optional[str] = Field(None, max_length=100)


# ===================================================================
# ENDPOINTS
# ===================================================================

# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "songs_dir": SONGS_DIR,
        "output_dir": OUTPUT_DIR,
    }


# ------------------------------------------------------------------
# Task polling
# ------------------------------------------------------------------
@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = _get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task["task_id"],
        "status": task["status"],
        "progress": task["progress"],
        "log": task["log"],
        "result": task["result"],
        "error": task["error"],
        "created_at": task["created_at"],
    }


# ------------------------------------------------------------------
# SSE stream for live progress
# ------------------------------------------------------------------
@app.get("/api/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str):
    task = _get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    def _event_generator():
        last_log_index = 0
        last_progress = -1
        last_status = None

        while True:
            current_task = _get_task(task_id)
            if current_task is None:
                yield "event: error\ndata: {\"error\": \"Task not found\"}\n\n"
                break

            # Emit new log lines
            with _tasks_lock:
                log_snapshot = list(current_task["log"])
                progress = current_task["progress"]
                status = current_task["status"]
                result = current_task["result"]
                error = current_task["error"]

            if len(log_snapshot) > last_log_index:
                new_lines = log_snapshot[last_log_index:]
                for line in new_lines:
                    payload = json.dumps({"type": "log", "message": line})
                    yield f"data: {payload}\n\n"
                last_log_index = len(log_snapshot)

            # Emit progress updates
            if progress != last_progress:
                payload = json.dumps({"type": "progress", "progress": progress})
                yield f"data: {payload}\n\n"
                last_progress = progress

            # Emit status changes
            if status != last_status:
                payload = json.dumps({"type": "status", "status": status})
                yield f"data: {payload}\n\n"
                last_status = status

            # Terminal states
            if status == "completed":
                payload = json.dumps({
                    "type": "complete",
                    "status": "completed",
                    "progress": 100,
                    "result": result,
                })
                yield f"data: {payload}\n\n"
                break
            elif status == "failed":
                payload = json.dumps({
                    "type": "complete",
                    "status": "failed",
                    "error": error,
                })
                yield f"data: {payload}\n\n"
                break

            time.sleep(0.5)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ------------------------------------------------------------------
# List songs (with pagination)
# ------------------------------------------------------------------
@app.get("/api/songs")
async def list_songs(
    page: int = 1,
    limit: int = 50,
    sort_by: str = "name",
    order: str = "asc"
):
    """
    List songs with pagination support.

    Args:
        page: Page number (1-indexed)
        limit: Items per page (max 100)
        sort_by: Sort field (name, size, modified)
        order: Sort order (asc, desc)
    """
    if not os.path.isdir(SONGS_DIR):
        return {"songs": [], "count": 0, "total": 0, "page": page, "pages": 0}

    # Validate parameters
    page = max(1, page)
    limit = max(1, min(100, limit))

    cache = _load_analysis_cache()
    all_songs = []

    for entry in os.listdir(SONGS_DIR):
        if not entry.lower().endswith((".mp3", ".wav", ".flac", ".m4a")):
            continue
        full_path = os.path.join(SONGS_DIR, entry)
        stat = os.stat(full_path)

        # Check if analysis cache exists for this file
        cached_entry = cache.get(full_path) or cache.get(entry)
        has_cache = cached_entry is not None
        has_deep = has_cache and _is_deep_analysis(cached_entry)

        all_songs.append({
            "name": entry,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "modified_ts": stat.st_mtime,
            "has_analysis": has_cache,
            "has_deep_analysis": has_deep,
        })

    # Sort
    sort_key = {
        "name": lambda x: x["name"].lower(),
        "size": lambda x: x["size_bytes"],
        "modified": lambda x: x["modified_ts"],
    }.get(sort_by, lambda x: x["name"].lower())

    all_songs.sort(key=sort_key, reverse=(order == "desc"))

    # Remove internal sort key
    for song in all_songs:
        song.pop("modified_ts", None)

    # Paginate
    total = len(all_songs)
    total_pages = (total + limit - 1) // limit
    start = (page - 1) * limit
    end = start + limit
    songs = all_songs[start:end]

    return {
        "songs": songs,
        "count": len(songs),
        "total": total,
        "page": page,
        "pages": total_pages,
        "limit": limit,
        "directory": SONGS_DIR,
    }


# ------------------------------------------------------------------
# Upload song
# ------------------------------------------------------------------
@app.post("/api/songs/upload")
async def upload_song(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Sanitize and validate filename
    safe_name = validate_filename(file.filename)
    if not safe_name.lower().endswith((".mp3", ".wav", ".flac", ".ogg", ".m4a")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Accepted: mp3, wav, flac, ogg, m4a",
        )

    # Validate path is safe (no traversal)
    dest_path = validate_safe_path(SONGS_DIR, safe_name)

    # Read and validate file size
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024*1024)}MB",
        )

    with open(dest_path, "wb") as f:
        f.write(contents)

    logger.info(f"Uploaded song: {safe_name} ({len(contents)} bytes)")

    stat = os.stat(dest_path)
    return {
        "filename": safe_name,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "path": dest_path,
    }


# ------------------------------------------------------------------
# Get cached analysis for a file
# ------------------------------------------------------------------
@app.get("/api/analysis/{filename}")
async def get_analysis(filename: str):
    cache = _load_analysis_cache()

    # Try by filename, full path, or relative path
    full_path = os.path.join(SONGS_DIR, filename)
    result = cache.get(full_path) or cache.get(filename)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No cached analysis found for '{filename}'. Run analysis first.",
        )
    return result


# ------------------------------------------------------------------
# Trigger audio analysis (background)
# ------------------------------------------------------------------
@app.post("/api/analyze")
async def analyze_songs(req: AnalyzeRequest):
    filenames: list[str] = []
    if req.filenames:
        filenames = req.filenames
    elif req.filename:
        filenames = [req.filename]
    else:
        raise HTTPException(status_code=400, detail="Provide 'filename' or 'filenames'")

    # Validate all files exist
    for fn in filenames:
        fpath = os.path.join(SONGS_DIR, fn)
        if not os.path.isfile(fpath):
            raise HTTPException(status_code=404, detail=f"Song file not found: {fn}")

    task = _create_task()

    def _do_analysis():
        cache = _load_analysis_cache()
        venv_path = os.environ.get("VIRTUAL_ENV")
        if not venv_path:
            venv_path = os.path.abspath("./venv")

        results = {}
        total = len(filenames)
        for idx, fn in enumerate(filenames):
            fpath = os.path.join(SONGS_DIR, fn)
            print(f"[{idx + 1}/{total}] Analyzing {fn} ...")

            # Core analysis
            features = analyze_audio_local(fpath)

            # Vocal analysis
            print(f"[{idx + 1}/{total}] Running vocal presence analysis for {fn} ...")
            vocal_regions = analyze_vocal_presence(fpath, venv_path)
            features["has_vocals"] = len(vocal_regions) > 0
            features["vocal_regions"] = vocal_regions
            features["filename"] = fn
            features["path"] = fpath
            features["mod_time"] = os.path.getmtime(fpath)

            # Update cache
            cache[fpath] = features
            results[fn] = features

            # Manual progress update
            task["progress"] = int(((idx + 1) / total) * 100)
            print(f"[{idx + 1}/{total}] Analysis complete for {fn}")

        # Persist cache
        _save_analysis_cache(cache)
        print("Analysis cache saved.")
        return results

    _run_in_background(task, _do_analysis)
    return {"task_id": task["task_id"], "status": "pending", "filenames": filenames}


# ------------------------------------------------------------------
# Kannada-specific analysis (background)
# ------------------------------------------------------------------
@app.post("/api/analyze/kannada")
async def analyze_kannada(req: KannadaAnalyzeRequest):
    fpath = os.path.join(SONGS_DIR, req.filename)
    if not os.path.isfile(fpath):
        raise HTTPException(status_code=404, detail=f"Song file not found: {req.filename}")

    task = _create_task()

    def _do_kannada_analysis():
        venv_path = os.environ.get("VIRTUAL_ENV")
        if not venv_path:
            venv_path = os.path.abspath("./venv")

        print(f"Starting Kannada mashup analysis for {req.filename} ...")
        analysis = analyze_kannada_track_for_mashup(fpath, venv_path)

        # Also store in standard cache
        cache = _load_analysis_cache()
        cache[fpath] = analysis
        _save_analysis_cache(cache)
        print("Kannada analysis complete and cached.")
        return analysis

    _run_in_background(task, _do_kannada_analysis)
    return {"task_id": task["task_id"], "status": "pending", "filename": req.filename}


# ------------------------------------------------------------------
# Single mashup (two songs)
# ------------------------------------------------------------------
@app.post("/api/mashup/single")
async def mashup_single(req: SingleMashupRequest):
    song_a_path = os.path.join(SONGS_DIR, req.songA)
    song_b_path = os.path.join(SONGS_DIR, req.songB)

    if not os.path.isfile(song_a_path):
        raise HTTPException(status_code=404, detail=f"Song A not found: {req.songA}")
    if not os.path.isfile(song_b_path):
        raise HTTPException(status_code=404, detail=f"Song B not found: {req.songB}")

    # Ensure output name has extension
    output_name = req.output_name
    if not output_name.lower().endswith(".mp3"):
        output_name += ".mp3"
    output_path = os.path.join(OUTPUT_DIR, output_name)

    task = _create_task()

    def _do_single_mashup():
        print(f"Starting single mashup: {req.songA} + {req.songB} -> {output_name}")

        # Build an argparse-like namespace that run_single_mashup_mode expects
        class Args:
            pass

        args = Args()
        args.songA_path = song_a_path
        args.songB_path = song_b_path
        args.out = output_path

        run_single_mashup_mode(args)
        print(f"Mashup complete: {output_name}")
        return {
            "output_filename": output_name,
            "output_path": output_path,
        }

    _run_in_background(task, _do_single_mashup)
    return {
        "task_id": task["task_id"],
        "status": "pending",
        "songA": req.songA,
        "songB": req.songB,
        "output_name": output_name,
    }


# ------------------------------------------------------------------
# DJ set mode
# ------------------------------------------------------------------
@app.post("/api/mashup/djset")
async def mashup_djset(req: DJSetRequest):
    songs_dir = req.songs_dir
    if not os.path.isabs(songs_dir):
        songs_dir = os.path.join(BASE_DIR, songs_dir)

    if not os.path.isdir(songs_dir):
        raise HTTPException(status_code=404, detail=f"Songs directory not found: {songs_dir}")

    mp3_files = [f for f in os.listdir(songs_dir) if f.lower().endswith(".mp3")]
    if len(mp3_files) < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 MP3 files in the directory for a DJ set.",
        )

    if req.mix_style not in ("relaxed", "energetic", "pro"):
        raise HTTPException(status_code=400, detail="mix_style must be relaxed, energetic, or pro")

    task = _create_task()

    def _do_djset():
        print(f"Starting DJ set mode: {songs_dir} ({req.mix_style} style)")

        # Build an argparse-like namespace that run_dj_set_mode expects
        class Args:
            pass

        args = Args()
        args.songs_dir = songs_dir
        args.mix_style = req.mix_style

        run_dj_set_mode(args)
        print("DJ set generation complete.")

        # Find the most recently created output file
        output_files = sorted(
            [f for f in os.listdir(OUTPUT_DIR) if f.startswith("ai_dj_set_")],
            key=lambda f: os.path.getmtime(os.path.join(OUTPUT_DIR, f)),
            reverse=True,
        )
        latest = output_files[0] if output_files else None
        return {
            "output_filename": latest,
            "output_path": os.path.join(OUTPUT_DIR, latest) if latest else None,
            "mix_style": req.mix_style,
        }

    _run_in_background(task, _do_djset)
    return {
        "task_id": task["task_id"],
        "status": "pending",
        "songs_dir": songs_dir,
        "mix_style": req.mix_style,
        "song_count": len(mp3_files),
    }


# ------------------------------------------------------------------
# Sandalwood (Kannada) mashup planning
# ------------------------------------------------------------------
@app.post("/api/mashup/sandalwood")
async def mashup_sandalwood(req: SandalwoodMashupRequest):
    if len(req.filenames) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 filenames")

    # Validate all files exist
    for fn in req.filenames:
        fpath = os.path.join(SONGS_DIR, fn)
        if not os.path.isfile(fpath):
            raise HTTPException(status_code=404, detail=f"Song file not found: {fn}")

    if req.style not in ("energetic", "smooth", "showcase"):
        raise HTTPException(status_code=400, detail="style must be energetic, smooth, or showcase")

    task = _create_task()

    def _do_sandalwood_mashup():
        venv_path = os.environ.get("VIRTUAL_ENV")
        if not venv_path:
            venv_path = os.path.abspath("./venv")

        total = len(req.filenames)
        print(f"Starting Kannada mashup planning: {total} tracks, {req.style} style, {req.duration} min")

        # Step 1: Analyze all tracks
        all_tracks = []
        for idx, fn in enumerate(req.filenames):
            fpath = os.path.join(SONGS_DIR, fn)
            print(f"[{idx + 1}/{total}] Deep analysis: {fn}")
            analysis = analyze_kannada_track_for_mashup(fpath, venv_path)
            all_tracks.append(analysis)
            task["progress"] = int(((idx + 1) / total) * 50)  # 0-50% for analysis

        # Step 2: Plan the mashup
        print("Planning mashup order and transitions...")
        task["progress"] = 55
        mashup_plan = plan_kannada_mashup(all_tracks, req.duration, req.style)
        task["progress"] = 60

        # Step 3: Generate human-readable report
        print("Generating mashup report...")
        report = generate_mashup_report(mashup_plan)

        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"kannada_mashup_report_{req.style}_{timestamp}.txt"
        report_path = os.path.join(OUTPUT_DIR, report_filename)
        with open(report_path, "w") as f:
            f.write(report)
        task["progress"] = 65

        # Step 4: Prepare for audio creation
        print("Preparing to create audio mashup...")
        tracks_by_name = {t['filename']: t for t in all_tracks}
        task["progress"] = 70

        # Step 5: Create the actual audio mashup using professional Sandalwood mixer
        print(f"Creating {req.style} audio mashup from {len(all_tracks)} tracks...")
        print("Using professional Sandalwood mixer with BPM sync, LUFS normalization, and beat alignment")

        try:
            # Filter to only the tracks selected by the planner (not all analyzed tracks)
            planned_filenames = set(mashup_plan.get('track_order', []))
            planned_tracks = [t for t in all_tracks if t['filename'] in planned_filenames]
            output_path = create_sandalwood_mashup(
                tracks_analysis=planned_tracks,
                mashup_plan=mashup_plan,
                output_dir=OUTPUT_DIR,
                target_lufs=-14.0,  # YouTube standard
                export_quality='high'  # 320kbps
            )
            actual_output = os.path.basename(output_path) if output_path else None
            task["progress"] = 95
        except Exception as mix_error:
            print(f"Professional mixer failed: {mix_error}")
            print("Falling back to basic continuous mix...")

            # Fallback to basic mixer if professional one fails
            mix_style_map = {
                'energetic': 'energetic',
                'smooth': 'relaxed',
                'showcase': 'pro',
            }
            mix_style = mix_style_map.get(req.style, 'energetic')

            setlist = []
            for fn in mashup_plan.get('track_order', req.filenames):
                track = tracks_by_name.get(fn)
                if track:
                    setlist.append({
                        'path': track['file_path'],
                        'filename': track['filename'],
                        'bpm': track['bpm'],
                        'key': track['key'],
                        'energy': track['energy'],
                        'duration': track['duration'],
                        'structure': track['structure'],
                    })

            create_continuous_mix_from_setlist(setlist, mix_style, OUTPUT_DIR)
            task["progress"] = 95

            # Find the created output file
            output_files = sorted(
                [f for f in os.listdir(OUTPUT_DIR) if f.startswith("ai_dj_set_") and f.endswith(".mp3")],
                key=lambda f: os.path.getmtime(os.path.join(OUTPUT_DIR, f)),
                reverse=True,
            )
            actual_output = output_files[0] if output_files else None

        # Also cache analyses
        cache = _load_analysis_cache()
        for track in all_tracks:
            cache[track["file_path"]] = track
        _save_analysis_cache(cache)

        print(f"Mashup complete! Audio: {actual_output}, Report: {report_filename}")
        return {
            "plan": mashup_plan,
            "report": report,
            "report_filename": report_filename,
            "output_filename": actual_output,
            "track_count": len(all_tracks),
            "style": req.style,
        }

    _run_in_background(task, _do_sandalwood_mashup)
    return {
        "task_id": task["task_id"],
        "status": "pending",
        "filenames": req.filenames,
        "style": req.style,
        "duration": req.duration,
    }


# ------------------------------------------------------------------
# Sandalwood Plan → Approve → Create (Intelligent Mixing Agent)
# ------------------------------------------------------------------

@app.post("/api/mashup/sandalwood/plan")
async def mashup_sandalwood_plan(req: SandalwoodPlanRequest):
    """Generate a clustering plan: analyze tracks, build compatibility matrix, cluster into groups."""
    for fn in req.filenames:
        fpath = os.path.join(SONGS_DIR, fn)
        if not os.path.isfile(fpath):
            raise HTTPException(status_code=404, detail=f"Song file not found: {fn}")

    task = _create_task()

    def _do_plan():
        venv_path = os.environ.get("VIRTUAL_ENV", os.path.abspath("./venv"))
        total = len(req.filenames)
        print(f"Planning mashup groups for {total} tracks, target {req.duration} min/group")

        # Load analysis cache — skip already-analyzed tracks
        cache = _load_analysis_cache()
        all_tracks = []
        for idx, fn in enumerate(req.filenames):
            fpath = os.path.join(SONGS_DIR, fn)
            if fpath in cache and _is_deep_analysis(cache[fpath]):
                print(f"[{idx + 1}/{total}] Deep cache hit: {fn}")
                all_tracks.append(cache[fpath])
            else:
                reason = "not cached" if fpath not in cache else "only basic analysis"
                print(f"[{idx + 1}/{total}] Deep analyzing ({reason}): {fn}")
                analysis = analyze_kannada_track_for_mashup(fpath, venv_path)
                all_tracks.append(analysis)
                cache[fpath] = analysis
            task["progress"] = int(((idx + 1) / total) * 70)

        _save_analysis_cache(cache)

        # Run clustering
        print("Clustering tracks into compatible groups...")
        task["progress"] = 75
        cluster_result = cluster_tracks_for_mashup(all_tracks, default_duration=req.duration)
        task["progress"] = 90

        # Store plan for later retrieval by /create endpoint
        plan_id = str(uuid.uuid4())
        plan_data = {
            'plan_id': plan_id,
            'groups': cluster_result['groups'],
            'excluded': cluster_result['excluded'],
            'matrix_summary': cluster_result['matrix_summary'],
            'all_tracks': all_tracks,
            'created_at': datetime.utcnow().isoformat(),
        }

        with _plans_lock:
            _mashup_plans[plan_id] = plan_data
            # Cleanup plans older than 1 hour
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(hours=1)
            expired = [
                k for k, v in _mashup_plans.items()
                if isinstance(v.get('created_at'), str)
                and datetime.fromisoformat(v['created_at']) < cutoff
            ]
            for k in expired:
                del _mashup_plans[k]

        print(f"Plan generated: {len(cluster_result['groups'])} groups, "
              f"{len(cluster_result['excluded'])} excluded")

        # Return serializable plan (strip all_tracks to save bandwidth)
        serializable_groups = []
        for g in cluster_result['groups']:
            serializable_groups.append({
                'group_id': g['group_id'],
                'name': g['name'],
                'style': g['style'],
                'track_order': g['track_order'],
                'track_count': g['track_count'],
                'avg_compatibility': g['avg_compatibility'],
                'estimated_duration_minutes': g['estimated_duration_minutes'],
                'timeline': g.get('timeline', []),
                'warnings': g.get('warnings', []),
                'best_pairs': g.get('best_pairs', []),
            })

        return {
            'plan_id': plan_id,
            'groups': serializable_groups,
            'excluded': cluster_result['excluded'],
            'matrix_summary': cluster_result['matrix_summary'],
            'total_analyzed': len(all_tracks),
        }

    _run_in_background(task, _do_plan)
    return {
        "task_id": task["task_id"],
        "status": "pending",
        "filenames": req.filenames,
        "duration": req.duration,
    }


@app.post("/api/mashup/sandalwood/create")
async def mashup_sandalwood_create(req: SandalwoodCreateRequest):
    """Create mashups from an approved plan. One mashup per group."""
    with _plans_lock:
        plan_data = _mashup_plans.get(req.plan_id)

    if not plan_data:
        raise HTTPException(status_code=404, detail="Plan not found. Generate a plan first.")

    task = _create_task()

    def _do_create():
        all_tracks = plan_data['all_tracks']
        tracks_by_name = {t['filename']: t for t in all_tracks}

        # Map group_id → style override from request
        style_overrides = {}
        for g in req.groups:
            gid = g.get('group_id')
            if gid is not None:
                style_overrides[gid] = g.get('style')

        results = []
        total_groups = len(req.groups)

        for idx, requested_group in enumerate(req.groups):
            gid = requested_group.get('group_id')
            # Find this group in the stored plan
            matching = [g for g in plan_data['groups'] if g['group_id'] == gid]
            if not matching:
                print(f"Warning: Group {gid} not found in plan, skipping")
                continue

            group = matching[0]
            style = style_overrides.get(gid) or group['style']
            track_order = group['track_order']

            # Build tracks_analysis for this group only
            group_tracks = [tracks_by_name[fn] for fn in track_order if fn in tracks_by_name]
            if len(group_tracks) < 2:
                print(f"Group {gid}: not enough tracks ({len(group_tracks)}), skipping")
                results.append({
                    'group_id': gid,
                    'group_name': group['name'],
                    'style': style,
                    'output_filename': None,
                    'error': 'Not enough tracks',
                })
                continue

            # Get or rebuild the mashup plan for this group
            mashup_plan = group.get('plan', {})
            mashup_plan['style'] = style

            print(f"\n[Group {gid}] Creating {style} mashup with {len(group_tracks)} tracks...")
            try:
                output_path = create_sandalwood_mashup(
                    tracks_analysis=group_tracks,
                    mashup_plan=mashup_plan,
                    output_dir=OUTPUT_DIR,
                    target_lufs=-14.0,
                    export_quality='high'
                )
                results.append({
                    'group_id': gid,
                    'group_name': group['name'],
                    'style': style,
                    'output_filename': os.path.basename(output_path) if output_path else None,
                    'track_count': len(group_tracks),
                })
            except Exception as e:
                print(f"Group {gid} failed: {e}")
                results.append({
                    'group_id': gid,
                    'group_name': group['name'],
                    'style': style,
                    'output_filename': None,
                    'error': str(e),
                })

            task["progress"] = int(((idx + 1) / total_groups) * 100)

        return {
            'plan_id': req.plan_id,
            'mashups': results,
            'total_created': sum(1 for r in results if r.get('output_filename')),
        }

    _run_in_background(task, _do_create)
    return {
        "task_id": task["task_id"],
        "status": "pending",
        "plan_id": req.plan_id,
    }


# ------------------------------------------------------------------
# Pallavi Medley - Signature Sandalwood mashup style
# ------------------------------------------------------------------
class PallaviMedleyRequest(BaseModel):
    """Request for Pallavi-to-Pallavi medley creation."""
    filenames: list[str] = Field(..., min_length=2, max_length=20)

    @field_validator('filenames')
    @classmethod
    def validate_filenames(cls, v):
        for f in v:
            if '..' in f or f.startswith('/'):
                raise ValueError('Invalid filename')
        return v


@app.post("/api/mashup/pallavi-medley")
async def create_pallavi_medley_endpoint(req: PallaviMedleyRequest):
    """
    Create a Pallavi-to-Pallavi medley - the signature Sandalwood mashup style.
    Extracts the catchiest Pallavi (chorus) sections and blends them together.
    This is what makes Kannada film medleys special!
    """
    task = _create_task("pallavi_medley", len(req.filenames))

    def _do_pallavi_medley():
        try:
            task["status"] = "running"
            task["progress"] = 10

            print(f"Creating Pallavi medley from {len(req.filenames)} tracks...")

            # Get venv path for Demucs
            venv_path = os.environ.get('VIRTUAL_ENV') or os.path.join(BASE_DIR, 'venv')

            # Analyze all tracks
            all_tracks = []
            for i, filename in enumerate(req.filenames):
                file_path = validate_safe_path(SONGS_DIR, filename)
                if not os.path.exists(file_path):
                    print(f"Warning: File not found: {filename}")
                    continue

                print(f"Analyzing [{i+1}/{len(req.filenames)}]: {filename}")
                analysis = analyze_kannada_track_for_mashup(file_path, venv_path)
                if analysis:
                    analysis['filename'] = filename
                    analysis['file_path'] = file_path
                    all_tracks.append(analysis)

                task["progress"] = 10 + int(50 * (i + 1) / len(req.filenames))

            if len(all_tracks) < 2:
                raise ValueError("Need at least 2 valid tracks with Pallavi sections")

            task["progress"] = 60

            # Create the Pallavi medley
            print("Creating Pallavi medley...")
            output_path = create_pallavi_medley(
                tracks_analysis=all_tracks,
                output_dir=OUTPUT_DIR,
                target_lufs=-14.0
            )

            task["progress"] = 95
            output_filename = os.path.basename(output_path) if output_path else None

            print(f"Pallavi medley complete: {output_filename}")
            return {
                "output_filename": output_filename,
                "track_count": len(all_tracks),
                "type": "pallavi_medley",
            }

        except Exception as e:
            logger.exception("Pallavi medley creation failed")
            raise

    _run_in_background(task, _do_pallavi_medley)
    return {
        "task_id": task["task_id"],
        "status": "pending",
        "filenames": req.filenames,
        "type": "pallavi_medley",
    }


# ------------------------------------------------------------------
# List output files
# ------------------------------------------------------------------
@app.get("/api/outputs")
async def list_outputs():
    if not os.path.isdir(OUTPUT_DIR):
        return {"outputs": [], "count": 0}

    outputs = []
    for entry in sorted(os.listdir(OUTPUT_DIR)):
        full_path = os.path.join(OUTPUT_DIR, entry)
        if not os.path.isfile(full_path):
            continue
        stat = os.stat(full_path)
        outputs.append({
            "name": entry,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    return {"outputs": outputs, "count": len(outputs), "directory": OUTPUT_DIR}


# ------------------------------------------------------------------
# Stream audio file (with Range header support for seeking)
# ------------------------------------------------------------------
@app.get("/api/stream/{filename}")
async def stream_audio(filename: str, request: Request):
    # Search in both output and songs directories
    file_path = None
    for directory in [OUTPUT_DIR, SONGS_DIR]:
        candidate = os.path.join(directory, filename)
        if os.path.isfile(candidate):
            file_path = candidate
            break

    if file_path is None:
        raise HTTPException(status_code=404, detail=f"Audio file not found: {filename}")

    file_size = os.path.getsize(file_path)

    # Determine media type
    ext = os.path.splitext(filename)[1].lower()
    media_types = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    # Check for Range header
    range_header = request.headers.get("range")

    if range_header is None:
        # No range requested: return the full file
        return FileResponse(
            path=file_path,
            media_type=media_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            },
        )

    # Parse Range header: "bytes=start-end"
    try:
        range_spec = range_header.replace("bytes=", "")
        parts = range_spec.split("-")
        range_start = int(parts[0]) if parts[0] else 0
        range_end = int(parts[1]) if parts[1] else file_size - 1
    except (ValueError, IndexError):
        raise HTTPException(status_code=416, detail="Invalid Range header")

    if range_start >= file_size or range_end >= file_size:
        raise HTTPException(
            status_code=416,
            detail="Range not satisfiable",
        )

    content_length = range_end - range_start + 1

    def _read_range():
        with open(file_path, "rb") as f:
            f.seek(range_start)
            remaining = content_length
            chunk_size = 8192
            while remaining > 0:
                read_size = min(chunk_size, remaining)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(
        _read_range(),
        status_code=206,
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Range": f"bytes {range_start}-{range_end}/{file_size}",
            "Content-Length": str(content_length),
        },
    )


# ------------------------------------------------------------------
# YouTube download
# ------------------------------------------------------------------
@app.post("/api/songs/youtube")
async def download_youtube(req: YouTubeDownloadRequest):
    """Download audio from a YouTube URL."""
    if not is_valid_youtube_url(req.url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    task = _create_task()

    def _do_download():
        print(f"Starting YouTube download: {req.url}")

        # First get video info
        success, info = get_video_info(req.url)
        if not success:
            raise Exception(info.get("error", "Failed to get video info"))

        print(f"Video: {info.get('title')} ({info.get('duration_string')})")
        task["progress"] = 10

        # Download
        print("Downloading audio...")
        task["progress"] = 20
        success, message, filename = download_from_youtube(req.url, SONGS_DIR)

        if not success:
            raise Exception(message)

        task["progress"] = 90
        print(f"Download complete: {filename}")

        return {
            "filename": filename,
            "title": info.get("title"),
            "duration": info.get("duration"),
            "message": message,
        }

    _run_in_background(task, _do_download)
    return {"task_id": task["task_id"], "status": "pending", "url": req.url}


@app.get("/api/youtube/info")
async def get_youtube_info(url: str):
    """Get metadata about a YouTube video without downloading."""
    if not is_valid_youtube_url(url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    success, info = get_video_info(url)
    if not success:
        raise HTTPException(status_code=400, detail=info.get("error", "Failed to get video info"))

    return info


# ------------------------------------------------------------------
# Batch Analysis
# ------------------------------------------------------------------
@app.post("/api/analyze/batch")
async def batch_analyze(req: BatchAnalyzeRequest):
    """Analyze multiple songs in parallel using deep Kannada analysis."""
    if not req.filenames:
        raise HTTPException(status_code=400, detail="No filenames provided")

    # Validate all files exist
    for fn in req.filenames:
        fpath = os.path.join(SONGS_DIR, fn)
        if not os.path.isfile(fpath):
            raise HTTPException(status_code=404, detail=f"Song file not found: {fn}")

    task = _create_task()

    def _do_batch_analysis():
        venv_path = os.environ.get("VIRTUAL_ENV")
        if not venv_path:
            venv_path = os.path.abspath("./venv")

        cache = _load_analysis_cache()
        results = {}
        total = len(req.filenames)

        for idx, fn in enumerate(req.filenames):
            fpath = os.path.join(SONGS_DIR, fn)
            print(f"[{idx + 1}/{total}] Deep analyzing: {fn}")

            analysis = analyze_kannada_track_for_mashup(fpath, venv_path)
            cache[fpath] = analysis
            results[fn] = analysis

            progress = int(((idx + 1) / total) * 100)
            task["progress"] = progress
            print(f"[{idx + 1}/{total}] Complete ({progress}%)")

        _save_analysis_cache(cache)
        print(f"Batch analysis complete. {total} tracks analyzed.")

        return {
            "analyzed_count": len(results),
            "filenames": list(results.keys()),
        }

    _run_in_background(task, _do_batch_analysis)
    return {
        "task_id": task["task_id"],
        "status": "pending",
        "filenames": req.filenames,
        "count": len(req.filenames),
    }


# ------------------------------------------------------------------
# Batch Mashup Creation
# ------------------------------------------------------------------
@app.post("/api/mashup/batch")
async def batch_mashup(req: BatchMashupRequest):
    """Create multiple mashups in batch."""
    if not req.combinations:
        raise HTTPException(status_code=400, detail="No combinations provided")

    task = _create_task()

    def _do_batch_mashup():
        results = []
        total = len(req.combinations)

        for idx, combo in enumerate(req.combinations):
            song_a = combo.get("songA")
            song_b = combo.get("songB")
            style = combo.get("style", "relaxed")

            print(f"[{idx + 1}/{total}] Creating mashup: {song_a} + {song_b}")

            song_a_path = os.path.join(SONGS_DIR, song_a)
            song_b_path = os.path.join(SONGS_DIR, song_b)

            if not os.path.isfile(song_a_path) or not os.path.isfile(song_b_path):
                results.append({
                    "songA": song_a,
                    "songB": song_b,
                    "status": "failed",
                    "error": "File not found",
                })
                continue

            try:
                output_name = f"batch_mashup_{idx + 1}_{int(datetime.now().timestamp())}.mp3"
                output_path = os.path.join(OUTPUT_DIR, output_name)

                class Args:
                    pass

                args = Args()
                args.songA_path = song_a_path
                args.songB_path = song_b_path
                args.out = output_path

                run_single_mashup_mode(args)

                results.append({
                    "songA": song_a,
                    "songB": song_b,
                    "status": "completed",
                    "output_filename": output_name,
                })

            except Exception as e:
                results.append({
                    "songA": song_a,
                    "songB": song_b,
                    "status": "failed",
                    "error": str(e),
                })

            progress = int(((idx + 1) / total) * 100)
            task["progress"] = progress

        successful = sum(1 for r in results if r["status"] == "completed")
        print(f"Batch complete: {successful}/{total} mashups created")

        return {
            "results": results,
            "total": total,
            "successful": successful,
            "failed": total - successful,
        }

    _run_in_background(task, _do_batch_mashup)
    return {
        "task_id": task["task_id"],
        "status": "pending",
        "combination_count": len(req.combinations),
    }


# ------------------------------------------------------------------
# DJ Software Export (Rekordbox, Serato)
# ------------------------------------------------------------------
@app.post("/api/export/dj")
async def export_for_dj_software(req: ExportRequest):
    """Export analysis to DJ software format (Rekordbox XML, Serato crates)."""
    if not req.filenames:
        raise HTTPException(status_code=400, detail="No filenames provided")

    if req.format not in ("rekordbox", "serato", "json"):
        raise HTTPException(status_code=400, detail="Format must be rekordbox, serato, or json")

    task = _create_task()

    def _do_export():
        cache = _load_analysis_cache()
        analysis_list = []

        print(f"Preparing {req.format} export for {len(req.filenames)} tracks...")

        for fn in req.filenames:
            fpath = os.path.join(SONGS_DIR, fn)
            if fpath in cache:
                analysis_list.append(cache[fpath])
            elif fn in cache:
                analysis_list.append(cache[fn])
            else:
                print(f"Warning: No analysis found for {fn}")

        if not analysis_list:
            raise Exception("No analyzed tracks found. Run analysis first.")

        task["progress"] = 50

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if req.format == "rekordbox":
            output_filename = f"rekordbox_export_{timestamp}.xml"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            generate_rekordbox_xml(
                analysis_list,
                output_path,
                playlist_name=req.playlist_name or f"AI-Mixer {timestamp}"
            )
            print(f"Rekordbox XML exported: {output_filename}")

        elif req.format == "serato":
            output_filename = f"serato_crate_{timestamp}.m3u"
            generate_serato_crates(
                analysis_list,
                OUTPUT_DIR,
                crate_name=req.playlist_name or f"AI-Mixer_{timestamp}"
            )
            print(f"Serato crate exported: {output_filename}")

        elif req.format == "json":
            output_filename = f"analysis_export_{timestamp}.json"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            export_analysis_json(analysis_list, output_path)
            print(f"JSON export: {output_filename}")

        task["progress"] = 100

        return {
            "format": req.format,
            "output_filename": output_filename,
            "track_count": len(analysis_list),
        }

    _run_in_background(task, _do_export)
    return {
        "task_id": task["task_id"],
        "status": "pending",
        "format": req.format,
        "filenames": req.filenames,
    }


# ------------------------------------------------------------------
# Get all analysis data (for compatibility calculations)
# ------------------------------------------------------------------
@app.get("/api/analysis/all")
async def get_all_analysis():
    """Get all cached analysis data."""
    cache = _load_analysis_cache()

    # Filter to only include files in SONGS_DIR
    song_analyses = {}
    for path, analysis in cache.items():
        if SONGS_DIR in path:
            filename = os.path.basename(path)
            song_analyses[filename] = analysis

    return {
        "count": len(song_analyses),
        "analyses": song_analyses,
    }


# ---------------------------------------------------------------------------
# SANDALWOOD ENHANCEMENTS API
# ---------------------------------------------------------------------------

# ------------------------------------------------------------------
# Audio Validation
# ------------------------------------------------------------------
@app.post("/api/validate")
async def validate_audio(filenames: List[str]):
    """
    Validate audio files for corruption and quality issues.
    """
    file_paths = []
    for filename in filenames:
        path = validate_safe_path(SONGS_DIR, filename)
        if os.path.exists(path):
            file_paths.append(path)

    if not file_paths:
        raise HTTPException(status_code=400, detail="No valid files found")

    results = batch_validate_audio(file_paths)
    return results


@app.get("/api/validate/{filename}")
async def validate_single_audio(filename: str):
    """
    Validate a single audio file.
    """
    file_path = validate_safe_path(SONGS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    result = validate_audio_file(file_path)
    return result


# ------------------------------------------------------------------
# Singer Detection
# ------------------------------------------------------------------
class SingerDetectionRequest(BaseModel):
    filename: str


@app.post("/api/singer/detect")
async def detect_singer_endpoint(req: SingerDetectionRequest):
    """
    Detect the likely singer in a track and get EQ recommendations.
    Requires the track to have been analyzed first.
    """
    file_path = validate_safe_path(SONGS_DIR, req.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    task = _create_task("singer_detection", 1)

    def _do_detection():
        try:
            task["status"] = "running"
            print(f"Detecting singer in {req.filename}...")

            # Load audio
            y, sr = librosa.load(file_path, sr=22050, mono=True)

            # Extract vocal features (ideally from separated vocals, but use full mix as fallback)
            task["progress"] = 30
            vocal_features = extract_vocal_features(y, sr)

            task["progress"] = 60
            singer_id, confidence, profile = detect_singer(vocal_features)

            task["progress"] = 90
            eq_profile = get_singer_eq_profile(singer_id)

            return {
                "filename": req.filename,
                "detected_singer": profile["name"],
                "singer_id": singer_id,
                "confidence": round(confidence, 2),
                "era": profile["era"],
                "characteristics": profile["characteristics"],
                "eq_profile": eq_profile,
                "vocal_features": {
                    "spectral_centroid": vocal_features.get("spectral_centroid_mean"),
                    "pitch_mean": vocal_features.get("pitch_mean"),
                    "pitch_std": vocal_features.get("pitch_std"),
                },
            }
        except Exception as e:
            logger.exception("Singer detection failed")
            raise

    _run_in_background(task, _do_detection)
    return {"task_id": task["task_id"], "status": "pending"}


@app.get("/api/singer/profiles")
async def list_singer_profiles():
    """
    List all available Kannada singer profiles and their EQ settings.
    """
    profiles = []
    for singer_id, profile in KANNADA_SINGER_PROFILES.items():
        if singer_id != "unknown":
            profiles.append({
                "id": singer_id,
                "name": profile["name"],
                "era": profile["era"],
                "characteristics": profile["characteristics"],
                "eq_profile": profile["eq_profile"],
            })

    return {"singers": profiles, "count": len(profiles)}


# ------------------------------------------------------------------
# Film Era Detection
# ------------------------------------------------------------------
@app.post("/api/era/detect")
async def detect_era_endpoint(req: SingerDetectionRequest):
    """
    Detect the film era/decade of a track based on audio characteristics.
    """
    file_path = validate_safe_path(SONGS_DIR, req.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    task = _create_task("era_detection", 1)

    def _do_detection():
        try:
            task["status"] = "running"
            print(f"Detecting era for {req.filename}...")

            # Load audio
            y, sr = librosa.load(file_path, sr=22050, mono=True)
            task["progress"] = 50

            result = analyze_era_from_audio(y, sr)
            task["progress"] = 100

            return {
                "filename": req.filename,
                **result,
            }
        except Exception as e:
            logger.exception("Era detection failed")
            raise

    _run_in_background(task, _do_detection)
    return {"task_id": task["task_id"], "status": "pending"}


@app.get("/api/era/profiles")
async def list_era_profiles():
    """
    List all film era profiles with their characteristics.
    """
    profiles = []
    for era_id, profile in FILM_ERA_PROFILES.items():
        profiles.append({
            "id": era_id,
            "name": profile["name"],
            "years": profile["years"],
            "style": profile["style"],
            "composers": profile["composers"],
            "characteristics": profile["characteristics"],
        })

    return {"eras": profiles, "count": len(profiles)}


# ------------------------------------------------------------------
# Preview Generation
# ------------------------------------------------------------------
class TransitionPreviewRequest(BaseModel):
    track1: str
    track2: str
    transition_point1: float = Field(..., ge=0, description="Transition point in track 1 (seconds)")
    transition_point2: float = Field(0, ge=0, description="Start point in track 2 (seconds)")
    duration: float = Field(8.0, ge=2, le=30, description="Transition duration (seconds)")


@app.post("/api/preview/transition")
async def create_transition_preview(req: TransitionPreviewRequest):
    """
    Generate a preview of the transition between two tracks.
    Returns a downloadable preview audio file.
    """
    track1_path = validate_safe_path(SONGS_DIR, req.track1)
    track2_path = validate_safe_path(SONGS_DIR, req.track2)

    if not os.path.exists(track1_path):
        raise HTTPException(status_code=404, detail=f"Track 1 not found: {req.track1}")
    if not os.path.exists(track2_path):
        raise HTTPException(status_code=404, detail=f"Track 2 not found: {req.track2}")

    task = _create_task("transition_preview", 1)

    def _do_preview():
        try:
            task["status"] = "running"
            print(f"Generating transition preview: {req.track1} -> {req.track2}")

            task["progress"] = 20

            # Generate preview
            output_filename = f"preview_transition_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            output_path = os.path.join(OUTPUT_DIR, output_filename)

            generate_transition_preview(
                track1_path,
                track2_path,
                req.transition_point1,
                req.transition_point2,
                req.duration,
                output_path,
            )

            task["progress"] = 100

            return {
                "preview_file": output_filename,
                "track1": req.track1,
                "track2": req.track2,
                "transition_point1": req.transition_point1,
                "transition_point2": req.transition_point2,
                "duration": req.duration,
            }
        except Exception as e:
            logger.exception("Preview generation failed")
            raise

    _run_in_background(task, _do_preview)
    return {"task_id": task["task_id"], "status": "pending"}


class TrackPreviewRequest(BaseModel):
    filename: str
    start_time: float = Field(0, ge=0, description="Start time in seconds")
    duration: float = Field(30, ge=5, le=60, description="Preview duration in seconds")


@app.post("/api/preview/track")
async def create_track_preview(req: TrackPreviewRequest):
    """
    Generate a preview clip of a single track.
    """
    file_path = validate_safe_path(SONGS_DIR, req.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    output_filename = f"preview_{req.filename.replace('.mp3', '')}_{int(req.start_time)}s.wav"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    generate_track_preview(file_path, req.start_time, req.duration, output_path)

    return {
        "preview_file": output_filename,
        "original": req.filename,
        "start_time": req.start_time,
        "duration": req.duration,
    }


# ------------------------------------------------------------------
# Custom Cue Points
# ------------------------------------------------------------------
class SetCuePointRequest(BaseModel):
    filename: str
    cue_type: str = Field(..., pattern="^(mix_in|mix_out|drop|loop_start|loop_end|hot_cue_[1-8])$")
    time: float = Field(..., ge=0, description="Cue point time in seconds")
    label: Optional[str] = None


@app.post("/api/cue-points")
async def set_cue_point(req: SetCuePointRequest):
    """
    Set a custom cue point for a track.
    Custom cue points override automatic ones in mashup creation.
    """
    # Validate file exists
    file_path = validate_safe_path(SONGS_DIR, req.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    cue_points = set_custom_cue_point(
        req.filename,
        req.cue_type,
        req.time,
        req.label
    )

    return {
        "filename": req.filename,
        "cue_points": cue_points,
        "message": f"Set {req.cue_type} at {req.time}s",
    }


@app.get("/api/cue-points/{filename}")
async def get_cue_points(filename: str):
    """
    Get all custom cue points for a track.
    """
    custom_points = get_custom_cue_points(filename)

    # Also get auto-detected cue points from cache
    cache = _load_analysis_cache()
    file_path = os.path.join(SONGS_DIR, filename)

    auto_points = {}
    cached = cache.get(file_path) or cache.get(filename)
    if cached and "dj_cue_points" in cached:
        auto_points = cached["dj_cue_points"]

    # Merge with custom taking precedence
    merged = merge_cue_points(auto_points, custom_points)

    return {
        "filename": filename,
        "auto_detected": auto_points,
        "custom": custom_points,
        "merged": merged,
    }


@app.delete("/api/cue-points/{filename}/{cue_type}")
async def remove_cue_point(filename: str, cue_type: str):
    """
    Delete a custom cue point.
    """
    success = delete_custom_cue_point(filename, cue_type)

    if not success:
        raise HTTPException(status_code=404, detail="Cue point not found")

    return {
        "filename": filename,
        "deleted": cue_type,
        "message": "Cue point deleted",
    }


# ------------------------------------------------------------------
# Enhanced Mashup with Custom Cue Points
# ------------------------------------------------------------------
class EnhancedMashupRequest(BaseModel):
    filenames: list[str] = Field(..., min_length=2, max_length=50)
    style: str = Field("energetic", pattern="^(energetic|smooth|showcase)$")
    duration: int = Field(10, ge=1, le=60)
    use_custom_cue_points: bool = Field(True, description="Use custom cue points if available")
    apply_singer_eq: bool = Field(False, description="Apply singer-aware EQ profiles")
    detect_era: bool = Field(False, description="Group by detected era")


# ------------------------------------------------------------------
# Health check with feature list
# ------------------------------------------------------------------
@app.get("/api/features")
async def list_features():
    """
    List all available features and their status.
    """
    return {
        "version": "2.3.0",
        "features": {
            "core": {
                "quick_mashup": True,
                "dj_set": True,
                "sandalwood_mashup": True,
            },
            "analysis": {
                "17_step_analysis": True,
                "tala_detection": True,
                "pallavi_detection": True,
                "vocal_region_detection": True,
            },
            "professional_mixer": {
                "bpm_sync": True,
                "lufs_normalization": True,
                "beat_grid_alignment": True,
                "multiple_transitions": ["crossfade", "bass_swap", "filter_sweep", "echo_out"],
            },
            "enhancements": {
                "singer_detection": True,
                "singer_eq_profiles": len(KANNADA_SINGER_PROFILES) - 1,  # Exclude unknown
                "film_era_detection": True,
                "era_profiles": len(FILM_ERA_PROFILES),
                "audio_validation": True,
                "custom_cue_points": True,
                "transition_preview": True,
                "pagination": True,
            },
            "export": {
                "rekordbox_xml": True,
                "serato_crates": True,
                "json": True,
            },
            "integrations": {
                "youtube_download": True,
            },
        },
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
