# AI-Mixer

![Version](https://img.shields.io/badge/version-2.5.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)

**AI-Mixer** is a powerful, local-first tool for intelligently remixing and mashing up songs using AI. It features advanced audio analysis including **Indian music Tala detection**, a beautiful **Web UI**, and professional DJ mixing capabilities.

---

## What's New in V2.5 - Intelligent Mixing Agent + Stem-Based DSP

### Intelligent Plan → Approve → Create Workflow

The Sandalwood Studio now features an **AI mixing agent** that automatically clusters tracks into compatible groups before mixing:

| Feature | Description |
|---------|-------------|
| **Track Clustering** | Greedy partition algorithm builds NxN compatibility matrix, groups tracks by best-fit |
| **Grade Distribution** | A-F grades (A≥80%, B≥65%, C≥50%, D≥35%, F<35%) for every track pair |
| **Group Review UI** | Visual group cards with compatibility badges, track lists, and style overrides |
| **Excluded Tracks** | Tracks with best compatibility <35% shown separately with reasons |
| **Multi-Mashup Generation** | One plan produces multiple mashups (one per group) in a single run |
| **5-Step Wizard** | Select → Analyze → **Review Plan** → Configure → Results |

### Stem-Based Mixing Engine

| Feature | Description |
|---------|-------------|
| **Demucs Stem Separation** | Splits tracks into vocals, drums, bass, other for independent processing |
| **Dual-Bus Timeline** | Instrumental + vocal busses mixed independently for cleaner results |
| **Formant-Preserving Pitch Shift** | pyrubberband `-F` flag keeps vocal character natural during key changes |
| **Shruti/Microtonal Tuning** | `librosa.estimate_tuning()` detects cents drift from A440 in vintage recordings |
| **Dynamic Sidechain Ducking** | RMS envelope → Gaussian smoothing → gain curve ducks instrumental under vocals |
| **Pedalboard Mastering Chain** | HPF 30Hz → Compressor → PeakLimiter via Spotify's Pedalboard library |

### Stem-Aware Transition Types

All 4 transition types now operate on separated stems for cleaner mixing:

| Type | Instrumental Bus | Vocal Bus | Duration |
|------|------------------|-----------|----------|
| `crossfade` | Equal-power sqrt curves | Equal-power sqrt curves | Tala-aware |
| `bass_swap` | Butterworth HPF on outgoing | sqrt crossfade | 8 bars (same tala) |
| `filter_sweep` | Progressive Butterworth LPF | sqrt crossfade | 4 bars (different tala) |
| `echo_out` | Multi-tap delay tail | Pedalboard delay tail | Tala-aware |

Transition type auto-selected based on energy differential, vocal overlap, and style.

### Deep Analysis Cache Validation

The plan endpoint now validates that cached analysis is the full 17-step deep analysis (not just basic 7-key). Tracks with only basic analysis are automatically re-analyzed before clustering.

---

## What's New in V2.4 - Sandalwood Studio UI

A dedicated **professional UI** for creating Kannada/Sandalwood mashups with a 5-step wizard:

### Sandalwood Studio Features

| Feature | Description |
|---------|-------------|
| **5-Step Wizard** | Guided workflow: Select → Analyze → Review Plan → Configure → Create |
| **Singer Detection Cards** | Visual cards showing detected artist with confidence bars |
| **Era Timeline** | Interactive decade visualization (1960s-2020s) |
| **Track Cards** | Drag-to-select with analysis badges (BPM, key, mood) |
| **Cue Point Editor** | Clickable waveform with custom cue markers |
| **Style Selector** | 4 mashup styles with animated transitions |
| **Progress Overlay** | Real-time creation progress with stage indicators |
| **Glass Morphism Design** | Modern UI with smooth Framer Motion animations |

Access the Sandalwood Studio at: **http://localhost:3000/sandalwood**

### Design System

- Glass morphism with backdrop blur
- Gold accent gradient for Sandalwood branding
- Framer Motion animations throughout
- Responsive layout with flex/grid
- Step indicator with progress tracking

---

## What's New in V2.3 - Complete Sandalwood Toolkit

### Singer Detection & EQ Profiles

Automatically detect famous Kannada playback singers and apply optimal EQ settings:

| Singer | Era | Style | EQ Focus |
|--------|-----|-------|----------|
| Dr. Rajkumar | 1960s-1990s | Classical, Powerful | Warmth boost, presence at 3.5kHz |
| S.P. Balasubrahmanyam | 1970s-2020s | Versatile, Melodic | Mid clarity, high shimmer |
| Rajesh Krishnan | 1990s-present | Energetic, Romantic | Bright, presence at 5kHz |
| K.S. Chithra | 1980s-present | Classical, Devotional | Balanced, presence at 5.5kHz |
| Shreya Ghoshal | 2000s-present | Ornamental, Bright | High clarity, air at 12kHz |
| K.J. Yesudas | 1960s-present | Classical, Rich | Warm, low boost |
| Sonu Nigam | 1990s-present | Powerful, Modern | Full range, presence at 4.5kHz |

```bash
# Detect singer in a track
curl -X POST http://localhost:8000/api/singer/detect \
  -H "Content-Type: application/json" \
  -d '{"filename": "naanu_neenu.mp3"}'
```

### Film Era Detection

Classify songs by decade and production style:

| Era | Years | Style | Typical Composers |
|-----|-------|-------|-------------------|
| 1960s Classical | 1960-1969 | Classical Devotional | G.K. Venkatesh, T.G. Lingappa |
| 1970s Melodic | 1970-1979 | Melodic Romantic | Rajan-Nagendra |
| 1980s Disco | 1980-1989 | Disco Pop | Hamsalekha, Upendra Kumar |
| 1990s Hamsalekha | 1990-1999 | Filmi Mass | Hamsalekha, V. Manohar |
| 2000s Modern | 2000-2009 | Modern Fusion | V. Harikrishna, Gurukiran |
| 2010s Contemporary | 2010-2019 | Contemporary EDM | Arjun Janya, V. Harikrishna |
| 2020s Indie | 2020-present | Indie Experimental | B. Ajaneesh Loknath, Ravi Basrur |

```bash
# Detect era of a track
curl -X POST http://localhost:8000/api/era/detect \
  -H "Content-Type: application/json" \
  -d '{"filename": "naanu_neenu.mp3"}'
```

### Audio File Validation

Detect corrupted or problematic audio files before processing:

| Check | Description |
|-------|-------------|
| File integrity | Verifies file can be loaded |
| Silence detection | Warns if audio is silent or very quiet |
| Clipping detection | Identifies distorted audio |
| DC offset | Detects problematic DC bias |
| Format validation | Verifies supported format |

```bash
# Validate audio files
curl -X POST http://localhost:8000/api/validate \
  -H "Content-Type: application/json" \
  -d '["song1.mp3", "song2.mp3"]'
```

### Real-Time Preview Generation

Preview transitions before creating the final mashup:

```bash
# Generate transition preview
curl -X POST http://localhost:8000/api/preview/transition \
  -H "Content-Type: application/json" \
  -d '{
    "track1": "song1.mp3",
    "track2": "song2.mp3",
    "transition_point1": 180.0,
    "transition_point2": 0.0,
    "duration": 8.0
  }'
```

### Custom Cue Points

Override automatic cue points with manual selections:

```bash
# Set a custom cue point
curl -X POST http://localhost:8000/api/cue-points \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "song.mp3",
    "cue_type": "mix_in",
    "time": 32.5,
    "label": "After Intro"
  }'

# Get cue points (auto + custom merged)
curl http://localhost:8000/api/cue-points/song.mp3
```

### Pagination for File Listings

Handle large libraries efficiently:

```bash
# Paginated song list
curl "http://localhost:8000/api/songs?page=1&limit=20&sort_by=modified&order=desc"
```

---

## What's New in V2.2 - Professional Sandalwood Mixer

The Sandalwood/Kannada mashup mode now uses a **professional-grade audio engine**:

### Audio Processing Features

| Feature | Description | Benefit |
|---------|-------------|---------|
| **Phase-Aligned Timeline** | Tracks placed on a timeline buffer with downbeat alignment | No drift between tracks |
| **BPM Synchronization** | Time-stretch all tracks to common tempo using pyrubberband | No beat clashes between songs |
| **LUFS Normalization** | Normalize to -14 LUFS (YouTube standard) | Consistent volume, broadcast-ready |
| **Beat-Grid Alignment** | Transitions snap to actual beat positions | Professional, on-beat mixing |
| **Key Compatibility** | Detect and optionally pitch-shift incompatible keys | Harmonic mixing |
| **Tala-Aware Transitions** | Snap transitions to Tala cycle boundaries | Respects Indian rhythmic structure |
| **Butterworth EQ Filters** | Professional-grade HPF/LPF via scipy.signal | Clean bass swaps and filter sweeps |

### Professional Transition Types

| Type | Description | Best For |
|------|-------------|----------|
| `crossfade` | Equal-power crossfade (sqrt curves) | General purpose |
| `bass_swap` | Butterworth HPF on outgoing, full incoming | Building energy |
| `filter_sweep` | Progressive Butterworth LPF on outgoing | Avoiding vocal clash |
| `echo_out` | Multi-tap delay tail on outgoing | Dramatic energy drops |

### Pallavi Medley Endpoint

Create signature Sandalwood film medleys with `/api/mashup/pallavi-medley`:
- Extracts **Pallavi (chorus)** sections from each track
- Blends the catchiest parts together with quick 2-second transitions
- This is the authentic Kannada DJ medley style!

```bash
curl -X POST http://localhost:8000/api/mashup/pallavi-medley \
  -H "Content-Type: application/json" \
  -d '{"filenames": ["song1.mp3", "song2.mp3", "song3.mp3"]}'
```

### Export Quality

| Setting | Bitrate | Use Case |
|---------|---------|----------|
| `high` | 320 kbps | YouTube upload, archival |
| `standard` | 256 kbps | Streaming, sharing |

---

## What's New in V2.1

- **YouTube Download** - Paste a YouTube link, auto-download and analyze
- **DJ Software Export** - Export to Rekordbox XML, Serato crates, or JSON
- **Batch Processing** - Analyze multiple songs in parallel
- **Waveform Zoom & Scroll** - Enhanced audio player with zoom controls
- **A/B Transition Preview** - Preview transitions before creating mashup
- **Cue Point Markers** - Visual markers for MIX IN, DROP, MIX OUT on waveform
- **Volume Control** - Adjustable volume slider in audio player

---

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

### DJ Software Export

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

---

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

---

## Usage

### Option 1: Web UI (Recommended)

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

---

## Web API Reference

The backend exposes a REST API at `http://localhost:8000`:

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/songs` | GET | List songs with pagination (`?page=1&limit=50`) |
| `/api/songs/upload` | POST | Upload a new audio file |
| `/api/songs/youtube` | POST | Download from YouTube URL |
| `/api/analysis/{filename}` | GET | Get cached analysis for a file |
| `/api/analysis/all` | GET | Get all cached analyses |
| `/api/features` | GET | List all available features and version |

### Analysis Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze` | POST | Basic analysis (async) |
| `/api/analyze/kannada` | POST | Deep 17-step Kannada analysis (async) |
| `/api/analyze/batch` | POST | Batch analyze multiple files (async) |
| `/api/validate` | POST | Validate audio files for issues |
| `/api/validate/{filename}` | GET | Validate single audio file |

### Mashup Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mashup/single` | POST | Create 2-song mashup (async) |
| `/api/mashup/djset` | POST | Create continuous DJ mix (async) |
| `/api/mashup/sandalwood` | POST | Create Kannada mashup + report (async) |
| `/api/mashup/sandalwood/plan` | POST | Analyze + cluster tracks → returns plan with groups (async) |
| `/api/mashup/sandalwood/create` | POST | Create mashups from approved plan with style overrides (async) |
| `/api/mashup/pallavi-medley` | POST | Create Pallavi-to-Pallavi medley (async) |
| `/api/mashup/batch` | POST | Create multiple mashups (async) |

### Singer & Era Detection

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/singer/detect` | POST | Detect singer and get EQ profile |
| `/api/singer/profiles` | GET | List all singer profiles |
| `/api/era/detect` | POST | Detect film era/decade |
| `/api/era/profiles` | GET | List all era profiles |

### Preview & Cue Points

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/preview/transition` | POST | Generate transition preview audio |
| `/api/preview/track` | POST | Generate track clip preview |
| `/api/cue-points` | POST | Set custom cue point |
| `/api/cue-points/{filename}` | GET | Get all cue points (auto + custom) |
| `/api/cue-points/{filename}/{type}` | DELETE | Delete custom cue point |

### Export Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/export/dj` | POST | Export to DJ software (Rekordbox/Serato/JSON) |

### Task & Output Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tasks/{id}` | GET | Check task status and progress |
| `/api/tasks/{id}/stream` | GET | SSE stream for live progress |
| `/api/outputs` | GET | List generated mashups |
| `/api/stream/{filename}` | GET | Stream audio with seeking support |

---

## Project Structure

```
AI-Mixer/
├── Backend (Python/FastAPI)
│   ├── web_server.py              # FastAPI backend (30+ endpoints)
│   ├── kannada_mashup_analyzer.py # Indian music analyzer + track clustering (2970+ lines)
│   ├── sandalwood_mixer.py        # Stem-based mixer (Demucs, Pedalboard mastering)
│   ├── sandalwood_enhancements.py # Singer/Era detection, validation
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
│       │   ├── SandalwoodStudio.jsx # Kannada mashup wizard (V2.4)
│       │   ├── SandalwoodStudio.css # Sandalwood Studio styling
│       │   └── Results.jsx        # Output player
│       └── components/
│           ├── AudioPlayer.jsx    # WaveSurfer with zoom + cue markers
│           ├── CompatibilityGraph.jsx  # Visual song connections
│           ├── TransitionPreview.jsx   # A/B preview component
│           └── TaskProgress.jsx   # Live progress with SSE
│
├── songs/                         # Input audio files
├── remix_outputs/                 # Generated mashups + reports
└── custom_cue_points.json         # User-defined cue points
```

---

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

### Compatibility Scoring (670 points max)

| Factor | Points | Description |
|--------|--------|-------------|
| **BPM** | 0-100 | Tempo matching with half-time/double-time detection |
| **Key/Ragam** | 0-150 | Harmonic compatibility (Camelot wheel + Indian scales) |
| **Energy** | 0-80 | Intensity and dynamics matching |
| **Structure** | 0-80 | Phrase and section alignment |
| **Tala** | 0-60 | Indian rhythm pattern matching |
| **Spectral** | 0-50 | Frequency profile similarity |
| **Harmonic Rhythm** | 0-40 | Chord change rate matching |
| **Vocal** | -50 to +40 | Region-based overlap analysis |
| **Emotional** | 0-40 | Arc type matching (building, climax, etc.) |
| **Pallavi** | 0-30 | Chorus section mashup potential |

---

## Tech Stack

**Backend:**
- Python 3.8+
- FastAPI (REST API with async tasks)
- librosa (audio analysis)
- Demucs (source separation — stem-based mixing)
- pyrubberband (time-stretch/pitch-shift with formant preservation)
- pyloudnorm (LUFS normalization)
- pedalboard (Spotify's audio plugin host — mastering chain)
- scipy (Butterworth filter design for transitions)
- pydub (audio manipulation)
- yt-dlp (YouTube downloads)

**Frontend:**
- React 19 + Vite
- WaveSurfer.js (waveform visualization)
- Framer Motion (animations)
- Lucide React (icons)
- React Router DOM (navigation)

---

## Implemented Features

### Core Features
- [x] Web UI with drag-and-drop
- [x] Three mixing modes (Quick/DJ Set/Kannada)
- [x] Visual compatibility graph
- [x] 17-step deep analysis
- [x] Tala detection with beat grid cross-validation
- [x] All Kannada styles (energetic/smooth/showcase)
- [x] Duration control for Kannada mode
- [x] Audio + report generation
- [x] Live progress with SSE

### V2.5 Features
- [x] Stem-based mixing with Demucs dual-bus timeline
- [x] Formant-preserving pitch shift (pyrubberband -F)
- [x] Shruti/microtonal tuning detection
- [x] Dynamic sidechain ducking (vocal-instrumental)
- [x] Pedalboard mastering chain (HPF + Compressor + Limiter)
- [x] Intelligent track clustering (greedy partition algorithm)
- [x] Plan → Approve → Create workflow with 2 new API endpoints
- [x] 5-step wizard with plan review UI (group cards, grade badges)
- [x] Multiple mashup generation per plan
- [x] Deep analysis cache validation (basic vs deep)

### V2.4 Features
- [x] Sandalwood Studio UI with 5-step wizard
- [x] Singer detection cards with confidence visualization
- [x] Era timeline with decade visualization
- [x] Cue point editor with waveform markers
- [x] Style selector with animated transitions
- [x] Progress overlay with stage indicators
- [x] Glass morphism design system
- [x] Framer Motion animations throughout

### V2.3 Features
- [x] Singer detection with 7 Kannada playback artist profiles
- [x] Singer-aware EQ recommendations
- [x] Film era detection (7 decades from 1960s-2020s)
- [x] Audio file corruption/quality detection
- [x] Real-time transition preview generation
- [x] Custom cue point management
- [x] Paginated file listings
- [x] Feature discovery endpoint (`/api/features`)

### V2.2 Features
- [x] Professional Sandalwood mixer (BPM sync, LUFS normalization)
- [x] Pallavi medley endpoint (chorus-to-chorus mashups)
- [x] Beat-grid aligned transitions
- [x] Multiple transition types (crossfade, bass_swap, filter_sweep, echo_out)
- [x] Enhanced compatibility scoring (670-point system)

### V2.1 Features
- [x] YouTube URL download
- [x] DJ software export (Rekordbox, Serato)
- [x] Batch analysis mode
- [x] Waveform zoom and scroll
- [x] A/B transition preview
- [x] Cue point markers on waveform

---

## Fixed Issues

| Issue | Version | Fix |
|-------|---------|-----|
| CORS Open | V2.2 | Restricted to localhost (configurable via `ALLOWED_ORIGINS`) |
| Path Validation | V2.2 | `validate_safe_path()` prevents directory traversal |
| Input Validation | V2.2 | Pydantic `Field` validators with patterns and limits |
| Request Size Limits | V2.2 | 100MB max upload size enforced |
| Logging | V2.2 | Proper logging framework replaces print statements |
| No BPM Sync | V2.2 | Professional mixer with pyrubberband time-stretch |
| Volume Inconsistency | V2.2 | LUFS normalization to -14 LUFS |

---

## Roadmap

### Planned Features
- [ ] Authentication and rate limiting for production
- [ ] Binary Serato crate format support
- [ ] Real-time waveform mixing in browser
- [ ] Real-time stem preview in browser
- [ ] Composer-aware sequencing (group Hamsalekha songs together)
- [ ] Multi-language support (Hindi, Telugu, Tamil mashups)
- [ ] Machine learning singer identification improvement
- [x] ~~Stem separation before mixing for cleaner results~~ (V2.5)

---

## API Examples

### Download from YouTube
```bash
curl -X POST http://localhost:8000/api/songs/youtube \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=..."}'
```

### Create Sandalwood Mashup
```bash
curl -X POST http://localhost:8000/api/mashup/sandalwood \
  -H "Content-Type: application/json" \
  -d '{
    "filenames": ["song1.mp3", "song2.mp3", "song3.mp3"],
    "style": "energetic",
    "duration": 10
  }'
```

### Plan → Create Mashup (Intelligent Agent)
```bash
# Step 1: Generate mashup plan (clusters tracks into compatible groups)
curl -X POST http://localhost:8000/api/mashup/sandalwood/plan \
  -H "Content-Type: application/json" \
  -d '{"filenames": ["song1.mp3", "song2.mp3", "song3.mp3", "song4.mp3", "song5.mp3"], "duration": 15}'

# Step 2: Poll task for plan_id
curl http://localhost:8000/api/tasks/{TASK_ID}

# Step 3: Create mashups from approved plan (with optional style overrides)
curl -X POST http://localhost:8000/api/mashup/sandalwood/create \
  -H "Content-Type: application/json" \
  -d '{"plan_id": "PLAN_ID", "groups": [{"group_id": 1, "style": "smooth"}]}'
```

### Detect Singer & Get EQ
```bash
curl -X POST http://localhost:8000/api/singer/detect \
  -H "Content-Type: application/json" \
  -d '{"filename": "song.mp3"}'
```

### Export to Rekordbox
```bash
curl -X POST http://localhost:8000/api/export/dj \
  -H "Content-Type: application/json" \
  -d '{"filenames": ["song1.mp3", "song2.mp3"], "format": "rekordbox"}'
```

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

**Vishwas**

---
*Built with passion for Kannada music and code.*
