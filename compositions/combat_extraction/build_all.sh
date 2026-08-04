#!/usr/bin/env bash
# build_all.sh — 《搜打撤》全量一键构建(链路 v2)
# 母节双版 → 全部子节 → SDC v1 → 连播 demo,统一走:
#   并行渲染(5 stems)+ 增量缓存(内容哈希,只重渲染过期项)+ 校验门 + TP 限幅压码
# 用法:./build_all.sh [--full]   (--full = 先清 stems 缓存强制全量)
set -e
cd "$(dirname "$0")"

if [ "$1" == "--full" ]; then
  echo "=== 强制全量:清 stems 缓存 ==="
  rm -f stems/stem_*
fi

echo "=== [1/4] 母节双版(build.sh)==="
./build.sh

echo "=== [2/4] 子节独立成品 ==="
for f in S1_Scavenge S2_Explore S4_Crisis S5_Extract S6_Calm; do
  python3 mix_stems.py --mid $f.mid --render-stems --out stems/_mix_$f.wav
  python3 encode_mp3.py stems/_mix_$f.wav $f.mp3 --title "$f"
done

echo "=== [3/4] 搜-打-撤 v1 ==="
python3 sections/sdc_v1.py >/dev/null
python3 mix_stems.py --mid Combat_Extraction_SDC_v1.mid --render-stems --out stems/_mix_sdc_v1.wav
python3 encode_mp3.py stems/_mix_sdc_v1.wav Combat_Extraction_SDC_v1.mp3 --title "搜打撤 v1 (S1→母节→S6)"

echo "=== [4/4] 连播 demo ==="
python3 sections/demo_playthrough.py >/dev/null
python3 mix_stems.py --mid Combat_Extraction_Playthrough.mid --render-stems --out stems/_mix_playthrough.wav
python3 encode_mp3.py stems/_mix_playthrough.wav Combat_Extraction_Playthrough.mp3 --title "Combat Extraction - Playthrough (S1→S6)"

echo "=== [5/5] 无缝大循环(可单曲循环,首尾无缝) ==="
python3 sections/build_loop.py >/dev/null
python3 mix_stems.py --mid Combat_Extraction_Loop.mid --render-stems --out stems/_mix_loop.wav
# 循环成品必须裁掉 FluidSynth 混响尾(2026-08-05 用户反馈末尾静音):
# 裁到 MIDI 实际长度 + 0.15s,循环播放时音乐结束后直接回开头,无静音带
LOOP_DUR=$(python3 -c "import mido; print(f'{mido.MidiFile(\"Combat_Extraction_Loop.mid\").length + 0.15:.2f}')")
ffmpeg -y -loglevel error -i stems/_mix_loop.wav -t "$LOOP_DUR" -c:a pcm_s16le stems/_mix_loop_trim.wav
python3 encode_mp3.py stems/_mix_loop_trim.wav Combat_Extraction_Loop.mp3 --title "搜打撤 无缝大循环"

echo "=== 完成:全部成品已重建 ==="
