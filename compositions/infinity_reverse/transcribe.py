#!/usr/bin/env python3
"""Stage 3 — Pitch transcription (bass + lead) for DDRKirby(ISQ) - Infinity.

- pyin on bass band (30-350 Hz) and mid band (65-2000 Hz) of harmonic stem
- median-filter + onset-guided note segmentation
- quantize to 8th grid at measured tempo
- measure pitch offset (cents vs 12-TET) to detect speed/pitch shifting
Outputs: data/bass_notes.json, data/lead_notes.json, plots/03_transcription_*.png
"""
import json
import os
import numpy as np
import librosa
import soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(OUT, "audio")
PLT = os.path.join(OUT, "plots")
DATA = os.path.join(OUT, "data")

SR = 44100
HOP = 512
BEAT_S = 0.34830      # measured quarter-note (172.27 BPM)
EIGHTH = BEAT_S / 2   # 0.17415 s

def load_stem(name):
    x, _ = sf.read(os.path.join(AUD, f"{name}.wav"))
    return x

def track_pyin(x, fmin, fmax):
    f0, voiced, prob = librosa.pyin(x, fmin=fmin, fmax=fmax, sr=SR, hop_length=HOP)
    t = librosa.times_like(f0, sr=SR, hop_length=HOP)
    return f0, voiced, prob, t

def notes_from_f0(f0, voiced, prob, t, onsets, min_len_s=0.08, conf=0.05):
    """Segment f0 track into notes using onset boundaries + pitch stability.
    Note: pyin prob is calibrated low here (median ~0.01), so conf is tiny."""
    ok = ((prob >= conf) | voiced) & np.isfinite(f0)
    f = np.where(ok, f0, np.nan)
    # median filter to kill octave jumps/spikes (window ~ 90ms)
    fmed = _rolling_median(f, 7)
    # note regions: contiguous voiced runs
    runs = []
    start = None
    for i, v in enumerate(ok):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(ok)))
    notes = []
    for s, e in runs:
        if (t[e - 1] - t[s]) < min_len_s:
            continue
        seg = fmed[s:e]
        valid = seg[~np.isnan(seg)]
        if len(valid) == 0:
            continue
        # sub-segment at onsets (pitch re-articulation)
        subs = [s]
        for o in onsets:
            if s < o < e:
                subs.append(o)
        subs.append(e)
        for a, b in zip(subs[:-1], subs[1:]):
            if (t[b - 1] - t[a]) < min_len_s * 0.6:
                continue
            vv = fmed[a:b]
            vv = vv[~np.isnan(vv)]
            if len(vv) < 2:
                continue
            midi = librosa.hz_to_midi(np.median(vv))
            if midi < 12 or midi > 127:
                continue
            notes.append({
                "start": float(t[a]), "end": float(t[b - 1]),
                "midi": float(midi), "hz": float(np.median(vv)),
                "cents": float(1200 * np.log2(np.median(vv) / librosa.midi_to_hz(round(midi)))),
            })
    return notes

def _rolling_median(arr, w):
    import scipy.ndimage as ndi
    out = np.full_like(arr, np.nan, dtype=float)
    m = ndi.median_filter(arr, size=w, mode="nearest")
    out[~np.isnan(arr)] = m[~np.isnan(arr)]
    return out

def quantize_notes(notes, grid=EIGHTH):
    """Snap start/end to nearest grid point, merge same-pitch adjacent notes."""
    for n in notes:
        n["start_q"] = round(n["start"] / grid) * grid
        n["end_q"] = round(n["end"] / grid) * grid
    notes.sort(key=lambda n: n["start_q"])
    merged = []
    for n in notes:
        if merged and merged[-1]["end_q"] >= n["start_q"] - 1e-6 and \
           abs(merged[-1]["midi"] - n["midi"]) < 0.5:
            merged[-1]["end_q"] = max(merged[-1]["end_q"], n["end_q"])
            merged[-1]["end"] = max(merged[-1]["end"], n["end"])
        else:
            merged.append(dict(n))
    return merged

def main():
    harm, _ = sf.read(os.path.join(AUD, "stem_harmonic.wav"))
    perc, _ = sf.read(os.path.join(AUD, "stem_percussive.wav"))

    # onsets from harmonic stem (note attacks) and percussive (drums)
    oenv_h = librosa.onset.onset_strength(y=harm, sr=SR, hop_length=HOP)
    ons_h = librosa.util.peak_pick(oenv_h, pre_max=8, post_max=8, pre_avg=16,
                                   post_avg=16, delta=0.35, wait=8)
    oenv_p = librosa.onset.onset_strength(y=perc, sr=SR, hop_length=HOP)
    ons_p = librosa.util.peak_pick(oenv_p, pre_max=4, post_max=4, pre_avg=8,
                                   post_avg=8, delta=0.2, wait=5)
    t_all = librosa.times_like(oenv_h, sr=SR, hop_length=HOP)

    # ---- bass (band-limited 30-190 Hz to exclude lead leakage) ----
    from scipy.signal import butter, sosfiltfilt
    nyq = SR / 2
    sos = butter(8, [30 / nyq, 190 / nyq], btype="band", output="sos")
    harm_lo = sosfiltfilt(sos, harm)
    print("tracking bass…")
    f0b, vb, pb, tb = track_pyin(harm_lo, fmin=30, fmax=200)
    bass_notes = notes_from_f0(f0b, vb, pb, tb, ons_p, min_len_s=0.09)
    bass_notes = quantize_notes(bass_notes)
    print(f"bass: {len(bass_notes)} notes")

    # ---- lead: comb-mask bass + harmonics out of the harmonic stem ----
    print("comb-masking bass…")
    S = librosa.stft(harm, n_fft=2048, hop_length=HOP)
    Sabs = np.abs(S)
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    mask = np.ones_like(Sabs)
    f0b_int = np.where(np.isfinite(f0b), f0b, 0)
    for k in range(1, 13):
        hf = f0b_int * k
        lo = hf * 0.94
        hi = hf * 1.06
        for f_idx in range(len(freqs)):
            in_band = (freqs[f_idx] > lo) & (freqs[f_idx] < hi) & (hf > 0) & (freqs[f_idx] > 60)
            mask[f_idx, in_band] = 0.0
    S_lead = S * mask
    sos2 = butter(8, [150 / nyq, 4000 / nyq], btype="band", output="sos")
    harm_lead = sosfiltfilt(sos2, librosa.istft(S_lead, hop_length=HOP))
    sf.write(os.path.join(AUD, "stem_lead_cleaned.wav"),
             harm_lead / (np.max(np.abs(harm_lead)) + 1e-9) * 0.95, SR)

    # ---- lead (tracked on comb-masked mid band) ----
    print("tracking lead…")
    mid_lead, _ = sf.read(os.path.join(AUD, "stem_lead_cleaned.wav"))
    f0l, vl, pl, tl = track_pyin(mid_lead, fmin=100, fmax=3000)
    lead_notes = notes_from_f0(f0l, vl, pl, tl, ons_h, min_len_s=0.08)
    lead_notes = quantize_notes(lead_notes)
    print(f"lead: {len(lead_notes)} notes")

    # ---- pitch offset analysis (speed/pitch shift detection) ----
    for name, f0, prob in [("bass", f0b, pb), ("lead", f0l, pl)]:
        ok = (prob >= 0.6) & np.isfinite(f0)
        cents = 1200 * np.log2(f0[ok] / librosa.midi_to_hz(np.round(librosa.hz_to_midi(f0[ok]))))
        cents = cents[np.abs(cents) < 50]
        hist, edges = np.histogram(cents, bins=np.arange(-50, 51, 2))
        mode = edges[np.argmax(hist)]
        print(f"{name}: median cents-offset {np.median(cents):+.1f}  mode {mode:+.1f}  "
              f"(n={len(cents)}, |c|<50: {100*len(cents)/np.sum(ok):.0f}%)")

    json.dump(bass_notes, open(os.path.join(DATA, "bass_notes.json"), "w"), indent=1)
    json.dump(lead_notes, open(os.path.join(DATA, "lead_notes.json"), "w"), indent=1)
    np.savez(os.path.join(DATA, "f0_tracks.npz"),
             t=tb, f0b=f0b, pb=pb, f0l=f0l, pl=pl,
             oenv_h=oenv_h, oenv_p=oenv_p,
             ons_h=ons_h, ons_p=ons_p)

    # ---- plot: 0-40s transcription overlay ----
    fig, ax = plt.subplots(3, 1, figsize=(15, 9), sharex=True)
    S = librosa.amplitude_to_db(np.abs(librosa.stft(harm, n_fft=2048, hop_length=HOP)), ref=1.0)
    ax[0].imshow(S, aspect="auto", origin="lower", extent=[0, 40, 0, SR/2/1000],
                 cmap="magma", vmin=-80, vmax=0); ax[0].set_ylim(0, 8)
    ax[0].set_ylabel("kHz"); ax[0].set_title("harmonic stem 0-40s")
    for n in lead_notes:
        if n["start"] < 40:
            ax[0].axvspan(n["start"], n["end"], ymin=0, ymax=1, alpha=0.15, color="lime")
    ax[1].plot(tb, f0b, ".", ms=1, alpha=0.4)
    for n in bass_notes:
        ax[1].axvspan(n["start"], n["end"], ymin=0, ymax=1, alpha=0.2, color="cyan")
    ax[1].set_ylim(0, 400); ax[1].set_ylabel("Hz"); ax[1].set_title("bass f0 + notes")
    ax[2].plot(tl, f0l, ".", ms=1, alpha=0.4)
    ax[2].set_ylim(50, 2500); ax[2].set_ylabel("Hz"); ax[2].set_title("lead f0 + notes")
    for n in lead_notes:
        ax[2].axvspan(n["start"], n["end"], ymin=0, ymax=1, alpha=0.15, color="lime")
    ax[2].set_xlabel("time (s)")
    plt.tight_layout()
    plt.savefig(os.path.join(PLT, "03_transcription_0-40s.png"), dpi=110)
    print("saved data + plot.")

if __name__ == "__main__":
    main()
