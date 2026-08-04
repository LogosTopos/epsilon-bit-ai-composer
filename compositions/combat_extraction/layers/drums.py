#!/usr/bin/env python3
"""drums.py — 打击乐层(高潮段满配版):kick/snare/hat/幽灵音/fill/timpani

母节 = 高潮段(用户决策):16 小节全程满配,无档位。16 小节 = 4 轮对话链。
- kick:8 分驱动,3+3+2 重音(0.0/1.5/3.0),全程;m18(rel 15)第 4 拍省略(回环)
- snare:2/4 拍背拍,全程
- hat:16 分,全程
- 幽灵音:每轮 bar1-3(rel 0-2/4-6/8-10/12-14)的 0.25/1.75/2.25/3.75(bar4 让位 fill/M3)
- crash:轮起点 rel 0/4/8/12
- fill:rel 7/11 末(cycle0:16 分 8 音;cycle1:32 分滚奏)
- timpani:全程 2.0 根音重击(轮力度 66/70/74/72)+ M3 齐击(rel 3/7/11 @3.0,38,78)
CC11 全程 80-84 微弧(轮起点 80/82/84/82)——GUGS 响应 CC11,低值会让音色静音
"""
import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS

# 16 小节和弦序(4 轮:轮1 Em Em C D,轮2-4 Em C G D)
CHORDS16 = ('Em', 'Em', 'C', 'D', 'Em', 'C', 'G', 'D',
            'Em', 'C', 'G', 'D', 'Em', 'C', 'G', 'D')
TIMP_ROOT = {'Em': 40, 'C': 36, 'G': 31, 'D': 38}
TIMP_VEL = (66, 70, 74, 72)          # 轮 1-4 的 2.0 重击力度(微弧)
CC11_TIER = (80, 82, 84, 82)         # 轮起点 CC11(无档位落差,80-84 微弧)


def build(s, bar0, cycle, ch):
    """写 16 小节母 loop(bar0 起,即 m3-18),cycle=0/1。返回 bar0+16。"""
    base = (bar0 - 1) * 4
    dk = 3 if cycle == 1 else 0            # cycle=1: kick 力度 +3

    def B(i, b):
        return base + i * 4 + b            # loop 内第 i 小节、小节内拍 b

    # CC11 微弧(轮起点 80/82/84/82)
    for i, ccv in enumerate(CC11_TIER):
        s.cc('drums', 11, ccv, B(i * 4, 0.0))

    # ---------- 全程骨架:kick 8分(3+3+2 重音;bar3 移位 3+2+3)+ snare 2/4 + hat 16分 ----------
    for i in range(16):
        shift = (i % 4 == 2)                     # 每轮 bar3:重音移位(句法转)
        for j in range(8):
            b = j * 0.5
            if i == 15 and b == 3.0:
                continue                          # m18 第 4 拍无重音(回环)
            if shift and b == 3.0:
                vel = 92 + dk                     # 移位小节:3.0 降普通(3+2+3)
            else:
                acc = (0.0, 1.5, 2.5) if shift else (0.0, 1.5, 3.0)
                vel = 104 + dk if b in acc else 92 + dk
            s.note('drums', 36, vel, B(i, b), 0.2)
        for b in ((1.0,) if i in (7, 11) else (1.0, 3.0)):   # rel 7/11 的 3.0 背拍让位 fill
            s.note('drums', 38, 98 + dk, B(i, b), 0.2)
        for j in range(16):
            s.note('drums', 42, 72, B(i, j * 0.25), 0.15)
        if shift:
            s.note('drums', 44, 74, B(i, 2.75), 0.15)   # 开镲(bar3,鼓手的呼吸)

    # ---------- 幽灵音:每轮 bar1-3(bar4 让位 fill/M3/riser) ----------
    for i in (0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14):
        for j in (1, 7, 9, 15):
            s.note('drums', 38, 45, B(i, j * 0.25), 0.1)

    # ---------- crash:轮起点(rel 0/4/8/12) ----------
    for i in (0, 4, 8, 12):
        s.note('drums', 49, 96, B(i, 0.0), 1.0)

    # ---------- fill:rel 3 小 fill(2 音收束)+ rel 7/11 大 fill(轮 2/3 收束) ----------
    for b, v in ((3.5, 96), (3.75, 88)):
        s.note('drums', 38, v, B(3, b), 0.2)     # 轮1 bar4 末小 fill
    if cycle == 0:
        for rel in (7, 11):
            for j in range(8):                       # 16 分 8 音(2.0-3.75)
                vel = 98 if j in (0, 4) else 90
                s.note('drums', 38, vel, B(rel, 2.0 + j * 0.25), 0.2)
    else:
        for rel in (7, 11):                          # cycle1:32 分滚奏变体
            for j in range(16):
                vel = 98 if j in (0, 8) else 92
                s.note('drums', 38, vel, B(rel, 2.0 + j * 0.125), 0.09)

    # ---------- timpani:全程 2.0 根音重击 + M3 齐击(rel 3/7/11) ----------
    for i in range(16):
        d = 0.2 if i >= 12 else 0.4              # 轮4 双音滚:主音缩短让位第二音
        s.note('timpani', TIMP_ROOT[CHORDS16[i]], TIMP_VEL[i // 4], B(i, 2.0), d)
        if i >= 12:                              # 轮4:双音滚(收束前密化)
            s.note('timpani', TIMP_ROOT[CHORDS16[i]], TIMP_VEL[i // 4] - 12, B(i, 2.25), 0.25)
    for rel in (3, 7, 11):
        s.note('timpani', 38, 78, B(rel, 3.0), 0.4)   # M3:D2 与 brass/kick/bass 齐奏
    # rel 15(m18)无 M3 —— 回环工程:m18 第 4 拍无重音

    return bar0 + 16


if __name__ == '__main__':
    ch = {'drums': 9, 'bass_electric': 6, 'timpani': 11}
    s = Score()
    for name, c in ch.items():
        bank, prog, (lo, hi), pan, rev = PROGS[name]
        s.add_instr(name, c, bank, prog, lo, hi, pan, rev)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        build(s, 3, 0, ch)     # 圈 1(cycle=0)
        build(s, 19, 1, ch)    # 圈 2(cycle=1 微变路径)
        s.flush('/tmp/smk_drums.mid')
    out = buf.getvalue()
    print(out)
    bad = out.count('[音区告警]') + out.count('[冲突]')
    print(f'smoke drums: {"PASS" if bad == 0 else "FAIL"} (issues={bad}, loop x2 bar0=3/19)')
    sys.exit(0 if bad == 0 else 1)
