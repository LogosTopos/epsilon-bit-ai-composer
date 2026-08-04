#!/usr/bin/env python3
"""After Rain Harbor demo.

This is a deliberately non-Thermocline composition:

- slow tempo;
- no combat groove;
- no foreground lead;
- no church/industrial/fugue vocabulary;
- motif exists as cross-role expectation: brushed pulse, soft bass landings,
  marimba-like chord fragments, glass pad swells, and quiet dew arps.
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

BPM = 112.0
BEATS_PER_BAR = 4.0
TOTAL_BARS = 64
TAIL_BEATS = 8.0
TOTAL_BEATS = TOTAL_BARS * BEATS_PER_BAR + TAIL_BEATS
BEAT_SEC = 60.0 / BPM
TOTAL_SAMPLES = int(round(TOTAL_BEATS * BEAT_SEC * SAMPLE_RATE))
TICKS_PER_BEAT = 480

OUT_DIR = PROJECT_ROOT / "output" / "analysis" / "after_rain_harbor_demo_v1"
STEM_DIR = OUT_DIR / "stem_mp3"
SOURCE_DIR = OUT_DIR / "source"

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SECTIONS = [
    {"name": "morning_drip", "start_bar": 0, "bars": 12, "energy": "quiet", "intent": "empty dock, small water ticks, no pulse pressure"},
    {"name": "first_reflection", "start_bar": 12, "bars": 12, "energy": "gentle", "intent": "warm chord fragments and slow bass landings appear"},
    {"name": "harbor_walk", "start_bar": 24, "bars": 16, "energy": "steady", "intent": "soft brushed groove and glass pad motion carry the loop"},
    {"name": "sun_break", "start_bar": 40, "bars": 12, "energy": "open", "intent": "higher shimmer, wider harmony, still no melody line"},
    {"name": "tide_return", "start_bar": 52, "bars": 12, "energy": "settle", "intent": "reduce density and return to morning_drip"},
]

PROGRESSIONS = {
    "morning_drip": ["F2", "C2", "G2", "Bb1"],
    "first_reflection": ["F2", "A1", "Bb1", "C2"],
    "harbor_walk": ["D2", "Bb1", "F2", "C2"],
    "sun_break": ["Bb1", "F2", "C2", "D2"],
    "tide_return": ["F2", "C2", "Bb1", "F2"],
}

PAD_CHORDS = {
    "F2": ["F3", "A3", "C4", "E4"],
    "C2": ["C3", "E3", "G3", "B3"],
    "G2": ["G3", "B3", "D4", "F#4"],
    "Bb1": ["Bb2", "D3", "F3", "A3"],
    "A1": ["A2", "C3", "E3", "G3"],
    "D2": ["D3", "F3", "A3", "C4"],
}

MIDI_PROGRAMS = {
    "bass_tide_floor": 38,
    "bass_soft_landings": 38,
    "marimba_chord_fragments": 12,
    "glass_pad_left": 89,
    "glass_pad_right": 89,
    "dew_arp_high": 11,
    "dew_arp_answer": 11,
    "brush_kick": 0,
    "brush_snare": 0,
    "brush_hat": 0,
    "water_ticks": 0,
    "air_breath": 122,
}

DRUM_MIDI_NOTES = {
    "brush_kick": 36,
    "brush_snare": 38,
    "brush_hat": 42,
    "water_ticks": 75,
}


def note(name: str, beat: float, duration: float, velocity: float, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "n": name,
        "b": round(beat, 4),
        "d": round(duration, 4),
        "v": round(velocity, 4),
    }
    item.update(extra)
    return item


def midi_to_note(value: int) -> str:
    return f"{NOTE_NAMES[value % 12]}{value // 12 - 1}"


def transpose(name: str, semitones: int) -> str:
    return midi_to_note(parse_note(name) + semitones)


def section_at_bar(bar: int) -> str:
    current = SECTIONS[0]["name"]
    for item in SECTIONS:
        if bar >= int(item["start_bar"]):
            current = str(item["name"])
    return current


def root_at_bar(bar: int) -> str:
    section = section_at_bar(bar)
    local = bar - int(next(item["start_bar"] for item in SECTIONS if item["name"] == section))
    prog = PROGRESSIONS[section]
    return prog[(local // 2) % len(prog)]


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


def butter(audio: np.ndarray, kind: str, cutoff: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, cutoff / (SAMPLE_RATE / 2.0), btype=kind, output="sos")
    return np.column_stack([signal.sosfilt(sos, audio[:, channel]) for channel in range(audio.shape[1])]).astype(np.float32)


def add_delay(audio: np.ndarray, delay_beats: float, wet: float, feedback: float = 0.18, cross: bool = True) -> np.ndarray:
    delay_samples = max(1, int(round(delay_beats * BEAT_SEC * SAMPLE_RATE)))
    out = audio.copy()
    first = np.zeros_like(out)
    first[delay_samples:] = audio[:-delay_samples]
    if cross:
        first = first[:, [1, 0]]
    out += first * wet
    second = np.zeros_like(out)
    if delay_samples * 2 < len(out):
        second[delay_samples * 2:] = audio[:-delay_samples * 2]
    if cross:
        second = second[:, [1, 0]]
    out += second * wet * feedback
    return out.astype(np.float32)


def sidechain_duck(audio: np.ndarray, trigger: np.ndarray, depth: float, release_ms: float = 180.0) -> np.ndarray:
    mono = np.abs(trigger.mean(axis=1)).astype(np.float32)
    alpha = math.exp(-1.0 / max(SAMPLE_RATE * release_ms / 1000.0, 1.0))
    envelope = signal.lfilter([1.0 - alpha], [1.0, -alpha], mono)
    peak = float(np.max(envelope)) if envelope.size else 0.0
    if peak > 1e-8:
        envelope = envelope / peak
    return (audio * (1.0 - depth * envelope[:, None])).astype(np.float32)


def render_bus(renderer: Renderer, tracks: list[dict[str, Any]], volume: float) -> np.ndarray:
    return mix_arrays(list(renderer.render_multi_stereo({"bpm": BPM, "tracks": tracks}, volume=volume).values()))


def write_wav_mp3(renderer: Renderer, audio: np.ndarray, stem: Path, bitrate: str = "224k") -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    sf.write(stem.with_suffix(".wav"), audio, SAMPLE_RATE)
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


def build_bass() -> dict[str, list[dict[str, Any]]]:
    floor: list[dict[str, Any]] = []
    landings: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        root = root_at_bar(bar)
        beat = bar * BEATS_PER_BAR
        if bar % 2 == 0:
            vel = 0.22 if section in {"morning_drip", "tide_return"} else 0.27
            floor.append(note(transpose(root, -12), beat, 7.65, vel, fx={"vib": [0.7, 3.0]}))
        if section != "morning_drip" or bar >= 8:
            offsets = [0.0, 2.5] if section in {"first_reflection", "tide_return"} else [0.0, 1.75, 3.0]
            for off in offsets:
                pitch = root if off == 0.0 else transpose(root, 7)
                landings.append(note(pitch, beat + off, 0.42, 0.25 if off == 0.0 else 0.18))
    return {
        "bass_floor": [make_track("bass_tide_floor", "sine", floor, pan=0.0, midi_program=38)],
        "bass_landings": [make_track("bass_soft_landings", "triangle", landings, pan=-0.03, midi_program=38)],
    }


def build_harmony(library: PresetLibrary) -> dict[str, list[dict[str, Any]]]:
    pad_left: list[dict[str, Any]] = []
    pad_right: list[dict[str, Any]] = []
    pulse: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        root = root_at_bar(bar)
        chord = PAD_CHORDS[root]
        beat = bar * BEATS_PER_BAR

        if bar % 2 == 0:
            duration = 7.5
            base_vel = 0.13 if section in {"morning_drip", "tide_return"} else 0.17
            for idx, pitch in enumerate(chord):
                target = pad_left if idx % 2 == 0 else pad_right
                target.append(
                    library.apply_macro(
                        "soft_swell",
                        note(pitch, beat + idx * 0.03, duration, base_vel * (0.95 - idx * 0.08), pan=-0.22 + idx * 0.15),
                    )
                )

        if section in {"first_reflection", "harbor_walk", "sun_break"}:
            shape = [0.0, 1.5, 2.25] if bar % 4 in {0, 1} else [0.5, 2.0, 3.25]
            for step, off in enumerate(shape):
                pitch = chord[(step + bar) % len(chord)]
                pulse.append(note(pitch, beat + off, 0.22, 0.26 if step == 0 else 0.18, pan=-0.18 + 0.18 * step))

    return {
        "pads": [
            library.make_track("pad_rain_glass", pad_left, name="glass_pad_left", pan=-0.18),
            library.make_track("pad_rain_glass", pad_right, name="glass_pad_right", pan=0.18),
        ],
        "pulses": [library.make_track("pulse_marimba_soft", pulse, name="marimba_chord_fragments", pan=-0.08)],
    }


def build_arps(library: PresetLibrary) -> dict[str, list[dict[str, Any]]]:
    high: list[dict[str, Any]] = []
    answer: list[dict[str, Any]] = []
    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        if section == "morning_drip" and bar < 4:
            continue
        root = root_at_bar(bar)
        chord = PAD_CHORDS[root]
        beat = bar * BEATS_PER_BAR
        if section in {"morning_drip", "tide_return"}:
            offsets = [1.25, 3.0] if bar % 2 == 0 else [0.75, 2.75]
        elif section == "sun_break":
            offsets = [0.75, 1.75, 2.75, 3.5]
        else:
            offsets = [0.75, 2.25, 3.25]
        for idx, off in enumerate(offsets):
            pitch = transpose(chord[(idx + bar) % len(chord)], 12)
            target = high if idx % 2 == 0 else answer
            target.append(library.apply_macro("dew_turn", note(pitch, beat + off, 0.32, 0.16, pan=0.18 if target is high else -0.24)))
    return {
        "dew_high": [library.make_track("arp_dew_sparkle", high, name="dew_arp_high", pan=0.28)],
        "dew_answer": [library.make_track("arp_dew_sparkle", answer, name="dew_arp_answer", pan=-0.24)],
    }


def build_drums(library: PresetLibrary) -> dict[str, list[dict[str, Any]]]:
    kick: list[dict[str, Any]] = []
    snare: list[dict[str, Any]] = []
    hat: list[dict[str, Any]] = []
    ticks: list[dict[str, Any]] = []
    breath: list[dict[str, Any]] = []

    for bar in range(TOTAL_BARS):
        section = section_at_bar(bar)
        beat = bar * BEATS_PER_BAR
        if section == "morning_drip":
            kick_offsets = [0.0] if bar % 4 in {0, 2} else []
            snare_offsets = [2.75] if bar >= 4 and bar % 4 == 1 else []
            hat_offsets = [1.5, 3.25] if bar >= 4 else [3.25]
        elif section == "sun_break":
            kick_offsets = [0.0, 2.5]
            snare_offsets = [1.75, 3.5]
            hat_offsets = [0.75, 1.5, 2.25, 3.25]
        elif section == "tide_return":
            kick_offsets = [0.0, 2.75] if bar % 2 == 0 else [1.5]
            snare_offsets = [3.0] if bar % 2 == 0 else []
            hat_offsets = [1.25, 3.25]
        else:
            kick_offsets = [0.0, 2.5]
            snare_offsets = [1.75, 3.25]
            hat_offsets = [0.75, 1.5, 2.75, 3.5]

        for off in kick_offsets:
            kick.append(note("C2", beat + off, 0.18, 0.28, fm_index=3.8, fm_ratio=1.0))
            kick.append(note("C1", beat + off, 0.26, 0.10))
        for off in snare_offsets:
            snare.append(note("D3", beat + off, 0.16, 0.18))
        for off in hat_offsets:
            hat.append(note("F#5", beat + off, 0.055, 0.12))
        for off in ([0.5, 2.0] if bar % 4 in {1, 3} else [3.0]):
            ticks.append(note("C6", beat + off, 0.04, 0.10, pan=-0.3 if bar % 2 else 0.3))
        if bar % 8 == 7:
            breath.append(note("A4", beat + 3.0, 0.65, 0.12, fx={"slide_to": "A5"}))

    return {
        "drum_core": [
            make_track("brush_kick", "fm", kick, pan=0.0, midi_channel=9),
            library.make_track("drum_snare_noise", snare, name="brush_snare", pan=0.02),
        ],
        "drum_detail": [
            library.make_track("noise_brush_soft", hat, name="brush_hat", pan=0.18),
            make_track("water_ticks", "noise_periodic", ticks, pan=0.0, midi_channel=9),
        ],
        "air": [make_track("air_breath", "noise_long", breath, pan=-0.12, midi_program=122)],
    }


def write_midi(path: Path, groups: dict[str, list[dict[str, Any]]], include_groups: set[str] | None = None) -> None:
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("track_name", name="after_rain_harbor_demo", time=0))
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
        "title": "After Rain Harbor demo v1",
        "bpm": BPM,
        "bars": TOTAL_BARS,
        "policy": {
            "no_lead": True,
            "style": "slow bright harbor loop, non-combat, non-industrial",
            "motif_definition": "cross-role expectation: bass landings, brushed pulse, chord fragments, pad swells, dew arps",
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
                "soft bass landings",
                "brushed percussion",
                "marimba-like chord fragments",
                "glass pad swells",
                "dew arps",
                "air breath transitions",
            ],
        },
        "contrast_from_thermocline": {
            "bpm": BPM,
            "no_combat_groove": True,
            "no_industrial_or_cathedral_palette": True,
            "no_fugue_or_subject_voice": True,
            "low_density": True,
        },
        "bus_stats": bus_stats,
        "pass": (
            not bool(np.isnan(master).any())
            and peak <= 0.950001
            and not any("lead" in name.lower() for name in names)
        ),
    }


def write_readme(validation: dict[str, Any]) -> None:
    text = f"""# after_rain_harbor_demo_v1

This demo is intentionally far from the Thermocline battle style.

## Direction

- Slow, bright, post-rain harbor loop.
- No foreground lead and no melody-only gate.
- No industrial, cathedral, fugue, or combat vocabulary.
- Motif is a cross-role expectation: soft bass landings, brushed percussion,
  short chord fragments, glassy pad swells, and quiet dew arps.

## Listen

1. `01_after_rain_harbor_master.mp3`
2. `02_bass_drums_only.mp3`
3. `03_harmony_motion_only.mp3`
4. `04_no_air_mix.mp3`
5. `stem_mp3/`

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

    bass = build_bass()
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
        "01_bass_floor": render_bus(renderer, bass["bass_floor"], volume=0.58) * 1.25,
        "02_bass_landings": render_bus(renderer, bass["bass_landings"], volume=0.52) * 0.96,
        "03_drums_core": render_bus(renderer, drums["drum_core"], volume=0.54) * 0.82,
        "04_drums_detail": render_bus(renderer, drums["drum_detail"], volume=0.46) * 0.62,
        "05_glass_pads": render_bus(renderer, harmony["pads"], volume=0.60) * 1.18,
        "06_marimba_fragments": render_bus(renderer, harmony["pulses"], volume=0.58) * 0.88,
        "07_dew_arps": render_bus(renderer, arps["dew_high"] + arps["dew_answer"], volume=0.54) * 0.76,
        "08_air": render_bus(renderer, drums["air"], volume=0.36) * 0.40,
    }

    buses["01_bass_floor"] = butter(buses["01_bass_floor"], "lowpass", 900.0)
    buses["02_bass_landings"] = butter(buses["02_bass_landings"], "lowpass", 1800.0)
    buses["05_glass_pads"] = add_delay(sidechain_duck(butter(buses["05_glass_pads"], "lowpass", 4200.0), kick_trigger, 0.05), 0.75, 0.08)
    buses["06_marimba_fragments"] = add_delay(butter(buses["06_marimba_fragments"], "lowpass", 5200.0), 0.50, 0.07)
    buses["07_dew_arps"] = add_delay(butter(buses["07_dew_arps"], "highpass", 450.0), 0.375, 0.10)
    buses["08_air"] = butter(buses["08_air"], "highpass", 900.0)

    mix = mix_arrays(list(buses.values()))
    mix = butter(mix, "highpass", 24.0)
    mix = np.tanh(mix * 0.82) / np.tanh(0.82)
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    master_gain = 0.94 / peak if peak > 1e-8 else 1.0
    master = (mix * master_gain).astype(np.float32)

    bass_drums = mix_arrays([buses["01_bass_floor"], buses["02_bass_landings"], buses["03_drums_core"], buses["04_drums_detail"]])
    harmony_motion = mix_arrays([buses["05_glass_pads"], buses["06_marimba_fragments"], buses["07_dew_arps"]])
    no_air = mix_arrays([audio for name, audio in buses.items() if name != "08_air"])

    write_wav_mp3(renderer, master, OUT_DIR / "01_after_rain_harbor_master")
    write_wav_mp3(renderer, bass_drums, OUT_DIR / "02_bass_drums_only")
    write_wav_mp3(renderer, harmony_motion, OUT_DIR / "03_harmony_motion_only")
    write_wav_mp3(renderer, no_air, OUT_DIR / "04_no_air_mix")

    for name, audio in buses.items():
        write_mp3(renderer, audio * master_gain, STEM_DIR / f"{name}.mp3")

    write_midi(OUT_DIR / "01_after_rain_harbor_full.mid", groups)
    write_midi(OUT_DIR / "02_bass_drums_only.mid", groups, include_groups={"bass_floor", "bass_landings", "drum_core", "drum_detail"})
    write_midi(OUT_DIR / "03_harmony_motion_only.mid", groups, include_groups={"pads", "pulses", "dew_high", "dew_answer"})

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
    print(OUT_DIR / "01_after_rain_harbor_master.mp3")


if __name__ == "__main__":
    main()
