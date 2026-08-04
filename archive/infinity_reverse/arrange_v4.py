#!/usr/bin/env python3
"""Stage 10 — v4 VARIATION ARRANGEMENT.

用户要求:小节内变奏增多(音符变短变密、变奏数量增加)+ 音色组合优化。

节奏变奏引擎:
  bass: 6 种 pattern(P0 pump8 / P1 octave8 / P2 16run / P3 syncop / P4 walk / P5 double16)
        按段落做 4-8 小节轮换,16 分网格,ghost 力度
  lead: 长音(>=3 8分)拆 8 分重复(力度衰减);句末(4 小节乐句第 4 小节)
        16 分和弦音装饰跑;音前 16 分先现(anticipation)
  counter: 平行和声 + 16 分错拍对位
  arp: 4 种 pattern(A updown / B broken / C wide / D endflam)按段轮换
  drums: 4 小节变奏循环(ghost snare / 开镲 / fill 变体)+ 边界 fill
音色组合(按段落映射):
  lead: intro/build/a2/reprise=pulse25, a1/b/climax/finale=pulse12.5,
        turn*=square50, intro/outro=triangle
  bass: square(800Hz LP),B 段 triangle;counter: pulse25, B=triangle, climax=square50
  arp: 轻段落 triangle,密段落 pulse12.5;pad: pulse25, break/outro=triangle
  glock: intro/outro 高八度 triangle 点缀层
Outputs: audio/arrangement_v4.wav|mp3, Infinity_arrangement_v4.mid,
         audio/arrangement_v4_sf.mp3, data/arrangement_v4.json
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
from arrange import SECTIONS, sec_of, bar_chords, chord_tones_for, smooth_chords, gen_counter, gen_pads

OUT = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(OUT, "audio")
DATA = os.path.join(OUT, "data")
BAR = 4 * 0.34830
BEAT = 0.34830
S16 = EIGHTH / 2

# ================================================================== BASS PATTERNS
# each pattern: list of (pos16, semitone_offset_from_root, vel)
BP = {
    "P0": [(i * 2, 0, 95) for i in range(8)],                                  # pump 8ths
    "P1": [(i * 2, 0 if i % 2 == 0 else -12, 92) for i in range(8)],           # octave pump
    "P2": [(i, 0 if i % 2 == 0 else -12, 88 if i % 2 == 0 else 46) for i in range(16)],  # 16ths drive
    "P3": [(0, 0, 95), (4, 0, 95), (6, -12, 88), (10, 0, 92), (12, -12, 84), (14, 0, 80)],  # syncop
    "P4": [(i * 2, 0 if i % 4 < 2 else 7, 90) for i in range(8)],              # root/5th walk
    "P5": [(i, 0 if i % 2 == 0 else -12, 100) for i in range(16)],             # double16 drive
}
BASS_CYCLE = {
    "build": ["P0"] * 4 + ["P1"] * 4,
    "a1": ["P1", "P2", "P0", "P3"],
    "turn1": ["P0", "P3", "P0", "P3"],
    "a2": ["P1", "P2", "P3", "P4"] * 2,
    "turn2": ["P0", "P3"],
    "b": ["P1", "P2", "P0", "P3"],
    "climax": ["P2", "P1", "P5", "P5"],
    "reprise": ["P0", "P1"],
    "turn3": ["P0", "P3", "P0", "P3"],
    "finale": ["P1", "P2", "P3", "P4", "P2", "P5", "P1", "P2"],
    "outro": ["P0", "P3"],
}
ROOT_MIDI = {6: 42, 11: 47, 4: 40, 2: 38}

def gen_bass_v4(bass_notes, chords_sm):
    out = []
    used = set()
    for s, e, name, d in SECTIONS:
        if not d.get("bass"):
            continue
        cyc = BASS_CYCLE.get(name, ["P0"])
        for bi, b in enumerate(np.arange(s, e, 1.0)):
            pat = cyc[bi % len(cyc)]
            used.add((name, pat))
            root, qual = bar_chords(chords_sm, int(b))
            base = ROOT_MIDI[root]
            if name == "b":  # reharm octave pump style
                pass
            t0 = b * BAR
            for pos, off, vel in BP[pat]:
                st = t0 + pos * S16
                dur = 2 * S16 if pos % 2 == 0 else 2 * S16
                midi = base + off
                if name == "b" and pos % 4 == 2:
                    midi -= 12
                out.append({"start_q": st, "end_q": st + dur, "midi": float(midi),
                            "vel": vel, "src": f"bp:{pat}"})
    # 16th pickups into A1 / climax / finale (3 notes, ending before the downbeat)
    for bt, root in [(15.625, 42), (122.625, 42), (162.875, 42)]:
        for k in range(3):
            st = bt * BAR + (k + 1) * S16
            out.append({"start_q": st, "end_q": st + S16, "midi": float(root),
                        "vel": 85 - 10 * k, "src": "pickup"})
    out.sort(key=lambda n: n["start_q"])
    return out, sorted(used)

# ================================================================== LEAD ACTIVATION
DENSE = ("a1", "a2", "b", "climax", "finale")

def activate_lead(lead_notes, chords_sm):
    out = []
    for n in lead_notes:
        sec, d = sec_of(n["start_q"])
        dur = n["end_q"] - n["start_q"]
        if sec in DENSE and dur >= 3 * EIGHTH:
            t = n["start_q"]
            k = 0
            while t < n["end_q"] - 0.06:
                e = min(t + 0.9 * EIGHTH, n["end_q"])
                out.append({"start_q": t, "end_q": e, "midi": n["midi"],
                            "vel": int(102 * 0.82 ** k), "src": "split"})
                t = e
                k += 1
        else:
            out.append(dict(n))
    # phrase-end ornaments + anticipations (dense sections only)
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
                tones = chord_tones_for(root, qual, bass_midi=48)
                tones = [t for t in tones if t > last["midi"] - 14]
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
    # anticipations: 16th chord tone before notes with a gap
    ordered = sorted(out, key=lambda n: n["start_q"])
    for i, n in enumerate(ordered):
        sec, d = sec_of(n["start_q"])
        if sec not in DENSE or n.get("src", "orig") in ("orn", "split"):
            continue
        prev_end = ordered[i - 1]["end_q"] if i > 0 else -1
        gap = n["start_q"] - prev_end
        if 0.17 <= gap <= 0.30:
            root, qual = bar_chords(chords_sm, int(n["start_q"] // BAR))
            tones = chord_tones_for(root, qual, bass_midi=48)
            tgt = min(tones, key=lambda c: abs(c - (n["midi"] - 5)))
            out.append({"start_q": n["start_q"] - 0.087, "end_q": n["start_q"] - 0.01,
                        "midi": float(tgt), "vel": 48, "src": "ant"})
    out.sort(key=lambda n: n["start_q"])
    return out

def activate_counter(counter, chords_sm):
    """Split long counter notes into 8th repeats + 16th-offset syncopation."""
    out = []
    for n in counter:
        sec, d = sec_of(n["start_q"])
        dur = n["end_q"] - n["start_q"]
        if sec in DENSE and dur >= 0.40:
            t = n["start_q"] + 0.087
            k = 0
            while t < n["end_q"] - 0.06:
                e = min(t + 0.9 * EIGHTH, n["end_q"])
                out.append({"start_q": t, "end_q": e, "midi": n["midi"],
                            "vel": int(82 * 0.85 ** k), "src": "sync"})
                t = e
                k += 1
        elif sec in DENSE and dur >= 0.25:
            out.append({"start_q": n["start_q"] + 0.087, "end_q": n["end_q"] + 0.087,
                        "midi": n["midi"], "vel": n["vel"], "src": "sync"})
        else:
            out.append(dict(n))
    return out

# ================================================================== ARP PATTERNS
ARP_PAT = {
    "A": [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1, 0, 1, 2, 3],
    "B": [0, 2, 1, 3, 0, 2, 1, 3, 0, 2, 1, 3, 0, 2, 1, 3],
    "C": [0, 1, 2, 3, 4, 3, 2, 1, 0, 1, 2, 3, 4, 3, 2, 1],
    "D": [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1, 0, 1, 2, 2],  # end double (32nd flam)
}
ARP_CYCLE = {"a1": ["A", "B"], "a2": ["A", "B", "C"], "b": ["A", "B"],
             "climax": ["C", "A", "B", "D"], "finale": ["A", "B", "C", "B"]}

def gen_arp_v4(arp_notes, chords_sm):
    out = [dict(n, vel=70, src="orig") for n in arp_notes]
    rng = np.random.default_rng(172)
    for s, e, name, d in SECTIONS:
        if d.get("arp") != "gen":
            continue
        cyc = ARP_CYCLE.get(name, ["A"])
        for bi, b in enumerate(np.arange(s, e, 1.0)):
            pat = ARP_PAT[cyc[bi % len(cyc)]]
            root, qual = bar_chords(chords_sm, int(b))
            tones = chord_tones_for(root, qual, bass_midi=48)
            if name == "climax":
                tones = tones + [tones[0] + 12]
            for i in range(16):
                st = (b + i * 0.125) * BAR
                midi = tones[pat[i] % len(tones)]
                if i == 15 and pat == ARP_PAT["D"] and name == "climax":
                    st2 = st + S16
                    out.append({"start_q": st2, "end_q": st2 + 0.07, "midi": float(midi),
                                "vel": 68, "src": "flam"})
                vel = 60 + int(22 * (i % 2 == 0)) + int(rng.integers(-6, 7))
                out.append({"start_q": st, "end_q": st + 0.09, "midi": float(midi),
                            "vel": vel, "src": f"arp:{cyc[bi % len(cyc)]}"})
    out.sort(key=lambda n: n["start_q"])
    return out

# ================================================================== DRUMS v4 (4-bar variation)
def drum_patterns_v4():
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
            if kd == "full":
                add(t0, "kick", 108); add(t0 + 2 * BEAT, "kick", 104)
                add(t0 + 2 * BEAT, "snare", 100)
                acc = [2, 6]
                if p == 1: acc = [1, 5]
                if p == 2: acc = [3, 7]
                for i in range(8):
                    add(t0 + i * EIGHTH, "hat", 74 if i in acc else 58)
                if p == 1:
                    add(t0 + 6.5 * EIGHTH, "snare", 36)          # ghost snare
                if p == 2:
                    add(t0 + 7.5 * EIGHTH, "hat", 52)            # open-ish hat
                    add(t0 + 7.5 * EIGHTH, "crash", 30)          # light crash
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
                if p == 1:
                    add(t0 + 6.5 * EIGHTH, "snare", 40)
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
                if p == 2:
                    add(t0 + 6.5 * EIGHTH, "hat", 48)
                if p == 3:
                    for k in range(3):
                        add(t0 + (6 + 0.5 * k) * EIGHTH, "snare", 60 + 12 * k)
            elif kd == "build":
                for i in range(8):
                    add(t0 + i * EIGHTH, "hat", 40 + int(rng.integers(0, 10)))
                if b >= 12:
                    add(t0, "kick", 96); add(t0 + 2 * BEAT, "kick", 92)
                if b >= 14:
                    add(t0 + 2 * BEAT, "snare", 88)
    add(15.75 * BAR, "crash", 70)
    add(163.25 * BAR, "crash", 95)
    ev.sort(key=lambda e: e[0])
    return ev

def render_drums_v4(events, n=N):
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
            dcy = 0.05 if vel >= 90 else 0.012
            out += noise_burst(t, 0.06 if dcy > 0.02 else 0.05, n, hp=6500,
                               decay=dcy, gain=0.22 * g, rng=rng)
        elif kind == "crash":
            out += noise_burst(t, 1.0, n, hp=2500, lp=9500, decay=0.30, gain=0.3 * g, rng=rng)
    return out

# ================================================================== TIMBRE MAPS
LEAD_WAVE = {"intro": "triangle", "build": "pulse", "a1": "pulse", "turn1": "pulse",
             "a2": "pulse", "turn2": "pulse", "b": "pulse", "climax": "pulse",
             "break": None, "reprise": "pulse", "turn3": "pulse", "finale": "pulse",
             "outro": "triangle"}
LEAD_DUTY = {"build": 0.25, "a1": 0.125, "turn1": 0.5, "a2": 0.25, "turn2": 0.5,
             "b": 0.125, "climax": 0.125, "reprise": 0.25, "turn3": 0.5, "finale": 0.125}
COUNTER_WAVE = {"a1": "pulse", "a2": "pulse", "b": "triangle", "climax": "pulse", "finale": "pulse"}
COUNTER_DUTY = {"a1": 0.25, "a2": 0.25, "climax": 0.5, "finale": 0.25}
ARP_WAVE = {"a1": "pulse", "a2": "pulse", "b": "pulse", "climax": "pulse", "finale": "pulse"}
ARP_DUTY = {"a1": 0.125, "a2": 0.125, "b": 0.125, "climax": 0.125, "finale": 0.125}
PAD_TRI = {"break", "outro"}

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
    # counter from the ORIGINAL lead (before activation), then activated
    lead_raw = [dict(n, src="orig") for n in lead_notes]
    from arrange import gen_counter
    counter0 = gen_counter(lead_raw, sm)
    lead = activate_lead(lead_notes, sm)
    counter = activate_counter(counter0, sm)
    bass, bass_used = gen_bass_v4(bass_notes, sm)
    arp = gen_arp_v4(arp_notes, sm)
    pads = gen_pads(sm)
    padsB = gen_pads(sm, padB=True)
    drums = drum_patterns_v4()
    # glock: intro+outro high octave doubling of lead
    glock = [dict(n, midi=min(n["midi"] + 12, 104), vel=55, src="glock")
             for n in lead if sec_of(n["start_q"])[0] in ("intro", "outro")]
    for name, part in [("lead", lead), ("counter", counter), ("bass", bass),
                       ("arp", arp), ("padA", pads), ("padB", padsB),
                       ("glock", glock), ("drums", drums)]:
        print(f"  {name}: {len(part)} events")
    print("  bass patterns used:", bass_used)

    print("rendering…")
    rng = np.random.default_rng(11)
    lead_long = [n for n in lead if n["end_q"] - n["start_q"] >= 0.3]
    lead_short = [n for n in lead if n["end_q"] - n["start_q"] < 0.3]
    lead_sig = render_by_section(lead_long, LEAD_WAVE, 0.85, LEAD_DUTY,
                                 vib_rate=12.0, vib_depth=5.0, sus=0.9, rel=0.05)
    lead_sig += render_by_section(lead_short, LEAD_WAVE, 0.85, LEAD_DUTY,
                                  sus=0.85, rel=0.04)
    counter_sig = render_by_section(counter, COUNTER_WAVE, 0.5, COUNTER_DUTY,
                                    sus=0.88, rel=0.05)
    bass_sig = np.zeros(N)
    for s, e, name, d in SECTIONS:
        if not d.get("bass"):
            continue
        sub = [n for n in bass if s * BAR <= n["start_q"] < e * BAR]
        if sub:
            wf = "triangle" if name == "b" else "pulse"
            dut = 0.5
            bass_sig += render_notes(sub, wf, 1.0, N, duty=dut, staccato=0.92,
                                     sus=0.9, rel=0.015, detune_cents=-7.0)
    nyq = SR / 2
    bass_sig = sosfiltfilt(butter(4, 800 / nyq, btype="low", output="sos"), bass_sig)
    arp_sig = render_by_section(arp, ARP_WAVE, 0.5, ARP_DUTY, staccato=0.7,
                                sus=0.9, rel=0.02)
    # pads: triangle in break/outro
    pad_sig = np.zeros(N)
    for s, e, name, d in SECTIONS:
        sub = [n for n in pads if s * BAR <= n["start_q"] < e * BAR]
        if sub:
            wf = "triangle" if name in PAD_TRI else "pulse"
            pad_sig += render_notes(sub, wf, 1.0, N, duty=0.25, staccato=1.0,
                                    sus=0.7, rel=0.25, vib_rate=5.0, vib_depth=2.0)
    padB_sig = render_notes(padsB, "pulse", 0.55, N, duty=0.125, staccato=1.0,
                            sus=0.6, rel=0.25, vib_rate=5.0, vib_depth=2.0)
    glock_sig = render_notes(glock, "triangle", 0.16, N, staccato=0.6, sus=0.8, rel=0.1)
    drum_sig = render_drums_v4(drums)

    # section gain automation (post-compressor)
    def sec_gain(t_s):
        name, d = sec_of(t_s)
        g = d.get("gain")
        if g == "fade":
            return 0.9 * np.clip(1 - (t_s - 181.6 * BAR) / (3.5 * BAR), 0.15, 1.0)
        return g
    tgrid = np.arange(N) / SR
    gain_curve = np.array([sec_gain(t) for t in tgrid])

    # balance
    stems = {"lead": lead_sig, "counter": counter_sig, "bass": bass_sig, "arp": arp_sig,
             "pad": pad_sig, "padB": padB_sig, "glock": glock_sig, "drums": drum_sig}
    for vn in stems:
        vx = stems[vn]
        r = np.sqrt(np.mean(vx ** 2)) + 1e-9
        stems[vn] = vx / r * 0.12
    BAL = {"lead": 0.95, "counter": 0.50, "bass": 1.25, "arp": 0.38,
           "pad": 0.50, "padB": 0.30, "glock": 0.16, "drums": 0.72}
    g = np.array([BAL[vn] for vn in stems])
    print("gains:", {vn: round(float(gi), 3) for vn, gi in zip(stems, g)})

    # stereo production
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
    lg, rg = to_stereo(stems["glock"] * gG, 0.3)
    L += lg; R += rg
    ld, rd = to_stereo(stems["drums"] * gD, 0.0)
    L += ld; R += rd
    wet = schroeder((src_l * 0.5 + stems["pad"] * 0.5 * gP + ad * 0.25).astype(np.float64),
                    SR, rt60=0.75, wet=0.30)
    L += wet[:, 0]; R += wet[:, 1]
    wet_d = schroeder((stems["drums"] * gD * 0.35).astype(np.float64), SR, rt60=0.5, wet=0.12)
    L += wet_d[:, 0]; R += wet_d[:, 1]
    mix = np.stack([L, R], axis=-1)
    mono = (L + R) / 2

    # glue + dynamics + master
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
    sf.write(os.path.join(AUD, "arrangement_v4.wav"), mix, SR)
    subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", os.path.join(AUD, "arrangement_v4.wav"),
                    "-codec:a", "libmp3lame", "-q:a", "2", os.path.join(AUD, "arrangement_v4.mp3")])
    print("wrote audio/arrangement_v4.wav/.mp3")

    report = {
        "sections": [{"name": n, "t": [round(s * BAR, 2), round(e * BAR, 2)]} for s, e, n, d in SECTIONS],
        "note_counts": {k: len(v) for k, v in [("lead", lead), ("counter", counter),
                                               ("bass", bass), ("arp", arp), ("pads", pads),
                                               ("glock", glock), ("drums", drums)]},
        "bass_patterns": bass_used,
        "gains": {vn: float(gi) for vn, gi in zip(stems, g)},
        "timbre_map": {"lead_wave": LEAD_WAVE, "lead_duty": LEAD_DUTY,
                       "counter": {k: v for k, v in COUNTER_WAVE.items()},
                       "bass_b_section": "triangle", "pad_triangle_sections": sorted(PAD_TRI)},
    }
    for s, e, name, d in SECTIONS:
        a = int(s * BAR * SR); b = int(e * BAR * SR)
        report.setdefault("section_rms", {})[name] = round(float(np.sqrt(np.mean(mix[a:b, :] ** 2))), 4)
    json.dump(report, open(os.path.join(DATA, "arrangement_v4.json"), "w"), indent=2)
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
    mid.save(os.path.join(OUT, "Infinity_arrangement_v4.mid"))
    print("wrote Infinity_arrangement_v4.mid")

    sf2 = os.path.join(OUT, "..", "..", "soundfonts", "MuseScore_General.sf2")
    if os.path.exists(sf2):
        subprocess.run(["fluidsynth", "-F", os.path.join(AUD, "arrangement_v4_sf.wav"), "-r", "44100",
                        "-R", "0.9", "-C", "0", "-g", "1.2", sf2,
                        os.path.join(OUT, "Infinity_arrangement_v4.mid")], capture_output=True)
        if os.path.exists(os.path.join(AUD, "arrangement_v4_sf.wav")):
            subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", os.path.join(AUD, "arrangement_v4_sf.wav"),
                            "-codec:a", "libmp3lame", "-q:a", "2", os.path.join(AUD, "arrangement_v4_sf.mp3")])
            print("wrote audio/arrangement_v4_sf.mp3")

if __name__ == "__main__":
    main()
