# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# stem_separation.py
# Pluggable stem separation with quality tiers:
#
#   Tier 1 "best": BS-RoFormer vocal model via the optional `audio-separator`
#                  package (SDX23-winning family, ~12.9 dB SDR vocals).
#                  Install with: pip install -r requirements-quality.txt
#   Tier 2 "fast": Demucs htdemucs_ft 4-stem CLI (project default).
#   Tier 3 "none": neural separation off — every caller (RoFormer, Demucs and
#                  the analyzer's vocal-region pass) degrades to master-channel
#                  mixing. No weights, no network. For offline / low-resource
#                  runs and the offline test suite.
#
# Select via env var AIMIXER_STEM_QUALITY=best|fast|auto|none (default: auto).
# "auto" uses RoFormer when the package is installed, otherwise Demucs.
# "none" (alias "off") skips separation entirely.
# -----------------------------------------------------------------------------

import os

# SDX23-class two-stem checkpoint bundled with audio-separator's model registry.
# Weights (~600MB) download once on first use.
ROFORMER_MODEL = "model_bs_roformer_ep_317_sdr_12.9755.ckpt"

_roformer_separator = None  # cached instance — model load is expensive


def get_stem_quality():
    """Read the requested separation quality tier from the environment."""
    quality = os.environ.get("AIMIXER_STEM_QUALITY", "auto").strip().lower()
    if quality == "off":  # friendly alias
        quality = "none"
    return quality if quality in ("best", "fast", "auto", "none") else "auto"


def stem_separation_disabled():
    """True when neural separation is switched off (AIMIXER_STEM_QUALITY=none).

    Lets every separation entry point — RoFormer, Demucs and the analyzer's
    vocal-region pass — degrade to master-channel mixing with no model weights
    and no network. Used for offline / low-resource runs and the offline tests.
    """
    return get_stem_quality() == "none"


def roformer_available():
    """True if the optional audio-separator package is importable."""
    try:
        from audio_separator.separator import Separator  # noqa: F401
        return True
    except Exception:
        return False


def separate_vocals_roformer(file_path, output_dir):
    """Two-stem (vocals / instrumental) split using BS-RoFormer.

    Returns {'vocals': path, 'instrumental': path} or None on any failure
    (package missing, weights not downloadable, separation error).
    """
    global _roformer_separator

    base = os.path.splitext(os.path.basename(file_path))[0]
    cached_vocals = os.path.join(output_dir, f"{base}_vocals_roformer.wav")
    cached_inst = os.path.join(output_dir, f"{base}_instrumental_roformer.wav")
    if os.path.exists(cached_vocals) and os.path.exists(cached_inst):
        print(f"  [Stem Separation] RoFormer cache hit for {base}")
        return {'vocals': cached_vocals, 'instrumental': cached_inst}

    try:
        from audio_separator.separator import Separator
    except Exception:
        return None

    try:
        os.makedirs(output_dir, exist_ok=True)
        if _roformer_separator is None or getattr(_roformer_separator, 'output_dir', None) != output_dir:
            separator = Separator(output_dir=output_dir, output_format="WAV")
            separator.load_model(model_filename=ROFORMER_MODEL)
            _roformer_separator = separator
        print(f"  [Stem Separation] Running BS-RoFormer on {os.path.basename(file_path)}...")
        output_files = _roformer_separator.separate(file_path)

        result = {}
        for out in output_files or []:
            path = out if os.path.isabs(out) else os.path.join(output_dir, out)
            lowered = os.path.basename(path).lower()
            if 'vocal' in lowered and 'instrumental' not in lowered:
                result['vocals'] = path
            elif 'instrumental' in lowered:
                result['instrumental'] = path
        if 'vocals' in result and 'instrumental' in result:
            # Stable names so repeat runs hit the cache
            os.replace(result['vocals'], cached_vocals)
            os.replace(result['instrumental'], cached_inst)
            return {'vocals': cached_vocals, 'instrumental': cached_inst}
        print("  [Stem Separation] RoFormer output missing expected stems")
        return None
    except Exception as e:
        print(f"  [Stem Separation] RoFormer failed: {e}")
        return None


def separate_stems_best(file_path, output_dir, venv_path=None, quality=None):
    """Separate a track using the best available engine.

    Returns:
        {'separator': 'roformer', 'stems': {'vocals', 'instrumental'}}
      or {'separator': 'demucs',   'stems': {'vocals', 'drums', 'bass', 'other'}}
      or None when no engine could produce stems.
    """
    quality = quality or get_stem_quality()
    if quality == "none":
        return None

    if quality in ("best", "auto"):
        stems = separate_vocals_roformer(file_path, os.path.join(output_dir, "roformer"))
        if stems:
            return {'separator': 'roformer', 'stems': stems}
        if quality == "best":
            print("  [Stem Separation] 'best' requested but RoFormer unavailable — "
                  "install with: pip install -r requirements-quality.txt. Trying Demucs...")

    from sandalwood_mixer import separate_stems_demucs
    stems = separate_stems_demucs(file_path, output_dir, venv_path)
    if stems:
        return {'separator': 'demucs', 'stems': stems}
    return None
