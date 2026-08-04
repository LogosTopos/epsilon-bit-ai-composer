#!/usr/bin/env python3
"""Direct Chat B draft for Thermocline battle BGM.

This pass intentionally bypasses the failed melody-only branch.  It starts from
bass + drums, delays the lead entry, and keeps lead level below the support
buses so the arrangement can be extended later with more ornaments.
"""

from __future__ import annotations

import csv
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import mido
import numpy as np
import scipy.signal as signal
import soundfile as sf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ebit.audio.constants import SAMPLE_RATE
from ebit.renderer import Renderer, parse_note

BPM = 192.0
BEATS_PER_BAR = 4.0
TOTAL_BARS = 64
TAIL_BEATS = 8.0
TOTAL_BEATS = TOTAL_BARS * BEATS_PER_BAR + TAIL_BEATS
BEAT_SEC = 60.0 / BPM
TOTAL_SAMPLES = int(round(TOTAL_BEATS * BEAT_SEC * SAMPLE_RATE))
TICKS_PER_BEAT = 480

OUT_DIR = PROJECT_ROOT / "output" / "analysis" / "温跃层战斗BGM_ChatB_direct_v1"
STEM_DIR = OUT_DIR / "stem_mp3"
SOURCE_DIR = OUT_DIR / "source"

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SECTIONS = [
    {
        "name": "bass_drums_first",
        "start_bar": 0,
        "bars": 8,
        "intent": "low-frequency pulse and tactical drum grid before any lead appears",
    },
    {
        "name": "engine_lock",
        "start_bar": 8,
        "bars": 8,
        "intent": "bass/drums gain speed; harmony stays out; lead still withheld",
    },
    {
        "name": "delayed_lead_entry",
        "start_bar": 16,
        "bars": 8,
        "intent": "lead enters in a restrained middle register and follows support accents",
    },
    {
        "name": "lead_evolution_a",
        "start_bar": 24,
        "bars": 8,
        "intent": "lead develops while first harmony stabs leave gaps",
    },
    {
        "name": "lead_evolution_b",
        "start_bar": 32,
        "bars": 8,
        "intent": "arp grid joins, but bass and drums remain the speed source",
    },
    {
        "name": "stasis_gap",
        "start_bar": 40,
        "bars": 8,
        "intent": "brief thinning for time-stop pressure and loop breathing room",
    },
    {
        "name": "combat_return",
        "start_bar": 48,
        "bars": 16,
        "intent": "fuller return with 2-3 harmony/arp support groups, still leaving ornament slots",
    },
]

PROGRESSIONS = {
    "bass_drums_first": ["C#2", "C#2", "A1", "B1"],
    "engine_lock": ["C#2", "E2", "B1", "F#1"],
    "delayed_lead_entry": ["C#2", "B1", "A1", "E2"],
    "lead_evolution_a": ["F#1", "A1", "C#2", "B1"],
    "lead_evolution_b": ["A1", "B1", "C#2", "E2"],
    "stasis_gap": ["C#2", "G#1", "A1", "F#1"],
    "combat_return": ["A1", "B1", "C#2", "G#1"],
}

PAD_CHORDS = {
    "C#2": ["C#3", "E3", "G#3", "B3"],
    "A1": ["A2", "C#3", "E3", "G#3"],
    "E2": ["E3", "G#3", "B3", "D#4"],
    "B1": ["B2", "D#3", "F#3", "A3"],
    "F#1": ["F#2", "A2", "C#3", "E3"],
    "G#1": ["G#2", "C3", "D#3", "F#3"],
}

MIDI_PROGRAMS = {
    "bass_sub_floor": 38,
    "bass_triangle_drive": 38,
    "bass_fm_edge": 39,
    "lead_core_delayed": 80,
    "lead_warm_body": 81,
    "lead_answer_pin": 82,
    "harmony_gate_stabs": 88,
    "harmony_low_plate": 49,
    "arp_cold_grid": 81,
    "counter_shadow": 80,
    "fx_transition_air": 97,
}

DRUM_MIDI_NOTES = {
    "drum_kick_fm": 36,
    "drum_kick_sub": 35,
    "drum_snare_noise": 38,
    "drum_clap_snap": 39,
    "drum_hat_needle": 42,
    "drum_hat_open": 46,
    "drum_perc_ticks": 75,
    "drum_roll_pressure": 38,
}


def midi_to_note(value: int) -> str:
    octave = value // 12 - 1
    return f"{NOTE_NAMES[value % 12]}{octave}"


def transpose(note_name: str, semitones: int) -> str:
    return midi_to_note(parse_note(note_name) + semitones)


def beat_to_sample(beat: float) -> int:
    return int(round(beat * BEAT_SEC * SAMPLE_RATE))


def empty() -> np.ndarray:
    return np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)


def n(
    note_name: str,
    beat: float,
    duration: float,
    velocity: float,
    fx: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "n": note_name,
        "b": round(beat, 4),
        "d": round(duration, 4),
        "v": round(max(0.0, min(1.0, velocity)), 4),
    }
    if fx:
        item["fx"] = fx
    item.update(extra)
    return item


def tail_note() -> dict[str, Any]:
    return n("C0", TOTAL_BEATS - 0.125, 0.125, 0.0)


def track(
    name: str,
    instrument: str,
    notes: list[dict[str, Any]],
    pan: float = 0.0,
    midi_program: int | None = None,
    midi_channel: int = 0,
) -> dict[str, Any]:
    return {
        "name": name,
        "instrument": instrument,
        "pan": pan,
        "midi_program": midi_program if midi_program is not None else MIDI_PROGRAMS.get(name, 80),
        "midi_channel": midi_channel,
        "notes": sorted(notes + [tail_note()], key=lambda item: (float(item["b"]), item["n"])),
    }


def section_at_bar(bar: int) -> str:
    for section in reversed(SECTIONS):
        if bar >= section["start_bar"]:
            return section["name"]
    return SECTIONS[0]["name"]


def section_start(name: str) -> int:
    return next(item["start_bar"] for item in SECTIONS if item["name"] == name)


def root_at_bar(bar: int) -> str:
    section = section_at_bar(bar)
    progression = PROGRESSIONS[section]
    rel = bar - section_start(section)
    return progression[(rel // 2) % len(progression)]


def pad_to_total(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        audio = np.column_stack([audio, audio])
    if len(audio) >= TOTAL_SAMPLES:
        return audio[:TOTAL_SAMPLES].astype(np.float32)
    out = empty()
    out[: len(audio)] = audio
    return out


def mix_arrays(arrays: list[np.ndarray]) -> np.ndarray:
    out = empty()
    for audio in arrays:
        out += pad_to_total(audio)
    return out.astype(np.float32)


def butter(audio: np.ndarray, kind: str, cutoff: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, cutoff / (SAMPLE_RATE / 2.0), btype=kind, output="sos")
    return np.column_stack(
        [signal.sosfilt(sos, audio[:, 0]), signal.sosfilt(sos, audio[:, 1])]
    ).astype(np.float32)


def add_delay(
    audio: np.ndarray,
    delay_beats: float,
    wet: float,
    feedback: float = 0.16,
    cross: bool = True,
) -> np.ndarray:
    delay_samples = max(1, beat_to_sample(delay_beats))
    out = audio.copy()
    first = np.zeros_like(out)
    first[delay_samples:] = audio[:-delay_samples]
    if cross:
        first = first[:, [1, 0]]
    out += first * wet
    second = np.zeros_like(out)
    if delay_samples * 2 < len(out):
        second[delay_samples * 2 :] = audio[: -delay_samples * 2]
    if cross:
        second = second[:, [1, 0]]
    out += second * wet * feedback
    return out.astype(np.float32)


def sidechain_duck(audio: np.ndarray, trigger: np.ndarray, depth: float, release_ms: float = 85.0) -> np.ndarray:
    mono = np.abs(trigger.mean(axis=1)).astype(np.float32)
    alpha = math.exp(-1.0 / max(SAMPLE_RATE * release_ms / 1000.0, 1.0))
    env = signal.lfilter([1.0 - alpha], [1.0, -alpha], mono)
    peak = float(np.max(env)) if env.size else 0.0
    if peak > 1e-8:
        env = env / peak
    return (audio * (1.0 - depth * env[:, None])).astype(np.float32)


def stats(audio: np.ndarray) -> tuple[float, float]:
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(np.square(audio.astype(np.float64))))) if audio.size else 0.0
    return peak, 20.0 * math.log10(max(rms, 1e-10))


def write_wav_mp3(renderer: Renderer, audio: np.ndarray, path_stem: Path, bitrate: str = "224k") -> None:
    path_stem.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path_stem.with_suffix(".wav"), audio, SAMPLE_RATE)
    renderer.save_mp3(audio, str(path_stem.with_suffix(".mp3")), bitrate=bitrate)


def write_mp3(renderer: Renderer, audio: np.ndarray, path_stem: Path, bitrate: str = "224k") -> None:
    path_stem.parent.mkdir(parents=True, exist_ok=True)
    renderer.save_mp3(audio, str(path_stem.with_suffix(".mp3")), bitrate=bitrate)


def render_bus(renderer: Renderer, tracks: list[dict[str, Any]], volume: float) -> np.ndarray:
    rendered = renderer.render_multi_stereo({"bpm": BPM, "tracks": tracks}, volume=volume)
    return mix_arrays(list(rendered.values()))


def add_cell(
    notes: list[dict[str, Any]],
    start: float,
    cell: list[tuple[str, float, float, float]],
    phrase: str,
    transpose_by: int = 0,
    velocity_scale: float = 1.0,
) -> None:
    for pitch, off, duration, velocity in cell:
        final_pitch = transpose(pitch, transpose_by) if transpose_by else pitch
        fx = {"vib": [4.5, 3.8]} if duration >= 0.75 else None
        notes.append(n(final_pitch, start + off, duration, velocity * velocity_scale, fx=fx, phrase=phrase))


# Eight-bar cells.  They avoid the previous v1 lead's constant arpeggiated
# up-sweep; speed comes from support accents and phrase handoff.
ENTRY_CELL = [
    ("G#4", 0.00, 0.50, 0.52),
    ("B4", 0.75, 0.25, 0.44),
    ("C#5", 1.25, 0.75, 0.54),
    ("E5", 2.50, 0.50, 0.48),
    ("D#5", 3.25, 0.50, 0.45),
    ("B4", 4.00, 0.75, 0.50),
    ("C#5", 5.25, 0.50, 0.52),
    ("G#4", 6.00, 0.50, 0.46),
    ("F#4", 6.75, 0.25, 0.42),
    ("G#4", 7.25, 0.75, 0.54),
]

CHASE_CELL = [
    ("C#5", 0.00, 0.50, 0.56),
    ("E5", 0.50, 0.50, 0.52),
    ("B4", 1.25, 0.25, 0.42),
    ("G#4", 1.75, 0.50, 0.48),
    ("F#5", 2.75, 0.50, 0.55),
    ("E5", 3.50, 0.50, 0.50),
    ("C#5", 4.25, 0.50, 0.54),
    ("B4", 5.00, 0.50, 0.46),
    ("D#5", 5.75, 0.25, 0.42),
    ("E5", 6.25, 0.50, 0.52),
    ("G#5", 7.00, 0.75, 0.58),
]

EVOLVE_CELL = [
    ("E5", 0.00, 0.50, 0.55),
    ("G#5", 0.75, 0.25, 0.47),
    ("F#5", 1.25, 0.50, 0.52),
    ("C#5", 2.00, 0.50, 0.50),
    ("B4", 2.75, 0.50, 0.46),
    ("E5", 3.50, 0.50, 0.54),
    ("A5", 4.50, 0.50, 0.58),
    ("G#5", 5.25, 0.25, 0.48),
    ("F#5", 5.75, 0.50, 0.52),
    ("E5", 6.50, 0.50, 0.50),
    ("C#5", 7.25, 0.75, 0.58),
]

RETURN_CELL = [
    ("F#5", 0.00, 0.50, 0.58),
    ("E5", 0.75, 0.50, 0.52),
    ("C#5", 1.50, 0.50, 0.54),
    ("G#4", 2.25, 0.50, 0.48),
    ("B4", 3.00, 0.50, 0.50),
    ("C#5", 3.75, 0.25, 0.48),
    ("E5", 4.25, 0.50, 0.54),
    ("B5", 5.00, 0.50, 0.58),
    ("A5", 5.75, 0.25, 0.48),
    ("G#5", 6.25, 0.50, 0.54),
    ("E5", 7.00, 1.00, 0.58),
]

STASIS_CELL = [
    ("C#5", 0.00, 1.50, 0.46),
    ("G#4", 2.50, 0.50, 0.40),
    ("B4", 4.00, 0.75, 0.42),
    ("C5", 5.50, 0.50, 0.46),
    ("C#5", 6.25, 1.00, 0.50),
]


def build_lead_notes() -> list[dict[str, Any]]:
    core: list[dict[str, Any]] = []
    add_cell(core, 64.0, ENTRY_CELL, "delayed_entry_a", velocity_scale=0.86)
    add_cell(core, 80.0, CHASE_CELL, "delayed_entry_answer", velocity_scale=0.88)
    add_cell(core, 96.0, CHASE_CELL, "evolution_a", transpose_by=0, velocity_scale=0.90)
    add_cell(core, 112.0, EVOLVE_CELL, "evolution_a_turn", velocity_scale=0.92)
    add_cell(core, 128.0, EVOLVE_CELL, "evolution_b_grid_fit", transpose_by=2, velocity_scale=0.92)
    add_cell(core, 144.0, CHASE_CELL, "evolution_b_answer", transpose_by=-2, velocity_scale=0.88)
    add_cell(core, 160.0, STASIS_CELL, "stasis_thin", transpose_by=-12, velocity_scale=0.78)
    add_cell(core, 176.0, ENTRY_CELL, "stasis_reentry", transpose_by=-5, velocity_scale=0.80)
    add_cell(core, 192.0, RETURN_CELL, "combat_return_a", velocity_scale=0.94)
    add_cell(core, 208.0, EVOLVE_CELL, "combat_return_b", transpose_by=0, velocity_scale=0.94)
    add_cell(core, 224.0, RETURN_CELL, "combat_return_answer", transpose_by=-2, velocity_scale=0.92)
    add_cell(core, 240.0, CHASE_CELL, "loop_preparation", transpose_by=-5, velocity_scale=0.88)
    return sorted(core, key=lambda item: (float(item["b"]), item["n"]))


def build_lead_tracks(lead_notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    core: list[dict[str, Any]] = []
    body: list[dict[str, Any]] = []
    pin: list[dict[str, Any]] = []
    for item in lead_notes:
        beat = float(item["b"])
        duration = float(item["d"])
        velocity = float(item["v"])
        phrase = str(item.get("phrase", ""))
        core.append(
            n(
                item["n"],
                beat,
                duration + 0.025,
                velocity,
                fx={"vib": [4.7, 3.2]} if duration >= 0.75 else None,
                phrase=phrase,
            )
        )
        body.append(
            n(
                item["n"],
                beat + 0.018,
                duration + 0.06,
                velocity * 0.26,
                fx={"vib": [4.0, 4.2]} if duration >= 0.5 else None,
                phrase=phrase,
            )
        )
        if beat >= 128.0 and duration <= 0.50 and phrase not in {"stasis_thin"}:
            pin.append(n(transpose(item["n"], 12), beat + 0.012, min(duration, 0.28), velocity * 0.15, phrase=phrase))
    return [
        track("lead_core_delayed", "pulse_25", core, pan=-0.03, midi_program=80),
        track("lead_warm_body", "sine", body, pan=0.04, midi_program=81),
        track("lead_answer_pin", "pulse_12", pin, pan=0.18, midi_program=82),
    ]


def build_lead_only_tracks(lead_notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    plain = [{key: value for key, value in item.items() if key in {"n", "b", "d", "v", "fx"}} for item in lead_notes]
    return [track("lead_only_plain_sine", "sine", plain, pan=0.0, midi_program=80)]


def build_bass_tracks() -> list[dict[str, Any]]:
    sub: list[dict[str, Any]] = []
    drive: list[dict[str, Any]] = []
    edge: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        root = root_at_bar(bar)
        beat = bar * BEATS_PER_BAR
        rel = bar - section_start(section)
        sub_vel = 0.23 if section in {"bass_drums_first", "engine_lock"} else 0.18
        sub.append(n(transpose(root, -12), beat, 3.82, sub_vel))

        if section == "bass_drums_first":
            if bar < 4:
                drive_offsets = [0.0, 2.5]
            else:
                drive_offsets = [0.0, 1.5, 2.5, 3.25]
        elif section == "stasis_gap":
            drive_offsets = [0.0, 3.0] if rel % 4 in {0, 3} else [0.0, 2.5]
        elif section == "engine_lock":
            drive_offsets = [0.0, 1.0, 1.75, 2.5, 3.25]
        else:
            drive_offsets = [0.0, 0.75, 1.5, 2.0, 2.75, 3.25]
        for off in drive_offsets:
            vel = 0.44 if off in {0.0, 2.0} else 0.34
            if section in {"bass_drums_first", "engine_lock"}:
                vel *= 1.08
            drive.append(n(root, beat + off, 0.30, vel))
        if section in {"lead_evolution_b", "combat_return"}:
            for off in [0.25, 1.25, 2.25, 3.50]:
                edge.append(n(transpose(root, 12), beat + off, 0.16, 0.18, fx={"retrigger": 2}))
        if section in {"engine_lock", "lead_evolution_a", "stasis_gap"} and bar % 4 == 3:
            edge.append(n(root, beat + 3.00, 0.70, 0.22, fx={"slide_to": transpose(root, 12)}))
    return [
        track("bass_sub_floor", "sine", sub, pan=0.0, midi_program=38),
        track("bass_triangle_drive", "triangle", drive, pan=0.0, midi_program=38),
        track("bass_fm_edge", "fm_bass", edge, pan=-0.04, midi_program=39),
    ]


def build_drum_groups() -> dict[str, list[dict[str, Any]]]:
    kick: list[dict[str, Any]] = []
    kick_sub: list[dict[str, Any]] = []
    snare: list[dict[str, Any]] = []
    clap: list[dict[str, Any]] = []
    hat: list[dict[str, Any]] = []
    open_hat: list[dict[str, Any]] = []
    ticks: list[dict[str, Any]] = []
    roll: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        beat = bar * BEATS_PER_BAR
        rel = bar - section_start(section)
        if section == "bass_drums_first":
            kick_hits = [0.0] if bar < 4 else [0.0, 2.5]
            snare_hits = [] if bar < 4 else [3.0]
            hat_grid = [1.0, 3.0] if bar < 4 else [i * 0.5 for i in range(8)]
        elif section == "engine_lock":
            kick_hits = [0.0, 1.5, 2.5, 3.25]
            snare_hits = [1.0, 3.0]
            hat_grid = [i * 0.5 for i in range(8)]
        elif section == "stasis_gap":
            kick_hits = [0.0] if rel % 4 in {0, 3} else [0.0, 3.0]
            snare_hits = [3.0] if rel % 4 in {1, 3} else []
            hat_grid = [0.5, 1.5, 2.5, 3.5]
        elif section in {"lead_evolution_b", "combat_return"}:
            kick_hits = [0.0, 1.0, 2.0, 3.0]
            if rel % 4 in {1, 3}:
                kick_hits += [2.5, 3.5]
            snare_hits = [1.0, 3.0]
            hat_grid = [i * 0.25 for i in range(16)]
        else:
            kick_hits = [0.0, 1.5, 2.0, 3.25]
            snare_hits = [1.0, 3.0]
            hat_grid = [i * 0.5 for i in range(8)]

        for off in kick_hits:
            kick.append(n("C2", beat + off, 0.14, 0.90 if off in {0.0, 2.0} else 0.68, fm_index=7.4, fm_ratio=3.0))
            kick_sub.append(n("C1", beat + off, 0.20, 0.34))
        for off in snare_hits:
            snare.append(n("D3", beat + off, 0.15, 0.64))
            clap.append(n("D4", beat + off + 0.012, 0.075, 0.22, fx={"retrigger": 2}))
        if bar % 8 == 7 and section not in {"bass_drums_first", "stasis_gap"}:
            roll.append(n("D3", beat + 3.0, 0.84, 0.38, fx={"retrigger": 8, "tremolo": [11.0, 0.18]}))
        for off in hat_grid:
            accent = 0.24 if abs(off % 1.0) < 1e-6 else 0.15
            if section in {"lead_evolution_b", "combat_return"}:
                accent *= 1.15
            hat.append(n("F#5", beat + off, 0.045, accent))
            if section == "combat_return" and int(off * 4) % 4 == 2:
                open_hat.append(n("F#5", beat + off, 0.08, accent * 0.48))
        if section in {"engine_lock", "lead_evolution_a", "lead_evolution_b", "combat_return"}:
            for off in [0.75, 2.75]:
                ticks.append(n("C6", beat + off, 0.04, 0.12))
            if rel % 4 == 2:
                ticks.append(n("G5", beat + 3.5, 0.07, 0.18, fx={"retrigger": 3}))
    return {
        "kick": [
            track("drum_kick_fm", "fm", kick, pan=0.0, midi_channel=9),
            track("drum_kick_sub", "sine", kick_sub, pan=0.0, midi_channel=9),
        ],
        "snare": [
            track("drum_snare_noise", "noise_short", snare, pan=0.02, midi_channel=9),
            track("drum_clap_snap", "noise_periodic", clap, pan=0.06, midi_channel=9),
            track("drum_roll_pressure", "noise_short", roll, pan=-0.04, midi_channel=9),
        ],
        "hat": [
            track("drum_hat_needle", "noise_short", hat, pan=0.24, midi_channel=9),
            track("drum_hat_open", "noise_long", open_hat, pan=-0.22, midi_channel=9),
        ],
        "perc": [track("drum_perc_ticks", "pulse_12", ticks, pan=-0.16, midi_channel=9)],
    }


def build_harmony_groups() -> dict[str, list[dict[str, Any]]]:
    gate: list[dict[str, Any]] = []
    low_plate: list[dict[str, Any]] = []
    arp: list[dict[str, Any]] = []
    counter: list[dict[str, Any]] = []
    for bar in range(0, TOTAL_BARS, 2):
        section = section_at_bar(bar)
        if section in {"bass_drums_first", "engine_lock", "delayed_lead_entry"}:
            continue
        root = root_at_bar(bar)
        chord = PAD_CHORDS[root]
        beat = bar * BEATS_PER_BAR
        if section in {"lead_evolution_a", "lead_evolution_b", "combat_return"}:
            for idx, pitch in enumerate(chord):
                gate.append(
                    n(
                        pitch,
                        beat + (0.0 if idx < 2 else 2.0),
                        1.55,
                        0.13 if idx < 2 else 0.10,
                        fx={"vib": [3.4 + idx * 0.15, 4.0], "tremolo": [2.2, 0.08]},
                        pan=-0.26 + idx * 0.17,
                    )
                )
        if section in {"stasis_gap", "combat_return"}:
            for idx, pitch in enumerate(chord[:3]):
                low_plate.append(n(pitch, beat, 7.60, 0.085, fx={"vib": [2.8, 6.0]}, pan=-0.18 + idx * 0.18))
        if section in {"lead_evolution_b", "combat_return"}:
            pattern = [transpose(chord[0], 12), transpose(chord[2], 12), transpose(chord[1], 12), transpose(chord[3], 12)]
            for idx in range(24):
                if idx % 8 in {6, 7}:
                    continue
                arp.append(n(pattern[idx % len(pattern)], beat + idx * 0.25, 0.105, 0.22 if idx % 4 else 0.29))

    for start in [104.0, 136.0, 200.0, 232.0]:
        for off, pitch in [(1.50, "E5"), (2.25, "G#5"), (4.75, "F#5"), (5.50, "E5")]:
            counter.append(n(pitch, start + off, 0.32, 0.25, fx={"vib": [5.0, 3.0]}))
    return {
        "harmony_stabs": [track("harmony_gate_stabs", "fm_string", gate, pan=0.0, midi_program=88)],
        "harmony_plate": [track("harmony_low_plate", "sine", low_plate, pan=0.0, midi_program=49)],
        "arp_grid": [track("arp_cold_grid", "pulse_12", arp, pan=0.20, midi_program=81)],
        "counter_shadow": [track("counter_shadow", "pulse_75", counter, pan=-0.18, midi_program=80)],
    }


def build_fx_tracks() -> list[dict[str, Any]]:
    air: list[dict[str, Any]] = []
    for bar in [8, 16, 24, 32, 40, 48, 64]:
        beat = bar * BEATS_PER_BAR
        if bar < TOTAL_BARS:
            air.append(n("G#6", beat - 0.50, 0.16, 0.16, fx={"slide_to": "C#7", "retrigger": 3}))
            air.append(n("C2", beat, 0.22, 0.18, fm_index=7.5, fm_ratio=4.0))
    for bar in [36, 44, 60]:
        beat = bar * BEATS_PER_BAR
        air.append(n("E6", beat + 3.25, 0.12, 0.12, fx={"slide_to": "B6"}))
    return [track("fx_transition_air", "fm", air, pan=0.22, midi_program=97)]


def master_from_buses(buses: dict[str, np.ndarray]) -> tuple[np.ndarray, float]:
    mix = mix_arrays(list(buses.values()))
    mix = butter(mix, "highpass", 25.0)
    mix = np.tanh(mix * 0.98) / np.tanh(0.98)
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    gain = 0.94 / peak if peak > 1e-8 else 1.0
    return (mix * gain).astype(np.float32), gain


def validation_report(
    master: np.ndarray,
    lead_only: np.ndarray,
    no_lead: np.ndarray,
    fit_gate: np.ndarray,
    bass_drums_only: np.ndarray,
    buses: dict[str, np.ndarray],
    lead_notes: list[dict[str, Any]],
) -> dict[str, Any]:
    bus_stats = {
        name: {
            "peak": round(stats(audio)[0], 6),
            "rms_db": round(stats(audio)[1], 2),
        }
        for name, audio in buses.items()
    }
    first_lead_beat = min(float(item["b"]) for item in lead_notes)
    first_lead_bar = first_lead_beat / BEATS_PER_BAR
    lead_rms = bus_stats["03_主旋律_lead_delayed_soft"]["rms_db"]
    bass_rms = bus_stats["01_低频_bass"]["rms_db"]
    drums_rms = bus_stats["02_鼓组_drums"]["rms_db"]
    harmony_combined_rms = stats(
        mix_arrays(
            [
                buses["04_和声_stabs"],
                buses["05_和声_pad"],
                buses["06_arp_grid"],
                buses["07_counter_shadow"],
            ]
        )
    )[1]
    return {
        "sample_rate": SAMPLE_RATE,
        "expected_duration_sec": round(TOTAL_SAMPLES / SAMPLE_RATE, 3),
        "master_shape": list(master.shape),
        "master_duration_sec": round(len(master) / SAMPLE_RATE, 3),
        "master_has_nan": bool(np.isnan(master).any()),
        "master_peak": round(stats(master)[0], 6),
        "master_rms_db": round(stats(master)[1], 2),
        "lead_only_rms_db": round(stats(lead_only)[1], 2),
        "no_lead_rms_db": round(stats(no_lead)[1], 2),
        "fit_gate_rms_db": round(stats(fit_gate)[1], 2),
        "bass_drums_only_rms_db": round(stats(bass_drums_only)[1], 2),
        "first_lead_beat": round(first_lead_beat, 3),
        "first_lead_bar_zero_based": round(first_lead_bar, 3),
        "lead_delayed_pass": first_lead_bar >= 16.0,
        "support_level_policy": {
            "lead_rms_db": lead_rms,
            "bass_rms_db": bass_rms,
            "drums_rms_db": drums_rms,
            "harmony_arp_counter_combined_rms_db": round(harmony_combined_rms, 2),
            "policy": "lead must not sit far above bass/drums; support buses are intentionally raised from v1",
            "pass": lead_rms <= max(bass_rms, drums_rms) + 1.0,
        },
        "bus_stats": bus_stats,
        "pass": (
            not bool(np.isnan(master).any())
            and 0.20 <= stats(master)[0] <= 0.96
            and stats(master)[1] > -32.0
            and abs((len(master) / SAMPLE_RATE) - (TOTAL_SAMPLES / SAMPLE_RATE)) <= 0.02
            and first_lead_bar >= 16.0
            and lead_rms <= max(bass_rms, drums_rms) + 1.0
        ),
    }


def build_score(lead_notes: list[dict[str, Any]], all_tracks: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    track_summaries = []
    for group, tracks in all_tracks.items():
        for item in tracks:
            real_notes = [note for note in item["notes"] if float(note.get("v", 0.0)) > 0.0]
            track_summaries.append(
                {
                    "group": group,
                    "name": item["name"],
                    "instrument": item["instrument"],
                    "midi_program": item.get("midi_program"),
                    "midi_channel": item.get("midi_channel", 0),
                    "note_count": len(real_notes),
                }
            )
    return {
        "title": "温跃层战斗BGM_ChatB_direct_v1",
        "generation_scope": "Chat B direct draft after abandoning melody-only Stage A",
        "ai_generated_notice": "This file and the generated music are AI generated; user listening judgment overrides this report.",
        "bpm": BPM,
        "bars": TOTAL_BARS,
        "tail_beats": TAIL_BEATS,
        "duration_sec": round(TOTAL_SAMPLES / SAMPLE_RATE, 3),
        "tonal_center": "C# minor / modal combat color",
        "sections": SECTIONS,
        "constraints_from_user": [
            "do not continue the failed melody-only path",
            "lead timbre and level must not dominate",
            "bass, drums, harmony and arp are raised relative to the previous v1 mix",
            "lead must not enter too early; bass and drums speak first",
            "add 2-3 harmony/arp groups while lead evolves",
            "preserve source files and leave space for later bass, drum and ornament additions",
        ],
        "reference_boundary": [
            "Use the successful high-speed reference MIDI render chain as engineering reference.",
            "Do not use the failed high-speed melody extraction documents as melodic source.",
            "Do not copy complete reference melodies.",
        ],
        "lead_first_beat": min(float(item["b"]) for item in lead_notes),
        "lead_phrase_counts": Counter(str(item.get("phrase", "")) for item in lead_notes),
        "lead_duration_vocab": sorted({round(float(item["d"]), 4) for item in lead_notes}),
        "progressions": PROGRESSIONS,
        "track_summaries": track_summaries,
        "tracks": all_tracks,
    }


def write_midi(path: Path, tracks_by_group: dict[str, list[dict[str, Any]]], include_groups: set[str] | None = None) -> None:
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("track_name", name="thermocline_chat_b_direct_meta", time=0))
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    midi.tracks.append(meta)

    for group_name, tracks in tracks_by_group.items():
        if include_groups is not None and group_name not in include_groups:
            continue
        for source in tracks:
            name = source.get("name", source.get("instrument", "track"))
            midi_track = mido.MidiTrack()
            channel = int(source.get("midi_channel", 0))
            midi_track.append(mido.MetaMessage("track_name", name=name, time=0))
            if channel != 9:
                program = int(source.get("midi_program", 80))
                midi_track.append(mido.Message("program_change", program=max(0, min(127, program)), channel=channel, time=0))
            events: list[tuple[int, int, mido.Message]] = []
            for item in source.get("notes", []):
                if float(item.get("v", 0.0)) <= 0.0:
                    continue
                start = int(round(float(item["b"]) * TICKS_PER_BEAT))
                end = int(round((float(item["b"]) + float(item["d"])) * TICKS_PER_BEAT))
                if end <= start:
                    continue
                if channel == 9:
                    pitch = DRUM_MIDI_NOTES.get(name, 42)
                else:
                    pitch = parse_note(str(item["n"]))
                velocity = max(1, min(127, int(round(float(item["v"]) * 127))))
                events.append((start, 1, mido.Message("note_on", note=pitch, velocity=velocity, channel=channel, time=0)))
                events.append((end, 0, mido.Message("note_off", note=pitch, velocity=0, channel=channel, time=0)))
            events.sort(key=lambda event: (event[0], event[1]))
            cursor = 0
            for tick, _order, msg in events:
                msg.time = max(0, tick - cursor)
                midi_track.append(msg)
                cursor = tick
            final_tick = int(round(TOTAL_BEATS * TICKS_PER_BEAT))
            midi_track.append(mido.MetaMessage("end_of_track", time=max(0, final_tick - cursor)))
            midi.tracks.append(midi_track)
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path)


def write_docs(score: dict[str, Any], validation: dict[str, Any], master_gain: float) -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    (SOURCE_DIR / "结构_score.json").write_text(
        json.dumps(score, ensure_ascii=False, indent=2, default=dict) + "\n",
        encoding="utf-8",
    )
    (OUT_DIR / "基础验证.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with (OUT_DIR / "分组stem电平.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["stem", "peak_pre_master_gain", "rms_db_pre_master_gain"])
        writer.writeheader()
        for name, stat in validation["bus_stats"].items():
            writer.writerow(
                {
                    "stem": name,
                    "peak_pre_master_gain": stat["peak"],
                    "rms_db_pre_master_gain": stat["rms_db"],
                }
            )

    section_lines = [
        f"- {item['name']}: bars {item['start_bar']}-{item['start_bar'] + item['bars']}, {item['intent']}"
        for item in SECTIONS
    ]
    readme = f"""# 温跃层战斗BGM_ChatB_direct_v1

本目录由 Chat B / Codex 生成，**不是人工生成**。听感审核优先于本说明。

## 本轮修正

- 放弃 melody-only Stage A，不沿用 `温跃层战斗BGM_v2_melody_only` 的失败路线。
- 低频 bass 和 drums 先入场，lead 到第 16 小节后才进入。
- lead 用较软、较低响度的 pulse/sine 叠层，不再压过全曲。
- bass、drums、harmony、arp 的相对响度比 `温跃层战斗BGM_v1_重新构思` 明显提高。
- harmony / arp 分成三组：`harmony_stabs`、`harmony_plate`、`arp_grid`，另有稀疏 `counter_shadow`。
- 保留脚本、结构 JSON、MIDI、分组 stems，后续可以继续加 bass fill、drum fill 和装饰音。

## 听音顺序

1. `01_温跃层_ChatB_direct_v1_master.mp3`
2. `02_fit_gate_bass_drums_lead.mp3`
3. `03_bass_drums_only.mp3`
4. `04_no_lead_arrangement.mp3`
5. `05_lead_only_plain_reference.mp3`
6. `stem_mp3/`

## 结构

{chr(10).join(section_lines)}

## 技术信息

- BPM: {BPM}
- Bars: {TOTAL_BARS}
- Duration: {TOTAL_SAMPLES / SAMPLE_RATE:.2f}s
- First lead bar: {validation['first_lead_bar_zero_based']}
- Master gain: {master_gain:.6f}
- Validation pass: {validation['pass']}
- Master peak: {validation['master_peak']}
- Master RMS: {validation['master_rms_db']} dB
- Lead/support level pass: {validation['support_level_policy']['pass']}
"""
    (OUT_DIR / "说明.md").write_text(readme, encoding="utf-8")

    render_chain = """# MIDI to MP3 Render Chain Check

本项目已有系统化 MIDI/结构谱到 MP3 的方法，不需要恢复旧 chat 才能渲染：

- `src/ebit/renderer.py` 提供 `Renderer.render_multi_stereo()` / `Renderer.render_stereo()`，把结构化 note timeline 渲染为 WAV buffer。
- `Renderer.save_mp3()` 通过 ffmpeg 把临时 WAV 转为 MP3。
- `examples/highspeed_reference_midi_v1/` 保留了参考 MIDI 与对应 MP3 审阅包。
- 该参考脚本还包含 GM program 到本项目波形的大致映射：bass -> triangle，lead/brass/fx -> sawtooth，guitar/organ -> pulse_25，bell/pipe -> fm_bell，pad/strings -> wavetable，drums -> kick/snare/hat/cymbal 分类。

本轮原创曲不是直接让系统播放器播放 MIDI，而是：

1. 用 Python note timeline 作为权威源。
2. 用项目 renderer 渲染 WAV/MP3，保持音色可控。
3. 同时导出标准 MIDI，方便后续外部审谱或重配器。

注意：外部 MIDI 播放器会按自己的 GM 音源播放，听感不会等同于本目录 MP3。
"""
    (OUT_DIR / "MIDI转MP3链路说明.md").write_text(render_chain, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STEM_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    renderer = Renderer()

    lead_notes = build_lead_notes()
    lead_tracks = build_lead_tracks(lead_notes)
    bass_tracks = build_bass_tracks()
    drum_groups = build_drum_groups()
    drum_tracks = drum_groups["kick"] + drum_groups["snare"] + drum_groups["hat"] + drum_groups["perc"]
    harmony_groups = build_harmony_groups()
    fx_tracks = build_fx_tracks()

    all_tracks = {
        "bass": bass_tracks,
        "drums": drum_tracks,
        "lead": lead_tracks,
        "harmony_stabs": harmony_groups["harmony_stabs"],
        "harmony_plate": harmony_groups["harmony_plate"],
        "arp_grid": harmony_groups["arp_grid"],
        "counter_shadow": harmony_groups["counter_shadow"],
        "fx": fx_tracks,
    }

    kick_trigger = render_bus(renderer, drum_groups["kick"], volume=0.70)
    buses: dict[str, np.ndarray] = {
        "01_低频_bass": render_bus(renderer, bass_tracks, volume=0.72) * 1.16,
        "02_鼓组_drums": render_bus(renderer, drum_tracks, volume=0.72) * 1.18,
        "03_主旋律_lead_delayed_soft": render_bus(renderer, lead_tracks, volume=0.48) * 0.88,
        "04_和声_stabs": render_bus(renderer, harmony_groups["harmony_stabs"], volume=0.62) * 1.18,
        "05_和声_pad": render_bus(renderer, harmony_groups["harmony_plate"], volume=0.58) * 1.04,
        "06_arp_grid": render_bus(renderer, harmony_groups["arp_grid"], volume=0.66) * 1.18,
        "07_counter_shadow": render_bus(renderer, harmony_groups["counter_shadow"], volume=0.54) * 0.96,
        "08_预留空间_fx": render_bus(renderer, fx_tracks, volume=0.40) * 0.44,
    }

    buses["01_低频_bass"] = butter(sidechain_duck(buses["01_低频_bass"], kick_trigger, 0.08), "lowpass", 5400.0)
    buses["03_主旋律_lead_delayed_soft"] = add_delay(butter(buses["03_主旋律_lead_delayed_soft"], "lowpass", 6400.0), 0.22, 0.03)
    buses["04_和声_stabs"] = butter(sidechain_duck(buses["04_和声_stabs"], kick_trigger, 0.12), "lowpass", 6500.0)
    buses["05_和声_pad"] = butter(sidechain_duck(buses["05_和声_pad"], kick_trigger, 0.14), "lowpass", 4800.0)
    buses["06_arp_grid"] = butter(sidechain_duck(buses["06_arp_grid"], kick_trigger, 0.10), "highpass", 120.0)
    buses["08_预留空间_fx"] = add_delay(butter(buses["08_预留空间_fx"], "highpass", 130.0), 0.25, 0.05)

    master, master_gain = master_from_buses(buses)
    fit_gate, _ = master_from_buses(
        {
            "01_低频_bass": buses["01_低频_bass"],
            "02_鼓组_drums": buses["02_鼓组_drums"],
            "03_主旋律_lead_delayed_soft": buses["03_主旋律_lead_delayed_soft"],
        }
    )
    bass_drums_only, _ = master_from_buses({"01_低频_bass": buses["01_低频_bass"], "02_鼓组_drums": buses["02_鼓组_drums"]})
    no_lead, _ = master_from_buses({key: value for key, value in buses.items() if key != "03_主旋律_lead_delayed_soft"})

    lead_only_raw = render_bus(renderer, build_lead_only_tracks(lead_notes), volume=0.60)
    lead_only = np.nan_to_num(lead_only_raw)
    lead_peak = float(np.max(np.abs(lead_only))) if lead_only.size else 0.0
    if lead_peak > 1e-8:
        lead_only = (lead_only / lead_peak * 0.82).astype(np.float32)

    write_wav_mp3(renderer, master, OUT_DIR / "01_温跃层_ChatB_direct_v1_master")
    write_wav_mp3(renderer, fit_gate, OUT_DIR / "02_fit_gate_bass_drums_lead")
    write_wav_mp3(renderer, bass_drums_only, OUT_DIR / "03_bass_drums_only")
    write_wav_mp3(renderer, no_lead, OUT_DIR / "04_no_lead_arrangement")
    write_wav_mp3(renderer, lead_only, OUT_DIR / "05_lead_only_plain_reference")

    for name, audio in buses.items():
        write_mp3(renderer, audio * master_gain, STEM_DIR / name)

    write_midi(OUT_DIR / "01_温跃层_ChatB_direct_v1_full.mid", all_tracks)
    write_midi(OUT_DIR / "02_fit_gate_bass_drums_lead.mid", all_tracks, include_groups={"bass", "drums", "lead"})
    write_midi(OUT_DIR / "03_bass_drums_only.mid", all_tracks, include_groups={"bass", "drums"})

    score = build_score(lead_notes, all_tracks)
    validation = validation_report(master, lead_only, no_lead, fit_gate, bass_drums_only, buses, lead_notes)
    write_docs(score, validation, master_gain)
    shutil.copy2(Path(__file__), SOURCE_DIR / Path(__file__).name)

    print(OUT_DIR)
    print(f"duration={len(master) / SAMPLE_RATE:.2f}s")
    print(f"master_gain={master_gain:.6f}")
    print(f"validation_pass={validation['pass']}")
    print(OUT_DIR / "01_温跃层_ChatB_direct_v1_master.mp3")


if __name__ == "__main__":
    main()
