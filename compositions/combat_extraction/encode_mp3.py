#!/usr/bin/env python3
"""encode_mp3.py — 通用 MP3 压码(峰值归一 + true-peak 限幅 + ID3)

链路审计(E Agent,2026-08)修复项:
- 旧配方 volume(补到采样峰值 -1dB)+ alimiter 0.95 → MP3 真峰值 TP -0.48~-0.53 dBTP 超限
- 新配方 volume(补到采样峰值 -1dB)+ alimiter=limit=0.891:level=0 → 实测 TP -1.06 dBTP ✓

用法:python3 encode_mp3.py in.wav out.mp3 "标题" [专辑]
输出:文件 + 采样峰值/真峰值/均值(ebur128 实测)
"""
import subprocess
import sys
import wave
import audioop
import math


def encode(src, dst, title, album='Combat Extraction'):
    with wave.open(src, 'rb') as w:
        n = w.getnframes()
        sw = w.readframes(n)
    pk = audioop.max(sw, 2) / 32768.0
    g = 20 * math.log10(0.891 / pk)              # 补到采样峰值 -1dB(0.891)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-i', src,
           '-af', f'volume={g:.2f}dB,alimiter=limit=0.891:level=0',   # TP 限幅修复
           '-c:a', 'libmp3lame', '-q:a', '2',
           '-metadata', f'title={title}',
           '-metadata', 'artist=ε-bit AI Composer',
           '-metadata', f'album={album}',
           '-metadata', 'genre=Game Music',
           dst]
    subprocess.run(cmd, check=True)
    # 校验:ebur128 出真峰值(TP)/均值,volumedetect 出采样峰值
    out = subprocess.run(['ffmpeg', '-i', dst, '-af', 'ebur128=peak=true',
                          '-f', 'null', '-'], capture_output=True, text=True)
    tp = mean = None
    for l in out.stderr.splitlines():
        l = l.strip()
        if 'I:' in l and 'LUFS' in l:
            mean = l.split('I:')[1].split()[0]
        if 'Peak:' in l:
            tp = l.split('Peak:')[1].split()[0]
    out2 = subprocess.run(['ffmpeg', '-i', dst, '-af', 'volumedetect', '-f', 'null', '-'],
                          capture_output=True, text=True)
    pk2 = [l.split('max_volume: ')[1].replace(' dB', '')
           for l in out2.stderr.splitlines() if 'max_volume' in l][0]
    print(f'{dst}: 采样峰值 {pk2} dB, TP {tp} dBTP, 集成响度 {mean} LUFS')
    if tp is not None:
        try:
            if float(tp) > -0.9:
                print(f'  [警告] TP {tp} 超 -1dB 口径,建议检查')
        except ValueError:
            pass
    return float(tp) if tp else None


if __name__ == '__main__':
    ap = __import__('argparse').ArgumentParser(description='MP3 压码(TP 限幅)')
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--title', default='Combat Extraction')
    ap.add_argument('--album', default='Combat Extraction')
    a = ap.parse_args()
    encode(a.src, a.dst, a.title, a.album)
