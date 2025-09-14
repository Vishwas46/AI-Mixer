import os
import sys
import shutil
import tempfile
import numpy as np
import librosa
from audio_utils import run_command, read_wav_mono

def analyze_alignment(remix_path, venv_path):
    """
    Analyzes the beat alignment of a remixed audio file.
    """
    if not os.path.exists(remix_path):
        print(f"Error: File not found at {remix_path}")
        return

    tmp_dir = tempfile.mkdtemp(prefix="remix_analyze_")
    print(f"Analyzing {os.path.basename(remix_path)}... Temp dir: {tmp_dir}")

    try:
        # 1. Separate stems using Demucs
        print("Separating stems...")
        model = "htdemucs_ft"
        demucs_executable = os.path.join(venv_path, 'bin', 'demucs')
        run_command([demucs_executable, "-o", tmp_dir, "-n", model, remix_path])
        
        stems_dir = os.path.join(tmp_dir, model, os.path.splitext(os.path.basename(remix_path))[0])
        
        vocals_path = os.path.join(stems_dir, "vocals.wav")
        drums_path = os.path.join(stems_dir, "drums.wav")

        if not os.path.exists(vocals_path) or not os.path.exists(drums_path):
            print("Error: Could not find separated vocal/drum stems.")
            return

        # 2. Load stems and get beat tracks
        print("Analyzing beat alignment...")
        y_voc, sr_voc = read_wav_mono(vocals_path)
        y_drm, sr_drm = read_wav_mono(drums_path)

        _, voc_beats = librosa.beat.beat_track(y=y_voc, sr=sr_voc)
        _, drm_beats = librosa.beat.beat_track(y=y_drm, sr=sr_drm)

        # 3. Calculate alignment error
        error_samples = []
        for voc_beat_frame in voc_beats:
            closest_drm_beat_frame = min(drm_beats, key=lambda x: abs(x - voc_beat_frame))
            error_samples.append(abs(voc_beat_frame - closest_drm_beat_frame))

        avg_error_frames = np.mean(error_samples)
        avg_error_ms = librosa.frames_to_time(avg_error_frames, sr=sr_voc) * 1000

        # 4. Print report
        print(f"\n--- Analysis Report for {os.path.basename(remix_path)} ---")
        print(f"Average Beat Alignment Error: {avg_error_ms:.2f} ms")
        if avg_error_ms < 20:
            print("Assessment: Excellent alignment. The vocals are tightly synced to the beat.")
        elif avg_error_ms < 40:
            print("Assessment: Good alignment. The mix should sound clean and professional.")
        elif avg_error_ms < 70:
            print("Assessment: Fair alignment. May have some minor, barely perceptible timing issues.")
        else:
            print("Assessment: Poor alignment. The vocals may sound noticeably off-beat.")
        print("-----------------------------------------------------\
")

    finally:
        shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python temp_analyze.py <path_to_remix_file>")
        sys.exit(1)
    
    remix_file = sys.argv[1]
    venv = os.path.abspath("./venv") 
    analyze_alignment(remix_file, venv)
