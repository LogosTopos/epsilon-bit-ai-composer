#!/usr/bin/env python3
"""Stage 7 — Reconstruction of DDRKirby(ISQ) - Infinity.

Chip-style re-synthesis of the transcribed voices:
  lead  : pulse (duty sweep 25%->50%, 12 Hz vibrato, 5 ms attack)
  bass  : square 50%, -7 cents, 8th-note staccato
  arp   : triangle, 16th grid, quiet sparkle
  pad   : detuned pulse25 chord tones from per-bar chords
  drums : intro kick + snare (only real hits found)

Comparison: segment-wise mel cosine, chroma corr, RMS corr, band ratios.
Outputs: audio/reconstruction.wav, audio/reconstruction.mp3, data/recon_metrics.json,
          plots/05_recon_compare.png, Infinity_reconstruction.mid
"""
import json
import os
import subprocess
import numpy as np
import librosa
import soundfile as sf

OUT = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(OUT, "audio")
DATA = os.path.join(OUT, "data")
PLT = os.path.join(OUT, "plots")
SR = 44100
DUR = 258.4
N = int(DUR * SR)
EIGHTH = 0.17415
SIXTEENTH = EIGHTH / 2

SRC = "/Users/topologyw/Music/网易云音乐/DDRKirby(ISQ) - Infinity.mp3"



def noise_burst(t0, dur_s, n, sr=SR, hp=0.0, lp=None, decay=0.1, gain=1.0, rng=None):
    rng = rng or np.random.default_rng(42)
    i0, i1 = int(t0 * sr), min(int((t0 + dur_s) * sr), n)
    if i1 <= i0:
        return np.zeros(n)
    x = rng.standard_normal(i1 - i0)
    from scipy.signal import butter, sosfilt, sosfiltfilt
    sos = None
    nyq = sr / 2
    if lp and hp:
        sos = butter(4, [hp / nyq, min(lp / nyq, 0.98)], btype="band", output="sos")
    elif hp:
        sos = butter(4, hp / nyq, btype="high", output="sos")
    elif lp:
        sos = butter(4, lp / nyq, btype="low", output="sos")
    if sos is not None:
        x = sosfilt(sos, x)
    env = np.exp(-np.arange(len(x)) / (decay * sr))
    out = np.zeros(n)
    out[i0:i1] = gain * x * env
    return out

def kick_synth(t0, n, sr=SR, f0=150.0, f1=45.0, dur=0.12, gain=1.0):
    i0 = int(t0 * sr)
    ln = min(int(dur * sr), n - i0)
    if ln <= 0:
        return np.zeros(n)
    tt = np.arange(ln) / sr
    f = f1 + (f0 - f1) * np.exp(-tt / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / sr
    x = np.sin(ph) * np.exp(-tt / 0.05)
    # click
    click = np.random.default_rng(7).standard_normal(int(0.004 * sr)) * np.exp(-np.arange(int(0.004 * sr)) / (0.001 * sr))
    out = np.zeros(n)
    out[i0:i0 + ln] = gain * x
    out[i0:i0 + len(click)] += 0.15 * gain * click
    return out

def adsr_envelope(t0, dur_s, n, sr=SR, att=0.005, rel=0.03, sus=1.0):
    """Exp attack, sustain, release envelope for a note."""
    i0 = int(t0 * sr)
    i1 = min(int((t0 + dur_s) * sr), n)
    if i1 <= i0:
        return None
    L = i1 - i0
    e = np.ones(L)
    a = int(att * sr)
    if a > 0 and a < L:
        e[:a] = np.linspace(0, 1, a)
    r = int(rel * sr)
    if r > 0 and r < L:
        e[-r:] *= np.linspace(1, 0, r)
    e *= sus
    return i0, e

# ------------------------------------------------------------------ synth engine
def pulse_bank(freqs, duties, n, sr=SR, vib_rate=0.0, vib_depth_c=0.0, vib_start=0.1,
               duty_sweep=None):
    """Render pulse tone(s) into an n-sample buffer starting at t=0.
    freqs: list of (t0, f0, f1); t0 is local time (0-based). Returns (n,) signal."""
    t = np.arange(n) / sr
    out = np.zeros(n)
    for (t0, f0, f1) in freqs:
        i0 = max(int(t0 * sr), 0)
        if i0 >= n:
            continue
        tt = t[i0:]
        phase = 2 * np.pi * f0 * tt
        if vib_rate > 0:
            ramp = np.clip((tt - t0) / vib_start, 0, 1)
            d = vib_depth_c / 1200
            # exact FM: phase = 2pi*f0*t - d*(f0/rate)*cos(2pi*rate*t)
            phase = phase - d * (f0 / vib_rate) * np.cos(2 * np.pi * vib_rate * tt) * ramp
        ph = np.mod(phase / (2 * np.pi), 1.0)
        if duty_sweep is not None:
            d0, d1, tau = duty_sweep
            duty = d1 + (d0 - d1) * np.exp(-(tt - t0) / tau)
        else:
            duty = duties
        out[i0:] += np.where(ph < duty, 1.0, -1.0)
    return out

def triangle_bank(freqs, n, sr=SR):
    """Render triangle tone(s) into an n-sample buffer starting at t=0."""
    t = np.arange(n) / sr
    out = np.zeros(n)
    for (t0, f) in freqs:
        i0 = max(int(t0 * sr), 0)
        if i0 >= n:
            continue
        tt = t[i0:]
        ph = np.mod(f * tt, 1.0)
        out[i0:] += 2 * np.abs(2 * ph - 1) - 1
    return out

def render_notes(notes, waveform, gain, n, sr=SR, vib_rate=0.0, vib_depth=0.0,
                 duty=0.25, duty_sweep=None, staccato=0.9, sus=0.8, rel=0.03,
                 detune_cents=0.0):
    out = np.zeros(n)
    for nt in notes:
        f = librosa.midi_to_hz(nt["midi"]) * 2 ** (detune_cents / 1200)
        t0 = nt["start_q"] if "start_q" in nt else nt["start"]
        d = (nt["end_q"] if "end_q" in nt else nt["end"]) - t0
        d = max(d, 0.05) * staccato
        env = adsr_envelope(t0, d, n, sr=sr, rel=rel, sus=sus)
        if env is None:
            continue
        i0, e = env
        L = len(e)
        if waveform == "pulse":
            seg = pulse_bank([(0.0, f, f)], duty, L, sr=sr, vib_rate=vib_rate,
                             vib_depth_c=vib_depth, duty_sweep=duty_sweep)
        elif waveform == "triangle":
            seg = triangle_bank([(0.0, f)], L, sr=sr)
        else:
            raise ValueError(waveform)
        out[i0:i0 + L] += gain * seg * e
    return out

# ------------------------------------------------------------------ mixing helpers
def band_rms(x, sr, lo, hi):
    from scipy.signal import butter, sosfiltfilt
    nyq = sr / 2
    f = sosfiltfilt(butter(6, [lo / nyq, min(hi / nyq, 0.98)], btype="band", output="sos"), x)
    return float(np.sqrt(np.mean(f ** 2)))

def main():
    bass_notes = json.load(open(os.path.join(DATA, "bass_notes.json")))
    lead_notes = json.load(open(os.path.join(DATA, "lead_notes.json")))
    arp_notes = json.load(open(os.path.join(DATA, "arp_notes.json")))
    chords = json.load(open(os.path.join(DATA, "chords.json")))["runs"]

    # ---------- pad chords -> sustained tones ----------
    NOTE_OFF = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6,
                "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    def chord_tones(name):
        name = name.replace("♯", "#").replace("♭", "b")
        root_s = name
        for suf in ("sus", "m", "7", "maj7"):
            if root_s.endswith(suf):
                root_s = root_s[:-len(suf)]
        root = NOTE_OFF[root_s]
        if name.endswith("m"):
            return [(root + 60), (root + 63), (root + 67)]
        if name.endswith("sus"):
            return [(root + 60), (root + 65), (root + 67)]
        return [(root + 60), (root + 64), (root + 67)]
    pad_notes = []
    for r in chords:
        tones = chord_tones(r["chord"])
        for m in tones:
            pad_notes.append({"start": r["t"], "end": r["t_end"], "midi": float(m),
                              "start_q": r["t"], "end_q": r["t_end"]})

    # ---------- intro drums ----------
    drums = {"kick": [1.38], "snare": [1.90, 2.45]}

    # ---------- render voices ----------
    print("rendering lead…")
    lead = render_notes(lead_notes, "pulse", 0.5, N, vib_rate=12.0, vib_depth=3.0,
                        duty=0.25, duty_sweep=(0.125, 0.25, 0.08), sus=0.85, rel=0.04)
    print("rendering bass…")
    bass = render_notes(bass_notes, "pulse", 0.7, N, duty=0.5, staccato=0.92,
                        sus=0.9, rel=0.02, detune_cents=-7.0)
    from scipy.signal import butter as _butter, sosfiltfilt as _sosfiltfilt
    _nyq = SR / 2
    bass = _sosfiltfilt(_butter(4, 800 / _nyq, btype="low", output="sos"), bass)
    print("rendering arp…")
    arp = render_notes(arp_notes, "pulse", 0.35, N, duty=0.125, staccato=0.75,
                       sus=0.9, rel=0.02)
    print("rendering pad…")
    pad = render_notes(pad_notes, "pulse", 0.22, N, duty=0.25, staccato=1.0,
                       sus=0.7, rel=0.15, vib_rate=5.0, vib_depth=2.0)
    print("rendering drums…")
    dr = np.zeros(N)
    for t in drums["kick"]:
        dr += kick_synth(t, N, gain=0.8)
    for t in drums["snare"]:
        dr += noise_burst(t, 0.16, N, hp=400, decay=0.045, gain=0.4)
    dr += noise_burst(2.45, 0.10, N, hp=1500, decay=0.03, gain=0.25)

    # ---------- band calibration: cascaded gain fit ----------
    y_orig, _ = librosa.load(SRC, sr=SR, mono=True)
    targets = {"low": band_rms(y_orig, SR, 30, 200),
               "mid": band_rms(y_orig, SR, 200, 4000),
               "high": band_rms(y_orig, SR, 4000, 16000)}
    print("original band RMS:", {k: round(v, 4) for k, v in targets.items()})
    voices = {"lead": lead, "bass": bass, "arp": arp, "pad": pad, "drums": dr}
    for vn in voices:
        vx = voices[vn]
        r = np.sqrt(np.mean(vx ** 2)) + 1e-9
        voices[vn] = vx / r * 0.12
    V = {vn: np.array([band_rms(vx, SR, 30, 200), band_rms(vx, SR, 200, 4000),
                       band_rms(vx, SR, 4000, 16000)]) for vn, vx in voices.items()}
    # 1) bass matches low band; 2) arp matches high band; 3) lead+pad share mid
    #    (minus bass/arp bleed); 4) drums fixed accent level
    g = {}
    g["bass"] = targets["low"] / (V["bass"][0] + 1e-9)
    g["arp"] = targets["high"] / (V["arp"][2] + 1e-9)
    mid_left = targets["mid"] - g["bass"] * V["bass"][1] - g["arp"] * V["arp"][1]
    lead_pad = max(mid_left, 0.6 * targets["mid"]) / (0.8 * V["lead"][1] + 0.2 * V["pad"][1] + 1e-9)
    g["lead"] = 0.8 * lead_pad
    g["pad"] = 0.2 * lead_pad
    g["drums"] = 0.5
    g = {k: max(v, 0.0) for k, v in g.items()}
    print("gains:", {k: round(float(v), 3) for k, v in g.items()})
    mix = sum(g[vn] * vx for vn, vx in voices.items())
    got = {"low": band_rms(mix, SR, 30, 200), "mid": band_rms(mix, SR, 200, 4000),
           "high": band_rms(mix, SR, 4000, 16000)}
    print("recon band RMS:   ", {k: round(v, 4) for k, v in got.items()})
    # dynamics matching: match SMOOTH envelopes (section dynamics), interpolate gain
    hop = SR // 2  # 0.5s
    r_orig = librosa.feature.rms(y=y_orig, frame_length=2048, hop_length=hop)[0]
    r_mix = librosa.feature.rms(y=mix, frame_length=2048, hop_length=hop)[0]
    ln = min(len(r_orig), len(r_mix))
    from scipy.ndimage import uniform_filter1d as _uf
    r_orig_s = _uf(r_orig[:ln], 7)
    r_mix_s = _uf(r_mix[:ln], 7)
    gain_block = np.clip(r_orig_s / (r_mix_s + 1e-9), 0.3, 3.0)
    # linear interpolation of block gains to sample domain
    t_block = librosa.times_like(r_orig[:ln], sr=SR, hop_length=hop)
    t_sample = np.arange(N) / SR
    gain_interp = np.interp(t_sample, t_block, gain_block)
    mix *= gain_interp
    print(f"dynamics matched (smooth gain {gain_block.min():.2f}-{gain_block.max():.2f})")
    # master: scale to original mean RMS, soft-clip only where needed
    target_mean = float(np.sqrt(np.mean(r_orig ** 2)))
    mix *= target_mean / (np.sqrt(np.mean(mix ** 2)) + 1e-9)
    peak = np.max(np.abs(mix))
    if peak > 0.99:
        mix = np.tanh(mix / (peak + 1e-9) * 2.5) * 0.95
    else:
        mix = mix / peak * 0.95
    sf.write(os.path.join(AUD, "reconstruction.wav"), mix, SR)
    subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", os.path.join(AUD, "reconstruction.wav"),
                    "-codec:a", "libmp3lame", "-q:a", "2", os.path.join(AUD, "reconstruction.mp3")])
    print("wrote audio/reconstruction.wav/.mp3")

    # ---------- comparison ----------
    print("comparison…")
    y_r, _ = librosa.load(os.path.join(AUD, "reconstruction.wav"), sr=SR, mono=True)
    segs = json.load(open(os.path.join(DATA, "global.json")))["segment_times"]
    mel_kw = dict(n_mels=64, hop_length=1024)
    Mo = librosa.feature.melspectrogram(y=y_orig, sr=SR, **mel_kw)
    Mr = librosa.feature.melspectrogram(y=y_r, sr=SR, **mel_kw)
    Mo_db = librosa.amplitude_to_db(Mo, ref=1.0)
    Mr_db = librosa.amplitude_to_db(Mr, ref=1.0)
    cos_sim = []
    for i in range(len(segs) - 1):
        a = int(segs[i] * SR / 1024); b = int(segs[i + 1] * SR / 1024)
        x, y2 = Mo_db[:, a:b].flatten(), Mr_db[:, a:b].flatten()
        cos_sim.append(float(np.dot(x, y2) / (np.linalg.norm(x) * np.linalg.norm(y2) + 1e-9)))
    print("segment mel cosine:", [round(c, 3) for c in cos_sim], "mean", round(float(np.mean(cos_sim)), 3))
    # chroma correlation
    co = librosa.feature.chroma_cens(y=y_orig, sr=SR, hop_length=1024)
    cr = librosa.feature.chroma_cens(y=y_r, sr=SR, hop_length=1024)
    chroma_corr = []
    for i in range(len(segs) - 1):
        a = int(segs[i] * SR / 1024); b = int(segs[i + 1] * SR / 1024)
        x, y2 = co[:, a:b].mean(axis=1), cr[:, a:b].mean(axis=1)
        chroma_corr.append(float(np.corrcoef(x, y2)[0, 1]))
    print("segment chroma corr:", [round(c, 3) for c in chroma_corr])
    # RMS curve (fine and smooth scales)
    ro = librosa.feature.rms(y=y_orig, frame_length=2048, hop_length=1024)[0]
    rr = librosa.feature.rms(y=y_r, frame_length=2048, hop_length=1024)[0]
    ln = min(len(ro), len(rr))
    rms_corr = float(np.corrcoef(ro[:ln], rr[:ln])[0, 1])
    ro_s = librosa.feature.rms(y=y_orig, frame_length=4096, hop_length=SR // 2)[0]
    rr_s = librosa.feature.rms(y=y_r, frame_length=4096, hop_length=SR // 2)[0]
    ln_s = min(len(ro_s), len(rr_s))
    rms_corr_smooth = float(np.corrcoef(ro_s[:ln_s], rr_s[:ln_s])[0, 1])
    from scipy.ndimage import uniform_filter1d as _uf2
    rms_corr_sec = float(np.corrcoef(_uf2(ro_s, 7)[:ln_s], _uf2(rr_s, 7)[:ln_s])[0, 1])
    print("RMS curve corr (23ms):", round(rms_corr, 3), " (0.5s):", round(rms_corr_smooth, 3),
          " (3.5s):", round(rms_corr_sec, 3))
    metrics = {"mel_cosine_segments": cos_sim, "mel_cosine_mean": float(np.mean(cos_sim)),
               "chroma_corr_segments": chroma_corr, "rms_corr": rms_corr,
               "rms_corr_smooth": rms_corr_smooth, "rms_corr_3s5": rms_corr_sec,
               "band_rms_recon": got, "band_rms_original": targets}
    json.dump(metrics, open(os.path.join(DATA, "recon_metrics.json"), "w"), indent=2)

    # ---------- plot ----------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(3, 2, figsize=(15, 10))
    for ax, sig, title in [(axs[0, 0], y_orig, "ORIGINAL"), (axs[0, 1], y_r, "RECONSTRUCTION")]:
        S = librosa.amplitude_to_db(np.abs(librosa.stft(sig, n_fft=2048, hop_length=512)), ref=1.0)
        ax.imshow(S, aspect="auto", origin="lower", extent=[0, DUR, 0, 16], cmap="magma",
                  vmin=-80, vmax=0)
        ax.set_ylim(0, 16); ax.set_title(title); ax.set_ylabel("kHz")
    axs[1, 0].bar(range(len(cos_sim)), cos_sim); axs[1, 0].set_title("mel cosine per segment")
    axs[1, 0].set_ylim(0, 1)
    axs[1, 1].bar(range(len(chroma_corr)), chroma_corr); axs[1, 1].set_title("chroma corr per segment")
    axs[1, 1].set_ylim(0, 1)
    axs[2, 0].plot(ro, label="orig", alpha=0.7); axs[2, 0].plot(rr, label="recon", alpha=0.7)
    axs[2, 0].legend(); axs[2, 0].set_title(f"RMS curve (corr {rms_corr:.3f})")
    axs[2, 1].axis("off")
    axs[2, 1].text(0.05, 0.9, f"mel mean {np.mean(cos_sim):.3f}\nchroma mean {np.mean(chroma_corr):.3f}\n"
                   f"rms {rms_corr:.3f}", fontsize=14, va="top")
    plt.tight_layout()
    plt.savefig(os.path.join(PLT, "05_recon_compare.png"), dpi=110)
    print("saved plots/05_recon_compare.png + data/recon_metrics.json")

    # ---------- MIDI export ----------
    try:
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
            events = []
            for nt in notes:
                st = int(round(nt["start_q"] * 172.27 / 60 * tpb))
                en = int(round(nt["end_q"] * 172.27 / 60 * tpb))
                if en <= st:
                    en = st + 60
                vel = 90
                events.append((st, "on", nt["midi"], vel))
                events.append((en, "off", nt["midi"], 0))
            events.sort(key=lambda e: (e[0], e[1] == "on"))
            last = 0
            for t, kind, note, vel in events:
                if kind == "on":
                    tr.append(Message("note_on", note=int(round(note)), velocity=vel,
                                      channel=channel, time=t - last))
                else:
                    tr.append(Message("note_off", note=int(round(note)), velocity=0,
                                      channel=channel, time=t - last))
                last = t
            mid.tracks.append(tr)
        add_track("Lead", lead_notes, 0, 80)
        add_track("Bass", bass_notes, 1, 38)
        add_track("Arp", arp_notes, 2, 81)
        add_track("Pad", pad_notes, 3, 89)
        dr_tr = MidiTrack()
        dr_tr.append(MetaMessage("track_name", name="Drums", time=0))
        dr_tr.append(MetaMessage("set_tempo", tempo=tempo_us, time=0))
        ev = []
        for t in drums["kick"]:
            ev.append((int(t * 172.27 / 60 * tpb), 36))
        for t in drums["snare"]:
            ev.append((int(t * 172.27 / 60 * tpb), 38))
        ev.sort()
        last = 0
        for t, note in ev:
            dr_tr.append(Message("note_on", note=note, velocity=100, channel=9, time=t - last))
            dr_tr.append(Message("note_off", note=note, velocity=0, channel=9, time=60))
            last = t
        mid.tracks.append(dr_tr)
        mid.save(os.path.join(OUT, "Infinity_reconstruction.mid"))
        print("wrote Infinity_reconstruction.mid")
    except Exception as e:
        print("MIDI export failed:", e)

if __name__ == "__main__":
    main()
