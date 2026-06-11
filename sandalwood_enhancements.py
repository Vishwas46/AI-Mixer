# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# sandalwood_enhancements.py
# Advanced Sandalwood/Kannada music enhancements:
# - Singer detection and vocal EQ profiles
# - Film era detection (decade/style classification)
# - Audio file validation and corruption detection
# - Real-time preview generation
# - Custom cue point management

import os
import json
import tempfile
import numpy as np
import librosa
import soundfile as sf
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any
from pydub import AudioSegment

# -----------------------------------------------------------------------------
# SINGER DETECTION AND EQ PROFILES
# -----------------------------------------------------------------------------

# Famous Kannada playback singers with their vocal characteristics
KANNADA_SINGER_PROFILES = {
    'dr_rajkumar': {
        'name': 'Dr. Rajkumar',
        'era': '1960s-1990s',
        'vocal_range_hz': (100, 400),  # Baritone
        'characteristics': ['deep', 'classical', 'powerful'],
        'eq_profile': {
            'low_shelf_db': 2,      # Boost warmth
            'low_shelf_freq': 200,
            'mid_boost_db': 1,
            'mid_freq': 2500,
            'high_shelf_db': -1,    # Slight cut for warmth
            'high_shelf_freq': 8000,
            'presence_boost_db': 2,
            'presence_freq': 3500,
        },
        'spectral_centroid_range': (1200, 2000),
        'pitch_std_range': (30, 80),  # Stable classical style
    },
    'spb': {
        'name': 'S.P. Balasubrahmanyam',
        'era': '1970s-2020s',
        'vocal_range_hz': (120, 500),  # Tenor
        'characteristics': ['versatile', 'melodic', 'smooth'],
        'eq_profile': {
            'low_shelf_db': 0,
            'low_shelf_freq': 150,
            'mid_boost_db': 2,
            'mid_freq': 3000,
            'high_shelf_db': 1,
            'high_shelf_freq': 10000,
            'presence_boost_db': 1.5,
            'presence_freq': 4000,
        },
        'spectral_centroid_range': (1800, 2800),
        'pitch_std_range': (40, 100),
    },
    'rajesh_krishnan': {
        'name': 'Rajesh Krishnan',
        'era': '1990s-present',
        'vocal_range_hz': (130, 450),
        'characteristics': ['energetic', 'filmi', 'romantic'],
        'eq_profile': {
            'low_shelf_db': 1,
            'low_shelf_freq': 180,
            'mid_boost_db': 2,
            'mid_freq': 2800,
            'high_shelf_db': 2,
            'high_shelf_freq': 12000,
            'presence_boost_db': 2,
            'presence_freq': 5000,
        },
        'spectral_centroid_range': (2000, 3200),
        'pitch_std_range': (50, 120),
    },
    'shreya_ghoshal': {
        'name': 'Shreya Ghoshal',
        'era': '2000s-present',
        'vocal_range_hz': (200, 800),  # Soprano
        'characteristics': ['classical', 'bright', 'ornamental'],
        'eq_profile': {
            'low_shelf_db': -1,
            'low_shelf_freq': 150,
            'mid_boost_db': 1,
            'mid_freq': 3500,
            'high_shelf_db': 2,
            'high_shelf_freq': 12000,
            'presence_boost_db': 2,
            'presence_freq': 6000,
        },
        'spectral_centroid_range': (2500, 4000),
        'pitch_std_range': (60, 150),  # More ornamental
    },
    'sonu_nigam': {
        'name': 'Sonu Nigam',
        'era': '1990s-present',
        'vocal_range_hz': (120, 550),
        'characteristics': ['versatile', 'powerful', 'modern'],
        'eq_profile': {
            'low_shelf_db': 1,
            'low_shelf_freq': 160,
            'mid_boost_db': 1.5,
            'mid_freq': 3200,
            'high_shelf_db': 1.5,
            'high_shelf_freq': 11000,
            'presence_boost_db': 2,
            'presence_freq': 4500,
        },
        'spectral_centroid_range': (2200, 3500),
        'pitch_std_range': (45, 110),
    },
    'chitra': {
        'name': 'K.S. Chithra',
        'era': '1980s-present',
        'vocal_range_hz': (220, 700),
        'characteristics': ['classical', 'devotional', 'melodic'],
        'eq_profile': {
            'low_shelf_db': 0,
            'low_shelf_freq': 180,
            'mid_boost_db': 1.5,
            'mid_freq': 3000,
            'high_shelf_db': 1,
            'high_shelf_freq': 10000,
            'presence_boost_db': 1.5,
            'presence_freq': 5500,
        },
        'spectral_centroid_range': (2300, 3800),
        'pitch_std_range': (50, 120),
    },
    'yesudas': {
        'name': 'K.J. Yesudas',
        'era': '1960s-present',
        'vocal_range_hz': (100, 450),
        'characteristics': ['classical', 'devotional', 'rich'],
        'eq_profile': {
            'low_shelf_db': 2,
            'low_shelf_freq': 200,
            'mid_boost_db': 1,
            'mid_freq': 2200,
            'high_shelf_db': 0,
            'high_shelf_freq': 8000,
            'presence_boost_db': 1.5,
            'presence_freq': 3000,
        },
        'spectral_centroid_range': (1500, 2500),
        'pitch_std_range': (35, 90),
    },
    # Default profile for unknown singers
    'unknown': {
        'name': 'Unknown Singer',
        'era': 'Unknown',
        'vocal_range_hz': (100, 600),
        'characteristics': ['generic'],
        'eq_profile': {
            'low_shelf_db': 0,
            'low_shelf_freq': 150,
            'mid_boost_db': 0,
            'mid_freq': 2500,
            'high_shelf_db': 0,
            'high_shelf_freq': 10000,
            'presence_boost_db': 0,
            'presence_freq': 4000,
        },
        'spectral_centroid_range': (1500, 3500),
        'pitch_std_range': (40, 150),
    },
}


def extract_vocal_features(vocal_audio: np.ndarray, sr: int) -> Dict[str, float]:
    """
    Extract features from isolated vocals for singer identification.
    """
    features = {}

    # 1. Spectral Centroid (brightness)
    spectral_centroids = librosa.feature.spectral_centroid(y=vocal_audio, sr=sr)[0]
    features['spectral_centroid_mean'] = float(np.mean(spectral_centroids))
    features['spectral_centroid_std'] = float(np.std(spectral_centroids))

    # 2. Pitch analysis
    pitches, magnitudes = librosa.piptrack(y=vocal_audio, sr=sr)
    pitch_values = []
    for t in range(pitches.shape[1]):
        index = magnitudes[:, t].argmax()
        pitch = pitches[index, t]
        if pitch > 50:  # Filter out noise
            pitch_values.append(pitch)

    if pitch_values:
        features['pitch_mean'] = float(np.mean(pitch_values))
        features['pitch_std'] = float(np.std(pitch_values))
        features['pitch_range'] = float(np.max(pitch_values) - np.min(pitch_values))
    else:
        features['pitch_mean'] = 0
        features['pitch_std'] = 0
        features['pitch_range'] = 0

    # 3. MFCC for timbre
    mfccs = librosa.feature.mfcc(y=vocal_audio, sr=sr, n_mfcc=13)
    for i in range(13):
        features[f'mfcc_{i}_mean'] = float(np.mean(mfccs[i]))
        features[f'mfcc_{i}_std'] = float(np.std(mfccs[i]))

    # 4. Spectral bandwidth (voice fullness)
    bandwidth = librosa.feature.spectral_bandwidth(y=vocal_audio, sr=sr)[0]
    features['bandwidth_mean'] = float(np.mean(bandwidth))

    # 5. Zero crossing rate (voice texture)
    zcr = librosa.feature.zero_crossing_rate(vocal_audio)[0]
    features['zcr_mean'] = float(np.mean(zcr))

    # 6. RMS energy
    rms = librosa.feature.rms(y=vocal_audio)[0]
    features['rms_mean'] = float(np.mean(rms))

    return features


def detect_singer(vocal_features: Dict[str, float]) -> Tuple[str, float, Dict]:
    """
    Detect the most likely singer based on vocal features.
    Returns (singer_id, confidence, profile).
    """
    best_match = 'unknown'
    best_score = 0

    spectral_centroid = vocal_features.get('spectral_centroid_mean', 2000)
    pitch_std = vocal_features.get('pitch_std', 80)

    for singer_id, profile in KANNADA_SINGER_PROFILES.items():
        if singer_id == 'unknown':
            continue

        score = 0
        max_score = 0

        # Match spectral centroid range
        sc_range = profile['spectral_centroid_range']
        if sc_range[0] <= spectral_centroid <= sc_range[1]:
            score += 40
        else:
            # Partial score based on distance
            distance = min(abs(spectral_centroid - sc_range[0]),
                           abs(spectral_centroid - sc_range[1]))
            score += max(0, 40 - distance / 50)
        max_score += 40

        # Match pitch stability
        ps_range = profile['pitch_std_range']
        if ps_range[0] <= pitch_std <= ps_range[1]:
            score += 30
        else:
            distance = min(abs(pitch_std - ps_range[0]),
                           abs(pitch_std - ps_range[1]))
            score += max(0, 30 - distance / 10)
        max_score += 30

        # Match vocal range
        pitch_mean = vocal_features.get('pitch_mean', 200)
        vr = profile['vocal_range_hz']
        if vr[0] <= pitch_mean <= vr[1]:
            score += 30
        max_score += 30

        confidence = score / max_score if max_score > 0 else 0

        if confidence > best_score:
            best_score = confidence
            best_match = singer_id

    return best_match, best_score, KANNADA_SINGER_PROFILES[best_match]


def get_singer_eq_profile(singer_id: str) -> Dict:
    """
    Get the EQ profile for a specific singer.
    """
    profile = KANNADA_SINGER_PROFILES.get(singer_id, KANNADA_SINGER_PROFILES['unknown'])
    return profile['eq_profile']


# -----------------------------------------------------------------------------
# FILM ERA DETECTION
# -----------------------------------------------------------------------------

FILM_ERA_PROFILES = {
    '1960s_classical': {
        'name': '1960s Classical Era',
        'years': (1960, 1969),
        'characteristics': {
            'bpm_range': (60, 100),
            'spectral_centroid_range': (1000, 2000),
            'dynamics_range': (0.3, 0.6),  # Lower dynamic range
            'instruments': ['tabla', 'harmonium', 'veena', 'flute'],
        },
        'composers': ['G.K. Venkatesh', 'T.G. Lingappa', 'Vijaya Bhaskar'],
        'style': 'classical_devotional',
    },
    '1970s_melodic': {
        'name': '1970s Melodic Era',
        'years': (1970, 1979),
        'characteristics': {
            'bpm_range': (70, 110),
            'spectral_centroid_range': (1200, 2200),
            'dynamics_range': (0.35, 0.65),
            'instruments': ['violin', 'guitar', 'drums', 'synthesizer'],
        },
        'composers': ['Rajan-Nagendra', 'Chellapilla Satyam', 'Upendra Kumar'],
        'style': 'melodic_romantic',
    },
    '1980s_disco': {
        'name': '1980s Disco Era',
        'years': (1980, 1989),
        'characteristics': {
            'bpm_range': (100, 130),
            'spectral_centroid_range': (1800, 3000),
            'dynamics_range': (0.4, 0.7),
            'instruments': ['synthesizer', 'drum_machine', 'electric_guitar'],
        },
        'composers': ['Hamsalekha', 'Upendra Kumar', 'Rajan-Nagendra'],
        'style': 'disco_pop',
    },
    '1990s_hamsalekha': {
        'name': '1990s Hamsalekha Era',
        'years': (1990, 1999),
        'characteristics': {
            'bpm_range': (90, 140),
            'spectral_centroid_range': (2000, 3500),
            'dynamics_range': (0.5, 0.8),
            'instruments': ['keyboards', 'drum_pads', 'guitar', 'flute'],
        },
        'composers': ['Hamsalekha', 'V. Manohar', 'Sadhu Kokila'],
        'style': 'filmi_mass',
    },
    '2000s_modern': {
        'name': '2000s Modern Era',
        'years': (2000, 2009),
        'characteristics': {
            'bpm_range': (95, 145),
            'spectral_centroid_range': (2500, 4000),
            'dynamics_range': (0.55, 0.85),
            'instruments': ['electronic', 'world_music', 'fusion'],
        },
        'composers': ['V. Harikrishna', 'Gurukiran', 'Mano Murthy'],
        'style': 'modern_fusion',
    },
    '2010s_contemporary': {
        'name': '2010s Contemporary Era',
        'years': (2010, 2019),
        'characteristics': {
            'bpm_range': (100, 150),
            'spectral_centroid_range': (2800, 4500),
            'dynamics_range': (0.6, 0.9),
            'instruments': ['edm', 'trap_beats', 'dubstep_elements'],
        },
        'composers': ['Arjun Janya', 'V. Harikrishna', 'Charan Raj'],
        'style': 'contemporary_edm',
    },
    '2020s_indie': {
        'name': '2020s Indie Era',
        'years': (2020, 2029),
        'characteristics': {
            'bpm_range': (80, 160),
            'spectral_centroid_range': (2500, 5000),
            'dynamics_range': (0.5, 0.95),
            'instruments': ['lo_fi', 'indie_rock', 'electronic'],
        },
        'composers': ['B. Ajaneesh Loknath', 'Ravi Basrur', 'Charan Raj'],
        'style': 'indie_experimental',
    },
}


def detect_film_era(
    bpm: float,
    spectral_centroid: float,
    dynamics: float,
    year_hint: Optional[int] = None
) -> Tuple[str, float, Dict]:
    """
    Detect the film era based on audio characteristics.
    Returns (era_id, confidence, profile).
    """
    best_match = '1990s_hamsalekha'  # Default to most common
    best_score = 0

    for era_id, profile in FILM_ERA_PROFILES.items():
        score = 0
        max_score = 0

        chars = profile['characteristics']

        # BPM match
        bpm_range = chars['bpm_range']
        if bpm_range[0] <= bpm <= bpm_range[1]:
            score += 30
        else:
            distance = min(abs(bpm - bpm_range[0]), abs(bpm - bpm_range[1]))
            score += max(0, 30 - distance)
        max_score += 30

        # Spectral centroid match
        sc_range = chars['spectral_centroid_range']
        if sc_range[0] <= spectral_centroid <= sc_range[1]:
            score += 30
        else:
            distance = min(abs(spectral_centroid - sc_range[0]),
                           abs(spectral_centroid - sc_range[1]))
            score += max(0, 30 - distance / 100)
        max_score += 30

        # Dynamics match
        dyn_range = chars['dynamics_range']
        if dyn_range[0] <= dynamics <= dyn_range[1]:
            score += 20
        max_score += 20

        # Year hint bonus
        if year_hint:
            year_range = profile['years']
            if year_range[0] <= year_hint <= year_range[1]:
                score += 20
        max_score += 20

        confidence = score / max_score if max_score > 0 else 0

        if confidence > best_score:
            best_score = confidence
            best_match = era_id

    return best_match, best_score, FILM_ERA_PROFILES[best_match]


def analyze_era_from_audio(y: np.ndarray, sr: int) -> Dict:
    """
    Analyze audio to detect film era.
    """
    # BPM
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(tempo)

    # Spectral centroid
    spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    spectral_centroid = float(np.mean(spectral_centroids))

    # Dynamics (RMS variance)
    rms = librosa.feature.rms(y=y)[0]
    dynamics = float(np.std(rms) / (np.mean(rms) + 1e-6))
    dynamics = min(1.0, dynamics)

    era_id, confidence, profile = detect_film_era(bpm, spectral_centroid, dynamics)

    return {
        'era_id': era_id,
        'era_name': profile['name'],
        'confidence': confidence,
        'style': profile['style'],
        'likely_composers': profile['composers'],
        'characteristics': {
            'detected_bpm': bpm,
            'spectral_centroid': spectral_centroid,
            'dynamics': dynamics,
        },
    }


# -----------------------------------------------------------------------------
# AUDIO FILE VALIDATION AND CORRUPTION DETECTION
# -----------------------------------------------------------------------------

def validate_audio_file(file_path: str) -> Dict[str, Any]:
    """
    Validate an audio file for corruption and quality issues.
    Returns validation results with warnings and errors.
    """
    result = {
        'valid': True,
        'file_path': file_path,
        'errors': [],
        'warnings': [],
        'info': {},
    }

    # Check file exists
    if not os.path.exists(file_path):
        result['valid'] = False
        result['errors'].append('File does not exist')
        return result

    # Check file size
    file_size = os.path.getsize(file_path)
    result['info']['file_size_bytes'] = file_size
    result['info']['file_size_mb'] = round(file_size / (1024 * 1024), 2)

    if file_size < 1000:  # Less than 1KB
        result['valid'] = False
        result['errors'].append('File is too small, likely corrupted')
        return result

    if file_size > 500 * 1024 * 1024:  # More than 500MB
        result['warnings'].append('File is very large (>500MB)')

    # Check file extension
    ext = os.path.splitext(file_path)[1].lower()
    supported_formats = ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac']
    if ext not in supported_formats:
        result['warnings'].append(f'Unsupported format: {ext}')

    result['info']['format'] = ext[1:]

    # Try to load with librosa
    try:
        y, sr = librosa.load(file_path, sr=None, duration=30)  # Load first 30 seconds

        result['info']['sample_rate'] = sr
        result['info']['duration_seconds'] = librosa.get_duration(y=y, sr=sr)
        result['info']['channels'] = 1 if y.ndim == 1 else y.shape[0]

        # Check for silence
        rms = librosa.feature.rms(y=y)[0]
        mean_rms = np.mean(rms)

        if mean_rms < 0.001:
            result['valid'] = False
            result['errors'].append('Audio is silent or nearly silent')
            return result

        if mean_rms < 0.01:
            result['warnings'].append('Audio level is very low')

        # Check for clipping
        clipping_ratio = np.sum(np.abs(y) > 0.99) / len(y)
        if clipping_ratio > 0.01:
            result['warnings'].append(f'Audio may be clipping ({clipping_ratio*100:.1f}% samples)')

        result['info']['peak_amplitude'] = float(np.max(np.abs(y)))
        result['info']['mean_rms'] = float(mean_rms)

        # Check for DC offset
        dc_offset = np.mean(y)
        if abs(dc_offset) > 0.05:
            result['warnings'].append(f'Audio has DC offset: {dc_offset:.3f}')

        result['info']['dc_offset'] = float(dc_offset)

        # Detect potential encoding issues (excessive high frequency noise)
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        if spectral_centroid > sr * 0.4:  # Very high spectral centroid
            result['warnings'].append('Unusual spectral content, possible encoding issue')

        result['info']['spectral_centroid'] = float(spectral_centroid)

    except Exception as e:
        result['valid'] = False
        result['errors'].append(f'Failed to load audio: {str(e)}')
        return result

    # Check duration
    if result['info'].get('duration_seconds', 0) < 10:
        result['warnings'].append('Audio is very short (<10 seconds)')

    if result['info'].get('duration_seconds', 0) > 600:
        result['warnings'].append('Audio is very long (>10 minutes)')

    return result


def batch_validate_audio(file_paths: List[str]) -> Dict[str, Any]:
    """
    Validate multiple audio files.
    """
    results = {
        'total_files': len(file_paths),
        'valid_files': 0,
        'invalid_files': 0,
        'files_with_warnings': 0,
        'validations': [],
    }

    for file_path in file_paths:
        validation = validate_audio_file(file_path)
        results['validations'].append(validation)

        if validation['valid']:
            results['valid_files'] += 1
        else:
            results['invalid_files'] += 1

        if validation['warnings']:
            results['files_with_warnings'] += 1

    return results


# -----------------------------------------------------------------------------
# REAL-TIME PREVIEW GENERATION
# -----------------------------------------------------------------------------

def generate_transition_preview(
    track1_path: str,
    track2_path: str,
    transition_point1: float,  # seconds
    transition_point2: float,  # seconds
    transition_duration: float = 8.0,
    output_path: Optional[str] = None,
) -> str:
    """
    Generate a preview of the transition between two tracks.
    Returns path to the preview audio file.
    """
    sr = 44100

    # Load track 1 (10 seconds before transition point)
    track1_start = max(0, transition_point1 - 10)
    y1, _ = librosa.load(
        track1_path, sr=sr, mono=True,
        offset=track1_start,
        duration=10 + transition_duration
    )

    # Load track 2 (start at transition point, get 10 + transition duration)
    y2, _ = librosa.load(
        track2_path, sr=sr, mono=True,
        offset=transition_point2,
        duration=transition_duration + 10
    )

    # Create crossfade transition
    trans_samples = int(transition_duration * sr)

    # Ensure we have enough audio
    if len(y1) < trans_samples or len(y2) < trans_samples:
        raise ValueError("Not enough audio for transition preview")

    # Get the overlapping regions
    out_segment = y1[-trans_samples:]
    in_segment = y2[:trans_samples]

    # Equal-power crossfade
    t = np.linspace(0, 1, trans_samples)
    fade_out = np.sqrt(1 - t)
    fade_in = np.sqrt(t)

    transition = out_segment * fade_out + in_segment * fade_in

    # Combine: pre-transition + transition + post-transition
    pre_transition = y1[:-trans_samples]
    post_transition = y2[trans_samples:]

    preview = np.concatenate([pre_transition, transition, post_transition])

    # Normalize
    preview = preview / (np.max(np.abs(preview)) + 1e-6) * 0.95

    # Save to file
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix='.wav', prefix='preview_')
        os.close(fd)

    sf.write(output_path, preview, sr)

    return output_path


def generate_track_preview(
    track_path: str,
    start_time: float,
    duration: float = 30.0,
    output_path: Optional[str] = None,
) -> str:
    """
    Generate a preview clip of a single track.
    """
    sr = 44100

    y, _ = librosa.load(
        track_path, sr=sr, mono=True,
        offset=start_time,
        duration=duration
    )

    # Add fade in/out
    fade_samples = int(0.5 * sr)
    if len(y) > fade_samples * 2:
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        y[:fade_samples] *= fade_in
        y[-fade_samples:] *= fade_out

    # Normalize
    y = y / (np.max(np.abs(y)) + 1e-6) * 0.95

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix='.wav', prefix='track_preview_')
        os.close(fd)

    sf.write(output_path, y, sr)

    return output_path


# -----------------------------------------------------------------------------
# CUSTOM CUE POINT MANAGEMENT
# -----------------------------------------------------------------------------

CUE_POINTS_FILE = 'custom_cue_points.json'


def load_custom_cue_points() -> Dict[str, Dict]:
    """
    Load custom cue points from file.
    """
    if os.path.exists(CUE_POINTS_FILE):
        with open(CUE_POINTS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_custom_cue_points(cue_points: Dict[str, Dict]) -> None:
    """
    Save custom cue points to file.
    """
    with open(CUE_POINTS_FILE, 'w') as f:
        json.dump(cue_points, f, indent=2)


def set_custom_cue_point(
    filename: str,
    cue_type: str,
    time_seconds: float,
    label: Optional[str] = None
) -> Dict:
    """
    Set a custom cue point for a track.

    cue_type: 'mix_in', 'mix_out', 'drop', 'loop_start', 'loop_end', 'hot_cue_1', etc.
    """
    cue_points = load_custom_cue_points()

    if filename not in cue_points:
        cue_points[filename] = {}

    cue_points[filename][cue_type] = {
        'time': time_seconds,
        'label': label or cue_type.upper().replace('_', ' '),
        'set_at': datetime.now().isoformat(),
        'is_custom': True,
    }

    save_custom_cue_points(cue_points)

    return cue_points[filename]


def get_custom_cue_points(filename: str) -> Dict:
    """
    Get custom cue points for a track.
    """
    cue_points = load_custom_cue_points()
    return cue_points.get(filename, {})


def delete_custom_cue_point(filename: str, cue_type: str) -> bool:
    """
    Delete a custom cue point.
    """
    cue_points = load_custom_cue_points()

    if filename in cue_points and cue_type in cue_points[filename]:
        del cue_points[filename][cue_type]
        if not cue_points[filename]:
            del cue_points[filename]
        save_custom_cue_points(cue_points)
        return True

    return False


def merge_cue_points(auto_cue_points: Dict, custom_cue_points: Dict) -> Dict:
    """
    Merge automatic and custom cue points, with custom taking precedence.
    """
    merged = auto_cue_points.copy()

    for cue_type, cue_data in custom_cue_points.items():
        merged[cue_type] = cue_data

    return merged


# -----------------------------------------------------------------------------
# MAIN / TEST
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("Sandalwood Enhancements Module")
    print("=" * 50)
    print("\nAvailable Kannada Singer Profiles:")
    for singer_id, profile in KANNADA_SINGER_PROFILES.items():
        if singer_id != 'unknown':
            print(f"  - {profile['name']} ({profile['era']})")

    print("\nAvailable Film Era Profiles:")
    for era_id, profile in FILM_ERA_PROFILES.items():
        years = profile['years']
        print(f"  - {profile['name']} ({years[0]}-{years[1]})")
        print(f"    Style: {profile['style']}")
        print(f"    Composers: {', '.join(profile['composers'][:3])}")
