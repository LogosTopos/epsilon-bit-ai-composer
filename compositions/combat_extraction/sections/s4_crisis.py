#!/usr/bin/env python3
"""s4_crisis.py — 子节 4:《危机版》(低血量/被追击,紧张化)

游戏场景:角色低血量 / 被追击。
人格意象:**绝境压迫**——心率型鼓点(心要跳出胸腔)+ 旋律层整体上移半音
的多调性紧张;bass 应答半音尖叫冲顶(52 音区上限);hook 喘息点变
"短促+重复"(喘不过气);唯一"冷静"的是原地不动的和声层(本子节人格签名)。

受控改动(相对母节 v9,依据:ARCHITECTURE §3 S4 规格 + 用户指令 2026-08):
- 多调性紧张:hook 与 brass_stab 全部音高 **+1 半音移调**(母节 HOOK_PHRASE/
  HOOK_HIGH/M2/M3_PITCH 素材整体 +1;brass 上限 69+1=70、hook 上限 81+1=82,
  均在 progs 音区 55-88 内);和声层(pad/choir/strings/piano/rhythm)保持原位,
  和弦进行网格不变——"和声层冷静"是本子节的人格签名
- BPM:build 内显式 s.tempo(168, (bar0-1)*4)(与母节同速,防连播拼接速度漂移)
- drums:kick 改"心率型"——每小节 8 个 8 分双发,重音错位(0.0/2.0 重 96、
  0.5/2.5 中 80、其余 68);snare 2/4(76);hat 16 分(66);幽灵音保留(52);
  rel 7/11 bar4 尾加 4 音 32 分 snare 急促收束(80/86/92/98,"绊脚"型急促
  fill——父会话补充指令"fill 加密为急促型");删 crash/开镲/母节大 fill
  (轮末推进主责在加密 riser,心率脉冲 = 鼓组身份)
- bass:母节 16 分模式保留(vel 108/重音 118,比母节 +4);每轮 bar2 应答改
  **半音尖叫冲顶**——末音顶到 bass 音区上限 52,倒数第二音半音趋近
  (Em/C/D: 51→52,G: 49→50);父建议冲 54/55 超出 progs 28-52,以
  "半音趋近顶到上限"替代;vel 110/108/110/106;m18 回环处理保留
- hook:乐句保留(vel 72-82,+6),音高全部 +1;**bar3 句尾长音(喘息点)改
  短促+重复**(3.5/3.75 两短音 78/72,"喘不过气"),bar1 句头长音保留
  (句法锚,防回退门铃碎片)
- brass:1/2/2/0 密度保留,音高全部 +1,vel 66-76;M3 齐奏 brass 76(音高 +1)
- timpani:2.0 根音(70/74/78/76,轮 4 双音滚保留)+ M3 齐击@3.0(80)
- rhythm:母节 v9 规格(只轮 2/4 出场、每小节 2 落点 0.25/2.0、vel 58),音高原位
  (⚠️ RHY_CHORD 55/67 超出 progs 声明 57-64——母节 v9 同款继承告警,非本子节新增)
- fx:riser 加密——每轮末 rel 3/7/11/15 都放(4 次,vel 46-76);0.0 低脉冲(44)
- piano:0.0 锚点(68,八度)
- strings/pad/choir:长音 62/46/54(比母节稍强);vln1 回声保留(62)
- CC11:84-88(轮起点 84/86/88/86,全曲最紧;GUGS 响应 CC11,全程 ≥74 保可闻)
- 强度定位:母节 + 紧迫(力度整体 +4-6)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS

# 16 小节和弦序(与母节共享骨架:轮1 Em Em C D,轮2-4 Em C G D)
CHORDS16 = ('Em', 'Em', 'C', 'D', 'Em', 'C', 'G', 'D',
            'Em', 'C', 'G', 'D', 'Em', 'C', 'G', 'D')

# ================= 移调 +1 半音的旋律素材(母节素材整体 +1,多调性紧张) =================
# 母节 M2 = (59,62,64,62)/(60,64,67,64)/(59,62,67,62)/(62,66,69,66)
# +1 后为和弦音的"半音紧张音"(单线乐句,无小二度堆叠)
M2_T = {
    'Em': (60, 63, 65, 63),
    'C':  (61, 65, 68, 65),
    'G':  (60, 63, 68, 63),
    'D':  (63, 67, 70, 67),
}
M3_PITCH_T = {'Em': 60, 'D': 63}          # 母节 59/62 +1

# 母节 HOOK_PHRASE 整体 +1(上限 82,在 progs 55-88 内)
HOOK_PHRASE_T = {
    'Em': {'bar1': 77, 'bar2': 75, 'bar3': (80, 79, 77), 'bar4': 75},
    'C':  {'bar1': 73, 'bar2': 75, 'bar3': (80, 77, 73), 'bar4': 75},
    'G':  {'bar1': 72, 'bar2': 75, 'bar3': (80, 77, 72), 'bar4': 75},
    'D':  {'bar1': 70, 'bar2': 72, 'bar3': (79, 75, 70), 'bar4': 72},
}
HOOK_HIGH_T = {'Em': 82, 'C': 78, 'G': 80, 'D': 79}   # 母节 81/77/79/78 +1

# ================= 原位素材(和声层/低音层不参与移调,与母节 v9 一致) =================
# 贝斯 16 分密集模式 × 3(母节 v8.1 可听性重构,原样保留)
BASS_P1 = {
    'Em': (28, 40, 43, 47, 40, 43, 47, 40, 43, 47, 43, 40, 47, 43, 40, 28),
    'C':  (36, 43, 48, 52, 43, 48, 52, 43, 48, 52, 48, 43, 52, 48, 43, 36),
    'G':  (31, 43, 47, 50, 43, 47, 50, 43, 47, 50, 47, 43, 50, 47, 43, 31),
    'D':  (38, 45, 50, 52, 45, 50, 52, 45, 50, 52, 50, 45, 52, 50, 45, 38),
}
BASS_P2 = {
    'Em': (28, 43, 47, 52, 43, 47, 52, 47, 43, 47, 52, 47, 43, 40, 43, 28),
    'C':  (36, 43, 48, 52, 48, 52, 48, 43, 48, 52, 48, 43, 52, 48, 43, 36),
    'G':  (31, 43, 47, 50, 47, 50, 47, 43, 47, 50, 47, 43, 50, 47, 43, 31),
    'D':  (38, 45, 50, 52, 50, 52, 50, 45, 50, 52, 50, 45, 52, 50, 45, 38),
}
BASS_P3 = {
    'Em': (28, 40, 28, 43, 47, 40, 43, 47, 40, 47, 43, 52, 47, 43, 40, 28),
    'C':  (36, 48, 36, 43, 52, 48, 43, 52, 48, 52, 43, 48, 52, 48, 43, 36),
    'G':  (31, 43, 31, 47, 50, 43, 47, 50, 43, 50, 47, 43, 50, 47, 43, 31),
    'D':  (38, 50, 38, 45, 52, 50, 45, 52, 50, 52, 45, 50, 52, 50, 45, 38),
}
BASS_MODES = (BASS_P1, BASS_P2, BASS_P3)
BASS_PLAN = (0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 0, 0, 0, 0)  # 每小节模式(4 轮渐进)

# S4 绝境应答(父指令:应答冲顶更"尖"):末音冲 bass 音区上限 52,倒数第二音
# 半音趋近(51→52 / 49→50,半音尖叫感);progs bass 上限 52,54/55 超出音区,
# 故以"半音趋近顶到上限"替代更高把位(单线乐句,半音紧张音不堆叠)
BASS_ANSWER = {
    'Em': (43, 47, 51, 52),
    'C':  (43, 48, 51, 52),
    'G':  (43, 47, 49, 50),
    'D':  (38, 50, 51, 52),
}
ANSWER_VEL = (110, 108, 110, 106)         # 母节 106/104/106/102 +4

# 弦乐和声堆叠(声部低→高:celli / vla / vln2 / vln1)
VOICES = {
    'Em': (40, 64, 64, 71),
    'C':  (36, 64, 67, 72),
    'G':  (43, 62, 67, 71),
    'D':  (38, 62, 66, 69),
}
ECHO_PAIR = {
    'Em': (64, 67), 'C': (64, 67), 'G': (62, 67), 'D': (62, 66),
}
ECHO_RELS = (0, 2, 4, 6, 8, 10, 12, 14)   # 每轮 bar1/3 句尾(vln1 回声)

# pad/choir 长音和弦(母节 v9 同表)
CHOIR_VOICE = {
    'Em': (52, 55, 64),
    'C':  (48, 52, 55),
    'G':  (55, 62, 67),
    'D':  (50, 54, 62),
}
RHY_CHORD = {
    'Em': (55, 64), 'C': (60, 67), 'G': (55, 62), 'D': (50, 62),
}
PIANO_ROOT = {'Em': 40, 'C': 36, 'G': 43, 'D': 38}
RISER = {'Em': (64, 67, 69, 71, 74, 76), 'D': (62, 66, 69, 71, 74, 78)}
RISER_VEL = (46, 52, 58, 64, 70, 76)      # 母节 42-72 → 46-76(+4,峰值恰在互锁阈值线内)
TIMP_ROOT = {'Em': 40, 'C': 36, 'G': 31, 'D': 38}
TIMP_VEL = (70, 74, 78, 76)               # 母节 66/70/74/72 +4(70-78)
CC11_TIER = (84, 86, 88, 86)              # 轮起点 CC11(全曲最紧;GUGS 响应 CC11)

ROLES = ('drums', 'bass_electric', 'vln1', 'vln2', 'vla', 'celli',
         'piano_bang', 'synth_pad', 'choir', 'hook', 'brass_stab',
         'timpani', 'fx', 'synth_rhythm')


def build(s, bar0, cycle, ch):
    """铺 16 小节 S4(小节 = bar0 起),返回 bar0+16。"""
    B = 'bass_electric'
    V1, V2, VA, VC = 'vln1', 'vln2', 'vla', 'celli'

    def bt(bar):
        return (bar - 1) * 4

    def riff_dense(bar, mode, prog, vel, answer=False, shift=False):
        """16 分密集驱动;重音 3+3+2(0/1.5/3.0)或移位 3+2+3;answer:末 4 音高把位应答"""
        pat = BASS_MODES[mode][prog]
        acc = (0, 6, 10) if shift else (0, 6, 12)
        if answer:
            pat = pat[:12] + BASS_ANSWER[prog]
        for i, p in enumerate(pat):
            if answer and i >= 12:
                v = ANSWER_VEL[i - 12]
            else:
                v = vel + (10 if i in acc else 0)
            dur = 0.36 if (i in acc or (answer and i >= 12)) else 0.24
            s.note(B, p, v, bt(bar) + i * 0.25, dur)

    def strchord(bar, prog, vel, dur):
        c, v3, v5, r1 = VOICES[prog]
        s.note(VC, c, vel, bt(bar), dur)
        s.note(VA, v3, vel, bt(bar), dur)
        s.note(V2, v5, vel, bt(bar), dur)
        s.note(V1, r1, vel, bt(bar), dur)

    for r in ROLES:
        assert r in ch, f's4_crisis: 通道映射缺少角色 {r}'

    # 与母节同速(显式写回,防连播拼接时速度漂移)
    s.tempo(168, bt(bar0))

    # CC11 轮起点微弧(84/86/88/86,全曲最紧)
    for role in ROLES:
        for i, ccv in enumerate(CC11_TIER):
            s.cc(role, 11, ccv, bt(bar0 + i * 4))

    # ---------------- drums:心率型 kick + snare 2/4 + hat 16 分 + 幽灵音 ----------------
    for i in range(16):
        for j in range(8):                       # 8 个 8 分双发:lub-dub 重音错位
            b = j * 0.5
            if i == 15 and b == 3.5:
                continue                         # m18 第 4 拍轻收(回环)
            vel = 96 if b in (0.0, 2.0) else (80 if b in (0.5, 2.5) else 68)
            s.note('drums', 36, vel, bt(bar0 + i) + b, 0.2)
        for b in (1.0, 3.0):
            s.note('drums', 38, 76, bt(bar0 + i) + b, 0.2)
        for j in range(16):
            s.note('drums', 42, 66, bt(bar0 + i) + j * 0.25, 0.15)
    for i in (0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14):   # 幽灵音:每轮 bar1-3
        for j in (1, 7, 9, 15):
            s.note('drums', 38, 52, bt(bar0 + i) + j * 0.25, 0.1)
    for rel in (7, 11):                                  # 急促 fill:32 分 4 音(绊脚收束)
        for j, v in enumerate((80, 86, 92, 98)):
            s.note('drums', 38, v, bt(bar0 + rel) + 3.25 + j * 0.125, 0.09)

    # ---------------- bass:16 分模式(108/重音 118)+ 应答 + m18 回环 ----------------
    for i in range(15):
        riff_dense(bar0 + i, BASS_PLAN[i], CHORDS16[i], 108,
                   answer=(i % 4 == 1), shift=(i % 4 == 2))
        dur = 2.0 if i in (3, 7, 11, 15) else 3.9     # riser 让位(含 rel 15,riser 加密)
        strchord(bar0 + i, CHORDS16[i], 62, dur)
    strchord(bar0 + 15, 'Em', 62, 2.0)               # m18 弦乐预挂 Em(母节回环工程)
    for k in range(16):                              # m18 bass:D pattern,尾 4 音降力
        v = 108 + (10 if k in (0, 6, 12) else 0)
        if k >= 12:
            v -= 12
        s.note(B, BASS_P1['D'][k], v, bt(bar0 + 15) + k * 0.25, 0.24)

    # vln1 回声(每轮 bar1/3 句尾,母节值 62 保留)
    for rel in ECHO_RELS:
        bar = bar0 + rel
        p0, p1 = ECHO_PAIR[CHORDS16[rel]]
        s.note(V1, p0, 62, bt(bar) + 3.5, 0.2)
        s.note(V1, p1, 62, bt(bar) + 3.75, 0.2)

    # ---------------- pad/choir 长音(46/54,riser 小节缩 2.0) ----------------
    for rel in range(16):
        cname = CHORDS16[rel]
        dur = 2.0 if rel in (3, 7, 11, 15) else 3.9
        s.chord('synth_pad', CHOIR_VOICE[cname], 46, bt(bar0 + rel), dur)
        s.chord('choir', CHOIR_VOICE[cname], 54, bt(bar0 + rel), dur)

    # ---------------- brass 刺刀:密度 1/2/2/0 保留,音高全部 +1,vel 66-76 ----------------
    STAB_SLOTS = ((0.75,), (0.75, 1.25), (0.75, 1.25), ())
    STAB_VEL = ((66,), (70, 76), (70, 76), ())
    for rel in range(16):
        cell = M2_T[CHORDS16[rel]]
        for i, b in enumerate(STAB_SLOTS[rel % 4]):
            s.note('brass_stab', cell[i], STAB_VEL[rel % 4][i], bt(bar0 + rel) + b, 0.35)
    for rel in (3, 7, 11):
        s.note('brass_stab', M3_PITCH_T[CHORDS16[rel]], 76, bt(bar0 + rel) + 3.0, 0.3)

    # ---------------- rhythm 节奏层(v9 规格:只轮 2/4、0.25/2.0 反拍、vel 58,音高原位) ----------------
    for rel in range(16):
        if rel // 4 not in (1, 3):
            continue
        if rel % 4 == 3:
            continue
        for b in (0.25, 2.0):
            s.chord('synth_rhythm', RHY_CHORD[CHORDS16[rel]], 58, bt(bar0 + rel) + b, 0.25)

    # ---------------- piano 0.0 锚点(68,八度) ----------------
    for rel in range(16):
        r0 = PIANO_ROOT[CHORDS16[rel]]
        s.note('piano_bang', r0, 68, bt(bar0 + rel), 0.3)
        s.note('piano_bang', r0 + 12, 68, bt(bar0 + rel), 0.3)

    # ---------------- fx:riser 加密(rel 3/7/11/15,vel 46-76)+ 0.0 低脉冲(44) ----------------
    for rel in range(16):
        s.note('fx', 57, 44, bt(bar0 + rel), 0.22)
    for rel in (3, 7, 11, 15):
        cname = CHORDS16[rel]
        for j, p in enumerate(RISER[cname]):
            s.note('fx', p, RISER_VEL[j], bt(bar0 + rel) + 2.0 + j * 0.25, 0.22)

    # ---------------- hook 乐句(vel 72-82,音高全部 +1) ----------------
    for rel in range(16):
        cname = CHORDS16[rel]
        ph = HOOK_PHRASE_T[cname]
        k = rel % 4
        hi = (rel // 4) % 2 == 1                      # 轮 2/4
        long_vel = 82 - (8 if rel == 15 else 0)
        short_vel = 72 - (8 if rel == 15 else 0)
        if k == 0:                                    # bar1:句头长音(3.5,喘息)
            p = HOOK_HIGH_T[cname] if hi else ph['bar1']
            s.note('hook', p, long_vel, bt(bar0 + rel) + 3.5, 0.8)
        elif k == 1:                                  # bar2:短音
            s.note('hook', ph['bar2'], short_vel, bt(bar0 + rel) + 2.5, 0.3)
        elif k == 2:                                  # bar3:短句 0.5/2.0 + 句尾"喘不过气"
            p3 = ph['bar3']
            s.note('hook', p3[0], short_vel, bt(bar0 + rel) + 0.5, 0.3)
            s.note('hook', p3[1], short_vel, bt(bar0 + rel) + 2.0, 0.3)
            s.note('hook', p3[2], 78, bt(bar0 + rel) + 3.5, 0.2)   # 喘息点→短促+重复
            s.note('hook', p3[2], 72, bt(bar0 + rel) + 3.75, 0.2)
        else:                                         # bar4:短收(rel 15 减力回环)
            s.note('hook', ph['bar4'], short_vel, bt(bar0 + rel) + 3.5, 0.3)

    # ---------------- timpani:2.0 根音(70-78)+ M3 齐击@3.0(80);轮 4 双音滚保留 ----------------
    for i in range(16):
        d = 0.2 if i >= 12 else 0.4
        s.note('timpani', TIMP_ROOT[CHORDS16[i]], TIMP_VEL[i // 4], bt(bar0 + i) + 2.0, d)
        if i >= 12:
            s.note('timpani', TIMP_ROOT[CHORDS16[i]], TIMP_VEL[i // 4] - 12,
                   bt(bar0 + i) + 2.25, 0.25)
    for rel in (3, 7, 11):
        s.note('timpani', 38, 80, bt(bar0 + rel) + 3.0, 0.4)

    return bar0 + 16


if __name__ == '__main__':
    import contextlib, io
    CH = {'piano_bang': 0, 'synth_pad': 1, 'vln1': 2, 'vln2': 3, 'vla': 4,
          'celli': 5, 'bass_electric': 6, 'fx': 7, 'drums': 9, 'hook': 10,
          'timpani': 11, 'brass_stab': 12, 'choir': 14, 'synth_rhythm': 15}
    s = Score(humanize=True, seed=42)
    for role, chn in CH.items():
        r = 'synth_lead' if role == 'hook' else role   # hook 嗓 = 方波(母节 v9 合成器版)
        bank, prog, (lo, hi), pan, rev = PROGS[r]
        s.add_instr(role, chn, bank, prog, lo, hi, pan, rev)
        s.cc(role, 7, 100, 0.0)
    s.tempo(168, 0.0)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert build(s, 3, 0, CH) == 19
        s.flush('S4_Crisis.mid')
    out = buf.getvalue()
    print(out)
    conf = out.count('[冲突]')
    warn = out.count('[音区告警]')
    inherited = out.count('synth_rhythm: 音')     # 告警应全部为 rhythm 继承项(母节 v9 同款)
    ok = conf == 0 and warn == inherited
    print(f'S4 冒烟: {"PASS" if ok else "FAIL"} S4_Crisis.mid(冲突 {conf} 处,音区告警 {warn} 处=rhythm 继承项 {inherited})')
    sys.exit(0 if ok else 1)
