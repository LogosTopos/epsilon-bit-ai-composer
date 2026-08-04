#!/usr/bin/env bash
# build.sh — 《搜打撤》母节 v9 构建 + 压码(链路审计 P0 落地,2026-08)
# 纪律:运行 Python 前永远清 __pycache__(防污染导致的莫名 bug);
# stems 缓存不再 rm——mix_stems.py 增量缓存(mid+音色库内容哈希)自动失效,
# 改层/换库后自动只重渲染过期项;确需全量时手动 rm -f stems/stem_*。
set -e
cd "$(dirname "$0")"

echo "=== 清缓存(py) ==="
rm -rf __pycache__ lib/__pycache__ layers/__pycache__ sections/__pycache__

echo "=== 生成双版本(trumpet / synth)==="
python3 compose.py --voice trumpet --out Combat_Extraction_v9_trumpet.mid
python3 compose.py --voice synth --out Combat_Extraction_v9_synth.mid

echo "=== 审计 ==="
python3 audit_v7.py --mid Combat_Extraction_v9_trumpet.mid --voice trumpet
python3 audit_v7.py --mid Combat_Extraction_v9_synth.mid --voice synth

echo "=== 渲染 + 混音(trumpet,并行+增量)==="
python3 mix_stems.py --mid Combat_Extraction_v9_trumpet.mid --render-stems --out stems/_mix_v9_trumpet.wav

echo "=== 渲染 + 混音(synth,增量:仅 stab 组重渲染)==="
python3 mix_stems.py --mid Combat_Extraction_v9_synth.mid --render-stems --out stems/_mix_v9_synth.wav

echo "=== 压码(TP 限幅,encode_mp3.py)==="
python3 encode_mp3.py stems/_mix_v9_trumpet.wav Combat_Extraction_v9_trumpet.mp3 --title "Combat Extraction v9 (trumpet)"
python3 encode_mp3.py stems/_mix_v9_synth.wav Combat_Extraction_v9_synth.mp3 --title "Combat Extraction v9 (synth)"

echo "=== 主成品(合成器版,用户听感:合成器 > 小号)==="
cp Combat_Extraction_v9_synth.mid Combat_Extraction.mid
cp Combat_Extraction_v9_synth.mp3 Combat_Extraction.mp3

echo "=== 完成 ==="
