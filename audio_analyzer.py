# audio_analyzer.py
import os
import sys
import shutil
import tempfile
import numpy as np
import librosa
from audio_utils import run_command, read_wav_mono

def analyze_structure(y, sr):
    """
    Analyzes the structure of a track by finding segments based on energy.
    Returns a list of dictionaries with 'start' and 'end' times in seconds.
    """
    print("  Analyzing song structure...")
    # Find segments by splitting the track where the volume is low
    segment_intervals = librosa.effects.split(y, top_db=40)
    
    # Convert from sample indices to seconds
    segments = []
    for interval in segment_intervals:
        segments.append({
            "start": librosa.samples_to_time(interval[0], sr=sr),
            "end": librosa.samples_to_time(interval[1], sr=sr)
        })
    return segments

def analyze_audio_local(file_path):
    """
    Analyzes a local audio file to extract BPM, musical key, energy, and structure.
    """
    print(f"Analyzing {os.path.basename(file_path)} for BPM, Key, Energy, and Structure...")
    y, sr = librosa.load(file_path)

    # 1. Estimate BPM (Tempo)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

    # 2. Estimate Key
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

    major_correlations = [np.corrcoef(chroma_mean, np.roll(major_profile, i))[0, 1] for i in range(12)]
    minor_correlations = [np.corrcoef(chroma_mean, np.roll(minor_profile, i))[0, 1] for i in range(12)]

    major_key = np.argmax(major_correlations)
    minor_key = np.argmax(minor_correlations)

    if np.max(major_correlations) > np.max(minor_correlations):
        key_index = major_key
        key_mode = "maj"
    else:
        key_index = minor_key
        key_mode = "min"
        
    keys = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    key_str = f"{keys[key_index]}:{key_mode}"

    # 3. Calculate Energy
    rms_energy = np.mean(librosa.feature.rms(y=y))
    energy_level = np.clip(rms_energy * 5, 0, 1) 

    # 4. Analyze Structure
    structure = analyze_structure(y, sr)

    return {
        "bpm": float(tempo),
        "key": int(key_index),
        "mode": key_mode,
        "key_str": key_str,
        "energy": float(energy_level),
        "structure": structure
    }

def analyze_vocal_presence(file_path, venv_path):
    """
    Separates a track and analyzes the vocal stem to find regions with vocals.
    Returns a list of dictionaries with 'start' and 'end' times for vocal regions.
    """
    print(f"Analyzing {os.path.basename(file_path)} for vocal presence and regions...")
    tmp_dir = tempfile.mkdtemp(prefix="vocal_check_")
    try:
        # 1. Separate stems using Demucs
        model = "htdemucs_ft"
        demucs_executable = os.path.join(venv_path, 'bin', 'demucs')
        run_command([demucs_executable, "-o", tmp_dir, "-n", model, file_path])
        
        stems_dir = os.path.join(tmp_dir, model, os.path.splitext(os.path.basename(file_path))[0])
        vocals_path = os.path.join(stems_dir, "vocals.wav")

        if not os.path.exists(vocals_path):
            return []

        # 2. Analyze the vocal stem for active regions
        y_voc, sr = librosa.load(vocals_path, sr=None)
        
        # Split based on silence
        vocal_intervals = librosa.effects.split(y_voc, top_db=45)
        
        vocal_regions = []
        if len(vocal_intervals) > 0:
            print(f"  Found {len(vocal_intervals)} potential vocal regions.")
            for interval in vocal_intervals:
                start_sec = librosa.samples_to_time(interval[0], sr=sr)
                end_sec = librosa.samples_to_time(interval[1], sr=sr)
                # Ignore very short, noisy segments
                if (end_sec - start_sec) > 0.5:
                    vocal_regions.append({"start": start_sec, "end": end_sec})
        
        return vocal_regions

    except Exception as e:
        print(f"Could not analyze vocal presence for {os.path.basename(file_path)}: {e}", file=sys.stderr)
        return [] # Assume no vocals on error
    finally:
        shutil.rmtree(tmp_dir)