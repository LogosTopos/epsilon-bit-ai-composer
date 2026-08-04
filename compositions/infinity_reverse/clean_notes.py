#!/usr/bin/env python3
"""Clean lead/bass transcriptions with autocorrelation pitch verification.

Fixes (audible artifacts in v1):
  1. lead notes midi < 53 (bass harmonic contamination)
  2. octave errors (pyin locking to a harmonic; e.g. B3 read as B6)
  3. bass notes midi < 36 (sub-octave jitter)
Outputs: data/lead_notes_clean.json, data/bass_notes_clean.json
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
EIGHTH = 0.17415

def autocorr_pitch(x, fmin=50, fmax=4000):
    """Autocorrelation pitch with parabolic interp; returns (f0, confidence)."""
    x = x - x.mean()
    n = len(x)
    w = np.hanning(n)
    ac = np.correlate(x * w, x * w, "full")[n - 1:]
    lo, hi = int(SR / fmax), int(SR / fmin)
    if hi - lo < 4:
        return None, 0
    seg = ac[lo:hi]
    i = int(np.argmax(seg)) + lo
    if i <= 0 or i >= len(ac) - 1:
        return None, 0
    a, b, c = ac[i - 1], ac[i], ac[i + 1]
    denom = a - 2 * b + c
    d = 0.5 * (a - c) / denom if abs(denom) > 1e-12 else 0.0
    T = i + d
    f0 = SR / T
    # confidence: peak-to-second-peak ratio
    seg2 = seg.copy()
    seg2[max(0, i - lo - 3):i - lo + 4] = 0
    second = seg2.max()
    conf = ac[i] / (second + 1e-9) if second > 0 else 0
    return f0, conf

def verify_notes(notes, sig, name, min_midi, verbose=True):
    fixed, dropped, kept = 0, 0, 0
    out = []
    for n in notes:
        midi = n["midi"]
        if midi < min_midi:
            dropped += 1
            continue
        # verify on a steady window in the middle of the note
        dur = n["end_q"] - n["start_q"]
        t0 = n["start_q"] + 0.04
        win = min(0.35, max(0.08, dur * 0.5))
        s, e = int(t0 * SR), int((t0 + win) * SR)
        if s < 0 or e > len(sig):
            out.append(n); kept += 1
            continue
        f0, conf = autocorr_pitch(sig[s:e], fmin=max(40, n["hz"] * 0.35),
                                  fmax=min(6000, n["hz"] * 3.2))
        if f0 is None or conf < 1.6:
            out.append(n); kept += 1  # autocorr unreliable -> keep pyin
            continue
        ac_midi = librosa.hz_to_midi(f0)
        diff = abs(ac_midi - midi)
        if diff > 0.6:  # disagreement -> trust autocorr (validated method)
            new_midi = round(ac_midi * 2) / 2
            # sanity: must stay within an octave of the original claim
            if abs(new_midi - midi) <= 12 and min_midi <= new_midi <= 100:
                n = dict(n, midi=new_midi, hz=float(librosa.midi_to_hz(new_midi)),
                         verified=True)
                fixed += 1
            else:
                dropped += 1
                continue
        out.append(n); kept += 1
    if verbose:
        print(f"{name}: {len(notes)} -> kept {kept}, fixed {fixed}, dropped {dropped}")
    return out

def main():
    lead_clean, _ = sf.read(os.path.join(AUD, "stem_lead_cleaned.wav"))
    harm, _ = sf.read(os.path.join(AUD, "stem_harmonic.wav"))
    lead = json.load(open(os.path.join(DATA, "lead_notes.json")))
    bass = json.load(open(os.path.join(DATA, "bass_notes.json")))
    lead_c = verify_notes(lead, lead_clean, "lead", min_midi=53)
    bass_c = verify_notes(bass, harm, "bass", min_midi=36)
    json.dump(lead_c, open(os.path.join(DATA, "lead_notes_clean.json"), "w"), indent=1)
    json.dump(bass_c, open(os.path.join(DATA, "bass_notes_clean.json"), "w"), indent=1)
    # stats
    import numpy as np
    lm = np.array([n["midi"] for n in lead_c])
    print(f"lead clean: {len(lead_c)} notes, range {lm.min():.0f}-{lm.max():.0f}")

if __name__ == "__main__":
    main()
