"""Optional adapter interfaces for external music/audio tooling.

Import concrete adapters directly, for example:

``from ebit.adapters.music21_adapter import analyze_composition``

Only dependency-free helper types are exported here.
"""

from .base import (
    AdapterResult,
    JsonDict,
    OptionalDependencyError,
    basic_composition_summary,
)
from .external_process import ExternalToolSpec, run_external_tool, run_json_tool

__all__ = [
    "AdapterResult",
    "ExternalToolSpec",
    "JsonDict",
    "OptionalDependencyError",
    "basic_composition_summary",
    "run_external_tool",
    "run_json_tool",
]
