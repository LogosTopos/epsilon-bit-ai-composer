#!/bin/sh
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/../.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-/opt/anaconda3/bin/python}

"$PYTHON_BIN" -c 'import mido, audioop; print("Python:", __import__("sys").executable)' 
"$PYTHON_BIN" "$HERE/compose.py" --out-dir "$HERE"

for mid in "$HERE"/*.mid; do
    base=${mid%.mid}
    wav="$base.wav"
    mp3="$base.mp3"
    fluidsynth -F "$wav" -r 44100 -R 0.9 -C 0 -g 1.15 \
        "$ROOT/soundfonts/MuseScore_General.sf2" "$mid" >/dev/null 2>&1
    # Preserve section dynamics; disable limiter auto-gain so the -1 dB-ish headroom stays real.
    ffmpeg -y -loglevel error -i "$wav" \
        -af 'alimiter=limit=0.95:level=0' \
        -codec:a libmp3lame -q:a 2 \
        -metadata artist='ε-bit AI Composer' \
        -metadata album='Threshold of Ashes' \
        -metadata title="$(basename "$base")" "$mp3"
    "$PYTHON_BIN" "$HERE/verify.py" --mid "$mid" --wav "$wav"
done

echo "Build complete: $HERE"
