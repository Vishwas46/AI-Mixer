> **Purpose of this Document:** This `GEMINI.md` serves as a detailed development journal and technical deep-dive for the AI-Mixer project. It documents the project's history, architectural decisions, experiments (like the pivot from the Spotify API), and future enhancements. It is intended for developers or anyone interested in the evolution and internal workings of the project.

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

## Project Expansion: Continuous Mix and Quality Analysis

The project was expanded to include capabilities for analyzing the quality of the generated remixes and for creating continuous DJ-style mixes from multiple tracks.

### Remix Quality Analysis

A new script, `analyze_remix_quality.py`, was created to provide a quantitative measure of the quality of the mashups.

*   **Problem:** While the existing remixes were musically interesting, it was difficult to objectively assess their technical quality. The key factor in a good mashup is the precise alignment of the vocals with the beat of the instrumental track.
*   **Process:**
    1.  The `analyze_remix_quality.py` script takes a final remixed audio file as input.
    2.  It uses Demucs to perform source separation on the remix, isolating the vocals and the drums.
    3.  It then uses `librosa` to perform beat tracking on both the vocal and drum stems.
    4.  Finally, it calculates the average time difference (alignment error) between the vocal beats and the drum beats.
*   **Findings:** Analysis of the three existing remixes revealed an average alignment error of over 100ms, which is classified as "Poor." This indicates that the simple time-stretching based on a single BPM value is not sufficient to maintain tight synchronization, and the vocals are likely to sound off-beat.

### Continuous DJ Mix

To further enhance the project's capabilities, a tool for creating continuous mixes was developed.

*   **Goal:** To combine multiple individual remixes into a single, seamless audio file, simulating a DJ set.
*   **Implementation:** A new script, `create_continuous_mix.py`, was created. This script was developed separately from `creative_remix.py` to maintain a clear separation of concerns, as its function (combining existing files) is distinct from the core remixing process.
*   **Functionality:** The script takes a list of audio files as input, creates a new directory in `remix_outputs/` named with the current date, and then uses `pydub` to join the tracks together with a smooth 5-second crossfade between each one. The final output is saved as `continuous_dj_mix.mp3`.

## Building and Running

### 1. Setup and Installation

The project uses a Python virtual environment (`venv`) to manage its dependencies. Before running the application, you should create and activate the virtual environment.

1.  **Create the virtual environment (if it doesn't exist):**
    ```bash
    python3 -m venv venv
    ```

2.  **Activate the virtual environment:**
    *   **On macOS and Linux:**
        ```bash
        source venv/bin/activate
        ```
    *   **On Windows:**
        ```bash
        .\venv\Scripts\activate
        ```

3.  **Install dependencies:**
    Once the virtual environment is activated, install the required packages from `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```

### 2. Running the Script

The `creative_remix.py` script can be run in two modes.

**A) Single Mashup Mode**

This mode creates a standard mashup of two songs.

```bash
python creative_remix.py --mode single_mashup --songA_path <path_to_song_A> --songB_path <path_to_song_B>
```

**B) AI DJ Set Mode**

This mode analyzes all songs in a directory, caches the analysis, curates a musically compatible setlist, and generates a final, continuous DJ mix. It supports three distinct styles using the `--mix-style` flag.

```bash
# Generate a standard, full-length DJ mix
python creative_remix.py --mode dj_set --mix_style relaxed

# Generate a fast-paced "highlight reel" mix
python creative_remix.py --mode dj_set --mix_style energetic

# Generate a professional-style mix with phrase matching
python creative_remix.py --mode dj_set --mix_style pro
```

*   **Relaxed Style (Default):** This mode uses the full length of each song, creating a traditional DJ set. All transitions are beat-aware and use EQ filtering to ensure a clean, professional sound.
*   **Energetic Style:** This mode creates a high-intensity "megamix" by finding and mixing the most energetic 50% of each song. All transitions are beat-synced and use EQ filtering for maximum clarity and punch.
*   **Pro Style:** This is the most advanced mode. It uses full-length tracks and performs a deep structural analysis to find the natural intro and outro of each song, attempting to perform a seamless "phrase match." All transitions use the same professional EQ filtering.

If `--songs_dir` is not provided, it defaults to the `songs/` directory. The final mix is saved with a timestamp and the mix style in the `remix_outputs/` folder.

### Example AI-Generated DJ Set

To illustrate the process, the AI was tasked with creating a set from a directory of 11 electronic music tracks.

1.  **Analysis:** The script first analyzed all 11 tracks for energy, BPM, and musical key, using the cached results to save time.
2.  **Curation:** It then curated a 6-track setlist. The process started by selecting the track with the lowest energy (`Darude - Sandstorm`) and then iteratively adding the most musically compatible song until the set was complete.
3.  **Mixing:** The script generated a continuous MP3 file, creating beat-aware transitions between each track. For example, the 14.1-second outro of `Sandstorm` was crossfaded with the intro of `Age of Love`.

**The final curated setlist was:**

1.  `Darude - Sandstorm` (136.0 BPM, E:min)
2.  `Age Of Love - The Age Of Love (Remix)` (136.0 BPM, F#:min)
3.  `Faithless - Insomnia` (129.2 BPM, B:min)
4.  `Swedish House Mafia - Don't You Worry Child` (129.2 BPM, D:maj)
5.  `Avicii - Levels` (123.0 BPM, E:maj)
6.  `Daft Punk - One More Time` (123.0 BPM, D:maj)

This entire process, thanks to the analysis cache, took only a few seconds to execute.

## Development Conventions

*   **Dependency Management:** All Python dependencies are managed through the `requirements.txt` file.
*   **Modular Structure:** The code is organized into functions with clear responsibilities.
*   **Command-Line Interface:** The main script uses the `argparse` module.
*   **Focus on Local Analysis:** The project is intentionally designed to be self-contained.

## Future Enhancements

*   **Dynamic Crowd Engagement Effects:** Implement advanced DJ techniques to create more dynamic and engaging mixes.
    *   **Automatic "Singalong" Moments:** Detect popular vocal phrases and automatically create "acapella out" moments by briefly cutting the instrumental to let the "crowd" (the listener) sing along.
    *   **Dynamic Build-ups and Drops:** Implement more sophisticated build-ups and drops by manipulating volume, using filter sweeps, and creating rhythmic stutters to mimic how a live DJ creates tension and release to make the crowd jump.

## Workflow Visualization

To help understand the project's architecture and execution flow, you can generate a visual diagram of the function calls. This project uses Mermaid to define the diagram as code.

### Prerequisites

- **Node.js and npm:** The diagram generation tool is a Node.js package. You can check if you have them installed by running `node -v` and `npm -v`.

### Installation

Install the Mermaid CLI (Command Line Interface) globally on your system:

```bash
npm install -g @mermaid-js/mermaid-cli
```

*Note: This is a development dependency for generating documentation and is not required to run the core AI-Mixer application.*

### Generating the Diagram

A Mermaid definition file named `flowchart.mmd` is included in the repository. To generate a scalable vector graphic (SVG) image from this file, run the following command:

```bash
mmdc -i flowchart.mmd -o flowchart.svg
```

You can then open the generated `flowchart.svg` in any modern web browser to view the diagram. Because it's an SVG, you can zoom in to see all details with perfect clarity.

## Major Feature Upgrade: Intelligent DJing

Based on detailed user feedback during an interactive session, the AI DJ underwent a significant upgrade to elevate its mixing capabilities from a simple automated tool to a more professional and artistic engine.

### 1. From Simple Overlaps to EQ-Clean Transitions

*   **Problem:** The initial "pro" mix style, while using phrase matching for timing, only performed a simple volume crossfade. This resulted in a muddy, "overlapped" sound, as the bass and other frequencies of the two tracks would clash.
*   **Diagnostics:** A new analysis script, `visualize_transition.py`, was created to generate spectrograms of the transitions. This provided clear visual proof of the frequency clashes.
*   **Solution:** The mixing engine was refactored to use a universal EQ-based transition for all mix styles. This new logic applies a high-pass filter to the outgoing track, cutting its bass to make room for the incoming track's bassline, mimicking a standard professional DJ technique.

### 2. From Energy-Based to "Intelligent" Clipping

*   **Problem:** The initial `energetic` style was designed to mix the "most energetic 50%" of each song. This was too simplistic, often just grabbing the main chorus or drop, leading to repetitive mixes that lacked flow.
*   **Solution:** A new "Intelligent Clipping" algorithm (`find_dj_clip`) was implemented. This new system goes far beyond simple loudness:
    *   It analyzes the song's structure to find musically distinct sections.
    *   It scores each section based on **rhythmic density** and **energy stability** to find the most "mixable" and loopable parts.
    *   It operates within a dynamic length constraint (20-50% of the song) to ensure clips are substantial.

### 3. Upgrading the Core Analysis Engine

*   **Problem:** During the implementation of Intelligent Clipping, it was discovered that the underlying structural analysis was too basic. It only split songs by silence, which was ineffective for electronic music and provided poor data for the clipping algorithm.
*   **Solution:** The core analysis engine in `audio_analyzer.py` was completely upgraded. It now uses a sophisticated novelty detection algorithm (`librosa.segment.agglomerative`) to find segment boundaries based on changes in the music's timbre and harmony. This provides the rich, high-quality structural data that the Intelligent Clipping feature needs to work effectively.

This iterative cycle of feedback, analysis, and implementation has resulted in a significantly more capable and professional-sounding AI DJ.