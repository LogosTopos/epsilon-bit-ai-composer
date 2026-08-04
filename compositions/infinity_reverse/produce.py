#!/usr/bin/env python3
"""Stage 8 — 'Song version' production render (v2).

Fixes vs v1:
  - cleaned transcriptions (lead_notes_clean / bass_notes_clean)
  - chord smoothing: 5-bar median filter over (root, quality) sequence
  - production chain: detuned stereo chorus on lead, ping-pong delay on arp,
    wide detuned pad, Schroeder reverb sends, dynamics matching
  - exports MIDI v2 and renders a FluidSynth (MuseScore_General.sf2) reference
Outputs: audio/reconstruction_v2.wav|mp3, audio/reconstruction_sf.mp3,
         Infinity_reconstruction_v2.mid, data/recon_metrics_v2.json
"""
import json
import os
import subprocess
import numpy as np
import librosa
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, hilbert
from scipy.ndimage import uniform_filter1d
from reconstruct import (SR, DUR, N, EIGHTH, SIXTEENTH, SRC,
                         render_notes, pulse_bank, triangle_bank, adsr_envelope,
                         noise_burst, kick_synth, band_rms)

OUT = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(OUT, "audio")
DATA = os.path.join(OUT, "data")
PLT = os.path.join(OUT, "plots")

# ---------------------------------------------------------------- schroeder reverb
def schroeder(x, sr, rt60=0.8, wet=0.3, stereo=True):
    """4 comb + 2 allpass reverb (mono in, mono/stereo out)."""
    def comb_len(s):
        return int(s * sr)
    combs = [(0.0297, 0.72), (0.0371, 0.70), (0.0411, 0.68), (0.0437, 0.66)]
    aps = [0.005, 0.0017]
    def process(sig, seed_off):
        y = np.zeros_like(sig)
        for cl, g in combs:
            L = comb_len(cl + seed_off)
            buf = np.zeros(L)
            for i in range(len(sig)):
                b = buf[i % L]
                y[i] += b
                buf[i % L] = sig[i] + g * b
        # allpass
        for ap in aps:
            L = comb_len(ap)
            buf = np.zeros(L)
            for i in range(len(sig)):
                b = buf[i % L]
                buf[i % L] = sig[i] + 0.5 * b
                y[i] = -0.5 * y[i] + b
        return y
    # runtime: python loops over 11M samples x4 combs x2 channels = too slow; use FFT-free
    # efficient comb via lfilter
    from scipy.signal import lfilter
    def fast_comb(sig, L, g):
        a = np.zeros(L + 1); a[0] = 1; a[L] = -g
        return lfilter([1], a, sig)
    def fast_allpass(sig, L, g=0.5):
        b = np.zeros(L + 1); b[0] = g; b[L] = 1
        a = np.zeros(L + 1); a[0] = 1; a[L] = g
        return lfilter(b, a, sig)
    def fast_process(sig, off):
        y = np.zeros_like(sig)
        for cl, g in combs:
            y += fast_comb(sig, comb_len(cl + off), g)
        y /= len(combs)
        for ap in aps:
            y = fast_allpass(y, comb_len(ap))
        return y
    if stereo:
        L = fast_process(x, 0.0)
        R = fast_process(x, 0.0007)
        return wet * np.stack([L, R], axis=-1)
    y = fast_process(x, 0.0)
    return wet * y

def to_stereo(mono, pan=0.0):
    """pan in [-1,1]; returns (L, R) arrays."""
    a = (pan + 1) / 2
    return mono * (1 - a) * 1.414, mono * a * 1.414

# ---------------------------------------------------------------- chord smoothing
NOTE_OFF = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6,
            "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
def parse_chord(name):
    name = name.replace("♯", "#").replace("♭", "b")
    root_s = name
    qual = "maj"
    for suf, q in [("sus", "sus"), ("m", "min"), ("7", "7"), ("maj7", "maj7")]:
        if root_s.endswith(suf):
            root_s = root_s[:-len(suf)]; qual = q
            break
    return NOTE_OFF[root_s], qual

def chord_tones(root, qual, bass_midi=42):
    if qual == "min":
        ts = [root + 60, root + 63, root + 67]
    elif qual == "sus":
        ts = [root + 60, root + 65, root + 67]
    else:
        ts = [root + 60, root + 64, root + 67]
    # avoid mud: keep at least an octave above bass
    while min(ts) < bass_midi + 12:
        ts = [t + 12 for t in ts]
    return ts

def smooth_chords(chords, k=5):
    """median-filter the (root, qual) sequence; bars are 4 beats."""
    bars = sorted(set(c["bar"] for c in chords))
    seq = {c["bar"]: (c["root"], c["qual"]) for c in chords}
    out = []
    for b in bars:
        lo = max(0, b - k // 2)
        hi = min(max(bars) + 1, b + k // 2 + 1)
        win = [seq[x] for x in range(lo, hi) if x in seq]
        if not win:
            continue
        roots = np.array([w[0] for w in win])
        # circular median on 12-pitch class
        ph = np.exp(2j * np.pi * roots / 12)
        med_root = int(round(np.angle(np.sum(ph)) / (2 * np.pi) * 12)) % 12
        quals = [w[1] for w in win]
        med_qual = max(set(quals), key=quals.count)
        out.append({"bar": b, "root": med_root, "qual": med_qual})
    return out

# ---------------------------------------------------------------- main
def main():
    lead_notes = json.load(open(os.path.join(DATA, "lead_notes_clean.json")))
    bass_notes = json.load(open(os.path.join(DATA, "bass_notes_clean.json")))
    arp_notes = json.load(open(os.path.join(DATA, "arp_notes.json")))
    chords = json.load(open(os.path.join(DATA, "chords.json")))["bars"]

    # ---- smoothed pads (with scale-compatibility snap) ----
    sm = smooth_chords(chords, k=5)
    SCALE = {6, 8, 9, 11, 1, 2, 4}  # F# minor scale pitch classes
    QUAL_OK = {6: {"min", "sus"}, 8: {"min"}, 9: {"min", "maj"}, 11: {"min", "sus"},
               1: {"min"}, 2: {"maj", "sus"}, 4: {"maj", "sus"}}
    ns = 0
    for c in sm:
        if c["root"] not in SCALE:
            # nearest scale tone (circular)
            d = min((abs((s - c["root"]) % 12), abs((c["root"] - s) % 12)) for s in SCALE)
            cands = [s for s in SCALE if min(abs((s - c["root"]) % 12), abs((c["root"] - s) % 12)) == d[0]]
            c["root"] = cands[0]
            ns += 1
        if c["qual"] not in QUAL_OK[c["root"]]:
            c["qual"] = "min" if c["root"] in (6, 11) else "maj"
            ns += 1
    print(f"scale snap: {ns} chords adjusted")
    pad_notes = []
    for c in sm:
        tones = chord_tones(c["root"], c["qual"])
        for m in tones:
            pad_notes.append({"start_q": c["bar"] * 4 * 0.34830,
                              "end_q": (c["bar"] + 1) * 4 * 0.34830,
                              "midi": float(m)})
    print(f"pads: {len(pad_notes)} notes from {len(sm)} smoothed bars")
    from collections import Counter
    print("  smoothed chords:", Counter(f'{librosa.midi_to_note(c["root"]+60)[:-1]}{"" if c["qual"]=="maj" else c["qual"]}' for c in sm).most_common(6))

    # ---- render voices (mono) ----
    print("rendering voices…")
    lead = render_notes(lead_notes, "pulse", 1.0, N, vib_rate=12.0, vib_depth=4.0,
                        duty=0.25, duty_sweep=(0.125, 0.25, 0.06), sus=0.9, rel=0.05)
    bass = render_notes(bass_notes, "pulse", 1.0, N, duty=0.5, staccato=0.92,
                        sus=0.9, rel=0.02, detune_cents=-7.0)
    nyq = SR / 2
    bass = sosfiltfilt(butter(4, 800 / nyq, btype="low", output="sos"), bass)
    arp = render_notes(arp_notes, "pulse", 1.0, N, duty=0.125, staccato=0.75,
                       sus=0.9, rel=0.02)
    pad = render_notes(pad_notes, "pulse", 1.0, N, duty=0.25, staccato=1.0,
                       sus=0.65, rel=0.25, vib_rate=5.0, vib_depth=2.0)
    dr = np.zeros(N)
    for t in [1.38]:
        dr += kick_synth(t, N, gain=1.0)
    for t in [1.90, 2.45]:
        dr += noise_burst(t, 0.16, N, hp=400, decay=0.045, gain=0.5)

    # ---- balance: match original band RMS via NNLS (all voices alive) ----
    y_orig, _ = librosa.load(SRC, sr=SR, mono=True)
    targets = {"low": band_rms(y_orig, SR, 30, 200),
               "mid": band_rms(y_orig, SR, 200, 4000),
               "high": band_rms(y_orig, SR, 4000, 16000)}
    from scipy.optimize import nnls
    voices = {"lead": lead, "bass": bass, "arp": arp, "pad": pad, "drums": dr}
    for vn in voices:
        vx = voices[vn]
        r = np.sqrt(np.mean(vx ** 2)) + 1e-9
        voices[vn] = vx / r * 0.12
    V = np.zeros((3, 5))
    for j, (vn, vx) in enumerate(voices.items()):
        V[0, j] = band_rms(vx, SR, 30, 200)
        V[1, j] = band_rms(vx, SR, 200, 4000)
        V[2, j] = band_rms(vx, SR, 4000, 16000)
    g, _ = nnls(V, np.array([targets["low"], targets["mid"], targets["high"]]))
    # musical floor: melody must be audible
    g[0] = max(g[0], 0.35)
    g[3] = max(g[3], 0.12)
    g = g / g.sum() * (g.sum() * 1.0)
    print("gains:", {vn: round(float(gi), 3) for vn, gi in zip(voices, g)})
    mix = sum(gi * vx for gi, vx in zip(g, voices.values()))

    # ---- stereo production ----
    L = np.zeros(N); R = np.zeros(N)
    gL, gR, gB = g[0], g[0], g[1]
    gA, gP, gD = g[2], g[3], g[4]
    # lead: center dry + detuned chorus pair
    lead_det1 = render_notes(lead_notes, "pulse", 0.10 * gL, N, duty=0.25, vib_rate=12.0,
                             vib_depth=4.0, duty_sweep=(0.125, 0.25, 0.06), sus=0.9,
                             rel=0.05, detune_cents=5.0)
    lead_det2 = render_notes(lead_notes, "pulse", 0.10 * gL, N, duty=0.25, vib_rate=12.0,
                             vib_depth=4.0, duty_sweep=(0.125, 0.25, 0.06), sus=0.9,
                             rel=0.05, detune_cents=-5.0)
    l1, r1 = to_stereo(voices["lead"] * 0.85 * gL, 0.0)
    l2, r2 = to_stereo(lead_det1, -0.6)
    l3, r3 = to_stereo(lead_det2, 0.6)
    L += l1 + l2 + l3; R += r1 + r2 + r3
    # bass: center
    lb, rb = to_stereo(voices["bass"] * gB, 0.0)
    L += lb; R += rb
    # arp: ping-pong delay
    arp_d = np.zeros(N)
    fb = 0.32
    delay_n = int(EIGHTH * SR)
    src = voices["arp"] * gA
    arp_d = src.copy()
    for k in range(1, 5):
        sh = k * delay_n
        arp_d[sh:] += src[:-sh] * fb ** k
    arp_d = sosfiltfilt(butter(4, 6000 / nyq, btype="low", output="sos"), arp_d)
    la, ra = to_stereo(arp_d * 0.7, -0.45)
    la2, ra2 = to_stereo(src * 0.5, 0.45)
    L += la + la2; R += ra + ra2
    # pad: wide detuned pair
    padL = render_notes(pad_notes, "pulse", 0.5 * gP, N, duty=0.25, staccato=1.0,
                        sus=0.65, rel=0.25, detune_cents=6.0)
    padR = render_notes(pad_notes, "pulse", 0.5 * gP, N, duty=0.25, staccato=1.0,
                        sus=0.65, rel=0.25, detune_cents=-6.0)
    lp, rp = to_stereo(voices["pad"] * 0.5 * gP, -0.35)
    lp2, rp2 = to_stereo(padL, -0.8)
    lp3, rp3 = to_stereo(padR, 0.8)
    L += lp + lp2 + lp3; R += rp + rp2 + rp3
    # drums: center
    ld, rd = to_stereo(voices["drums"] * gD, 0.0)
    L += ld; R += rd
    # reverb sends (dry drums: send 0)
    wet = schroeder((voices["lead"] * 0.5 * gL + voices["pad"] * 0.5 * gP +
                     src * 0.3).astype(np.float64), SR, rt60=0.7, wet=0.28)
    L += wet[:, 0]; R += wet[:, 1]
    mix = np.stack([L, R], axis=-1)
    mono = (L + R) / 2

    # ---- dynamics matching (smooth) on the mono projection ----
    hop = SR // 2
    r_orig = librosa.feature.rms(y=y_orig, frame_length=2048, hop_length=hop)[0]
    r_mix = librosa.feature.rms(y=mono, frame_length=2048, hop_length=hop)[0]
    ln = min(len(r_orig), len(r_mix))
    r_os = uniform_filter1d(r_orig[:ln], 7)
    r_ms = uniform_filter1d(r_mix[:ln], 7)
    gblock = np.clip(r_os / (r_ms + 1e-9), 0.3, 3.0)
    t_block = librosa.times_like(r_orig[:ln], sr=SR, hop_length=hop)
    ginterp = np.interp(np.arange(N) / SR, t_block, gblock)
    mix *= ginterp[:, None]
    # master
    target_mean = float(np.sqrt(np.mean(r_orig ** 2)))
    mix *= target_mean / (np.sqrt(np.mean(mix ** 2)) + 1e-9)
    peak = np.max(np.abs(mix))
    if peak > 0.99:
        mix = np.tanh(mix / (peak + 1e-9) * 2.5) * 0.95
    else:
        mix = mix / peak * 0.95
    sf.write(os.path.join(AUD, "reconstruction_v2.wav"), mix, SR)
    subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", os.path.join(AUD, "reconstruction_v2.wav"),
                    "-codec:a", "libmp3lame", "-q:a", "2", os.path.join(AUD, "reconstruction_v2.mp3")])
    print("wrote audio/reconstruction_v2.wav/.mp3")

    # ---- metrics ----
    y_r, _ = librosa.load(os.path.join(AUD, "reconstruction_v2.wav"), sr=SR, mono=True)
    segs = json.load(open(os.path.join(DATA, "global.json")))["segment_times"]
    Mo = librosa.amplitude_to_db(librosa.feature.melspectrogram(y=y_orig, sr=SR, n_mels=64, hop_length=1024), ref=1.0)
    Mr = librosa.amplitude_to_db(librosa.feature.melspectrogram(y=y_r, sr=SR, n_mels=64, hop_length=1024), ref=1.0)
    co = librosa.feature.chroma_cens(y=y_orig, sr=SR, hop_length=1024)
    cr = librosa.feature.chroma_cens(y=y_r, sr=SR, hop_length=1024)
    cos_sim, chroma_corr = [], []
    for i in range(len(segs) - 1):
        a = int(segs[i] * SR / 1024); b = int(segs[i + 1] * SR / 1024)
        x, y2 = Mo[:, a:b].flatten(), Mr[:, a:b].flatten()
        cos_sim.append(float(np.dot(x, y2) / (np.linalg.norm(x) * np.linalg.norm(y2) + 1e-9)))
        chroma_corr.append(float(np.corrcoef(co[:, a:b].mean(axis=1), cr[:, a:b].mean(axis=1))[0, 1]))
    ro = librosa.feature.rms(y=y_orig, frame_length=2048, hop_length=1024)[0]
    rr = librosa.feature.rms(y=y_r, frame_length=2048, hop_length=1024)[0]
    ln2 = min(len(ro), len(rr))
    rms_corr = float(np.corrcoef(ro[:ln2], rr[:ln2])[0, 1])
    ro_s = librosa.feature.rms(y=y_orig, frame_length=4096, hop_length=SR // 2)[0]
    rr_s = librosa.feature.rms(y=y_r, frame_length=4096, hop_length=SR // 2)[0]
    ln3 = min(len(ro_s), len(rr_s))
    rms_sec = float(np.corrcoef(uniform_filter1d(ro_s, 7)[:ln3], uniform_filter1d(rr_s, 7)[:ln3])[0, 1])
    print("v2 metrics: mel %.3f | chroma %.3f | rms23ms %.3f | rms3.5s %.3f" % (
        np.mean(cos_sim), np.mean(chroma_corr), rms_corr, rms_sec))
    metrics = {"mel_cosine_mean": float(np.mean(cos_sim)), "mel_cosine_segments": cos_sim,
               "chroma_corr_mean": float(np.mean(chroma_corr)), "chroma_corr_segments": chroma_corr,
               "rms_corr": rms_corr, "rms_3s5": rms_sec,
               "gains": {vn: float(gi) for vn, gi in zip(voices, g)}}
    json.dump(metrics, open(os.path.join(DATA, "recon_metrics_v2.json"), "w"), indent=2)

    # ---- MIDI v2 export ----
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
            ev.append((st, "on", nt["midi"], 92))
            ev.append((en, "off", nt["midi"], 0))
        ev.sort(key=lambda e: (e[0], e[1] == "on"))
        last = 0
        for t, kind, note, vel in ev:
            msg = Message("note_on" if kind == "on" else "note_off",
                          note=int(round(note)), velocity=vel, channel=channel, time=t - last)
            tr.append(msg)
            last = t
        mid.tracks.append(tr)
    add_track("Lead", lead_notes, 0, 80)
    add_track("Bass", bass_notes, 1, 38)
    add_track("Arp", arp_notes, 2, 81)
    add_track("Pad", pad_notes, 3, 89)
    dr_tr = MidiTrack()
    dr_tr.append(MetaMessage("track_name", name="Drums", time=0))
    dr_tr.append(MetaMessage("set_tempo", tempo=tempo_us, time=0))
    ev = [(int(1.38 * 172.27 / 60 * tpb), 36), (int(1.90 * 172.27 / 60 * tpb), 38),
          (int(2.45 * 172.27 / 60 * tpb), 38)]
    last = 0
    for t, note in ev:
        dr_tr.append(Message("note_on", note=note, velocity=100, channel=9, time=t - last))
        dr_tr.append(Message("note_off", note=note, velocity=0, channel=9, time=60))
        last = t
    mid.tracks.append(dr_tr)
    mid.save(os.path.join(OUT, "Infinity_reconstruction_v2.mid"))
    print("wrote Infinity_reconstruction_v2.mid")

    # ---- FluidSynth reference render (project stack) ----
    sf2 = os.path.join(OUT, "..", "..", "soundfonts", "MuseScore_General.sf2")
    if os.path.exists(sf2):
        subprocess.run(["fluidsynth", "-F", os.path.join(AUD, "recon_sf.wav"), "-r", "44100",
                        "-R", "0.9", "-C", "0", "-g", "1.2", sf2,
                        os.path.join(OUT, "Infinity_reconstruction_v2.mid")],
                       capture_output=True)
        if os.path.exists(os.path.join(AUD, "recon_sf.wav")):
            subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", os.path.join(AUD, "recon_sf.wav"),
                            "-codec:a", "libmp3lame", "-q:a", "2", os.path.join(AUD, "reconstruction_sf.mp3")])
            y_sf, _ = librosa.load(os.path.join(AUD, "recon_sf.wav"), sr=SR, mono=True)
            Ms = librosa.amplitude_to_db(librosa.feature.melspectrogram(y=y_sf, sr=SR, n_mels=64, hop_length=1024), ref=1.0)
            cs = librosa.feature.chroma_cens(y=y_sf, sr=SR, hop_length=1024)
            cos_sf, chroma_sf = [], []
            for i in range(len(segs) - 1):
                a = int(segs[i] * SR / 1024); b = int(segs[i + 1] * SR / 1024)
                x, y2 = Mo[:, a:b].flatten(), Ms[:, a:b].flatten()
                cos_sf.append(float(np.dot(x, y2) / (np.linalg.norm(x) * np.linalg.norm(y2) + 1e-9)))
                chroma_sf.append(float(np.corrcoef(co[:, a:b].mean(axis=1), cs[:, a:b].mean(axis=1))[0, 1]))
            print("soundfont render: mel %.3f | chroma %.3f" % (np.mean(cos_sf), np.mean(chroma_sf)))
            metrics["sf_mel_cosine_mean"] = float(np.mean(cos_sf))
            metrics["sf_chroma_corr_mean"] = float(np.mean(chroma_sf))
            json.dump(metrics, open(os.path.join(DATA, "recon_metrics_v2.json"), "w"), indent=2)
    else:
        print("soundfont not found, skipping FluidSynth render")

if __name__ == "__main__":
    main()
