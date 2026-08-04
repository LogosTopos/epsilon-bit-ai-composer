#!/usr/bin/env python3
"""Stage 5b — corrected harmony & data-driven drum clustering."""
import json
import os
import numpy as np
import librosa
import soundfile as sf
from collections import Counter
from scipy.signal import butter, sosfiltfilt, hilbert
from scipy.ndimage import uniform_filter1d
from sklearn.cluster import KMeans

OUT = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(OUT, "audio")
DATA = os.path.join(OUT, "data")
SR = 44100
HOP = 512
EIGHTH = 0.17415
BAR_S = 4 * 0.34830

MAJ = np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0], float)
MIN = np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0], float)
SUS = np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0], float)

def main():
    y, _ = librosa.load("/Users/topologyw/Music/网易云音乐/DDRKirby(ISQ) - Infinity.mp3", sr=SR, mono=True)
    perc, _ = sf.read(os.path.join(AUD, "stem_percussive.wav"))
    bass_notes = json.load(open(os.path.join(DATA, "bass_notes.json")))
    z = np.load(os.path.join(DATA, "f0_tracks.npz"))
    ons_p = z["ons_p"]

    # ============ 1. chords without 7th template ============
    print("chord estimation (maj/min/sus)…")
    chroma = librosa.feature.chroma_cens(y=y, sr=SR, hop_length=512)
    n_bars = int(258.38 // BAR_S)
    bar_starts = np.arange(n_bars) * BAR_S

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
        cands = []
        for root in range(12):
            for qual, tmpl in [("maj", MAJ), ("min", MIN), ("sus", SUS)]:
                tm = np.roll(tmpl, root)
                score = np.dot(c, tm)
                if root_prior is not None and root != root_prior:
                    score *= 0.85
                cands.append((score, root, qual))
        cands.sort(reverse=True)
        score, root, qual = cands[0]
        name = librosa.midi_to_note(root + 60)[:-1] + ("m" if qual == "min" else "" if qual == "maj" else qual)
        alt = librosa.midi_to_note(cands[1][1] + 60)[:-1] + ("m" if cands[1][2] == "min" else "")
        chords.append({"bar": i, "t": round(bs, 3), "chord": name, "root": root, "qual": qual,
                       "score": round(float(score), 3), "alt": alt, "bass_root": root_prior})
    runs = []
    for ch in chords:
        if runs and runs[-1]["chord"] == ch["chord"] and ch["bar"] == runs[-1]["bar_end"] + 1:
            runs[-1]["bar_end"] = ch["bar"]; runs[-1]["t_end"] = ch["t"] + BAR_S
        else:
            runs.append(dict(ch, bar_end=ch["bar"], t_end=ch["t"] + BAR_S))
    print(f"  {len(runs)} chord runs:")
    for r in runs:
        print(f"    bar {r['bar']:3d}-{r['bar_end']:3d}  {r['t']:7.2f}-{r['t_end']:7.2f}  {r['chord']:5s} (alt {r['alt']:4s}, bass {r['bass_root']})")
    json.dump({"bars": chords, "runs": runs}, open(os.path.join(DATA, "chords.json"), "w"), indent=1)

    # ============ 2. grid-position analysis (kick/snare placement) ============
    grid = np.arange(0, 258.38, EIGHTH)
    # low-band + click-band onset strengths aligned to grid
    nyq = SR / 2
    lo = sosfiltfilt(butter(8, [30 / nyq, 130 / nyq], btype="band", output="sos"), y)
    env_lo = np.abs(hilbert(lo))
    env_lo = uniform_filter1d(env_lo / (env_lo.max() + 1e-9), 400)
    click = sosfiltfilt(butter(8, [1000 / nyq, 4500 / nyq], btype="band", output="sos"), y)
    env_cl = np.abs(hilbert(click))
    env_cl = uniform_filter1d(env_cl / (env_cl.max() + 1e-9), 200)
    # average energy at each 8th position (over all bars), using small window after grid point
    pos_e_lo = np.zeros(8); pos_e_cl = np.zeros(8); pos_n = np.zeros(8)
    for g in grid[2:-2]:
        i = int(round((g % BAR_S) / EIGHTH)) % 8
        s = int(g * SR); e = int((g + 0.06) * SR)
        pos_e_lo[i] += env_lo[s:e].mean()
        pos_e_cl[i] += env_cl[s:e].mean()
        pos_n[i] += 1
    pos_e_lo /= pos_n; pos_e_cl /= pos_n
    print("avg low-band energy per 8th position:", np.round(pos_e_lo, 4).tolist())
    print("avg click-band energy per 8th position:", np.round(pos_e_cl, 4).tolist())

    # ============ 3. k-means drum clustering ============
    print("drum k-means…")
    S_p = np.abs(librosa.stft(perc, n_fft=2048, hop_length=512))
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    b_lo = (freqs > 40) & (freqs < 120)
    b_mid = (freqs > 150) & (freqs < 400)
    b_noi = (freqs > 1000) & (freqs < 3000)
    b_hi = (freqs > 6000) & (freqs < 12000)
    feats = []
    for o in ons_p:
        fr = max(0, o - 2); to = min(S_p.shape[1], o + 40)
        w = S_p[:, fr:to]
        etot = w.sum() + 1e-9
        # decay time: energy in 2nd half vs 1st half
        w1 = w[:, :20].sum(); w2 = w[:, 20:].sum()
        decay = w2 / (w1 + 1e-9)
        feats.append([w[b_lo].sum() / etot, (w[b_mid].sum() + w[b_noi].sum()) / etot,
                      w[b_hi].sum() / etot, decay])
    F = np.array(feats)
    km = KMeans(n_clusters=4, n_init=10, random_state=0).fit(F)
    labs = km.labels_
    for ci in range(4):
        sub = F[labs == ci]
        print(f"  cluster {ci}: n={len(sub)} mean=[lo {sub[:,0].mean():.3f}, mid+noise {sub[:,1].mean():.3f}, hi {sub[:,2].mean():.3f}, decay {sub[:,3].mean():.3f}]")
    # label clusters by heuristics
    names = {}
    for ci in range(4):
        m = F[labs == ci].mean(axis=0)
        if m[0] > 0.25 and m[3] < 0.5:
            names[ci] = "kick"
        elif m[2] > 0.3 and m[3] < 0.4:
            names[ci] = "hat"
        elif m[2] > 0.3 and m[3] >= 0.4:
            names[ci] = "crash"
        elif m[1] > 0.2:
            names[ci] = "snare"
        else:
            names[ci] = "other"
    print("  labels:", names)
    # positions on grid
    for ci in range(4):
        ts = ons_p[labs == ci] * 512 / SR
        pos = np.round((ts[:, None] - grid[None, :]) / EIGHTH, 5)
        cl = np.argmin(np.abs(pos), axis=1)
        dev = np.abs(pos[np.arange(len(ts)), cl])
        ok = dev < 0.5
        if ok.sum() > 10:
            hist = np.bincount((cl[ok] % 8), minlength=8)
            print(f"  {names[ci]:6s} grid positions (8ths): {hist.tolist()}  off-grid: {ok.sum()}/{len(ts)}")
    # save labeled events
    events = []
    for o, ci in zip(ons_p, labs):
        events.append({"t": round(float(o * 512 / SR), 3), "class": names[ci]})
    events.sort(key=lambda e: e["t"])
    merged = []
    for e in events:
        if merged and e["t"] - merged[-1]["t"] < 0.035 and merged[-1]["class"] != "hat":
            continue
        merged.append(e)
    print("  merged:", dict(Counter(e["class"] for e in merged)))
    json.dump(merged, open(os.path.join(DATA, "drums.json"), "w"), indent=1)

    # ============ 4. kick candidates from click-band too ============
    # kicks = events classified kick in k-means OR low+click coincident on grid 0/4
    kick_cands = [e for e in merged if e["class"] == "kick"]
    pos0_4 = []
    for e in kick_cands:
        dev = np.abs((e["t"] - grid) / EIGHTH)
        gpos = np.argmin(dev)
        if dev[gpos] < 0.5 and (gpos % 8) in (0, 4):
            pos0_4.append(e["t"])
    print(f"  kicks on grid positions 0/4: {len(pos0_4)} / {len(kick_cands)}")
    json.dump({"kick_times": [round(float(t), 3) for t in pos0_4]},
              open(os.path.join(DATA, "drums_kick.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
