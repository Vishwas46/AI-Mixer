# AI-Mixer

A Python script that uses AI to create a remix of two songs. It separates the vocals from one song and the instrumental from another, then adjusts the pitch and tempo to create a harmonious mashup.

## Dependencies

This project uses a virtual environment (`venv`) to manage dependencies. The main libraries used are:

*   `demucs`: For audio source separation.
*   `librosa`: For audio analysis.
*   `pydub`: For audio manipulation and effects.
*   `numpy`: For numerical operations.
*   `soundfile`: For reading and writing audio files.
*   `spotipy`: For interacting with the Spotify API.
*   `python-dotenv`: For managing environment variables.

All dependencies are listed in the `requirements.txt` file and can be installed by running:
```bash
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/pip install -r requirements.txt
```

## Usage

The script is run from the command line. You need to provide the paths to the two local audio files you want to remix, as well as the names of the songs for the Spotify API to fetch the metadata.

```bash
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/python creative_remix.py song1.mp3 song2.mp3 --songA-name "Artist - Song Title" --songB-name "Another Artist - Another Song Title"
```

### Two-Way Remixing

By default, the script takes the vocals from song A and the instrumental from song B. You can reverse this by using the `--vocals-from` argument:

```bash
/Users/vishwas/Documents/workspace/AI-Mixer/venv/bin/python creative_remix.py songA.mp3 songB.mp3 --songA-name "Artist - Song Title" --songB-name "Another Artist - Another Song Title" --vocals-from B
```

### Remix Styles

The script supports different remixing styles using the `--remix-style` argument:

*   `full` (default): Creates a single remix with vocals from one song and instrumental from the other.
*   `verse-chorus`: Creates a dynamic remix where the vocals and instrumental switch between the two songs at one-minute intervals.

## Spotify API Integration

This project has been updated to use the Spotify API to fetch accurate BPM and key information for the songs being remixed. This should result in higher-quality remixes.

### Known Issues

There is currently a persistent "403 Forbidden" error when trying to connect to the Spotify API. This issue persists even after extensive troubleshooting, including:

*   Verifying the code and authentication flow.
*   Regenerating API credentials multiple times.
*   Recreating the application on the Spotify Developer Dashboard.
*   Clearing the token cache.
*   Adding the user to the application's "Users and Access" list.

This suggests the issue may be with the Spotify account or an issue on Spotify's end.

**Workaround:** Due to this, the project has been updated to use a manual approach for audio analysis. For more details, see the `GEMINI.md` file.

## File Descriptions

*   `creative_remix.py`: The main Python script that creates the remix. It handles source separation, audio analysis (using the Spotify API), alignment, and mixing.
*   `visualize_alignment.py`: A utility script to generate a plot that visually compares the beat alignment of two different remix versions.
*   `plot_alignment_error.py`: Another utility script that generates a plot to compare the beat alignment *error* of two different remix versions, providing a more quantitative analysis.
*   `song1.mp3` and `song2.mp3`: The two input audio files used for the remix.
*   `requirements.txt`: A list of all the Python dependencies for the project.
*   `.env`: A file to store the Spotify API credentials (`SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`).

## Inspiration

This project is inspired by the techniques of professional DJs. Here are some quotes from David Guetta on the art of DJing (from a WIRED YouTube video):

> "Music relies on contrast. Quiet moments make the loud ones hit harder, and mono makes the stereo feel wider. Dropping the kick creates tension, and bringing it back releases energy. Louder tricks the ear into feeling better. This is the foundation of music really.. Switch tracks till the crowd reacts. If tech house hits, dig into your tech house playlist. Use EQ to clean, not filter. For build-ups, combine high/low pass with delay or echo for tension and release. You need to be able to try different things until you win. It's going to be an incredible feeling of energy.... Beat matching is simple now with modern technology. I mix by lowering the bass to avoid clashing and keep the beat steady so people can dance. The next step is mixing in key-like C minor to G, which sounds harmonious. If I hear a DJ do that, I'm like, okay, this guy is good..."
