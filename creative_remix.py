#!/usr/bin/env python
# creative_remix.py
import argparse
import os
import sys
import json
import numpy as np
import librosa
from datetime import datetime
from pydub import AudioSegment
import pyrubberband as pyrb
from pydub.effects import high_pass_filter, low_pass_filter
from audio_analyzer import analyze_audio_local, analyze_vocal_presence
from remix_engine import build_remix

def run_single_mashup_mode(args):
    """
    The original functionality: creates a mashup of two songs.
    """
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
            # Fallback for when not running in an activated venv
            venv_path = os.path.abspath("./venv")
            print(f"Warning: VIRTUAL_ENV not set. Assuming venv path: {venv_path}")


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

def get_key_distance(key1_idx, mode1, key2_idx, mode2):
    """Calculates the distance between two keys on the Circle of Fifths."""
    circle_of_fifths_major = [0, 7, 2, 9, 4, 11, 6, 1, 8, 3, 10, 5]
    circle_of_fifths_minor = [9, 4, 11, 6, 1, 8, 3, 10, 5, 0, 7, 2]

    pos1 = circle_of_fifths_major[key1_idx] if mode1 == 'maj' else circle_of_fifths_minor[key1_idx]
    pos2 = circle_of_fifths_major[key2_idx] if mode2 == 'maj' else circle_of_fifths_minor[key2_idx]
    
    distance = abs(pos1 - pos2)
    return min(distance, 12 - distance)

def calculate_compatibility(track1, track2):
    """Calculates a compatibility score between two tracks."""
    score = 0
    
    key_dist = get_key_distance(track1['key'], track1['mode'], track2['key'], track2['mode'])
    key_score = max(0, 100 - key_dist * 25)
    score += key_score * 1.5

    bpm_diff = abs(track1['bpm'] - track2['bpm'])
    bpm_score = max(0, 100 - bpm_diff * 10)
    score += bpm_score

    energy_diff = track2['energy'] - track1['energy']
    if 0 < energy_diff < 0.3:
        score += 50
    elif energy_diff < -0.2:
        score -= 50

    if track1.get('has_vocals') and track2.get('has_vocals'):
        score -= 200

    return score

def curate_setlist(all_songs_features, set_length=6):
    """
    Curates and orders a setlist from a list of songs.
    """
    if len(all_songs_features) < set_length:
        set_length = len(all_songs_features)

    start_track = min(all_songs_features, key=lambda x: x['energy'])
    
    setlist = [start_track]
    remaining_tracks = [s for s in all_songs_features if s['path'] != start_track['path']]

    while len(setlist) < set_length and remaining_tracks:
        last_track = setlist[-1]
        best_next_track = None
        highest_score = -float('inf')

        for next_track in remaining_tracks:
            score = calculate_compatibility(last_track, next_track)
            if score > highest_score:
                highest_score = score
                best_next_track = next_track
        
        if best_next_track:
            setlist.append(best_next_track)
            remaining_tracks.remove(best_next_track)
        else:
            break
            
    return setlist

def find_energetic_segment(file_path, duration_percentage=0.5):
    """
    Finds the most energetic segment of a track.
    Returns start and end time in milliseconds.
    """
    print(f"  Finding most energetic {duration_percentage*100:.0f}% of {os.path.basename(file_path)}...")
    y, sr = librosa.load(file_path)
    
    frame_length = 2048
    hop_length = 512
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    
    total_duration_s = librosa.get_duration(y=y, sr=sr)
    segment_duration_s = total_duration_s * duration_percentage
    segment_len_frames = int(segment_duration_s * sr / hop_length)
    
    max_avg_rms = 0
    start_frame = 0
    for i in range(len(rms) - segment_len_frames):
        avg_rms = np.mean(rms[i:i+segment_len_frames])
        if avg_rms > max_avg_rms:
            max_avg_rms = avg_rms
            start_frame = i
            
    start_ms = (start_frame * hop_length / sr) * 1000
    end_ms = start_ms + (segment_duration_s * 1000)
    
    return start_ms, end_ms

def create_continuous_mix_from_setlist(setlist, mix_style, output_dir="remix_outputs/"):
    """
    Creates a continuous DJ mix from a curated setlist with a simplified, robust approach.
    """
    print(f"\n--- Step 3: Creating the continuous mix ({mix_style} style)... ---")
    if len(setlist) < 2:
        print("Not enough tracks in the setlist to create a mix.")
        return

    # --- Load all audio segments --- #
    audio_segments = [AudioSegment.from_mp3(s['path']) for s in setlist]

    # --- Initialize the mix --- #
    final_mix = audio_segments[0]
    print(f"Starting mix with: {setlist[0]['filename']}")

    # --- Process transitions --- #
    for i in range(len(setlist) - 1):
        current_audio = final_mix
        next_audio = audio_segments[i+1]
        current_features = setlist[i]
        next_features = setlist[i+1]

        crossfade_duration = 8000  # Default fallback crossfade

        if mix_style == 'pro':
            outro_segment = current_features['structure'][-1] if current_features['structure'] else None
            intro_segment = next_features['structure'][0] if next_features['structure'] else None
            
            if outro_segment and intro_segment:
                outro_duration = (outro_segment['end'] - outro_segment['start']) * 1000
                intro_duration = (intro_segment['end'] - intro_segment['start']) * 1000
                
                if outro_duration > 1000 and intro_duration > 1000:
                    # Use the shorter of the two segments for the transition
                    crossfade_duration = int(min(outro_duration, intro_duration))
                    print(f"Mixing in {next_features['filename']} (Pro Transition: {crossfade_duration/1000:.1f}s)")
                else:
                    print(f"Mixing in {next_features['filename']} (Fallback Beat-Match)")
            else:
                print(f"Mixing in {next_features['filename']} (Fallback Beat-Match)")
        else:
            # Logic for relaxed and energetic styles
            bpm = current_features['bpm']
            if bpm > 0:
                crossfade_duration = int((60000 / bpm) * 16) # 4 bars
            print(f"Mixing in {next_features['filename']}")

        # --- Final safety check on crossfade duration --- #
        safe_crossfade = min(crossfade_duration, len(current_audio), len(next_audio))

        # --- Append the next track with the calculated crossfade --- #
        final_mix = current_audio.append(next_audio, crossfade=safe_crossfade)

    # --- Export the final mix --- #
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"ai_dj_set_{mix_style}_{timestamp}.mp3"
    output_path = os.path.join(output_dir, output_filename)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"\nExporting final mix to {output_path}...")
    final_mix.export(output_path, format="mp3", bitrate="192k")
    print("--- DJ set creation complete! ---")

def run_dj_set_mode(args):
    """
    Creates a continuous DJ set from a directory of songs, using deep analysis.
    """
    print("--- AI Virtual DJ Set Mode ---")
    
    songs_dir = args.songs_dir
    cache_path = "analysis_cache.json"
    
    if not os.path.isdir(songs_dir):
        print(f"Error: Directory not found at {songs_dir}", file=sys.stderr)
        sys.exit(1)

    analysis_cache = {}
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            analysis_cache = json.load(f)
            print("Loaded analysis cache.")

    venv_path = os.environ.get('VIRTUAL_ENV')
    if not venv_path:
        venv_path = os.path.abspath("./venv")
        print(f"Warning: VIRTUAL_ENV not set. Assuming venv path: {venv_path}")

    print("\n--- Step 1: Deep Analysis (with Caching) ---")
    song_files = [f for f in os.listdir(songs_dir) if f.lower().endswith('.mp3')]
    
    if len(song_files) < 2:
        print("Error: Need at least 2 songs in the directory to create a mix.", file=sys.stderr)
        sys.exit(1)

    all_songs_features = []
    cache_updated = False
    for song_file in song_files:
        file_path = os.path.join(songs_dir, song_file)
        file_mod_time = os.path.getmtime(file_path)
        
        cached_data = analysis_cache.get(file_path)
        is_cached = (cached_data and 
                     cached_data.get('mod_time') == file_mod_time and
                     'structure' in cached_data and 
                     'vocal_regions' in cached_data)

        if is_cached:
            print(f"Using cached analysis for {song_file}")
            features = cached_data
        else:
            print(f"Cache miss or file updated. Analyzing {song_file}...")
            cache_updated = True
            features = analyze_audio_local(file_path)
            
            vocal_regions = analyze_vocal_presence(file_path, venv_path)
            features['has_vocals'] = len(vocal_regions) > 0
            features['vocal_regions'] = vocal_regions
            features['mod_time'] = file_mod_time
        
        features['path'] = file_path
        features['filename'] = song_file
        all_songs_features.append(features)
        analysis_cache[file_path] = features
        print("-" * 20)

    if cache_updated:
        with open(cache_path, 'w') as f:
            json.dump(analysis_cache, f, indent=4)
            print("Analysis cache updated.")

    print("\n--- Analysis Complete ---")
    for song in all_songs_features:
        print(f"{song['filename']}:\n" 
              f"  BPM: {song['bpm']:.2f}, Key: {song['key_str']}, " 
              f"  Energy: {song['energy']:.2f}, Vocals: {song.get('has_vocals')}, "
              f"  Segments: {len(song.get('structure', []))}")
    print("-" * 20)

    print("\n--- Step 2: Curating and ordering the setlist... ---")
    setlist = curate_setlist(all_songs_features)
    
    print("Curated Setlist:")
    for i, song in enumerate(setlist):
        print(f"  {i+1}. {song['filename']} (BPM: {song['bpm']:.1f}, Key: {song['key_str']}, Energy: {song['energy']:.2f})")
    print("-" * 20)

    create_continuous_mix_from_setlist(setlist, args.mix_style)

def main():
    parser = argparse.ArgumentParser(description="AI-powered music remixing and DJing tool.")
    parser.add_argument("--mode", default="single_mashup", choices=["single_mashup", "dj_set"], 
                        help="The operating mode.")
    
    parser.add_argument("--songA_path", help="Path to song A (for single_mashup mode)")
    parser.add_argument("--songB_path", help="Path to song B (for single_mashup mode)")
    parser.add_argument("--out", default="creative_remix.mp3", help="Output file path (for single_mashup mode)")

    parser.add_argument("--songs_dir", default="songs/", help="Directory of songs to use for the DJ set.")
    parser.add_argument("--mix_style", default="relaxed", choices=["relaxed", "energetic", "pro"],
                        help="The mixing style for the DJ set.")

    args = parser.parse_args()

    if args.mode == "single_mashup":
        if not args.songA_path or not args.songB_path:
            parser.error("--songA_path and --songB_path are required for single_mashup mode.")
        run_single_mashup_mode(args)
    elif args.mode == "dj_set":
        run_dj_set_mode(args)

if __name__ == "__main__":
    main()
