> **Purpose of this Document:** This `README.md` is the primary user-facing documentation for the AI-Mixer project. It provides a general overview, installation instructions, and clear usage examples for running the tool. It is intended for anyone who wants to use or quickly understand the project.

# AI-Mixer

A Python script that uses AI to create a remix of two songs. It separates the vocals from one song and the instrumental from another, then adjusts the pitch and tempo to create a harmonious mashup.

## Dependencies

This project uses a virtual environment (`venv`) to manage dependencies. The main libraries used are:

*   `demucs`: For audio source separation.
*   `librosa`: For audio analysis.
*   `pydub`: For audio manipulation and effects.
*   `numpy`: For numerical operations.
*   `soundfile`: For reading and writing audio files.

All dependencies are listed in the `requirements.txt` file and can be installed by running:
```bash
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/pip install -r requirements.txt
```

## Usage

The main script, `creative_remix.py`, operates in two modes, specified with the `--mode` flag.

### 1. Single Mashup Mode (`--mode single_mashup`)

This mode creates a classic mashup from two songs, taking the vocals from one and the instrumental from the other.

```bash
# Basic usage (vocals from songA, instrumental from songB)
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/python creative_remix.py --mode single_mashup --songA_path songA.mp3 --songB_path songB.mp3

# Specify a different output file
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/python creative_remix.py --mode single_mashup --songA_path songA.mp3 --songB_path songB.mp3 --out my_remix.mp3
```

### 2. AI DJ Set Mode (`--mode dj_set`)

This is the most powerful feature. The script analyzes an entire directory of songs and automatically generates a continuous, multi-song DJ mix. It can create two different styles of mix using the `--mix_style` flag.

**Workflow:**
1.  **Analyze:** The script performs a deep analysis of all songs in a directory to find their BPM, key, energy, and vocal presence. This analysis is cached in `analysis_cache.json` to make subsequent runs much faster.
2.  **Curate:** It then acts as an AI DJ, selecting the lowest-energy track to start and building a musically compatible setlist based on harmonic mixing, tempo, and energy flow.
3.  **Mix:** Finally, it generates a single MP3 file of the complete set, with each track seamlessly crossfaded into the next.

**How to Run:**
```bash
# Generate a standard, full-length DJ mix (relaxed style)
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/python creative_remix.py --mode dj_set --mix_style relaxed

# Generate a fast-paced "highlight reel" mix (energetic style)
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/python creative_remix.py --mode dj_set --mix_style energetic

# Use a different directory of songs
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/python creative_remix.py --mode dj_set --songs_dir /path/to/my/music
```

**Mix Styles:**
*   `relaxed` (Default): This mode uses the full length of each song to create a traditional DJ set with a simple, beat-aware volume crossfade.
*   `energetic` (Pro Mix): This mode creates a high-intensity "megamix" using professional DJ techniques. It automatically finds the most energetic 50% of each track, then seamlessly mixes these clips by:
    *   **Tempo Synchronizing:** Perfectly matching the BPM of the incoming track to the outgoing track.
    *   **EQ Mixing:** Performing a "bass swap" to ensure a clean, powerful transition without clashing frequencies.

The final mix is saved with a timestamp in the `remix_outputs/` directory.

---
*Note: The `create_continuous_mix.py` script is still available for manually stitching together audio files, but the AI DJ mode provides a more intelligent, automated solution.*

## Core Technology: Local-First Audio Analysis

This project relies on local audio analysis and does not require any external APIs.

*   **Audio Analysis:** The `audio_analyzer.py` script uses the `librosa` library to analyze local audio files and extract their BPM and musical key. This is the core of the project's ability to create harmonically compatible mashups.
*   **Source Separation:** The project uses `demucs` to separate the vocals and instrumentals from the source tracks.

### Design Choice: Why Local Analysis?

The project was initially designed to use the Spotify API to fetch song metadata. However, due to persistent and unresolvable "403 Forbidden" errors with the API, a decision was made to pivot to a more robust, local-first approach.

**Advantages of Local Analysis:**

*   **Reliability:** The tool is not dependent on an external service that may have authentication issues, rate limits, or downtime.
*   **Privacy:** No data about your local music library is sent to a third party.
*   **Flexibility:** The tool can be used with any audio file, not just those available on Spotify.

This change makes the AI-Mixer a more resilient and self-contained application.

## File Descriptions

*   `creative_remix.py`: The main Python script that orchestrates the remixing process.
*   `audio_analyzer.py`: A utility script that handles local audio analysis (BPM, key).
*   `remix_engine.py`: The core engine that handles the actual remixing, including source separation, alignment, and mixing.
*   `visualize_alignment.py`: A utility script to generate a plot that visually compares the beat alignment of two different remix versions.
*   `plot_alignment_error.py`: Another utility script that generates a plot to compare the beat alignment *error* of two different remix versions.
*   `requirements.txt`: A list of all the Python dependencies for the project.

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

## Inspiration

This project is inspired by the techniques of professional DJs. Here are some quotes from David Guetta on the art of DJing (from a WIRED YouTube video):

> "Music relies on contrast. Quiet moments make the loud ones hit harder, and mono makes the stereo feel wider. Dropping the kick creates tension, and bringing it back releases energy. Louder tricks the ear into feeling better. This is the foundation of music really.. Switch tracks till the crowd reacts. If tech house hits, dig into your tech house playlist. Use EQ to clean, not filter. For build-ups, combine high/low pass with delay or echo for tension and release. You need to be able to try different things until you win. It's going to be an incredible feeling of energy.... Beat matching is simple now with modern technology. I mix by lowering the bass to avoid clashing and keep the beat steady so people can dance. The next step is mixing in key-like C minor to G, which sounds harmonious. If I hear a DJ do that, I'm like, okay, this guy is good..."