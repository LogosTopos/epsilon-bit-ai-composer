#!/usr/bin/env python3
"""Stage 9 — v3 ARRANGEMENT (创作目标:复杂、好听、成熟,非还原).

Material: Infinity 转录(lead/bass/arp/chords)+ 项目编曲工艺:
  - 转场五件套:节奏先现 / 密度渐进 / 音色提前 / 和声预挂 / 速度恒定(172.27)
  - 和声功能化:B 段 i-iv-VII-VI(F♯m-Bm-E-D)
  - 对位:主旋律下方三度/六度平行副旋律(就近归位)
  - 动机贯穿:引子预示主题碎片 → A1 呈示 → B 段发展 → 余韵回声
  - 程序化 halftime 鼓组:kick 1&3 / snare 3 / 8 分 hats + 16 分 fill
Structure (bars @172.27, bar=1.3932s, mapped to original segment boundaries):
  intro 0-8 | build 8-16 | A1 16-33.6 | TURN1 33.6-47.8 | A2 47.8-82.3 |
  TURN2 82.3-96.6 | B 96.6-122.8 | CLIMAX 122.8-137.4 | BREAK 137.4-145.5 |
  REPRISE 145.5-149.1 | TURN3 149.1-163.3 | FINALE 163.3-181.6 | OUTRO 181.6-185.5
Outputs: audio/arrangement_v3.wav|mp3, Infinity_arrangement_v3.mid,
         audio/arrangement_v3_sf.mp3 (FluidSynth), data/arrangement_v3.json
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
from produce import schroeder, to_stereo, parse_chord, chord_tones, smooth_chords

OUT = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(OUT, "audio")
DATA = os.path.join(OUT, "data")
BAR = 4 * 0.34830          # 1.3932s
N_BARS = 185.5
BEAT = 0.34830

def t_bar(b): return b * BAR

# ------------------------------------------------------------------ structure
# (start_bar, end_bar, name, density dict)
SECTIONS = [
    (0.0,   8.0,   "intro",    dict(bass=False, drums="none", arp="orig",  counter=False, pad=True,  lead="motif",   gain=0.55)),
    (8.0,  16.0,   "build",    dict(bass=True,  drums="build", arp="orig",  counter=False, pad=True,  lead="all",     gain=0.75)),
    (16.0, 33.6,   "a1",       dict(bass=True,  drums="full",  arp="gen",   counter=True,  pad=True,  lead="all",     gain=0.95)),
    (33.6, 47.8,   "turn1",    dict(bass=True,  drums="half",  arp="orig",  counter=False, pad=True,  lead="all",     gain=0.70)),
    (47.8, 82.3,   "a2",       dict(bass=True,  drums="full",  arp="gen",   counter=True,  pad=True,  lead="all",     gain=1.00)),
    (82.3, 96.6,   "turn2",    dict(bass=True,  drums="half",  arp="orig",  counter=False, pad=True,  lead="all",     gain=0.70)),
    (96.6, 122.8,  "b",        dict(bass=True,  drums="full",  arp="gen",   counter=True,  pad=True,  lead="all",     gain=0.92, chords="bm_cycle")),
    (122.8, 137.4, "climax",   dict(bass=True,  drums="climax", arp="gen",  counter=True,  pad=True,  lead="all",     gain=1.10, chords="climax")),
    (137.4, 145.5, "break",    dict(bass=False, drums="none",  arp="orig",  counter=False, pad=True,  lead="all",     gain=0.50, chords="pedal")),
    (145.5, 149.1, "reprise",  dict(bass=True,  drums="half",  arp="orig",  counter=False, pad=True,  lead="all",     gain=0.80)),
    (149.1, 163.3, "turn3",    dict(bass=True,  drums="half",  arp="orig",  counter=False, pad=True,  lead="all",     gain=0.72)),
    (163.3, 181.6, "finale",   dict(bass=True,  drums="full",  arp="gen",   counter=True,  pad=True,  lead="octave",  gain=1.15)),
    (181.6, 185.5, "outro",    dict(bass=True,  drums="half",  arp="orig",  counter=False, pad=True,  lead="all",     gain="fade")),
]

def sec_of(t_s):
    for s, e, name, d in SECTIONS:
        if s * BAR <= t_s < e * BAR:
            return name, d
    return "outro", SECTIONS[-1][3]

# ------------------------------------------------------------------ helpers
PENTA = {6, 8, 9, 11, 1, 4}   # F# minor pentatonic (F#,G#,A,B,C#,E)

def bar_chords(smoothed, b):
    """Return (root, qual) for bar b, honoring section overrides."""
    name, d = sec_of(b * BAR)
    s0 = next(sec[0] for sec in SECTIONS if sec[2] == name)
    if d.get("chords") == "bm_cycle":
        cyc = [(6, "min")] * 5 + [(11, "min")] * 5 + [(4, "maj")] * 5 + [(2, "maj")] * 5
        return cyc[int((b - s0) % len(cyc))]
    if d.get("chords") == "climax":
        cyc = [(6, "min")] * 4 + [(2, "maj")] * 4 + [(4, "maj")] * 4 + [(6, "min")] * 4
        return cyc[int((b - s0) % len(cyc))]
    if d.get("chords") == "pedal":
        return (6, "min")
    for c in smoothed:
        if c["bar"] == int(b):
            return (c["root"], c["qual"])
    return (6, "min")

def chord_tones_for(root, qual, bass_midi=42):
    ts = chord_tones(root, qual)
    while min(ts) < bass_midi + 12:
        ts = [t + 12 for t in ts]
    return ts

# ------------------------------------------------------------------ part generators
def gen_lead(lead_notes, chords_sm):
    """Lead part: transcribed notes, octave in finale, motif preview in intro."""
    out = []
    for n in lead_notes:
        name, d = sec_of(n["start_q"])
        midi = n["midi"]
        if d.get("lead") == "octave" and midi < 96:
            midi += 12
        if d.get("lead") == "motif":
            continue  # replaced by motif
        out.append({"start_q": n["start_q"], "end_q": n["end_q"], "midi": midi,
                    "vel": 100, "src": "orig"})
    # intro motif: first 2 bars of A1 lead, echoed, ending on held F#5
    motif = [n for n in out if 16.0 * BAR <= n["start_q"] < 18.0 * BAR]
    if motif:
        base = motif[0]["start_q"] - 16.0 * BAR
        for rep, (bs, ve, hold) in enumerate([(0.5, 100, 1.5), (2.5, 62, 1.5)]):
            for n in motif:
                st = bs * BAR + (n["start_q"] - 16.0 * BAR - base)
                out.append({"start_q": st, "end_q": st + max(0.15, n["end_q"] - n["start_q"]),
                            "midi": n["midi"], "vel": ve, "src": "motif"})
        out.append({"start_q": 4.0 * BAR, "end_q": 7.9 * BAR, "midi": 78.0,
                    "vel": 95, "src": "motif_hold"})  # F#5 held
    out.sort(key=lambda n: n["start_q"])
    return out

def gen_counter(lead_part, chords_sm):
    """3rd-below parallel harmony, chord-tone snapped; 6th in climax."""
    out = []
    for n in lead_part:
        if n["src"] == "motif":
            continue
        name, d = sec_of(n["start_q"])
        if not d.get("counter"):
            continue
        b = int(n["start_q"] // BAR)
        root, qual = bar_chords(chords_sm, b)
        tones = chord_tones_for(root, qual, bass_midi=36)
        iv = -9 if name == "climax" else -3
        tgt = n["midi"] + iv
        best = min(tones, key=lambda c: abs(c - tgt))
        midi = best if abs(best - tgt) <= 3 else tgt
        if midi < 53:
            midi += 12
        out.append({"start_q": n["start_q"], "end_q": n["end_q"], "midi": float(midi),
                    "vel": 78, "src": "counter"})
    return out

def gen_bass(bass_notes, chords_sm):
    """Transcribed bass (scale-snapped); B section reharmonized; build pickup."""
    SCALE = {6, 8, 9, 11, 1, 2, 4}
    def snap(midi, b):
        pc = round(midi) % 12
        if pc in SCALE:
            return midi
        root, _ = bar_chords(chords_sm, b)
        # prefer the neighbor that belongs to the bar's chord family
        cands = [s for s in SCALE if abs(((s - pc) % 12 + 12) % 12) == 1 or abs(((pc - s) % 12 + 12) % 12) == 1]
        pref = sorted(cands, key=lambda s: 0 if s == root else (1 if s in {(root + 3) % 12, (root + 7) % 12} else 2))
        if pref:
            tgt = pref[0]
            # keep octave, minimal move
            move = ((tgt - pc) % 12 + 12) % 12
            if move > 6:
                move -= 12
            return midi + move
        return midi
    out = []
    for n in bass_notes:
        name, d = sec_of(n["start_q"])
        if not d.get("bass"):
            continue
        b = int(n["start_q"] // BAR)
        if name == "b":
            root, qual = bar_chords(chords_sm, b)
            midi = {6: 42, 11: 47, 4: 40, 2: 38}[root]
            # octave pump: alternate root / root-12 every 8th
            pos8 = int(round((n["start_q"] % BAR) / EIGHTH))
            if pos8 % 2 == 1:
                midi -= 12
            out.append({"start_q": n["start_q"], "end_q": n["end_q"], "midi": float(midi),
                        "vel": 95, "src": "reharm"})
        else:
            out.append(dict(n, midi=snap(n["midi"], b), vel=95, src="orig"))
    # 16th pickup into A1 (bar 15.5-16)
    for k in range(4):
        st = (15.5 + 0.125 * k) * BAR
        out.append({"start_q": st, "end_q": st + 0.1, "midi": 42.0, "vel": 85, "src": "pickup"})
    out.sort(key=lambda n: n["start_q"])
    return out

def gen_arp(arp_notes, chords_sm):
    """Generated pentatonic 16th arps in dense sections; original accents elsewhere."""
    out = [dict(n, vel=70, src="orig") for n in arp_notes]
    rng = np.random.default_rng(172)
    for s, e, name, d in SECTIONS:
        if d.get("arp") != "gen":
            continue
        for b in np.arange(s, e, 1.0):
            root, qual = bar_chords(chords_sm, int(b))
            tones = chord_tones_for(root, qual, bass_midi=48)
            tones = [t for t in tones if t % 12 in PENTA or t - 1 % 12 in PENTA]
            if not tones:
                continue
            pat = [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1, 0, 1, 2, 3]
            for i in range(16):
                st = (b + i * 0.125) * BAR
                midi = tones[pat[i] % len(tones)] + (12 if i % 8 == 7 and name == "climax" else 0)
                vel = 55 + int(25 * (i % 2 == 0)) + rng.integers(-6, 7)
                out.append({"start_q": st, "end_q": st + 0.10, "midi": float(midi),
                            "vel": vel, "src": "gen"})
    out.sort(key=lambda n: n["start_q"])
    return out

def gen_pads(chords_sm, padB=False):
    """PadA: smoothed chords (pulse25). PadB: +12 triangle layer (climax/finale)."""
    out = []
    for b in range(int(N_BARS)):
        root, qual = bar_chords(chords_sm, b)
        name, d = sec_of(b * BAR)
        tones = chord_tones_for(root, qual, bass_midi=42)
        for m in tones:
            if padB and name in ("climax", "finale"):
                out.append({"start_q": b * BAR, "end_q": (b + 1) * BAR,
                            "midi": float(m + 12), "vel": 60, "src": "padB"})
            elif not padB:
                out.append({"start_q": b * BAR, "end_q": (b + 1) * BAR,
                            "midi": float(m), "vel": 85, "src": "padA"})
    return out

# ------------------------------------------------------------------ drums
def drum_patterns():
    """Returns list of (t, kind, vel). kinds: kick/snare/hat/crash/fill."""
    ev = []
    rng = np.random.default_rng(7)
    def add(t, kind, vel):
        ev.append((t, kind, vel))
    for s, e, name, d in SECTIONS:
        kind_d = d.get("drums")
        for b in np.arange(s, e, 1.0):
            t0 = b * BAR
            last_bar = b >= e - 1
            if kind_d == "full":
                add(t0, "kick", 108)
                add(t0 + 2 * BEAT, "kick", 104)
                add(t0 + 2 * BEAT, "snare", 100 + int(rng.integers(-4, 5)))
                for i in range(8):
                    v = 74 if i % 2 == 1 else 58
                    add(t0 + i * EIGHTH, "hat", v)
                if b % 4 == 0:
                    add(t0, "crash", 92)
                if last_bar:  # fill: 16th snare run into next section
                    for k in range(4):
                        add(t0 + (5.5 + 0.25 * k) * EIGHTH, "snare", 70 + 15 * k)
            elif kind_d == "climax":
                add(t0, "kick", 112); add(t0 + 2 * BEAT, "kick", 106)
                add(t0 + 2 * BEAT, "snare", 104)
                for i in range(8):
                    add(t0 + i * EIGHTH, "hat", 76 if i % 2 else 60)
                if b % 4 == 0:
                    add(t0, "crash", 100)
                if b >= e - 2:  # double-time kick
                    for k in range(8):
                        add(t0 + k * 0.5 * BEAT, "kick", 100)
            elif kind_d == "half":
                add(t0, "kick", 100)
                add(t0 + 2 * BEAT, "snare", 92)
                for i in (1, 3, 5, 7):
                    add(t0 + i * EIGHTH, "hat", 62)
            elif kind_d == "build":
                for i in range(8):
                    add(t0 + i * EIGHTH, "hat", 40 + int(rng.integers(0, 10)))
                if b >= 12:  # kick from bar 12, snare from bar 14 (density ramp)
                    add(t0, "kick", 96); add(t0 + 2 * BEAT, "kick", 92)
                if b >= 14:
                    add(t0 + 2 * BEAT, "snare", 88)
            elif kind_d == "none":
                pass
            # reprise: 和声预挂/节奏先现 handled by 'half'
    # extra: pickup crash into A1 (bar 15.75) and into finale (bar 162.75)
    add(15.75 * BAR, "crash", 70)
    add(163.25 * BAR, "crash", 95)
    ev.sort(key=lambda e: e[0])
    return ev

def render_drums(events, n=N):
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

# ------------------------------------------------------------------ main
def main():
    lead_notes = json.load(open(os.path.join(DATA, "lead_notes_clean.json")))
    bass_notes = json.load(open(os.path.join(DATA, "bass_notes_clean.json")))
    arp_notes = json.load(open(os.path.join(DATA, "arp_notes.json")))
    chords = json.load(open(os.path.join(DATA, "chords.json")))["bars"]
    sm = smooth_chords(chords, k=5)
    # scale-compatible snap (same as produce.py)
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
    lead = gen_lead(lead_notes, sm)
    counter = gen_counter(lead, sm)
    bass = gen_bass(bass_notes, sm)
    arp = gen_arp(arp_notes, sm)
    pads = gen_pads(sm)
    padsB = gen_pads(sm, padB=True)
    drums = drum_patterns()
    for name, part in [("lead", lead), ("counter", counter), ("bass", bass),
                       ("arp", arp), ("padA", pads), ("padB", padsB), ("drums", drums)]:
        print(f"  {name}: {len(part)} events")

    print("rendering…")
    rng = np.random.default_rng(11)
    def vel_jitter(part, amp=6):
        return part  # velocities already set
    # lead (with vibrato on long notes only)
    lead_long = [n for n in lead if n["end_q"] - n["start_q"] >= 0.3]
    lead_short = [n for n in lead if n["end_q"] - n["start_q"] < 0.3]
    L1 = render_notes(lead_long, "pulse", 0.9, N, vib_rate=12.0, vib_depth=5.0,
                      duty=0.25, duty_sweep=(0.125, 0.25, 0.06), sus=0.92, rel=0.06)
    L2 = render_notes(lead_short, "pulse", 0.9, N, duty=0.25, duty_sweep=(0.125, 0.25, 0.04),
                      sus=0.9, rel=0.04)
    lead_sig = L1 + L2
    counter_sig = render_notes(counter, "pulse", 0.5, N, duty=0.25, sus=0.9, rel=0.05)
    bass_sig = render_notes(bass, "pulse", 1.0, N, duty=0.5, staccato=0.94,
                            sus=0.92, rel=0.02, detune_cents=-7.0)
    nyq = SR / 2
    bass_sig = sosfiltfilt(butter(4, 800 / nyq, btype="low", output="sos"), bass_sig)
    arp_sig = render_notes(arp, "pulse", 0.5, N, duty=0.125, staccato=0.8, sus=0.9, rel=0.02)
    pad_sig = render_notes(pads, "pulse", 1.0, N, duty=0.25, staccato=1.0, sus=0.7,
                           rel=0.25, vib_rate=5.0, vib_depth=2.0)
    padB_sig = render_notes(padsB, "pulse", 0.55, N, duty=0.125, staccato=1.0, sus=0.6,
                            rel=0.25, vib_rate=5.0, vib_depth=2.0)
    drum_sig = render_drums(drums)

    # section gain automation (applied POST-compressor so dynamics survive glue)
    def sec_gain(t_s):
        name, d = sec_of(t_s)
        g = d.get("gain")
        if g == "fade":
            return 0.9 * np.clip(1 - (t_s - 181.6 * BAR) / (3.5 * BAR), 0.15, 1.0)
        return g
    tgrid = np.arange(N) / SR
    gain_curve = np.array([sec_gain(t) for t in tgrid])

    # band balance (NNLS on the 7 stems)
    y_orig, _ = librosa.load(SRC, sr=SR, mono=True)
    targets = {"low": band_rms(y_orig, SR, 30, 200), "mid": band_rms(y_orig, SR, 200, 4000),
               "high": band_rms(y_orig, SR, 4000, 16000)}
    stems = {"lead": lead_sig, "counter": counter_sig, "bass": bass_sig, "arp": arp_sig,
             "pad": pad_sig, "padB": padB_sig, "drums": drum_sig}
    for vn in stems:
        vx = stems[vn]
        r = np.sqrt(np.mean(vx ** 2)) + 1e-9
        stems[vn] = vx / r * 0.12
    # musical balance (fixed weights — this is now a creative mix, not a fit)
    BAL = {"lead": 0.90, "counter": 0.50, "bass": 1.20, "arp": 0.35,
           "pad": 0.50, "padB": 0.30, "drums": 0.70}
    g = np.array([BAL[vn] for vn in stems])
    print("gains:", {vn: round(float(gi), 3) for vn, gi in zip(stems, g)})

    # stereo production
    L = np.zeros(N); R = np.zeros(N)
    gL, gC, gB, gA, gP, gPB, gD = g
    # lead: center + detuned chorus pair + slap delay
    det1 = render_notes(lead_long, "pulse", 0.10 * gL, N, vib_rate=12.0, vib_depth=5.0,
                        duty=0.25, duty_sweep=(0.125, 0.25, 0.06), sus=0.92, rel=0.06,
                        detune_cents=5.0)
    det2 = render_notes(lead_long, "pulse", 0.10 * gL, N, vib_rate=12.0, vib_depth=5.0,
                        duty=0.25, duty_sweep=(0.125, 0.25, 0.06), sus=0.92, rel=0.06,
                        detune_cents=-5.0)
    slap = np.zeros(N)
    dn = int(3 * EIGHTH * SR / 2)  # 3/16 = dotted 8th slap? use 3 16ths = 0.261s
    dn = int(0.2612 * SR)
    src_l = stems["lead"] * 0.85 * gL
    slap[dn:] = src_l[:-dn] * 0.18
    l1, r1 = to_stereo(src_l, 0.0)
    l2, r2 = to_stereo(det1 * gL, -0.55)
    l3, r3 = to_stereo(det2 * gL, 0.55)
    ls, rs = to_stereo(slap, 0.25)
    L += l1 + l2 + l3 + ls; R += r1 + r2 + r3 + rs
    # counter: slightly left
    lc, rc = to_stereo(stems["counter"] * gC, -0.25)
    L += lc; R += rc
    # bass: center
    lb, rb = to_stereo(stems["bass"] * gB, 0.0)
    L += lb; R += rb
    # arp: ping-pong 8th delay
    dd = int(EIGHTH * SR)
    ad = stems["arp"] * gA
    acc = ad.copy()
    for k in range(1, 5):
        acc[dd * k:] += ad[:-dd * k] * 0.32 ** k
    acc = sosfiltfilt(butter(4, 6000 / nyq, btype="low", output="sos"), acc)
    la, ra = to_stereo(acc * 0.7, -0.45)
    la2, ra2 = to_stereo(ad * 0.5, 0.45)
    L += la + la2; R += ra + ra2
    # pads: wide
    pl = render_notes(pads, "pulse", 0.5 * gP, N, duty=0.25, staccato=1.0, sus=0.7,
                      rel=0.25, detune_cents=6.0)
    pr = render_notes(pads, "pulse", 0.5 * gP, N, duty=0.25, staccato=1.0, sus=0.7,
                      rel=0.25, detune_cents=-6.0)
    lp, rp = to_stereo(stems["pad"] * 0.5 * gP, -0.3)
    lp2, rp2 = to_stereo(pl, -0.8)
    lp3, rp3 = to_stereo(pr, 0.8)
    L += lp + lp2 + lp3; R += rp + rp2 + rp3
    lpb, rpb = to_stereo(stems["padB"] * gPB, 0.0)
    L += lpb; R += rpb
    # drums: center + subtle room
    ld, rd = to_stereo(stems["drums"] * gD, 0.0)
    L += ld; R += rd
    # reverb sends (drums minimal room)
    wet = schroeder((src_l * 0.5 + stems["pad"] * 0.5 * gP + ad * 0.25).astype(np.float64),
                    SR, rt60=0.75, wet=0.30)
    L += wet[:, 0]; R += wet[:, 1]
    wet_d = schroeder((stems["drums"] * gD * 0.35).astype(np.float64), SR, rt60=0.5, wet=0.12)
    L += wet_d[:, 0]; R += wet_d[:, 1]
    mix = np.stack([L, R], axis=-1)
    mono = (L + R) / 2

    # dynamics: shape to arrangement (not to original) — gentle glue + limiter
    # glue compressor (feed-forward, soft knee)
    from scipy.signal import lfilter
    env = np.abs(mono)
    env = lfilter([1 - 0.9995], [1, -0.9995], env)  # ~20ms peak follow
    thr, ratio, knee = 0.28, 1.8, 0.15
    def comp_gain(x):
        over = x - thr
        soft = np.where(over > 0, over - knee / 2 + (knee / 2) * np.tanh(over / knee * 2), 0)
        g = 1 - (1 - 1 / ratio) * np.clip(soft, 0, None) / (x + 1e-9)
        return np.clip(g, 0.35, 1.0)
    gc = comp_gain(env)
    gc = uniform_filter1d(gc, int(0.01 * SR // 1))  # 10ms smoothing
    mix *= gc[:, None]
    # arrangement dynamics (section gains + outro fade) after glue
    mix *= gain_curve[:, None]
    mix *= 0.22 / (np.sqrt(np.mean(mix ** 2)) + 1e-9)
    peak = np.max(np.abs(mix))
    if peak > 0.97:  # true soft ceiling: only shave the very top
        mix = mix * (0.97 / peak)
    _r2 = float(np.sqrt(np.mean(mix ** 2)))
    print(f"  master: final RMS {_r2:.4f} (peak {peak:.3f})")
    sf.write(os.path.join(AUD, "arrangement_v3.wav"), mix, SR)
    subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", os.path.join(AUD, "arrangement_v3.wav"),
                    "-codec:a", "libmp3lame", "-q:a", "2", os.path.join(AUD, "arrangement_v3.mp3")])
    print("wrote audio/arrangement_v3.wav/.mp3")

    # ---- report ----
    report = {
        "sections": [{"name": n, "bars": [s, e], "t": [round(s * BAR, 2), round(e * BAR, 2)],
                      "density": d} for s, e, n, d in SECTIONS],
        "note_counts": {k: len(v) for k, v in [("lead", lead), ("counter", counter),
                                               ("bass", bass), ("arp", arp), ("pads", pads)]},
        "gains": {vn: float(gi) for vn, gi in zip(stems, g)},
    }
    # per-section RMS (dynamics contrast check)
    for s, e, name, d in SECTIONS:
        a = int(s * BAR * SR); b = int(e * BAR * SR)
        r = float(np.sqrt(np.mean(mix[a:b, :] ** 2)))
        report.setdefault("section_rms", {})[name] = round(r, 4)
    # band RMS final
    for bn, (lo, hi) in {"low": (30, 200), "mid": (200, 4000), "high": (4000, 16000)}.items():
        report.setdefault("band_rms", {})[bn] = round(band_rms(mix[:, 0], SR, lo, hi), 4)
    json.dump(report, open(os.path.join(DATA, "arrangement_v3.json"), "w"), indent=2)
    print("section RMS:", {k: v for k, v in report["section_rms"].items()})
    print("band RMS:", report["band_rms"])

    # ---- MIDI export ----
    import mido
    from mido import MidiFile, MidiTrack, MetaMessage, Message
    tpb = 480
    mid = MidiFile(ticks_per_beat=tpb)
    tempo_us = int(60.0 / 172.27 * 1e6)
    def add_track(name, notes, channel, program, base_vel=96):
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
        # section CC11 expression
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
    dr_tr = MidiTrack()
    dr_tr.append(MetaMessage("track_name", name="Drums", time=0))
    dr_tr.append(MetaMessage("set_tempo", tempo=tempo_us, time=0))
    GM = {"kick": 36, "snare": 38, "hat": 42, "crash": 49}
    ev = []
    for t, kind, vel in drums:
        ev.append((int(t * 172.27 / 60 * tpb), GM[kind], int(vel)))
    ev.sort()
    last = 0
    for t, note, vel in ev:
        dr_tr.append(Message("note_on", note=note, velocity=vel, channel=9, time=t - last))
        dr_tr.append(Message("note_off", note=note, velocity=0, channel=9, time=80))
        last = t
    mid.tracks.append(dr_tr)
    mid.save(os.path.join(OUT, "Infinity_arrangement_v3.mid"))
    print("wrote Infinity_arrangement_v3.mid")

    # ---- FluidSynth render ----
    sf2 = os.path.join(OUT, "..", "..", "soundfonts", "MuseScore_General.sf2")
    if os.path.exists(sf2):
        subprocess.run(["fluidsynth", "-F", os.path.join(AUD, "arrangement_v3_sf.wav"), "-r", "44100",
                        "-R", "0.9", "-C", "0", "-g", "1.2", sf2,
                        os.path.join(OUT, "Infinity_arrangement_v3.mid")], capture_output=True)
        if os.path.exists(os.path.join(AUD, "arrangement_v3_sf.wav")):
            subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", os.path.join(AUD, "arrangement_v3_sf.wav"),
                            "-codec:a", "libmp3lame", "-q:a", "2", os.path.join(AUD, "arrangement_v3_sf.mp3")])
            print("wrote audio/arrangement_v3_sf.mp3")

if __name__ == "__main__":
    main()
