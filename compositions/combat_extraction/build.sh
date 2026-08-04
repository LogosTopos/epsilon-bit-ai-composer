#!/usr/bin/env bash
# build.sh — 《搜打撤》母节 v9 构建(缓存制度化)
# 纪律:运行 Python 前永远清 __pycache__ 与 stems/stem_*(防污染导致的莫名 bug)
set -e
cd "$(dirname "$0")"

echo "=== 清缓存 ==="
rm -rf __pycache__ lib/__pycache__ layers/__pycache__
rm -f stems/stem_*

echo "=== 生成双版本(trumpet / synth)==="
python3 compose.py --voice trumpet --out Combat_Extraction_v9_trumpet.mid
python3 compose.py --voice synth --out Combat_Extraction_v9_synth.mid

echo "=== 审计 ==="
python3 audit_v7.py --mid Combat_Extraction_v9_trumpet.mid --voice trumpet
python3 audit_v7.py --mid Combat_Extraction_v9_synth.mid --voice synth

echo "=== 渲染 + 混音(trumpet)==="
rm -f stems/stem_*
python3 mix_stems.py --mid Combat_Extraction_v9_trumpet.mid --render-stems --out stems/_mix_v9_trumpet.wav

echo "=== 渲染 + 混音(synth)==="
rm -f stems/stem_*
python3 mix_stems.py --mid Combat_Extraction_v9_synth.mid --render-stems --out stems/_mix_v9_synth.wav

echo "=== 完成 ==="
