#!/usr/bin/env python3
"""Glass Choir Battle demo.

Goal:
- erase Thermocline kinship by avoiding root-drone bass grammar and regular
  8/16-bar section pacing;
- build a high-frequency battle cue from fast upper percussion and glass shards;
- restore an aria-like timbre honestly by using local AMY sample assets
  (`ANGLECHOIR-C.wav`, `CH.ORGAN D 3.wav`) as audio sources, not renamed FM.

The slow material is a long low chant line. It is melodic, but it is not a lead
hook: it moves as an under-voice while the battle energy comes from high
percussion and bright fragments.
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

from ebit import Renderer  # noqa: E402
from ebit.audio.constants import SAMPLE_RATE  # noqa: E402
from ebit.renderer import parse_note  # noqa: E402

BPM = 168.0
BEATS_PER_BAR = 4.0
TOTAL_BARS = 89
TAIL_BEATS = 10.0
TOTAL_BEATS = TOTAL_BARS * BEATS_PER_BAR + TAIL_BEATS
BEAT_SEC = 60.0 / BPM
TOTAL_SAMPLES = int(round(TOTAL_BEATS * BEAT_SEC * SAMPLE_RATE))
TICKS_PER_BEAT = 480

OUT_DIR = PROJECT_ROOT / "output" / "analysis" / "glass_choir_battle_demo_v1"
STEM_DIR = OUT_DIR / "stem_mp3"
SOURCE_DIR = OUT_DIR / "source"

SAMPLE_DIR = PROJECT_ROOT / "research" / "external_sources" / "permissive" / "amy" / "sounds" / "partial_sources"
CHOIR_SAMPLE = SAMPLE_DIR / "ANGLECHOIR-C.wav"
ORGAN_SAMPLE = SAMPLE_DIR / "CH.ORGAN D 3.wav"
CHIME_SAMPLE = SAMPLE_DIR / "CHIME E5  -L.wav"

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SECTIONS = [
    {"name": "cut_0_glass_alarm", "start_bar": 0, "bars": 7, "intent": "hard start: high ticks first, low chant delayed"},
    {"name": "cut_1_choir_drop", "start_bar": 7, "bars": 11, "intent": "low sampled choir enters as a falling line, drums remain above it"},
    {"name": "cut_2_shard_run", "start_bar": 18, "bars": 9, "intent": "upper shards and hats sprint; low line holds back"},
    {"name": "cut_3_suspended_void", "start_bar": 27, "bars": 5, "intent": "micro-break: percussion thins, choir tail and organ breath"},
    {"name": "cut_4_crossfire", "start_bar": 32, "bars": 13, "intent": "full high-frequency battle engine without root-drone bass"},
    {"name": "cut_5_false_floor", "start_bar": 45, "bars": 8, "intent": "low chant rises instead of cadencing; groove displaced"},
    {"name": "cut_6_white_strobe", "start_bar": 53, "bars": 14, "intent": "maximum upper density, no singable lead"},
    {"name": "cut_7_choir_lock", "start_bar": 67, "bars": 10, "intent": "choir/organ unison locks the scene while percussion answers"},
    {"name": "cut_8_fragment_exit", "start_bar": 77, "bars": 12, "intent": "broken ending that can loop to the alarm cut"},
]

MIDI_PROGRAMS = {
    "sampled_low_chant": 54,
    "sampled_organ_shadow": 20,
    "sub_punctuation": 38,
    "glass_shards": 11,
    "answer_shards": 15,
    "strobe_ticks": 0,
    "knife_hat": 0,
    "glass_snare": 0,
    "air_impact": 122,
}

DRUM_MIDI_NOTES = {
    "strobe_ticks": 75,
    "knife_hat": 42,
    "glass_snare": 38,
    "air_impact": 49,
}


def note(name: str, beat: float, duration: float, velocity: float, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"n": name, "b": round(beat, 4), "d": round(duration, 4), "v": round(velocity, 4)}
    item.update(extra)
    return item


def midi_to_note(value: int) -> str:
    return f"{NOTE_NAMES[value % 12]}{value // 12 - 1}"


def transpose(name: str, semitones: int) -> str:
    return midi_to_note(parse_note(name) + semitones)


def beat_to_sample(beat: float) -> int:
    return int(round(beat * BEAT_SEC * SAMPLE_RATE))


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
    delay_samples = max(1, beat_to_sample(delay_beats))
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


def sidechain_duck(audio: np.ndarray, trigger: np.ndarray, depth: float, release_ms: float = 85.0) -> np.ndarray:
    mono = np.abs(trigger.mean(axis=1)).astype(np.float32)
    alpha = math.exp(-1.0 / max(SAMPLE_RATE * release_ms / 1000.0, 1.0))
    envelope = signal.lfilter([1.0 - alpha], [1.0, -alpha], mono)
    peak = float(np.max(envelope)) if envelope.size else 0.0
    if peak > 1e-8:
        envelope = envelope / peak
    return (audio * (1.0 - depth * envelope[:, None])).astype(np.float32)


def load_sample(path: Path) -> np.ndarray:
    audio, sr = sf.read(path, dtype="float32")
    if sr != SAMPLE_RATE:
        length = int(round(len(audio) * SAMPLE_RATE / sr))
        audio = signal.resample(audio, length).astype(np.float32)
    if audio.ndim == 1:
        audio = np.column_stack([audio, audio])
    else:
        audio = audio[:, :2]
        if audio.shape[1] == 1:
            audio = np.column_stack([audio[:, 0], audio[:, 0]])
    audio = audio.astype(np.float32)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1e-8:
        audio = audio / peak
    return audio


def pitch_sample(audio: np.ndarray, semitones: float) -> np.ndarray:
    if abs(semitones) < 0.001:
        return audio.copy()
    ratio = 2.0 ** (semitones / 12.0)
    # Higher pitch means faster playback and shorter result.
    src_x = np.arange(audio.shape[0], dtype=np.float32) * ratio
    valid = src_x < audio.shape[0] - 1
    src_x = src_x[valid]
    if src_x.size == 0:
        return audio[:1].copy()
    out = np.zeros((src_x.size, 2), dtype=np.float32)
    base_x = np.arange(audio.shape[0], dtype=np.float32)
    out[:, 0] = np.interp(src_x, base_x, audio[:, 0])
    out[:, 1] = np.interp(src_x, base_x, audio[:, 1])
    return out


def stretch_to(audio: np.ndarray, frames: int) -> np.ndarray:
    if frames <= 1:
        return audio[:1].copy()
    base_x = np.arange(audio.shape[0], dtype=np.float32)
    target_x = np.linspace(0, audio.shape[0] - 1, frames, dtype=np.float32)
    out = np.zeros((frames, 2), dtype=np.float32)
    out[:, 0] = np.interp(target_x, base_x, audio[:, 0])
    out[:, 1] = np.interp(target_x, base_x, audio[:, 1])
    return out


def envelope(frames: int, attack: float = 0.08, release: float = 0.18) -> np.ndarray:
    env = np.ones(frames, dtype=np.float32)
    attack_n = min(frames, int(round(frames * attack)))
    release_n = min(frames, int(round(frames * release)))
    if attack_n > 1:
        env[:attack_n] *= np.linspace(0.0, 1.0, attack_n, dtype=np.float32)
    if release_n > 1:
        env[-release_n:] *= np.linspace(1.0, 0.0, release_n, dtype=np.float32)
    return env


def place_audio(target: np.ndarray, clip: np.ndarray, beat: float, duration_beats: float, gain: float, pan: float = 0.0) -> None:
    start = beat_to_sample(beat)
    frames = max(1, beat_to_sample(duration_beats))
    if start >= target.shape[0]:
        return
    clip = stretch_to(clip, frames)
    clip *= envelope(clip.shape[0])[:, None]
    end = min(start + clip.shape[0], target.shape[0])
    clip = clip[: end - start]
    left = math.cos((max(-1.0, min(1.0, pan)) + 1.0) * math.pi / 4.0)
    right = math.sin((max(-1.0, min(1.0, pan)) + 1.0) * math.pi / 4.0)
    target[start:end, 0] += clip[:, 0] * gain * left
    target[start:end, 1] += clip[:, 1] * gain * right


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


def build_sample_chant() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
    choir_src = load_sample(CHOIR_SAMPLE)
    organ_src = load_sample(ORGAN_SAMPLE)
    chime_src = load_sample(CHIME_SAMPLE)
    choir = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    organ = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    glints = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    chimes = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)

    # Not a root progression: long under-voice contour with asymmetric durations.
    events = [
        (5.0, 8.5, -7, 0.42, -0.12, "C2"),
        (12.5, 7.0, -10, 0.36, 0.18, "A1"),
        (18.5, 9.0, -5, 0.44, -0.05, "D2"),
        (26.5, 5.5, -12, 0.28, 0.00, "G1"),
        (31.5, 10.0, -3, 0.46, 0.16, "E2"),
        (40.0, 8.0, -8, 0.38, -0.18, "Bb1"),
        (47.0, 10.5, -1, 0.48, 0.05, "F2"),
        (56.5, 8.0, -6, 0.40, -0.08, "C2"),
        (64.0, 9.5, -4, 0.42, 0.20, "Eb2"),
        (72.5, 8.0, -9, 0.36, -0.16, "B1"),
        (80.0, 10.0, -2, 0.46, 0.00, "F#2"),
        (89.0, 7.5, -11, 0.34, 0.10, "G1"),
        (96.0, 10.5, -5, 0.42, -0.10, "D2"),
        (106.0, 7.0, -3, 0.38, 0.18, "E2"),
        (112.0, 9.5, -8, 0.40, -0.12, "Bb1"),
        (121.0, 9.0, -6, 0.36, 0.12, "C2"),
    ]

    midi_notes: list[dict[str, Any]] = []
    for beat, dur, semitones, gain, pan, midi_note in events:
        place_audio(choir, pitch_sample(choir_src, semitones), beat, dur, gain, pan)
        if beat > 24.0 and beat < 130.0:
            place_audio(organ, pitch_sample(organ_src, semitones + 2), beat + 0.25, max(1.0, dur * 0.72), gain * 0.46, -pan)
        midi_notes.append(note(midi_note, beat, dur, 0.45))

    # Short upper choir fragments add real sample color to the high-frequency
    # engine without becoming a conventional melody.
    for idx, beat in enumerate([18.0, 22.5, 34.0, 37.5, 42.0, 54.0, 58.5, 62.25, 70.0, 74.5, 83.0, 88.5, 99.0, 103.5, 118.0, 124.5, 134.0, 141.5, 150.0, 158.5, 166.0, 174.5, 186.0, 194.5, 204.0, 213.5, 221.0, 229.5, 238.0, 246.5, 258.0, 267.5, 276.0, 284.5, 296.0, 307.5, 318.0, 329.5, 340.0]):
        semitones = 5 + (idx % 5) * 2
        dur = 0.75 if idx % 3 else 1.15
        pan = -0.32 + 0.16 * (idx % 5)
        place_audio(glints, pitch_sample(choir_src, semitones), beat, dur, 0.18, pan)

    for idx, section in enumerate(SECTIONS):
        beat = float(section["start_bar"]) * BEATS_PER_BAR
        semitones = [-12, -7, -5, 0, 2, -3, 5, -9, -2][idx]
        place_audio(chimes, pitch_sample(chime_src, semitones), beat + 0.125, 1.35, 0.24, -0.35 if idx % 2 else 0.35)
        if idx in {2, 4, 6, 8}:
            place_audio(chimes, pitch_sample(chime_src, semitones + 7), beat + 2.625, 0.70, 0.15, 0.18 if idx % 2 else -0.18)

    choir = butter(add_delay(choir, 1.5, 0.10, feedback=0.25), "lowpass", 3800.0)
    organ = butter(add_delay(organ, 0.75, 0.08, feedback=0.20), "lowpass", 3000.0)
    glints = butter(add_delay(glints, 0.375, 0.18, feedback=0.24), "highpass", 600.0)
    chimes = butter(add_delay(chimes, 0.5, 0.20, feedback=0.22), "highpass", 500.0)
    return choir, organ, glints, chimes, midi_notes


def build_high_drums() -> dict[str, list[dict[str, Any]]]:
    ticks: list[dict[str, Any]] = []
    hats: list[dict[str, Any]] = []
    snare: list[dict[str, Any]] = []
    impacts: list[dict[str, Any]] = []

    for bar in range(TOTAL_BARS):
        beat = bar * BEATS_PER_BAR
        if bar < 7:
            tick_offsets = [0.0, 0.625, 1.5, 2.125, 3.25]
            hat_offsets = [0.375, 1.25, 2.625, 3.5]
            snare_offsets: list[float] = []
        elif bar < 27:
            tick_offsets = [0.0, 0.5, 1.25, 1.75, 2.5, 3.125]
            hat_offsets = [0.25, 0.875, 1.5, 2.25, 3.0, 3.625]
            snare_offsets = [1.375, 3.25] if bar % 3 else [2.125]
        elif bar < 32:
            tick_offsets = [0.75, 2.75]
            hat_offsets = [1.5, 3.5]
            snare_offsets = []
        elif bar < 53:
            tick_offsets = [0.0, 0.375, 0.875, 1.5, 2.0, 2.375, 3.0, 3.625]
            hat_offsets = [0.25, 0.75, 1.25, 1.875, 2.5, 3.25, 3.75]
            snare_offsets = [0.875, 2.875]
        elif bar < 77:
            tick_offsets = [i * 0.375 for i in range(10) if i * 0.375 < 4.0]
            hat_offsets = [0.1875, 0.75, 1.3125, 1.875, 2.4375, 3.0, 3.5625]
            snare_offsets = [1.125, 2.625, 3.5] if bar % 4 in {1, 2} else [2.125]
        else:
            tick_offsets = [0.0, 0.75, 2.25, 3.125]
            hat_offsets = [0.5, 1.5, 3.25]
            snare_offsets = [2.75] if bar % 2 == 0 else []

        for idx, off in enumerate(tick_offsets):
            ticks.append(note("C6", beat + off, 0.065, 0.30 if idx % 3 == 0 else 0.20, pan=-0.38 + 0.19 * (idx % 5)))
        for idx, off in enumerate(hat_offsets):
            hats.append(note("F#5", beat + off, 0.075, 0.24 if idx % 2 else 0.18, pan=0.24 if idx % 2 else -0.22))
        for off in snare_offsets:
            snare.append(note("D4", beat + off, 0.14, 0.34, fx={"retrigger": 2}))
        if bar in {7, 18, 27, 32, 45, 53, 67, 77, 88}:
            impacts.append(note("C5", beat, 0.36, 0.34, fx={"slide_to": "C7"}))

    return {
        "ticks": [make_track("strobe_ticks", "noise_periodic", ticks, midi_channel=9)],
        "hats": [make_track("knife_hat", "noise_short", hats, midi_channel=9)],
        "snare": [make_track("glass_snare", "noise_short", snare, midi_channel=9)],
        "impacts": [make_track("air_impact", "noise_long", impacts, midi_channel=9)],
    }


def build_shards() -> dict[str, list[dict[str, Any]]]:
    primary: list[dict[str, Any]] = []
    answer: list[dict[str, Any]] = []
    cells = [
        ["F#6", "C#7", "G6", "D7"],
        ["A6", "E7", "B6", "F#7"],
        ["D6", "A6", "E6", "B6"],
    ]
    for bar in range(TOTAL_BARS):
        beat = bar * BEATS_PER_BAR
        if bar < 7:
            offsets = [1.0, 2.5]
        elif bar < 27:
            offsets = [0.5, 1.25, 2.25, 3.0]
        elif bar < 32:
            offsets = [1.5]
        elif bar < 67:
            offsets = [0.125, 0.875, 1.5, 2.125, 2.875, 3.5]
        elif bar < 77:
            offsets = [0.5, 1.5, 2.25, 3.25]
        else:
            offsets = [0.75, 2.75]
        cell = cells[bar % len(cells)]
        for idx, off in enumerate(offsets):
            pitch = cell[idx % len(cell)]
            target = primary if idx % 2 == 0 else answer
            fx = {"arp": [0, 7, 12]} if bar >= 32 and idx % 3 == 0 else {"vib": [7.0, 3.0]}
            target.append(note(pitch, beat + off, 0.16 if bar >= 32 else 0.22, 0.30 if target is primary else 0.22, fx=fx))
    return {
        "primary": [make_track("glass_shards", "fm_bell", primary, pan=0.24, midi_program=11)],
        "answer": [make_track("answer_shards", "sine", answer, pan=-0.28, midi_program=15)],
    }


def build_sub_punctuation() -> dict[str, list[dict[str, Any]]]:
    notes: list[dict[str, Any]] = []
    # Sparse hits only. This avoids the old long-root bass floor.
    for beat, pitch in [
        (28.0, "F1"),
        (45.5, "Bb1"),
        (54.0, "C2"),
        (66.5, "A1"),
        (78.0, "D2"),
        (89.5, "F#1"),
        (118.0, "G1"),
        (132.0, "C2"),
    ]:
        notes.append(note(pitch, beat, 0.42, 0.25, fx={"slide_to": transpose(pitch, -12)}))
    return {"sub_punctuation": [make_track("sub_punctuation", "fm_bass", notes, midi_program=38)]}


def write_midi(path: Path, groups: dict[str, list[dict[str, Any]]], chant_notes: list[dict[str, Any]], include_groups: set[str] | None = None) -> None:
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("track_name", name="glass_choir_battle_demo", time=0))
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    midi.tracks.append(meta)

    all_tracks: list[dict[str, Any]] = []
    if include_groups is None or "sampled_chant" in include_groups:
        all_tracks.append(make_track("sampled_low_chant", "sine", chant_notes, midi_program=54))
    for group, tracks in groups.items():
        if include_groups is not None and group not in include_groups:
            continue
        all_tracks.extend(tracks)

    for src in all_tracks:
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


def validation_report(master: np.ndarray, buses: dict[str, np.ndarray], groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    track_names = [track["name"] for tracks in groups.values() for track in tracks] + ["sampled_low_chant", "sampled_organ_shadow"]
    peak, rms = stats(master)
    return {
        "sample_rate": SAMPLE_RATE,
        "expected_duration_sec": round(TOTAL_BEATS * BEAT_SEC, 3),
        "master_shape": list(master.shape),
        "master_duration_sec": round(master.shape[0] / SAMPLE_RATE, 3),
        "master_has_nan": bool(np.isnan(master).any()),
        "master_peak": round(peak, 6),
        "master_rms_db": round(rms, 2),
        "sample_assets": {
            "choir": str(CHOIR_SAMPLE.relative_to(PROJECT_ROOT)),
            "organ": str(ORGAN_SAMPLE.relative_to(PROJECT_ROOT)),
            "chime": str(CHIME_SAMPLE.relative_to(PROJECT_ROOT)),
        },
        "no_lead_policy": {
            "no_track_name_contains_lead": not any("lead" in name.lower() for name in track_names),
            "track_count": len(track_names),
            "foreground_roles": [
                "high-frequency strobe ticks",
                "knife hats",
                "glass shards",
                "sampled low chant under-voice",
                "sampled choir glints",
                "sampled cathedral chimes",
                "sparse sub punctuation",
                "air impacts",
            ],
        },
        "kinship_breakers": {
            "irregular_section_lengths": [item["bars"] for item in SECTIONS],
            "no_root_drone_bass_floor": True,
            "low_voice_is_sampled_chant_line": True,
            "battle_energy_from_high_frequency": True,
        },
        "bus_stats": {name: {"peak": round(stats(audio)[0], 6), "rms_db": round(stats(audio)[1], 2)} for name, audio in buses.items()},
        "pass": (
            not bool(np.isnan(master).any())
            and peak <= 0.950001
            and not any("lead" in name.lower() for name in track_names)
            and CHOIR_SAMPLE.exists()
            and ORGAN_SAMPLE.exists()
            and CHIME_SAMPLE.exists()
        ),
    }


def write_score(groups: dict[str, list[dict[str, Any]]], chant_notes: list[dict[str, Any]], master_gain: float) -> None:
    tracks: list[dict[str, Any]] = [make_track("sampled_low_chant", "sine", chant_notes, midi_program=54)]
    for group_tracks in groups.values():
        tracks.extend(group_tracks)
    score = {
        "title": "Glass Choir Battle demo v1",
        "bpm": BPM,
        "bars": TOTAL_BARS,
        "sections": SECTIONS,
        "master_gain": round(master_gain, 6),
        "policy": {
            "no_lead": True,
            "style": "high-frequency battle with sampled low chant",
            "not_thermocline": [
                "asymmetric macro sections",
                "no root-drone bass progression",
                "low material is a chant contour, not a bass loop",
                "upper percussion carries battle speed",
            ],
        },
        "sample_assets": {
            "choir": str(CHOIR_SAMPLE.relative_to(PROJECT_ROOT)),
            "organ": str(ORGAN_SAMPLE.relative_to(PROJECT_ROOT)),
            "chime": str(CHIME_SAMPLE.relative_to(PROJECT_ROOT)),
        },
        "tracks": tracks,
    }
    (SOURCE_DIR / "结构_score.json").write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_readme(validation: dict[str, Any]) -> None:
    text = f"""# glass_choir_battle_demo_v1

This demo tries to erase the remaining Thermocline kinship while returning to a
combat use case.

## Direction

- High-frequency battle BGM.
- Battle speed comes from upper percussion and glass shards, not low kick/bass.
- Slow low material is a sampled choir/organ under-voice.
- Macro form uses irregular section lengths: 7, 11, 9, 5, 13, 8, 14, 10, 12 bars.
- No root-drone bass progression and no lead-melody gate.

## Timbre Boundary

The aria-like color uses local AMY sample assets:

- `{validation['sample_assets']['choir']}`
- `{validation['sample_assets']['organ']}`
- `{validation['sample_assets']['chime']}`

This is still not a full lyrical choir instrument. It is a sampled low-chant
texture plus upper choir/chime fragments layered into the epsilon-bit renderer
output.

## Listen

1. `01_glass_choir_battle_master.mp3`
2. `02_chant_only.mp3`
3. `03_high_engine_only.mp3`
4. `04_no_chant_mix.mp3`
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
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STEM_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    if not CHOIR_SAMPLE.exists() or not ORGAN_SAMPLE.exists() or not CHIME_SAMPLE.exists():
        raise FileNotFoundError("Required AMY sample assets are missing.")

    renderer = Renderer()

    choir, organ, glints, chimes, chant_notes = build_sample_chant()
    drums = build_high_drums()
    shards = build_shards()
    sub = build_sub_punctuation()
    groups = {**drums, **shards, **sub}

    tick_trigger = render_bus(renderer, drums["ticks"], volume=0.62)
    buses = {
        "01_sampled_choir_chant": choir * 1.75,
        "02_sampled_organ_shadow": organ * 1.05,
        "03_sampled_choir_glints": glints * 2.25,
        "04_sampled_cathedral_chimes": chimes * 1.30,
        "05_strobe_ticks": render_bus(renderer, drums["ticks"], volume=0.76) * 2.70,
        "06_knife_hat": render_bus(renderer, drums["hats"], volume=0.68) * 2.35,
        "07_glass_snare": render_bus(renderer, drums["snare"], volume=0.70) * 1.75,
        "08_glass_shards": render_bus(renderer, shards["primary"], volume=0.72) * 2.10,
        "09_answer_shards": render_bus(renderer, shards["answer"], volume=0.64) * 1.45,
        "10_sub_punctuation": render_bus(renderer, sub["sub_punctuation"], volume=0.54) * 0.70,
        "11_air_impacts": render_bus(renderer, drums["impacts"], volume=0.50) * 1.25,
    }

    buses["01_sampled_choir_chant"] = sidechain_duck(butter(buses["01_sampled_choir_chant"], "lowpass", 4200.0), tick_trigger, 0.06)
    buses["02_sampled_organ_shadow"] = sidechain_duck(butter(buses["02_sampled_organ_shadow"], "lowpass", 2600.0), tick_trigger, 0.08)
    buses["03_sampled_choir_glints"] = butter(buses["03_sampled_choir_glints"], "highpass", 700.0)
    buses["04_sampled_cathedral_chimes"] = butter(buses["04_sampled_cathedral_chimes"], "highpass", 520.0)
    buses["05_strobe_ticks"] = butter(buses["05_strobe_ticks"], "highpass", 1400.0)
    buses["06_knife_hat"] = butter(buses["06_knife_hat"], "highpass", 2200.0)
    buses["07_glass_snare"] = add_delay(butter(buses["07_glass_snare"], "highpass", 850.0), 0.375, 0.08, feedback=0.16)
    buses["08_glass_shards"] = add_delay(butter(buses["08_glass_shards"], "highpass", 600.0), 0.25, 0.10, feedback=0.20)
    buses["09_answer_shards"] = add_delay(butter(buses["09_answer_shards"], "highpass", 700.0), 0.625, 0.09, feedback=0.18)
    buses["10_sub_punctuation"] = butter(buses["10_sub_punctuation"], "lowpass", 900.0)
    buses["11_air_impacts"] = butter(buses["11_air_impacts"], "highpass", 700.0)

    mix = mix_arrays(list(buses.values()))
    mix = butter(mix, "highpass", 26.0)
    mix = np.tanh(mix * 0.90) / np.tanh(0.90)
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    master_gain = 0.94 / peak if peak > 1e-8 else 1.0
    master = (mix * master_gain).astype(np.float32)

    chant_only = mix_arrays([buses["01_sampled_choir_chant"], buses["02_sampled_organ_shadow"], buses["03_sampled_choir_glints"], buses["04_sampled_cathedral_chimes"]]) * master_gain
    high_engine = mix_arrays([buses["05_strobe_ticks"], buses["06_knife_hat"], buses["07_glass_snare"], buses["08_glass_shards"], buses["09_answer_shards"], buses["11_air_impacts"]]) * master_gain
    no_chant = mix_arrays([audio for name, audio in buses.items() if not name.startswith(("01_", "02_", "03_", "04_"))]) * master_gain

    write_wav_mp3(renderer, master, OUT_DIR / "01_glass_choir_battle_master")
    write_wav_mp3(renderer, chant_only.astype(np.float32), OUT_DIR / "02_chant_only")
    write_wav_mp3(renderer, high_engine.astype(np.float32), OUT_DIR / "03_high_engine_only")
    write_wav_mp3(renderer, no_chant.astype(np.float32), OUT_DIR / "04_no_chant_mix")

    for name, audio in buses.items():
        write_mp3(renderer, (audio * master_gain).astype(np.float32), STEM_DIR / f"{name}.mp3")

    write_midi(OUT_DIR / "01_glass_choir_battle_full.mid", groups, chant_notes)
    write_midi(OUT_DIR / "02_chant_only.mid", groups, chant_notes, include_groups={"sampled_chant"})
    write_midi(OUT_DIR / "03_high_engine_only.mid", groups, chant_notes, include_groups={"ticks", "hats", "snare", "primary", "answer", "impacts"})

    write_score(groups, chant_notes, master_gain)
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
    print(OUT_DIR / "01_glass_choir_battle_master.mp3")


if __name__ == "__main__":
    main()
