
import os
import librosa
import librosa.display
import numpy as np
import matplotlib.pyplot as plt

def analyze_transitions(mix_path, setlist_paths, output_dir="transition_analysis"):
    """
    Analyzes the transitions in a DJ mix by generating spectrograms for each transition point.
    """
    print(f"Analyzing mix: {mix_path}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    # Load the full mix
    print("Loading full mix file (this may take a moment)...")
    y_mix, sr_mix = librosa.load(mix_path)

    # Calculate transition points based on original track durations
    print("Calculating transition points...")
    cumulative_duration = 0
    transition_points_s = []
    for i, song_path in enumerate(setlist_paths[:-1]):
        try:
            duration = librosa.get_duration(path=song_path)
            cumulative_duration += duration
            transition_points_s.append(cumulative_duration)
            print(f"  Track {i+1} ({os.path.basename(song_path)}) ends at {cumulative_duration:.2f}s")
        except Exception as e:
            print(f"Could not process {song_path}: {e}")
            # Fallback if a song can't be read
            if i > 0:
                transition_points_s.append(transition_points_s[-1] + 180) # Assume 3 min duration
            else:
                transition_points_s.append(180)


    # Analyze each transition
    for i, point_s in enumerate(transition_points_s):
        track_a_name = os.path.splitext(os.path.basename(setlist_paths[i]))[0][:20]
        track_b_name = os.path.splitext(os.path.basename(setlist_paths[i+1]))[0][:20]
        print(f"\nAnalyzing transition {i+1}: {track_a_name} -> {track_b_name}...")

        # Define a 30-second window around the transition point
        start_s = max(0, point_s - 15)
        end_s = min(point_s + 15, len(y_mix) / sr_mix)
        
        # Extract the clip from the main mix
        start_sample = librosa.time_to_samples(start_s, sr=sr_mix)
        end_sample = librosa.time_to_samples(end_s, sr=sr_mix)
        y_clip = y_mix[start_sample:end_sample]

        # Create the Mel spectrogram
        S = librosa.feature.melspectrogram(y=y_clip, sr=sr_mix, n_mels=128, fmax=8000)
        S_dB = librosa.power_to_db(S, ref=np.max)

        # Plotting
        fig, ax = plt.subplots(figsize=(12, 6))
        img = librosa.display.specshow(S_dB, sr=sr_mix, x_axis='time', y_axis='mel', ax=ax, fmax=8000)
        fig.colorbar(img, ax=ax, format='%+2.0f dB')
        
        # Add a line for the exact transition point
        transition_line_time = point_s - start_s
        ax.axvline(x=transition_line_time, color='r', linestyle='--', linewidth=2, label=f'Transition Point ({point_s:.2f}s)')
        
        ax.set_title(f"Spectrogram of Transition {i+1}\n({track_a_name} -> {track_b_name})")
        ax.set_xlabel("Time (seconds within clip)")
        ax.set_ylabel("Frequency (Hz)")
        ax.legend()

        # Save the figure
        output_path = os.path.join(output_dir, f"transition_{i+1}_{track_a_name}_to_{track_b_name}.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"  Saved analysis to: {output_path}")

    print("\nAnalysis complete.")

if __name__ == '__main__':
    # --- Configuration ---
    LATEST_MIX_FILE = "remix_outputs/ai_dj_set_pro_20250921_194837.mp3"
    SONGS_DIR = "songs/"

    # This setlist is from the log of the last run
    CURATED_SETLIST_FILENAMES = [
        "Darude - Sandstorm [y6120QOlsfU].mp3",
        "Age Of Love - The Age Of Love (Charlotte de Witte & Enrico Sangiuliano Remix) [0YVvcTIGy40].mp3",
        "Faithless - Insomnia (Official 4K Video) [P8JEm4d6Wu4].mp3",
        "Swedish House Mafia ft. John Martin - Don't You Worry Child (Official Video) [1y6smkh6c-0].mp3",
        "Daft Punk - One More Time (Official Video) [FGBhQbmPwH8].mp3",
        "Avicii - Levels [_ovdm2yX4MA].mp3"
    ]

    setlist_full_paths = [os.path.join(SONGS_DIR, f) for f in CURATED_SETLIST_FILENAMES]

    if not os.path.exists(LATEST_MIX_FILE):
        print(f"Error: Mix file not found at {LATEST_MIX_FILE}")
        print("Please make sure the file exists before running the analysis.")
    else:
        analyze_transitions(LATEST_MIX_FILE, setlist_full_paths)
