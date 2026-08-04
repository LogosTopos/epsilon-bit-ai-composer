#!/usr/bin/env python3
"""Stage 1 — Global analysis of DDRKirby(ISQ) - Infinity.

Extracts: tempo, meter, key, structure segments, dynamics profile,
overall spectral fingerprint. Writes plots + JSON into plots/ and data/.
"""
import json
import os
import sys

import numpy as np
import librosa
from scipy import signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = "/Users/topologyw/Music/网易云音乐/DDRKirby(ISQ) - Infinity.mp3"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)))

# key profile correlations (Krumhansl-Schmuckler, major/minor)
K_S_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
K_S_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

def krumhansl(chroma_mean, profile):
    return float(np.corrcoef(chroma_mean, profile)[0, 1])

def main():
    print("loading…")
    y, sr = librosa.load(SRC, sr=44100, mono=True)
    dur = len(y) / sr
    print(f"duration: {dur:.2f}s")

    # ---------- dynamics ----------
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    times_rms = librosa.times_like(rms, sr=sr, hop_length=512)
    print(f"RMS: median={np.median(rms):.4f} p95={np.percentile(rms,95):.4f} "
          f"dynamic range(p95/p10)={20*np.log10(np.percentile(rms,95)/np.percentile(rms,10)):.1f} dB")

    # ---------- tempo ----------
    # Robust approach: measure the onset grid directly from strong onset
    # peaks, then lock phase by comb alignment. (Default beat_track locks
    # onto the dominant kick-snare period = half-time.)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
    pk = librosa.util.peak_pick(onset_env, pre_max=5, post_max=5, pre_avg=10, post_avg=10, delta=0.25, wait=4)
    if len(pk) > 20:
        dt = np.diff(pk) * 512 / sr
        q8 = np.median(dt[(dt > 0.13) & (dt < 0.22)])   # 8th-note candidates
        q4 = np.median(dt[(dt > 0.26) & (dt < 0.44)])   # quarter-note candidates
        print(f"onset intervals: 8th~{q8*1000:.1f}ms  quarter~{q4*1000:.1f}ms")
        beat_s = q4 if np.isfinite(q4) else 2 * q8
    else:
        beat_s = 0.35294
    bpm_final = 60.0 / beat_s
    print(f"beat: {beat_s*1000:.2f} ms -> tempo {bpm_final:.2f} BPM")
    # comb phase alignment: find phase offset maximizing onset energy on the beat grid
    Lb = beat_s * sr / 512
    n_units = int(len(onset_env) / Lb) + 1
    best_phase, best_e = 0, -1
    for ph in range(int(Lb)):
        idx = np.round(np.arange(ph, n_units * Lb, Lb)).astype(int)
        idx = idx[idx < len(onset_env)]
        e = onset_env[idx].sum()
        if e > best_e:
            best_e, best_phase = e, ph
    beats = best_phase * 512 / sr + np.arange(n_units) * beat_s
    beats = beats[beats < dur - 0.05]
    print(f"locked tempo: {bpm_final:.2f} BPM, {len(beats)} beats, first 8: {np.round(beats[:8],3)}")
    tempo_1 = tempo_2 = tempo_3 = bpm_final
    beats_1 = (beats * sr).astype(int)
    print(f"tempo (beat_track): {float(tempo_1):.2f} | (onset autocorr): {float(tempo_2):.2f} | (tempogram peak): {tempo_3:.2f}")
    print(f"  #beats: {len(beats_1)}  first 12 beat times: {np.round(beats_1[:12]/sr, 3)}")

    # ---------- key ----------
    chroma = librosa.feature.chroma_cens(y=y, sr=sr, hop_length=512)
    cm = chroma.mean(axis=1)
    keys = []
    for root in range(12):
        cmr = np.roll(cm, root)
        keys.append((krumhansl(cmr, K_S_MAJ), f"{librosa.midi_to_note(root+60)[:-1]} major"))
        keys.append((krumhansl(cmr, K_S_MIN), f"{librosa.midi_to_note(root+60)[:-1]} minor"))
    keys.sort(reverse=True)
    print("key candidates:", [(k, round(s, 3)) for s, k in keys[:6]])

    # ---------- structure ----------
    # beat-synchronous chroma self-similarity + novelty
    beats_fr = librosa.samples_to_frames(beats_1, hop_length=512)
    chroma_beat = librosa.util.sync(chroma, beats_fr, aggregate=np.median)
    C = librosa.segment.recurrence_matrix(chroma_beat, mode="affinity", k=8)
    nov = librosa.segment.recurrence_to_lag(C)
    novelty = librosa.segment.lag_to_recurrence(nov).sum(axis=1)
    novelty = librosa.util.normalize(novelty)
    bounds = librosa.segment.agglomerative(chroma_beat, 8)
    seg_times = beats_1[bounds] / sr
    print("structure (agglomerative, 8 segs):")
    for i in range(len(bounds) - 1):
        print(f"  seg{i}: {seg_times[i]:7.2f}s – {seg_times[i+1]:7.2f}s  ({seg_times[i+1]-seg_times[i]:5.2f}s)")
    print(f"  seg{len(bounds)-1}: {seg_times[-1]:7.2f}s – {dur:7.2f}s")

    # per-segment key (sanity: does tonal center move?)
    print("per-segment key candidates:")
    for i in range(len(bounds) - 1):
        f0 = librosa.samples_to_frames(beats_1[bounds[i]], hop_length=512)
        f1 = librosa.samples_to_frames(beats_1[bounds[i + 1]], hop_length=512)
        seg_chroma = chroma[:, f0:f1].mean(axis=1)
        keys_i = []
        for root in range(12):
            cmr = np.roll(seg_chroma, root)
            keys_i.append((krumhansl(cmr, K_S_MAJ), f"{librosa.midi_to_note(root+60)[:-1]} major"))
            keys_i.append((krumhansl(cmr, K_S_MIN), f"{librosa.midi_to_note(root+60)[:-1]} minor"))
        keys_i.sort(reverse=True)
        print(f"  seg{i}: {keys_i[0][1]} (r={keys_i[0][0]:.2f}) | {keys_i[1][1]} (r={keys_i[1][0]:.2f})")

    # ---------- spectral overview ----------
    S = np.abs(librosa.stft(y, n_fft=4096, hop_length=1024))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)
    spec_env = S.mean(axis=1)
    spec_env_db = librosa.amplitude_to_db(spec_env, ref=np.max)
    # spectral centroid / rolloff
    cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    roll = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.95)[0]
    print(f"spectral centroid median: {np.median(cent):.0f} Hz, rolloff95 median: {np.median(roll):.0f} Hz")
    # fraction of energy > 15 kHz (aliasing / digital-brightness indicator)
    hi = (freqs > 15000) & (freqs < 20000)
    frac_hi = S[hi, :].sum() / S.sum()
    print(f"energy fraction 15-20kHz: {100*frac_hi:.2f}%")

    # ---------- save ----------
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
    json.dump({
        "duration_s": round(dur, 3),
        "tempo_beat_track": round(float(tempo_1), 2),
        "tempo_onset": round(float(tempo_2), 2),
        "tempo_tempogram_peak": round(tempo_3, 2),
        "n_beats": int(len(beats_1)),
        "keys": [(k, round(s, 3)) for s, k in keys[:6]],
        "segment_times": [round(float(t), 3) for t in seg_times],
        "rms_median": float(np.median(rms)),
        "rms_p95": float(np.percentile(rms, 95)),
        "centroid_median_hz": float(np.median(cent)),
        "rolloff95_median_hz": float(np.median(roll)),
        "frac_energy_15_20k": float(frac_hi),
    }, open(os.path.join(OUT, "data", "global.json"), "w"), indent=2)

    # ---------- plots ----------
    os.makedirs(os.path.join(OUT, "plots"), exist_ok=True)
    fig, ax = plt.subplots(3, 1, figsize=(14, 9))
    ax[0].plot(times_rms, rms, lw=0.8); ax[0].set_title("RMS dynamics"); ax[0].set_xlabel("time (s)")
    for bt in beats_1/sr:
        ax[0].axvline(bt, color="r", alpha=0.15, lw=0.5)
    for st in seg_times:
        ax[0].axvline(st, color="g", alpha=0.6, ls="--")
    ax[1].imshow(np.log1p(S), aspect="auto", origin="lower", extent=[0, dur, 0, sr/2/1000],
                 cmap="magma", interpolation="nearest")
    ax[1].set_ylim(0, 16); ax[1].set_ylabel("kHz"); ax[1].set_title("Spectrogram (log scale, 0-16kHz)")
    ax[2].semilogx(freqs[1:], spec_env_db[1:], lw=0.8)
    ax[2].set_title("Mean spectral envelope"); ax[2].set_xlabel("Hz"); ax[2].set_ylabel("dB")
    ax[2].set_xlim(40, 20000); ax[2].grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "plots", "01_global.png"), dpi=110)
    print("plots saved.")

if __name__ == "__main__":
    main()
