# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# tests/make_test_songs.py
# Renders small synthetic "songs" (drums + bass + a singing-ish lead) at known
# BPM and key so the full analysis/mixing pipeline can be verified end-to-end
# without copyrighted audio, model weights, or network access.
#
#   python tests/make_test_songs.py            # writes WAVs into songs/
# -----------------------------------------------------------------------------

import os
import sys
import numpy as np
import soundfile as sf

SR = 44100


def _env_exp(n, decay):
    return np.exp(-np.linspace(0, decay, n))


def _kick(n):
    t = np.linspace(0, n / SR, n, endpoint=False)
    freq = np.linspace(150, 50, n)
    return np.sin(2 * np.pi * freq * t) * _env_exp(n, 8)


def _snare(n, rng):
    return rng.standard_normal(n) * _env_exp(n, 12) * 0.5


def _hat(n, rng):
    noise = rng.standard_normal(n) * _env_exp(n, 30) * 0.25
    return np.diff(noise, prepend=0.0)  # crude high-pass for a metallic feel


def _tone(freq, n, harmonics=(1.0, 0.5, 0.25), vibrato_hz=0.0):
    t = np.linspace(0, n / SR, n, endpoint=False)
    vib = np.sin(2 * np.pi * vibrato_hz * t) * 0.01 * freq if vibrato_hz else 0.0
    y = np.zeros(n)
    for i, amp in enumerate(harmonics, start=1):
        y += amp * np.sin(2 * np.pi * (freq * i + vib * i) * t)
    return y / max(1e-9, np.max(np.abs(y)))


def _midi_to_hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def make_song(path, bpm, root_midi, duration_sec=60, kind="vocal", seed=42):
    """Render a synthetic song.

    kind="vocal":   drums + bass + a vibrato lead gated in 8-bars-on/4-bars-off
                    phrases (gives the analyzer real structure boundaries).
    kind="backing": drums + bass + pad chords, no lead.
    """
    rng = np.random.default_rng(seed)
    n_total = int(duration_sec * SR)
    beat = 60.0 / bpm
    beat_n = int(beat * SR)
    n_beats = n_total // beat_n

    drums = np.zeros(n_total)
    bass = np.zeros(n_total)
    lead = np.zeros(n_total)

    # natural-minor scale degrees (semitones from root)
    scale = [0, 2, 3, 5, 7, 8, 10, 12]

    for b in range(n_beats):
        start = b * beat_n
        seg = min(beat_n, n_total - start)

        k = _kick(min(seg, int(0.12 * SR)))
        drums[start:start + len(k)] += k
        if b % 4 in (1, 3):
            s = _snare(min(seg, int(0.1 * SR)), rng)
            drums[start:start + len(s)] += s
        for half in (0, beat_n // 2):
            h_start = start + half
            h_len = min(int(0.03 * SR), n_total - h_start)
            if h_len > 1:
                drums[h_start:h_start + h_len] += _hat(h_len, rng)

        # bass: root on the downbeat, fifth on beat 3
        bass_midi = root_midi - 12 + (7 if b % 4 == 2 else 0)
        bass_note = _tone(_midi_to_hz(bass_midi), seg, harmonics=(1.0, 0.4)) * 0.5
        bass[start:start + seg] += bass_note * _env_exp(seg, 3)

        bar = b // 4
        if kind == "vocal":
            # 8 bars singing, 4 bars rest — creates vocal phrases and gaps
            if bar % 12 < 8:
                degree = scale[(b * 3 + bar) % len(scale)]
                note = _tone(_midi_to_hz(root_midi + 12 + degree), seg,
                             harmonics=(1.0, 0.6, 0.4, 0.2), vibrato_hz=5.5)
                lead[start:start + seg] += note * 0.45 * _env_exp(seg, 1.5)
        else:
            # backing: sustained pad chord each bar
            if b % 4 == 0:
                pad_len = min(4 * beat_n, n_total - start)
                for degree in (0, 3, 7):
                    pad = _tone(_midi_to_hz(root_midi + degree), pad_len,
                                harmonics=(1.0, 0.3))
                    lead[start:start + pad_len] += pad * 0.12

    mix = drums * 0.8 + bass * 0.7 + lead
    mix = mix / max(1e-9, np.max(np.abs(mix))) * 0.85
    sf.write(path, mix.astype(np.float32), SR)
    return path


SONG_SPECS = [
    # filename                     bpm  root_midi (62=D, 64=E, 69=A)  kind
    ("test_vocal_92bpm_Dm.wav",     92, 62, "vocal"),
    ("test_backing_104bpm_Em.wav", 104, 64, "backing"),
    ("test_third_120bpm_Am.wav",   120, 69, "vocal"),
]


def generate_all(out_dir="songs"):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for fname, bpm, root, kind in SONG_SPECS:
        path = os.path.join(out_dir, fname)
        if not os.path.exists(path):
            print(f"Rendering {fname} ({bpm} BPM, kind={kind})...")
            make_song(path, bpm, root, kind=kind)
        else:
            print(f"Exists: {fname}")
        paths.append(path)
    return paths


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "songs"
    for p in generate_all(out):
        print("  ->", p)
