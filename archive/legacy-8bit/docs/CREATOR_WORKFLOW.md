# Creator Workflow

This document explains how to add new instrument cards and macro cards to `ε-bit-ai-composer`.

The preset system is deliberately small. A card does not invent a new audio engine; it expands into the same note and track dictionaries that `src/ebit/renderer.py` already renders.

## Folder Layout

```text
presets/
  instruments/
    bass_triangle_drive.json
    arp_cue_quiet.json
  macros/
    quiet_vibrato.json
    teleport_up.json
```

## Instrument Cards

Instrument cards describe reusable track defaults.

Required fields:

- `type`: must be `instrument`
- `id`: unique card id
- `instrument`: one renderer waveform name

Useful optional fields:

- `role`: musical role, such as `bass`, `arp`, `cue_arp`, `fx`
- `description`: human explanation
- `pan`: stereo position from `-1.0` to `1.0`
- `volume`: note velocity multiplier
- `midi_program`: optional GM program for exported MIDI
- `midi_channel`: optional MIDI channel
- `default_note`: defaults merged into every note
- `default_fx`: default renderer FX merged into every note

Example:

```json
{
  "type": "instrument",
  "id": "arp_cue_quiet",
  "instrument": "pulse_12",
  "role": "cue_arp",
  "description": "Quiet prompt-like arp/counter layer.",
  "pan": -0.2,
  "volume": 0.22,
  "midi_program": 80,
  "default_fx": {
    "vib": [5.0, 2.0]
  }
}
```

Supported `instrument` values:

- `pulse_12`, `pulse_25`, `pulse_50`, `pulse_75`
- `triangle`
- `sawtooth`
- `sine`
- `wavetable`
- `noise_short`, `noise_long`, `noise_periodic`
- `fm`, `fm_bass`, `fm_bell`, `fm_brass`, `fm_lead`, `fm_string`

## Macro Cards

Macro cards describe reusable note decorations.

Required fields:

- `type`: must be `macro`
- `id`: unique card id

Useful optional fields:

- `description`: human explanation
- `fx`: renderer FX merged into the note
- `note_defaults`: other note defaults merged before note-specific values

Example:

```json
{
  "type": "macro",
  "id": "teleport_up",
  "description": "Rising slide used for teleport or lock-on chirps.",
  "fx": {
    "slide_to": "C#7",
    "retrigger": 3
  }
}
```

Supported `fx` keys:

- `slide_to`: target note, such as `"C#7"`
- `vib`: `[rate_hz, depth_cents]`
- `tremolo`: `[rate_hz, depth_amp]`, where depth must be `0.0..0.6`
- `retrigger`: positive integer
- `arp`: non-empty semitone interval list

## Python Use

```python
from ebit import PresetLibrary, Renderer

library = PresetLibrary.load("presets")

note = library.apply_macro(
    "teleport_up",
    {"n": "G#6", "b": 7.5, "d": 0.18, "v": 0.2},
)

track = library.make_track("fx_teleport_chirp", [note])
composition = {"bpm": 192, "tracks": [track]}
audio = Renderer().render_stereo(composition, volume=0.6)
```

Run the bundled proof:

```bash
python scripts/render_preset_demo.py
```

## External Adapter Use

Instrument and macro cards should stay as JSON even when an external backend is
used. Adapters consume the same composition dictionaries as the renderer:

```python
from ebit.adapters.amy_adapter import build_amy_event_plan
from ebit.adapters.music21_adapter import analyze_composition

analysis = analyze_composition(composition)
amy_plan = build_amy_event_plan(composition)
```

Use this pattern for project-specific instrument specialization:

1. copy or extend the nearest useful instrument card;
2. keep the same role and macro compatibility unless there is a clear reason to
   change it;
3. add backend-specific fields only as extra data;
4. keep the normal renderer fields valid, so the local epsilon-bit demo still
   works.

## Design Rules

- Put reusable sound identity in instrument cards.
- Put reusable note movement in macro cards.
- Keep card names role-based, not song-specific.
- Keep prompt-like cue arps quiet by default.
- Keep full arrangement decisions in Python scripts until they repeat across songs.

Bad card idea:

```text
thermocline_bar_32_final_hook_exact_copy
```

Good card idea:

```text
arp_cue_quiet
snare_roll_8
fx_teleport_chirp
```

## Compatibility

Old script-style composition remains valid. Presets are optional and incremental:

1. write notes directly in Python;
2. use a macro card when a note gesture repeats;
3. use an instrument card when a track role repeats;
4. move only stable, reusable decisions into `presets/`.
