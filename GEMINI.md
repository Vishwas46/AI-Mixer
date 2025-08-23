# GEMINI.md: AI-Mixer

## Project Overview

This project, "AI-Mixer," is a Python-based command-line tool that intelligently remixes two songs. It leverages AI and signal processing libraries to perform source separation, audio analysis, and creative mixing. The core functionality involves separating the vocals from one track and the instrumental from another, then aligning their tempo and pitch to create a harmonious mashup.

The project uses `demucs` for high-quality audio source separation, `librosa` and `pyrubberband` for robust audio analysis and manipulation (BPM detection, pitch shifting, time stretching), and `pydub` for combining and applying effects to the audio tracks. A key feature is the use of the Spotify API to retrieve accurate BPM and key information for the input songs, which is crucial for a high-quality remix.

The main script, `creative_remix.py`, orchestrates the entire remixing process. Additionally, there are utility scripts (`visualize_alignment.py` and `plot_alignment_error.py`) for analyzing and visualizing the beat alignment of the generated remixes.

## Building and Running

### 1. Setup and Installation

The project uses a Python virtual environment (`venv`) to manage its dependencies.

**Installation:**

To install the required packages, run the following command from the project's root directory:

```bash
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/pip install -r requirements.txt
```

**Spotify API Configuration:**

The project requires access to the Spotify API. You need to create a `.env` file in the root of the project with your Spotify API credentials:

```
# .env
SPOTIFY_CLIENT_ID="your_spotify_client_id"
SPOTIFY_CLIENT_SECRET="your_spotify_client_secret"
```

### 2. Running the Remix Script

The main script for creating remixes is `creative_remix.py`. It takes the paths to two audio files and their corresponding names (for Spotify search) as input.

**Basic Usage:**

```bash
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/python creative_remix.py song1.mp3 song2.mp3 --songA-name "Artist - Song Title" --songB-name "Another Artist - Another Song Title"
```

**Customization:**

*   **Vocals Source:** You can specify which song to take the vocals from using the `--vocals-from` argument (e.g., `--vocals-from B`).
*   **Remix Style:** The `--remix-style` argument allows you to choose between a `full` remix and a `verse-chorus` style.

### 3. Running the Analysis Scripts

The project includes two utility scripts for analyzing the beat alignment of the remixes.

*   **`visualize_alignment.py`:** Generates a plot to visually compare the beat alignment of two different remix versions.
*   **`plot_alignment_error.py`:** Creates a plot to compare the beat alignment error of two different remix versions quantitatively.

**Usage:**

```bash
# Example for visualize_alignment.py
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/python visualize_alignment.py /path/to/stems_dir_1 /path/to/stems_dir_2
```

## Development Conventions

*   **Dependency Management:** All Python dependencies are managed through the `requirements.txt` file.
*   **Environment Variables:** The project uses a `.env` file to manage sensitive information like API keys, loaded via the `python-dotenv` library.
*   **Modular Structure:** The code is organized into functions with clear responsibilities, such as Spotify API interaction, audio processing, and file handling.
*   **Command-Line Interface:** The main script uses the `argparse` module to provide a user-friendly command-line interface.
*   **Known Issues:** There is a known issue with the Spotify API integration, resulting in a "403 Forbidden" error. This is documented in the `README.md` and needs to be resolved for the full functionality of the script.

    **Update:** Due to persistent issues with the Spotify API, the project has been updated to use a manual approach for audio analysis. The `spotify_client.py` script now includes a function that uses the `librosa` library to analyze local audio files and extract their BPM and key. This ensures that the core remixing functionality is not blocked by the API issue.
