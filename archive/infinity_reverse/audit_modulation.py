#!/usr/bin/env python3
"""Stage 6 — '9-bit' modulation audit.

A. NMF voice-count estimate on the mid-band (how many concurrent sources)
B. within-note harmonic evolution (duty sweep / timbre modulation)
C. pitch slides between consecutive lead notes
D. noise-percussion spectral character (filtered noise vs sampled drum)
"""
import json
import os
import numpy as np
import librosa
import soundfile as sf

OUT = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(OUT, "audio")
DATA = os.path.join(OUT, "data")
SR = 44100
HOP = 512

def main():
    report = {}

    # ===== A. NMF voice count =====
    print("A. NMF voice count…")
    harm, _ = sf.read(os.path.join(AUD, "stem_harmonic.wav"))
    seg = harm[int(30 * SR):int(70 * SR)]  # main body window
    S = np.abs(librosa.stft(seg, n_fft=2048, hop_length=HOP))
    S = S / (S.max() + 1e-9)
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    band = (freqs > 150) & (freqs < 4000)
    Sb = S[band]
    errs = {}
    for r in [2, 3, 4, 5, 6, 8]:
        W, H = librosa.decompose.decompose(Sb, n_components=r, sort=True)
        approx = W @ H
        err = np.mean((Sb - approx) ** 2) / np.mean(Sb ** 2)
        errs[r] = float(err)
        print(f"  rank {r}: rel. recon error {err:.4f}")
    report["nmf_ranks"] = errs

    # ===== B. within-note harmonic evolution =====
    print("B. within-note timbre evolution…")
    lead_clean, _ = sf.read(os.path.join(AUD, "stem_lead_cleaned.wav"))
    lead_notes = json.load(open(os.path.join(DATA, "lead_notes.json")))
    from timbre import harmonic_profile
    rows = []
    for n in lead_notes:
        if n["end"] - n["start"] > 0.6 and n["midi"] > 55:
            t0 = n["start"]
            profs = []
            for (a, b) in [(0.05, 0.2), (0.2, 0.4), (0.4, 0.6)]:
                s = int((t0 + a) * SR); e = int((t0 + b) * SR)
                if e > len(lead_clean):
                    break
                p = harmonic_profile(lead_clean[s:e], SR, n["hz"])
                profs.append(p)
            if len(profs) == 3:
                # odd/even balance change across windows
                even3 = np.array([p[1] for p in profs])
                odd3 = np.array([p[2] for p in profs])
                rows.append({"t": n["start"], "midi": n["midi"],
                             "h2": [round(float(x), 2) for x in even3],
                             "h3": [round(float(x), 2) for x in odd3]})
    print(f"  {len(rows)} long notes: (h2, h3) across [0.05-0.2, 0.2-0.4, 0.4-0.6]s")
    for r in rows[:10]:
        print(f"    t={r['t']:6.2f} midi={r['midi']:5.1f} h2={r['h2']} h3={r['h3']}")
    report["note_evolution"] = rows[:10]

    # ===== C. pitch slides =====
    print("C. pitch slides…")
    z = np.load(os.path.join(DATA, "f0_tracks.npz"))
    f0l, pl, tl = z["f0l"], z["pl"], z["t"]
    notes = sorted(lead_notes, key=lambda n: n["start"])
    slides = 0
    for a, b in zip(notes[:-1], notes[1:]):
        gap = b["start"] - a["end"]
        if 0.02 < gap < 0.12 and abs(b["midi"] - a["midi"]) > 1:
            i0 = int(a["end"] * SR / 512); i1 = int(b["start"] * SR / 512)
            c = f0l[i0:i1]
            c = c[np.isfinite(c)]
            if len(c) >= 3:
                spread = np.ptp(c)
                if spread > 0.15 * min(a["hz"], b["hz"]):
                    slides += 1
    print(f"  gliding transitions found: {slides} / {len(notes)} gaps")
    report["slides"] = {"gliding": slides, "gaps_checked": len(notes)}

    # ===== D. noise percussion character =====
    print("D. noise percussion character…")
    perc, _ = sf.read(os.path.join(AUD, "stem_percussive.wav"))
    # strongest transient events (top 200 by local crest factor)
    frame = librosa.util.frame(perc, frame_length=2048, hop_length=512)
    crest = np.abs(frame).max(axis=0) / (np.sqrt(np.mean(frame ** 2, axis=0)) + 1e-9)
    top = np.argsort(crest)[::-1][:200]
    flatness = []
    for fi in top:
        Sf = np.abs(librosa.stft(perc[fi * 512:fi * 512 + 8192], n_fft=1024, hop_length=256))
        fsel = librosa.fft_frequencies(sr=SR, n_fft=1024)
        bandm = (fsel > 500) & (fsel < 8000)
        env_t = Sf[bandm].mean(axis=1)  # time average over frames
        # spectral flatness of the burst
        gm = np.exp(np.mean(np.log(env_t[env_t > 1e-6])))
        am = np.mean(env_t[env_t > 1e-6])
        flatness.append(gm / am)
    flatness = np.array(flatness)
    print(f"  top-200 transient spectral flatness: median {np.median(flatness):.3f} "
          f"(white noise ~1.0, tonal ~0.1)")
    report["percussion_flatness"] = {
        "median": float(np.median(flatness)),
        "p25": float(np.percentile(flatness, 25)),
        "p75": float(np.percentile(flatness, 75)),
    }

    json.dump(report, open(os.path.join(DATA, "modulation_audit.json"), "w"), indent=2)
    print("saved data/modulation_audit.json")

if __name__ == "__main__":
    main()
