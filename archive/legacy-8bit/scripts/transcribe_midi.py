#!/usr/bin/env python3
"""Transcribe a reference MIDI into a readable score: per-voice, per-bar,
note-by-note with velocities — the old-school way of learning a piece.

Outputs:
  <stem>.md      readable score (voices grouped by program, bars as rows)
  <stem>_stats.json  per-voice loudness/density statistics

Usage:
  python3 scripts/transcribe_midi.py <midi...> [--bars N] [--out DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import mido
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

GM_NAMES = {
    0: "Acoustic Grand Piano", 1: "Bright Acoustic Piano", 19: "Church Organ", 24: "Nylon Guitar",
    30: "Distortion Guitar", 36: "Fretless Bass", 40: "Violin", 48: "String Ensemble",
    56: "Trumpet", 110: "Guitar Fret Noise", 81: "Lead 1 (square)", 80: "Lead 2 (saw)",
    35: "Fretless Bass 2", 9: "Glockenspiel", 11: "Music Box", 16: "Drawbar Organ", 8: "Celesta",
    26: "Steel Guitar", 128: "Drums",
}


def parse_events(path: Path) -> tuple[float, int, list[dict]]:
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


def to_name(pitch: int) -> str:
    return f"{NOTE_NAMES[pitch % 12]}{pitch // 12 - 1}"


def transcribe(path: Path, max_bars: int) -> tuple[str, dict]:
    bpm, tpb, notes = parse_events(path)
    beats_per_bar = 4
    max_tick = max((n["end"] for n in notes), default=0)
    n_bars = int(max_tick / tpb / beats_per_bar) + 1
    if max_bars and max_bars > 0:
        n_bars = min(n_bars, max_bars)

    # group by (channel, program); drums separate
    voices: dict[tuple[int, int], list[dict]] = defaultdict(list)
    drums: list[dict] = []
    for n in notes:
        if n["ch"] == 9:
            drums.append(n)
        else:
            voices[(n["ch"], n["prog"])].append(n)

    lines: list[str] = []
    lines.append(f"# 抄谱: {path.name}")
    lines.append(f"\nBPM {bpm:.0f} | {n_bars} 小节 | ticks/beat {tpb}\n")

    stats_all: dict = {}

    # order voices by median pitch (melody first)
    def median_pitch(grp: list[dict]) -> int:
        return int(np.median([n["pitch"] for n in grp]))

    ordered = sorted(voices.items(), key=lambda kv: -median_pitch(kv[1]))

    for (ch, prog), grp in ordered:
        if len(grp) < 8 and median_pitch(grp) < 60:
            continue  # skip tiny filler voices
        name = GM_NAMES.get(prog, f"prog{prog}")
        vels = np.array([n["vel"] for n in grp])
        density = len(grp) / max(1.0, n_bars)
        lines.append(f"\n## 声部 ch{ch} {name}(program {prog}) — 音符 {len(grp)},密度 {density:.1f}/小节")
        lines.append(f"力度: 中位 {int(np.median(vels))} | 均值 {int(np.mean(vels))} | P25 {int(np.percentile(vels, 25))} | P75 {int(np.percentile(vels, 75))} | 最大 {int(vels.max())} | 最小 {int(vels.min())}")
        stats_all[f"ch{ch}_p{prog}_{name}"] = {
            "notes": len(grp), "density_per_bar": round(density, 2),
            "vel_median": int(np.median(vels)), "vel_mean": int(np.mean(vels)),
            "vel_p25": int(np.percentile(vels, 25)), "vel_p75": int(np.percentile(vels, 75)),
            "vel_max": int(vels.max()), "vel_min": int(vels.min()),
            "pitch_median": median_pitch(grp),
            "vel_hist": {str(k): v for k, v in Counter(int(x // 8) * 8 for x in vels).most_common(10)},
        }
        # per-bar table
        for bar in range(n_bars):
            s = bar * beats_per_bar * tpb
            e = s + beats_per_bar * tpb
            bar_notes = sorted([n for n in grp if s <= n["start"] < e], key=lambda n: n["start"])
            if not bar_notes:
                continue
            cells = []
            for n in bar_notes:
                beat = (n["start"] - s) / tpb
                dur = (n["end"] - n["start"]) / tpb
                cells.append(f"{to_name(n['pitch'])}({beat:.2f},{dur:.2f},v{n['vel']})")
            lines.append(f"  m{bar + 1:>3}: " + " ".join(cells))

    # drums summary
    if drums:
        vels = np.array([n["vel"] for n in drums])
        pc = Counter(n["pitch"] for n in drums)
        lines.append(f"\n## 鼓(通道9)— 音符 {len(drums)},密度 {len(drums)/max(1,n_bars):.1f}/小节")
        lines.append(f"力度: 中位 {int(np.median(vels))} | 最大 {int(vels.max())} | 最小 {int(vels.min())}")
        lines.append(f"音高分布: {dict(pc.most_common(8))}")
        stats_all["drums"] = {
            "notes": len(drums), "density_per_bar": round(len(drums) / max(1, n_bars), 2),
            "vel_median": int(np.median(vels)), "vel_max": int(vels.max()),
            "pitch_hist": {str(k): v for k, v in pc.most_common(8)},
        }
        for bar in range(min(n_bars, 24)):
            s = bar * beats_per_bar * tpb
            e = s + beats_per_bar * tpb
            bar_notes = sorted([n for n in drums if s <= n["start"] < e], key=lambda n: n["start"])
            if not bar_notes:
                continue
            cells = [f"{n['pitch']}({(n['start']-s)/tpb:.2f},v{n['vel']})" for n in bar_notes]
            lines.append(f"  m{bar + 1:>3}: " + " ".join(cells))

    return "\n".join(lines), stats_all


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("midi", nargs="+", type=Path)
    ap.add_argument("--bars", type=int, default=0, help="limit bars (0 = full)")
    ap.add_argument("--out", type=Path, default=PROJECT_ROOT / "output" / "2026-08-03" / "transcriptions")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for path in args.midi:
        md, stats_all = transcribe(path, args.bars)
        stem = path.stem.replace(" ", "_")
        (args.out / f"{stem}_抄谱.md").write_text(md, encoding="utf-8")
        (args.out / f"{stem}_声部统计.json").write_text(json.dumps(stats_all, ensure_ascii=False, indent=2), encoding="utf-8")
        n_voices = len([k for k in stats_all if not k.startswith("drum")])
        print(f"transcribed {path.name}: {n_voices} voices -> {args.out / (stem + '_抄谱.md')}")


if __name__ == "__main__":
    main()
