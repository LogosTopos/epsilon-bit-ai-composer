"""
8-bit audio constants: note frequencies, keyboard mappings, wave tables, effects.

Covers: NES (2A03), Game Boy (DMG), C64 (SID) era sound sources.
"""

SAMPLE_RATE = 44100
BUFFER_SIZE = 256
CHANNELS = 1  # legacy mono; stereo outputs use CHANNELS_STEREO
CHANNELS_STEREO = 2
MAX_POLYPHONY = 8

# ─── FM synthesis presets ───────────────────────────────────

# FM algorithm presets (2-op): (mod_freq_ratio, mod_index, feedback)
FM_PRESETS: dict[str, tuple[float, float, float]] = {
    # name → (modulator_ratio, modulation_index, feedback)
    "fm_bass":       (0.5, 4.0, 0.5),    # deep, rumbling bass
    "fm_bright_bass":(0.5, 6.0, 0.7),    # brighter, more aggressive bass
    "fm_bell":       (3.0, 2.0, 0.0),    # bell-like, metallic
    "fm_brass":      (1.0, 3.0, 0.3),    # brassy, rich harmonics
    "fm_epiano":     (1.0, 1.5, 0.0),    # electric piano-ish
    "fm_string":     (2.0, 1.0, 0.2),    # string-like pad
    "fm_lead":       (1.0, 5.0, 0.4),    # aggressive lead
    "fm_perc":       (4.0, 8.0, 0.0),    # percussive, atonal
}

# ─── Wave types ────────────────────────────────────────────

# NES pulse channels (2A03 APU) — 4 duty cycles
WAVE_PULSE_125 = "pulse_12"   # duty 12.5% — thin, reedy, NES lead
WAVE_PULSE_25  = "pulse_25"   # duty 25% — hollow, woodwind-like
WAVE_PULSE_50  = "pulse_50"   # duty 50% — classic square wave
WAVE_PULSE_75  = "pulse_75"   # duty 75% — inverted 25%, nasal

# NES triangle channel — pure, soft, bass
WAVE_TRIANGLE = "triangle"

# C64-style sawtooth
WAVE_SAWTOOTH = "sawtooth"

# NES noise channel
WAVE_NOISE_SHORT = "noise_short"  # mode 0: 32767-bit LFSR — harsh, snare
WAVE_NOISE_LONG  = "noise_long"   # mode 1: 93-bit LFSR — rumbly, kick

# C64-style periodic/tuned noise — metallic, ringing
WAVE_NOISE_PERIODIC = "noise_periodic"

# Pure sine (clean tone, useful for layering and bell-like sounds)
WAVE_SINE = "sine"

# Game Boy-style 4-bit wavetable (user-definable 32-sample waveform)
WAVE_WAVETABLE = "wavetable"

# FM synthesis (2-op frequency modulation)
WAVE_FM = "fm"

# FM variants with specific presets
WAVE_FM_BASS = "fm_bass"
WAVE_FM_BELL = "fm_bell"
WAVE_FM_BRASS = "fm_brass"
WAVE_FM_LEAD = "fm_lead"
WAVE_FM_PAD = "fm_string"

WAVE_TYPES = [
    WAVE_PULSE_125, WAVE_PULSE_25, WAVE_PULSE_50, WAVE_PULSE_75,
    WAVE_TRIANGLE, WAVE_SAWTOOTH,
    WAVE_NOISE_SHORT, WAVE_NOISE_LONG, WAVE_NOISE_PERIODIC,
    WAVE_SINE, WAVE_WAVETABLE,
    WAVE_FM, WAVE_FM_BASS, WAVE_FM_BELL, WAVE_FM_BRASS, WAVE_FM_LEAD, WAVE_FM_PAD,
]

# Wave type → display name
WAVE_LABELS: dict[str, str] = {
    WAVE_PULSE_125:  "PULSE 12%",
    WAVE_PULSE_25:   "PULSE 25%",
    WAVE_PULSE_50:   "PULSE 50%",
    WAVE_PULSE_75:   "PULSE 75%",
    WAVE_TRIANGLE:   "TRIANGLE",
    WAVE_SAWTOOTH:   "SAW",
    WAVE_NOISE_SHORT:    "NOISE-S",
    WAVE_NOISE_LONG:     "NOISE-L",
    WAVE_NOISE_PERIODIC: "NOISE-P",
    WAVE_SINE:       "SINE",
    WAVE_WAVETABLE:  "WAVE",
    WAVE_FM:         "FM",
    WAVE_FM_BASS:    "FM-BASS",
    WAVE_FM_BELL:    "FM-BELL",
    WAVE_FM_BRASS:   "FM-BRASS",
    WAVE_FM_LEAD:    "FM-LEAD",
    WAVE_FM_PAD:     "FM-PAD",
}

# ─── Arpeggio presets ──────────────────────────────────────

ARPEGGIO_OFF = "off"
ARPEGGIO_MAJOR = "maj"       # root + major 3rd + perfect 5th
ARPEGGIO_MINOR = "min"       # root + minor 3rd + perfect 5th
ARPEGGIO_SUS4 = "sus4"       # root + perfect 4th + perfect 5th
ARPEGGIO_DIM = "dim"         # root + minor 3rd + tritone
ARPEGGIO_AUG = "aug"         # root + major 3rd + minor 6th
ARPEGGIO_OCTAVE = "oct"      # root + octave
ARPEGGIO_MAJ7 = "maj7"       # root + maj3 + 5th + maj7th
ARPEGGIO_MIN7 = "min7"       # root + min3 + 5th + min7th

ARPEGGIO_INTERVALS: dict[str, list[int]] = {
    ARPEGGIO_MAJOR:  [0, 4, 7],
    ARPEGGIO_MINOR:  [0, 3, 7],
    ARPEGGIO_SUS4:   [0, 5, 7],
    ARPEGGIO_DIM:    [0, 3, 6],
    ARPEGGIO_AUG:    [0, 4, 8],
    ARPEGGIO_OCTAVE: [0, 12],
    ARPEGGIO_MAJ7:   [0, 4, 7, 11],
    ARPEGGIO_MIN7:   [0, 3, 7, 10],
}

ARPEGGIO_TYPES = list(ARPEGGIO_INTERVALS.keys())

# ─── Default wavetable (NES-style "chip lead" 4-bit) ──────
# 32 samples, values 0–15 (4-bit), rendered as -1.0 .. 1.0
DEFAULT_WAVETABLE: list[float] = [
    0.0, 0.2, 0.5, 0.8, 1.0, 0.8, 0.5, 0.2,
    0.0, -0.2, -0.5, -0.8, -1.0, -0.8, -0.5, -0.2,
    0.2, 0.5, 0.7, 0.9, 0.7, 0.3, 0.0, -0.3,
    -0.6, -0.9, -0.7, -0.4, 0.0, 0.4, 0.6, 0.5,
]

# ─── Note frequencies ─────────────────────────────────────

NOTE_NAMES = [
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"
]


def midi_to_freq(midi_note: int) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


MIDI_FREQS = {n: midi_to_freq(n) for n in range(128)}

# ─── Keyboard mapping ─────────────────────────────────────
# Piano-style layout (2 rows, one octave + 4 notes)
#
#   Black:  W  E        T  Y  U        O  P
#   White: A  S  D  F  G  H  J  K  L  ;  '
#   Note:  C4 D4 E4 F4 G4 A4 B4 C5 D5 E5 F5

KEYMAP: dict[str, int] = {
    # Bottom row — white keys (natural notes)
    "a": 60,   # C4
    "s": 62,   # D4
    "d": 64,   # E4
    "f": 65,   # F4
    "g": 67,   # G4
    "h": 69,   # A4
    "j": 71,   # B4
    "k": 72,   # C5
    "l": 74,   # D5
    ";": 76,   # E5
    "'": 77,   # F5
    # Top row — black keys (accidentals)
    "w": 61,   # C#4
    "e": 63,   # D#4
    "t": 66,   # F#4
    "y": 68,   # G#4
    "u": 70,   # A#4
    "o": 73,   # C#5
    "p": 75,   # D#5
}

NOTE_TO_KEY: dict[int, str] = {v: k for k, v in KEYMAP.items()}

NOTE_DISPLAY: dict[int, str] = {
    n: f"{NOTE_NAMES[n % 12]}{n // 12 - 1}"
    for n in range(128)
}

# Piano order: the physical sequence of keys left-to-right
# Used by the UI to build the keyboard in correct order.
PIANO_ORDER = [
    {"type": "white", "key": "a"},
    {"type": "black", "key": "w"},
    {"type": "white", "key": "s"},
    {"type": "black", "key": "e"},
    {"type": "white", "key": "d"},
    {"type": "white", "key": "f"},
    {"type": "black", "key": "t"},
    {"type": "white", "key": "g"},
    {"type": "black", "key": "y"},
    {"type": "white", "key": "h"},
    {"type": "black", "key": "u"},
    {"type": "white", "key": "j"},
    {"type": "white", "key": "k"},
    {"type": "black", "key": "o"},
    {"type": "white", "key": "l"},
    {"type": "black", "key": "p"},
    {"type": "white", "key": ";"},
    {"type": "white", "key": "'"},
]
