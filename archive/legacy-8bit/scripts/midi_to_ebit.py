#!/usr/bin/env python3
"""Reproduce a reference MIDI through the epsilon-bit render pipeline.

Parses a Standard MIDI File (any type), splits notes by program/percussion,
maps program families onto the project's 8-bit instrument palette, and renders
with the project's PresetLibrary + Renderer. Output mirrors the other demos:
master wav/mp3, stems, midi, score json, validation json, readme.

Usage:
  python3 scripts/midi_to_ebit.py <midi_path> [--max-bars N] [--out NAME] [--bpm X]

  --max-bars N   render only the first N bars (default 64; 0 = full piece)
  --out NAME     output dir name under output/analysis/ (default: midi stem name)
  --bpm X        override tempo (default: tempo from the midi file)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import mido
import numpy as np
import scipy.signal as signal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ebit import PresetLibrary, Renderer  # noqa: E402
from ebit.audio.constants import SAMPLE_RATE  # noqa: E402

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

TAIL_BEATS = 6.0

# ── program family -> project instrument mapping ──────────────────────────
# (family ranges, instrument name, pan, per-note velocity gain)
PROGRAM_MAP: list[tuple[range, str, float, float]] = [
    (range(0, 8), "pulse_25", -0.06, 0.62),       # piano / bright keys
    (range(8, 16), "fm_bell", 0.06, 0.55),        # chromatic percussion (bell-like)
    (range(16, 24), "fm_brass", -0.05, 0.55),     # organs (sustained brass-like body)
    (range(24, 30), "pulse_25", 0.10, 0.50),      # guitars (clean pluck feel)
    (range(30, 32), "sawtooth", -0.10, 0.45),     # distortion / overdrive guitars
    (range(32, 40), "fm_bass", 0.0, 0.72),        # bass family (FM bass body)
    (range(40, 52), "fm_string", 0.0, 0.42),      # strings / ensembles
    (range(52, 60), "pulse_12", 0.08, 0.55),      # brass (trumpet leads)
    (range(60, 72), "pulse_25", 0.0, 0.50),       # reeds
    (range(72, 80), "pulse_50", 0.05, 0.50),      # pipes / synth leads
    (range(80, 88), "pulse_12", 0.10, 0.48),      # synth lead
    (range(88, 96), "fm_string", 0.0, 0.40),      # synth pad
    (range(96, 104), "noise_periodic", 0.0, 0.45),  # synth FX
    (range(104, 112), "fm_string", 0.0, 0.45),    # ethnic / misc
    (range(112, 128), "pulse_50", 0.0, 0.45),     # percussive / SFX fallback
]

# percussion pitch -> (instrument, note name)
DRUM_MAP = {
    35: ("fm", "C2"), 36: ("fm", "C2"),      # kick
    38: ("noise_short", "D3"), 40: ("noise_short", "D3"),  # snare
    42: ("noise_short", "F#5"), 44: ("noise_short", "F#5"), 46: ("noise_short", "F#5"),  # hats
    49: ("noise_short", "C5"), 51: ("noise_short", "C5"), 57: ("noise_short", "C5"), 59: ("noise_short", "C5"),
}


def midi_to_note(value: int) -> str:
    value = max(0, min(127, int(round(value))))
    return f"{NOTE_NAMES[value % 12]}{value // 12 - 1}"


def parse_midi(path: Path) -> tuple[float, dict[tuple[int, int], list[dict[str, Any]]], list[dict[str, Any]]]:
    """Return (bpm, voice_notes, drum_notes).

    voice_notes[(channel, program)] = list of notes — one voice per channel,
    NOT merged by program, so the original voice structure is preserved.
    """
    mid = mido.MidiFile(str(path))
    ticks_per_beat = mid.ticks_per_beat or 480

    bpm = 120.0
    for tr in mid.tracks:
        for msg in tr:
            if msg.type == "set_tempo":
                bpm = mido.tempo2bpm(msg.tempo)
                break
        else:
            continue
        break

    active: dict[tuple[int, int], tuple[int, int, int]] = {}  # (ch,note) -> (start_tick, vel, program)
    voice_notes: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    drums: list[dict[str, Any]] = []
    current_program: dict[int, int] = defaultdict(int)

    for tr in mid.tracks:
        abs_tick = 0
        for msg in tr:
            abs_tick += msg.time
            if msg.type == "program_change":
                current_program[msg.channel] = msg.program
            elif msg.type == "note_on" and msg.velocity > 0:
                active[(msg.channel, msg.note)] = (abs_tick, msg.velocity, current_program[msg.channel])
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in active:
                    start_tick, vel, prog = active.pop(key)
                    end_tick = abs_tick
                    note = {
                        "n": midi_to_note(msg.note),
                        "b": start_tick / ticks_per_beat,
                        "d": max(0.05, (end_tick - start_tick) / ticks_per_beat),
                        "v": min(1.0, vel / 127.0),
                    }
                    if msg.channel == 9 or prog == 128:
                        drums.append(note)
                    else:
                        voice_notes[(msg.channel, prog)].append(note)

    # close any dangling notes at the end
    for (ch, pitch), (start_tick, vel, prog) in active.items():
        note = {
            "n": midi_to_note(pitch),
            "b": start_tick / ticks_per_beat,
            "d": 0.25,
            "v": min(1.0, vel / 127.0),
        }
        if ch == 9:
            drums.append(note)
        else:
            voice_notes[(ch, prog)].append(note)

    return bpm, dict(voice_notes), drums


def map_to_tracks(voice_notes: dict[tuple[int, int], list[dict[str, Any]]], drums: list[dict[str, Any]], name_prefix: str) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []

    for (ch, prog), notes in sorted(voice_notes.items()):
        if not notes:
            continue
        instrument = "pulse_50"
        pan = 0.0
        vel_gain = 0.5
        for rng, inst, p, vg in PROGRAM_MAP:
            if prog in rng:
                instrument, pan, vel_gain = inst, p, vg
                break
        track_notes = [dict(item) for item in notes]
        for item in track_notes:
            item["v"] = round(item["v"] * vel_gain, 4)
        tracks.append({
            "name": f"{name_prefix}_ch{ch}_p{prog}",
            "instrument": instrument,
            "pan": pan,
            "midi_program": prog,
            "midi_channel": ch % 16,
            "notes": track_notes,
        })

    # drums: group by instrument
    drum_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for note in drums:
        inst, pitch_name = DRUM_MAP.get(parse_pitch(note["n"]), ("noise_short", "C5"))
        drum_groups[inst].append({**note, "n": pitch_name, "v": round(note["v"] * 0.75, 4)})
    for inst, notes in drum_groups.items():
        tracks.append({
            "name": f"{name_prefix}_drums_{inst}",
            "instrument": inst,
            "pan": 0.0,
            "midi_program": 0,
            "midi_channel": 9,
            "notes": notes,
        })
    return tracks


def parse_pitch(name: str) -> int:
    note = name[:-1]
    octave = int(name[-1])
    return 12 * (octave + 1) + NOTE_NAMES.index(note)


def pad_audio(audio: np.ndarray, total_samples: int) -> np.ndarray:
    if audio.shape[0] < total_samples:
        padded = np.zeros((total_samples, audio.shape[1]), dtype=audio.dtype)
        padded[: audio.shape[0]] = audio
        return padded
    return audio[:total_samples]


def mix_arrays(arrays: list[np.ndarray], total_samples: int) -> np.ndarray:
    mixed = np.zeros((total_samples, 2), dtype=np.float32)
    for audio in arrays:
        n = min(audio.shape[0], total_samples)
        mixed[:n] += audio[:n]
    return mixed


def butter(audio: np.ndarray, kind: str, cutoff: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, cutoff, btype=kind, fs=SAMPLE_RATE, output="sos")
    return signal.sosfilt(sos, audio).astype(np.float32)


def stats(audio: np.ndarray) -> tuple[float, float]:
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(np.square(audio)))) if audio.size else 0.0
    return peak, 20.0 * math.log10(rms + 1e-12)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("midi", type=Path)
    ap.add_argument("--max-bars", type=int, default=64, help="bars to render (0 = full)")
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--bpm", type=float, default=None)
    args = ap.parse_args()

    bpm, program_notes, drums = parse_midi(args.midi)
    if args.bpm:
        bpm = args.bpm

    # total beats: either full piece (max end) or capped by max_bars
    all_beats = [n["b"] + n["d"] for notes in program_notes.values() for n in notes] + [n["b"] + n["d"] for n in drums]
    full_beats = max(all_beats) if all_beats else 0.0
    if args.max_bars and args.max_bars > 0:
        total_beats = min(full_beats, args.max_bars * 4.0) + TAIL_BEATS
        capped = True
    else:
        total_beats = full_beats + TAIL_BEATS
        capped = False

    beat_sec = 60.0 / bpm
    total_samples = int(round(total_beats * beat_sec * SAMPLE_RATE))

    name = args.out or args.midi.stem
    out_dir = PROJECT_ROOT / "output" / "2026-08-03" / f"touhou_{name}_render_v1"
    stem_dir = out_dir / "stem_mp3"
    source_dir = out_dir / "source"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)

    tracks = map_to_tracks(program_notes, drums, name)
    # cap notes beyond total_beats (keep ones that start before the cap)
    for track in tracks:
        track["notes"] = [n for n in track["notes"] if n["b"] < total_beats]
        track["notes"].sort(key=lambda n: n["b"])

    print(f"voices: {len(tracks)} tracks (per channel+program)")
    library = PresetLibrary.load(PROJECT_ROOT / "presets")
    renderer = Renderer()

    # render per-track stereo, group into buses by instrument family
    buses: dict[str, np.ndarray] = {}
    for idx, track in enumerate(tracks):
        audio = pad_audio(renderer.render_stereo({"bpm": bpm, "tracks": [track]}, volume=0.9), total_samples)
        key = f"{idx:02d}_{track['instrument']}"
        buses[key] = audio

    # bus shaping
    shaped: dict[str, np.ndarray] = {}
    for key, audio in buses.items():
        inst = key.split("_", 1)[1]
        if inst in ("triangle", "fm") or key.endswith("_triangle"):
            shaped[key] = butter(audio, "lowpass", 1600.0)
        elif inst == "fm_string":
            shaped[key] = butter(audio, "lowpass", 5200.0)
        elif inst in ("pulse_12", "pulse_25", "pulse_50", "noise_periodic"):
            shaped[key] = butter(audio, "highpass", 220.0)
        else:
            shaped[key] = audio

    mix = mix_arrays(list(shaped.values()), total_samples)
    mix = butter(mix, "highpass", 24.0)
    mix = np.tanh(mix * 0.8) / np.tanh(0.8)
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    master_gain = 0.94 / peak if peak > 1e-8 else 1.0
    master = (mix * master_gain).astype(np.float32)

    renderer.save_wav(master, str(out_dir / "01_master.wav"))
    renderer.save_mp3(master, str(out_dir / "01_master.mp3"), bitrate="224k")
    for key, audio in shaped.items():
        renderer.save_mp3(audio * master_gain, str(stem_dir / f"{key}.mp3"), bitrate="192k")

    # write source midi (original file copy) + score json + validation
    shutil.copy2(args.midi, source_dir / args.midi.name)
    score = {
        "title": f"touhou {name} reproduction v1",
        "source_midi": str(args.midi),
        "bpm": bpm,
        "total_beats": round(total_beats, 3),
        "capped": capped,
        "max_bars": args.max_bars,
        "track_count": len(tracks),
        "tracks": [{"name": t["name"], "instrument": t["instrument"], "notes": len(t["notes"])} for t in tracks],
    }
    (source_dir / "结构_score.json").write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(Path(__file__), source_dir / Path(__file__).name)

    mp, mr = stats(master)
    validation = {
        "duration_sec": round(master.shape[0] / SAMPLE_RATE, 3),
        "master_peak": round(mp, 6),
        "master_rms_db": round(mr, 2),
        "master_has_nan": bool(np.isnan(master).any()),
        "bus_count": len(buses),
        "pass": not bool(np.isnan(master).any()) and mp <= 0.950001,
    }
    (out_dir / "基础验证.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with (out_dir / "分组stem电平.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["stem", "peak", "rms_db"])
        writer.writeheader()
        for key, audio in shaped.items():
            p, r = stats(audio)
            writer.writerow({"stem": key, "peak": round(p, 6), "rms_db": round(r, 2)})

    (out_dir / "说明.md").write_text(
        f"# touhou {name} reproduction v1\n\n- Source: {args.midi.name}\n- BPM: {bpm}\n- Duration: {validation['duration_sec']}s\n- Tracks: {len(tracks)} (split by program, mapped onto the 8-bit palette)\n- Validation pass: {validation['pass']}\n",
        encoding="utf-8",
    )

    print(out_dir)
    print(f"duration={validation['duration_sec']}s bpm={bpm} tracks={len(tracks)} pass={validation['pass']}")
    print(out_dir / "01_master.mp3")


if __name__ == "__main__":
    main()
