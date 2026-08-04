#!/usr/bin/env python3
"""Render a short demo using instrument and macro preset cards."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ebit import PresetLibrary, Renderer  # noqa: E402
from ebit.audio.constants import SAMPLE_RATE  # noqa: E402

BPM = 192
OUT_DIR = PROJECT_ROOT / "output" / "preset_demo"


def note(name: str, beat: float, duration: float, velocity: float, **extra: object) -> dict:
    item = {"n": name, "b": round(beat, 4), "d": round(duration, 4), "v": round(velocity, 4)}
    item.update(extra)
    return item


def stats(audio: np.ndarray) -> dict[str, float]:
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(np.square(audio.astype(np.float64))))) if audio.size else 0.0
    return {"peak": round(peak, 6), "rms_db": round(20.0 * math.log10(max(rms, 1e-10)), 2)}


def main() -> None:
    library = PresetLibrary.load(PROJECT_ROOT / "presets")
    renderer = Renderer()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    bass_notes = []
    roots = ["C#2", "A1", "E2", "B1"]
    for bar, root in enumerate(roots):
        beat = bar * 4
        for off in [0.0, 0.75, 1.5, 2.0, 2.75, 3.25]:
            bass_notes.append(note(root, beat + off, 0.28, 0.52 if off in {0.0, 2.0} else 0.4))

    snare_notes = [
        note("D3", 1.0, 0.14, 0.58),
        note("D3", 3.0, 0.14, 0.58),
        library.apply_macro("snare_roll_8", note("D3", 7.0, 0.75, 0.42)),
        note("D3", 9.0, 0.14, 0.58),
        note("D3", 11.0, 0.14, 0.58),
        library.apply_macro("snare_roll_8", note("D3", 15.0, 0.75, 0.46)),
    ]

    arp_notes = []
    pattern = ["C#5", "E5", "G#5", "B5", "E6", "B5", "G#5", "E5"]
    for step in range(64):
        arp_notes.append(note(pattern[step % len(pattern)], step * 0.25, 0.105, 0.22 if step % 4 else 0.3))

    cue_notes = [
        library.apply_macro("quiet_vibrato", note("G#5", 4.5, 0.18, 0.18)),
        library.apply_macro("quiet_vibrato", note("B5", 6.5, 0.18, 0.16)),
        library.apply_macro("alarm_minor_7", note("C#4", 12.0, 0.75, 0.14)),
    ]

    fx_notes = [
        library.apply_macro("teleport_up", note("G#6", 7.5, 0.18, 0.2)),
        library.apply_macro("teleport_up", note("E6", 15.25, 0.16, 0.18), slide_to="B6"),
    ]

    tracks = [
        library.make_track("bass_triangle_drive", bass_notes, name="demo_bass_triangle_drive"),
        library.make_track("drum_snare_noise", snare_notes, name="demo_snare_noise"),
        library.make_track("arp_primary_grid", arp_notes, name="demo_arp_primary_grid"),
        library.make_track("arp_cue_quiet", cue_notes, name="demo_quiet_cue_arp"),
        library.make_track("fx_teleport_chirp", fx_notes, name="demo_teleport_chirp"),
    ]

    composition = {"bpm": BPM, "tracks": tracks}
    audio = renderer.render_stereo(composition, volume=0.58)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.96:
        audio = (audio / peak * 0.94).astype(np.float32)

    renderer.save_wav(audio, str(OUT_DIR / "preset_demo.wav"))
    renderer.save_mp3(audio, str(OUT_DIR / "preset_demo.mp3"), bitrate="224k")
    (OUT_DIR / "preset_demo_score.json").write_text(
        json.dumps(composition, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validation = {"duration_sec": round(len(audio) / SAMPLE_RATE, 2), **stats(audio)}
    (OUT_DIR / "preset_demo_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(OUT_DIR)
    print(f"duration={validation['duration_sec']:.2f}s")
    print(f"peak={validation['peak']}")
    print(f"rms_db={validation['rms_db']}")
    print(OUT_DIR / "preset_demo.mp3")


if __name__ == "__main__":
    main()
