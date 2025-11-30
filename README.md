# AI-Mixer

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)

**AI-Mixer** is a powerful, local-first command-line tool that intelligently remixes and mashes up songs using artificial intelligence. It leverages advanced audio processing libraries to separate vocals and instrumentals, analyze musical structure, and create seamless, beat-matched DJ mixes automatically.

## 🚀 Features

*   **Single Mashup Mode:** Create a classic mashup by blending the vocals of one track with the instrumental of another.
*   **AI DJ Set Mode:** Automatically generate a continuous, multi-song DJ set from a directory of MP3s.
    *   **Deep Analysis:** Analyzes BPM, key, energy, and structural segments (intro, verse, chorus) using local processing.
    *   **Smart Curation:** Curates a setlist based on harmonic mixing rules and energy flow.
    *   **Mix Styles:** Choose from `relaxed` (full length), `energetic` (highlight reel), or `pro` (phrase-matched) mixing styles.
*   **Local-First Privacy:** No external APIs required. All analysis happens locally on your machine, ensuring privacy and reliability.
*   **High-Quality Separation:** Uses **Demucs** for state-of-the-art source separation.
*   **Intelligent Clipping:** Automatically identifies the most "mixable" and loopable sections of tracks for high-energy mixes.

## 🛠️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Vishwas46/AI-Mixer.git
    cd AI-Mixer
    ```

2.  **Set up a Virtual Environment:**
    It is highly recommended to use a virtual environment to manage dependencies.
    ```bash
    # Create venv
    python3 -m venv venv

    # Activate venv
    # On macOS/Linux:
    source venv/bin/activate
    # On Windows:
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

    *Note: You will also need `ffmpeg` installed on your system for audio processing.*

## 🎧 Usage

The main entry point is `creative_remix.py`.

### 1. Create a Single Mashup
Mix the vocals of Song A with the instrumental of Song B.

```bash
python creative_remix.py --mode single_mashup --songA_path "path/to/vocals_song.mp3" --songB_path "path/to/instrumental_song.mp3" --out "my_mashup.mp3"
```

### 2. Generate an AI DJ Set
Create a seamless mix from a folder of songs.

```bash
# Standard mix (Relaxed style)
python creative_remix.py --mode dj_set --songs_dir "songs/" --mix_style relaxed

# High-energy megamix (Energetic style)
python creative_remix.py --mode dj_set --songs_dir "songs/" --mix_style energetic

# Professional phrase-matched mix (Pro style)
python creative_remix.py --mode dj_set --songs_dir "songs/" --mix_style pro
```

The output will be saved in the `remix_outputs/` directory.

## 🧠 How It Works

AI-Mixer combines several advanced audio technologies:

1.  **Audio Analysis (`librosa`):** Extracts BPM, Key, and Energy. It uses spectral novelty detection to identify musical structure (intros, verses, drops).
2.  **Source Separation (`demucs`):** Splits audio files into four stems (vocals, drums, bass, other) to allow for independent manipulation.
3.  **Time & Pitch Manipulation (`rubberband`):** High-quality time-stretching and pitch-shifting to match tempos and keys without artifacts.
4.  **Mixing Engine:** Intelligently aligns beats and applies EQ-based crossfades to prevent frequency clashes during transitions.

## 🗺️ Roadmap

*   **Dynamic Crowd Engagement:** Implement "acapella out" moments for singalongs.
*   **Advanced FX:** Add filter sweeps, stutters, and build-up effects during transitions.
*   **Real-time Mode:** Explore possibilities for real-time mixing input.

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ✍️ Author

**Vishwas**

---
*Built with passion for music and code.*
