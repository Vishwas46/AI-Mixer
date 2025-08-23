# remix_engine.py
import os
import shutil
import tempfile
import numpy as np
import pyrubberband as pyrb
from pydub import AudioSegment
from pydub.effects import normalize as pydub_normalize, high_pass_filter
from audio_utils import ensure_dir, run_command, read_wav_mono, write_wav, db_to_gain

def demucs_separate(in_path, out_dir, venv_path):
    """Uses Demucs to separate stems."""
    ensure_dir(out_dir)
    model = "htdemucs_ft"
    demucs_executable = os.path.join(venv_path, 'bin', 'demucs')
    run_command([demucs_executable, "-o", out_dir, "-n", model, in_path])
    base = os.path.splitext(os.path.basename(in_path))[0]
    return os.path.join(out_dir, model, base)

def time_stretch_to_bpm(y, sr, src_bpm, tgt_bpm):
    """Time-stretches audio to a target BPM."""
    if src_bpm <= 1 or tgt_bpm <= 1:
        return y
    rate = tgt_bpm / src_bpm
    return pyrb.time_stretch(y, sr, rate)

def semitone_diff(root_src, mode_src, root_tgt, mode_tgt):
    """Calculates semitone difference between two keys."""
    # This is a placeholder for your original key logic.
    # A simple root difference is often a good starting point.
    return root_tgt - root_src

def process_and_mix(vocals_np, drums_np, bass_np, sr, voc_features, inst_features):
    """Processes and mixes the separated audio stems."""
    print("Stretching, shifting, and aligning tracks...")
    
    # Time-stretch vocals to match instrumental BPM
    vocals_ts = time_stretch_to_bpm(vocals_np, sr, voc_features['bpm'], inst_features['bpm'])
    
    # Pitch-shift vocals to match instrumental key
    n_semi = semitone_diff(voc_features['key'], voc_features['mode'], inst_features['key'], inst_features['mode'])
    print(f"Pitch shifting vocals by {n_semi:+.1f} semitones.")
    vocals_ps = pyrb.pitch_shift(vocals_ts, sr, n_semi)

    # Normalize and gain stage
    def norm(y, peak_db=-1.0):
        peak_lin = db_to_gain(peak_db)
        m = np.max(np.abs(y)) + 1e-9
        return y * (peak_lin / m)

    drums = norm(drums_np, peak_db=-3.0)
    bass = norm(bass_np, peak_db=-6.0)
    vocals = norm(vocals_ps, peak_db=-6.0)
    
    # Ensure all tracks are the same length
    max_len = len(drums)
    vocals = np.pad(vocals, (0, max_len - len(vocals))) if len(vocals) < max_len else vocals[:max_len]
    bass = np.pad(bass, (0, max_len - len(bass))) if len(bass) < max_len else bass[:max_len]

    # Convert to Pydub AudioSegments for mixing
    tmp_dir = tempfile.mkdtemp()
    try:
        write_wav(os.path.join(tmp_dir, "vocals.wav"), vocals, sr)
        write_wav(os.path.join(tmp_dir, "drums.wav"), drums, sr)
        write_wav(os.path.join(tmp_dir, "bass.wav"), bass, sr)

        seg_voc = AudioSegment.from_wav(os.path.join(tmp_dir, "vocals.wav"))
        seg_drums = AudioSegment.from_wav(os.path.join(tmp_dir, "drums.wav"))
        seg_bass = AudioSegment.from_wav(os.path.join(tmp_dir, "bass.wav"))

        # Simple overlay mixing
        mix = seg_drums.overlay(seg_bass).overlay(seg_voc)
        mix = pydub_normalize(mix)

    finally:
        shutil.rmtree(tmp_dir)
        
    return mix

def build_remix(songA_path, songB_path, out_path, venv_path, voc_features, inst_features):
    """Orchestrates the entire remixing process."""
    tmp_dir = tempfile.mkdtemp(prefix="remix_")
    print(f"Temporary files will be stored in: {tmp_dir}")
    try:
        # 1. Separate stems for both songs
        print("Separating stems for Song A...")
        stems_A_dir = demucs_separate(songA_path, tmp_dir, venv_path)
        print("Separating stems for Song B...")
        stems_B_dir = demucs_separate(songB_path, tmp_dir, venv_path)
        
        # 2. Load the required stems
        vocals_np, sr = read_wav_mono(os.path.join(stems_A_dir, "vocals.wav"))
        drums_np, _ = read_wav_mono(os.path.join(stems_B_dir, "drums.wav"))
        bass_np, _ = read_wav_mono(os.path.join(stems_B_dir, "bass.wav"))
        
        # 3. Process and mix
        mix = process_and_mix(vocals_np, drums_np, bass_np, sr, voc_features, inst_features)
        
        # 4. Export final mix
        print(f"Exporting final mix to {out_path}...")
        ext = os.path.splitext(out_path)[1].lower()
        if ext == ".mp3":
            mix.export(out_path, format="mp3", bitrate="320k")
        else:
            mix.export(out_path, format="wav")
            
        print("Remix complete!")

    finally:
        # Comment out the next line to inspect temporary files
        shutil.rmtree(tmp_dir)