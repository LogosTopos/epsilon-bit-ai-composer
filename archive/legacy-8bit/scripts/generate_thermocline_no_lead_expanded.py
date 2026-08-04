#!/usr/bin/env python3
"""No-lead expanded BGM from the successful Thermocline v1 backing track.

The goal is not to repair the failed lead-writing path.  This pass removes the
lead role entirely and turns bass, drums, harmony, arp, counter pins, and FX
into the musical foreground.
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from ebit.audio.constants import SAMPLE_RATE
from ebit.renderer import Renderer, parse_note
from generate_thermocline_v1 import (  # noqa: E402
    BEATS_PER_BAR,
    BPM,
    PAD_CHORDS,
    PROGRESSIONS,
    SECTIONS,
    TAIL_BEATS,
    TOTAL_BARS,
    TOTAL_BEATS,
    TOTAL_SAMPLES,
    add_delay,
    beat_to_sample,
    butter,
    mix_arrays,
    n,
    render_bus,
    root_at_bar,
    section_at_bar,
    sidechain_duck,
    stats,
    transpose,
    write_mp3,
    write_wav_mp3,
)

OUT_DIR = PROJECT_ROOT / "output" / "analysis" / "温跃层战斗BGM_v1_no_lead_expanded"
STEM_DIR = OUT_DIR / "stem_mp3"
SOURCE_DIR = OUT_DIR / "source"
TICKS_PER_BEAT = 480

SECTION_INTENTS_BACKING = {
    "lock_on_intro": "cold lock-on signal, sparse drums, bass identity without foreground melody",
    "teleport_chase_a": "bass riff, kick grid, and arp fragments become the foreground engine",
    "pressure_rise": "chromatic pressure from bass fills, snare rolls, alarm motor, and chord stabs",
    "full_combat_hook": "full backing combat loop: bass, drums, stabs, and dual arps carry the hook function",
    "stasis_break": "short time-stop breath with low register threat, pads, and sparse percussion",
    "final_loop_return": "return to the backing engine, then cadence back toward the opening loop",
}

MIDI_PROGRAMS = {
    "bass_sub_floor": 38,
    "bass_pulse_drive": 38,
    "bass_offbeat_answer": 39,
    "bass_fm_edge": 39,
    "bass_drop_fill": 39,
    "drum_tactical_kick": 0,
    "drum_kick_sub": 0,
    "drum_snare_noise": 0,
    "drum_snap_clap": 0,
    "drum_ghost_snare": 0,
    "drum_hat_needle": 0,
    "drum_hat_wide": 0,
    "drum_ride_noise": 0,
    "drum_shell_ticks": 0,
    "drum_tom_fill": 0,
    "harm_chord_stabs": 81,
    "harm_low_pad": 49,
    "harm_high_shimmer": 88,
    "arp_primary_grid": 81,
    "arp_cross_sync": 80,
    "counter_pins": 80,
    "alarm_motor": 87,
    "fx_teleport_chirp": 97,
    "fx_low_impact": 97,
    "fx_stasis_sweep": 97,
}

DRUM_MIDI_NOTES = {
    "drum_tactical_kick": 36,
    "drum_kick_sub": 35,
    "drum_snare_noise": 38,
    "drum_snap_clap": 39,
    "drum_ghost_snare": 37,
    "drum_hat_needle": 42,
    "drum_hat_wide": 46,
    "drum_ride_noise": 51,
    "drum_shell_ticks": 75,
    "drum_tom_fill": 45,
}


def t(
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
        "midi_program": MIDI_PROGRAMS.get(name, 80) if midi_program is None else midi_program,
        "midi_channel": midi_channel,
        "notes": sorted(notes + [n("C0", TOTAL_BEATS - 0.125, 0.125, 0.0)], key=lambda item: (float(item["b"]), item["n"])),
    }


def section_start(name: str) -> int:
    return next(item["start_bar"] for item in SECTIONS if item["name"] == name)


def chord_at_bar(bar: int) -> list[str]:
    return PAD_CHORDS[root_at_bar(bar)]


def add_bass_pattern(notes: list[dict[str, Any]], root: str, beat: float, offsets: list[float], section: str) -> None:
    for off in offsets:
        accent = off in {0.0, 2.0}
        velocity = 0.58 if accent else 0.43
        if section in {"pressure_rise", "full_combat_hook", "final_loop_return"}:
            velocity *= 1.08
        notes.append(n(root, beat + off, 0.30, velocity))


def build_bass_groups() -> dict[str, list[dict[str, Any]]]:
    sub: list[dict[str, Any]] = []
    drive: list[dict[str, Any]] = []
    answer: list[dict[str, Any]] = []
    edge: list[dict[str, Any]] = []
    drops: list[dict[str, Any]] = []

    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        root = root_at_bar(bar)
        beat = bar * BEATS_PER_BAR
        rel = bar - section_start(section)

        sub_vel = 0.30
        if section in {"full_combat_hook", "final_loop_return"}:
            sub_vel = 0.34
        elif section == "stasis_break":
            sub_vel = 0.24
        sub.append(n(transpose(root, -12), beat, 3.82, sub_vel))

        if section == "lock_on_intro":
            offsets = [0.0] if bar < 4 else [0.0, 1.5, 2.5, 3.25]
        elif section == "stasis_break":
            offsets = [0.0, 2.5] if rel % 4 in {0, 3} else [0.0, 1.75, 3.0]
        elif section == "pressure_rise":
            offsets = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
        elif section in {"full_combat_hook", "final_loop_return"}:
            offsets = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
        else:
            offsets = [0.0, 0.75, 1.5, 2.0, 2.75, 3.25]
        add_bass_pattern(drive, root, beat, offsets, section)

        if section in {"teleport_chase_a", "pressure_rise", "full_combat_hook", "final_loop_return"}:
            fifth = transpose(root, 7)
            octave = transpose(root, 12)
            for off, pitch, vel in [(0.25, octave, 0.24), (1.25, fifth, 0.22), (2.25, octave, 0.25), (3.25, fifth, 0.23)]:
                if section == "teleport_chase_a" and rel % 4 == 0 and off in {1.25, 3.25}:
                    continue
                answer.append(n(pitch, beat + off, 0.16, vel, fx={"retrigger": 2}))

        if section in {"pressure_rise", "full_combat_hook", "final_loop_return"}:
            for off in [0.375, 1.875, 2.875]:
                edge.append(n(transpose(root, 12), beat + off, 0.12, 0.23, fx={"retrigger": 2}))
        if bar % 8 == 7 and section != "lock_on_intro":
            drops.append(n(transpose(root, 12), beat + 3.00, 0.70, 0.28, fx={"slide_to": transpose(root, -12)}))
            drops.append(n(transpose(root, -12), beat + 3.75, 0.25, 0.26))

    return {
        "bass_sub": [t("bass_sub_floor", "sine", sub, pan=0.0, midi_program=38)],
        "bass_drive": [t("bass_pulse_drive", "triangle", drive, pan=0.0, midi_program=38)],
        "bass_answer": [t("bass_offbeat_answer", "pulse_25", answer, pan=-0.05, midi_program=39)],
        "bass_edge": [
            t("bass_fm_edge", "fm_bass", edge, pan=0.05, midi_program=39),
            t("bass_drop_fill", "sawtooth", drops, pan=-0.08, midi_program=39),
        ],
    }


def build_drum_groups() -> dict[str, list[dict[str, Any]]]:
    kick: list[dict[str, Any]] = []
    kick_sub: list[dict[str, Any]] = []
    snare: list[dict[str, Any]] = []
    clap: list[dict[str, Any]] = []
    ghost: list[dict[str, Any]] = []
    hat: list[dict[str, Any]] = []
    hat_wide: list[dict[str, Any]] = []
    ride: list[dict[str, Any]] = []
    shell: list[dict[str, Any]] = []
    tom: list[dict[str, Any]] = []

    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        beat = bar * BEATS_PER_BAR
        rel = bar - section_start(section)

        if section == "lock_on_intro":
            kick_hits = [0.0] if bar < 4 else [0.0, 2.5]
            snare_hits = [] if bar < 4 else [3.0]
            hat_grid = [0.0, 1.0, 2.0, 3.0] if bar < 4 else [i * 0.5 for i in range(8)]
        elif section == "stasis_break":
            kick_hits = [0.0] if rel % 4 in {0, 3} else [0.0, 3.0]
            snare_hits = [3.0] if rel % 2 else []
            hat_grid = [0.5, 1.5, 2.5, 3.5]
        elif section == "pressure_rise":
            kick_hits = [0.0, 1.5, 2.5, 3.25]
            snare_hits = [1.0, 3.0]
            hat_grid = [i * 0.25 for i in range(16)]
        elif section in {"full_combat_hook", "final_loop_return"}:
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
            main_vel = 0.94 if off in {0.0, 2.0} else 0.70
            kick.append(n("C2", beat + off, 0.15, main_vel, fm_index=7.6, fm_ratio=3.2))
            kick_sub.append(n("C1", beat + off, 0.24, 0.36))

        for off in snare_hits:
            snare.append(n("D3", beat + off, 0.16, 0.68))
            clap.append(n("D4", beat + off + 0.012, 0.08, 0.25, fx={"retrigger": 2}))
            if section in {"teleport_chase_a", "pressure_rise", "full_combat_hook", "final_loop_return"}:
                ghost.append(n("D3", beat + off - 0.25, 0.055, 0.17))

        if bar % 8 == 7 and section != "lock_on_intro":
            snare.append(n("D3", beat + 3.0, 0.88, 0.46, fx={"retrigger": 8, "tremolo": [11.0, 0.16]}))
            tom.append(n("G2", beat + 2.50, 0.12, 0.22, fx={"slide_to": "C2"}))
            tom.append(n("D2", beat + 3.50, 0.12, 0.24, fx={"slide_to": "G1"}))

        for off in hat_grid:
            accent = 0.28 if abs(off % 1.0) < 1e-6 else 0.16
            if section in {"pressure_rise", "full_combat_hook", "final_loop_return"}:
                accent *= 1.18
            hat.append(n("F#5", beat + off, 0.045, accent))
            if section in {"full_combat_hook", "final_loop_return"} and int(off * 4) % 4 == 2:
                hat_wide.append(n("F#5", beat + off, 0.075, accent * 0.50))
            if section in {"full_combat_hook", "final_loop_return"} and abs((off * 4) % 4) < 1e-6:
                ride.append(n("A5", beat + off + 0.02, 0.10, 0.09))

        if section in {"teleport_chase_a", "pressure_rise", "full_combat_hook", "final_loop_return"}:
            for off in [0.75, 2.75]:
                shell.append(n("C6", beat + off, 0.05, 0.17))
            if rel % 4 == 2:
                shell.append(n("G5", beat + 3.5, 0.08, 0.24, fx={"retrigger": 3}))

    return {
        "drum_core": [
            t("drum_tactical_kick", "fm", kick, pan=0.0, midi_channel=9),
            t("drum_kick_sub", "sine", kick_sub, pan=0.0, midi_channel=9),
            t("drum_snare_noise", "noise_short", snare, pan=0.02, midi_channel=9),
            t("drum_snap_clap", "noise_periodic", clap, pan=0.06, midi_channel=9),
        ],
        "drum_detail": [
            t("drum_ghost_snare", "noise_short", ghost, pan=-0.04, midi_channel=9),
            t("drum_hat_needle", "noise_short", hat, pan=0.23, midi_channel=9),
            t("drum_hat_wide", "noise_long", hat_wide, pan=-0.24, midi_channel=9),
            t("drum_ride_noise", "noise_long", ride, pan=0.12, midi_channel=9),
            t("drum_shell_ticks", "pulse_12", shell, pan=-0.16, midi_channel=9),
            t("drum_tom_fill", "fm_bass", tom, pan=-0.08, midi_channel=9),
        ],
    }


def build_harmony_arp_groups() -> dict[str, list[dict[str, Any]]]:
    stabs: list[dict[str, Any]] = []
    low_pad: list[dict[str, Any]] = []
    high_shimmer: list[dict[str, Any]] = []
    arp_primary: list[dict[str, Any]] = []
    arp_cross: list[dict[str, Any]] = []
    counter: list[dict[str, Any]] = []
    alarm: list[dict[str, Any]] = []

    for bar in range(0, TOTAL_BARS, 2):
        section = section_at_bar(bar)
        chord = chord_at_bar(bar)
        beat = bar * BEATS_PER_BAR

        pad_velocity = 0.11 if section in {"lock_on_intro", "stasis_break"} else 0.09
        for idx, pitch in enumerate(chord):
            pan = -0.30 + idx * 0.20
            low_pad.append(
                n(
                    pitch,
                    beat,
                    7.72,
                    pad_velocity,
                    fx={"vib": [3.0 + idx * 0.18, 4.6], "tremolo": [2.2, 0.10]},
                    pan=pan,
                )
            )
            if section in {"pressure_rise", "full_combat_hook", "final_loop_return"}:
                high_shimmer.append(
                    n(
                        transpose(pitch, 12),
                        beat + 0.02,
                        7.55,
                        pad_velocity * 0.55,
                        fx={"vib": [4.3, 6.5], "tremolo": [3.0, 0.08]},
                        pan=-pan,
                    )
                )

        if section in {"teleport_chase_a", "pressure_rise", "full_combat_hook", "final_loop_return"}:
            for off in [0.0, 1.5, 2.0, 3.5, 4.0, 5.5, 6.0, 7.5]:
                for idx, pitch in enumerate(chord[:3]):
                    stabs.append(n(transpose(pitch, 12), beat + off + idx * 0.012, 0.24, 0.22 - idx * 0.025, pan=-0.12 + idx * 0.12))

        if section in {"teleport_chase_a", "pressure_rise", "full_combat_hook", "final_loop_return"}:
            pattern = [transpose(chord[0], 12), transpose(chord[2], 12), transpose(chord[1], 12), transpose(chord[3], 12)]
            density = 32 if section in {"pressure_rise", "full_combat_hook", "final_loop_return"} else 16
            step = 0.25 if density == 32 else 0.5
            for idx in range(density):
                if section == "teleport_chase_a" and idx % 4 == 3:
                    continue
                arp_primary.append(n(pattern[idx % len(pattern)], beat + idx * step, 0.115, 0.32 if idx % 4 else 0.42))
            if section in {"full_combat_hook", "final_loop_return"}:
                cross_pattern = [transpose(chord[3], 12), transpose(chord[1], 12), transpose(chord[2], 12), transpose(chord[0], 12)]
                for idx in range(16):
                    off = 0.125 + idx * 0.5
                    arp_cross.append(n(cross_pattern[idx % len(cross_pattern)], beat + off, 0.09, 0.105 if idx % 2 else 0.14))

        if section in {"pressure_rise", "stasis_break", "final_loop_return"}:
            alarm.append(n(chord[0], beat, 0.75, 0.17, fx={"arp": [0, 3, 6, 10]}))
            alarm.append(n(chord[1], beat + 4.0, 0.75, 0.15, fx={"arp": [0, 2, 7, 9]}))

    for start in [64.0, 96.0, 144.0, 224.0, 256.0]:
        for off, pitch in [
            (1.75, "E5"),
            (2.25, "G#5"),
            (2.75, "A5"),
            (5.75, "B5"),
            (6.25, "C#6"),
        ]:
            counter.append(n(pitch, start + off, 0.18, 0.12, fx={"vib": [5.0, 2.0]}))

    return {
        "harmony_stabs": [t("harm_chord_stabs", "pulse_25", stabs, pan=0.0, midi_program=81)],
        "harmony_pads": [
            t("harm_low_pad", "sine", low_pad, pan=0.0, midi_program=49),
            t("harm_high_shimmer", "wavetable", high_shimmer, pan=0.0, midi_program=88),
        ],
        "arp_primary": [t("arp_primary_grid", "pulse_12", arp_primary, pan=0.18, midi_program=81)],
        "arp_secondary": [
            t("arp_cross_sync", "pulse_12", arp_cross, pan=-0.20, midi_program=80),
            t("counter_pins", "sine", counter, pan=-0.12, midi_program=80),
            t("alarm_motor", "pulse_12", alarm, pan=-0.25, midi_program=87),
        ],
    }


def build_fx_groups() -> dict[str, list[dict[str, Any]]]:
    chirp: list[dict[str, Any]] = []
    impact: list[dict[str, Any]] = []
    sweep: list[dict[str, Any]] = []
    for bar in [8, 24, 32, 48, 56, 72]:
        beat = bar * BEATS_PER_BAR
        if bar < TOTAL_BARS:
            chirp.append(n("G#6", beat - 0.50, 0.18, 0.24, fx={"slide_to": "C#7", "retrigger": 3}))
            impact.append(n("C2", beat, 0.28, 0.27, fm_index=8.0, fm_ratio=4.0))
            impact.append(n("C1", beat + 0.02, 0.34, 0.20))
    for bar in range(12, TOTAL_BARS, 8):
        beat = bar * BEATS_PER_BAR + 3.0
        chirp.append(n("E6", beat, 0.16, 0.16, fx={"slide_to": "B6"}))
    for bar in [28, 44, 50, 52, 60]:
        beat = bar * BEATS_PER_BAR
        sweep.append(n("C#4", beat + 2.0, 1.20, 0.18, fx={"vib": [8.0, 28]}))
        impact.append(n("G#1", beat + 2.0, 0.42, 0.17, fx={"slide_to": "C#1"}))
    return {
        "fx": [
            t("fx_teleport_chirp", "pulse_12", chirp, pan=0.26, midi_program=97),
            t("fx_low_impact", "fm", impact, pan=0.0, midi_program=97),
            t("fx_stasis_sweep", "fm", sweep, pan=-0.18, midi_program=97),
        ]
    }


def master_from_buses(buses: dict[str, np.ndarray]) -> tuple[np.ndarray, float]:
    mix = mix_arrays(list(buses.values()))
    mix = butter(mix, "highpass", 24.0)
    mix = np.tanh(mix * 0.94) / np.tanh(0.94)
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    gain = 0.94 / peak if peak > 1e-8 else 1.0
    return (mix * gain).astype(np.float32), gain


def write_midi(path: Path, track_groups: dict[str, list[dict[str, Any]]], include_groups: set[str] | None = None) -> None:
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("track_name", name="thermocline_backing_expanded_meta", time=0))
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    midi.tracks.append(meta)

    for group_name, tracks in track_groups.items():
        if include_groups is not None and group_name not in include_groups:
            continue
        for source in tracks:
            name = str(source.get("name", source.get("instrument", "track")))
            channel = int(source.get("midi_channel", 0))
            mtrack = mido.MidiTrack()
            mtrack.append(mido.MetaMessage("track_name", name=name, time=0))
            if channel != 9:
                program = int(source.get("midi_program", 80))
                mtrack.append(mido.Message("program_change", program=max(0, min(127, program)), channel=channel, time=0))
            events: list[tuple[int, int, mido.Message]] = []
            for item in source.get("notes", []):
                if float(item.get("v", 0.0)) <= 0.0:
                    continue
                start = int(round(float(item["b"]) * TICKS_PER_BEAT))
                end = int(round((float(item["b"]) + float(item["d"])) * TICKS_PER_BEAT))
                if end <= start:
                    continue
                pitch = DRUM_MIDI_NOTES.get(name, 42) if channel == 9 else parse_note(str(item["n"]))
                velocity = max(1, min(127, int(round(float(item["v"]) * 127))))
                events.append((start, 1, mido.Message("note_on", note=pitch, velocity=velocity, channel=channel, time=0)))
                events.append((end, 0, mido.Message("note_off", note=pitch, velocity=0, channel=channel, time=0)))
            events.sort(key=lambda event: (event[0], event[1]))
            cursor = 0
            for tick, _order, msg in events:
                msg.time = max(0, tick - cursor)
                mtrack.append(msg)
                cursor = tick
            final_tick = int(round(TOTAL_BEATS * TICKS_PER_BEAT))
            mtrack.append(mido.MetaMessage("end_of_track", time=max(0, final_tick - cursor)))
            midi.tracks.append(mtrack)
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path)


def validate_audio(master: np.ndarray, buses: dict[str, np.ndarray], aux: dict[str, np.ndarray], track_groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    bus_stats = {
        name: {
            "peak": round(stats(audio)[0], 6),
            "rms_db": round(stats(audio)[1], 2),
        }
        for name, audio in buses.items()
    }
    bass_combined = mix_arrays([buses["01_bass_sub"], buses["02_bass_drive"], buses["03_bass_upper_motion"]])
    drum_combined = mix_arrays([buses["04_drums_core"], buses["05_drums_detail"]])
    harmony_arp_combined = mix_arrays(
        [
            buses["06_harmony_stabs"],
            buses["07_harmony_pads"],
            buses["08_arp_primary"],
            buses["09_arp_secondary_counter"],
        ]
    )
    all_names = [track["name"] for tracks in track_groups.values() for track in tracks]
    return {
        "sample_rate": SAMPLE_RATE,
        "expected_duration_sec": round(TOTAL_SAMPLES / SAMPLE_RATE, 3),
        "master_shape": list(master.shape),
        "master_duration_sec": round(len(master) / SAMPLE_RATE, 3),
        "master_has_nan": bool(np.isnan(master).any()),
        "master_peak": round(stats(master)[0], 6),
        "master_rms_db": round(stats(master)[1], 2),
        "bass_drums_only_rms_db": round(stats(aux["bass_drums_only"])[1], 2),
        "harmony_arps_only_rms_db": round(stats(aux["harmony_arps_only"])[1], 2),
        "no_fx_rms_db": round(stats(aux["no_fx"])[1], 2),
        "bass_combined_rms_db": round(stats(bass_combined)[1], 2),
        "drum_combined_rms_db": round(stats(drum_combined)[1], 2),
        "harmony_arp_combined_rms_db": round(stats(harmony_arp_combined)[1], 2),
        "no_lead_policy": {
            "no_track_name_contains_lead": not any("lead" in name.lower() for name in all_names),
            "track_count": len(all_names),
            "foreground_roles": ["bass riff", "drum fills", "chord stabs", "dual arps", "counter pins", "transition fx"],
        },
        "reference_v1_comparison": {
            "v1_bass_rms_db": -21.6,
            "v1_drums_rms_db": -21.98,
            "v1_harmony_arp_rms_db": -29.42,
            "target": "bass/drums are the main engine; harmony/arps are audible without introducing lead",
        },
        "bus_stats": bus_stats,
        "pass": (
            not bool(np.isnan(master).any())
            and 0.20 <= stats(master)[0] <= 0.96
            and stats(master)[1] > -30.0
            and stats(bass_combined)[1] > -18.5
            and stats(drum_combined)[1] > -19.5
            and stats(harmony_arp_combined)[1] > -22.5
            and not any("lead" in name.lower() for name in all_names)
        ),
    }


def build_score(track_groups: dict[str, list[dict[str, Any]]], validation: dict[str, Any]) -> dict[str, Any]:
    summaries = []
    for group, tracks in track_groups.items():
        for item in tracks:
            real_notes = [note for note in item["notes"] if float(note.get("v", 0.0)) > 0.0]
            summaries.append(
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
        "title": "温跃层战斗BGM_v1_no_lead_expanded",
        "generation_scope": "Expansion of the successful v1 backing-track idea without a foreground melody bus.",
        "ai_generated_notice": "This output is AI generated; user listening judgment overrides this report.",
        "source_reference": "examples/thermocline_v1_reconsidered",
        "bpm": BPM,
        "bars": TOTAL_BARS,
        "tail_beats": TAIL_BEATS,
        "duration_sec": round(TOTAL_SAMPLES / SAMPLE_RATE, 3),
        "tonal_center": "C# minor",
        "sections": [
            {**item, "intent": SECTION_INTENTS_BACKING.get(item["name"], item["intent"])}
            for item in SECTIONS
        ],
        "progressions": PROGRESSIONS,
        "design_rules": [
            "No foreground melody bus and no single replacement melody line.",
            "Bass is raised and split into sub, drive, offbeat answer, and edge/fill layers.",
            "Drums are split into core and detail buses with fills and ghost hits.",
            "Harmony/arps are expanded into pads, chord stabs, primary arp, secondary arp, counter pins, and alarm motor.",
            "The arrangement keeps space for later extra bass fills, drum fills, ornaments, and interactive game cues.",
        ],
        "validation": validation,
        "track_summaries": summaries,
        "track_groups": track_groups,
        "track_name_counts": Counter(item["name"] for item in summaries),
    }


def write_docs(score: dict[str, Any], validation: dict[str, Any], master_gain: float) -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    (SOURCE_DIR / "结构_score.json").write_text(json.dumps(score, ensure_ascii=False, indent=2, default=dict) + "\n", encoding="utf-8")
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
        f"- {item['name']}: bars {item['start_bar']}-{item['start_bar'] + item['bars']}, "
        f"{SECTION_INTENTS_BACKING.get(item['name'], item['intent'])}"
        for item in SECTIONS
    ]
    readme = f"""# 温跃层战斗BGM_v1_no_lead_expanded

本目录为 AI 生成，基于 `温跃层战斗BGM_v1_重新构思` 的非 lead 成功方向继续扩写；原始 v1 目录未被覆盖。

## 核心决策

- 不修主旋律，不新增主旋律，不用另一条主旋律替代旧主旋律。
- 直接把 v1 去 lead 伴奏扩写成完整 BGM 草案。
- Bass 提升为主引擎，并拆成 sub / drive / offbeat answer / edge fill。
- Drums 拆成 core / detail，增加 ghost snare、tom fill、ride noise、shell tick。
- 和声与 arp 拆成 stabs / pads / primary arp / secondary arp / counter pins / alarm motor。
- FX 保持克制，给后续游戏事件和手工修饰留空间。

## 听音顺序

1. `01_温跃层_no_lead_expanded_master.mp3`
2. `02_bass_drums_only.mp3`
3. `03_harmony_arps_only.mp3`
4. `04_no_fx_mix.mp3`
5. `stem_mp3/`

## 结构

{chr(10).join(section_lines)}

## 技术信息

- BPM: {BPM}
- Bars: {TOTAL_BARS}
- Duration: {TOTAL_SAMPLES / SAMPLE_RATE:.2f}s
- Master gain: {master_gain:.6f}
- Validation pass: {validation['pass']}
- Master peak: {validation['master_peak']}
- Master RMS: {validation['master_rms_db']} dB
- Bass combined RMS: {validation['bass_combined_rms_db']} dB
- Drum combined RMS: {validation['drum_combined_rms_db']} dB
- Harmony/arp combined RMS: {validation['harmony_arp_combined_rms_db']} dB
- No foreground melody bus policy: {validation['no_lead_policy']['no_track_name_contains_lead']}
"""
    (OUT_DIR / "说明.md").write_text(readme, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STEM_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    renderer = Renderer()

    bass_groups = build_bass_groups()
    drum_groups = build_drum_groups()
    harmony_groups = build_harmony_arp_groups()
    fx_groups = build_fx_groups()

    track_groups = {
        "bass_sub": bass_groups["bass_sub"],
        "bass_drive": bass_groups["bass_drive"],
        "bass_answer": bass_groups["bass_answer"],
        "bass_edge": bass_groups["bass_edge"],
        "drum_core": drum_groups["drum_core"],
        "drum_detail": drum_groups["drum_detail"],
        "harmony_stabs": harmony_groups["harmony_stabs"],
        "harmony_pads": harmony_groups["harmony_pads"],
        "arp_primary": harmony_groups["arp_primary"],
        "arp_secondary": harmony_groups["arp_secondary"],
        "fx": fx_groups["fx"],
    }

    kick_trigger = render_bus(renderer, drum_groups["drum_core"][:2], volume=0.74)
    buses: dict[str, np.ndarray] = {
        "01_bass_sub": render_bus(renderer, bass_groups["bass_sub"], volume=0.76) * 1.34,
        "02_bass_drive": render_bus(renderer, bass_groups["bass_drive"], volume=0.76) * 1.34,
        "03_bass_upper_motion": render_bus(renderer, bass_groups["bass_answer"] + bass_groups["bass_edge"], volume=0.72) * 1.75,
        "04_drums_core": render_bus(renderer, drum_groups["drum_core"], volume=0.74) * 1.18,
        "05_drums_detail": render_bus(renderer, drum_groups["drum_detail"], volume=0.68) * 1.35,
        "06_harmony_stabs": render_bus(renderer, harmony_groups["harmony_stabs"], volume=0.70) * 1.55,
        "07_harmony_pads": render_bus(renderer, harmony_groups["harmony_pads"], volume=0.60) * 0.98,
        "08_arp_primary": render_bus(renderer, harmony_groups["arp_primary"], volume=0.72) * 2.20,
        "09_arp_secondary_counter": render_bus(renderer, harmony_groups["arp_secondary"], volume=0.42) * 0.42,
        "10_fx_space": render_bus(renderer, fx_groups["fx"], volume=0.48) * 0.72,
    }

    buses["01_bass_sub"] = butter(sidechain_duck(buses["01_bass_sub"], kick_trigger, 0.07), "lowpass", 2600.0)
    buses["02_bass_drive"] = butter(sidechain_duck(buses["02_bass_drive"], kick_trigger, 0.08), "lowpass", 5200.0)
    buses["03_bass_upper_motion"] = butter(sidechain_duck(buses["03_bass_upper_motion"], kick_trigger, 0.06), "highpass", 90.0)
    buses["06_harmony_stabs"] = butter(sidechain_duck(buses["06_harmony_stabs"], kick_trigger, 0.11), "lowpass", 6800.0)
    buses["07_harmony_pads"] = butter(sidechain_duck(buses["07_harmony_pads"], kick_trigger, 0.14), "lowpass", 5200.0)
    buses["08_arp_primary"] = add_delay(butter(sidechain_duck(buses["08_arp_primary"], kick_trigger, 0.08), "highpass", 160.0), 0.25, 0.025)
    buses["09_arp_secondary_counter"] = add_delay(butter(buses["09_arp_secondary_counter"], "highpass", 260.0), 0.375, 0.018)
    buses["10_fx_space"] = add_delay(butter(buses["10_fx_space"], "highpass", 120.0), 0.25, 0.055)

    master, master_gain = master_from_buses(buses)
    bass_drums_only, _ = master_from_buses({key: value for key, value in buses.items() if key.startswith(("01_", "02_", "03_", "04_", "05_"))})
    harmony_arps_only, _ = master_from_buses({key: value for key, value in buses.items() if key.startswith(("06_", "07_", "08_", "09_"))})
    no_fx, _ = master_from_buses({key: value for key, value in buses.items() if key != "10_fx_space"})

    write_wav_mp3(renderer, master, OUT_DIR / "01_温跃层_no_lead_expanded_master")
    write_wav_mp3(renderer, bass_drums_only, OUT_DIR / "02_bass_drums_only")
    write_wav_mp3(renderer, harmony_arps_only, OUT_DIR / "03_harmony_arps_only")
    write_wav_mp3(renderer, no_fx, OUT_DIR / "04_no_fx_mix")

    for name, audio in buses.items():
        write_mp3(renderer, audio * master_gain, STEM_DIR / name)

    write_midi(OUT_DIR / "01_温跃层_no_lead_expanded_full.mid", track_groups)
    write_midi(OUT_DIR / "02_bass_drums_only.mid", track_groups, include_groups={"bass_sub", "bass_drive", "bass_answer", "bass_edge", "drum_core", "drum_detail"})
    write_midi(OUT_DIR / "03_harmony_arps_only.mid", track_groups, include_groups={"harmony_stabs", "harmony_pads", "arp_primary", "arp_secondary"})

    aux = {
        "bass_drums_only": bass_drums_only,
        "harmony_arps_only": harmony_arps_only,
        "no_fx": no_fx,
    }
    validation = validate_audio(master, buses, aux, track_groups)
    score = build_score(track_groups, validation)
    write_docs(score, validation, master_gain)

    shutil.copy2(Path(__file__), SOURCE_DIR / Path(__file__).name)
    shutil.copy2(
        PROJECT_ROOT / "scripts" / "generate_thermocline_v1.py",
        SOURCE_DIR / "source_reference_generate_thermocline_v1.py",
    )

    print(OUT_DIR)
    print(f"duration={len(master) / SAMPLE_RATE:.2f}s")
    print(f"master_gain={master_gain:.6f}")
    print(f"validation_pass={validation['pass']}")
    print(OUT_DIR / "01_温跃层_no_lead_expanded_master.mp3")


if __name__ == "__main__":
    main()
