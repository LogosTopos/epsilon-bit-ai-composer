# Architecture

The repository now has four layers:

```text
upper-layer composition cards
  -> composition script
  -> preset cards
  -> explicit note timelines
  -> optional external adapters for analysis / alternate backends
  -> src/ebit/renderer.py
  -> stereo numpy buffers
  -> WAV/MP3 through soundfile + ffmpeg
  -> optional MIDI through mido
  -> validation JSON and stem CSV
```

The most important current boundary is musical, not technical: the system is
reliable only when it works as a constrained role-first support engine. It
should not start from a free lead melody. The recommended plan is described in
[Fixed Pattern Composition Protocol](FIXED_PATTERN_COMPOSITION_PROTOCOL.md).

The intended upper-layer cards are:

- `motif_card`: cross-role event cell, not a melody line;
- `groove_card`: pulse, accent hierarchy, and motion policy;
- `section_card`: section function and role activation;
- `role_budget_card`: density, register, and foreground budgets;
- `timbre_card`: target sound and asset/backend selection;
- `backend_card`: renderer or external process boundary.

## Renderer Input

The renderer accepts a small dictionary format:

```json
{
  "bpm": 192,
  "tracks": [
    {
      "name": "bass_drive",
      "instrument": "triangle",
      "pan": 0.0,
      "notes": [
        {"n": "C#2", "b": 0.0, "d": 0.5, "v": 0.8}
      ]
    }
  ]
}
```

Important note fields:

- `n`: note name, such as `C#4`.
- `b`: start beat.
- `d`: duration in beats.
- `v`: velocity.
- `fx`: optional macros, including `slide_to`, `vib`, `tremolo`, `retrigger`, and `arp`.
- `pan`: optional per-note pan override.

## Local Instruments

Supported local instrument names:

- pulse: `pulse_12`, `pulse_25`, `pulse_50`, `pulse_75`
- bass/chip: `triangle`
- bright: `sawtooth`, `wavetable`
- clean: `sine`
- noise: `noise_short`, `noise_long`, `noise_periodic`
- FM: `fm`, `fm_bass`, `fm_bell`, `fm_brass`, `fm_lead`, `fm_string`

These are not General MIDI instruments. MIDI export is for inspection and DAW handoff; external MIDI playback will not match the MP3 rendered by this project.

## Preset Layer

The creator-facing preset layer lives in:

```text
presets/instruments/
presets/macros/
src/ebit/presets.py
```

It does not replace the renderer. It expands cards into normal renderer dictionaries.

Instrument cards define reusable track defaults:

```json
{
  "type": "instrument",
  "id": "arp_cue_quiet",
  "instrument": "pulse_12",
  "role": "cue_arp",
  "pan": -0.2,
  "volume": 0.22,
  "default_fx": {
    "vib": [5.0, 2.0]
  }
}
```

Macro cards define reusable note decorations:

```json
{
  "type": "macro",
  "id": "teleport_up",
  "fx": {
    "slide_to": "C#7",
    "retrigger": 3
  }
}
```

Python usage:

```python
from ebit import PresetLibrary

library = PresetLibrary.load("presets")
note = library.apply_macro("teleport_up", {"n": "G#6", "b": 7.5, "d": 0.18, "v": 0.2})
track = library.make_track("fx_teleport_chirp", [note])
```

This keeps the old idea of instrument cards and macros, but with a small schema that is compatible with the current scripts.

See [Creator Workflow](CREATOR_WORKFLOW.md) for the card schema and extension rules.

## External Adapter Layer

Optional adapters live in:

```text
src/ebit/adapters/
```

They do not replace the renderer or the JSON card format. Their job is to make
the normal composition dictionary available to external tools:

- MusPy for symbolic conversion and batch-oriented analysis.
- music21 for explainable theory summaries.
- AMY for richer synth event plans.
- JSON-speaking subprocess tools for final-stage render or mix experiments.

Only dependency-free adapter helpers are exported from `ebit.__init__`.
Concrete adapters import their optional packages lazily, so existing scripts keep
working with the normal `requirements.txt`.

See [External Adapters](EXTERNAL_ADAPTERS.md) for usage.

Complex timbres such as choir, organ, or aria-like textures require a real
asset/backend route: SFZ/SF2, AMY PCM, or an AU/VST-style external process.
See [Complex Timbre Backends](COMPLEX_TIMBRE_BACKENDS.md).

## Composition Script Pattern

The useful scripts follow this pattern:

1. Define sections, tempo, progression, and role constraints.
2. Build role-specific tracks directly in Python or through `presets/` cards.
3. Render each role group as a stem bus.
4. Apply simple filtering, delay, and sidechain-like ducking.
5. Mix and limit.
6. Write master MP3, comparison MP3s, stem MP3s, MIDI, score JSON, and validation files.

## Why This Shape

The project found that raw AI composition tends to fail where control matters most: melody quality, arrangement density, and mix balance. Code-based arrangement keeps those decisions inspectable. AI can still help write or revise scripts, but the musical artifact remains reproducible.
