# audio_utils.py
import os
import subprocess
import numpy as np
import soundfile as sf
import librosa

def run_command(cmd):
    """Executes a shell command and raises an error if it fails."""
    print(">>", " ".join(cmd))
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stdout)
        print(p.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return p.stdout

def ensure_dir(path):
    """Ensures a directory exists."""
    os.makedirs(path, exist_ok=True)
    return path

def read_wav_mono(path, sr=44100):
    """Reads a WAV file into a mono numpy array."""
    y, _ = librosa.load(path, sr=sr, mono=True)
    return y, sr

def write_wav(path, y, sr):
    """Writes a numpy array to a WAV file."""
    y = np.clip(y, -1.0, 1.0).astype(np.float32)
    sf.write(path, y, sr, subtype="PCM_16")

def db_to_gain(db):
    """Converts decibels to linear gain."""
    return 10.0 ** (db / 20.0)