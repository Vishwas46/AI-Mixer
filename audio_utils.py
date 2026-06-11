# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# audio_utils.py
import os
import shutil
import subprocess
import tempfile
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

def has_ffmpeg():
    """True when the ffmpeg binary (needed for MP3 export) is on PATH."""
    return shutil.which("ffmpeg") is not None

def export_audio(y, sr, output_dir, base_name, export_quality="high"):
    """Export mono float audio as MP3 when ffmpeg is available, else WAV.

    Args:
        y: mono float32/float64 numpy array in [-1, 1]
        sr: sample rate
        output_dir: destination directory (created if missing)
        base_name: filename without extension
        export_quality: 'high' (320k) or 'standard' (256k) MP3 bitrate

    Returns:
        str: path of the file actually written (.mp3 or .wav)
    """
    os.makedirs(output_dir, exist_ok=True)
    y = np.asarray(y, dtype=np.float32)

    if has_ffmpeg():
        from pydub import AudioSegment
        bitrate = "320k" if export_quality == "high" else "256k"
        output_path = os.path.join(output_dir, f"{base_name}.mp3")
        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            sf.write(tmp_wav.name, y, sr)
            AudioSegment.from_wav(tmp_wav.name).export(
                output_path, format="mp3", bitrate=bitrate)
        finally:
            os.unlink(tmp_wav.name)
        return output_path

    output_path = os.path.join(output_dir, f"{base_name}.wav")
    sf.write(output_path, np.clip(y, -1.0, 1.0), sr)
    print(f"  [Export] ffmpeg not found — wrote WAV instead of MP3: {base_name}.wav")
    return output_path