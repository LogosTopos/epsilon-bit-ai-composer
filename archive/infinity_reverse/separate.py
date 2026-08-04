#!/usr/bin/env python3
"""Stage 2 — Source separation for DDRKirby(ISQ) - Infinity.

Pipeline: HPSS (harmonic/percussive) -> band splits -> stems.
Stems (local, gitignored):
  audio/stem_harmonic.wav   (pitched content)
  audio/stem_percussive.wav (drums/transients)
  audio/stem_bass.wav       (harmonic, 30-250 Hz)
  audio/stem_mid.wav        (harmonic, 250-4000 Hz: lead+pad)
  audio/stem_high.wav       (harmonic, >4 kHz: sparkle/arps)
Diagnostics: zoomed spectrograms of original vs stems.
"""
import os
import numpy as np
import librosa
import soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = "/Users/topologyw/Music/网易云音乐/DDRKirby(ISQ) - Infinity.mp3"
OUT = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(OUT, "audio")
PLT = os.path.join(OUT, "plots")
os.makedirs(AUD, exist_ok=True)
os.makedirs(PLT, exist_ok=True)

def bandpass(x, sr, lo, hi, order=8):
    from scipy.signal import butter, sosfiltfilt
    nyq = sr / 2
    wn = [max(lo, 20) / nyq, min(hi / nyq, 0.98)]
    print(f"  bandpass {lo}-{hi}: wn={wn}")
    sos = butter(order, wn, btype="band", output="sos")
    return sosfiltfilt(sos, x)

def main():
    y, sr = librosa.load(SRC, sr=44100, mono=True)
    print(f"loaded {len(y)/sr:.1f}s")

    # ---- HPSS: percussive soft-mask, harmonic = complement (lossless) ----
    D = librosa.stft(y, n_fft=2048, hop_length=512)
    Dm = np.abs(D)
    _, Dp = librosa.decompose.hpss(D, margin=1.5)
    Pmask = np.abs(Dp) / (Dm + 1e-12)
    perc = librosa.istft(D * Pmask, hop_length=512)
    harm = librosa.istft(D * (1 - Pmask), hop_length=512)
    print(f"energy split: harmonic {np.sum(harm**2)/np.sum(y**2)*100:.1f}%  percussive {np.sum(perc**2)/np.sum(y**2)*100:.1f}%")

    bass = bandpass(harm, sr, 30, 250)
    mid = bandpass(harm, sr, 250, 4000)
    high = bandpass(harm, sr, 4000, 16000)

    for name, x in [("stem_harmonic", harm), ("stem_percussive", perc),
                    ("stem_bass", bass), ("stem_mid", mid), ("stem_high", high)]:
        x = x / (np.max(np.abs(x)) + 1e-9) * 0.95
        sf.write(os.path.join(AUD, f"{name}.wav"), x, sr)
        print(f"wrote {name}.wav")

    # ---- diagnostics: zoomed spectrograms 0-16s ----
    fig, axs = plt.subplots(4, 1, figsize=(15, 12), sharex=True)
    t0, t1 = 0.0, 16.0
    n0, n1 = int(t0 * sr), int(t1 * sr)
    S_full = librosa.amplitude_to_db(np.abs(librosa.stft(y[n0:n1], n_fft=2048, hop_length=512)), ref=1.0)
    S_h = librosa.amplitude_to_db(np.abs(librosa.stft(harm[n0:n1], n_fft=2048, hop_length=512)), ref=1.0)
    S_p = librosa.amplitude_to_db(np.abs(librosa.stft(perc[n0:n1], n_fft=2048, hop_length=512)), ref=1.0)
    S_b = librosa.amplitude_to_db(np.abs(librosa.stft(bass[n0:n1], n_fft=2048, hop_length=512)), ref=1.0)
    for ax, S, title in [(axs[0], S_full, "ORIGINAL"), (axs[1], S_h, "HARMONIC (HPSS)"),
                         (axs[2], S_p, "PERCUSSIVE (HPSS)"), (axs[3], S_b, "BASS BAND (30-250Hz)")]:
        im = ax.imshow(S, aspect="auto", origin="lower", extent=[t0, t1, 0, sr / 2 / 1000],
                       cmap="magma", vmin=-80, vmax=0)
        ax.set_ylim(0, 16)
        ax.set_ylabel("kHz")
        ax.set_title(title)
        plt.colorbar(im, ax=ax, fraction=0.02)
    axs[3].set_xlabel("time (s)")
    plt.tight_layout()
    plt.savefig(os.path.join(PLT, "02_separation_0-16s.png"), dpi=110)
    print("diagnostics saved.")

if __name__ == "__main__":
    main()
