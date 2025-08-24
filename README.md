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

The script can be used in two main ways: for creating a single mashup or for acting as an "AI DJ Assistant" to create a series of compatible mashups from a larger collection of songs.

### Single Mashup

The script is run from the command line. You need to provide the paths to the two local audio files you want to remix.

```bash
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/python creative_remix.py song1.mp3 song2.mp3
```

### AI DJ Assistant Workflow

For a more advanced use case, the project can analyze a directory of songs and help you create a series of harmonically and rhythmically compatible mashups, similar to how a DJ plans a set.

1.  **Place Songs:** Add all your `.mp3` files to the `songs/` directory.
2.  **Analyze and Plan:** The AI assistant will analyze each song to determine its BPM and musical key.
3.  **Generate Mashups:** Based on this analysis, the assistant will propose a series of high-quality mashup pairs.
4.  **Output:** The generated mashups and a `README.md` file documenting the process will be saved in the `remix_outputs/` directory.

### Two-Way Remixing

By default, the script takes the vocals from song A and the instrumental from song B. You can reverse this by using the `--vocals-from` argument:

```bash
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/python creative_remix.py songA.mp3 songB.mp3 --vocals-from B
```

### Remix Styles

The script supports different remixing styles using the `--remix-style` argument:

*   `full` (default): Creates a single remix with vocals from one song and instrumental from the other.
*   `verse-chorus`: Creates a dynamic remix where the vocals and instrumental switch between the two songs at one-minute intervals.

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

## Inspiration

This project is inspired by the techniques of professional DJs. Here are some quotes from David Guetta on the art of DJing (from a WIRED YouTube video):

> "Music relies on contrast. Quiet moments make the loud ones hit harder, and mono makes the stereo feel wider. Dropping the kick creates tension, and bringing it back releases energy. Louder tricks the ear into feeling better. This is the foundation of music really.. Switch tracks till the crowd reacts. If tech house hits, dig into your tech house playlist. Use EQ to clean, not filter. For build-ups, combine high/low pass with delay or echo for tension and release. You need to be able to try different things until you win. It's going to be an incredible feeling of energy.... Beat matching is simple now with modern technology. I mix by lowering the bass to avoid clashing and keep the beat steady so people can dance. The next step is mixing in key-like C minor to G, which sounds harmonious. If I hear a DJ do that, I'm like, okay, this guy is good..."