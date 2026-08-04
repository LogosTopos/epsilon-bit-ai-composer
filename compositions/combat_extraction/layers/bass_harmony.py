#!/usr/bin/env python3
"""bass_harmony.py — 贝斯 riff + 弦乐和声层(《搜打撤》战斗背景曲)

依据:docs/COMPOSITION_PLAN.md §2 结构表 / §4 和声与 riff 表 / §8 力度
本层角色:bass_electric(ch6) + vln1/vln2/vla/celli(ch2-5)

- 档1(m3-6, Em Em C D):贝斯 8 分 riff(§4 表),vel 76,CC11 60
- 档2(m7-10, Em C G D):8 分 riff vel 84,CC11 72;弦乐每小节 1 个 2 拍长音和弦
  (按"共 4 个/4 小节 + 2 拍后换"读法),vel 56
- 档3(m11-14, Em C G D):贝斯 16 分加倍(§4 示例结构:根音脉冲 + 八度/和弦音交替),
  vel 96,CC11 84;弦乐整小节长音 vel 62(更密);vln1 16 分 E 五声音型 76 78 81 78(vel 66)
- 呼吸(m15-16, Em Em):贝斯 riff 减半仅第 1/3 拍,vel 72,CC11 66;
  m16 最后 2 拍 E2(40)长音 1.5 拍;弦乐保持 Em 长音,vel 50
- cycle=1 微变:8 分 riff 每半小节左轮换 1 个 8 分(28 28 40 28 → 28 40 28 28),和声不变

弦乐和弦连接表(声部低→高:celli / vla / vln2 / vln1;功能按 E 小调标):
  Em(i):   (40, 64, 67, 71)  E2 + E4-G4-B4(根位)
  C(bVI):  (36, 64, 67, 72)  C2 + E4-G4-C5(一转位)
  G(bIII): (43, 62, 67, 71)  G3 + D4-G4-B4(二转位) —— 根音 31 低于 celli 下界 36,取 G3
  D(bVII): (38, 62, 66, 69)  D2 + D4-F#4-A4(根位)
  连接(上三声部,半音):Em→C (0,0,+1);C→G (-2,0,-1);G→D (0,-1,-2);D→Em (+2,+1,+2)
  —— 全部 ≤3、无声部交叉;celli 根音进行 40→36(-4)→43(+7,音区强制)→38(-5)→40(+2),
     其中 G 根音 31 超 celli 下界(36-76),该两处跨度无更优解,已注释说明
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# §4 贝斯 riff 表(8 分 ×8/小节)
RIFF = {
    'Em': (28, 28, 40, 28, 28, 40, 28, 35),
    'C':  (36, 36, 48, 36, 36, 48, 36, 43),
    'G':  (31, 31, 43, 31, 31, 43, 31, 38),
    'D':  (38, 38, 50, 38, 38, 50, 38, 45),
}

# 档3 16 分加倍(§4 示例结构):每 8 分拆两发 [X, 根音],
# X 按 根音→八度→和弦音→八度 交替;后半小节的和弦音换五度(Em: 43→35,即 riff 末音)
RIFF16 = {
    'Em': (28, 28, 40, 28, 43, 28, 40, 28, 28, 28, 40, 28, 35, 28, 40, 28),
    'C':  (36, 36, 48, 36, 40, 36, 48, 36, 36, 36, 48, 36, 43, 36, 48, 36),
    'G':  (31, 31, 43, 31, 35, 31, 43, 31, 31, 31, 43, 31, 38, 31, 43, 31),
    'D':  (38, 38, 50, 38, 42, 38, 50, 38, 38, 38, 50, 38, 45, 38, 50, 38),
}

# 弦乐和声堆叠(连接表见模块 docstring)
VOICES = {
    'Em': (40, 64, 67, 71),
    'C':  (36, 64, 67, 72),
    'G':  (43, 62, 67, 71),
    'D':  (38, 62, 66, 69),
}

# 档3 vln1 16 分 E 五声音型(§5)
FIG = (76, 78, 81, 78)

# §2 结构表:每档 4 小节(呼吸 2 小节)
TIERS = (
    ('Em', 'Em', 'C', 'D'),   # 档1 m3-6
    ('Em', 'C', 'G', 'D'),    # 档2 m7-10
    ('Em', 'C', 'G', 'D'),    # 档3 m11-14
    ('Em', 'Em'),             # 呼吸 m15-16
)
BASS_VEL = (76, 84, 96, 72)   # 档1/2/3/呼吸
STR_VEL = (56, 62, 50)        # 档2/3/呼吸
CC11_TIER = (60, 72, 84, 66)  # 各档起点(§8)


def build(s, bar0, cycle, ch):
    """铺 16 小节母 loop(小节 = bar0 起),返回 bar0+16。"""
    B = 'bass_electric'
    V1, V2, VA, VC = 'vln1', 'vln2', 'vla', 'celli'

    def bt(bar):
        return (bar - 1) * 4

    def riff8(bar, prog, vel):
        pat = list(RIFF[prog])
        if cycle == 1:   # 微变:每半小节 8 分次序左轮换(和声不变)
            pat = pat[1:4] + pat[:1] + pat[5:8] + pat[4:5]
        for i, p in enumerate(pat):
            s.note(B, p, vel, bt(bar) + i * 0.5, 0.48)

    def riff16(bar, prog, vel):
        for i, p in enumerate(RIFF16[prog]):
            s.note(B, p, vel, bt(bar) + i * 0.25, 0.24)

    def strchord(bar, prog, vel, dur):
        c, v3, v5, r1 = VOICES[prog]
        s.note(VC, c, vel, bt(bar), dur)
        s.note(VA, v3, vel, bt(bar), dur)
        s.note(V2, v5, vel, bt(bar), dur)
        s.note(V1, r1, vel, bt(bar), dur)

    # CC11 档位起点(§8):60/72/84/66
    for name in (B, V1, V2, VA, VC):
        for i, ccv in enumerate(CC11_TIER):
            s.cc(name, 11, ccv, bt(bar0 + i * 4))

    # 档1:8 分 riff
    for i, prog in enumerate(TIERS[0]):
        riff8(bar0 + i, prog, BASS_VEL[0])
    # 档2:8 分 riff + 弦乐 2 拍长音和弦(4 个/4 小节)
    for i, prog in enumerate(TIERS[1]):
        riff8(bar0 + 4 + i, prog, BASS_VEL[1])
        strchord(bar0 + 4 + i, prog, STR_VEL[0], 2.0)
    # 档3:16 分加倍 + 弦乐整小节长音 + vln1 16 分五声音型
    for i, prog in enumerate(TIERS[2]):
        riff16(bar0 + 8 + i, prog, BASS_VEL[2])
        strchord(bar0 + 8 + i, prog, STR_VEL[1], 4.0)
    for bar in range(bar0 + 8, bar0 + 12):
        for k in range(16):
            s.note(V1, FIG[k & 3], 66, bt(bar) + k * 0.25, 0.24)
    # 呼吸:riff 减半(仅第 1/3 拍)+ m16 长音收尾;弦乐保持 Em 长音
    for i in range(2):
        bar = bar0 + 12 + i
        s.note(B, 28, BASS_VEL[3], bt(bar), 0.48)
        s.note(B, 28, BASS_VEL[3], bt(bar) + 2.0, 0.48)
        strchord(bar, 'Em', STR_VEL[2], 4.0)
    s.note(B, 40, BASS_VEL[3], bt(bar0 + 13) + 2.5, 1.5)  # m16 最后 2 拍 E2 长音 1.5 拍
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
