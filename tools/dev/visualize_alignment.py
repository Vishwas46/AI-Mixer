# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import os
import argparse

def visualize_alignment(stems_dir_1, stems_dir_2, name_1, name_2):
    """
    Generates and saves a plot comparing the beat alignments of two sets of stems.
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

    # Create plots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True, sharey=True)

    ax1.set_title(f'Beat Alignment - {name_1}')
    librosa.display.waveshow(y_drm_1, sr=sr1, alpha=0.5, ax=ax1, label='Drums')
    ax1.vlines(librosa.frames_to_time(beats_voc_1, sr=sr1), -1, 1, color='r', linestyle='--', label='Vocals')
    ax1.vlines(librosa.frames_to_time(beats_drm_1, sr=sr1), -1, 1, color='b', linestyle=':', label='Drums')
    ax1.legend()

    ax2.set_title(f'Beat Alignment - {name_2}')
    librosa.display.waveshow(y_drm_2, sr=sr2, alpha=0.5, ax=ax2, label='Drums')
    ax2.vlines(librosa.frames_to_time(beats_voc_2, sr=sr2), -1, 1, color='r', linestyle='--', label='Vocals')
    ax2.vlines(librosa.frames_to_time(beats_drm_2, sr=sr2), -1, 1, color='b', linestyle=':', label='Drums')
    ax2.legend()

    plt.tight_layout()
    plt.savefig('beat_alignment_comparison.png')
    print("Saved beat alignment comparison to beat_alignment_comparison.png")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stems_dir_1', help='Path to the first stems directory')
    parser.add_argument('stems_dir_2', help='Path to the second stems directory')
    parser.add_argument('--name_1', default='Original', help='Name for the first plot')
    parser.add_argument('--name_2', default='DTW', help='Name for the second plot')
    args = parser.parse_args()
    visualize_alignment(args.stems_dir_1, args.stems_dir_2, args.name_1, args.name_2)