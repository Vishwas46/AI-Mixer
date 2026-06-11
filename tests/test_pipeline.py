# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# tests/test_pipeline.py
# End-to-end pipeline check on synthetic songs. Runs fully offline: it defaults
# AIMIXER_STEM_QUALITY=none so no Demucs/RoFormer weights are downloaded and no
# network is touched, exercising the graceful-degradation paths. Export
# AIMIXER_STEM_QUALITY=fast|auto|best beforehand to test real separation.
#
#   venv/bin/python tests/test_pipeline.py
#
# Checks: 17-step analysis sanity -> Mashup Lab (all 3 styles) -> nonstop
# sandalwood mix. Exits non-zero on the first hard failure.
# -----------------------------------------------------------------------------

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import soundfile as sf

from tests.make_test_songs import generate_all, SONG_SPECS

OUTPUT_DIR = "remix_outputs"
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))
    return ok


def bpm_matches(detected, expected, tol=4.0):
    for mult in (0.5, 1.0, 2.0):
        if abs(detected - expected * mult) <= tol:
            return True
    return False


def audio_stats(path):
    y, sr = sf.read(path)
    if y.ndim > 1:
        y = y.mean(axis=1)
    stats = {
        "duration": len(y) / sr,
        "peak": float(np.max(np.abs(y))) if len(y) else 0.0,
        "has_nan": bool(np.isnan(y).any()),
        "lufs": None,
    }
    try:
        import pyloudnorm as pyln
        stats["lufs"] = pyln.Meter(sr).integrated_loudness(y)
    except Exception:
        pass
    return stats


def main():
    # Run offline by default: skip neural separation everywhere (no weights, no
    # network) so the suite exercises the graceful-degradation paths. Override
    # by exporting AIMIXER_STEM_QUALITY=fast|auto|best to test real separation.
    os.environ.setdefault("AIMIXER_STEM_QUALITY", "none")

    # Measure DSP stats on the lossless WAV export, not a lossy MP3 round-trip.
    # MP3 inter-sample overshoot pushes the decoded peak above 1.0 even though
    # our master is limited to <=0.985 — so an MP3 peak check tests the codec,
    # not our DSP (and would depend on libsndfile's MP3 decode). Forcing WAV
    # keeps every assertion on the true mastered signal, including the 16-bit
    # export true-peak guard this suite is meant to protect.
    import audio_utils
    audio_utils.has_ffmpeg = lambda: False

    venv_path = os.environ.get("VIRTUAL_ENV", os.path.abspath("./venv"))
    print("=" * 70)
    print("PIPELINE TEST — synthetic songs "
          f"(AIMIXER_STEM_QUALITY={os.environ['AIMIXER_STEM_QUALITY']})")
    print("=" * 70)

    print("\n[1/4] Generating synthetic songs...")
    paths = generate_all("songs")

    print("\n[2/4] Deep analysis sanity...")
    from kannada_mashup_analyzer import analyze_kannada_track_for_mashup, plan_kannada_mashup

    analyses = []
    for path, (fname, bpm, root, kind) in zip(paths, SONG_SPECS):
        print(f"\n--- Analyzing {fname} (expected ~{bpm} BPM) ---")
        analysis = analyze_kannada_track_for_mashup(path, venv_path)
        analyses.append(analysis)
        check(f"{fname}: BPM {analysis['bpm']:.1f} ~ {bpm}",
              bpm_matches(analysis["bpm"], bpm))
        check(f"{fname}: beat grid present",
              len(analysis.get("beat_grid", {}).get("downbeat_times", [])) > 0)
        check(f"{fname}: sections present",
              len((analysis.get("sections") or {}).get("sections", [])) > 0)
        check(f"{fname}: duration ~60s", abs(analysis["duration"] - 60) < 5,
              f"{analysis['duration']:.1f}s")

    print("\n[3/4] Mashup Lab — all 3 styles...")
    from mashup_lab import create_lab_mashup, STYLE_PRESETS

    vocal_analysis, backing_analysis = analyses[0], analyses[1]
    backing_duration = backing_analysis["duration"]
    lab_results = []
    for style in STYLE_PRESETS:
        print(f"\n--- Style: {style} ---")
        try:
            result = create_lab_mashup(vocal_analysis, backing_analysis,
                                       OUTPUT_DIR, style=style, venv_path=venv_path)
        except Exception as exc:
            traceback.print_exc()
            check(f"lab/{style}: created", False, str(exc))
            continue
        lab_results.append(result)
        stats = audio_stats(result["output_path"])
        check(f"lab/{style}: output exists", os.path.exists(result["output_path"]),
              result["output_filename"])
        check(f"lab/{style}: duration within 20% of backing",
              abs(stats["duration"] - backing_duration) / backing_duration < 0.2,
              f"{stats['duration']:.1f}s vs {backing_duration:.1f}s")
        check(f"lab/{style}: no NaN", not stats["has_nan"])
        check(f"lab/{style}: peak <= 0.999", stats["peak"] <= 0.999,
              f"peak {stats['peak']:.3f}")
        if stats["lufs"] is not None:
            check(f"lab/{style}: LUFS in [-17, -10]",
                  -17 <= stats["lufs"] <= -10, f"{stats['lufs']:.1f} LUFS")
        check(f"lab/{style}: placements > 0", len(result["placements"]) > 0,
              f"{len(result['placements'])} phrases, separator={result['separator_used']}, "
              f"degraded={result['degraded']}")
        if result["placements"]:
            bar_sec = 4 * 60.0 / backing_analysis["bpm"]
            first_entry = result["placements"][0]["timeline_start_sec"]
            check(f"lab/{style}: vocal enters after an intro",
                  first_entry >= 2 * bar_sec, f"first entry {first_entry:.1f}s")

    print("\n[4/4] Nonstop sandalwood mix...")
    from sandalwood_mixer import create_sandalwood_mashup

    plan = plan_kannada_mashup(analyses, target_duration_minutes=3, style="energetic")
    check("nonstop: plan has track order", len(plan.get("track_order", [])) >= 2,
          str(plan.get("track_order")))
    try:
        planned = set(plan.get("track_order", []))
        tracks = [a for a in analyses if a["filename"] in planned]
        out_path = create_sandalwood_mashup(tracks, plan, OUTPUT_DIR)
        stats = audio_stats(out_path)
        check("nonstop: output exists", os.path.exists(out_path), os.path.basename(out_path))
        check("nonstop: duration > 30s", stats["duration"] > 30, f"{stats['duration']:.1f}s")
        check("nonstop: no NaN", not stats["has_nan"])
        if stats["lufs"] is not None:
            check("nonstop: LUFS in [-17, -10]", -17 <= stats["lufs"] <= -10,
                  f"{stats['lufs']:.1f} LUFS")
    except Exception as exc:
        traceback.print_exc()
        check("nonstop: created", False, str(exc))

    print("\n" + "=" * 70)
    failed = [c for c in CHECKS if not c[1]]
    print(f"RESULT: {len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    if lab_results:
        sep = lab_results[0]["separator_used"]
        print(f"Separation tier used: vocal={sep['vocal']}, backing={sep['backing']} "
              f"(degraded={lab_results[0]['degraded']})")
    for name, _, detail in failed:
        print(f"  FAILED: {name} {detail}")
    print("=" * 70)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
