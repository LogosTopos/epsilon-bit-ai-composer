# Thermocline Call-Response v5 Specification

This is an execution spec for the next Thermocline holy-war battle revision. It
exists because the v1-v4 attempts proved that ad hoc track writing produces
cue-hit clutter, not a planned call-response structure.

## Goal

Create a four-minute Thermocline battle cue whose theme is a high-occupancy
chant/classical-ensemble layer, supported by bass, harmony, and rock-like drums.

Do not make a lead-melody draft. Do not promote cue hits into the foreground.
Do not inflate complexity by adding tracks with nearly identical function.

Reference files:

- Theme and game context: `/Users/topologyw/温跃层.md`
- Best current Thermocline no-lead reference:
  `output/analysis/温跃层战斗BGM_v1_no_lead_expanded/01_温跃层_no_lead_expanded_full.mid`
- Current flawed draft to revise:
  `scripts/generate_thermocline_holy_war_battle_demo.py`
- Current flawed output:
  `output/analysis/thermocline_holy_war_battle_demo_v4/`

## Diagnosis Of v4

Keep the broad frame:

- four-minute duration;
- Thermocline game theme;
- high-occupancy bass/harmony foundation;
- explicit sub-kick layer;
- sparse decoration instead of fixed repeating decoration.

Fix these problems:

- `choir_call_symbols` and `choir_response_symbols` are sparse cue layers, not
  the theme. Their names make them look more important than they are.
- `sampled_organ_symbols` is a short response cue, not a sustained organ role.
  Rename or merge it so it cannot be mistaken for a structural layer.
- `pulse_rifle_left` and `pulse_rifle_right` are decorative projectile cues.
  They must not be perceived as a soft saw/pulse pseudo-melody.
- Decorative cues must not appear at fixed clock-like intervals.
- Transitions still rely too much on role on/off changes. They should change
  occupancy gradually.
- The current AMY choir sample layer still does not fully sound like a
  GarageBand `Classical Ensemble`; document it as a limited sampled chant
  approximation unless a better backend is added.

## Mandatory Role Model

Use these functional roles. Do not add more roles unless one of these is
insufficient and the reason is written in `说明.md`.

| Role | Track name | Function | Occupancy target in active sections | Motion rule | Relative level rule |
| --- | --- | --- | --- | --- | --- |
| Theme | `chant_classical_theme` | Main chant/classical-ensemble theme | >= 85% | conservative, slow turns only | loudest or within -3 dB of loudest |
| Theme support | `chant_response_sustain` | Sustained answer, not short shout | 40-80% when active | mostly shared tones with theme | within -3 to -8 dB of theme |
| Bass floor | `bass_sustain_floor` | Low weight and continuity | >= 85% | root/fifth/octave only | within -3 to -8 dB of theme |
| Bass drive | `bass_drive_rock` | Motif pulse and motion | 30-55% | repetitive cell, low variation | within -4 to -10 dB of theme |
| Harmony | `harmony_oath_pad` | Filling and harmonic gravity | >= 70% | staged chord expansion | within -5 to -12 dB of theme |
| Drums | `drum_rock_core` | Stable kick/snare/hat groove | stable pattern, not rain texture | regular accents | kick/snare audible, hats subordinate |
| Low drum | `drum_sub_kick` | Heavy low drum impact | tied to strong beats only | no random fills | audible but not masking bass |
| Secondary answer | `oath_answer_cue` | Short organ/brass/choir answer | <= 15% | call-response only | at least -10 dB below theme |
| Scene FX | `scene_fx_cues` | teleport, rifle, heat, shield, shell | <= 3% each | one-off trigger events | at least -18 dB below theme |

Forbidden structural roles:

- separate `pulse_rifle_left` and `pulse_rifle_right` tracks;
- separate `heat_meter`, `counter_oath_pins`, and `drum_shell_ticks` as
  recurring pattern layers;
- multiple soft saw/pulse pseudo-lead tracks;
- short choir shouts as the theme.

Allowed replacement:

- merge all rifle/heat/pin/shell details into one low-level `scene_fx_cues`
  track or a single bus whose MIDI export is clearly named `scene_fx_cues`;
- keep `oath_answer_cue` for short organ/brass/choir responses, but it must not
  be the main chant layer.

## Call-Response Structure

The theme is not a melody-only lead. It is a slow, high-occupancy chant layer.
The response is also sustained enough to be perceived as music, not a cue.

Use this hierarchy:

1. `chant_classical_theme` states the current section's stable tone/chordal
   center.
2. `bass_sustain_floor` and `harmony_oath_pad` confirm the same center.
3. `bass_drive_rock` and `drum_rock_core` provide groove.
4. `chant_response_sustain` enters after the theme is established.
5. `oath_answer_cue` answers only at important phrase points.
6. `scene_fx_cues` mark gameplay transitions only.

Do not write a fast-changing top-line melody. If a track changes pitch several
times in a bar, it is an ornament by default and must be quiet.

## Transition Rules

No hard role swaps except for deliberate one-beat tactical cuts.

For each section entrance:

1. Bars 1-2: minimal valid cell.
   - theme root/fifth or one sustained sampled chord;
   - bass floor only;
   - kick/snare skeleton.
2. Bars 3-4: partial expansion.
   - add response sustain;
   - add bass drive;
   - expand harmony from root/fifth to triad or suspended chord.
3. Bars 5+: full section.
   - full theme layer;
   - full rock groove;
   - optional answer cue at phrase points.

For each exit:

1. remove decoration first;
2. thin response sustain;
3. thin harmony;
4. leave theme or bass as the handoff;
5. only then change section center.

The same track should change occupancy smoothly. Do not implement breath by
turning a track completely off and another unrelated track on in the same beat.

## Ornament Rules

Ornaments are allowed only at:

- section starts;
- section exits;
- call-response handoff points;
- heat/teleport/shield gameplay events;
- rare late-section escalation points.

Ornaments are not allowed to repeat every fixed number of bars throughout the
piece. If the same ornament appears predictably every few seconds, remove it or
promote it into a regular groove role with high rhythmic regularity and lower
melodic variation.

Required limits:

- each scene FX role occupancy <= 3%;
- all merged scene FX at least -18 dB below `chant_classical_theme`;
- no more than one scene-FX event cluster per section half unless the section
  is explicitly a transition section;
- no decorative track may be louder than bass, harmony, theme, or drum core.

## Track Consolidation Rules

Track identity is `timbre + broad function`.

Merge these in v5:

- `pulse_rifle_left` + `pulse_rifle_right` -> `scene_fx_cues`;
- `heat_meter` -> `scene_fx_cues`;
- `counter_oath_pins` -> `scene_fx_cues`;
- `drum_shell_ticks` -> either `scene_fx_cues` or remove;
- `sampled_organ_symbols` -> either `oath_answer_cue` or a true sustained
  organ/ensemble support layer.

Rename these:

- `sampled_chant_bed` -> `chant_classical_theme`;
- `choir_call_symbols` -> `chant_call_cue_symbols` if kept;
- `choir_response_symbols` -> `chant_response_sustain_symbols` only if it
  becomes sustained; otherwise `chant_response_cue_symbols`.

## Timbre Guidance

The target is close to a GarageBand-style `Classical Ensemble` or chant/choir
pad, not horror choir, not short ghostly shouts.

Near-term internal approximation:

- use `OVATION D3.wav`, `ANGLECHOIR-C.wav`, and `CH.ORGAN D 3.wav` only as
  sustained layers or secondary responses;
- avoid exposed short choir slices as the main motif;
- if short samples must be loop-stretched, hide artifacts under harmony and
  bass rather than making them foreground;
- write `说明.md` honestly: this is a sampled approximation, not a solved
  realistic classical ensemble.

Better future route:

- replace this role with SFZ/SF2/AU/VST rendering when an accessible classical
  ensemble or choir asset is available;
- keep the same symbolic role names and validation rules.

## Validation Requirements

v5 is not acceptable unless `基础验证.json` contains:

- `relative_bus_balance`;
- `track_occupancy`;
- a `role_contract` section summarizing theme/support/ornament roles;
- `ornament_event_counts` for scene FX.

Minimum metric targets:

- `chant_classical_theme` occupancy >= 85%;
- `chant_classical_theme` relative level = 0 to -3 dB from loudest;
- `bass_sustain_floor` occupancy >= 85%;
- `harmony_oath_pad` occupancy >= 70%;
- `bass_drive_rock` occupancy 30-55%;
- each scene FX track occupancy <= 3%;
- merged scene FX bus <= -18 dB relative to `chant_classical_theme`;
- no cue/ornament role may be in the top five relative RMS roles;
- output duration 235-245 seconds;
- master peak <= 0.95;
- no NaN samples.

The report should also print the top 15 occupancy roles and top 15 relative RMS
roles after render.

## Required Output Directory

Use a new output directory:

```text
output/analysis/thermocline_holy_war_battle_demo_v5/
```

Required files:

```text
01_thermocline_holy_war_battle_master.mp3
01_thermocline_holy_war_battle_master.wav
01_thermocline_holy_war_battle_full.mid
02_theme_bass_harmony_only.mp3
03_drums_only.mp3
04_no_scene_fx_mix.mp3
05_scene_fx_only.mp3
stem_mp3/
source/generate_thermocline_holy_war_battle_demo.py
source/结构_score.json
基础验证.json
分组stem电平.csv
说明.md
```

## Claude Code Execution Plan

Suggested handoff prompt:

```text
Read docs/THERMOCLINE_CALL_RESPONSE_V5_SPEC.md and implement v5 exactly from
that spec. Preserve existing v4 output. Edit scripts/generate_thermocline_holy_war_battle_demo.py
and update README only if needed. Render output/analysis/thermocline_holy_war_battle_demo_v5/
with all required MP3/WAV/MID/JSON/CSV/说明.md artifacts. Do not add a lead
melody. Do not promote cue hits into foreground roles.
```

1. Edit only `scripts/generate_thermocline_holy_war_battle_demo.py` unless a
   small README pointer update is needed.
2. Preserve v4 output; write v5 to the new directory above.
3. Rename and consolidate roles according to this spec.
4. Replace short `choir_call` foreground behavior with sustained
   `chant_classical_theme` and `chant_response_sustain`.
5. Merge projectile/heat/pin/shell details into `scene_fx_cues`, or remove
   them if they do not serve a section handoff.
6. Implement staged activation/deactivation inside the section generator.
7. Add validation fields and fail/pass checks listed above.
8. Render the full set of output files.
9. Run:

```bash
python -m py_compile scripts/generate_thermocline_holy_war_battle_demo.py
python scripts/generate_thermocline_holy_war_battle_demo.py
git diff --check -- scripts/generate_thermocline_holy_war_battle_demo.py README.md
```

10. In `说明.md`, state known timbre limitations plainly. Do not claim the AMY
    sample approximation is a full classical ensemble.

## Acceptance Summary

The main question for v5 is not "are there many tracks?" It is:

```text
Can the listener identify a sustained chant/classical theme, supported by bass,
harmony, and drums, while decorative gameplay cues remain subordinate?
```

If the answer is no, reject the render even if the script passes technically.
