#!/usr/bin/env python3
"""s_bt.py — 子节 S-BT:《子弹时间》(时间冻结人格,游戏时停状态用曲)

人格意象:「时间冻结」——玩家触发时停的瞬间,世界凝固:高频打击乐全部抽离,
只剩每拍的心跳 kick(8 分双发:重 80 + 轻 68)、深潜的低音长音与更静更长的
弦乐氛围;hook 化作"时间晶体"在每 2 小节的高区闪烁(稀疏、晶莹);
16 分驱动整体消失(母节核心驱动感被抽离 = "时间冻结"感)。
音乐不变速:168 BPM 保持(绝不写其他 tempo);低通感 = 减高频打击乐
(hat/ghost/开镲全撤)+ 抽离密度。

依据:THERMOCLINE_MUSIC_DESIGN.md §3(S-BT 规格行,2026-08 定稿)
+ STATUS 教训 #8 红线(2026-08 用户裁决):子节创作不再使用刺刀元素(铜管
刺刀一律不用;无 M3 齐奏;无 riser);音高一律母节素材原位(不移调/不叠置/
不扩展音区);只做层开关 + 密度/力度变形 + 人格化乐句重写(节奏型可新写,
音高取母节素材)。可留:hook 乐句(旋律辅助)/ synth_rhythm / fx riser
——S-BT 人格为"冻结",故 synth_rhythm 与 fx 一并撤空,只留 hook 作时间晶体。

受控改动(相对母节 v9):
- 结构:16 小节,Em-C-G-D 循环与 S1/S6 同网格;168 BPM 保持
- drums:满配 → 仅心跳 kick:每拍 8 分双发(重 80 @ 拍头 + 轻 68 @ 拍后 8 分,
  共 8 击/小节);snare/hat/幽灵音/开镲/crash/fill 全撤(减高频打击乐)
- timpani:全程 2.0 根音重击 → 仅轮末(rel 3/7/11/15)2.0 根音轻击(vel 52)
- bass:16 分密集驱动 → 全小节根音长音(vel 74)+ 每轮 bar2 单音 8 分应答
  (vel 64,母节 BASS_ANSWER 第 3 音原位)
- strings:长音 3.9(0.1 呼吸隙)→ 4.0 无隙连奏(比母节更长更静);vel 58 → 40
- pad/choir:长音 vel 42/50 → 32/38(氛围主导)
- piano:0.0 八度重击 → 单音轻锚(36)
- hook → 时间晶体:每 2 小节 1-2 音高区闪烁(轮弧线:轮 1 高开→轮 2 下沉→轮 3 呼应
  →轮 4 低收;vel 66-72,母节 hook 已验证音集原位,69-81 带);cycle1 轮中换色彩音
  (两圈微变防机械)
- vln1 回声:保留单音(3.5,vel 36;16 分对拆成单 8 分——无 16 分节奏型)
- 全撤:刺刀层 / synth_rhythm / fx(含 riser 与 0.0 低脉冲——冻结段无推进)
- CC11:74/76/78/76 轻档微弧(≥70,GUGS 响应 CC11 保可闻)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS

# 16 小节和弦序(与母节共享骨架:轮1 Em Em C D,轮2-4 Em C G D)
CHORDS16 = ('Em', 'Em', 'C', 'D', 'Em', 'C', 'G', 'D',
            'Em', 'C', 'G', 'D', 'Em', 'C', 'G', 'D')

# 弦乐和声堆叠(声部低→高:celli / vla / vln2 / vln1,母节 VOICES 原样)
VOICES = {
    'Em': (40, 64, 64, 71),
    'C':  (36, 64, 67, 72),
    'G':  (43, 62, 67, 71),
    'D':  (38, 62, 66, 69),
}
# pad/choir 和声(母节 riff_texture CHOIR_VOICE 原样)
CHOIR = {
    'Em': (52, 55, 64),
    'C':  (48, 52, 55),
    'G':  (55, 62, 67),
    'D':  (50, 54, 62),
}
# 低音根音(母节 bass 锚点口径:E1=28 / C2=36 / G1=31 / D2=38)
ROOT_LOW = {'Em': 28, 'C': 36, 'G': 31, 'D': 38}
# timpani 根音(母节 TIMP_ROOT 原样,2.0 重击位)
TIMP_ROOT = {'Em': 40, 'C': 36, 'G': 31, 'D': 38}
# piano 0.0 锚点(母节 PIANO_ROOT 原样)
PIANO_ROOT = {'Em': 40, 'C': 36, 'G': 43, 'D': 38}
# 母节 bass 对话链应答(每轮 bar2 高把位 BASS_ANSWER;取第 3 音作 S-BT 单音 8 分应答,原位)
BASS_ANSWER = {'Em': 47, 'C': 48, 'G': 47, 'D': 50}
# 时间晶体(弧线设计,2026-08-05 用户反馈'旋律不对'后重构):
#   旧版问题:轮头 8 次全用 81,主音 81/79 机械交替,节奏位固定,听感=节拍器;
#   新版:每轮(4 小节)一个微型弧线——轮 1 高开(81→76 五度下落)、轮 2 下沉
#   (G 和弦用低音 71)、轮 3 呼应(轮中换 E5 色彩)、轮 4 低收(79→74 落句 + 71
#   落底回环);节奏位仍 2.5/3.5(规格:每 2 小节 1-2 音);cycle1 轮中换色彩音防机械。
#   全部音高 ∈ 母节 hook 已验证音集 {69,71,72,74,76,78,79,81},原位不扩展。
CRYSTAL = {
    0:  ((2.5, 81, 72), (3.5, 76, 66)),   # 轮 1 Em:高开 + 五度下落
    2:  ((2.5, 79, 70),),                  # 轮 1 C:和弦音 G5
    4:  ((2.5, 81, 72), (3.5, 78, 66)),   # 轮 2 Em:高音 + F#5 经过色
    6:  ((2.5, 71, 70),),                  # 轮 2 G:低音 B4 下沉
    8:  ((2.5, 81, 72), (3.5, 76, 66)),   # 轮 3 Em:呼应轮 1
    10: ((2.5, 76, 70),),                  # 轮 3 C:三音 E5 色彩(非 G5)
    12: ((2.5, 79, 72), (3.5, 74, 66)),   # 轮 4 Em:低收(三音→七音落句)
    14: ((2.5, 71, 70),),                  # 轮 4 G:落底回环
}
CRYSTAL_C1 = {
    0:  ((2.5, 81, 72), (3.5, 76, 66)),
    2:  ((2.5, 76, 68),),                  # C:三音 E5
    4:  ((2.5, 81, 72), (3.5, 76, 66)),
    6:  ((2.5, 74, 68),),                  # G:五音 D5
    8:  ((2.5, 81, 72), (3.5, 78, 66)),
    10: ((2.5, 79, 68),),                  # C:和弦音 G5
    12: ((2.5, 79, 72), (3.5, 76, 66)),
    14: ((2.5, 74, 68),),                  # G:五音 D5
}
# vln1 回声(母节 ECHO_PAIR 第 1 音原位;只出现在 Em/C/G 小节,与母节同 rel)
ECHO_PAIR = {'Em': 64, 'C': 64, 'G': 62}
# 时间晶体小节:每 2 小节(rel 0/2/4/6/8/10/12/14;轮头 rel%4==0 取 2 音)
CRY_RELS = (0, 2, 4, 6, 8, 10, 12, 14)
ANSWER_RELS = (1, 5, 9, 13)      # 母节对话链 bar2 位(单音应答)
TIMP_RELS = (3, 7, 11, 15)       # 轮末(母节 M3 位,改轻击)

CC11_TIER = (74, 76, 78, 76)     # 轮起点轻档微弧(全 ≥70)

ROLE_CH = {'piano_bang': 0, 'synth_pad': 1, 'vln1': 2, 'vln2': 3, 'vla': 4,
           'celli': 5, 'bass_electric': 6, 'drums': 9, 'hook': 10,
           'timpani': 11, 'choir': 14}


def build(s, bar0, cycle, ch):
    """铺 16 小节 S-BT(小节 = bar0 起),返回 bar0+16。"""
    B = 'bass_electric'
    V1, V2, VA, VC = 'vln1', 'vln2', 'vla', 'celli'
    P, PA, CHO = 'piano_bang', 'synth_pad', 'choir'

    def bt(bar):
        return (bar - 1) * 4

    # CC11 轻档微弧(轮起点 74/76/78/76;全部 ≥70,GUGS 保可闻)
    for name in (B, V1, V2, VA, VC, P, PA, CHO, 'drums', 'timpani', 'hook'):
        for i, ccv in enumerate(CC11_TIER):
            s.cc(name, 11, ccv, bt(bar0 + i * 4))

    # ---------------- drums:仅心跳 kick(每拍 8 分双发 = 重 80 + 轻 68)----------------
    for i in range(16):
        for j in range(8):
            b = j * 0.5
            if j % 2 == 0:                       # 拍头:重 80
                s.note('drums', 36, 80, bt(bar0 + i) + b, 0.2)
            else:                                # 拍后 8 分:轻 68(双发 = 重+轻)
                s.note('drums', 36, 68, bt(bar0 + i) + b, 0.18)

    # ---------------- timpani:轮末 2.0 根音轻击(vel 52,母节重击位的轻声回响)----------------
    for rel in TIMP_RELS:
        s.note('timpani', TIMP_ROOT[CHORDS16[rel]], 52, bt(bar0 + rel) + 2.0, 0.4)

    # ---------------- bass:全小节根音长音 + 每轮 bar2 单音 8 分应答 ----------------
    for i in range(16):
        prog = CHORDS16[i]
        s.note(B, ROOT_LOW[prog], 74, bt(bar0 + i), 3.9)
        if i in ANSWER_RELS:                     # 母节对话链 bar2 位:单音应答(原位,8 分)
            s.note(B, BASS_ANSWER[prog], 64, bt(bar0 + i) + 2.5, 0.4)

    # ---------------- 氛围层:弦乐/pad/choir 无隙长音(4.0,比母节 3.9 更拉长、更静) ----------------
    for i, prog in enumerate(CHORDS16):
        c, v3, v5, r1 = VOICES[prog]
        for name, pitch, vel in ((VC, c, 40), (VA, v3, 40), (V2, v5, 40), (V1, r1, 40)):
            s.note(name, pitch, vel, bt(bar0 + i), 4.0)
        s.chord(PA, CHOIR[prog], 32, bt(bar0 + i), 4.0)
        s.chord(CHO, CHOIR[prog], 38, bt(bar0 + i), 4.0)
        s.note(P, PIANO_ROOT[prog], 36, bt(bar0 + i), 0.3)   # 0.0 单音轻锚
        # vln1 回声(bar1/3 句尾 3.5,单音;16 分对拆成单 8 分——无 16 分节奏型)
        if i in CRY_RELS and prog in ECHO_PAIR:
            s.note(V1, ECHO_PAIR[prog], 36, bt(bar0 + i) + 3.5, 0.25)

    # ---------------- hook 时间晶体:每 2 小节 1-2 音高区闪烁(轮弧线,母节素材原位) ----------------
    tbl = CRYSTAL if cycle == 0 else CRYSTAL_C1
    for rel, seq in tbl.items():
        t = bt(bar0 + rel)
        for off, p, v in seq:
            s.note('hook', p, v, t + off, 0.45 if off == 2.5 else 0.5)

    return bar0 + 16


if __name__ == '__main__':
    import contextlib, io
    s = Score(humanize=True, seed=42)
    for role, chn in ROLE_CH.items():
        # hook 不是 PROGS 键:按项目惯例映射到合成器嗓(synth_lead,主成品口径)
        bank, prog, (lo, hi), pan, rev = PROGS['synth_lead' if role == 'hook' else role]
        s.add_instr(role, chn, bank, prog, lo, hi, pan, rev)
        s.cc(role, 7, 100, 0.0)
    s.tempo(168, 0.0)
    assert build(s, 3, 0, ROLE_CH) == 19
    assert build(s, 19, 1, ROLE_CH) == 35
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        s.flush('S_BT.mid')
    out = buf.getvalue()
    print(out, end='')
    bad = out.count('[音区告警]') + out.count('  [冲突]')
    print(f'S-BT 冒烟: {"PASS" if bad == 0 else "FAIL"} S_BT.mid(音区告警/自检冲突 = {bad},32 小节两圈)')
    sys.exit(0 if bad == 0 else 1)
