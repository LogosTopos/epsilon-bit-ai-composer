#!/usr/bin/env python3
"""mix_stems.py — 《深渊对位》stem 级混音

把 render_stems.py 产出的 5 个 stem 用 ffmpeg 混音,支持:
  --profile baseline  纯相加(验证 stem 拆分保真度,对比整轨渲染)
  --profile mix       生产混音:EQ 清理(highpass/高频打磨)+ 平衡 + alimiter

用法:
    python3 mix_stems.py --profile baseline --out stems/_mix_baseline.wav
    python3 mix_stems.py --profile mix      --out stems/_mix_prod.wav
    python3 mix_stems.py --profile mix      --out Contrapunctus_Abyssi_stemmed.wav
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_stems import stats  # noqa: E402

STEMS = [
    ('strings',    'stems/stem_strings.wav'),
    ('woodwinds',  'stems/stem_woodwinds.wav'),
    ('brass',      'stems/stem_brass.wav'),
    ('percussion', 'stems/stem_percussion.wav'),
    ('color',      'stems/stem_color.wav'),
]

# 生产混音链(以 strings 为基准,平衡系数来自 stem RMS 与听感经验):
#   strings 主体不动;木管/色彩偏弱(补);铜管中坚(微补);打击乐瞬态强(微压)
CHAIN_MIX = {
    'strings':    'highpass=f=30,acompressor=threshold=-28dB:ratio=1.8:attack=15:release=200,volume=1.00',
    'woodwinds':  'highpass=f=45,volume=1.6',
    'brass':      'highpass=f=35,volume=1.15',
    'percussion': 'volume=1.0,acompressor=threshold=-18dB:ratio=2.5:attack=5:release=120',
    'color':      'highpass=f=28,volume=1.5',
}

CHAIN_BASELINE = {name: 'volume=1.0' for name, _ in STEMS}


def mix(profile, out_wav):
    chains = CHAIN_MIX if profile == 'mix' else CHAIN_BASELINE
    inputs = []
    flt = []
    for i, (name, path) in enumerate(STEMS):
        inputs += ['-i', path]
        flt.append(f'[{i}:a]{chains[name]}[s{i}]')
    flt.append(''.join(f'[s{i}]' for i in range(len(STEMS))) + 'amix=inputs=5:normalize=0[mix]')
    flt.append('[mix]alimiter=limit=0.95[out]')
    cmd = (['ffmpeg', '-y', '-loglevel', 'error'] + inputs +
           ['-filter_complex', ';'.join(flt), '-map', '[out]', '-c:a', 'pcm_s16le', out_wav])
    subprocess.run(cmd, check=True)
    return stats(out_wav)


def main():
    ap = argparse.ArgumentParser(description='《深渊对位》stem 混音')
    ap.add_argument('--profile', choices=['baseline', 'mix'], default='mix')
    ap.add_argument('--out', default='stems/_mix_prod.wav')
    args = ap.parse_args()
    print(f'== 混音 [{args.profile}] → {args.out} ==')
    for name, path in STEMS:
        st = stats(path)
        print(f'  {name:10s} RMS {st["rms_db"]:6.1f} dB  峰值 {st["peak_db"]:5.1f} dB')
    st = mix(args.profile, args.out)
    print(f'  混音结果      RMS {st["rms_db"]:6.1f} dB  峰值 {st["peak_db"]:5.1f} dB  {st["seconds"]}s')
    ref = stats('stems/_full_reference.wav')
    print(f'  整轨参考      RMS {ref["rms_db"]:6.1f} dB  峰值 {ref["peak_db"]:5.1f} dB')


if __name__ == '__main__':
    main()
