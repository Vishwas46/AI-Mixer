# GEMINI.md: AI-Mixer

## Project Overview

This project, "AI-Mixer," is a Python-based command-line tool that intelligently remixes two songs. It leverages AI and signal processing libraries to perform source separation, audio analysis, and creative mixing. The core functionality involves separating the vocals from one track and the instrumental from another, then aligning their tempo and pitch to create a harmonious mashup.

The project uses `demucs` for high-quality audio source separation, `librosa` and `pyrubberband` for robust audio analysis and manipulation (BPM detection, pitch shifting, time stretching), and `pydub` for combining and applying effects to the audio tracks. The project's intelligence comes from its ability to analyze audio locally, without relying on external APIs.

The main script, `creative_remix.py`, orchestrates the entire remixing process. Additionally, there are utility scripts (`visualize_alignment.py` and `plot_alignment_error.py`) for analyzing and visualizing the beat alignment of the generated remixes.

## Project Evolution: From Spotify API to Local-First

The project underwent a significant architectural change, moving from a reliance on the Spotify API to a self-contained, local-first analysis model.

*   **Initial Goal:** The original plan was to use the Spotify API to fetch accurate BPM and key information for songs, assuming this would be the most reliable source of metadata.
*   **The Problem:** A persistent and unresolvable "403 Forbidden" error blocked all attempts to connect to the Spotify API. Extensive troubleshooting (verifying credentials, regenerating keys, checking application permissions) failed to resolve the issue, suggesting a problem outside the scope of the code itself.
*   **The Pivot:** To ensure the project's core functionality was not blocked by an unreliable external dependency, the decision was made to pivot to a local analysis solution. The `spotify_client.py` was refactored into `audio_analyzer.py`, and the `librosa` library was used to implement robust local BPM and key detection.
*   **Outcome:** This refactoring made the project more resilient, private, and flexible, as it no longer relies on an internet connection or a third-party service.

## AI DJ Assistant Session

This local-first model was successfully put to the test in a guided "AI DJ Assistant" session.

*   **Goal:** Analyze a collection of 10 dance tracks and produce a series of high-quality, danceable mashups.
*   **Process:**
    1.  **Analysis:** All 10 tracks were analyzed using the local `analyze_audio_local` function.
    2.  **Curation:** Based on the analysis, three harmonically and rhythmically compatible pairs were identified.
    3.  **Generation:** The `creative_remix.py` script was used to generate three unique mashups.
*   **Outcome:** The session was successful, proving the viability and effectiveness of the local-first approach.

## Building and Running

### 1. Setup and Installation

The project uses a Python virtual environment (`venv`) to manage its dependencies.

**Installation:**

```bash
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/pip install -r requirements.txt
```

### 2. Running the Remix Script

**Basic Usage:**

```bash
/Users/vishwas/Documents/workspace/AI--Mixer/venv/bin/python creative_remix.py song1.mp3 song2.mp3
```

## Development Conventions

*   **Dependency Management:** All Python dependencies are managed through the `requirements.txt` file.
*   **Modular Structure:** The code is organized into functions with clear responsibilities.
*   **Command-Line Interface:** The main script uses the `argparse` module.
*   **Focus on Local Analysis:** The project is intentionally designed to be self-contained.
