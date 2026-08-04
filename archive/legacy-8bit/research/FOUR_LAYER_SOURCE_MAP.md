# Four-Layer Source Map

Date: 2026-05-26

Purpose: save-token map of the pulled projects against the user's four-layer
plan:

```text
instrument -> macro -> demo -> final
```

## TL;DR

The more mature route is:

```text
JSON instrument cards + JSON macro cards + deterministic demo compiler
  first,
then optional final-stage render/mix backends.
```

Reason: JSON cards preserve editability, compatibility and explainability.
Final-stage backends such as DawDreamer are powerful, but they should consume
already-structured material; they should not become the primary source of truth.

## Layer Map

| Project | License posture | Instrument | Macro | Demo | Final | Practical role |
| --- | --- | --- | --- | --- | --- | --- |
| Current `ebit` renderer | MIT core | Medium | Medium | High | Low-Medium | Current source of truth: card/note/track JSON into deterministic audio/MIDI/stems. Keep as core. |
| AMY | MIT | High | Medium | Medium | Medium | Best first external synth backend for richer JSON instrument cards. Supports FM, wavetable, sampler, drums, MIDI and Python control. |
| sfizz | BSD-2-Clause | High | Low | Medium | Medium | Best sample/SFZ backend candidate. Use for `sample_card` or `sfz_card`, not as the default card format. |
| MusPy | MIT | Low | Low-Medium | High | Low | Symbolic music import/export, representations, evaluation and dataset tooling. Good for demo-analysis and MIDI pipeline. |
| music21 | BSD-3-Clause | Low | Medium | High | Low | Theory/analysis layer: chords, keys, roles, transformations. Useful for explainable demo planning. |
| DDSP | Apache-2.0 | Medium-High | Medium | Low | Medium | Later trainable timbre/timbre-transfer research backend. Too heavy for first core path. |
| AudioCraft | MIT code, CC-BY-NC weights | Low-Medium | Low | Medium | Medium | Audio sketch generator only. Poor fit for editable instrument/macro protocols. Watch model-weight license. |
| Tone.js | MIT | Medium | Medium | High | Low-Medium | Future browser preview/editor. Good for consuming JSON score/cards, not replacing Python core. |
| Riffusion | MIT code | Low | Low | Medium | Medium | Web/API example for audio generation. Not a structured music protocol backend. |
| DawDreamer | GPLv3 | Medium | Medium-High | Medium | High | Strong final-stage graph/VST/automation backend. GPL quarantine; use only as optional external adapter or design reference. |
| pedalboard | GPLv3 | Low | High | Low-Medium | High | Excellent effects/mixing chain reference. GPL quarantine; do not import into MIT core. |
| MAGDA | GPLv3 | Low-Medium | Medium | High | High | DAW/UI/AI-chat design reference. Not a Python package; GPL quarantine. |
| Nasong | GPL-3.0-or-later | High | High | Medium-High | Medium | Philosophically close: code-as-music, Value signals, trainable instruments. Reimplement ideas clean-room only. |
| Neutone SDK | LGPL-2.1 | Medium | High | Low | Medium-High | Neural effect/plugin deployment. Interesting later; not first-phase core. |
| Web Synth | GPL | High | High | High | Medium | Modular WebAudio design reference. GPL quarantine. |
| RAVE | unclear/noncommercial risk | Medium-High | Low | Low | Medium | Treat as license-unclear/noncommercial until resolved. |
| DSK ai Synth | Web app, no source found | Medium | Low | Low | Low | External manual sound source only: export WAV/SFZ, then ingest into cards if needed. |

## Where Each Layer Should Live

### 1. Instrument Layer

Best source of truth:

```text
presets/instruments/*.json
```

An instrument should describe reproducible synthesis or sample behavior, not
just point to a rendered WAV. A good card should be editable, diffable and
compatible with macros.

Recommended future card shape:

```json
{
  "type": "instrument",
  "id": "bass_triangle_drive_project_x",
  "extends": "bass_triangle_drive",
  "engine": "numpy",
  "instrument": "triangle",
  "role": "bass",
  "volume": 1.08,
  "pan": 0.0,
  "params": {
    "filter_cutoff": 5200,
    "attack_ms": 5,
    "release_ms": 50
  },
  "compat": {
    "macro_fx": ["slide_to", "vib", "tremolo", "retrigger", "arp"],
    "render_backends": ["numpy", "amy"]
  }
}
```

This allows project-specific specialization without breaking macro/demo/final
compatibility.

Best candidates:

- Current `ebit` cards: immediate core.
- AMY: best richer synth backend.
- sfizz: sample/SFZ side path.
- Nasong/Web Synth: useful design philosophy only, due GPL.

### 2. Macro Layer

Best source of truth:

```text
presets/macros/*.json
```

Macros should remain symbolic operations on notes/events:

- pitch movement: `slide_to`, `vib`, `arp`
- articulation: `retrigger`, envelope variants
- mix/event gestures: ducking, delay-send, riser, transition cue

Best candidates:

- Current `ebit` macro model: immediate core.
- AMY: can expose backend-specific modulations, but should receive generic macro intent.
- music21/MusPy: useful for symbolic transformations.
- Nasong/Web Synth/pedalboard/DawDreamer: useful references for modulation/effects graphs, but not core code.

### 3. Demo Layer

The demo layer should compile:

```text
instrument cards + macro cards + arrangement plan
  -> note/track timelines
  -> local preview audio + MIDI + stems + validation
```

Best candidates:

- Current Python composition scripts: already work, but need schema extraction.
- MusPy/music21: good for import/export, role analysis, density metrics and MIDI review.
- Tone.js: later browser preview/editor.
- AudioCraft/Riffusion: possible audio sketching, not core.

### 4. Final Layer

The final layer should polish already structured output:

```text
demo stems / MIDI / score JSON
  -> higher quality synth, plugin graph, effects, mix, mastering
```

Best candidates:

- DawDreamer: strongest conceptually, but GPL quarantine.
- pedalboard: very strong effects chain reference, but GPL quarantine.
- Neutone: later neural effect/plugin bridge, LGPL review needed.
- AMY/sfizz: can also improve final rendering without moving into GPL.

## JSON Instrument Cards vs WAV Instrument Assets

JSON instrument cards are the better primary format.

### Why JSON Wins

1. Editable after generation.
   - You can derive `project_x_bass` from `bass_triangle_drive` with a few parameter overrides.

2. Diffable and reviewable.
   - Git can show what changed: volume, pan, engine, FM ratio, envelope, macro compatibility.

3. Macro-compatible.
   - A macro can declare which note/event operations it requires.
   - A card can declare which operations it supports.

4. Backend-independent.
   - One card can target `numpy` first and later gain `amy` or `sfz` rendering.

5. Better for AI/human collaboration.
   - LLMs can edit JSON safely if schema validation exists.
   - WAV editing is opaque and hard to review.

### Where WAV Still Belongs

WAV should be an asset referenced by a card, not the card itself.

Example:

```json
{
  "type": "instrument",
  "id": "ui_alarm_sampled",
  "engine": "sample",
  "role": "fx",
  "sample": {
    "path": "assets/samples/ui_alarm.wav",
    "root_note": "C5",
    "loop": false
  },
  "compat": {
    "macro_fx": ["retrigger", "tremolo"]
  }
}
```

## JSON Cards vs Demo-to-Final Backend

These are not mutually exclusive, but they mature at different speeds.

| Path | Maturity | Feasibility | Risk | Best use |
| --- | --- | --- | --- | --- |
| JSON instrument cards first | High | High | Low | Core project identity and protocol. |
| Demo compiler first | High | High | Low-Medium | Turn cards/macros into listenable proof. |
| DawDreamer/pedalboard final chain first | Medium | Medium-Low for MIT core | High license/runtime risk | Optional polishing backend after schema exists. |
| AudioCraft/Riffusion first | Medium | Low for explainability | High control/license/model risk | Sketch generator only. |

Verdict:

```text
JSON cards are the mature foundation.
Demo-to-final backends are later accelerators.
```

If the project starts with DawDreamer-like finalization, it may sound more
professional sooner, but the core explainability claim remains weak. If the
project starts with JSON cards and schemas, every later backend can become a
replaceable renderer rather than a source of lock-in.

## Recommended Next Step

Build this order:

1. `InstrumentCardV2` schema with `extends`, `engine`, `params`, `compat`.
2. `MacroCardV2` schema with declared required capabilities.
3. Compatibility checker:

```text
instrument_card + macro_card + backend -> valid / invalid / degraded
```

4. Adapter wrapper for the current NumPy renderer.
5. One AMY prototype backend for 1 bass card and 1 FX chirp card.
6. Only then evaluate final-stage backends such as DawDreamer.

This keeps the project's core promise intact:

```text
interface diverse,
workflow complete,
creation process explainable.
```

