#!/usr/bin/env python3
"""Thermocline holy-war battle demo v6.

v6 removes the horror-choir problem entirely:

- No choir/chant samples. The AMY choir sounds like horror-film texture,
  not a classical ensemble. Removed.
- bass_motif_drive is the main voice: driving rock bass riffs with
  call-response between registers and stereo positions.
- Drums rebuilt with natural section transitions, fill bars, ghost notes,
  velocity humanization, and evolving hi-hat patterns.
- harmony_oath_pad and organ_answer_cue support the bass motif.
- scene_fx_cues remain sparse decorative events.
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

random.seed(42)
np.random.seed(42)

BPM = 176.0
BEATS_PER_BAR = 4.0
TOTAL_BARS = 174
TAIL_BEATS = 8.0
TOTAL_BEATS = TOTAL_BARS * BEATS_PER_BAR + TAIL_BEATS
BEAT_SEC = 60.0 / BPM
TOTAL_SAMPLES = int(round(TOTAL_BEATS * BEAT_SEC * SAMPLE_RATE))
TICKS_PER_BEAT = 480

OUT_DIR = PROJECT_ROOT / "output" / "analysis" / "thermocline_holy_war_battle_demo_v6"
STEM_DIR = OUT_DIR / "stem_mp3"
SOURCE_DIR = OUT_DIR / "source"

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SECTIONS = [
    {"name": "arming_liturgy",        "start_bar": 0,   "bars": 12, "energy": 0.38, "groove": "march_slow"},
    {"name": "teleport_breach",       "start_bar": 12,  "bars": 16, "energy": 0.70, "groove": "drive_fast"},
    {"name": "bullet_time_freeze",    "start_bar": 28,  "bars": 10, "energy": 0.46, "groove": "half_time"},
    {"name": "zealot_call_response",  "start_bar": 38,  "bars": 18, "energy": 0.78, "groove": "rock_steady"},
    {"name": "heat_accumulation",     "start_bar": 56,  "bars": 20, "energy": 0.86, "groove": "dense_roll"},
    {"name": "shield_reset_void",     "start_bar": 76,  "bars": 8,  "energy": 0.34, "groove": "minimal"},
    {"name": "holy_war_charge",       "start_bar": 84,  "bars": 22, "energy": 1.00, "groove": "full_charge"},
    {"name": "shockwave_rescue",      "start_bar": 106, "bars": 14, "energy": 0.64, "groove": "staggered"},
    {"name": "overheat_trance",       "start_bar": 120, "bars": 18, "energy": 0.94, "groove": "blast"},
    {"name": "dual_protagonist",      "start_bar": 138, "bars": 18, "energy": 0.88, "groove": "crossfire"},
    {"name": "thermocline_reversal",  "start_bar": 156, "bars": 12, "energy": 0.82, "groove": "rising"},
    {"name": "loop_exit_oath",        "start_bar": 168, "bars": 6,  "energy": 0.58, "groove": "abrupt"},
]

MIDI_PROGRAMS = {
    "bass_motif_drive": 38,
    "bass_sustain_floor": 38,
    "harmony_oath_pad": 49,
    "drum_rock_core": 0,
    "drum_sub_kick": 0,
    "organ_answer_cue": 20,
    "scene_fx_cues": 81,
}

DRUM_MIDI_NOTES = {
    "drum_rock_core": 36,
    "drum_sub_kick": 35,
}

ROOTS = ["C3", "G2", "D3", "A2", "F3", "C3", "E3", "G3", "D3", "A2", "F3", "C3"]


# ── helpers ─────────────────────────────────────────────────────

def n(name: str, beat: float, duration: float, velocity: float, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"n": name, "b": round(beat, 4), "d": round(duration, 4), "v": round(velocity, 4)}
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


def section_at_bar(bar: int) -> dict[str, Any]:
    for section in reversed(SECTIONS):
        if bar >= int(section["start_bar"]):
            return section
    return SECTIONS[0]


def section_end_bar(section: dict[str, Any]) -> int:
    return int(section["start_bar"]) + int(section["bars"])


def root_at_bar(bar: int) -> str:
    return ROOTS[(bar // 8) % len(ROOTS)]


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


def add_delay(audio: np.ndarray, delay_beats: float, wet: float, feedback: float = 0.16, cross: bool = True) -> np.ndarray:
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


def sidechain_duck(audio: np.ndarray, trigger: np.ndarray, depth: float, release_ms: float = 70.0) -> np.ndarray:
    mono = np.abs(trigger.mean(axis=1)).astype(np.float32)
    alpha = math.exp(-1.0 / max(SAMPLE_RATE * release_ms / 1000.0, 1.0))
    envelope = signal.lfilter([1.0 - alpha], [1.0, -alpha], mono)
    peak = float(np.max(envelope)) if envelope.size else 0.0
    if peak > 1e-8:
        envelope = envelope / peak
    return (audio * (1.0 - depth * envelope[:, None])).astype(np.float32)


def make_track(
    name: str, instrument: str, notes: list[dict[str, Any]],
    pan: float = 0.0, midi_program: int | None = None, midi_channel: int = 0,
) -> dict[str, Any]:
    tail = n("C0", TOTAL_BEATS - 0.125, 0.125, 0.0)
    return {
        "name": name, "instrument": instrument, "pan": pan,
        "midi_program": MIDI_PROGRAMS.get(name, 80) if midi_program is None else midi_program,
        "midi_channel": midi_channel,
        "notes": sorted(notes + [tail], key=lambda item: (float(item["b"]), item["n"])),
    }


def render_bus(renderer: Renderer, tracks: list[dict[str, Any]], volume: float) -> np.ndarray:
    return mix_arrays(list(renderer.render_multi_stereo({"bpm": BPM, "tracks": tracks}, volume=volume).values()))


def write_wav_mp3(renderer: Renderer, audio: np.ndarray, stem: Path, bitrate: str = "256k") -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    sf.write(stem.with_suffix(".wav"), audio, SAMPLE_RATE)
    renderer.save_mp3(audio, str(stem.with_suffix(".mp3")), bitrate=bitrate)


def write_mp3(renderer: Renderer, audio: np.ndarray, path: Path, bitrate: str = "224k") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    renderer.save_mp3(audio, str(path), bitrate=bitrate)


def humanize_vel(base: float, amount: float = 0.06) -> float:
    return base + random.uniform(-amount, amount)


def chord_notes(root: str, intervals: list[int], octave_shift: int = 0) -> list[str]:
    base = transpose(root, octave_shift)
    return [transpose(base, interval) for interval in intervals]


# ── v6 bass motif system ────────────────────────────────────────

def build_bass_motif_system() -> dict[str, list[dict[str, Any]]]:
    """Build bass layers with bass_motif_drive as the main voice.

    bass_motif_drive: driving rock bass riffs, call-response between registers.
    bass_sustain_floor: low foundation, root/fifth/octave, >=85% occupancy.
    """
    motif_notes: list[dict[str, Any]] = []
    sustain_notes: list[dict[str, Any]] = []

    # Motif cells — rock-style bass patterns (1 bar each)
    # Each cell is a list of (offset_in_bar, pitch_offset_from_root, duration, accent)
    motif_cell_a = [  # "call" — root-anchored, driving
        (0.0, 0, 0.28, 0.70), (0.50, 7, 0.24, 0.58), (1.0, 0, 0.28, 0.72),
        (1.50, 12, 0.22, 0.52), (2.0, 0, 0.28, 0.68), (2.50, 7, 0.24, 0.54),
        (3.0, 0, 0.30, 0.74), (3.50, 5, 0.20, 0.48),
    ]
    motif_cell_b = [  # "response" — fifth/octave anchored, answering
        (0.0, 7, 0.26, 0.62), (0.50, 12, 0.22, 0.50), (1.0, 7, 0.26, 0.64),
        (1.50, 0, 0.24, 0.56), (2.0, 12, 0.28, 0.66), (2.50, 7, 0.22, 0.48),
        (3.0, 0, 0.30, 0.70), (3.50, -2, 0.18, 0.40),
    ]
    motif_cell_c = [  # "drive" — dense, for high-energy sections
        (0.0, 0, 0.18, 0.78), (0.25, 7, 0.16, 0.60), (0.50, 0, 0.18, 0.76),
        (0.75, 12, 0.15, 0.56), (1.0, 0, 0.18, 0.80), (1.25, 7, 0.16, 0.62),
        (1.50, 0, 0.18, 0.74), (1.75, 5, 0.15, 0.52),
        (2.0, 0, 0.18, 0.78), (2.50, 7, 0.16, 0.58),
        (3.0, 12, 0.20, 0.72), (3.50, 0, 0.18, 0.64),
    ]
    motif_cell_d = [  # "half-time" — sparse, for quiet sections
        (0.0, 0, 0.40, 0.56), (2.0, 7, 0.36, 0.50),
        (3.0, 0, 0.38, 0.54),
    ]

    def get_motif_cell(groove: str, call: bool) -> list[tuple]:
        if groove in {"minimal", "half_time"}:
            return motif_cell_d
        if groove in {"dense_roll", "blast", "full_charge"}:
            return motif_cell_c
        if call:
            return motif_cell_a
        return motif_cell_b

    for section in SECTIONS:
        start_bar = int(section["start_bar"])
        end_bar = section_end_bar(section)
        energy = float(section["energy"])
        groove = str(section.get("groove", "rock_steady"))

        for bar in range(start_bar, end_bar):
            beat = bar_to_beat(bar)
            root = root_at_bar(bar)
            rel = bar - start_bar
            phase = rel

            # ── bass_sustain_floor — always present ──
            sus_vel = 0.28 + energy * 0.10
            if phase < 2:
                sus_vel *= 0.60
            elif phase < 4:
                sus_vel *= 0.80
            sustain_notes.append(n(transpose(root, -12), beat, 3.86, sus_vel))

            # ── bass_motif_drive — call-response pattern ──
            # Phase 0-1: minimal motif (root only)
            # Phase 2-3: partial motif (call only, center)
            # Phase 4+: full call-response (alternating every 2 bars)
            is_call = (rel // 2) % 2 == 0
            cell = get_motif_cell(groove, is_call)
            motif_gain = 0.55 if phase < 2 else (0.78 if phase < 4 else 1.0)

            for off, pitch_off, dur, base_vel in cell:
                if phase < 2 and off >= 2.0:
                    continue  # minimal: only first half of bar
                if phase < 4 and len([o for o, _, _, _ in cell if o < 2.0]) > 0 and off >= 2.0 and groove not in {"dense_roll", "blast"}:
                    continue  # partial: thin out second half

                pitch_name = transpose(root, pitch_off)
                vel = base_vel * motif_gain * energy
                vel = humanize_vel(vel, 0.04)

                # Call-response panning
                if phase >= 4:
                    pan = -0.28 if is_call else 0.28
                else:
                    pan = 0.0

                motif_notes.append(n(pitch_name, beat + off, max(0.06, dur), vel, pan=pan))

    return {
        "bass_motif": [make_track("bass_motif_drive", "triangle", motif_notes, pan=0.0, midi_program=38)],
        "bass_sustain": [make_track("bass_sustain_floor", "sine", sustain_notes, pan=0.0, midi_program=38)],
    }


# ── v6 harmony ───────────────────────────────────────────────────

def build_harmony() -> dict[str, list[dict[str, Any]]]:
    """Harmony pad supporting the bass motif. Staged expansion."""
    harmony_notes: list[dict[str, Any]] = []

    for section in SECTIONS:
        start_bar = int(section["start_bar"])
        end_bar = section_end_bar(section)
        energy = float(section["energy"])

        for bar in range(start_bar, end_bar):
            beat = bar_to_beat(bar)
            root = root_at_bar(bar)
            rel = bar - start_bar
            phase = rel

            if rel % 2 != 0:
                continue  # every 2 bars

            dur = 7.60 if bar + 1 < end_bar else 3.60

            if phase < 2:
                intervals = [0, 7]
                vel_base = (0.16 + energy * 0.08) * 0.50
            elif phase < 4:
                intervals = [0, 7, 12]
                vel_base = (0.16 + energy * 0.08) * 0.72
            else:
                intervals = [0, 7, 12, 14]
                vel_base = 0.16 + energy * 0.08

            for idx, pitch in enumerate(chord_notes(root, intervals)):
                harmony_notes.append(n(
                    pitch, beat, dur,
                    humanize_vel(vel_base * (0.95 if idx % 2 else 1.0), 0.03),
                    pan=-0.22 + 0.14 * idx,
                ))

    return {"harmony": [make_track("harmony_oath_pad", "fm_string", harmony_notes, pan=0.0, midi_program=49)]}


# ── v6 organ answer cue ─────────────────────────────────────────

def build_organ_answer_cue() -> dict[str, list[dict[str, Any]]]:
    """Short organ/brass answers at phrase points. No choir. <=15% occupancy."""
    answer_notes: list[dict[str, Any]] = []

    for section in SECTIONS:
        start_bar = int(section["start_bar"])
        end_bar = section_end_bar(section)
        energy = float(section["energy"])

        for bar in range(start_bar, end_bar):
            rel = bar - start_bar
            root = root_at_bar(bar)

            # Phrase points: section start, mid, and end
            is_phrase = (
                rel == 0 or
                rel == int(section["bars"]) // 2 or
                rel == int(section["bars"]) - 2
            )
            if not is_phrase:
                continue

            beat = bar_to_beat(bar) + 2.0
            vel = (0.30 + energy * 0.35)

            # Organ chord stab
            pitches = chord_notes(root, [0, 7, 12], octave_shift=12)
            for idx, pitch in enumerate(pitches):
                answer_notes.append(n(
                    pitch, beat + idx * 0.04, 0.38,
                    humanize_vel(vel * (0.85 if idx > 0 else 1.0), 0.04),
                    pan=-0.20 + 0.20 * idx,
                ))

    return {"organ_answer": [make_track("organ_answer_cue", "fm_brass", answer_notes, pan=0.0, midi_program=20)]}


# ── v6 scene fx cues ────────────────────────────────────────────

def build_scene_fx_cues() -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Sparse decorative events. No choir samples. <=3% occupancy."""
    symbols: list[dict[str, Any]] = []
    event_counts: dict[str, int] = {
        "rifle_burst": 0, "heat_click": 0, "shield_ring": 0,
        "impact_hit": 0, "pin_tick": 0,
    }

    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        name = str(section["name"])
        energy = float(section["energy"])
        start_bar = int(section["start_bar"])
        rel = bar - start_bar
        beat = bar_to_beat(bar)
        root = root_at_bar(bar)

        is_section_start = (rel == 0)
        is_section_exit = (rel == int(section["bars"]) - 1)
        is_handoff = (bar in {12, 28, 38, 56, 76, 84, 106, 120, 138, 156, 168})
        is_escalation = (energy >= 0.86 and rel in {5, 9, 13}
                         and name not in {"shockwave_rescue", "shield_reset_void"})
        can_ornament = is_section_start or is_section_exit or is_handoff or is_escalation
        if not can_ornament:
            continue

        # Rifle burst — synth pulse pings
        if energy >= 0.60 and name not in {"arming_liturgy", "shield_reset_void"}:
            if is_section_start or is_handoff or is_escalation:
                pitches = [transpose(root, 12), transpose(root, 19), transpose(root, 14)]
                offsets = [0.125, 1.375, 2.875] if energy >= 0.78 else [0.25, 2.25]
                for idx, off in enumerate(offsets):
                    vel = 0.08 + energy * 0.08
                    symbols.append(n(
                        pitches[idx % len(pitches)], beat + off, 0.06,
                        humanize_vel(vel, 0.02),
                        pan=-0.40 + 0.40 * (idx % 2),
                    ))
                    event_counts["rifle_burst"] += 1

        # Heat click — short high pings
        if name in {"heat_accumulation", "overheat_trance", "thermocline_reversal"}:
            if is_section_start or is_escalation:
                for off in [0.0, 1.5, 3.0]:
                    if event_counts["heat_click"] % 2 == 0:
                        pitch = transpose(root, 24 + (event_counts["heat_click"] % 3) * 2)
                        symbols.append(n(pitch, beat + off, 0.05,
                                         humanize_vel(0.06 + energy * 0.05, 0.02)))
                    event_counts["heat_click"] += 1

        # Shield ring
        if name in {"bullet_time_freeze", "shield_reset_void", "shockwave_rescue"}:
            if is_section_start or rel == int(section["bars"]) // 2:
                for off in [0.0, 2.0]:
                    symbols.append(n(
                        transpose(root, 31), beat + off, 0.18,
                        humanize_vel(0.12 + energy * 0.10, 0.03), pan=0.0,
                    ))
                    event_counts["shield_ring"] += 1

        # Impact hit
        if is_section_start or is_section_exit:
            symbols.append(n(
                transpose(root, -12), beat + 0.02, 0.18,
                humanize_vel(0.18 + energy * 0.12, 0.04), pan=0.0,
            ))
            event_counts["impact_hit"] += 1

        # Pin tick — very rare
        if energy >= 0.82 and (is_section_exit or is_escalation):
            if event_counts["pin_tick"] < 40:
                for off in [1.0, 3.0]:
                    pitch = transpose(root, 24 if (rel + int(off)) % 2 else 19)
                    symbols.append(n(
                        pitch, beat + off + 0.50, 0.05,
                        humanize_vel(0.06 + energy * 0.04, 0.02),
                        pan=-0.24 + 0.48 * (int(off) % 2),
                    ))
                    event_counts["pin_tick"] += 1

    return symbols, event_counts


# ── v6 drums — complex patterns with natural transitions ─────────

def build_drums() -> dict[str, list[dict[str, Any]]]:
    """Build drum tracks with smooth section transitions.

    Features:
    - Fill bars at section exits (extra snare/kick activity)
    - Transition bars at section entrances (simplified skeleton)
    - Ghost snare notes between main hits
    - Velocity humanization throughout
    - Hi-hat patterns that evolve within sections
    - Ride bell on high-energy choruses
    """
    kick_notes: list[dict[str, Any]] = []
    snare_notes: list[dict[str, Any]] = []
    hat_notes: list[dict[str, Any]] = []
    sub_kick_notes: list[dict[str, Any]] = []

    def kick_pattern(groove: str, energy: float, phase: int, bar: int) -> list[float]:
        """Return kick hit offsets for this bar."""
        if groove == "minimal":
            return [0.0] if phase == 0 else ([0.0, 2.5] if phase >= 4 else [0.0])
        if groove == "half_time":
            return [0.0] if phase % 2 == 0 else [0.0, 3.0]
        if groove == "march_slow":
            if bar < 4:
                return [0.0]
            return [0.0, 2.5]
        if groove == "drive_fast":
            return [0.0, 1.5, 2.5, 3.25] if phase >= 2 else [0.0, 2.5]
        if groove == "staggered":
            return [0.0, 2.75]
        if groove == "full_charge":
            if phase < 2:
                return [0.0, 2.0]
            return [0.0, 1.5, 2.0, 3.25]
        if groove == "dense_roll":
            if phase < 2:
                return [0.0, 2.0]
            return [0.0, 1.0, 2.0, 3.0]
        if groove in {"blast", "crossfire"}:
            if phase < 2:
                return [0.0, 2.0]
            if phase % 2 == 0:
                return [0.0, 1.5, 2.25, 3.25]
            return [0.5, 1.25, 2.0, 3.5]
        if groove == "rising":
            return [0.0, 0.75, 1.75, 2.5, 3.25]
        if groove == "abrupt":
            return [0.0, 1.5, 2.5, 3.25]
        # rock_steady
        if phase < 2:
            return [0.0, 2.0]
        return [0.0, 1.5, 2.5, 3.25]

    def snare_pattern(groove: str, energy: float, phase: int, bar: int) -> list[float]:
        """Return snare hit offsets for this bar."""
        if groove == "minimal":
            return []
        if groove == "half_time":
            return [3.25] if phase % 2 == 0 else []
        if groove == "march_slow":
            return [2.0] if bar >= 2 else []
        if groove == "staggered":
            return [1.5, 3.25] if phase % 2 == 0 else [2.5]
        if groove == "full_charge":
            if phase < 2:
                return [2.0]
            return [1.0, 3.0]
        if groove in {"dense_roll", "blast"}:
            if phase < 2:
                return [2.0]
            return [1.0, 3.0]
        if groove == "crossfire":
            if phase < 2:
                return [2.0]
            return [1.0, 3.0]
        if groove == "rising":
            return [1.25, 2.75]
        if groove == "abrupt":
            return [1.0, 3.0]
        # rock_steady, drive_fast
        if phase < 2:
            return [2.0]
        return [1.0, 3.0]

    def hat_pattern(groove: str, energy: float, phase: int, bar: int) -> list[tuple[float, float, bool]]:
        """Return (offset, duration, is_accent) for hi-hat hits."""
        if groove == "minimal":
            return [(0.0, 0.06, True), (2.0, 0.06, True)]
        if groove == "half_time":
            result = []
            pos = 0.0
            while pos < 4.0:
                acc = (pos == 0.0 or pos == 2.0)
                result.append((pos, 0.05, acc))
                pos += 1.0
            return result
        if groove in {"march_slow", "staggered"}:
            result = []
            pos = 0.0
            while pos < 4.0:
                acc = (pos == 0.0 or pos == 2.0)
                result.append((pos, 0.05, acc))
                pos += 0.50
            return result
        if groove in {"drive_fast", "rock_steady"}:
            if phase < 2:
                step = 0.50
            elif energy >= 0.80:
                step = 0.25
            else:
                step = 0.25 if energy >= 0.70 else 0.50
            result = []
            pos = 0.0
            while pos < 4.0:
                acc = (pos == 0.0 or pos == 2.0)
                result.append((pos, 0.04, acc))
                pos += step
            return result
        if groove in {"dense_roll", "blast", "full_charge", "crossfire"}:
            if phase < 2:
                step = 0.50
            else:
                step = 0.25
            result = []
            pos = 0.0
            while pos < 4.0:
                acc = (pos == 0.0 or pos == 2.0)
                result.append((pos, 0.04, acc))
                pos += step
            return result
        if groove == "rising":
            step = 0.25
            result = []
            pos = 0.0
            while pos < 4.0:
                acc = (pos == 0.0 or pos == 2.0)
                result.append((pos, 0.04, acc))
                pos += step
            return result
        if groove == "abrupt":
            step = 0.25
            result = []
            pos = 0.0
            while pos < 4.0:
                acc = (pos == 0.0 or pos == 2.0)
                result.append((pos, 0.04, acc))
                pos += step
            return result
        return [(0.0, 0.06, True), (2.0, 0.06, True)]

    prev_groove: str | None = None

    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        name = str(section["name"])
        energy = float(section["energy"])
        groove = str(section.get("groove", "rock_steady"))
        start_bar = int(section["start_bar"])
        end_bar = section_end_bar(section)
        rel = bar - start_bar
        beat = bar_to_beat(bar)

        # Detect section transition
        is_first_bar = (rel == 0)
        is_last_bar = (rel == int(section["bars"]) - 1)
        is_penultimate = (rel == int(section["bars"]) - 2)

        # ── Transition handling ──
        # First bar of section: simplified skeleton for smooth entrance
        if is_first_bar:
            transition_in = True
        else:
            transition_in = False

        # Last bar of section: fill bar
        is_fill = is_last_bar

        # ── Build patterns ──
        kicks = kick_pattern(groove, energy, rel, bar)
        snares = snare_pattern(groove, energy, rel, bar)
        hats = hat_pattern(groove, energy, rel, bar)

        # Transition in: simplify
        if transition_in and rel < 2:
            kicks = [k for k in kicks if k in {0.0, 2.0, 2.5}][:2]
            snares = snares[:1]

        # Fill bar: add extra activity
        if is_fill and energy >= 0.40:
            # Extra kick on last beat
            if 3.5 not in kicks:
                kicks = list(kicks) + [3.5]
            # Snare fill: 16th notes on beat 4
            if energy >= 0.65:
                for off in [3.0, 3.25, 3.50, 3.75]:
                    if off not in snares:
                        snares = list(snares) + [off]

        # ── Kick notes ──
        for off in kicks:
            vel = humanize_vel(0.36 + energy * 0.22, 0.05)
            kick_notes.append(n("C2", beat + off, 0.105, vel, pan=0.0, drum_note=36))
            # Sub kick on strong beats
            if off in {0.0, 2.0} or (energy >= 0.86 and off in {1.0, 3.0}):
                sub_vel = humanize_vel(0.30 + energy * 0.20, 0.04)
                sub_kick_notes.append(n("C1", beat + off, 0.24, sub_vel, pan=0.0, drum_note=35))

        # ── Snare notes ──
        for idx, off in enumerate(snares):
            is_fill_note = is_fill and off >= 3.0
            vel = humanize_vel(
                (0.28 + energy * 0.24) * (0.65 if is_fill_note else 1.0), 0.05
            )
            pan = -0.08 if idx % 2 else 0.08
            snare_notes.append(n("D4", beat + off, 0.105, vel, pan=pan, drum_note=38))

        # ── Ghost snare notes ──
        if energy >= 0.55 and not is_first_bar:
            ghost_offsets = []
            if groove in {"dense_roll", "blast", "full_charge", "crossfire"}:
                ghost_offsets = [0.5, 1.5, 2.5]
            elif energy >= 0.70:
                ghost_offsets = [1.5, 3.5]
            for goff in ghost_offsets:
                # Don't ghost if there's already a real snare nearby
                if any(abs(goff - s) < 0.2 for s in snares):
                    continue
                snare_notes.append(n(
                    "D4", beat + goff, 0.04,
                    humanize_vel(0.06 + energy * 0.06, 0.02),
                    pan=random.uniform(-0.12, 0.12), drum_note=38,
                ))

        # ── Hat notes ──
        for hat_idx, (off, dur, is_accent) in enumerate(hats):
            vel = humanize_vel(
                (0.14 + energy * 0.14) * (1.35 if is_accent else 1.0), 0.04
            )
            pan = -0.34 if hat_idx % 2 else 0.34
            hat_notes.append(n("F#5", beat + off, dur, vel, pan=pan, drum_note=42))

        # ── 32nd burst hats (high energy, late section) ──
        if energy >= 0.86 and groove not in {"staggered", "minimal"} and rel >= 4:
            if rel in {3, 7, 13, 17}:
                for off in [0.375, 1.375, 2.375, 3.375]:
                    hat_notes.append(n(
                        "G6", beat + off, 0.035,
                        humanize_vel(0.11 + energy * 0.12, 0.04),
                        pan=-0.22 + 0.44 * random.random(), drum_note=44,
                    ))

        # ── Ride bell on high-energy chorus sections ──
        if groove in {"full_charge", "blast"} and rel >= 4:
            if rel % 4 == 0:
                for off in [0.0]:
                    hat_notes.append(n(
                        "A5", beat + off, 0.25,
                        humanize_vel(0.20 + energy * 0.12, 0.04),
                        pan=0.0, drum_note=51,
                    ))

        prev_groove = groove

    # Merge all drum notes into drum_rock_core
    drum_rock_notes = kick_notes + snare_notes + hat_notes

    return {
        "drum_rock_core": [make_track("drum_rock_core", "noise_long", drum_rock_notes,
                                       midi_channel=9, midi_program=0)],
        "drum_sub_kick": [make_track("drum_sub_kick", "sine", sub_kick_notes,
                                      midi_channel=9, midi_program=0)],
        # Internal split for audio rendering
        "_kick": [make_track("_kick", "noise_long", kick_notes, midi_channel=9)],
        "_snare": [make_track("_snare", "noise_short", snare_notes, midi_channel=9)],
        "_hat": [make_track("_hat", "noise_short", hat_notes, midi_channel=9)],
    }


# ── MIDI export ──────────────────────────────────────────────────

def write_midi(
    path: Path, groups: dict[str, list[dict[str, Any]]],
    include_groups: set[str] | None = None,
) -> None:
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("track_name", name="thermocline_holy_war_battle_v6", time=0))
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    midi.tracks.append(meta)

    all_tracks: list[dict[str, Any]] = []
    for group, tracks in groups.items():
        if include_groups is not None and group not in include_groups:
            continue
        if group.startswith("_"):
            continue
        all_tracks.extend(tracks)

    for src in all_tracks:
        name = str(src.get("name", src.get("instrument", "track")))
        channel = int(src.get("midi_channel", 0))
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name=name, time=0))
        if channel != 9:
            track.append(mido.Message(
                "program_change",
                program=max(0, min(127, int(src.get("midi_program", MIDI_PROGRAMS.get(name, 80))))),
                channel=channel, time=0,
            ))
        events: list[tuple[int, int, mido.Message]] = []
        for item in src.get("notes", []):
            if float(item.get("v", 0.0)) <= 0:
                continue
            start = int(round(float(item["b"]) * TICKS_PER_BEAT))
            end = int(round((float(item["b"]) + float(item["d"])) * TICKS_PER_BEAT))
            if end <= start:
                continue
            if channel == 9:
                pitch = int(item.get("drum_note", DRUM_MIDI_NOTES.get(name, 36)))
            else:
                pitch = parse_note(str(item["n"]))
            velocity = max(1, min(127, int(round(float(item["v"]) * 127))))
            events.append((start, 1, mido.Message("note_on", note=pitch, velocity=velocity, channel=channel, time=0)))
            events.append((end, 0, mido.Message("note_off", note=pitch, velocity=0, channel=channel, time=0)))
        events.sort(key=lambda e: (e[0], e[1]))
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


# ── validation ───────────────────────────────────────────────────

def band_energy(audio: np.ndarray) -> dict[str, float]:
    mono = audio.mean(axis=1) if audio.ndim == 2 else audio
    total = float(np.mean(mono.astype(np.float64) ** 2))
    bands = {
        "sub_20_120_pct": (20.0, 120.0), "low_120_500_pct": (120.0, 500.0),
        "mid_500_2000_pct": (500.0, 2000.0), "high_2000_8000_pct": (2000.0, 8000.0),
        "air_8000_16000_pct": (8000.0, 16000.0),
    }
    result: dict[str, float] = {}
    for label, (lo, hi) in bands.items():
        sos = signal.butter(4, [lo / (SAMPLE_RATE / 2.0), hi / (SAMPLE_RATE / 2.0)], btype="bandpass", output="sos")
        filtered = signal.sosfilt(sos, mono).astype(np.float64)
        power = float(np.mean(filtered**2))
        result[label] = round(100.0 * power / max(total, 1e-20), 2)
    return result


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
    span_end = max(end for _, end in intervals)
    merged: list[list[float]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    union = sum(end - start for start, end in merged)
    dur_sum = sum(end - start for start, end in intervals)
    return {
        "track": str(track.get("name", "track")), "notes": len(intervals),
        "occupancy_pct": round(100.0 * union / max(span_end, 1e-9), 2),
        "avg_note_beats": round(dur_sum / len(intervals), 3),
    }


def validation_report(
    master: np.ndarray, buses: dict[str, np.ndarray],
    groups: dict[str, list[dict[str, Any]]], fx_event_counts: dict[str, int],
) -> dict[str, Any]:
    all_midi_tracks: list[dict[str, Any]] = []
    for group, tracks in groups.items():
        if group.startswith("_"):
            continue
        all_midi_tracks.extend(tracks)
    track_names = [str(t.get("name", "track")) for t in all_midi_tracks]
    peak, rms = stats(master)

    bus_stats = {
        name: {"peak": round(stats(audio)[0], 6), "rms_db": round(stats(audio)[1], 2)}
        for name, audio in buses.items()
    }
    top_rms = max((item["rms_db"] for item in bus_stats.values()), default=-100.0)

    relative_bus_balance = {
        name: {"rms_db": item["rms_db"], "relative_to_loudest_db": round(item["rms_db"] - top_rms, 2)}
        for name, item in sorted(bus_stats.items(), key=lambda p: p[1]["rms_db"], reverse=True)
    }

    occupancy_list = sorted(
        [note_occupancy(t) for t in all_midi_tracks],
        key=lambda item: float(item["occupancy_pct"]), reverse=True,
    )

    def _occ(name: str) -> float:
        for item in occupancy_list:
            if str(item.get("track", "")) == name:
                return float(item.get("occupancy_pct", 0.0))
        return 0.0

    motif_occ = _occ("bass_motif_drive")
    sustain_occ = _occ("bass_sustain_floor")
    harmony_occ = _occ("harmony_oath_pad")
    drum_occ = _occ("drum_rock_core")
    organ_occ = _occ("organ_answer_cue")
    scene_occ = _occ("scene_fx_cues")

    motif_rms = bus_stats.get("bass_motif_drive", {}).get("rms_db", -100.0)
    scene_rms = bus_stats.get("scene_fx_cues", {}).get("rms_db", -100.0)

    role_contract = {
        "bass_motif_drive": {"occupancy_pct": motif_occ, "target": "40-60%",
                            "pass": 40.0 <= motif_occ <= 60.0},
        "bass_sustain_floor": {"occupancy_pct": sustain_occ, "target": ">= 85%",
                               "pass": sustain_occ >= 85.0},
        "harmony_oath_pad": {"occupancy_pct": harmony_occ, "target": ">= 70%",
                             "pass": harmony_occ >= 70.0},
        "drum_rock_core": {"occupancy_pct": drum_occ, "target": "stable groove, not rain texture"},
        "organ_answer_cue": {"occupancy_pct": organ_occ, "target": "<= 15%",
                             "pass": organ_occ <= 15.0},
        "scene_fx_cues": {"occupancy_pct": scene_occ, "target": "<= 3%",
                          "pass": scene_occ <= 3.0,
                          "relative_to_motif_db": round(scene_rms - motif_rms, 2),
                          "relative_target": "<= -18 dB",
                          "relative_pass": (scene_rms - motif_rms) <= -18.0},
        "no_choir_samples": True,
        "no_lead_track_name": not any("lead" in n.lower() for n in track_names),
    }

    checks = [
        not bool(np.isnan(master).any()), peak <= 0.950001,
        not any("lead" in n.lower() for n in track_names),
        235.0 <= master.shape[0] / SAMPLE_RATE <= 245.0,
        sustain_occ >= 85.0, harmony_occ >= 70.0,
        40.0 <= motif_occ <= 60.0, organ_occ <= 15.0, scene_occ <= 3.0,
        (scene_rms - motif_rms) <= -18.0,
    ]

    return {
        "sample_rate": SAMPLE_RATE,
        "expected_duration_sec": round(TOTAL_BEATS * BEAT_SEC, 3),
        "master_shape": list(master.shape),
        "master_duration_sec": round(master.shape[0] / SAMPLE_RATE, 3),
        "master_has_nan": bool(np.isnan(master).any()),
        "master_peak": round(peak, 6), "master_rms_db": round(rms, 2),
        "band_energy_pct": band_energy(master),
        "sections": SECTIONS,
        "bus_stats": bus_stats,
        "relative_bus_balance": relative_bus_balance,
        "track_occupancy": occupancy_list,
        "top_15_occupancy": [item for item in occupancy_list[:15]],
        "top_15_relative_rms": [
            {"name": name, "rms_db": info["rms_db"], "relative_db": info["relative_to_loudest_db"]}
            for name, info in list(relative_bus_balance.items())[:15]
        ],
        "role_contract": role_contract,
        "ornament_event_counts": fx_event_counts,
        "track_count": len(track_names),
        "track_names": track_names,
        "pass": all(checks),
        "checks_detail": {
            "no_nan": not bool(np.isnan(master).any()),
            "peak_ok": peak <= 0.950001,
            "no_lead_name": not any("lead" in n.lower() for n in track_names),
            "duration_ok": 235.0 <= master.shape[0] / SAMPLE_RATE <= 245.0,
            "sustain_occupancy_ok": sustain_occ >= 85.0,
            "harmony_occupancy_ok": harmony_occ >= 70.0,
            "motif_occupancy_ok": 40.0 <= motif_occ <= 60.0,
            "organ_cue_ok": organ_occ <= 15.0,
            "scene_fx_ok": scene_occ <= 3.0,
            "scene_fx_relative_ok": (scene_rms - motif_rms) <= -18.0,
        },
    }


# ── score and readme ─────────────────────────────────────────────

def write_score(groups: dict[str, list[dict[str, Any]]], master_gain: float) -> None:
    tracks: list[dict[str, Any]] = []
    for gname, gtrack in groups.items():
        if gname.startswith("_"):
            continue
        tracks.extend(gtrack)
    score = {
        "title": "Thermocline holy-war battle demo v6",
        "bpm": BPM, "bars": TOTAL_BARS,
        "duration_sec": round(TOTAL_BEATS * BEAT_SEC, 3),
        "master_gain": round(master_gain, 6),
        "sections": SECTIONS,
        "theme_source": str(Path("/Users/topologyw/温跃层.md")),
        "spec": "docs/THERMOCLINE_CALL_RESPONSE_V5_SPEC.md",
        "policy": {
            "no_choir": True,
            "motif_driven": True,
            "style": "bass-motif-driven rock battle cue, no chant/choir",
            "role_model": "bass_motif_drive, bass_sustain_floor, harmony_oath_pad, drum_rock_core, drum_sub_kick, organ_answer_cue, scene_fx_cues",
            "drum_features": "natural transitions, fill bars, ghost notes, velocity humanization, evolving hat patterns",
        },
        "tracks": tracks,
    }
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    (SOURCE_DIR / "结构_score.json").write_text(
        json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_readme(validation: dict[str, Any]) -> None:
    text = f"""# thermocline_holy_war_battle_demo_v6

Four-minute Thermocline battle cue — bass-motif-driven rock battle cue.

## Direction

- v6 removes all choir/chant samples. The AMY choir sounds like horror-film
  texture, not a classical ensemble.
- `bass_motif_drive` is the main voice: driving rock bass riffs with
  call-response between registers and stereo positions.
- Drums rebuilt with section transition fills, ghost notes, velocity
  humanization, and evolving hi-hat patterns.
- `harmony_oath_pad` and `organ_answer_cue` support the bass motif.
- `scene_fx_cues` remain sparse decorative events.

## No Choir / Chant

This version uses zero choir or chant samples. All voices are epsilon-bit
synth: triangle/sine bass, fm_string harmony, fm_brass organ answers, and
noise-based drums. No horror-film high-frequency chant textures.

## Drum Improvements

- Section transitions: first bar of new section simplifies to skeleton pattern
- Fill bars: last bar of each section adds 16th-note snare activity
- Ghost snare notes between main hits for groove texture
- Velocity humanization on all drum hits
- Hi-hat density evolves with section energy
- Ride bell accents on high-energy choruses

## Listen

1. `01_thermocline_holy_war_battle_master.mp3`
2. `02_bass_harmony_only.mp3`
3. `03_drums_only.mp3`
4. `04_no_scene_fx_mix.mp3`
5. `05_scene_fx_only.mp3`
6. `stem_mp3/`

## Technical

- BPM: {BPM}
- Bars: {TOTAL_BARS}
- Duration: {validation['master_duration_sec']}s
- Master peak: {validation['master_peak']}
- Master RMS: {validation['master_rms_db']} dB
- Band energy: {validation['band_energy_pct']}
- Validation pass: {validation['pass']}
- Role contract: {json.dumps(validation.get('role_contract', {}), indent=2, ensure_ascii=False)}
"""
    (OUT_DIR / "说明.md").write_text(text, encoding="utf-8")


# ── main ─────────────────────────────────────────────────────────

def main() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STEM_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    renderer = Renderer()

    bass = build_bass_motif_system()
    harmony = build_harmony()
    organ = build_organ_answer_cue()
    drums = build_drums()
    fx_symbols, fx_event_counts = build_scene_fx_cues()
    fx_track = [make_track("scene_fx_cues", "pulse_12", fx_symbols, midi_program=81)]

    groups = {**bass, **harmony, **organ, **drums, "fx": fx_track}

    # ── Render buses ──
    kick_trigger = render_bus(renderer, drums["_kick"], volume=0.55)

    buses: dict[str, np.ndarray] = {}
    buses["bass_motif_drive"] = render_bus(renderer, bass["bass_motif"], volume=0.72) * 2.50
    buses["bass_sustain_floor"] = render_bus(renderer, bass["bass_sustain"], volume=0.42) * 1.50
    buses["harmony_oath_pad"] = render_bus(renderer, harmony["harmony"], volume=0.32) * 1.20
    buses["drum_rock_core_kick"] = render_bus(renderer, drums["_kick"], volume=0.55) * 3.00
    buses["drum_rock_core_snare"] = render_bus(renderer, drums["_snare"], volume=0.50) * 3.80
    buses["drum_rock_core_hat"] = render_bus(renderer, drums["_hat"], volume=0.40) * 2.40
    buses["drum_sub_kick"] = render_bus(renderer, drums["drum_sub_kick"], volume=0.48) * 2.60
    buses["organ_answer_cue"] = render_bus(renderer, organ["organ_answer"], volume=0.38) * 1.50
    buses["scene_fx_cues"] = render_bus(renderer, fx_track, volume=0.18) * 0.35

    # ── Post-processing ──
    buses["bass_motif_drive"] = sidechain_duck(
        butter(buses["bass_motif_drive"], "bandpass", (65.0, 2200.0)), kick_trigger, 0.06
    )
    buses["bass_sustain_floor"] = butter(buses["bass_sustain_floor"], "lowpass", 520.0)
    buses["harmony_oath_pad"] = sidechain_duck(
        butter(buses["harmony_oath_pad"], "bandpass", (260.0, 4200.0)), kick_trigger, 0.035
    )
    buses["drum_rock_core_kick"] = butter(buses["drum_rock_core_kick"], "bandpass", (55.0, 1100.0))
    buses["drum_rock_core_snare"] = add_delay(
        butter(buses["drum_rock_core_snare"], "highpass", 700.0), 0.25, 0.025, feedback=0.08
    )
    buses["drum_rock_core_hat"] = butter(buses["drum_rock_core_hat"], "highpass", 2600.0)
    buses["drum_sub_kick"] = sidechain_duck(
        butter(buses["drum_sub_kick"], "bandpass", (32.0, 180.0)),
        buses["drum_rock_core_kick"], 0.03,
    )
    buses["organ_answer_cue"] = butter(
        add_delay(buses["organ_answer_cue"], 0.25, 0.04, feedback=0.10),
        "bandpass", (220.0, 4200.0),
    )
    buses["scene_fx_cues"] = butter(
        add_delay(buses["scene_fx_cues"], 0.1875, 0.04, feedback=0.10),
        "bandpass", (400.0, 6200.0),
    )

    # ── Mix ──
    mix = mix_arrays(list(buses.values()))
    mix = butter(mix, "highpass", 30.0)
    mix = np.tanh(mix * 0.70) / np.tanh(0.70)
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    master_gain = 0.94 / peak if peak > 1e-8 else 1.0
    master = (mix * master_gain).astype(np.float32)

    # ── Submixes ──
    bass_harmony = mix_arrays([
        buses["bass_motif_drive"], buses["bass_sustain_floor"],
        buses["harmony_oath_pad"], buses["organ_answer_cue"],
    ]) * master_gain
    drums_only = mix_arrays([
        buses["drum_rock_core_kick"], buses["drum_rock_core_snare"],
        buses["drum_rock_core_hat"], buses["drum_sub_kick"],
    ]) * master_gain
    no_scene_fx = mix_arrays([
        audio for name, audio in buses.items() if name != "scene_fx_cues"
    ]) * master_gain
    scene_fx_only = buses["scene_fx_cues"] * master_gain

    # ── Output ──
    write_wav_mp3(renderer, master, OUT_DIR / "01_thermocline_holy_war_battle_master")
    write_wav_mp3(renderer, bass_harmony.astype(np.float32), OUT_DIR / "02_bass_harmony_only")
    write_wav_mp3(renderer, drums_only.astype(np.float32), OUT_DIR / "03_drums_only")
    write_wav_mp3(renderer, no_scene_fx.astype(np.float32), OUT_DIR / "04_no_scene_fx_mix")
    write_wav_mp3(renderer, scene_fx_only.astype(np.float32), OUT_DIR / "05_scene_fx_only")

    for name, audio in buses.items():
        write_mp3(renderer, (audio * master_gain).astype(np.float32), STEM_DIR / f"{name}.mp3")

    write_midi(OUT_DIR / "01_thermocline_holy_war_battle_full.mid", groups)
    write_midi(OUT_DIR / "02_bass_harmony_only.mid", groups,
               include_groups={"bass_motif", "bass_sustain", "harmony", "organ_answer"})
    write_midi(OUT_DIR / "03_drums_only.mid", groups,
               include_groups={"drum_rock_core", "drum_sub_kick"})
    write_midi(OUT_DIR / "04_no_scene_fx_mix.mid", groups,
               include_groups={"bass_motif", "bass_sustain", "harmony", "organ_answer",
                               "drum_rock_core", "drum_sub_kick"})
    write_midi(OUT_DIR / "05_scene_fx_only.mid", groups,
               include_groups={"fx"})

    write_score(groups, master_gain)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), SOURCE_DIR / Path(__file__).name)

    validation = validation_report(master, buses, groups, fx_event_counts)
    (OUT_DIR / "基础验证.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    with (OUT_DIR / "分组stem电平.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["stem", "peak_pre_master_gain", "rms_db_pre_master_gain"])
        writer.writeheader()
        for name, audio in buses.items():
            pv, rv = stats(audio)
            writer.writerow({"stem": name, "peak_pre_master_gain": round(pv, 6),
                             "rms_db_pre_master_gain": round(rv, 2)})

    write_readme(validation)

    print(OUT_DIR)
    print(f"duration={validation['master_duration_sec']}s")
    print(f"peak={validation['master_peak']}")
    print(f"rms_db={validation['master_rms_db']}")
    print(f"band_energy={validation['band_energy_pct']}")
    print(f"pass={validation['pass']}")
    print(f"checks={json.dumps(validation.get('checks_detail', {}), indent=2)}")
    print(f"role_contract={json.dumps(validation.get('role_contract', {}), indent=2, ensure_ascii=False)}")
    print(f"top_5_rms={json.dumps(validation.get('top_15_relative_rms', [])[:5], indent=2)}")
    print(OUT_DIR / "01_thermocline_holy_war_battle_master.mp3")


if __name__ == "__main__":
    main()
