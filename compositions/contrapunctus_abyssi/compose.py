#!/usr/bin/env python3
"""compose.py — 《深渊对位 / Contrapunctus Abyssi》(~4:33,单乐章)

技术密度实验:在更短的时间里堆叠更多作曲技法,并补上混音/演奏层的缺口。

形式:引子 → 帕萨卡利亚(11 段变奏,固定低音=深渊动机 X 的扩大化,和声被迫转位)
→ 赋格(4 进入 + 间插段序列 + 八度/铜管进入)→ 增时+倒影高潮 → 皮卡迪尾声。

技法清单:固定低音变奏 / 减缩(十六分音型)/ 卡农 / 主题移调传递 / 混色叠置
(长笛+中提琴六度、巴松+低音、长笛+短笛式齐奏)/ hemiola(3+3+2)/ 间插段
序列转调(F→Gm→Eb→A7)/ 弱音小号 / 主题增时 / 倒影头 / 属持续 / 皮卡迪。

链路层(相对组曲的新增):CC10 管弦乐声像、CC91 分层混响、CC11 连续斜坡、
人性化抖动、Orchestra Kit 鼓组。
"""
import argparse
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.orch import Score, CH, PROGS

BPB = 4
B = lambda n: (n - 1) * BPB

# ---------------- 帕萨卡利亚固定低音(16 四分音符 = 4 小节) ----------------
# 结构: X 头(D-C#-A)+ lamento(Bb-A-G)+ 半音(Eb-D-C#)+ 收束(D-A-D)
GROUND = {
    'Dm': [38, 37, 33, 33, 34, 33, 31, 31, 39, 38, 37, 37, 38, 33, 38, 38],
    'F':  [41, 40, 36, 36, 38, 36, 34, 34, 32, 31, 30, 30, 31, 38, 31, 31],
    'Gm': [43, 42, 38, 38, 39, 38, 36, 36, 34, 33, 32, 32, 33, 40, 33, 33],
    'Eb': [39, 38, 34, 34, 35, 34, 32, 32, 30, 29, 28, 28, 39, 34, 39, 39],
    'A7': [33, 32, 28, 28, 29, 28, 38, 38, 34, 33, 32, 32, 33, 28, 33, 33],
    'E':  [40, 39, 35, 35, 36, 35, 33, 33, 42, 40, 39, 39, 40, 35, 40, 40],
}
# hemiola 版(Eb,3+3+2 八分组合,12 音)
HEMIOLA = ([39, 38, 34, 35, 34, 32, 30, 29, 28, 39, 34, 39], (1.5, 1.5, 1.0))

# ---------------- 主题 T1(= 赋格主题,4 小节) ----------------
T1 = [
    (0, 74, 1.5), (1.5, 73, 0.5), (2.0, 69, 0.5), (2.5, 69, 0.5), (3.0, 71, 1.0),   # X 头 + 级进
    (4, 72, 1.0), (5, 74, 1.0), (6, 76, 1.0), (7, 77, 1.0),                          # 上行
    (8, 76, 1.0), (9, 74, 0.5), (9.5, 72, 0.5), (10, 74, 2.0),                        # 回落
    (12, 71, 1.0), (13, 72, 1.0), (14, 69, 2.0),                                      # 收束
]
# 答题(A 小调,五度下)
ANS = [(b, p - 5, d) for b, p, d in T1]
# 对题(八分流动线,4 小节)
CS = [
    (0, 59, 0.5), (0.5, 60, 0.5), (1.0, 62, 0.5), (1.5, 64, 0.5), (2.0, 65, 0.5), (2.5, 64, 0.5),
    (3.0, 62, 0.5), (3.5, 60, 0.5), (4, 59, 0.5), (4.5, 57, 0.5), (5.0, 55, 0.5), (5.5, 57, 0.5),
    (6.0, 59, 0.5), (6.5, 60, 0.5), (7.0, 62, 0.5), (7.5, 64, 0.5),
    (8, 65, 0.5), (8.5, 64, 0.5), (9.0, 62, 0.5), (9.5, 61, 0.5), (10.0, 62, 0.5), (10.5, 61, 0.5),
    (11.0, 59, 0.5), (11.5, 57, 0.5),
]
# 对位旋律(双簧管,St2)
CM = [
    (0, 77, 1.5), (1.5, 76, 0.5), (2.0, 74, 1.0), (3.0, 72, 1.0),
    (4, 74, 1.0), (5, 76, 0.5), (6, 77, 0.5), (7, 79, 1.0), (8, 81, 1.0),
    (9, 79, 1.5), (10.5, 77, 0.5), (11, 76, 1.0), (12, 74, 1.0),
    (13, 76, 2.0), (15, 73, 1.0), (16, 74, 1.0),
]
# St5 旋律(F 大调,长笛)
M_F = [
    (0, 77, 1.5), (1.5, 79, 0.5), (2.0, 81, 1.0), (3.0, 81, 1.0),
    (4, 70, 1.0), (5, 69, 1.0), (6, 65, 1.0), (7, 67, 1.0),
    (8, 68, 2.0), (10, 70, 1.0), (11, 72, 1.0),
    (12, 71, 1.0), (13, 72, 0.5), (14, 71, 0.5), (15, 67, 2.0),
]
# St5 对位(双簧管)
O_F = [
    (0, 65, 2.0), (2, 67, 1.0), (3, 65, 1.0), (4, 62, 2.0), (6, 65, 1.0), (7, 62, 1.0),
    (8, 60, 2.0), (10, 61, 1.0), (11, 60, 1.0), (12, 59, 2.0), (14, 62, 1.0), (15, 59, 1.0),
]
# St11 增时头(X-aug,4 小节)
X_AUG = [
    (0, 74, 2.0), (2, 73, 1.0), (3, 69, 1.0), (4, 71, 2.0), (6, 69, 1.0), (7, 67, 1.0),
    (8, 75, 2.0), (10, 74, 1.0), (11, 72, 1.0), (12, 74, 2.0), (14, 73, 1.0), (15, 74, 1.0),
]
# 终曲圣咏(12 小节,D 大调)
CHORALE = [
    (0, 62, 2.0), (2, 61, 1.0), (3, 57, 1.0), (4, 59, 2.0), (6, 61, 1.0), (7, 62, 1.0),
    (8, 64, 2.0), (10, 62, 1.0), (11, 61, 1.0), (12, 62, 2.0), (14, 59, 1.0), (15, 57, 1.0),
    (16, 66, 2.0), (18, 64, 1.0), (19, 62, 1.0), (20, 64, 2.0), (22, 62, 1.0), (23, 61, 1.0),
    (24, 66, 2.0), (26, 64, 1.0), (27, 62, 1.0), (28, 61, 2.0), (30, 59, 1.0), (31, 57, 1.0),
    (32, 62, 2.0), (34, 61, 1.0), (35, 57, 1.0), (36, 59, 2.0), (38, 57, 1.0), (39, 66, 1.0),
    (40, 66, 2.0), (42, 64, 1.0), (43, 62, 1.0), (44, 62, 4.0),
]
FIN_CHORDS = {62: (62, 66, 69), 61: (61, 64, 68), 57: (57, 61, 64), 59: (59, 62, 66),
              64: (64, 67, 71), 66: (66, 69, 73)}

# 和声(帕萨卡利亚上方 = 固定低音暗示的和弦;赋格段另行)
CHT = {'Dm': (53, 57, 62), 'F': (65, 69, 72), 'Gm': (55, 58, 62), 'Eb': (51, 55, 58),
       'A7': (57, 61, 64), 'Am': (57, 60, 64), 'E7': (52, 56, 59), 'D': (62, 66, 69),
       'Bm': (59, 62, 66), 'G': (55, 59, 62), 'A': (57, 61, 64), 'Bb': (58, 62, 65)}
# 转位和弦(6/3):低音提琴区三音组,帕萨卡利亚上方的"被迫转位"
INV6 = {'Dm': ((53, 57), (62,)), 'F': ((65, 69), (72,)), 'Gm': ((55, 58), (62,)),
        'Eb': ((51, 55), (58,)), 'A7': ((57, 61), (64,)), 'D': ((62, 66), (69,)),
        'Bm': ((59, 62), (66,)), 'G': ((55, 59), (62,)), 'A': ((57, 61), (64,))}
ROOT = {'Dm': 38, 'F': 41, 'Gm': 43, 'Eb': 39, 'A7': 33, 'Am': 33, 'E7': 28,
        'D': 38, 'Bm': 35, 'G': 31, 'A': 33, 'Bb': 34}
ROOT8 = {'Dm': 50, 'F': 53, 'Gm': 55, 'Eb': 51, 'A7': 45, 'Am': 45, 'E7': 40,
         'D': 50, 'Bm': 47, 'G': 43, 'A': 45, 'Bb': 46}
FIFTH = {'Dm': 57, 'F': 60, 'Gm': 62, 'Eb': 58, 'A7': 52, 'Am': 52, 'E7': 47,
         'D': 57, 'Bm': 54, 'G': 50, 'A': 52, 'Bb': 53}
HARP = {'Dm': (62, 65, 69, 74), 'F': (65, 69, 72, 77), 'Gm': (55, 58, 62, 67),
        'Eb': (51, 55, 58, 63), 'A7': (57, 61, 64, 69), 'D': (62, 66, 69, 74)}
CHOIR = {'A7': (57, 61, 64, 67), 'Dm': (53, 57, 62)}

# ---------------- 减缩工具(调内十六分走句) ----------------
SCALE_D = [38, 40, 41, 43, 45, 46, 48, 50, 52, 53, 55, 57, 58, 60, 62, 64, 65, 67, 69, 70, 72, 74, 76, 77, 79, 81, 82, 84, 86]


def _snap(x, scale):
    return min(scale, key=lambda s: abs(s - x))


def _walk(cur, target, scale, step=1):
    ci, ti = scale.index(_snap(cur, scale)), scale.index(_snap(target, scale))
    if ci == ti:
        return target
    ni = ci + (step if ti > ci else -step)
    if (ti > ci and ni >= ti) or (ti < ci and ni <= ti):
        return target
    return scale[ni]


def dimin(seq, scale=SCALE_D):
    """减缩:旋律音 → 十六分调内走句(导向下一音)"""
    out = []
    for i, (t, p, d) in enumerate(seq):
        nxt = seq[i + 1][1] if i + 1 < len(seq) else p
        n = max(1, int(round(d * 4)))
        cur = p
        for k in range(n):
            if k > 0 and cur != nxt:
                cur = _walk(cur, nxt, scale)
            out.append((t + k / 4.0, cur, 0.22))
    return out


def T(seq, semis):
    return [(b, p + semis, d) for b, p, d in seq]


# ---------------- 帕萨卡利亚布局 ----------------
ST = {
    1:  (5,  'Dm', 'Dm'),   # 呈示:一提 T1
    2:  (9,  'Dm', 'Dm'),   # 双簧管对位 + 转位和弦
    3:  (13, 'Dm', 'Dm'),   # 长笛减缩 + 中提六度
    4:  (17, 'Dm', 'Dm'),   # 卡农(错一小节)+ 巴松叠低音
    5:  (21, 'F',  'F'),    # F 大调新旋律(木管)
    6:  (25, 'Gm', 'Gm'),   # g 小调:中提主题 + 震音
    7:  (29, 'Eb', 'Eb'),   # 降 E:hemiola + 一提主题
    8:  (33, 'A7', 'A7'),   # 属七:弱音小号主题 + 滚奏
    9:  (37, 'A7', 'E'),    # 紧接:低音错两小节进入
    10: (41, 'A7', 'A7'),   # 高潮 1:长号低音 + 全奏
    11: (45, 'Dm', 'Dm'),   # 高潮 2:解决 + 增时头
}
FUGUE_H = {49: 'Dm', 50: 'Dm', 51: 'A7', 52: 'Dm', 53: 'Am', 54: 'Am', 55: 'E7', 56: 'Am',
           57: 'Dm', 58: 'Dm', 59: 'A7', 60: 'Dm', 61: 'Am', 62: 'Am', 63: 'E7', 64: 'Am',
           65: 'Bb', 66: 'Bb', 67: 'Gm', 68: 'Gm', 69: 'Dm', 70: 'Dm', 71: 'A7', 72: 'A7',
           73: 'Am', 74: 'Am', 75: 'E7', 76: 'E7', 77: 'Eb', 78: 'Eb', 79: 'A7', 80: 'A7',
           81: 'Dm', 82: 'Dm', 83: 'A7', 84: 'A7',
           85: 'D', 86: 'D', 87: 'Bm', 88: 'Bm', 89: 'G', 90: 'G', 91: 'A', 92: 'A',
           93: 'D', 94: 'D', 95: 'D', 96: 'D'}


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
        ('drums', CH['drums'], 128, 48, (0, 127), 64, 30),   # Orchestra Kit
        ('timpani', CH['timpani'], *PROGS['timpani']),
        ('horn', CH['horns'], *PROGS['horn']),
        ('trumpet', CH['brass'], *PROGS['trumpet']),    # 先占 ch13
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

    s.tempo(54, B(1)); s.tempo(84, B(5)); s.tempo(96, B(49))
    s.tempo(104, B(81)); s.tempo(72, B(85))

    # ---------------- 引子(m1-4) ----------------
    for n in range(1, 5):
        s.note('bass', 38, 44, B(n), 4.0)
        s.chord('organ', (38, 50), 40, B(n), 4.0)
    s.note('bell', 74, 46, B(1), 3.0)
    for t, p, d in [(B(1), 62, 1.5), (B(1) + 1.5, 61, 0.5), (B(1) + 2.0, 57, 1.0),
                    (B(3), 74, 1.5), (B(3) + 1.5, 73, 0.5), (B(3) + 2.0, 69, 1.0)]:
        s.note('celli' if t < B(3) else 'vln1', p, 60, t, d)   # X 碎片 + 主题预示
    s.arp('harp', HARP['Dm'], 42, B(1) + 2, 0.5, 1, 1.5)
    s.note('timpani', 38, 42, B(4) + 3, 1.0)
    dyn('celli', 34, 1); dyn('vln1', 30, 3); dyn('organ', 28, 1); dyn('bass', 30, 1)

    # ---------------- 帕萨卡利亚(m5-48) ----------------
    # St1-4:d 小调低音 + 一提主题 / 对位 / 减缩 / 卡农
    for st, bar0 in [(1, 5), (2, 9), (3, 13), (4, 17)]:
        g = GROUND['Dm']
        for i, p in enumerate(g):
            s.note('bass', p, 58, B(bar0) + i, 0.92)
            s.note('celli', p + 12, 54, B(bar0) + i, 0.92)
        if st == 1:
            for t, p, d in T1:
                s.note('vln1', p, 92, B(bar0) + t, d)
        if st == 2:
            for t, p, d in CM:
                s.note('oboe', p, 86, B(bar0) + t, d)
            for n in range(bar0, bar0 + 4):
                ch = ['Dm', 'Dm', 'Dm', 'Dm'][n - bar0]
                a, b2 = INV6['Dm']
                s.chord('vla', a, 48, B(n), 4.0)
                s.chord('vln2', b2, 50, B(n), 4.0)
        if st == 3:
            for t, p, d in dimin(T1):
                s.note('flute', p, 80, B(bar0) + t, d)
            for t, p, d in T1:
                s.note('vla', p - 9 if p - 9 >= 48 else p - 5, 62, B(bar0) + t, d * 0.9)
            for t, p in [(B(13) + 2, 86), (B(13) + 4, 89), (B(15) + 3, 88), (B(15) + 5, 93)]:
                s.note('celesta', p, 50, t, 1.0)
        if st == 4:
            s.prog('bassoon', *PROGS['bassoon'][:2], B(17))
            for t, p, d in T1:
                s.note('vln1', p, 90, B(bar0) + t, d)
            for t, p, d in T1:
                if t < 8:
                    s.note('vln2', p, 86, B(bar0 + 1) + t, d)  # 卡农:错一小节(2 小节后断)
            for i, p in enumerate(g):
                s.note('bassoon', p + 12, 52, B(bar0) + i, 0.92)  # 巴松叠低音(混色)
        s.arp('harp', HARP['Dm'], 54, B(bar0), 0.5, 1, 2.0) if st in (1, 2, 3) else None
    for bn, v in [(5, 52), (9, 56), (13, 58), (17, 60)]:
        dyn('vln1', v, bn); dyn('celli', v - 4, bn); dyn('bass', v - 4, bn)
    dyn('oboe', 52, 9); dyn('flute', 54, 13); dyn('vla', 50, 13); dyn('bassoon', 50, 17)

    # St5(F):木管新旋律 + 拨弦
    s.prog('vln1', *PROGS['vln1_pizz'][:2], B(21))
    s.prog('vln2', *PROGS['vln2_pizz'][:2], B(21))
    s.prog('vla', *PROGS['vla_pizz'][:2], B(21))
    for i, p in enumerate(GROUND['F']):
        s.note('bass', p, 56, B(21) + i, 0.92)
        s.note('celli', p + 12, 52, B(21) + i, 0.92)
    for t, p, d in M_F:
        s.note('flute', p, 84, B(21) + t, d)
    for t, p, d in O_F:
        s.note('oboe', p, 74, B(21) + t, d)
    for n in range(21, 25):
        ch = ['F', 'F', 'F', 'F'][n - 21]
        s.chord('vln1', (69, 72, 77), 46, B(n), 0.6)
        if n < 24:
            s.chord('vln2', (65, 69, 72), 44, B(n) + 2, 0.6)
        s.chord('vla', (57, 60, 65), 42, B(n), 0.6)
        s.arp('harp', HARP['F'], 50, B(n), 0.5, 1, 2.0)
    dyn('flute', 56, 21); dyn('oboe', 50, 21)

    # St6(Gm):中提主题(移调)+ 震音
    s.prog('vln1', *PROGS['vln1_trem'][:2], B(25))
    s.prog('vln2', *PROGS['vln2_trem'][:2], B(25))
    s.prog('vla', *PROGS['vla_slow'][:2], B(25))
    for i, p in enumerate(GROUND['Gm']):
        s.note('bass', p, 56, B(25) + i, 0.92)
        s.note('celli', p + 12, 52, B(25) + i, 0.92)
    for t, p, d in T(T1, -5):
        s.note('vla', p, 84, B(25) + t, d)                      # 主题传递:中提琴(g 小调)
    for t, p, d in T(CM, -17):
        s.note('bassoon', p, 70, B(25) + t, d)                  # 对位移调(巴松)
    for n in range(25, 29):
        s.chord('vln1', (55, 58, 62), 44, B(n), 4.0)
        s.chord('vln2', (67, 71, 74), 42, B(n), 4.0)
    dyn('vla', 54, 25); dyn('bassoon', 50, 25); dyn('vln1', 42, 25); dyn('vln2', 40, 25)

    # St7(Eb):hemiola 低音 + 一提主题(移调)+ 钢片琴
    s.prog('vln1', *PROGS['vln1_slow'][:2], B(29))
    s.prog('vla', *PROGS['vla_trem'][:2], B(29))
    t0 = B(29)
    for i, p in enumerate(HEMIOLA[0]):
        s.note('bass', p, 58, t0, HEMIOLA[1][i % 3] - 0.08)
        t0 += HEMIOLA[1][i % 3]
    for i, p in enumerate(GROUND['Eb']):
        s.note('celli', p + 12, 52, B(29) + i, 0.92)            # 大提保持 4/4 律动(交叉节奏)
    for t, p, d in T(T1, -11):
        s.note('vln1', p, 90, B(29) + t, d)
    for n in range(29, 33):
        s.chord('vln2', (63, 67, 70), 42, B(n), 4.0)
        s.chord('vla', (55, 58), 40, B(n), 4.0)
    for t, p in [(B(30), 84), (B(30) + 2, 88), (B(31) + 2, 86), (B(31) + 4, 91)]:
        s.note('celesta', p, 48, t, 1.0)
    dyn('vln1', 54, 29); dyn('vla', 42, 29); dyn('vln2', 40, 29)

    # St8(A7):弱音小号主题 + 滚奏
    s.prog('vln1', *PROGS['vln1_trem'][:2], B(33))
    s.prog('hmn_trumpet', *PROGS['hmn_trumpet'][:2], B(33))
    for i, p in enumerate(GROUND['A7']):
        s.note('bass', p, 60, B(33) + i, 0.92)
        s.note('celli', p + 12, 54, B(33) + i, 0.92)
    for t, p, d in T(T1, -5):
        s.note('hmn_trumpet', p, 86, B(33) + t, d)              # 主题传递:弱音小号(属七)
    s.roll('timpani', 45, 34, 66, B(33), B(37), step=0.25)
    for n in range(33, 37):
        s.chord('vln1', (57, 61, 64), 46, B(n), 4.0)
        s.chord('vln2', (69, 73, 76), 44, B(n), 4.0)
        s.chord('vla', (57, 61, 64), 42, B(n), 4.0)
    dyn('hmn_trumpet', 70, 33); dyn('vln1', 62, 33); dyn('vln2', 60, 33); dyn('vla', 58, 33)
    dyn('bass', 62, 33)

    # St9:紧接(低音错两小节进入)+ 碎片
    for i, p in enumerate(GROUND['A7']):
        s.note('celli', p + 12, 58, B(37) + i, 0.92)
    for i, p in enumerate(GROUND['E']):
        s.note('bass', p, 60, B(39) + i, 0.92)                  # E 调答题式进入
    for t, p, d in [(B(37), 69, 1.5), (B(37) + 1.5, 68, 0.5), (B(37) + 2.0, 64, 0.5),
                    (B(38), 67, 1.0), (B(38) + 1, 69, 1.0), (B(38) + 2, 71, 1.0),
                    (B(38) + 3, 72, 1.0), (B(39), 74, 1.5), (B(39) + 1.5, 73, 0.5),
                    (B(39) + 2.0, 69, 0.5), (B(40), 71, 1.0), (B(40) + 1, 72, 1.0),
                    (B(40) + 2, 74, 1.0), (B(40) + 3, 76, 1.0)]:
        s.note('vln1', p, 84, t, d)
    for t, p, d in [(B(38), 64, 1.5), (B(38) + 1.5, 63, 0.5), (B(38) + 2.0, 59, 0.5),
                    (B(39), 62, 1.0), (B(39) + 1, 64, 1.0), (B(39) + 2, 66, 1.0),
                    (B(39) + 3, 67, 1.0), (B(40), 69, 1.5), (B(40) + 1.5, 68, 0.5),
                    (B(40) + 2.0, 64, 0.5)]:
        s.note('vln2', p, 80, t, d)
    s.prog('vln1', *PROGS['vln1_slow'][:2], B(37))
    s.prog('vln2', *PROGS['vln2_slow'][:2], B(37))
    dyn('vln1', 52, 37); dyn('vln2', 48, 37); dyn('celli', 56, 37); dyn('bass', 56, 39)

    # St10-11:高潮(长号低音 + 全奏 + 增时头)
    s.prog('vln1', *PROGS['vln1_slow'][:2], B(41))
    s.prog('vln2', *PROGS['vln2_slow'][:2], B(41))
    s.prog('vla', *PROGS['vla_slow'][:2], B(41))
    s.prog('trombone', *PROGS['trombone'][:2], B(41))
    for st, bar0, key in [(10, 41, 'A7'), (11, 45, 'Dm')]:
        for i, p in enumerate(GROUND[key]):
            s.note('trombone', p + 12, 94, B(bar0) + i, 0.9)
            s.note('bass', p, 72, B(bar0) + i, 0.9)
        for n in range(bar0, bar0 + 4):
            chk = ['A7', 'A7', 'A7', 'A7'] if key == 'A7' else ['Dm', 'Dm', 'Dm', 'Dm']
            s.chord('vln2', (FIFTH[chk[n - bar0]] + 12, CHT[chk[n - bar0]][1]), 56, B(n), 4.0)
            s.chord('vla', (FIFTH[chk[n - bar0]], CHT[chk[n - bar0]][1] - 4), 52, B(n), 4.0)
            s.chord('horn', (ROOT8[chk[n - bar0]], FIFTH[chk[n - bar0]]), 62, B(n), 2.0)
            s.note('celli', ROOT8[chk[n - bar0]], 60, B(n), 2.0)
            s.arp('harp', HARP[chk[n - bar0]], 62, B(n), 0.5, 1, 2.0)
    for t, p, d in T(T1, -5):                                    # 主题:一提(属七,高八度)
        s.note('vln1', p + 12, 96, B(41) + t, d)
    for t, p, d in X_AUG:                                        # 增时头:解决段
        s.note('vln1', p, 96, B(45) + t, d)
        s.note('choir', p - 12, 60, B(45) + t, d)
    for n in range(41, 45):
        s.chord('choir', CHOIR['A7'], 54, B(n), 4.0)
    s.roll('timpani', 45, 40, 82, B(41), B(45), step=0.25)
    s.note('drums', 49, 92, B(41), 1.5)
    s.note('drums', 36, 88, B(41), 0.6)
    s.note('timpani', 38, 80, B(45), 0.8)
    s.note('timpani', 38, 76, B(48), 1.0)
    s.note('drums', 49, 90, B(45), 1.5)
    s.note('drums', 36, 86, B(45), 0.6)
    s.prog('glock', *PROGS['glock'][:2], B(45))
    for t, p in [(B(45), 86), (B(45) + 2, 93), (B(46), 88), (B(46) + 2, 96),
                 (B(47), 86), (B(47) + 2, 91), (B(48), 88)]:
        s.note('glock', p, 52, t, 1.5)
    for bn, v in [(41, 74), (43, 82), (45, 84), (47, 80)]:
        dyn('vln1', v, bn); dyn('trombone', v - 6, bn); dyn('bass', v - 8, bn)
        dyn('choir', v - 18, bn); dyn('vln2', v - 10, bn); dyn('vla', v - 12, bn)
        dyn('horn', v - 10, bn); dyn('celli', v - 12, bn); dyn('harp', 56, 41)

    # ---------------- 赋格(m49-80) ----------------
    for n in range(49, 85):
        ch = FUGUE_H[n]
        s.note('bass', ROOT[ch], 56, B(n), 4.0)
    # 进入 1:大提琴(主题,d,低八度)
    for t, p, d in T(T1, -12):
        s.note('celli', p, 90, B(49) + t, d)
    # 对题 1:大提琴
    for t, p, d in T(CS, -12):
        s.note('celli', p, 72, B(53) + t, d)
    # 进入 2:中提琴(答题,a,低八度)
    for t, p, d in T(ANS, -12):
        s.note('vla', p, 88, B(53) + t, d)
    # 对题 2:中提琴
    for t, p, d in T(CS, -7):
        s.note('vla', p, 70, B(57) + t, d)
    # 进入 3:二提(主题,d)
    for t, p, d in T1:
        s.note('vln2', p, 90, B(57) + t, d)
    # 对题 3:二提
    for t, p, d in CS:
        s.note('vln2', p + 12, 70, B(61) + t, d)
    # 进入 4:一提(答题,a)
    for t, p, d in ANS:
        s.note('vln1', p, 92, B(61) + t, d)
    # 对题 4:一提
    for t, p, d in CS:
        s.note('vln1', p + 12, 72, B(65) + t, d)
    # 间插段 1(m65-68):对题序列(Bb/Gm),木管对话(各 2 小节)
    for t, p, d in T(CS, -7):
        if t < 8:
            s.note('flute', p + 12, 74, B(65) + t, 0.4 if t + d > 8 else d)
    for t, p, d in T(CS, -7):
        if t < 8:
            s.note('clarinet', p + 12, 72, B(67) + t, 0.4 if t + d > 8 else d)
    s.prog('clarinet', *PROGS['clarinet'][:2], B(65))
    for n in range(65, 69):
        ch = FUGUE_H[n]
        s.chord('vln2', (FIFTH[ch] + 12, CHT[ch][1]), 44, B(n), 4.0)
        s.chord('vla', (FIFTH[ch], CHT[ch][1] - 4), 42, B(n), 4.0)
    # 进入 5:小号(主题,高八度)+ 大管(主题,低八度)
    s.prog('trumpet', *PROGS['trumpet'][:2], B(69))
    s.prog('bassoon', *PROGS['bassoon'][:2], B(69))
    for t, p, d in T(T1, 12):
        s.note('trumpet', p, 88, B(69) + t, d)
    for t, p, d in T(T1, -12):
        s.note('bassoon', p, 80, B(69) + t, d)
    # 进入 6:圆号(答题,a)
    for t, p, d in T(ANS, -12):
        s.note('horn', p, 84, B(73) + t, d)
    # 间插段 2(m77-80):X 碎片序列(Eb→A7)+ 震音渐强
    s.prog('vln1', *PROGS['vln1_trem'][:2], B(77))
    s.prog('vln2', *PROGS['vln2_trem'][:2], B(77))
    s.prog('vla', *PROGS['vla_trem'][:2], B(77))
    for t, p, d in [(B(77), 75, 1.5), (B(77) + 1.5, 74, 0.5), (B(77) + 2.0, 70, 0.5),
                    (B(77) + 2.5, 70, 0.5), (B(77) + 3.0, 72, 1.0),
                    (B(78), 73, 1.0), (B(78) + 1, 75, 1.0), (B(78) + 2, 77, 1.0),
                    (B(78) + 3, 78, 1.0)]:
        s.note('flute', p, 82, t, d)                            # X at Eb(高八度)
    for t, p, d in [(B(79), 69, 1.5), (B(79) + 1.5, 68, 0.5), (B(79) + 2.0, 64, 0.5),
                    (B(79) + 2.5, 64, 0.5), (B(79) + 3.0, 66, 1.0),
                    (B(80), 67, 1.0), (B(80) + 1, 69, 1.0), (B(80) + 2, 71, 1.0),
                    (B(80) + 3, 72, 1.0)]:
        s.note('oboe', p, 84, t, d)                             # X at A(属)
    s.roll('timpani', 33, 35, 72, B(79), B(81), step=0.25)
    for n in range(77, 81):
        ch = FUGUE_H[n]
        s.chord('vln1', (CHT[ch][1], CHT[ch][2], CHT[ch][0] + 12), 48, B(n), 4.0)
        s.chord('vln2', (CHT[ch][0] + 16, CHT[ch][2] + 12), 44, B(n), 4.0)
        s.chord('vla', (CHT[ch][0], CHT[ch][1]), 42, B(n), 4.0)
    for bn, v in [(49, 66), (53, 70), (57, 68), (61, 72), (65, 66), (69, 74), (73, 76), (77, 70), (79, 80), (80, 86)]:
        dyn('vln1', v, bn); dyn('vln2', v - 2, bn); dyn('vla', v - 4, bn)
        dyn('celli', v - 4, bn); dyn('bass', v - 6, bn)
    dyn('flute', 50, 65); dyn('clarinet', 48, 67); dyn('bassoon', 56, 69)
    dyn('trumpet', 58, 69); dyn('horn', 54, 73); dyn('oboe', 58, 79)

    # ---------------- 高潮(m81-84,104):增时低音 + 倒影头 + 属驻留 ----------------
    s.prog('vln1', *PROGS['vln1_slow'][:2], B(81))
    s.prog('trombone', *PROGS['trombone'][:2], B(81))
    for t, p, d in [(B(81), 50, 2.0), (B(81) + 2, 49, 2.0), (B(82), 45, 2.0), (B(82) + 2, 45, 2.0),
                    (B(83), 46, 2.0), (B(83) + 2, 45, 2.0), (B(84), 43, 2.0), (B(84) + 2, 43, 2.0)]:
        s.note('trombone', p, 92, t, d)                         # 主题增时(X 头 + lamento,高八度)
    for t, p, d in [(B(81), 69, 1.5), (B(81) + 1.5, 71, 0.5), (B(81) + 2.0, 74, 0.5),
                    (B(81) + 2.5, 74, 0.5), (B(81) + 3.0, 76, 1.0),
                    (B(82), 72, 0.25), (B(82) + 0.25, 70, 0.25), (B(82) + 0.5, 69, 0.25),
                    (B(82) + 0.75, 67, 0.25), (B(82) + 1.0, 65, 0.25), (B(82) + 1.25, 64, 0.25),
                    (B(82) + 1.5, 62, 0.25), (B(82) + 1.75, 60, 0.25),
                    (B(83), 69, 1.5), (B(83) + 1.5, 68, 0.5), (B(83) + 2.0, 64, 0.5),
                    (B(83) + 2.5, 64, 0.5), (B(83) + 3.0, 66, 1.0)]:
        s.note('vln1', p, 94, t, d)                             # 倒影头 + 十六分下行 + X at A
    for n in range(81, 85):
        ch = FUGUE_H[n]
        s.chord('vln2', (CHT[ch][1] + 8, CHT[ch][2] + 8), 50, B(n), 4.0)
        s.chord('vla', (50, 57) if ch == 'Dm' else (57, 61), 46, B(n), 4.0)
        s.note('celli', ROOT8[ch], 58, B(n), 4.0)
        s.note('horn', ROOT8[ch], 54, B(n), 4.0)
    s.roll('timpani', 45, 45, 85, B(83), B(85), step=0.25)
    s.note('drums', 49, 94, B(83), 2.0)
    s.note('drums', 36, 90, B(83), 0.8)
    for bn, v in [(81, 78), (83, 90)]:
        dyn('vln1', v, bn); dyn('trombone', v - 4, bn); dyn('vln2', v - 8, bn)
        dyn('vla', v - 10, bn); dyn('celli', v - 8, bn); dyn('bass', v - 10, bn)

    # ---------------- 皮卡迪尾声(m85-96,72:D 大调) ----------------
    s.prog('vln2', *PROGS['vln2_slow'][:2], B(85))
    s.prog('vla', *PROGS['vla_slow'][:2], B(85))
    s.prog('trombone', *PROGS['tuba'][:2], B(85))
    s.prog('organ', *PROGS['organ'][:2], B(85))
    for t, p, d in [(tb, p, d) for tb, p, d in CHORALE if tb < 38]:
        s.note('vln1', p + 12, 90, B(85) + t, d)
        s.chord('choir', FIN_CHORDS[p], 54, B(85) + t, d)
        s.chord('organ', (p - 12, p - 5), 44, B(85) + t, d)
    for n in range(85, 95):
        ch = FUGUE_H[n]
        s.chord('vln2', (FIFTH[ch] + 12, CHT[ch][1]), 50, B(n), 4.0)
        s.chord('vla', (FIFTH[ch], CHT[ch][1] - 4), 46, B(n), 4.0)
        s.note('celli', ROOT8[ch], 56, B(n), 4.0)
        s.note('bass', ROOT[ch], 54, B(n), 4.0)
        s.note('tuba', ROOT[ch] + 12, 52, B(n), 4.0)
        s.chord('horn', (ROOT8[ch], FIFTH[ch]), 56, B(n), 2.0)
        s.arp('harp', HARP['D'], 56, B(n), 0.5, 1, 2.0)
    for n, v in [(85, 52), (89, 56), (93, 62)]:
        s.note('bell', 74, v, B(n), 3.0)
    s.roll('timpani', 38, 35, 72, B(93), B(95), step=0.25)
    s.note('timpani', 38, 80, B(95), 2.0)
    for n in (95, 96):
        s.chord('vln1', (74, 78, 81), 90, B(n), 4.0)
        s.chord('vln2', (66, 69), 64, B(n), 4.0)
        s.chord('vla', (62, 65), 60, B(n), 4.0)
        s.chord('celli', (50, 57), 62, B(n), 4.0)
        s.chord('bass', (38, 50), 58, B(n), 4.0)
        s.chord('horn', (50, 57), 60, B(n), 4.0)
        s.chord('choir', (62, 66, 69), 54, B(n), 4.0)
        s.chord('organ', (38, 50, 57), 50, B(n), 4.0)
        s.note('tuba', 38, 56, B(n), 4.0)
    for bn, v in [(85, 66), (89, 72), (93, 78), (95, 80)]:
        dyn('vln1', v, bn); dyn('choir', v - 14, bn); dyn('vln2', v - 10, bn)
        dyn('vla', v - 12, bn); dyn('celli', v - 8, bn); dyn('bass', v - 10, bn)
        dyn('horn', v - 10, bn); dyn('organ', v - 16, bn); dyn('tuba', v - 14, bn)


def main():
    ap = argparse.ArgumentParser(description='《深渊对位》生成器')
    ap.add_argument('--out', default='Contrapunctus_Abyssi.mid')
    args = ap.parse_args()
    s = Score(humanize=True, seed=42)
    build(s)
    s.flush(args.out)
    print('=== 段落时间表 ===')
    print('  引子     1-4   @54  →  0.0 - 17.8s')
    print('  帕萨卡利亚 5-48  @84  →  17.8 - 143.5s')
    print('  赋格    49-80  @96  →  143.5 - 223.5s')
    print('  高潮    81-84  @104 →  223.5 - 232.7s')
    print('  尾声    85-96  @72  →  232.7 - 272.7s')
    print('总时长 ≈ 273s ≈ 4:33')


if __name__ == '__main__':
    main()
