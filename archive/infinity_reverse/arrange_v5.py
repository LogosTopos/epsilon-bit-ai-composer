#!/usr/bin/env python3
"""Stage 11 — v5: 创作缺陷修复版.

P0 和声戏剧性: 7 处 C#7(V) 注入(三 turn 尾 / B 尾 / climax 尾属驻留 / finale 尾)
               + outro V→i 真终止(替代 fade)
P0 织体分层:   pad 根+五度空三音、下移音区;arp 上移八度;bass 按乐句内 lead
               密度选 pattern(问答式);hats 4 小节呼吸;混响按段落参与
P1 动机:       climax 下行和弦音对题;outro 主题末句时值伸缩;乐句对齐伴奏周期;
               滑音渲染;build 滤波渐开 + 转场 noise riser
P2 首尾:       intro 第 4 小节鼓先入;长音拆分留呼吸空拍
Outputs: audio/arrangement_v5.wav|mp3, Infinity_arrangement_v5.mid,
         audio/arrangement_v5_sf.mp3, data/arrangement_v5.json
"""
import json
import os
import subprocess
import numpy as np
import librosa
import soundfile as sf
from scipy.signal import butter, sosfiltfilt
from scipy.ndimage import uniform_filter1d
from reconstruct import (SR, DUR, N, EIGHTH, SIXTEENTH, SRC, render_notes,
                         pulse_bank, noise_burst, kick_synth, band_rms)
from produce import schroeder, to_stereo
from arrange import sec_of, chord_tones_for, smooth_chords, gen_counter, gen_pads

OUT = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(OUT, "audio")
DATA = os.path.join(OUT, "data")
BAR = 4 * 0.34830
BEAT = 0.34830
S16 = EIGHTH / 2

# ---------------- sections (v5: intro hook, outro cadence, gains) ----------------
SECTIONS = [
    (0.0,   8.0,   "intro",    dict(bass="hook", drums="hook",  arp="orig", counter=False, pad=True,  lead="motif",   gain=0.62)),
    (8.0,  16.0,   "build",    dict(bass=True,   drums="build", arp="orig",  counter=False, pad=True,  lead="all",     gain=0.75)),
    (16.0, 33.6,   "a1",       dict(bass=True,   drums="full",  arp="gen",   counter=True,  pad=True,  lead="all",     gain=0.95)),
    (33.6, 47.8,   "turn1",    dict(bass=True,   drums="half",  arp="orig",  counter=False, pad=True,  lead="all",     gain=0.70)),
    (47.8, 82.3,   "a2",       dict(bass=True,   drums="full",  arp="gen",   counter=True,  pad=True,  lead="all",     gain=1.00)),
    (82.3, 96.6,   "turn2",    dict(bass=True,   drums="half",  arp="orig",  counter=False, pad=True,  lead="all",     gain=0.70)),
    (96.6, 122.8,  "b",        dict(bass=True,   drums="full",  arp="gen",   counter=True,  pad=True,  lead="all",     gain=0.92, chords="bm_cycle")),
    (122.8, 137.4, "climax",   dict(bass=True,   drums="climax", arp="gen",  counter=True,  pad=True,  lead="all",     gain=1.12, chords="climax")),
    (137.4, 145.5, "break",    dict(bass=False,  drums="none",  arp="orig",  counter=False, pad=True,  lead="all",     gain=0.50, chords="pedal")),
    (145.5, 149.1, "reprise",  dict(bass=True,   drums="half",  arp="orig",  counter=False, pad=True,  lead="all",     gain=0.80)),
    (149.1, 163.3, "turn3",    dict(bass=True,   drums="half",  arp="orig",  counter=False, pad=True,  lead="all",     gain=0.72)),
    (163.3, 181.6, "finale",   dict(bass=True,   drums="full",  arp="gen",   counter=True,  pad=True,  lead="octave",  gain=1.15)),
    (181.6, 185.5, "outro",    dict(bass=True,   drums="outro", arp="orig",  counter=False, pad=True,  lead="augment", gain=0.85)),
]
DENSE = ("a1", "a2", "b", "climax", "finale")

# ---------------- V7 injection (dominant function) ----------------
# (bar_start, bar_end, chord) — C#7 = V7 of F#m
V7_BARS = [(46.0, 47.8), (94.8, 96.6), (120.8, 122.8), (134.4, 137.4),
           (161.3, 163.3), (179.5, 181.6), (181.6, 182.7)]
V7 = (1, "7")

def sec_of_v5(t_s):
    for s, e, name, d in SECTIONS:
        if s * BAR <= t_s < e * BAR:
            return name, d
    return "outro", SECTIONS[-1][3]

def bar_chords(smoothed, b):
    for (s, e) in V7_BARS:
        if s <= b < e:
            return V7
    name, d = sec_of_v5(b * BAR)
    s0 = next(sec[0] for sec in SECTIONS if sec[2] == name)
    if d.get("chords") == "bm_cycle":
        cyc = [(6, "min")] * 5 + [(11, "min")] * 5 + [(4, "maj")] * 5 + [(2, "maj")] * 3 + [V7] * 2
        return cyc[int((b - s0) % len(cyc))]
    if d.get("chords") == "climax":
        cyc = [(6, "min")] * 4 + [(2, "maj")] * 4 + [(4, "maj")] * 3 + [V7] * 3
        return cyc[int((b - s0) % len(cyc))]
    if d.get("chords") == "pedal":
        return (6, "min")
    for c in smoothed:
        if c["bar"] == int(b):
            return (c["root"], c["qual"])
    return (6, "min")

def chord_tones_v5(root, qual, bass_midi=42):
    """Voicings: triad=root+fifth only (空三音,项目规则); 7=root+7th(+5th)."""
    if qual == "7":
        ts = [root + 60, root + 67, root + 70]
    elif qual == "min":
        ts = [root + 60, root + 67]
    elif qual == "sus":
        ts = [root + 60, root + 67]
    else:
        ts = [root + 60, root + 67]
    while min(ts) < bass_midi + 12:
        ts = [t + 12 for t in ts]
    return ts

# ---------------- phrase detection (melody-driven alignment) ----------------
def detect_phrases(lead_part):
    """Phrase starts: gap>=0.5s between consecutive real lead notes (or bar 0)."""
    notes = sorted([n for n in lead_part if n.get("src", "orig") in ("orig", "split", "octave")],
                   key=lambda n: n["start_q"])
    starts = [0.0]
    for a, b in zip(notes[:-1], notes[1:]):
        if b["start_q"] - a["end_q"] >= 0.5:
            starts.append(b["start_q"])
    return starts

def phrase_start_bar(starts, t_s):
    st = 0.0
    for s in starts:
        if s <= t_s:
            st = s
        else:
            break
    return st / BAR

# ---------------- bass (density-aware, phrase-aligned) ----------------
BP = {
    "P0": [(i * 2, 0, 95) for i in range(8)],
    "P1": [(i * 2, 0 if i % 2 == 0 else -12, 92) for i in range(8)],
    "P2": [(i, 0 if i % 2 == 0 else -12, 88 if i % 2 == 0 else 38) for i in range(16)],
    "P3": [(0, 0, 95), (4, 0, 95), (6, -12, 88), (10, 0, 92), (12, -12, 84), (14, 0, 80)],
    "P4": [(i * 2, 0 if i % 4 < 2 else 7, 90) for i in range(8)],
    "P5": [(i, 0 if i % 2 == 0 else -12, 100) for i in range(16)],
}
ROOT_MIDI = {6: 42, 11: 47, 4: 40, 2: 38, 1: 37}
EIGHTH_PATS = ["P0", "P1", "P3"]
SIXTEENTH_PATS = ["P2", "P4", "P5"]

def gen_bass_v5(bass_notes, chords_sm, lead_part):
    """Bass: pattern chosen by the LEAD's local density (call-response),
    cycle aligned to melody phrases."""
    # per-bar lead density (activated part)
    lead_per_bar = {}
    for n in lead_part:
        b = int(n["start_q"] // BAR)
        lead_per_bar[b] = lead_per_bar.get(b, 0) + 1
    starts = detect_phrases(lead_part)
    out = []
    used = set()
    for s, e, name, d in SECTIONS:
        if not d.get("bass"):
            continue
        for b in np.arange(s, e, 1.0):
            if name == "intro" and b < 6:
                continue          # bass enters bar 6 (hook)
            if name == "outro" and b >= 182.6:
                continue          # stop after the V7 bar (final chord holds without bass)
            root, qual = bar_chords(chords_sm, int(b))
            base = ROOT_MIDI[root]
            if name == "b":
                base = ROOT_MIDI[root]
            pstart = phrase_start_bar(starts, b * BAR)
            idx = int((b - pstart) % 3)
            dense = lead_per_bar.get(int(b), 0) >= 6
            pat = (EIGHTH_PATS if dense else SIXTEENTH_PATS)[idx]
            used.add((name, pat))
            t0 = b * BAR
            for pos, off, vel in BP[pat]:
                st = t0 + pos * S16
                midi = base + off
                if name == "b" and pos % 4 == 2 and qual != "7":
                    midi -= 12
                out.append({"start_q": st, "end_q": st + 2 * S16, "midi": float(midi),
                            "vel": vel, "src": f"bp:{pat}"})
    # 16th pickups into A1 / climax / finale
    for bt, root in [(15.625, 42), (122.625, 42), (162.875, 42)]:
        for k in range(3):
            st = bt * BAR + (k + 1) * S16
            out.append({"start_q": st, "end_q": st + S16, "midi": float(root),
                        "vel": 85 - 10 * k, "src": "pickup"})
    out.sort(key=lambda n: n["start_q"])
    return out, sorted(used)

# ---------------- lead: split with breathing + motifs + ornaments ----------------
def activate_lead_v5(lead_notes, chords_sm):
    out = []
    for n in lead_notes:
        sec, d = sec_of_v5(n["start_q"])
        dur = n["end_q"] - n["start_q"]
        if sec in DENSE and dur >= 3 * EIGHTH:
            t = n["start_q"]
            k = 0  # hit counter (breathing: every 3rd slot is a rest)
            while t < n["end_q"] - 0.06:
                if k % 3 == 2:
                    t += 0.9 * EIGHTH          # breath
                else:
                    e = min(t + 0.85 * EIGHTH, n["end_q"])
                    out.append({"start_q": t, "end_q": e, "midi": n["midi"],
                                "vel": int(102 * 0.85 ** k), "src": "split"})
                    t = e
                k += 1
        else:
            out.append(dict(n, src="orig"))
    # phrase-end ornaments (16th chord runs) + anticipations
    for s, e, name, d in SECTIONS:
        if name not in DENSE:
            continue
        for b in np.arange(s, e, 1.0):
            if int(b) % 4 != 3:
                continue
            bar_notes = [n for n in out if b * BAR <= n["start_q"] < (b + 1) * BAR]
            if not bar_notes:
                continue
            last = max(bar_notes, key=lambda n: n["end_q"])
            gap = (b + 1) * BAR - last["end_q"]
            if gap >= 0.26:
                root, qual = bar_chords(chords_sm, int(b))
                tones = [t for t in chord_tones_v5(root, qual, 48) if t > last["midi"] - 14]
                if not tones:
                    continue
                t = last["end_q"] + 0.09
                k = 0
                while t < (b + 1) * BAR - 0.05 and k < 6:
                    midi = tones[(k * 2) % len(tones)]
                    out.append({"start_q": t, "end_q": t + 0.09, "midi": float(midi),
                                "vel": 52 + 6 * (k % 2), "src": "orn"})
                    t += 0.174
                    k += 1
    ordered = sorted(out, key=lambda n: n["start_q"])
    for i, n in enumerate(ordered):
        sec, d = sec_of_v5(n["start_q"])
        if sec not in DENSE or n.get("src", "orig") in ("orn", "split"):
            continue
        prev_end = ordered[i - 1]["end_q"] if i > 0 else -1
        gap = n["start_q"] - prev_end
        if 0.17 <= gap <= 0.30:
            root, qual = bar_chords(chords_sm, int(n["start_q"] // BAR))
            tones = chord_tones_v5(root, qual, 48)
            tgt = min(tones, key=lambda c: abs(c - (n["midi"] - 5)))
            out.append({"start_q": n["start_q"] - 0.087, "end_q": n["start_q"] - 0.01,
                        "midi": float(tgt), "vel": 48, "src": "ant"})
    out.sort(key=lambda n: n["start_q"])
    return out

def augment_outro_theme(lead_notes, chords_sm):
    """Outro: last phrase of the finale melody, doubled durations, on final F#m."""
    finale_notes = [n for n in lead_notes if 163.3 * BAR <= n["start_q"] < 181.6 * BAR]
    # take the last phrase (notes after the final big gap)
    finale_notes.sort(key=lambda n: n["start_q"])
    if not finale_notes:
        return []
    # find the last gap >= 0.5s
    split_i = 0
    for i in range(1, len(finale_notes)):
        if finale_notes[i]["start_q"] - finale_notes[i - 1]["end_q"] >= 0.5:
            split_i = i
    phrase = finale_notes[split_i:]
    out = []
    t = 182.9 * BAR
    for n in phrase:
        dur = max(0.35, (n["end_q"] - n["start_q"]) * 2.0)
        out.append({"start_q": t, "end_q": t + dur, "midi": n["midi"],
                    "vel": 96, "src": "augment"})
        t += dur + 0.10
    return out

def gen_counter_v5(lead_raw, chords_sm):
    """Climax: descending chord-tone countersubject; else 3rd-below harmony (snapped)."""
    base = gen_counter(lead_raw, chords_sm)
    out = []
    for n in base:
        sec, d = sec_of_v5(n["start_q"])
        if sec == "climax":
            b = int(n["start_q"] // BAR)
            root, qual = bar_chords(chords_sm, b)
            tones = chord_tones_v5(root, qual, 48)
            pos8 = int(round((n["start_q"] % BAR) / EIGHTH))
            seq = [0, 2, 1, 0, 1, 2, 0, 1]  # descending-ish walk
            midi = tones[seq[pos8 % len(seq)] % len(tones)]
            out.append({"start_q": n["start_q"], "end_q": n["end_q"], "midi": float(midi),
                        "vel": 80, "src": "walk"})
        elif sec == "finale":
            out.append({"start_q": n["start_q"], "end_q": n["end_q"], "midi": n["midi"] - 6,
                        "vel": 78, "src": "sixth"})
        else:
            out.append(dict(n))
    return out

def gen_arp_v5(arp_notes, chords_sm, lead_part):
    """Arp +12 octave (register separation), phrase-aligned pattern cycles."""
    out = [dict(n, midi=min(n["midi"] + 12, 108), vel=70, src="orig") for n in arp_notes]
    rng = np.random.default_rng(172)
    PATS = {"A": [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1, 0, 1, 2, 3],
            "B": [0, 2, 1, 3, 0, 2, 1, 3, 0, 2, 1, 3, 0, 2, 1, 3],
            "C": [0, 1, 2, 3, 4, 3, 2, 1, 0, 1, 2, 3, 4, 3, 2, 1],
            "D": [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1, 0, 1, 2, 2]}
    CYCLE = {"a1": ["A", "B"], "a2": ["A", "B", "C"], "b": ["A", "B"],
             "climax": ["C", "A", "B", "D"], "finale": ["A", "B", "C", "B"]}
    starts = detect_phrases(lead_part)
    for s, e, name, d in SECTIONS:
        if d.get("arp") != "gen":
            continue
        cyc = CYCLE.get(name, ["A"])
        for b in np.arange(s, e, 1.0):
            pstart = phrase_start_bar(starts, b * BAR)
            pat = PATS[cyc[int((b - pstart) % len(cyc))]]
            root, qual = bar_chords(chords_sm, int(b))
            tones = [t + 12 for t in chord_tones_v5(root, qual, 48)]
            if name == "climax":
                tones = tones + [tones[0] + 12]
            for i in range(16):
                st = (b + i * 0.125) * BAR
                midi = tones[pat[i] % len(tones)]
                if i == 15 and pat is PATS["D"] and name == "climax":
                    out.append({"start_q": st + S16, "end_q": st + S16 + 0.07,
                                "midi": float(midi), "vel": 68, "src": "flam"})
                vel = 60 + int(22 * (i % 2 == 0)) + int(rng.integers(-6, 7))
                out.append({"start_q": st, "end_q": st + 0.09, "midi": float(midi),
                            "vel": vel, "src": f"arp:{cyc[int((b - pstart) % len(cyc))]}"})
    out.sort(key=lambda n: n["start_q"])
    return out

# ---------------- pads: root+fifth, phrase-hold, final chord ---------------- 
def gen_pads_v5(chords_sm, padB=False):
    out = []
    for b in range(int(185.6)):
        root, qual = bar_chords(chords_sm, b)
        name, d = sec_of_v5(b * BAR)
        if padB and name not in ("climax", "finale"):
            continue
        tones = chord_tones_v5(root, qual, 42)
        t0 = b * BAR
        t1 = (b + 1) * BAR
        if name == "outro" and b >= 182.7:
            t1 = 185.6 * BAR  # hold final F#m to the end
        for m in tones:
            out.append({"start_q": t0, "end_q": t1,
                        "midi": float(m + (12 if padB else 0)),
                        "vel": 60 if padB else 85, "src": "padB" if padB else "padA"})
    return out

# ---------------- drums (hook / breathing hats / outro stop) ----------------
def drum_patterns_v5():
    ev = []
    rng = np.random.default_rng(7)
    def add(t, kind, vel):
        ev.append((t, kind, vel))
    for s, e, name, d in SECTIONS:
        kd = d.get("drums")
        for b in np.arange(s, e, 1.0):
            t0 = b * BAR
            p = int(b) % 4
            last_bar = b >= e - 1
            if kd == "hook":
                if b >= 4:
                    add(t0, "kick", 96); add(t0 + 2 * BEAT, "kick", 92)
                    add(t0 + 2 * BEAT, "snare", 78)
                    for i in (1, 3, 5, 7):
                        add(t0 + i * EIGHTH, "hat", 46)
            elif kd == "build":
                for i in range(8):
                    add(t0 + i * EIGHTH, "hat", 40 + int(rng.integers(0, 10)))
                if b >= 12:
                    add(t0, "kick", 96); add(t0 + 2 * BEAT, "kick", 92)
                if b >= 14:
                    add(t0 + 2 * BEAT, "snare", 88)
            elif kd == "full":
                add(t0, "kick", 108); add(t0 + 2 * BEAT, "kick", 104)
                add(t0 + 2 * BEAT, "snare", 100)
                if p == 2:                      # breathing bar: offbeat hats only
                    for i in (1, 3, 5, 7):
                        add(t0 + i * EIGHTH, "hat", 62)
                else:
                    acc = [2, 6] if p == 0 else ([1, 5] if p == 1 else [3, 7])
                    for i in range(8):
                        add(t0 + i * EIGHTH, "hat", 74 if i in acc else 58)
                if p == 1:
                    add(t0 + 6.5 * EIGHTH, "snare", 32)
                if p == 3:
                    for k in range(4):
                        add(t0 + (5.5 + 0.25 * k) * EIGHTH, "snare", 62 + 14 * k)
                if b % 4 == 0:
                    add(t0, "crash", 92)
                if last_bar:
                    for k in range(4):
                        add(t0 + (5.5 + 0.25 * k) * EIGHTH, "snare", 70 + 15 * k)
            elif kd == "climax":
                add(t0, "kick", 112); add(t0 + 2 * BEAT, "kick", 106)
                add(t0 + 2 * BEAT, "snare", 104)
                for i in range(8):
                    add(t0 + i * EIGHTH, "hat", 76 if i % 2 else 60)
                if b % 4 == 0:
                    add(t0, "crash", 100)
                if b >= e - 2:
                    for k in range(8):
                        add(t0 + k * 0.5 * BEAT, "kick", 100)
            elif kd == "half":
                add(t0, "kick", 100)
                add(t0 + 2 * BEAT, "snare", 92)
                for i in (1, 3, 5, 7):
                    add(t0 + i * EIGHTH, "hat", 62)
                if p == 3:
                    for k in range(3):
                        add(t0 + (6 + 0.5 * k) * EIGHTH, "snare", 60 + 12 * k)
            elif kd == "outro":
                if b < 182.7:
                    add(t0, "kick", 100)
                    add(t0 + 2 * BEAT, "snare", 92)
                    for i in (1, 3, 5, 7):
                        add(t0 + i * EIGHTH, "hat", 58)
    add(15.75 * BAR, "crash", 70)
    add(163.25 * BAR, "crash", 95)
    ev.sort(key=lambda e: e[0])
    return ev

def render_drums_v5(events, n=N):
    out = np.zeros(n)
    rng = np.random.default_rng(3)
    for t, kind, vel in events:
        g = vel / 110.0
        if kind == "kick":
            out += kick_synth(t, n, f0=150, f1=44, dur=0.11, gain=0.9 * g)
        elif kind == "snare":
            out += noise_burst(t, 0.14, n, hp=800, lp=6000, decay=0.045, gain=0.5 * g, rng=rng)
            tt = int(0.09 * SR)
            tone = np.sin(2 * np.pi * 190 * np.arange(tt) / SR) * np.exp(-np.arange(tt) / (0.025 * SR))
            i0 = int(t * SR)
            out[i0:i0 + tt] += 0.28 * g * tone
        elif kind == "hat":
            out += noise_burst(t, 0.05, n, hp=6500, decay=0.012, gain=0.22 * g, rng=rng)
        elif kind == "crash":
            out += noise_burst(t, 1.0, n, hp=2500, lp=9500, decay=0.30, gain=0.3 * g, rng=rng)
    return out

# ---------------- slides + filter sweep + risers ----------------
def render_slides(lead_part, wave_map, gain, n=N):
    """Portamento between nearby notes (gap 0.02-0.12s, interval 2-7 st)."""
    notes = sorted([x for x in lead_part if x.get("src", "orig") in ("orig", "split", "octave")],
                   key=lambda x: x["start_q"])
    out = np.zeros(n)
    for a, b in zip(notes[:-1], notes[1:]):
        gap = b["start_q"] - a["end_q"]
        dmidi = b["midi"] - a["midi"]
        if 0.02 <= gap <= 0.12 and 2 <= abs(dmidi) <= 7:
            f0 = librosa.midi_to_hz(a["midi"])
            f1 = librosa.midi_to_hz(b["midi"])
            sec, _ = sec_of_v5(b["start_q"])
            wf = wave_map.get(sec, "pulse")
            if wf != "pulse":
                continue
            dur = gap
            i0 = int(a["end_q"] * SR)
            L = int(dur * SR)
            tt = np.arange(L) / SR
            # exponential glide
            f = f0 * (f1 / f0) ** (tt / dur)
            ph = 2 * np.pi * np.cumsum(f) / SR
            duty = 0.25
            seg = np.where(np.mod(ph / (2 * np.pi), 1) < duty, 1.0, -1.0)
            env = np.minimum(tt / 0.012, (dur - tt) / 0.012).clip(0, 1)
            out[i0:i0 + L] += gain * 0.45 * seg * env
    return out

def time_varying_lp(x, fc_start, fc_end, t0, t1):
    """One-pole lowpass with cutoff sweeping fc_start->fc_end over [t0,t1]."""
    sr = SR
    n = len(x)
    fc = np.full(n, fc_end)
    a = int(t0 * sr); b = min(int(t1 * sr), n)
    if b > a:
        ramp = np.linspace(0, 1, b - a)
        fc[a:b] = fc_start + (fc_end - fc_start) * ramp
    out = np.empty(n)
    y = 0.0
    for i in range(n):
        alpha = 1 - np.exp(-2 * np.pi * fc[i] / sr)
        y += alpha * (x[i] - y)
        out[i] = y
    return out

def noise_riser(t0, dur_s, n=N, gain=0.35):
    """White noise with rising LP cutoff and gain ramp (transition FX)."""
    rng = np.random.default_rng(5)
    L = int(dur_s * SR)
    x = rng.standard_normal(L)
    out = np.zeros(n)
    fc = np.linspace(400, 8000, L)
    y = 0.0
    sweep = np.empty(L)
    for i in range(L):
        alpha = 1 - np.exp(-2 * np.pi * fc[i] / SR)
        y += alpha * (x[i] - y)
        sweep[i] = y
    env = (np.arange(L) / L) ** 1.5
    i0 = int(t0 * SR)
    out[i0:i0 + L] = gain * sweep * env
    return out

# ---------------- timbre maps ----------------
LEAD_WAVE = {"intro": "triangle", "build": "pulse", "a1": "pulse", "turn1": "pulse",
             "a2": "pulse", "turn2": "pulse", "b": "pulse", "climax": "pulse",
             "break": None, "reprise": "pulse", "turn3": "pulse", "finale": "pulse",
             "outro": "triangle"}
LEAD_DUTY = {"build": 0.25, "a1": 0.125, "turn1": 0.5, "a2": 0.25, "turn2": 0.5,
             "b": 0.125, "climax": 0.125, "reprise": 0.25, "turn3": 0.5, "finale": 0.125}
WET_MAP = {"turn1": 0.16, "turn2": 0.16, "turn3": 0.16, "break": 0.45,
           "climax": 0.40, "finale": 0.35, "b": 0.32}

def render_by_section(notes, wave_map, gain, duty_map=None, **kw):
    sig = np.zeros(N)
    for s, e, name, d in SECTIONS:
        wf = wave_map.get(name)
        if wf is None:
            continue
        sub = [n for n in notes if s * BAR <= n["start_q"] < e * BAR]
        if not sub:
            continue
        kws = dict(kw)
        if duty_map and name in duty_map:
            kws["duty"] = duty_map[name]
        sig += render_notes(sub, wf, gain, N, **kws)
    return sig

# ================================================================== MAIN
def main():
    lead_notes = json.load(open(os.path.join(DATA, "lead_notes_clean.json")))
    bass_notes = json.load(open(os.path.join(DATA, "bass_notes_clean.json")))
    arp_notes = json.load(open(os.path.join(DATA, "arp_notes.json")))
    chords = json.load(open(os.path.join(DATA, "chords.json")))["bars"]
    sm = smooth_chords(chords, k=5)
    SCALE = {6, 8, 9, 11, 1, 2, 4}
    QUAL_OK = {6: {"min", "sus"}, 8: {"min"}, 9: {"min", "maj"}, 11: {"min", "sus"},
               1: {"min"}, 2: {"maj", "sus"}, 4: {"maj", "sus"}}
    for c in sm:
        if c["root"] not in SCALE:
            d0 = min((abs((s - c["root"]) % 12), abs((c["root"] - s) % 12)) for s in SCALE)
            cands = [s for s in SCALE if min(abs((s - c["root"]) % 12), abs((c["root"] - s) % 12)) == d0[0]]
            c["root"] = cands[0]
        if c["qual"] not in QUAL_OK[c["root"]]:
            c["qual"] = "min" if c["root"] in (6, 11) else "maj"

    print("generating parts…")
    lead_raw = [dict(n, src="orig") for n in lead_notes]
    lead = activate_lead_v5(lead_raw, sm)
    # intro motif + held F#5 (same as v3)
    motif = [n for n in lead if 16.0 * BAR <= n["start_q"] < 18.0 * BAR]
    if motif:
        base = motif[0]["start_q"] - 16.0 * BAR
        for bs, ve, hold in [(0.5, 100, 1.5), (2.5, 62, 1.5)]:
            for n in motif:
                st = bs * BAR + (n["start_q"] - 16.0 * BAR - base)
                lead.append({"start_q": st, "end_q": st + max(0.15, n["end_q"] - n["start_q"]),
                             "midi": n["midi"], "vel": ve, "src": "motif"})
        lead.append({"start_q": 4.0 * BAR, "end_q": 7.9 * BAR, "midi": 78.0,
                     "vel": 95, "src": "motif_hold"})
    # outro: augmented final theme
    lead += augment_outro_theme(lead_raw, sm)
    # octave in finale
    for n in lead:
        sec, d = sec_of_v5(n["start_q"])
        if d.get("lead") == "octave" and n["midi"] < 96:
            n["midi"] += 12
    lead.sort(key=lambda n: n["start_q"])

    counter = gen_counter_v5(lead_raw, sm)
    bass, bass_used = gen_bass_v5(bass_notes, sm, lead)
    arp = gen_arp_v5(arp_notes, sm, lead)
    pads = gen_pads_v5(sm)
    padsB = gen_pads_v5(sm, padB=True)
    drums = drum_patterns_v5()
    glock = [dict(n, midi=min(n["midi"] + 12, 104), vel=55, src="glock")
             for n in lead if sec_of_v5(n["start_q"])[0] in ("intro", "outro") and n["midi"] < 92]
    for name, part in [("lead", lead), ("counter", counter), ("bass", bass),
                       ("arp", arp), ("padA", pads), ("padB", padsB),
                       ("glock", glock), ("drums", drums)]:
        print(f"  {name}: {len(part)} events")
    print("  bass patterns:", bass_used)

    print("rendering…")
    lead_long = [n for n in lead if n["end_q"] - n["start_q"] >= 0.3]
    lead_short = [n for n in lead if n["end_q"] - n["start_q"] < 0.3]
    lead_sig = render_by_section(lead_long, LEAD_WAVE, 0.85, LEAD_DUTY,
                                 vib_rate=12.0, vib_depth=5.0, sus=0.9, rel=0.05)
    lead_sig += render_by_section(lead_short, LEAD_WAVE, 0.85, LEAD_DUTY,
                                  sus=0.85, rel=0.04)
    lead_sig += render_slides(lead, LEAD_WAVE, 0.85)
    # build-section filter opening on lead (700Hz -> 6kHz)
    lead_sig = time_varying_lp(lead_sig, 700, 6000, 8.0 * BAR, 16.0 * BAR)
    # brief filter closing into break (4.5k -> 1.5k over 136-137.4)
    lead_sig = time_varying_lp(lead_sig, 4500, 1500, 136.0 * BAR, 137.4 * BAR)

    counter_sig = render_by_section(counter, {"a1": "pulse", "a2": "pulse", "b": "triangle",
                                              "climax": "pulse", "finale": "pulse"},
                                    0.5, {"a1": 0.25, "a2": 0.25, "climax": 0.5, "finale": 0.25},
                                    sus=0.88, rel=0.05)
    bass_sig = np.zeros(N)
    for s, e, name, d in SECTIONS:
        if not d.get("bass"):
            continue
        sub = [n for n in bass if s * BAR <= n["start_q"] < e * BAR]
        if sub:
            wf = "triangle" if name == "b" else "pulse"
            bass_sig += render_notes(sub, wf, 1.0, N, duty=0.5, staccato=0.92,
                                     sus=0.9, rel=0.015, detune_cents=-7.0)
    nyq = SR / 2
    bass_sig = sosfiltfilt(butter(4, 800 / nyq, btype="low", output="sos"), bass_sig)
    arp_sig = render_by_section(arp, {"a1": "pulse", "a2": "pulse", "b": "pulse",
                                      "climax": "pulse", "finale": "pulse"},
                                0.5, {"a1": 0.125, "a2": 0.125, "b": 0.125,
                                      "climax": 0.125, "finale": 0.125},
                                staccato=0.7, sus=0.9, rel=0.02)
    pad_sig = np.zeros(N)
    for s, e, name, d in SECTIONS:
        sub = [n for n in pads if s * BAR <= n["start_q"] < e * BAR]
        if sub:
            wf = "triangle" if name in ("break", "outro") else "pulse"
            pad_sig += render_notes(sub, wf, 1.0, N, duty=0.25, staccato=1.0,
                                    sus=0.75, rel=0.35, vib_rate=5.0, vib_depth=2.0)
    padB_sig = render_notes(padsB, "pulse", 0.5, N, duty=0.125, staccato=1.0,
                            sus=0.65, rel=0.3, vib_rate=5.0, vib_depth=2.0)
    glock_sig = render_notes(glock, "triangle", 0.16, N, staccato=0.6, sus=0.8, rel=0.12)
    drum_sig = render_drums_v5(drums)
    # risers into A1 / climax / finale
    drum_sig += noise_riser(15.0 * BAR, 1.0 * BAR, gain=0.30)
    drum_sig += noise_riser(121.4 * BAR, 1.4 * BAR, gain=0.38)
    drum_sig += noise_riser(162.0 * BAR, 1.3 * BAR, gain=0.38)

    # section gains (smoothed ramps)
    def sec_gain(t_s):
        name, d = sec_of_v5(t_s)
        return d.get("gain", 1.0)
    tgrid = np.arange(N) / SR
    gain_curve = np.array([sec_gain(t) for t in tgrid])
    gain_curve = uniform_filter1d(gain_curve, int(0.8 * SR // 1))  # 0.8s ramps

    stems = {"lead": lead_sig, "counter": counter_sig, "bass": bass_sig, "arp": arp_sig,
             "pad": pad_sig, "padB": padB_sig, "glock": glock_sig, "drums": drum_sig}
    for vn in stems:
        vx = stems[vn]
        r = np.sqrt(np.mean(vx ** 2)) + 1e-9
        stems[vn] = vx / r * 0.12
    BAL = {"lead": 0.95, "counter": 0.48, "bass": 1.25, "arp": 0.40,
           "pad": 0.48, "padB": 0.30, "glock": 0.16, "drums": 0.72}
    g = np.array([BAL[vn] for vn in stems])
    print("gains:", {vn: round(float(gi), 3) for vn, gi in zip(stems, g)})

    L = np.zeros(N); R = np.zeros(N)
    gL, gC, gB, gA, gP, gPB, gG, gD = g
    det1 = render_by_section(lead_long, LEAD_WAVE, 0.10 * gL, LEAD_DUTY, vib_rate=12.0,
                             vib_depth=5.0, sus=0.9, rel=0.05, detune_cents=5.0)
    det2 = render_by_section(lead_long, LEAD_WAVE, 0.10 * gL, LEAD_DUTY, vib_rate=12.0,
                             vib_depth=5.0, sus=0.9, rel=0.05, detune_cents=-5.0)
    src_l = stems["lead"] * 0.85 * gL
    slap = np.zeros(N)
    dn = int(0.2612 * SR)
    slap[dn:] = src_l[:-dn] * 0.16
    l1, r1 = to_stereo(src_l, 0.0)
    l2, r2 = to_stereo(det1 * gL, -0.55)
    l3, r3 = to_stereo(det2 * gL, 0.55)
    ls, rs = to_stereo(slap, 0.25)
    L += l1 + l2 + l3 + ls; R += r1 + r2 + r3 + rs
    lc, rc = to_stereo(stems["counter"] * gC, -0.25)
    L += lc; R += rc
    lb, rb = to_stereo(stems["bass"] * gB, 0.0)
    L += lb; R += rb
    dd = int(EIGHTH * SR)
    ad = stems["arp"] * gA
    acc = ad.copy()
    for k in range(1, 5):
        acc[dd * k:] += ad[:-dd * k] * 0.32 ** k
    acc = sosfiltfilt(butter(4, 6000 / nyq, btype="low", output="sos"), acc)
    la, ra = to_stereo(acc * 0.7, -0.45)
    la2, ra2 = to_stereo(ad * 0.5, 0.45)
    L += la + la2; R += ra + ra2
    pl = render_notes(pads, "pulse", 0.5 * gP, N, duty=0.25, staccato=1.0, sus=0.75,
                      rel=0.35, detune_cents=6.0)
    pr = render_notes(pads, "pulse", 0.5 * gP, N, duty=0.25, staccato=1.0, sus=0.75,
                      rel=0.35, detune_cents=-6.0)
    lp, rp = to_stereo(stems["pad"] * 0.5 * gP, -0.3)
    lp2, rp2 = to_stereo(pl, -0.8)
    lp3, rp3 = to_stereo(pr, 0.8)
    L += lp + lp2 + lp3; R += rp + rp2 + rp3
    lpb, rpb = to_stereo(stems["padB"] * gPB, 0.0)
    L += lpb; R += rpb
    lg, rg = to_stereo(stems["glock"] * gG, 0.3)
    L += lg; R += rg
    ld, rd = to_stereo(stems["drums"] * gD, 0.0)
    L += ld; R += rd
    # section-aware reverb
    wet_curve = np.array([WET_MAP.get(sec_of_v5(t)[0], 0.30) for t in tgrid])
    wet_curve = uniform_filter1d(wet_curve, int(0.8 * SR // 1))
    wet = schroeder((src_l * 0.5 + stems["pad"] * 0.5 * gP + ad * 0.25).astype(np.float64),
                    SR, rt60=0.75, wet=0.30)
    wet *= wet_curve[:, None]
    L += wet[:, 0]; R += wet[:, 1]
    wet_d = schroeder((stems["drums"] * gD * 0.35).astype(np.float64), SR, rt60=0.5, wet=0.12)
    L += wet_d[:, 0]; R += wet_d[:, 1]
    mix = np.stack([L, R], axis=-1)
    mono = (L + R) / 2

    from scipy.signal import lfilter
    env = np.abs(mono)
    env = lfilter([1 - 0.9995], [1, -0.9995], env)
    thr, ratio, knee = 0.28, 1.8, 0.15
    def comp_gain(x):
        over = x - thr
        soft = np.where(over > 0, over - knee / 2 + (knee / 2) * np.tanh(over / knee * 2), 0)
        gv = 1 - (1 - 1 / ratio) * np.clip(soft, 0, None) / (x + 1e-9)
        return np.clip(gv, 0.35, 1.0)
    gc = comp_gain(env)
    gc = uniform_filter1d(gc, int(0.01 * SR // 1))
    mix *= gc[:, None]
    mix *= gain_curve[:, None]
    mix *= 0.22 / (np.sqrt(np.mean(mix ** 2)) + 1e-9)
    peak = np.max(np.abs(mix))
    if peak > 0.97:
        mix = mix * (0.97 / peak)
    sf.write(os.path.join(AUD, "arrangement_v5.wav"), mix, SR)
    subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", os.path.join(AUD, "arrangement_v5.wav"),
                    "-codec:a", "libmp3lame", "-q:a", "2", os.path.join(AUD, "arrangement_v5.mp3")])
    print("wrote audio/arrangement_v5.wav/.mp3")

    report = {
        "sections": [{"name": n, "t": [round(s * BAR, 2), round(e * BAR, 2)]} for s, e, n, d in SECTIONS],
        "v7_bars": V7_BARS,
        "note_counts": {k: len(v) for k, v in [("lead", lead), ("counter", counter),
                                               ("bass", bass), ("arp", arp), ("pads", pads),
                                               ("glock", glock), ("drums", drums)]},
        "bass_patterns": bass_used,
    }
    for s, e, name, d in SECTIONS:
        a = int(s * BAR * SR); b = int(e * BAR * SR)
        report.setdefault("section_rms", {})[name] = round(float(np.sqrt(np.mean(mix[a:b, :] ** 2))), 4)
    json.dump(report, open(os.path.join(DATA, "arrangement_v5.json"), "w"), indent=2)
    print("section RMS:", {k: v for k, v in report["section_rms"].items()})

    # MIDI export
    import mido
    from mido import MidiFile, MidiTrack, MetaMessage, Message
    tpb = 480
    mid = MidiFile(ticks_per_beat=tpb)
    tempo_us = int(60.0 / 172.27 * 1e6)
    def add_track(name, notes, channel, program):
        tr = MidiTrack()
        tr.append(MetaMessage("track_name", name=name, time=0))
        tr.append(MetaMessage("set_tempo", tempo=tempo_us, time=0))
        tr.append(Message("program_change", program=program, channel=channel, time=0))
        ev = []
        for nt in notes:
            st = int(round(nt["start_q"] * 172.27 / 60 * tpb))
            en = int(round(nt["end_q"] * 172.27 / 60 * tpb))
            if en <= st:
                en = st + 60
            ev.append((st, "on", nt["midi"], int(np.clip(nt.get("vel", 90), 20, 115))))
            ev.append((en, "off", nt["midi"], 0))
        for s, e, name, d in SECTIONS:
            g0 = d.get("gain")
            if isinstance(g0, (int, float)):
                ev.append((int(s * BAR * 172.27 / 60 * tpb), "cc11", 0, int(np.clip(g0 * 127, 20, 120))))
        ev.sort(key=lambda e: (e[0], e[1] == "on"))
        last = 0
        for t, kind, note, vel in ev:
            if kind == "cc11":
                tr.append(Message("control_change", control=11, value=vel, channel=channel, time=t - last))
            else:
                tr.append(Message("note_on" if kind == "on" else "note_off",
                                  note=int(round(note)), velocity=vel, channel=channel, time=t - last))
            last = t
        mid.tracks.append(tr)
    add_track("Lead", lead, 0, 80)
    add_track("Counter", counter, 1, 81)
    add_track("Bass", bass, 2, 38)
    add_track("Arp", arp, 3, 89)
    add_track("PadA", pads, 4, 91)
    add_track("PadB", padsB, 5, 89)
    add_track("Glock", glock, 6, 10)
    dr_tr = MidiTrack()
    dr_tr.append(MetaMessage("track_name", name="Drums", time=0))
    dr_tr.append(MetaMessage("set_tempo", tempo=tempo_us, time=0))
    GM = {"kick": 36, "snare": 38, "hat": 42, "crash": 49}
    ev = [(int(t * 172.27 / 60 * tpb), GM[k], int(v)) for t, k, v in drums]
    ev.sort()
    last = 0
    for t, note, vel in ev:
        dr_tr.append(Message("note_on", note=note, velocity=vel, channel=9, time=t - last))
        dr_tr.append(Message("note_off", note=note, velocity=0, channel=9, time=60))
        last = t
    mid.tracks.append(dr_tr)
    mid.save(os.path.join(OUT, "Infinity_arrangement_v5.mid"))
    print("wrote Infinity_arrangement_v5.mid")

    sf2 = os.path.join(OUT, "..", "..", "soundfonts", "MuseScore_General.sf2")
    if os.path.exists(sf2):
        subprocess.run(["fluidsynth", "-F", os.path.join(AUD, "arrangement_v5_sf.wav"), "-r", "44100",
                        "-R", "0.9", "-C", "0", "-g", "1.2", sf2,
                        os.path.join(OUT, "Infinity_arrangement_v5.mid")], capture_output=True)
        if os.path.exists(os.path.join(AUD, "arrangement_v5_sf.wav")):
            subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", os.path.join(AUD, "arrangement_v5_sf.wav"),
                            "-codec:a", "libmp3lame", "-q:a", "2", os.path.join(AUD, "arrangement_v5_sf.mp3")])
            print("wrote audio/arrangement_v5_sf.mp3")

if __name__ == "__main__":
    main()
