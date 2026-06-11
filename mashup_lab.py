# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# mashup_lab.py
# Mashup Lab: true vocal-over-instrumental mashups (the "Cocktail Mashup"
# formula): take the VOICE of one song, lay it over the MUSIC of another,
# tempo-locked, key-locked, beat-aligned, ducked and mastered.
#
# Three style presets model the signature Sandalwood reference mixes:
#   divine         - devotional blend: long fades, vocal reverb, gentle ducking
#   cocktail_party - party mashup: punchy entries, deeper ducking, hot vocals
#   club_remix     - club energy: filtered intro sweep, pre-vocal drop, loud
# -----------------------------------------------------------------------------

import os
import numpy as np
import librosa
from datetime import datetime

from audio_utils import export_audio, db_to_gain
from stem_separation import separate_stems_best
from sandalwood_mixer import (
    time_stretch_audio,
    pitch_shift_pro,
    dynamic_sidechain_ducking,
    apply_master_bus_glue,
    get_key_semitone_diff,
    snap_to_tala_boundary,
    detect_shruti_tuning,
    apply_butterworth_hpf,
    apply_butterworth_lpf,
)

try:
    from pedalboard import Pedalboard, Reverb
    HAS_REVERB = True
except ImportError:
    HAS_REVERB = False


STYLE_PRESETS = {
    'divine': {
        'label': 'Divine Mashup',
        'duck_db': -3.0,
        'vocal_reverb': {'room_size': 0.6, 'wet_level': 0.22},
        'entry_fade_bars': 2.0,
        'exit_fade_bars': 2.0,
        'drop_silence_beats': 0,
        'lpf_intro_sweep': False,
        'vocal_gain_db': 1.0,
        'target_lufs': -14.0,
    },
    'cocktail_party': {
        'label': 'Cocktail Party',
        'duck_db': -4.5,
        'vocal_reverb': None,
        'entry_fade_bars': 0.5,
        'exit_fade_bars': 1.0,
        'drop_silence_beats': 0,
        'lpf_intro_sweep': False,
        'vocal_gain_db': 1.5,
        'target_lufs': -14.0,
    },
    'club_remix': {
        'label': 'Club Remix',
        'duck_db': -5.0,
        'vocal_reverb': None,
        'entry_fade_bars': 0.25,
        'exit_fade_bars': 0.5,
        'drop_silence_beats': 2,
        'lpf_intro_sweep': True,
        'vocal_gain_db': 1.0,
        'target_lufs': -13.5,
    },
}


def normalize_tempo_ratio(vocal_bpm, backing_bpm):
    """Fold half/double-time so the vocal stretch ratio stays musical.

    A 150 BPM vocal over a 75 BPM beat is the SAME groove (double-time), so we
    fold the vocal BPM to whichever of (0.5x, 1x, 2x) sits closest to the
    backing tempo before computing the stretch ratio.

    Returns:
        (effective_vocal_bpm, ratio) where ratio = backing_bpm / effective_vocal_bpm
    """
    if vocal_bpm <= 0 or backing_bpm <= 0:
        return max(vocal_bpm, 1), 1.0
    effective = min((vocal_bpm * m for m in (0.5, 1.0, 2.0)),
                    key=lambda b: abs(b - backing_bpm))
    return effective, backing_bpm / effective


def choose_semitone_shift(vocal_key, vocal_mode, backing_key, backing_mode):
    """Semitones to shift the VOCALS so they sit in (or next to) the backing key.

    Reuses the project's harmonic logic (relative major/minor and 4th/5th
    relationships count as already-compatible = 0 shift). Shifts larger than
    ±3 semitones strain even formant-preserved vocals, so those are folded to
    the Camelot-adjacent key (a perfect 4th/5th from the backing) instead.
    """
    diff = get_key_semitone_diff(vocal_key, vocal_mode, backing_key, backing_mode)
    if diff == 0:
        return 0
    if abs(diff) > 3:
        alt = diff - 7 if diff > 0 else diff + 7
        diff = alt if abs(alt) <= 3 else int(np.clip(diff, -3, 3))
    return int(diff)


def extract_vocal_phrases(vocal_analysis, time_scale=1.0):
    """Pull sung phrases (start/end seconds) out of a track's deep analysis.

    Primary source: pallavi/charanam sections intersected with detected vocal
    regions. Falls back to raw vocal regions, then (when Demucs never ran and
    vocal_regions is empty) to the song's 8-bar phrase grid across the middle
    80% of the track — so Mashup Lab still works with no separation model.

    Times are multiplied by time_scale to follow the tempo-locked vocals.
    """
    duration = vocal_analysis.get('duration', 0) or 0
    bar_sec = (vocal_analysis.get('phrases') or {}).get('bar_duration_sec') or 2.0
    sections = (vocal_analysis.get('sections') or {}).get('sections') or []
    vocal_regions = vocal_analysis.get('vocal_regions') or []

    phrases = []
    sung_sections = [s for s in sections
                     if s.get('has_vocals') and s.get('section_type') in ('pallavi', 'charanam')]
    if sung_sections and vocal_regions:
        for sec in sung_sections:
            for region in vocal_regions:
                start = max(sec['start'], region['start'])
                end = min(sec['end'], region['end'])
                if end - start >= 2.0:
                    phrases.append({'start': start, 'end': end,
                                    'section_type': sec['section_type'],
                                    'energy': sec.get('energy', 0.5)})
    elif vocal_regions:
        for region in vocal_regions:
            if region['end'] - region['start'] >= 2.0:
                phrases.append({'start': region['start'], 'end': region['end'],
                                'section_type': 'vocal', 'energy': 0.5})

    if not phrases and duration > 0:
        body_start, body_end = duration * 0.1, duration * 0.9
        grid = [t for t in (vocal_analysis.get('phrases') or {}).get('8_bar_phrases') or []
                if body_start <= t <= body_end]
        if len(grid) >= 2:
            for a, b in zip(grid[:-1], grid[1:]):
                phrases.append({'start': a, 'end': b, 'section_type': 'phrase', 'energy': 0.5})
        else:
            phrases.append({'start': body_start, 'end': body_end,
                            'section_type': 'full', 'energy': 0.5})

    phrases.sort(key=lambda p: p['start'])
    merged = []
    for p in phrases:
        if merged and p['start'] - merged[-1]['end'] < bar_sec:
            merged[-1]['end'] = max(merged[-1]['end'], p['end'])
        else:
            merged.append(dict(p))

    for p in merged:
        p['start'] *= time_scale
        p['end'] *= time_scale
    return merged


def plan_vocal_placement(vocal_phrases, backing_analysis, preset):
    """Map vocal phrases onto the backing track's beat grid.

    The first phrase lands on the backing's primary hook (or 8 bars in), every
    phrase start snaps to a tala-cycle downbeat, and the vocal track's own
    gaps between phrases are preserved as backing-only stretches (natural
    builds and breakdowns).
    """
    if not vocal_phrases:
        return []

    beat_grid = backing_analysis.get('beat_grid') or {}
    downbeats = beat_grid.get('downbeat_times') or []
    beats_per_cycle = (backing_analysis.get('tala') or {}).get('beats_per_cycle', 4)
    bpm = backing_analysis.get('bpm') or 120
    bar_sec = 4 * 60.0 / bpm
    backing_dur = backing_analysis.get('duration', 0) or 0

    first_downbeat = beat_grid.get('first_downbeat', 0) or 0
    anchor = first_downbeat + 8 * bar_sec
    hook = (backing_analysis.get('hooks_and_drops') or {}).get('primary_hook') or {}
    hook_time = hook.get('time', hook.get('start'))
    if hook_time is not None and 4 * bar_sec <= hook_time <= backing_dur * 0.5:
        anchor = hook_time
    anchor = snap_to_tala_boundary(anchor, downbeats, beats_per_cycle)

    placements = []
    base_offset = anchor - vocal_phrases[0]['start']
    prev_end = 0.0
    for phrase in vocal_phrases:
        start = snap_to_tala_boundary(phrase['start'] + base_offset, downbeats, beats_per_cycle)
        if start < prev_end + 0.5 * bar_sec:
            continue  # snapped onto the previous phrase — skip rather than overlap
        duration = phrase['end'] - phrase['start']
        if backing_dur and start + 2.0 > backing_dur - 3.0:
            break  # keep the backing outro vocal-free
        end = min(start + duration, backing_dur - 1.0) if backing_dur else start + duration
        fade_in = min(preset['entry_fade_bars'] * bar_sec, (end - start) * 0.3)
        fade_out = min(preset['exit_fade_bars'] * bar_sec, (end - start) * 0.3)
        placements.append({
            'timeline_start_sec': float(start),
            'vocal_start_sec': float(phrase['start']),
            'vocal_end_sec': float(phrase['start'] + (end - start)),
            'fade_in_sec': float(fade_in),
            'fade_out_sec': float(fade_out),
            'section_type': phrase.get('section_type', 'vocal'),
        })
        prev_end = end
    return placements


def _load_instrumental_bus(separation, master_audio, sr):
    """Build the music-only bus from whatever the separator produced."""
    if not separation:
        return master_audio.copy(), False
    stems = separation['stems']
    if 'instrumental' in stems:
        inst, _ = librosa.load(stems['instrumental'], sr=sr, mono=True)
        return inst, True
    parts = []
    for name in ('drums', 'bass', 'other'):
        if name in stems:
            part, _ = librosa.load(stems[name], sr=sr, mono=True)
            parts.append(part)
    if not parts:
        return master_audio.copy(), False
    length = max(len(p) for p in parts)
    inst = np.zeros(length, dtype=np.float32)
    for part in parts:
        inst[:len(part)] += part
    return inst, True


def _load_vocal_stem(separation, master_audio, sr):
    """Build the voice-only bus; basic HPF approximation when no model ran."""
    if separation and 'vocals' in separation['stems']:
        vocals, _ = librosa.load(separation['stems']['vocals'], sr=sr, mono=True)
        return vocals, True
    # No separator available: high-pass the master to at least thin the bass
    return apply_butterworth_hpf(master_audio, sr, cutoff=140).astype(np.float32), False


def create_lab_mashup(vocal_analysis, backing_analysis, output_dir,
                      style='divine', target_lufs=None, venv_path=None,
                      export_quality='high'):
    """Create a vocal-over-instrumental mashup from two analyzed tracks.

    Args:
        vocal_analysis: deep analysis dict of the song whose VOICE is used
        backing_analysis: deep analysis dict of the song whose MUSIC is used
        output_dir: destination directory
        style: 'divine' | 'cocktail_party' | 'club_remix'
        target_lufs: override the preset loudness target
        venv_path: venv containing the demucs binary
        export_quality: 'high' (320k) or 'standard' (256k)

    Returns:
        dict with output_path/output_filename, separator_used, degraded flag,
        target_bpm, semitone_shift, tempo_ratio, placements and warnings.
    """
    if style not in STYLE_PRESETS:
        raise ValueError(f"Unknown style '{style}'. Choose from {list(STYLE_PRESETS)}")
    preset = STYLE_PRESETS[style]
    if target_lufs is None:
        target_lufs = preset['target_lufs']

    print("\n" + "=" * 70)
    print(f"MASHUP LAB — {preset['label'].upper()}")
    print(f"  Voice : {vocal_analysis.get('filename')}")
    print(f"  Music : {backing_analysis.get('filename')}")
    print("=" * 70)

    sr = 44100
    venv_path = venv_path or os.environ.get('VIRTUAL_ENV', os.path.abspath('./venv'))
    stem_dir = os.path.join(output_dir, 'stem_cache')
    warnings = []

    vocal_path = vocal_analysis.get('file_path')
    backing_path = backing_analysis.get('file_path')
    if not vocal_path or not os.path.exists(vocal_path):
        raise FileNotFoundError(f"Vocal track not found: {vocal_path}")
    if not backing_path or not os.path.exists(backing_path):
        raise FileNotFoundError(f"Backing track not found: {backing_path}")

    # --- Phase 1: stem separation -------------------------------------------
    print("\n--- Phase 1: Separating stems ---")
    y_backing, _ = librosa.load(backing_path, sr=sr, mono=True)
    y_vocal_master, _ = librosa.load(vocal_path, sr=sr, mono=True)

    backing_sep = separate_stems_best(backing_path, stem_dir, venv_path)
    vocal_sep = separate_stems_best(vocal_path, stem_dir, venv_path)

    instrumental, backing_clean = _load_instrumental_bus(backing_sep, y_backing, sr)
    vocals, vocal_clean = _load_vocal_stem(vocal_sep, y_vocal_master, sr)

    separator_used = {
        'backing': backing_sep['separator'] if backing_sep else 'none',
        'vocal': vocal_sep['separator'] if vocal_sep else 'none',
    }
    degraded = not (backing_clean and vocal_clean)
    if not backing_clean:
        warnings.append("No separation model available for the music track — "
                        "its original vocals remain in the backing.")
    if not vocal_clean:
        warnings.append("No separation model available for the voice track — "
                        "using a filtered master instead of a clean acapella.")

    # --- Phase 2: tempo lock (backing is the master clock, untouched) --------
    print("\n--- Phase 2: Tempo locking vocals to the beat ---")
    backing_bpm = backing_analysis.get('bpm') or 120
    vocal_bpm = vocal_analysis.get('bpm') or backing_bpm
    effective_vocal_bpm, ratio = normalize_tempo_ratio(vocal_bpm, backing_bpm)
    print(f"  Voice {vocal_bpm:.1f} BPM (counted as {effective_vocal_bpm:.1f}) "
          f"-> Music {backing_bpm:.1f} BPM (stretch x{ratio:.3f})")
    if ratio < 0.77 or ratio > 1.30:
        warnings.append(f"Large tempo stretch (x{ratio:.2f}) — vocals may sound processed.")
    if abs(ratio - 1.0) > 0.02:
        vocals = time_stretch_audio(vocals, sr, effective_vocal_bpm, backing_bpm)
    time_scale = 1.0 / ratio

    # --- Phase 3: key lock (formant-preserving, shruti-corrected) ------------
    print("\n--- Phase 3: Key locking vocals ---")
    semitones = choose_semitone_shift(
        vocal_analysis.get('key', 0), vocal_analysis.get('mode', 1),
        backing_analysis.get('key', 0), backing_analysis.get('mode', 1))
    cents_drift = detect_shruti_tuning(y_vocal_master, sr)
    print(f"  Shift: {semitones:+d} semitones, shruti correction {-cents_drift:+.1f} cents")
    if abs(semitones) > 0 or abs(cents_drift) > 5:
        vocals = pitch_shift_pro(vocals, sr, semitones,
                                 cents_offset=-cents_drift, is_vocal=True)

    # --- Phase 4: phrase planning on the backing beat grid -------------------
    print("\n--- Phase 4: Placing vocal phrases on the beat grid ---")
    phrases = extract_vocal_phrases(vocal_analysis, time_scale)
    placements = plan_vocal_placement(phrases, backing_analysis, preset)
    if not placements:
        beat_grid = backing_analysis.get('beat_grid') or {}
        start = (beat_grid.get('first_downbeat', 0) or 0) + 8 * (4 * 60.0 / backing_bpm)
        placements = [{
            'timeline_start_sec': float(start),
            'vocal_start_sec': 0.0,
            'vocal_end_sec': float(min(len(vocals) / sr,
                                       max(0.0, len(instrumental) / sr - start - 3.0))),
            'fade_in_sec': 2.0, 'fade_out_sec': 2.0, 'section_type': 'full',
        }]
        warnings.append("No vocal phrases detected — placing the whole vocal as one block.")
    print(f"  {len(placements)} vocal phrase(s) placed "
          f"(first entry at {placements[0]['timeline_start_sec']:.1f}s)")

    # --- Style FX on the backing ----------------------------------------------
    bar_sec = 4 * 60.0 / backing_bpm
    first_entry = int(placements[0]['timeline_start_sec'] * sr)
    if preset['lpf_intro_sweep'] and first_entry > sr:
        sweep_len = min(int(8 * bar_sec * sr), first_entry)
        num_chunks = 10
        chunk = sweep_len // num_chunks
        if chunk > 0:
            print("  [Style FX] Filtered intro sweep (club style)")
            for c in range(num_chunks):
                c_start, c_end = c * chunk, (c + 1) * chunk if c < num_chunks - 1 else sweep_len
                cutoff = 2000 + (10000 - 2000) * (c / max(1, num_chunks - 1))
                instrumental[c_start:c_end] = apply_butterworth_lpf(
                    instrumental[c_start:c_end], sr, cutoff)
    if preset['drop_silence_beats'] > 0 and first_entry > 0:
        drop_len = int(preset['drop_silence_beats'] * (60.0 / backing_bpm) * sr)
        drop_start = max(0, first_entry - drop_len)
        print(f"  [Style FX] Pre-vocal drop: {preset['drop_silence_beats']} beats of silence")
        instrumental[drop_start:first_entry] *= np.linspace(1.0, 0.0, first_entry - drop_start)

    # --- Render the vocal timeline ---------------------------------------------
    timeline_voc = np.zeros(len(instrumental), dtype=np.float32)
    for placement in placements:
        seg_start = int(placement['vocal_start_sec'] * sr)
        seg_end = min(int(placement['vocal_end_sec'] * sr), len(vocals))
        if seg_end <= seg_start:
            continue
        segment = vocals[seg_start:seg_end].copy()
        fade_in = min(int(placement['fade_in_sec'] * sr), len(segment) // 2)
        fade_out = min(int(placement['fade_out_sec'] * sr), len(segment) // 2)
        if fade_in > 0:
            segment[:fade_in] *= np.sqrt(np.linspace(0, 1, fade_in))
        if fade_out > 0:
            segment[-fade_out:] *= np.sqrt(np.linspace(1, 0, fade_out))
        t0 = int(placement['timeline_start_sec'] * sr)
        t1 = min(t0 + len(segment), len(timeline_voc))
        if t1 > t0:
            timeline_voc[t0:t1] += segment[:t1 - t0]

    if preset['vocal_reverb'] and HAS_REVERB:
        print("  [Style FX] Vocal reverb (divine style)")
        reverb = Pedalboard([Reverb(room_size=preset['vocal_reverb']['room_size'],
                                    wet_level=preset['vocal_reverb']['wet_level'])])
        timeline_voc = reverb(np.expand_dims(timeline_voc, 0), sr, reset=True)[0]

    # --- Sidechain ducking + summing -------------------------------------------
    print("\n--- Phase 5: Sidechain ducking & mastering ---")
    timeline_inst = dynamic_sidechain_ducking(
        instrumental, timeline_voc, sr, max_reduction_db=preset['duck_db'])
    length = min(len(timeline_inst), len(timeline_voc))
    master_mix = (timeline_inst[:length]
                  + timeline_voc[:length] * db_to_gain(preset['vocal_gain_db']))

    final_audio = apply_master_bus_glue(master_mix, sr, target_lufs)
    final_audio = np.nan_to_num(np.asarray(final_audio, dtype=np.float32))

    # --- Export ------------------------------------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"mashup_lab_{style}_{timestamp}"
    print(f"Exporting: {base_name} ({len(final_audio) / sr:.1f}s)")
    output_path = export_audio(final_audio, sr, output_dir, base_name, export_quality)
    print("✅ Mashup Lab creation successful!")

    return {
        'output_path': output_path,
        'output_filename': os.path.basename(output_path),
        'style': style,
        'separator_used': separator_used,
        'degraded': degraded,
        'target_bpm': float(backing_bpm),
        'semitone_shift': semitones,
        'tempo_ratio': float(ratio),
        'placements': placements,
        'duration_sec': float(len(final_audio) / sr),
        'warnings': warnings,
    }


if __name__ == "__main__":
    print("Mashup Lab — vocal-over-instrumental engine loaded.")
    print(f"Styles: {', '.join(STYLE_PRESETS)}")
