#!/usr/bin/env python3
"""Score analysis for reference MIDI files.

Objective, measurable features only (no style judgement):
  - key/mode estimate from pitch-class histogram (Krumhansl-Kessler weights)
  - per-track role guess (melody / bass / pad / drums) from register + density
  - melody contour summary (intervals, range, first 48 notes)
  - harmonic rhythm (unique pitch sets per bar)
  - rhythmic profile (16th-grid onset histogram, syncopation index, density curve)
  - structure (bar self-similarity matrix -> section segmentation)

Usage:
  python3 scripts/analyze_midi_scores.py <midi...> [--out DIR]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import mido
import numpy as np

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Krumhansl-Kessler major/minor key profiles (normalized)
KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def key_estimate(pitch_classes: np.ndarray) -> tuple[str, str, float]:
    hist = np.zeros(12)
    for pc in pitch_classes:
        hist[pc] += 1
    if hist.sum() == 0:
        return "?", "?", 0.0
    hist = hist / hist.sum()
    best_major, best_minor = -1.0, -1.0
    major_key, minor_key = 0, 0
    for tonic in range(12):
        corr_m = float(np.dot(hist, np.roll(KK_MAJOR, tonic)))
        corr_n = float(np.dot(hist, np.roll(KK_MINOR, tonic)))
        if corr_m > best_major:
            best_major, major_key = corr_m, tonic
        if corr_n > best_minor:
            best_minor, minor_key = corr_n, tonic
    if best_major >= best_minor:
        return NOTE_NAMES[major_key], "major", best_major
    return NOTE_NAMES[minor_key], "minor", best_minor


def parse_midi_events(path: Path) -> tuple[float, int, list[dict]]:
    """Return (bpm, ticks_per_beat, notes). notes: {ch, pitch, vel, start_tick, end_tick, program}"""
    mid = mido.MidiFile(str(path))
    tpb = mid.ticks_per_beat or 480
    bpm = 120.0
    for tr in mid.tracks:
        for msg in tr:
            if msg.type == "set_tempo":
                bpm = mido.tempo2bpm(msg.tempo)
                break
        else:
            continue
        break
    active: dict[tuple[int, int], tuple[int, int, int]] = {}
    notes: list[dict] = []
    program_of: dict[int, int] = defaultdict(int)
    for tr in mid.tracks:
        tick = 0
        for msg in tr:
            tick += msg.time
            if msg.type == "program_change":
                program_of[msg.channel] = msg.program
            elif msg.type == "note_on" and msg.velocity > 0:
                active[(msg.channel, msg.note)] = (tick, msg.velocity, program_of[msg.channel])
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in active:
                    st, vel, prog = active.pop(key)
                    notes.append({"ch": key[0], "pitch": key[1], "vel": vel, "start": st, "end": tick, "prog": prog})
    for (ch, note), (st, vel, prog) in active.items():
        notes.append({"ch": ch, "pitch": note, "vel": vel, "start": st, "end": st + tpb // 2, "prog": prog})
    return bpm, tpb, notes


def analyze(path: Path) -> dict:
    bpm, tpb, notes = parse_midi_events(path)
    if not notes:
        return {"file": str(path), "error": "no notes"}
    max_tick = max(n["end"] for n in notes)
    beat_sec = 60.0 / bpm

    drums = [n for n in notes if n["ch"] == 9]
    pitched = [n for n in notes if n["ch"] != 9]

    # ── key estimate (pitched only) ──
    pcs = np.array([n["pitch"] % 12 for n in pitched])
    tonic, mode, corr = key_estimate(pcs)

    # ── per-track role guess: group by (ch, prog) ──
    groups: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for n in pitched:
        groups[(n["ch"], n["prog"])].append(n)
    role_info = []
    for (ch, prog), grp in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        pitches = np.array([n["pitch"] for n in grp])
        density = len(grp) / max(1.0, (max_tick / tpb))
        role_info.append({
            "ch": ch, "program": prog,
            "notes": len(grp),
            "median_pitch": int(np.median(pitches)),
            "range": [int(pitches.min()), int(pitches.max())],
            "density_notes_per_beat": round(density, 3),
        })

    # melody track = highest median pitch among non-drum groups with enough notes
    melody = None
    if role_info:
        candidates = [r for r in role_info if r["notes"] > 30]
        if candidates:
            melody = max(candidates, key=lambda r: r["median_pitch"])
    melody_notes = []
    if melody:
        melody_notes = sorted(
            [n for n in groups[(melody["ch"], melody["program"])]],
            key=lambda n: n["start"],
        )

    # ── melody contour ──
    contour = {}
    if melody_notes:
        pitches = [n["pitch"] for n in melody_notes]
        intervals = np.diff(pitches)
        contour = {
            "note_count": len(pitches),
            "range_semitones": int(max(pitches) - min(pitches)),
            "interval_hist": {str(int(k)): v for k, v in Counter(intervals).most_common(8)},
            "first_48": [f"{NOTE_NAMES[p % 12]}{p // 12 - 1}" for p in pitches[:48]],
        }

    # ── harmonic rhythm: unique pitch-class sets per 4-beat bar ──
    beats_per_bar = 4
    n_bars = int(max_tick / tpb / beats_per_bar) + 1
    bar_sets = []
    for bar in range(n_bars):
        s = bar * beats_per_bar * tpb
        e = s + beats_per_bar * tpb
        pcs = {n["pitch"] % 12 for n in pitched if s <= n["start"] < e}
        bar_sets.append(pcs)
    changes = sum(1 for i in range(1, len(bar_sets)) if bar_sets[i] != bar_sets[i - 1])

    # ── rhythm profile (16th grid, all notes incl drums) ──
    grid = 16
    grid_hist = np.zeros(grid)
    onset_by_bar: list[int] = []
    for bar in range(n_bars):
        s = bar * beats_per_bar * tpb
        e = s + beats_per_bar * tpb
        count = 0
        for n in notes:
            if s <= n["start"] < e:
                count += 1
                slot = int((n["start"] - s) / tpb * grid) % grid
                grid_hist[slot] += 1
        onset_by_bar.append(count)
    grid_hist = grid_hist / grid_hist.sum() if grid_hist.sum() else grid_hist
    # syncopation proxy: weight of off-grid slots (not 0,4,8,12)
    sync = float(grid_hist[[i for i in range(16) if i % 4 != 0]].sum())

    # ── structure: bar fingerprint self-similarity ──
    def fingerprint(bar: int) -> tuple:
        s = bar * beats_per_bar * tpb
        e = s + beats_per_bar * tpb
        return tuple(sorted({n["pitch"] for n in pitched if s <= n["start"] < e}))

    fps = [fingerprint(b) for b in range(n_bars)]
    seg = [0]
    for b in range(1, n_bars):
        if fps[b] != fps[b - 1] and b - seg[-1] >= 2:
            seg.append(b)
    if seg[-1] != n_bars:
        seg.append(n_bars)
    sections = [{"start_bar": seg[i], "bars": seg[i + 1] - seg[i]} for i in range(len(seg) - 1)]

    duration = max_tick / tpb * beat_sec
    return {
        "file": str(path),
        "bpm": round(bpm, 1),
        "duration_sec": round(duration, 1),
        "total_notes": len(notes),
        "drum_notes": len(drums),
        "pitched_notes": len(pitched),
        "key_estimate": {"tonic": tonic, "mode": mode, "corr": round(corr, 3)},
        "tracks": role_info,
        "melody_track": melody,
        "melody_contour": contour,
        "harmonic_rhythm": {
            "bars": n_bars,
            "unique_pitch_sets": len(set(map(frozenset, bar_sets))),
            "changes": changes,
        },
        "rhythm": {
            "grid16_hist": [round(float(x), 4) for x in grid_hist],
            "syncopation_index": round(sync, 3),
            "onset_per_bar": onset_by_bar,
            "peak_density_bar": int(np.argmax(onset_by_bar)) if onset_by_bar else 0,
        },
        "structure_sections": sections,
        "avg_notes_per_bar": round(len(notes) / max(1, n_bars), 2),
    }


def render_md(a: dict) -> str:
    if "error" in a:
        return f"# {a['file']}\n\nERROR: {a['error']}\n"
    lines = [f"# {Path(a['file']).name}", ""]
    lines.append(f"- BPM: {a['bpm']} | 时长: {a['duration_sec']}s | 音符: {a['total_notes']}(旋律声部 {a['pitched_notes']} / 鼓 {a['drum_notes']})")
    k = a["key_estimate"]
    lines.append(f"- **调性估计**: {k['tonic']} {k['mode']}(Krumhansl-Kessler 相关度 {k['corr']})")
    lines.append("")
    lines.append("## 声部构成")
    lines.append("| 通道 | 音色 | 音符数 | 中位音高 | 音域 | 密度(音符/拍) |")
    lines.append("|---|---|---|---|---|---|")
    for t in a["tracks"]:
        lines.append(f"| {t['ch']} | {t['program']} | {t['notes']} | {t['median_pitch']} | {t['range'][0]}-{t['range'][1]} | {t['density_notes_per_beat']} |")
    lines.append("")
    m = a["melody_track"]
    if m:
        lines.append(f"## 主旋律轨:通道 {m['ch']} 音色 {m['program']}(中位音高 {m['median_pitch']})")
        c = a["melody_contour"]
        lines.append(f"- 音符数 {c['note_count']},音域 {c['range_semitones']} 半音")
        lines.append(f"- 音程序直方图(前8):{c['interval_hist']}")
        lines.append(f"- 开头 48 音:{' '.join(c['first_48'][:24])}")
        lines.append("")
    hr = a["harmonic_rhythm"]
    lines.append(f"## 和声节奏:共 {hr['bars']} 小节,{hr['unique_pitch_sets']} 个不同音高集合,变化 {hr['changes']} 次")
    r = a["rhythm"]
    lines.append(f"## 节奏特征:16分网格直方图 {r['grid16_hist']},切分指数 {r['syncopation_index']}")
    lines.append(f"- 每小节 onset 数:{r['onset_per_bar'][:48]}...")
    lines.append(f"- 峰值密度小节: {r['peak_density_bar']},平均 {a['avg_notes_per_bar']} 音符/小节")
    lines.append("")
    lines.append("## 结构分段(指纹变化)")
    for s in a["structure_sections"]:
        lines.append(f"- 小节 {s['start_bar']} 起,长 {s['bars']} 小节")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("midi", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=PROJECT_ROOT / "output" / "2026-08-03" / "score_analysis")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    summary = []
    for path in args.midi:
        a = analyze(path)
        summary.append(a)
        stem = path.stem.replace(" ", "_")
        (args.out / f"{stem}.json").write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.out / f"{stem}.md").write_text(render_md(a), encoding="utf-8")
        print(f"analyzed {path.name}: key={a.get('key_estimate', {}).get('tonic', '?')} {a.get('key_estimate', {}).get('mode', '?')} bars={a.get('harmonic_rhythm', {}).get('bars', '?')}")
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("out:", args.out)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    main()
