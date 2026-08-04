# Fixed Pattern Composition Protocol

This document states the current musical capability boundary of
epsilon-bit-ai-composer. It is intentionally conservative. The project can
produce useful results today when the Agent works inside a fixed, role-first
support-engine pattern. It should not pretend to be a general free-composition
system.

## Capability Boundary

Current reliable mode:

```text
human emotion / scene / constraint
  -> structured cards
  -> no-lead support engine
  -> deterministic demo render
  -> variants and listening selection
  -> optional external final-stage backend
```

Current unreliable mode:

```text
human emotion / scene / constraint
  -> LLM invents motif
  -> LLM writes melody_only
  -> arrangement is built around that melody
```

The second mode is rejected as the default workflow. The Thermocline case
showed that lead-melody attempts can damage an otherwise usable track. The
stronger result came after deleting the lead and letting bass, drums, arps,
harmony, counters, and FX carry the piece.

## Fixed Pattern

The default composition regime is:

- Build the song as a support engine first.
- Treat foreground lead as absent by default.
- Use bass, drums, arps, harmony, counters, stabs, and FX as the foreground
  material.
- Let motif mean a repeatable cross-role event cell, not a singable melody.
- Change motif behavior mainly at section boundaries.
- Upgrade energy by density, register, timbre, motion, and role activation,
  not by constantly inventing new themes.
- Promote only variants that survive listening, stem solo checks, and A/B
  comparison against the no-lead baseline.

This means the current system is closer to an arranger / pattern engine than a
melodic composer. That is not a small limitation. It is the central design
constraint.

## Motif Definition

In this project, a good motif is not primarily a note contour. A good motif is
a stable expectation pattern distributed across roles.

Examples of motif dimensions:

- rhythmic cell;
- bass accent placement;
- kick/snare answer pattern;
- arp pickup or turn;
- harmony stab timing;
- FX or counter cue placement;
- section-level omission and return.

The Agent should write these as explicit cards and budgets before writing dense
notes. If a proposed motif cannot be expressed as cross-role behavior, it is
not yet ready to become a composition plan.

## Theme, Occupancy, And Ornament Rules

Do not confuse cue density with musical density. A track that fires short events
for less than roughly one tenth of each active bar is usually a cue or ornament,
not a theme, even if its peak level is high.

Theme-bearing roles must satisfy all of these constraints inside the sections
where they are active:

- high occupancy, usually sustained or frequently connected enough to be heard
  as continuous material;
- conservative melodic motion, with small changes or slow harmonic turns;
- stable function across several bars;
- relative loudness near the foreground only when the role is regular enough to
  be perceived as a base layer.

Ornament/cue roles are allowed to be irregular, but must stay subordinate:

- large note-to-note contour changes make a role ornamental by default;
- reversed, glitch, chirp, pin, rifle, shell, heat-flicker, and similar cue
  gestures must not dominate the mix;
- decorative effects are not suitable as fixed repeating layers. Do not place
  the same ornament every few bars like a clock unless it has been promoted to
  a regular groove role;
- use ornaments mainly at section boundaries, energy pivots, call-response
  handoffs, and one-off scene events;
- if an ornament is active in many bars, lower its relative level or merge it
  into a more stable role;
- do not promote two tracks with the same timbre and function merely to inflate
  track count.

Track identity means `timbre + broad function`, not `every pattern gets its own
track`. Functionally similar tracks should be merged unless they need different
mix treatment, backend routing, or section ownership.

## Transition And Breathing Rules

Breathing should not come from abruptly muting and unmuting unrelated tracks.
Use staged role activation instead:

- introduce a minimal valid cell first;
- after one or two bars, expand it into a partial chord, chant, or rhythm;
- after another one or two bars, expand to the full role;
- close roles in the reverse order, leaving an answering role active long enough
  to make the handoff audible.

For harmony or chant roles, prefer gradual occupancy changes over hard cuts.
For example, a chord layer can begin as a root/fifth, then add the octave, then
add the color tone. A chant layer can begin as a sustained tone, then add a
response, then add a mass/ensemble layer.

## Complex Timbre Theme Rule

If the brief asks for aria, choir, classical ensemble, or chant as the theme,
that role is a theme-bearing timbre, not a decorative sample. It must receive
the same high-occupancy and conservative-motion treatment as bass or harmony.
Short choir shouts may exist, but only as secondary call-response material.

## Upper-Layer Cards

`instrument_card` and `macro_card` are renderer-facing vocabulary. They are too
low-level to tell an Agent what makes a track work. A complete Agent plan should
add the following upper-layer cards above them.

### motif_card

Defines the event cell shared by roles.

```json
{
  "type": "motif",
  "id": "",
  "description": "",
  "cycle_beats": 0,
  "event_roles": [
    {
      "role": "",
      "event_function": "",
      "allowed_positions": [],
      "variation_rule": ""
    }
  ],
  "section_change_policy": "",
  "forbidden_behaviors": []
}
```

### groove_card

Defines the pulse, accent hierarchy, and motion feel.

```json
{
  "type": "groove",
  "id": "",
  "tempo_policy": "",
  "grid": "",
  "accent_layers": [
    {
      "role": "",
      "accent_function": "",
      "density_budget": ""
    }
  ],
  "swing_or_push_policy": "",
  "silence_policy": ""
}
```

### section_card

Defines arrangement function instead of melodic content.

```json
{
  "type": "section",
  "id": "",
  "function": "",
  "energy": "",
  "length_beats": 0,
  "active_roles": [],
  "new_material_allowed": false,
  "motif_transform": "",
  "transition_in": "",
  "transition_out": ""
}
```

### role_budget_card

Prevents the Agent from making every role busy at the same time.

```json
{
  "type": "role_budget",
  "id": "",
  "roles": [
    {
      "role": "",
      "foreground_budget": "",
      "density_limit": "",
      "register_limit": "",
      "must_leave_space_for": []
    }
  ],
  "collision_rules": []
}
```

### timbre_card

Keeps sound design separate from note writing.

```json
{
  "type": "timbre",
  "id": "",
  "target_function": "",
  "engine": "",
  "source_asset": "",
  "fallback_engine": "",
  "articulation_policy": "",
  "compatibility_requirements": []
}
```

### backend_card

States which renderer or external tool is responsible for the final sound.

```json
{
  "type": "backend",
  "id": "",
  "backend": "",
  "license_boundary": "",
  "input_format": "",
  "output_format": "",
  "failure_fallback": "",
  "agent_may_change": []
}
```

## Agent Operating Rules

An Agent should fill upper-layer cards before creating notes.

Minimum order:

```text
human brief
  -> motif_card
  -> groove_card
  -> section_card
  -> role_budget_card
  -> instrument_card / macro_card selection
  -> no-lead composition script
  -> stems and validation
  -> variants
  -> optional final backend
```

Rules:

- Do not start from `melody_only`.
- Do not create a lead just because the brief says emotional, vocal, aria,
  lyrical, or dramatic.
- Do not use instrument names as proof of timbre quality.
- Keep rejected variants and reasons in the output log.
- A lead is admitted only when the no-lead baseline already works and the lead
  A/B render is better.
- If the Agent cannot explain which role carries the motif at each section, the
  plan is incomplete.

## Promotion Tests

A generated piece should not be promoted unless it passes:

- no-lead baseline render exists;
- stems exist for bass, drums, harmony/pad, arp/motion, counters, and FX where
  applicable;
- the motif remains recognizable when any single nonessential role is muted;
- density increases do not erase the groove;
- adapter warnings are written down;
- final selection is based on listening, not only symbolic metrics.

## Practical Reading Of The Limitation

The current project can still be useful. It can generate and refine many
controlled variants inside a known arrangement philosophy. That is enough for
game BGM, loops, combat states, and texture-driven tracks.

It is not yet enough for arbitrary style transfer, realistic vocal writing, or
high-quality independent lead-melody invention. Those require either stronger
composition models, external symbolic corpora with careful constraints, or
human-curated motif decisions.
