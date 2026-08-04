#!/usr/bin/env python3
"""Stage 5c — sweep-based kick detection + pitch-aware snare/hat detection."""
import json
import os
import numpy as np
import librosa
from scipy.signal import butter, sosfiltfilt, hilbert
from collections import Counter

OUT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(OUT, "data")
SR = 44100
EIGHTH = 0.17415
BAR_S = 4 * 0.34830

def band_env(x, sr, lo, hi, order=6):
    nyq = sr / 2
    f = sosfiltfilt(butter(order, [lo / nyq, min(hi / nyq, 0.98)], btype="band", output="sos"), x)
    return np.abs(hilbert(f))

def main():
    y, _ = librosa.load("/Users/topologyw/Music/网易云音乐/DDRKirby(ISQ) - Infinity.mp3", sr=SR, mono=True)
    z = np.load(os.path.join(DATA, "f0_tracks.npz"))
    # lead f0 frames -> times (to veto pitched attacks from snare detection)
    tl, pl = z["t"], z["pl"]
    lead_voiced = (pl > 0.02) & np.isfinite(z["f0l"])
    grid = np.arange(0, 258.38, EIGHTH)

    # ---------- kicks: low-band peak-frequency downward sweeps ----------
    seg_lo = y
    S = np.abs(librosa.stft(seg_lo, n_fft=1024, hop_length=128))
    fr = librosa.fft_frequencies(sr=SR, n_fft=1024)
    sel = (fr >= 30) & (fr <= 200)
    pk = np.argmax(S[sel], axis=0)
    pkf = fr[sel][pk]  # peak freq trajectory, 2.9ms/frame
    # energy threshold: only consider frames with meaningful low energy
    low_energy = S[sel].sum(axis=0)
    thr = np.percentile(low_energy, 55)
    kick_times = []
    i = 0
    n_frames = len(pkf)
    while i < n_frames - 60:
        if low_energy[i] < thr:
            i += 1
            continue
        # look ahead 40 frames (~116ms): peak freq must descend >= 80Hz
        win = pkf[i:i + 40]
        if win.max() - win.min() >= 80 and win[-1] < win[0]:
            # endpoint of sweep
            end = i + np.argmin(win)
            kick_times.append((i + end) * 128 / SR * 0.5 * 2)  # careful with hop
            i = end + 20
        else:
            i += 1
    # hop=128 at sr=44100 -> frame time = 128/44100 = 2.902ms
    kick_times = [t * 2.902e-3 for t in range(len(pkf))]  # placeholder, fixed below

    # redo cleanly with explicit time axis
    frame_t = np.arange(n_frames) * 128 / SR
    kick_times = []
    i = 0
    while i < n_frames - 60:
        if low_energy[i] < thr:
            i += 1
            continue
        win = pkf[i:i + 40]
        if win.max() - win.min() >= 80 and win[-1] < win[0] and win[0] >= 70:
            end = i + int(np.argmin(win))
            kick_times.append(float(frame_t[end]))
            i = end + 25
        else:
            i += 1
    # merge duplicates < 60ms
    kick_times = sorted(kick_times)
    merged = [kick_times[0]] if kick_times else []
    for t in kick_times[1:]:
        if t - merged[-1] > 0.06:
            merged.append(t)
    kick_times = merged
    # grid analysis
    pos_all, dev_all = [], []
    for t in kick_times:
        d = np.abs((t - grid) / EIGHTH)
        g = np.argmin(d)
        pos_all.append(g % 8)
        dev_all.append(d[g])
    dev_all = np.array(dev_all)
    ok = dev_all < 0.5
    print(f"kicks: {len(kick_times)} detected; on-grid {ok.sum()} ({100*ok.mean():.0f}%)")
    if ok.sum():
        hist = np.bincount(np.array(pos_all)[ok], minlength=8)
        print("  grid positions:", hist.tolist())
        print("  sample times:", [round(t, 3) for t in kick_times[:10]])

    # ---------- snares: 1-3kHz noise bursts without concurrent pitched lead ----------
    env_sn = band_env(y, SR, 900, 3500)
    env_sn = env_sn / (env_sn.max() + 1e-9)
    from scipy.ndimage import uniform_filter1d
    env_s = uniform_filter1d(env_sn, 200)
    # onset strength = first difference
    os_ = np.diff(np.concatenate([[0], env_s]))
    os_[os_ < 0] = 0
    frame_l = librosa.util.frame(os_, frame_length=512, hop_length=256).max(axis=0)
    pk_sn = librosa.util.peak_pick(frame_l, pre_max=6, post_max=6, pre_avg=10, post_avg=10,
                                   delta=0.15, wait=10)
    sn_t = pk_sn * 256 / SR
    # veto: pitch track active within 40ms
    keep = []
    for t in sn_t:
        fi = int(t * SR / 512)
        nearby_voice = lead_voiced[max(0, fi - 3):fi + 4].any()
        if not nearby_voice:
            keep.append(t)
    sn_t = keep
    pos_all, dev_all = [], []
    for t in sn_t:
        d = np.abs((t - grid) / EIGHTH)
        g = np.argmin(d)
        pos_all.append(g % 8)
        dev_all.append(d[g])
    dev_all = np.array(dev_all); ok = dev_all < 0.5
    print(f"snares: {len(sn_t)} detected (after pitch veto); on-grid {ok.sum()} ({100*ok.mean():.0f}%)")
    if ok.sum():
        hist = np.bincount(np.array(pos_all)[ok], minlength=8)
        print("  grid positions:", hist.tolist())
        print("  sample times:", [round(t, 3) for t in sn_t[:10]])

    # ---------- hats: 7-12kHz short bursts ----------
    env_ht = band_env(y, SR, 7000, 12000)
    env_ht = env_ht / (env_ht.max() + 1e-9)
    env_h = uniform_filter1d(env_ht, 120)
    os_ = np.diff(np.concatenate([[0], env_h]))
    os_[os_ < 0] = 0
    frame_h = librosa.util.frame(os_, frame_length=512, hop_length=256).max(axis=0)
    pk_ht = librosa.util.peak_pick(frame_h, pre_max=4, post_max=4, pre_avg=8, post_avg=8,
                                   delta=0.12, wait=6)
    ht_t = pk_ht * 256 / SR
    pos_all, dev_all = [], []
    for t in ht_t:
        d = np.abs((t - grid) / EIGHTH)
        g = np.argmin(d)
        pos_all.append(g % 8)
        dev_all.append(d[g])
    dev_all = np.array(dev_all); ok = dev_all < 0.5
    print(f"hats: {len(ht_t)} detected; on-grid {ok.sum()} ({100*ok.mean():.0f}%)")
    if ok.sum():
        hist = np.bincount(np.array(pos_all)[ok], minlength=8)
        print("  grid positions:", hist.tolist())

    # save
    json.dump({
        "kick": [round(t, 3) for t in kick_times],
        "snare": [round(t, 3) for t in sn_t],
        "hat": [round(t, 3) for t in ht_t],
    }, open(os.path.join(DATA, "drums.json"), "w"), indent=1)
    print("saved data/drums.json")

if __name__ == "__main__":
    main()
