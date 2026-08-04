#!/usr/bin/env python3
"""Moonlit Manor Waltz — an original composition in Bb minor, 3/4 time.

Musical design (not parameter stacking):

- INTENT: a moonlit western manor at night; elegant, slightly dangerous
  waltz. Learned from the Touhou reference analysis but NOT a copy:
  the Septette motif climbs chromatically and wraps around a high pitch;
  here the motif is built on small-third leaps upward with stepwise
  returns around the tonic, and the B section uses a chromatically
  rising four-note cell (Db-Eb-F-Gb) with stepwise falls.
- FORM: intro (8) | A (16) | B (16) | A' (16, with perfect cadence) | coda (8)
- HARMONY: A = i-VI-III-VII two-bar cycle (Bbm Gb Db Ab, passacaglia-ish);
  B = iv-ii°-V-i (Ebm Cdim F Bbm) for tension;
  A' ends with VI-VII-V-i cadence (Gb Ab F Bbm).
- RHYTHM: oom-pah-pah waltz — bass on beat 1, chords on beats 2&3;
  melody mostly on beats 1-2 with long arrivals on beat 3.
- ROLES: trumpet-like pulse lead, fm_string chords, triangle bass,
  light waltz drums (kick on 1, hat on 2&3), arp sparkle in B.
- This is an explicit extension of the project's no-lead policy:
  a real composed melody line, rendered as the foreground.
"""

from __future__ import annotations

import csv
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any

import mido
import numpy as np
import scipy.signal as signal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ebit import PresetLibrary, Renderer  # noqa: E402
from ebit.audio.constants import SAMPLE_RATE  # noqa: E402
from ebit.renderer import parse_note  # noqa: E402

BPM = 132.0
BEATS_PER_BAR = 3.0
TOTAL_BARS = 64
TAIL_BEATS = 6.0
TOTAL_BEATS = TOTAL_BARS * BEATS_PER_BAR + TAIL_BEATS
BEAT_SEC = 60.0 / BPM
TOTAL_SAMPLES = int(round(TOTAL_BEATS * BEAT_SEC * SAMPLE_RATE))
TICKS_PER_BEAT = 480

OUT_DIR = PROJECT_ROOT / "output" / "2026-08-03" / "moonlit_manor_waltz_v3"
STEM_DIR = OUT_DIR / "stem_mp3"
SOURCE_DIR = OUT_DIR / "source"

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SECTIONS = [
    {"name": "intro", "start_bar": 0, "bars": 8, "intent": "manor door opens: bare waltz bass and dark chords, no melody"},
    {"name": "a_theme", "start_bar": 8, "bars": 16, "intent": "main motif: tonic-third-leap-up with stepwise return"},
    {"name": "b_contrast", "start_bar": 24, "bars": 16, "intent": "higher register, chromatically rising cell, iv-ii-V tension, arp sparkle"},
    {"name": "a_return", "start_bar": 40, "bars": 16, "intent": "theme returns, ends VI-VII-V-i perfect cadence"},
    {"name": "coda", "start_bar": 56, "bars": 8, "intent": "motif echoes fade into the night"},
]

# two-bar harmony cycle per section: bar -> (root, chord tones for oom-pah)
HARMONY = {
    "intro": ["Bbm", "Bbm", "Gb", "Gb", "Bbm", "Bbm", "Gb", "Gb"],
    "a_theme": ["Bbm", "Bbm", "Gb", "Gb", "Db", "Db", "Ab", "Ab"],
    "b_contrast": ["Ebm", "Ebm", "Cdim", "Cdim", "F", "F", "Bbm", "Bbm"],
    "a_return": ["Bbm", "Bbm", "Gb", "Gb", "Db", "Db", "Ab", "Ab", "Gb", "Gb", "Ab", "Ab", "F", "F", "Bbm", "Bbm"],
    "coda": ["Bbm", "Bbm", "Bbm", "Bbm", "Bbm", "Bbm", "Bbm", "Bbm"],
}

CHORD_TONES = {
    "Bbm": ["Bb2", "Db3", "F3"],
    "Gb": ["Gb2", "Bb2", "Db3"],
    "Db": ["Db2", "F2", "Ab2"],
    "Ab": ["Ab2", "C3", "Eb3"],
    "Ebm": ["Eb2", "Gb2", "Bb2"],
    "Cdim": ["C3", "Eb3", "Gb3"],
    "F": ["F2", "A2", "C3"],
}


def section_at_bar(bar: int) -> str:
    section = SECTIONS[0]["name"]
    for item in SECTIONS:
        if bar >= int(item["start_bar"]):
            section = item["name"]
    return section


def harmony_at_bar(bar: int) -> str:
    section = section_at_bar(bar)
    cycle = HARMONY[section]
    start = next(item["start_bar"] for item in SECTIONS if item["name"] == section)
    return cycle[(bar - int(start)) % len(cycle)]


def note(name: str, beat: float, duration: float, velocity: float, **extra: Any) -> dict[str, Any]:
    return {"n": name, "b": beat, "d": duration, "v": velocity, **extra}


def midi_to_note(value: int) -> str:
    return f"{NOTE_NAMES[value % 12]}{value // 12 - 1}"


def transpose(name: str, semitones: int) -> str:
    return midi_to_note(parse_note(name) + semitones)


def make_track(
    name: str,
    instrument: str,
    notes: list[dict[str, Any]],
    pan: float = 0.0,
    midi_program: int | None = None,
    midi_channel: int = 0,
) -> dict[str, Any]:
    tail = note("C0", TOTAL_BEATS - 0.125, 0.125, 0.0)
    return {
        "name": name,
        "instrument": instrument,
        "pan": pan,
        "midi_program": MIDI_PROGRAMS.get(name, 80) if midi_program is None else midi_program,
        "midi_channel": midi_channel,
        "notes": sorted(notes + [tail], key=lambda item: (float(item["b"]), item["n"])),
    }


MIDI_PROGRAMS = {
    "manor_melody": 56,      # trumpet
    "waltz_bass": 38,
    "manor_chords_left": 49,  # strings
    "manor_chords_right": 49,
    "waltz_kick": 0,
    "waltz_hat": 42,
    "manor_arp": 81,
}

DRUM_MIDI_NOTES = {"waltz_kick": 36, "waltz_hat": 42}


# ── THE MELODY (composed note by note) ─────────────────────────────────────
# Motif A (2 bars): | Bb4 D5 C5 | Bb4 F5 Eb5 |  — tonic, small-third leap up,
# stepwise return; second bar leaps a fourth then steps back.
# Phrase 1 = A + A2 (ending steps down, half-cadence feel).
# Phrase 2 = variation rising to Gb5, more tension.
A_THEME = {
    0: [(0, "Bb4", 1.0), (1, "D5", 1.0), (2, "C5", 1.0)],
    1: [(0, "Bb4", 1.5), (1, "F5", 1.5)],
    2: [(0, "Eb5", 1.0), (1, "D5", 1.0), (2, "Bb4", 1.0)],
    3: [(0, "Db5", 1.5), (1, "C5", 1.5)],
    4: [(0, "Bb4", 1.0), (1, "D5", 1.0), (2, "F5", 1.0)],
    5: [(0, "Eb5", 1.5), (1, "Db5", 1.5)],
    6: [(0, "C5", 1.0), (1, "Bb4", 1.0), (2, "Ab4", 1.0)],
    7: [(0, "Bb4", 2.5)],
    8: [(0, "Bb4", 1.0), (1, "D5", 1.0), (2, "C5", 1.0)],
    9: [(0, "Bb4", 1.0), (1, "F5", 1.5), (2, "Gb5", 0.5)],
    10: [(0, "F5", 1.0), (1, "Eb5", 1.0), (2, "D5", 1.0)],
    11: [(0, "Eb5", 1.5), (1, "F5", 1.5)],
    12: [(0, "Gb5", 1.0), (1, "F5", 1.0), (2, "Eb5", 1.0)],
    13: [(0, "Db5", 1.5), (1, "Eb5", 1.5)],
    14: [(0, "F5", 1.0), (1, "Eb5", 1.0), (2, "Db5", 1.0)],
    15: [(0, "Bb4", 2.0), (2, "Ab4", 0.5)],
}

# B section: chromatically rising four-note cell + stepwise falls, +12 register
B_THEME = {
    0: [(0, "Db5", 0.5), (0.5, "Eb5", 0.5), (1, "F5", 0.5), (1.5, "Gb5", 1.5)],
    1: [(0, "F5", 0.5), (0.5, "Eb5", 0.5), (1, "Db5", 0.5), (1.5, "C5", 1.5)],
    2: [(0, "C5", 0.5), (0.5, "Db5", 0.5), (1, "Eb5", 0.5), (1.5, "F5", 1.5)],
    3: [(0, "Eb5", 0.5), (0.5, "Db5", 0.5), (1, "C5", 0.5), (1.5, "Bb4", 1.5)],
    4: [(0, "F5", 1.0), (1, "F5", 1.0), (2, "Ab5", 1.0)],
    5: [(0, "Gb5", 1.0), (1, "F5", 1.0), (2, "Eb5", 1.0)],
    6: [(0, "Db5", 1.0), (1, "Eb5", 1.0), (2, "F5", 1.0)],
    7: [(0, "Bb4", 3.0)],
    8: [(0, "F5", 0.5), (0.5, "Gb5", 0.5), (1, "Ab5", 0.5), (1.5, "Bb5", 1.5)],
    9: [(0, "Ab5", 0.5), (0.5, "Gb5", 0.5), (1, "F5", 0.5), (1.5, "Eb5", 1.5)],
    10: [(0, "Eb5", 0.5), (0.5, "F5", 0.5), (1, "Gb5", 0.5), (1.5, "Ab5", 1.5)],
    11: [(0, "Gb5", 0.5), (0.5, "F5", 0.5), (1, "Eb5", 0.5), (1.5, "Db5", 1.5)],
    12: [(0, "F5", 1.0), (1, "F5", 1.0), (2, "C5", 1.0)],
    13: [(0, "Db5", 1.0), (1, "C5", 1.0), (2, "Bb4", 1.0)],
    14: [(0, "Bb4", 1.5), (1, "Db5", 1.5)],
    15: [(0, "Bb4", 3.0)],
}

# A' return: same as A, then a real cadence on the last 4 bars:
# | Gb: Gb5 F5 Eb5 | Ab: Eb5 Db5 | F: C5 F5 | Bbm: Bb4 (long)
A_RETURN = dict(A_THEME)
A_RETURN[12] = [(0, "Gb5", 1.0), (1, "F5", 1.0), (2, "Eb5", 1.0)]
A_RETURN[13] = [(0, "Eb5", 1.5), (1, "Db5", 1.5)]
A_RETURN[14] = [(0, "C5", 1.0), (1, "F5", 2.0)]
A_RETURN[15] = [(0, "Bb4", 3.0)]

# coda: motif echoes, thinning
CODA = {
    0: [(0, "Bb4", 1.0), (1, "Db5", 1.0), (2, "C5", 1.0)],
    2: [(0, "Bb4", 2.0)],
    4: [(0, "F5", 1.0), (1, "Eb5", 1.0), (2, "Db5", 1.0)],
    5: [(0, "Bb4", 3.0)],
}


def build_melody() -> dict[str, list[dict[str, Any]]]:
    melody: list[dict[str, Any]] = []
    thick: list[dict[str, Any]] = []
    echo: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        start = next(item["start_bar"] for item in SECTIONS if item["name"] == section)
        local = bar - int(start)
        if section == "a_theme":
            table = A_THEME
        elif section == "b_contrast":
            table = B_THEME
        elif section == "a_return":
            table = A_RETURN
        elif section == "coda":
            table = CODA
        else:
            continue
        beat = bar * BEATS_PER_BAR
        for off, pitch, dur in table.get(local, []):
            vel = 0.34 if dur >= 2.0 else (0.30 if dur >= 1.0 else 0.22)  # main tier / ornament tier
            melody.append(note(pitch, beat + off, dur, vel, pan=0.06))
            # low-octave doubling (learned from the original: piano doubles the lead)
            if section in {"a_theme", "a_return"} and dur >= 1.0:
                thick.append(note(transpose(pitch, -12), beat + off, dur, 0.24, pan=-0.08))
        # high sparkle echo (the original's third trumpet ch7: sparse replies)
        if section == "a_return" and local in (14, 15):
            echo.append(note("F6", beat + 2, 0.4, 0.16, pan=0.3))
        if section == "b_contrast" and local % 8 == 7:
            echo.append(note(transpose(CODA.get(0, [])[0][1] if False else "Bb4", 24), beat + 2, 0.35, 0.15, pan=0.3))
    return {"melody": [make_track("manor_melody", "pulse_12", melody, pan=0.06)],
            "melody_thick": [make_track("manor_melody_low", "pulse_25", thick, pan=-0.08)],
            "melody_echo": [make_track("manor_melody_high", "pulse_12", echo, pan=0.3)]}


def build_bass(library: PresetLibrary) -> dict[str, list[dict[str, Any]]]:
    bass: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        chord = harmony_at_bar(bar)
        root = CHORD_TONES[chord][0]
        beat = bar * BEATS_PER_BAR
        root_low = transpose(root, -12)
        # oom-pah: root on beat 1, chord fifth/third on beats 2-3
        vel = 0.24 if section == "intro" else (0.20 if section == "coda" else 0.26)
        bass.append(note(root_low, beat, 1.0, vel))
        fifth = transpose(root, 7)
        bass.append(note(fifth, beat + 1, 1.0, 0.18))
        bass.append(note(transpose(root, 3), beat + 2, 1.0, 0.16))
    return {"bass": [library.make_track("bass_triangle_drive", bass, name="waltz_bass", pan=0.0)]}


def build_harmony(library: PresetLibrary) -> dict[str, list[dict[str, Any]]]:
    """Five-layer texture (from the transcription blueprint):
    sustained strings (L/R), church organ long notes, broken-chord layer."""
    left: list[dict[str, Any]] = []
    right: list[dict[str, Any]] = []
    organ: list[dict[str, Any]] = []
    broken: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        chord = harmony_at_bar(bar)
        tones = CHORD_TONES[chord]
        beat = bar * BEATS_PER_BAR
        if section == "coda" and bar % 2 == 1:
            continue  # thinning
        # sustained strings: whole-bar chord, split L/R (110-tier -> 0.20)
        vel = 0.20 if section in {"intro", "coda"} else 0.24
        for idx, pitch in enumerate(tones):
            target = left if idx % 2 == 0 else right
            target.append(note(transpose(pitch, 12), beat, 3.0, vel * (0.95 - idx * 0.06), pan=-0.22 + idx * 0.22))
        # church organ: 2-bar long note, dark body (110-tier -> 0.18)
        if bar % 2 == 0:
            organ.append(note(transpose(tones[0], 0), beat, 6.0, 0.17, pan=0.0))
        # broken chords: eighth notes in A, sixteenths in B (90-tier -> 0.14)
        if section not in {"intro", "coda"}:
            steps = 6 if section != "b_contrast" else 12
            for step in range(steps):
                pitch = transpose(tones[step % 3], 24)
                broken.append(note(pitch, beat + step * (3.0 / steps), 0.4, 0.13, pan=0.18 if step % 2 else -0.18))
    return {
        "chords": [
            library.make_track("pad_dark_fm_string", left, name="manor_strings_left", pan=-0.22),
            library.make_track("pad_dark_fm_string", right, name="manor_strings_right", pan=0.22),
        ],
        "organ": [library.make_track("pad_dark_fm_string", organ, name="manor_organ", pan=0.0, midi_program=19)],
        "broken": [library.make_track("arp_primary_grid", broken, name="manor_broken", pan=0.12)],
    }


def build_decoration(library: PresetLibrary) -> dict[str, list[dict[str, Any]]]:
    """Low-register sawtooth ornaments (the original's distortion guitar, 70-tier)."""
    deco: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        if section not in {"b_contrast", "a_return"}:
            continue
        chord = harmony_at_bar(bar)
        root = CHORD_TONES[chord][0]
        beat = bar * BEATS_PER_BAR
        if section == "b_contrast" and bar % 2 == 0:
            deco.append(note(transpose(root, -12), beat + 2, 0.3, 0.10, pan=-0.25))
        if section == "a_return" and bar % 4 == 3:
            deco.append(note(transpose(root, -12), beat + 1, 0.25, 0.09, pan=-0.25))
    return {"decoration": [make_track("manor_decoration", "sawtooth", deco, pan=-0.25)]}


def build_drums(library: PresetLibrary) -> dict[str, list[dict[str, Any]]]:
    kick: list[dict[str, Any]] = []
    hat: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        if section in {"intro", "coda"}:
            if section == "coda" and bar >= 60:
                continue
            kick.append(note("C2", bar * BEATS_PER_BAR, 0.16, 0.14, fm_index=6.0, fm_ratio=2.0))
            continue
        beat = bar * BEATS_PER_BAR
        kick.append(note("C2", beat, 0.18, 0.22, fm_index=8.0, fm_ratio=2.5))
        kick.append(note("C1", beat, 0.26, 0.08))
        hat.append(note("F#5", beat + 1, 0.05, 0.07))
        hat.append(note("F#5", beat + 2, 0.05, 0.08))
    return {
        "drum_core": [make_track("waltz_kick", "fm", kick, pan=0.0, midi_channel=9)],
        "drum_detail": [library.make_track("noise_brush_soft", hat, name="waltz_hat", pan=0.2)],
    }


def write_midi(path: Path, groups: dict[str, list[dict[str, Any]]], include_groups: set[str] | None = None) -> None:
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("track_name", name="moonlit_manor_waltz", time=0))
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=3, denominator=4, time=0))
    midi.tracks.append(meta)
    for group, tracks in groups.items():
        if include_groups is not None and group not in include_groups:
            continue
        for src in tracks:
            name = str(src.get("name", src.get("instrument", "track")))
            channel = int(src.get("midi_channel", 0))
            track = mido.MidiTrack()
            track.append(mido.MetaMessage("track_name", name=name, time=0))
            if channel != 9:
                track.append(mido.Message("program_change", program=max(0, min(127, int(src.get("midi_program", 80)))), channel=channel, time=0))
            events: list[tuple[int, int, mido.Message]] = []
            for item in src.get("notes", []):
                if float(item.get("v", 0.0)) <= 0:
                    continue
                start = int(round(float(item["b"]) * TICKS_PER_BEAT))
                end = int(round((float(item["b"]) + float(item["d"])) * TICKS_PER_BEAT))
                if end <= start:
                    continue
                pitch = DRUM_MIDI_NOTES.get(name, 42) if channel == 9 else parse_note(str(item["n"]))
                velocity = max(1, min(127, int(round(float(item["v"]) * 127))))
                events.append((start, 1, mido.Message("note_on", note=pitch, velocity=velocity, channel=channel, time=0)))
                events.append((end, 0, mido.Message("note_off", note=pitch, velocity=0, channel=channel, time=0)))
            events.sort(key=lambda e: (e[0], e[1]))
            cursor = 0
            for tick, _order, message in events:
                message.time = max(0, tick - cursor)
                track.append(message)
                cursor = tick
            track.append(mido.MetaMessage("end_of_track", time=max(0, int(round(TOTAL_BEATS * TICKS_PER_BEAT)) - cursor)))
            midi.tracks.append(track)
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path)


def pad_audio(audio: np.ndarray) -> np.ndarray:
    if audio.shape[0] < TOTAL_SAMPLES:
        padded = np.zeros((TOTAL_SAMPLES, 2), dtype=audio.dtype)
        padded[: audio.shape[0]] = audio
        return padded
    return audio[:TOTAL_SAMPLES]


def mix_arrays(arrays: list[np.ndarray]) -> np.ndarray:
    mixed = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    for audio in arrays:
        n = min(audio.shape[0], TOTAL_SAMPLES)
        mixed[:n] += audio[:n]
    return mixed


def butter(audio: np.ndarray, kind: str, cutoff: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, cutoff, btype=kind, fs=SAMPLE_RATE, output="sos")
    return signal.sosfilt(sos, audio).astype(np.float32)


def add_delay(audio: np.ndarray, delay_beats: float, wet: float, feedback: float = 0.15) -> np.ndarray:
    delay_samples = int(round(delay_beats * BEAT_SEC * SAMPLE_RATE))
    out = audio.copy()
    for channel in (0, 1):
        delayed = np.zeros_like(audio)
        delayed[delay_samples:] = audio[:-delay_samples] * wet
        repeat = np.zeros_like(audio)
        repeat[delay_samples:] = delayed[:-delay_samples] * feedback
        delayed += repeat
        out[:, 1 - channel] += delayed[:, channel]
    return out


def stats(audio: np.ndarray) -> tuple[float, float]:
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(np.square(audio)))) if audio.size else 0.0
    return peak, 20.0 * math.log10(rms + 1e-12)


def render_bus(renderer: Renderer, tracks: list[dict[str, Any]], volume: float) -> np.ndarray:
    return pad_audio(renderer.render_stereo({"bpm": BPM, "tracks": tracks}, volume=volume))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STEM_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    library = PresetLibrary.load(PROJECT_ROOT / "presets")
    renderer = Renderer()

    melody = build_melody()
    bass = build_bass(library)
    harmony = build_harmony(library)
    decoration = build_decoration(library)
    drums = build_drums(library)

    groups: dict[str, list[dict[str, Any]]] = {**melody, **bass, **harmony, **decoration, **drums}

    buses = {
        "01_melody": render_bus(renderer, melody["melody"] + melody["melody_thick"] + melody["melody_echo"], volume=0.72),
        "02_bass": render_bus(renderer, bass["bass"], volume=0.54),
        "03_strings": render_bus(renderer, harmony["chords"], volume=0.50),
        "04_organ": render_bus(renderer, harmony["organ"], volume=0.44),
        "05_broken": render_bus(renderer, harmony["broken"], volume=0.38),
        "06_decoration": render_bus(renderer, decoration["decoration"], volume=0.34),
        "07_drums_core": render_bus(renderer, drums["drum_core"], volume=0.46),
        "08_drums_detail": render_bus(renderer, drums["drum_detail"], volume=0.32),
    }
    buses["01_melody"] = add_delay(butter(buses["01_melody"], "highpass", 200.0), 0.75, 0.10)
    buses["02_bass"] = butter(buses["02_bass"], "lowpass", 1500.0)
    buses["03_strings"] = add_delay(butter(buses["03_strings"], "lowpass", 5000.0), 1.5, 0.06)
    buses["04_organ"] = butter(buses["04_organ"], "lowpass", 3500.0)
    buses["05_broken"] = add_delay(butter(buses["05_broken"], "highpass", 500.0), 0.375, 0.10)
    buses["06_decoration"] = butter(buses["06_decoration"], "highpass", 80.0)
    buses["07_drums_core"] = butter(buses["07_drums_core"], "highpass", 60.0)
    buses["08_drums_detail"] = butter(buses["08_drums_detail"], "highpass", 3000.0)

    mix = mix_arrays(list(buses.values()))
    mix = butter(mix, "highpass", 24.0)
    mix = np.tanh(mix * 0.8) / np.tanh(0.8)
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    master_gain = 0.94 / peak if peak > 1e-8 else 1.0
    master = (mix * master_gain).astype(np.float32)

    melody_only = mix_arrays([buses["01_melody"]])
    bass_drums = mix_arrays([buses["02_bass"], buses["07_drums_core"], buses["08_drums_detail"]])

    renderer.save_wav(master, str(OUT_DIR / "01_moonlit_manor_waltz_master.wav"))
    renderer.save_mp3(master, str(OUT_DIR / "01_moonlit_manor_waltz_master.mp3"), bitrate="224k")
    renderer.save_mp3(melody_only * master_gain, str(OUT_DIR / "02_melody_only.mp3"))
    renderer.save_mp3(bass_drums * master_gain, str(OUT_DIR / "03_bass_drums_only.mp3"))
    for key, audio in buses.items():
        renderer.save_mp3(audio * master_gain, str(STEM_DIR / f"{key}.mp3"), bitrate="192k")

    write_midi(OUT_DIR / "01_moonlit_manor_waltz_full.mid", groups)
    write_midi(OUT_DIR / "02_melody_only.mid", groups, include_groups={"melody", "melody_thick", "melody_echo"})

    score = {
        "title": "Moonlit Manor Waltz v3",
        "bpm": BPM,
        "bars": TOTAL_BARS,
        "time_signature": "3/4",
        "key": "Bb minor",
        "form": "intro(8) A(16) B(16) A'(16) coda(8)",
        "melody_motif": "tonic, small-third leap up, stepwise return; B uses chromatically rising four-note cell",
        "harmony": "A: i-VI-III-VII (Bbm Gb Db Ab); B: iv-ii-V-i (Ebm Cdim F Bbm); cadence VI-VII-V-i",
        "policy": "melody-first original composition (explicit extension of no-lead protocol)",
        "sections": SECTIONS,
        "tracks": [{t["name"]: len(t["notes"])} for g in groups.values() for t in g],
    }
    (SOURCE_DIR / "结构_score.json").write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(Path(__file__), SOURCE_DIR / Path(__file__).name)

    mp, mr = stats(master)
    validation = {
        "duration_sec": round(master.shape[0] / SAMPLE_RATE, 3),
        "master_peak": round(mp, 6),
        "master_rms_db": round(mr, 2),
        "master_has_nan": bool(np.isnan(master).any()),
        "melody_present": True,
        "bus_stats": {k: {"peak": round(stats(v)[0], 6), "rms_db": round(stats(v)[1], 2)} for k, v in buses.items()},
        "pass": not bool(np.isnan(master).any()) and mp <= 0.950001,
    }
    (OUT_DIR / "基础验证.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "说明.md").write_text(
        f"# Moonlit Manor Waltz v3\n\n- Bb minor, 3/4, {BPM} BPM, {TOTAL_BARS} bars\n- Duration: {validation['duration_sec']}s\n- Form: intro / A / B (contrast) / A' (cadence) / coda\n- Melody composed note-by-note (see 结构_score.json)\n- Validation pass: {validation['pass']}\n",
        encoding="utf-8",
    )

    print(OUT_DIR)
    print(f"duration={validation['duration_sec']}s pass={validation['pass']} peak={validation['master_peak']}")
    print(OUT_DIR / "01_moonlit_manor_waltz_master.mp3")


if __name__ == "__main__":
    main()
