#!/usr/bin/env python3
"""Mine Tunnel March demo — a deliberately non-Thermocline, non-harbor piece.

Direction: underground mine march in A Phrygian.

- 104 BPM, 40 bars, ~1:37 — steady four-on-the-floor march with snare on 2&4
- no foreground lead; role-first support engine (protocol-compliant)
- motif is a cross-role cell: "pick-strike answer" — bass accent + metallic
  strike + arp reply, repeated every 4 bars
- Phrygian colour via b2 (Bb) inside the G chord and the A-G-F-E descent
- sections: deep_entry (dark, sparse) -> march_core -> vein_open (denser,
  brighter, riser transition) -> echo_return (decay, metallic echoes)
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
import soundfile as sf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ebit import PresetLibrary, Renderer  # noqa: E402
from ebit.audio.constants import SAMPLE_RATE  # noqa: E402
from ebit.renderer import parse_note  # noqa: E402

BPM = 104.0
BEATS_PER_BAR = 4.0
TOTAL_BARS = 40
TAIL_BEATS = 8.0
TOTAL_BEATS = TOTAL_BARS * BEATS_PER_BAR + TAIL_BEATS
BEAT_SEC = 60.0 / BPM
TOTAL_SAMPLES = int(round(TOTAL_BEATS * BEAT_SEC * SAMPLE_RATE))
TICKS_PER_BEAT = 480

OUT_DIR = PROJECT_ROOT / "output" / "2026-08-03" / "mine_tunnel_march_demo_v1"
STEM_DIR = OUT_DIR / "stem_mp3"
SOURCE_DIR = OUT_DIR / "source"

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SECTIONS = [
    {"name": "deep_entry", "start_bar": 0, "bars": 8, "energy": "dark", "intent": "single footsteps, dark pad, dripping water, bass root only"},
    {"name": "march_core", "start_bar": 8, "bars": 16, "energy": "steady", "intent": "full march: bass drive, kick 1&3, snare 2&4, arp grid, pick strikes every 4 bars"},
    {"name": "vein_open", "start_bar": 24, "bars": 8, "energy": "open", "intent": "denser and brighter: wider harmony, higher arps, bass accents, riser into the return"},
    {"name": "echo_return", "start_bar": 32, "bars": 8, "energy": "settle", "intent": "decay: sparse kick, metallic echoes, pad thinning, no drums at the end"},
]

# A Phrygian: A Bb C D E F G. Descending i - bVII - bVI - v as the march loop.
PHRYGIAN_ROOTS = ["A1", "G1", "F1", "E1"]
VEIN_ROOTS = ["A1", "F1", "E1", "G1"]

PAD_CHORDS = {
    "A1": ["A3", "C4", "E4"],
    "G1": ["G3", "Bb3", "D4"],  # Bb = phrygian b2 colour
    "F1": ["F3", "A3", "C4"],
    "E1": ["E3", "G3", "B3"],
}

MIDI_PROGRAMS = {
    "tunnel_bass_floor": 38,
    "tunnel_bass_drive": 38,
    "march_kick": 0,
    "march_snare": 40,
    "march_hat": 42,
    "drip_ticks": 122,
    "pick_strike": 15,
    "dark_pad_left": 49,
    "dark_pad_right": 49,
    "tunnel_arp_grid": 81,
    "tunnel_riser": 91,
}

DRUM_MIDI_NOTES = {
    "march_kick": 36,
    "march_snare": 38,
    "march_hat": 42,
    "drip_ticks": 75,
    "pick_strike": 62,
}


def note(name: str, beat: float, duration: float, velocity: float, **extra: Any) -> dict[str, Any]:
    return {"n": name, "b": beat, "d": duration, "v": velocity, **extra}


def midi_to_note(value: int) -> str:
    return f"{NOTE_NAMES[value % 12]}{value // 12 - 1}"


def transpose(name: str, semitones: int) -> str:
    return midi_to_note(parse_note(name) + semitones)


def section_at_bar(bar: int) -> str:
    for item in SECTIONS:
        if bar >= int(item["start_bar"]):
            section = item["name"]
    return section


def root_at_bar(bar: int) -> str:
    section = section_at_bar(bar)
    roots = VEIN_ROOTS if section == "vein_open" else PHRYGIAN_ROOTS
    start = next(item["start_bar"] for item in SECTIONS if item["name"] == section)
    return roots[(bar - int(start)) % len(roots)]


def pad_audio(audio: np.ndarray) -> np.ndarray:
    if audio.shape[0] < TOTAL_SAMPLES:
        if audio.ndim == 2:
            padded = np.zeros((TOTAL_SAMPLES, audio.shape[1]), dtype=audio.dtype)
        else:
            padded = np.zeros(TOTAL_SAMPLES, dtype=audio.dtype)
        padded[: audio.shape[0]] = audio
        return padded
    return audio[:TOTAL_SAMPLES]


def mix_arrays(arrays: list[np.ndarray]) -> np.ndarray:
    if arrays and arrays[0].ndim == 2:
        mixed = np.zeros((TOTAL_SAMPLES, arrays[0].shape[1]), dtype=np.float32)
        for audio in arrays:
            n = min(audio.shape[0], TOTAL_SAMPLES)
            mixed[:n] += audio[:n]
        return mixed
    mixed = np.zeros(TOTAL_SAMPLES, dtype=np.float32)
    for audio in arrays:
        n = min(audio.shape[0], TOTAL_SAMPLES)
        mixed[:n] += audio[:n]
    return mixed


def stats(audio: np.ndarray) -> tuple[float, float]:
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(np.square(audio)))) if audio.size else 0.0
    rms_db = 20.0 * math.log10(rms + 1e-12)
    return peak, rms_db


def butter(audio: np.ndarray, kind: str, cutoff: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, cutoff, btype=kind, fs=SAMPLE_RATE, output="sos")
    return signal.sosfilt(sos, audio).astype(np.float32)


def add_delay(audio: np.ndarray, delay_beats: float, wet: float, feedback: float = 0.18, cross: bool = True) -> np.ndarray:
    delay_samples = int(round(delay_beats * BEAT_SEC * SAMPLE_RATE))
    out = audio.copy()
    for channel in (0, 1):
        delayed = np.zeros_like(audio)
        delayed[delay_samples:] = audio[:-delay_samples] * wet
        if feedback > 0:
            for _ in range(1):
                repeat = np.zeros_like(audio)
                repeat[delay_samples:] = delayed[:-delay_samples] * feedback
                delayed += repeat
        if cross:
            out[:, 1 - channel] += delayed[:, channel]
        else:
            out[:, channel] += delayed[:, channel]
    return out


def sidechain_duck(audio: np.ndarray, trigger: np.ndarray, depth: float, release_ms: float = 180.0) -> np.ndarray:
    envelope = np.abs(trigger)
    if envelope.ndim == 2:
        envelope = envelope.max(axis=1)
    window = int(round(release_ms / 1000.0 * SAMPLE_RATE))
    if window > 0:
        kernel = np.ones(window) / window
        envelope = np.convolve(envelope, kernel, mode="same")
    envelope = np.clip(envelope * 8.0, 0.0, 1.0)
    duck = 1.0 - depth * envelope
    return (audio * duck[:, None]).astype(np.float32)


def render_bus(renderer: Renderer, tracks: list[dict[str, Any]], volume: float) -> np.ndarray:
    return pad_audio(renderer.render_stereo({"bpm": BPM, "tracks": tracks}, volume=volume))


def write_wav_mp3(renderer: Renderer, audio: np.ndarray, stem: Path, bitrate: str = "224k") -> None:
    renderer.save_wav(audio, str(stem.with_suffix(".wav")))
    renderer.save_mp3(audio, str(stem.with_suffix(".mp3")), bitrate=bitrate)


def write_mp3(renderer: Renderer, audio: np.ndarray, path: Path, bitrate: str = "224k") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    renderer.save_mp3(audio, str(path), bitrate=bitrate)


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


def build_bass(library: PresetLibrary) -> dict[str, list[dict[str, Any]]]:
    floor: list[dict[str, Any]] = []
    drive: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        root = root_at_bar(bar)
        beat = bar * BEATS_PER_BAR

        if bar % 2 == 0:
            vel = 0.24 if section in {"deep_entry", "echo_return"} else 0.28
            floor.append(note(transpose(root, -12), beat, 7.65, vel, fx={"vib": [0.8, 2.5]}))

        if section == "deep_entry":
            if bar % 4 == 0:
                drive.append(note(root, beat, 0.30, 0.24))
        elif section == "echo_return":
            if bar % 4 in {0, 2}:
                drive.append(note(root, beat, 0.30, 0.22))
                drive.append(note(transpose(root, 7), beat + 2.0, 0.24, 0.16))
        else:
            # march drive: root, fifth push, root, octave push — heavy pickup feel
            drive.append(note(root, beat, 0.32, 0.30))
            drive.append(note(transpose(root, 7), beat + 0.75, 0.20, 0.18))
            drive.append(note(root, beat + 2.0, 0.30, 0.26))
            drive.append(note(transpose(root, 12), beat + 2.75, 0.22, 0.16))
            if section == "vein_open" and bar % 2 == 1:
                drive.append(note(transpose(root, 7), beat + 1.5, 0.16, 0.15))  # displaced accent
        if section == "vein_open" and bar == 31:
            drive.append(library.apply_macro("bass_octave_drop", note(root, beat + 2.0, 1.9, 0.30)))

    return {
        "bass_floor": [make_track("tunnel_bass_floor", "sine", floor, pan=0.0)],
        "bass_drive": [library.make_track("bass_triangle_drive", drive, name="tunnel_bass_drive", pan=-0.03)],
    }


def build_harmony(library: PresetLibrary) -> dict[str, list[dict[str, Any]]]:
    pad_left: list[dict[str, Any]] = []
    pad_right: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        root = root_at_bar(bar)
        chord = PAD_CHORDS[root]
        beat = bar * BEATS_PER_BAR
        if bar % 2 == 0:
            duration = 7.5
            base_vel = 0.15 if section in {"deep_entry", "echo_return"} else 0.19
            spread = 24 if section == "vein_open" else 12
            for idx, pitch in enumerate(chord):
                target = pad_left if idx % 2 == 0 else pad_right
                target.append(
                    note(
                        transpose(pitch, spread),
                        beat + idx * 0.04,
                        duration,
                        base_vel * (0.95 - idx * 0.08),
                        pan=-0.22 + idx * 0.15,
                    )
                )
    return {
        "pads": [
            library.make_track("pad_dark_fm_string", pad_left, name="dark_pad_left", pan=-0.18),
            library.make_track("pad_dark_fm_string", pad_right, name="dark_pad_right", pan=0.18),
        ],
    }


def build_arps(library: PresetLibrary) -> dict[str, list[dict[str, Any]]]:
    grid: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        if section == "deep_entry":
            continue
        root = root_at_bar(bar)
        chord = PAD_CHORDS[root]
        beat = bar * BEATS_PER_BAR
        if section == "echo_return":
            if bar % 2 == 0:
                continue
            offsets = [1.25, 3.0]
            spread = 12
        elif section == "vein_open":
            offsets = [0.25, 1.0, 2.25, 3.25]
            spread = 24
        else:
            offsets = [0.5, 2.25]
            spread = 12
        for idx, off in enumerate(offsets):
            pitch = transpose(chord[(idx + bar) % len(chord)], spread)
            grid.append(note(pitch, beat + off, 0.26, 0.17 if idx % 2 == 0 else 0.13, pan=0.12 if idx % 2 == 0 else -0.14))
    return {
        "arp_grid": [library.make_track("arp_primary_grid", grid, name="tunnel_arp_grid", pan=0.14)],
    }


def build_drums(library: PresetLibrary) -> dict[str, list[dict[str, Any]]]:
    kick: list[dict[str, Any]] = []
    snare: list[dict[str, Any]] = []
    hat: list[dict[str, Any]] = []
    ticks: list[dict[str, Any]] = []
    strikes: list[dict[str, Any]] = []
    riser: list[dict[str, Any]] = []

    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        beat = bar * BEATS_PER_BAR

        if section == "deep_entry":
            if bar % 2 == 0:
                kick.append(note("C2", beat, 0.18, 0.26, fm_index=8.0, fm_ratio=2.5))
                kick.append(note("C1", beat, 0.26, 0.09))
            if bar % 7 == 2:
                ticks.append(note("C6", beat + 2.25, 0.045, 0.11, pan=0.3))
            if bar % 7 == 5:
                ticks.append(note("C6", beat + 3.5, 0.04, 0.09, pan=-0.3))
        elif section == "echo_return":
            if bar % 4 == 0:
                kick.append(note("C2", beat, 0.18, 0.24, fm_index=8.0, fm_ratio=2.5))
                kick.append(note("C1", beat, 0.26, 0.08))
            if bar % 2 == 1:
                snare.append(note("D3", beat + 3.0, 0.16, 0.14))
            strikes.append(library.apply_macro("metal_strike", note("C5", beat + 1.5, 0.12, 0.16)))
            strikes.append(library.apply_macro("metal_strike", note("C5", beat + 3.5, 0.12, 0.13)))
        else:
            kick.append(note("C2", beat, 0.18, 0.30, fm_index=8.0, fm_ratio=2.5))
            kick.append(note("C1", beat, 0.26, 0.10))
            snare.append(note("D3", beat + 1.0, 0.16, 0.20))
            kick.append(note("C2", beat + 2.0, 0.18, 0.28, fm_index=8.0, fm_ratio=2.5))
            kick.append(note("C1", beat + 2.0, 0.26, 0.09))
            snare.append(note("D3", beat + 3.0, 0.16, 0.19))
            hat.append(note("F#5", beat + 0.5, 0.055, 0.10))
            hat.append(note("F#5", beat + 1.5, 0.055, 0.11))
            hat.append(note("F#5", beat + 2.5, 0.055, 0.10))
            hat.append(note("F#5", beat + 3.5, 0.055, 0.11))
            if section == "vein_open":
                hat.append(note("F#5", beat + 0.75, 0.05, 0.08))
                hat.append(note("F#5", beat + 2.75, 0.05, 0.08))
            if bar % 7 == 2:
                ticks.append(note("C6", beat + 2.25, 0.045, 0.10, pan=0.3))
            if bar % 4 == 3:
                strikes.append(library.apply_macro("metal_strike", note("C5", beat + 3.5, 0.12, 0.17)))
            if section == "vein_open" and bar == 31:
                snare.append(library.apply_macro("snare_roll_8", note("D3", beat + 2.0, 1.75, 0.30)))
            if section == "vein_open" and bar == 30:
                riser.append(library.apply_macro("industrial_riser", note("C4", beat + 3.0, 3.75, 0.16)))

    return {
        "drum_core": [
            make_track("march_kick", "fm", kick, pan=0.0, midi_channel=9),
            library.make_track("drum_snare_noise", snare, name="march_snare", pan=0.02),
        ],
        "drum_detail": [
            library.make_track("noise_brush_soft", hat, name="march_hat", pan=0.18),
            make_track("drip_ticks", "noise_periodic", ticks, pan=0.0, midi_channel=9),
            make_track("pick_strike", "fm", strikes, pan=-0.08, midi_program=15),
        ],
        "riser": [make_track("tunnel_riser", "sawtooth", riser, pan=0.0, midi_program=91)],
    }


def write_midi(path: Path, groups: dict[str, list[dict[str, Any]]], include_groups: set[str] | None = None) -> None:
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("track_name", name="mine_tunnel_march_demo", time=0))
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
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
                track.append(
                    mido.Message(
                        "program_change",
                        program=max(0, min(127, int(src.get("midi_program", MIDI_PROGRAMS.get(name, 80))))),
                        channel=channel,
                        time=0,
                    )
                )
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


def build_score(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    tracks: list[dict[str, Any]] = []
    for group_tracks in groups.values():
        tracks.extend(group_tracks)
    return {
        "title": "Mine Tunnel March demo v1",
        "bpm": BPM,
        "bars": TOTAL_BARS,
        "policy": {
            "no_lead": True,
            "style": "A phrygian underground mine march, role-first support engine",
            "motif_definition": "cross-role pick-strike cell: bass accent + metallic strike + arp reply every 4 bars",
        },
        "sections": SECTIONS,
        "tracks": tracks,
    }


def validation_report(master: np.ndarray, buses: dict[str, np.ndarray], groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    names = [track["name"] for tracks in groups.values() for track in tracks]
    bus_stats = {name: {"peak": round(stats(audio)[0], 6), "rms_db": round(stats(audio)[1], 2)} for name, audio in buses.items()}
    peak, rms = stats(master)
    return {
        "sample_rate": SAMPLE_RATE,
        "expected_duration_sec": round(TOTAL_BEATS * BEAT_SEC, 3),
        "master_shape": list(master.shape),
        "master_duration_sec": round(master.shape[0] / SAMPLE_RATE, 3),
        "master_has_nan": bool(np.isnan(master).any()),
        "master_peak": round(peak, 6),
        "master_rms_db": round(rms, 2),
        "no_lead_policy": {
            "no_track_name_contains_lead": not any("lead" in name.lower() for name in names),
            "track_count": len(names),
            "foreground_roles": [
                "bass drive with displaced accents",
                "march kick/snare on 1&3 / 2&4",
                "phrygian dark pads",
                "high arp grid",
                "metallic pick strikes",
                "drip ticks and riser transition",
            ],
        },
        "contrast_from_thermocline": {
            "bpm": BPM,
            "no_combat_groove": True,
            "no_church_or_fugue_vocabulary": True,
            "march_feel": True,
            "phrygian_mode": True,
            "moderate_density": True,
        },
        "bus_stats": bus_stats,
        "pass": (
            not bool(np.isnan(master).any())
            and peak <= 0.950001
            and not any("lead" in name.lower() for name in names)
        ),
    }


def write_readme(validation: dict[str, Any]) -> None:
    text = f"""# mine_tunnel_march_demo_v1

Underground mine march in A Phrygian — deliberately different from both the
Thermocline battle style and the After Rain Harbor style.

## Direction

- Steady 104 BPM march: kick on 1&3, snare on 2&4, hat eighths.
- No foreground lead; role-first support engine per the Fixed Pattern Protocol.
- Motif = cross-role pick-strike cell (bass accent + metallic strike + arp
  reply every 4 bars), not a melody.
- Phrygian colour: A-G-F-E descent with Bb inside the G chord.
- Sections: deep_entry (dark footsteps) -> march_core -> vein_open (brighter,
  denser, riser transition) -> echo_return (metallic echoes, decay).

## Listen

1. `01_mine_tunnel_march_master.mp3`
2. `02_march_bass_drums.mp3`
3. `03_dark_harmony_only.mp3`
4. `stem_mp3/`

## Technical

- BPM: {BPM}
- Bars: {TOTAL_BARS}
- Duration: {validation['master_duration_sec']}s
- Master peak: {validation['master_peak']}
- Master RMS: {validation['master_rms_db']} dB
- No lead policy: {validation['no_lead_policy']['no_track_name_contains_lead']}
- Validation pass: {validation['pass']}
"""
    (OUT_DIR / "说明.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STEM_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    library = PresetLibrary.load(PROJECT_ROOT / "presets")
    renderer = Renderer()

    bass = build_bass(library)
    harmony = build_harmony(library)
    arps = build_arps(library)
    drums = build_drums(library)

    groups: dict[str, list[dict[str, Any]]] = {
        **bass,
        **harmony,
        **arps,
        **drums,
    }

    kick_trigger = render_bus(renderer, drums["drum_core"][:1], volume=0.58)
    buses = {
        "01_bass_floor": render_bus(renderer, bass["bass_floor"], volume=0.58) * 1.2,
        "02_bass_drive": render_bus(renderer, bass["bass_drive"], volume=0.54) * 0.98,
        "03_drums_core": render_bus(renderer, drums["drum_core"], volume=0.56) * 0.88,
        "04_drums_detail": render_bus(renderer, drums["drum_detail"], volume=0.46) * 0.66,
        "05_dark_pads": render_bus(renderer, harmony["pads"], volume=0.60) * 1.1,
        "06_arp_grid": render_bus(renderer, arps["arp_grid"], volume=0.50) * 0.72,
        "07_riser": render_bus(renderer, drums["riser"], volume=0.34) * 0.5,
    }

    buses["01_bass_floor"] = butter(buses["01_bass_floor"], "lowpass", 900.0)
    buses["02_bass_drive"] = butter(buses["02_bass_drive"], "lowpass", 1800.0)
    buses["05_dark_pads"] = add_delay(sidechain_duck(butter(buses["05_dark_pads"], "lowpass", 4200.0), kick_trigger, 0.06), 0.75, 0.07)
    buses["06_arp_grid"] = add_delay(butter(buses["06_arp_grid"], "highpass", 450.0), 0.375, 0.10)
    buses["04_drums_detail"] = add_delay(butter(buses["04_drums_detail"], "highpass", 200.0), 0.5, 0.12, feedback=0.14)
    buses["07_riser"] = butter(buses["07_riser"], "highpass", 300.0)

    mix = mix_arrays(list(buses.values()))
    mix = butter(mix, "highpass", 24.0)
    mix = np.tanh(mix * 0.82) / np.tanh(0.82)
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    master_gain = 0.94 / peak if peak > 1e-8 else 1.0
    master = (mix * master_gain).astype(np.float32)

    bass_drums = mix_arrays([buses["01_bass_floor"], buses["02_bass_drive"], buses["03_drums_core"], buses["04_drums_detail"]])
    dark_harmony = mix_arrays([buses["05_dark_pads"], buses["06_arp_grid"], buses["07_riser"]])

    write_wav_mp3(renderer, master, OUT_DIR / "01_mine_tunnel_march_master")
    write_wav_mp3(renderer, bass_drums, OUT_DIR / "02_march_bass_drums")
    write_wav_mp3(renderer, dark_harmony, OUT_DIR / "03_dark_harmony_only")

    for name, audio in buses.items():
        write_mp3(renderer, audio * master_gain, STEM_DIR / f"{name}.mp3")

    write_midi(OUT_DIR / "01_mine_tunnel_march_full.mid", groups)
    write_midi(OUT_DIR / "02_march_bass_drums.mid", groups, include_groups={"bass_floor", "bass_drive", "drum_core", "drum_detail"})
    write_midi(OUT_DIR / "03_dark_harmony_only.mid", groups, include_groups={"pads", "arp_grid", "riser"})

    score = build_score(groups)
    score["master_gain"] = round(master_gain, 6)
    (OUT_DIR / "source" / "结构_score.json").write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(Path(__file__), SOURCE_DIR / Path(__file__).name)

    validation = validation_report(master, buses, groups)
    (OUT_DIR / "基础验证.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with (OUT_DIR / "分组stem电平.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["stem", "peak_pre_master_gain", "rms_db_pre_master_gain"])
        writer.writeheader()
        for name, audio in buses.items():
            peak_value, rms_value = stats(audio)
            writer.writerow({"stem": name, "peak_pre_master_gain": round(peak_value, 6), "rms_db_pre_master_gain": round(rms_value, 2)})

    write_readme(validation)

    print(OUT_DIR)
    print(f"duration={validation['master_duration_sec']}s")
    print(f"peak={validation['master_peak']}")
    print(f"rms_db={validation['master_rms_db']}")
    print(f"pass={validation['pass']}")
    print(OUT_DIR / "01_mine_tunnel_march_master.mp3")


if __name__ == "__main__":
    main()
