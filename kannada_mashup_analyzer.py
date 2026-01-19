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
# -----------------------------------------------------------------------------

import os
import sys
import numpy as np
import librosa
import scipy.signal
from collections import defaultdict
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
# MAIN EXTENDED ANALYSIS FUNCTION
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

    # Compile complete analysis
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

        # Best mix points
        'best_mix_in_point': sections['intro']['start'] if sections['intro'] else 0,
        'best_mix_out_point': sections['outro']['start'] if sections['outro'] else duration - 10,
        'best_hook_time': hooks_drops['primary_hook']['start'] if hooks_drops['primary_hook'] else None,
    }

    # Print summary
    print(f"\n{'='*60}")
    print("ANALYSIS SUMMARY")
    print(f"{'='*60}")
    print(f"BPM: {analysis['bpm']:.1f}")
    print(f"Key: {analysis['key_str']}")
    print(f"Energy: {analysis['energy']:.2f}")
    print(f"Tala: {analysis['tala']['tala_name']} (confidence: {analysis['tala']['confidence']:.2f})")
    print(f"Scale: {analysis['scale']['scale_name']} ({analysis['scale']['emotional_category']})")
    print(f"Brightness: {analysis['spectral']['brightness_class']}")
    print(f"Bass: {analysis['spectral']['bass_class']}")
    print(f"Rhythm Density: {analysis['percussion']['density_class']}")
    print(f"Emotional Arc: {analysis['emotional_curve']['arc_type']}")
    print(f"Hooks Found: {len(analysis['hooks_and_drops']['hooks'])}")
    print(f"Beat Drops: {analysis['hooks_and_drops']['drop_count']}")
    print(f"Pallavis (Chorus): {len(analysis['sections']['pallavis'])}")
    print(f"Charanams (Verse): {len(analysis['sections']['charanams'])}")
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

    parser = argparse.ArgumentParser(
        description="Kannada Mashup Analyzer - Deep analysis for Anand Audio style songs"
    )
    parser.add_argument(
        "file_path",
        help="Path to the audio file to analyze"
    )
    parser.add_argument(
        "--compare",
        help="Path to second audio file for compatibility analysis"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path for analysis results"
    )
    parser.add_argument(
        "--venv",
        help="Path to virtual environment for Demucs"
    )

    args = parser.parse_args()

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
            print(f"  {factor}: {data['score']} points")
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
