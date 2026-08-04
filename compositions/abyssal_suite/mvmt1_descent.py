#!/usr/bin/env python3
"""mvmt1_descent.py — 第一乐章《坠落 / Descent》(d 小调,4/4)

奏鸣式:引子(66)→ 呈示(84:主题A / 木管应答 / 主题B)→ 发展(84→108:赋格段、
紧接段、属持续)→ 再现(84:全奏 + 主题B于D大调)→ 尾声(66)。
循环动机 X(D–C#–A,下行小二度+下行四度)为本乐章主题头,全曲统一材料。
"""
import argparse
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.orch import Score, CH, PROGS

BPB = 4
B = lambda n: (n - 1) * BPB          # 小节 → 绝对拍

# ---------- 和声表 ----------
# lamento:i–VI–iv–V7(Dm–Bb–Gm–A7);主题A段 V-i-VI-iv→V 布局
H = {}
for n in range(1, 9):  H[n] = 'Dm'   # 引子(drone)
H.update({9: 'A7', 10: 'A7', 11: 'Dm', 12: 'Dm', 13: 'Bb', 14: 'Bb', 15: 'Gm', 16: 'A7',
          17: 'Dm', 18: 'Dm', 19: 'Bb', 20: 'Bb', 21: 'Gm', 22: 'Gm', 23: 'Bb', 24: 'A7'})
for n in range(25, 29): H[n] = ['Bb', 'Gm', 'C7', 'F'][n - 25]
H.update({29: 'F', 30: 'F', 31: 'Dm', 32: 'Dm', 33: 'Bb', 34: 'Bb', 35: 'F', 36: 'F',
          37: 'C7', 38: 'F', 39: 'C7', 40: 'C7'})
for n in range(41, 65):
    H[n] = ['Dm', 'Dm', 'Bb', 'Bb', 'Am', 'Am', 'F', 'F',
            'Dm', 'Dm', 'Bb', 'Bb', 'Am', 'Am', 'Dm', 'Dm',
            'Dm', 'Dm', 'Bb', 'Bb', 'A7', 'A7', 'A7', 'A7'][n - 41]
for n in range(65, 93):
    H[n] = ['A7', 'A7', 'Dm', 'Dm', 'Bb', 'Bb', 'Gm', 'Gm',
            'A7', 'A7', 'Dm', 'Dm', 'Bb', 'Bb', 'Gm', 'A7',
            'D', 'D', 'Bm', 'Bm', 'G', 'G', 'A', 'A',
            'A7', 'A7', 'Dm', 'Dm'][n - 65]
for n in range(93, 100): H[n] = 'Dm'

# 和弦构成
CHT = {
    'Dm':  (62, 65, 69), 'Bb': (58, 62, 65), 'Gm': (55, 58, 62), 'A7': (57, 61, 64),
    'F':   (65, 69, 72), 'C7': (60, 64, 67), 'Am': (57, 60, 64), 'D':  (62, 66, 69),
    'Bm':  (59, 62, 66), 'G':  (55, 59, 62), 'A':  (57, 61, 64),
}
ROOT = {'Dm': 38, 'Bb': 34, 'Gm': 31, 'A7': 33, 'F': 29, 'C7': 36, 'Am': 33,
        'D': 38, 'Bm': 35, 'G': 31, 'A': 33}
ROOT8 = {'Dm': 50, 'Bb': 46, 'Gm': 43, 'A7': 45, 'F': 41, 'C7': 48, 'Am': 45,
         'D': 50, 'Bm': 47, 'G': 43, 'A': 45}
FIFTH = {'Dm': 57, 'Bb': 53, 'Gm': 50, 'A7': 52, 'F': 48, 'C7': 55, 'Am': 52,
         'D': 57, 'Bm': 54, 'G': 50, 'A': 52}
HARP = {'Dm': (62, 65, 69, 74), 'Bb': (58, 62, 65, 70), 'Gm': (55, 58, 62, 67), 'A7': (57, 61, 64, 69),
        'F': (65, 69, 72, 77), 'C7': (60, 64, 67, 72), 'Am': (57, 60, 64, 69),
        'D': (62, 66, 69, 74), 'Bm': (59, 62, 66, 71), 'G': (55, 59, 62, 67), 'A': (57, 61, 64, 69)}
CHOIR = {'Dm': (62, 65, 69), 'Bb': (58, 62, 65), 'Gm': (55, 58, 62), 'A7': (57, 61, 64, 67),
         'F': (65, 69, 72), 'C7': (60, 64, 67), 'Am': (57, 60, 64, 67),
         'D': (62, 66, 69, 74), 'Bm': (59, 62, 66, 71), 'G': (55, 59, 62, 67), 'A': (57, 61, 64, 69)}

# ---------- 主题 A(16 小节,相对第 9 小节) ----------
THEME_A = [
    (0, 74, 1.5), (1.5, 73, 0.5), (2.0, 69, 1.0), (3.0, 71, 1.0),          # m9  A7  X头
    (4, 74, 1.5), (5.5, 76, 0.5), (6.0, 77, 1.0), (7.0, 76, 1.0),          # m10 A7
    (8, 74, 1.0), (9, 73, 0.5), (9.5, 69, 0.5), (10, 71, 1.0), (11, 72, 1.0),  # m11 Dm
    (12, 69, 2.0), (14, 67, 1.0), (15, 69, 1.0),                          # m12 Dm
    (16, 72, 1.0), (17, 74, 0.5), (17.5, 76, 0.5), (18, 77, 1.0), (19, 79, 1.0),  # m13 Bb
    (20, 81, 1.0), (21, 79, 0.5), (21.5, 77, 0.5), (22, 76, 1.0), (23, 74, 1.0),  # m14 Bb
    (24, 76, 1.5), (25.5, 77, 0.5), (26, 79, 1.0), (27, 77, 1.0),          # m15 Gm
    (28, 74, 1.0), (29, 73, 0.5), (29.5, 69, 0.5), (30, 69, 2.0),          # m16 A7  X尾
    (32, 76, 1.5), (33.5, 74, 0.5), (34, 72, 1.0), (35, 71, 1.0),          # m17 Dm
    (36, 74, 1.5), (37.5, 76, 0.5), (38, 77, 1.0), (39, 79, 1.0),          # m18 Dm
    (40, 81, 1.0), (41, 79, 0.5), (41.5, 77, 0.5), (42, 76, 1.0), (43, 74, 1.0),  # m19 Bb
    (44, 72, 1.0), (45, 74, 0.5), (45.5, 76, 0.5), (46, 77, 1.0), (47, 79, 1.0),  # m20 Bb
    (48, 81, 1.5), (49.5, 79, 0.5), (50, 77, 1.0), (51, 76, 1.0),          # m21 Gm
    (52, 77, 1.5), (53.5, 76, 0.5), (54, 74, 0.5), (54.5, 72, 0.5), (55, 71, 1.0),  # m22 Gm
    (56, 72, 1.0), (57, 71, 0.5), (57.5, 69, 0.5), (58, 67, 1.0), (59, 69, 1.0),  # m23 Bb
    (60, 74, 1.0), (61, 73, 0.5), (61.5, 69, 0.5), (62, 62, 1.0), (63, 62, 1.0),  # m24 A7→Dm
]

# 主题 B(12 小节,相对第 29 小节,F 大调,双簧管)
THEME_B = [
    (0, 77, 1.0), (1, 81, 1.0), (2, 79, 1.0), (3, 77, 1.0),                # m29 F
    (4, 76, 1.5), (5.5, 74, 0.5), (6, 72, 1.0), (7, 74, 1.0),              # m30
    (8, 72, 1.5), (9.5, 70, 0.5), (10, 69, 1.0), (11, 72, 1.0),            # m31 Dm
    (12, 74, 2.0), (14, 72, 2.0),                                          # m32 Dm
    (16, 77, 1.0), (17, 81, 1.0), (18, 84, 1.0), (19, 81, 1.0),            # m33 Bb
    (20, 79, 1.5), (21.5, 77, 0.5), (22, 76, 1.0), (23, 77, 1.0),          # m34 Bb
    (24, 81, 1.0), (25, 79, 1.0), (26, 77, 1.0), (27, 76, 1.0),            # m35 F
    (28, 77, 2.0), (30, 74, 2.0),                                          # m36 F
    (32, 76, 1.0), (33, 74, 1.0), (34, 72, 1.5), (35.5, 70, 0.5),          # m37 C7
    (36, 69, 1.0), (37, 67, 1.0), (38, 65, 2.0),                           # m38 F
    (40, 77, 1.0), (41, 76, 1.0), (42, 74, 1.0), (43, 72, 1.0),            # m39 C7
    (44, 70, 1.0), (45, 69, 1.0), (46, 67, 2.0),                           # m40 C7
]

# 赋格段主题 S(4 小节,相对第 41 小节,d 小调)
SUBJECT = [
    (0, 74, 1.5), (1.5, 73, 0.5), (2.0, 69, 0.5), (2.5, 69, 0.5), (3.0, 71, 1.0),  # m41 X头+级进
    (4, 72, 1.0), (5, 74, 1.0), (6, 76, 1.0), (7, 77, 1.0),                          # m42 上行
    (8, 76, 1.0), (9, 74, 0.5), (9.5, 72, 0.5), (10, 74, 2.0),                        # m43 回落
    (12, 72, 1.0), (13, 71, 1.0), (14, 69, 2.0),                                      # m44 尾音=答题主音
]
# 对题 CS(八分流动线,相对第 45 小节)
COUNTER = [
    (0, 76, 0.5), (0.5, 74, 0.5), (1.0, 72, 0.5), (1.5, 71, 0.5), (2.0, 69, 0.5), (2.5, 71, 0.5),
    (3.0, 72, 0.5), (3.5, 74, 0.5), (4, 76, 0.5), (4.5, 77, 0.5), (5.0, 79, 0.5), (5.5, 81, 0.5),
    (6.0, 79, 0.5), (6.5, 77, 0.5), (7.0, 76, 0.5), (7.5, 74, 0.5),
    (8, 72, 0.5), (8.5, 74, 0.5), (9.0, 76, 0.5), (9.5, 77, 0.5), (10.0, 79, 0.5), (10.5, 77, 0.5),
    (11.0, 76, 0.5), (11.5, 74, 0.5), (12, 72, 0.5), (12.5, 71, 0.5), (13.0, 69, 0.5), (13.5, 67, 0.5),
    (14.0, 69, 0.5), (14.5, 71, 0.5), (15.0, 72, 0.5), (15.5, 74, 0.5),
]
# 答题(五度下方,a 小调):显式写出,尾部调性贴合 F→Dm 和声
ANSWER = [
    (0, 69, 1.5), (1.5, 68, 0.5), (2.0, 64, 0.5), (2.5, 64, 0.5), (3.0, 66, 1.0),  # m45 A G# E E F#
    (4, 67, 1.0), (5, 69, 1.0), (6, 71, 1.0), (7, 72, 1.0),                          # m46 C D E F
    (8, 71, 1.0), (9, 69, 0.5), (9.5, 67, 0.5), (10, 69, 2.0),                        # m47 B A G A
    (12, 67, 1.0), (13, 66, 1.0), (14, 64, 2.0),                                      # m48 G F# E
]

# 木管应答(Bb→Gm→C7→F,四个 X 片段)
BRIDGE_X = {
    25: (70, 69, 65),   # Bb4 A4 F4(长笛)
    26: (67, 66, 62),   # G4 F#4 D4(单簧管)
    27: (72, 71, 67),   # C5 B4 G4(双簧管)
    28: (77, 76, 72),   # F5 E5 C5(长笛)
}


def build(s: Score):
    # ---------------- 注册音色(每通道一轨,琶音切换走 prog) ----------------
    regs = [
        ('bell', CH['piano'], *PROGS['church_bell']),
        ('harp', CH['harp'], *PROGS['harp']),
        ('vln1', CH['vln1'], *PROGS['vln1_slow']),
        ('vln2', CH['vln2'], *PROGS['vln2_slow']),
        ('vla', CH['vla'], *PROGS['vla_slow']),
        ('celli', CH['celli'], *PROGS['celli_pizz']),      # 呈示部先拨弦
        ('bass', CH['bass'], *PROGS['bass_slow']),
        ('flute', CH['flute'], *PROGS['flute']),
        ('oboe', CH['oboe'], *PROGS['oboe']),
        ('clarinet', CH['clarinet'], *PROGS['clarinet']),
        ('drums', CH['drums'], 128, 0, (0, 127)),
        ('timpani', CH['timpani'], *PROGS['timpani']),
        ('horn', CH['horns'], *PROGS['horn']),
        ('trombone', CH['brass'], *PROGS['trombone']),     # 先占 ch13
        ('trumpet', CH['brass'], *PROGS['trumpet']),
        ('choir', CH['choir'], *PROGS['choir']),
        ('organ', CH['keys'], *PROGS['organ']),
    ]
    for name, ch, bank, prog, (lo, hi) in regs:
        s.add_instr(name, ch, bank, prog, lo, hi)
        s.cc(name, 7, 100, 0.0)
    s.cc('timpani', 7, 88, 0.0)

    def dyn(inst, v, bar_n):
        s.cc(inst, 11, v, B(bar_n))

    # ---------------- 速度与拍号 ----------------
    s.tempo(66, B(1)); s.tempo(84, B(9)); s.tempo(96, B(57)); s.tempo(108, B(61))
    s.tempo(84, B(65)); s.tempo(66, B(93))

    # ---------------- 引子(m1-8,d 持续音 + 钟声 + 滚奏 + X 碎片) ----------------
    for n in range(1, 9):
        s.note('bass', 38, 50, B(n), 4.0)                    # D2 持续
        s.chord('organ', (38, 50), 44, B(n), 4.0)            # 管风琴 D2+D3
    s.chord('vla', (62, 65, 69), 34, B(1), 8.0)              # 中提琴 Dm 长音
    for t, v in [(B(1), 40), (B(4), 42), (B(7), 44)]:
        s.note('bell', 62, v, t, 3.0)                        # 教堂钟 D4
    for t in (B(1), B(3), B(5), B(7)):
        s.arp('harp', HARP['Dm'], 40, t, 0.5, 1, 2.0)
    for t, x, v in [(B(2), (62, 61, 57), 36), (B(5), (58, 57, 53), 44), (B(7), (69, 68, 64), 52)]:
        s.note('celli', x[0], v, t, 1.5)                     # 大提琴 X 碎片(p→mf)
        s.note('celli', x[1], v, t + 1.5, 0.5)
        s.note('celli', x[2], v, t + 2.0, 1.0)
    s.roll('timpani', 38, 26, 62, B(5), B(9), step=0.25)     # 定音鼓滚奏渐强(收敛)
    for t, p, d in [(B(7), 74, 1.0), (B(7) + 1, 73, 0.5), (B(7) + 1.5, 69, 0.5),
                    (B(7) + 2, 69, 1.0), (B(7) + 3, 71, 1.0),
                    (B(8), 74, 1.5), (B(8) + 1.5, 76, 0.5), (B(8) + 2, 77, 1.0)]:
        s.note('vln1', p, 84, t, d)                          # 主题头预示
    dyn('vln1', 26, 7); dyn('vln1', 48, 8)
    dyn('celli', 28, 1); dyn('celli', 50, 7)
    dyn('vla', 24, 1); dyn('organ', 30, 1); dyn('harp', 40, 1)
    dyn('bass', 30, 1); dyn('bass', 52, 8)

    # ---------------- 呈示部 · 主题 A(m9-24) ----------------
    for n in range(9, 25):
        ch = H[n]
        s.ostinato('celli', [(ROOT8[ch], 1.0), (FIFTH[ch], 1.0)], 78, B(n), 2)   # 拨弦 ostinato
        s.note('vla', CHT[ch][1], 52, B(n), 4.0)                                # 中提琴三音
        s.note('bass', ROOT[ch], 60, B(n), 2.0)
        s.note('bass', ROOT[ch], 58, B(n) + 2, 2.0)
        s.arp('harp', HARP[ch], 62, B(n), 0.5, 1, 2.0)
    for n in range(13, 25):
        s.note('vln2', FIFTH[H[n]] + 12, 40, B(n), 4.0)      # 二提轻和声(五音+八度)
    for t, p, d in THEME_A:
        s.note('vln1', p, 90, B(9) + t, d)
    for bn, v in [(9, 58), (11, 64), (13, 68), (15, 70), (17, 68), (19, 70), (21, 72), (23, 70), (24, 58)]:
        dyn('vln1', v, bn)
    dyn('vla', 36, 9); dyn('vla', 44, 17); dyn('vln2', 34, 13)
    dyn('bass', 55, 9); dyn('bass', 50, 25); dyn('bass', 48, 29)
    # m24 末拍竖琴预挂 A(属准备,转场五件套-和声预挂)
    s.note('harp', 57, 50, B(24) + 3.5, 0.5)

    # ---------------- 木管应答(m25-28,弦乐震音) ----------------
    s.prog('vln1', *PROGS['vln1_trem'][:2], B(25))
    s.prog('vln2', *PROGS['vln2_trem'][:2], B(25))
    s.prog('vla', *PROGS['vla_trem'][:2], B(25))
    for n in range(25, 29):
        x = BRIDGE_X[n]
        inst = 'flute' if n in (25, 28) else ('clarinet' if n == 26 else 'oboe')
        for i, p in enumerate(x):
            s.note(inst, p, 88, B(n) + i, 1.0)
        s.note('bass', {'Bb': 34, 'Gm': 31, 'C7': 36, 'F': 29}[H[n]], 48, B(n), 4.0)
        s.note('celli', ROOT8[H[n]], 60, B(n), 0.5)
        s.note('celli', FIFTH[H[n]], 58, B(n) + 2, 0.5)
        s.chord('vln1', (CHT[H[n]][0], CHT[H[n]][2]), 42, B(n), 4.0)
        s.chord('vla', (CHT[H[n]][1], CHT[H[n]][2]), 44, B(n), 4.0)
    dyn('vln1', 38, 25); dyn('vln2', 36, 25); dyn('vla', 36, 25)
    dyn('flute', 44, 25); dyn('clarinet', 44, 26); dyn('oboe', 46, 27)

    # ---------------- 主题 B(m29-40,F 大调,双簧管独奏) ----------------
    s.prog('vln1', *PROGS['vln1_pizz'][:2], B(29))
    s.prog('vln2', *PROGS['vln2_pizz'][:2], B(29))
    s.prog('vla', *PROGS['vla_pizz'][:2], B(29))
    for t, p, d in THEME_B:
        s.note('oboe', p, 88, B(29) + t, d)
    for n in range(29, 41):
        ch = H[n]
        s.chord('vln1', (CHT[ch][2] + 12, CHT[ch][0] + 12), 52, B(n), 0.6)
        s.chord('vln2', (CHT[ch][1] + 12, CHT[ch][2]), 50, B(n) + 2, 0.6)
        s.note('celli', ROOT8[ch], 56, B(n), 0.8)
        s.note('bass', ROOT[ch], 50, B(n), 2.0)
        if n in (29, 33, 37):
            s.arp('harp', HARP[ch], 56, B(n), 0.5, 1, 2.0)
    for n, p in [(29, 53), (33, 58), (37, 60)]:
        s.note('horn', p, 62, B(n), 8.0)                     # 圆号持续音
    for bn, v in [(29, 58), (33, 66), (37, 62), (39, 50)]:
        dyn('oboe', v, bn)
    dyn('horn', 34, 29)
    # m40 末拍属预挂:低音 A 提前落
    s.note('bass', 33, 60, B(40) + 3.0, 1.0)

    # ---------------- 发展部 · 赋格段(m41-56) ----------------
    s.prog('vln1', *PROGS['vln1_slow'][:2], B(41))
    s.prog('vln2', *PROGS['vln2_slow'][:2], B(41))
    s.prog('vla', *PROGS['vla_slow'][:2], B(41))
    for n in range(41, 57):
        ch = H[n]
        s.chord('vla', (CHT[ch][1], CHT[ch][2]), 44, B(n), 4.0)   # 内声部持续
        s.note('bass', ROOT[ch], 52, B(n), 2.0)
        s.note('bass', ROOT[ch], 50, B(n) + 2, 2.0)
    for n in range(41, 49):                                        # 拨弦延续(织体不断)
        s.note('celli', ROOT8[H[n]], 56, B(n), 0.7)
        s.note('celli', FIFTH[H[n]], 52, B(n) + 2, 0.7)
    s.prog('celli', *PROGS['celli_slow'][:2], B(49))              # 大提琴转弓
    for t, p, d in SUBJECT:
        s.note('vln1', p, 92, B(41) + t, d)                       # 进入 1:一提(主题,d)
    for t, p, d in COUNTER:
        s.note('vln1', p, 78, B(45) + t, d)                       # 对题:一提
    for t, p, d in ANSWER:
        s.note('vln2', p, 90, B(45) + t, d)                       # 进入 2:二提(答题,a)
    for t, p, d in COUNTER:
        s.note('vln2', p, 74, B(49) + t, d)                       # 对题:二提
    for t, p, d in SUBJECT:
        s.note('celli', p - 12, 86, B(49) + t, d)                 # 进入 3:大提琴(主题,低八度)
    for t, p, d in ANSWER:
        s.note('flute', p + 12, 88, B(53) + t, d)                 # 进入 4:长笛(答题,a,高八度)
    for t, p, d in SUBJECT:
        s.note('trombone', p - 17, 84, B(53) + t, d)              # 进入 5:长号(主题,低音区)
    for bn, v in [(41, 62), (45, 66), (49, 70), (53, 74)]:
        dyn('vln1', v, bn); dyn('vln2', v, bn)
    dyn('vla', 48, 41); dyn('celli', 54, 49); dyn('flute', 62, 53); dyn('trombone', 62, 53)
    dyn('bass', 56, 41)

    # ---------------- 紧接段(m57-60,X 卡农,随和声移调) ----------------
    for t, p, d, v in [(B(57), 74, 1.5, 92), (B(57) + 1.5, 73, 0.5, 90), (B(57) + 2.0, 69, 0.5, 90),
                      (B(57) + 2.5, 69, 0.5, 88), (B(57) + 3.0, 71, 1.0, 88),
                      (B(58), 72, 1.0, 88), (B(58) + 1, 74, 1.0, 88), (B(58) + 2, 76, 1.0, 90),
                      (B(58) + 3, 77, 1.0, 90)]:
        s.note('vln1', p, v, t, d)                               # X(D)+上行
    for t, p, d, v in [(B(58), 70, 1.5, 88), (B(58) + 1.5, 69, 0.5, 86), (B(58) + 2.0, 65, 0.5, 86),
                      (B(58) + 2.5, 65, 0.5, 84), (B(58) + 3.0, 67, 1.0, 84),
                      (B(59), 69, 1.0, 84), (B(59) + 1, 71, 1.0, 84), (B(59) + 2, 72, 1.0, 84),
                      (B(59) + 3, 74, 1.0, 84)]:
        s.note('vln2', p, v, t, d)                               # X(Bb)+上行
    for t, p, d, v in [(B(59), 46, 1.5, 84), (B(59) + 1.5, 45, 0.5, 82), (B(59) + 2.0, 41, 0.5, 82),
                      (B(59) + 2.5, 41, 0.5, 80), (B(59) + 3.0, 43, 0.5, 80)]:
        s.note('trombone', p, v, t, d)                           # X(Bb,低八度)
    s.prog('trumpet', *PROGS['trumpet'][:2], B(60))              # 长号停 → 小号(无声区切换)
    for t, p, d, v in [(B(60), 69, 1.5, 88), (B(60) + 1.5, 68, 0.5, 86), (B(60) + 2.0, 64, 0.5, 86),
                      (B(60) + 2.5, 64, 0.5, 84), (B(60) + 3.0, 66, 0.5, 84)]:
        s.note('trumpet', p, v, t, d)                            # X(A,G#=属三音)
    s.note('trumpet', 67, 84, B(61), 1.0); s.note('trumpet', 69, 84, B(61) + 1, 1.0)
    dyn('vln1', 82, 57); dyn('vln2', 80, 57); dyn('bass', 58, 57)

    # ---------------- 属持续(m61-64,A7 渐强) ----------------
    s.prog('vln1', *PROGS['vln1_trem'][:2], B(61))
    s.prog('vln2', *PROGS['vln2_trem'][:2], B(61))
    s.prog('vla', *PROGS['vla_trem'][:2], B(61))
    s.roll('timpani', 45, 38, 82, B(61), B(65), step=0.25)
    for n in range(61, 65):
        s.chord('vla', (57, 61, 64), 60, B(n), 4.0)
        s.chord('vln1', (69, 73, 76), 62, B(n), 4.0)
        s.chord('vln2', (64, 69, 73), 58, B(n), 4.0)
        s.chord('horn', (45, 52), 62, B(n), 2.0)
        s.note('bass', 33, 56, B(n), 4.0)
        if n >= 63:
            s.note('drums', 36, 84 + (n - 63) * 8, B(n) + 3.5, 0.3)
    for bn, v in [(61, 80), (62, 90), (63, 100), (64, 112)]:
        dyn('vln1', v, bn); dyn('vln2', v, bn); dyn('vla', v, bn)
        dyn('horn', v - 6, bn); dyn('trumpet', v - 10, bn)
    dyn('bass', 60, 61); dyn('bass', 72, 64)

    # ---------------- 再现(m65-92) ----------------
    s.prog('vln1', *PROGS['vln1_slow'][:2], B(65))
    s.prog('vln2', *PROGS['vln2_slow'][:2], B(65))
    s.prog('vla', *PROGS['vla_slow'][:2], B(65))
    s.prog('celli', *PROGS['celli_slow'][:2], B(65))
    for n in range(65, 81):
        ch = H[n]
        s.chord('vln2', (FIFTH[ch] + 12, CHT[ch][1] + 12), 54, B(n), 4.0)
        s.chord('vla', (FIFTH[ch], CHT[ch][1]), 52, B(n), 4.0)   # 中提琴:五音+三音(低八度,避同度)
        s.chord('choir', CHOIR[ch], 56, B(n), 4.0)
        s.note('celli', ROOT8[ch], 66, B(n), 2.0)
        s.note('celli', FIFTH[ch], 62, B(n) + 2, 2.0)
        s.note('bass', ROOT[ch], 64, B(n), 4.0)
        s.chord('horn', (ROOT8[ch], FIFTH[ch]), 70, B(n), 1.0)   # 铜管柱式(拍1/拍3,根+五)
        s.chord('trumpet', (ROOT8[ch] + 12, FIFTH[ch] + 12), 68, B(n), 1.0)
        s.chord('horn', (ROOT8[ch], FIFTH[ch]), 64, B(n) + 2, 1.0)
        s.chord('trumpet', (ROOT8[ch] + 12, FIFTH[ch] + 12), 62, B(n) + 2, 1.0)
        s.arp('harp', HARP[ch], 70, B(n), 0.5, 1, 2.0)
    for t, p, d in THEME_A:                                      # 旋律:一提 + 长笛齐奏
        s.note('vln1', p, 96, B(65) + t, d)
        s.note('flute', p, 88, B(65) + t, d)
    for n in (73, 77, 81):
        s.note('timpani', 38, 82, B(n), 0.6)
        s.note('drums', 36, 92, B(n), 0.5)
    for n in (65, 81):
        s.note('drums', 49, 96, B(n), 1.0)
    s.roll('timpani', 38, 45, 82, B(79), B(81), step=0.25)
    for bn, v in [(65, 82), (69, 90), (73, 96), (77, 104), (80, 100)]:
        dyn('vln1', v, bn); dyn('vln2', v - 4, bn); dyn('vla', v - 6, bn)
        dyn('choir', v - 22, bn); dyn('flute', v - 8, bn); dyn('horn', v - 10, bn)
        dyn('trumpet', v - 10, bn); dyn('celli', v - 14, bn)
        dyn('bass', v - 14, bn)

    # 主题 B 再现于 D 大调(m81-88,双簧管 + 拨弦)
    s.prog('vln1', *PROGS['vln1_pizz'][:2], B(81))
    s.prog('vln2', *PROGS['vln2_pizz'][:2], B(81))
    for t, p, d in THEME_B:
        s.note('oboe', p - 3, 90, B(81) + t, d)
    for n in range(81, 89):
        ch = H[n]
        s.chord('vln1', (CHT[ch][2] + 12, CHT[ch][0] + 12), 54, B(n), 0.6)
        s.chord('vln2', (CHT[ch][1] + 12, CHT[ch][2]), 52, B(n) + 2, 0.6)
        s.chord('vla', (CHT[ch][1], CHT[ch][2]), 40, B(n), 4.0)
        s.note('celli', ROOT8[ch], 58, B(n), 4.0)
        s.note('bass', ROOT[ch], 56, B(n), 4.0)
        s.arp('harp', HARP[ch], 64, B(n), 0.5, 1, 2.0)
    for bn, v in [(81, 56), (85, 62), (88, 52)]:
        dyn('oboe', v, bn)

    # 收束(m89-92:A7 → Dm,属准备回落)
    s.prog('vln1', *PROGS['vln1_slow'][:2], B(89))
    s.prog('vln2', *PROGS['vln2_slow'][:2], B(89))
    for t, p, d in [(B(89), 74, 1.0), (B(89) + 1, 73, 0.5), (B(89) + 1.5, 69, 0.5),
                    (B(89) + 2, 69, 1.0), (B(89) + 3, 62, 1.0),
                    (B(90), 62, 2.0), (B(90) + 2, 62, 2.0)]:
        s.note('vln1', p, 90, t, d)
    for n in range(89, 91):
        ch = H[n]
        s.chord('vln2', (69, 73), 50, B(n), 4.0)
        s.chord('vla', (57, 61, 64), 48, B(n), 4.0)
        s.chord('choir', CHOIR[ch], 46, B(n), 4.0)
        s.chord('horn', (45, 52), 54, B(n), 2.0)
        s.note('timpani', 45, 62, B(n), 0.8)
    s.note('timpani', 38, 70, B(91), 1.2)
    for n in (91, 92):
        s.chord('vln2', (62, 65, 69), 44, B(n), 4.0)
        s.chord('vla', (50, 57), 44, B(n), 4.0)
        s.chord('choir', (62, 65, 69), 42, B(n), 4.0)
        s.chord('horn', (50, 57), 46, B(n), 4.0)
        s.chord('organ', (38, 50), 40, B(n), 4.0)
        s.note('bass', 38, 48, B(n), 4.0)
    for bn, v in [(89, 52), (91, 42)]:
        dyn('vln1', v, bn); dyn('choir', v - 12, bn); dyn('organ', v - 10, bn)
        dyn('bass', 50, 89); dyn('bass', 42, 91); dyn('celli', 44, 89)

    # ---------------- 尾声(m93-98,归于寂静) ----------------
    for n in range(93, 99):
        s.note('bass', 38, 44, B(n), 4.0)
        s.chord('organ', (38, 50), 36, B(n), 4.0)
    for t, v in [(B(93), 38), (B(95) + 2, 34), (B(97) + 1, 30)]:
        s.note('bell', 62, v, t, 3.0)
    s.note('celli', 62, 44, B(94), 1.5); s.note('celli', 61, 42, B(94) + 1.5, 0.5)
    s.note('celli', 57, 40, B(94) + 2.0, 1.0)
    s.note('vln1', 74, 46, B(96), 1.5); s.note('vln1', 73, 44, B(96) + 1.5, 0.5)
    s.note('vln1', 69, 42, B(96) + 2.0, 1.0)
    s.note('timpani', 38, 50, B(96), 1.0)
    dyn('vln1', 30, 93); dyn('vln1', 20, 97)
    dyn('celli', 30, 93); dyn('organ', 26, 93); dyn('bass', 26, 93); dyn('bass', 18, 97)


def main():
    ap = argparse.ArgumentParser(description='第一乐章《坠落》')
    ap.add_argument('--out', default='Mvmt1_Descent.mid')
    args = ap.parse_args()
    s = Score()
    build(s)
    issues = s.flush(args.out)
    print('=== 段落时间表(bar→秒)===')
    print('  引子   1-8    @66  →  0.0 - 29.1s')
    print('  呈示   9-40   @84  →  29.1 - 120.5s')
    print('  发展   41-56  @84  →  120.5 - 166.2s')
    print('  紧接   57-60  @96  →  166.2 - 176.2s')
    print('  属持续 61-64  @108 →  176.2 - 185.1s')
    print('  再现   65-92  @84  →  185.1 - 265.1s')
    print('  尾声   93-98  @66  →  265.1 - 286.9s')
    print(f'总时长 ≈ 287s ≈ 4:47')


if __name__ == '__main__':
    main()
