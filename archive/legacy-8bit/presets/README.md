# Presets

This folder is the lightweight creator-facing layer.

- `instruments/` contains renderer-ready instrument cards.
- `macros/` contains reusable note-effect cards.

Cards are JSON on purpose: they are easy to inspect, easy for another agent to edit, and expand into the same note/track dictionaries used by the Python scripts.

## Instrument Card

```json
{
  "type": "instrument",
  "id": "bass_triangle_drive",
  "instrument": "triangle",
  "role": "bass",
  "pan": 0.0,
  "volume": 1.1,
  "midi_program": 38,
  "default_fx": {}
}
```

## Macro Card

```json
{
  "type": "macro",
  "id": "quiet_vibrato",
  "fx": {
    "vib": [4.8, 3.0]
  }
}
```

Use them from Python:

```python
from ebit.presets import PresetLibrary

library = PresetLibrary.load("presets")
note = library.apply_macro("quiet_vibrato", {"n": "C#5", "b": 0, "d": 1, "v": 0.5})
track = library.make_track("arp_cue_quiet", [note])
```

Run the working demo:

```bash
python scripts/render_preset_demo.py
```
