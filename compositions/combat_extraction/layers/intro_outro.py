#!/usr/bin/env python3
"""intro_outro.py — Intro(m1-2)+ Outro(m19-20)(规划 §2/§6/§8)。

Intro (m1-2):军鼓 16分渐强滚奏(vel 30→70,滚入 m2 第 4 拍爆炸)
  + 贝斯 28 脉冲渐入(m2 起,8分,vel 50→78)
  + m2 第 4 拍 crash 爆炸 + kick 重击,直入档1;CC11 30→60。
Outro (m19-20):m19 crash 爆炸 + 全停(仅 1 个 crash 长音 + 低音尾音 28);
  m20 低音 28 长音渐弱(CC11 60→20)+ 军鼓轻击 1 次收束。
角色:'drums'(ch9)、'bass_electric'(ch6);通道由总装注册绑定,层内直接用角色名。
"""
import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS


def build_intro(s, bar0, ch):
    """m1-2:滚奏渐强 → 贝斯脉冲渐入 → m2 第 4 拍镲爆直入档1。返回 bar0+2。"""
    base = (bar0 - 1) * 4

    def B(b):
        return base + b

    # m1: 军鼓 16分渐强滚奏(vel 30→70),连续滚至 m2 第 4 拍爆炸前
    s.cc('drums', 11, 30, B(0.0))
    s.cc('drums', 11, 60, B(4.0))
    s.roll('drums', 38, 30, 70, B(0.0), B(7.0), 0.25)

    # m2: 贝斯 28 脉冲渐入(8分,vel 50→78,第 4 拍让位给爆炸)
    for j in range(6):
        b = 4.0 + j * 0.5
        v = int(50 + (78 - 50) * (j / 5.0))
        s.note('bass_electric', 28, v, B(b), 0.35)

    # m2 第 4 拍:crash 爆炸 + kick 重击,直入档1
    s.note('drums', 49, 88, B(7.0), 0.7)   # 短促爆炸,让位给档1起点 crash
    s.note('drums', 36, 90, B(7.0), 0.3)
    return bar0 + 2


def build_outro(s, bar0, ch):
    """m19-20:镲爆炸全停 → 低音长音渐弱 + 军鼓轻击收束。返回 bar0+2。"""
    base = (bar0 - 1) * 4

    def B(b):
        return base + b

    # m19: crash 爆炸 + 全停,仅 crash 长音 + 低音尾音 28
    s.cc('drums', 11, 60, B(0.0))
    s.note('drums', 49, 90, B(0.0), 2.5)
    s.note('bass_electric', 28, 80, B(0.0), 2.5)

    # m20: 低音 28 长音渐弱(CC11 60→20,锚点防提前衰减),军鼓轻击 1 次收束
    s.cc('drums', 11, 60, B(4.0))
    s.cc('drums', 11, 20, B(8.0))
    s.note('bass_electric', 28, 60, B(4.0), 4.0)
    s.note('drums', 38, 55, B(7.5), 0.2)
    return bar0 + 2


if __name__ == '__main__':
    ch = {'drums': 9, 'bass_electric': 6, 'timpani': 11}
    s = Score()
    for name, c in (('drums', ch['drums']), ('bass_electric', ch['bass_electric'])):
        bank, prog, (lo, hi), pan, rev = PROGS[name]
        s.add_instr(name, c, bank, prog, lo, hi, pan, rev)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        build_intro(s, 1, ch)
        build_outro(s, 19, ch)
        s.flush('/tmp/smk_intro_outro.mid')
    out = buf.getvalue()
    print(out)
    bad = out.count('[音区告警]') + out.count('[冲突]')
    print(f'smoke intro_outro: {"PASS" if bad == 0 else "FAIL"} (issues={bad})')
    sys.exit(0 if bad == 0 else 1)
