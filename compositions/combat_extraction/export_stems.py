#!/usr/bin/env python3
"""export_stems.py — stems 交付导出(链路 v2)

把成品 MIDI 拆 5 组 stems → 并行渲染 → 裁母节单圈(loop)→ 24-bit wav
→ loop 信息 JSON → zip 打包,供 FMOD/Wwise/Godot 垂直混音集成。

用法:
  python3 export_stems.py --mid Combat_Extraction.mid --loop-start 2.857 --loop-len 22.857
                          [--out dist/stems_24bit]
  # 母节默认 loop:2.857s 起(2 小节留白后 m3)、22.857s(16 小节 @168BPM)
  # 不裁 loop 时(--loop-start 省略):输出完整 stems(连播/SDC 用)
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mix_stems import split_stems, render, STEMS, SF2S  # noqa: E402


def to_24bit(src, dst):
    """pcm_s16le → pcm_s24le(保留头尾,不裁)。"""
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src,
                    '-c:a', 'pcm_s24le', dst], check=True)


def cut_loop(src, dst, start, length):
    """裁单圈 loop:从 start 秒起,截 length 秒(母节 = 16 小节 @168BPM = 22.857s)。"""
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src,
                    '-ss', f'{start:.4f}', '-t', f'{length:.4f}',
                    '-c:a', 'pcm_s24le', dst], check=True)


def main():
    ap = argparse.ArgumentParser(description='stems 24-bit 交付导出')
    ap.add_argument('--mid', required=True)
    ap.add_argument('--loop-start', type=float, default=None,
                    help='loop 起点秒(母节 2.857 = m3 起点);缺省 = 不裁,输出完整 stems')
    ap.add_argument('--loop-len', type=float, default=None, help='loop 长度秒(母节 22.857)')
    ap.add_argument('--out', default='dist/stems_24bit')
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    os.makedirs('stems', exist_ok=True)
    midbase = os.path.splitext(os.path.basename(args.mid))[0]
    cache_dir = os.path.join('stems', midbase)
    os.makedirs(cache_dir, exist_ok=True)
    paths = split_stems(args.mid, cache_dir)
    todo = [(name, os.path.join(cache_dir, f'stem_{name}.wav'), mid)
            for name, mid in paths.items()]
    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(lambda it: render(it[2], it[1]), todo))

    loop_info = {'source': os.path.basename(args.mid), 'sample_rate': 44100, 'bits': 24}
    if args.loop_start is not None and args.loop_len is not None:
        loop_info['loop_start_s'] = round(args.loop_start, 4)
        loop_info['loop_len_s'] = round(args.loop_len, 4)
        for name, raw, _ in todo:
            cut_loop(raw, os.path.join(args.out, f'{name}.wav'),
                     args.loop_start, args.loop_len)
    else:
        for name, raw, _ in todo:
            to_24bit(raw, os.path.join(args.out, f'{name}.wav'))
    json.dump(loop_info, open(os.path.join(args.out, 'loop.json'), 'w'), indent=2)

    zip_path = args.out + '.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in os.listdir(args.out):
            z.write(os.path.join(args.out, f), arcname=f)
    print(f'stems 交付: {args.out}/ (24-bit' +
          (f', loop {loop_info["loop_start_s"]}s + {loop_info["loop_len_s"]}s' if 'loop_start_s' in loop_info else ', 完整')
          + f')→ {zip_path}')
    for name, _, _ in todo:
        print(f'  {name}.wav ✓')


if __name__ == '__main__':
    main()
