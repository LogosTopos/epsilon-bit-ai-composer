#!/usr/bin/env python3
"""drums.py — M1 节奏动机全谱(档1/2/3 + 呼吸):16 小节母 loop(规划 §2/§3)。

角色:'drums'(ch9,GM 鼓:36 kick / 38 snare / 42 hat / 49 crash)。
档位(相对 bar0):
  i=0..3   档1  kick 3+3+2(0.0/1.5/3.0)+ snare 2/4 拍 + hat 8分 + 档起点 crash  CC11 60
  i=4..7   档2  同档1 + hat 16分 + m10 末 1 拍 16分 snare fill                  CC11 72
  i=8..11  档3  kick 8分驱动(3+3+2 重音在 0.0/1.5/3.0)+ snare 2/4 + 每小节起点
                crash + m14 末 2 拍 16分 fill                                   CC11 84
  i=12..15 呼吸  kick 减半(每 2 拍一发)+ hat 8分,snare/cymbal 抽离               CC11 66
cycle=1 微变(§6 允许):kick 力度 +3;m10 fill → 2 拍 3+3+2 十六分滚奏;
m14 fill → 32分滚奏。
循环工程(§7):m18(i=15)第 4 拍无重音/新事件;呼吸段能量回落不归零。
"""
import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS


def build(s, bar0, cycle, ch):
    """写 16 小节母 loop(bar0 起,即 m3-18),cycle=0/1。返回 bar0+16。"""
    base = (bar0 - 1) * 4
    dk = 3 if cycle == 1 else 0            # cycle=1: kick 力度 +3

    def B(i, b):
        return base + i * 4 + b            # loop 内第 i 小节、小节内拍 b

    # ---------- 档1 (i=0..3): 骨架 kick 3+3+2 + 背拍 + hat 8分 ----------
    s.cc('drums', 11, 60, B(0, 0.0))
    for i in range(4):
        for b in (0.0, 1.5, 3.0):
            s.note('drums', 36, 88 + dk, B(i, b), 0.2)     # kick 3+3+2
        for b in (1.0, 3.0):
            s.note('drums', 38, 84, B(i, b), 0.2)          # snare 2/4 拍
        for j in range(8):
            s.note('drums', 42, 60, B(i, j * 0.5), 0.15)   # hat 8分
    s.note('drums', 49, 88, B(0, 0.0), 1.2)                # m3 起点 crash

    # ---------- 档2 (i=4..7): + hat 16分 + m10 fill ----------
    s.cc('drums', 11, 72, B(4, 0.0))
    for i in range(4, 8):
        for b in (0.0, 1.5, 3.0):
            s.note('drums', 36, 94 + dk, B(i, b), 0.2)
        for b in ((1.0,) if i == 7 else (1.0, 3.0)):       # m10 背拍 3.0 让给 fill
            s.note('drums', 38, 90, B(i, b), 0.2)
        for j in range(16):
            s.note('drums', 42, 66, B(i, j * 0.25), 0.15)  # hat 16分
    s.note('drums', 49, 94, B(4, 0.0), 1.2)                # m7 起点 crash
    if cycle == 0:
        # m10 末 1 拍 16分 snare fill + kick 预击(渐强,直入档3 密度翻倍)
        for j in range(4):
            s.note('drums', 38, 90, B(7, 3.0 + j * 0.25), 0.2)
        for j in range(3):
            s.note('drums', 36, 72 + j * 6, B(7, 3.25 + j * 0.25), 0.2)
    else:
        # m10: 2 拍 3+3+2 十六分滚奏(重音在 16分位 0/3/6 → 拍 2.0/2.75/3.5)+ kick
        for j in range(8):
            vel = 94 if j in (0, 3, 6) else 84
            s.note('drums', 38, vel, B(7, 2.0 + j * 0.25), 0.2)
        for j in range(3):
            s.note('drums', 36, 60 + j * 8, B(7, 3.25 + j * 0.25), 0.2)

    # ---------- 档3 (i=8..11): kick 8分驱动 + 每小节 crash + m14 fill ----------
    s.cc('drums', 11, 84, B(8, 0.0))
    for i in range(8, 12):
        for j in range(8):
            b = j * 0.5
            vel = 104 + dk if b in (0.0, 1.5, 3.0) else 92 + dk
            s.note('drums', 36, vel, B(i, b), 0.2)         # 8分驱动,3+3+2 重音
        for b in ((1.0,) if i == 11 else (1.0, 3.0)):      # m14 背拍让给 fill
            s.note('drums', 38, 98, B(i, b), 0.2)
        for j in range(16):
            s.note('drums', 42, 72, B(i, j * 0.25), 0.15)
        s.note('drums', 49, 100, B(i, 0.0), 1.2)           # 每小节起点 crash
    if cycle == 0:
        # m14 末 2 拍 16分 fill(2.0/3.0 背拍收进 fill 重音)
        for j in range(8):
            vel = 98 if j in (0, 4) else 90
            s.note('drums', 38, vel, B(11, 2.0 + j * 0.25), 0.2)
    else:
        # m14: 2 拍 32分滚奏(2.0/3.0 重音)
        for j in range(16):
            vel = 98 if j in (0, 8) else 92
            s.note('drums', 38, vel, B(11, 2.0 + j * 0.125), 0.09)

    # ---------- 呼吸 (i=12..15): 鼓抽离,回落不归零 ----------
    # 渐变:第一小节(m15)kick 每拍 1 发 + hat 8分;第二小节(m16)kick 每 2 拍 1 发 + hat 4分
    s.cc('drums', 11, 66, B(12, 0.0))
    for b in (0.0, 1.0, 2.0, 3.0):
        s.note('drums', 36, 78 + dk, B(12, b), 0.2)
    for b in (0.0, 2.0):
        s.note('drums', 36, 74 + dk, B(13, b), 0.2)
    for j in range(8):
        s.note('drums', 42, 72, B(12, j * 0.5), 0.15)
    for j in range(4):
        s.note('drums', 42, 66, B(13, j * 1.0), 0.15)
    # 呼吸段无 snare / 无 crash(§3 cymbal 抽离;§7 m18 第 4 拍无重音)

    return bar0 + 16


if __name__ == '__main__':
    ch = {'drums': 9, 'bass_electric': 6, 'timpani': 11}
    s = Score()
    bank, prog, (lo, hi), pan, rev = PROGS['drums']
    s.add_instr('drums', ch['drums'], bank, prog, lo, hi, pan, rev)
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
