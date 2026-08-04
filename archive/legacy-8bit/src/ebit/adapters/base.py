"""Shared helpers for optional external-library adapters.

Adapters are deliberately thin. They translate the project's normal
composition dictionaries into objects or event streams used by optional
libraries, without making those libraries required by the core renderer.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Iterable

from ebit.renderer import parse_note

JsonDict = dict[str, Any]

_NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


class OptionalDependencyError(ImportError):
    """Raised when an adapter is used without its optional dependency."""

    def __init__(
        self,
        package: str,
        adapter: str | None = None,
        install_hint: str | None = None,
        reason: str | None = None,
    ) -> None:
        detail = f"Optional dependency {package!r} is not installed"
        if adapter:
            detail += f" for adapter {adapter!r}"
        if reason:
            detail += f"; import failed with: {reason}"
        if install_hint:
            detail += f". {install_hint}"
        super().__init__(detail)
        self.package = package
        self.adapter = adapter
        self.install_hint = install_hint
        self.reason = reason


@dataclass(frozen=True)
class AdapterResult:
    """Small structured result for Agent-facing adapter calls."""

    ok: bool
    data: Any = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    backend: str = ""

    @classmethod
    def success(
        cls,
        data: Any = None,
        *,
        backend: str = "",
        warnings: Iterable[str] = (),
    ) -> "AdapterResult":
        return cls(
            ok=True,
            data=data,
            backend=backend,
            warnings=tuple(warnings),
        )

    @classmethod
    def failure(
        cls,
        errors: Iterable[str],
        *,
        backend: str = "",
        data: Any = None,
        warnings: Iterable[str] = (),
    ) -> "AdapterResult":
        return cls(
            ok=False,
            data=data,
            backend=backend,
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

    def raise_for_errors(self) -> None:
        if not self.ok:
            raise RuntimeError("; ".join(self.errors) or "adapter call failed")


def require_optional_module(
    module_name: str,
    *,
    adapter: str | None = None,
    install_hint: str | None = None,
) -> ModuleType:
    """Import an optional module and raise a clear adapter error if missing."""

    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        package = module_name.split(".", 1)[0]
        raise OptionalDependencyError(
            package,
            adapter,
            install_hint,
            reason=str(exc),
        ) from exc


def iter_tracks(composition: JsonDict) -> Iterable[JsonDict]:
    """Yield track dictionaries from a renderer composition."""

    tracks = composition.get("tracks", [])
    if not isinstance(tracks, list):
        return ()
    return (track for track in tracks if isinstance(track, dict))


def iter_notes(track: JsonDict) -> Iterable[JsonDict]:
    """Yield note dictionaries from a renderer track."""

    notes = track.get("notes", [])
    if not isinstance(notes, list):
        return ()
    return (note for note in notes if isinstance(note, dict))


def composition_end_beat(composition: JsonDict) -> float:
    """Return the latest note end beat in a renderer composition."""

    end = 0.0
    for track in iter_tracks(composition):
        for note in iter_notes(track):
            end = max(end, float(note.get("b", 0.0)) + float(note.get("d", 0.25)))
    return end


def note_to_midi(note_name: str | int) -> int:
    """Convert an epsilon-bit note value to a MIDI pitch number."""

    if isinstance(note_name, int):
        return note_name
    return parse_note(str(note_name))


def midi_to_note_name(midi_note: int) -> str:
    """Convert a MIDI pitch number to a sharp-note name such as C#4."""

    midi_note = int(midi_note)
    if not 0 <= midi_note <= 127:
        raise ValueError(f"MIDI pitch must be in 0..127, got {midi_note}")
    return f"{_NOTE_NAMES[midi_note % 12]}{midi_note // 12 - 1}"


def velocity_to_midi(value: Any, default: float = 0.8) -> int:
    """Convert renderer velocity 0..1-ish to MIDI velocity 1..127."""

    try:
        velocity = float(value)
    except (TypeError, ValueError):
        velocity = default
    return max(1, min(127, int(round(velocity * 127.0))))


def midi_velocity_to_unit(value: Any, default: int = 96) -> float:
    """Convert MIDI velocity to renderer velocity."""

    try:
        velocity = int(value)
    except (TypeError, ValueError):
        velocity = default
    return round(max(0, min(127, velocity)) / 127.0, 4)


def looks_like_drum_track(track: JsonDict) -> bool:
    """Best-effort percussion hint from track metadata."""

    if bool(track.get("is_drum")):
        return True
    label = " ".join(
        str(track.get(key, "")).lower()
        for key in ("name", "role", "instrument")
    )
    return any(token in label for token in ("drum", "kick", "snare", "hat", "noise"))


def basic_composition_summary(composition: JsonDict) -> JsonDict:
    """Return cheap structural facts useful before external analysis."""

    tracks = list(iter_tracks(composition))
    note_count = 0
    roles: dict[str, int] = {}
    instruments: dict[str, int] = {}
    for track in tracks:
        notes = list(iter_notes(track))
        note_count += len(notes)
        role = str(track.get("role") or track.get("name") or "unnamed")
        instrument = str(track.get("instrument", "pulse_50"))
        roles[role] = roles.get(role, 0) + len(notes)
        instruments[instrument] = instruments.get(instrument, 0) + len(notes)
    return {
        "bpm": composition.get("bpm", 120),
        "track_count": len(tracks),
        "note_count": note_count,
        "end_beat": composition_end_beat(composition),
        "roles": roles,
        "instruments": instruments,
    }
