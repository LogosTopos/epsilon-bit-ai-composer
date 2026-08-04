#!/usr/bin/env python3
"""s1_scavenge.py — 子节 1:《低音入场版》(搜刮/开场氛围)

依据:ARCHITECTURE §3 子节规范(S1)+ 用户指令(2026-08):
① 删整个 stab(hook/brass/fx/rhythm 全撤) ② bass 平和化——
   8 分根音脉冲(规划 §4 原版 riff,音符数 16→8),句尾 bend 保留贝斯手感

受控改动(相对母节 v8.2):
- stab 组 4 角色(hook/brass_stab/fx/synth_rhythm):全删
- bass:16 分密集高把位 → 8 分根音脉冲(低把位 E1/G1 区),vel 70-84,
  句尾重音 84 + bend +2(贝斯手的"手"),每轮 bar4 句尾长音(1 拍,句号感)
- drums:满配 8 分驱动 → kick 每拍(4 分,vel 70)+ snare 2/4(58)+ hat 8 分(48)
- strings/pad/choir:长音保持(vel 40/30/36,氛围主导)
- piano:0.0 轻击(40,小节锚点)
- vln1 回声:保留但轻(vel 40,应答 bass 句尾)
- timpani/M3/riser/fill/幽灵音/开镲:全撤(重击元素不进场)
- CC11:80-84 → 76 微弧(轻档;GUGS 响应 CC11,bass 保持可闻)
- 与母节共享:16 小节网格 / Em-C-G-D 循环 / 168 BPM / m18 回环轻收
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS

# 16 小节和弦序(与母节共享骨架:轮1 Em Em C D,轮2-4 Em C G D)
CHORDS16 = ('Em', 'Em', 'C', 'D', 'Em', 'C', 'G', 'D',
            'Em', 'C', 'G', 'D', 'Em', 'C', 'G', 'D')

# 平和 Bass:规划 §4 原版 8 分 riff(根音脉冲 + 五度/八度),每小节 8 音
BASS_CALM = {
    'Em': (28, 28, 40, 28, 28, 40, 28, 35),   # E1 E1 E2 E1 E1 E2 E1 G2
    'C':  (36, 36, 48, 36, 36, 48, 36, 43),   # C2 C2 C3 C2 C2 C3 C2 G2
    'G':  (31, 31, 43, 31, 31, 43, 31, 38),   # G1 G1 G2 G1 G1 G2 G1 D2
    'D':  (38, 38, 50, 38, 38, 50, 38, 45),   # D2 D2 D3 D2 D2 D3 D2 A2
}
BASS_VEL = (82, 82, 88, 82, 82, 88, 82, 96)   # 句尾重音 96 + bend(主角但平和,比母节 104-116 轻)
CC11_TIER = (78, 80, 82, 80)                  # 轮起点 CC11 微弧(轻档,保 bass 可闻)


def build(s, bar0, cycle, ch):
    """铺 16 小节 S1(小节 = bar0 起),返回 bar0+16。"""
    B = 'bass_electric'
    V1, V2, VA, VC = 'vln1', 'vln2', 'vla', 'celli'
    P, PA, CHO = 'piano_bang', 'synth_pad', 'choir'

    def bt(bar):
        return (bar - 1) * 4

    # CC11 微弧(轮起点 74/76/78/76)
    for name in (B, V1, V2, VA, VC, P, PA, CHO):
        for i, ccv in enumerate(CC11_TIER):
            s.cc(name, 11, ccv, bt(bar0 + i * 4))

    # ---------------- drums:kick 每拍 + snare 2/4 轻 + hat 8分 ----------------
    for i in range(16):
        for b in (0.0, 1.0, 2.0, 3.0):
            if i == 15 and b == 3.0:
                continue                       # m18 第 4 拍轻收(回环)
            s.note('drums', 36, 70, bt(bar0 + i) + b, 0.2)
        for b in (1.0, 3.0):
            s.note('drums', 38, 58, bt(bar0 + i) + b, 0.2)
        for j in range(8):
            s.note('drums', 42, 48, bt(bar0 + i) + j * 0.5, 0.15)
    s.note('drums', 49, 70, bt(bar0), 1.0)     # 起点 crash(轻)

    # ---------------- bass:平和 8 分脉冲 + bar4 句号长音(无 bend——用户反馈弹簧音效去掉) ----------------
    for i in range(16):
        prog = CHORDS16[i]
        for j, p in enumerate(BASS_CALM[prog]):
            vel = BASS_VEL[j]
            dur = 0.45
            # 每轮 bar4:句尾音加长(句号感,1 拍)
            if i % 4 == 3 and j == 7:
                dur = 0.95
            s.note(B, p, vel, bt(bar0 + i) + j * 0.5, dur)

    # ---------------- 氛围层:strings/pad/choir 长音 + piano 轻锚点 + vln1 回声 ----------------
    VOICES = {
        'Em': (40, 64, 64, 71),
        'C':  (36, 64, 67, 72),
        'G':  (43, 62, 67, 71),
        'D':  (38, 62, 66, 69),
    }
    CHOIR = {
        'Em': (52, 55, 64),
        'C':  (48, 52, 55),
        'G':  (55, 62, 67),
        'D':  (50, 54, 62),
    }
    for i, prog in enumerate(CHORDS16):
        c, v3, v5, r1 = VOICES[prog]
        for name, pitch, vel in ((VC, c, 40), (VA, v3, 40), (V2, v5, 40), (V1, r1, 40)):
            s.note(name, pitch, vel, bt(bar0 + i), 3.9)
        s.chord(PA, CHOIR[prog], 30, bt(bar0 + i), 3.9)
        s.chord(CHO, CHOIR[prog], 36, bt(bar0 + i), 3.9)
        r0 = {'Em': 40, 'C': 36, 'G': 43, 'D': 38}[prog]
        s.note(P, r0, 40, bt(bar0 + i), 0.3)
        s.note(P, r0 + 12, 40, bt(bar0 + i), 0.3)
        # vln1 回声:bar1/3 句尾(应答 bass 句尾重音),轻
        if i % 4 in (0, 2):
            pair = {'Em': (64, 67), 'C': (64, 67), 'G': (62, 67)}[prog]
            s.note(V1, pair[0], 40, bt(bar0 + i) + 3.5, 0.2)
            s.note(V1, pair[1], 40, bt(bar0 + i) + 3.75, 0.2)

    return bar0 + 16


if __name__ == '__main__':
    import contextlib, io
    CH = {'piano_bang': 0, 'synth_pad': 1, 'vln1': 2, 'vln2': 3, 'vla': 4,
          'celli': 5, 'bass_electric': 6, 'drums': 9, 'choir': 14}
    s = Score(humanize=True, seed=42)
    for role, chn in CH.items():
        bank, prog, (lo, hi), pan, rev = PROGS[role]
        s.add_instr(role, chn, bank, prog, lo, hi, pan, rev)
        s.cc(role, 7, 100, 0.0)
    s.tempo(168, 0.0)
    build(s, 3, 0, CH)
    build(s, 19, 1, CH)
    s.flush('S1_Scavenge.mid')
    print('S1 冒烟完成: S1_Scavenge.mid(期望 0 音区告警 / 0 冲突)')
