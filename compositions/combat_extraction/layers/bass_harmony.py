#!/usr/bin/env python3
"""bass_harmony.py — 贝斯 + 弦乐和声层(高潮段满配版)

母节 = 高潮段:16 小节全程满配。bass 16 分密集驱动(3+3+2 重音 0/1.5/3.0),
每轮 bar2 末高把位应答(对话链);弦乐长音全程;vln1 回声(bar1/3 句尾)。
- bass:base 100 / 重音 110(索引 0/6/12);应答 106/104/106/102;m18 尾 -10(回环)
- 应答音高(随和弦,28-52 内冲顶):Em 40,43,47,52 / C 36,43,48,52 / G 31,43,47,50 / D 38,45,50,45
- 弦乐:VOICES 全程 3.9 长音;rel 3/7/11(轮末 riser 小节)缩为 2.0(让位蓄积)
- vln1 回声:rel 0/2/4/6/8/10/12/14 的 3.5/3.75(和弦音,64-71 带)
- CC11:轮起点 80/82/84/82(微弧,无档位落差)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============ 主角贝斯(重心:用户要求 bass 是总旋律重心,合成器降为辅助) ============
# 16 小节和弦序(4 轮:轮1 Em Em C D,轮2-4 Em C G D)
CHORDS16 = ('Em', 'Em', 'C', 'D', 'Em', 'C', 'G', 'D',
            'Em', 'C', 'G', 'D', 'Em', 'C', 'G', 'D')

# 贝斯 16 分密集模式 × 3(4 轮渐进:轮1 陈述 → 轮2 高把位弧线 → 轮3 旋律跳跃 → 轮4 收束回 P1)
# P1 基础脉冲:根音 + 八度/五度交替
BASS_P1 = {
    'Em': (28, 40, 28, 43, 40, 43, 28, 40, 43, 47, 43, 40, 43, 40, 43, 28),
    'C':  (36, 48, 36, 43, 48, 43, 36, 48, 43, 48, 43, 40, 43, 40, 43, 36),
    'G':  (31, 43, 31, 38, 43, 38, 31, 43, 38, 43, 38, 35, 38, 35, 38, 31),
    'D':  (38, 50, 38, 45, 50, 45, 38, 50, 45, 50, 45, 42, 45, 42, 45, 38),
}
# P2 高把位弧线:后半小节向 52 爬升再回落(轮2)
BASS_P2 = {
    'Em': (28, 40, 28, 43, 40, 47, 40, 43, 47, 43, 47, 52, 47, 43, 40, 43),
    'C':  (36, 48, 36, 43, 48, 43, 48, 52, 48, 43, 48, 52, 48, 43, 40, 43),
    'G':  (31, 43, 31, 38, 43, 38, 43, 47, 43, 38, 43, 50, 47, 43, 38, 43),
    'D':  (38, 50, 38, 45, 50, 45, 50, 52, 50, 45, 50, 52, 50, 45, 42, 45),
}
# P3 旋律跳跃:句首跳进 + 中段环绕 + 句尾冲顶(轮3)
BASS_P3 = {
    'Em': (28, 40, 28, 43, 40, 28, 43, 40, 47, 43, 47, 52, 43, 40, 43, 40),
    'C':  (36, 48, 36, 43, 48, 43, 36, 48, 43, 48, 43, 52, 48, 43, 40, 43),
    'G':  (31, 43, 31, 38, 43, 38, 31, 43, 38, 43, 38, 50, 43, 38, 35, 38),
    'D':  (38, 50, 38, 45, 50, 45, 38, 50, 45, 50, 45, 52, 50, 45, 42, 45),
}
BASS_MODES = (BASS_P1, BASS_P2, BASS_P3)
BASS_PLAN = (0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 0, 0, 0, 0)  # 每小节模式(4 轮渐进)

# 对话链:每轮 bar2 末高把位应答(4 音上行,冲顶音区 28-52)
BASS_ANSWER = {
    'Em': (40, 43, 47, 52),   # E2 G2 B2 E3
    'C':  (36, 43, 48, 52),   # C2 G2 C3 E3
    'G':  (31, 43, 47, 50),   # G1 G2 B2 D3
    'D':  (38, 45, 50, 45),   # D2 A2 D3 A2
}
ANSWER_VEL = (106, 104, 106, 102)

# 弦乐和声堆叠(声部低→高:celli / vla / vln2 / vln1)
# v7 和谐修正:Em 的 vln2 67→64(与 vla 齐奏)——67 与 hook 78(G5)大七度摩擦(64 次)
VOICES = {
    'Em': (40, 64, 64, 71),
    'C':  (36, 64, 67, 72),
    'G':  (43, 62, 67, 71),
    'D':  (38, 62, 66, 69),
}

# vln1 回声(降 8 度,和弦音,64-71 带;对话链:应答 hook 句尾)
ECHO_PAIR = {
    'Em': (64, 67),   # E4 G4
    'C':  (64, 67),   # E4 G4
    'G':  (62, 67),   # D4 G4 —— 避开弦乐长音顶声部 71(G 小节 vln1=71,同通道会重叠)
}
# 回声小节:每轮 bar1/bar3(rel 0/2/4/6/8/10/12/14)
ECHO_RELS = (0, 2, 4, 6, 8, 10, 12, 14)

BASS_VEL = 102          # 主角,全场最响;重音 +10 = 112(humanize ±2 后 <105 阈值不误计)
STR_VEL = 58            # 弦乐长音(满配统一)
CC11_TIER = (80, 82, 84, 82)   # 轮起点 CC11 微弧


def build(s, bar0, cycle, ch):
    """铺 16 小节母 loop(小节 = bar0 起),返回 bar0+16。"""
    B = 'bass_electric'
    V1, V2, VA, VC = 'vln1', 'vln2', 'vla', 'celli'

    def bt(bar):
        return (bar - 1) * 4

    def riff_dense(bar, mode, prog, vel, answer=False, shift=False):
        """16 分密集驱动(模式渐进);重音 3+3+2(0/1.5/3.0)或移位 3+2+3(0/1.25/2.75);
        answer:末 4 音换高把位应答(对话链);shift:每轮 bar3 重音移位(句法转)"""
        pat = BASS_MODES[mode][prog]
        acc = (0, 6, 10) if shift else (0, 6, 12)   # 3+2+3:0/1.5/2.5(间隔 3,2,3 个 8 分)
        if answer:
            pat = pat[:12] + BASS_ANSWER[prog]
        for i, p in enumerate(pat):
            if answer and i >= 12:
                v = ANSWER_VEL[i - 12]
            else:
                v = vel + (10 if i in acc else 0)
            s.note(B, p, v, bt(bar) + i * 0.25, 0.24)

    def strchord(bar, prog, vel, dur):
        c, v3, v5, r1 = VOICES[prog]
        # dur 3.9:换和弦时旧尾音在下一音头前收掉(砍'尾音盖音头'碰撞)
        s.note(VC, c, vel, bt(bar), dur)
        s.note(VA, v3, vel, bt(bar), dur)
        s.note(V2, v5, vel, bt(bar), dur)
        s.note(V1, r1, vel, bt(bar), dur)

    # CC11 微弧(轮起点 80/82/84/82)
    for name in (B, V1, V2, VA, VC):
        for i, ccv in enumerate(CC11_TIER):
            s.cc(name, 11, ccv, bt(bar0 + i * 4))

    # 全程:bass dense(模式渐进)+ 弦乐长音(rel 3/7/11 缩 2.0 让位 riser);rel 15 单独处理(回环)
    # 句法:每轮 bar3 重音移位 3+2+3(转),bar4 回归 3+3+2 收束;cycle1 模式轮次错位(防两圈机械)
    plan = BASS_PLAN if cycle == 0 else (1, 1, 1, 1, 2, 2, 2, 2, 0, 0, 0, 0, 1, 1, 1, 1)
    for i in range(15):
        riff_dense(bar0 + i, plan[i], CHORDS16[i], BASS_VEL,
                   answer=(i % 4 == 1), shift=(i % 4 == 2))   # 每轮 bar2 应答 / bar3 移位
        dur = 2.0 if i in (3, 7, 11) else 3.9
        strchord(bar0 + i, CHORDS16[i], STR_VEL, dur)
    strchord(bar0 + 15, 'Em', STR_VEL, 3.9)

    # vln1 回声(每轮 bar1/3 句尾 3.5/3.75)
    for rel in ECHO_RELS:
        bar = bar0 + rel
        p0, p1 = ECHO_PAIR[CHORDS16[rel]]
        s.note(V1, p0, 62, bt(bar) + 3.5, 0.2)
        s.note(V1, p1, 62, bt(bar) + 3.75, 0.2)

    # m18(rel 15)回环:尾 4 个 16 分降力(3.0 重音保留但轻,衔接 m3)
    for k in range(16):
        v = 102 + (10 if k in (0, 6, 12) else 0)
        if k >= 12:
            v -= 10
        s.note(B, BASS_P1['Em'][k], v, bt(bar0 + 15) + k * 0.25, 0.24)

    return bar0 + 16


if __name__ == '__main__':
    from lib.orch import Score
    from lib.progs import PROGS
    CH = {'bass_electric': 6, 'vln1': 2, 'vln2': 3, 'vla': 4, 'celli': 5}

    def make():
        sc = Score(humanize=True, seed=42)
        for role, c in CH.items():
            bank, prog, (lo, hi), pan, rev = PROGS[role]
            sc.add_instr(role, c, bank, prog, lo, hi, pan, rev)
            sc.cc(role, 7, 100, 0.0)
        return sc

    s0 = make()
    assert build(s0, 3, 0, CH) == 19
    s0.flush('/tmp/smk_bass.mid')
    s1 = make()
    assert build(s1, 3, 1, CH) == 19
    s1.flush('/tmp/smk_bass_c1.mid')
    print('bass_harmony 冒烟完成: /tmp/smk_bass.mid(cycle0)、/tmp/smk_bass_c1.mid(cycle1)')
