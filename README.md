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

## Features

### Core Mixing Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Quick Mashup** | Blend vocals of Song A with instrumental of Song B | Classic mashup creation |
| **DJ Set** | All songs mixed into one continuous track | Party mixes, podcasts |
| **Kannada/Sandalwood** | Indian film music optimized with Tala detection | Bollywood/Sandalwood mashups |

### Advanced Analysis

- **Beat Grid Detection** - Precise BPM with downbeat alignment
- **Tala Detection** - Identifies Indian rhythmic cycles (Adi Tala, Rupaka, Mishra Chapu, etc.)
- **Scale/Ragam Analysis** - Detects Kannada musical scales (Mohanam, Kalyani, etc.)
- **Vocal-Free Zone Detection** - Finds safe mix points without vocal clashes
- **DJ Cue Points** - Auto-generates MIX IN, MIX OUT, DROP, LOOP points
- **Phrase Boundaries** - Identifies 4/8/16/32 bar musical phrases
- **Emotional Intensity Curve** - Maps energy flow throughout the song

### Mixing Styles

**DJ Set Styles:**
- `relaxed` - Full-length tracks with smooth 8-bar transitions
- `energetic` - Highlight reels with punchy drops
- `pro` - Professional phrase-matched mixing

**Kannada/Sandalwood Styles:**
- `energetic` - High-energy dance mashup, builds progressively
- `smooth` - Melodic flowing transitions, consistent energy
- `showcase` - Features the best hooks from each song

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
4. **Click "Analyze & Create"** - done!

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
| `/api/analyze/kannada` | POST | Deep Kannada analysis (async) |
| `/api/mashup/single` | POST | Create 2-song mashup (async) |
| `/api/mashup/djset` | POST | Create DJ set (async) |
| `/api/mashup/sandalwood` | POST | Create Kannada mashup with planning (async) |
| `/api/tasks/{id}` | GET | Check task status |
| `/api/tasks/{id}/stream` | GET | SSE stream for live progress |
| `/api/outputs` | GET | List generated mashups |
| `/api/stream/{filename}` | GET | Stream audio with seeking support |

## Project Structure

```
AI-Mixer/
├── creative_remix.py        # Main CLI entry point
├── audio_analyzer.py        # Core audio analysis (BPM, key, energy)
├── remix_engine.py          # Mixing engine with Demucs separation
├── kannada_mashup_analyzer.py  # Indian music analyzer (Tala, Ragam, etc.)
├── web_server.py            # FastAPI backend (13 endpoints)
├── ui/                      # React + Vite frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Home.jsx     # Main mashup creation page
│   │   │   ├── Library.jsx  # Song management
│   │   │   └── Results.jsx  # Output player
│   │   └── components/
│   │       ├── AudioPlayer.jsx      # WaveSurfer-based player
│   │       ├── CompatibilityGraph.jsx  # Visual song connections
│   │       └── Navbar.jsx
├── songs/                   # Input audio files
└── remix_outputs/           # Generated mashups
```

## How It Works

### Audio Analysis Pipeline

1. **Load Audio** - librosa loads and resamples to 22050 Hz
2. **Beat Detection** - Onset strength analysis + beat tracking
3. **Vocal Analysis** - HPSS separation to detect vocal regions
4. **Beat Grid** - Precise tempo with downbeat detection
5. **Tala Detection** - 4-method cross-validated Indian rhythm detection
6. **Scale Analysis** - Chroma feature matching against Kannada scales
7. **Hook Detection** - Energy dip/surge patterns for drops and hooks
8. **Section Classification** - Intro/Outro/Pallavi/Charanam/Interlude
9. **Phrase Boundaries** - 4/8/16/32 bar structure detection
10. **DJ Cue Points** - Auto-generated MIX IN, MIX OUT, LOOP points
11. **Compatibility Scoring** - Multi-factor matching (BPM, key, energy, Tala)

### Tala Detection (V2)

Uses 4-method weighted scoring:
- **Onset Accent Analysis** (weight: 1.0) - Rhythmic pattern from onset strength
- **Percussion Isolation** (weight: 1.5) - HPSS-separated drum patterns
- **Beat Grid Cross-Validation** (weight: 2.0) - Validates against detected beats
- **Interval Pattern Analysis** (weight: 1.0) - Inter-beat timing patterns

Detects: Adi Tala (8 beats), Rupaka (6), Mishra Chapu (7), Khanda Chapu (5), Tisra (3), Eka (4), Sankeerna (9)

### Transition Logic

| Compatibility | Transition Type | Duration |
|---------------|-----------------|----------|
| > 70% | EQ Swap | 8 bars |
| > 50% | Filter Sweep | 4 bars |
| < 50% | Drop Swap | Instant |

## Tech Stack

**Backend:**
- Python 3.8+
- FastAPI (REST API)
- librosa (audio analysis)
- Demucs (source separation)
- rubberband (time-stretch/pitch-shift)

**Frontend:**
- React 19 + Vite
- WaveSurfer.js (waveform visualization)
- Framer Motion (animations)
- Lucide React (icons)

## Roadmap

- [ ] Real-time preview before creating mashup
- [ ] Custom transition point selection
- [ ] Export to DJ software (Rekordbox, Serato)
- [ ] Batch processing mode
- [ ] Mobile-responsive UI improvements

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

**Vishwas**

---
*Built with passion for Kannada music and code.*
