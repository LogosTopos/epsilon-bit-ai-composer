#!/usr/bin/env python3
"""riff_texture.py — 《搜打撤》战斗背景曲:riff/纹理层

职责(规划 §5 角色):brass_stab(M2 刺刀)、guitar_dist(Hook)、choir、
piano_bang、synth_pad。16 小节母 loop(小节 = bar0 起),返回 bar0+16:
  rel 0-3   档1:本层静默
  rel 4-7   档2:brass_stab M2(vel 80)
  rel 8-11  档3:brass_stab M2(vel 90)+ guitar_dist Hook + choir + piano_bang + synth_pad
  rel 12-13 呼吸:choir Em 长音(vel 50),其余静默
和弦:rel 4-11 = Em|C|G|D 循环,rel 12-13 = Em(规划 §4)
M3 齐击:brass 在 4 小节圈第 4 小节第 4 拍(rel 7、11)奏 64(E4)vel 96,与贝斯/鼓同步;
        档1 圈(rel 3)按"档1 不出现"不发声
CC11:档2 72 / 档3 84 / 呼吸 66(本层角色全按档位)

设计决策(仅力度/细节微变,动机音高与规划一致):
  1. M2 为 8 分刺刀:每小节 0/0.5/1/1.5 拍 4 个短音,后半小节休止(dur 0.35),
     2 小节音高循环 64 65 64 65 | 64 65 67 65;beat 3.0 留空给 M3 齐击
  2. Hook cycle=1 微变:Em 小节末 2 音降八度(76 78 → 64 66)。高八度选项
     (88 90)中 90 超 guitar 音区上限 88,故选降八度(音级不变,不破和声)
  3. cycle=1 档3 其余小节(C/G/D):Hook 不铺满,改第 1/3 拍和弦音单音刺点
     (vel 70,dur 0.3),保持攻击性并防腻(规划 §6 cycle=1 微变)
  4. piano_bang G 小节根音 31(G1)超音区 36-84,整体上移八度用 43+55
     (根音+八度双音手势不变)
  5. synth_pad 选"仅档3 与合唱叠置"(vel 40):档2 长音已由 strings 层承担,
     避免重复(规划 §5 synth_pad 注明可只档3)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 和声表(规划 §4):小节和弦序
CHORDS = ('Em', 'C', 'G', 'D')

# M2 刺刀(规划 §3):2 小节循环音高,每小节 4 × 8 分(拍 0/0.5/1/1.5)
M2 = ((64, 65, 64, 65), (64, 65, 67, 65))

# Hook(规划 §3):每小节 8 × 8 分(拍 0-3.5)
HOOK = {
    'Em': (76, 78, 79, 78, 79, 78, 76, 78),   # 高音修复:B5/A5→G5(实测 79 高频占比最低)
    'C':  (72, 76, 77, 79, 77, 76, 72, 76),
    'G':  (71, 74, 76, 79, 76, 74, 71, 74),
    'D':  (69, 72, 74, 78, 74, 72, 69, 72),
}

# cycle=1 切分刺点(第 1/3 拍,和弦音单音,vel 70)——档3 C/G/D 小节
GUITAR_STAB = {
    'C': (72, 76),   # C5 E5
    'G': (71, 74),   # B4 D5
    'D': (69, 74),   # A4 D5
}

# 合唱/合成垫长音和弦(3 音;和弦音 +12,+12 低于音区 48 的 G 用 +24)
CHOIR_VOICE = {
    'Em': (52, 55, 59),
    'C':  (48, 52, 55),
    'G':  (55, 59, 62),
    'D':  (50, 54, 57),
}

# 钢琴低音重击根音(§3 M3 低音音级;G1=31 超音区 36-84,上移八度用 G2=43)
PIANO_ROOT = {'Em': 40, 'C': 36, 'G': 43, 'D': 38}

# 本层角色(规划 §5)
ROLES = ('brass_stab', 'guitar_dist', 'choir', 'piano_bang', 'synth_pad')


def build(s, bar0, cycle, ch):
    """16 小节母 loop(小节 = bar0 起),返回 bar0+16。
    s: Score;bar0: 起始小节;cycle: 0/1(母 loop 第几次);ch: 角色→通道映射"""
    for r in ROLES:
        assert r in ch, f'riff_texture: 通道映射缺少角色 {r}'

    def beat(rel, off):
        return (bar0 + rel - 1) * 4 + off

    def cc(role, val, rel):
        s.cc(role, 11, val, beat(rel, 0.0))

    # ---------------- 档2(rel 4-7):M2 刺刀 vel 80 ----------------
    # 先现:档1 末(m6 beat2.0 起)低力度预击 3 音(避开 3.0 M3 齐击位),切入不突兀
    for i, p in enumerate(M2[0][:3]):
        s.note('brass_stab', p, 55, beat(3, 2.0 + i * 0.5), 0.35)
    cc('brass_stab', 72, 4)
    for rel in range(4, 8):
        for i, p in enumerate(M2[(rel - 4) % 2]):
            s.note('brass_stab', p, 74, beat(rel, i * 0.5), 0.35)   # 让位贝斯

    # ---------------- 档3(rel 8-11):全奏 ----------------
    # 先现:档2 末(m10)铜管低力度预击(2.0/2.5/3.5,避开 3.0 M3 齐击)+ 吉他 2 音预击
    for i, p in enumerate(M2[0][:2]):
        s.note('brass_stab', p, 62, beat(7, 2.0 + i * 0.5), 0.35)
    s.note('brass_stab', M2[0][0], 62, beat(7, 3.5), 0.35)
    s.note('guitar_dist', HOOK['Em'][0], 48, beat(7, 2.5), 0.4)
    s.note('guitar_dist', HOOK['Em'][1], 55, beat(7, 3.0), 0.4)
    for role in ROLES:
        cc(role, 84, 8)
    for rel in range(8, 12):
        cname = CHORDS[(rel - 8) % 4]

        # M2 刺刀 vel 90(档3 末小节渐弱)
        brass_vel = 82 if rel < 11 else 62
        for i, p in enumerate(M2[(rel - 8) % 2]):
            s.note('brass_stab', p, brass_vel, beat(rel, i * 0.5), 0.35)

        # Hook:cycle 0 铺满全 riff;cycle 1 Em 小节微变、其余小节切分刺点
        if cycle == 1 and cname != 'Em':
            s.note('guitar_dist', GUITAR_STAB[cname][0], 70, beat(rel, 0.0), 0.3)
            s.note('guitar_dist', GUITAR_STAB[cname][1], 70, beat(rel, 2.0), 0.3)
        else:
            hook = list(HOOK[cname])
            if cycle == 1 and cname == 'Em':          # 小节末 2 音降八度
                hook[6], hook[7] = 64, 66
            # 力度斜坡:第一小节 70→96 渐入(切入不生硬);末小节 96→70 渐出
            if rel == 8:
                ramp = (62, 68, 74, 80, 84, 88, 88, 88)
            elif rel == 11:
                ramp = (88, 88, 84, 80, 74, 68, 64, 60)
            else:
                ramp = (88,) * 8
            for i, p in enumerate(hook):
                s.note('guitar_dist', p, ramp[i], beat(rel, i * 0.5), 0.4)

        # 合唱长音 + 合成垫叠置(m11 低力度渐入,m14 渐出)
        choir_vel = 40 if rel == 8 else (44 if rel == 11 else 50)   # 让位贝斯
        pad_vel = 30 if rel == 8 else (34 if rel == 11 else 40)
        s.chord('choir', CHOIR_VOICE[cname], choir_vel, beat(rel, 0.0), 3.9)
        s.chord('synth_pad', CHOIR_VOICE[cname], pad_vel, beat(rel, 0.0), 3.9)

        # 钢琴低音八度重击(第 1 拍;m11 轻、m14 更轻收束)
        bang_vel = 56 if rel == 8 else (62 if rel == 11 else 70)   # 让位贝斯
        r0 = PIANO_ROOT[cname]
        s.note('piano_bang', r0, bang_vel, beat(rel, 0.0), 0.3)
        s.note('piano_bang', r0 + 12, bang_vel, beat(rel, 0.0), 0.3)

    # ---------------- M3 齐击:档2/档3 圈第 4 小节第 4 拍(rel 7、11) ----------------
    for rel in (7, 11):
        s.note('brass_stab', 64, 96, beat(rel, 3.0), 0.3)

    # ---------------- 持续段(rel 12-13):轻层保持(吉他刺点/合唱/钢琴),无空闲 ----------------
    for role in ROLES:
        cc(role, 74, 12)
    for rel in (12, 13):
        s.chord('choir', CHOIR_VOICE['Em'], 46, beat(rel, 0.0), 3.9)
        s.note('guitar_dist', HOOK['Em'][0], 60, beat(rel, 0.0), 0.3)
        s.note('guitar_dist', HOOK['Em'][2], 60, beat(rel, 2.0), 0.3)
        r0 = PIANO_ROOT['Em']
        s.note('piano_bang', r0, 56, beat(rel, 0.0), 0.3)
        s.note('piano_bang', r0 + 12, 56, beat(rel, 0.0), 0.3)

    return bar0 + 16


if __name__ == '__main__':
    from lib.orch import Score
    from lib.progs import PROGS
    SMOKE_CH = {'piano_bang': 0, 'synth_pad': 1, 'guitar_dist': 10,
                'brass_stab': 12, 'choir': 14}
    s = Score()
    for role, chn in SMOKE_CH.items():
        bank, prog, (lo, hi), pan, rev = PROGS[role]
        s.add_instr(role, chn, bank, prog, lo, hi, pan, rev)
    build(s, 3, 0, SMOKE_CH)
    s.flush('/tmp/smk_riff.mid')
    print('冒烟:build(s, 3, 0, ch) → /tmp/smk_riff.mid(期望 0 音区告警 / 0 冲突)')
