# AI-Mixer

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)

**AI-Mixer** is a powerful, local-first tool for intelligently remixing and mashing up songs using AI. It features advanced audio analysis including **Indian music Tala detection**, a beautiful **Web UI**, and professional DJ mixing capabilities.

## What's New in V2

- **Web UI** - Beautiful drag-and-drop interface with dark glassmorphism theme
- **Kannada/Sandalwood Mode** - Optimized for Indian film music with Tala & Ragam detection
- **Visual Compatibility Graph** - See how your songs connect at a glance
- **One-Click Mashups** - Drop songs, pick a style, get your mix
- **17-Step Deep Analysis** - Professional DJ-grade analysis for each track

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
1. **Drop your songs** into the upload zone
2. **Choose a mode** (Quick Mashup / DJ Set / Kannada)
3. **Pick a style** (Energetic / Smooth / Showcase)
4. **Set duration** (for Kannada mode: 5-30 minutes)
5. **Click "Analyze & Create"** - done!
6. **Download** audio mashup + detailed report

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

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/songs` | GET | List all songs with analysis status |
| `/api/songs/upload` | POST | Upload a new audio file |
| `/api/analyze/kannada` | POST | Deep 17-step Kannada analysis (async) |
| `/api/mashup/single` | POST | Create 2-song mashup (async) |
| `/api/mashup/djset` | POST | Create DJ set (async) |
| `/api/mashup/sandalwood` | POST | Create Kannada mashup + report (async) |
| `/api/tasks/{id}` | GET | Check task status and progress |
| `/api/tasks/{id}/stream` | GET | SSE stream for live progress |
| `/api/outputs` | GET | List generated mashups |
| `/api/stream/{filename}` | GET | Stream audio with seeking support |

## Project Structure

```
AI-Mixer/
├── creative_remix.py          # Main CLI entry point
├── audio_analyzer.py          # Core audio analysis (BPM, key, energy)
├── remix_engine.py            # Mixing engine with Demucs separation
├── kannada_mashup_analyzer.py # Indian music analyzer (2400+ lines)
│                              # - Tala detection (7 talas)
│                              # - Scale/Ragam analysis (10 scales)
│                              # - DJ cue point generation
│                              # - Mashup planning & compatibility
├── web_server.py              # FastAPI backend (13 endpoints)
├── ui/                        # React + Vite frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Home.jsx       # Main mashup creation (drag-drop, modes)
│   │   │   ├── Library.jsx    # Song management
│   │   │   └── Results.jsx    # Output player
│   │   └── components/
│   │       ├── AudioPlayer.jsx         # WaveSurfer-based player
│   │       ├── CompatibilityGraph.jsx  # Visual song connections
│   │       ├── TaskProgress.jsx        # Live progress with SSE
│   │       └── Navbar.jsx
├── songs/                     # Input audio files (place your MP3s here)
└── remix_outputs/             # Generated mashups + reports
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

### Compatibility Scoring

Songs are scored on multiple factors:
- **BPM** (0-30 pts) - Tempo matching, half-time detection
- **Key** (0-30 pts) - Harmonic compatibility (Camelot wheel)
- **Energy** (0-20 pts) - Intensity matching
- **Tala** (0-20 pts) - Rhythm pattern matching

## Tech Stack

**Backend:**
- Python 3.8+
- FastAPI (REST API with async tasks)
- librosa (audio analysis)
- Demucs (source separation)
- rubberband (time-stretch/pitch-shift)
- pydub (audio manipulation)

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

## Roadmap (Next Steps)

- [ ] Real-time audio preview before creating mashup
- [ ] Custom transition point selection (manual cue points)
- [ ] Export to DJ software (Rekordbox XML, Serato crates)
- [ ] Batch processing mode for large libraries
- [ ] YouTube URL input (download + analyze)
- [ ] Waveform zoom and selection in UI
- [ ] A/B preview of transitions

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

**Vishwas**

---
*Built with passion for Kannada music and code.*
