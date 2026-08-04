# Thermocline Case Study

Thermocline, Chinese name `温跃层`, is a fast teleport-shooter game concept. The BGM target is high-speed, reactive, gunplay-compatible, and loopable during combat.

## Game-Music Intent

- 192 BPM combat energy.
- Chip / 8-bit inspired local synthesis.
- Bass and drums as the main movement engine.
- Harmony and arps as pressure, not decoration.
- FX for teleport, lock-on, and stasis cues.
- Default to no foreground melody. A lead must beat the no-lead backing in an
  explicit A/B comparison before it is admitted.

## Process Summary

### Reference MIDI

Kept folder:

```text
examples/highspeed_reference_midi_v1/
```

This pack was useful for listening to density, register, and arrangement roles. It should not be treated as a melody-copy source.

### Community MIDI Analysis

Kept folder:

```text
examples/community_midi_analysis_v1/
```

This is a supporting analysis pack. It is useful background, but AI-written conclusions are advisory.

### Thermocline v1

Script:

```bash
python scripts/generate_thermocline_v1.py
```

Kept output example:

```text
examples/thermocline_v1_reconsidered/
```

Important result: the accompaniment was strong, but the lead was too dominant and musically weaker than the support layers. The useful lesson was not "fix the lead"; it was "the backing already contains the real BGM."

### Chat B Direct

Script:

```bash
python scripts/generate_thermocline_chatb_direct.py
```

Kept output example:

```text
examples/thermocline_chatb_direct_v1/
```

This pass delayed and lowered the lead while raising bass, drums, harmony, and arps. It clarified the direction, but the best path still became no-lead.
Do not use this folder as the musical quality target; it is failure-boundary
evidence.

### No-Lead Expanded

Current recommended script:

```bash
python scripts/generate_thermocline_no_lead_expanded.py
```

Generated output:

```text
output/analysis/温跃层战斗BGM_v1_no_lead_expanded/
```

This script removes the foreground lead role and expands:

- `bass_sub`
- `bass_drive`
- `bass_answer`
- `bass_edge`
- `drum_core`
- `drum_detail`
- `harmony_stabs`
- `harmony_pads`
- `arp_primary`
- `arp_secondary`
- `fx`

The secondary arp/counter layer should stay quiet. It is a cue/prompt layer, not a foreground hook.

The new `presets/` layer contains first-class cards for this lesson, including `arp_primary_grid` and `arp_cue_quiet`. New work should prefer the quiet cue card for prompt-like arps instead of copying loud arp settings.

## Reproduce

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_thermocline_no_lead_expanded.py
```

Expected terminal marker:

```text
validation_pass=True
```

## Musical Caveats

The current direction is strong enough to continue, but still draft-level. Useful next music work:

- better section transitions,
- intensity variants,
- loop-point checking,
- game-event cue variants,
- final mix balancing on multiple playback systems.
