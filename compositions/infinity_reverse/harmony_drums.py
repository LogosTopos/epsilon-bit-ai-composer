#!/usr/bin/env python3
"""Stage 5a — Harmony, drums & section timbre for reconstruction.

- per-bar chord estimation (chroma + bass-root prior, maj/min/sus templates)
- kick detection from low-band transients of the ORIGINAL (HPSS sends kicks to
  the harmonic stem, so we go back to the source)
- snare/hat pattern from percussive stem (reclassified with tuned rules)
- section-level lead timbre (best-fit notes per structure segment)
Outputs: data/chords.json, data/drums.json, data/section_timbre.json
"""
import json
import os
import numpy as np
import librosa
import soundfile as sf
from collections import Counter
from scipy.signal import butter, sosfiltfilt, hilbert

OUT = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(OUT, "audio")
DATA = os.path.join(OUT, "data")
SR = 44100
HOP = 512
BEAT_S = 0.34830
EIGHTH = BEAT_S / 2
BAR_S = 4 * BEAT_S

MAJ = np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0], float)
MIN = np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0], float)
SUS = np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0], float)
DOM7 = np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0], float)

def main():
    y, _ = librosa.load("/Users/topologyw/Music/网易云音乐/DDRKirby(ISQ) - Infinity.mp3", sr=SR, mono=True)
    harm, _ = sf.read(os.path.join(AUD, "stem_harmonic.wav"))
    perc, _ = sf.read(os.path.join(AUD, "stem_percussive.wav"))
    bass_notes = json.load(open(os.path.join(DATA, "bass_notes.json")))
    lead_notes = json.load(open(os.path.join(DATA, "lead_notes.json")))

    n_bars = int(258.38 // BAR_S)
    bar_starts = np.arange(n_bars) * BAR_S

    # ============ 1. per-bar chords ============
    print("chord estimation…")
    chroma = librosa.feature.chroma_cens(y=y, sr=SR, hop_length=512)
    # bass root per bar from bass notes
    def bar_bass_root(bs):
        roots = [int(round((n["midi"] - 60) % 12)) for n in bass_notes
                 if n["start_q"] >= bs - 0.1 and n["start_q"] < bs + BAR_S - 0.1]
        return Counter(roots).most_common(1)[0][0] if roots else None

    chords = []
    for i, bs in enumerate(bar_starts):
        f0 = int(bs * SR / 512); f1 = int((bs + BAR_S) * SR / 512)
        if f0 >= chroma.shape[1]:
            break
        c = chroma[:, f0:f1].mean(axis=1)
        c = c / (c.max() + 1e-9)
        root_prior = bar_bass_root(bs)
        best = None
        for root in range(12):
            for qual, tmpl in [("maj", MAJ), ("min", MIN), ("sus", SUS), ("7", DOM7)]:
                tm = np.roll(tmpl, root)
                score = np.dot(c, tm)
                if root_prior is not None and root != root_prior:
                    score *= 0.82  # weak prior: favor bass root
                if best is None or score > best[0]:
                    best = (score, root, qual)
        score, root, qual = best
        name = librosa.midi_to_note(root + 60)[:-1] + ("m" if qual == "min" else "" if qual == "maj" else qual)
        chords.append({"bar": i, "t": round(bs, 3), "chord": name, "root": root,
                       "qual": qual, "score": round(float(score), 3),
                       "bass_root": root_prior})
    # dedupe runs
    runs = []
    for ch in chords:
        if runs and runs[-1]["chord"] == ch["chord"] and ch["bar"] == runs[-1]["bar"] + 1:
            runs[-1]["bar_end"] = ch["bar"]; runs[-1]["t_end"] = ch["t"] + BAR_S
        else:
            runs.append(dict(ch, bar_end=ch["bar"], t_end=ch["t"] + BAR_S))
    print(f"  {len(chords)} bars -> {len(runs)} chord runs:")
    for r in runs[:40]:
        print(f"    bar {r['bar']:3d}-{r['bar_end']:3d}  {r['t']:7.2f}-{r['t_end']:7.2f}  {r['chord']:6s} (score {r['score']})")
    json.dump({"bars": chords, "runs": runs}, open(os.path.join(DATA, "chords.json"), "w"), indent=1)

    # ============ 2. kicks ============
    print("kick detection…")
    # low band of original, transient energy
    nyq = SR / 2
    lo = sosfiltfilt(butter(8, [30 / nyq, 130 / nyq], btype="band", output="sos"), y)
    env_low = np.abs(hilbert(lo))
    env_low = env_low / (env_low.max() + 1e-9)
    # smooth + peak-pick
    from scipy.ndimage import uniform_filter1d
    env_s = uniform_filter1d(env_low, 400)
    frame = librosa.util.frame(env_s, frame_length=512, hop_length=256).max(axis=0)
    oenv = np.log1p(frame * 100)
    kicks = librosa.util.peak_pick(oenv, pre_max=8, post_max=8, pre_avg=12, post_avg=12,
                                   delta=0.25, wait=12)
    kick_t = kicks * 256 / SR
    # sanity: align to beat grid (halftime: beats 0,2 of each bar?)
    grid = np.arange(0, 258.38, EIGHTH)
    offs = (kick_t[:, None] - grid[None, :]) / EIGHTH
    closest = np.argmin(np.abs(offs), axis=1)
    dev = np.abs(offs[np.arange(len(kick_t)), closest])
    on_grid = dev < 0.5
    print(f"  {len(kick_t)} kick candidates, {on_grid.sum()} on 8th grid ({100*on_grid.mean():.0f}%)")
    # grid-position histogram (which 8th of the bar)
    pos = (closest[on_grid] % 8)
    hist = np.bincount(pos, minlength=8)
    print("  kick position in bar (8ths):", hist.tolist())
    json.dump({"kick_times": [round(float(t), 3) for t in kick_t]},
              open(os.path.join(DATA, "drums_kick.json"), "w"), indent=1)

    # ============ 3. snare/hat reclassify with tuned rules ============
    print("snare/hat reclassification…")
    z = np.load(os.path.join(DATA, "f0_tracks.npz"))
    ons_p = z["ons_p"]
    S_p = np.abs(librosa.stft(perc, n_fft=2048, hop_length=512))
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    b_lo = (freqs > 40) & (freqs < 120)
    b_mid = (freqs > 150) & (freqs < 400)
    b_noi = (freqs > 1000) & (freqs < 3000)
    b_hi = (freqs > 6000) & (freqs < 12000)
    events = []
    for o in ons_p:
        fr = max(0, o - 2); to = min(S_p.shape[1], o + 30)
        w = S_p[:, fr:to]
        etot = w.sum() + 1e-9
        e_lo = w[b_lo].sum() / etot
        e_mid = w[b_mid].sum() / etot
        e_noi = w[b_noi].sum() / etot
        e_hi = w[b_hi].sum() / etot
        if e_lo > 0.22 and e_hi < 0.12:
            cls = "kick"
        elif e_hi > 0.35 and e_lo < 0.08:
            cls = "hat"
        elif e_noi + e_mid > 0.22 and e_hi < 0.30:
            cls = "snare"
        elif e_hi > 0.25:
            cls = "crash"
        else:
            cls = "other"
        events.append({"t": float(o * 512 / SR), "class": cls})
    # merge events within 40ms (keep strongest class)
    events.sort(key=lambda e: e["t"])
    merged = []
    for e in events:
        if merged and e["t"] - merged[-1]["t"] < 0.04:
            continue
        merged.append(e)
    dc = Counter(e["class"] for e in merged)
    print("  merged drum classes:", dict(dc))
    json.dump([{"t": round(e["t"], 3), "class": e["class"]} for e in merged],
              open(os.path.join(DATA, "drums.json"), "w"), indent=1)

    # ============ 4. section-level lead timbre ============
    print("section lead timbre…")
    seg = json.load(open(os.path.join(DATA, "global.json")))["segment_times"]
    from timbre import harmonic_profile, fit_models
    section_map = {}
    for si in range(len(seg) - 1):
        t0, t1 = seg[si], seg[si + 1]
        notes = [n for n in lead_notes if t0 < n["start"] < t1 and n["end"] - n["start"] > 0.3
                 and n["midi"] > 55]
        fits = []
        for n in notes[:12]:
            s = int((n["start"] + n["end"]) / 2 * SR) - SR // 8
            e = s + SR // 4
            if s < 0 or e > len(harm) or n["hz"] * 24 > SR / 2.2:
                continue
            p = harmonic_profile(harm[s:e], SR, n["hz"])
            if p[0] > 0.05:
                fits.append(fit_models(p))
        if fits:
            c = Counter(f[0] for f in fits)
            section_map[si] = {"n": len(fits), "fits": c.most_common()}
            print(f"  seg{si} [{t0:.1f}-{t1:.1f}s]: {c.most_common()}")
    json.dump(section_map, open(os.path.join(DATA, "section_timbre.json"), "w"), indent=1)
    print("done.")

if __name__ == "__main__":
    main()
