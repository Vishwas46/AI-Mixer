# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
import librosa
import matplotlib.pyplot as plt
import numpy as np
import os
import argparse

def plot_alignment_error(stems_dir_1, stems_dir_2, name_1, name_2):
    """
    Generates and saves a plot comparing the beat alignment errors of two sets of stems.
    """
    # Find the actual stem folders
    stems_1_A = os.path.join(stems_dir_1, 'stems', 'htdemucs_ft', 'song1')
    stems_1_B = os.path.join(stems_dir_1, 'stems', 'htdemucs_ft', 'song2')
    stems_2_A = os.path.join(stems_dir_2, 'stems', 'htdemucs_ft', 'song1')
    stems_2_B = os.path.join(stems_dir_2, 'stems', 'htdemucs_ft', 'song2')

    # Load audio
    y_voc_1, sr1 = librosa.load(os.path.join(stems_1_A, 'vocals.wav'))
    y_drm_1, _ = librosa.load(os.path.join(stems_1_B, 'drums.wav'))
    y_voc_2, sr2 = librosa.load(os.path.join(stems_2_A, 'vocals.wav'))
    y_drm_2, _ = librosa.load(os.path.join(stems_2_B, 'drums.wav'))

    # Get beats
    _, beats_voc_1 = librosa.beat.beat_track(y=y_voc_1, sr=sr1)
    _, beats_drm_1 = librosa.beat.beat_track(y=y_drm_1, sr=sr1)
    _, beats_voc_2 = librosa.beat.beat_track(y=y_voc_2, sr=sr2)
    _, beats_drm_2 = librosa.beat.beat_track(y=y_drm_2, sr=sr2)

    # Calculate alignment error
    def calculate_error(beats_voc, beats_drm, sr):
        error = []
        for voc_beat in beats_voc:
            closest_drm_beat = min(beats_drm, key=lambda x: abs(x - voc_beat))
            error.append(abs(voc_beat - closest_drm_beat))
        return librosa.frames_to_time(beats_voc, sr=sr), librosa.frames_to_time(np.array(error), sr=sr)

    time_1, error_1 = calculate_error(beats_voc_1, beats_drm_1, sr1)
    time_2, error_2 = calculate_error(beats_voc_2, beats_drm_2, sr2)

    # Create plot
    plt.figure(figsize=(10, 6))
    plt.plot(time_1, error_1, 'o-', label=name_1)
    plt.plot(time_2, error_2, 'x-', label=name_2)
    plt.title('Beat Alignment Error Comparison')
    plt.xlabel('Time (s)')
    plt.ylabel('Alignment Error (s)')
    plt.legend()
    plt.grid(True)
    plt.savefig('beat_alignment_error.png')
    print("Saved beat alignment error comparison to beat_alignment_error.png")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stems_dir_1', help='Path to the first stems directory')
    parser.add_argument('stems_dir_2', help='Path to the second stems directory')
    parser.add_argument('--name_1', default='Original', help='Name for the first plot')
    parser.add_argument('--name_2', default='DTW', help='Name for the second plot')
    args = parser.parse_args()
    plot_alignment_error(args.stems_dir_1, args.stems_dir_2, args.name_1, args.name_2)