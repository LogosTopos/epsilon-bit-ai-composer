"""MusPy bridge for symbolic import/export and batch evaluation.

MusPy is optional. Install it, or put a local MusPy checkout on ``PYTHONPATH``,
before calling functions that construct MusPy objects.
"""

from __future__ import annotations

from typing import Any

from ebit.audio.constants import WAVE_TYPES

from .base import (
    JsonDict,
    basic_composition_summary,
    iter_notes,
    iter_tracks,
    looks_like_drum_track,
    midi_to_note_name,
    midi_velocity_to_unit,
    note_to_midi,
    require_optional_module,
    velocity_to_midi,
)


def _muspy():
    return require_optional_module(
        "muspy",
        adapter="muspy_adapter",
        install_hint="Install with `pip install muspy`, or add the local MusPy checkout to PYTHONPATH.",
    )


def composition_to_muspy(composition: JsonDict, *, resolution: int = 24) -> Any:
    """Convert an epsilon-bit composition dict to a ``muspy.Music`` object."""

    muspy = _muspy()
    bpm = float(composition.get("bpm", 120))
    tracks = []

    for track in iter_tracks(composition):
        notes = []
        for note in iter_notes(track):
            try:
                pitch = note_to_midi(note["n"])
            except (KeyError, ValueError):
                continue
            start = int(round(float(note.get("b", 0.0)) * resolution))
            duration = max(1, int(round(float(note.get("d", 0.25)) * resolution)))
            notes.append(
                muspy.Note(
                    time=start,
                    pitch=pitch,
                    duration=duration,
                    velocity=velocity_to_midi(note.get("v", 0.8)),
                    pitch_str=str(note.get("n", "")) or None,
                )
            )

        tracks.append(
            muspy.Track(
                program=int(track.get("midi_program", 0) or 0),
                is_drum=looks_like_drum_track(track),
                name=str(track.get("name") or track.get("instrument") or "track"),
                notes=notes,
            )
        )

    return muspy.Music(
        resolution=resolution,
        tempos=[muspy.Tempo(time=0, qpm=bpm)],
        tracks=tracks,
    )


def muspy_to_composition(
    music: Any,
    *,
    default_instrument: str = "pulse_50",
    bpm: float | None = None,
) -> JsonDict:
    """Convert a ``muspy.Music`` object into a renderer composition dict."""

    resolution = int(getattr(music, "resolution", 24) or 24)
    if bpm is None:
        tempos = list(getattr(music, "tempos", []) or [])
        bpm = float(getattr(tempos[0], "qpm", 120)) if tempos else 120.0

    tracks = []
    for index, track in enumerate(getattr(music, "tracks", []) or []):
        name = str(getattr(track, "name", "") or f"track_{index}")
        instrument = name if name in WAVE_TYPES else default_instrument
        notes = []
        for note in getattr(track, "notes", []) or []:
            notes.append(
                {
                    "n": midi_to_note_name(int(note.pitch)),
                    "b": round(float(note.time) / resolution, 6),
                    "d": round(float(note.duration) / resolution, 6),
                    "v": midi_velocity_to_unit(getattr(note, "velocity", 96)),
                }
            )
        track_dict: JsonDict = {
            "name": name,
            "instrument": instrument,
            "notes": notes,
        }
        program = getattr(track, "program", None)
        if program is not None:
            track_dict["midi_program"] = int(program)
        if bool(getattr(track, "is_drum", False)):
            track_dict["is_drum"] = True
        tracks.append(track_dict)

    return {
        "bpm": round(float(bpm), 6),
        "tracks": tracks,
    }


def summarize_muspy(music: Any) -> JsonDict:
    """Return structural facts from a MusPy-like object."""

    resolution = int(getattr(music, "resolution", 24) or 24)
    tempos = list(getattr(music, "tempos", []) or [])
    tracks = list(getattr(music, "tracks", []) or [])
    note_count = 0
    pitches: list[int] = []
    track_summaries = []

    for index, track in enumerate(tracks):
        notes = list(getattr(track, "notes", []) or [])
        note_count += len(notes)
        pitches.extend(int(note.pitch) for note in notes)
        track_summaries.append(
            {
                "index": index,
                "name": getattr(track, "name", None),
                "program": getattr(track, "program", None),
                "is_drum": bool(getattr(track, "is_drum", False)),
                "note_count": len(notes),
            }
        )

    end_time = 0
    for track in tracks:
        for note in getattr(track, "notes", []) or []:
            end_time = max(end_time, int(note.time) + int(note.duration))

    return {
        "resolution": resolution,
        "bpm": float(getattr(tempos[0], "qpm", 120)) if tempos else None,
        "track_count": len(tracks),
        "note_count": note_count,
        "end_beat": round(float(end_time) / resolution, 6),
        "pitch_range": [min(pitches), max(pitches)] if pitches else None,
        "tracks": track_summaries,
    }


def summarize_composition_as_muspy(composition: JsonDict) -> JsonDict:
    """Summarize a composition, using MusPy if available and basic facts if not."""

    try:
        return summarize_muspy(composition_to_muspy(composition))
    except ImportError:
        return basic_composition_summary(composition)
