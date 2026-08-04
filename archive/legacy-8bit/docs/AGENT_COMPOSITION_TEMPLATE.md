# Agent Composition Template

This template is a process contract for an autonomous composition Agent. It
contains no musical content by itself. Fill it from the human brief and the
local project inventory.

## 0. Operating Rule

- Follow [Fixed Pattern Composition Protocol](FIXED_PATTERN_COMPOSITION_PROTOCOL.md).
- Keep all editable musical decisions in JSON cards, composition dictionaries,
  and Python scripts.
- Use external adapters for analysis, preview, conversion, or final-stage
  polishing.
- Do not make a melody-only draft the gate for the whole song.
- Build a no-lead baseline first. The baseline should be carried by support
  roles such as bass, drums, arps, harmony, counters, and FX.
- Treat foreground melody as absent by default. Add it only after an A/B render
  shows it improves the already-working no-lead baseline.
- Do not use `examples/thermocline_chatb_direct_v1/` as the quality target.
  It is process evidence. The successful Thermocline lesson is the stricter
  no-lead revision derived from `examples/thermocline_v1_reconsidered/`.

## 1. Human Intent

```yaml
emotion:
scene:
energy_curve:
duration_or_loop_constraints:
references_or_avoidances:
hard_technical_constraints:
```

## 1.5 Upper-Layer Cards

Fill these before writing notes. Leave fields blank or descriptive if the human
brief does not specify content; do not invent concrete musical material merely
to satisfy the template.

```yaml
motif_card:
  id:
  cross_role_event_cell:
  section_change_policy:
groove_card:
  id:
  pulse_policy:
  accent_hierarchy:
section_cards:
  - id:
    function:
    role_activation:
role_budget_card:
  id:
  density_limits:
  foreground_limits:
  occupancy_targets:
  ornament_limits:
transition_policy_card:
  id:
  staged_activation:
  staged_deactivation:
  call_response_handoffs:
timbre_cards:
  - id:
    target_function:
    asset_or_backend:
backend_cards:
  - id:
    backend:
    boundary:
```

## 2. Local Inventory

```yaml
instrument_cards:
  - id:
    role:
    reason_to_use:
    needs_project_specialization:
macro_cards:
  - id:
    gesture_type:
    compatible_roles:
existing_examples_to_compare:
  - path:
    reason_to_compare:
external_adapters_available:
  muspy:
  music21:
  amy:
  external_process:
```

## 3. Instrument Vocabulary Plan

```yaml
selected_cards:
  - card_id:
    role:
    source_card_or_new_card:
    compatibility_requirements:
    project_specific_overrides:
new_cards_needed:
  - proposed_id:
    role:
    engine:
    schema_fields_to_define:
```

## 4. Macro Vocabulary Plan

```yaml
selected_macros:
  - macro_id:
    role_usage:
    compatibility_requirements:
new_macros_needed:
  - proposed_id:
    gesture_intent:
    renderer_fx_or_adapter_target:
```

## 5. Section Plan

```yaml
sections:
  - id:
    function:
    energy:
    density:
    roles_active:
    transition_in:
    transition_out:
loop_strategy:
```

## 6. Role-First Arrangement Plan

```yaml
support_engine:
  bass:
    job:
    density_budget:
    active_section_occupancy_target:
    melodic_motion_limit:
    register_policy:
  drums:
    job:
    density_budget:
    accent_policy:
  harmony_or_pad:
    job:
    density_budget:
    active_section_occupancy_target:
    chord_expansion_policy:
    register_policy:
  chant_or_classical_theme:
    job:
    active_section_occupancy_target:
    melodic_motion_limit:
    call_response_policy:
    must_not_be_reduced_to_short_cues:
  arp_or_motion:
    job:
    density_budget:
    foreground_budget:
  fx_or_cues:
    job:
    placement_policy:
    relative_level_limit:
    repetition_policy:
    allowed_trigger_points:
foreground_policy:
  lead_default:
  no_lead_baseline_required:
  lead_admission_rule:
  counter_roles_allowed:
  silence_allowed:
  selection_criteria:
```

## 7. Variant Plan

```yaml
variant_batches:
  - batch_id:
    variable_to_change:
    fixed_constraints:
    render_outputs:
    analysis_outputs:
comparison_method:
promotion_rule:
rejection_rule:
```

## 8. Adapter Use Plan

```yaml
muspy:
  use_for:
  expected_output:
music21:
  use_for:
  expected_output:
amy:
  use_for:
  expected_output:
external_process:
  use_for:
  expected_output:
```

For choir, organ, aria-like, or other complex timbres, consult
[Complex Timbre Backends](COMPLEX_TIMBRE_BACKENDS.md). Do not claim a complex
sound has been solved by renaming an FM patch.

## 9. Validation Checklist

```yaml
structure:
  - sections exist and match the plan
  - roles enter and exit intentionally
  - loop or ending behavior is explicit
render:
  - local render completes
  - no-lead baseline render exists before any optional lead render
  - optional lead render is compared against the no-lead baseline
  - stems or comparison files are written
  - output path is recorded
agent_review:
  - adapter warnings are recorded
  - rejected variants have reasons
  - final selected variant has a reproducible script
  - theme-bearing roles have high active-section occupancy
  - roles with large melodic changes are treated as ornaments unless explicitly approved
  - functionally similar tracks are merged unless separate routing is required
  - transitions use staged activation/deactivation, not only hard cuts
listening_review:
  - human-listenable file exists
  - problems are written as concrete next edits
```

## 10. Output Log

```yaml
composition_script:
preset_cards_created_or_changed:
adapter_reports:
renders:
no_lead_baseline:
optional_lead_comparisons:
selected_version:
known_issues:
next_edit_targets:
```
