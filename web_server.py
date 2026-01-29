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
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    JSONResponse,
    FileResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    filename: Optional[str] = None
    filenames: Optional[list[str]] = None


class KannadaAnalyzeRequest(BaseModel):
    filename: str


class SingleMashupRequest(BaseModel):
    songA: str
    songB: str
    output_name: str


class DJSetRequest(BaseModel):
    songs_dir: str = "songs/"
    mix_style: str = "relaxed"


class SandalwoodMashupRequest(BaseModel):
    filenames: list[str]
    style: str = "energetic"
    duration: int = 10


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
# List songs
# ------------------------------------------------------------------
@app.get("/api/songs")
async def list_songs():
    if not os.path.isdir(SONGS_DIR):
        return {"songs": []}

    cache = _load_analysis_cache()
    songs = []

    for entry in sorted(os.listdir(SONGS_DIR)):
        if not entry.lower().endswith(".mp3"):
            continue
        full_path = os.path.join(SONGS_DIR, entry)
        stat = os.stat(full_path)

        # Check if analysis cache exists for this file
        has_cache = full_path in cache or entry in cache

        songs.append({
            "name": entry,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "has_analysis": has_cache,
        })

    return {"songs": songs, "count": len(songs), "directory": SONGS_DIR}


# ------------------------------------------------------------------
# Upload song
# ------------------------------------------------------------------
@app.post("/api/songs/upload")
async def upload_song(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Sanitize filename: keep only the basename
    safe_name = os.path.basename(file.filename)
    if not safe_name.lower().endswith((".mp3", ".wav", ".flac", ".ogg", ".m4a")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Accepted: mp3, wav, flac, ogg, m4a",
        )

    dest_path = os.path.join(SONGS_DIR, safe_name)
    contents = await file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

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
            task["progress"] = int(((idx + 1) / total) * 70)  # 0-70% for analysis

        # Step 2: Plan the mashup
        print("Planning mashup order and transitions...")
        task["progress"] = 75
        mashup_plan = plan_kannada_mashup(all_tracks, req.duration, req.style)
        task["progress"] = 90

        # Step 3: Generate human-readable report
        print("Generating mashup report...")
        report = generate_mashup_report(mashup_plan)
        task["progress"] = 95

        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"kannada_mashup_report_{req.style}_{timestamp}.txt"
        report_path = os.path.join(OUTPUT_DIR, report_filename)
        with open(report_path, "w") as f:
            f.write(report)

        # Also cache analyses
        cache = _load_analysis_cache()
        for track in all_tracks:
            cache[track["file_path"]] = track
        _save_analysis_cache(cache)

        print(f"Mashup planning complete. Report saved to {report_filename}")
        return {
            "plan": mashup_plan,
            "report": report,
            "report_filename": report_filename,
            "track_count": len(all_tracks),
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


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
