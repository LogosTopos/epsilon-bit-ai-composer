# Agent-Friendly Workflow Reassessment

Date: 2026-05-26

Question:

Can the pulled external libraries improve the failed workflow:

```text
emotion/need -> LLM motif -> melody_only -> add drums/harmony/bass -> full song
```

or should the workflow itself be replaced?

## TL;DR

The old melody-first workflow is not reliable enough as the main path.

The better Agent workflow is:

```text
emotion/need
  -> structured brief
  -> instrument + macro vocabulary
  -> section / groove / bass / harmony / arp engine
  -> many foreground-cell variants
  -> optional lead/counter selection
  -> demo render + validation
  -> final polishing backend
```

External libraries help most with:

- structured representation,
- batch variant generation,
- validation,
- richer rendering,
- final polishing.

They do not, by themselves, solve "LLM writes a good lead melody".

## Agent-Friendly Criteria

A component is Agent-friendly if it has most of these properties:

1. Text/JSON/Python API, not GUI-only.
2. Deterministic or reproducible output.
3. Small, inspectable intermediate objects.
4. Batch mode support for many variants.
5. Clear errors and validation hooks.
6. License can fit the project architecture.
7. Works without requiring the Agent to "hear" subjectively at every step.

## Agent-Friendliness Map

| Project | Agent-friendly? | Best Agent use | Limitation |
| --- | --- | --- | --- |
| Current `ebit` renderer/cards | Very high | Agent emits JSON cards, macros, tracks, scripts; renderer gives deterministic stems/MIDI/validation. | Current schema is still informal and hard-coded composition scripts dominate. |
| AMY | High | Agent can choose synth engines/patch params and render richer instrument cards. | Needs adapter and card schema; does not compose melody. |
| MusPy | High | Agent can manipulate symbolic representations, batch evaluate MIDI, convert formats. | Helps structure/evaluation, not taste. |
| music21 | High | Agent can validate key, contour, interval leaps, chord fit, phrase rules. | Classical/theory bias; no direct "sounds good" guarantee. |
| sfizz | Medium | Agent can reference SFZ/sample instrument cards. | More asset/backend than composer; SFZ complexity needs a scoped subset. |
| Tone.js | Medium-High | Future browser preview/editor that consumes project JSON. | Frontend/playback layer, not composer. |
| DDSP | Medium | Later trainable timbre/timbre-transfer experiments. | Heavy ML stack; not first bridge from macro to demo. |
| AudioCraft | Medium | Sidecar sketch generator; can suggest audio directions. | Opaque audio output; poor fit for editable melody/card pipeline; weights may be noncommercial. |
| Riffusion | Medium-Low | API/server design reference for audio generation. | Spectrogram/audio generation is not explainable composition. |
| DawDreamer | Medium for Agent, High for final | Agent can build render graphs/VST automation if isolated. | GPL, runtime/VST dependency, final-stage not composition-stage. |
| pedalboard | Medium for Agent, High for final | Agent can specify effects chains. | GPL; does not solve demo composition. |
| Nasong | High conceptually | Code-as-music, `Value` signals, trainable instruments are close to the desired philosophy. | GPL; clean-room reimplementation only. |
| MAGDA | Medium | AI-chat-to-DSL and DAW UI design reference. | GUI/DAW app, GPL, not a Python package. |
| Web Synth | Medium conceptually | Modular graph/UI/preset-sharing reference. | GPL and web-specific. |
| RAVE | Low-Medium | Possible timbre model research. | License unclear/noncommercial risk; not composition workflow. |
| DSK ai Synth | Low | Manual external source for WAV/SFZ-like assets. | No public source/API found; not Agent-native. |

## Why `motif -> melody_only` Failed

The failure is structural, not just a missing library.

Correction after later review: `examples/thermocline_chatb_direct_v1/` is not
the best result and should not be used as the quality target. The better
Thermocline direction came from applying a stricter no-lead edit to
`examples/thermocline_v1_reconsidered/`: delete the melody role completely and
let bass, drums, arps, harmony and supporting FX carry the track.

```text
/Users/topologyw/Documents/QQ下载/01_温跃层_no_lead_expanded_master.mp3
```

That local file was later deleted, but the lesson is still reproducible from
the checked-in no-lead script and the `thermocline_v1_reconsidered` source
direction. The relevant process evidence is:

- melody-only path was abandoned,
- bass and drums enter first,
- lead/melody is removed rather than merely delayed or quieted,
- harmony/arp groups are raised into the support engine,
- ornament slots remain as support/cue material, not lead melody.

This implies the successful pattern was:

```text
support engine first -> no-lead baseline -> optional lead only if A/B proves it helps
```

not:

```text
lead melody first -> add accompaniment later
```

The melody-first workflow is fragile because:

1. Lead melody needs aesthetic judgment.
   - LLMs can output valid notes, but they do not reliably judge singability,
     contour, repetition, hook value or annoyance.

2. Melody-only removes the context that makes a phrase work.
   - Bass rhythm, drum grid, harmonic rhythm, register, timbre and gaps often
     decide whether a motif feels good.

3. LLM-generated motifs tend to over-specify note sequences.
   - They under-specify role, density, contour, breath, foreground budget and
     transition behavior.

4. The "best" result came from foreground redistribution.
   - Bass, drums, arps and stabs carried the musical identity better than a
     conventional lead line.

## Can External Libraries Optimize `motif -> melody_only`?

Partially, but not enough to make it the main path.

### What They Can Improve

music21 can check:

- key fit,
- chord tones vs non-chord tones,
- contour,
- interval leaps,
- phrase cadence,
- repeated motifs.

MusPy can help with:

- symbolic representations,
- batch candidate generation,
- MIDI import/export,
- objective metrics.

AMY can help with:

- fast preview of instrument-card variants,
- richer timbre while staying parameterized.

Tone.js can help with:

- browser-side preview,
- interactive review,
- later human/Agent editing UI.

### What They Cannot Solve Alone

They cannot reliably answer:

```text
Is this lead melody actually good?
Does this hook feel like the intended game emotion?
Is this foreground role better as lead, bass riff, arp, counter, or drum fill?
```

So the libraries can improve validation and search, but not rescue a pure
melody-first design.

## Better Bridge From `instrument + macro` To `demo`

The bridge should be a role-first demo compiler, not a melody-only compiler.

Recommended intermediate objects:

```text
EmotionBrief
SectionPlan
RoleBudget
GroovePlan
HarmonicPlan
MotifCell
ForegroundPolicy
ArrangementPlan
RenderPlan
ValidationReport
```

The Agent should produce and revise these, rather than directly emitting a
single lead melody.

## Proposed New Agent Workflow

### Step 1: Human Input

Human provides only:

```text
emotion, scene, energy curve, references, hard constraints
```

Example:

```text
cold high-speed teleport combat, no heroic melody, bass/drums carry motion,
leave space for UI cues, loopable 70-90 seconds
```

### Step 2: Agent Builds Vocabulary

Agent selects or specializes:

```text
instrument cards
macro cards
role presets
section templates
```

### Step 3: Agent Builds Support Engine First

Generate:

```text
bass pattern
drum grid
harmonic rhythm
arp texture
counter/FX slots
```

This matches the corrected Thermocline lesson: a strict no-lead support engine
is the baseline, not the ChatB direct folder.

### Step 4: Agent Generates Foreground Cells

Generate many short candidates:

```text
motif cells
pickup cells
counter cells
arp cells
bass fill cells
drum fill cells
lead fragments
```

Do not force them into one lead melody yet.

### Step 5: Batch Render and Score

Use current renderer / AMY preview to create many variants.

Use music21/MusPy-like checks for:

- register,
- density,
- contour,
- phrase gaps,
- chord fit,
- repetition,
- foreground bus conflicts.

### Step 6: Foreground Selection

Choose one policy:

```text
no lead
delayed soft lead
bass-led hook
arp-led hook
call-response counters
drums + FX hook
```

This is where the old workflow forced "lead melody" too early.

### Step 7: Demo Compile

Compile selected roles into:

```text
score JSON
MIDI
master MP3
stems
validation report
```

### Step 8: Final Polish

Only after the demo is structurally good:

```text
DawDreamer-like graph
pedalboard-like effects chain
sfizz/AMY higher quality backend
manual or Agent-assisted mix revisions
```

## Best External Structures For Crossing The Gap

There is no single external library that directly solves:

```text
instrument + macro -> good demo
```

But a mature composite bridge exists:

| Need | Best pulled component |
| --- | --- |
| Structured symbolic representation | MusPy |
| Music-theory validation | music21 |
| Parameterized synth preview | AMY |
| Current deterministic render/stems | `ebit` |
| Future browser review | Tone.js |
| Final graph/VST/effects idea | DawDreamer/pedalboard, quarantined |

This means the strongest bridge is not one library; it is a protocol plus
variant-search loop.

## Revised Core Thesis

Do not ask the Agent to write "a good melody".

Ask the Agent to:

```text
build a role-balanced engine,
generate many foreground candidates,
render them,
validate them,
choose a foreground policy,
then optionally promote one candidate into a lead.
```

The lead is an optional result of arrangement search, not the seed of the whole
composition.

## Implementation Recommendation

Next technical milestone:

```text
AgentDemoPlanner v0
```

Inputs:

```json
{
  "emotion": "cold high-speed teleport combat",
  "energy_curve": ["sparse", "engine lock", "pressure", "combat return"],
  "foreground_policy": "bass_drums_arp_first",
  "allow_lead": "delayed_soft_only"
}
```

Outputs:

```text
SectionPlan
RoleBudget
selected instrument cards
selected macro cards
8-16 demo variants
validation reports
```

Only after this exists should the project invest in final-stage backends.
