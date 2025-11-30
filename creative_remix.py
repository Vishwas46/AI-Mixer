#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# creative_remix.py
import argparse
import os
import sys
import json
import numpy as np
import librosa
import time
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

def find_dj_clip(song_path, structure, bpm, song_duration):
    """
    Finds the best segment of a track for DJ mixing based on rhythmic density,
    energy stability, and musical phrasing (loopability).
    """
    try:
        y, sr = librosa.load(song_path)
    except Exception as e:
        print(f"  Could not load {os.path.basename(song_path)} for clip analysis: {e}")
        return 0, 30000 # fallback to first 30s

    best_segment = None
    max_score = -1

    print(f"  Analyzing {len(structure)} segments for 'mixability' (20-50% length)...")

    # Define the desired length constraints based on the total song duration
    min_len_s = song_duration * 0.20
    max_len_s = song_duration * 0.50

    for segment in structure:
        start_s = segment['start']
        end_s = segment['end']
        duration = end_s - start_s

        # --- Filter out unsuitable segments ---
        if not (min_len_s < duration < max_len_s):
            continue
        
        y_seg = y[int(start_s*sr):int(end_s*sr)]
        if len(y_seg) == 0:
            continue

        # --- Calculate Score ---
        # 1. Rhythmic Density Score
        onset_env = librosa.onset.onset_strength(y=y_seg, sr=sr)
        rhythmic_density = np.mean(onset_env)

        # 2. Energy Stability Score (low variance is good)
        rms = librosa.feature.rms(y=y_seg)[0]
        energy_stability = 1 / (1 + np.var(rms))

        # 3. "Loopability" Score (favors segments that are multiples of 8 bars)
        beats_per_bar = 4 # Assume 4/4 time
        beats = (duration * bpm) / 60
        bars = beats / beats_per_bar
        # Penalize segments that are not close to a multiple of 8 or 16 bars
        loopability_8 = 1 - (abs(round(bars / 8) * 8 - bars) / 8)
        loopability_16 = 1 - (abs(round(bars / 16) * 16 - bars) / 16)
        loopability = max(loopability_8, loopability_16)

        # --- Final Score ---
        final_score = (rhythmic_density * 2) + energy_stability + (loopability * 1.5)

        if final_score > max_score:
            max_score = final_score
            best_segment = segment

    if best_segment:
        print(f"    -> Best clip found: {best_segment['start']:.1f}s - {best_segment['end']:.1f}s (Score: {max_score:.2f})")
        return best_segment['start'] * 1000, best_segment['end'] * 1000
    else:
        # Fallback to just the most energetic part if no suitable segment is found
        print("  Fallback: No suitable structural segment found, finding most energetic part.")
        return find_energetic_segment(song_path)

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

    # --- If energetic style, clip tracks to their most energetic part --- #
    if mix_style == 'energetic':
        print("\n--- Clipping tracks for energetic style (Intelligent Mode)... ---")
        clipped_segments = []
        for i, song in enumerate(setlist):
            start_ms, end_ms = find_dj_clip(song['path'], song['structure'], song['bpm'], song['duration'])
            clipped_segments.append(audio_segments[i][start_ms:end_ms])
        audio_segments = clipped_segments

    # --- Initialize the mix --- #
    final_mix = audio_segments[0]
    print(f"Starting mix with: {setlist[0]['filename']}")

    # --- Process transitions --- #
    for i in range(len(setlist) - 1):
        current_features = setlist[i]
        next_features = setlist[i+1]
        next_audio = audio_segments[i+1]

        # --- Step 1: Calculate Crossfade Duration (Style-Dependent) ---
        crossfade_duration = 8000  # Default
        if mix_style == 'pro':
            outro_segment = current_features['structure'][-1] if current_features['structure'] else None
            intro_segment = next_features['structure'][0] if next_features['structure'] else None
            if outro_segment and intro_segment:
                outro_duration = (outro_segment['end'] - outro_segment['start']) * 1000
                intro_duration = (intro_segment['end'] - intro_segment['start']) * 1000
                if outro_duration > 1000 and intro_duration > 1000:
                    crossfade_duration = int(min(outro_duration, intro_duration, 16000))
        else:  # relaxed and energetic
            bpm = current_features['bpm']
            if bpm > 0:
                crossfade_duration = int((60000 / bpm) * 16)  # 4 bars

        safe_crossfade = min(crossfade_duration, len(final_mix), len(next_audio))

        # --- Step 2: Perform Unified EQ-Based Transition ---
        print(f"Mixing in {next_features['filename']} (EQ Transition: {safe_crossfade/1000:.1f}s)")
        
        # 1. Get the audio segments for the transition
        out_fade_segment = final_mix[-safe_crossfade:]
        in_fade_segment = next_audio[:safe_crossfade]

        # 2. High-pass the outgoing segment to remove its bass
        out_fade_filtered = out_fade_segment.high_pass_filter(140)

        # 3. Manually create the transition by fading and overlaying
        transition = in_fade_segment.fade_in(safe_crossfade).overlay(
            out_fade_filtered.fade_out(safe_crossfade)
        )

        # 4. Stitch the mix back together
        main_part = final_mix[:-safe_crossfade]
        rest_of_next_track = next_audio[safe_crossfade:]
        final_mix = main_part + transition + rest_of_next_track

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
                     'vocal_regions' in cached_data and
                     'duration' in cached_data) # Check for new duration field

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