# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# sandalwood_mixer.py
# Professional Sandalwood/Kannada mashup mixer with BPM sync, beat alignment,
# LUFS normalization, and Tala-aware transitions.

import os
import tempfile
import shutil
import numpy as np
import librosa
import soundfile as sf
import pyrubberband as pyrb
from datetime import datetime
from pydub import AudioSegment
from pydub.effects import normalize as pydub_normalize

# Try to import pyloudnorm for LUFS normalization
try:
    import pyloudnorm as pyln
    HAS_PYLOUDNORM = True
except ImportError:
    HAS_PYLOUDNORM = False
    print("Warning: pyloudnorm not installed. Using peak normalization instead.")


def time_stretch_audio(y, sr, source_bpm, target_bpm):
    """
    Time-stretch audio to match target BPM using pyrubberband.
    Returns stretched audio at the same sample rate.
    """
    if source_bpm <= 0 or target_bpm <= 0:
        return y

    # Limit stretch ratio to avoid extreme artifacts
    ratio = target_bpm / source_bpm
    if ratio < 0.5 or ratio > 2.0:
        print(f"  Warning: BPM ratio {ratio:.2f} is extreme, limiting to 0.5-2.0 range")
        ratio = max(0.5, min(2.0, ratio))

    if abs(ratio - 1.0) < 0.02:  # Less than 2% difference, skip
        return y

    print(f"  Time-stretching: {source_bpm:.1f} BPM -> {target_bpm:.1f} BPM (ratio: {ratio:.3f})")
    return pyrb.time_stretch(y, sr, ratio)


def pitch_shift_audio(y, sr, semitones):
    """
    Pitch-shift audio by given semitones using pyrubberband.
    """
    if abs(semitones) < 0.1:  # Less than 0.1 semitone, skip
        return y

    print(f"  Pitch-shifting by {semitones:+.1f} semitones")
    return pyrb.pitch_shift(y, sr, semitones)


def normalize_lufs(y, sr, target_lufs=-14.0):
    """
    Normalize audio to target LUFS (Loudness Units Full Scale).
    YouTube recommends -14 LUFS for uploaded content.
    Falls back to peak normalization if pyloudnorm is not available.
    """
    if HAS_PYLOUDNORM:
        meter = pyln.Meter(sr)
        current_lufs = meter.integrated_loudness(y)

        if np.isinf(current_lufs) or np.isnan(current_lufs):
            print("  Warning: Could not measure LUFS, using peak normalization")
            return peak_normalize(y)

        gain_db = target_lufs - current_lufs
        # Limit gain to avoid extreme amplification
        gain_db = max(-20, min(20, gain_db))

        print(f"  LUFS normalization: {current_lufs:.1f} -> {target_lufs:.1f} (gain: {gain_db:+.1f} dB)")
        y_normalized = pyln.normalize.loudness(y, current_lufs, target_lufs)
        return y_normalized
    else:
        return peak_normalize(y)


def peak_normalize(y, target_db=-1.0):
    """
    Normalize audio to target peak level in dB.
    """
    peak = np.max(np.abs(y))
    if peak < 1e-6:
        return y

    target_linear = 10 ** (target_db / 20.0)
    return y * (target_linear / peak)


def get_key_semitone_diff(key1, mode1, key2, mode2):
    """
    Calculate semitone difference to transpose key1 to key2.
    Uses Circle of Fifths for harmonic compatibility.
    Returns 0 if keys are compatible, otherwise the shift needed.
    """
    # Key indices: 0=C, 1=C#, 2=D, ..., 11=B

    # Compatible keys (no shift needed):
    # - Same key
    # - Relative major/minor (3 semitones apart)
    # - Perfect 4th/5th (5 or 7 semitones)

    diff = (key2 - key1) % 12

    # Check if already compatible
    if diff == 0:  # Same key
        return 0
    if diff == 3 and mode1 != mode2:  # Relative major/minor
        return 0
    if diff == 9 and mode1 != mode2:  # Relative (other direction)
        return 0
    if diff == 5 or diff == 7:  # Perfect 4th/5th
        return 0

    # Find closest compatible key
    # Prefer shifting by perfect 4th/5th
    if diff <= 6:
        return -diff if diff <= 2 else (5 - diff)
    else:
        return 12 - diff if (12 - diff) <= 2 else (7 - (12 - diff))


def find_nearest_beat(time_sec, beat_times, tolerance=0.1):
    """
    Find the nearest beat to a given time.
    Returns the beat time and index.
    """
    if not len(beat_times):
        return time_sec, -1

    diffs = np.abs(np.array(beat_times) - time_sec)
    idx = np.argmin(diffs)

    if diffs[idx] <= tolerance:
        return beat_times[idx], idx
    return time_sec, -1


def snap_to_tala_boundary(time_sec, tala_info, beat_times):
    """
    Snap a time to the nearest Tala cycle boundary.
    For Adi Tala (8 beats), snaps to every 8th beat.
    """
    if not tala_info or not len(beat_times):
        return time_sec

    beats_per_cycle = tala_info.get('beats_per_cycle', 8)

    # Find the nearest beat
    _, beat_idx = find_nearest_beat(time_sec, beat_times)
    if beat_idx < 0:
        return time_sec

    # Find nearest Tala boundary (start of cycle)
    cycle_position = beat_idx % beats_per_cycle

    if cycle_position <= beats_per_cycle // 2:
        # Snap backwards to cycle start
        boundary_idx = beat_idx - cycle_position
    else:
        # Snap forwards to next cycle start
        boundary_idx = beat_idx + (beats_per_cycle - cycle_position)

    if 0 <= boundary_idx < len(beat_times):
        return beat_times[boundary_idx]

    return time_sec


def create_transition_segment(out_audio, in_audio, sr, transition_type='crossfade', duration_sec=4.0):
    """
    Create a professional transition between two audio segments.

    Types:
    - crossfade: Standard equal-power crossfade
    - bass_swap: High-pass outgoing, bring in full incoming
    - filter_sweep: Low-pass sweep on outgoing
    - echo_out: Add delay/reverb tail on outgoing
    """
    duration_samples = int(duration_sec * sr)

    # Ensure we have enough audio
    out_len = len(out_audio)
    in_len = len(in_audio)

    if out_len < duration_samples or in_len < duration_samples:
        duration_samples = min(out_len, in_len)

    out_segment = out_audio[-duration_samples:]
    in_segment = in_audio[:duration_samples]

    # Create fade curves
    t = np.linspace(0, 1, duration_samples)

    if transition_type == 'crossfade':
        # Equal-power crossfade
        fade_out = np.sqrt(1 - t)
        fade_in = np.sqrt(t)
        transition = out_segment * fade_out + in_segment * fade_in

    elif transition_type == 'bass_swap':
        # High-pass filter the outgoing track to remove bass
        # Simple approximation using librosa
        out_hp = librosa.effects.preemphasis(out_segment, coef=0.97)
        fade_out = 1 - t
        fade_in = t
        transition = out_hp * fade_out + in_segment * fade_in

    elif transition_type == 'filter_sweep':
        # Gradual low-pass on outgoing
        # Simulate by reducing high frequencies progressively
        transition = np.zeros(duration_samples)
        chunk_size = duration_samples // 10
        for i in range(10):
            start = i * chunk_size
            end = start + chunk_size
            # Reduce high frequencies more as we progress
            coef = 0.9 - (i * 0.08)
            chunk = librosa.effects.preemphasis(out_segment[start:end], coef=max(0.1, coef))
            transition[start:end] = chunk * (1 - t[start:end]) + in_segment[start:end] * t[start:end]

    elif transition_type == 'echo_out':
        # Add reverb-like tail using simple delay
        fade_out = np.sqrt(1 - t)
        fade_in = np.sqrt(t)

        # Create echo (simple delay at 0.25s intervals)
        echo_segment = out_segment.copy()
        delay_samples = int(0.25 * sr)
        for delay_mult in [1, 2, 3]:
            delay = delay_samples * delay_mult
            if delay < duration_samples:
                gain = 0.5 ** delay_mult
                echo_segment[delay:] += out_segment[:-delay] * gain

        echo_segment = np.clip(echo_segment, -1.0, 1.0)
        transition = echo_segment * fade_out + in_segment * fade_in

    else:
        # Default to crossfade
        fade_out = 1 - t
        fade_in = t
        transition = out_segment * fade_out + in_segment * fade_in

    return np.clip(transition, -1.0, 1.0), duration_samples


def select_transition_type(track1_analysis, track2_analysis, style='energetic'):
    """
    Select appropriate transition type based on track analysis and style.
    """
    energy1 = track1_analysis.get('energy', 0.5)
    energy2 = track2_analysis.get('energy', 0.5)
    energy_diff = energy2 - energy1

    # Check if both have vocals in transition region
    vocals_overlap = (track1_analysis.get('has_vocals', False) and
                      track2_analysis.get('has_vocals', False))

    if style == 'showcase':
        # Pro style: more variety
        if energy_diff > 0.2:
            return 'bass_swap'  # Building energy
        elif energy_diff < -0.2:
            return 'echo_out'  # Dropping energy
        elif vocals_overlap:
            return 'filter_sweep'  # Avoid vocal clash
        else:
            return 'crossfade'

    elif style == 'smooth':
        # Smooth style: gentle transitions
        if vocals_overlap:
            return 'filter_sweep'
        return 'crossfade'

    else:  # energetic
        if energy_diff > 0.15:
            return 'bass_swap'
        elif vocals_overlap:
            return 'filter_sweep'
        return 'crossfade'


def calculate_transition_duration(track1_analysis, track2_analysis, target_bpm):
    """
    Calculate optimal transition duration in seconds.
    Aims for 4-8 bars depending on track characteristics.
    """
    # Base: 4 bars
    bars = 4

    # Extend to 8 bars if:
    # - Both tracks have clear structure
    # - Energy levels are similar
    # - Tala cycles match

    tala1 = track1_analysis.get('tala', {})
    tala2 = track2_analysis.get('tala', {})

    if tala1.get('tala_key') == tala2.get('tala_key'):
        bars = 8  # Full Tala cycle transition

    energy_diff = abs(track1_analysis.get('energy', 0.5) - track2_analysis.get('energy', 0.5))
    if energy_diff > 0.3:
        bars = max(4, bars - 2)  # Shorter transition for energy jumps

    # Convert bars to seconds
    if target_bpm > 0:
        seconds_per_beat = 60.0 / target_bpm
        seconds_per_bar = seconds_per_beat * 4  # Assuming 4/4
        return bars * seconds_per_bar

    return 8.0  # Default 8 seconds


def get_cue_points(track_analysis):
    """
    Extract usable cue points from track analysis.
    Returns mix_in and mix_out times in seconds.
    """
    cue_points = track_analysis.get('dj_cue_points', {})

    mix_in = cue_points.get('mix_in', {}).get('time', 0)
    mix_out = cue_points.get('mix_out', {}).get('time')

    if mix_out is None:
        # Fallback: 80% of track duration
        duration = track_analysis.get('duration', 180)
        mix_out = duration * 0.8

    return mix_in, mix_out


def get_pallavi_time(track_analysis):
    """
    Get the start time of the first Pallavi (chorus) section.
    Returns None if not detected.
    """
    section_class = track_analysis.get('section_classification', {})
    pallavis = section_class.get('pallavis', [])

    if pallavis:
        return pallavis[0].get('start', None)
    return None


def create_sandalwood_mashup(
    tracks_analysis,
    mashup_plan,
    output_dir,
    target_lufs=-14.0,
    export_quality='high'
):
    """
    Create a professional Sandalwood mashup from analyzed tracks.

    Args:
        tracks_analysis: List of track analysis dictionaries from kannada_mashup_analyzer
        mashup_plan: Mashup plan from plan_kannada_mashup()
        output_dir: Directory to save output
        target_lufs: Target loudness in LUFS (-14 recommended for YouTube)
        export_quality: 'high' (320kbps) or 'standard' (256kbps)

    Returns:
        Path to the created mashup file
    """
    print("\n" + "="*60)
    print("SANDALWOOD PROFESSIONAL MIXER")
    print("="*60)

    if len(tracks_analysis) < 2:
        raise ValueError("Need at least 2 tracks for a mashup")

    # Get track order from plan
    track_order = mashup_plan.get('track_order', [t['filename'] for t in tracks_analysis])
    style = mashup_plan.get('style', 'energetic')

    # Create lookup by filename
    tracks_by_name = {t['filename']: t for t in tracks_analysis}

    # Determine target BPM (median of all tracks)
    bpms = [t.get('bpm', 120) for t in tracks_analysis if t.get('bpm', 0) > 0]
    target_bpm = np.median(bpms) if bpms else 120
    print(f"\nTarget BPM: {target_bpm:.1f}")

    # Process each track
    processed_tracks = []
    sr = 44100  # Standard sample rate

    print("\n--- Phase 1: Loading and Pre-processing Tracks ---")

    for i, filename in enumerate(track_order):
        track = tracks_by_name.get(filename)
        if not track:
            print(f"Warning: Track {filename} not found in analysis, skipping")
            continue

        file_path = track.get('file_path')
        if not file_path or not os.path.exists(file_path):
            print(f"Warning: File not found for {filename}, skipping")
            continue

        print(f"\n[{i+1}/{len(track_order)}] Processing: {filename}")

        # Load audio
        y, orig_sr = librosa.load(file_path, sr=sr, mono=True)
        print(f"  Loaded: {len(y)/sr:.1f}s at {sr}Hz")

        # Get cue points
        mix_in, mix_out = get_cue_points(track)
        print(f"  Cue points: mix_in={mix_in:.1f}s, mix_out={mix_out:.1f}s")

        # Time-stretch to target BPM
        track_bpm = track.get('bpm', target_bpm)
        if abs(track_bpm - target_bpm) > 2:  # More than 2 BPM difference
            y = time_stretch_audio(y, sr, track_bpm, target_bpm)

            # Adjust cue points for new tempo
            tempo_ratio = target_bpm / track_bpm
            mix_in = mix_in / tempo_ratio
            mix_out = mix_out / tempo_ratio

        # Normalize loudness
        y = normalize_lufs(y, sr, target_lufs)

        # Store processed track
        processed_tracks.append({
            'filename': filename,
            'audio': y,
            'sr': sr,
            'mix_in': mix_in,
            'mix_out': mix_out,
            'analysis': track,
            'bpm': target_bpm,  # Now synced
        })

    if len(processed_tracks) < 2:
        raise ValueError("Not enough valid tracks to create mashup")

    print("\n--- Phase 2: Creating Mashup with Transitions ---")

    # Build the mashup
    final_audio = None

    for i, track in enumerate(processed_tracks):
        y = track['audio']
        mix_in = track['mix_in']
        mix_out = track['mix_out']
        analysis = track['analysis']

        # Convert times to samples
        mix_in_sample = int(mix_in * sr)
        mix_out_sample = int(mix_out * sr)

        # Ensure valid range
        mix_in_sample = max(0, min(mix_in_sample, len(y) - sr))
        mix_out_sample = max(mix_in_sample + sr, min(mix_out_sample, len(y)))

        # Extract the usable segment
        segment = y[mix_in_sample:mix_out_sample]

        print(f"\n[{i+1}] {track['filename']}")
        print(f"    Using segment: {mix_in:.1f}s - {mix_out:.1f}s ({len(segment)/sr:.1f}s)")

        if final_audio is None:
            # First track
            final_audio = segment
        else:
            # Create transition
            prev_track = processed_tracks[i-1]

            # Select transition type
            trans_type = select_transition_type(prev_track['analysis'], analysis, style)

            # Calculate transition duration
            trans_duration = calculate_transition_duration(prev_track['analysis'], analysis, target_bpm)

            print(f"    Transition: {trans_type} ({trans_duration:.1f}s)")

            # Create the transition
            transition, trans_samples = create_transition_segment(
                final_audio, segment, sr,
                transition_type=trans_type,
                duration_sec=trans_duration
            )

            # Combine: main part of previous + transition + rest of current
            main_part = final_audio[:-trans_samples]
            rest_of_current = segment[trans_samples:]

            final_audio = np.concatenate([main_part, transition, rest_of_current])

    # Final normalization
    print("\n--- Phase 3: Final Processing ---")
    final_audio = normalize_lufs(final_audio, sr, target_lufs)

    # Prevent clipping
    final_audio = np.clip(final_audio, -0.99, 0.99)

    # Export
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if export_quality == 'high':
        output_filename = f"sandalwood_mashup_{style}_{timestamp}.mp3"
        bitrate = "320k"
    else:
        output_filename = f"sandalwood_mashup_{style}_{timestamp}.mp3"
        bitrate = "256k"

    output_path = os.path.join(output_dir, output_filename)

    # Convert to pydub for MP3 export
    print(f"\nExporting: {output_filename}")
    print(f"  Duration: {len(final_audio)/sr:.1f}s")
    print(f"  Quality: {bitrate}")

    # Write to temp WAV first
    tmp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    try:
        sf.write(tmp_wav.name, final_audio, sr)

        # Convert to MP3
        audio_segment = AudioSegment.from_wav(tmp_wav.name)
        audio_segment.export(output_path, format="mp3", bitrate=bitrate)

    finally:
        os.unlink(tmp_wav.name)

    print(f"\n{'='*60}")
    print(f"MASHUP COMPLETE: {output_filename}")
    print(f"{'='*60}")

    return output_path


def create_pallavi_medley(tracks_analysis, output_dir, target_lufs=-14.0):
    """
    Create a Pallavi-to-Pallavi medley - the signature Sandalwood mashup style.
    Extracts Pallavi (chorus) sections and blends them together.

    This is what makes Kannada film medleys special - transitioning
    directly between the catchiest parts of each song.
    """
    print("\n" + "="*60)
    print("PALLAVI MEDLEY CREATOR")
    print("="*60)

    sr = 44100
    pallavi_segments = []

    for track in tracks_analysis:
        pallavi_time = get_pallavi_time(track)
        if pallavi_time is None:
            # Try to use first hook/drop as fallback
            hooks = track.get('hooks_drops', {}).get('hooks', [])
            if hooks:
                pallavi_time = hooks[0].get('time', None)

        if pallavi_time is None:
            print(f"  No Pallavi found for {track['filename']}, skipping")
            continue

        file_path = track.get('file_path')
        if not file_path or not os.path.exists(file_path):
            continue

        # Load audio
        y, _ = librosa.load(file_path, sr=sr, mono=True)

        # Extract ~30 seconds around the Pallavi
        pallavi_sample = int(pallavi_time * sr)
        segment_duration = 30 * sr  # 30 seconds

        start = max(0, pallavi_sample - int(5 * sr))  # 5 sec before
        end = min(len(y), start + segment_duration)

        segment = y[start:end]

        # Time-stretch to common BPM
        track_bpm = track.get('bpm', 120)
        target_bpm = 128  # Standard for medleys
        if abs(track_bpm - target_bpm) > 3:
            segment = time_stretch_audio(segment, sr, track_bpm, target_bpm)

        segment = normalize_lufs(segment, sr, target_lufs)

        pallavi_segments.append({
            'filename': track['filename'],
            'audio': segment,
            'analysis': track
        })

        print(f"  Extracted Pallavi from {track['filename']} at {pallavi_time:.1f}s")

    if len(pallavi_segments) < 2:
        raise ValueError("Need at least 2 tracks with Pallavi sections")

    # Create the medley with quick transitions
    final_audio = pallavi_segments[0]['audio']

    for i in range(1, len(pallavi_segments)):
        segment = pallavi_segments[i]['audio']

        # Quick 2-second crossfade for medley style
        trans_duration = 2.0
        transition, trans_samples = create_transition_segment(
            final_audio, segment, sr,
            transition_type='crossfade',
            duration_sec=trans_duration
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
