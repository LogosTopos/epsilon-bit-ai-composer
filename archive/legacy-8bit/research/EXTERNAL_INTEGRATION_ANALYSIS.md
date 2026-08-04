# External Integration Analysis

Date: 2026-05-26

Scope: local source pull and first-pass integration assessment for turning
`epsilon-bit-ai-composer` into a protocol-centered, explainable music workflow.

## Local Pull Layout

Research clones live under:

```text
research/external_sources/
```

This directory is intentionally ignored by git. It is a local inspection cache,
not vendored project code.

## Legal Boundary

This is not legal advice. Engineering rule for this project:

1. MIT core may depend directly only on permissive or carefully reviewed weak-copyleft packages.
2. GPL/strong-copyleft projects stay in an observation quarantine.
3. Do not copy GPL code, file structure, class names, internal algorithms, or tests into MIT core.
4. If a GPL project teaches a useful idea, convert that idea into a short behavior/spec note first, then implement from scratch against the project-owned schema.
5. If GPL functionality is needed, prefer an optional external process, CLI adapter, or separate GPL plugin package.

## Pulled Candidates

### Permissive / Usually Core-Compatible

| Project | Local path | Commit | Observed license | Useful role |
| --- | --- | --- | --- | --- |
| AMY | `permissive/amy` | `9d9964b` | MIT | Best first candidate for an `InstrumentCard -> synth backend` adapter. It has Python bindings, MIDI support, FM, wavetable, sampler, drum and patch concepts. |
| sfizz | `permissive/sfizz` | `f5c6e29` | BSD-2-Clause | SFZ parser/synth library. Useful for a `sample/SFZ instrument card` backend, but dependency details still need review. |
| MusPy | `permissive/muspy` | `2e1dc66` | MIT | Symbolic music data model, MIDI/MusicXML/ABC I/O, datasets, evaluation. Good for import/export and analysis, not a renderer replacement. |
| music21 | `permissive/music21` | `dd7966d` | BSD-3-Clause | Deep symbolic analysis and theory toolkit. Good for analysis and conversion; avoid bundling its corpus assets without review. |
| DDSP | `permissive/ddsp` | `88621d2` | Apache-2.0 | Differentiable DSP research backend. Useful later for trainable/timbre-transfer experiments, not first implementation. |
| AudioCraft | `permissive/audiocraft` | `896ec7c` | MIT code, CC-BY-NC weights | Useful as optional audio sketch generator. Do not treat pretrained weights as commercial-safe by default. |
| Tone.js | `web_apps/Tone.js` | `106c934` | MIT | Strong candidate for a future browser editor/player using the same JSON score protocol. |
| Riffusion | `web_apps/riffusion` | `94c29ab` | MIT code | Useful as an example of audio-generation API/server shape, not useful for explainable card/macro generation directly. |

### Quarantine / Optional Adapter Only

| Project | Local path | Commit/source | Observed license | Boundary |
| --- | --- | --- | --- | --- |
| DawDreamer | `gpl_observe/DawDreamer` | `b891902` | GPLv3 | Useful design reference for DAW graph, VST, FAUST, automation, MIDI timing. Do not import into MIT core. |
| pedalboard | `gpl_observe/pedalboard` | `cd18ef0` | GPLv3 | Excellent effects/VST API, but GPLv3. Treat as optional external process/plugin package only. |
| MAGDA | `gpl_observe/magda-core` | `0912d0a` | GPLv3 | Useful as DAW/UI/AI-chat design reference. Not a Python package and not core-compatible. |
| Nasong | `gpl_observe/nasong_pypi/nasong-0.1.0` | PyPI sdist | GPL-3.0-or-later | The prior AI answer claiming MIT was wrong. Useful philosophy: code-as-music, Value signals, trainable instruments. Reimplement only as fresh specs. |
| Neutone SDK | `gpl_observe/neutone_sdk` | `b298a5f` | LGPL-2.1 | Possibly usable with careful dynamic-linking/legal review, but not a first-phase core dependency. |
| Web Synth | `web_apps/web-synth` | `4aa1154` | GPL due Faust | Good modular WebAudio graph reference. Use only for behavior/spec observation. |
| RAVE | `gpl_observe/RAVE` | `f048ec4` | Conflicting: `LICENSE` is CC-BY-NC 4.0, setup classifier says MIT | Treat as non-commercial/unclear until license is resolved. |

### Web Apps Without Useful Source Found

| App | Finding | Integration posture |
| --- | --- | --- |
| DSK ai Synth | Official page indicates DSK virtual instruments are free for private and commercial use; no public source/API found in first pass. | Manual asset import only: generate WAV/SFZ externally, then ingest via future `sample_card` / `sfz_card`. |
| 和弦派 / other commercial AI music sites | No obvious open source core found in first pass. | Treat as external authoring/export tools, not dependencies. |

## First Technical Read

The safest architecture is not "more dependencies in core"; it is a stable
intermediate representation with optional adapters.

Recommended schema modules:

```text
ebit.schema.note
ebit.schema.track
ebit.schema.instrument_card
ebit.schema.macro_card
ebit.schema.composition_plan
ebit.schema.render_result
```

Recommended adapter modules:

```text
ebit.backends.numpy_renderer      # current renderer, core
ebit.backends.amy                 # permissive synth backend, first candidate
ebit.backends.sfz                 # SFZ/sample backend, second candidate
ebit.adapters.muspy               # symbolic import/export/evaluation
ebit.adapters.music21             # theory/analysis, optional
ebit.adapters.audiocraft          # optional audio sketch generator only
ebit.adapters.external_gpl        # CLI/subprocess hooks, if ever needed
```

## Best Immediate Candidates

1. AMY adapter.
   - Fits the instrument-card idea directly.
   - Has Python API and compact event serialization.
   - Can cover richer FM, wavetable, sampler, drum and preset concepts.

2. MusPy/music21 import/export.
   - Helps turn community MIDI references into explainable role/density reports.
   - Supports the existing project direction without changing audio output.

3. SFZ card layer.
   - Adds sample-based instruments without giving up explainability.
   - Needs careful scope: start with a small subset, not full SFZ.

4. Tone.js preview/editor.
   - Good later step if the project gains a browser-facing card/score editor.
   - It should consume project JSON rather than becoming the source of truth.

## GPL Observation Strategy

For GPL projects, extract only high-level requirements:

- "DAW graph must support named processors and explicit routing."
- "Effects chains should be serializable as ordered nodes with parameters."
- "Automation should be represented as time/value curves, not hidden callbacks."
- "AI chat must emit an auditable DSL or JSON plan before execution."
- "Live coding systems benefit from hot reload, but persisted output must be deterministic."

Then implement those requirements independently against `ebit.schema`.

## Recommended Next Implementation Order

1. Add Pydantic schemas for existing note/track/card dictionaries.
2. Add a `Backend` protocol and wrap the current NumPy renderer as the first backend.
3. Add `InstrumentBackend` and prototype AMY for one bass card and one chirp card.
4. Add MusPy/music21 MIDI analysis adapter for role/density reports.
5. Add a small SFZ/sample card proof only after the AMY adapter works.
6. Keep all GPL projects out of the dependency graph until a separate plugin package is explicitly chosen.

## Bottom Line

The user's proposed three-step research direction is sound, but the GPL rewrite
idea must be treated as clean-room/spec extraction, not "read and heavily modify".
The strongest route is:

```text
owned schema + owned deterministic renderer
  -> permissive backend adapters
  -> optional quarantined GPL bridges
  -> later browser editor using the same schema
```

