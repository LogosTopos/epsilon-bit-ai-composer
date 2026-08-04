"""AMY event-plan adapter.

AMY is a richer optional synth backend. This module does not make AMY a core
dependency; it can build inspectable ``amy.send(**event)`` dictionaries without
importing AMY, and can send them only when AMY is installed.
"""

from __future__ import annotations

from typing import Any

from .base import (
    AdapterResult,
    JsonDict,
    basic_composition_summary,
    iter_notes,
    iter_tracks,
    note_to_midi,
    require_optional_module,
)

_AMY_WAVE_BY_EBIT_INSTRUMENT = {
    "pulse_12": "PULSE",
    "pulse_125": "PULSE",
    "pulse_25": "PULSE",
    "pulse_50": "PULSE",
    "pulse_75": "PULSE",
    "triangle": "TRIANGLE",
    "sawtooth": "SAW_DOWN",
    "sine": "SINE",
    "wavetable": "WAVETABLE",
    "noise_short": "NOISE",
    "noise_long": "NOISE",
    "noise_periodic": "NOISE",
    "fm": "SINE",
    "fm_bass": "SINE",
    "fm_bell": "SINE",
    "fm_brass": "SINE",
    "fm_lead": "SINE",
    "fm_string": "SINE",
}

_FX_NOT_EXPORTED = {"slide_to", "vib", "tremolo", "retrigger", "arp"}
_FM_NAMES = {"fm", "fm_bass", "fm_bell", "fm_brass", "fm_lead", "fm_string"}


def is_amy_available() -> bool:
    """Return whether the optional ``amy`` Python module can be imported."""

    try:
        require_optional_module("amy", adapter="amy_adapter")
    except ImportError:
        return False
    return True


def composition_to_amy_events(
    composition: JsonDict,
    *,
    start_osc: int = 0,
    include_note_offs: bool = True,
    resolve_constants: bool = False,
    velocity_scale: float = 1.0,
) -> list[JsonDict]:
    """Convert a composition into AMY ``send`` event dictionaries.

    This is a basic preview bridge: it exports track waves, note-on events,
    note-off events, and panning. Renderer-specific FX remain in epsilon-bit
    unless a downstream AMY-specific specializer expands them.
    """

    events, _warnings, _unsupported = _build_events(
        composition,
        start_osc=start_osc,
        include_note_offs=include_note_offs,
        resolve_constants=resolve_constants,
        velocity_scale=velocity_scale,
    )
    return events


def build_amy_event_plan(
    composition: JsonDict,
    *,
    start_osc: int = 0,
    include_note_offs: bool = True,
    resolve_constants: bool = False,
    velocity_scale: float = 1.0,
) -> AdapterResult:
    """Return an Agent-friendly AMY plan with warnings and summary data."""

    events, warnings, unsupported = _build_events(
        composition,
        start_osc=start_osc,
        include_note_offs=include_note_offs,
        resolve_constants=resolve_constants,
        velocity_scale=velocity_scale,
    )
    return AdapterResult.success(
        {
            "events": events,
            "event_count": len(events),
            "unsupported_fx": sorted(unsupported),
            "summary": basic_composition_summary(composition),
        },
        backend="amy",
        warnings=warnings,
    )


def send_amy_events(events: list[JsonDict], amy_module: Any | None = None) -> AdapterResult:
    """Send event dictionaries through ``amy.send``.

    AMY playback/render setup is intentionally left to the caller. This function
    only sends already-built event dictionaries.
    """

    amy = amy_module or require_optional_module(
        "amy",
        adapter="amy_adapter",
        install_hint="Install AMY, or add its checkout to PYTHONPATH.",
    )
    sent = 0
    for event in events:
        sendable = _resolve_event_constants(dict(event), amy)
        amy.send(**sendable)
        sent += 1
    return AdapterResult.success({"sent": sent}, backend="amy")


def _build_events(
    composition: JsonDict,
    *,
    start_osc: int,
    include_note_offs: bool,
    resolve_constants: bool,
    velocity_scale: float,
) -> tuple[list[JsonDict], list[str], set[str]]:
    bpm = float(composition.get("bpm", 120))
    beat_ms = 60000.0 / bpm
    amy = None
    if resolve_constants:
        amy = require_optional_module(
            "amy",
            adapter="amy_adapter",
            install_hint="Install AMY, or add its checkout to PYTHONPATH.",
        )

    events: list[JsonDict] = []
    warnings: list[str] = []
    unsupported_fx: set[str] = set()
    fm_used = False

    for track_index, track in enumerate(iter_tracks(composition)):
        osc = start_osc + track_index
        instrument = str(track.get("instrument", "pulse_50"))
        wave = _AMY_WAVE_BY_EBIT_INSTRUMENT.get(instrument, "PULSE")
        if instrument in _FM_NAMES:
            fm_used = True
        if amy is not None:
            wave = getattr(amy, wave, wave)

        track_pan = _ebit_pan_to_amy(track.get("pan", 0.0))
        events.append(
            {
                "time": 0,
                "osc": osc,
                "wave": wave,
                "pan": track_pan,
            }
        )

        for note in iter_notes(track):
            fx = note.get("fx") or {}
            if isinstance(fx, dict):
                unsupported_fx.update(set(fx) & _FX_NOT_EXPORTED)
            try:
                midi = note_to_midi(note["n"])
            except (KeyError, ValueError):
                continue
            start_ms = int(round(float(note.get("b", 0.0)) * beat_ms))
            duration_ms = int(round(float(note.get("d", 0.25)) * beat_ms))
            velocity = max(0.0, min(1.0, float(note.get("v", 0.8)) * velocity_scale))
            note_pan = _ebit_pan_to_amy(note.get("pan", track.get("pan", 0.0)))
            events.append(
                {
                    "time": start_ms,
                    "osc": osc,
                    "note": midi,
                    "vel": round(velocity, 4),
                    "pan": note_pan,
                }
            )
            if include_note_offs:
                events.append(
                    {
                        "time": start_ms + max(1, duration_ms),
                        "osc": osc,
                        "note": midi,
                        "vel": 0,
                    }
                )

    events.sort(
        key=lambda event: (
            int(event.get("time", 0)),
            int(event.get("osc", 0)),
            event.get("vel", 1) == 0,
        )
    )

    if unsupported_fx:
        warnings.append(
            "AMY plan exports basic note events only; renderer FX not exported: "
            + ", ".join(sorted(unsupported_fx))
        )
    if fm_used:
        warnings.append(
            "FM epsilon-bit instruments are mapped to simple AMY sine waves until an AMY-specific patch is supplied."
        )
    return events, warnings, unsupported_fx


def _ebit_pan_to_amy(value: Any) -> float:
    try:
        pan = float(value)
    except (TypeError, ValueError):
        pan = 0.0
    pan = max(-1.0, min(1.0, pan))
    return round((pan + 1.0) / 2.0, 4)


def _resolve_event_constants(event: JsonDict, amy: Any) -> JsonDict:
    for key in ("wave", "filter_type"):
        value = event.get(key)
        if isinstance(value, str) and value.isupper():
            event[key] = getattr(amy, value, value)
    return event
