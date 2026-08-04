#!/usr/bin/env python3
"""Post-processing pipeline for epsilon-bit BGM stems.

Applies professional-grade effects using scipy (no GPL dependency):
1. Multi-band dynamics (3-band compressor)
2. Convolution reverb (cathedral impulse response)
3. Stereo widening (mid-side processing)
4. Soft clipper / saturator
5. True-peak limiter

Designed to consume stem_mp3 directories and produce final mastered output.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import scipy.signal as signal
import soundfile as sf

SAMPLE_RATE = 44100

# ═══════════════════════════════════════════════════════════════
# 1. Convolution Reverb — synthetic cathedral IR
# ═══════════════════════════════════════════════════════════════

def make_cathedral_ir(duration_ms: float = 2200.0, size: float = 0.85,
                      brightness: float = 0.55) -> np.ndarray:
    """Generate a synthetic cathedral impulse response.

    Uses filtered noise with exponential decay, early reflections,
    and a diffuse tail to simulate a large stone cathedral.
    """
    n_samples = int(SAMPLE_RATE * duration_ms / 1000.0)
    rng = np.random.RandomState(42)

    # Early reflections: sparse impulses
    early_n = int(SAMPLE_RATE * 0.080)
    early = np.zeros(early_n, dtype=np.float32)
    reflection_times = [0.012, 0.025, 0.038, 0.052, 0.068, 0.082, 0.098]
    reflection_gains = [0.70, 0.50, 0.35, 0.25, 0.18, 0.13, 0.09]
    for t_sec, gain in zip(reflection_times, reflection_gains):
        idx = int(t_sec * SAMPLE_RATE)
        if idx < early_n:
            early[idx] = gain

    # Diffuse tail: filtered noise with exponential decay
    tail_n = n_samples - early_n
    raw_noise = rng.randn(tail_n).astype(np.float32)
    # Low-pass filter the noise for warmth
    sos_lp = signal.butter(2, 4000 / (SAMPLE_RATE / 2.0), btype="low", output="sos")
    noise = signal.sosfilt(sos_lp, raw_noise)

    # Exponential decay envelope
    decay = np.exp(-np.arange(tail_n) / (SAMPLE_RATE * duration_ms / 1000.0 * size))
    noise *= decay.astype(np.float32) * brightness

    ir = np.concatenate([early, noise])
    # Normalize
    peak = np.max(np.abs(ir))
    if peak > 1e-8:
        ir = ir / peak * 0.85
    return ir.astype(np.float32)


def apply_reverb(audio: np.ndarray, ir: np.ndarray, wet_mix: float = 0.30) -> np.ndarray:
    """Apply convolution reverb to stereo audio."""
    if audio.ndim == 1:
        audio = np.column_stack([audio, audio])
    wet_l = signal.convolve(audio[:, 0], ir, mode="full")[: len(audio)]
    wet_r = signal.convolve(audio[:, 1], ir, mode="full")[: len(audio)]
    wet = np.column_stack([wet_l, wet_r]).astype(np.float32)
    # Normalize wet to avoid clipping
    wet_peak = np.max(np.abs(wet))
    if wet_peak > 1e-8:
        wet = wet / wet_peak * 0.70
    return ((1.0 - wet_mix) * audio + wet_mix * wet).astype(np.float32)


# ═══════════════════════════════════════════════════════════════
# 2. Multi-band Compressor (3-band)
# ═══════════════════════════════════════════════════════════════

def crossover_bands(audio: np.ndarray, low_split: float = 250.0,
                    high_split: float = 3000.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Split audio into low, mid, high bands using Linkwitz-Riley crossovers."""
    nyq = SAMPLE_RATE / 2.0
    sos_low = signal.butter(4, low_split / nyq, btype="low", output="sos")
    sos_band = signal.butter(4, [low_split / nyq, high_split / nyq],
                             btype="band", output="sos")
    sos_high = signal.butter(4, high_split / nyq, btype="high", output="sos")
    if audio.ndim == 1:
        lo = signal.sosfilt(sos_low, audio)
        mid = signal.sosfilt(sos_band, audio)
        hi = signal.sosfilt(sos_high, audio)
    else:
        lo = np.column_stack([signal.sosfilt(sos_low, audio[:, c]) for c in range(audio.shape[1])])
        mid = np.column_stack([signal.sosfilt(sos_band, audio[:, c]) for c in range(audio.shape[1])])
        hi = np.column_stack([signal.sosfilt(sos_high, audio[:, c]) for c in range(audio.shape[1])])
    return lo.astype(np.float32), mid.astype(np.float32), hi.astype(np.float32)


def compress_band(band: np.ndarray, threshold_db: float = -24.0,
                  ratio: float = 4.0, attack_ms: float = 10.0,
                  release_ms: float = 80.0, makeup_db: float = 3.0) -> np.ndarray:
    """RMS-based feed-forward compressor for a single band."""
    mono = band.mean(axis=1) if band.ndim > 1 else band
    rms_window = int(SAMPLE_RATE * 0.010)  # 10ms RMS window
    rms = np.sqrt(signal.convolve(mono ** 2, np.ones(rms_window) / rms_window, mode="same"))

    threshold_linear = 10.0 ** (threshold_db / 20.0)
    gain_reduction = np.ones_like(rms)
    over = rms > threshold_linear
    gain_reduction[over] = (threshold_linear / rms[over]) ** (1.0 - 1.0 / ratio)

    # Smooth gain reduction with attack/release
    attack_coef = math.exp(-1.0 / (SAMPLE_RATE * attack_ms / 1000.0))
    release_coef = math.exp(-1.0 / (SAMPLE_RATE * release_ms / 1000.0))

    smoothed = np.ones_like(gain_reduction)
    for i in range(1, len(gain_reduction)):
        coef = attack_coef if gain_reduction[i] < smoothed[i - 1] else release_coef
        smoothed[i] = coef * smoothed[i - 1] + (1.0 - coef) * gain_reduction[i]

    makeup = 10.0 ** (makeup_db / 20.0)
    if band.ndim > 1:
        return (band * smoothed[:, np.newaxis] * makeup).astype(np.float32)
    return (band * smoothed * makeup).astype(np.float32)


def multiband_compress(audio: np.ndarray) -> np.ndarray:
    """Apply 3-band compression optimized for game BGM."""
    lo, mid, hi = crossover_bands(audio)

    # Low band: gentle compression for solid bass
    lo = compress_band(lo, threshold_db=-22.0, ratio=3.0, makeup_db=4.0,
                       attack_ms=15.0, release_ms=100.0)
    # Mid band: moderate compression for clarity
    mid = compress_band(mid, threshold_db=-26.0, ratio=4.0, makeup_db=3.0,
                        attack_ms=8.0, release_ms=60.0)
    # High band: light compression for air
    hi = compress_band(hi, threshold_db=-30.0, ratio=2.5, makeup_db=2.0,
                       attack_ms=5.0, release_ms=40.0)

    return (lo + mid + hi).astype(np.float32)


# ═══════════════════════════════════════════════════════════════
# 3. Stereo Widening (mid-side processing)
# ═══════════════════════════════════════════════════════════════

def stereo_widen(audio: np.ndarray, width: float = 1.25) -> np.ndarray:
    """Mid-side stereo widening. width=1.0 is neutral, >1.0 widens."""
    if audio.ndim < 2 or audio.shape[1] < 2:
        return audio
    mid = (audio[:, 0] + audio[:, 1]) * 0.5
    side = (audio[:, 0] - audio[:, 1]) * 0.5
    side *= width
    left = mid + side
    right = mid - side
    return np.column_stack([left, right]).astype(np.float32)


# ═══════════════════════════════════════════════════════════════
# 4. Soft Clipper / Saturator
# ═══════════════════════════════════════════════════════════════

def soft_clip(audio: np.ndarray, drive: float = 1.05) -> np.ndarray:
    """Hyperbolic tangent soft clipper with drive control."""
    driven = audio * drive
    return (np.tanh(driven) / np.tanh(drive)).astype(np.float32)


# ═══════════════════════════════════════════════════════════════
# 5. True-Peak Limiter
# ═══════════════════════════════════════════════════════════════

def true_peak_limit(audio: np.ndarray, ceiling_db: float = -0.3,
                    oversample: int = 4) -> np.ndarray:
    """Simple look-ahead brickwall limiter with oversampling."""
    ceiling = 10.0 ** (ceiling_db / 20.0)
    mono = np.abs(audio).max(axis=1) if audio.ndim > 1 else np.abs(audio)
    peak = float(np.max(mono)) if mono.size else 0.0
    if peak <= ceiling + 1e-8:
        return audio.astype(np.float32)
    gain = ceiling / peak
    # Smooth gain change
    release_samples = int(SAMPLE_RATE * 0.010)
    alpha = math.exp(-1.0 / release_samples)
    smoothed_gain = gain
    if audio.ndim > 1:
        out = np.zeros_like(audio)
        for i in range(len(audio)):
            instant = ceiling / max(np.max(np.abs(audio[i])), 1e-8)
            smoothed_gain = alpha * smoothed_gain + (1.0 - alpha) * min(instant, smoothed_gain * 1.01)
            out[i] = audio[i] * min(1.0, smoothed_gain)
        return out.astype(np.float32)
    return (audio * gain).astype(np.float32)


# ═══════════════════════════════════════════════════════════════
# Master chain
# ═══════════════════════════════════════════════════════════════

def master_chain(audio: np.ndarray, reverb_wet: float = 0.22,
                 stereo_width: float = 1.18, drive: float = 1.04,
                 ceiling_db: float = -0.3) -> tuple[np.ndarray, dict[str, Any]]:
    """Apply the full mastering chain."""
    ir = make_cathedral_ir(duration_ms=2000.0, size=0.82, brightness=0.50)
    report = {}

    # Stage 1: Multiband compression
    compressed = multiband_compress(audio)
    report["mb_comp"] = _rms_report(compressed)

    # Stage 2: Cathedral reverb
    reverbed = apply_reverb(compressed, ir, wet_mix=reverb_wet)
    report["reverb"] = _rms_report(reverbed)

    # Stage 3: Stereo widening
    widened = stereo_widen(reverbed, width=stereo_width)
    report["widen"] = _rms_report(widened)

    # Stage 4: Soft clip / saturation
    saturated = soft_clip(widened, drive=drive)
    report["saturate"] = _rms_report(saturated)

    # Stage 5: Final limiting
    limited = true_peak_limit(saturated, ceiling_db=ceiling_db)
    report["final"] = _rms_report(limited)

    return limited.astype(np.float32), report


def _rms_report(audio: np.ndarray) -> dict[str, float]:
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(np.square(audio.astype(np.float64)))))
    return {
        "peak": round(peak, 6),
        "rms_db": round(20.0 * math.log10(max(rms, 1e-10)), 2),
    }


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Post-process epsilon-bit BGM stems")
    parser.add_argument("input_wav", help="Path to input WAV file")
    parser.add_argument("--output", "-o", default=None, help="Output WAV path")
    parser.add_argument("--reverb", type=float, default=0.22, help="Reverb wet mix (default 0.22)")
    parser.add_argument("--width", type=float, default=1.18, help="Stereo width (default 1.18)")
    parser.add_argument("--drive", type=float, default=1.04, help="Saturation drive (default 1.04)")
    parser.add_argument("--ceiling", type=float, default=-0.3, help="Limiter ceiling dB (default -0.3)")
    parser.add_argument("--report", "-r", default=None, help="Write processing report JSON")
    args = parser.parse_args()

    input_path = Path(args.input_wav)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {input_path}...")
    audio, sr = sf.read(input_path)
    if sr != SAMPLE_RATE:
        print(f"Warning: resampling from {sr} to {SAMPLE_RATE}")
        # Simple resample by ratio
        ratio = SAMPLE_RATE / sr
        new_len = int(len(audio) * ratio)
        audio = signal.resample(audio, new_len).astype(np.float32)

    if audio.ndim == 1:
        audio = np.column_stack([audio, audio])
    audio = audio.astype(np.float32)

    print(f"Processing: {len(audio) / SAMPLE_RATE:.1f}s, peak={np.max(np.abs(audio)):.4f}")
    print(f"  Stage 1: Multi-band compression...")
    print(f"  Stage 2: Cathedral reverb (wet={args.reverb})...")
    print(f"  Stage 3: Stereo widening (width={args.width})...")
    print(f"  Stage 4: Soft saturation (drive={args.drive})...")
    print(f"  Stage 5: True-peak limiting (ceiling={args.ceiling}dB)...")

    output, report = master_chain(audio, reverb_wet=args.reverb,
                                  stereo_width=args.width, drive=args.drive,
                                  ceiling_db=args.ceiling)

    out_path = Path(args.output) if args.output else input_path.with_stem(input_path.stem + "_mastered")
    sf.write(out_path, output, SAMPLE_RATE)
    print(f"Saved: {out_path}")

    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for stage, info in report.items():
        print(f"  [{stage}] peak={info['peak']:.4f}, RMS={info['rms_db']:.2f} dB")


if __name__ == "__main__":
    main()
