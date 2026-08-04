"""
Offline audio renderer: converts structured note timelines to WAV/MP3.

Input format (from LLM):
{
  "bpm": 140,
  "tracks": [
    {"instrument": "pulse_50", "pan": 0.0, "notes": [{"n": "C4", "b": 0.0, "d": 0.5, "v": 0.8}]}
  ]
}

V2 additions:
  - 2-op FM synthesis (fm, fm_bass, fm_bell, fm_brass, fm_lead, fm_string)
  - Stereo output with per-track pan (-1.0 L .. 0.0 C .. +1.0 R)
  - Per-note FM parameters (fm_index, fm_ratio)
"""

from __future__ import annotations

import math
import os
import subprocess
import tempfile

import numpy as np
import soundfile as sf

from .audio.constants import (
    FM_PRESETS, MIDI_FREQS, SAMPLE_RATE, WAVE_TYPES,
)

_NOTE_MAP = {
    "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3,
    "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8,
    "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11,
}

_FM_WAVE_TYPES = {"fm", "fm_bass", "fm_bell", "fm_brass", "fm_lead", "fm_string"}

_ATTACK_SAMPLES = int(SAMPLE_RATE * 0.005)
_RELEASE_SAMPLES = int(SAMPLE_RATE * 0.05)


def parse_note(name: str) -> int:
    """Parse 'C4' -> 60, 'D#3' -> 51, etc."""
    name = name.strip().upper()
    try:
        return int(name)
    except ValueError:
        pass
    if len(name) >= 2:
        note_part = name[:-1]
        octave_part = name[-1]
        if note_part in _NOTE_MAP and octave_part.isdigit():
            return _NOTE_MAP[note_part] + (int(octave_part) + 1) * 12
    raise ValueError(f"Cannot parse note: {name}")


# ─── Vectorized waveform generators ──────────────────────────

def _gen_pulse(phase_norm: np.ndarray, duty: float) -> np.ndarray:
    return np.where(phase_norm < duty, 1.0, -1.0).astype(np.float32)


def _gen_triangle(phase_norm: np.ndarray) -> np.ndarray:
    p = phase_norm.astype(np.float32)
    out = np.empty_like(p)
    mask1 = p < 0.25
    out[mask1] = 4.0 * p[mask1]
    mask2 = (p >= 0.25) & (p < 0.75)
    out[mask2] = 2.0 - 4.0 * p[mask2]
    mask3 = p >= 0.75
    out[mask3] = 4.0 * p[mask3] - 4.0
    return out


def _gen_sawtooth(phase_norm: np.ndarray) -> np.ndarray:
    return (2.0 * phase_norm - 1.0).astype(np.float32)


def _gen_sine(phase_norm: np.ndarray) -> np.ndarray:
    return np.sin(2.0 * np.pi * phase_norm).astype(np.float32)


def _gen_wavetable(phase_norm: np.ndarray) -> np.ndarray:
    return (_gen_triangle(phase_norm) * 0.7 +
            _gen_pulse(phase_norm, 0.25) * 0.3)


def _gen_fm(phase_norm: np.ndarray, mod_ratio: float = 1.0,
            mod_index: float = 3.0, feedback: float = 0.0) -> np.ndarray:
    """2-op FM synthesis.

    output(t) = sin(2π·phase + I·sin(2π·phase·ratio + fb·prev_output))

    Args:
        phase_norm: Carrier phase in [0, 1)
        mod_ratio: Modulator frequency ratio (Fm/Fc)
        mod_index: Modulation index (brightness/complexity)
        feedback: Feedback amount (0-1), modulator output fed back into itself
    """
    n = len(phase_norm)
    # Modulator phase
    mod_phase = phase_norm * mod_ratio
    # Modulator signal
    modulator = np.sin(2.0 * np.pi * mod_phase)
    # Apply feedback (simple 1-sample delay)
    if feedback > 0.001:
        fb_buf = np.zeros(n, dtype=np.float32)
        fb_buf[0] = 0.0
        for i in range(1, n):
            fb_buf[i] = modulator[i] + feedback * fb_buf[i - 1]
        modulator = fb_buf
    # Carrier = sin(2π·phase + mod_index · modulator)
    return np.sin(2.0 * np.pi * phase_norm + mod_index * modulator).astype(np.float32)


def _gen_noise_lfsr(n_samples: int, seed: int, tap1: int, tap2: int) -> np.ndarray:
    reg = np.uint16(seed)
    out = np.empty(n_samples, dtype=np.float32)
    for i in range(n_samples):
        bit = ((int(reg) & 1) ^ ((int(reg) >> tap1) & 1)) & 1
        reg = (reg >> 1) | (np.uint16(bit) << 14)
        out[i] = float(int(reg) & 1) * 2.0 - 1.0
    return out


# ─── Envelope generator ──────────────────────────────────────

def _make_ar_envelope(n_samples: int, velocity: float, volume: float) -> np.ndarray:
    env = np.ones(n_samples, dtype=np.float32) * velocity * volume
    att_len = min(_ATTACK_SAMPLES, n_samples)
    if att_len > 1:
        env[:att_len] *= np.linspace(0.0, 1.0, att_len, dtype=np.float32)
    rel_len = min(_RELEASE_SAMPLES, n_samples)
    if rel_len > 1:
        env[-rel_len:] *= np.linspace(1.0, 0.0, rel_len, dtype=np.float32)
    return env


def _apply_arp(base_midi: int, intervals: list[int],
                n_samples: int, sr: int) -> np.ndarray:
    """Return per-sample MIDI offset array for arpeggio macro.

    Cycles through `intervals` (semitone offsets) at ENV_TICK_HZ.
    """
    from ebit.audio.envelope import ENV_TICK_HZ
    samples_per_tick = int(round(sr / ENV_TICK_HZ))
    out = np.empty(n_samples, dtype=np.float32)
    n_int = len(intervals)
    pos, tick = 0, 0
    while pos < n_samples:
        end = min(pos + samples_per_tick, n_samples)
        out[pos:end] = float(intervals[tick % n_int])
        pos = end
        tick += 1
    return out


# ─── Effect macro helpers ────────────────────────────────────

def _apply_slide(freqs: np.ndarray, base_midi: int, target_note: str,
                 n_s: int) -> np.ndarray:
    """Linear pitch slide from base to target note in cents space."""
    target_midi = parse_note(target_note)
    delta_semitones = float(target_midi - base_midi)
    t = np.arange(n_s, dtype=np.float32)
    cents_offset = delta_semitones * 100.0 * t / float(n_s)
    freq_mult = np.power(2.0, cents_offset / 1200.0).astype(np.float32)
    return freqs * freq_mult


def _apply_vib(freqs: np.ndarray, rate_hz: float, depth_cents: float,
               n_s: int, sr: int) -> np.ndarray:
    """Sine LFO vibrato (frequency modulation) in cents."""
    t = np.arange(n_s, dtype=np.float32) / float(sr)
    cents_mod = depth_cents * np.sin(2.0 * np.pi * rate_hz * t)
    freq_mult = np.power(2.0, cents_mod / 1200.0).astype(np.float32)
    return freqs * freq_mult


def _apply_tremolo(env: np.ndarray, rate_hz: float, depth_amp: float,
                   n_s: int, sr: int) -> np.ndarray:
    """Sine LFO tremolo (amplitude modulation). Output in [1-depth, 1]."""
    t = np.arange(n_s, dtype=np.float32) / float(sr)
    lfo = 1.0 - depth_amp * 0.5 * (1.0 - np.sin(2.0 * np.pi * rate_hz * t))
    return env * lfo.astype(np.float32)


def _apply_retrigger(wave: np.ndarray, n_segments: int, n_s: int,
                     vel: float, volume: float, sr: int,
                     tremolo_rate: float | None = None,
                     tremolo_depth: float | None = None) -> np.ndarray:
    """Split note into N segments, each with fresh AR envelope."""
    result = np.zeros(n_s, dtype=np.float32)
    seg_len = n_s // n_segments
    for i in range(n_segments):
        s0 = i * seg_len
        s1 = s0 + seg_len if i < n_segments - 1 else n_s
        seg_n = s1 - s0
        seg_env = _make_ar_envelope(seg_n, vel, volume)
        if tremolo_rate is not None and tremolo_depth is not None:
            seg_env = _apply_tremolo(seg_env, tremolo_rate, tremolo_depth, seg_n, sr)
        result[s0:s1] = wave[s0:s1] * seg_env
    return result


# ─── Waveform dispatch ───────────────────────────────────────

def _gen_waveform(wave_type: str, phase_norm: np.ndarray,
                  fm_index: float = 3.0, fm_ratio: float = 1.0) -> np.ndarray:
    """Generate periodic waveform samples."""
    if wave_type in ("pulse_12", "pulse_125"):
        return _gen_pulse(phase_norm, 0.125)
    elif wave_type == "pulse_25":
        return _gen_pulse(phase_norm, 0.25)
    elif wave_type == "pulse_50":
        return _gen_pulse(phase_norm, 0.5)
    elif wave_type == "pulse_75":
        return _gen_pulse(phase_norm, 0.75)
    elif wave_type == "triangle":
        return _gen_triangle(phase_norm)
    elif wave_type == "sawtooth":
        return _gen_sawtooth(phase_norm)
    elif wave_type == "sine":
        return _gen_sine(phase_norm)
    elif wave_type == "wavetable":
        return _gen_wavetable(phase_norm)
    elif wave_type in _FM_WAVE_TYPES or wave_type == "fm":
        # Look up FM preset, or use defaults
        preset = FM_PRESETS.get(wave_type, (fm_ratio, fm_index, 0.0))
        return _gen_fm(phase_norm, mod_ratio=preset[0],
                       mod_index=fm_index if wave_type == "fm" else preset[1],
                       feedback=preset[2])
    else:
        return _gen_pulse(phase_norm, 0.5)


# ─── Pan law ─────────────────────────────────────────────────

def _pan_gains(pan: float) -> tuple[float, float]:
    """Constant-power pan law. pan in [-1, 1] → (left_gain, right_gain)."""
    pan = max(-1.0, min(1.0, pan))
    angle = (pan + 1.0) * math.pi / 4.0  # map [-1,1] → [0, π/2]
    return math.cos(angle), math.sin(angle)


# ─── Renderer ────────────────────────────────────────────────

class Renderer:
    """Offline audio renderer with vectorized sample generation.

    Supports mono (legacy) and stereo output with per-track panning.
    """

    _noise_cache: dict[str, np.ndarray] = {}
    _NOISE_CACHE_SECS = 30

    def __init__(self):
        self._noise_offset: dict[str, int] = {
            "noise_short": 0, "noise_long": 0, "noise_periodic": 0,
        }

    @classmethod
    def _get_noise_buffer(cls, noise_type: str) -> np.ndarray:
        if noise_type not in cls._noise_cache:
            n_samples = int(SAMPLE_RATE * cls._NOISE_CACHE_SECS)
            if noise_type == "noise_short":
                buf = _gen_noise_lfsr(n_samples, 0x7FFF, 1, 1)
            elif noise_type == "noise_long":
                buf = _gen_noise_lfsr(n_samples, 0x7FFF, 6, 6)
            elif noise_type == "noise_periodic":
                buf = _gen_noise_lfsr(n_samples, 0x7FFF, 6, 1)
            else:
                buf = np.zeros(n_samples, dtype=np.float32)
            cls._noise_cache[noise_type] = buf
        return cls._noise_cache[noise_type]

    def _slice_noise(self, noise_type: str, n: int) -> np.ndarray:
        buf = self._get_noise_buffer(noise_type)
        offset = self._noise_offset.get(noise_type, 0)
        if offset + n > len(buf):
            first = buf[offset:]
            second = buf[:n - len(first)]
            result = np.concatenate([first, second])
            self._noise_offset[noise_type] = n - len(first)
        else:
            result = buf[offset:offset + n].copy()
            self._noise_offset[noise_type] = offset + n
        return result

    # ── Mono rendering (backward-compatible) ──────────────────

    def render_multi(self, composition: dict, volume: float = 0.6
                     ) -> dict[str, np.ndarray]:
        """Render all tracks to mono. Returns {instrument_name: np.ndarray}."""
        return self._render_tracks(composition, volume=volume, stereo=False)

    def render(self, composition: dict, volume: float = 0.6) -> np.ndarray:
        """Render to a single mixed mono buffer (backward-compatible)."""
        per_track = self.render_multi(composition, volume=volume)
        if not per_track:
            return np.zeros(int(SAMPLE_RATE * 1), dtype=np.float32)
        max_len = max(len(a) for a in per_track.values())
        audio = np.zeros(max_len, dtype=np.float64)
        for arr in per_track.values():
            audio[:len(arr)] += arr.astype(np.float64)
        peak = float(np.max(np.abs(audio)))
        if peak > 0.99:
            audio = audio / peak * 0.95
        return audio.astype(np.float32)

    # ── Stereo rendering (new) ────────────────────────────────

    def render_multi_stereo(self, composition: dict, volume: float = 0.6
                            ) -> dict[str, np.ndarray]:
        """Render all tracks to stereo with per-track panning.

        Returns {instrument_name: np.ndarray of shape (samples, 2)}.
        """
        return self._render_tracks(composition, volume=volume, stereo=True)

    def render_stereo(self, composition: dict, volume: float = 0.6) -> np.ndarray:
        """Render to a single stereo mix (samples, 2)."""
        per_track = self.render_multi_stereo(composition, volume=volume)
        if not per_track:
            return np.zeros((int(SAMPLE_RATE * 1), 2), dtype=np.float32)
        max_len = max(a.shape[0] for a in per_track.values())
        audio = np.zeros((max_len, 2), dtype=np.float64)
        for arr in per_track.values():
            n = arr.shape[0]
            audio[:n] += arr.astype(np.float64)
        peak = float(np.max(np.abs(audio)))
        if peak > 0.99:
            audio = audio / peak * 0.95
        return audio.astype(np.float32)

    # ── Internal render logic ─────────────────────────────────

    def _render_tracks(self, composition: dict, volume: float = 0.6,
                       stereo: bool = False) -> dict[str, np.ndarray]:
        """Shared render logic for mono and stereo output."""
        bpm = composition.get("bpm", 120)
        tracks = composition.get("tracks", [])

        if not tracks:
            key = "silence"
            if stereo:
                return {key: np.zeros((int(SAMPLE_RATE * 1), 2), dtype=np.float32)}
            return {key: np.zeros(int(SAMPLE_RATE * 1), dtype=np.float32)}

        beat_dur = 60.0 / bpm

        max_end = 0.0
        for track in tracks:
            for note in track.get("notes", []):
                end_beat = note.get("b", 0.0) + note.get("d", 0.25)
                if end_beat > max_end:
                    max_end = end_beat
        total_beats = max_end + 0.25
        total_samples = int(total_beats * beat_dur * SAMPLE_RATE)

        result: dict[str, np.ndarray] = {}

        for track_idx, track in enumerate(tracks):
            instrument = track.get("instrument", "pulse_50")
            if instrument not in WAVE_TYPES:
                instrument = "pulse_50"

            is_noise = instrument in ("noise_short", "noise_long", "noise_periodic")
            is_fm = instrument in _FM_WAVE_TYPES or instrument == "fm"
            track_pan = track.get("pan", 0.0)

            if stereo:
                buf = np.zeros((total_samples, 2), dtype=np.float32)
            else:
                buf = np.zeros(total_samples, dtype=np.float32)

            notes = track.get("notes", [])

            for note in notes:
                try:
                    pitch = parse_note(note["n"])
                except (KeyError, ValueError):
                    continue

                freq = MIDI_FREQS.get(pitch, 440.0)
                start_beat = note.get("b", 0.0)
                dur_beat = note.get("d", 0.25)
                vel = note.get("v", 0.8)
                fm_idx = note.get("fm_index", 3.0)
                fm_rat = note.get("fm_ratio", 1.0)
                note_pan = note.get("pan", track_pan)
                note_fx = note.get("fx", None)
                note_vol_env = note.get("volume_envelope", None)

                start_s = int(start_beat * beat_dur * SAMPLE_RATE)
                n_s = max(1, int(dur_beat * beat_dur * SAMPLE_RATE))
                end_s = min(start_s + n_s, total_samples)
                n_s = end_s - start_s
                if n_s <= 0:
                    continue

                # ── Pitch trajectory ──
                arp_intervals = None
                arp_active = False
                if note_fx and "arp" in note_fx:
                    arp_intervals = note_fx["arp"]

                if is_noise:
                    freqs = None
                    phase_norm = None
                else:
                    if arp_intervals and len(arp_intervals) > 0:
                        arp_active = True
                        arp_offsets = _apply_arp(pitch, arp_intervals, n_s, SAMPLE_RATE)
                        unique_off = np.unique(arp_offsets)
                        freqs = np.zeros(n_s, dtype=np.float32)
                        for off in unique_off:
                            mask = arp_offsets == off
                            midi_note = pitch + int(off)
                            freqs[mask] = MIDI_FREQS.get(midi_note, 440.0)
                    else:
                        freqs = np.full(n_s, freq, dtype=np.float32)

                    # slide_to: linear pitch ramp (silently skip if arp active or noise)
                    if note_fx and "slide_to" in note_fx and not arp_active:
                        freqs = _apply_slide(freqs, pitch, note_fx["slide_to"], n_s)

                    # vib: sine LFO on frequency (silently skip for noise)
                    if note_fx and "vib" in note_fx:
                        rate_hz, depth_cents = note_fx["vib"]
                        if rate_hz <= 0 or depth_cents < 0:
                            raise ValueError(
                                f"vib rate must be > 0 and depth >= 0, got {note_fx['vib']}")
                        freqs = _apply_vib(freqs, rate_hz, depth_cents, n_s, SAMPLE_RATE)

                    # phase from frequency trajectory
                    phase = np.zeros(n_s, dtype=np.float32)
                    phase[1:] = np.cumsum(freqs[:-1] / SAMPLE_RATE)
                    phase_norm = phase % 1.0

                # ── Waveform generation ──
                if is_noise:
                    wave = self._slice_noise(instrument, n_s)
                elif is_fm:
                    preset = FM_PRESETS.get(instrument, (fm_rat, fm_idx, 0.0))
                    wave = _gen_fm(phase_norm,
                                   mod_ratio=fm_rat if instrument == "fm" else preset[0],
                                   mod_index=fm_idx if instrument == "fm" else preset[1],
                                   feedback=preset[2])
                else:
                    wave = _gen_waveform(instrument, phase_norm)

                # ── Envelope ──
                if note_vol_env is not None and len(note_vol_env) > 0:
                    from ebit.audio.envelope import expand_volume_envelope
                    env = expand_volume_envelope(note_vol_env, n_s, sr=SAMPLE_RATE)
                    env = env.astype(np.float32) * vel * volume
                else:
                    env = _make_ar_envelope(n_s, vel, volume)

                # tremolo: amplitude LFO (works on all wave types including noise)
                tremolo_rate = None
                tremolo_depth = None
                if note_fx and "tremolo" in note_fx:
                    tremolo_rate, tremolo_depth = note_fx["tremolo"]
                    if tremolo_rate <= 0:
                        raise ValueError(
                            f"tremolo rate must be > 0, got {tremolo_rate}")
                    if not (0.0 <= tremolo_depth <= 0.6):
                        raise ValueError(
                            f"tremolo depth must be in [0, 0.6], got {tremolo_depth}")
                    env = _apply_tremolo(env, tremolo_rate, tremolo_depth, n_s, SAMPLE_RATE)

                # ── Mix into buffer ──
                if note_fx and "retrigger" in note_fx:
                    n_seg = int(note_fx["retrigger"])
                    if n_seg < 1:
                        raise ValueError(
                            f"retrigger must be positive integer, got {n_seg}")
                    note_audio = _apply_retrigger(
                        wave, n_seg, n_s, vel, volume, SAMPLE_RATE,
                        tremolo_rate, tremolo_depth)
                else:
                    note_audio = wave * env

                if stereo:
                    lg, rg = _pan_gains(note_pan)
                    buf[start_s:end_s, 0] += note_audio * lg
                    buf[start_s:end_s, 1] += note_audio * rg
                else:
                    buf[start_s:end_s] += note_audio

            key = instrument
            if key in result:
                key = f"{instrument}#{track_idx}"
            result[key] = buf

        return result

    # ── I/O ───────────────────────────────────────────────────

    def save_wav(self, audio: np.ndarray, path: str) -> str:
        sf.write(path, audio, SAMPLE_RATE)
        return path

    def save_mp3(self, audio: np.ndarray, path: str, bitrate: str = "192k") -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        try:
            self.save_wav(audio, wav_path)
            subprocess.run(
                ["ffmpeg", "-y", "-i", wav_path, "-b:a", bitrate, path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
            )
        finally:
            os.unlink(wav_path)
        return path
