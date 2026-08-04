"""Preset card helpers for instruments and note macros.

The preset layer is intentionally thin. Cards expand into the same track/note
shape that :class:`ebit.renderer.Renderer` already accepts, so old Python
composition scripts and new card-based workflows can coexist.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .audio.constants import WAVE_TYPES

JsonDict = dict[str, Any]

SUPPORTED_MACRO_FX = {"slide_to", "vib", "tremolo", "retrigger", "arp"}


@dataclass(frozen=True)
class InstrumentCard:
    """Reusable renderer-facing instrument role."""

    id: str
    instrument: str
    role: str = ""
    description: str = ""
    pan: float = 0.0
    volume: float = 1.0
    midi_program: int | None = None
    midi_channel: int = 0
    default_note: JsonDict = field(default_factory=dict)
    default_fx: JsonDict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "InstrumentCard":
        card_type = data.get("type")
        if card_type != "instrument":
            raise ValueError(f"instrument card must use type='instrument', got {card_type!r}")
        card_id = _require_str(data, "id")
        instrument = _require_str(data, "instrument")
        if instrument not in WAVE_TYPES:
            raise ValueError(f"{card_id}: unknown renderer instrument {instrument!r}")
        pan = _clamp_float(data.get("pan", 0.0), -1.0, 1.0, f"{card_id}.pan")
        volume = _clamp_float(data.get("volume", 1.0), 0.0, 4.0, f"{card_id}.volume")
        default_note = _dict_or_empty(data.get("default_note"), f"{card_id}.default_note")
        default_fx = _dict_or_empty(data.get("default_fx"), f"{card_id}.default_fx")
        _validate_fx(default_fx, f"{card_id}.default_fx")
        midi_program = data.get("midi_program")
        if midi_program is not None:
            midi_program = int(midi_program)
            if not 0 <= midi_program <= 127:
                raise ValueError(f"{card_id}.midi_program must be in [0, 127]")
        midi_channel = int(data.get("midi_channel", 0))
        if not 0 <= midi_channel <= 15:
            raise ValueError(f"{card_id}.midi_channel must be in [0, 15]")
        return cls(
            id=card_id,
            instrument=instrument,
            role=str(data.get("role", "")),
            description=str(data.get("description", "")),
            pan=pan,
            volume=volume,
            midi_program=midi_program,
            midi_channel=midi_channel,
            default_note=default_note,
            default_fx=default_fx,
        )

    def make_track(self, notes: list[JsonDict], name: str | None = None, **overrides: Any) -> JsonDict:
        """Build a renderer track from raw note dictionaries."""
        track: JsonDict = {
            "name": name or self.id,
            "instrument": overrides.pop("instrument", self.instrument),
            "pan": overrides.pop("pan", self.pan),
            "notes": [self.apply_to_note(note) for note in notes],
        }
        if self.midi_program is not None:
            track["midi_program"] = self.midi_program
        track["midi_channel"] = self.midi_channel
        track.update(overrides)
        return track

    def apply_to_note(self, note: JsonDict) -> JsonDict:
        """Merge instrument defaults into a note without mutating the input."""
        out = dict(self.default_note)
        out.update(note)
        if self.volume != 1.0:
            out["v"] = round(float(out.get("v", 0.8)) * self.volume, 4)
        fx = _merge_fx(self.default_fx, out.get("fx"))
        if fx:
            out["fx"] = fx
        return out


@dataclass(frozen=True)
class MacroCard:
    """Reusable note decoration that expands into renderer note fields."""

    id: str
    description: str = ""
    fx: JsonDict = field(default_factory=dict)
    note_defaults: JsonDict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "MacroCard":
        card_type = data.get("type")
        if card_type != "macro":
            raise ValueError(f"macro card must use type='macro', got {card_type!r}")
        card_id = _require_str(data, "id")
        fx = _dict_or_empty(data.get("fx"), f"{card_id}.fx")
        note_defaults = _dict_or_empty(data.get("note_defaults"), f"{card_id}.note_defaults")
        _validate_fx(fx, f"{card_id}.fx")
        _validate_fx(_dict_or_empty(note_defaults.get("fx"), f"{card_id}.note_defaults.fx"), f"{card_id}.note_defaults.fx")
        return cls(
            id=card_id,
            description=str(data.get("description", "")),
            fx=fx,
            note_defaults=note_defaults,
        )

    def apply(self, note: JsonDict, **params: Any) -> JsonDict:
        """Merge this macro into a note without mutating the input.

        ``params`` can override top-level ``fx`` keys, for example
        ``macro.apply(note, slide_to="C2")``.
        """
        out = dict(self.note_defaults)
        out.update(note)
        fx = _merge_fx(self.note_defaults.get("fx"), out.get("fx"))
        fx = _merge_fx(fx, self.fx)
        if params:
            fx = _merge_fx(fx, params)
        if fx:
            _validate_fx(fx, self.id)
            out["fx"] = fx
        return out


class PresetLibrary:
    """Load and access instrument/macro cards from a directory tree."""

    def __init__(
        self,
        instruments: dict[str, InstrumentCard] | None = None,
        macros: dict[str, MacroCard] | None = None,
    ) -> None:
        self.instruments = instruments or {}
        self.macros = macros or {}

    @classmethod
    def load(cls, root: str | Path) -> "PresetLibrary":
        root = Path(root)
        instruments: dict[str, InstrumentCard] = {}
        macros: dict[str, MacroCard] = {}
        for path in sorted(root.rglob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            card_type = data.get("type")
            if card_type == "instrument":
                card = InstrumentCard.from_dict(data)
                _ensure_unique(instruments, card.id, path)
                instruments[card.id] = card
            elif card_type == "macro":
                card = MacroCard.from_dict(data)
                _ensure_unique(macros, card.id, path)
                macros[card.id] = card
            else:
                raise ValueError(f"{path}: unknown card type {card_type!r}")
        return cls(instruments=instruments, macros=macros)

    def instrument(self, card_id: str) -> InstrumentCard:
        try:
            return self.instruments[card_id]
        except KeyError as exc:
            raise KeyError(f"unknown instrument card {card_id!r}") from exc

    def macro(self, card_id: str) -> MacroCard:
        try:
            return self.macros[card_id]
        except KeyError as exc:
            raise KeyError(f"unknown macro card {card_id!r}") from exc

    def apply_macro(self, card_id: str, note: JsonDict, **params: Any) -> JsonDict:
        return self.macro(card_id).apply(note, **params)

    def make_track(
        self,
        instrument_id: str,
        notes: list[JsonDict],
        name: str | None = None,
        macros: list[str] | None = None,
        **overrides: Any,
    ) -> JsonDict:
        expanded = notes
        for macro_id in macros or []:
            macro = self.macro(macro_id)
            expanded = [macro.apply(note) for note in expanded]
        return self.instrument(instrument_id).make_track(expanded, name=name, **overrides)


def load_preset_library(root: str | Path) -> PresetLibrary:
    return PresetLibrary.load(root)


def _require_str(data: JsonDict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"card field {key!r} must be a non-empty string")
    return value


def _dict_or_empty(value: Any, label: str) -> JsonDict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return dict(value)


def _clamp_float(value: Any, low: float, high: float, label: str) -> float:
    out = float(value)
    if not low <= out <= high:
        raise ValueError(f"{label} must be in [{low}, {high}], got {out}")
    return out


def _merge_fx(first: Any, second: Any) -> JsonDict:
    fx = _dict_or_empty(first, "fx")
    fx.update(_dict_or_empty(second, "fx"))
    return fx


def _validate_fx(fx: JsonDict, label: str) -> None:
    unknown = set(fx) - SUPPORTED_MACRO_FX
    if unknown:
        raise ValueError(f"{label}: unsupported fx keys {sorted(unknown)}")
    if "retrigger" in fx and int(fx["retrigger"]) < 1:
        raise ValueError(f"{label}.retrigger must be >= 1")
    if "tremolo" in fx:
        rate, depth = fx["tremolo"]
        if float(rate) <= 0 or not 0.0 <= float(depth) <= 0.6:
            raise ValueError(f"{label}.tremolo must be [rate_hz > 0, depth in 0..0.6]")
    if "vib" in fx:
        rate, depth = fx["vib"]
        if float(rate) <= 0 or float(depth) < 0:
            raise ValueError(f"{label}.vib must be [rate_hz > 0, depth_cents >= 0]")
    if "arp" in fx:
        if not isinstance(fx["arp"], list) or not fx["arp"]:
            raise ValueError(f"{label}.arp must be a non-empty interval list")
        for item in fx["arp"]:
            int(item)


def _ensure_unique(cards: dict[str, Any], card_id: str, path: Path) -> None:
    if card_id in cards:
        raise ValueError(f"duplicate card id {card_id!r} at {path}")
