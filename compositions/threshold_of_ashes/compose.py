#!/usr/bin/env python3
"""Threshold of Ashes — three original pieces with explicit transition craft.

The score is deliberately small and deterministic: every section is a function,
every transition is a named function, and section markers are written into MIDI.
The musical design uses five transition devices:

1. rhythm preview: the next section's pulse appears quietly before the seam;
2. density crossfade: the outgoing pattern is thinned before the downbeat;
3. harmonic pre-hang: the incoming root/fifth arrives before the section change;
4. timbral hand-off: the new lead/riser enters before the full arrangement;
5. tempo bridge: tempo changes happen inside a transition, never at a naked seam.
"""
from __future__ import annotations

import argparse
import os
import random
from collections import defaultdict

import mido

TPB = 480
BAR = 4.0

# MIDI channels. Channel 9 is GM percussion.
PIANO, PAD, STRINGS, CELLI, BASS, HORNS, LEAD, CHOIR, DRUMS, TIMP, HARP, FLUTE = (
    0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12
)

PROGRAMS = {
    PIANO: (0, "Piano"), PAD: (89, "Warm Pad"), STRINGS: (48, "Strings"),
    CELLI: (49, "Slow Strings"), BASS: (32, "Acoustic Bass"),
    HORNS: (60, "French Horn"), LEAD: (56, "Trumpet"),
    CHOIR: (52, "Choir"), TIMP: (47, "Timpani"), HARP: (46, "Harp"),
    FLUTE: (73, "Flute"),
}

# Chord spellings are voiced low enough for the selected GM instruments.
CHORDS = {
    "Dm": (50, 53, 57), "Bb": (46, 50, 53), "F": (41, 45, 48),
    "C": (48, 52, 55), "Gm": (43, 46, 50), "A": (45, 49, 52),
    "Eb": (51, 55, 58), "Am": (45, 48, 52), "G": (43, 47, 50),
    "Em": (40, 43, 47), "D": (50, 54, 57), "Bdim": (47, 50, 53),
}
ROOT = {name: notes[0] for name, notes in CHORDS.items()}


class Score:
    def __init__(self, seed: int = 42):
        self.events = defaultdict(list)  # channel -> (tick, order, message)
        self.meta = []
        self.markers = []
        self.rng = random.Random(seed)

    @staticmethod
    def tick(beat: float) -> int:
        return int(round(beat * TPB))

    def add_event(self, channel: int, beat: float, message, order: int = 10):
        self.events[channel].append((self.tick(beat), order, message))

    def note(self, channel: int, pitch: int, velocity: int, beat: float,
             duration: float, humanize: bool = False):
        if humanize:
            beat += self.rng.choice((-0.008, -0.004, 0.0, 0.004, 0.008))
            velocity += self.rng.choice((-2, -1, 0, 0, 1, 2))
        pitch = max(0, min(127, int(pitch)))
        velocity = max(1, min(127, int(velocity)))
        start = self.tick(beat)
        end = self.tick(beat + max(0.05, duration))
        self.add_event(channel, beat, mido.Message("note_on", channel=channel,
                                                   note=pitch, velocity=velocity), 20)
        self.add_event(channel, (end / TPB), mido.Message("note_off", channel=channel,
                                                          note=pitch, velocity=0), 0)

    def chord(self, channel: int, pitches, velocity: int, beat: float, duration: float):
        for pitch in pitches:
            self.note(channel, pitch, velocity, beat, duration)

    def cc(self, channel: int, number: int, value: int, beat: float):
        self.add_event(channel, beat, mido.Message("control_change", channel=channel,
                                                   control=number, value=value), 5)

    def tempo(self, bpm: float, beat: float):
        self.meta.append((self.tick(beat), 5, mido.MetaMessage(
            "set_tempo", tempo=mido.bpm2tempo(bpm))))

    def marker(self, beat: float, text: str):
        self.markers.append((beat, text))
        self.meta.append((self.tick(beat), 10, mido.MetaMessage("marker", text=text)))

    def write(self, path: str, title: str, initial_bpm: float):
        mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
        meta = mido.MidiTrack()
        meta.append(mido.MetaMessage("track_name", name=title, time=0))
        meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4,
                                     clocks_per_click=24,
                                     notated_32nd_notes_per_beat=8, time=0))
        self.meta.append((0, 0, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(initial_bpm))))
        last = 0
        for tick, order, msg in sorted(self.meta, key=lambda x: (x[0], x[1])):
            msg.time = max(0, tick - last)
            meta.append(msg)
            last = tick
        meta.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(meta)

        for channel in sorted(self.events):
            tr = mido.MidiTrack()
            name = "Percussion" if channel == DRUMS else PROGRAMS.get(channel, (0, "Instrument"))[1]
            tr.append(mido.MetaMessage("track_name", name=name, time=0))
            if channel != DRUMS:
                program = PROGRAMS.get(channel, (0, ""))[0]
                tr.append(mido.Message("program_change", channel=channel, program=program, time=0))
                tr.append(mido.Message("control_change", channel=channel, control=7, value=100, time=0))
                tr.append(mido.Message("control_change", channel=channel, control=91, value=48, time=0))
            last = 0
            for tick, order, msg in sorted(self.events[channel], key=lambda x: (x[0], x[1])):
                msg.time = max(0, tick - last)
                tr.append(msg)
                last = tick
            tr.append(mido.MetaMessage("end_of_track", time=0))
            mid.tracks.append(tr)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        mid.save(path)


def set_dynamic(s: Score, channels, beat: float, value: int):
    for ch in channels:
        if ch != DRUMS:
            s.cc(ch, 11, value, beat)


def harmony_bar(s: Score, beat: float, chord: str, level: int = 2, color: str = "normal"):
    """A four-beat harmony unit with progressively added inner voices."""
    root, third, fifth = CHORDS[chord]
    pad_vel = (30, 38, 46, 54)[max(0, min(3, level))]
    string_vel = max(28, pad_vel + 4)
    s.chord(PAD, (root + 12, third + 12, fifth + 12), pad_vel, beat, 3.85)
    s.note(CELLI, root, string_vel, beat, 3.7)
    if level >= 1:
        s.note(STRINGS, fifth + 12, string_vel, beat, 3.7)
    if level >= 2:
        s.note(STRINGS, third + 12, string_vel - 2, beat, 3.7)
        s.note(PIANO, root + 12, pad_vel + 8, beat, 0.30)
        s.note(PIANO, fifth + 12, pad_vel + 4, beat + 2.0, 0.25)
    if level >= 3:
        s.chord(CHOIR, (root + 24, third + 24, fifth + 24), 38, beat, 3.5)
    if color == "open":
        s.chord(PAD, (root + 12, fifth + 12), pad_vel + 4, beat, 3.85)


def bass_bar(s: Score, beat: float, chord: str, level: int = 2, mode: int = 0):
    root, third, fifth = CHORDS[chord]
    notes = [root - 12, root, fifth, third, fifth, root, fifth, root]
    if mode == 1:
        notes = [root - 12, fifth, root, third, fifth, third, fifth, root]
    if mode == 2:
        notes = [root - 12, root, third, fifth, root + 12, fifth, third, root]
    for i, pitch in enumerate(notes[: 4 if level < 2 else 8]):
        at = beat + i * (0.5 if level >= 2 else 1.0)
        dur = 0.36 if level >= 2 else 0.72
        vel = 62 + (14 if i in (0, 4) else 0) + level * 4
        s.note(BASS, pitch, vel, at, dur, humanize=True)


def drums_bar(s: Score, beat: float, level: int = 2, variant: int = 0):
    if level <= 0:
        return
    kick = (0.0, 1.5, 2.5, 3.25) if variant else (0.0, 1.5, 3.0)
    for at in kick:
        s.note(DRUMS, 36, 76 + level * 5, beat + at, 0.18)
    if level >= 2:
        for at in (1.0, 3.0):
            s.note(DRUMS, 38, 68 + level * 5, beat + at, 0.16)
        for i in range(8):
            s.note(DRUMS, 42, 42 + level * 4, beat + i * 0.5, 0.11)
    if level >= 3:
        for at in (0.75, 1.75, 2.75, 3.75):
            s.note(DRUMS, 42, 34, beat + at, 0.09)


def lead_bar(s: Score, beat: float, chord: str, phrase: int = 0, level: int = 2):
    """Short, singable call/response material; rests are intentional."""
    root, third, fifth = CHORDS[chord]
    scale = [root + 24, third + 24, fifth + 24, root + 36]
    patterns = (
        ((0.5, 0), (1.0, 1), (1.5, 2), (2.5, 1)),
        ((0.0, 2), (0.75, 1), (1.5, 0), (2.5, 3)),
        ((0.5, 0), (1.25, 2), (2.0, 1), (3.0, 0)),
        ((0.0, 3), (1.5, 2), (2.25, 1), (3.5, 0)),
    )
    for i, (at, degree) in enumerate(patterns[phrase % len(patterns)]):
        if level == 1 and i in (1, 3):
            continue
        s.note(LEAD, scale[degree], 54 + level * 7, beat + at,
               0.28 if i != 3 else 0.55, humanize=True)


def harp_bar(s: Score, beat: float, chord: str, velocity: int = 42, reverse: bool = False):
    root, third, fifth = CHORDS[chord]
    seq = (root + 24, third + 24, fifth + 24, third + 24)
    if reverse:
        seq = tuple(reversed(seq))
    for i, pitch in enumerate(seq):
        s.note(HARP, pitch, velocity, beat + i * 0.75, 0.55)


def transition_prehang(s: Score, beat: float, chord: str, label: str,
                       bpm_from: float | None = None, bpm_to: float | None = None):
    """One bar: incoming harmonic root at beat 2, outgoing rhythm thins."""
    s.marker(beat, f"T:{label}:prehang")
    if bpm_from is not None:
        s.tempo(bpm_from, beat)
    if bpm_to is not None:
        s.tempo(bpm_to, beat + BAR)
    root, _, fifth = CHORDS[chord]
    set_dynamic(s, (PAD, CELLI, STRINGS), beat, 48)
    s.note(BASS, root - 12, 58, beat + 2.0, 1.8)
    s.chord(PAD, (root + 12, fifth + 12), 34, beat + 2.0, 1.8)
    s.note(DRUMS, 42, 32, beat + 2.0, 0.10)
    s.note(DRUMS, 42, 38, beat + 3.0, 0.10)
    return beat + BAR


def transition_riser(s: Score, beat: float, chord: str, label: str, bars: int = 2,
                     bpm_from: float | None = None, bpm_to: float | None = None):
    """Two-bar pentatonic riser; pad enters first, flute becomes the timbral hand-off."""
    s.marker(beat, f"T:{label}:riser")
    if bpm_from is not None:
        s.tempo(bpm_from, beat)
    if bpm_from is not None and bpm_to is not None:
        s.tempo((bpm_from + bpm_to) / 2, beat + BAR)
        s.tempo(bpm_to, beat + bars * BAR)
    root, third, fifth = CHORDS[chord]
    set_dynamic(s, (PAD, CELLI, STRINGS, FLUTE), beat, 60)
    s.chord(PAD, (root + 12, fifth + 12), 38, beat, bars * BAR - 0.1)
    s.note(CELLI, root, 42, beat, bars * BAR - 0.15)
    scale = [root + 24, third + 24, fifth + 24, root + 36, third + 36, fifth + 36]
    total = bars * 8
    for i in range(total):
        pitch = scale[min(i // 3, len(scale) - 1)]
        vel = 36 + round(34 * i / max(1, total - 1))
        s.note(FLUTE, pitch, vel, beat + i * 0.25, 0.18)
    s.note(DRUMS, 49, 74, beat + (bars * BAR - 0.25), 0.55)
    s.note(DRUMS, 36, 88, beat + (bars * BAR - 0.25), 0.18)
    return beat + bars * BAR


def transition_roll(s: Score, beat: float, chord: str, label: str,
                    bpm_from: float | None = None, bpm_to: float | None = None):
    """One bar: 16th roll, low-root arrival, and an empty last eighth."""
    s.marker(beat, f"T:{label}:roll")
    if bpm_from is not None:
        s.tempo(bpm_from, beat)
    if bpm_from is not None and bpm_to is not None:
        s.tempo((bpm_from + bpm_to) / 2, beat + 2.0)
        s.tempo(bpm_to, beat + BAR)
    root, _, fifth = CHORDS[chord]
    set_dynamic(s, (BASS, DRUMS, FLUTE), beat, 70)
    for i in range(16):
        s.note(DRUMS, 38, 34 + round(38 * i / 15), beat + i * 0.25, 0.10)
    s.note(BASS, root - 12, 62, beat + 2.0, 1.6)
    s.chord(PAD, (root + 12, fifth + 12), 32, beat + 2.0, 1.6)
    s.note(DRUMS, 36, 94, beat + 3.5, 0.18)
    return beat + BAR


def transition_cut(s: Score, beat: float, chord: str, label: str,
                   bpm_from: float | None = None, bpm_to: float | None = None):
    """One bar: a controlled stop, leaving a two-beat harmonic afterimage."""
    s.marker(beat, f"T:{label}:cut")
    if bpm_from is not None:
        s.tempo(bpm_from, beat)
    if bpm_to is not None:
        s.tempo(bpm_to, beat + 2.0)
    root, _, fifth = CHORDS[chord]
    set_dynamic(s, (PAD, CELLI, STRINGS, BASS, LEAD), beat, 42)
    s.note(DRUMS, 49, 90, beat, 1.0)
    s.note(BASS, root - 12, 66, beat, 1.9)
    s.chord(PAD, (root + 12, fifth + 12), 40, beat, 1.9)
    s.note(TIMP, root - 12, 66, beat, 0.7)
    return beat + BAR


def section(s: Score, beat: float, name: str, chords, level: int, tempo: float,
            lead: bool = False, drums: int = 0, bass: bool = False,
            harp: bool = False, mode_offset: int = 0):
    s.marker(beat, f"SECTION:{name}")
    s.tempo(tempo, beat)
    for i, chord in enumerate(chords):
        at = beat + i * BAR
        harmony_bar(s, at, chord, level, color="open" if level == 1 else "normal")
        if bass:
            bass_bar(s, at, chord, level, mode=(i + mode_offset) % 3)
        if drums:
            drums_bar(s, at, drums, variant=(i + mode_offset) % 4 == 2)
        if lead and (i % 2 == 0 or level >= 3):
            lead_bar(s, at, chord, phrase=(i + mode_offset) % 4, level=level)
        if harp:
            harp_bar(s, at, chord, velocity=36 + level * 5, reverse=(i % 2 == 1))
    return beat + len(chords) * BAR


def build_ashen(s: Score):
    """Low-speed exploration -> fracture -> return; 72/84/104/72 BPM."""
    b = 0.0
    b = section(s, b, "A_ASHEN_APPROACH", ("Dm", "Bb", "F", "C", "Dm", "Bb", "Gm", "A"),
                level=1, tempo=72, harp=True)
    b = transition_prehang(s, b, "Gm", "A->B", bpm_from=72, bpm_to=84)
    b = section(s, b, "B_TRACKING_PULSE", ("Gm", "Eb", "Bb", "F") * 3,
                level=2, tempo=84, drums=1, bass=True, lead=True, harp=True, mode_offset=1)
    b = transition_riser(s, b, "A", "B->C", bars=2, bpm_from=84, bpm_to=104)
    b = section(s, b, "C_FRACTURE_FULL", ("Dm", "Bb", "F", "C", "Gm", "Bb", "A", "A") * 2,
                level=3, tempo=104, drums=3, bass=True, lead=True, harp=False, mode_offset=2)
    b = transition_cut(s, b, "Dm", "C->D", bpm_from=104, bpm_to=72)
    b = section(s, b, "D_AFTERIMAGE_RETURN", ("Dm", "Bb", "F", "C", "Dm", "Gm", "A", "Dm"),
                level=1, tempo=72, harp=True)
    s.marker(b, "END")
    return b


def build_riftline(s: Score):
    """Fast pursuit piece; transitions change density before changing harmonic weight."""
    b = 0.0
    b = section(s, b, "A_LONG_RANGE_LOCK", ("Em", "C", "G", "D") * 2,
                level=1, tempo=124, drums=1, bass=True, harp=True)
    b = transition_prehang(s, b, "C", "A->B", bpm_from=124, bpm_to=132)
    b = section(s, b, "B_FIRE_CORRIDOR", ("Em", "C", "G", "D") * 4,
                level=2, tempo=132, drums=2, bass=True, lead=True, mode_offset=1)
    b = transition_riser(s, b, "G", "B->C", bars=2, bpm_from=132, bpm_to=144)
    b = section(s, b, "C_FAULTLINE_PURSUIT", ("Em", "G", "C", "D", "Em", "G", "Am", "Bdim") * 2,
                level=3, tempo=144, drums=3, bass=True, lead=True, mode_offset=2)
    b = transition_roll(s, b, "Em", "C->D", bpm_from=144, bpm_to=132)
    b = section(s, b, "D_ESCAPE_LOOP", ("Em", "C", "G", "D") * 2,
                level=2, tempo=132, drums=2, bass=True, lead=True, mode_offset=0)
    b = transition_cut(s, b, "Em", "D->E", bpm_from=132, bpm_to=96)
    b = section(s, b, "E_ASHEN_LINE", ("Em", "C", "G", "D") * 2,
                level=1, tempo=96, harp=True)
    s.marker(b, "END")
    return b


def build_dawn(s: Score):
    """A full arc with a gradual tempo bridge and a genuine tonal release."""
    b = 0.0
    b = section(s, b, "A_NIGHT_FLIGHT", ("Am", "F", "C", "G") * 2,
                level=1, tempo=88, harp=True)
    b = transition_prehang(s, b, "F", "A->B", bpm_from=88, bpm_to=104)
    b = section(s, b, "B_BEFORE_DAWN", ("F", "C", "G", "Am") * 4,
                level=2, tempo=104, drums=1, bass=True, lead=True, harp=True, mode_offset=1)
    b = transition_riser(s, b, "C", "B->C", bars=2, bpm_from=104, bpm_to=120)
    # The next section moves into F major through C, not by a naked key jump.
    b = section(s, b, "C_DAYLIGHT_BREAK", ("F", "C", "Dm", "Bb", "F", "C", "Gm", "C") * 2,
                level=3, tempo=120, drums=3, bass=True, lead=True, mode_offset=2)
    b = transition_roll(s, b, "F", "C->D", bpm_from=120, bpm_to=108)
    b = section(s, b, "D_SAFE_WINDOW", ("F", "Bb", "F", "C", "Dm", "Bb", "C", "F"),
                level=2, tempo=108, drums=2, bass=True, lead=True, mode_offset=0)
    b = transition_cut(s, b, "F", "D->E", bpm_from=108, bpm_to=78)
    b = section(s, b, "E_DAWN_AFTERGLOW", ("F", "C", "Dm", "Bb", "F", "C", "F", "F"),
                level=1, tempo=78, harp=True)
    s.marker(b, "END")
    return b


PIECES = {
    "Ashen_Approach": ("Ashen Approach", build_ashen, 72),
    "Riftline_Hunt": ("Riftline Hunt", build_riftline, 124),
    "Dawn_Extraction": ("Dawn Extraction", build_dawn, 88),
}


def make_piece(name: str, title: str, builder, initial_bpm: float, out_dir: str):
    s = Score(seed=42)
    total = builder(s)
    path = os.path.join(out_dir, f"{name}.mid")
    s.write(path, title, initial_bpm)
    print(f"{name}: {total / BAR:.0f} bars, {total:.1f} beats, {path}")
    print("  " + " | ".join(f"{beat / BAR + 1:.0f}:{text}" for beat, text in s.markers))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()
    for name, (title, builder, bpm) in PIECES.items():
        make_piece(name, title, builder, bpm, args.out_dir)


if __name__ == "__main__":
    main()
