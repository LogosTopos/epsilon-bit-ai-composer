#!/usr/bin/env python3
"""Render a fresh combat BGM draft for the Thermocline teleport shooter."""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import scipy.signal as signal
import soundfile as sf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ebit.audio.constants import SAMPLE_RATE
from ebit.renderer import Renderer, parse_note

BPM = 192.0
BEATS_PER_BAR = 4.0
TOTAL_BARS = 72
TAIL_BEATS = 8.0
TOTAL_BEATS = TOTAL_BARS * BEATS_PER_BAR + TAIL_BEATS
BEAT_SEC = 60.0 / BPM
TOTAL_SAMPLES = int(round(TOTAL_BEATS * BEAT_SEC * SAMPLE_RATE))

OUT_DIR = PROJECT_ROOT / "output" / "analysis" / "温跃层战斗BGM_v1_重新构思"
STEM_DIR = OUT_DIR / "stem_mp3"

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SECTIONS = [
    {
        "name": "lock_on_intro",
        "start_bar": 0,
        "bars": 8,
        "intent": "cold lock-on signal, sparse drums, establish the C# minor identity",
    },
    {
        "name": "teleport_chase_a",
        "start_bar": 8,
        "bars": 16,
        "intent": "main two-bar call and four-bar answer, combat grid enters",
    },
    {
        "name": "pressure_rise",
        "start_bar": 24,
        "bars": 8,
        "intent": "chromatic danger notes and snare pressure before the first full hook",
    },
    {
        "name": "full_combat_hook",
        "start_bar": 32,
        "bars": 16,
        "intent": "bright lead stack, four-on-floor drive, playable high-energy loop body",
    },
    {
        "name": "stasis_break",
        "start_bar": 48,
        "bars": 8,
        "intent": "short time-stop breath with lower register and threat stabs",
    },
    {
        "name": "final_loop_return",
        "start_bar": 56,
        "bars": 16,
        "intent": "return to the full hook, then cadence back toward the opening loop",
    },
]

PROGRESSIONS = {
    "lock_on_intro": ["C#2", "A1", "E2", "B1"],
    "teleport_chase_a": ["C#2", "A1", "E2", "B1"],
    "pressure_rise": ["F#1", "A1", "B1", "G#1"],
    "full_combat_hook": ["A1", "B1", "C#2", "E2"],
    "stasis_break": ["C#2", "G#1", "A1", "F#1"],
    "final_loop_return": ["A1", "B1", "C#2", "G#1"],
}

PAD_CHORDS = {
    "C#2": ["C#3", "E3", "G#3", "B3"],
    "A1": ["A2", "C#3", "E3", "G#3"],
    "E2": ["E3", "G#3", "B3", "D#4"],
    "B1": ["B2", "D#3", "F#3", "A3"],
    "F#1": ["F#2", "A2", "C#3", "E3"],
    "G#1": ["G#2", "C3", "D#3", "F#3"],
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
        "v": round(velocity, 4),
    }
    if fx:
        item["fx"] = fx
    item.update(extra)
    return item


def tail_note() -> dict[str, Any]:
    return n("C0", TOTAL_BEATS - 0.125, 0.125, 0.0)


def track(name: str, instrument: str, notes: list[dict[str, Any]], pan: float = 0.0) -> dict[str, Any]:
    return {"name": name, "instrument": instrument, "pan": pan, "notes": notes + [tail_note()]}


def section_at_bar(bar: int) -> str:
    for section in reversed(SECTIONS):
        if bar >= section["start_bar"]:
            return section["name"]
    return SECTIONS[0]["name"]


def root_at_bar(bar: int) -> str:
    section = section_at_bar(bar)
    progression = PROGRESSIONS[section]
    return progression[((bar - next(s["start_bar"] for s in SECTIONS if s["name"] == section)) // 2) % len(progression)]


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


def add_delay(audio: np.ndarray, delay_beats: float, wet: float, feedback: float = 0.18, cross: bool = True) -> np.ndarray:
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


def sidechain_duck(audio: np.ndarray, trigger: np.ndarray, depth: float, release_ms: float = 95.0) -> np.ndarray:
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
        fx = {"vib": [4.7, 4.0]} if duration >= 0.75 else None
        notes.append(
            n(
                final_pitch,
                start + off,
                duration,
                velocity * velocity_scale,
                fx=fx,
                phrase=phrase,
            )
        )


HOOK_A = [
    ("C#5", 0.00, 0.75, 0.76),
    ("E5", 0.75, 0.25, 0.62),
    ("G#5", 1.00, 0.50, 0.72),
    ("B5", 1.50, 0.50, 0.68),
    ("A5", 2.00, 0.75, 0.70),
    ("G#5", 2.75, 0.25, 0.58),
    ("E5", 3.00, 0.50, 0.64),
    ("G#5", 3.50, 0.50, 0.70),
    ("C#6", 4.00, 1.00, 0.76),
    ("B5", 5.00, 0.50, 0.62),
    ("A5", 5.50, 0.50, 0.66),
    ("G#5", 6.00, 1.00, 0.72),
    ("E5", 7.00, 0.50, 0.60),
    ("F#5", 7.50, 0.25, 0.58),
    ("G#5", 7.75, 0.25, 0.64),
    ("A5", 8.00, 0.75, 0.72),
    ("G#5", 8.75, 0.25, 0.58),
    ("E5", 9.00, 0.50, 0.64),
    ("C#5", 9.50, 0.50, 0.66),
    ("B4", 10.00, 0.50, 0.58),
    ("C#5", 10.50, 0.50, 0.66),
    ("E5", 11.00, 1.00, 0.72),
    ("D#5", 12.00, 0.50, 0.58),
    ("E5", 12.50, 0.50, 0.64),
    ("G#5", 13.00, 0.50, 0.70),
    ("A5", 13.50, 0.50, 0.72),
    ("G#5", 14.00, 0.75, 0.68),
    ("E5", 14.75, 0.25, 0.58),
    ("C#5", 15.00, 1.00, 0.78),
]

HOOK_B = [
    ("E5", 0.00, 0.50, 0.68),
    ("G#5", 0.50, 0.50, 0.72),
    ("C#6", 1.00, 0.75, 0.78),
    ("B5", 1.75, 0.25, 0.58),
    ("A5", 2.00, 0.50, 0.66),
    ("G#5", 2.50, 0.50, 0.68),
    ("E5", 3.00, 1.00, 0.72),
    ("C#5", 4.50, 0.50, 0.64),
    ("E5", 5.00, 0.50, 0.68),
    ("F#5", 5.50, 0.50, 0.62),
    ("G#5", 6.00, 0.75, 0.72),
    ("B5", 6.75, 0.25, 0.60),
    ("C#6", 7.00, 1.00, 0.78),
    ("E6", 8.00, 0.75, 0.82),
    ("D#6", 8.75, 0.25, 0.64),
    ("C#6", 9.00, 0.75, 0.78),
    ("B5", 9.75, 0.25, 0.62),
    ("A5", 10.00, 0.50, 0.70),
    ("G#5", 10.50, 0.50, 0.70),
    ("E5", 11.00, 0.75, 0.66),
    ("F#5", 11.75, 0.25, 0.58),
    ("G#5", 12.00, 0.50, 0.72),
    ("A5", 12.50, 0.50, 0.74),
    ("B5", 13.00, 0.50, 0.70),
    ("C#6", 13.50, 0.50, 0.78),
    ("B5", 14.00, 0.50, 0.66),
    ("G#5", 14.50, 0.50, 0.70),
    ("C#6", 15.00, 1.00, 0.82),
]

PRESSURE = [
    ("F#5", 0.00, 0.50, 0.68),
    ("G#5", 0.50, 0.50, 0.72),
    ("A5", 1.00, 0.50, 0.74),
    ("C6", 1.50, 0.50, 0.78),
    ("C#6", 2.00, 0.75, 0.82),
    ("B5", 2.75, 0.25, 0.60),
    ("A5", 3.00, 0.50, 0.68),
    ("G#5", 3.50, 0.50, 0.70),
    ("F#5", 4.00, 0.50, 0.68),
    ("E5", 4.50, 0.50, 0.62),
    ("D#5", 5.00, 0.50, 0.66),
    ("C5", 5.50, 0.50, 0.72),
    ("C#5", 6.00, 0.50, 0.78),
    ("E5", 6.50, 0.50, 0.72),
    ("G#5", 7.00, 0.50, 0.78),
    ("C#6", 7.50, 0.50, 0.86),
]

CHORUS = [
    ("E5", 0.00, 0.50, 0.72),
    ("G#5", 0.50, 0.50, 0.78),
    ("C#6", 1.00, 0.75, 0.86),
    ("E6", 1.75, 0.25, 0.70),
    ("D#6", 2.00, 0.50, 0.74),
    ("C#6", 2.50, 0.50, 0.80),
    ("B5", 3.00, 1.00, 0.76),
    ("A5", 4.00, 0.50, 0.74),
    ("B5", 4.50, 0.50, 0.76),
    ("C#6", 5.00, 0.50, 0.82),
    ("E6", 5.50, 0.50, 0.86),
    ("F#6", 6.00, 0.75, 0.90),
    ("E6", 6.75, 0.25, 0.72),
    ("C#6", 7.00, 1.00, 0.82),
    ("G#5", 8.00, 0.50, 0.74),
    ("A5", 8.50, 0.50, 0.76),
    ("B5", 9.00, 0.50, 0.78),
    ("C#6", 9.50, 0.50, 0.84),
    ("B5", 10.00, 0.75, 0.74),
    ("A5", 10.75, 0.25, 0.62),
    ("G#5", 11.00, 0.50, 0.72),
    ("E5", 11.50, 0.50, 0.68),
    ("C#6", 12.00, 0.50, 0.82),
    ("B5", 12.50, 0.50, 0.74),
    ("A5", 13.00, 0.50, 0.72),
    ("G#5", 13.50, 0.50, 0.72),
    ("E5", 14.00, 0.50, 0.68),
    ("G#5", 14.50, 0.50, 0.78),
    ("C#6", 15.00, 1.00, 0.88),
]

BRIDGE = [
    ("C#5", 0.00, 1.50, 0.60),
    ("B4", 2.00, 0.75, 0.52),
    ("A4", 3.00, 1.25, 0.56),
    ("G#4", 5.00, 0.75, 0.54),
    ("C5", 6.00, 1.00, 0.64),
    ("C#5", 8.00, 0.75, 0.68),
    ("E5", 8.75, 0.25, 0.54),
    ("G#5", 9.00, 0.50, 0.66),
    ("B5", 9.50, 0.50, 0.62),
    ("A5", 10.00, 0.75, 0.58),
    ("G#5", 10.75, 0.25, 0.52),
    ("F#5", 11.00, 0.50, 0.58),
    ("E5", 11.50, 0.50, 0.56),
    ("D#5", 12.00, 0.50, 0.58),
    ("E5", 12.50, 0.50, 0.64),
    ("G#5", 13.00, 0.50, 0.68),
    ("C#6", 13.50, 0.50, 0.74),
    ("B5", 14.00, 0.50, 0.62),
    ("G#5", 14.50, 0.50, 0.66),
    ("C#6", 15.00, 1.00, 0.78),
]

LOOP_RETURN = [
    ("F#6", 0.00, 0.50, 0.90),
    ("E6", 0.50, 0.50, 0.80),
    ("C#6", 1.00, 0.50, 0.82),
    ("B5", 1.50, 0.50, 0.72),
    ("A5", 2.00, 0.75, 0.74),
    ("G#5", 2.75, 0.25, 0.62),
    ("E5", 3.00, 0.50, 0.70),
    ("C#5", 3.50, 0.50, 0.78),
    ("E5", 4.00, 0.50, 0.72),
    ("G#5", 4.50, 0.50, 0.78),
    ("C#6", 5.00, 0.75, 0.86),
    ("B5", 5.75, 0.25, 0.68),
    ("A5", 6.00, 0.50, 0.74),
    ("G#5", 6.50, 0.50, 0.72),
    ("E5", 7.00, 0.50, 0.70),
    ("C#5", 7.50, 0.50, 0.84),
    ("C#5", 8.00, 1.50, 0.84),
    ("G#5", 10.00, 0.50, 0.72),
    ("E5", 10.50, 0.50, 0.70),
    ("C#5", 11.00, 1.00, 0.84),
    ("B4", 12.50, 0.50, 0.58),
    ("C#5", 13.00, 0.50, 0.76),
    ("E5", 13.50, 0.50, 0.72),
    ("G#5", 14.00, 0.50, 0.78),
    ("C#6", 14.50, 0.50, 0.86),
    ("C#5", 15.00, 1.00, 0.82),
]


def build_lead_notes() -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    add_cell(notes, 0.0, HOOK_A[:15], "intro_signal", transpose_by=-12, velocity_scale=0.78)
    add_cell(notes, 16.0, HOOK_A, "intro_full_call", transpose_by=-12, velocity_scale=0.82)
    add_cell(notes, 32.0, HOOK_A, "chase_main_call", velocity_scale=0.92)
    add_cell(notes, 48.0, HOOK_B, "chase_answer", velocity_scale=0.94)
    add_cell(notes, 64.0, HOOK_A, "chase_variation_return", transpose_by=0, velocity_scale=0.96)
    add_cell(notes, 80.0, HOOK_B, "chase_peak_answer", transpose_by=0, velocity_scale=0.98)
    add_cell(notes, 96.0, PRESSURE, "pressure_rise_a", velocity_scale=0.98)
    add_cell(notes, 104.0, PRESSURE, "pressure_rise_b", transpose_by=2, velocity_scale=1.0)
    add_cell(notes, 112.0, CHORUS, "full_hook_a", velocity_scale=1.0)
    add_cell(notes, 128.0, CHORUS, "full_hook_b", velocity_scale=1.02)
    add_cell(notes, 144.0, HOOK_B, "full_hook_answer", transpose_by=0, velocity_scale=1.02)
    add_cell(notes, 160.0, CHORUS, "full_hook_restate", transpose_by=0, velocity_scale=1.02)
    add_cell(notes, 192.0, BRIDGE, "stasis_break_low", transpose_by=-12, velocity_scale=0.84)
    add_cell(notes, 208.0, BRIDGE, "stasis_reentry", transpose_by=0, velocity_scale=0.92)
    add_cell(notes, 224.0, CHORUS, "final_hook_a", velocity_scale=1.06)
    add_cell(notes, 240.0, CHORUS, "final_hook_b", velocity_scale=1.06)
    add_cell(notes, 256.0, HOOK_B, "final_answer", velocity_scale=1.04)
    add_cell(notes, 272.0, LOOP_RETURN, "loop_return_cadence", velocity_scale=1.0)
    return sorted(notes, key=lambda item: (item["b"], item["n"]))


def build_lead_tracks(lead_notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    core: list[dict[str, Any]] = []
    body: list[dict[str, Any]] = []
    click: list[dict[str, Any]] = []
    octave: list[dict[str, Any]] = []
    side: list[dict[str, Any]] = []
    for item in lead_notes:
        pitch = item["n"]
        beat = float(item["b"])
        duration = float(item["d"])
        velocity = float(item["v"])
        phrase = item.get("phrase", "")
        fx = {"vib": [4.8, 4.5]} if duration >= 0.75 else None
        core.append(n(pitch, beat, duration + 0.035, velocity, fx=fx, phrase=phrase))
        body.append(n(pitch, beat + 0.016, duration + 0.075, velocity * 0.34, fx={"vib": [4.2, 5.0]}, phrase=phrase))
        click.append(
            n(
                pitch,
                beat,
                min(0.105, max(0.055, duration * 0.22)),
                velocity * 0.24,
                phrase=phrase,
                fm_index=5.8,
                fm_ratio=3.0,
            )
        )
        if beat >= 112.0 and (duration >= 0.50 or phrase.startswith("final")):
            octave.append(n(transpose(pitch, 12), beat + 0.012, min(duration, 0.65), velocity * 0.16, phrase=phrase))
        if phrase.startswith(("pressure", "final")) and duration <= 0.50:
            side.append(n(pitch, beat + 0.018, min(duration, 0.35), velocity * 0.16, fx={"retrigger": 2}, phrase=phrase))
    return [
        track("lead_core_pulse", "pulse_25", core, pan=0.0),
        track("lead_body_sine", "sine", body, pan=-0.05),
        track("lead_click_fm", "fm", click, pan=0.04),
        track("lead_high_octave", "pulse_75", octave, pan=0.18),
        track("lead_side_pin", "pulse_12", side, pan=-0.18),
    ]


def build_lead_only_tracks(lead_notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [track("lead_only_plain_sine", "sine", [{k: v for k, v in item.items() if k in {"n", "b", "d", "v", "fx"}} for item in lead_notes], pan=0.0)]


def build_bass_tracks() -> list[dict[str, Any]]:
    pulse: list[dict[str, Any]] = []
    sub: list[dict[str, Any]] = []
    saw: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        root = root_at_bar(bar)
        beat = bar * BEATS_PER_BAR
        if section in {"lock_on_intro", "stasis_break"}:
            pulse.append(n(root, beat, 1.40, 0.38))
            pulse.append(n(transpose(root, 12), beat + 2.0, 0.70, 0.26))
            sub.append(n(transpose(root, -12), beat, 3.70, 0.18))
            if section == "stasis_break" and bar % 4 == 2:
                saw.append(n(root, beat + 2.0, 0.90, 0.20, fx={"slide_to": transpose(root, -12)}))
        elif section == "pressure_rise":
            for off in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]:
                pulse.append(n(root, beat + off, 0.32, 0.40 if off in {0.0, 2.0} else 0.30))
            if bar % 2 == 1:
                saw.append(n(root, beat + 3.0, 0.75, 0.30, fx={"slide_to": transpose(root, 12)}))
            sub.append(n(transpose(root, -12), beat, 3.75, 0.16))
        else:
            for off in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]:
                pulse.append(n(root, beat + off, 0.30, 0.42 if off in {0.0, 2.0} else 0.31))
            if section in {"full_combat_hook", "final_loop_return"}:
                for off in [0.25, 1.25, 2.25, 3.25]:
                    saw.append(n(transpose(root, 12), beat + off, 0.18, 0.18, fx={"retrigger": 2}))
            sub.append(n(transpose(root, -12), beat, 3.80, 0.15))
    return [
        track("bass_pulse_drive", "pulse_50", pulse, pan=0.0),
        track("bass_clean_sub", "sine", sub, pan=0.0),
        track("bass_saw_edge", "sawtooth", saw, pan=-0.04),
    ]


def build_drum_groups() -> dict[str, list[dict[str, Any]]]:
    kick: list[dict[str, Any]] = []
    kick_sub: list[dict[str, Any]] = []
    snare: list[dict[str, Any]] = []
    clap: list[dict[str, Any]] = []
    hat: list[dict[str, Any]] = []
    hat_wide: list[dict[str, Any]] = []
    perc: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        beat = bar * BEATS_PER_BAR
        if section == "lock_on_intro":
            kick_hits = [0.0] if bar < 4 else [0.0, 2.5]
            hat_grid = [0.0, 1.0, 2.0, 3.0] if bar < 4 else [i * 0.5 for i in range(8)]
        elif section == "stasis_break":
            kick_hits = [0.0] if bar % 4 in {0, 3} else [0.0, 3.0]
            hat_grid = [0.5, 1.5, 2.5, 3.5]
        elif section == "pressure_rise":
            kick_hits = [0.0, 1.5, 2.5, 3.25]
            hat_grid = [i * 0.25 for i in range(16)]
        elif section in {"full_combat_hook", "final_loop_return"}:
            kick_hits = [0.0, 1.0, 2.0, 3.0]
            if bar % 4 in {1, 3}:
                kick_hits += [2.5, 3.5]
            hat_grid = [i * 0.25 for i in range(16)]
        else:
            kick_hits = [0.0, 1.5, 2.0, 3.25]
            hat_grid = [i * 0.5 for i in range(8)]

        for off in kick_hits:
            kick.append(n("C2", beat + off, 0.15, 0.86 if off in {0.0, 2.0} else 0.64, fm_index=7.5, fm_ratio=3.2))
            kick_sub.append(n("C1", beat + off, 0.22, 0.28))
        if section != "lock_on_intro" or bar >= 4:
            for off in [1.0, 3.0]:
                snare.append(n("D3", beat + off, 0.16, 0.62))
                clap.append(n("D4", beat + off + 0.012, 0.08, 0.22, fx={"retrigger": 2}))
        if bar % 8 == 7 and section in {"pressure_rise", "full_combat_hook", "final_loop_return"}:
            snare.append(n("D3", beat + 3.0, 0.92, 0.42, fx={"retrigger": 8, "tremolo": [10.0, 0.16]}))
        for off in hat_grid:
            accent = 0.24 if abs(off % 1.0) < 1e-6 else 0.14
            if section in {"pressure_rise", "full_combat_hook", "final_loop_return"}:
                accent *= 1.20
            hat.append(n("F#5", beat + off, 0.05, accent))
            if section in {"full_combat_hook", "final_loop_return"} and int(off * 4) % 2 == 1:
                hat_wide.append(n("F#5", beat + off, 0.042, accent * 0.55))
        if section in {"teleport_chase_a", "pressure_rise", "full_combat_hook", "final_loop_return"}:
            for off in [0.75, 2.75]:
                perc.append(n("C6", beat + off, 0.05, 0.15))
            if bar % 4 == 2:
                perc.append(n("G5", beat + 3.5, 0.08, 0.22, fx={"retrigger": 3}))

    return {
        "kick": [
            track("drum_kick_fm", "fm", kick, pan=0.0),
            track("drum_kick_sub", "sine", kick_sub, pan=0.0),
        ],
        "snare": [
            track("drum_snare_noise", "noise_short", snare, pan=0.02),
            track("drum_snap_clap", "noise_periodic", clap, pan=0.06),
        ],
        "hat": [
            track("drum_hat_needle", "noise_short", hat, pan=0.23),
            track("drum_hat_wide", "noise_long", hat_wide, pan=-0.24),
        ],
        "perc": [track("drum_shell_perc", "pulse_12", perc, pan=-0.16)],
    }


def build_harmony_tracks() -> list[dict[str, Any]]:
    pad_low: list[dict[str, Any]] = []
    pad_high: list[dict[str, Any]] = []
    arp: list[dict[str, Any]] = []
    counter: list[dict[str, Any]] = []
    alarm: list[dict[str, Any]] = []
    for bar in range(0, TOTAL_BARS, 2):
        section = section_at_bar(bar)
        root = root_at_bar(bar)
        chord = PAD_CHORDS[root]
        beat = bar * BEATS_PER_BAR
        pad_velocity = 0.11 if section in {"lock_on_intro", "stasis_break"} else 0.075
        for idx, pitch in enumerate(chord):
            pan = -0.28 + idx * 0.18
            pad_low.append(
                n(
                    pitch,
                    beat,
                    7.75,
                    pad_velocity,
                    fx={"vib": [3.2 + idx * 0.2, 4.8], "tremolo": [2.4, 0.10]},
                    pan=pan,
                )
            )
            if section in {"pressure_rise", "full_combat_hook", "final_loop_return"}:
                pad_high.append(
                    n(
                        transpose(pitch, 12),
                        beat + 0.02,
                        7.60,
                        pad_velocity * 0.36,
                        fx={"vib": [4.5, 7.0]},
                        pan=-pan,
                    )
                )
        if section in {"teleport_chase_a", "pressure_rise", "full_combat_hook", "final_loop_return"}:
            pattern = [transpose(p, 12) for p in chord]
            for idx in range(32):
                if section == "teleport_chase_a" and idx % 2 == 1:
                    continue
                note = pattern[idx % len(pattern)]
                arp.append(n(note, beat + idx * 0.25, 0.075, 0.13 if idx % 4 else 0.18))
        if section in {"pressure_rise", "stasis_break"}:
            alarm.append(n(chord[0], beat, 0.75, 0.14, fx={"arp": [0, 3, 6, 10]}))
            alarm.append(n(chord[1], beat + 4.0, 0.75, 0.12, fx={"arp": [0, 2, 7, 9]}))

    for start in [64.0, 144.0, 240.0]:
        for off, pitch in [(2.0, "E5"), (2.5, "G#5"), (3.0, "A5"), (3.5, "G#5"), (6.0, "B5"), (6.5, "C#6")]:
            counter.append(n(pitch, start + off, 0.32, 0.22, fx={"vib": [5.1, 3.0]}))
    return [
        track("harmony_cold_pad", "sine", pad_low, pan=0.0),
        track("harmony_frost_high_pad", "wavetable", pad_high, pan=0.0),
        track("harmony_combat_arp", "pulse_12", arp, pan=0.18),
        track("harmony_answer_pins", "pulse_75", counter, pan=-0.18),
        track("harmony_alarm_color", "pulse_25", alarm, pan=-0.24),
    ]


def build_fx_tracks() -> list[dict[str, Any]]:
    chirp: list[dict[str, Any]] = []
    impact: list[dict[str, Any]] = []
    stab: list[dict[str, Any]] = []
    for bar in [8, 24, 32, 48, 56, 72]:
        beat = bar * BEATS_PER_BAR
        if bar < TOTAL_BARS:
            chirp.append(n("G#6", beat - 0.50, 0.18, 0.26, fx={"slide_to": "C#7", "retrigger": 3}))
            impact.append(n("C2", beat, 0.28, 0.30, fm_index=8.0, fm_ratio=4.0))
            impact.append(n("C1", beat + 0.02, 0.32, 0.18))
    for bar in range(12, TOTAL_BARS, 8):
        beat = bar * BEATS_PER_BAR + 3.0
        chirp.append(n("E6", beat, 0.16, 0.18, fx={"slide_to": "B6"}))
    for bar in [28, 50, 52]:
        beat = bar * BEATS_PER_BAR
        stab.append(n("C#4", beat + 2.0, 1.20, 0.20, fx={"vib": [8.0, 30]}))
        impact.append(n("G#1", beat + 2.0, 0.42, 0.16, fx={"slide_to": "C#1"}))
    return [
        track("fx_teleport_chirp", "pulse_12", chirp, pan=0.26),
        track("fx_low_impact", "fm", impact, pan=0.0),
        track("fx_lockon_stab", "fm", stab, pan=-0.18),
    ]


def build_score(lead_notes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "title": "温跃层战斗BGM_v1_重新构思",
        "bpm": BPM,
        "bars": TOTAL_BARS,
        "tail_beats": TAIL_BEATS,
        "duration_sec": round(TOTAL_SAMPLES / SAMPLE_RATE, 3),
        "sections": SECTIONS,
        "tonal_center": "C# minor with harmonic/minor-threat color",
        "anti_inertia_rules": [
            "No new reference-song extraction or similarity analysis in this pass.",
            "The main melody is newly written from phrase cells, not copied from previous superweapon drafts.",
            "Fast motion is delegated to drums, bass, arp, and teleport FX; the lead keeps repeatable call-and-answer phrases.",
            "Only short pickups use sixteenth-note density; long notes are allowed to remain long.",
        ],
        "lead_notes": lead_notes,
        "lead_duration_vocab": sorted({round(float(item["d"]), 4) for item in lead_notes}),
        "lead_phrase_counts": Counter(str(item.get("phrase", "")) for item in lead_notes),
        "progressions": PROGRESSIONS,
    }


def master_from_buses(buses: dict[str, np.ndarray]) -> tuple[np.ndarray, float]:
    mix = mix_arrays(list(buses.values()))
    mix = butter(mix, "highpass", 26.0)
    mix = np.tanh(mix * 1.04) / np.tanh(1.04)
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    gain = 0.94 / peak if peak > 1e-8 else 1.0
    return (mix * gain).astype(np.float32), gain


def validate_audio(master: np.ndarray, lead_only: np.ndarray, no_lead: np.ndarray, buses: dict[str, np.ndarray]) -> dict[str, Any]:
    validations = {
        "sample_rate": SAMPLE_RATE,
        "expected_duration_sec": round(TOTAL_SAMPLES / SAMPLE_RATE, 3),
        "master_shape": list(master.shape),
        "master_duration_sec": round(len(master) / SAMPLE_RATE, 3),
        "master_has_nan": bool(np.isnan(master).any()),
        "master_peak": round(stats(master)[0], 6),
        "master_rms_db": round(stats(master)[1], 2),
        "lead_only_rms_db": round(stats(lead_only)[1], 2),
        "no_lead_rms_db": round(stats(no_lead)[1], 2),
        "bus_stats": {
            name: {
                "peak": round(stats(audio)[0], 6),
                "rms_db": round(stats(audio)[1], 2),
            }
            for name, audio in buses.items()
        },
    }
    validations["pass"] = (
        not validations["master_has_nan"]
        and 0.20 <= validations["master_peak"] <= 0.96
        and validations["master_rms_db"] > -32.0
        and abs(validations["master_duration_sec"] - validations["expected_duration_sec"]) <= 0.02
    )
    return validations


def write_docs(score: dict[str, Any], validation: dict[str, Any], master_gain: float) -> None:
    (OUT_DIR / "结构_score.json").write_text(
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
    readme = f"""# 温跃层战斗BGM_v1_重新构思

本轮是重开对话后的新作曲版本，目标不是继续扒谱，而是直接写一段可作为游戏战斗循环雏形的 BGM。

## 创作计划

- 游戏目标：无 CD 瞬移、枪械后坐力、时停/高速反应、超级兵器爽感。
- 音乐目标：高速度、大动态、短暂哈人，但主旋律仍要能复述。
- 本轮边界：不继续做参考曲逆向；不复用旧 `超级兵器主旋律_v1` 旋律轮廓；只把旧产物当作失败边界。
- 写法：主旋律使用 2 小节口号动机与 4 小节回答句；鼓、低频、arp 和瞬移 FX 承担速度；lead 避免被切碎。

## 听音顺序

1. `01_温跃层战斗BGM_v1_master.mp3`：完整样段。
2. `02_主旋律only_朴素sine.mp3`：只判断旋律轮廓和切分是否成立。
3. `03_去掉主旋律_伴奏对比.mp3`：判断 BGM 驱动感是否过度依赖 lead。
4. `stem_mp3/`：分组听主旋律、低频、鼓、和声、FX。

## 结构

{chr(10).join(section_lines)}

## 技术信息

- BPM: {BPM}
- Bars: {TOTAL_BARS}
- Duration: {TOTAL_SAMPLES / SAMPLE_RATE:.2f}s
- Tonal center: C# minor
- Master gain: {master_gain:.6f}
- Validation pass: {validation['pass']}
- Master peak: {validation['master_peak']}
- Master RMS: {validation['master_rms_db']} dB
"""
    (OUT_DIR / "说明.md").write_text(readme, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STEM_DIR.mkdir(parents=True, exist_ok=True)
    renderer = Renderer()

    lead_notes = build_lead_notes()
    drum_groups = build_drum_groups()
    buses: dict[str, np.ndarray] = {}
    buses["01_主旋律_lead"] = render_bus(renderer, build_lead_tracks(lead_notes), volume=0.56) * 1.05
    buses["02_低频_bass"] = render_bus(renderer, build_bass_tracks(), volume=0.58) * 0.90
    kick_trigger = render_bus(renderer, drum_groups["kick"], volume=0.62)
    buses["03_鼓组_drums"] = (
        render_bus(renderer, drum_groups["kick"] + drum_groups["snare"] + drum_groups["hat"] + drum_groups["perc"], volume=0.62)
        * 1.18
    )
    buses["04_和声与arp"] = render_bus(renderer, build_harmony_tracks(), volume=0.48) * 0.86
    buses["05_瞬移FX"] = render_bus(renderer, build_fx_tracks(), volume=0.52) * 0.84

    buses["01_主旋律_lead"] = add_delay(butter(buses["01_主旋律_lead"], "lowpass", 7200.0), 0.18, 0.045)
    buses["02_低频_bass"] = butter(sidechain_duck(buses["02_低频_bass"], kick_trigger, 0.12), "lowpass", 5200.0)
    buses["04_和声与arp"] = butter(sidechain_duck(buses["04_和声与arp"], kick_trigger, 0.16), "lowpass", 6800.0)
    buses["05_瞬移FX"] = add_delay(butter(buses["05_瞬移FX"], "highpass", 120.0), 0.25, 0.06)

    master, master_gain = master_from_buses(buses)
    lead_only_raw = render_bus(renderer, build_lead_only_tracks(lead_notes), volume=0.70)
    lead_only = np.nan_to_num(lead_only_raw)
    lead_peak = float(np.max(np.abs(lead_only))) if lead_only.size else 0.0
    if lead_peak > 1e-8:
        lead_only = (lead_only / lead_peak * 0.88).astype(np.float32)
    no_lead_buses = {key: value for key, value in buses.items() if key != "01_主旋律_lead"}
    no_lead, _ = master_from_buses(no_lead_buses)

    write_wav_mp3(renderer, master, OUT_DIR / "01_温跃层战斗BGM_v1_master")
    write_wav_mp3(renderer, lead_only, OUT_DIR / "02_主旋律only_朴素sine")
    write_wav_mp3(renderer, no_lead, OUT_DIR / "03_去掉主旋律_伴奏对比")
    for name, audio in buses.items():
        write_mp3(renderer, audio * master_gain, STEM_DIR / name)

    score = build_score(lead_notes)
    validation = validate_audio(master, lead_only, no_lead, buses)
    write_docs(score, validation, master_gain)

    print(OUT_DIR)
    print(f"duration={len(master) / SAMPLE_RATE:.2f}s")
    print(f"master_gain={master_gain:.6f}")
    print(f"validation_pass={validation['pass']}")
    print(OUT_DIR / "01_温跃层战斗BGM_v1_master.mp3")


if __name__ == "__main__":
    main()
