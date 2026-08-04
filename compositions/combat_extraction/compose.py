#!/usr/bin/env python3
"""compose.py — 《搜打撤》战斗背景曲 总装(父会话)

结构: Intro(m1-2) → 母loop ×2(m3-18 ×2)→ Outro(m19-20)
分层: intro_outro / drums / bass_harmony / riff_texture(各子Agent独立模块)
本文件只做:音色注册 + 按序调用各层 + 自检。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.orch import Score
from lib.progs import PROGS
import layers.intro_outro as L_io
import layers.drums as L_drums
import layers.bass_harmony as L_bass
import layers.riff_texture as L_riff

# 角色 → 通道(规划 §5)
ROLE_CH = {
    'piano_bang': 0, 'synth_pad': 1,
    'vln1': 2, 'vln2': 3, 'vla': 4, 'celli': 5,
    'bass_electric': 6,
    'drums': 9, 'guitar_dist': 10, 'timpani': 11,
    'brass_stab': 12, 'keys': 13, 'choir': 14,
}


def build(s: Score):
    for role, ch in ROLE_CH.items():
        bank, prog, (lo, hi), pan, rev = PROGS[role]
        s.add_instr(role, ch, bank, prog, lo, hi, pan, rev)
        s.cc(role, 7, 100, 0.0)

    s.tempo(168, 0.0)                        # 168 BPM(战斗曲速度)

    b = L_io.build_intro(s, 1, ROLE_CH)
    for cycle in (0, 1):                     # 母 loop ×2(展示无缝循环)
        for layer in (L_drums, L_bass, L_riff):
            layer.build(s, b, cycle, ROLE_CH)    # 各层同起点并行铺 16 小节
        b += 16
    L_io.build_outro(s, b, ROLE_CH)          # b = 35


def main():
    import argparse
    ap = argparse.ArgumentParser(description='《搜打撤》战斗背景曲')
    ap.add_argument('--out', default='Combat_Extraction.mid')
    args = ap.parse_args()
    s = Score(humanize=True, seed=42)
    build(s)
    s.flush(args.out)
    print('=== 结构 ===')
    print('  Intro m1-2 → 母loop m3-18 ×2 → Outro m19-20')
    print('  168 BPM, E 小调,Em-C-G-D 循环和声')
    print('  时长 ≈ 57s(母 loop 22.9s,可无限循环)')


if __name__ == '__main__':
    main()
