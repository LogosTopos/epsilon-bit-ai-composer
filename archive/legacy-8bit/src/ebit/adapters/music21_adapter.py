"""music21 bridge for explainable symbolic analysis.

music21 is optional. This adapter keeps it out of the renderer path while
making key, contour, density, and chordified summaries easy for an Agent to
request.
"""

from __future__ import annotations

from typing import Any

from .base import (
    JsonDict,
    iter_notes,
    iter_tracks,
    midi_to_note_name,
    midi_velocity_to_unit,
    note_to_midi,
    require_optional_module,
    velocity_to_midi,
)


def _m21_modules() -> JsonDict:
    hint = "Install with `pip install music21`, or add the local music21 checkout to PYTHONPATH."
    return {
        "stream": require_optional_module("music21.stream", adapter="music21_adapter", install_hint=hint),
        "note": require_optional_module("music21.note", adapter="music21_adapter", install_hint=hint),
        "tempo": require_optional_module("music21.tempo", adapter="music21_adapter", install_hint=hint),
        "meter": require_optional_module("music21.meter", adapter="music21_adapter", install_hint=hint),
    }


def composition_to_stream(composition: JsonDict) -> Any:
    """Convert an epsilon-bit composition dict to a music21 ``Score``."""

    m21 = _m21_modules()
    score = m21["stream"].Score()
    bpm = float(composition.get("bpm", 120))
    score.insert(0, m21["tempo"].MetronomeMark(number=bpm))
    if "time_signature" in composition:
        score.insert(0, m21["meter"].TimeSignature(str(composition["time_signature"])))

    for index, track in enumerate(iter_tracks(composition)):
        part = m21["stream"].Part()
        name = str(track.get("name") or track.get("instrument") or f"track_{index}")
        part.id = name
        part.partName = name
        for event in iter_notes(track):
            try:
                midi_pitch = note_to_midi(event["n"])
            except (KeyError, ValueError):
                continue
            item = m21["note"].Note()
            item.pitch.midi = midi_pitch
            item.quarterLength = max(0.001, float(event.get("d", 0.25)))
            item.volume.velocity = velocity_to_midi(event.get("v", 0.8))
            part.insert(float(event.get("b", 0.0)), item)
        score.insert(0, part)
    return score


def stream_to_composition(
    stream_obj: Any,
    *,
    bpm: float | None = None,
    default_instrument: str = "pulse_50",
) -> JsonDict:
    """Convert a music21 stream-like object into a renderer composition dict."""

    parts = list(getattr(stream_obj, "parts", []) or [])
    if not parts:
        parts = [stream_obj]

    if bpm is None:
        bpm = _tempo_from_stream(stream_obj) or 120.0

    tracks = []
    for index, part in enumerate(parts):
        name = str(getattr(part, "partName", None) or getattr(part, "id", None) or f"part_{index}")
        notes = []
        for element in part.flatten().notes:
            pitches = list(getattr(element, "pitches", []) or [])
            if not pitches and hasattr(element, "pitch"):
                pitches = [element.pitch]
            for pitch in pitches:
                velocity = getattr(getattr(element, "volume", None), "velocity", None)
                notes.append(
                    {
                        "n": midi_to_note_name(int(pitch.midi)),
                        "b": round(float(element.offset), 6),
                        "d": round(float(getattr(element, "quarterLength", 0.25)), 6),
                        "v": midi_velocity_to_unit(velocity),
                    }
                )
        tracks.append(
            {
                "name": name,
                "instrument": default_instrument,
                "notes": notes,
            }
        )

    return {
        "bpm": round(float(bpm), 6),
        "tracks": tracks,
    }


def analyze_composition(composition: JsonDict) -> JsonDict:
    """Run music21 analysis on an epsilon-bit composition."""

    return summarize_stream(composition_to_stream(composition))


def summarize_stream(stream_obj: Any) -> JsonDict:
    """Return Agent-friendly facts from a music21 stream-like object."""

    flat = stream_obj.flatten()
    note_like = list(flat.notes)
    pitches = []
    offsets = []
    durations = []
    for element in note_like:
        element_pitches = list(getattr(element, "pitches", []) or [])
        if not element_pitches and hasattr(element, "pitch"):
            element_pitches = [element.pitch]
        pitches.extend(int(pitch.midi) for pitch in element_pitches)
        offsets.append(round(float(element.offset), 6))
        durations.append(round(float(getattr(element, "quarterLength", 0.0)), 6))

    summary: JsonDict = {
        "note_event_count": len(note_like),
        "pitch_count": len(pitches),
        "pitch_range": [min(pitches), max(pitches)] if pitches else None,
        "start_beat": min(offsets) if offsets else None,
        "end_beat": max(
            (offset + duration for offset, duration in zip(offsets, durations)),
            default=0.0,
        ),
        "key": None,
        "chordified_sample": [],
    }

    try:
        key_obj = stream_obj.analyze("key")
        summary["key"] = {
            "tonic": getattr(getattr(key_obj, "tonic", None), "name", None),
            "mode": getattr(key_obj, "mode", None),
            "correlation": getattr(key_obj, "correlationCoefficient", None),
        }
    except Exception as exc:  # music21 analysis can fail on sparse material
        summary["key_error"] = str(exc)

    try:
        chords = stream_obj.chordify().flatten().getElementsByClass("Chord")
        sample = []
        for chord in list(chords)[:16]:
            sample.append(
                {
                    "offset": round(float(chord.offset), 6),
                    "pitches": [pitch.nameWithOctave for pitch in chord.pitches],
                    "common_name": getattr(chord, "commonName", None),
                }
            )
        summary["chordified_sample"] = sample
    except Exception as exc:
        summary["chordify_error"] = str(exc)

    return summary


def _tempo_from_stream(stream_obj: Any) -> float | None:
    try:
        for mark in stream_obj.flatten().getElementsByClass("MetronomeMark"):
            number = getattr(mark, "number", None)
            if number:
                return float(number)
    except Exception:
        return None
    return None
