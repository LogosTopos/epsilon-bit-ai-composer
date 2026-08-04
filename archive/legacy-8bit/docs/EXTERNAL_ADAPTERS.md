# External Adapters

`ebit.adapters` is the optional bridge layer for external symbolic, synth, and
final-stage tools. The renderer and preset cards remain the source of truth:

```text
JSON cards / Python composition dict
  -> optional adapters
  -> analysis, alternate synth events, or final-stage tools
```

The core package still does not require MusPy, music21, AMY, DawDreamer,
pedalboard, or any other external backend.

For the specific question of sampled, plugin-hosted, or aria-like timbres, see
[Complex Timbre Backends](COMPLEX_TIMBRE_BACKENDS.md).

## Adapter Map

| Module | Best layer | Dependency | Purpose |
| --- | --- | --- | --- |
| `ebit.adapters.muspy_adapter` | demo | optional `muspy` | Convert composition dicts to/from MusPy for symbolic processing, MIDI-like workflows, and batch evaluation. |
| `ebit.adapters.music21_adapter` | macro/demo | optional `music21` | Convert to music21 streams and request key, chordified, contour, and density summaries. |
| `ebit.adapters.amy_adapter` | instrument/demo/final | optional `amy` only when sending | Build inspectable `amy.send(**event)` plans from epsilon-bit tracks. |
| `ebit.adapters.external_process` | final | no Python dependency | Call heavyweight or quarantined tools through JSON over stdin/stdout. |

## Optional Installs

Install only what you need:

```bash
pip install muspy music21
```

For local cloned checkouts, expose them on `PYTHONPATH` before running scripts:

```bash
export PYTHONPATH="$PWD/research/external_sources/permissive/muspy:$PWD/research/external_sources/permissive/music21:$PYTHONPATH"
```

AMY can be used the same way after it is installed or exposed:

```bash
export PYTHONPATH="$PWD/research/external_sources/permissive/amy:$PYTHONPATH"
```

## MusPy

Use MusPy when the Agent wants a symbolic object for batch transformations,
format conversion, or external metrics.

```python
from ebit.adapters.muspy_adapter import composition_to_muspy, summarize_muspy

music = composition_to_muspy(composition, resolution=24)
summary = summarize_muspy(music)
```

Round-trip back into epsilon-bit:

```python
from ebit.adapters.muspy_adapter import muspy_to_composition

composition = muspy_to_composition(music, default_instrument="pulse_50")
```

## music21

Use music21 for explainable symbolic analysis. It can identify likely key,
summarize pitch range, and inspect chordified simultaneities. Treat this as
validation, not as proof that a song is good.

```python
from ebit.adapters.music21_adapter import analyze_composition

analysis = analyze_composition(composition)
```

For custom work:

```python
from ebit.adapters.music21_adapter import composition_to_stream

score = composition_to_stream(composition)
```

## AMY

AMY is best treated as a richer synth target for JSON instrument-card
specialization. The first adapter exports a basic event plan:

```python
from ebit.adapters.amy_adapter import build_amy_event_plan

plan = build_amy_event_plan(composition)
events = plan.data["events"]
```

When AMY is installed and initialized by the caller:

```python
from ebit.adapters.amy_adapter import send_amy_events

send_amy_events(events)
```

Current AMY export scope:

- track waveform selection;
- note-on and note-off scheduling;
- velocity;
- panning.

Renderer FX such as `slide_to`, `vib`, `tremolo`, `retrigger`, and `arp` are
reported as warnings in `build_amy_event_plan`. A later AMY-specific patch
specializer can expand them, but the generic adapter does not pretend they are
already equivalent.

## External Process

Use `external_process` for tools that should not be imported into the core
package. This is the right shape for local DawDreamer, pedalboard, MAGDA-style,
or custom final-stage experiments.

The external command receives one JSON document on stdin. If it succeeds, it
should print one JSON document on stdout.

```python
from ebit import ExternalToolSpec, run_json_tool

spec = ExternalToolSpec(
    name="local_finalizer",
    command=["python", "tools/local_finalizer.py"],
    timeout=300,
)

result = run_json_tool(spec, {"composition": composition})
result.raise_for_errors()
```

This keeps the epsilon-bit project editable and inspectable while allowing
local experiments to use whatever backend is useful.

## Agent Rules

- Keep `composition` dictionaries and preset JSON cards as the source of truth.
- Use adapters to inspect, transform, preview, or polish; do not replace the
  source composition with opaque audio output.
- Prefer many small variants plus summaries over one large melody-only attempt.
- Build and validate a no-lead support engine first.
- Treat melody as absent by default. Admit a lead only through an A/B comparison
  against the no-lead baseline.
- Do not use `examples/thermocline_chatb_direct_v1/` as the musical target; it
  is only process evidence.
- Record warnings from adapters in the output folder next to renders.
