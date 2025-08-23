#!/usr/bin/env python
# creative_remix.py
import argparse
import os
import sys
from spotify_client import analyze_audio_local
from remix_engine import build_remix

def main():
    parser = argparse.ArgumentParser(description="Builds a creative remix of two songs.")
    parser.add_argument("songA_path", help="Path to song A audio file")
    parser.add_argument("songB_path", help="Path to song B audio file")
    parser.add_argument("--out", default="creative_remix.mp3", help="Output file path")
    args = parser.parse_args()

    try:
        # 1. Analyze local audio files
        print("Analyzing audio files locally...")
        features_A = analyze_audio_local(args.songA_path)
        features_B = analyze_audio_local(args.songB_path)
        print(f"Song A: BPM {features_A['bpm']:.1f}, Key {features_A['key_str']}")
        print(f"Song B: BPM {features_B['bpm']:.1f}, Key {features_B['key_str']}")
        
        # 2. Get the path to the virtual environment for Demucs
        venv_path = os.environ.get('VIRTUAL_ENV')
        if not venv_path:
            raise RuntimeError("Virtual environment not activated. Please activate it before running.")

        # 3. Build the remix
        build_remix(
            songA_path=args.songA_path,
            songB_path=args.songB_path,
            out_path=args.out,
            venv_path=venv_path,
            voc_features=features_A,  # Using Vocals from A, Instrumental from B
            inst_features=features_B
        )

    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
