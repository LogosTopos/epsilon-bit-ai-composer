#!/usr/bin/env python3
"""riff_texture.py — 《搜打撤》战斗背景曲:riff/纹理层(高潮段满配版)

母节 = 高潮段(用户决策):16 小节全程满配,无档位,4 轮对话链横向叙事。
角色:brass_stab(M2 刺刀+M3)、hook(小号/合成器)、choir、piano_bang、synth_pad、
synth_rhythm(切分节奏层)、fx(riser+低脉冲)。
- hook 对话链:bar1 全 riff → bar2 缩刺点(让位 brass 插入+bass 应答)→
  bar3 全 riff(轮3 变奏)→ bar4 全 riff(轮4 末减力回环)
- 轮次微变:轮2 bar1 尾 2 音降 8 度;轮3 bar3 变奏(A5 经过音);轮4 bar4 减力
- fx:rel 3/7/11 轮末 riser(五声上行 6 音,弦乐/pad/choir 让位 2.0)+ 每小节 0.0 低脉冲
CC11:轮起点 80/82/84/82(微弧)

v9 完全辅助化(用户决策,2026-08):stab 组 = 色彩点缀/推进,不再承担第二旋律面。
- ⚠️ 红线:stab 组含 humanize 峰值 hook ≤ 84、其余角色 ≤ 78;禁单角色每小节 > 4 音(audit 第 5 维验收)
- brass 密度 2/4/3/2 → 1/2/2/0(bar4 让位 M3/riser),vel 76-96 → 62-76,轮次力度波删除
- M3 齐奏 brass 96 → 76(冲击交给 timpani/kick/bass 三件套)
- rhythm 全程 4 落点 → 只轮 2/4 出场、每小节 2 落点(0.25/2.0 反拍),vel 70 → 58
- riser 50-86 → 42-72(尾音不越互锁阈值 84)
- hook 保持(v7.1 决策:唯一旋律辅助,vel 66-76)
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
# M2 刺刀 v8(用户诊断:半音锯齿+全外音不解决 = 不和谐主因):从 (57,58,...) 半音外音
# 改为'和弦分解刺刀'——每和弦三音上行+回落,全和弦音,带刺刀顿挫但和谐:
#   Em 5-7-1-7 / C 1-3-5-3 / G 3-5-1-5 / D 1-3-5-3
M2 = {
    'Em': (59, 62, 64, 62),   # B3 D4 E4 D4
    'C':  (60, 64, 67, 64),   # C4 E4 G4 E4
    'G':  (59, 62, 67, 62),   # B3 D4 G4 D4
    'D':  (62, 66, 69, 66),   # D4 F#4 A4 F#4
}
M3_PITCH = {'Em': 59, 'D': 62}   # M3 齐击:和弦 5 音/根音(与刺刀同源)

# Hook 乐句 v8.2(用户诊断:碎片点缀 = 门铃感/旋律怪;改为'句法化长音句'):
# 每轮 4 小节一句:bar1 长音(3.5,0.8 拍喘息)→ bar2 短音(2.5,让位 bass 应答)→
# bar3 短句(0.5/2.0 + 3.5 长音)→ bar4 短收(3.5)。音高随和弦五声、下行倾向,
# 轮 2/4 句头换五声高音(防机械)。
HOOK_PHRASE = {
    'Em': {'bar1': 76, 'bar2': 74, 'bar3': (79, 78, 76), 'bar4': 74},
    'C':  {'bar1': 72, 'bar2': 74, 'bar3': (79, 76, 72), 'bar4': 74},
    'G':  {'bar1': 71, 'bar2': 74, 'bar3': (79, 76, 71), 'bar4': 74},
    'D':  {'bar1': 69, 'bar2': 71, 'bar3': (78, 74, 69), 'bar4': 71},
}
HOOK_HIGH = {'Em': 81, 'C': 77, 'G': 79, 'D': 78}   # 轮2/4 句头高音(五声)
HOOK_LONG_VEL = 76    # 长音(喘息点),+BOOST 后 <84 不越互锁阈值
HOOK_SHORT_VEL = 66

# 节奏层切分和弦(57-64 带;v8 修正:C 小节原 (62,64) = 大七度(尖锐),改纯五度 (60,67))
RHY_CHORD = {
    'Em': (55, 64),   # G3 E4(六度)
    'C':  (60, 67),   # C4 G4(纯五度)
    'G':  (55, 62),   # G3 D4(纯五度)
    'D':  (50, 62),   # D3 D4(八度)
}

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
RISER_VEL = (42, 48, 54, 60, 66, 72)   # v9:全组 <78,推进感靠音符走向而非音量

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

    # ---------------- brass 刺刀乐句(v9:完全辅助化——密度 1/2/2/0,vel 62-76,不再承担第二旋律面) ----------------
    # 每轮:bar1 动机头 1 音 → bar2 刺刀插入 2 音(对话链保留,轻点)→
    #       bar3 2 音(呼应)→ bar4 0 音(让位 M3/riser)。全组 < 互锁阈值 84。
    STAB_SLOTS = ((0.75,), (0.75, 1.25), (0.75, 1.25), ())
    STAB_VEL = ((66,), (70, 76), (70, 76), ())
    for rel in range(16):
        cname = CHORDS16[rel]
        cell = M2[cname]
        for i, b in enumerate(STAB_SLOTS[rel % 4]):
            s.note('brass_stab', cell[i], STAB_VEL[rel % 4][i], beat(rel, b), 0.35)
    for rel in (3, 7, 11):
        s.note('brass_stab', M3_PITCH[CHORDS16[rel]], 76, beat(rel, 3.0), 0.3)   # M3 齐奏降力(76+humanize±2=78,冲击交给 timpani/kick/bass)

    # ---------------- rhythm 节奏层(v9:完全辅助化——只轮 2/4 出场、每小节 2 落点反拍;bar4 让位 M3/riser) ----------------
    # 每圈 6 小节 × 2 落点 × 2 音 = 24 音(原 112),vel 70 → 58(与 strings 同档垫底)
    for rel in range(16):
        if rel // 4 not in (1, 3):
            continue                         # 只轮 2/4 出场(轮 1/3 空窗,中频清空)
        if rel % 4 == 3:
            continue                         # bar4 让位 M3/riser
        cname = CHORDS16[rel]
        for b in (0.25, 2.0):
            s.chord('synth_rhythm', RHY_CHORD[cname], 58, beat(rel, b), 0.25)

    # ---------------- piano 0.0 锚点重击(全程) ----------------
    for rel in range(16):
        r0 = PIANO_ROOT[CHORDS16[rel]]
        s.note('piano_bang', r0, 64, beat(rel, 0.0), 0.3)
        s.note('piano_bang', r0 + 12, 64, beat(rel, 0.0), 0.3)

    # ---------------- fx:每小节 0.0 低脉冲(统一 57,v8 去掉轮3/4 的 59 外音)+ 轮末 riser ----------------
    for rel in range(16):
        s.note('fx', 57, 42, beat(rel, 0.0), 0.22)
    for rel in (3, 7, 11):
        cname = CHORDS16[rel]
        for j, p in enumerate(RISER[cname]):
            s.note('fx', p, RISER_VEL[j], beat(rel, 2.0 + j * 0.25), 0.22)

    # ---------------- hook 乐句(每轮一句:长音喘息 + 五声短句,轮2/4 句头高音) ----------------
    for rel in range(16):
        cname = CHORDS16[rel]
        ph = HOOK_PHRASE[cname]
        k = rel % 4
        hi = (rel // 4) % 2 == 1                 # 轮 2/4
        long_vel = HOOK_LONG_VEL + VOICE_BOOST - (8 if rel == 15 else 0)
        short_vel = HOOK_SHORT_VEL + VOICE_BOOST - (8 if rel == 15 else 0)
        if k == 0:                               # bar1:句头长音(3.5,喘息)
            p = HOOK_HIGH[cname] if hi else ph['bar1']
            s.note('hook', p, long_vel, beat(rel, 3.5), 0.8)
        elif k == 1:                             # bar2:短音(让位刺刀/bass 应答)
            s.note('hook', ph['bar2'], short_vel, beat(rel, 2.5), 0.3)
        elif k == 2:                             # bar3:短句 0.5/2.0 + 句尾长音
            p3 = ph['bar3']
            s.note('hook', p3[0], short_vel, beat(rel, 0.5), 0.3)
            s.note('hook', p3[1], short_vel, beat(rel, 2.0), 0.3)
            s.note('hook', p3[2], long_vel, beat(rel, 3.5), 0.8)
        else:                                    # bar4:短收(rel15 减力回环)
            s.note('hook', ph['bar4'], short_vel, beat(rel, 3.5), 0.3)

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
