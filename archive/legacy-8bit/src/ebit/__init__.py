"""Reusable renderer and helpers for epsilon-bit AI composition."""

from .renderer import Renderer, parse_note
from .presets import InstrumentCard, MacroCard, PresetLibrary, load_preset_library
from .adapters import (
    AdapterResult,
    ExternalToolSpec,
    OptionalDependencyError,
    basic_composition_summary,
    run_external_tool,
    run_json_tool,
)

__all__ = [
    "AdapterResult",
    "ExternalToolSpec",
    "InstrumentCard",
    "MacroCard",
    "OptionalDependencyError",
    "PresetLibrary",
    "Renderer",
    "basic_composition_summary",
    "load_preset_library",
    "parse_note",
    "run_external_tool",
    "run_json_tool",
]
