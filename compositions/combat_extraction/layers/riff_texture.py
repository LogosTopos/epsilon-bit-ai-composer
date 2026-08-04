#!/usr/bin/env python3
"""riff_texture.py — 《搜打撤》战斗背景曲:riff/纹理层(高潮段满配版)

母节 = 高潮段(用户决策):16 小节全程满配,无档位,4 轮对话链横向叙事。
角色:brass_stab(M2 刺刀+M3)、hook(小号/合成器)、choir、piano_bang、synth_pad、
synth_rhythm(切分节奏层)、fx(riser+低脉冲)。
- hook 对话链:bar1 全 riff → bar2 缩刺点(让位 brass 插入+bass 应答)→
  bar3 全 riff(轮3 变奏)→ bar4 全 riff(轮4 末减力回环)
- 轮次微变:轮2 bar1 尾 2 音降 8 度;轮3 bar3 变奏(A5 经过音);轮4 bar4 减力
- brass M2 全程(0.75/1.25/2.75/3.25 互锁位)+ M3 rel 3/7/11 @3.0
- fx:rel 3/7/11 轮末 riser(五声上行 6 音,弦乐/pad/choir 让位 2.0)+ 每小节 0.0 低脉冲
CC11:轮起点 80/82/84/82(微弧)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 合成器版力度补偿(compose.py 注入:synth 时 = 6)
VOICE_BOOST = 0

# 16 小节和弦序(4 轮:轮1 Em Em C D,轮2-4 Em C G D)
CHORDS16 = ('Em', 'Em', 'C', 'D', 'Em', 'C', 'G', 'D',
            'Em', 'C', 'G', 'D', 'Em', 'C', 'G', 'D')

# M2 刺刀(半音威胁动机,两轮和谐修正后):57/58 = A3/Bb3,62 = D4。
# v5 降 5 度(64,65,67→59,60,62)后与 vln1 顶声部 71(大七度)及 pad 48 仍摩擦;
# v7 再降 60→58:与全部长音/短音层 ≥4 半音(实测 282→目标 ≤150 的关键砍项)
M2 = ((57, 58, 57, 58), (57, 58, 62, 58))
M2_SLOTS = (0.75, 1.25, 2.75, 3.25)   # 互锁位:填补 bass/hook 空隙
BRASS_VEL = (80, 88, 78, 88)

# Hook 稀疏点缀表(v7.1 用户决策:合成器 = 总旋律的辅助,重心在贝斯)
# 每和弦 4 槽音高(0.5 / 2.0 / 2.5 / 3.5 拍),E 小调五声高区,全部与长音/刺刀 ≥2 半音
# 小节用法:bar1(0.5,3.5) bar2(0.5,2.5) bar3(0.5,2.0,3.5) bar4(0.5,3.5)
HOOK_DOT = {
    'Em': (79, 78, 76, 76),   # A5 G5 E5 E5
    'C':  (79, 76, 72, 72),   # G5 E5 C5 C5
    'G':  (79, 76, 74, 74),   # G5 E5 D5 D5
    'D':  (78, 74, 71, 71),   # F#5 D5 B4 B4
}
HOOK_DOT_VEL = (72, 72, 66, 72)   # 辅助层力度(不越互锁阈值);rel 15 再 -8

# 节奏层切分和弦(57-64 带;v7 和谐修正:M2 降至 57/58 后,各小节避开其±1)
RHY_CHORD = {
    'Em': (55, 64),   # G3 E4
    'C':  (62, 64),   # D4 E4
    'G':  (55, 62),   # G3 D4
    'D':  (50, 62),   # D3 D4(根音+5 音)
}
RHY_SLOTS = (0.25, 1.0, 2.0, 3.0)

# 合唱/合成垫长音和弦(3 音;v7 和谐修正:Em/G/D 避开与 M2 的摩擦)
CHOIR_VOICE = {
    'Em': (52, 55, 64),
    'C':  (48, 52, 55),
    'G':  (55, 62, 67),
    'D':  (50, 54, 62),
}

# 钢琴低音重击根音(G1=31 超音区,上移八度用 G2=43)
PIANO_ROOT = {'Em': 40, 'C': 36, 'G': 43, 'D': 38}

# riser(rel 3/7/11 轮末,2.0-3.25 六音五声上行;和弦音避让长音摩擦)
RISER = {
    'Em': (64, 67, 69, 71, 74, 76),
    'D':  (62, 66, 69, 71, 74, 78),
}
RISER_VEL = (50, 58, 66, 74, 80, 86)   # 3.0 槽 80(humanize ±2 后 <84,不越互锁阈值)

CC11_TIER = (80, 82, 84, 82)   # 轮起点 CC11 微弧

ROLES = ('brass_stab', 'hook', 'choir', 'piano_bang', 'synth_pad',
         'synth_rhythm', 'fx')


def build(s, bar0, cycle, ch):
    """16 小节母 loop(小节 = bar0 起),返回 bar0+16。"""
    for r in ROLES:
        assert r in ch, f'riff_texture: 通道映射缺少角色 {r}'

    def beat(rel, off):
        return (bar0 + rel - 1) * 4 + off

    def cc(role, val, rel):
        s.cc(role, 11, val, beat(rel, 0.0))

    # CC11 微弧(轮起点 80/82/84/82)
    for role in ROLES:
        for i, ccv in enumerate(CC11_TIER):
            cc(role, ccv, i * 4)

    # ---------------- 全程:pad/choir 长音(rel 3/7/11 缩 2.0 让位 riser) ----------------
    for rel in range(16):
        cname = CHORDS16[rel]
        dur = 2.0 if rel in (3, 7, 11) else 3.9
        s.chord('synth_pad', CHOIR_VOICE[cname], 42, beat(rel, 0.0), dur)
        s.chord('choir', CHOIR_VOICE[cname], 50, beat(rel, 0.0), dur)

    # ---------------- brass M2 全程 + M3(rel 3/7/11 @3.0) ----------------
    for rel in range(16):
        cell = M2[rel % 2]
        for i, b in enumerate(M2_SLOTS):
            s.note('brass_stab', cell[i], BRASS_VEL[i], beat(rel, b), 0.35)
    for rel in (3, 7, 11):
        s.note('brass_stab', 57, 96, beat(rel, 3.0), 0.3)   # M3 齐奏(与 timpani/kick/bass)

    # ---------------- rhythm 节奏层全程 ----------------
    for rel in range(16):
        cname = CHORDS16[rel]
        for b in RHY_SLOTS:
            s.chord('synth_rhythm', RHY_CHORD[cname], 70, beat(rel, b), 0.25)

    # ---------------- piano 0.0 锚点重击(全程) ----------------
    for rel in range(16):
        r0 = PIANO_ROOT[CHORDS16[rel]]
        s.note('piano_bang', r0, 64, beat(rel, 0.0), 0.3)
        s.note('piano_bang', r0 + 12, 64, beat(rel, 0.0), 0.3)

    # ---------------- fx:每小节 0.0 低脉冲(57,电子心跳)+ 轮末 riser ----------------
    for rel in range(16):
        s.note('fx', 57, 42, beat(rel, 0.0), 0.22)
    for rel in (3, 7, 11):
        cname = CHORDS16[rel]
        for j, p in enumerate(RISER[cname]):
            s.note('fx', p, RISER_VEL[j], beat(rel, 2.0 + j * 0.25), 0.22)

    # ---------------- hook 稀疏点缀(辅助层;重心在 bass) ----------------
    for rel in range(16):
        cname = CHORDS16[rel]
        d0, d1, d2, d3 = HOOK_DOT[cname]
        k = rel % 4
        if k == 1:
            slots = ((0.5, d0, 0), (2.5, d2, 2))            # bar2:两音(让位刺刀/应答)
        elif k == 3:
            slots = ((0.5, d0, 0), (3.5, d3, 3))            # bar4:首尾(rel15 减力回环)
        else:
            slots = ((0.5, d0, 0), (2.0, d1, 1), (3.5, d3, 3))   # bar1/3:三音小句
        for b, p, slot in slots:
            v = HOOK_DOT_VEL[slot] + VOICE_BOOST
            if rel == 15:
                v -= 8
            s.note('hook', p, v, beat(rel, b), 0.3)

    return bar0 + 16


if __name__ == '__main__':
    from lib.orch import Score
    from lib.progs import PROGS
    SMOKE_CH = {'piano_bang': 0, 'synth_pad': 1, 'hook': 10,
                'brass_stab': 12, 'choir': 14, 'synth_rhythm': 15, 'fx': 7}
    s = Score()
    for role, chn in SMOKE_CH.items():
        bank, prog, (lo, hi), pan, rev = PROGS[role]
        s.add_instr(role, chn, bank, prog, lo, hi, pan, rev)
    build(s, 3, 0, SMOKE_CH)
    s.flush('/tmp/smk_riff_v7.mid')
    print('冒烟:build(s, 3, 0, ch) → /tmp/smk_riff_v7.mid(期望 0 音区告警 / 0 冲突)')
