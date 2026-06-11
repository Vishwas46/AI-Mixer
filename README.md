# Sandalwood AI Mixer

![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)

**Sandalwood AI Mixer** is a local-first AI mashup studio for Kannada (Sandalwood) film music.
Give it your songs — it analyzes them like a DJ would (tempo, key, tala, vocals, hooks, song
sections) and produces professional, broadcast-loudness mixes.

It makes two kinds of mixes, modeled on the signature styles of real Kannada DJ sets:

| Mix | What it is | Inspired by |
|-----|------------|-------------|
| **Mashup Lab** | The **voice of one song over the music of another** — tempo-locked, key-locked, beat-aligned | Divine mashups, DJ Chetas-style cocktail mashups, club remixes |
| **Nonstop Party Mix** | Many songs joined into one continuous DJ mix, auto-planned by compatibility | Nonstop Kannada DJ sets |

Everything runs on your machine. No cloud, no accounts, your songs never leave your computer.

---

## Quickstart

### 1. Backend (Python 3.8+)

```bash
git clone https://github.com/Vishwas46/AI-Mixer.git
cd AI-Mixer

python3 -m venv venv            # must be ./venv — the stem separator looks for it
source venv/bin/activate        # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. System tools (recommended)

```bash
# macOS
brew install ffmpeg rubberband

# Ubuntu/Debian
sudo apt install ffmpeg rubberband-cli
```

Both are optional — the app still works without them (see
[Graceful degradation](#graceful-degradation)) — but with them you get MP3 export
and the highest-quality time-stretch/pitch-shift.

### 3. Best-quality vocal separation (optional)

```bash
pip install -r requirements-quality.txt   # BS-RoFormer via audio-separator (~600MB one-time model download)
export AIMIXER_STEM_QUALITY=best          # auto (default) | fast | best | none (offline, no separation)
```

### 4. Run it

```bash
# Terminal 1 — backend
venv/bin/uvicorn web_server:app --host 0.0.0.0 --port 8000

# Terminal 2 — web UI
cd ui && npm install && npm run dev
```

Open **http://localhost:3000** — the Sandalwood Studio wizard is the home page.

---

## Using the app

1. **Choose what to make** — *Mashup Lab* (2 songs) or *Nonstop Party Mix* (2+ songs).
2. **Add songs** — drag-and-drop files, or paste a YouTube link.
3. **Mashup Lab:** pick the *Voice* song and the *Music* song, choose one of three styles,
   and hit Create:
   - **Divine Mashup** — soft devotional blend, voice floats with gentle echo
   - **Cocktail Party** — punchy voice entries over a dance beat
   - **Club Remix** — filtered build-up, a drop, then the voice rides the beat
4. **Nonstop Party Mix:** analyze your tracks, review the AI's grouping plan
   (compatibility grades A–F per pair), adjust styles per group, and create —
   one mashup per compatible group.
5. Listen and download from **My Mixes**.

The old Quick Mashup and DJ Set modes still exist under **Advanced** in the navbar.

---

## AI models

| Model | Role | Status | First-run download |
|-------|------|--------|--------------------|
| **Demucs htdemucs_ft** (Meta) | 4-stem separation (vocals/drums/bass/other) | Default, installed with requirements.txt | ~1 GB from Meta's servers |
| **BS-RoFormer** (via [audio-separator](https://github.com/nomadkaraoke/python-audio-separator)) | Best-quality vocal/instrumental split (SDX23-winning family) | Optional — `requirements-quality.txt` | ~600 MB from Hugging Face |
| librosa DSP | Tempo, key, tala, structure, hooks (17-step analysis) | Always on | none |

Selection is automatic: RoFormer when installed (`AIMIXER_STEM_QUALITY=auto|best`),
otherwise Demucs, otherwise a basic filter fallback. The result reports which tier ran.
Set `AIMIXER_STEM_QUALITY=none` (alias `off`) to skip neural separation everywhere —
analysis, Mashup Lab and the nonstop mix all degrade to master-channel mixing, so the
whole pipeline runs with no model weights and no network (offline / low-resource / CI).

**Evaluated, on the roadmap (not shipped):**
- *All-In-One music structure analyzer* — trained beat/downbeat/section model; heavy
  native dependencies, revisit when packaging stabilizes.
- *Google Magenta RealTime 2* — open-weights real-time music **generation**; interesting
  for AI-generated transition fills between songs, but it creates new music rather than
  mixing existing songs, so it is out of scope for the mixer core.
- *Reference-mix learning* — analyze a downloaded DJ mix and auto-extract its style
  template (energy arc, transition timing) to drive the mixer.

---

## How the mixing works

### Mashup Lab (vocal-over-instrumental)

1. **Separate** both songs into stems (RoFormer → Demucs → filter fallback).
   The music song keeps only its instruments; the voice song keeps only its vocals.
2. **Tempo-lock** — the music track is the master clock; the vocals are time-stretched
   to it (half/double-time aware, transient-preserving).
3. **Key-lock** — vocals are pitch-shifted with formant preservation (no chipmunk voice),
   including microtonal *shruti* drift correction for vintage recordings. Shifts beyond
   ±3 semitones fold to the Camelot-adjacent key instead.
4. **Place phrases** — sung phrases (from pallavi/charanam sections × detected vocal
   regions) snap to the music track's tala-cycle downbeats; the voice song's own gaps
   become natural instrumental breakdowns.
5. **Style FX** — per-preset reverb, intro filter sweep, pre-vocal drop.
6. **Duck & master** — sidechain ducking carves space for the voice, then a mastering
   chain (30 Hz HPF → bus compressor → limiter) and LUFS normalization (-14 default).

### Nonstop Party Mix

- **17-step deep analysis** per track: BPM/beat grid, 4-method tala detection,
  scale/ragam, vocal regions (Demucs), hooks & drops, harmonic rhythm, spectral profile,
  percussion density, pallavi/charanam sections, emotional curve, phrase boundaries,
  vocal-free zones, Anand-Audio patterns, DJ cue points, transition recommendations.
- **670-point compatibility scoring** between every pair (BPM, key/ragam, energy,
  structure, tala, spectral, harmonic rhythm, vocal overlap, emotional arc, pallavi).
- **Clustering agent** partitions tracks into compatible groups (A–F grades) and plans
  an energy arc per group (energetic / smooth / showcase).
- **Stem-based timeline** with four transition types — crossfade, bass swap,
  filter sweep, echo out — snapped to tala boundaries, then the same ducking and
  mastering chain as the Lab.

### Graceful degradation

| Missing | What happens |
|---------|--------------|
| ffmpeg | Output is WAV instead of MP3 (the UI tells you) |
| rubberband CLI | librosa time-stretch/pitch-shift fallback (formant preservation lost) |
| Demucs/RoFormer weights (no network) | Mixes still render from the master channel; the result is flagged `degraded` with a warning |
| `AIMIXER_STEM_QUALITY=none` set | Neural separation skipped everywhere by choice — fully offline; mixes render from the master channel, flagged `degraded` |
| pedalboard / pyloudnorm | Peak normalization fallback |

---

## Web API

Backend runs at `http://localhost:8000`. Highlights (see `/api/features` for the full list):

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/songs` | GET | List songs (paginated) |
| `/api/songs/upload` | POST | Upload an audio file |
| `/api/songs/youtube` | POST | Download a song from a YouTube URL |
| `/api/analyze/kannada` | POST | 17-step deep analysis (async task) |
| **`/api/mashup/lab`** | POST | **Mashup Lab**: `{vocal_track, backing_track, style}` with style `divine` \| `cocktail_party` \| `club_remix` |
| `/api/mashup/sandalwood` | POST | Nonstop mix in one call (analyze → plan → create) |
| `/api/mashup/sandalwood/plan` | POST | Cluster tracks into compatible groups, return plan |
| `/api/mashup/sandalwood/create` | POST | Create mashups from an approved plan |
| `/api/mashup/pallavi-medley` | POST | Chorus-to-chorus medley |
| `/api/singer/detect` | POST | Detect Kannada playback singer + EQ profile |
| `/api/era/detect` | POST | Detect film era (1960s–2020s) |
| `/api/tasks/{id}` | GET | Task status/progress (`/stream` for SSE) |
| `/api/outputs` | GET | List generated mixes |
| `/api/stream/{filename}` | GET | Stream/download audio with seeking |
| `/api/mashup/single`, `/api/mashup/djset` | POST | *Advanced* legacy modes |
| `/api/export/dj` | POST | Export analysis to Rekordbox/Serato/JSON |

Example — create a divine mashup:

```bash
curl -X POST http://localhost:8000/api/mashup/lab \
  -H "Content-Type: application/json" \
  -d '{"vocal_track": "devotional_song.mp3", "backing_track": "modern_beat.mp3", "style": "divine"}'
# → {"task_id": "..."}; poll /api/tasks/{task_id} until completed
```

---

## Project structure

```
AI-Mixer/
├── web_server.py               # FastAPI backend (tasks, SSE progress, all endpoints)
├── kannada_mashup_analyzer.py  # 17-step analysis, compatibility scoring, clustering
├── sandalwood_mixer.py         # Nonstop stem-based mixer + mastering chain
├── mashup_lab.py               # Vocal-over-instrumental engine (V3)
├── stem_separation.py          # RoFormer/Demucs quality tiers (V3)
├── sandalwood_enhancements.py  # Singer/era detection, validation, previews
├── audio_analyzer.py           # Base analysis + Demucs vocal regions
├── creative_remix.py           # Legacy quick-mashup / DJ-set modes (Advanced)
├── remix_engine.py             # Stem overlay engine used by the quick mashup
├── audio_utils.py              # Shared audio IO + export (MP3/WAV fallback)
├── youtube_downloader.py       # yt-dlp integration
├── rekordbox_exporter.py       # DJ software export
├── requirements.txt            # Core dependencies
├── requirements-quality.txt    # Optional BS-RoFormer tier
├── tests/
│   ├── make_test_songs.py      # Synthetic songs at known BPM/key
│   └── test_pipeline.py        # End-to-end pipeline check (no network needed)
├── tools/                      # Dev/legacy utilities
└── ui/                         # React 19 + Vite frontend
    └── src/
        ├── api.js              # Central API client (VITE_API_BASE)
        ├── pages/              # SandalwoodStudio (home), Library, Results, Advanced
        └── components/         # AudioPlayer, TransitionPreview, TaskProgress, Navbar
```

Songs live in `songs/`, generated mixes in `remix_outputs/` — both git-ignored.

---

## Testing

```bash
# Renders 3 synthetic songs (92/104/120 BPM, known keys) into songs/
venv/bin/python tests/make_test_songs.py

# Full pipeline: analysis sanity → 3 Mashup Lab styles → nonstop mix,
# with loudness/clipping/duration assertions. Fully offline by default —
# defaults AIMIXER_STEM_QUALITY=none, so no model weights and no network.
venv/bin/python tests/test_pipeline.py

# To exercise real neural separation instead (downloads Demucs weights once):
AIMIXER_STEM_QUALITY=fast venv/bin/python tests/test_pipeline.py
```

For a real-audio test, drop two Kannada songs into `songs/` (or paste YouTube links in
the UI) and run a Divine mashup — listen for the voice entering on the beat.

---

## Version history

| Version | Highlights |
|---------|-----------|
| **3.0** | Sandalwood-first MVP: Mashup Lab engine + UI (3 style presets), RoFormer quality tier, central UI API client, Advanced page for legacy modes, README as single source of truth, synthetic-audio test suite, and 10 bug fixes (librosa 0.10+ tempo arrays, multi-track planner crash, section-key mismatch, task-creation TypeErrors, mastering-chain limiter import, `/api/analysis/all` route shadowing, UI/API field mismatches, upload dependency, true-peak guard) |
| 2.5 | Plan → Approve → Create clustering agent, stem-based dual-bus mixing |
| 2.4 | Sandalwood Studio wizard UI |
| 2.3 | Singer/era detection, validation, previews, cue points |
| 2.2 | Professional mixer: BPM sync, LUFS, tala-aware transitions, Butterworth EQ |
| 2.1 | YouTube download, DJ export, batch analysis |

---

## License

MIT — see [LICENSE](LICENSE).

## Author

**Vishwas**

---
*Built with passion for Kannada music and code.*
