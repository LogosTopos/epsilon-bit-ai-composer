#!/usr/bin/env python3
"""Exploratory structural analysis of reference MIDI files.

NO pre-defined templates. NO classification into pre-existing categories.
Only objective, measurable features extracted from each piece:
  - Measure-by-measure note density (raw array)
  - Onset distribution within the measure (16th-note grid histogram)
  - Inter-onset interval histogram
  - Pitch class / octave distribution
  - Rest position map
  - Self-similarity matrix (measure vs measure)
  - Note duration histogram
  - Simultaneous voice count over time

Output: raw feature JSON per piece + cross-piece comparison matrix.
"""

from __future__ import annotations

import json, math, sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "research" / "external_sources" / "permissive" / "music21"))

from music21 import converter

OUT_DIR = PROJECT_ROOT / "output" / "analysis" / "reference_deep_analysis_v2"
MIDI_DIRS = [
    PROJECT_ROOT / "examples" / "highspeed_reference_midi_v1" / "midi",
    PROJECT_ROOT / "examples" / "community_midi_analysis_v1" / "midi",
]
GRID_RESOLUTION = 16  # 16th-note grid


def extract_features(path: Path) -> dict[str, Any]:
    """Extract only objective, measurable features. No classification."""
    print(f"  {path.name}")
    score = converter.parse(path)
    f: dict[str, Any] = {"file": str(path.relative_to(PROJECT_ROOT))}

    # ── Flatten all note events ──
    flat = score.flatten()
    all_objs = list(flat.notes)
    events = []
    for obj in all_objs:
        if obj.isNote and obj.pitch:
            events.append({
                "onset": float(obj.offset),
                "dur": float(obj.quarterLength),
                "pitch": obj.pitch.midi,
                "is_rest": False,
            })
        elif obj.isRest:
            events.append({
                "onset": float(obj.offset),
                "dur": float(obj.quarterLength),
                "pitch": None,
                "is_rest": True,
            })

    if not events:
        return f

    events.sort(key=lambda e: e["onset"])
    pitches_only = [e for e in events if e["pitch"] is not None]
    f["note_count"] = len(pitches_only)
    f["rest_count"] = sum(1 for e in events if e["is_rest"])

    # ── 1. Measure-by-measure density ──
    measures = list(flat.getElementsByClass("Measure"))
    density = []
    for m in measures:
        m_notes = [n for n in m.notes if n.isNote and n.pitch]
        density.append(len(m_notes))
    f["density_per_measure"] = density

    # ── 2. Onset distribution within the measure ──
    # For each note, compute its position within the measure (0-4 beats)
    onset_hist = Counter()
    for e in pitches_only:
        beat_in_bar = e["onset"] % 4.0
        grid_pos = int(beat_in_bar * GRID_RESOLUTION / 4.0) % GRID_RESOLUTION
        onset_hist[grid_pos] += 1
    f["onset_grid_histogram"] = {str(k): v for k, v in sorted(onset_hist.items())}

    # ── 3. Inter-onset interval distribution ──
    onsets = sorted(e["onset"] for e in pitches_only)
    ioi = [round(onsets[i] - onsets[i - 1], 3) for i in range(1, len(onsets))]
    ioi_hist = Counter()
    for interval in ioi:
        # Bucket by 16th-note (0.25 beat) resolution
        bucket = round(interval * 4) / 4  # quantize to 16th
        ioi_hist[bucket] += 1
    f["ioi_histogram"] = {str(k): v for k, v in sorted(ioi_hist.items())[:20]}
    if ioi:
        f["ioi_stats"] = {
            "mean": round(np.mean(ioi), 3),
            "median": round(np.median(ioi), 3),
            "std": round(np.std(ioi), 3),
            "min": round(min(ioi), 3),
            "max": round(max(ioi), 3),
        }

    # ── 4. Pitch distribution ──
    pitch_hist = Counter(e["pitch"] for e in pitches_only)
    f["pitch_range"] = {"min": min(pitch_hist.keys()), "max": max(pitch_hist.keys())}
    f["pitch_class_histogram"] = {str(k): v for k, v in
                                  sorted(Counter(p % 12 for p in pitch_hist.keys() for _ in range(pitch_hist[p])).items())}

    # ── 5. Rest positions ──
    rest_positions = []
    for e in events:
        if e["is_rest"]:
            rest_positions.append(round(e["onset"], 2))
    f["rest_positions"] = rest_positions[:30]  # first 30 rests
    f["rest_intervals"] = {}
    if len(rest_positions) > 1:
        rest_gaps = [round(rest_positions[i] - rest_positions[i - 1], 2)
                     for i in range(1, len(rest_positions))]
        rest_hist = Counter(rest_gaps)
        f["rest_intervals"] = {str(k): v for k, v in rest_hist.most_common(10)}

    # ── 6. Self-similarity matrix (measure vs measure) ──
    if len(density) >= 4:
        n = len(density)
        # Compare each measure to every other using density + pitch content
        sim_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                # Simple density correlation with context
                if i >= 1 and j >= 1:
                    # Compare 2-measure windows
                    wi = density[max(0, i - 1):min(n, i + 2)]
                    wj = density[max(0, j - 1):min(n, j + 2)]
                    # Pad to same length
                    max_len = max(len(wi), len(wj))
                    wi_pad = np.pad(wi, (0, max_len - len(wi)), constant_values=0)
                    wj_pad = np.pad(wj, (0, max_len - len(wj)), constant_values=0)
                    if np.std(wi_pad) > 0 and np.std(wj_pad) > 0:
                        corr = np.corrcoef(wi_pad, wj_pad)[0, 1]
                        sim_matrix[i, j] = 0 if np.isnan(corr) else corr
        f["self_similarity"] = {
            "shape": list(sim_matrix.shape),
            "summary": {
                "mean_similarity": round(float(np.mean(sim_matrix)), 3),
                "high_similarity_pairs": int(np.sum(sim_matrix > 0.7)),
            }
        }

    # ── 7. Note duration distribution ──
    dur_hist = Counter()
    for e in pitches_only:
        bucket = round(e["dur"] * 4) / 4
        dur_hist[bucket] += 1
    f["duration_histogram"] = {str(k): v for k, v in sorted(dur_hist.items())}

    # ── 8. Simultaneous voice count over time ──
    # Sample voice count at 16th-note intervals
    max_onset = max(e["onset"] + e["dur"] for e in pitches_only) if pitches_only else 0
    voice_samples = []
    t = 0.0
    while t < max_onset:
        active = sum(1 for e in pitches_only
                     if e["onset"] <= t < e["onset"] + e["dur"])
        voice_samples.append(active)
        t += 0.25
    if voice_samples:
        f["voice_count_stats"] = {
            "mean": round(np.mean(voice_samples), 1),
            "max": int(np.max(voice_samples)),
            "min": int(np.min(voice_samples)),
            "std": round(np.std(voice_samples), 1),
        }

    # ── 9. Phrase boundary detection (data-driven, not template) ──
    # A phrase boundary candidate is any point where:
    # (a) there is a rest ≥ 0.5 beats, OR
    # (b) the last note in a measure is ≥ 1.5x longer than the measure average
    boundaries = []
    for i, m in enumerate(measures):
        m_notes = [n for n in m.notes if n.isNote]
        if not m_notes:
            boundaries.append(i)  # empty measure is a boundary
            continue
        # Check for long final note
        last = m_notes[-1]
        last_dur = float(getattr(last, "quarterLength", 0.25))
        avg_dur = np.mean([float(getattr(n, "quarterLength", 0.25)) for n in m_notes])
        if last_dur >= avg_dur * 2.0 or last_dur >= 2.0:
            boundaries.append(i)
        # Check for internal rest
        rests = [n for n in m_notes if getattr(n, "isRest", False)]
        if any(float(getattr(r, "quarterLength", 0)) >= 1.0 for r in rests):
            boundaries.append(i)
    f["phrase_boundary_measures"] = sorted(set(boundaries))

    # ── 10. Key signature ──
    try:
        k = score.analyze("key")
        f["detected_key"] = {
            "tonic": k.tonic.name,
            "mode": k.mode,
            "correlation": getattr(k, "correlationCoefficient", None),
        }
    except Exception:
        f["detected_key"] = None

    return f


def build_comparison_matrix(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Cross-piece comparison: which pieces are structurally similar?"""
    names = [Path(r["file"]).stem for r in results]

    # Compare density curves (normalized and resampled to same length)
    densities = []
    for r in results:
        d = r.get("density_per_measure", [])
        if d:
            arr = np.array(d, dtype=float)
            if arr.max() > 0:
                arr = arr / arr.max()
            densities.append(arr)

    # Compute pairwise correlation of density curves
    cmp: dict[str, Any] = {"pieces": names}
    if len(densities) >= 2:
        # Resample all to median length
        target_len = int(np.median([len(d) for d in densities]))
        resampled = []
        for d in densities:
            if len(d) > 1:
                indices = np.linspace(0, len(d) - 1, target_len)
                resampled.append(np.interp(indices, np.arange(len(d)), d))
            else:
                resampled.append(np.zeros(target_len))

        n = len(resampled)
        sim = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    corr = np.corrcoef(resampled[i], resampled[j])[0, 1]
                    sim[i, j] = 0 if np.isnan(corr) else corr

        cmp["density_correlation_matrix"] = {
            "pieces": names,
            "matrix": [[round(float(sim[i, j]), 3) for j in range(n)] for i in range(n)],
        }

        # Find most similar pairs
        pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                pairs.append((names[i], names[j], float(sim[i, j])))
        pairs.sort(key=lambda x: x[2], reverse=True)
        cmp["most_similar_pairs"] = pairs[:10]

    # Compare IOI statistics
    ioi_means = [r.get("ioi_stats", {}).get("mean", 0) for r in results]
    ioi_stds = [r.get("ioi_stats", {}).get("std", 0) for r in results]
    cmp["ioi_comparison"] = {
        names[i]: {"mean": ioi_means[i], "std": ioi_stds[i]}
        for i in range(len(names))
    }

    # Compare pitch spans
    spans = [r.get("pitch_range", {}).get("max", 0) - r.get("pitch_range", {}).get("min", 0)
             for r in results]
    cmp["pitch_span_comparison"] = {names[i]: spans[i] for i in range(len(names))}

    # Compare voice count
    voice_means = [r.get("voice_count_stats", {}).get("mean", 0) for r in results]
    cmp["voice_density_comparison"] = {names[i]: voice_means[i] for i in range(len(names))}

    return cmp


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reports_dir = OUT_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    all_midi = []
    for d in MIDI_DIRS:
        if d.exists():
            all_midi.extend(sorted(d.glob("*.mid")))

    print(f"Analyzing {len(all_midi)} MIDI files (no templates, objective features only)")
    results = []

    for midi_path in all_midi:
        try:
            r = extract_features(midi_path)
            results.append(r)
            stem = midi_path.stem
            (reports_dir / f"{stem}.json").write_text(
                json.dumps(r, ensure_ascii=False, indent=2, default=str) + "\n",
                encoding="utf-8")
        except Exception as exc:
            print(f"  ERROR: {midi_path.name}: {exc}")

    # Cross-piece comparison
    cmp = build_comparison_matrix(results)
    (OUT_DIR / "cross_piece_comparison.json").write_text(
        json.dumps(cmp, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8")

    # Raw feature summary
    print(f"\nAnalyzed {len(results)} pieces. Key raw findings:")
    for r in results:
        name = Path(r["file"]).stem
        den = r.get("density_per_measure", [])
        ioi = r.get("ioi_stats", {})
        vc = r.get("voice_count_stats", {})
        key_info = r.get("detected_key", {})
        key_str = f"{key_info.get('tonic','?')} {key_info.get('mode','?')}" if key_info else "?"
        print(f"  {name[:40]:40s} | key={key_str:8s} | density µ={np.mean(den):.0f} σ={np.std(den):.0f} | "
              f"IOI µ={ioi.get('mean',0):.2f} | voices µ={vc.get('mean',0):.1f} max={vc.get('max',0)} | "
              f"range={r.get('pitch_range',{}).get('min',0)}-{r.get('pitch_range',{}).get('max',0)}")

    print(f"\nMost structurally similar pairs (density curve correlation):")
    for a, b, s in cmp.get("most_similar_pairs", [])[:5]:
        print(f"  {a[:30]} ↔ {b[:30]} : r={s:.3f}")

    print(f"\nReports: {OUT_DIR}")


if __name__ == "__main__":
    main()
