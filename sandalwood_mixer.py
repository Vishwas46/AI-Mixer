# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# sandalwood_mixer.py
# Professional Sandalwood/Kannada mashup mixer featuring:
# - Stem-Based Mixing (Zero vocal clash, pristine drum transients)
# - Formant-Preserving Pitch Shifting (Maintains singer's natural throat size)
# - Microtonal "Shruti" Alignment (Fixes analog tape drift from 60s/70s tracks)
# - Dynamic Sidechain Ducking (Psychoacoustic vocal pocketing)
# - Master Bus "Glue" (Pedalboard Studio Compressors & Limiters)
# -----------------------------------------------------------------------------

import os
import numpy as np
import librosa
import pyrubberband as pyrb
import scipy.signal
import scipy.ndimage
import subprocess
from datetime import datetime

from audio_utils import export_audio

# Try to import Pedalboard for Studio-Grade Mastering
try:
    from pedalboard import Pedalboard, Compressor, HighpassFilter, Delay
    try:
        from pedalboard import Limiter
    except ImportError:  # pre-0.9 releases shipped the class as PeakLimiter
        from pedalboard import PeakLimiter as Limiter
    HAS_PEDALBOARD = True
except ImportError:
    HAS_PEDALBOARD = False
    print("WARNING: 'pedalboard' not installed. Falling back to basic clipping. Run: pip install pedalboard")

# Try to import pyloudnorm for LUFS normalization
try:
    import pyloudnorm as pyln
    HAS_PYLOUDNORM = True
except ImportError:
    HAS_PYLOUDNORM = False
    print("WARNING: pyloudnorm not installed. Using peak normalization instead.")


# =============================================================================
# PRO DSP & AUDIO UTILITIES
# =============================================================================

def separate_stems_demucs(file_path, output_dir, venv_path=None):
    """Run Demucs to separate audio into 4 stems: Vocals, Drums, Bass, Other."""
    print(f"  [Stem Separation] Running Demucs on {os.path.basename(file_path)}...")
    model = "htdemucs_ft"
    demucs_cmd = os.path.join(venv_path, 'bin', 'demucs') if venv_path else "demucs"
    
    try:
        subprocess.run([demucs_cmd, "-o", output_dir, "-n", model, file_path], 
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        stem_dir = os.path.join(output_dir, model, base_name)
        return {
            'vocals': os.path.join(stem_dir, "vocals.wav"),
            'drums': os.path.join(stem_dir, "drums.wav"),
            'bass': os.path.join(stem_dir, "bass.wav"),
            'other': os.path.join(stem_dir, "other.wav")
        }
    except Exception as e:
        print(f"  [Stem Error] Demucs failed: {e}. Falling back to master audio.")
        return None

def detect_shruti_tuning(y, sr):
    """Detects tape-drift (Shruti). Calculates how many cents off the track is from A440."""
    tuning = librosa.estimate_tuning(y=y, sr=sr)
    cents_offset = tuning * 100.0 
    return cents_offset

def time_stretch_audio(y, sr, source_bpm, target_bpm):
    """Time-stretch audio to match target BPM using pyrubberband (crisp transients)."""
    if source_bpm <= 0 or target_bpm <= 0: return y
    ratio = target_bpm / source_bpm
    
    if ratio < 0.5 or ratio > 2.0:
        ratio = max(0.5, min(2.0, ratio))
    if abs(ratio - 1.0) < 0.02: return y
    
    # -c 3 preserves transients for drums
    try:
        return pyrb.time_stretch(y, sr, ratio, rbargs={'-c': '3'})
    except Exception:
        try:
            return pyrb.time_stretch(y, sr, ratio)
        except Exception:
            # rubberband binary missing — librosa phase-vocoder fallback
            print("  [DSP] rubberband unavailable, using librosa time-stretch fallback")
            return librosa.effects.time_stretch(y=y, rate=ratio)

def pitch_shift_pro(y, sr, semitones, cents_offset=0, is_vocal=False):
    """
    Pitch-shift audio using Formant Preservation and Shruti (Microtonal) tuning.
    """
    total_shift = semitones + (cents_offset / 100.0)
    if abs(total_shift) < 0.05: return y

    # -F preserves formants (throat size) so singers don't sound like chipmunks
    rbargs = {'-F': ''} if is_vocal else {'-c': '3'}
    
    try:
        return pyrb.pitch_shift(y, sr, total_shift, rbargs=rbargs)
    except Exception:
        try:
            return pyrb.pitch_shift(y, sr, total_shift)
        except Exception:
            # rubberband binary missing — librosa fallback (no formant preservation)
            print("  [DSP] rubberband unavailable, using librosa pitch-shift fallback")
            return librosa.effects.pitch_shift(y=y, sr=sr, n_steps=total_shift)

def dynamic_sidechain_ducking(instrumental, vocal, sr, max_reduction_db=-4.0):
    """
    Psychoacoustic ducking: Smoothly reduces instrumental volume exactly when vocals hit.
    """
    print("  [Pro DSP] Applying dynamic sidechain ducking (Vocals carving Instrumental pocket)...")
    if len(instrumental) == 0 or len(vocal) == 0:
        return instrumental

    length = min(len(instrumental), len(vocal))
    inst_trim = instrumental[:length]
    voc_trim = vocal[:length]

    # Calculate Vocal RMS Energy
    frame_length = int(sr * 0.05) # 50ms
    hop_length = int(sr * 0.01)   # 10ms
    rms = librosa.feature.rms(y=voc_trim, frame_length=frame_length, hop_length=hop_length)[0]
    
    # Smooth the RMS to prevent popping (Attack/Release simulation)
    rms_smoothed = scipy.ndimage.gaussian_filter1d(rms, sigma=3)
    rms_norm = rms_smoothed / (np.max(rms_smoothed) + 1e-9)
    
    # Map normalized RMS to a gain reduction curve
    gain_db = rms_norm * max_reduction_db
    gain_lin = 10 ** (gain_db / 20.0)
    
    # Interpolate curve back to audio sample rate
    times_rms = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
    times_audio = np.linspace(0, length/sr, length)
    gain_curve = np.interp(times_audio, times_rms, gain_lin)
    
    ducked_inst = inst_trim * gain_curve
    
    # Pad back to original length if needed
    if length < len(instrumental):
        ducked_inst = np.concatenate([ducked_inst, instrumental[length:]])
        
    return ducked_inst

def apply_master_bus_glue(y, sr, target_lufs=-14.0):
    """
    Studio-grade mastering using Spotify's Pedalboard. Adds glue and limits peaks safely.
    """
    if HAS_PYLOUDNORM:
        try:
            meter = pyln.Meter(sr)
            current_lufs = meter.integrated_loudness(y)
            if not (np.isinf(current_lufs) or np.isnan(current_lufs)):
                gain_db = target_lufs - current_lufs
                gain_db = max(-20, min(20, gain_db))
                y = pyln.normalize.loudness(y, current_lufs, target_lufs)
        except Exception:
            pass

    if HAS_PEDALBOARD:
        print("  [Mastering] Applying Master Bus Compression & Peak Limiting...")
        board = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=30), # Remove subsonic rumble
            Compressor(threshold_db=-14.0, ratio=2.5, attack_ms=15.0, release_ms=150.0),
            Limiter(threshold_db=-0.3, release_ms=100.0)
        ])
        y_2d = np.expand_dims(y, axis=0)
        y = board(y_2d, sr, reset=True)[0]
    else:
        peak = np.max(np.abs(y))
        if peak > 0:
            y = y * (0.95 / peak)

    # True-peak safety: limiter release tails can overshoot slightly, and
    # 16-bit export would hard-clip anything above full scale
    peak = np.max(np.abs(y)) if len(y) else 0.0
    if peak > 0.985:
        y = y * (0.985 / peak)
    return y

def get_key_semitone_diff(key1_idx, mode1, key2_idx, mode2):
    diff = (key2_idx - key1_idx) % 12
    if diff == 0: return 0 
    if diff == 3 and mode1 != mode2: return 0 
    if diff == 9 and mode1 != mode2: return 0 
    if diff == 7 or diff == 5: return 0 
    if diff <= 6: return diff
    else: return diff - 12

def snap_to_tala_boundary(target_time, downbeat_times, beats_per_cycle):
    if not downbeat_times or beats_per_cycle <= 0: return target_time
    downbeats_per_cycle = max(1, beats_per_cycle // 4)
    cycle_boundaries = downbeat_times[::downbeats_per_cycle]
    if not cycle_boundaries: return min(downbeat_times, key=lambda x: abs(x - target_time))
    return min(cycle_boundaries, key=lambda x: abs(x - target_time))

def get_cue_points(track_analysis):
    cue_points = track_analysis.get('dj_cue_points', {})
    mix_in = cue_points.get('mix_in', {}).get('time', 0)
    mix_out = cue_points.get('mix_out', {}).get('time')
    if mix_out is None:
        duration = track_analysis.get('duration', 180)
        mix_out = duration * 0.8
    return mix_in, mix_out


# =============================================================================
# BUTTERWORTH FILTERS & TRANSITION UTILITIES
# =============================================================================

def apply_butterworth_hpf(y, sr, cutoff=250, order=4):
    """Butterworth High-Pass Filter for bass_swap transitions."""
    nyquist = 0.5 * sr
    normal_cutoff = cutoff / nyquist
    b, a = scipy.signal.butter(order, normal_cutoff, btype='high', analog=False)
    return scipy.signal.lfilter(b, a, y)


def apply_butterworth_lpf(y, sr, cutoff=5000, order=4):
    """Butterworth Low-Pass Filter for filter_sweep transitions."""
    nyquist = 0.5 * sr
    normal_cutoff = cutoff / nyquist
    b, a = scipy.signal.butter(order, normal_cutoff, btype='low', analog=False)
    return scipy.signal.lfilter(b, a, y)


def select_transition_type(track1_analysis, track2_analysis, style='energetic'):
    """Select optimal transition type based on energy, vocals, and style."""
    energy1 = track1_analysis.get('energy', 0.5)
    energy2 = track2_analysis.get('energy', 0.5)
    energy_diff = energy2 - energy1
    vocals_overlap = (
        track1_analysis.get('has_vocals', False)
        and track2_analysis.get('has_vocals', False)
    )

    if style == 'showcase':
        if energy_diff > 0.2:
            return 'bass_swap'
        elif energy_diff < -0.2:
            return 'echo_out'
        elif vocals_overlap:
            return 'filter_sweep'
        else:
            return 'crossfade'
    elif style == 'smooth':
        return 'filter_sweep' if vocals_overlap else 'crossfade'
    else:  # energetic
        if energy_diff > 0.15:
            return 'bass_swap'
        elif vocals_overlap:
            return 'filter_sweep'
        else:
            return 'crossfade'


def calculate_transition_duration(track1_analysis, track2_analysis, target_bpm):
    """Calculate optimal transition duration in seconds (Tala-aware)."""
    bars = 4
    tala1 = track1_analysis.get('tala', {})
    tala2 = track2_analysis.get('tala', {})
    if tala1.get('tala_key') == tala2.get('tala_key'):
        bars = 8  # Same tala = longer, smoother transition
    if target_bpm > 0:
        return bars * (60.0 / target_bpm) * 4
    return 8.0


def get_pallavi_time(track_analysis):
    """Get the start time of the first Pallavi section."""
    section_class = track_analysis.get('sections', {})
    pallavis = section_class.get('pallavis', [])
    if pallavis:
        return pallavis[0].get('start', None)
    return None


def create_transition_segment(out_audio, in_audio, sr, transition_type='crossfade',
                              duration_sec=4.0):
    """Create a mono transition segment between two audio arrays.

    Used by create_pallavi_medley(). The main mixer uses stem-aware inline logic.
    Returns: (transition_audio, duration_samples)
    """
    duration_samples = int(duration_sec * sr)
    out_len, in_len = len(out_audio), len(in_audio)
    if out_len < duration_samples or in_len < duration_samples:
        duration_samples = min(out_len, in_len)

    out_segment = out_audio[-duration_samples:]
    in_segment = in_audio[:duration_samples]
    t = np.linspace(0, 1, duration_samples)

    if transition_type == 'bass_swap':
        out_hp = apply_butterworth_hpf(out_segment, sr, cutoff=250)
        transition = out_hp * (1 - t) + in_segment * t
    elif transition_type == 'filter_sweep':
        num_chunks = 10
        chunk_size = duration_samples // num_chunks
        filtered_out = out_segment.copy()
        for c in range(num_chunks):
            c_start = c * chunk_size
            c_end = c_start + chunk_size if c < num_chunks - 1 else duration_samples
            cutoff = max(2000, 10000 - (c * 800))
            filtered_out[c_start:c_end] = apply_butterworth_lpf(
                out_segment[c_start:c_end], sr, cutoff)
        transition = filtered_out * (1 - t) + in_segment * t
    elif transition_type == 'echo_out':
        delay_samples = int(0.25 * sr)
        decayed = out_segment.copy()
        for tap in range(1, 5):
            offset = tap * delay_samples
            decay = 0.6 ** tap
            if offset < duration_samples:
                decayed[offset:] += out_segment[:duration_samples - offset] * decay
        decayed = np.clip(decayed, -1.0, 1.0)
        transition = decayed * (1 - t) + in_segment * t
    else:  # crossfade
        transition = out_segment * np.sqrt(1 - t) + in_segment * np.sqrt(t)

    return np.clip(transition, -1.0, 1.0), duration_samples


# =============================================================================
# MAIN PRO MIXER ENGINE (STEM-BASED)
# =============================================================================

def create_sandalwood_mashup(tracks_analysis, mashup_plan, output_dir, target_lufs=-14.0, export_quality='high'):
    print("\n" + "="*70)
    print("SANDALWOOD BROADCAST-READY MIXER (STEMS + FORMANT PRESERVATION)")
    print("="*70)

    if len(tracks_analysis) < 2:
        raise ValueError("Need at least 2 tracks for a mashup")

    track_order = mashup_plan.get('track_order', [t['filename'] for t in tracks_analysis])
    style = mashup_plan.get('style', 'energetic')
    tracks_by_name = {t['filename']: t for t in tracks_analysis}
    
    bpms = [t.get('bpm', 120) for t in tracks_analysis if t.get('bpm', 0) > 0]
    target_bpm = np.median(bpms) if bpms else 120
    print(f"\nTarget Master Clock: {target_bpm:.1f} BPM")

    sr = 44100
    venv_path = os.environ.get('VIRTUAL_ENV', os.path.abspath("./venv"))
    stem_cache_dir = os.path.join(output_dir, "stem_cache")
    processed_tracks = []

    # -------------------------------------------------------------------------
    # PHASE 1: Pre-processing (Stem Separation, Shruti, Time & Pitch)
    # -------------------------------------------------------------------------
    print("\n--- Phase 1: Stem Loading & DSP Processing ---")
    for i, filename in enumerate(track_order):
        track_data = tracks_by_name.get(filename)
        if not track_data: continue
        
        file_path = track_data.get('file_path')
        print(f"\n[{i+1}/{len(track_order)}] Processing: {filename}")
        
        # Load master to find tuning drift
        y_master, _ = librosa.load(file_path, sr=sr, mono=True)
        cents_drift = detect_shruti_tuning(y_master, sr)
        print(f"  [Tuning] Detected Shruti drift: {cents_drift:+.1f} cents")

        # 1. Stem Separation
        stem_paths = separate_stems_demucs(file_path, stem_cache_dir, venv_path)
        
        stems = {}
        has_stems = False
        if stem_paths:
            has_stems = True
            print("  [Stem Engine] Loading separated stems (Drums, Bass, Vocals, Other)")
            stems['vocals'], _ = librosa.load(stem_paths['vocals'], sr=sr, mono=True)
            stems['drums'], _ = librosa.load(stem_paths['drums'], sr=sr, mono=True)
            stems['bass'], _ = librosa.load(stem_paths['bass'], sr=sr, mono=True)
            stems['other'], _ = librosa.load(stem_paths['other'], sr=sr, mono=True)
        else:
            print("  [Stem Engine] No stems found. Using Master channel.")
            stems['master'] = y_master

        # 2. Time-Stretch (All Stems)
        original_bpm = track_data.get('bpm', target_bpm)
        ratio = target_bpm / original_bpm
        if abs(ratio - 1.0) > 0.02:
            print(f"  Time-stretching: {original_bpm:.1f} -> {target_bpm:.1f} BPM")
            for key in stems.keys():
                stems[key] = time_stretch_audio(stems[key], sr, original_bpm, target_bpm)

        # 3. Harmonic Locking & Formant-Preserved Pitch Shifting
        shift_semitones = 0
        if i > 0:
            prev_track_data = processed_tracks[-1]['analysis']
            shift_semitones = get_key_semitone_diff(
                prev_track_data['key'], prev_track_data['mode'],
                track_data['key'], track_data['mode']
            )

        # Total shift includes semitones and microtonal cents correction
        total_shift = shift_semitones - (cents_drift / 100.0)

        if abs(total_shift) > 0.05:
            print(f"  [Harmonic Sync] Pitch-shifting by {total_shift:+.2f} semitones")
            if has_stems:
                # NEVER PITCH SHIFT DRUMS! Preserves transients and kick drum punch.
                stems['vocals'] = pitch_shift_pro(stems['vocals'], sr, total_shift, is_vocal=True)
                stems['bass'] = pitch_shift_pro(stems['bass'], sr, total_shift, is_vocal=False)
                stems['other'] = pitch_shift_pro(stems['other'], sr, total_shift, is_vocal=False)
            else:
                stems['master'] = pitch_shift_pro(stems['master'], sr, total_shift, is_vocal=False)

        # Map Beat Grid to new tempo
        time_scale = 1.0 / ratio
        original_downbeats = track_data.get('beat_grid', {}).get('downbeat_times', [])
        synced_downbeats = [t * time_scale for t in original_downbeats]
        
        mix_in, mix_out = get_cue_points(track_data)

        processed_tracks.append({
            'filename': filename,
            'stems': stems,
            'has_stems': has_stems,
            'downbeats': synced_downbeats,
            'mix_in': mix_in * time_scale,
            'mix_out': mix_out * time_scale,
            'analysis': track_data
        })

    # -------------------------------------------------------------------------
    # PHASE 2: Multitrack Timeline Composition (Stem Swapping)
    # -------------------------------------------------------------------------
    print("\n--- Phase 2: Timeline Construction & Stem Mixing ---")
    
    total_samples_est = sum([len(t['stems'].get('drums', t['stems'].get('master', []))) for t in processed_tracks])
    
    # 2 Dedicated Busses for sidechaining
    timeline_inst = np.zeros(total_samples_est, dtype=np.float32)
    timeline_voc = np.zeros(total_samples_est, dtype=np.float32)
    
    prev_placement = None 

    for i, track in enumerate(processed_tracks):
        stems = track['stems']
        
        if track['has_stems']:
            track_inst = stems['drums'] + stems['bass'] + stems['other']
            track_voc = stems['vocals']
        else:
            track_inst = stems['master']
            track_voc = np.zeros_like(track_inst)

        track_len = len(track_inst)
        
        if i == 0:
            start_index = 0
            # Fade in
            fade_in_len = int(0.05 * sr)
            if track_len > fade_in_len:
                track_inst[:fade_in_len] *= np.linspace(0, 1, fade_in_len)
                track_voc[:fade_in_len] *= np.linspace(0, 1, fade_in_len)
                
            timeline_inst[:track_len] += track_inst
            timeline_voc[:track_len] += track_voc
            prev_placement = {'start_index': 0, 'end_index': track_len, 'track': track}
        else:
            prev_track = prev_placement['track']
            
            # Tala-aware Phase Alignment
            prev_beats = prev_track['analysis'].get('tala', {}).get('beats_per_cycle', 4)
            curr_beats = track['analysis'].get('tala', {}).get('beats_per_cycle', 4)

            prev_exit_beat = snap_to_tala_boundary(prev_track['mix_out'], prev_track['downbeats'], prev_beats)
            curr_entry_beat = snap_to_tala_boundary(track['mix_in'], track['downbeats'], curr_beats)

            global_handoff = prev_placement['start_index'] + int(prev_exit_beat * sr)
            start_index = max(0, global_handoff - int(curr_entry_beat * sr))
            
            # Expand buffers if needed
            end_index = start_index + track_len
            if end_index > len(timeline_inst):
                pad_len = end_index - len(timeline_inst)
                timeline_inst = np.concatenate([timeline_inst, np.zeros(pad_len)])
                timeline_voc = np.concatenate([timeline_voc, np.zeros(pad_len)])

            overlap_len = prev_placement['end_index'] - start_index
            
            # --- STEM-AWARE TRANSITION (4 types) ---
            if overlap_len > 0:
                prev_analysis = prev_track['analysis']
                curr_analysis = track['analysis']
                transition_type = select_transition_type(prev_analysis, curr_analysis, style)
                trans_duration_sec = calculate_transition_duration(
                    prev_analysis, curr_analysis, target_bpm)
                trans_len = min(int(trans_duration_sec * sr), overlap_len)

                print(f"  Transition [{transition_type}] ({trans_duration_sec:.1f}s): "
                      f"{prev_track['filename']} -> {track['filename']}")

                t = np.linspace(0, 1, trans_len)
                inst_seg = timeline_inst[start_index:start_index + trans_len].copy()

                # -- Instrumental bus transition --
                if transition_type == 'bass_swap':
                    # Butterworth HPF strips bass from outgoing, incoming punches through
                    filtered = apply_butterworth_hpf(inst_seg, sr, cutoff=250)
                    timeline_inst[start_index:start_index + trans_len] = (
                        filtered * (1 - t) + inst_seg * t * 0)  # kill old bass
                    timeline_inst[start_index:start_index + trans_len] *= (1 - t)
                    track_inst[:trans_len] *= t
                elif transition_type == 'filter_sweep':
                    # Progressive Butterworth LPF sweeps out the outgoing track
                    num_chunks = 10
                    chunk_size = trans_len // num_chunks
                    for c in range(num_chunks):
                        c_start = c * chunk_size
                        c_end = c_start + chunk_size if c < num_chunks - 1 else trans_len
                        cutoff = max(2000, 10000 - (c * 800))
                        chunk = inst_seg[c_start:c_end]
                        timeline_inst[start_index + c_start:start_index + c_end] = (
                            apply_butterworth_lpf(chunk, sr, cutoff))
                    # Also fade out the filtered result
                    timeline_inst[start_index:start_index + trans_len] *= (1 - t)
                    track_inst[:trans_len] *= t
                elif transition_type == 'echo_out':
                    # Multi-tap delay on outgoing instrumental
                    delay_samples = int(0.25 * sr)
                    decayed = inst_seg.copy()
                    for tap in range(1, 5):
                        offset = tap * delay_samples
                        decay = 0.6 ** tap
                        if offset < trans_len:
                            decayed[offset:] += inst_seg[:trans_len - offset] * decay
                    decayed = np.clip(decayed, -1.0, 1.0)
                    timeline_inst[start_index:start_index + trans_len] = decayed * (1 - t)
                    track_inst[:trans_len] *= t
                else:  # crossfade — sqrt curves for smooth equal-power
                    timeline_inst[start_index:start_index + trans_len] *= np.sqrt(1 - t)
                    track_inst[:trans_len] *= np.sqrt(t)

                # Fade remaining overlap beyond trans_len (if overlap > transition)
                remaining_overlap = overlap_len - trans_len
                if remaining_overlap > 0:
                    rem_start = start_index + trans_len
                    rem_t = np.linspace(0, 1, remaining_overlap)
                    timeline_inst[rem_start:prev_placement['end_index']] *= (1 - rem_t)
                    track_inst[trans_len:overlap_len] *= rem_t

                # -- Vocal bus transition --
                if transition_type == 'echo_out' and HAS_PEDALBOARD and prev_track['has_stems']:
                    # Analog delay tail on outgoing vocals
                    delay_board = Pedalboard([
                        Delay(delay_seconds=60 / target_bpm, feedback=0.3, mix=0.4)])
                    tail = timeline_voc[start_index:start_index + trans_len]
                    tail_2d = np.expand_dims(tail, axis=0)
                    processed_tail = delay_board(tail_2d, sr, reset=True)[0]
                    timeline_voc[start_index:start_index + trans_len] = (
                        processed_tail * np.sqrt(1 - t))
                else:
                    # Smooth sqrt crossfade for vocals on all other transition types
                    timeline_voc[start_index:start_index + trans_len] *= np.sqrt(1 - t)

                # Fade in incoming vocals
                track_voc[:trans_len] *= np.sqrt(t)

                # Handle remaining vocal overlap
                if remaining_overlap > 0:
                    rem_t = np.linspace(0, 1, remaining_overlap)
                    timeline_voc[rem_start:prev_placement['end_index']] *= np.sqrt(1 - rem_t)
                    track_voc[trans_len:overlap_len] *= np.sqrt(rem_t)

            # Mix into timeline
            timeline_inst[start_index:end_index] += track_inst
            timeline_voc[start_index:end_index] += track_voc
            
            prev_placement = {'start_index': start_index, 'end_index': end_index, 'track': track}

    # Fade out last track (3-second fade)
    fade_out_len = int(3.0 * sr)
    if prev_placement and prev_placement['end_index'] > fade_out_len:
        end = min(prev_placement['end_index'], len(timeline_inst))
        start = end - fade_out_len
        fade_curve = np.linspace(1, 0, fade_out_len)
        timeline_inst[start:end] *= fade_curve
        timeline_voc[start:end] *= fade_curve

    # -------------------------------------------------------------------------
    # PHASE 3: Summing & Psychoacoustic Ducking
    # -------------------------------------------------------------------------
    print("\n--- Phase 3: Summing & Psychoacoustics ---")
    
    # Trim silence
    non_zeros = np.nonzero(timeline_inst + timeline_voc)[0]
    if len(non_zeros) > 0:
        start_idx = non_zeros[0]
        end_idx = non_zeros[-1]
        timeline_inst = timeline_inst[start_idx:end_idx]
        timeline_voc = timeline_voc[start_idx:end_idx]

    # Apply dynamic sidechain: vocals physically carve space out of the instrumental track
    timeline_inst = dynamic_sidechain_ducking(timeline_inst, timeline_voc, sr, max_reduction_db=-3.5)
    
    # Sum master
    master_mix = timeline_inst + timeline_voc

    # -------------------------------------------------------------------------
    # PHASE 4: Studio Mastering
    # -------------------------------------------------------------------------
    print("\n--- Phase 4: Final Mastering ---")
    final_audio = apply_master_bus_glue(master_mix, sr, target_lufs)

    # -------------------------------------------------------------------------
    # PHASE 5: Export
    # -------------------------------------------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"sandalwood_pro_mix_{style}_{timestamp}"
    print(f"Exporting: {base_name} ({len(final_audio)/sr:.1f}s)")
    output_path = export_audio(final_audio, sr, output_dir, base_name, export_quality)

    # Stem cache preserved at stem_cache_dir for faster re-renders
    print("✅ Professional Mashup Creation Successful!")
    return output_path

# =============================================================================
# PALLAVI MEDLEY CREATOR
# =============================================================================

def create_pallavi_medley(tracks_analysis, output_dir, target_lufs=-14.0):
    """Create a Pallavi-to-Pallavi medley from multiple Kannada tracks.

    Extracts the Pallavi (chorus) section from each track, time-stretches to a
    common BPM, and chains them with crossfade transitions. Applies master bus
    glue for broadcast-ready output.

    Args:
        tracks_analysis: List of analysis dicts from analyze_kannada_track_for_mashup
        output_dir: Directory for output file
        target_lufs: Target loudness in LUFS (default -14.0)

    Returns:
        str: Path to the exported MP3 file
    """
    print("\n" + "=" * 60)
    print("PALLAVI MEDLEY CREATOR")
    print("=" * 60)

    sr = 44100
    pallavi_segments = []

    for track in tracks_analysis:
        pallavi_time = get_pallavi_time(track)
        if pallavi_time is None:
            # Fallback: use the primary hook time
            hooks = track.get('hooks_and_drops', {}).get('hooks', [])
            if hooks:
                pallavi_time = hooks[0].get('time', hooks[0].get('start', None))
        if pallavi_time is None:
            print(f"  No Pallavi found for {track['filename']}, skipping")
            continue

        file_path = track.get('file_path')
        if not file_path or not os.path.exists(file_path):
            print(f"  File not found for {track['filename']}, skipping")
            continue

        y, _ = librosa.load(file_path, sr=sr, mono=True)
        pallavi_sample = int(pallavi_time * sr)
        segment_duration = 30 * sr  # 30 seconds per pallavi segment
        start = max(0, pallavi_sample - int(5 * sr))  # 5s before pallavi
        end = min(len(y), start + segment_duration)
        segment = y[start:end]

        # Time-stretch to common BPM
        track_bpm = track.get('bpm', 120)
        target_bpm = 128
        if abs(track_bpm - target_bpm) > 3:
            segment = time_stretch_audio(segment, sr, track_bpm, target_bpm)

        pallavi_segments.append({
            'filename': track['filename'],
            'audio': segment,
        })
        print(f"  Extracted Pallavi from {track['filename']} at {pallavi_time:.1f}s")

    if len(pallavi_segments) < 2:
        raise ValueError("Need at least 2 tracks with Pallavi sections for a medley")

    # Chain segments with crossfade transitions
    print(f"\nChaining {len(pallavi_segments)} Pallavi segments with crossfades...")
    final_audio = pallavi_segments[0]['audio']
    for i in range(1, len(pallavi_segments)):
        segment = pallavi_segments[i]['audio']
        transition, trans_samples = create_transition_segment(
            final_audio, segment, sr, 'crossfade', 2.0)
        main_part = final_audio[:-trans_samples]
        rest = segment[trans_samples:]
        final_audio = np.concatenate([main_part, transition, rest])

    # Apply master bus glue
    print("Applying final mastering...")
    final_audio = apply_master_bus_glue(final_audio, sr, target_lufs)

    # Export
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"pallavi_medley_{timestamp}"
    output_path = export_audio(final_audio, sr, output_dir, base_name, "high")

    print(f"✅ Pallavi Medley created: {os.path.basename(output_path)} ({len(final_audio)/sr:.1f}s)")
    return output_path


if __name__ == "__main__":
    print("Sandalwood V3 Pro Mixer - Stem-Based Generative Engine loaded.")
