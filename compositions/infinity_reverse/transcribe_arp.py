#!/usr/bin/env python3
"""Transcribe the high-band arp voice (4-16 kHz) and quantize to the 16th grid."""
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
SIXTEENTH = 0.17415 / 2

def main():
    high, _ = sf.read(os.path.join(AUD, "stem_high.wav"))
    f0, voiced, prob = librosa.pyin(high, fmin=500, fmax=8000, sr=SR, hop_length=HOP)
    t = librosa.times_like(f0, sr=SR, hop_length=HOP)
    ok = np.isfinite(f0) & (prob > 0.03)
    # note runs
    runs = np.diff(np.concatenate([[0], ok.astype(int)]))
    starts = np.where(runs == 1)[0]
    ends = np.where(runs == -1)[0]
    if len(ends) == len(starts) - 1:
        ends = np.append(ends, len(ok))
    notes = []
    for s, e in zip(starts, ends):
        if e - s < 2:
            continue
        seg = f0[s:e]
        midi = float(np.median(librosa.hz_to_midi(seg)))
        notes.append({"start": float(t[s]), "end": float(t[e - 1]),
                      "midi": midi, "hz": float(np.median(seg))})
    # quantize to 16th grid
    for n in notes:
        n["start_q"] = round(n["start"] / SIXTEENTH) * SIXTEENTH
        n["end_q"] = round(n["end"] / SIXTEENTH) * SIXTEENTH
    # alignment quality
    dev = np.array([abs(n["start"] / SIXTEENTH - round(n["start"] / SIXTEENTH)) for n in notes])
    print(f"arp: {len(notes)} notes; 16th-grid alignment: median dev {np.median(dev)*100:.1f}% of 16th")
    # dedupe: same pitch & adjacent on grid -> merge
    notes.sort(key=lambda n: n["start_q"])
    merged = []
    for n in notes:
        if merged and n["start_q"] - merged[-1]["end_q"] <= 1e-6 and abs(n["midi"] - merged[-1]["midi"]) < 0.5:
            merged[-1]["end_q"] = max(merged[-1]["end_q"], n["end_q"])
        else:
            merged.append(dict(n))
    durs = np.array([n["end_q"] - n["start_q"] for n in merged])
    print(f"merged: {len(merged)} notes; dur median {np.median(durs)*1000:.0f}ms")
    # pitch histogram
    from collections import Counter
    hist = Counter(int(round(n["midi"])) for n in merged)
    print("top pitches:", hist.most_common(10))
    json.dump(merged, open(os.path.join(DATA, "arp_notes.json"), "w"), indent=1)
    # grid coverage: which 16ths are hit
    grid = np.arange(0, 258.38, SIXTEENTH)
    hits = set()
    for n in merged:
        hits.add(int(round(n["start_q"] / SIXTEENTH)))
    allpos = set(range(len(grid)))
    print(f"16th positions hit: {len(hits)}/{len(grid)} ({100*len(hits)/len(grid):.0f}%)")
    # density map per bar (avg notes per bar)
    import collections
    bars = collections.Counter(int(n["start_q"] // (4 * 0.34830)) for n in merged)
    vals = np.array(list(bars.values()))
    print(f"notes/bar: median {np.median(vals):.0f}, max {vals.max()}")

if __name__ == "__main__":
    main()
