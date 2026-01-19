#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# kannada_mashup_analyzer.py
# Extended Deep Analysis for Kannada Music Mashups (Anand Audio Style)
#
# This module provides comprehensive audio analysis parameters essential for
# creating professional mashups of Kannada songs, particularly from channels
# like Anand Audio. It identifies all key characteristics needed for seamless
# DJ mixing and mashup creation.
#
# VERSION 2.0 - Enhanced with Professional DJ Features:
# - Beat grid and downbeat detection
# - Phrase boundary detection (4/8/16/32 bar phrases)
# - DJ cue points (mix-in, mix-out, drop, loop points)
# - Vocal-free mix zones
# - Transition type recommendations
# - Multi-track mashup planning
# - Anand Audio specific patterns (dialogue, filmi intros)
# -----------------------------------------------------------------------------

import os
import sys
import numpy as np
import librosa
import scipy.signal
from collections import defaultdict
from itertools import combinations
from audio_analyzer import analyze_audio_local, analyze_vocal_presence


# =============================================================================
# KANNADA/INDIAN MUSIC CONSTANTS
# =============================================================================

# Common Talas (Rhythmic Cycles) in Kannada Film Music
TALA_PATTERNS = {
    'adi_tala': {'beats': 8, 'subdivision': [4, 2, 2], 'name': 'Adi Tala (8 beats)'},
    'rupaka_tala': {'beats': 6, 'subdivision': [2, 4], 'name': 'Rupaka Tala (6 beats)'},
    'mishra_chapu': {'beats': 7, 'subdivision': [3, 4], 'name': 'Mishra Chapu (7 beats)'},
    'khanda_chapu': {'beats': 5, 'subdivision': [2, 3], 'name': 'Khanda Chapu (5 beats)'},
    'triputa_tala': {'beats': 7, 'subdivision': [3, 2, 2], 'name': 'Triputa Tala (7 beats)'},
    'eka_tala': {'beats': 4, 'subdivision': [4], 'name': 'Eka Tala (4 beats)'},
    'jhampai_tala': {'beats': 10, 'subdivision': [7, 3], 'name': 'Jhampai Tala (10 beats)'},
}

# Common scales in Kannada film music (mapped to Western chromatic notes)
# These are inspired by popular ragas used in Kannada cinema
KANNADA_SCALE_PROFILES = {
    'mohanam': [0, 2, 4, 7, 9],  # Pentatonic - very common in upbeat songs
    'kalyani': [0, 2, 4, 6, 7, 9, 11],  # Similar to Lydian - celebratory feel
    'shankarabharanam': [0, 2, 4, 5, 7, 9, 11],  # Major scale - very common
    'kharaharapriya': [0, 2, 3, 5, 7, 9, 10],  # Dorian - emotional songs
    'natabhairavi': [0, 2, 3, 5, 7, 8, 10],  # Natural minor - sad songs
    'mayamalavagowla': [0, 1, 4, 5, 7, 8, 11],  # Classical feel
    'hamsadhwani': [0, 2, 4, 7, 11],  # Pentatonic - auspicious songs
    'bilahari': [0, 2, 4, 5, 7, 9, 11],  # Similar to major - bright songs
    'sindhubhairavi': [0, 1, 3, 4, 5, 7, 8, 10],  # Emotional/devotional
    'abheri': [0, 3, 5, 7, 10],  # Pentatonic minor - folk songs
}

# Emotional categories for Kannada songs
EMOTION_CATEGORIES = {
    'romantic': ['mohanam', 'kalyani', 'bilahari'],
    'celebratory': ['shankarabharanam', 'kalyani', 'hamsadhwani'],
    'melancholic': ['natabhairavi', 'kharaharapriya', 'sindhubhairavi'],
    'devotional': ['mayamalavagowla', 'hamsadhwani', 'sindhubhairavi'],
    'folk_energetic': ['abheri', 'mohanam', 'shankarabharanam'],
}

# DJ Transition Types
TRANSITION_TYPES = {
    'cut': 'Hard cut - instant switch, works for dramatic moments',
    'crossfade': 'Gradual blend over 4-8 bars',
    'eq_swap': 'Swap bass first, then mids/highs - professional DJ technique',
    'echo_out': 'Echo/delay out the outgoing track',
    'filter_sweep': 'High-pass filter sweep on outgoing track',
    'drop_swap': 'Cut at the drop of the incoming track',
    'acapella_blend': 'Bring in vocals over instrumental',
    'instrumental_blend': 'Bring in instrumental under vocals',
}

# Anand Audio specific song patterns
ANAND_AUDIO_PATTERNS = {
    'dialogue_intro': 'Movie dialogue before song starts',
    'filmi_intro': 'Orchestral/BGM style intro',
    'gaana_style': 'High-energy folk/mass style',
    'melody_style': 'Soft romantic melody',
    'devotional_style': 'Bhakti/devotional song',
    'duet_style': 'Male-female duet pattern',
    'item_number': 'Dance/item song pattern',
}


# =============================================================================
# BEAT GRID AND DOWNBEAT DETECTION (DJ ESSENTIAL)
# =============================================================================

def detect_beat_grid(y, sr):
    """
    Detects the beat grid including downbeat (beat 1) position.

    This is ESSENTIAL for DJing - you need to know exactly where each beat
    falls to beat-match properly. The downbeat is especially important for
    phrase-aligned mixing.

    Returns:
        dict: Beat grid with timestamps, downbeats, and confidence
    """
    print("  Detecting beat grid and downbeats...")

    # Get tempo and beat frames
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Calculate beat interval consistency (for tempo stability)
    if len(beat_times) > 1:
        intervals = np.diff(beat_times)
        tempo_stability = 1 - (np.std(intervals) / np.mean(intervals)) if np.mean(intervals) > 0 else 0
        avg_beat_interval = float(np.mean(intervals))
    else:
        tempo_stability = 0
        avg_beat_interval = 60.0 / tempo if tempo > 0 else 0.5

    # Detect downbeats (beat 1 of each bar)
    # Use onset strength to find accented beats
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)

    # Get onset strength at each beat
    beat_strengths = []
    for frame in beat_frames:
        if frame < len(onset_env):
            beat_strengths.append(onset_env[frame])
        else:
            beat_strengths.append(0)
    beat_strengths = np.array(beat_strengths)

    # Find downbeats by looking for periodic accent pattern
    # Typically in 4/4, beat 1 is strongest, beat 3 is second strongest
    downbeat_indices = []
    best_start = 0
    max_strength = -1

    if len(beat_strengths) >= 8:
        # Try to find 4-beat pattern
        for start in range(4):
            pattern_strength = 0
            count = 0
            for i in range(start, len(beat_strengths), 4):
                pattern_strength += beat_strengths[i]
                count += 1
            if count > 0:
                pattern_strength /= count

            if pattern_strength > max_strength:
                max_strength = pattern_strength
                best_start = start

        # Mark downbeats (every 4th beat starting from best_start)
        for i in range(best_start, len(beat_frames), 4):
            downbeat_indices.append(i)

    downbeat_times = [float(beat_times[i]) for i in downbeat_indices if i < len(beat_times)]

    # First downbeat is crucial for mixing
    first_downbeat = downbeat_times[0] if downbeat_times else (beat_times[0] if len(beat_times) > 0 else 0)

    return {
        'tempo': float(tempo),
        'tempo_stability': float(tempo_stability),
        'beat_times': [float(t) for t in beat_times],
        'beat_count': len(beat_times),
        'avg_beat_interval': avg_beat_interval,
        'downbeat_times': downbeat_times,
        'first_downbeat': float(first_downbeat),
        'beats_per_bar': 4,  # Assuming 4/4, could be detected
        'is_tempo_stable': tempo_stability > 0.9,
        'tempo_drift_warning': tempo_stability < 0.85
    }


# =============================================================================
# PHRASE BOUNDARY DETECTION (DJ ESSENTIAL)
# =============================================================================

def detect_phrase_boundaries(y, sr, beat_grid, duration):
    """
    Detects musical phrase boundaries (4, 8, 16, 32 bar phrases).

    DJs ALWAYS mix on phrase boundaries for seamless transitions.
    A phrase is typically 8 or 16 bars in pop/film music.

    Returns:
        dict: Phrase boundaries at different levels
    """
    print("  Detecting phrase boundaries...")

    tempo = beat_grid['tempo']
    beat_times = beat_grid['beat_times']
    beats_per_bar = beat_grid['beats_per_bar']

    if tempo <= 0 or len(beat_times) < 16:
        return {
            '4_bar_phrases': [],
            '8_bar_phrases': [],
            '16_bar_phrases': [],
            '32_bar_phrases': [],
            'primary_phrase_length': 8,
            'phrase_boundaries': []
        }

    # Calculate bar duration
    bar_duration = (60.0 / tempo) * beats_per_bar

    # Detect structural changes using spectral flux
    hop_length = 512
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)

    # Compute novelty function (detects changes)
    # Use a longer window for phrase-level detection
    novelty_window = int(bar_duration * sr / hop_length * 4)  # 4 bars window
    if novelty_window > 1:
        novelty = np.abs(np.diff(np.convolve(onset_env, np.ones(novelty_window)/novelty_window, mode='same')))
    else:
        novelty = np.abs(np.diff(onset_env))

    # Find peaks in novelty (potential phrase boundaries)
    min_phrase_samples = int(4 * bar_duration * sr / hop_length)  # Minimum 4 bars between phrases
    peaks, _ = scipy.signal.find_peaks(novelty, distance=min_phrase_samples, height=np.mean(novelty))

    # Convert to times
    novelty_times = librosa.frames_to_time(peaks, sr=sr, hop_length=hop_length)

    # Generate phrase boundaries at regular intervals
    phrases_4bar = []
    phrases_8bar = []
    phrases_16bar = []
    phrases_32bar = []

    # Start from the first downbeat
    first_downbeat = beat_grid['first_downbeat']

    # Generate 4-bar phrases
    time = first_downbeat
    bar_count = 0
    while time < duration:
        phrases_4bar.append(float(time))
        if bar_count % 2 == 0:
            phrases_8bar.append(float(time))
        if bar_count % 4 == 0:
            phrases_16bar.append(float(time))
        if bar_count % 8 == 0:
            phrases_32bar.append(float(time))
        time += bar_duration * 4
        bar_count += 1

    # Determine primary phrase length based on novelty alignment
    phrase_alignment_scores = {}
    for phrase_name, phrases in [('4_bar', phrases_4bar), ('8_bar', phrases_8bar),
                                   ('16_bar', phrases_16bar)]:
        if len(phrases) < 2:
            continue
        # Score how well novelty peaks align with phrase boundaries
        alignment_score = 0
        for nov_time in novelty_times:
            min_dist = min(abs(nov_time - p) for p in phrases)
            if min_dist < bar_duration:  # Within 1 bar
                alignment_score += 1
        phrase_alignment_scores[phrase_name] = alignment_score / len(novelty_times) if novelty_times.size > 0 else 0

    # Best phrase length
    if phrase_alignment_scores:
        primary_phrase = max(phrase_alignment_scores.items(), key=lambda x: x[1])[0]
        primary_phrase_bars = int(primary_phrase.split('_')[0])
    else:
        primary_phrase_bars = 8  # Default

    return {
        '4_bar_phrases': phrases_4bar,
        '8_bar_phrases': phrases_8bar,
        '16_bar_phrases': phrases_16bar,
        '32_bar_phrases': phrases_32bar,
        'primary_phrase_length': primary_phrase_bars,
        'phrase_boundaries': phrases_8bar,  # Most common for mixing
        'bar_duration_sec': float(bar_duration),
        'detected_structure_changes': [float(t) for t in novelty_times[:20]]
    }


# =============================================================================
# DJ CUE POINTS (ACTIONABLE MIX POINTS)
# =============================================================================

def generate_dj_cue_points(y, sr, beat_grid, phrases, sections, hooks_drops, vocal_regions, duration):
    """
    Generates actionable DJ cue points for mixing.

    These are the EXACT timestamps a DJ needs:
    - MIX IN: Where to start bringing this track in
    - MIX OUT: Where to start transitioning out
    - DROP: The main energy drop point
    - LOOP: Safe points to create a loop
    - HOT CUES: Quick jump points for live performance

    Returns:
        dict: Complete cue point set
    """
    print("  Generating DJ cue points...")

    bar_duration = phrases.get('bar_duration_sec', 2.0)
    phrase_boundaries = phrases.get('8_bar_phrases', [])

    # Helper: find nearest phrase boundary
    def nearest_phrase(time):
        if not phrase_boundaries:
            return time
        return min(phrase_boundaries, key=lambda p: abs(p - time))

    # Helper: check if time is in vocal region
    def in_vocal_region(time):
        for vr in vocal_regions:
            if vr['start'] <= time <= vr['end']:
                return True
        return False

    # =========== MIX IN POINT ===========
    # Best place to bring this track into a mix
    # Prefer: start of intro, first phrase boundary, or first non-vocal section

    mix_in_candidates = []

    # Option 1: Start of intro (if exists and is instrumental)
    intro = sections.get('intro')
    if intro and not intro.get('has_vocals', False):
        mix_in_candidates.append({
            'time': nearest_phrase(intro['start']),
            'reason': 'Start of instrumental intro',
            'quality': 'excellent'
        })

    # Option 2: First phrase boundary
    if phrase_boundaries:
        first_phrase = phrase_boundaries[0]
        mix_in_candidates.append({
            'time': first_phrase,
            'reason': 'First phrase boundary',
            'quality': 'good'
        })

    # Option 3: First vocal-free zone after intro
    if vocal_regions:
        first_vocal_start = vocal_regions[0]['start'] if vocal_regions else duration
        if first_vocal_start > bar_duration * 4:
            mix_in_candidates.append({
                'time': nearest_phrase(0),
                'reason': 'Instrumental opening',
                'quality': 'good'
            })

    # Select best mix-in point
    mix_in = mix_in_candidates[0] if mix_in_candidates else {'time': 0, 'reason': 'Track start', 'quality': 'fair'}

    # =========== MIX OUT POINT ===========
    # Best place to transition out of this track

    mix_out_candidates = []

    # Option 1: Start of outro
    outro = sections.get('outro')
    if outro:
        mix_out_candidates.append({
            'time': nearest_phrase(outro['start']),
            'reason': 'Start of outro section',
            'quality': 'excellent'
        })

    # Option 2: Last instrumental section
    interludes = sections.get('interludes', [])
    if interludes:
        last_interlude = max(interludes, key=lambda x: x['start'])
        if last_interlude['start'] > duration * 0.6:
            mix_out_candidates.append({
                'time': nearest_phrase(last_interlude['start']),
                'reason': 'Final interlude',
                'quality': 'good'
            })

    # Option 3: 16 bars before end
    late_phrase = [p for p in phrase_boundaries if duration - 32 * bar_duration / 4 < p < duration - 8 * bar_duration / 4]
    if late_phrase:
        mix_out_candidates.append({
            'time': late_phrase[0],
            'reason': 'Late song phrase boundary',
            'quality': 'good'
        })

    mix_out = mix_out_candidates[0] if mix_out_candidates else {'time': max(0, duration - 30), 'reason': 'Near end', 'quality': 'fair'}

    # =========== DROP POINT ===========
    # The main energy moment - perfect for dramatic transitions

    drops = hooks_drops.get('beat_drops', [])
    primary_hook = hooks_drops.get('primary_hook')

    if drops:
        main_drop = max(drops, key=lambda d: d.get('intensity', 0))
        drop_cue = {
            'time': nearest_phrase(main_drop['time']),
            'intensity': main_drop['intensity'],
            'reason': 'Main beat drop'
        }
    elif primary_hook:
        drop_cue = {
            'time': nearest_phrase(primary_hook['start']),
            'intensity': 1.0,
            'reason': 'Primary hook section'
        }
    else:
        # Find highest energy point
        hop_length = 2048
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        peak_frame = np.argmax(rms)
        peak_time = librosa.frames_to_time(peak_frame, sr=sr, hop_length=hop_length)
        drop_cue = {
            'time': nearest_phrase(float(peak_time)),
            'intensity': 0.8,
            'reason': 'Peak energy point'
        }

    # =========== LOOP POINTS ===========
    # Safe points to create seamless loops (for extending/shortening)

    loop_points = []

    # Find stable energy sections that align with phrases
    hop_length = 2048
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

    for i, phrase_start in enumerate(phrase_boundaries[:-1]):
        phrase_end = phrase_boundaries[i + 1] if i + 1 < len(phrase_boundaries) else duration

        # Get frames for this phrase
        start_frame = librosa.time_to_frames(phrase_start, sr=sr, hop_length=hop_length)
        end_frame = librosa.time_to_frames(phrase_end, sr=sr, hop_length=hop_length)

        if end_frame > start_frame and end_frame <= len(rms):
            segment_rms = rms[start_frame:end_frame]
            energy_stability = 1 - (np.std(segment_rms) / (np.mean(segment_rms) + 0.001))

            # Good loops have stable energy and are not in vocal regions
            is_vocal_free = not any(in_vocal_region(t) for t in [phrase_start, (phrase_start + phrase_end) / 2])

            if energy_stability > 0.7:
                loop_quality = 'excellent' if is_vocal_free else 'good'
                loop_points.append({
                    'start': float(phrase_start),
                    'end': float(phrase_end),
                    'bars': 8,
                    'quality': loop_quality,
                    'is_vocal_free': is_vocal_free,
                    'energy_stability': float(energy_stability)
                })

    # Sort by quality and stability
    loop_points = sorted(loop_points, key=lambda x: (-1 if x['quality'] == 'excellent' else 0, -x['energy_stability']))[:5]

    # =========== HOT CUES ===========
    # Quick reference points for live performance

    hot_cues = []

    # Hot Cue 1: Track start / Mix in
    hot_cues.append({'number': 1, 'time': mix_in['time'], 'label': 'MIX IN', 'color': 'green'})

    # Hot Cue 2: First chorus/pallavi
    pallavis = sections.get('pallavis', [])
    if pallavis:
        hot_cues.append({'number': 2, 'time': nearest_phrase(pallavis[0]['start']), 'label': 'CHORUS 1', 'color': 'blue'})

    # Hot Cue 3: Main drop
    hot_cues.append({'number': 3, 'time': drop_cue['time'], 'label': 'DROP', 'color': 'red'})

    # Hot Cue 4: Best hook
    if primary_hook:
        hot_cues.append({'number': 4, 'time': nearest_phrase(primary_hook['start']), 'label': 'HOOK', 'color': 'yellow'})

    # Hot Cue 5: Mix out
    hot_cues.append({'number': 5, 'time': mix_out['time'], 'label': 'MIX OUT', 'color': 'orange'})

    return {
        'mix_in': mix_in,
        'mix_out': mix_out,
        'drop': drop_cue,
        'loop_points': loop_points,
        'hot_cues': hot_cues,
        'recommended_mix_duration_bars': 8 if beat_grid.get('is_tempo_stable', True) else 4
    }


# =============================================================================
# VOCAL-FREE MIX ZONES (ESSENTIAL FOR MASHUPS)
# =============================================================================

def detect_vocal_free_zones(vocal_regions, phrases, duration):
    """
    Identifies zones where there are no vocals - perfect for mixing.

    Vocal clashes are the #1 problem in mashups. These zones tell you
    exactly where you can safely bring in another track's vocals.

    Returns:
        dict: Vocal-free zones with mixability ratings
    """
    print("  Detecting vocal-free mix zones...")

    phrase_boundaries = phrases.get('8_bar_phrases', [])
    bar_duration = phrases.get('bar_duration_sec', 2.0)

    # Build vocal timeline
    vocal_timeline = np.zeros(int(duration * 10))  # 0.1 second resolution
    for vr in vocal_regions:
        start_idx = int(vr['start'] * 10)
        end_idx = int(vr['end'] * 10)
        vocal_timeline[start_idx:end_idx] = 1

    # Find continuous vocal-free regions
    vocal_free_zones = []
    in_free_zone = False
    zone_start = 0

    for i, has_vocal in enumerate(vocal_timeline):
        time = i / 10.0
        if has_vocal == 0 and not in_free_zone:
            in_free_zone = True
            zone_start = time
        elif has_vocal == 1 and in_free_zone:
            in_free_zone = False
            zone_end = time
            zone_duration = zone_end - zone_start

            # Only consider zones longer than 2 bars
            if zone_duration >= bar_duration * 2:
                # Find nearest phrase boundaries
                start_aligned = min(phrase_boundaries, key=lambda p: abs(p - zone_start)) if phrase_boundaries else zone_start
                end_aligned = min(phrase_boundaries, key=lambda p: abs(p - zone_end)) if phrase_boundaries else zone_end

                # Calculate mixability
                bars = zone_duration / bar_duration
                if bars >= 16:
                    mixability = 'excellent'
                elif bars >= 8:
                    mixability = 'good'
                elif bars >= 4:
                    mixability = 'fair'
                else:
                    mixability = 'tight'

                vocal_free_zones.append({
                    'start': float(zone_start),
                    'end': float(zone_end),
                    'duration': float(zone_duration),
                    'bars': float(bars),
                    'phrase_aligned_start': float(start_aligned),
                    'phrase_aligned_end': float(end_aligned),
                    'mixability': mixability,
                    'position': 'intro' if zone_start < duration * 0.15 else ('outro' if zone_end > duration * 0.85 else 'middle')
                })

    # Handle final zone if song ends without vocals
    if in_free_zone:
        zone_end = duration
        zone_duration = zone_end - zone_start
        if zone_duration >= bar_duration * 2:
            bars = zone_duration / bar_duration
            mixability = 'excellent' if bars >= 16 else ('good' if bars >= 8 else 'fair')
            vocal_free_zones.append({
                'start': float(zone_start),
                'end': float(zone_end),
                'duration': float(zone_duration),
                'bars': float(bars),
                'mixability': mixability,
                'position': 'outro'
            })

    # Find the best mix zones
    intro_zones = [z for z in vocal_free_zones if z['position'] == 'intro']
    outro_zones = [z for z in vocal_free_zones if z['position'] == 'outro']
    middle_zones = [z for z in vocal_free_zones if z['position'] == 'middle']

    return {
        'all_zones': vocal_free_zones,
        'intro_zones': intro_zones,
        'outro_zones': outro_zones,
        'middle_zones': middle_zones,
        'best_mix_in_zone': max(intro_zones, key=lambda z: z['duration']) if intro_zones else None,
        'best_mix_out_zone': max(outro_zones, key=lambda z: z['duration']) if outro_zones else None,
        'total_vocal_free_time': sum(z['duration'] for z in vocal_free_zones),
        'vocal_free_percentage': sum(z['duration'] for z in vocal_free_zones) / duration * 100 if duration > 0 else 0
    }


# =============================================================================
# TRANSITION RECOMMENDATIONS
# =============================================================================

def recommend_transitions(track_analysis, target_bpm_range=None):
    """
    Recommends the best transition types for this track.

    Different songs work better with different transition styles.
    This analyzes the track characteristics and suggests optimal methods.

    Returns:
        dict: Transition recommendations for mixing in and out
    """
    print("  Generating transition recommendations...")

    energy = track_analysis.get('energy', 0.5)
    has_vocals = track_analysis.get('has_vocals', False)
    drops = track_analysis.get('hooks_and_drops', {}).get('beat_drops', [])
    spectral = track_analysis.get('spectral', {})
    percussion = track_analysis.get('percussion', {})

    bass_class = spectral.get('bass_class', 'balanced')
    rhythm_density = percussion.get('density_class', 'moderate')

    # MIX IN recommendations
    mix_in_methods = []

    # High energy tracks: drop swap or cut works well
    if energy > 0.7:
        mix_in_methods.append({
            'method': 'drop_swap',
            'description': TRANSITION_TYPES['drop_swap'],
            'confidence': 0.9,
            'duration_bars': 0  # Instant
        })
        mix_in_methods.append({
            'method': 'eq_swap',
            'description': TRANSITION_TYPES['eq_swap'],
            'confidence': 0.85,
            'duration_bars': 8
        })

    # Vocal tracks: bring in during instrumental sections
    if has_vocals:
        mix_in_methods.append({
            'method': 'instrumental_blend',
            'description': TRANSITION_TYPES['instrumental_blend'],
            'confidence': 0.8,
            'duration_bars': 16
        })

    # Bass-heavy tracks: EQ swap is essential
    if bass_class == 'bass_heavy':
        mix_in_methods.append({
            'method': 'eq_swap',
            'description': TRANSITION_TYPES['eq_swap'],
            'confidence': 0.95,
            'duration_bars': 8
        })

    # Default: crossfade
    mix_in_methods.append({
        'method': 'crossfade',
        'description': TRANSITION_TYPES['crossfade'],
        'confidence': 0.7,
        'duration_bars': 8
    })

    # MIX OUT recommendations
    mix_out_methods = []

    # If has good drops, can cut out on a drop
    if drops:
        mix_out_methods.append({
            'method': 'drop_swap',
            'description': 'Cut out as new track drops',
            'confidence': 0.85,
            'duration_bars': 0
        })

    # Echo out works for most tracks
    mix_out_methods.append({
        'method': 'echo_out',
        'description': TRANSITION_TYPES['echo_out'],
        'confidence': 0.8,
        'duration_bars': 4
    })

    # Filter sweep for energetic tracks
    if energy > 0.6:
        mix_out_methods.append({
            'method': 'filter_sweep',
            'description': TRANSITION_TYPES['filter_sweep'],
            'confidence': 0.85,
            'duration_bars': 8
        })

    # Default crossfade
    mix_out_methods.append({
        'method': 'crossfade',
        'description': TRANSITION_TYPES['crossfade'],
        'confidence': 0.7,
        'duration_bars': 8
    })

    # Sort by confidence
    mix_in_methods = sorted(mix_in_methods, key=lambda x: -x['confidence'])
    mix_out_methods = sorted(mix_out_methods, key=lambda x: -x['confidence'])

    return {
        'mix_in_recommendations': mix_in_methods[:3],  # Top 3
        'mix_out_recommendations': mix_out_methods[:3],
        'best_mix_in': mix_in_methods[0] if mix_in_methods else None,
        'best_mix_out': mix_out_methods[0] if mix_out_methods else None,
        'ideal_transition_duration_bars': 8 if energy < 0.7 else 4,
        'notes': []
    }


# =============================================================================
# ANAND AUDIO SPECIFIC PATTERN DETECTION
# =============================================================================

def detect_anand_audio_patterns(y, sr, sections, vocal_regions, duration):
    """
    Detects patterns specific to Anand Audio / Kannada film songs.

    Anand Audio songs often have:
    - Movie dialogue intros
    - Filmi orchestral intros
    - "Gaana" style high-energy sections
    - Duet patterns (male-female alternating)

    Returns:
        dict: Detected Anand Audio specific patterns
    """
    print("  Detecting Anand Audio specific patterns...")

    patterns_detected = []
    song_style = 'unknown'

    intro = sections.get('intro')
    pallavis = sections.get('pallavis', [])
    charanams = sections.get('charanams', [])
    interludes = sections.get('interludes', [])

    # Check for dialogue intro (low energy, speech-like, at the start)
    if intro and intro['start'] < 5:
        intro_start = int(intro['start'] * sr)
        intro_end = int(min(intro['end'], 15) * sr)  # First 15 seconds max

        if intro_end > intro_start:
            y_intro = y[intro_start:intro_end]

            # Speech detection: low spectral centroid variance, moderate energy
            spectral_centroid = librosa.feature.spectral_centroid(y=y_intro, sr=sr)[0]
            centroid_variance = np.var(spectral_centroid)

            # Speech typically has lower variance than music
            if centroid_variance < 500000:  # Threshold for speech-like content
                patterns_detected.append({
                    'pattern': 'dialogue_intro',
                    'description': ANAND_AUDIO_PATTERNS['dialogue_intro'],
                    'start': intro['start'],
                    'end': intro['end'],
                    'confidence': 0.7
                })

    # Check for filmi orchestral intro
    if intro and intro.get('brightness', 0) > 2000 and not intro.get('has_vocals', False):
        patterns_detected.append({
            'pattern': 'filmi_intro',
            'description': ANAND_AUDIO_PATTERNS['filmi_intro'],
            'start': intro['start'],
            'end': intro['end'],
            'confidence': 0.75
        })

    # Detect song style based on overall characteristics
    total_energy = sum(s.get('energy', 0) for s in sections.get('sections', [])) / max(len(sections.get('sections', [])), 1)

    if total_energy > 0.6 and len(interludes) >= 2:
        song_style = 'gaana_style'
        patterns_detected.append({
            'pattern': 'gaana_style',
            'description': ANAND_AUDIO_PATTERNS['gaana_style'],
            'confidence': 0.8
        })
    elif total_energy < 0.4 and len(vocal_regions) > 3:
        song_style = 'melody_style'
        patterns_detected.append({
            'pattern': 'melody_style',
            'description': ANAND_AUDIO_PATTERNS['melody_style'],
            'confidence': 0.75
        })

    # Check for duet pattern (alternating vocal sections)
    if len(vocal_regions) >= 4:
        # Look for alternating pattern in vocal regions
        gaps = []
        for i in range(len(vocal_regions) - 1):
            gap = vocal_regions[i + 1]['start'] - vocal_regions[i]['end']
            gaps.append(gap)

        # Duets typically have regular gaps between vocal sections
        if len(gaps) >= 3 and np.std(gaps) < np.mean(gaps) * 0.5:
            patterns_detected.append({
                'pattern': 'duet_style',
                'description': ANAND_AUDIO_PATTERNS['duet_style'],
                'confidence': 0.7
            })

    # Identify the best sections for showcasing (the "hero" moments)
    hero_sections = []
    all_sections = sections.get('sections', [])
    for sec in all_sections:
        if sec.get('energy', 0) > total_energy * 1.3:
            hero_sections.append({
                'start': sec['start'],
                'end': sec['end'],
                'type': sec['section_type'],
                'energy': sec['energy']
            })

    return {
        'detected_patterns': patterns_detected,
        'song_style': song_style,
        'has_dialogue_intro': any(p['pattern'] == 'dialogue_intro' for p in patterns_detected),
        'has_filmi_intro': any(p['pattern'] == 'filmi_intro' for p in patterns_detected),
        'is_gaana_style': song_style == 'gaana_style',
        'is_duet': any(p['pattern'] == 'duet_style' for p in patterns_detected),
        'hero_sections': hero_sections[:3],  # Top 3 energy moments
        'skip_intro_until': intro['end'] if any(p['pattern'] == 'dialogue_intro' for p in patterns_detected) else 0
    }


# =============================================================================
# TALA (RHYTHMIC CYCLE) DETECTION
# =============================================================================

def detect_tala(y, sr, estimated_bpm):
    """
    Detects the probable Tala (rhythmic cycle) of a Kannada song.

    Indian music uses complex rhythmic cycles that don't always fit Western
    4/4 time. This function analyzes beat patterns to identify the tala.

    Returns:
        dict: Tala information including name, beats per cycle, and confidence
    """
    print("  Detecting Tala (rhythmic cycle)...")

    # Get onset envelope and beats
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env)

    if len(beats) < 16:
        return {
            'tala_name': 'Unknown',
            'beats_per_cycle': 4,
            'confidence': 0.0,
            'pattern': 'insufficient_data'
        }

    # Analyze inter-beat intervals for pattern detection
    beat_times = librosa.frames_to_time(beats, sr=sr)
    intervals = np.diff(beat_times)

    # Normalize intervals to detect accents
    if len(intervals) > 0:
        mean_interval = np.mean(intervals)
        normalized_intervals = intervals / mean_interval
    else:
        normalized_intervals = np.array([1.0])

    # Get onset strengths at beat positions
    beat_strengths = onset_env[beats[:-1]] if len(beats) > 1 else np.array([1.0])

    # Score each tala pattern
    tala_scores = {}
    for tala_key, tala_info in TALA_PATTERNS.items():
        cycle_len = tala_info['beats']

        # Check if beats align with this cycle length
        if len(beat_strengths) >= cycle_len * 2:
            # Reshape into cycles
            num_cycles = len(beat_strengths) // cycle_len
            if num_cycles > 0:
                cycles = beat_strengths[:num_cycles * cycle_len].reshape(num_cycles, cycle_len)

                # Calculate accent pattern consistency
                mean_cycle = np.mean(cycles, axis=0)
                accent_pattern = mean_cycle / np.max(mean_cycle) if np.max(mean_cycle) > 0 else mean_cycle

                # Score based on how well accents match subdivision pattern
                subdivision = tala_info['subdivision']
                expected_accents = []
                pos = 0
                for sub in subdivision:
                    expected_accents.append(pos)
                    pos += sub

                accent_score = sum(accent_pattern[i] for i in expected_accents if i < len(accent_pattern))
                consistency = 1 - np.std(cycles, axis=0).mean() if len(cycles) > 1 else 0.5

                tala_scores[tala_key] = (accent_score * consistency, tala_info)

    # Find best matching tala
    if tala_scores:
        best_tala = max(tala_scores.items(), key=lambda x: x[0])
        confidence = min(best_tala[1][0] / 5.0, 1.0)  # Normalize confidence

        return {
            'tala_name': best_tala[1][1]['name'],
            'tala_key': best_tala[0],
            'beats_per_cycle': best_tala[1][1]['beats'],
            'subdivision': best_tala[1][1]['subdivision'],
            'confidence': float(confidence)
        }

    # Default to Adi Tala (most common in film music)
    return {
        'tala_name': 'Adi Tala (8 beats) - default',
        'tala_key': 'adi_tala',
        'beats_per_cycle': 8,
        'subdivision': [4, 2, 2],
        'confidence': 0.3
    }


# =============================================================================
# MELODIC SCALE / RAGAM-INSPIRED ANALYSIS
# =============================================================================

def detect_scale_profile(y, sr):
    """
    Detects the melodic scale/ragam-inspired pattern of the song.

    Kannada film music often uses scales derived from Carnatic ragas.
    This identifies which scale profile best matches the song.

    Returns:
        dict: Scale information including name, notes, and emotional category
    """
    print("  Analyzing melodic scale profile...")

    # Extract chromagram
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)

    # Normalize
    chroma_normalized = chroma_mean / np.max(chroma_mean) if np.max(chroma_mean) > 0 else chroma_mean

    # Find the tonic (Sa/root note)
    tonic_idx = np.argmax(chroma_mean)

    # Rotate chroma to start from tonic
    rotated_chroma = np.roll(chroma_normalized, -tonic_idx)

    # Score each scale profile
    scale_scores = {}
    for scale_name, scale_notes in KANNADA_SCALE_PROFILES.items():
        # Create a binary mask for the scale
        scale_mask = np.zeros(12)
        for note in scale_notes:
            scale_mask[note] = 1

        # Score: sum of chroma values at scale positions - sum at non-scale positions
        scale_energy = sum(rotated_chroma[note] for note in scale_notes)
        non_scale_energy = sum(rotated_chroma[i] for i in range(12) if i not in scale_notes)

        # Penalize non-scale notes
        score = scale_energy - (non_scale_energy * 0.5)
        scale_scores[scale_name] = score

    # Find best matching scale
    best_scale = max(scale_scores.items(), key=lambda x: x[1])

    # Determine emotional category
    emotion = 'neutral'
    for emotion_cat, scales in EMOTION_CATEGORIES.items():
        if best_scale[0] in scales:
            emotion = emotion_cat
            break

    # Get note names
    note_names = ['Sa', 'Ri1', 'Ri2/Ga1', 'Ga2', 'Ma1', 'Ma2', 'Pa', 'Dha1', 'Dha2/Ni1', 'Ni2', 'Ni3', 'Sa+']
    western_notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    tonic_western = western_notes[tonic_idx]
    scale_swaras = [note_names[n] for n in KANNADA_SCALE_PROFILES[best_scale[0]]]

    return {
        'scale_name': best_scale[0],
        'scale_notes': KANNADA_SCALE_PROFILES[best_scale[0]],
        'scale_swaras': scale_swaras,
        'tonic_index': int(tonic_idx),
        'tonic_western': tonic_western,
        'emotional_category': emotion,
        'confidence': float(min(best_scale[1] / 5.0, 1.0)),
        'all_scores': {k: float(v) for k, v in sorted(scale_scores.items(), key=lambda x: -x[1])[:5]}
    }


# =============================================================================
# HOOK/CHORUS AND BEAT DROP DETECTION
# =============================================================================

def detect_hooks_and_drops(y, sr, structure):
    """
    Identifies hook sections (catchy repeated parts) and beat drops.

    Essential for mashups - hooks are the recognizable parts people remember,
    and beat drops are perfect transition points.

    Returns:
        dict: Hook sections and beat drop locations
    """
    print("  Detecting hooks and beat drops...")

    # Calculate spectral features over time
    hop_length = 512
    frame_length = 2048

    # RMS energy
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]

    # Spectral centroid (brightness)
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]

    # Spectral flux (change in spectrum)
    spectral_flux = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)

    # Smooth the signals
    window = 20
    rms_smooth = np.convolve(rms, np.ones(window)/window, mode='same')

    # Detect beat drops: sudden decrease in energy followed by buildup
    beat_drops = []
    min_drop_duration = sr // hop_length  # ~1 second minimum

    for i in range(min_drop_duration, len(rms_smooth) - min_drop_duration):
        before_energy = np.mean(rms_smooth[i-min_drop_duration:i])
        at_point = rms_smooth[i]
        after_energy = np.mean(rms_smooth[i:i+min_drop_duration])

        # Look for significant energy dip followed by increase
        if at_point < before_energy * 0.4 and after_energy > at_point * 2:
            drop_time = librosa.frames_to_time(i, sr=sr, hop_length=hop_length)

            # Avoid duplicates within 2 seconds
            if not beat_drops or (drop_time - beat_drops[-1]['time']) > 2.0:
                beat_drops.append({
                    'time': float(drop_time),
                    'intensity': float(after_energy / (at_point + 0.001))
                })

    # Detect hooks: high energy + high spectral flux segments that repeat
    hooks = []

    # Find high-energy segments from structure
    for segment in structure:
        start_frame = librosa.time_to_frames(segment['start'], sr=sr, hop_length=hop_length)
        end_frame = librosa.time_to_frames(segment['end'], sr=sr, hop_length=hop_length)

        if end_frame > start_frame and end_frame <= len(rms_smooth):
            seg_energy = np.mean(rms_smooth[start_frame:end_frame])
            seg_flux = np.mean(spectral_flux[start_frame:end_frame])
            seg_brightness = np.mean(spectral_centroid[start_frame:end_frame])

            # Hooks are typically high energy, rhythmically active, bright sections
            hook_score = (seg_energy * 2 + seg_flux + seg_brightness / 5000)

            if hook_score > np.mean(rms_smooth) * 3:
                hooks.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'hook_score': float(hook_score),
                    'type': 'high_energy_hook'
                })

    # Sort hooks by score
    hooks = sorted(hooks, key=lambda x: -x['hook_score'])[:5]  # Top 5 hooks

    return {
        'hooks': hooks,
        'beat_drops': beat_drops,
        'primary_hook': hooks[0] if hooks else None,
        'drop_count': len(beat_drops)
    }


# =============================================================================
# HARMONIC RHYTHM ANALYSIS
# =============================================================================

def analyze_harmonic_rhythm(y, sr):
    """
    Analyzes how often the harmony/chords change in the song.

    Important for mashup creation - songs with similar harmonic rhythm
    mix together more naturally.

    Returns:
        dict: Harmonic rhythm characteristics
    """
    print("  Analyzing harmonic rhythm...")

    hop_length = 512

    # Extract chroma features
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)

    # Calculate harmonic change (how different each frame is from the previous)
    chroma_diff = np.diff(chroma, axis=1)
    harmonic_novelty = np.sqrt(np.sum(chroma_diff**2, axis=0))

    # Smooth the novelty curve
    window = 10
    harmonic_novelty_smooth = np.convolve(harmonic_novelty, np.ones(window)/window, mode='same')

    # Find chord change points (peaks in novelty)
    peaks, properties = scipy.signal.find_peaks(
        harmonic_novelty_smooth,
        height=np.mean(harmonic_novelty_smooth),
        distance=sr // hop_length // 2  # Minimum 0.5 second between changes
    )

    # Convert to time
    chord_change_times = librosa.frames_to_time(peaks, sr=sr, hop_length=hop_length)

    # Calculate statistics
    if len(chord_change_times) > 1:
        intervals = np.diff(chord_change_times)
        avg_chord_duration = float(np.mean(intervals))
        chord_change_rate = 60.0 / avg_chord_duration if avg_chord_duration > 0 else 0  # Changes per minute
    else:
        avg_chord_duration = 0
        chord_change_rate = 0

    # Classify harmonic rhythm
    if chord_change_rate < 15:
        rhythm_class = 'slow_harmonic_rhythm'
        rhythm_description = 'Slow chord changes - atmospheric/sustained'
    elif chord_change_rate < 30:
        rhythm_class = 'moderate_harmonic_rhythm'
        rhythm_description = 'Moderate chord changes - typical pop/film song'
    elif chord_change_rate < 60:
        rhythm_class = 'fast_harmonic_rhythm'
        rhythm_description = 'Fast chord changes - dynamic/energetic'
    else:
        rhythm_class = 'very_fast_harmonic_rhythm'
        rhythm_description = 'Very fast chord changes - jazz-influenced/complex'

    return {
        'chord_change_rate': float(chord_change_rate),
        'avg_chord_duration': avg_chord_duration,
        'total_chord_changes': len(peaks),
        'rhythm_class': rhythm_class,
        'rhythm_description': rhythm_description,
        'chord_change_times': [float(t) for t in chord_change_times[:20]]  # First 20
    }


# =============================================================================
# SPECTRAL CHARACTERISTICS FOR EQ MATCHING
# =============================================================================

def analyze_spectral_characteristics(y, sr):
    """
    Analyzes spectral characteristics crucial for EQ matching in mashups.

    When mixing songs, matching their spectral profiles creates smoother transitions.

    Returns:
        dict: Spectral analysis including brightness, bass character, etc.
    """
    print("  Analyzing spectral characteristics...")

    hop_length = 512

    # Spectral centroid (brightness)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    brightness = float(np.mean(centroid))

    # Spectral bandwidth
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=hop_length)[0]
    spectral_spread = float(np.mean(bandwidth))

    # Spectral rolloff (frequency below which 85% of energy is contained)
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)[0]
    rolloff_freq = float(np.mean(rolloff))

    # Spectral contrast (difference between peaks and valleys in spectrum)
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=hop_length)
    contrast_mean = [float(np.mean(contrast[i])) for i in range(contrast.shape[0])]

    # Bass analysis (energy in low frequencies)
    stft = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)

    # Sub-bass (20-60 Hz)
    sub_bass_mask = (freqs >= 20) & (freqs < 60)
    sub_bass_energy = float(np.mean(stft[sub_bass_mask, :])) if np.any(sub_bass_mask) else 0

    # Bass (60-250 Hz)
    bass_mask = (freqs >= 60) & (freqs < 250)
    bass_energy = float(np.mean(stft[bass_mask, :])) if np.any(bass_mask) else 0

    # Low-mids (250-500 Hz)
    low_mid_mask = (freqs >= 250) & (freqs < 500)
    low_mid_energy = float(np.mean(stft[low_mid_mask, :])) if np.any(low_mid_mask) else 0

    # Mids (500-2000 Hz)
    mid_mask = (freqs >= 500) & (freqs < 2000)
    mid_energy = float(np.mean(stft[mid_mask, :])) if np.any(mid_mask) else 0

    # High-mids (2000-4000 Hz)
    high_mid_mask = (freqs >= 2000) & (freqs < 4000)
    high_mid_energy = float(np.mean(stft[high_mid_mask, :])) if np.any(high_mid_mask) else 0

    # Highs (4000+ Hz)
    high_mask = freqs >= 4000
    high_energy = float(np.mean(stft[high_mask, :])) if np.any(high_mask) else 0

    # Calculate balance scores
    total_energy = sub_bass_energy + bass_energy + low_mid_energy + mid_energy + high_mid_energy + high_energy
    if total_energy > 0:
        bass_ratio = (sub_bass_energy + bass_energy) / total_energy
        mid_ratio = (low_mid_energy + mid_energy + high_mid_energy) / total_energy
        high_ratio = high_energy / total_energy
    else:
        bass_ratio = mid_ratio = high_ratio = 0.33

    # Classify brightness
    if brightness < 1500:
        brightness_class = 'dark'
    elif brightness < 3000:
        brightness_class = 'neutral'
    elif brightness < 4500:
        brightness_class = 'bright'
    else:
        brightness_class = 'very_bright'

    # Classify bass character
    if bass_ratio > 0.4:
        bass_class = 'bass_heavy'
    elif bass_ratio > 0.25:
        bass_class = 'balanced_bass'
    else:
        bass_class = 'light_bass'

    return {
        'brightness': brightness,
        'brightness_class': brightness_class,
        'spectral_spread': spectral_spread,
        'rolloff_frequency': rolloff_freq,
        'spectral_contrast': contrast_mean,
        'frequency_bands': {
            'sub_bass': sub_bass_energy,
            'bass': bass_energy,
            'low_mid': low_mid_energy,
            'mid': mid_energy,
            'high_mid': high_mid_energy,
            'high': high_energy
        },
        'band_ratios': {
            'bass_ratio': float(bass_ratio),
            'mid_ratio': float(mid_ratio),
            'high_ratio': float(high_ratio)
        },
        'bass_class': bass_class
    }


# =============================================================================
# PERCUSSION AND RHYTHM DENSITY ANALYSIS
# =============================================================================

def analyze_percussion_patterns(y, sr):
    """
    Analyzes percussion patterns and rhythmic density.

    Kannada songs often feature distinctive percussion like tabla, mridangam,
    and electronic drums. Understanding the rhythm helps in beat-matching.

    Returns:
        dict: Percussion analysis including density, patterns, and accents
    """
    print("  Analyzing percussion patterns...")

    hop_length = 512

    # Separate percussive component
    y_harmonic, y_percussive = librosa.effects.hpss(y)

    # Get onset envelope from percussive component
    onset_env = librosa.onset.onset_strength(y=y_percussive, sr=sr, hop_length=hop_length)

    # Detect onsets
    onsets = librosa.onset.onset_detect(y=y_percussive, sr=sr, hop_length=hop_length)
    onset_times = librosa.frames_to_time(onsets, sr=sr, hop_length=hop_length)

    # Calculate rhythm density (onsets per second)
    duration = librosa.get_duration(y=y, sr=sr)
    rhythm_density = len(onset_times) / duration if duration > 0 else 0

    # Analyze accent pattern by looking at onset strength periodicity
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

    # Calculate onset strength at beat positions
    beat_onset_strengths = []
    for beat in beats:
        if beat < len(onset_env):
            beat_onset_strengths.append(float(onset_env[beat]))

    # Find accent pattern (which beats are emphasized)
    if len(beat_onset_strengths) >= 8:
        # Reshape into groups of 8 (assuming 4/4 time, 2 bars)
        num_groups = len(beat_onset_strengths) // 8
        if num_groups > 0:
            beat_groups = np.array(beat_onset_strengths[:num_groups * 8]).reshape(num_groups, 8)
            avg_accent_pattern = np.mean(beat_groups, axis=0)
            accent_pattern = (avg_accent_pattern / np.max(avg_accent_pattern) * 100).astype(int).tolist()
        else:
            accent_pattern = [100, 50, 75, 50, 100, 50, 75, 50]  # Default
    else:
        accent_pattern = [100, 50, 75, 50, 100, 50, 75, 50]  # Default

    # Classify rhythm density
    if rhythm_density < 2:
        density_class = 'sparse'
        density_description = 'Minimal percussion - ballad/slow song'
    elif rhythm_density < 4:
        density_class = 'moderate'
        density_description = 'Moderate rhythm - typical film song'
    elif rhythm_density < 6:
        density_class = 'dense'
        density_description = 'Dense rhythm - dance/energetic song'
    else:
        density_class = 'very_dense'
        density_description = 'Very dense rhythm - fast-paced/folk dance'

    # Detect if there's a strong backbeat (emphasis on beats 2 and 4)
    has_backbeat = False
    if len(accent_pattern) >= 4:
        backbeat_strength = (accent_pattern[1] + accent_pattern[3]) / 2
        downbeat_strength = (accent_pattern[0] + accent_pattern[2]) / 2
        has_backbeat = backbeat_strength > downbeat_strength * 0.8

    return {
        'rhythm_density': float(rhythm_density),
        'density_class': density_class,
        'density_description': density_description,
        'onset_count': len(onset_times),
        'accent_pattern_8beat': accent_pattern,
        'has_backbeat': has_backbeat,
        'avg_onset_strength': float(np.mean(onset_env)),
        'tempo': float(tempo)
    }


# =============================================================================
# SONG SECTION CLASSIFICATION (PALLAVI, CHARANAM, INTERLUDE)
# =============================================================================

def classify_song_sections(y, sr, structure, vocal_regions):
    """
    Classifies song sections into traditional Kannada song structure.

    Kannada film songs typically follow: Intro -> Pallavi (Chorus) ->
    Charanam (Verse) -> Interlude -> Pallavi (repeat)

    Returns:
        dict: Section classification with timestamps
    """
    print("  Classifying song sections (Pallavi/Charanam/Interlude)...")

    hop_length = 512

    # Get features for each segment
    classified_sections = []

    # Create vocal presence map
    def has_vocals_at(time):
        for region in vocal_regions:
            if region['start'] <= time <= region['end']:
                return True
        return False

    for i, segment in enumerate(structure):
        start = segment['start']
        end = segment['end']
        duration = end - start
        mid_time = (start + end) / 2

        # Extract segment audio
        start_sample = int(start * sr)
        end_sample = int(end * sr)
        y_seg = y[start_sample:end_sample]

        if len(y_seg) < sr * 0.5:  # Skip very short segments
            continue

        # Calculate segment features
        rms = librosa.feature.rms(y=y_seg)[0]
        energy = float(np.mean(rms))

        spectral_centroid = librosa.feature.spectral_centroid(y=y_seg, sr=sr)[0]
        brightness = float(np.mean(spectral_centroid))

        # Check vocal presence
        has_vocals = has_vocals_at(mid_time)

        # Check if this is at the beginning (intro) or end (outro)
        total_duration = librosa.get_duration(y=y, sr=sr)
        is_intro_region = start < total_duration * 0.1
        is_outro_region = end > total_duration * 0.9

        # Classify section
        if is_intro_region and not has_vocals:
            section_type = 'intro'
        elif is_outro_region and not has_vocals:
            section_type = 'outro'
        elif not has_vocals and duration > 10:
            section_type = 'interlude'
        elif not has_vocals and duration <= 10:
            section_type = 'instrumental_break'
        elif has_vocals and energy > np.mean([s.get('energy', 0.5) for s in structure if 'energy' in s] or [0.5]):
            section_type = 'pallavi'  # Chorus - typically higher energy
        else:
            section_type = 'charanam'  # Verse

        classified_sections.append({
            'start': float(start),
            'end': float(end),
            'duration': float(duration),
            'section_type': section_type,
            'has_vocals': has_vocals,
            'energy': energy,
            'brightness': brightness,
            'segment_index': i
        })

    # Find repeated sections (potential pallavi/chorus)
    # Sections with similar features might be repetitions
    for i, sec1 in enumerate(classified_sections):
        sec1['is_repeat'] = False
        for j, sec2 in enumerate(classified_sections):
            if i != j and abs(sec1['energy'] - sec2['energy']) < 0.1:
                if abs(sec1['duration'] - sec2['duration']) < 2.0:
                    sec1['is_repeat'] = True
                    break

    return {
        'sections': classified_sections,
        'intro': next((s for s in classified_sections if s['section_type'] == 'intro'), None),
        'outro': next((s for s in classified_sections if s['section_type'] == 'outro'), None),
        'pallavis': [s for s in classified_sections if s['section_type'] == 'pallavi'],
        'charanams': [s for s in classified_sections if s['section_type'] == 'charanam'],
        'interludes': [s for s in classified_sections if s['section_type'] == 'interlude']
    }


# =============================================================================
# EMOTIONAL INTENSITY CURVE
# =============================================================================

def analyze_emotional_curve(y, sr):
    """
    Analyzes the emotional intensity curve throughout the song.

    Understanding how energy and emotion flow through a song helps in
    creating mashups that maintain emotional coherence.

    Returns:
        dict: Emotional intensity data over time
    """
    print("  Analyzing emotional intensity curve...")

    hop_length = 2048  # Larger hop for smoother curve

    # Calculate features at each point
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]

    # Normalize features
    rms_norm = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 0.001)
    centroid_norm = (spectral_centroid - np.min(spectral_centroid)) / (np.max(spectral_centroid) - np.min(spectral_centroid) + 0.001)

    # Combined intensity (energy + brightness)
    intensity = (rms_norm * 0.7 + centroid_norm * 0.3)

    # Smooth the curve
    window = 10
    intensity_smooth = np.convolve(intensity, np.ones(window)/window, mode='same')

    # Get timestamps
    times = librosa.frames_to_time(np.arange(len(intensity_smooth)), sr=sr, hop_length=hop_length)

    # Find peak moments
    peaks, _ = scipy.signal.find_peaks(intensity_smooth, height=0.7, distance=sr//hop_length*5)
    peak_times = times[peaks].tolist() if len(peaks) > 0 else []

    # Classify the overall arc
    first_quarter = np.mean(intensity_smooth[:len(intensity_smooth)//4])
    second_quarter = np.mean(intensity_smooth[len(intensity_smooth)//4:len(intensity_smooth)//2])
    third_quarter = np.mean(intensity_smooth[len(intensity_smooth)//2:3*len(intensity_smooth)//4])
    fourth_quarter = np.mean(intensity_smooth[3*len(intensity_smooth)//4:])

    quarters = [first_quarter, second_quarter, third_quarter, fourth_quarter]

    # Determine arc type
    if quarters[1] > quarters[0] and quarters[2] > quarters[1]:
        arc_type = 'building'
        arc_description = 'Intensity builds throughout'
    elif quarters[1] > quarters[0] and quarters[2] < quarters[1]:
        arc_type = 'peak_middle'
        arc_description = 'Peaks in the middle, classic song structure'
    elif quarters[0] > quarters[1]:
        arc_type = 'front_loaded'
        arc_description = 'High energy start, gradually decreases'
    elif quarters[3] > quarters[2]:
        arc_type = 'finale_build'
        arc_description = 'Builds to a finale'
    else:
        arc_type = 'consistent'
        arc_description = 'Relatively consistent energy throughout'

    # Downsample for storage (every 2 seconds)
    sample_interval = int(2 * sr / hop_length)
    curve_points = []
    for i in range(0, len(intensity_smooth), max(1, sample_interval)):
        curve_points.append({
            'time': float(times[i]) if i < len(times) else float(times[-1]),
            'intensity': float(intensity_smooth[i])
        })

    return {
        'arc_type': arc_type,
        'arc_description': arc_description,
        'peak_times': [float(t) for t in peak_times[:10]],  # Top 10 peaks
        'peak_count': len(peaks),
        'avg_intensity': float(np.mean(intensity_smooth)),
        'max_intensity': float(np.max(intensity_smooth)),
        'intensity_variance': float(np.var(intensity_smooth)),
        'quarter_intensities': [float(q) for q in quarters],
        'curve_points': curve_points[:50]  # First 50 points for visualization
    }


# =============================================================================
# MASHUP COMPATIBILITY SCORING FOR KANNADA SONGS
# =============================================================================

def calculate_kannada_mashup_compatibility(track1, track2):
    """
    Calculates comprehensive mashup compatibility score between two Kannada tracks.

    This goes beyond simple BPM/key matching to consider Kannada music-specific
    factors like tala, scale compatibility, and emotional matching.

    Returns:
        dict: Detailed compatibility analysis
    """
    score = 0
    factors = {}

    # 1. BPM Compatibility (0-100 points)
    bpm_diff = abs(track1['bpm'] - track2['bpm'])
    if bpm_diff <= 3:
        bpm_score = 100
    elif bpm_diff <= 8:
        bpm_score = 80
    elif bpm_diff <= 15:
        bpm_score = 50
    else:
        bpm_score = max(0, 100 - bpm_diff * 5)
    factors['bpm'] = {'score': bpm_score, 'difference': bpm_diff}
    score += bpm_score

    # 2. Key/Scale Compatibility (0-150 points)
    # Same key = 150, relative major/minor = 120, circle of fifths neighbor = 100
    key_diff = abs(track1['key'] - track2['key'])
    same_mode = track1['mode'] == track2['mode']

    if key_diff == 0 and same_mode:
        key_score = 150
    elif key_diff == 0:
        key_score = 130  # Same key, different mode (relative)
    elif key_diff in [5, 7]:  # Circle of fifths neighbors
        key_score = 100
    elif key_diff in [2, 10]:  # Whole step away
        key_score = 70
    else:
        key_score = max(0, 100 - key_diff * 15)

    factors['key'] = {'score': key_score, 'key_difference': key_diff, 'same_mode': same_mode}
    score += key_score

    # 3. Tala Compatibility (0-80 points) - NEW for Kannada
    if 'tala' in track1 and 'tala' in track2:
        if track1['tala']['tala_key'] == track2['tala']['tala_key']:
            tala_score = 80
        elif track1['tala']['beats_per_cycle'] == track2['tala']['beats_per_cycle']:
            tala_score = 60
        else:
            tala_score = 20
    else:
        tala_score = 40  # Unknown, neutral score

    factors['tala'] = {'score': tala_score}
    score += tala_score

    # 4. Scale/Ragam Compatibility (0-80 points) - NEW for Kannada
    if 'scale' in track1 and 'scale' in track2:
        scale1 = track1['scale']['scale_name']
        scale2 = track2['scale']['scale_name']
        emotion1 = track1['scale']['emotional_category']
        emotion2 = track2['scale']['emotional_category']

        if scale1 == scale2:
            scale_score = 80
        elif emotion1 == emotion2:
            scale_score = 60
        else:
            # Check for scale note overlap
            notes1 = set(track1['scale']['scale_notes'])
            notes2 = set(track2['scale']['scale_notes'])
            overlap = len(notes1.intersection(notes2)) / max(len(notes1), len(notes2))
            scale_score = int(overlap * 50)
    else:
        scale_score = 40

    factors['scale'] = {'score': scale_score}
    score += scale_score

    # 5. Energy Compatibility (0-60 points)
    energy_diff = abs(track1['energy'] - track2['energy'])
    if energy_diff < 0.1:
        energy_score = 60
    elif energy_diff < 0.2:
        energy_score = 45
    elif energy_diff < 0.3:
        energy_score = 30
    else:
        energy_score = 15

    factors['energy'] = {'score': energy_score, 'difference': energy_diff}
    score += energy_score

    # 6. Spectral Compatibility (0-50 points)
    if 'spectral' in track1 and 'spectral' in track2:
        brightness_diff = abs(track1['spectral']['brightness'] - track2['spectral']['brightness']) / 5000
        bass_match = track1['spectral']['bass_class'] == track2['spectral']['bass_class']

        spectral_score = max(0, 30 - brightness_diff * 30)
        if bass_match:
            spectral_score += 20
    else:
        spectral_score = 25

    factors['spectral'] = {'score': spectral_score}
    score += spectral_score

    # 7. Harmonic Rhythm Compatibility (0-40 points)
    if 'harmonic_rhythm' in track1 and 'harmonic_rhythm' in track2:
        hr_class1 = track1['harmonic_rhythm']['rhythm_class']
        hr_class2 = track2['harmonic_rhythm']['rhythm_class']

        if hr_class1 == hr_class2:
            hr_score = 40
        else:
            hr_score = 20
    else:
        hr_score = 20

    factors['harmonic_rhythm'] = {'score': hr_score}
    score += hr_score

    # 8. Vocal Clash Penalty (-100 points if both have vocals in same regions)
    vocal_clash = False
    if track1.get('has_vocals') and track2.get('has_vocals'):
        vocal_clash = True
        score -= 100

    factors['vocal_clash'] = {'has_clash': vocal_clash, 'penalty': -100 if vocal_clash else 0}

    # Calculate overall compatibility grade
    max_score = 100 + 150 + 80 + 80 + 60 + 50 + 40  # 560 max
    percentage = (score / max_score) * 100

    if percentage >= 80:
        grade = 'A'
        recommendation = 'Excellent match - perfect for mashup'
    elif percentage >= 65:
        grade = 'B'
        recommendation = 'Good match - will work well with minor adjustments'
    elif percentage >= 50:
        grade = 'C'
        recommendation = 'Moderate match - requires pitch/tempo adjustment'
    elif percentage >= 35:
        grade = 'D'
        recommendation = 'Challenging match - significant processing needed'
    else:
        grade = 'F'
        recommendation = 'Poor match - not recommended for mashup'

    return {
        'total_score': score,
        'max_possible': max_score,
        'percentage': float(percentage),
        'grade': grade,
        'recommendation': recommendation,
        'factors': factors
    }


# =============================================================================
# MULTI-TRACK MASHUP PLANNER
# =============================================================================

def plan_kannada_mashup(all_tracks_analysis, target_duration_minutes=10, style='energetic'):
    """
    Plans a complete Kannada mashup from multiple tracks.

    This is the core function for creating professional mashups - it:
    1. Finds the best track combinations
    2. Orders them for optimal flow
    3. Identifies transition points
    4. Generates a complete mashup timeline

    Args:
        all_tracks_analysis: List of analysis dicts from analyze_kannada_track_for_mashup
        target_duration_minutes: Target mashup length
        style: 'energetic', 'smooth', or 'showcase'

    Returns:
        dict: Complete mashup plan with timeline
    """
    print(f"\n{'='*60}")
    print("KANNADA MASHUP PLANNER")
    print(f"Planning {style} mashup from {len(all_tracks_analysis)} tracks")
    print(f"Target duration: {target_duration_minutes} minutes")
    print(f"{'='*60}\n")

    if len(all_tracks_analysis) < 2:
        return {'error': 'Need at least 2 tracks for a mashup'}

    # Calculate all pairwise compatibility scores
    print("Calculating track compatibility matrix...")
    compatibility_matrix = {}
    for i, track1 in enumerate(all_tracks_analysis):
        for j, track2 in enumerate(all_tracks_analysis):
            if i != j:
                key = (track1['filename'], track2['filename'])
                compatibility_matrix[key] = calculate_kannada_mashup_compatibility(track1, track2)

    # Find best pairs
    best_pairs = sorted(
        compatibility_matrix.items(),
        key=lambda x: x[1]['percentage'],
        reverse=True
    )

    print(f"\nTop 5 compatible pairs:")
    for (t1, t2), compat in best_pairs[:5]:
        print(f"  {t1} -> {t2}: {compat['percentage']:.1f}% ({compat['grade']})")

    # Build optimal setlist using greedy algorithm
    target_duration_sec = target_duration_minutes * 60
    tracks_by_name = {t['filename']: t for t in all_tracks_analysis}

    # Sort tracks by energy for different styles
    if style == 'energetic':
        # Start medium, build to high, end high
        sorted_tracks = sorted(all_tracks_analysis, key=lambda x: x['energy'])
        start_track = sorted_tracks[len(sorted_tracks) // 3]  # Medium energy start
    elif style == 'smooth':
        # Consistent energy throughout
        avg_energy = sum(t['energy'] for t in all_tracks_analysis) / len(all_tracks_analysis)
        sorted_tracks = sorted(all_tracks_analysis, key=lambda x: abs(x['energy'] - avg_energy))
        start_track = sorted_tracks[0]
    else:  # showcase - feature all hooks
        # Order by hook score
        sorted_tracks = sorted(all_tracks_analysis,
                              key=lambda x: x.get('hooks_and_drops', {}).get('hooks', [{}])[0].get('hook_score', 0) if x.get('hooks_and_drops', {}).get('hooks') else 0,
                              reverse=True)
        start_track = sorted_tracks[0]

    # Build setlist
    setlist = [start_track]
    remaining = [t for t in all_tracks_analysis if t['filename'] != start_track['filename']]
    current_duration = 0

    while remaining and current_duration < target_duration_sec:
        current_track = setlist[-1]

        # Find best next track
        best_next = None
        best_score = -1

        for candidate in remaining:
            key = (current_track['filename'], candidate['filename'])
            if key in compatibility_matrix:
                score = compatibility_matrix[key]['percentage']

                # Bonus for energy progression in energetic style
                if style == 'energetic':
                    energy_diff = candidate['energy'] - current_track['energy']
                    if energy_diff > 0:
                        score += 10  # Reward energy increase

                if score > best_score:
                    best_score = score
                    best_next = candidate

        if best_next:
            setlist.append(best_next)
            remaining.remove(best_next)

            # Estimate duration (use 60% of each track for energetic, 80% for smooth)
            clip_ratio = 0.6 if style == 'energetic' else 0.8
            current_duration += best_next['duration'] * clip_ratio
        else:
            break

    # Generate detailed mashup timeline
    print(f"\nGenerating mashup timeline with {len(setlist)} tracks...")
    timeline = []
    mashup_time = 0

    for i, track in enumerate(setlist):
        # Determine clip points
        cue_points = track.get('dj_cue_points', {})
        mix_in = cue_points.get('mix_in', {}).get('time', 0)
        mix_out = cue_points.get('mix_out', {}).get('time', track['duration'] * 0.8)

        # For energetic style, use shorter clips centered on hooks
        if style == 'energetic':
            primary_hook = track.get('hooks_and_drops', {}).get('primary_hook')
            if primary_hook:
                # Center clip around hook
                hook_time = primary_hook['start']
                clip_duration = min(60, track['duration'] * 0.4)  # Max 60 seconds
                clip_start = max(0, hook_time - clip_duration / 3)
                clip_end = min(track['duration'], clip_start + clip_duration)
            else:
                clip_start = mix_in
                clip_end = mix_out
        else:
            clip_start = mix_in
            clip_end = mix_out

        clip_duration = clip_end - clip_start

        # Determine transition to next track
        if i < len(setlist) - 1:
            next_track = setlist[i + 1]
            key = (track['filename'], next_track['filename'])
            compat = compatibility_matrix.get(key, {})

            # Choose transition type based on compatibility and style
            if compat.get('percentage', 0) > 70:
                transition_type = 'eq_swap'
                transition_bars = 8
            elif compat.get('percentage', 0) > 50:
                transition_type = 'filter_sweep'
                transition_bars = 4
            else:
                transition_type = 'drop_swap'
                transition_bars = 0

            transition_duration = (60 / track['bpm']) * 4 * transition_bars  # Convert bars to seconds
        else:
            transition_type = 'fade_out'
            transition_duration = 4
            transition_bars = 0

        timeline.append({
            'position': i + 1,
            'track': track['filename'],
            'bpm': track['bpm'],
            'key': track['key_str'],
            'energy': track['energy'],
            'mashup_start_time': mashup_time,
            'clip_start': float(clip_start),
            'clip_end': float(clip_end),
            'clip_duration': float(clip_duration),
            'transition_to_next': transition_type,
            'transition_duration': float(transition_duration),
            'transition_bars': transition_bars,
            'notes': f"Scale: {track.get('scale', {}).get('scale_name', 'unknown')}, Style: {track.get('anand_audio_patterns', {}).get('song_style', 'unknown')}"
        })

        mashup_time += clip_duration - transition_duration  # Overlap during transition

    # Calculate final mashup stats
    total_duration = sum(t['clip_duration'] for t in timeline) - sum(t['transition_duration'] for t in timeline[:-1])

    # Find potential problem areas
    warnings = []
    for i in range(len(timeline) - 1):
        t1 = timeline[i]
        t2 = timeline[i + 1]
        bpm_diff = abs(t1['bpm'] - t2['bpm'])
        if bpm_diff > 8:
            warnings.append(f"Large BPM jump ({bpm_diff:.1f}) between {t1['track']} and {t2['track']}")

    # Generate mixing instructions
    mixing_instructions = []
    for i, item in enumerate(timeline):
        instruction = {
            'step': i + 1,
            'action': f"Play {item['track']}",
            'start_at': f"{item['clip_start']:.1f}s",
            'play_until': f"{item['clip_end']:.1f}s",
        }
        if i < len(timeline) - 1:
            instruction['transition'] = f"{item['transition_type']} over {item['transition_bars']} bars into {timeline[i+1]['track']}"
        else:
            instruction['transition'] = 'Fade out to end mashup'
        mixing_instructions.append(instruction)

    return {
        'style': style,
        'total_tracks': len(setlist),
        'estimated_duration_seconds': float(total_duration),
        'estimated_duration_minutes': float(total_duration / 60),
        'timeline': timeline,
        'mixing_instructions': mixing_instructions,
        'best_pairs': [(t1, t2, c['percentage'], c['grade']) for (t1, t2), c in best_pairs[:10]],
        'warnings': warnings,
        'track_order': [t['filename'] for t in setlist],
        'average_compatibility': sum(compatibility_matrix[(setlist[i]['filename'], setlist[i+1]['filename'])]['percentage']
                                    for i in range(len(setlist)-1)) / (len(setlist)-1) if len(setlist) > 1 else 0
    }


def generate_mashup_report(mashup_plan):
    """
    Generates a human-readable mashup report.

    Returns:
        str: Formatted report for the DJ
    """
    report = []
    report.append("=" * 60)
    report.append("KANNADA MASHUP REPORT")
    report.append("=" * 60)
    report.append("")
    report.append(f"Style: {mashup_plan['style'].upper()}")
    report.append(f"Total Tracks: {mashup_plan['total_tracks']}")
    report.append(f"Estimated Duration: {mashup_plan['estimated_duration_minutes']:.1f} minutes")
    report.append(f"Average Compatibility: {mashup_plan['average_compatibility']:.1f}%")
    report.append("")
    report.append("-" * 60)
    report.append("TRACK ORDER")
    report.append("-" * 60)

    for item in mashup_plan['timeline']:
        report.append(f"\n{item['position']}. {item['track']}")
        report.append(f"   BPM: {item['bpm']:.1f} | Key: {item['key']} | Energy: {item['energy']:.2f}")
        report.append(f"   Play: {item['clip_start']:.1f}s - {item['clip_end']:.1f}s ({item['clip_duration']:.1f}s)")
        report.append(f"   Transition: {item['transition_to_next']} ({item['transition_bars']} bars)")

    report.append("")
    report.append("-" * 60)
    report.append("MIXING INSTRUCTIONS")
    report.append("-" * 60)

    for instr in mashup_plan['mixing_instructions']:
        report.append(f"\nStep {instr['step']}: {instr['action']}")
        report.append(f"  Start at: {instr['start_at']}")
        report.append(f"  Play until: {instr['play_until']}")
        report.append(f"  Then: {instr['transition']}")

    if mashup_plan['warnings']:
        report.append("")
        report.append("-" * 60)
        report.append("WARNINGS")
        report.append("-" * 60)
        for warning in mashup_plan['warnings']:
            report.append(f"  ⚠ {warning}")

    report.append("")
    report.append("=" * 60)

    return "\n".join(report)


# =============================================================================
# MAIN EXTENDED ANALYSIS FUNCTION (V2 with DJ Features)
# =============================================================================

def analyze_kannada_track_for_mashup(file_path, venv_path=None):
    """
    Performs comprehensive deep analysis of a Kannada track for mashup creation.

    This combines the base analysis with Kannada music-specific parameters
    essential for professional DJ mixing of Anand Audio style songs.

    Args:
        file_path: Path to the audio file
        venv_path: Path to virtual environment (for Demucs)

    Returns:
        dict: Complete analysis with all mashup-essential parameters
    """
    print(f"\n{'='*60}")
    print(f"KANNADA MASHUP DEEP ANALYSIS")
    print(f"File: {os.path.basename(file_path)}")
    print(f"{'='*60}\n")

    # Get venv path if not provided
    if venv_path is None:
        venv_path = os.environ.get('VIRTUAL_ENV')
        if not venv_path:
            venv_path = os.path.abspath("./venv")

    # 1. Load audio
    print("Loading audio...")
    y, sr = librosa.load(file_path)
    duration = librosa.get_duration(y=y, sr=sr)

    # 2. Run base analysis
    print("\n--- BASE ANALYSIS ---")
    base_features = analyze_audio_local(file_path)

    # 3. Vocal analysis
    print("\n--- VOCAL ANALYSIS ---")
    vocal_regions = analyze_vocal_presence(file_path, venv_path)
    has_vocals = len(vocal_regions) > 0

    # 4. Tala detection
    print("\n--- TALA DETECTION ---")
    tala_info = detect_tala(y, sr, base_features['bpm'])

    # 5. Scale/Ragam analysis
    print("\n--- SCALE/RAGAM ANALYSIS ---")
    scale_info = detect_scale_profile(y, sr)

    # 6. Hook and beat drop detection
    print("\n--- HOOK & BEAT DROP DETECTION ---")
    hooks_drops = detect_hooks_and_drops(y, sr, base_features['structure'])

    # 7. Harmonic rhythm analysis
    print("\n--- HARMONIC RHYTHM ANALYSIS ---")
    harmonic_rhythm = analyze_harmonic_rhythm(y, sr)

    # 8. Spectral characteristics
    print("\n--- SPECTRAL ANALYSIS ---")
    spectral = analyze_spectral_characteristics(y, sr)

    # 9. Percussion analysis
    print("\n--- PERCUSSION ANALYSIS ---")
    percussion = analyze_percussion_patterns(y, sr)

    # 10. Section classification
    print("\n--- SECTION CLASSIFICATION ---")
    sections = classify_song_sections(y, sr, base_features['structure'], vocal_regions)

    # 11. Emotional curve
    print("\n--- EMOTIONAL INTENSITY ANALYSIS ---")
    emotional_curve = analyze_emotional_curve(y, sr)

    # ========== NEW DJ FEATURES (V2) ==========

    # 12. Beat grid and downbeat detection
    print("\n--- BEAT GRID DETECTION ---")
    beat_grid = detect_beat_grid(y, sr)

    # 13. Phrase boundary detection
    print("\n--- PHRASE BOUNDARY DETECTION ---")
    phrases = detect_phrase_boundaries(y, sr, beat_grid, duration)

    # 14. Vocal-free mix zones
    print("\n--- VOCAL-FREE ZONE DETECTION ---")
    vocal_free_zones = detect_vocal_free_zones(vocal_regions, phrases, duration)

    # 15. Anand Audio specific patterns
    print("\n--- ANAND AUDIO PATTERN DETECTION ---")
    anand_patterns = detect_anand_audio_patterns(y, sr, sections, vocal_regions, duration)

    # Compile complete analysis (partial - will add DJ cue points after)
    analysis = {
        # File info
        'file_path': file_path,
        'filename': os.path.basename(file_path),
        'duration': float(duration),

        # Base features
        'bpm': base_features['bpm'],
        'key': base_features['key'],
        'mode': base_features['mode'],
        'key_str': base_features['key_str'],
        'energy': base_features['energy'],
        'structure': base_features['structure'],

        # Vocal info
        'has_vocals': has_vocals,
        'vocal_regions': vocal_regions,
        'vocal_percentage': sum((r['end'] - r['start']) for r in vocal_regions) / duration * 100 if duration > 0 else 0,

        # Kannada music-specific
        'tala': tala_info,
        'scale': scale_info,

        # Mashup-essential
        'hooks_and_drops': hooks_drops,
        'harmonic_rhythm': harmonic_rhythm,
        'spectral': spectral,
        'percussion': percussion,
        'sections': sections,
        'emotional_curve': emotional_curve,

        # NEW: DJ-essential features
        'beat_grid': beat_grid,
        'phrases': phrases,
        'vocal_free_zones': vocal_free_zones,
        'anand_audio_patterns': anand_patterns,
    }

    # 16. DJ Cue Points (needs other analysis data)
    print("\n--- DJ CUE POINT GENERATION ---")
    dj_cue_points = generate_dj_cue_points(y, sr, beat_grid, phrases, sections, hooks_drops, vocal_regions, duration)
    analysis['dj_cue_points'] = dj_cue_points

    # 17. Transition recommendations
    print("\n--- TRANSITION RECOMMENDATIONS ---")
    transitions = recommend_transitions(analysis)
    analysis['transition_recommendations'] = transitions

    # Calculate DJ-friendly summary fields
    analysis['best_mix_in_point'] = dj_cue_points['mix_in']['time']
    analysis['best_mix_out_point'] = dj_cue_points['mix_out']['time']
    analysis['best_hook_time'] = hooks_drops['primary_hook']['start'] if hooks_drops['primary_hook'] else None
    analysis['best_drop_time'] = dj_cue_points['drop']['time']
    analysis['best_loop'] = dj_cue_points['loop_points'][0] if dj_cue_points['loop_points'] else None

    # Print comprehensive summary
    print(f"\n{'='*60}")
    print("KANNADA MASHUP ANALYSIS SUMMARY (V2)")
    print(f"{'='*60}")
    print(f"\n[BASIC INFO]")
    print(f"  BPM: {analysis['bpm']:.1f} (Stable: {beat_grid['is_tempo_stable']})")
    print(f"  Key: {analysis['key_str']}")
    print(f"  Energy: {analysis['energy']:.2f}")
    print(f"  Duration: {duration:.1f}s ({duration/60:.1f} min)")

    print(f"\n[KANNADA MUSIC CHARACTERISTICS]")
    print(f"  Tala: {analysis['tala']['tala_name']} (confidence: {analysis['tala']['confidence']:.2f})")
    print(f"  Scale: {analysis['scale']['scale_name']} ({analysis['scale']['emotional_category']})")
    print(f"  Song Style: {anand_patterns['song_style']}")
    if anand_patterns['has_dialogue_intro']:
        print(f"  WARNING: Has dialogue intro - skip to {anand_patterns['skip_intro_until']:.1f}s")

    print(f"\n[SPECTRAL PROFILE]")
    print(f"  Brightness: {analysis['spectral']['brightness_class']}")
    print(f"  Bass: {analysis['spectral']['bass_class']}")
    print(f"  Rhythm Density: {analysis['percussion']['density_class']}")

    print(f"\n[SONG STRUCTURE]")
    print(f"  Emotional Arc: {analysis['emotional_curve']['arc_type']}")
    print(f"  Hooks Found: {len(analysis['hooks_and_drops']['hooks'])}")
    print(f"  Beat Drops: {analysis['hooks_and_drops']['drop_count']}")
    print(f"  Pallavis (Chorus): {len(analysis['sections']['pallavis'])}")
    print(f"  Charanams (Verse): {len(analysis['sections']['charanams'])}")
    print(f"  Interludes: {len(analysis['sections']['interludes'])}")

    print(f"\n[DJ CUE POINTS]")
    print(f"  MIX IN:  {dj_cue_points['mix_in']['time']:.1f}s ({dj_cue_points['mix_in']['reason']})")
    print(f"  MIX OUT: {dj_cue_points['mix_out']['time']:.1f}s ({dj_cue_points['mix_out']['reason']})")
    print(f"  DROP:    {dj_cue_points['drop']['time']:.1f}s ({dj_cue_points['drop']['reason']})")
    if dj_cue_points['loop_points']:
        best_loop = dj_cue_points['loop_points'][0]
        print(f"  LOOP:    {best_loop['start']:.1f}s - {best_loop['end']:.1f}s ({best_loop['bars']} bars, {best_loop['quality']})")

    print(f"\n[VOCAL-FREE MIX ZONES]")
    print(f"  Total vocal-free: {vocal_free_zones['vocal_free_percentage']:.1f}% of track")
    print(f"  Intro zones: {len(vocal_free_zones['intro_zones'])}")
    print(f"  Outro zones: {len(vocal_free_zones['outro_zones'])}")
    print(f"  Middle zones: {len(vocal_free_zones['middle_zones'])}")

    print(f"\n[TRANSITION RECOMMENDATIONS]")
    print(f"  Best mix-in method: {transitions['best_mix_in']['method']}")
    print(f"  Best mix-out method: {transitions['best_mix_out']['method']}")

    print(f"\n[PHRASE GRID]")
    print(f"  First downbeat: {beat_grid['first_downbeat']:.2f}s")
    print(f"  Bar duration: {phrases.get('bar_duration_sec', 0):.2f}s")
    print(f"  Primary phrase length: {phrases['primary_phrase_length']} bars")
    print(f"  8-bar phrases: {len(phrases['8_bar_phrases'])}")

    print(f"{'='*60}\n")

    return analysis


def analyze_mashup_compatibility(track1_analysis, track2_analysis):
    """
    Analyzes compatibility between two tracks for mashup creation.

    Args:
        track1_analysis: Analysis dict from analyze_kannada_track_for_mashup
        track2_analysis: Analysis dict from analyze_kannada_track_for_mashup

    Returns:
        dict: Detailed compatibility analysis
    """
    return calculate_kannada_mashup_compatibility(track1_analysis, track2_analysis)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """Command-line interface for Kannada mashup analysis."""
    import argparse
    import glob

    parser = argparse.ArgumentParser(
        description="Kannada Mashup Analyzer V2 - Professional DJ analysis for Anand Audio style songs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single track
  python kannada_mashup_analyzer.py song.mp3

  # Compare two tracks for compatibility
  python kannada_mashup_analyzer.py song1.mp3 --compare song2.mp3

  # Plan a mashup from a directory of songs
  python kannada_mashup_analyzer.py --mashup-dir ./songs/ --style energetic --duration 10

  # Analyze and save results
  python kannada_mashup_analyzer.py song.mp3 --output analysis.json
        """
    )

    # Single file analysis
    parser.add_argument(
        "file_path",
        nargs='?',
        help="Path to the audio file to analyze"
    )

    # Comparison mode
    parser.add_argument(
        "--compare",
        help="Path to second audio file for compatibility analysis"
    )

    # Mashup planning mode
    parser.add_argument(
        "--mashup-dir",
        help="Directory containing songs for mashup planning"
    )
    parser.add_argument(
        "--style",
        choices=['energetic', 'smooth', 'showcase'],
        default='energetic',
        help="Mashup style (default: energetic)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=10,
        help="Target mashup duration in minutes (default: 10)"
    )

    # Output options
    parser.add_argument(
        "--output",
        help="Output JSON file path for analysis results"
    )
    parser.add_argument(
        "--report",
        help="Output text file path for human-readable mashup report"
    )

    # Environment
    parser.add_argument(
        "--venv",
        help="Path to virtual environment for Demucs"
    )

    args = parser.parse_args()

    # Mashup planning mode
    if args.mashup_dir:
        if not os.path.isdir(args.mashup_dir):
            print(f"Error: Directory not found: {args.mashup_dir}")
            return

        # Find all MP3 files
        mp3_files = glob.glob(os.path.join(args.mashup_dir, "*.mp3"))
        if len(mp3_files) < 2:
            print(f"Error: Need at least 2 MP3 files for mashup planning. Found: {len(mp3_files)}")
            return

        print(f"\nFound {len(mp3_files)} tracks for mashup planning")
        print("=" * 60)

        # Analyze all tracks
        all_analyses = []
        for mp3_file in mp3_files:
            analysis = analyze_kannada_track_for_mashup(mp3_file, args.venv)
            all_analyses.append(analysis)

        # Plan the mashup
        mashup_plan = plan_kannada_mashup(
            all_analyses,
            target_duration_minutes=args.duration,
            style=args.style
        )

        # Generate and print report
        report = generate_mashup_report(mashup_plan)
        print(report)

        # Save report if requested
        if args.report:
            with open(args.report, 'w') as f:
                f.write(report)
            print(f"\nReport saved to {args.report}")

        # Save JSON if requested
        if args.output:
            import json
            output_data = {
                'analyses': all_analyses,
                'mashup_plan': mashup_plan
            }
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
            print(f"Full analysis saved to {args.output}")

        return

    # Single file or comparison mode
    if not args.file_path:
        parser.print_help()
        return

    # Run analysis
    analysis1 = analyze_kannada_track_for_mashup(args.file_path, args.venv)

    # Compare if second file provided
    if args.compare:
        analysis2 = analyze_kannada_track_for_mashup(args.compare, args.venv)
        compatibility = analyze_mashup_compatibility(analysis1, analysis2)

        print(f"\n{'='*60}")
        print("MASHUP COMPATIBILITY ANALYSIS")
        print(f"{'='*60}")
        print(f"Track 1: {analysis1['filename']}")
        print(f"Track 2: {analysis2['filename']}")
        print(f"\nCompatibility Score: {compatibility['percentage']:.1f}%")
        print(f"Grade: {compatibility['grade']}")
        print(f"Recommendation: {compatibility['recommendation']}")
        print(f"\nFactor Breakdown:")
        for factor, data in compatibility['factors'].items():
            print(f"  {factor}: {data.get('score', 'N/A')} points")
        print(f"\n[SUGGESTED TRANSITION]")
        print(f"  Mix out of Track 1 at: {analysis1['best_mix_out_point']:.1f}s")
        print(f"  Mix in Track 2 at: {analysis2['best_mix_in_point']:.1f}s")
        print(f"  Recommended method: {analysis1['transition_recommendations']['best_mix_out']['method']}")
        print(f"{'='*60}\n")

    # Save to file if output path provided
    if args.output:
        import json
        output_data = {
            'track1': analysis1,
        }
        if args.compare:
            output_data['track2'] = analysis2
            output_data['compatibility'] = compatibility

        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"Analysis saved to {args.output}")


if __name__ == "__main__":
    main()
