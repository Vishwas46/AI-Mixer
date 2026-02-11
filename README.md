# AI-Mixer

![Version](https://img.shields.io/badge/version-2.2.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)

**AI-Mixer** is a powerful, local-first tool for intelligently remixing and mashing up songs using AI. It features advanced audio analysis including **Indian music Tala detection**, a beautiful **Web UI**, and professional DJ mixing capabilities.

## What's New in V2.2 - Professional Sandalwood Mixer

The Sandalwood/Kannada mashup mode now uses a **professional-grade audio engine**:

### Audio Processing Features

| Feature | Description | Benefit |
|---------|-------------|---------|
| **BPM Synchronization** | Time-stretch all tracks to common tempo using pyrubberband | No beat clashes between songs |
| **LUFS Normalization** | Normalize to -14 LUFS (YouTube standard) | Consistent volume, broadcast-ready |
| **Beat-Grid Alignment** | Transitions snap to actual beat positions | Professional, on-beat mixing |
| **Key Compatibility** | Detect and optionally pitch-shift incompatible keys | Harmonic mixing |
| **Tala-Aware Transitions** | Align transitions to Tala cycle boundaries | Respects Indian rhythmic structure |

### Professional Transition Types

| Type | Description | Best For |
|------|-------------|----------|
| `crossfade` | Equal-power crossfade | General purpose |
| `bass_swap` | High-pass outgoing, full incoming | Building energy |
| `filter_sweep` | Progressive low-pass on outgoing | Avoiding vocal clash |
| `echo_out` | Delay/reverb tail on outgoing | Dramatic energy drops |

### New: Pallavi Medley Endpoint

Create signature Sandalwood film medleys with `/api/mashup/pallavi-medley`:
- Extracts **Pallavi (chorus)** sections from each track
- Blends the catchiest parts together with quick 2-second transitions
- This is the authentic Kannada DJ medley style!

```bash
# Create a Pallavi medley
curl -X POST http://localhost:8000/api/mashup/pallavi-medley \
  -H "Content-Type: application/json" \
  -d '{"filenames": ["song1.mp3", "song2.mp3", "song3.mp3"]}'
```

### Export Quality

| Setting | Bitrate | Use Case |
|---------|---------|----------|
| `high` | 320 kbps | YouTube upload, archival |
| `standard` | 256 kbps | Streaming, sharing |

## What's New in V2.1

- **YouTube Download** - Paste a YouTube link, auto-download and analyze
- **DJ Software Export** - Export to Rekordbox XML, Serato crates, or JSON
- **Batch Processing** - Analyze multiple songs in parallel
- **Waveform Zoom & Scroll** - Enhanced audio player with zoom controls
- **A/B Transition Preview** - Preview transitions before creating mashup
- **Cue Point Markers** - Visual markers for MIX IN, DROP, MIX OUT on waveform
- **Volume Control** - Adjustable volume slider in audio player

## Features

### Core Mixing Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Quick Mashup** | Blend vocals of Song A with instrumental of Song B | Classic mashup creation |
| **DJ Set** | All songs mixed into one continuous track | Party mixes, podcasts |
| **Kannada/Sandalwood** | Indian film music optimized with Tala detection | Bollywood/Sandalwood mashups |

### Advanced Analysis (17 Steps)

| Step | Feature | Description |
|------|---------|-------------|
| 1 | Audio Loading | librosa loads at 22050 Hz |
| 2 | Base Analysis | BPM, Key, Energy, Structure |
| 3 | Vocal Analysis | Demucs-based vocal region detection |
| 4 | Beat Grid | Precise tempo + downbeat detection |
| 5 | Tala Detection | 4-method cross-validated Indian rhythm |
| 6 | Scale/Ragam | Kannada musical scale matching |
| 7 | Hook Detection | Catchy/memorable section identification |
| 8 | Harmonic Rhythm | Chord change rate analysis |
| 9 | Spectral Analysis | Brightness, bass, 6-band EQ profile |
| 10 | Percussion | Rhythm density, accent patterns |
| 11 | Section Classification | Pallavi, Charanam, Interlude, Intro/Outro |
| 12 | Emotional Curve | Intensity arc mapping |
| 13 | Phrase Boundaries | 4/8/16/32 bar structure |
| 14 | Vocal-Free Zones | Safe mix points detection |
| 15 | Anand Audio Patterns | Dialogue intro, filmi style, duet detection |
| 16 | DJ Cue Points | MIX IN, MIX OUT, DROP, LOOP, HOT CUES |
| 17 | Transition Recommendations | EQ swap, filter sweep, drop swap |

### New in V2.1: DJ Software Export

Export your analyzed songs to professional DJ software:

| Format | Software | Features Exported |
|--------|----------|-------------------|
| **Rekordbox XML** | Pioneer Rekordbox | BPM, Key, Cue Points, Memory Cues, Tempo Grid |
| **Serato M3U** | Serato DJ | Playlist with metadata |
| **JSON** | Custom Tools | Full analysis data for integration |

### Mixing Styles

**DJ Set Styles:**
| Style | Description |
|-------|-------------|
| `relaxed` | Full-length tracks with smooth 8-bar transitions |
| `energetic` | Highlight reels with punchy drops |
| `pro` | Professional phrase-matched mixing |

**Kannada/Sandalwood Styles:**
| Style | Track Selection | Clip Length | Focus |
|-------|-----------------|-------------|-------|
| `energetic` | Builds energy progressively, +10 bonus for energy increases | 60% (max 60s) | Centers clips on detected hooks |
| `smooth` | Consistent energy, starts with average-energy track | 80% of track | Standard mix_in to mix_out points |
| `showcase` | Best hooks first (ranked by hook_score) | Variable | Features each song's best parts |

## Installation

### 1. Clone & Setup

```bash
git clone https://github.com/Vishwas46/AI-Mixer.git
cd AI-Mixer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Install ffmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows (with Chocolatey)
choco install ffmpeg
```

### 3. Setup Web UI (Optional)

```bash
cd ui
npm install
cd ..
```

## Usage

### Option 1: Web UI (Recommended for Beginners)

```bash
# Terminal 1 - Start backend
python web_server.py

# Terminal 2 - Start frontend
cd ui && npm run dev
```

Open http://localhost:3000 and:
1. **Drop your songs** into the upload zone OR **paste a YouTube URL**
2. **Choose a mode** (Quick Mashup / DJ Set / Kannada)
3. **Pick a style** (Energetic / Smooth / Showcase)
4. **Set duration** (for Kannada mode: 5-30 minutes)
5. **Preview transitions** with A/B preview before creating
6. **Click "Create"** - done!
7. **Export to DJ software** (Rekordbox, Serato) or download mashup

### Option 2: Command Line

#### Quick Mashup (2 songs)
```bash
python creative_remix.py --mode single_mashup \
  --songA_path "song1.mp3" \
  --songB_path "song2.mp3" \
  --out "mashup.mp3"
```

#### DJ Set (multiple songs)
```bash
python creative_remix.py --mode dj_set \
  --songs_dir "songs/" \
  --mix_style energetic
```

#### Kannada Deep Analysis
```bash
# Analyze a single track
python kannada_mashup_analyzer.py "song.mp3" --output analysis.json

# Plan a multi-track mashup
python kannada_mashup_analyzer.py \
  --mashup-dir "kannada_songs/" \
  --style energetic \
  --duration 15 \
  --report
```

## Web API Endpoints

The backend exposes a REST API at `http://localhost:8000`:

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/songs` | GET | List all songs with analysis status |
| `/api/songs/upload` | POST | Upload a new audio file |
| `/api/songs/youtube` | POST | Download from YouTube URL |
| `/api/analysis/{filename}` | GET | Get cached analysis for a file |
| `/api/analysis/all` | GET | Get all cached analyses |

### Analysis Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze` | POST | Basic analysis (async) |
| `/api/analyze/kannada` | POST | Deep 17-step Kannada analysis (async) |
| `/api/analyze/batch` | POST | Batch analyze multiple files (async) |

### Mashup Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mashup/single` | POST | Create 2-song mashup (async) |
| `/api/mashup/djset` | POST | Create continuous DJ mix (async) |
| `/api/mashup/sandalwood` | POST | Create Kannada mashup + report (async) |
| `/api/mashup/batch` | POST | Create multiple mashups (async) |

### Export Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/export/dj` | POST | Export to DJ software (Rekordbox/Serato/JSON) |
| `/api/youtube/info` | GET | Get YouTube video metadata |

### Task & Output Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tasks/{id}` | GET | Check task status and progress |
| `/api/tasks/{id}/stream` | GET | SSE stream for live progress |
| `/api/outputs` | GET | List generated mashups |
| `/api/stream/{filename}` | GET | Stream audio with seeking support |

## Project Structure

```
AI-Mixer/
├── Backend (Python/FastAPI)
│   ├── web_server.py              # FastAPI backend (20+ endpoints)
│   ├── kannada_mashup_analyzer.py # Indian music analyzer (2400+ lines)
│   ├── audio_analyzer.py          # Core audio analysis
│   ├── creative_remix.py          # Mashup creation modes
│   ├── remix_engine.py            # Audio mixing/DSP
│   ├── youtube_downloader.py      # YouTube download integration
│   └── rekordbox_exporter.py      # DJ software export
│
├── Frontend (React + Vite)
│   └── ui/src/
│       ├── pages/
│       │   ├── Home.jsx           # Main mashup creation (drag-drop, modes)
│       │   ├── Library.jsx        # Song management & analysis
│       │   ├── Studio.jsx         # Advanced mixing modes
│       │   └── Results.jsx        # Output player
│       └── components/
│           ├── AudioPlayer.jsx    # WaveSurfer with zoom + cue markers
│           ├── CompatibilityGraph.jsx  # Visual song connections
│           ├── TransitionPreview.jsx   # A/B preview component
│           └── TaskProgress.jsx   # Live progress with SSE
│
├── songs/                         # Input audio files
└── remix_outputs/                 # Generated mashups + reports
```

## How It Works

### Tala Detection (V2)

Uses 4-method weighted scoring for robust detection:

| Method | Weight | Description |
|--------|--------|-------------|
| Onset Accent Analysis | 1.0 | Rhythmic pattern from onset strength |
| Percussion Isolation | 1.5 | HPSS-separated drum patterns |
| Beat Grid Cross-Validation | 2.0 | Validates against detected beats |
| Interval Pattern Analysis | 1.0 | Inter-beat timing patterns |

**Supported Talas:** Adi Tala (8 beats), Rupaka (6), Mishra Chapu (7), Khanda Chapu (5), Tisra (3), Eka (4), Sankeerna (9)

### Transition Logic

| Compatibility | Transition Type | Duration | Description |
|---------------|-----------------|----------|-------------|
| > 70% | EQ Swap | 8 bars | Smooth frequency blend |
| > 50% | Filter Sweep | 4 bars | Gradual filter transition |
| < 50% | Drop Swap | Instant | Hard cut on beat |

### Compatibility Scoring (Enhanced in V2.2)

Songs are scored on multiple factors (max 670 points):

| Factor | Points | Description |
|--------|--------|-------------|
| **BPM** | 0-100 | Tempo matching with half-time/double-time detection |
| **Key/Ragam** | 0-150 | Harmonic compatibility (Camelot wheel + Indian scales) |
| **Energy** | 0-80 | Intensity and dynamics matching |
| **Structure** | 0-80 | Phrase and section alignment |
| **Tala** | 0-60 | Indian rhythm pattern matching |
| **Spectral** | 0-50 | Frequency profile similarity |
| **Harmonic Rhythm** | 0-40 | Chord change rate matching |
| **Vocal** | -50 to +40 | Region-based overlap analysis (not flat penalty) |
| **Emotional** | 0-40 | Arc type matching (building, climax, etc.) |
| **Pallavi** | 0-30 | Chorus section mashup potential |

## Tech Stack

**Backend:**
- Python 3.8+
- FastAPI (REST API with async tasks)
- librosa (audio analysis)
- Demucs (source separation)
- rubberband (time-stretch/pitch-shift)
- pydub (audio manipulation)
- yt-dlp (YouTube downloads)

**Frontend:**
- React 19 + Vite
- WaveSurfer.js (waveform visualization)
- Framer Motion (animations)
- Lucide React (icons)
- React Router DOM (navigation)

## Implemented Features

- [x] Web UI with drag-and-drop
- [x] Three mixing modes (Quick/DJ Set/Kannada)
- [x] Visual compatibility graph
- [x] 17-step deep analysis
- [x] Tala detection with beat grid cross-validation
- [x] All Kannada styles (energetic/smooth/showcase)
- [x] Duration control for Kannada mode
- [x] Audio + report generation
- [x] Live progress with SSE
- [x] YouTube URL download
- [x] DJ software export (Rekordbox, Serato)
- [x] Batch analysis mode
- [x] Waveform zoom and scroll
- [x] A/B transition preview
- [x] Cue point markers on waveform
- [x] **Professional Sandalwood mixer** (BPM sync, LUFS normalization)
- [x] **Pallavi medley endpoint** (chorus-to-chorus mashups)
- [x] **Beat-grid aligned transitions**
- [x] **Multiple transition types** (crossfade, bass_swap, filter_sweep, echo_out)
- [x] **Enhanced compatibility scoring** (670-point system with Pallavi potential)

## Known Issues & Roadmap

### Fixed in V2.2

| Issue | Status | Fix |
|-------|--------|-----|
| CORS Open | **Fixed** | Restricted to localhost (configurable via `ALLOWED_ORIGINS`) |
| Path Validation | **Fixed** | `validate_safe_path()` prevents directory traversal |
| Input Validation | **Fixed** | Pydantic `Field` validators with patterns and limits |
| Request Size Limits | **Fixed** | 100MB max upload size enforced |
| Logging | **Fixed** | Proper logging framework replaces print statements |

### Roadmap (Next Steps)

- [ ] Real-time audio preview before creating mashup
- [ ] Custom transition point selection (manual cue points)
- [ ] Authentication and rate limiting for production
- [ ] Pagination for file listings
- [ ] Binary Serato crate format support
- [ ] Audio file corruption detection
- [ ] Singer-aware vocal EQ profiles
- [ ] Film era detection (group songs by decade/style)

## API Examples

### Download from YouTube

```bash
curl -X POST http://localhost:8000/api/songs/youtube \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=..."}'
```

### Batch Analyze Songs

```bash
curl -X POST http://localhost:8000/api/analyze/batch \
  -H "Content-Type: application/json" \
  -d '{"filenames": ["song1.mp3", "song2.mp3", "song3.mp3"]}'
```

### Export to Rekordbox

```bash
curl -X POST http://localhost:8000/api/export/dj \
  -H "Content-Type: application/json" \
  -d '{"filenames": ["song1.mp3", "song2.mp3"], "format": "rekordbox"}'
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

**Vishwas**

---
*Built with passion for Kannada music and code.*
