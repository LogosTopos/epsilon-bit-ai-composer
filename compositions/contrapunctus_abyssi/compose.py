#!/usr/bin/env python3
"""compose.py v2 — 《深渊对位 / Contrapunctus Abyssi》(~5:30,单乐章)

v2 重写目标(依据用户反馈"更流畅、自然、和谐"与编曲问题回顾):
1. 和声层:上方和声跟随固定低音做**声部连接**(共同音保持/就近移动),每 2 拍一个
   功能性和弦(i/V7/viio6-5/VI/bII),转位常态化 —— 消灭"低音乱跑、和声钉住"
2. 结构:帕萨卡利亚 11×4 小块 → **3 大组连续演化**(弦乐室内 → 木管进入 →
   铜管+打击乐推进),织体渐变衔接而非切换;高潮 4→8 小节带渐强阶梯
3. 材料:新增对比主题 T2(抒情大跳)与性格化对题 CS2(延留/回转),替代八分音阶跑动
4. 配器:乐器角色化(长笛=高音持续、双簧管=中音独奏、圆号=和声支撑、巴松=低音八度、
   定音鼓=组C至尾声持续律动),不再"出场一次即弃"
5. 速度:54→72→84→96→104→72 全部渐变(tempo_ramp),CC11 乐句级节点
6. 保留:深渊动机 X、帕萨卡利亚+赋格双结构、赋格主题=T1、密接和应、皮卡迪尾声
"""
import argparse
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.orch import Score, CH, PROGS

BPB = 4
B = lambda n: (n - 1) * BPB

# ================= 主题材料 =================

# 主题 T1(4 小节,d 小调):X 头 + 级进上行 + 回转回落 + 抒情收束
# 附点与长音给予呼吸感(原版全是均匀四分)
T1 = [
    (0, 74, 1.5), (1.5, 73, 0.5), (2.0, 69, 2.0),                      # X 头
    (4, 71, 1.0), (5, 72, 0.5), (5.5, 74, 0.5), (6, 76, 1.0), (7, 77, 1.0),   # 级进上行
    (8, 76, 1.5), (9.5, 74, 0.5), (10, 72, 1.0), (11, 74, 1.0),        # 回转回落
    (12, 71, 1.5), (13.5, 72, 0.5), (14, 69, 2.0),                     # 收束
]
ANS = [(b, p - 5, d) for b, p, d in T1]   # 答题(五度下)

# 对题 CS2(4 小节):延留 + 回转,性格化(原版是八分音阶跑动)
CS2 = [
    (0, 55, 1.5), (1.5, 57, 0.5), (2.0, 59, 1.0), (3.0, 57, 1.0),      # 延留 55→57
    (4, 60, 1.5), (5.5, 62, 0.5), (6.0, 64, 1.0), (7.0, 62, 1.0),
    (8, 65, 1.0), (9, 64, 0.5), (9.5, 62, 0.5), (10, 60, 1.5), (11.5, 59, 0.5),  # 回转
    (12, 57, 1.0), (13, 59, 1.0), (14, 55, 2.0),
]
CS2_LOW = [(b, p - 7, d) for b, p, d in CS2]

# 对比主题 T2(4 小节,F 大调,抒情):上行五度大跳 + 弧线回落,用于间插段
T2 = [
    (0, 72, 1.5), (1.5, 77, 1.5), (3.0, 76, 1.0),
    (4, 74, 1.5), (5.5, 72, 0.5), (6.0, 69, 1.0), (7.0, 71, 1.0),
    (8, 72, 1.0), (9, 74, 1.0), (10, 76, 1.5), (11.5, 77, 0.5),
    (12, 76, 1.0), (13, 74, 1.0), (14, 72, 1.5), (15.5, 69, 0.5),
]

# 双簧管对位 CM2(帕萨卡利亚 A 组,色彩音 E/F 强调)
CM2 = [
    (0, 76, 1.0), (1, 77, 1.0), (2, 74, 0.5), (2.5, 72, 0.5), (3, 71, 1.0),
    (4, 72, 1.5), (5.5, 74, 0.5), (6, 77, 1.0), (7, 76, 1.0),
    (8, 74, 1.0), (9, 72, 0.5), (9.5, 71, 0.5), (10, 69, 1.5), (11.5, 71, 0.5),
    (12, 72, 1.0), (13, 71, 1.0), (14, 69, 2.0),
]

# 圣咏旋律(尾声,D 大调,16 小节,平滑级进)
CHORALE = [
    (0, 62, 2.0), (2, 61, 1.0), (3, 57, 1.0), (4, 59, 2.0), (6, 61, 1.0), (7, 62, 1.0),
    (8, 64, 2.0), (10, 62, 1.0), (11, 61, 1.0), (12, 62, 2.0), (14, 59, 1.0), (15, 57, 1.0),
    (16, 66, 2.0), (18, 64, 1.0), (19, 62, 1.0), (20, 64, 2.0), (22, 62, 1.0), (23, 61, 1.0),
    (24, 66, 2.0), (26, 64, 1.0), (27, 62, 1.0), (28, 61, 2.0), (30, 59, 1.0), (31, 57, 1.0),
    (32, 62, 2.0), (34, 61, 1.0), (35, 57, 1.0), (36, 59, 2.0), (38, 57, 1.0), (39, 66, 1.0),
    (40, 66, 2.0), (42, 64, 1.0), (43, 62, 1.0), (44, 62, 4.0),
]

# ================= 帕萨卡利亚固定低音 =================
# 结构: X 头(D-C#-A)+ lamento(Bb-A-G)+ 半音(Eb-D-C#)+ 收束(D-A-D)
GROUND = {
    'Dm': [38, 37, 33, 33, 34, 33, 31, 31, 39, 38, 37, 37, 38, 33, 38, 38],
    'F':  [41, 40, 36, 36, 38, 36, 34, 34, 32, 31, 30, 30, 31, 38, 31, 31],
    'Gm': [43, 42, 38, 38, 39, 38, 36, 36, 34, 33, 32, 32, 33, 40, 33, 33],
    'Eb': [39, 38, 34, 34, 35, 34, 32, 32, 30, 29, 28, 28, 39, 34, 39, 39],
    'A7': [33, 32, 28, 28, 29, 28, 38, 38, 34, 33, 32, 32, 33, 28, 33, 33],
    'E':  [40, 39, 35, 35, 36, 35, 33, 33, 42, 40, 39, 39, 40, 35, 40, 40],
}

# 转调偏移(Dm 为 0)
KEY_DELTA = {'Dm': 0, 'F': 3, 'Gm': 5, 'Eb': 1, 'A7': -5, 'E': 2}

# ================= 和声模板(每 2 个低音音一个和弦 = 每周期 8 和弦) =================
# 每项 = 上声部候选音高:固定低音 + 功能性和声,候选供声部连接器选择
# 功能设计(对应低音分组):
#   [D,C#] i → [A,A] V7 → [Bb,A] VI → [G,G] i → [Eb,D] bII → [C#,C#] V6/5 → [D,A] i → [D,D] i
HARM_TEMPLATE = [
    [45, 50, 53, 57, 62],      # i        D-F-A
    [45, 52, 55, 60],          # V7       A-C#-E-G
    [50, 53, 58],              # VI       Bb-D-F
    [43, 46, 50, 55],          # i        G-Bb-D
    [46, 51, 55, 58],          # bII      Eb-G-Bb
    [52, 55, 57, 60],          # V6/5     C#-E-G-A
    [45, 50, 53, 57, 62],      # i        D-F-A
    [50, 53, 57, 62],          # i(收)    D-F-A-D
]

# 尾声圣咏和声(D 大调:旋律音 → 三和弦),供四部和声连接
FIN_CHORDS = {62: (62, 66, 69), 61: (61, 64, 68), 57: (57, 61, 64), 59: (59, 62, 66),
              64: (64, 67, 71), 66: (66, 69, 73)}


def harmony_for(key):
    """返回该调性固定低音周期的 8 个和弦 [(低音, 候选上声部), ...](每 2 个低音音一个)"""
    d = KEY_DELTA[key]
    ground = GROUND[key]
    return [(ground[2 * i], [p + d for p in cands])
            for i, cands in enumerate(HARM_TEMPLATE)]


def connect(harm, n_voices=3, ranges=None):
    """声部连接器:为每和弦从上声部候选中选 n_voices 个,使相邻和弦移动最小。
    贪心最近移动(先选共同音/最近音),保证声部平滑 —— "和谐"的工程保证。
    harm: [(低音, 候选上声部列表), ...];ranges: 每声部 (lo, hi) 钳制。
    返回 [(低音, [v0..vn-1]), ...]
    """
    if ranges is None:
        ranges = [(48, 96)] * n_voices
    prev = None
    out = []
    for bass, cands in harm:
        cands = sorted(set(cands))
        if len(cands) < n_voices:
            # 补八度
            c0 = list(cands)
            k = 0
            while len(c0) < n_voices:
                c0.append(c0[k] + 12)
                k += 1
            cands = sorted(set(c0))
        if prev is None:
            # 首和弦:取中间 n_voices 个
            sel = cands[len(cands) // 2 - n_voices // 2: len(cands) // 2 - n_voices // 2 + n_voices]
            if len(sel) < n_voices:
                sel = cands[:n_voices]
        else:
            best, best_cost = None, None
            from itertools import combinations
            for combo in combinations(cands, n_voices):
                c = sorted(combo)
                cost = sum(abs(a - b) for a, b in zip(c, prev))
                if best_cost is None or cost < best_cost:
                    best, best_cost = c, cost
            sel = best
        # 音区钳制
        sel = list(sel)
        for i in range(n_voices):
            lo, hi = ranges[i]
            while sel[i] < lo:
                sel[i] += 12
            while sel[i] > hi:
                sel[i] -= 12
        prev = sorted(sel)
        out.append((bass, prev))
    return out


def T(seq, semis):
    return [(b, p + semis, d) for b, p, d in seq]


def ground_bar(s, low_name, high_name, ground, vel, bar0, oct_up=0):
    """固定低音 + 高八度强化(每拍一个)"""
    for i, p in enumerate(ground):
        s.note(low_name, p, vel, B(bar0) + i, 0.92)
        if high_name:
            s.note(high_name, p + 12 + oct_up, vel - 4, B(bar0) + i, 0.92)


def harmony_block(s, harm, vnames, vels, bar0, beats_per_chord=2):
    """按声部连接结果铺和声长音(每和弦 beats_per_chord 拍)"""
    n = len(harm)
    for ci, (bass, voices) in enumerate(harm):
        t = B(bar0) + ci * beats_per_chord
        for vi, (name, vel) in enumerate(zip(vnames, vels)):
            if vi < len(voices):
                s.note(name, voices[vi], vel, t, beats_per_chord - 0.05)


# ================= 主结构 =================

def build(s: Score):
    regs = [
        ('bell', CH['piano'], *PROGS['church_bell']),
        ('harp', CH['harp'], *PROGS['harp']),
        ('vln1', CH['vln1'], *PROGS['vln1_slow']),
        ('vln2', CH['vln2'], *PROGS['vln2_slow']),
        ('vla', CH['vla'], *PROGS['vla_slow']),
        ('celli', CH['celli'], *PROGS['celli_slow']),
        ('bass', CH['bass'], *PROGS['bass_slow']),
        ('flute', CH['flute'], *PROGS['flute']),
        ('oboe', CH['oboe'], *PROGS['oboe']),
        ('clarinet', CH['clarinet'], *PROGS['clarinet']),
        ('bassoon', CH['clarinet'], *PROGS['bassoon']),
        ('drums', CH['drums'], 128, 48, (0, 127), 64, 30),
        ('timpani', CH['timpani'], *PROGS['timpani']),
        ('horn', CH['horns'], *PROGS['horn']),
        ('trumpet', CH['brass'], *PROGS['trumpet']),
        ('hmn_trumpet', CH['brass'], *PROGS['hmn_trumpet']),
        ('trombone', CH['brass'], *PROGS['trombone']),
        ('tuba', CH['brass'], *PROGS['tuba']),
        ('choir', CH['choir'], *PROGS['choir']),
        ('organ', CH['keys'], *PROGS['organ']),
        ('celesta', CH['keys'], *PROGS['celesta']),
        ('glock', CH['keys'], *PROGS['glock']),
    ]
    for name, ch, bank, prog, (lo, hi), pan, rev in regs:
        s.add_instr(name, ch, bank, prog, lo, hi, pan, rev)
        s.cc(name, 7, 100, 0.0)
    s.cc('timpani', 7, 88, 0.0)
    s.cc('drums', 7, 96, 0.0)

    def dyn(inst, v, bar_n):
        s.cc(inst, 11, v, B(bar_n))

    # 速度(全程渐变,不硬切)
    s.tempo(54, B(1))
    s.tempo_ramp(54, 72, B(6), B(9), steps=5)     # 引子 → 帕萨卡利亚
    s.tempo(72, B(9))
    s.tempo_ramp(72, 84, B(44), B(45), steps=3)   # 帕萨卡利亚 → 间插段
    s.tempo(84, B(45))
    s.tempo_ramp(84, 96, B(48), B(49), steps=3)   # 间插段 → 赋格
    s.tempo(96, B(49))
    s.tempo_ramp(96, 104, B(84), B(85), steps=3)  # 赋格 → 高潮
    s.tempo(104, B(85))
    s.tempo_ramp(104, 72, B(91), B(93), steps=4)  # 高潮 → 尾声

    # ---------------- 引子(m1-8,@54,安静) ----------------
    for n in (1, 5):
        s.note('bass', 38, 40, B(n), 7.0)
        s.chord('organ', (38, 50), 38, B(n), 7.0)
        s.note('bell', 74, 44, B(n), 3.0)
    # X 碎片缓慢呈现(大提)
    for t, p, d in [(B(1), 62, 1.5), (B(1) + 1.5, 61, 0.5), (B(1) + 2.0, 57, 1.5),
                    (B(3), 62, 2.0), (B(5), 74, 1.5), (B(5) + 1.5, 73, 0.5), (B(5) + 2.0, 69, 2.0)]:
        s.note('celli', p, 56, t, d)
    s.arp('harp', (62, 65, 69, 74), 40, B(1) + 3, 0.5, 2, 1.0)
    s.roll('timpani', 38, 24, 34, B(7), B(9), step=0.5)
    # 主题头预示(一提,m7-8)
    for t, p, d in [(B(7), 74, 1.5), (B(7) + 1.5, 73, 0.5), (B(7) + 2.0, 69, 2.0)]:
        s.note('vln1', p, 58, t, d)
    dyn('bass', 28, 1); dyn('organ', 26, 1); dyn('celli', 32, 1); dyn('vln1', 30, 7)
    dyn('timpani', 20, 7)

    # ---------------- 帕萨卡利亚 A 组(m9-20,@72,弦乐室内) ----------------
    # 周期 1(9-12):大提低音 + 中提/二提和声 + 一提主题
    harm = connect(harmony_for('Dm'), n_voices=2, ranges=[(48, 74), (60, 88)])
    for cyc in range(3):
        bar0 = 9 + cyc * 4
        key = ['Dm', 'Dm', 'Dm'][cyc]
        harm = connect(harmony_for(key), n_voices=2, ranges=[(48, 74), (60, 88)])
        if cyc == 0:
            ground_bar(s, 'bass', 'celli', GROUND[key], 56, bar0)   # Dm 低音低至 G1
            harmony_block(s, harm, ['vla', 'vln2'], [48, 50], bar0)
            for t, p, d in T1:
                s.note('vln1', p, 88, B(bar0) + t, d)
            s.arp('harp', (62, 65, 69, 74), 42, B(bar0), 0.5, 2, 2.0)
        elif cyc == 1:
            # 木管轻描:双簧管对位 + 一提主题加花(附点化)
            ground_bar(s, 'bass', 'celli', GROUND[key], 56, bar0)
            harmony_block(s, harm, ['vla', 'vln2'], [48, 50], bar0)
            for t, p, d in T(CM2, 0):
                s.note('oboe', p, 74, B(bar0) + t, d)
            for t, p, d in T1:
                if d >= 1.5:
                    s.note('vln1', p, 86, B(bar0) + t, d)
                else:
                    s.note('vln1', p, 86, B(bar0) + t, d * 0.75)
            s.arp('harp', (62, 65, 69, 74), 44, B(bar0), 0.5, 2, 2.0)
        else:
            # 长笛高八度主题 + 一提对位 + 中提震音和声
            s.prog('vla', *PROGS['vla_trem'][:2], B(bar0))
            ground_bar(s, 'bass', 'celli', GROUND[key], 58, bar0)
            harmony_block(s, harm, ['vla', 'vln2'], [46, 50], bar0)
            for t, p, d in T(T1, 12):
                s.note('flute', p, 78, B(bar0) + t, d)
            for t, p, d in T(CM2, 0):
                s.note('vln1', p, 74, B(bar0) + t, d)
            s.note('celesta', 86, 46, B(bar0) + 2, 1.0)
            s.note('celesta', 89, 46, B(bar0) + 4, 1.0)
    for bn, v in [(9, 48), (13, 50), (17, 54)]:
        dyn('vln1', v + 6, bn); dyn('celli', v - 4, bn); dyn('vla', v - 4, bn)
        dyn('vln2', v - 4, bn)
    dyn('oboe', 48, 13); dyn('flute', 50, 17); dyn('bassoon', 48, 17)

    # ---------------- 帕萨卡利亚 B 组(m21-32,木管角色化,转调) ----------------
    # 周期 1(21-24,F):长笛主题 + 双簧管对位 + 巴松低音八度
    harm = connect(harmony_for('F'), n_voices=2, ranges=[(48, 74), (60, 88)])
    for i, p in enumerate(GROUND['F']):     # F 低音低至 G1:巴松低于音区自动高八度
        s.note('bassoon', p if p >= 34 else p + 12, 52, B(21) + i, 0.92)
        s.note('bass', p + 12, 56, B(21) + i, 0.92)
    harmony_block(s, harm, ['vla', 'vln2'], [46, 48], 21)
    for t, p, d in T(T1, 3):
        s.note('flute', p + 12, 80, B(21) + t, d)
    for t, p, d in T(CM2, -5):
        s.note('oboe', p, 70, B(21) + t, d)
    s.arp('harp', (65, 69, 72, 77), 44, B(21), 0.5, 2, 2.0)

    # 周期 2(25-28,Gm):中提主题(移调)+ 弦乐震音 + 巴松对位
    s.prog('vln1', *PROGS['vln1_trem'][:2], B(25))
    s.prog('vln2', *PROGS['vln2_trem'][:2], B(25))
    s.prog('vla', *PROGS['vla_slow'][:2], B(25))
    harm = connect(harmony_for('Gm'), n_voices=2, ranges=[(48, 74), (60, 88)])
    ground_bar(s, 'bass', 'celli', GROUND['Gm'], 56, 25)   # Gm 低音低至 F2,大提高八度
    harmony_block(s, harm, ['vla', 'vln2'], [46, 48], 25)
    for t, p, d in T(T1, -5):
        s.note('vla', p, 82, B(25) + t, d)
    for t, p, d in T(CS2, -7):
        s.note('bassoon', p + 7, 64, B(25) + t, d)
    for n in range(25, 29):
        s.chord('vln1', (55, 58, 62), 42, B(n), 4.0)
    s.prog('vln1', *PROGS['vln1_slow'][:2], B(29))

    # 周期 3(29-32,Eb):一提主题 + 长笛装饰 + 竖琴密集琶音,渐强引出 C 组
    s.prog('vla', *PROGS['vla_trem'][:2], B(29))
    harm = connect(harmony_for('Eb'), n_voices=2, ranges=[(48, 74), (60, 88)])
    ground_bar(s, 'bass', 'celli', GROUND['Eb'], 58, 29)   # Eb 低音低至 E1,大提高八度
    harmony_block(s, harm, ['vla', 'vln2'], [46, 48], 29)
    for t, p, d in T(T1, -11):
        s.note('vln1', p, 88, B(29) + t, d)
    for t, p, d in T(CM2, -3):
        s.note('flute', p, 66, B(29) + t, d)
    s.arp('harp', (63, 67, 70, 75), 46, B(29), 0.5, 2, 1.0)
    s.arp('harp', (63, 67, 70, 75), 48, B(31), 0.5, 2, 1.0)
    for bn, v in [(21, 50), (25, 54), (29, 58)]:
        dyn('vln1', v + 6, bn); dyn('celli', v - 4, bn); dyn('vla', v - 4, bn)
        dyn('vln2', v - 4, bn); dyn('bassoon', v - 6, bn); dyn('flute', v - 2, bn)

    # ---------------- 帕萨卡利亚 C 组(m33-44,铜管+打击乐,推进) ----------------
    # 周期 1(33-36,A7):弱音小号主题 + 圆号和声 + 定音鼓滚奏
    s.prog('vln1', *PROGS['vln1_trem'][:2], B(33))
    s.prog('vla', *PROGS['vla_slow'][:2], B(33))
    s.prog('hmn_trumpet', *PROGS['hmn_trumpet'][:2], B(33))
    s.prog('horn', *PROGS['horn'][:2], B(33))
    harm = connect(harmony_for('A7'), n_voices=2, ranges=[(48, 74), (60, 88)])
    ground_bar(s, 'bass', 'celli', GROUND['A7'], 58, 33)   # A7 低音低至 E1,大提高八度
    harmony_block(s, harm, ['vla', 'vln2'], [46, 48], 33)
    for t, p, d in T(T1, -5):
        s.note('hmn_trumpet', p, 84, B(33) + t, d)
    for n in range(33, 37):
        s.chord('horn', (57, 61, 64), 54, B(n), 4.0)
    s.roll('timpani', 45, 30, 50, B(33), B(37), step=0.5)

    # 周期 2(37-40,Dm):全奏初现(一提主题 + 小号/圆号和声 + 定音鼓)
    s.prog('vln1', *PROGS['vln1_slow'][:2], B(37))
    s.prog('trumpet', *PROGS['trumpet'][:2], B(37))
    harm = connect(harmony_for('Dm'), n_voices=2, ranges=[(48, 74), (60, 88)])
    ground_bar(s, 'bass', 'celli', GROUND['Dm'], 62, 37)
    harmony_block(s, harm, ['vla', 'vln2'], [48, 50], 37)
    for t, p, d in T1:
        s.note('vln1', p, 92, B(37) + t, d)
    for n in range(37, 41):
        s.chord('horn', (50, 57), 56, B(n), 4.0)
        s.chord('trumpet', (62, 66, 69), 50, B(n), 4.0)
    s.roll('timpani', 45, 40, 62, B(37), B(41), step=0.25)

    # 周期 3(41-44,Dm,渐强至 ff):大号低音 + 铜管全奏和声 + 打击乐
    s.prog('trombone', *PROGS['trombone'][:2], B(41))
    s.prog('tuba', *PROGS['tuba'][:2], B(41))
    harm = connect(harmony_for('Dm'), n_voices=2, ranges=[(48, 74), (60, 88)])
    ground_bar(s, 'tuba', 'bass', GROUND['Dm'], 66, 41)
    ground_bar(s, 'bass', 'celli', GROUND['Dm'], 58, 41)
    harmony_block(s, harm, ['vla', 'vln2'], [50, 52], 41)
    for t, p, d in T(T1, 12):
        s.note('vln1', p, 94, B(41) + t, d)
    for n in range(41, 45):
        s.chord('horn', (50, 57, 62), 60, B(n), 4.0)
        s.chord('trumpet', (62, 66, 69), 54, B(n), 4.0)
        s.chord('trombone', (41, 45, 50), 58, B(n), 4.0)
    s.roll('timpani', 45, 50, 80, B(41), B(45), step=0.25)
    s.note('drums', 49, 88, B(41), 1.5)     # 镲轻击
    s.note('drums', 36, 84, B(41), 0.6)     # 大鼓
    for bn, v in [(33, 56), (37, 64), (41, 72)]:
        dyn('vln1', v + 6, bn); dyn('celli', v - 4, bn); dyn('vla', v - 4, bn)
        dyn('vln2', v - 4, bn); dyn('timpani', v - 20, bn)
        dyn('horn', v - 6, bn); dyn('trumpet', v - 10, bn); dyn('tuba', v - 12, bn)

    # ---------------- 间插段(m45-48,@84,双簧管 T2 抒情) ----------------
    s.prog('vln1', *PROGS['vln1_slow'][:2], B(45))
    s.prog('vla', *PROGS['vla_slow'][:2], B(45))
    # 和声:F → Dm → Bb → A7(属准备)
    inter_harm = [(41, [48, 53, 57]), (38, [50, 53, 57]), (34, [46, 50, 53]), (33, [45, 52, 55, 60])]
    inter = connect(inter_harm, n_voices=3, ranges=[(48, 72), (60, 84), (69, 96)])
    for ci, (bass, voices) in enumerate(inter):
        t = B(45) + ci * 4
        for vi, name in enumerate(['vla', 'vln2', 'vln1']):
            s.note(name, voices[vi], 42 + vi * 4, t, 3.95)
        s.note('celli', bass + 12, 50, t, 3.95)
    for t, p, d in T2:
        s.note('oboe', p, 80, B(45) + t, d)
    s.arp('harp', (65, 69, 72, 77), 44, B(45), 0.5, 1, 1.0)
    s.arp('harp', (62, 65, 69, 74), 44, B(46), 0.5, 1, 1.0)
    s.arp('harp', (58, 62, 65, 70), 44, B(47), 0.5, 1, 1.0)
    for bn, v in [(45, 50), (47, 56)]:
        dyn('oboe', v, bn); dyn('vla', v - 8, bn); dyn('vln1', v - 10, bn)
        dyn('vln2', v - 10, bn); dyn('celli', v - 8, bn)

    # ---------------- 赋格(m49-80,@96) ----------------
    FUGUE_H = {49: 'Dm', 50: 'Dm', 51: 'A7', 52: 'Dm', 53: 'Am', 54: 'Am', 55: 'E7', 56: 'Am',
               57: 'Dm', 58: 'Dm', 59: 'A7', 60: 'Dm', 61: 'Am', 62: 'Am', 63: 'E7', 64: 'Am',
               65: 'Bb', 66: 'Bb', 67: 'Gm', 68: 'Gm', 69: 'Dm', 70: 'Dm', 71: 'A7', 72: 'A7',
               73: 'Am', 74: 'Am', 75: 'E7', 76: 'E7', 77: 'Eb', 78: 'Eb', 79: 'A7', 80: 'A7',
               81: 'Dm', 82: 'Dm', 83: 'A7', 84: 'A7'}
    ROOT = {'Dm': 38, 'F': 41, 'Gm': 43, 'Eb': 39, 'A7': 33, 'Am': 33, 'E7': 28,
            'D': 38, 'Bm': 35, 'G': 31, 'A': 33, 'Bb': 34}
    # 呈示期(49-64)纯四声部对位,不加和声(巴赫式);间插/进入期(65-76)加内声部长音
    fh = []
    for n in range(65, 77, 2):
        ch = FUGUE_H[n]
        fh.append((ROOT[ch], harmony_cands(ch)))
    fh_conn = connect(fh, n_voices=2, ranges=[(48, 74), (60, 84)])
    for i, (bass, voices) in enumerate(fh_conn):
        n = 65 + i * 2
        for vi, name in enumerate(['vla', 'vln2']):
            s.note(name, voices[vi], 40 + vi * 3, B(n), 1.95)
        s.note('celli', bass + 12, 50, B(n), 1.95)   # 骨架低音高八度(避开 E7/A7 根音区)
    # 进入 1:大提琴(主题,d,低八度)
    for t, p, d in T(T1, -12):
        s.note('celli', p, 86, B(49) + t, d)
    # 对题 1:大提琴
    for t, p, d in T(CS2_LOW, 0):
        s.note('celli', p + 12, 68, B(53) + t, d)
    # 进入 2:中提琴(答题,a)
    for t, p, d in T(ANS, -12):
        s.note('vla', p, 84, B(53) + t, d)
    # 对题 2:中提琴
    for t, p, d in T(CS2, -7):
        s.note('vla', p, 66, B(57) + t, d)
    # 进入 3:二提(主题,d)
    for t, p, d in T1:
        s.note('vln2', p, 86, B(57) + t, d)
    # 对题 3:二提
    for t, p, d in T(CS2, 0):
        s.note('vln2', p + 12, 66, B(61) + t, d)
    # 进入 4:一提(答题,a)
    for t, p, d in ANS:
        s.note('vln1', p, 88, B(61) + t, d)
    # 对题 4:一提
    for t, p, d in T(CS2, 0):
        s.note('vln1', p + 12, 68, B(65) + t, d)
    # 间插段 1(m65-68):对题材料模进对话(长笛/单簧管)
    s.prog('clarinet', *PROGS['clarinet'][:2], B(65))
    for t, p, d in T(CS2, 5):
        if t < 8:
            s.note('flute', p + 12, 72, B(65) + t, d)
    for t, p, d in T(CS2, 3):
        if t < 8:
            s.note('clarinet', p + 12, 70, B(67) + t, d)
    # 进入 5-6(m69-76):小号(主题,高八度)+ 大管(答题,低八度)+ 圆号(对题)
    s.prog('trumpet', *PROGS['trumpet'][:2], B(69))
    s.prog('bassoon', *PROGS['bassoon'][:2], B(69))
    s.prog('horn', *PROGS['horn'][:2], B(69))
    for t, p, d in T(T1, 12):
        s.note('trumpet', p, 84, B(69) + t, d)
    for t, p, d in T(T1, -12):
        s.note('bassoon', p, 76, B(69) + t, d)
    for t, p, d in T(CS2, -7):
        s.note('horn', p + 12, 70, B(73) + t, d)
    # 间插段 2(m77-80):X 碎片序列(Eb→A7)+ 震音渐强
    s.prog('vln1', *PROGS['vln1_trem'][:2], B(77))
    s.prog('vln2', *PROGS['vln2_trem'][:2], B(77))
    s.prog('vla', *PROGS['vla_trem'][:2], B(77))
    for t, p, d in [(B(77), 75, 1.5), (B(77) + 1.5, 74, 0.5), (B(77) + 2.0, 70, 0.5),
                    (B(77) + 2.5, 70, 0.5), (B(77) + 3.0, 72, 1.0),
                    (B(78), 73, 1.0), (B(78) + 1, 75, 1.0), (B(78) + 2, 77, 1.0),
                    (B(78) + 3, 78, 1.0)]:
        s.note('flute', p, 80, t, d)
    for t, p, d in [(B(79), 69, 1.5), (B(79) + 1.5, 68, 0.5), (B(79) + 2.0, 64, 0.5),
                    (B(79) + 2.5, 64, 0.5), (B(79) + 3.0, 66, 1.0),
                    (B(80), 67, 1.0), (B(80) + 1, 69, 1.0), (B(80) + 2, 71, 1.0),
                    (B(80) + 3, 72, 1.0)]:
        s.note('oboe', p, 82, t, d)
    s.roll('timpani', 33, 30, 60, B(79), B(81), step=0.25)
    for n in range(77, 81):
        s.chord('vln1', (57, 61, 64) if FUGUE_H[n] == 'A7' else (63, 67, 70), 44, B(n), 4.0)
        s.chord('vln2', (69, 73, 76), 42, B(n), 4.0)
        s.chord('vla', (57, 61, 64), 40, B(n), 4.0)
    for bn, v in [(49, 52), (53, 56), (57, 54), (61, 58), (65, 52), (69, 62), (73, 64), (77, 60), (79, 68)]:
        dyn('vln1', v, bn); dyn('vln2', v - 2, bn); dyn('vla', v - 4, bn)
        dyn('celli', v - 4, bn)
    dyn('flute', 48, 65); dyn('clarinet', 46, 67); dyn('bassoon', 52, 69)
    dyn('trumpet', 54, 69); dyn('horn', 50, 73); dyn('oboe', 56, 79)

    # ---------------- 密接和应(m81-84,@104,主题错 2 小节三层) ----------------
    s.prog('vln1', *PROGS['vln1_slow'][:2], B(81))
    s.prog('vln2', *PROGS['vln2_slow'][:2], B(81))
    s.prog('vla', *PROGS['vla_slow'][:2], B(81))
    for t, p, d in T1:                                       # 层 1:一提(主题)
        s.note('vln1', p, 92, B(81) + t, d)
    for t, p, d in T(ANS, 0):                                # 层 2:二提(答题,错 2 小节)
        s.note('vln2', p + 7, 86, B(83) + t, d)
    # 层 3:中提(主题,低八度,错 4 小节,仅头 2 小节)
    for t, p, d in T(T1, -12):
        if t < 8:
            s.note('vla', p, 82, B(83) + t, d)
    for n in range(81, 85):
        s.chord('celli', (38, 45, 50), 54, B(n), 4.0)
        s.chord('horn', (50, 57, 62), 52, B(n), 4.0)
    s.roll('timpani', 45, 40, 70, B(81), B(85), step=0.25)
    for bn, v in [(81, 62), (83, 70)]:
        dyn('vln1', v, bn); dyn('vln2', v - 4, bn); dyn('vla', v - 6, bn)
        dyn('celli', v - 8, bn)

    # ---------------- 高潮(m85-92,@104,8 小节:渐强阶梯 + 全奏) ----------------
    s.prog('vln1', *PROGS['vln1_slow'][:2], B(85))
    s.prog('trombone', *PROGS['trombone'][:2], B(85))
    s.prog('trumpet', *PROGS['trumpet'][:2], B(85))
    s.prog('vla', *PROGS['vla_slow'][:2], B(85))
    # 85-88:增时低音(长号)+ 倒影头 + 十六分下行
    for t, p, d in [(B(85), 50, 2.0), (B(85) + 2, 49, 2.0), (B(86), 45, 2.0), (B(86) + 2, 45, 2.0),
                    (B(87), 46, 2.0), (B(87) + 2, 45, 2.0), (B(88), 43, 2.0), (B(88) + 2, 43, 2.0)]:
        s.note('trombone', p, 88, t, d)
    for t, p, d in [(B(85), 69, 1.5), (B(85) + 1.5, 71, 0.5), (B(85) + 2.0, 74, 0.5),
                    (B(85) + 2.5, 74, 0.5), (B(85) + 3.0, 76, 1.0),
                    (B(86), 72, 0.25), (B(86) + 0.25, 70, 0.25), (B(86) + 0.5, 69, 0.25),
                    (B(86) + 0.75, 67, 0.25), (B(86) + 1.0, 65, 0.25), (B(86) + 1.25, 64, 0.25),
                    (B(86) + 1.5, 62, 0.25), (B(86) + 1.75, 60, 0.25),
                    (B(87), 69, 1.5), (B(87) + 1.5, 68, 0.5), (B(87) + 2.0, 64, 0.5),
                    (B(87) + 2.5, 64, 0.5), (B(87) + 3.0, 66, 1.0),
                    (B(88), 67, 1.0), (B(88) + 1, 69, 1.0), (B(88) + 2, 71, 1.0),
                    (B(88) + 3, 72, 1.0)]:
        s.note('vln1', p, 92, t, d)
    for n in range(85, 89):
        s.chord('vln2', (66, 69), 48, B(n), 4.0) if n >= 87 else None   # 85-86 二提仍在吹密接主题
        s.chord('vla', (50, 57, 62), 46, B(n), 4.0)
        s.chord('horn', (50, 57), 54, B(n), 2.0)
        s.note('celli', 38, 54, B(n), 4.0)
        s.note('bass', 38, 56, B(n), 4.0)
    # 89-92:全奏保持 + 合唱进入 + 打击乐满
    for t, p, d in [(B(89), 50, 2.0), (B(89) + 2, 49, 2.0), (B(90), 45, 2.0), (B(90) + 2, 45, 2.0),
                    (B(91), 46, 2.0), (B(91) + 2, 45, 2.0), (B(92), 43, 2.0), (B(92) + 2, 43, 2.0)]:
        s.note('trombone', p, 92, t, d)
    for t, p, d in [(B(89), 74, 1.5), (B(89) + 1.5, 73, 0.5), (B(89) + 2.0, 69, 0.5),
                    (B(89) + 2.5, 69, 0.5), (B(89) + 3.0, 71, 1.0),
                    (B(90), 72, 1.0), (B(90) + 1, 74, 1.0), (B(90) + 2, 76, 1.0),
                    (B(90) + 3, 77, 1.0),
                    (B(91), 76, 1.5), (B(91) + 1.5, 74, 0.5), (B(91) + 2.0, 72, 1.0),
                    (B(91) + 3.0, 74, 1.0),
                    (B(92), 71, 1.5), (B(92) + 1.5, 72, 0.5), (B(92) + 2.0, 69, 2.0)]:
        s.note('vln1', p, 94, t, d)
        s.note('choir', p - 12, 60, t, d)
    for n in range(89, 93):
        s.chord('vln2', (66, 69, 73), 50, B(n), 4.0)
        s.chord('vla', (50, 57, 62), 48, B(n), 4.0)
        s.chord('horn', (50, 57), 58, B(n), 2.0)
        s.chord('trumpet', (62, 66, 69), 52, B(n), 4.0)
        s.note('celli', 38, 58, B(n), 4.0)
        s.note('bass', 38, 60, B(n), 4.0)
        s.note('tuba', 38, 56, B(n), 4.0)
    s.roll('timpani', 45, 50, 88, B(89), B(93), step=0.25)
    s.note('drums', 49, 96, B(89), 2.0)
    s.note('drums', 36, 92, B(89), 0.8)
    s.note('drums', 49, 92, B(91), 1.5)
    s.note('glock', 86, 56, B(89), 1.5)
    s.note('glock', 93, 56, B(90), 1.5)
    s.note('glock', 88, 56, B(91), 1.5)
    s.note('glock', 96, 56, B(92), 1.5)
    for bn, v in [(85, 66), (87, 74), (89, 80), (91, 84)]:
        dyn('vln1', v, bn); dyn('trombone', v - 4, bn); dyn('vln2', v - 8, bn)
        dyn('vla', v - 10, bn); dyn('celli', v - 8, bn); dyn('bass', v - 10, bn)
        dyn('trumpet', v - 12, bn); dyn('horn', v - 8, bn); dyn('choir', v - 18, bn)

    # ---------------- 尾声(m93-108,@72,D 大调圣咏,渐弱) ----------------
    s.prog('vln2', *PROGS['vln2_slow'][:2], B(93))
    s.prog('vla', *PROGS['vla_slow'][:2], B(93))
    s.prog('trombone', *PROGS['tuba'][:2], B(93))
    s.prog('organ', *PROGS['organ'][:2], B(93))
    # 圣咏四部和声(声部连接:每 2 拍一和弦)
    chor = []
    for t, p, d in CHORALE:
        chord = FIN_CHORDS[p]
        chor.append((p - 12, [p - 12, chord[0], chord[1], chord[2], p]))
    chor_conn = connect(chor, n_voices=3, ranges=[(48, 74), (55, 84), (60, 96)])
    for ci, (bass, voices) in enumerate(chor_conn):
        t, p, d = CHORALE[ci]
        bt = B(93) + t
        s.note('vln1', p + 12, 84, bt, d)
        s.chord('choir', FIN_CHORDS[p], 50, bt, d)
        s.chord('organ', (p - 12, p - 5), 42, bt, d)
        for vi, name in enumerate(['vla', 'vln2']):
            if vi < len(voices):
                s.note(name, voices[vi], 44, bt, d)
        s.note('celli', bass, 46, bt, d)
        tb = bass if bass <= 53 else bass - 12   # 大号音区 26-53
        s.note('tuba', tb, 40, bt, d)
    # 钟声 + 竖琴(每 4 小节)
    for n, v in [(93, 52), (97, 58), (101, 64), (105, 52)]:
        s.note('bell', 74, v, B(n), 3.0)
        s.arp('harp', (62, 66, 69, 74), 40, B(n) + 1, 0.5, 2, 1.5)
    # 结尾和弦(m107-108,pp + 钟声余韵)
    for n in (107, 108):
        s.chord('vln1', (74, 78, 81), 84, B(n), 4.0)
        s.chord('vln2', (66, 69), 56, B(n), 4.0)
        s.chord('vla', (62, 65), 52, B(n), 4.0)
        s.chord('celli', (50, 57), 54, B(n), 4.0)
        s.chord('bass', (38, 50), 52, B(n), 4.0)
        s.chord('choir', (62, 66, 69), 50, B(n), 4.0)
        s.chord('organ', (38, 50, 57), 44, B(n), 4.0)
        s.note('tuba', 38, 48, B(n), 4.0)
        s.note('bell', 86, 56, B(n) + 1, 2.5)
    s.roll('timpani', 38, 30, 20, B(103), B(107), step=0.5)
    for bn, v in [(93, 60), (97, 54), (101, 48), (105, 42), (107, 40)]:
        dyn('vln1', v + 6, bn); dyn('choir', v - 10, bn); dyn('vln2', v - 6, bn)
        dyn('vla', v - 8, bn); dyn('celli', v - 6, bn); dyn('bass', v - 8, bn)
        dyn('organ', v - 12, bn); dyn('tuba', v - 10, bn); dyn('timpani', v - 20, bn)


def harmony_cands(ch):
    """赋格每 2 小节和声候选(基于功能)"""
    base = {'Dm': [45, 50, 53, 57, 62], 'Am': [45, 48, 52, 57, 60], 'E7': [47, 50, 52, 55, 59],
            'A7': [45, 52, 55, 60], 'Bb': [46, 50, 53, 58], 'Gm': [43, 46, 50, 55],
            'Eb': [46, 51, 55, 58], 'F': [48, 53, 57], 'G': [43, 47, 50, 55], 'A': [45, 52, 57, 60],
            'Bm': [47, 50, 54, 59], 'D': [45, 50, 54, 57, 62]}
    return base.get(ch, [45, 50, 53, 57, 62])


def main():
    ap = argparse.ArgumentParser(description='《深渊对位》生成器 v2')
    ap.add_argument('--out', default='Contrapunctus_Abyssi.mid')
    args = ap.parse_args()
    s = Score(humanize=True, seed=42)
    build(s)
    s.flush(args.out)
    print('=== 段落时间表 ===')
    print('  引子     1-8    @54   →  0:00')
    print('  帕萨卡利亚A 9-20  @72')
    print('  帕萨卡利亚B 21-32 @72')
    print('  帕萨卡利亚C 33-44 @72')
    print('  间插段   45-48  @84')
    print('  赋格    49-80  @96')
    print('  密接和应 81-84  @104')
    print('  高潮    85-92  @104')
    print('  尾声    93-108 @72')
    print('总时长 ≈ 330s ≈ 5:30')


if __name__ == '__main__':
    main()
