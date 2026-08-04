#!/usr/bin/env python3
"""Thermocline bass/drum spine v3.

This version follows the post-v6 direction:

- no aria, choir, chant, or lead role;
- bass_drive is the motif: a slow high-note melody A expanded into a fast
  c-a-a ostinato, where c follows A and a is the fixed low root;
- bass and drums form the complete song spine before harmony and scene detail;
- local third-party sample assets are used as explicit bass/drum layers while
  epsilon-bit synthesis remains the deterministic fallback body.
"""

from __future__ import annotations

import csv
import json
import math
import random
import shutil
import sys
from pathlib import Path
from typing import Any

import mido
import numpy as np
import scipy.signal as signal
import soundfile as sf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ebit import Renderer  # noqa: E402
from ebit.audio.constants import SAMPLE_RATE  # noqa: E402
from ebit.renderer import parse_note  # noqa: E402


random.seed(73)
np.random.seed(73)

BPM = 184.0
BEATS_PER_BAR = 4.0
TOTAL_BARS = 144
TAIL_BEATS = 8.0
TOTAL_BEATS = TOTAL_BARS * BEATS_PER_BAR + TAIL_BEATS
BEAT_SEC = 60.0 / BPM
TOTAL_SAMPLES = int(round(TOTAL_BEATS * BEAT_SEC * SAMPLE_RATE))
TICKS_PER_BEAT = 480

OUT_DIR = PROJECT_ROOT / "output" / "analysis" / "thermocline_bass_drum_spine_v3"
STEM_DIR = OUT_DIR / "stem_mp3"
SOURCE_DIR = OUT_DIR / "source"

SAMPLE_ASSETS = {
    "bass_pizz_rr": [
        PROJECT_ROOT / "research/external_sources/permissive/sfizz/tests/TestFiles/SpecificBugs/MeatBassPizz/Samples/pizz/a0_vl4_rr1.wav",
        PROJECT_ROOT / "research/external_sources/permissive/sfizz/tests/TestFiles/SpecificBugs/MeatBassPizz/Samples/pizz/a0_vl4_rr2.wav",
        PROJECT_ROOT / "research/external_sources/permissive/sfizz/tests/TestFiles/SpecificBugs/MeatBassPizz/Samples/pizz/a0_vl4_rr3.wav",
        PROJECT_ROOT / "research/external_sources/permissive/sfizz/tests/TestFiles/SpecificBugs/MeatBassPizz/Samples/pizz/a0_vl4_rr4.wav",
    ],
    "kick": [PROJECT_ROOT / "research/external_sources/permissive/sfizz/tests/TestFiles/kick.wav"],
    "snare": [PROJECT_ROOT / "research/external_sources/permissive/sfizz/tests/TestFiles/snare.wav"],
    "closed_hat": [PROJECT_ROOT / "research/external_sources/permissive/sfizz/tests/TestFiles/closedhat.wav"],
}

SECTIONS = [
    {
        "name": "cold_start_lock",
        "start_bar": 0,
        "bars": 8,
        "energy": 0.34,
        "groove": "skeleton",
        "intent": "establish the bass-cell identity without aria or lead material",
    },
    {
        "name": "pressure_drive_a",
        "start_bar": 8,
        "bars": 16,
        "energy": 0.70,
        "groove": "drive",
        "intent": "bass phrase becomes the foreground engine over a regular kick/snare grid",
    },
    {
        "name": "cross_current_b",
        "start_bar": 24,
        "bars": 16,
        "energy": 0.76,
        "groove": "syncopated",
        "intent": "same high-low-low motif answered by offbeat kick placement and moving high notes",
    },
    {
        "name": "stasis_drop",
        "start_bar": 40,
        "bars": 8,
        "energy": 0.42,
        "groove": "half_time",
        "intent": "thin the kit and leave a low bass handoff rather than swapping roles",
    },
    {
        "name": "spine_hook_full",
        "start_bar": 48,
        "bars": 24,
        "energy": 0.96,
        "groove": "full",
        "intent": "complete bass/drum hook, with sampled attacks reinforcing the synthetic drive",
    },
    {
        "name": "deep_water_bridge",
        "start_bar": 72,
        "bars": 16,
        "energy": 0.62,
        "groove": "bridge",
        "intent": "reduce hats, keep motif continuity through longer bass ties",
    },
    {
        "name": "overheat_engine",
        "start_bar": 88,
        "bars": 24,
        "energy": 1.00,
        "groove": "overheat",
        "intent": "highest density version of the same motif, not a new lead",
    },
    {
        "name": "counterflow_return",
        "start_bar": 112,
        "bars": 16,
        "energy": 0.84,
        "groove": "counterflow",
        "intent": "bring back the A phrase while percussion stresses cross-current accents",
    },
    {
        "name": "loop_exit_spine",
        "start_bar": 128,
        "bars": 16,
        "energy": 0.72,
        "groove": "exit",
        "intent": "thin decoration first, then cadence the bass phrase back to the opening",
    },
]

ROOT_BLOCKS = [
    "C2", "G1", "D2", "A1", "F1", "C2", "E2", "G1", "D2",
    "A1", "F1", "G1", "C2", "E2", "D2", "G1", "A1", "G1",
]

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

MIDI_PROGRAMS = {
    "bass_sub_floor": 38,
    "bass_drive_core": 38,
    "sampled_bass_pluck": 33,
    "sampled_drum_kick": 0,
    "sampled_drum_snare": 0,
    "sampled_drum_hat": 0,
    "drum_sub_kick": 0,
    "drum_noise_snap": 0,
    "drum_hat_air": 0,
    "drum_ride_noise": 0,
    "harmony_pressure_stabs": 81,
    "harmony_low_pad": 49,
    "decor_metal_sparks": 88,
    "scene_fx_impacts": 97,
}

DRUM_MIDI_NOTES = {
    "sampled_drum_kick": 36,
    "sampled_drum_snare": 38,
    "sampled_drum_hat": 42,
    "drum_sub_kick": 35,
    "drum_noise_snap": 39,
    "drum_hat_air": 42,
    "drum_ride_noise": 51,
}


def n(name: str, beat: float, duration: float, velocity: float, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "n": name,
        "b": round(float(beat), 4),
        "d": round(float(duration), 4),
        "v": round(float(velocity), 4),
    }
    item.update(extra)
    return item


def midi_to_note(value: int) -> str:
    return f"{NOTE_NAMES[value % 12]}{value // 12 - 1}"


def transpose(name: str, semitones: int) -> str:
    return midi_to_note(parse_note(name) + semitones)


def bar_to_beat(bar: int | float) -> float:
    return float(bar) * BEATS_PER_BAR


def beat_to_sample(beat: float) -> int:
    return int(round(beat * BEAT_SEC * SAMPLE_RATE))


def section_end_bar(section: dict[str, Any]) -> int:
    return int(section["start_bar"]) + int(section["bars"])


def section_at_bar(bar: int) -> dict[str, Any]:
    for section in reversed(SECTIONS):
        if bar >= int(section["start_bar"]):
            return section
    return SECTIONS[0]


def section_start(name: str) -> int:
    return next(int(section["start_bar"]) for section in SECTIONS if section["name"] == name)


def root_at_bar(bar: int) -> str:
    return ROOT_BLOCKS[min(bar // 8, len(ROOT_BLOCKS) - 1)]


def next_root_at_bar(bar: int) -> str:
    return ROOT_BLOCKS[min((bar // 8) + 1, len(ROOT_BLOCKS) - 1)]


def pan_stereo(mono: np.ndarray, pan: float) -> np.ndarray:
    pan = max(-1.0, min(1.0, pan))
    angle = (pan + 1.0) * math.pi / 4.0
    return np.column_stack([mono * math.cos(angle), mono * math.sin(angle)]).astype(np.float32)


def pad_audio(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        audio = np.column_stack([audio, audio])
    if audio.shape[0] >= TOTAL_SAMPLES:
        return audio[:TOTAL_SAMPLES].astype(np.float32)
    out = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    out[: audio.shape[0], :] = audio.astype(np.float32)
    return out


def mix_arrays(arrays: list[np.ndarray]) -> np.ndarray:
    out = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    for audio in arrays:
        out += pad_audio(audio)
    return out.astype(np.float32)


def stats(audio: np.ndarray) -> tuple[float, float]:
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(np.square(audio.astype(np.float64))))) if audio.size else 0.0
    return peak, 20.0 * math.log10(max(rms, 1e-10))


def butter(audio: np.ndarray, kind: str, cutoff: float | tuple[float, float], order: int = 2) -> np.ndarray:
    if isinstance(cutoff, tuple):
        normalized: float | list[float] = [cutoff[0] / (SAMPLE_RATE / 2.0), cutoff[1] / (SAMPLE_RATE / 2.0)]
    else:
        normalized = cutoff / (SAMPLE_RATE / 2.0)
    sos = signal.butter(order, normalized, btype=kind, output="sos")
    return np.column_stack([signal.sosfilt(sos, audio[:, channel]) for channel in range(audio.shape[1])]).astype(np.float32)


def add_delay(audio: np.ndarray, delay_beats: float, wet: float, feedback: float = 0.12, cross: bool = True) -> np.ndarray:
    delay_samples = max(1, beat_to_sample(delay_beats))
    out = audio.copy()
    first = np.zeros_like(out)
    first[delay_samples:] = audio[:-delay_samples]
    if cross:
        first = first[:, [1, 0]]
    out += first * wet
    second = np.zeros_like(out)
    if delay_samples * 2 < len(out):
        second[delay_samples * 2:] = audio[: -delay_samples * 2]
    if cross:
        second = second[:, [1, 0]]
    out += second * wet * feedback
    return out.astype(np.float32)


def short_room(audio: np.ndarray, amount: float) -> np.ndarray:
    taps = [(0.031, 0.42), (0.047, 0.30), (0.071, 0.20), (0.113, 0.13)]
    out = audio.copy()
    for seconds, gain in taps:
        shift = int(round(seconds * SAMPLE_RATE))
        delayed = np.zeros_like(out)
        delayed[shift:] = audio[:-shift]
        out += delayed[:, [1, 0]] * (amount * gain)
    return out.astype(np.float32)


def sidechain_duck(audio: np.ndarray, trigger: np.ndarray, depth: float, release_ms: float = 80.0) -> np.ndarray:
    mono = np.abs(trigger.mean(axis=1)).astype(np.float32)
    alpha = math.exp(-1.0 / max(SAMPLE_RATE * release_ms / 1000.0, 1.0))
    envelope = signal.lfilter([1.0 - alpha], [1.0, -alpha], mono)
    peak = float(np.max(envelope)) if envelope.size else 0.0
    if peak > 1e-8:
        envelope = envelope / peak
    return (audio * (1.0 - depth * envelope[:, None])).astype(np.float32)


def soft_clip(audio: np.ndarray, drive: float) -> np.ndarray:
    return (np.tanh(audio * drive) / max(np.tanh(drive), 1e-9)).astype(np.float32)


def make_track(
    name: str,
    instrument: str,
    notes: list[dict[str, Any]],
    pan: float = 0.0,
    midi_program: int | None = None,
    midi_channel: int = 0,
) -> dict[str, Any]:
    tail = n("C0", TOTAL_BEATS - 0.125, 0.125, 0.0)
    return {
        "name": name,
        "instrument": instrument,
        "pan": pan,
        "midi_program": MIDI_PROGRAMS.get(name, 80) if midi_program is None else midi_program,
        "midi_channel": midi_channel,
        "notes": sorted(notes + [tail], key=lambda item: (float(item["b"]), str(item["n"]))),
    }


def render_synth_bus(renderer: Renderer, tracks: list[dict[str, Any]], volume: float) -> np.ndarray:
    rendered = renderer.render_multi_stereo({"bpm": BPM, "tracks": tracks}, volume=volume)
    return mix_arrays(list(rendered.values()))


def write_wav_mp3(renderer: Renderer, audio: np.ndarray, stem: Path, bitrate: str = "256k") -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    sf.write(stem.with_suffix(".wav"), audio, SAMPLE_RATE)
    renderer.save_mp3(audio, str(stem.with_suffix(".mp3")), bitrate=bitrate)


def write_mp3(renderer: Renderer, audio: np.ndarray, path: Path, bitrate: str = "224k") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    renderer.save_mp3(audio, str(path), bitrate=bitrate)


def humanize(base: float, amount: float) -> float:
    return max(0.0, base + random.uniform(-amount, amount))


def chord_notes(root: str, intervals: list[int], octave_shift: int = 12) -> list[str]:
    shifted = transpose(root, octave_shift)
    return [transpose(shifted, interval) for interval in intervals]


# Slow high-note melody A over one 8-bar block. Each slow note c lasts an
# integer number of beats; each beat is expanded into c-a-a where a is the
# current low root.
SLOW_HIGH_MELODY_A: list[tuple[float, float, int | str]] = [
    (0.0, 4.0, 16),
    (4.0, 2.0, 19),
    (6.0, 2.0, 21),
    (8.0, 4.0, 19),
    (12.0, 2.0, 16),
    (14.0, 2.0, 14),
    (16.0, 4.0, 16),
    (20.0, 2.0, 18),
    (22.0, 2.0, 21),
    (24.0, 3.0, 23),
    (27.0, 1.0, 21),
    (28.0, 2.0, 19),
    (30.0, 2.0, "next+16"),
]

OSTINATO_CELL_BEATS = 1.0
OSTINATO_OFFSETS = (0.0, 1.0 / 3.0, 2.0 / 3.0)


def resolve_phrase_pitch(root: str, next_root: str, pitch_ref: int | str) -> str:
    if isinstance(pitch_ref, int):
        return transpose(root, pitch_ref)
    if pitch_ref == "next":
        return next_root
    if pitch_ref.startswith("next+"):
        return transpose(next_root, int(pitch_ref.replace("next+", "")))
    if pitch_ref.startswith("next"):
        return transpose(next_root, int(pitch_ref.replace("next", "")))
    raise ValueError(f"Unknown pitch reference: {pitch_ref}")


def high_melody_ref_at_phrase_beat(phrase_beat: float) -> int | str:
    phrase_beat = phrase_beat % 32.0
    for start, duration, pitch_ref in SLOW_HIGH_MELODY_A:
        if start <= phrase_beat < start + duration:
            return pitch_ref
    return SLOW_HIGH_MELODY_A[-1][2]


def high_melody_pitch_at_beat(beat: float) -> str:
    bar = min(TOTAL_BARS - 1, max(0, int(beat // BEATS_PER_BAR)))
    phrase_beat = beat % (8.0 * BEATS_PER_BAR)
    pitch_ref = high_melody_ref_at_phrase_beat(phrase_beat)
    return resolve_phrase_pitch(root_at_bar(bar), next_root_at_bar(bar), pitch_ref)


def beat_section(beat: float) -> dict[str, Any]:
    return section_at_bar(min(TOTAL_BARS - 1, max(0, int(beat // BEATS_PER_BAR))))


def build_bass_groups() -> dict[str, list[dict[str, Any]]]:
    sub_floor: list[dict[str, Any]] = []
    drive_core: list[dict[str, Any]] = []
    sampled_pluck: list[dict[str, Any]] = []

    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        energy = float(section["energy"])
        groove = str(section["groove"])
        beat = bar_to_beat(bar)
        root = root_at_bar(bar)

        floor_vel = 0.26 + energy * 0.08
        if groove in {"skeleton", "half_time", "bridge"}:
            floor_vel *= 0.86
        sub_floor.append(n(transpose(root, -12), beat, 3.88, floor_vel))

    cell_start = 0.0
    while cell_start < TOTAL_BARS * BEATS_PER_BAR - 0.0001:
        bar = min(TOTAL_BARS - 1, int(cell_start // BEATS_PER_BAR))
        section = beat_section(cell_start)
        rel = bar - int(section["start_bar"])
        energy = float(section["energy"])
        root = root_at_bar(bar)
        high_pitch = high_melody_pitch_at_beat(cell_start)
        pan = -0.05 if (bar // 2) % 2 else 0.05
        gain = 0.72 + energy * 0.45
        if rel < 2:
            gain *= 0.78

        high_beat = cell_start + OSTINATO_OFFSETS[0]
        low_beat_1 = cell_start + OSTINATO_OFFSETS[1]
        low_beat_2 = cell_start + OSTINATO_OFFSETS[2]

        high_vel = humanize(0.84 * gain, 0.035)
        low_vel_1 = humanize(0.62 * gain, 0.030)
        low_vel_2 = humanize(0.72 * gain, 0.030)
        drive_core.append(n(high_pitch, high_beat, 0.22, high_vel, pan=pan, role="slow_melody_high"))
        drive_core.append(n(root, low_beat_1, 0.16, low_vel_1, pan=-pan, role="fixed_low_anchor"))
        drive_core.append(n(root, low_beat_2, 0.22, low_vel_2, pan=-pan, role="fixed_low_anchor"))

        sample_dur = 0.28 if energy >= 0.85 else 0.34
        sampled_pluck.append(n(high_pitch, high_beat, sample_dur, humanize(0.44 + energy * 0.24, 0.035)))
        cell_start += OSTINATO_CELL_BEATS

    return {
        "bass_sub_floor": [make_track("bass_sub_floor", "sine", sub_floor, midi_program=38)],
        "bass_drive_core": [make_track("bass_drive_core", "triangle", drive_core, midi_program=38)],
        "sampled_bass_pluck": [make_track("sampled_bass_pluck", "sample_bass_pizz", sampled_pluck, midi_program=33)],
    }


def kick_offsets(groove: str, phrase_pos: int, rel: int) -> list[float]:
    if groove == "skeleton":
        return [0.0] if rel < 4 else [0.0, 2.5]
    if groove == "half_time":
        return [0.0, 3.0] if phrase_pos in {1, 5, 7} else [0.0]
    if groove == "bridge":
        return [0.0, 2.75] if phrase_pos % 2 else [0.0, 2.0]
    if groove == "drive":
        return [0.0, 1.5, 2.5, 3.25] if phrase_pos not in {3, 7} else [0.0, 2.0, 3.5]
    if groove == "syncopated":
        return [0.0, 1.25, 2.5, 3.25] if phrase_pos % 2 else [0.0, 1.5, 2.25, 3.5]
    if groove == "full":
        return [0.0, 1.0, 2.0, 3.0] if phrase_pos in {0, 4} else [0.0, 1.5, 2.5, 3.25]
    if groove == "overheat":
        return [0.0, 0.75, 1.5, 2.25, 3.25] if phrase_pos not in {3, 7} else [0.0, 1.0, 2.0, 3.5]
    if groove == "counterflow":
        return [0.0, 1.5, 2.0, 3.25] if phrase_pos % 2 else [0.0, 0.75, 2.5, 3.5]
    if groove == "exit":
        return [0.0, 1.5, 2.5, 3.25] if rel < 12 else [0.0, 2.0]
    return [0.0, 2.5]


def snare_offsets(groove: str, phrase_pos: int, rel: int) -> list[float]:
    if groove == "skeleton":
        return [] if rel < 4 else [3.0]
    if groove == "half_time":
        return [3.0] if phrase_pos % 2 == 0 else []
    if groove == "bridge":
        return [2.5] if phrase_pos in {1, 3, 5, 7} else []
    if groove in {"full", "overheat", "counterflow"}:
        return [1.0, 3.0]
    if groove == "exit" and rel >= 12:
        return [2.0]
    return [1.0, 3.0]


def hat_grid(groove: str, phrase_pos: int, rel: int) -> list[float]:
    if groove == "skeleton":
        return [0.0, 2.0] if rel < 4 else [i * 0.5 for i in range(8)]
    if groove == "half_time":
        return [0.0, 1.0, 2.0, 3.0]
    if groove == "bridge":
        return [i * 0.5 for i in range(8)]
    if groove in {"full", "overheat", "counterflow"}:
        return [i * 0.25 for i in range(16)]
    if groove == "exit" and rel >= 12:
        return [0.0, 1.0, 2.0, 3.0]
    return [i * 0.5 for i in range(8)] if phrase_pos in {0, 3, 7} else [i * 0.25 for i in range(16)]


def build_drum_groups() -> dict[str, list[dict[str, Any]]]:
    kick: list[dict[str, Any]] = []
    snare: list[dict[str, Any]] = []
    hat: list[dict[str, Any]] = []
    sub_kick: list[dict[str, Any]] = []
    snap: list[dict[str, Any]] = []
    hat_air: list[dict[str, Any]] = []
    ride: list[dict[str, Any]] = []

    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        start_bar = int(section["start_bar"])
        rel = bar - start_bar
        end_bar = section_end_bar(section)
        phrase_pos = bar % 8
        beat = bar_to_beat(bar)
        energy = float(section["energy"])
        groove = str(section["groove"])
        is_fill = phrase_pos == 7 or bar == end_bar - 1

        kicks = kick_offsets(groove, phrase_pos, rel)
        snares = snare_offsets(groove, phrase_pos, rel)
        hats = hat_grid(groove, phrase_pos, rel)

        if is_fill and groove not in {"skeleton", "half_time"}:
            kicks = sorted(set(kicks + [3.5]))
            snares = sorted(set(snares + [3.0, 3.25, 3.5, 3.75]))

        for off in kicks:
            strong = off in {0.0, 2.0}
            vel = humanize((0.58 + energy * 0.28) * (1.10 if strong else 0.88), 0.045)
            kick.append(n("C2", beat + off, 0.20, vel, drum_note=36))
            if strong or energy >= 0.90:
                sub_kick.append(n("C1", beat + off, 0.28, humanize(0.24 + energy * 0.17, 0.025), drum_note=35))

        for idx, off in enumerate(snares):
            fill_scale = 0.58 if is_fill and off >= 3.0 else 1.0
            vel = humanize((0.48 + energy * 0.26) * fill_scale, 0.045)
            snare.append(n("D3", beat + off, 0.20, vel, pan=-0.06 if idx % 2 else 0.06, drum_note=38))
            snap.append(n("D4", beat + off + 0.014, 0.07, vel * 0.32, pan=0.0, drum_note=39, fx={"retrigger": 2}))

        if groove in {"drive", "syncopated", "full", "overheat", "counterflow"} and not is_fill:
            for off in [0.75, 2.75]:
                if any(abs(off - s) < 0.18 for s in snares):
                    continue
                snap.append(n("D3", beat + off, 0.045, humanize(0.08 + energy * 0.07, 0.018),
                              pan=random.uniform(-0.16, 0.16), drum_note=37))

        for idx, off in enumerate(hats):
            is_accent = abs(off % 1.0) < 1e-6
            vel = humanize((0.18 + energy * 0.12) * (1.32 if is_accent else 0.82), 0.035)
            pan = -0.32 if idx % 2 else 0.32
            hat.append(n("F#5", beat + off, 0.055, vel, pan=pan, drum_note=42))
            hat_air.append(n("F#5", beat + off, 0.045, vel * 0.80, pan=pan, drum_note=42))

        if groove in {"full", "overheat"} and phrase_pos in {0, 4} and rel >= 4:
            ride.append(n("A5", beat, 0.24, humanize(0.22 + energy * 0.12, 0.035), drum_note=51))

    return {
        "sampled_drum_kick": [make_track("sampled_drum_kick", "sample_kick", kick, midi_channel=9)],
        "sampled_drum_snare": [make_track("sampled_drum_snare", "sample_snare", snare, midi_channel=9)],
        "sampled_drum_hat": [make_track("sampled_drum_hat", "sample_closed_hat", hat, midi_channel=9)],
        "drum_sub_kick": [make_track("drum_sub_kick", "sine", sub_kick, midi_channel=9)],
        "drum_noise_snap": [make_track("drum_noise_snap", "noise_short", snap, midi_channel=9)],
        "drum_hat_air": [make_track("drum_hat_air", "noise_short", hat_air, midi_channel=9)],
        "drum_ride_noise": [make_track("drum_ride_noise", "noise_periodic", ride, midi_channel=9)],
    }


def build_support_groups() -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    stabs: list[dict[str, Any]] = []
    pads: list[dict[str, Any]] = []
    sparks: list[dict[str, Any]] = []
    impacts: list[dict[str, Any]] = []
    event_counts = {"metal_spark": 0, "impact": 0, "riser": 0}

    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        start_bar = int(section["start_bar"])
        end_bar = section_end_bar(section)
        rel = bar - start_bar
        phrase_pos = bar % 8
        beat = bar_to_beat(bar)
        root = root_at_bar(bar)
        energy = float(section["energy"])
        groove = str(section["groove"])

        if phrase_pos in {0, 4}:
            high_pitch = high_melody_pitch_at_beat(beat)
            pitches = [transpose(root, 12), transpose(root, 19), high_pitch]
            if groove not in {"skeleton", "half_time", "bridge"}:
                pitches.append(transpose(root, 22))
            for idx, pitch in enumerate(pitches):
                stabs.append(n(pitch, beat + 0.06 * idx, 0.58, humanize(0.15 + energy * 0.08, 0.02),
                               pan=-0.18 + idx * 0.12))

        if phrase_pos == 2 and groove not in {"skeleton"}:
            high_support = transpose(high_melody_pitch_at_beat(beat), -12)
            pitches = [root, transpose(root, 7), high_support, transpose(root, 12)]
            for idx, pitch in enumerate(pitches):
                pads.append(n(pitch, beat, 7.70, humanize(0.08 + energy * 0.06, 0.015), pan=-0.24 + idx * 0.16))

        is_section_edge = rel == 0 or bar == end_bar - 1
        is_phrase_handoff = phrase_pos == 7
        if (is_section_edge or is_phrase_handoff) and groove not in {"skeleton"}:
            for off, interval in [(0.0, 24), (1.5, 31), (3.0, 26)]:
                if event_counts["metal_spark"] % 3 == 1 and not is_section_edge:
                    event_counts["metal_spark"] += 1
                    continue
                sparks.append(n(transpose(root, interval), beat + off + 0.08, 0.06,
                                humanize(0.06 + energy * 0.045, 0.012),
                                pan=-0.42 + 0.42 * (event_counts["metal_spark"] % 3)))
                event_counts["metal_spark"] += 1

        if is_section_edge:
            impacts.append(n(transpose(root, -12), beat + 0.015, 0.24, humanize(0.15 + energy * 0.13, 0.025)))
            event_counts["impact"] += 1

        if bar in {47, 87, 111, 127}:
            for idx, off in enumerate([2.50, 2.75, 3.00, 3.25, 3.50]):
                sparks.append(n(transpose(root, 19 + idx), beat + off, 0.055, 0.07 + idx * 0.01, pan=-0.35 + idx * 0.18))
                event_counts["riser"] += 1

    return {
        "harmony_pressure_stabs": [make_track("harmony_pressure_stabs", "fm_brass", stabs, midi_program=81)],
        "harmony_low_pad": [make_track("harmony_low_pad", "fm_string", pads, midi_program=49)],
        "decor_metal_sparks": [make_track("decor_metal_sparks", "pulse_12", sparks, midi_program=88)],
        "scene_fx_impacts": [make_track("scene_fx_impacts", "fm_bass", impacts, midi_program=97)],
    }, event_counts


# Sample renderer

def load_mono_sample(path: Path) -> np.ndarray:
    audio, sr = sf.read(path, always_2d=True, dtype="float32")
    if sr != SAMPLE_RATE:
        gcd = math.gcd(sr, SAMPLE_RATE)
        audio = signal.resample_poly(audio, SAMPLE_RATE // gcd, sr // gcd, axis=0).astype(np.float32)
    mono = audio.mean(axis=1).astype(np.float32)
    peak = float(np.max(np.abs(mono))) if mono.size else 0.0
    if peak > 1e-8:
        mono = mono / peak
    return trim_sample(mono)


def trim_sample(sample: np.ndarray) -> np.ndarray:
    if not sample.size:
        return sample
    threshold = max(float(np.max(np.abs(sample))) * 0.004, 1e-5)
    indices = np.flatnonzero(np.abs(sample) > threshold)
    if len(indices) == 0:
        return sample
    start = max(0, int(indices[0]) - 128)
    end = min(len(sample), int(indices[-1]) + int(0.15 * SAMPLE_RATE))
    return sample[start:end].astype(np.float32)


def load_sample_bank() -> dict[str, list[np.ndarray]]:
    missing = [str(path) for paths in SAMPLE_ASSETS.values() for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing sample assets:\n" + "\n".join(missing))
    return {name: [load_mono_sample(path) for path in paths] for name, paths in SAMPLE_ASSETS.items()}


def playback_sample(source: np.ndarray, n_samples: int, ratio: float, velocity: float, release_ms: float) -> np.ndarray:
    if n_samples <= 0:
        return np.zeros(0, dtype=np.float32)
    idx = np.arange(n_samples, dtype=np.float32) * ratio
    valid = idx < (len(source) - 1)
    out = np.zeros(n_samples, dtype=np.float32)
    if np.any(valid):
        base_idx = idx[valid]
        out[valid] = np.interp(base_idx, np.arange(len(source), dtype=np.float32), source).astype(np.float32)
    attack = min(max(8, int(0.0025 * SAMPLE_RATE)), n_samples)
    release = min(max(8, int(release_ms / 1000.0 * SAMPLE_RATE)), n_samples)
    env = np.ones(n_samples, dtype=np.float32)
    if attack > 1:
        env[:attack] *= np.linspace(0.0, 1.0, attack, dtype=np.float32)
    if release > 1:
        env[-release:] *= np.linspace(1.0, 0.0, release, dtype=np.float32)
    return (out * env * velocity).astype(np.float32)


def render_sampled_bass(track: dict[str, Any], bank: dict[str, list[np.ndarray]], gain: float) -> np.ndarray:
    out = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    samples = bank["bass_pizz_rr"]
    base_midi = 21  # A0 sample root from the sfizz MeatBassPizz fixture.
    rr = 0
    for item in track.get("notes", []):
        velocity = float(item.get("v", 0.0))
        if velocity <= 0:
            continue
        start = beat_to_sample(float(item["b"]))
        n_samples = int(round(float(item["d"]) * BEAT_SEC * SAMPLE_RATE))
        if start >= TOTAL_SAMPLES or n_samples <= 0:
            continue
        end = min(TOTAL_SAMPLES, start + n_samples)
        n_samples = end - start
        pitch = parse_note(str(item["n"]))
        ratio = 2.0 ** ((pitch - base_midi) / 12.0)
        src = samples[rr % len(samples)]
        rr += 1
        mono = playback_sample(src, n_samples, ratio, velocity * gain, release_ms=90.0)
        out[start:end] += pan_stereo(mono, float(item.get("pan", 0.0)))
    return out


def render_sampled_drums(track: dict[str, Any], bank: dict[str, list[np.ndarray]], asset_name: str, gain: float) -> np.ndarray:
    out = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    src = bank[asset_name][0]
    for item in track.get("notes", []):
        velocity = float(item.get("v", 0.0))
        if velocity <= 0:
            continue
        start = beat_to_sample(float(item["b"]))
        n_samples = int(round(float(item["d"]) * BEAT_SEC * SAMPLE_RATE))
        if asset_name == "kick":
            n_samples = max(n_samples, int(0.32 * SAMPLE_RATE))
            release_ms = 120.0
        elif asset_name == "snare":
            n_samples = max(n_samples, int(0.22 * SAMPLE_RATE))
            release_ms = 85.0
        else:
            n_samples = max(n_samples, int(0.075 * SAMPLE_RATE))
            release_ms = 35.0
        if start >= TOTAL_SAMPLES:
            continue
        end = min(TOTAL_SAMPLES, start + n_samples)
        n_samples = end - start
        mono = playback_sample(src, n_samples, 1.0, velocity * gain, release_ms=release_ms)
        out[start:end] += pan_stereo(mono, float(item.get("pan", 0.0)))
    return out


# MIDI and reports

def write_midi(path: Path, groups: dict[str, list[dict[str, Any]]], include_groups: set[str] | None = None) -> None:
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("track_name", name="thermocline_bass_drum_spine_v3", time=0))
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    midi.tracks.append(meta)

    tracks: list[dict[str, Any]] = []
    for group, group_tracks in groups.items():
        if include_groups is not None and group not in include_groups:
            continue
        tracks.extend(group_tracks)

    for src in tracks:
        name = str(src.get("name", src.get("instrument", "track")))
        channel = int(src.get("midi_channel", 0))
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name=name, time=0))
        if channel != 9:
            track.append(mido.Message(
                "program_change",
                program=max(0, min(127, int(src.get("midi_program", MIDI_PROGRAMS.get(name, 80))))),
                channel=channel,
                time=0,
            ))
        events: list[tuple[int, int, mido.Message]] = []
        for item in src.get("notes", []):
            velocity_value = float(item.get("v", 0.0))
            if velocity_value <= 0:
                continue
            start = int(round(float(item["b"]) * TICKS_PER_BEAT))
            end = int(round((float(item["b"]) + float(item["d"])) * TICKS_PER_BEAT))
            if end <= start:
                continue
            if channel == 9:
                pitch = int(item.get("drum_note", DRUM_MIDI_NOTES.get(name, 36)))
            else:
                pitch = parse_note(str(item["n"]))
            velocity = max(1, min(127, int(round(velocity_value * 127))))
            events.append((start, 1, mido.Message("note_on", note=pitch, velocity=velocity, channel=channel, time=0)))
            events.append((end, 0, mido.Message("note_off", note=pitch, velocity=0, channel=channel, time=0)))
        events.sort(key=lambda event: (event[0], event[1]))
        cursor = 0
        for tick, _order, message in events:
            message.time = max(0, tick - cursor)
            track.append(message)
            cursor = tick
        final_tick = int(round(TOTAL_BEATS * TICKS_PER_BEAT))
        track.append(mido.MetaMessage("end_of_track", time=max(0, final_tick - cursor)))
        midi.tracks.append(track)

    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path)


def note_occupancy(track: dict[str, Any]) -> dict[str, float | int | str]:
    intervals: list[tuple[float, float]] = []
    for item in track.get("notes", []):
        if float(item.get("v", 0.0)) <= 0:
            continue
        start = float(item["b"])
        end = start + float(item["d"])
        if end > start:
            intervals.append((start, end))
    if not intervals:
        return {"track": str(track.get("name", "track")), "notes": 0, "occupancy_pct": 0.0, "avg_note_beats": 0.0}
    merged: list[list[float]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    union = sum(end - start for start, end in merged)
    dur_sum = sum(end - start for start, end in intervals)
    return {
        "track": str(track.get("name", "track")),
        "notes": len(intervals),
        "occupancy_pct": round(100.0 * union / max(TOTAL_BEATS, 1e-9), 2),
        "avg_note_beats": round(dur_sum / len(intervals), 3),
    }


def band_energy(audio: np.ndarray) -> dict[str, float]:
    mono = audio.mean(axis=1) if audio.ndim == 2 else audio
    total = float(np.mean(mono.astype(np.float64) ** 2))
    bands = {
        "sub_20_120_pct": (20.0, 120.0),
        "low_120_500_pct": (120.0, 500.0),
        "mid_500_2000_pct": (500.0, 2000.0),
        "high_2000_8000_pct": (2000.0, 8000.0),
        "air_8000_16000_pct": (8000.0, 16000.0),
    }
    result: dict[str, float] = {}
    for label, (lo, hi) in bands.items():
        sos = signal.butter(4, [lo / (SAMPLE_RATE / 2.0), hi / (SAMPLE_RATE / 2.0)], btype="bandpass", output="sos")
        filtered = signal.sosfilt(sos, mono).astype(np.float64)
        power = float(np.mean(filtered**2))
        result[label] = round(100.0 * power / max(total, 1e-20), 2)
    return result


def ostinato_arpeggio_metrics(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    drive_track = groups["bass_drive_core"][0]
    sampled_track = groups["sampled_bass_pluck"][0]
    high_offsets = {round(OSTINATO_OFFSETS[0], 3)}
    low_offsets = {round(OSTINATO_OFFSETS[1], 3), round(OSTINATO_OFFSETS[2], 3)}
    beat_summaries: list[dict[str, Any]] = []
    low_anchor_violations: list[dict[str, Any]] = []
    high_melody_violations: list[dict[str, Any]] = []
    high_intervals: list[int] = []
    valid_low_cells = 0
    valid_high_cells = 0

    total_cells = TOTAL_BARS * int(BEATS_PER_BAR / OSTINATO_CELL_BEATS)
    for cell_idx in range(total_cells):
        cell_start = float(cell_idx) * OSTINATO_CELL_BEATS
        bar = min(TOTAL_BARS - 1, int(cell_start // BEATS_PER_BAR))
        root = root_at_bar(bar)
        root_midi = parse_note(root)
        expected_high = high_melody_pitch_at_beat(cell_start)
        expected_high_midi = parse_note(expected_high)
        end_beat = cell_start + OSTINATO_CELL_BEATS
        drive_notes = [
            item for item in drive_track["notes"]
            if float(item.get("v", 0.0)) > 0 and cell_start <= float(item["b"]) < end_beat
        ]
        sampled_notes = [
            item for item in sampled_track["notes"]
            if float(item.get("v", 0.0)) > 0 and cell_start <= float(item["b"]) < end_beat
        ]
        offsets = [round(float(item["b"]) - cell_start, 3) for item in drive_notes]
        lows_ok = True
        highs_ok = True
        for item, offset in zip(drive_notes, offsets, strict=False):
            pitch_midi = parse_note(str(item["n"]))
            if offset in low_offsets and pitch_midi != root_midi:
                lows_ok = False
                low_anchor_violations.append({
                    "cell": cell_idx,
                    "offset": offset,
                    "note": str(item["n"]),
                    "expected_root": root,
                })
            if offset in high_offsets:
                interval = pitch_midi - root_midi
                high_intervals.append(interval)
                if pitch_midi != expected_high_midi:
                    highs_ok = False
                    high_melody_violations.append({
                        "cell": cell_idx,
                        "offset": offset,
                        "note": str(item["n"]),
                        "expected_high": expected_high,
                    })

        if low_offsets.issubset(set(offsets)) and lows_ok:
            valid_low_cells += 1
        if high_offsets.issubset(set(offsets)) and highs_ok:
            valid_high_cells += 1

        if cell_idx < 16 or cell_idx % 32 == 31:
            beat_summaries.append({
                "cell": cell_idx,
                "bar": bar,
                "root": root,
                "expected_high": expected_high,
                "drive_note_count": len(drive_notes),
                "sampled_high_accents": len(sampled_notes),
                "offsets": offsets,
                "low_anchor_ok": lows_ok,
                "high_intervals": [
                    parse_note(str(item["n"])) - root_midi
                    for item, offset in zip(drive_notes, offsets, strict=False)
                    if offset in high_offsets
                ],
            })

    unique_high_intervals = sorted(set(high_intervals))
    melody_durations = sorted(set(duration for _start, duration, _pitch in SLOW_HIGH_MELODY_A))
    pass_ok = (
        len(low_anchor_violations) == 0
        and len(high_melody_violations) == 0
        and valid_low_cells == total_cells
        and valid_high_cells == total_cells
        and len(unique_high_intervals) >= 4
        and len(melody_durations) >= 3
    )
    return {
        "skeleton": "one fast c-a-a cell per beat; c follows slow melody A, a stays on current root",
        "cells_checked": total_cells,
        "cells_with_all_root_low_anchors": valid_low_cells,
        "cells_with_valid_slow_melody_high": valid_high_cells,
        "unique_high_intervals": unique_high_intervals,
        "slow_high_melody_durations_beats": melody_durations,
        "low_anchor_violations": low_anchor_violations,
        "high_melody_violations": high_melody_violations,
        "sample_cells": beat_summaries,
        "pass": pass_ok,
        "target": "all low offsets equal current root; every high offset equals slow melody A; >=4 unique high intervals; variable A note lengths",
    }


def validation_report(
    master: np.ndarray,
    buses: dict[str, np.ndarray],
    groups: dict[str, list[dict[str, Any]]],
    event_counts: dict[str, int],
) -> dict[str, Any]:
    tracks = [track for group_tracks in groups.values() for track in group_tracks]
    track_names = [str(track.get("name", "track")) for track in tracks]
    peak, rms_db = stats(master)
    bus_stats = {
        name: {"peak": round(stats(audio)[0], 6), "rms_db": round(stats(audio)[1], 2)}
        for name, audio in buses.items()
    }
    top_rms = max((item["rms_db"] for item in bus_stats.values()), default=-100.0)
    relative_bus_balance = {
        name: {"rms_db": item["rms_db"], "relative_to_loudest_db": round(item["rms_db"] - top_rms, 2)}
        for name, item in sorted(bus_stats.items(), key=lambda pair: pair[1]["rms_db"], reverse=True)
    }
    occupancy = sorted([note_occupancy(track) for track in tracks], key=lambda item: float(item["occupancy_pct"]), reverse=True)

    def occ(name: str) -> float:
        for item in occupancy:
            if item["track"] == name:
                return float(item["occupancy_pct"])
        return 0.0

    bass_bus_names = ["bass_sub_floor", "bass_drive_core", "sampled_bass_pluck"]
    drum_bus_names = [
        "sampled_drum_kick", "sampled_drum_snare", "sampled_drum_hat",
        "drum_sub_kick", "drum_noise_snap", "drum_hat_air", "drum_ride_noise",
    ]
    decor_bus_names = ["harmony_pressure_stabs", "harmony_low_pad", "decor_metal_sparks", "scene_fx_impacts"]
    bass_mix = mix_arrays([buses[name] for name in bass_bus_names])
    drum_mix = mix_arrays([buses[name] for name in drum_bus_names])
    decor_mix = mix_arrays([buses[name] for name in decor_bus_names])
    bass_peak, bass_rms = stats(bass_mix)
    drum_peak, drum_rms = stats(drum_mix)
    decor_peak, decor_rms = stats(decor_mix)
    ostinato = ostinato_arpeggio_metrics(groups)

    forbidden_terms = ("lead", "aria", "choir", "chant")
    forbidden_name_ok = not any(any(term in name.lower() for term in forbidden_terms) for name in track_names)
    sample_assets = {
        name: [{"path": str(path.relative_to(PROJECT_ROOT)), "exists": path.exists()} for path in paths]
        for name, paths in SAMPLE_ASSETS.items()
    }
    sample_assets_ok = all(item["exists"] for items in sample_assets.values() for item in items)

    role_contract = {
        "bass_drive_as_motif": {
            "bass_drive_core_occupancy_pct": occ("bass_drive_core"),
            "sampled_bass_pluck_occupancy_pct": occ("sampled_bass_pluck"),
            "target": "core drive >= 40%, sampled high accents >= 8%, slow-melody c-a-a ostinato passes",
            "pass": (
                occ("bass_drive_core") >= 40.0
                and occ("sampled_bass_pluck") >= 8.0
                and bool(ostinato["pass"])
            ),
        },
        "bass_floor_continuity": {
            "occupancy_pct": occ("bass_sub_floor"),
            "target": ">= 90%",
            "pass": occ("bass_sub_floor") >= 90.0,
        },
        "drum_spine": {
            "kick_notes": next(item["notes"] for item in occupancy if item["track"] == "sampled_drum_kick"),
            "snare_notes": next(item["notes"] for item in occupancy if item["track"] == "sampled_drum_snare"),
            "hat_notes": next(item["notes"] for item in occupancy if item["track"] == "sampled_drum_hat"),
            "target": "regular kit spine with section-aware fills",
            "pass": occ("sampled_drum_kick") >= 10.0 and occ("sampled_drum_hat") >= 6.0,
        },
        "decorations_subordinate": {
            "decor_relative_to_bass_db": round(decor_rms - bass_rms, 2),
            "decor_relative_to_drums_db": round(decor_rms - drum_rms, 2),
            "target": "decor at least 7 dB below louder spine bus",
            "pass": decor_rms <= max(bass_rms, drum_rms) - 7.0,
        },
        "no_aria_choir_chant_lead_names": forbidden_name_ok,
        "third_party_sample_assets_available": sample_assets_ok,
        "ostinato_arpeggio": ostinato,
    }

    checks = [
        not bool(np.isnan(master).any()),
        peak <= 0.950001,
        185.0 <= master.shape[0] / SAMPLE_RATE <= 198.0,
        forbidden_name_ok,
        sample_assets_ok,
        role_contract["bass_drive_as_motif"]["pass"],
        role_contract["bass_floor_continuity"]["pass"],
        role_contract["drum_spine"]["pass"],
        role_contract["decorations_subordinate"]["pass"],
        bool(ostinato["pass"]),
    ]

    return {
        "sample_rate": SAMPLE_RATE,
        "bpm": BPM,
        "bars": TOTAL_BARS,
        "expected_duration_sec": round(TOTAL_BEATS * BEAT_SEC, 3),
        "master_shape": list(master.shape),
        "master_duration_sec": round(master.shape[0] / SAMPLE_RATE, 3),
        "master_has_nan": bool(np.isnan(master).any()),
        "master_peak": round(peak, 6),
        "master_rms_db": round(rms_db, 2),
        "band_energy_pct": band_energy(master),
        "sections": SECTIONS,
        "bus_stats": bus_stats,
        "relative_bus_balance": relative_bus_balance,
        "track_occupancy": occupancy,
        "top_15_occupancy": occupancy[:15],
        "top_15_relative_rms": [
            {"name": name, "rms_db": item["rms_db"], "relative_db": item["relative_to_loudest_db"]}
            for name, item in list(relative_bus_balance.items())[:15]
        ],
        "spine_stats": {
            "bass_combined_peak": round(bass_peak, 6),
            "bass_combined_rms_db": round(bass_rms, 2),
            "drum_combined_peak": round(drum_peak, 6),
            "drum_combined_rms_db": round(drum_rms, 2),
            "decor_combined_peak": round(decor_peak, 6),
            "decor_combined_rms_db": round(decor_rms, 2),
        },
        "role_contract": role_contract,
        "ornament_event_counts": event_counts,
        "sample_assets": sample_assets,
        "track_count": len(track_names),
        "track_names": track_names,
        "pass": all(checks),
        "checks_detail": {
            "no_nan": not bool(np.isnan(master).any()),
            "peak_ok": peak <= 0.950001,
            "duration_ok": 185.0 <= master.shape[0] / SAMPLE_RATE <= 198.0,
            "forbidden_name_ok": forbidden_name_ok,
            "sample_assets_ok": sample_assets_ok,
            "bass_drive_as_motif_ok": role_contract["bass_drive_as_motif"]["pass"],
            "bass_floor_continuity_ok": role_contract["bass_floor_continuity"]["pass"],
            "drum_spine_ok": role_contract["drum_spine"]["pass"],
            "decorations_subordinate_ok": role_contract["decorations_subordinate"]["pass"],
            "ostinato_arpeggio_ok": bool(ostinato["pass"]),
        },
    }


def write_score(groups: dict[str, list[dict[str, Any]]], master_gain: float) -> None:
    tracks = [track for group_tracks in groups.values() for track in group_tracks]
    score = {
        "title": "Thermocline bass/drum spine v3",
        "bpm": BPM,
        "bars": TOTAL_BARS,
        "duration_sec": round(TOTAL_BEATS * BEAT_SEC, 3),
        "master_gain": round(master_gain, 6),
        "sections": SECTIONS,
        "root_blocks_8bar": ROOT_BLOCKS,
        "policy": {
            "no_aria": True,
            "no_choir": True,
            "no_chant": True,
            "no_lead_role": True,
            "foreground": "bass_drive_core + sampled_bass_pluck + sampled drum kit",
            "motif_shape": "slow high-note melody A expanded into one fast c-a-a cell per beat; low notes stay on root",
            "slow_high_melody_A": [
                {"start_beat": start, "duration_beats": duration, "pitch_ref": pitch_ref}
                for start, duration, pitch_ref in SLOW_HIGH_MELODY_A
            ],
        },
        "sample_assets": {
            name: [str(path.relative_to(PROJECT_ROOT)) for path in paths]
            for name, paths in SAMPLE_ASSETS.items()
        },
        "tracks": tracks,
    }
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    (SOURCE_DIR / "结构_score.json").write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_readme(validation: dict[str, Any]) -> None:
    text = f"""# thermocline_bass_drum_spine_v3

本轮按新的创作判断重做：删掉咏叹调/choir/chant，不再让短 cue 或假人声当主题。

## 核心方向

- `bass_drive_core` 是 motif 主体：先写一条慢高音线 A，再把 A 的每个慢音 `c` 展开成快速 `c-a-a` 循环。
- `a` 永远是当前 root 低音；只允许 `c` 随慢旋律 A 连续变化。
- 每 1 拍一个 `c-a-a` 单元，近似一种 bass arpeggio / ostinato；不再使用 v2 那种每小节两组三音，也不再插过门低音。
- 辅助和声 stabs / pads 会读取同一条慢高音线 A，而不是另写一条 lead。
- `sampled_bass_pluck` 使用本地 sfizz/MeatBassPizz 样本做拨弦攻击层，叠在 epsilon-bit 合成 bass 上。
- `sampled_drum_kick` / `sampled_drum_snare` / `sampled_drum_hat` 使用本地 sfizz 测试样本做更真实的鼓攻击层。
- 和声、金属点、场景冲击只做装饰和后期空间，不承担 lead 或 aria 功能。
- GPL observe 目录里的整段 bass/drum loop 没有用于本次成品；本轮只使用 `research/external_sources/permissive/` 下的短样本资产。

## 听音顺序

1. `01_thermocline_bass_drum_spine_master.mp3`
2. `02_bass_drums_spine_only.mp3`
3. `03_sampled_bass_drum_kit_only.mp3`
4. `04_no_decorations_mix.mp3`
5. `05_decorations_fx_only.mp3`
6. `stem_mp3/`

## 技术信息

- BPM: {BPM}
- Bars: {TOTAL_BARS}
- Duration: {validation['master_duration_sec']}s
- Master peak: {validation['master_peak']}
- Master RMS: {validation['master_rms_db']} dB
- Band energy: {validation['band_energy_pct']}
- Validation pass: {validation['pass']}
- Spine stats: {json.dumps(validation.get('spine_stats', {}), ensure_ascii=False)}
- Role contract: {json.dumps(validation.get('role_contract', {}), ensure_ascii=False, indent=2)}
"""
    (OUT_DIR / "说明.md").write_text(text, encoding="utf-8")


def main() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STEM_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    renderer = Renderer()
    sample_bank = load_sample_bank()

    bass = build_bass_groups()
    drums = build_drum_groups()
    support, event_counts = build_support_groups()
    groups = {**bass, **drums, **support}

    buses: dict[str, np.ndarray] = {}
    buses["bass_sub_floor"] = render_synth_bus(renderer, bass["bass_sub_floor"], volume=0.42) * 1.18
    buses["bass_drive_core"] = render_synth_bus(renderer, bass["bass_drive_core"], volume=0.58) * 1.95
    buses["sampled_bass_pluck"] = render_sampled_bass(bass["sampled_bass_pluck"][0], sample_bank, gain=0.62) * 1.25

    buses["sampled_drum_kick"] = render_sampled_drums(drums["sampled_drum_kick"][0], sample_bank, "kick", gain=0.62) * 1.18
    buses["sampled_drum_snare"] = render_sampled_drums(drums["sampled_drum_snare"][0], sample_bank, "snare", gain=0.70) * 3.45
    buses["sampled_drum_hat"] = render_sampled_drums(drums["sampled_drum_hat"][0], sample_bank, "closed_hat", gain=0.36) * 1.75
    buses["drum_sub_kick"] = render_synth_bus(renderer, drums["drum_sub_kick"], volume=0.48) * 0.92
    buses["drum_noise_snap"] = render_synth_bus(renderer, drums["drum_noise_snap"], volume=0.42) * 4.00
    buses["drum_hat_air"] = render_synth_bus(renderer, drums["drum_hat_air"], volume=0.40) * 4.00
    buses["drum_ride_noise"] = render_synth_bus(renderer, drums["drum_ride_noise"], volume=0.30) * 2.40

    buses["harmony_pressure_stabs"] = render_synth_bus(renderer, support["harmony_pressure_stabs"], volume=0.28) * 0.95
    buses["harmony_low_pad"] = render_synth_bus(renderer, support["harmony_low_pad"], volume=0.24) * 0.75
    buses["decor_metal_sparks"] = render_synth_bus(renderer, support["decor_metal_sparks"], volume=0.18) * 0.38
    buses["scene_fx_impacts"] = render_synth_bus(renderer, support["scene_fx_impacts"], volume=0.28) * 0.58

    kick_trigger = mix_arrays([buses["sampled_drum_kick"], buses["drum_sub_kick"]])

    buses["bass_sub_floor"] = sidechain_duck(butter(buses["bass_sub_floor"], "lowpass", 180.0), kick_trigger, 0.05)
    buses["bass_drive_core"] = soft_clip(butter(buses["bass_drive_core"], "bandpass", (55.0, 1850.0)), 0.95)
    buses["sampled_bass_pluck"] = short_room(soft_clip(butter(buses["sampled_bass_pluck"], "bandpass", (60.0, 2600.0)), 0.85), 0.08)

    buses["sampled_drum_kick"] = soft_clip(butter(buses["sampled_drum_kick"], "bandpass", (42.0, 2100.0)), 1.10)
    buses["sampled_drum_snare"] = short_room(butter(buses["sampled_drum_snare"], "bandpass", (160.0, 6200.0)), 0.12)
    buses["sampled_drum_hat"] = butter(buses["sampled_drum_hat"], "highpass", 4200.0)
    buses["drum_sub_kick"] = butter(buses["drum_sub_kick"], "bandpass", (34.0, 150.0))
    buses["drum_noise_snap"] = short_room(butter(buses["drum_noise_snap"], "highpass", 900.0), 0.10)
    buses["drum_hat_air"] = butter(short_room(buses["drum_hat_air"], 0.08), "highpass", 4500.0)
    buses["drum_ride_noise"] = butter(buses["drum_ride_noise"], "highpass", 3200.0)

    buses["harmony_pressure_stabs"] = sidechain_duck(
        add_delay(butter(buses["harmony_pressure_stabs"], "bandpass", (260.0, 4300.0)), 0.50, 0.06, 0.10),
        kick_trigger,
        0.08,
    )
    buses["harmony_low_pad"] = sidechain_duck(butter(buses["harmony_low_pad"], "bandpass", (180.0, 2800.0)), kick_trigger, 0.08)
    buses["decor_metal_sparks"] = add_delay(butter(buses["decor_metal_sparks"], "bandpass", (1300.0, 7600.0)), 0.1875, 0.07, 0.10)
    buses["scene_fx_impacts"] = butter(short_room(buses["scene_fx_impacts"], 0.16), "bandpass", (45.0, 1600.0))

    spine_names = [
        "bass_sub_floor", "bass_drive_core", "sampled_bass_pluck",
        "sampled_drum_kick", "sampled_drum_snare", "sampled_drum_hat", "drum_sub_kick", "drum_noise_snap",
        "drum_hat_air", "drum_ride_noise",
    ]
    decor_names = ["harmony_pressure_stabs", "harmony_low_pad", "decor_metal_sparks", "scene_fx_impacts"]

    mix = mix_arrays(list(buses.values()))
    mix = butter(mix, "highpass", 28.0)
    mix = soft_clip(mix, 0.78)
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    master_gain = 0.94 / peak if peak > 1e-8 else 1.0
    master = (mix * master_gain).astype(np.float32)

    bass_drums_spine = (mix_arrays([buses[name] for name in spine_names]) * master_gain).astype(np.float32)
    sampled_engine = (mix_arrays([
        buses["sampled_bass_pluck"], buses["sampled_drum_kick"],
        buses["sampled_drum_snare"], buses["sampled_drum_hat"],
    ]) * master_gain).astype(np.float32)
    no_decorations = (mix_arrays([buses[name] for name in spine_names]) * master_gain).astype(np.float32)
    decorations_only = (mix_arrays([buses[name] for name in decor_names]) * master_gain).astype(np.float32)

    write_wav_mp3(renderer, master, OUT_DIR / "01_thermocline_bass_drum_spine_master")
    write_wav_mp3(renderer, bass_drums_spine, OUT_DIR / "02_bass_drums_spine_only")
    write_wav_mp3(renderer, sampled_engine, OUT_DIR / "03_sampled_bass_drum_kit_only")
    write_wav_mp3(renderer, no_decorations, OUT_DIR / "04_no_decorations_mix")
    write_wav_mp3(renderer, decorations_only, OUT_DIR / "05_decorations_fx_only")

    for name, audio in buses.items():
        write_mp3(renderer, (audio * master_gain).astype(np.float32), STEM_DIR / f"{name}.mp3")

    write_midi(OUT_DIR / "01_thermocline_bass_drum_spine_full.mid", groups)
    write_midi(OUT_DIR / "02_bass_drums_spine_only.mid", groups, include_groups=set(spine_names))
    write_midi(OUT_DIR / "03_sampled_bass_drum_kit_only.mid", groups,
               include_groups={"sampled_bass_pluck", "sampled_drum_kick", "sampled_drum_snare", "sampled_drum_hat"})
    write_midi(OUT_DIR / "04_no_decorations_mix.mid", groups, include_groups=set(spine_names))
    write_midi(OUT_DIR / "05_decorations_fx_only.mid", groups, include_groups=set(decor_names))

    write_score(groups, master_gain)
    shutil.copy2(Path(__file__), SOURCE_DIR / Path(__file__).name)

    validation = validation_report(master, buses, groups, event_counts)
    (OUT_DIR / "基础验证.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with (OUT_DIR / "分组stem电平.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["stem", "peak_pre_master_gain", "rms_db_pre_master_gain"])
        writer.writeheader()
        for name, audio in buses.items():
            peak_value, rms_value = stats(audio)
            writer.writerow({
                "stem": name,
                "peak_pre_master_gain": round(peak_value, 6),
                "rms_db_pre_master_gain": round(rms_value, 2),
            })

    write_readme(validation)

    print(OUT_DIR)
    print(f"duration={validation['master_duration_sec']}s")
    print(f"peak={validation['master_peak']}")
    print(f"rms_db={validation['master_rms_db']}")
    print(f"band_energy={validation['band_energy_pct']}")
    print(f"pass={validation['pass']}")
    print(f"checks={json.dumps(validation.get('checks_detail', {}), indent=2)}")
    print(f"spine_stats={json.dumps(validation.get('spine_stats', {}), indent=2)}")
    print(f"top_8_rms={json.dumps(validation.get('top_15_relative_rms', [])[:8], indent=2)}")
    print(OUT_DIR / "01_thermocline_bass_drum_spine_master.mp3")


if __name__ == "__main__":
    main()
