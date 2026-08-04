#!/usr/bin/env python3
"""Extract minimal repeating units (motifs/cells) from reference MIDI files.

A "motif" is the smallest melodic-rhythmic unit that repeats identically or
with variation. This script finds them by scanning for:
  1. Exact rhythmic-pattern repetition
  2. Pitch-interval sequence repetition (transposition-invariant)
  3. Combined rhythmic+interval pattern repetition

Each detected motif is output with its note sequence, occurrence positions,
and transpositions.
"""

from __future__ import annotations

import json, sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "research" / "external_sources" / "permissive" / "music21"))
from music21 import converter

OUT_DIR = PROJECT_ROOT / "output" / "analysis" / "motif_extraction_v1"
MIDI_DIRS = [
    PROJECT_ROOT / "examples" / "highspeed_reference_midi_v1" / "midi",
    PROJECT_ROOT / "examples" / "community_midi_analysis_v1" / "midi",
]


def extract_primary_voice(score) -> list[dict[str, Any]]:
    """Get the primary melodic voice as a sequence of (onset, duration, pitch) events."""
    if score.hasPartLikeStreams():
        parts = list(score.parts)
        primary = max(parts, key=lambda p: len([n for n in p.flatten().notes if n.isNote and n.pitch]))
    else:
        primary = score

    notes = []
    for n in primary.flatten().notes:
        if n.isNote and n.pitch:
            notes.append({
                "onset": float(n.offset),
                "duration": float(n.quarterLength),
                "pitch": n.pitch.midi,
            })
    notes.sort(key=lambda x: x["onset"])
    return notes


def rhythm_pattern(notes: list[dict], start: int, length: int) -> tuple[float, ...]:
    """Extract duration ratios for a window of notes, normalized to first duration."""
    durs = [notes[i]["duration"] for i in range(start, min(start + length, len(notes)))]
    if not durs or durs[0] == 0:
        return tuple()
    return tuple(round(d / durs[0], 2) for d in durs)


def interval_pattern(notes: list[dict], start: int, length: int) -> tuple[int, ...]:
    """Extract pitch intervals (semitones) for a window of notes."""
    pitches = [notes[i]["pitch"] for i in range(start, min(start + length, len(notes)))]
    if len(pitches) < 2:
        return tuple()
    return tuple(pitches[i] - pitches[i - 1] for i in range(1, len(pitches)))


def onset_pattern(notes: list[dict], start: int, length: int) -> tuple[float, ...]:
    """Extract inter-onset intervals for a window of notes."""
    onsets = [notes[i]["onset"] for i in range(start, min(start + length, len(notes)))]
    if len(onsets) < 2:
        return tuple()
    return tuple(round(onsets[i] - onsets[i - 1], 2) for i in range(1, len(onsets)))


def find_motifs(notes: list[dict], min_len: int = 3, max_len: int = 16) -> list[dict[str, Any]]:
    """Find all repeating motifs (3-16 notes) in the primary voice.

    Returns motifs sorted by (occurrence_count * pattern_length) — a measure of
    structural importance.
    """
    n = len(notes)
    if n < min_len * 2:
        return []

    # Store all found patterns: key -> list of (start_index, length)
    rhythmic: dict[tuple, list[tuple[int, int]]] = defaultdict(list)
    intervallic: dict[tuple, list[tuple[int, int]]] = defaultdict(list)
    combined: dict[tuple, list[tuple[int, int]]] = defaultdict(list)

    min_gap = 4  # minimum notes between occurrences (avoid overlapping windows)

    for length in range(min_len, min(max_len + 1, n - min_len)):
        for start in range(0, n - length):
            # Rhythmic pattern (onset intervals)
            rp = onset_pattern(notes, start, length)
            if len(rp) >= min_len - 1:
                # Check previous occurrences
                is_new = True
                for prev_start, prev_len in rhythmic.get(rp, []):
                    if abs(start - prev_start) < length:
                        is_new = False
                        break
                if is_new:
                    # Find other occurrences
                    for other in range(0, n - length):
                        if abs(other - start) >= min_gap:
                            op = onset_pattern(notes, other, length)
                            if op == rp:
                                rhythmic[rp].append((other, length))

            # Intervallic pattern (pitch intervals — transposition-invariant)
            ip = interval_pattern(notes, start, length)
            if len(ip) >= min_len - 1:
                is_new = True
                for prev_start, prev_len in intervallic.get(ip, []):
                    if abs(start - prev_start) < length:
                        is_new = False
                        break
                if is_new:
                    for other in range(0, n - length):
                        if abs(other - start) >= min_gap:
                            op = interval_pattern(notes, other, length)
                            if op == ip:
                                intervallic[ip].append((other, length))

            # Combined (rhythm + intervals)
            if len(rp) >= min_len - 1 and len(ip) >= min_len - 1:
                cp = (rp, ip)
                is_new = True
                for prev_start, prev_len in combined.get(cp, []):
                    if abs(start - prev_start) < length:
                        is_new = False
                        break
                if is_new:
                    for other in range(0, n - length):
                        if abs(other - start) >= min_gap:
                            op_onset = onset_pattern(notes, other, length)
                            op_int = interval_pattern(notes, other, length)
                            if op_onset == rp and op_int == ip:
                                combined[cp].append((other, length))

    # Build result list
    motifs = []

    # Combined patterns (most specific, highest quality)
    for (rp, ip), occurrences in combined.items():
        if len(occurrences) >= 2:
            motifs.append({
                "type": "rhythmic+intervallic",
                "length_notes": len(rp) + 1,
                "occurrences": len(occurrences),
                "rhythm_intervals": [round(x, 2) for x in rp],
                "pitch_intervals": list(ip),
                "positions": [{"start_note": s, "length": l} for s, l in occurrences[:8]],
                "score": len(occurrences) * (len(rp) + 1),
            })

    # Rhythmic-only patterns
    for rp, occurrences in rhythmic.items():
        if len(occurrences) >= 3:
            motifs.append({
                "type": "rhythmic",
                "length_notes": len(rp) + 1,
                "occurrences": len(occurrences),
                "rhythm_intervals": [round(x, 2) for x in rp],
                "positions": [{"start_note": s, "length": l} for s, l in occurrences[:8]],
                "score": len(occurrences) * (len(rp) + 1),
            })

    # Intervallic-only patterns
    for ip, occurrences in intervallic.items():
        if len(occurrences) >= 3:
            motifs.append({
                "type": "intervallic",
                "length_notes": len(ip) + 1,
                "occurrences": len(occurrences),
                "pitch_intervals": list(ip),
                "positions": [{"start_note": s, "length": l} for s, l in occurrences[:8]],
                "score": len(occurrences) * (len(ip) + 1),
            })

    motifs.sort(key=lambda m: m["score"], reverse=True)
    return motifs


def motif_to_notes(primary: list[dict], motif: dict) -> list[dict[str, Any]]:
    """Convert a motif pattern back to concrete note dictionaries for its first occurrence."""
    first = motif["positions"][0]
    start = first["start_note"]
    length = first["length"]
    return [
        {"pitch": primary[i]["pitch"], "onset": primary[i]["onset"],
         "duration": primary[i]["duration"]}
        for i in range(start, start + length)
    ]


def analyze_piece(path: Path) -> dict[str, Any]:
    """Extract all repeating motifs from one piece."""
    print(f"  {path.name}")
    score = converter.parse(path)
    primary = extract_primary_voice(score)

    if len(primary) < 6:
        return {"file": str(path.relative_to(PROJECT_ROOT)), "primary_note_count": len(primary),
                "motifs": []}

    motifs = find_motifs(primary, min_len=3, max_len=16)

    # Deduplicate: remove motifs that are subsets of larger motifs
    filtered = []
    for m in motifs:
        is_subset = False
        for m2 in filtered:
            if (m["type"] == m2["type"] and
                m["length_notes"] < m2["length_notes"] and
                len(m["positions"]) <= len(m2["positions"])):
                # Check if all positions of m are contained in m2
                m_starts = {p["start_note"] for p in m["positions"]}
                m2_starts = {p["start_note"] for p in m2["positions"]}
                if m_starts.issubset(m2_starts):
                    is_subset = True
                    break
        if not is_subset:
            filtered.append(m)

    # Take top motifs
    top = filtered[:12]

    # Annotate with actual note content for first occurrence
    for m in top:
        m["example_notes"] = motif_to_notes(primary, m)

    return {
        "file": str(path.relative_to(PROJECT_ROOT)),
        "primary_note_count": len(primary),
        "motif_count": len(filtered),
        "top_motifs": top,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reports_dir = OUT_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    all_midi = []
    for d in MIDI_DIRS:
        if d.exists():
            all_midi.extend(sorted(d.glob("*.mid")))

    print(f"Extracting motifs from {len(all_midi)} pieces...")
    all_results = []

    for midi_path in all_midi:
        try:
            r = analyze_piece(midi_path)
            all_results.append(r)
            stem = midi_path.stem
            (reports_dir / f"{stem}_motifs.json").write_text(
                json.dumps(r, ensure_ascii=False, indent=2, default=str) + "\n",
                encoding="utf-8")

            # Print summary
            print(f"\n  {stem[:50]}")
            for i, m in enumerate(r["top_motifs"][:5]):
                notes = m.get("example_notes", [])
                pitch_str = " ".join(str(n["pitch"]) for n in notes[:8])
                dur_str = " ".join(str(round(n["duration"], 1)) for n in notes[:8])
                print(f"    [{i+1}] {m['type']}, {m['length_notes']} notes, "
                      f"{m['occurrences']}× repeats | pitches: {pitch_str} | durs: {dur_str}")

        except Exception as exc:
            print(f"  ERROR: {midi_path.name}: {exc}")

    # Cross-piece summary
    summary = {
        "pieces_analyzed": len(all_results),
        "pieces_with_motifs": sum(1 for r in all_results if r["motif_count"] > 0),
    }
    (OUT_DIR / "motif_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(f"\nDone. {summary['pieces_with_motifs']}/{summary['pieces_analyzed']} pieces have repeating motifs.")
    print(f"Reports: {reports_dir}")


if __name__ == "__main__":
    main()
