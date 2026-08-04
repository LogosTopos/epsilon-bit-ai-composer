# GitHub Release Checklist

## Before Commit

Run:

```bash
git status --short
du -sh .
python -m py_compile src/ebit/renderer.py src/ebit/presets.py scripts/generate_thermocline_v1.py scripts/generate_thermocline_chatb_direct.py scripts/generate_thermocline_no_lead_expanded.py scripts/render_preset_demo.py
```

Confirm:

- no virtualenvs,
- no `.DS_Store`,
- no `output/`,
- no generated WAV files,
- only curated MP3/MIDI examples under `examples/`.
- preset cards load with `scripts/render_preset_demo.py`.

## Smoke Test

```bash
python scripts/generate_thermocline_no_lead_expanded.py
python scripts/render_preset_demo.py
```

Expected marker:

```text
validation_pass=True
```

Expected output:

```text
output/analysis/温跃层战斗BGM_v1_no_lead_expanded/01_温跃层_no_lead_expanded_master.mp3
output/preset_demo/preset_demo.mp3
```

## GitHub Authentication

Do not use GitHub email/password for command-line pushes. Use existing `git` credentials, GitHub CLI, SSH, or a personal access token.

Useful command if not already authenticated:

```bash
gh auth login
```

## Suggested Release Assets

After regenerating the no-lead output, attach these as GitHub Release assets:

- `01_温跃层_no_lead_expanded_master.mp3`
- `02_bass_drums_only.mp3`
- `03_harmony_arps_only.mp3`
- `04_no_fx_mix.mp3`
- optional zipped `stem_mp3/`
