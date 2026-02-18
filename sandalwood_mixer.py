# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# sandalwood_mixer.py
# Professional Sandalwood/Kannada mashup mixer with Phase Alignment,
# Harmonic Mixing, and Butterworth EQ transitions.

import os
import tempfile
import numpy as np
import librosa
import soundfile as sf
import pyrubberband as pyrb
import scipy.signal
from datetime import datetime
from pydub import AudioSegment

# Try to import pyloudnorm for LUFS normalization
try:
    import pyloudnorm as pyln
    HAS_PYLOUDNORM = True
except ImportError:
    HAS_PYLOUDNORM = False
    print("Warning: pyloudnorm not installed. Using peak normalization instead.")


# =============================================================================
# DSP & AUDIO UTILITIES
# =============================================================================

def time_stretch_audio(y, sr, source_bpm, target_bpm):
    """Time-stretch audio to match target BPM using pyrubberband."""
    if source_bpm <= 0 or target_bpm <= 0:
        return y

    ratio = target_bpm / source_bpm
    if ratio < 0.5 or ratio > 2.0:
        print(f"  Warning: BPM ratio {ratio:.2f} is extreme, limiting to 0.5-2.0 range")
        ratio = max(0.5, min(2.0, ratio))

    if abs(ratio - 1.0) < 0.02:
        return y

    print(f"  Time-stretching: {source_bpm:.1f} BPM -> {target_bpm:.1f} BPM (ratio: {ratio:.3f})")
    return pyrb.time_stretch(y, sr, ratio)


def pitch_shift_audio(y, sr, semitones):
    """Pitch-shift audio by given semitones using pyrubberband."""
    if abs(semitones) < 0.1:
        return y

    print(f"  [Harmonic Sync] Pitch-shifting by {semitones:+.1f} semitones")
    return pyrb.pitch_shift(y, sr, semitones)


def apply_butterworth_hpf(y, sr, cutoff=250, order=4):
    """
    Applies a professional Butterworth High-Pass Filter.
    Removes bass frequencies (<250Hz) to prevent muddy transitions.
    """
    nyquist = 0.5 * sr
    normal_cutoff = cutoff / nyquist
    b, a = scipy.signal.butter(order, normal_cutoff, btype='high', analog=False)
    return scipy.signal.lfilter(b, a, y)


def apply_butterworth_lpf(y, sr, cutoff=5000, order=4):
    """Applies a Butterworth Low-Pass Filter for filter sweep transitions."""
    nyquist = 0.5 * sr
    normal_cutoff = cutoff / nyquist
    b, a = scipy.signal.butter(order, normal_cutoff, btype='low', analog=False)
    return scipy.signal.lfilter(b, a, y)


def normalize_lufs(y, sr, target_lufs=-14.0):
    """Normalize audio to target LUFS."""
    if HAS_PYLOUDNORM:
        try:
            meter = pyln.Meter(sr)
            current_lufs = meter.integrated_loudness(y)
            
            if np.isinf(current_lufs) or np.isnan(current_lufs):
                return peak_normalize(y)

            gain_db = target_lufs - current_lufs
            gain_db = max(-20, min(20, gain_db)) # Safety clamp
            return pyln.normalize.loudness(y, current_lufs, target_lufs)
        except Exception:
            return peak_normalize(y)
    else:
        return peak_normalize(y)


def peak_normalize(y, target_db=-1.0):
    """Normalize audio to target peak level in dB."""
    peak = np.max(np.abs(y))
    if peak < 1e-6: return y
    target_linear = 10 ** (target_db / 20.0)
    return y * (target_linear / peak)


def get_key_semitone_diff(key1_idx, mode1, key2_idx, mode2):
    """Calculate semitone difference to transpose key1 to key2 using Camelot logic."""
    diff = (key2_idx - key1_idx) % 12
    if diff == 0: return 0 
    if diff == 3 and mode1 != mode2: return 0 # Relative major/minor
    if diff == 9 and mode1 != mode2: return 0 
    if diff == 7 or diff == 5: return 0 # Perfect 5th/4th
    
    if diff <= 6: return diff
    else: return diff - 12


def snap_to_tala_boundary(target_time, downbeat_times, beats_per_cycle):
    """
    Snap a time to the nearest Tala cycle boundary.
    Tala cycles span beats_per_cycle/4 downbeats (since downbeats are every 4 beats).
    Falls back to nearest downbeat if insufficient data.
    """
    if not downbeat_times or beats_per_cycle <= 0:
        return target_time

    downbeats_per_cycle = max(1, beats_per_cycle // 4)
    cycle_boundaries = downbeat_times[::downbeats_per_cycle]

    if not cycle_boundaries:
        return min(downbeat_times, key=lambda x: abs(x - target_time))

    return min(cycle_boundaries, key=lambda x: abs(x - target_time))


def get_cue_points(track_analysis):
    """Extract usable cue points from track analysis."""
    cue_points = track_analysis.get('dj_cue_points', {})
    mix_in = cue_points.get('mix_in', {}).get('time', 0)
    mix_out = cue_points.get('mix_out', {}).get('time')
    if mix_out is None:
        duration = track_analysis.get('duration', 180)
        mix_out = duration * 0.8
    return mix_in, mix_out


def get_pallavi_time(track_analysis):
    """Get the start time of the first Pallavi."""
    section_class = track_analysis.get('section_classification', {})
    pallavis = section_class.get('pallavis', [])
    if pallavis:
        return pallavis[0].get('start', None)
    return None


def select_transition_type(track1_analysis, track2_analysis, style='energetic'):
    """Select appropriate transition type based on track analysis and style."""
    energy1 = track1_analysis.get('energy', 0.5)
    energy2 = track2_analysis.get('energy', 0.5)
    energy_diff = energy2 - energy1
    vocals_overlap = (track1_analysis.get('has_vocals', False) and track2_analysis.get('has_vocals', False))

    if style == 'showcase':
        if energy_diff > 0.2: return 'bass_swap'
        elif energy_diff < -0.2: return 'echo_out'
        elif vocals_overlap: return 'filter_sweep'
        else: return 'crossfade'
    elif style == 'smooth':
        return 'filter_sweep' if vocals_overlap else 'crossfade'
    else:
        return 'bass_swap' if energy_diff > 0.15 else ('filter_sweep' if vocals_overlap else 'crossfade')


def calculate_transition_duration(track1_analysis, track2_analysis, target_bpm):
    """Calculate optimal transition duration in seconds."""
    bars = 4
    tala1 = track1_analysis.get('tala', {})
    tala2 = track2_analysis.get('tala', {})
    
    if tala1.get('tala_key') == tala2.get('tala_key'):
        bars = 8 
        
    if target_bpm > 0:
        return bars * (60.0 / target_bpm) * 4
    return 8.0


# Legacy helper for Pallavi Medley compatibility
def create_transition_segment(out_audio, in_audio, sr, transition_type='crossfade', duration_sec=4.0):
    duration_samples = int(duration_sec * sr)
    out_len = len(out_audio)
    in_len = len(in_audio)
    if out_len < duration_samples or in_len < duration_samples:
        duration_samples = min(out_len, in_len)

    out_segment = out_audio[-duration_samples:]
    in_segment = in_audio[:duration_samples]
    t = np.linspace(0, 1, duration_samples)

    if transition_type == 'bass_swap':
        out_hp = apply_butterworth_hpf(out_segment, sr, cutoff=250)
        transition = out_hp * (1-t) + in_segment * t

    elif transition_type == 'filter_sweep':
        num_chunks = 10
        chunk_size = duration_samples // num_chunks
        filtered_out = out_segment.copy()
        for c in range(num_chunks):
            c_start = c * chunk_size
            c_end = c_start + chunk_size if c < num_chunks - 1 else duration_samples
            cutoff = max(2000, 10000 - (c * 800))
            filtered_out[c_start:c_end] = apply_butterworth_lpf(
                out_segment[c_start:c_end], sr, cutoff
            )
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

    else:  # crossfade (default)
        fade_out = np.sqrt(1 - t)
        fade_in = np.sqrt(t)
        transition = out_segment * fade_out + in_segment * fade_in

    return np.clip(transition, -1.0, 1.0), duration_samples


# =============================================================================
# MAIN MIXER ENGINE
# =============================================================================

def create_sandalwood_mashup(tracks_analysis, mashup_plan, output_dir, target_lufs=-14.0, export_quality='high'):
    print("\n" + "="*60)
    print("SANDALWOOD PROFESSIONAL MIXER (PHASE ALIGNED + HARMONIC)")
    print("="*60)

    if len(tracks_analysis) < 2:
        raise ValueError("Need at least 2 tracks for a mashup")

    # 1. Setup Phase
    track_order = mashup_plan.get('track_order', [t['filename'] for t in tracks_analysis])
    style = mashup_plan.get('style', 'energetic')
    tracks_by_name = {t['filename']: t for t in tracks_analysis}
    
    bpms = [t.get('bpm', 120) for t in tracks_analysis if t.get('bpm', 0) > 0]
    target_bpm = np.median(bpms) if bpms else 120
    print(f"\nTarget BPM for Master Clock: {target_bpm:.1f}")

    sr = 44100
    processed_tracks = []

    # 2. Pre-processing Loop (Stretch, Pitch, Grid Mapping)
    print("\n--- Phase 1: Pre-processing (Time & Pitch) ---")
    for i, filename in enumerate(track_order):
        track_data = tracks_by_name.get(filename)
        if not track_data: continue
        
        # Load Audio
        file_path = track_data.get('file_path')
        if not file_path or not os.path.exists(file_path):
            print(f"Warning: File not found {filename}")
            continue
            
        print(f"[{i+1}/{len(track_order)}] Processing: {filename}")
        y, _ = librosa.load(file_path, sr=sr, mono=True)
        
        # --- BPM Sync ---
        original_bpm = track_data.get('bpm', target_bpm)
        ratio = target_bpm / original_bpm
        if abs(ratio - 1.0) > 0.02:
            y = time_stretch_audio(y, sr, original_bpm, target_bpm)
            
        # --- Harmonic Locking (CRITICAL FIX) ---
        if i > 0:
            prev_track_data = processed_tracks[-1]['analysis']
            shift_semitones = get_key_semitone_diff(
                prev_track_data['key'], prev_track_data['mode'],
                track_data['key'], track_data['mode']
            )
            
            if shift_semitones != 0:
                y = pitch_shift_audio(y, sr, shift_semitones)

        # Normalize Loudness
        y = normalize_lufs(y, sr, target_lufs)

        # --- Re-Map Beat Grid to New Tempo ---
        time_scale = 1.0 / ratio
        original_downbeats = track_data.get('beat_grid', {}).get('downbeat_times', [])
        synced_downbeats = [t * time_scale for t in original_downbeats]
        
        mix_in, mix_out = get_cue_points(track_data)
        synced_mix_in = mix_in * time_scale
        synced_mix_out = mix_out * time_scale

        processed_tracks.append({
            'filename': filename,
            'audio': y,
            'downbeats': synced_downbeats,
            'mix_in': synced_mix_in,
            'mix_out': synced_mix_out,
            'analysis': track_data
        })

    if len(processed_tracks) < 2:
        raise ValueError("Processing failed, not enough tracks.")

    # 3. Timeline Composition (Phase Alignment)
    print("\n--- Phase 2: Timeline Construction ---")
    
    total_samples_est = sum([len(t['audio']) for t in processed_tracks])
    mix_buffer = np.zeros(total_samples_est, dtype=np.float32)
    
    # Store placement info for the previous track to align the next one
    prev_placement = None 
    
    for i, track in enumerate(processed_tracks):
        audio = track['audio']
        
        if i == 0:
            # First track starts at 0
            start_index = 0
            
            # Simple fade in
            fade_in_len = int(0.05 * sr)
            if len(audio) > fade_in_len:
                audio[:fade_in_len] *= np.linspace(0, 1, fade_in_len)
            
            # Place in buffer
            mix_buffer[:len(audio)] += audio
            
            # Record placement for next iteration
            prev_placement = {
                'start_index': 0,
                'end_index': len(audio),
                'track': track
            }
            
        else:
            # --- PHASE ALIGNMENT ALGORITHM ---
            prev_track = prev_placement['track']
            
            # 1. Identify "Global Handoff Point" (Tala boundary near mix_out of prev track)
            prev_mix_out = prev_track['mix_out']
            prev_tala = prev_track['analysis'].get('tala', {})
            prev_beats_per_cycle = prev_tala.get('beats_per_cycle', 4)

            if prev_track['downbeats']:
                prev_exit_beat_local_time = snap_to_tala_boundary(
                    prev_mix_out, prev_track['downbeats'], prev_beats_per_cycle
                )
            else:
                prev_exit_beat_local_time = prev_mix_out

            prev_exit_beat_sample_local = int(prev_exit_beat_local_time * sr)
            global_handoff_sample = prev_placement['start_index'] + prev_exit_beat_sample_local

            # 2. Identify "Pickup Point" (Tala boundary near mix_in of current track)
            curr_mix_in = track['mix_in']
            curr_tala = track['analysis'].get('tala', {})
            curr_beats_per_cycle = curr_tala.get('beats_per_cycle', 4)

            if track['downbeats']:
                curr_entry_beat_local_time = snap_to_tala_boundary(
                    curr_mix_in, track['downbeats'], curr_beats_per_cycle
                )
            else:
                curr_entry_beat_local_time = curr_mix_in
                
            curr_entry_beat_sample_local = int(curr_entry_beat_local_time * sr)
            
            # 3. Calculate Start Index
            # We want: global_handoff_sample == start_index + curr_entry_beat_sample_local
            start_index = global_handoff_sample - curr_entry_beat_sample_local
            start_index = max(0, start_index) # Safety
            
            print(f"  Aligning {track['filename']}...")
            print(f"    Target Beat (Timeline): {global_handoff_sample/sr:.2f}s")
            print(f"    Source Beat (Local):    {curr_entry_beat_local_time:.2f}s")
            print(f"    Shifted Start:          {start_index/sr:.2f}s")
            
            # --- TRANSITION SELECTION ---
            prev_analysis = prev_track['analysis']
            curr_analysis = track['analysis']
            transition_type = select_transition_type(prev_analysis, curr_analysis, style)
            trans_duration_sec = calculate_transition_duration(prev_analysis, curr_analysis, target_bpm)
            trans_len_samples = int(trans_duration_sec * sr)

            print(f"    Transition: {transition_type} ({trans_duration_sec:.1f}s)")

            # --- APPLY TRANSITION to outgoing track in buffer ---
            overlap_end = min(start_index + trans_len_samples, len(mix_buffer), prev_placement['end_index'])

            if start_index < overlap_end:
                segment_len = overlap_end - start_index
                segment = mix_buffer[start_index:overlap_end].copy()
                t = np.linspace(0, 1, segment_len)

                if transition_type == 'bass_swap':
                    filtered = apply_butterworth_hpf(segment, sr, cutoff=250)
                    mix_buffer[start_index:overlap_end] = segment * (1 - t) + filtered * t

                elif transition_type == 'filter_sweep':
                    num_chunks = 10
                    chunk_size = segment_len // num_chunks
                    for c in range(num_chunks):
                        c_start = c * chunk_size
                        c_end = c_start + chunk_size if c < num_chunks - 1 else segment_len
                        cutoff = max(2000, 10000 - (c * 800))
                        chunk = segment[c_start:c_end]
                        mix_buffer[start_index + c_start:start_index + c_end] = apply_butterworth_lpf(
                            chunk, sr, cutoff
                        )

                elif transition_type == 'echo_out':
                    delay_samples = int(0.25 * sr)
                    decayed = segment.copy()
                    for tap in range(1, 5):
                        offset = tap * delay_samples
                        decay = 0.6 ** tap
                        if offset < segment_len:
                            decayed[offset:] += segment[:segment_len - offset] * decay
                    decayed = np.clip(decayed, -1.0, 1.0)
                    mix_buffer[start_index:overlap_end] = decayed * (1 - t)

                else:  # crossfade
                    mix_buffer[start_index:overlap_end] = segment * np.sqrt(1 - t)

            # 4. Add the new track
            end_index = start_index + len(audio)

            # Expand buffer if needed
            if end_index > len(mix_buffer):
                pad = np.zeros(end_index - len(mix_buffer))
                mix_buffer = np.concatenate([mix_buffer, pad])

            # Fade in the new track
            fade_in_len = min(trans_len_samples, len(audio))
            if fade_in_len > 0:
                if transition_type == 'crossfade':
                    fade_in_curve = np.sqrt(np.linspace(0, 1, fade_in_len))
                else:
                    fade_in_curve = np.linspace(0, 1, fade_in_len)
                audio[:fade_in_len] *= fade_in_curve
                
            # Mix (Sum)
            mix_buffer[start_index:end_index] += audio
            
            # Update placement
            prev_placement = {
                'start_index': start_index,
                'end_index': end_index,
                'track': track
            }

    # 4. Final Polish
    print("\n--- Phase 3: Mastering ---")
    # Trim silence
    non_zeros = np.nonzero(mix_buffer)[0]
    if len(non_zeros) > 0:
        mix_buffer = mix_buffer[non_zeros[0]:non_zeros[-1]]
        
    final_audio = normalize_lufs(mix_buffer, sr, target_lufs)
    final_audio = np.clip(final_audio, -0.99, 0.99)

    # 5. Export
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if export_quality == 'high':
        output_filename = f"sandalwood_mashup_{style}_{timestamp}.mp3"
        bitrate = "320k"
    else:
        output_filename = f"sandalwood_mashup_{style}_{timestamp}.mp3"
        bitrate = "256k"
        
    output_path = os.path.join(output_dir, output_filename)

    print(f"Exporting: {output_filename} ({len(final_audio)/sr:.1f}s, {bitrate})")
    tmp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    try:
        sf.write(tmp_wav.name, final_audio, sr)
        audio_segment = AudioSegment.from_wav(tmp_wav.name)
        audio_segment.export(output_path, format="mp3", bitrate=bitrate)
    finally:
        os.unlink(tmp_wav.name)

    print("Mashup Creation Successful!")
    return output_path


def create_pallavi_medley(tracks_analysis, output_dir, target_lufs=-14.0):
    """
    Create a Pallavi-to-Pallavi medley (Original sequential logic preserved).
    """
    print("\n" + "="*60)
    print("PALLAVI MEDLEY CREATOR")
    print("="*60)

    sr = 44100
    pallavi_segments = []

    for track in tracks_analysis:
        pallavi_time = get_pallavi_time(track)
        if pallavi_time is None:
            hooks = track.get('hooks_drops', {}).get('hooks', [])
            if hooks: pallavi_time = hooks[0].get('time', None)

        if pallavi_time is None:
            print(f"  No Pallavi found for {track['filename']}, skipping")
            continue

        file_path = track.get('file_path')
        if not file_path or not os.path.exists(file_path): continue

        y, _ = librosa.load(file_path, sr=sr, mono=True)
        pallavi_sample = int(pallavi_time * sr)
        segment_duration = 30 * sr 
        start = max(0, pallavi_sample - int(5 * sr))
        end = min(len(y), start + segment_duration)
        segment = y[start:end]

        # Time-stretch to common BPM (128)
        track_bpm = track.get('bpm', 120)
        target_bpm = 128
        if abs(track_bpm - target_bpm) > 3:
            segment = time_stretch_audio(segment, sr, track_bpm, target_bpm)

        segment = normalize_lufs(segment, sr, target_lufs)
        pallavi_segments.append({'filename': track['filename'], 'audio': segment})
        print(f"  Extracted Pallavi from {track['filename']} at {pallavi_time:.1f}s")

    if len(pallavi_segments) < 2:
        raise ValueError("Need at least 2 tracks with Pallavi sections")

    final_audio = pallavi_segments[0]['audio']
    for i in range(1, len(pallavi_segments)):
        segment = pallavi_segments[i]['audio']
        trans_duration = 2.0
        transition, trans_samples = create_transition_segment(
            final_audio, segment, sr, 'crossfade', trans_duration
        )
        main_part = final_audio[:-trans_samples]
        rest = segment[trans_samples:]
        final_audio = np.concatenate([main_part, transition, rest])

    # Export
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"pallavi_medley_{timestamp}.mp3"
    output_path = os.path.join(output_dir, output_filename)

    tmp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    try:
        sf.write(tmp_wav.name, final_audio, sr)
        audio_segment = AudioSegment.from_wav(tmp_wav.name)
        audio_segment.export(output_path, format="mp3", bitrate="320k")
    finally:
        os.unlink(tmp_wav.name)

    print(f"\nPallavi Medley created: {output_filename}")
    return output_path


if __name__ == "__main__":
    print("Sandalwood Mixer - Professional Kannada Mashup Engine")
    print("Use via web_server.py or import create_sandalwood_mashup()")
