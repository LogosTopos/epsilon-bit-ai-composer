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

# ============ 主角贝斯(用户要求:能被人看见的贝斯手) ============
# 设计:16 分驱动 + 高把位跳进(28↔43/47/50)+ 句尾 bend 滑音。
# 档1/2 用主题(3 拍 16 分 + 第 4 拍 8 分重音,有呼吸);档3 全 16 分密集驱动。
BASS_THEME = {
    'Em': [(28, 0.25), (40, 0.25), (28, 0.25), (43, 0.25), (40, 0.25), (28, 0.25), (43, 0.25), (40, 0.25),
           (47, 0.25), (43, 0.25), (40, 0.25), (43, 0.25), (40, 0.5)],
    'C':  [(36, 0.25), (48, 0.25), (36, 0.25), (43, 0.25), (48, 0.25), (43, 0.25), (36, 0.25), (48, 0.25),
           (43, 0.25), (48, 0.25), (40, 0.25), (43, 0.25), (40, 0.5)],
    'G':  [(31, 0.25), (43, 0.25), (31, 0.25), (38, 0.25), (43, 0.25), (38, 0.25), (31, 0.25), (43, 0.25),
           (38, 0.25), (43, 0.25), (35, 0.25), (38, 0.25), (35, 0.5)],
    'D':  [(38, 0.25), (50, 0.25), (38, 0.25), (45, 0.25), (50, 0.25), (45, 0.25), (38, 0.25), (50, 0.25),
           (45, 0.25), (50, 0.25), (42, 0.25), (45, 0.25), (42, 0.5)],
}
# 档3 全 16 分密集版(16 音/小节,高把位在拍 2/3)
BASS_DENSE = {
    'Em': (28, 40, 28, 43, 40, 43, 28, 40, 43, 47, 43, 40, 43, 40, 43, 28),
    'C':  (36, 48, 36, 43, 48, 43, 36, 48, 43, 48, 43, 40, 43, 40, 43, 36),
    'G':  (31, 43, 31, 38, 43, 38, 31, 43, 38, 43, 38, 35, 38, 35, 38, 31),
    'D':  (38, 50, 38, 45, 50, 45, 38, 50, 45, 50, 45, 42, 45, 42, 45, 38),
}

# 弦乐和声堆叠(连接表见模块 docstring)
VOICES = {
    'Em': (40, 64, 67, 71),
    'C':  (36, 64, 67, 72),
    'G':  (43, 62, 67, 71),
    'D':  (38, 62, 66, 69),
}

# 档3 vln1 16 分音型(和谐修正):随和弦取音,全部为和弦音。
# 原 (76,78,81,78):81 在 C/G 为外音,78 与 Hook 79 摩擦;统一 76/79 在 D 小节
# 与二提 F#4 八度半音摩擦(实测 103 次)——按和弦取音彻底消除
FIG_VAR = {
    'Em': (76, 79, 76, 79),
    'C':  (76, 79, 76, 79),
    'G':  (74, 79, 74, 79),
    'D':  (74, 78, 74, 78),
}

# §2 结构表:每档 4 小节(呼吸 2 小节)
TIERS = (
    ('Em', 'Em', 'C', 'D'),   # 档1 m3-6
    ('Em', 'C', 'G', 'D'),    # 档2 m7-10
    ('Em', 'C', 'G', 'D'),    # 档3 m11-14
    ('Em', 'Em'),             # 呼吸 m15-16
)
BASS_VEL = (88, 96, 104, 72)  # 档1/2/3/呼吸 —— 主角,全场最响
STR_VEL = (52, 58, 46)        # 档2/3/呼吸 —— 辅助让位
CC11_TIER = (60, 72, 84, 66)  # 各档起点(§8)


def build(s, bar0, cycle, ch):
    """铺 16 小节母 loop(小节 = bar0 起),返回 bar0+16。"""
    B = 'bass_electric'
    V1, V2, VA, VC = 'vln1', 'vln2', 'vla', 'celli'

    def bt(bar):
        return (bar - 1) * 4

    def riff_main(bar, prog, vel):
        """主角主题:16 分驱动 + 句尾 8 分重音 + bend 滑音(贝斯手的"手")"""
        t = bt(bar)
        pat = list(BASS_THEME[prog])
        if cycle == 1:   # 微变:高把位组(后 5 音)前后轮换,和声不变
            pat = pat[:8] + pat[9:] + pat[8:9]
        for i, (p, d) in enumerate(pat):
            is_tail = (i == len(pat) - 1)
            v = vel + (10 if is_tail else 0)      # 句尾重音(贝斯手的落点)
            dur = d * 0.92
            s.note(B, p, v, t, dur)
            if is_tail:
                s.bend(B, 2, t, d * 0.92, 0.22)   # 句尾推弦 +2 半音
            t += d

    def riff_dense(bar, prog, vel):
        """档3 全 16 分密集驱动"""
        for i, p in enumerate(BASS_DENSE[prog]):
            v = vel + (10 if i % 4 == 0 else 0)   # 每拍头重音
            s.note(B, p, v, bt(bar) + i * 0.25, 0.24)

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

    # 档1:主角主题 + 弦乐低力度长音垫(角色化:弦乐不闪现)
    for i, prog in enumerate(TIERS[0]):
        riff_main(bar0 + i, prog, BASS_VEL[0])
        strchord(bar0 + i, prog, 38, 4.0)
    # 档2:主角主题 + 弦乐 2 拍长音和弦(首小节低力度渐入)
    for i, prog in enumerate(TIERS[1]):
        riff_main(bar0 + 4 + i, prog, BASS_VEL[1])
        strchord(bar0 + 4 + i, prog, 44 if i == 0 else STR_VEL[0], 2.0)
    # 档3:全 16 分密集驱动(主角爆发)+ 弦乐整小节长音 + vln1 音型
    for i, prog in enumerate(TIERS[2]):
        riff_dense(bar0 + 8 + i, prog, BASS_VEL[2])
        strchord(bar0 + 8 + i, prog, STR_VEL[1], 4.0)
    for i, bar in enumerate(range(bar0 + 8, bar0 + 12)):
        fig_vel = 50 if i == 0 else 66            # 首小节渐入
        fig = FIG_VAR[TIERS[2][i]]                # 随和弦取音(全部和弦音)
        for k in range(16):
            s.note(V1, fig[k & 3], fig_vel, bt(bar) + k * 0.25, 0.24)
    # 持续段(用户要求:Bass 大多数时间存在,不搞空闲段):
    # 16 分密集驱动保持(轻于档3),末小节第 4 拍降力(回环衔接)
    strchord(bar0 + 12, 'Em', STR_VEL[2], 4.0)
    strchord(bar0 + 13, 'Em', STR_VEL[2], 4.0)
    for i in range(2):
        for k in range(16):
            v = 90 if k % 4 == 0 else 82
            if i == 1 and k >= 12:
                v -= 10                        # m16 末 4 个 16 分让位回环
            s.note(B, BASS_DENSE['Em'][k], v, bt(bar0 + 12 + i) + k * 0.25, 0.24)
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
