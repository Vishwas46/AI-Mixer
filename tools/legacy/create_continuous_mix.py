# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------

import os
import sys
from pydub import AudioSegment
from datetime import datetime

def create_continuous_mix(input_files, output_dir, crossfade_duration_ms=5000):
    """
    Creates a continuous mix from a list of audio files with crossfades.
    """
    if not input_files:
        print("Error: No input files provided.")
        return

    print("Loading audio files...")
    segments = [AudioSegment.from_mp3(f) for f in input_files]

    # Start with the first track
    final_mix = segments[0]

    # Sequentially crossfade the remaining tracks
    for i in range(1, len(segments)):
        print(f"Crossfading track {i+1}...")
        final_mix = final_mix.append(segments[i], crossfade=crossfade_duration_ms)

    # Create the dated output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_path = os.path.join(output_dir, "continuous_dj_mix.mp3")
    
    print(f"Exporting final mix to {output_path}...")
    final_mix.export(output_path, format="mp3", bitrate="320k")
    print("Continuous mix complete!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_continuous_mix.py <file1.mp3> <file2.mp3> ...")
        sys.exit(1)

    input_files = sys.argv[1:]
    
    # Create a new directory in remix_outputs with the current date
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_directory = os.path.join("remix_outputs", date_str)
    
    create_continuous_mix(input_files, output_directory)