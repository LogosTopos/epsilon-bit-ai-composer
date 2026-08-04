#!/usr/bin/env python3
"""render_stems.py — 《深渊对位》stem 分轨渲染

把 Contrapunctus_Abyssi.mid 按通道组拆成 5 个 stem(弦乐/木管/铜管/打击乐/色彩),
各自用项目标准管线(fluidsynth + MuseScore_General.sf2)渲染成 WAV,
为 stem 级混音(EQ/压缩/平衡)提供素材。

用法:
    python3 render_stems.py [--mid Contrapunctus_Abyssi.mid] [--out stems]

输出:
    stems/*.mid      拆分后的临时 MIDI(每份含 meta 轨 + 组内音轨)
    stems/*.wav      各组渲染结果
    stems/stems.json 各组 RMS/峰值统计
"""
import argparse
import json
import os
import subprocess
import sys
import wave

import mido

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SF2 = os.path.join(ROOT, 'soundfonts', 'MuseScore_General.sf2')

# 通道组: (组名, [通道列表], 说明)
GROUPS = [
    ('strings',     [2, 3, 4, 5, 6],   '一提/二提/中提/大提/低音提琴'),
    ('woodwinds',   [7, 8, 10],        '长笛/双簧管/单簧管/大管'),
    ('brass',       [12, 13],          '圆号/小号/弱音小号/长号/大号'),
    ('percussion',  [9, 11],           '打击乐(Orchestra Kit)/定音鼓'),
    ('color',       [0, 1, 14, 15],    '教堂钟/竖琴/合唱/管风琴/钢片琴/钟琴'),
]
CH_TO_GROUP = {ch: name for name, chans, _ in GROUPS for ch in chans}


def split_midi(src_path, out_dir):
    """按通道组拆分格式 1 MIDI。每组 = meta 轨 + 该组通道的音轨。"""
    mid = mido.MidiFile(src_path)
    meta = mid.tracks[0]
    by_group = {name: [] for name, _, _ in GROUPS}
    for t in mid.tracks[1:]:
        # 每轨单通道;取该轨第一个 channel 归属组
        chans = {m.channel for m in t if hasattr(m, 'channel')}
        assert len(chans) == 1, f'音轨含多通道 {chans}'
        ch = chans.pop()
        by_group[CH_TO_GROUP[ch]].append(t)
    paths = {}
    for name, chans, _ in GROUPS:
        out = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)
        out.tracks.append(meta)
        for t in by_group[name]:
            out.tracks.append(t)
        p = os.path.join(out_dir, f'stem_{name}.mid')
        out.save(p)
        paths[name] = p
        print(f'  stem_{name:10s} ch{chans} → {p} ({len(by_group[name])} 轨)')
    return paths


def render(src_mid, out_wav):
    cmd = ['fluidsynth', '-F', out_wav, '-r', '44100', '-R', '0.9', '-C', '0',
           '-g', '1.2', SF2, src_mid]
    subprocess.run(cmd, check=True, capture_output=True)


def stats(wav_path):
    """RMS(dB, 以 32768 为满幅)与峰值(dBFS)。口径与作品说明一致。"""
    with wave.open(wav_path, 'rb') as w:
        n = w.getnframes()
        sw = w.readframes(n)
    import audioop
    import math
    rms = audioop.rms(sw, 2) / 32768.0
    mx = audioop.max(sw, 2) / 32768.0
    return {'rms_db': 20 * math.log10(max(rms, 1e-9)),
            'peak_db': 20 * math.log10(max(mx, 1e-9)),
            'seconds': round(n / 44100.0, 1)}


def main():
    ap = argparse.ArgumentParser(description='《深渊对位》stem 分轨渲染')
    ap.add_argument('--mid', default='Contrapunctus_Abyssi.mid')
    ap.add_argument('--out', default='stems')
    args = ap.parse_args()

    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)

    print('== 1. 拆 MIDI ==')
    paths = split_midi(args.mid, out_dir)

    print('== 2. 渲染(fluidsynth 标准管线) ==')
    results = {}
    for name, _, desc in GROUPS:
        wav = os.path.join(out_dir, f'stem_{name}.wav')
        if not os.path.exists(wav):
            print(f'  渲染 {name} ({desc})...', flush=True)
            render(paths[name], wav)
        results[name] = stats(wav)
        print(f'  {name:10s} {results[name]["seconds"]:6.1f}s  '
              f'RMS {results[name]["rms_db"]:6.1f} dB  峰值 {results[name]["peak_db"]:5.1f} dB')

    json_path = os.path.join(out_dir, 'stems.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'== 完成:统计写入 {json_path} ==')

    # 整轨参考(若存在)
    ref = os.path.join(out_dir, '_full_reference.wav')
    if not os.path.exists(ref):
        print('== 3. 整轨参考渲染(对比基准) ==')
        render(args.mid, ref)
    print('  整轨参考:', stats(ref))


if __name__ == '__main__':
    main()
