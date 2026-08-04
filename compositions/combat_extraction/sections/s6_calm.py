#!/usr/bin/env python3
"""s6_calm.py — 子节 6:《结算平静版》(撤离成功,淡出收束)

人格意象:「尘埃落定」——撤离成功,战斗能量全部退场,音乐如尘埃缓缓落地:
前 8 小节极轻巡逻(鼓最简:每 2 拍一颗心跳)→ 第 9 小节起打击乐全撤,只剩氛围与
低音脉动 → rel 11 的 D 和弦"融化"进 Em(长音重叠 1 拍)→ rel 12-15 和声停在 Em,
CC11 渐降淡出,最后 2 小节只剩 pad/choir 余韵 + 两声钢琴"余烬"。

依据:ARCHITECTURE §3 子节规范(S6 = S1 变体 + 和声停在 Em 长音 → 淡出)+ 用户指令(2026-08):
鼓可更轻(rel 8 起全撤)、Em 长音融化式淡出、最后 1-2 小节只剩余韵。

受控改动(相对母节 v9):
- 结构:16 小节 → 前 12 小节平静循环(Em-C-G-D),后 4 小节(rel 12-15)和声停在 Em
- hook/brass_stab/fx/synth_rhythm/timpani:整节全删(警戒/推进/冲击元素全撤)
- drums:满配 → 仅前 8 小节极轻巡逻(kick 每 2 拍 52 + snare 2/4 44 + hat 4 分 40),
  rel 8 起全撤(比原规格"前 12 小节"更轻——尘埃落定,打击乐随 CC11 下降提前退场)
- bass:前 12 小节 8 分根音脉冲(vel 66-74,句尾重音 80,每轮 bar4 句号长音);
  rel 12-13 每小节 1 个 E1 长音(3.5 拍,60);rel 14-15 撤(只剩余韵)
- strings/pad/choir:前 12 小节长音 36/28/32;rel 11 的 D 和弦延至 rel 12 内 1 拍
  (融化式重叠);rel 12-15 停在 Em 长音连奏(vel 每小节 -8 渐弱),
  rel 14-15 撤 strings 只留 pad/choir 余韵
- piano:前 12 小节 0.0 轻击(36);rel 14/15 各一声极轻"余烬"(E2,vel 20/16)
- vln1 回声:前 12 小节保留(vel 36,bar1/3 句尾);后 4 小节撤
- CC11:轮起点 74/74/60/36 + rel 15 落 30(后段渐降淡出——全曲唯一允许 <70 的段落)
- 与母节共享:前 12 小节网格 / Em-C-G-D 循环 / 168 BPM
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS

# 16 小节和弦序(与母节共享骨架:轮1 Em Em C D,轮2-4 Em C G D)
CHORDS16 = ('Em', 'Em', 'C', 'D', 'Em', 'C', 'G', 'D',
            'Em', 'C', 'G', 'D', 'Em', 'C', 'G', 'D')
FRONT = 12                                     # 前 12 小节平静段;rel 12-15 = Em 长音淡出

# 8 分根音脉冲(低把位根音,66-74 档;句尾重音 80;每轮 bar4 句号长音)
BASS_ROOT = {'Em': 28, 'C': 36, 'G': 31, 'D': 38}
BASS_VEL = (70, 70, 74, 70, 70, 74, 70, 80)
CC11_NODES = ((0, 74), (4, 74), (8, 60), (12, 36), (15, 30))   # 轮起点 + 尾落(淡出段)

# 弦乐和声堆叠(声部低→高:celli / vla / vln2 / vln1,母节 VOICES 原样)
VOICES = {
    'Em': (40, 64, 64, 71),
    'C':  (36, 64, 67, 72),
    'G':  (43, 62, 67, 71),
    'D':  (38, 62, 66, 69),
}
CHOIR_VOICE = {
    'Em': (52, 55, 64),
    'C':  (48, 52, 55),
    'G':  (55, 62, 67),
    'D':  (50, 54, 62),
}
PIANO_ROOT = {'Em': 40, 'C': 36, 'G': 43, 'D': 38}
ECHO_PAIR = {
    'Em': (64, 67),
    'C':  (64, 67),
    'G':  (62, 67),
}
ECHO_RELS = (0, 2, 4, 6, 8, 10)                # 前 12 小节 bar1/3 句尾

ROLE_CH = {'piano_bang': 0, 'synth_pad': 1, 'vln1': 2, 'vln2': 3, 'vla': 4,
           'celli': 5, 'bass_electric': 6, 'fx': 7, 'drums': 9, 'hook': 10,
           'timpani': 11, 'brass_stab': 12, 'keys': 13, 'choir': 14,
           'synth_rhythm': 15}


def build(s, bar0, cycle, ch):
    """铺 16 小节 S6(小节 = bar0 起),返回 bar0+16。"""
    B = 'bass_electric'
    V1, V2, VA, VC = 'vln1', 'vln2', 'vla', 'celli'
    P, PA, CHO = 'piano_bang', 'synth_pad', 'choir'

    def bt(bar):
        return (bar - 1) * 4

    # CC11:轮起点 74/74/60/36 + rel 15 落 30(interp 自动渐降,淡出段唯一允许 <70)
    for name in (B, V1, V2, VA, VC, P, PA, CHO, 'drums'):
        for rel, ccv in CC11_NODES:
            s.cc(name, 11, ccv, bt(bar0 + rel))

    # ---------------- drums:前 8 小节极轻巡逻(kick 每 2 拍 + snare 2/4 + hat 4分);rel 8 起全撤 ----------------
    for i in range(8):
        for b in (0.0, 2.0):
            s.note('drums', 36, 52, bt(bar0 + i) + b, 0.2)
        for b in (1.0, 3.0):
            s.note('drums', 38, 44, bt(bar0 + i) + b, 0.2)
        for b in (0.0, 1.0, 2.0, 3.0):
            s.note('drums', 42, 40, bt(bar0 + i) + b, 0.15)

    # ---------------- bass:前 12 小节 8 分根音脉冲(每轮 bar4 句号长音);rel 12-13 E1 长音 ----------------
    for i in range(FRONT):
        r = BASS_ROOT[CHORDS16[i]]
        for j in range(8):
            dur = 0.95 if (i % 4 == 3 and j == 7) else 0.45
            s.note(B, r, BASS_VEL[j], bt(bar0 + i) + j * 0.5, dur)
    for i in (12, 13):
        s.note(B, 28, 60, bt(bar0 + i), 3.5)   # E1 长音(3.5 拍,静待收束)

    # ---------------- 氛围层:前 12 小节长音;rel 11 D 和弦融化进 Em;rel 12-15 Em 连音渐弱 ----------------
    for i in range(FRONT):
        prog = CHORDS16[i]
        c, v3, v5, r1 = VOICES[prog]
        dur = 5.0 if i == 11 else 3.9          # rel 11:D 和弦延 1 拍进 rel 12(融化)
        for name, pitch in ((VC, c), (VA, v3), (V2, v5), (V1, r1)):
            s.note(name, pitch, 36, bt(bar0 + i), dur)
        s.chord(PA, CHOIR_VOICE[prog], 28, bt(bar0 + i), dur)
        s.chord(CHO, CHOIR_VOICE[prog], 32, bt(bar0 + i), dur)
        s.note(P, PIANO_ROOT[prog], 36, bt(bar0 + i), 0.3)
        if i in ECHO_RELS:                     # vln1 回声(bar1/3 句尾)
            p0, p1 = ECHO_PAIR[prog]
            s.note(V1, p0, 36, bt(bar0 + i) + 3.5, 0.2)
            s.note(V1, p1, 36, bt(bar0 + i) + 3.75, 0.2)
    # 后 4 小节:Em 长音连奏(dur 4.0 无隙),vel 每小节 -8 渐弱;
    # rel 14-15 撤 strings,只剩 pad/choir 余韵
    c, v3, v5, r1 = VOICES['Em']
    for k, i in enumerate(range(12, 16)):
        if k < 2:                              # rel 12-13:全组
            for name, pitch in ((VC, c), (VA, v3), (V2, v5), (V1, r1)):
                s.note(name, pitch, 36 - k * 8, bt(bar0 + i), 4.0)
        s.chord(PA, CHOIR_VOICE['Em'], 28 - k * 8, bt(bar0 + i), 4.0)
        s.chord(CHO, CHOIR_VOICE['Em'], 32 - k * 8, bt(bar0 + i), 4.0)
    # 钢琴余烬(最后 2 小节,极轻 E2)
    s.note(P, 40, 20, bt(bar0 + 14) + 3.0, 0.25)
    s.note(P, 40, 16, bt(bar0 + 15) + 3.5, 0.25)

    return bar0 + 16


if __name__ == '__main__':
    import contextlib, io
    USED = ('drums', 'bass_electric', 'vln1', 'vln2', 'vla', 'celli',
            'synth_pad', 'choir', 'piano_bang')
    s = Score(humanize=True, seed=42)
    for role in USED:
        bank, prog, (lo, hi), pan, rev = PROGS[role]
        s.add_instr(role, ROLE_CH[role], bank, prog, lo, hi, pan, rev)
        s.cc(role, 7, 100, 0.0)
    s.tempo(168, 0.0)
    assert build(s, 3, 0, ROLE_CH) == 19
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        s.flush('S6_Calm.mid')
    out = buf.getvalue()
    print(out, end='')
    bad = out.count('[音区告警]') + out.count('  [冲突]')
    print(f'S6 冒烟: {"PASS" if bad == 0 else "FAIL"} S6_Calm.mid(音区告警/自检冲突 = {bad})')
    sys.exit(0 if bad == 0 else 1)
