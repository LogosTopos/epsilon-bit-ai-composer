#!/usr/bin/env python3
"""build_loop.py — 《搜打撤》无缝大循环成品(可单曲循环 100 遍,2026-08-05 设计)

目标:一首 3 分半的完整曲子,首尾无缝衔接(循环点两侧 = 两个相同小节),
每遍循环有微变(遍间轮转),能量弧完整(搜刮→集结→战斗→时停→再战→绝境→
冲刺→尘埃落定→回搜刮)。

## 无缝原理(与 demo_playthrough 的线性叙事不同)
1. 和声连续:全部段落共享 Em-C-G-D 16 小节骨架,任何两段相接都是
   Em(m16) → Em(m1) 零突变(母节回环边界本身)。
2. 循环预伏:最后用 loop_return(2 小节)回 S1——其末小节逐字复刻 S1 首小节,
   循环点两侧为两个相同小节,接缝不可察觉。
3. 能量藏缝:循环点落在整曲能量最低处(S6 余烬 → S1 低能量),接缝最不引人注意。
4. 遍间轮转(--cycle N):母节两段 cycle 互换、S-BT 晶体 cycle1、S5 bass plan
   cycle1——第 N 遍与前一遍有 1-2 处不同,循环不腻。

## 结构(140 小节 ≈ 3:20,能量弧)
  S1 搜刮(低) →riser→ S2 警觉(中低) →riser→ 母节 c1(高) →time_fold→
  S-BT 时停(中低) →time_unfold→ 母节 c2(高+) →riser→ S4 绝境 v2(高) →roll32→
  S5 冲刺 176(最高) →crash_stop(168 回写)→ S6 尘埃落定(低) →loop_return→ (回 S1)

用法:
  python3 sections/build_loop.py                # cycle 0(默认)
  python3 sections/build_loop.py --cycle 1      # 遍间轮转变体
运行前先清 __pycache__(缓存纪律)。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS
import compose                                   # ROLE_CH(唯一通道表来源)
import sections.transitions as T
import sections.s1_scavenge as S1
import sections.s2_explore as S2
import sections.s_bt as SBT
import sections.s4_crisis_v2 as S4
import sections.s5_extract_v2 as S5
import sections.s6_calm as S6
import layers.drums as L_drums
import layers.bass_harmony as L_bass
import layers.riff_texture as L_riff

ROLE_CH = compose.ROLE_CH

# 大循环规划表:(区块名, 类型, 小节数, BPM)。类型 → 组装函数。
# 转场逐一与 TRANSITIONS 衔接矩阵交叉校验(不一致即断言失败)。
STEPS = [
    ('S1 搜刮',          'S1',          16, 168),
    ('riser S1->S2',     'riser',        2, 168),
    ('S2 警觉',          'S2',          16, 168),
    ('riser S2->S3',     'riser',        2, 168),
    ('S3 母节 c1',       'S3',          16, 168),
    ('time_fold S3->S-BT', 'time_fold',  1, 168),
    ('S-BT 子弹时间',    'S-BT',        16, 168),
    ('time_unfold S-BT->S3', 'time_unfold', 1, 168),
    ('S3 母节 c2',       'S3',          16, 168),
    ('riser S3->S4',     'riser',        2, 168),
    ('S4 绝境 v2',       'S4',          16, 168),
    ('roll32 S4->S5',    'roll32',       1, 168),
    ('S5 冲刺(176)',     'S5',          16, 176),
    ('crash_stop S5->S6', 'crash_stop',  1, 168),
    ('S6 尘埃落定',      'S6',          16, 168),
    ('loop_return S6->S1', 'loop_return', 2, 168),
]

# 与衔接矩阵的交叉校验(大循环用到的每条衔接必须等于矩阵推荐元素)
_MATRIX_CHECK = [
    ('S1', 'S2', 'riser'), ('S2', 'S3', 'riser'), ('S3', 'S-BT', 'time_fold'),
    ('S-BT', 'S3', 'time_unfold'), ('S3', 'S4', 'riser'), ('S4', 'S5', 'roll32'),
    ('S5', 'S6', 'crash_stop'), ('S6', 'S1', 'loop_return'),
]


def _mother(s, bar0, cycle):
    """S3(母节)由三层 build 直接组装(compose.py 同款调用方式)。"""
    for layer in (L_drums, L_bass, L_riff):
        layer.build(s, bar0, cycle, ROLE_CH)
    return bar0 + 16


def _run_step(s, b, kind, s3_cycles, loop_cycle):
    """按类型执行一步组装,返回新的小节游标。"""
    if kind == 'S1':
        return S1.build(s, b, 0, ROLE_CH)
    if kind == 'S2':
        return S2.build(s, b, 0, ROLE_CH)
    if kind == 'S3':
        return _mother(s, b, s3_cycles.pop(0))
    if kind == 'S-BT':
        return SBT.build(s, b, 1 if loop_cycle % 2 else 0, ROLE_CH)
    if kind == 'S4':
        return S4.build(s, b, 0, ROLE_CH)
    if kind == 'S5':
        return S5.build(s, b, 1 if loop_cycle % 2 else 0, ROLE_CH)  # 176 由 build 内部写 tempo
    if kind == 'S6':
        return S6.build(s, b, 0, ROLE_CH)
    if kind == 'riser':
        return T.riser(s, b, ROLE_CH, chord='Em')
    if kind == 'time_fold':
        return T.time_fold(s, b, ROLE_CH, chord='Em')
    if kind == 'time_unfold':
        return T.time_unfold(s, b, ROLE_CH)
    if kind == 'roll32':
        return T.roll32(s, b, ROLE_CH)
    if kind == 'crash_stop':
        return T.crash_stop(s, b, ROLE_CH, tempo=168, chord='Em')
    if kind == 'loop_return':
        return T.loop_return(s, b, ROLE_CH)
    raise ValueError(f'loop: 未知步骤类型 {kind}')


def build_loop(s, loop_cycle=0):
    """按 STEPS 组装无缝大循环,返回小节跨度表(与实际打印同源)。"""
    for frm, to, element in _MATRIX_CHECK:
        rec = T.TRANSITIONS[(frm, to)]
        assert rec[0] == element, f'loop: 矩阵要求 {frm}->{to} 用 {rec[0]},实际 {element}'
    L_riff.VOICE_BOOST = 6                     # 合成器嗓力度补偿(compose --voice synth 口径)
    s.tempo(168, 0.0)
    b = 3                                      # 对齐母节惯例:m1-2 留白,从 m3 起
    spans = []
    # 遍间轮转:cycle 奇数 → 母节两段互换(先 c1 后 c0)+ S-BT/S5 用 cycle1 变体
    s3_cycles = [1, 0] if loop_cycle % 2 else [0, 1]
    for label, kind, n, bpm in STEPS:
        spans.append((label, b, n, bpm))
        b = _run_step(s, b, kind, s3_cycles, loop_cycle)
    return spans


def print_plan(spans):
    total = 0.0
    print('=== 结构(Combat_Extraction_Loop.mid,无缝大循环)===')
    print(f'  {"区块":<18}{"小节范围":<12}{"小节":>4}{"BPM":>6}{"时长":>9}')
    for label, b, n, bpm in spans:
        dur = n * 4 / bpm * 60
        total += dur
        print(f'  {label:<18}{b:>3}-{b+n-1:<8}{n:>4}{bpm:>6}{dur:>8.1f}s')
    print(f'  总时长 ≈ {total:.0f}s(循环点:末小节与首小节同内容,无缝)')


if __name__ == '__main__':
    import contextlib, io
    loop_cycle = 0
    if '--cycle' in sys.argv:
        loop_cycle = int(sys.argv[sys.argv.index('--cycle') + 1])
    s = Score(humanize=True, seed=42)
    for role, chn in ROLE_CH.items():
        if role == 'hook':                     # 合成器嗓(主成品口径,compose.py 同款)
            bank, prog, (lo, hi), pan, rev = PROGS['synth_lead']
        else:
            bank, prog, (lo, hi), pan, rev = PROGS[role]
        s.add_instr(role, chn, bank, prog, lo, hi, pan, rev)
        s.cc(role, 7, 100, 0.0)
    s.tempo(168, 0.0)
    spans = build_loop(s, loop_cycle)
    print_plan(spans)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        s.flush('Combat_Extraction_Loop.mid')
    out = buf.getvalue()
    bad = out.count('[音区告警]') + out.count('  [冲突]')
    print(out, end='')
    print(f'LOOP 冒烟: {"PASS" if bad == 0 else "FAIL"} Combat_Extraction_Loop.mid'
          f'(cycle={loop_cycle}, 告警+冲突 = {bad})')
    sys.exit(0 if bad == 0 else 1)
