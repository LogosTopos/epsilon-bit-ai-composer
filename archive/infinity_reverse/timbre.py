#!/usr/bin/env python3
"""Stage 4 — Timbre fingerprinting for DDRKirby(ISQ) - Infinity.

Per-voice analysis on transcribed notes:
  1. harmonic amplitude model fit (square50 / pulse25 / pulse12.5 / triangle / saw / exp-decay)
  2. vibrato rate/depth on sustained notes
  3. amplitude envelope (attack/decay)
  4. drum classification + per-class spectra (kick/snare/hat/crash)
  5. reverb tail estimation
  6. stereo width per band (mid/side)
Outputs: data/timbre.json, plots/04_* 05_* 06_*
"""
import json
import os
import numpy as np
import librosa
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, hilbert
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(OUT, "audio")
PLT = os.path.join(OUT, "plots")
DATA = os.path.join(OUT, "data")
SR = 44100
HOP = 512

# ---------- harmonic models: amplitude at harmonic k (normalized to A1=1) ----------
def model_pulse(duty, kmax=24):
    k = np.arange(1, kmax + 1)
    a = np.abs(np.sin(np.pi * k * duty)) / k
    return a / a[0]

def model_triangle(kmax=24):
    k = np.arange(1, kmax + 1)
    a = np.where(k % 2 == 1, 1.0 / k ** 2, 0.0)
    return a / a[0]

def model_saw(kmax=24):
    k = np.arange(1, kmax + 1)
    return 1.0 / k

def model_square(kmax=24):
    k = np.arange(1, kmax + 1)
    a = np.where(k % 2 == 1, 1.0 / k, 0.0)
    return a / a[0]

MODELS = {
    "square50": model_square,
    "pulse25": lambda kmax: model_pulse(0.25, kmax),
    "pulse12.5": lambda kmax: model_pulse(0.125, kmax),
    "triangle": model_triangle,
    "saw": model_saw,
}

def harmonic_profile(x, sr, f0, kmax=24, n_fft=8192):
    """Average amplitude of harmonics k*f0 in signal x.
    Robust: per-frame median across time; ±2% bands; picks frames where the
    fundamental stands out most (least interference)."""
    S = np.abs(librosa.stft(x, n_fft=n_fft, hop_length=2048, window="hann"))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    prof = np.zeros((kmax, S.shape[1]))
    for k in range(1, kmax + 1):
        f = k * f0
        lo, hi = f * 0.98, f * 1.02
        sel = (freqs >= lo) & (freqs <= hi)
        if sel.sum():
            prof[k - 1, :] = S[sel, :].max(axis=0)  # max-pool over the narrow band
    # frame quality: A1 / (A1 + noise floor estimate) — use energy of the frame
    frame_energy = S.sum(axis=0)
    quality = prof[0] / (frame_energy + 1e-9)
    q_med = np.median(quality)
    good = quality >= q_med  # take the better half of frames
    p = np.median(prof[:, good], axis=1)
    if p[0] > 1e-9:
        p = p / p[0]
    return p

def fit_models(prof, kmax=24):
    best = None
    for name, fn in MODELS.items():
        m = fn(kmax)
        # compare on harmonics where model is non-trivial; use log-domain error
        use = (prof > 1e-4) & (m > 1e-4)
        if use.sum() < 3:
            continue
        err = np.sqrt(np.mean((np.log10(prof[use]) - np.log10(m[use])) ** 2))
        if best is None or err < best[1]:
            best = (name, err, float(use.sum()))
    # exponential-decay model (generic synth)
    k = np.arange(1, kmax + 1)
    use = prof > 1e-4
    if use.sum() >= 3:
        lk, lp = np.log(k[use]), np.log(prof[use])
        slope = np.polyfit(lk, lp, 1)[0]
        pred = np.exp(slope * lk)
        err = np.sqrt(np.mean((lp - pred) ** 2))
        if best is None or err < best[1]:
            best = ("exp_decay(1/k^%.2f)" % -slope, err, float(use.sum()))
    return best

def main():
    harm, _ = sf.read(os.path.join(AUD, "stem_harmonic.wav"))
    perc, _ = sf.read(os.path.join(AUD, "stem_percussive.wav"))
    lead_clean, _ = sf.read(os.path.join(AUD, "stem_lead_cleaned.wav"))
    bass_notes = json.load(open(os.path.join(DATA, "bass_notes.json")))
    lead_notes = json.load(open(os.path.join(DATA, "lead_notes.json")))
    z = np.load(os.path.join(DATA, "f0_tracks.npz"))
    ons_p = z["ons_p"]

    report = {}

    # ============ 1. lead harmonic model ============
    print("lead harmonic profiles…")
    lead_long = [n for n in lead_notes if n["end"] - n["start"] > 0.35 and n["midi"] > 55]
    profiles, fitted = [], []
    for n in lead_long[:40]:
        s = int((n["start"] + n["end"]) / 2 * SR) - SR // 8
        e = s + SR // 4
        if s < 0 or e > len(lead_clean):
            continue
        f0 = n["hz"]
        if f0 * 24 > SR / 2.2:
            continue
        prof = harmonic_profile(lead_clean[s:e], SR, f0)
        if prof[0] > 0.05:
            profiles.append(prof)
            fitted.append(fit_models(prof))
    if profiles:
        P = np.array(profiles)
        Pmean = P.mean(axis=0)
        best_global = fit_models(Pmean)
        print(f"  {len(P)} notes profiled; global best: {best_global}")
        from collections import Counter
        print("  per-note best fits:", Counter(f[0] for f in fitted).most_common())
        report["lead_model"] = {"global": best_global,
                                "notes_used": len(P),
                                "per_note": Counter(f[0] for f in fitted).most_common()}
        np.save(os.path.join(DATA, "lead_profiles.npy"), P)
    else:
        Pmean = None

    # ============ 2. bass harmonic model ============
    print("bass harmonic profiles…")
    bass_long = [n for n in bass_notes if n["end"] - n["start"] > 0.3 and 36 < n["midi"] < 46]
    bprofiles, bfitted = [], []
    for n in bass_long[:40]:
        s = int((n["start"] + n["end"]) / 2 * SR) - SR // 8
        e = s + SR // 4
        if s < 0 or e > len(harm):
            continue
        prof = harmonic_profile(harm[s:e], SR, n["hz"])
        if prof[0] > 0.05:
            bprofiles.append(prof)
            bfitted.append(fit_models(prof))
    if bprofiles:
        BP = np.array(bprofiles)
        BPmean = BP.mean(axis=0)
        best_bass = fit_models(BPmean)
        from collections import Counter
        print(f"  {len(BP)} notes profiled; global best: {best_bass}")
        print("  per-note best fits:", Counter(f[0] for f in bfitted).most_common())
        report["bass_model"] = {"global": best_bass, "notes_used": len(BP),
                                "per_note": Counter(f[0] for f in bfitted).most_common()}
        np.save(os.path.join(DATA, "bass_profiles.npy"), BP)
    else:
        BPmean = None

    # ============ 3. vibrato on sustained lead ============
    print("vibrato analysis…")
    vib = []
    for n in lead_notes:
        if n["end"] - n["start"] < 0.5 or n["midi"] < 55:
            continue
        s = int((n["start"] + 0.1) * SR); e = int((n["end"] - 0.05) * SR)
        if e - s < SR // 3:
            continue
        f0, voiced, prob = librosa.pyin(lead_clean[s:e], fmin=max(80, n["hz"] * 0.7),
                                        fmax=min(SR // 2, n["hz"] * 1.4), sr=SR, hop_length=HOP)
        ok = np.isfinite(f0)
        if ok.sum() < 10:
            continue
        c = f0[ok]
        c = c / np.median(c) - 1  # fractional deviation
        nf = len(c)
        if nf < 16:
            continue
        cw = c - np.convolve(c, np.ones(5) / 5, mode="same")  # highpass-ish
        spec = np.abs(np.fft.rfft(cw * np.hanning(nf)))
        freqs_mod = np.fft.rfftfreq(nf, HOP / SR)
        band = (freqs_mod > 2) & (freqs_mod < 15)
        if band.sum() and spec[band].max() > 0:
            fi = np.argmax(spec[band]) 
            rate = freqs_mod[band][fi]
            depth = 2 * spec[band][fi] / (spec[band].sum() + 1e-9) * np.std(cw) * 1200
            vib.append({"rate_hz": float(rate), "depth_cents": float(depth),
                        "note_midi": n["midi"], "t": n["start"]})
    if vib:
        r = np.array([v["rate_hz"] for v in vib]); d = np.array([v["depth_cents"] for v in vib])
        print(f"  {len(vib)} sustained notes: vibrato rate median {np.median(r):.2f} Hz, "
              f"depth median {np.median(d):.1f} cents")
        report["vibrato"] = {"n": len(vib), "rate_median": float(np.median(r)),
                             "depth_median": float(np.median(d))}

    # ============ 4. envelope (attack/decay) on long lead notes ============
    print("envelope analysis…")
    env_atk, env_dec = [], []
    for n in lead_long:
        s = int((n["start"] - 0.01) * SR); e = int((n["start"] + 0.25) * SR)
        if s < 0 or e > len(lead_clean):
            continue
        seg = lead_clean[s:e]
        amp = np.abs(hilbert(seg))
        # 10->90% attack
        p10, p90 = np.percentile(amp, 10), np.percentile(amp, 90)
        if p90 <= p10:
            continue
        thr10 = p10 + 0.1 * (p90 - p10); thr90 = p10 + 0.9 * (p90 - p10)
        cross10 = np.argmax(amp >= thr10); cross90 = np.argmax(amp >= thr90)
        if cross90 > cross10 > 0:
            env_atk.append((cross90 - cross10) / SR)
        # decay from peak to -20dB within 0.5s
        s2 = int(n["start"] * SR); e2 = int((n["start"] + 0.5) * SR)
        seg2 = lead_clean[s2:e2]
        amp2 = np.abs(hilbert(seg2))
        pk = np.argmax(amp2)
        tail = amp2[pk:]
        if len(tail) > 10:
            pkv = tail.max()
            d20 = np.argmax(tail < pkv * 0.1)
            if d20 > 10:
                env_dec.append(d20 / SR)
    if env_atk:
        report["envelope"] = {"attack_median_ms": float(1000 * np.median(env_atk)),
                              "decay20_median_ms": float(1000 * np.median(env_dec)) if env_dec else None}
        print(f"  attack 10-90%: median {1000*np.median(env_atk):.1f} ms; decay-to-20dB: "
              f"{1000*np.median(env_dec):.1f} ms")

    # ============ 5. drums: classify onsets ============
    print("drum classification…")
    S_p = np.abs(librosa.stft(perc, n_fft=2048, hop_length=512))
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    bands = {"kick": (40, 120), "snare_body": (150, 400), "snare_noise": (1000, 3000),
             "hat": (6000, 12000), "crash": (4000, 9000)}
    band_idx = {k: (freqs >= lo) & (freqs <= hi) for k, (lo, hi) in bands.items()}
    drum_events = []
    for o in ons_p:
        fr = max(0, o - 3); to = min(S_p.shape[1], o + 25)  # ~0.3s window
        energies = {k: S_p[sel, fr:to].sum() for k, sel in band_idx.items()}
        etot = S_p[:, fr:to].sum() + 1e-9
        energies = {k: v / etot for k, v in energies.items()}
        # heuristics: kick = strong low; hat = strong 6-12k & weak low; snare = mid+noise
        if energies["kick"] > 0.30 and energies["hat"] < 0.15:
            cls = "kick"
        elif energies["hat"] > 0.30 and energies["kick"] < 0.12:
            cls = "hat"
        elif energies["crash"] > 0.25 and energies["snare_noise"] > 0.12:
            cls = "crash"
        elif energies["snare_noise"] + energies["snare_body"] > 0.20:
            cls = "snare"
        else:
            cls = "other"
        drum_events.append({"t": float(o * 512 / SR), "class": cls, "energies": energies})
    from collections import Counter
    dc = Counter(e["class"] for e in drum_events)
    print("  drum events:", dict(dc))
    report["drums"] = {"n_events": len(drum_events), "classes": dict(dc)}

    # per-class spectral centroid & decay
    drum_spec = {}
    for cls in ["kick", "snare", "hat", "crash"]:
        evs = [e for e in drum_events if e["class"] == cls][:20]
        profs = []
        for e in evs:
            fr = max(0, int(e["t"] * SR / 512)); to = fr + 25
            seg = perc[int(e["t"] * SR):int((e["t"] + 0.3) * SR)]
            if len(seg) < SR // 4:
                continue
            Ss = np.abs(librosa.stft(seg, n_fft=2048, hop_length=512))
            profs.append(Ss.mean(axis=1))
        if profs:
            Pm = np.mean(profs, axis=0)
            cent = np.sum(freqs * Pm) / np.sum(Pm)
            drum_spec[cls] = {"centroid_hz": float(cent)}
            np.save(os.path.join(DATA, f"drum_spec_{cls}.npy"), Pm)
    report["drum_spectra"] = drum_spec
    print("  drum centroids:", {k: round(v["centroid_hz"]) for k, v in drum_spec.items()})

    # ============ 6. reverb tail ============
    print("reverb tail…")
    # find loudest snare, measure percussive decay; and harmonic decay after section gap
    sn = [e for e in drum_events if e["class"] == "snare"]
    if sn:
        e0 = max(sn, key=lambda e: e["energies"]["snare_noise"])
        t0 = e0["t"]
        seg = perc[int(t0 * SR):int((t0 + 2.5) * SR)]
        amp = np.abs(hilbert(seg))
        pk = np.argmax(amp)
        tail = amp[pk:]
        rt60 = None
        for frac in [0.1, 0.01]:
            thr = amp[pk] * frac
            idx = np.argmax(tail < thr)
            if idx > 20:
                rt60 = idx / SR
                break
        print(f"  snare at {t0:.2f}s: tail to -20dB in {rt60:.3f}s" if rt60 else "  no clean tail")
        report["reverb"] = {"snare_tail_to_minus20db_s": rt60}

    # ============ 7. stereo width ============
    print("stereo width…")
    L, _ = sf.read(os.path.join(AUD, "stem_harmonic.wav"))
    y, _ = librosa.load("/Users/topologyw/Music/网易云音乐/DDRKirby(ISQ) - Infinity.mp3", sr=SR, mono=False)
    if y.ndim == 2:
        M = (y[0] + y[1]) / 2
        S_side = (y[0] - y[1]) / 2
        bands_w = {"low": (30, 200), "mid": (200, 2000), "high": (2000, 8000), "veryhigh": (8000, 20000)}
        widths = {}
        for bname, (lo, hi) in bands_w.items():
            Mf = sosfiltfilt(butter(8, [lo / (SR / 2), min(hi / (SR / 2), 0.98)], btype="band", output="sos"), M)
            Sf = sosfiltfilt(butter(8, [lo / (SR / 2), min(hi / (SR / 2), 0.98)], btype="band", output="sos"), S_side)
            widths[bname] = float(np.sqrt(np.mean(Sf ** 2) / (np.mean(Mf ** 2) + 1e-9)))
        print("  side/mid ratio per band:", {k: round(v, 3) for k, v in widths.items()})
        report["stereo_side_mid"] = widths

    json.dump(report, open(os.path.join(DATA, "timbre.json"), "w"), indent=2)

    # ============ plots ============
    fig, axs = plt.subplots(2, 2, figsize=(14, 9))
    k = np.arange(1, 25)
    if Pmean is not None:
        axs[0, 0].bar(k - 0.2, Pmean, width=0.35, label="measured")
        for name, fn in [("square50", model_square), ("pulse25", lambda km: model_pulse(0.25, km))]:
            axs[0, 0].plot(k, fn(24), ".-", lw=0.8, label=name)
        axs[0, 0].set_title("LEAD harmonic profile (mean of %d notes)" % len(P))
        axs[0, 0].set_xlabel("harmonic k"); axs[0, 0].legend(fontsize=8)
    if BPmean is not None:
        axs[0, 1].bar(k - 0.2, BPmean, width=0.35, label="measured")
        axs[0, 1].plot(k, model_triangle(24), ".-", lw=0.8, label="triangle")
        axs[0, 1].plot(k, model_square(24), ".-", lw=0.8, label="square50")
        axs[0, 1].set_title("BASS harmonic profile")
        axs[0, 1].set_xlabel("harmonic k"); axs[0, 1].legend(fontsize=8)
    if vib:
        axs[1, 0].scatter([v["rate_hz"] for v in vib], [v["depth_cents"] for v in vib], s=8)
        axs[1, 0].set_title("vibrato rate vs depth")
        axs[1, 0].set_xlabel("rate (Hz)"); axs[1, 0].set_ylabel("depth (cents)")
    for i, cls in enumerate(["kick", "snare", "hat", "crash"]):
        p = os.path.join(DATA, f"drum_spec_{cls}.npy")
        if os.path.exists(p):
            Pm = np.load(p)
            axs[1, 1].semilogx(freqs[1:], librosa.amplitude_to_db(Pm[1:], ref=np.max(Pm)), lw=0.9, label=cls)
    axs[1, 1].set_title("drum spectra"); axs[1, 1].set_xlim(30, 20000)
    axs[1, 1].legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(PLT, "04_timbre.png"), dpi=110)
    print("saved timbre.json + plots.")

if __name__ == "__main__":
    main()
