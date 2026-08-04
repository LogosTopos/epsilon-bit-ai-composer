#!/usr/bin/env python3
"""Small artifact verifier for the Threshold of Ashes collection."""
import argparse
import audioop
import math
import os
import wave

import mido


def verify(mid_path, wav_path):
    mid = mido.MidiFile(mid_path)
    notes = sum(1 for tr in mid.tracks for msg in tr
                if msg.type == "note_on" and msg.velocity > 0)
    markers = []
    t = 0
    for msg in mid.tracks[0]:
        t += msg.time
        if msg.type == "marker":
            markers.append((t / mid.ticks_per_beat, msg.text))
    with wave.open(wav_path, "rb") as w:
        raw = w.readframes(w.getnframes())
        rate = w.getframerate()
        duration = w.getnframes() / rate
        width = w.getsampwidth()
    rms = audioop.rms(raw, width) / (2 ** (width * 8 - 1))
    peak = audioop.max(raw, width) / (2 ** (width * 8 - 1))
    rms_db = 20 * math.log10(max(rms, 1e-12))
    peak_db = 20 * math.log10(max(peak, 1e-12))
    assert notes > 100, f"too few MIDI notes: {notes}"
    assert duration > 30, f"too short: {duration:.1f}s"
    assert peak < 0.99, f"near clipping: {peak_db:.2f}dBFS"
    assert any(text == "END" for _, text in markers), "missing END marker"
    print(f"{os.path.basename(mid_path)}: notes={notes} duration={duration:.2f}s "
          f"RMS={rms_db:.2f}dBFS peak={peak_db:.2f}dBFS markers={len(markers)} PASS")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mid", required=True)
    ap.add_argument("--wav", required=True)
    args = ap.parse_args()
    verify(args.mid, args.wav)
