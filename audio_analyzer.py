# spotify_client.py
import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

def get_spotify_client():
    """Returns an authenticated spotipy client."""
    load_dotenv()
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env file")

    client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(client_credentials_manager=client_credentials_manager)

import librosa
import numpy as np

def analyze_audio_local(file_path):
    """
    Analyzes a local audio file to extract BPM and musical key.
    """
    print(f"Analyzing {file_path} locally...")
    y, sr = librosa.load(file_path)

    # 1. Estimate BPM (Tempo)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

    # 2. Estimate Key
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    
    # Correlate with major and minor key profiles
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

    major_correlations = [np.corrcoef(chroma_mean, np.roll(major_profile, i))[0, 1] for i in range(12)]
    # audio_analyzer.py
import librosa
import numpy as np

def analyze_audio_local(file_path):
    """
    Analyzes a local audio file to extract BPM and musical key.
    """
    print(f"Analyzing {file_path} locally...")
    y, sr = librosa.load(file_path)

    # 1. Estimate BPM (Tempo)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

    # 2. Estimate Key
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    
    # Correlate with major and minor key profiles
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

    return {
        "bpm": float(tempo),
        "key": int(key_index),
        "mode": key_mode,
        "key_str": key_str
    }


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

    return {
        "bpm": float(tempo),
        "key": int(key_index),
        "mode": key_mode,
        "key_str": key_str
    }