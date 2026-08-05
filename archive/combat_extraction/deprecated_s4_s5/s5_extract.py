#!/usr/bin/env python3
"""s5_extract.py — 子节 5:《撤离冲刺版》(撤离倒计时,BPM 176)

游戏场景:撤离倒计时冲刺。
人格意象:**逃亡冲刺**——32 分 hat 的心跳加速、32 分 riser 的引擎轰鸣、
hook 句头八度叠置的\"呼喊\"(冲 HOOK_HIGH 再回落)、每轮 bar4 M3 齐奏的\"顿足\"。

受控改动(相对母节 v9,依据:ARCHITECTURE §3 S5 规格 + 用户指令 2026-08):
- BPM:build 开头 s.tempo(176, (bar0-1)*4),本子节全程 176(+8 冲刺)
- drums:kick 3+3+2 保持(重音 100/普通 82,bar3 移位 3+2+3 保留);snare 2/4
  (84,rel 7/11 的 3.0 背拍让位 fill);hat **32 分全程**(58,心跳加速);
  幽灵音加密(16 分 52,避开 2/4 背拍与 fill 区);fill 加密——rel 7/11 bar4
  32 分 snare 滚奏 16 音(vel 渐强 44→76);删 crash/开镲
- bass:母节 16 分模式保留(vel 108/重音 118),每轮 bar2 应答保留
  (110/108/110/106)——应答不冲顶(冲顶是 S4 的签名),m18 回环处理保留
- hook:乐句保留 + **句头呼喊**:bar1 句头长音改冲 HOOK_HIGH(全轮统一,
  不再轮 1/3 用低位)+ 八度叠置(3.5 槽同时发 P 与 P-12,vel 72/64);
  短音不叠(70);bar3 句尾长音单音(72),音高原位
- brass:1/2/2/0 保留,vel 70-80(+4),音高原位;M3 齐奏 brass 80
- rhythm:母节 v9 规格(只轮 2/4 出场、每小节 2 落点 0.25/2.0)vel 62
  (⚠️ RHY_CHORD 55/67 超出 progs 声明 57-64——母节 v9 同款继承告警,非本子节新增)
- fx:riser 改 **32 分上行**(rel 3/7/11,母节六音素材两八度往返,vel 46-78
  渐强=加速器);0.0 低脉冲(46)
- timpani:2.0 根音(72/76/80/78)+ M3@3.0(84,顿足——冲击由 timpani/kick/
  bass 三件套承担,brass M3 保持 80 辅助位,同母节 v9 哲学)
- piano:0.0 锚点**双八度**(根音 +12 +24,vel 70)
- strings/pad/choir:长音(62/46/54);vln1 回声保留(66)
- CC11:84-88(轮起点 84/86/88/86)
- 强度定位:母节 + 冲刺(力度 +4-6,密度以 hat/riser/fill 的 32 分为代表)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS

# 16 小节和弦序(与母节共享骨架:轮1 Em Em C D,轮2-4 Em C G D)
CHORDS16 = ('Em', 'Em', 'C', 'D', 'Em', 'C', 'G', 'D',
            'Em', 'C', 'G', 'D', 'Em', 'C', 'G', 'D')

# ================= 原位素材(与母节 v9 一致;S5 不做移调,S4 才是多调性子节) =================
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

BASS_ANSWER = {                          # 母节应答原位(不冲顶——那是 S4 的签名)
    'Em': (40, 43, 47, 52),
    'C':  (36, 43, 48, 52),
    'G':  (31, 43, 47, 50),
    'D':  (38, 45, 50, 45),
}
ANSWER_VEL = (110, 108, 110, 106)         # 母节 106/104/106/102 +4(跟上 +4 基速)

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

# brass 刺刀(母节原位)/ M3 齐奏
M2 = {
    'Em': (59, 62, 64, 62),
    'C':  (60, 64, 67, 64),
    'G':  (59, 62, 67, 62),
    'D':  (62, 66, 69, 66),
}
M3_PITCH = {'Em': 59, 'D': 62}

# hook 乐句(母节原位;句头统一冲 HOOK_HIGH = 呼喊签名)
HOOK_PHRASE = {
    'Em': {'bar1': 76, 'bar2': 74, 'bar3': (79, 78, 76), 'bar4': 74},
    'C':  {'bar1': 72, 'bar2': 74, 'bar3': (79, 76, 72), 'bar4': 74},
    'G':  {'bar1': 71, 'bar2': 74, 'bar3': (79, 76, 71), 'bar4': 74},
    'D':  {'bar1': 69, 'bar2': 71, 'bar3': (78, 74, 69), 'bar4': 71},
}
HOOK_HIGH = {'Em': 81, 'C': 77, 'G': 79, 'D': 78}

# fx riser(母节六音五声素材;32 分版 = 素材两八度往返,顶到 fx 上限 90)
RISER = {'Em': (64, 67, 69, 71, 74, 76), 'D': (62, 66, 69, 71, 74, 78)}
RISER_32 = {c: tuple(RISER[c]) + tuple(p + 12 for p in RISER[c]) for c in RISER}

TIMP_ROOT = {'Em': 40, 'C': 36, 'G': 31, 'D': 38}
TIMP_VEL = (72, 76, 80, 78)               # 母节 66/70/74/72 +6(72-80)
CC11_TIER = (84, 86, 88, 86)              # 轮起点 CC11(与 S4 同紧)

ROLES = ('drums', 'bass_electric', 'vln1', 'vln2', 'vla', 'celli',
         'piano_bang', 'synth_pad', 'choir', 'hook', 'brass_stab',
         'timpani', 'fx', 'synth_rhythm')


def build(s, bar0, cycle, ch):
    """铺 16 小节 S5(小节 = bar0 起),全程 176 BPM。返回 bar0+16。"""
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
        assert r in ch, f's5_extract: 通道映射缺少角色 {r}'

    # 本子节全程 176(冲刺;撤离倒计时节奏)
    s.tempo(176, (bar0 - 1) * 4)

    # CC11 轮起点微弧(84/86/88/86)
    for role in ROLES:
        for i, ccv in enumerate(CC11_TIER):
            s.cc(role, 11, ccv, bt(bar0 + i * 4))

    # ---------------- drums:kick 3+3+2(100/82)+ snare 2/4(84)+ hat 32 分 + 幽灵音 16 分 ----------------
    for i in range(16):
        shift = (i % 4 == 2)                     # 每轮 bar3:重音移位(句法转)
        for j in range(8):
            b = j * 0.5
            if i == 15 and b == 3.0:
                continue                          # m18 第 4 拍无重音(回环)
            if shift and b == 3.0:
                vel = 82                          # 移位小节:3.0 降普通(3+2+3)
            else:
                acc = (0.0, 1.5, 2.5) if shift else (0.0, 1.5, 3.0)
                vel = 100 if b in acc else 82
            s.note('drums', 36, vel, bt(bar0 + i) + b, 0.2)
        for b in ((1.0,) if i in (7, 11) else (1.0, 3.0)):   # rel 7/11 的 3.0 背拍让位 fill
            s.note('drums', 38, 84, bt(bar0 + i) + b, 0.2)
        for j in range(32):                      # hat 32 分全程(心跳加速)
            s.note('drums', 42, 58, bt(bar0 + i) + j * 0.125, 0.08)
    GHOST_SLOTS = (0.25, 0.5, 0.75, 1.25, 1.5, 1.75, 2.25, 2.5, 2.75, 3.25, 3.5, 3.75)
    for i in range(16):                          # 幽灵音加密:16 分(避开 2/4 背拍与 fill 区)
        for b in GHOST_SLOTS:
            if i in (7, 11) and b >= 2.0:
                continue
            s.note('drums', 38, 52, bt(bar0 + i) + b, 0.1)
    for rel in (7, 11):                          # fill 加密:32 分 snare 滚奏(渐强 44→76)
        for j in range(16):
            vel = int(round(44 + (76 - 44) * j / 15))
            s.note('drums', 38, vel, bt(bar0 + rel) + 2.0 + j * 0.125, 0.09)

    # ---------------- bass:16 分模式(108/重音 118)+ 应答 + m18 回环 ----------------
    for i in range(15):
        riff_dense(bar0 + i, BASS_PLAN[i], CHORDS16[i], 108,
                   answer=(i % 4 == 1), shift=(i % 4 == 2))
        dur = 2.0 if i in (3, 7, 11) else 3.9     # riser 让位(rel 15 无 riser,母节同)
        strchord(bar0 + i, CHORDS16[i], 62, dur)
    strchord(bar0 + 15, 'Em', 62, 3.9)           # m18 弦乐预挂 Em(母节回环工程)
    for k in range(16):                          # m18 bass:D pattern,尾 4 音降力
        v = 108 + (10 if k in (0, 6, 12) else 0)
        if k >= 12:
            v -= 12
        s.note(B, BASS_P1['D'][k], v, bt(bar0 + 15) + k * 0.25, 0.24)

    # vln1 回声(每轮 bar1/3 句尾,66)
    for rel in ECHO_RELS:
        bar = bar0 + rel
        p0, p1 = ECHO_PAIR[CHORDS16[rel]]
        s.note(V1, p0, 66, bt(bar) + 3.5, 0.2)
        s.note(V1, p1, 66, bt(bar) + 3.75, 0.2)

    # ---------------- pad/choir 长音(46/54,riser 小节缩 2.0) ----------------
    for rel in range(16):
        cname = CHORDS16[rel]
        dur = 2.0 if rel in (3, 7, 11) else 3.9
        s.chord('synth_pad', CHOIR_VOICE[cname], 46, bt(bar0 + rel), dur)
        s.chord('choir', CHOIR_VOICE[cname], 54, bt(bar0 + rel), dur)

    # ---------------- brass 刺刀:密度 1/2/2/0 保留,vel 70-80(+4),音高原位 ----------------
    STAB_SLOTS = ((0.75,), (0.75, 1.25), (0.75, 1.25), ())
    STAB_VEL = ((70,), (74, 80), (74, 80), ())
    for rel in range(16):
        cell = M2[CHORDS16[rel]]
        for i, b in enumerate(STAB_SLOTS[rel % 4]):
            s.note('brass_stab', cell[i], STAB_VEL[rel % 4][i], bt(bar0 + rel) + b, 0.35)
    for rel in (3, 7, 11):
        s.note('brass_stab', M3_PITCH[CHORDS16[rel]], 80, bt(bar0 + rel) + 3.0, 0.3)

    # ---------------- rhythm 节奏层(v9 规格:只轮 2/4、0.25/2.0 反拍)vel 62 ----------------
    for rel in range(16):
        if rel // 4 not in (1, 3):
            continue
        if rel % 4 == 3:
            continue
        for b in (0.25, 2.0):
            s.chord('synth_rhythm', RHY_CHORD[CHORDS16[rel]], 62, bt(bar0 + rel) + b, 0.25)

    # ---------------- piano 0.0 锚点双八度(根音 +12 +24,vel 70) ----------------
    for rel in range(16):
        r0 = PIANO_ROOT[CHORDS16[rel]]
        s.note('piano_bang', r0, 70, bt(bar0 + rel), 0.3)
        s.note('piano_bang', r0 + 12, 70, bt(bar0 + rel), 0.3)
        s.note('piano_bang', r0 + 24, 70, bt(bar0 + rel), 0.3)

    # ---------------- fx:riser 32 分上行(rel 3/7/11,渐强 46-78)+ 0.0 低脉冲(46) ----------------
    for rel in range(16):
        s.note('fx', 57, 46, bt(bar0 + rel), 0.22)
    for rel in (3, 7, 11):
        cname = CHORDS16[rel]
        for j, p in enumerate(RISER_32[cname]):
            vel = 46 + int(round((78 - 46) * j / 11))
            s.note('fx', p, vel, bt(bar0 + rel) + 2.0 + j * 0.125, 0.09)

    # ---------------- hook 乐句:句头呼喊(冲 HOOK_HIGH + 八度叠置)+ 原位乐句 ----------------
    for rel in range(16):
        cname = CHORDS16[rel]
        ph = HOOK_PHRASE[cname]
        k = rel % 4
        long_vel = 72 - (8 if rel == 15 else 0)
        short_vel = 70 - (8 if rel == 15 else 0)
        oct_vel = 64 - (8 if rel == 15 else 0)
        if k == 0:                                 # bar1:句头呼喊(全轮冲 HOOK_HIGH + 低八度)
            p = HOOK_HIGH[cname]
            s.note('hook', p, long_vel, bt(bar0 + rel) + 3.5, 0.8)
            s.note('hook', p - 12, oct_vel, bt(bar0 + rel) + 3.5, 0.8)
        elif k == 1:                               # bar2:短音(不叠)
            s.note('hook', ph['bar2'], short_vel, bt(bar0 + rel) + 2.5, 0.3)
        elif k == 2:                               # bar3:短句 0.5/2.0 + 句尾长音(单音)
            p3 = ph['bar3']
            s.note('hook', p3[0], short_vel, bt(bar0 + rel) + 0.5, 0.3)
            s.note('hook', p3[1], short_vel, bt(bar0 + rel) + 2.0, 0.3)
            s.note('hook', p3[2], long_vel, bt(bar0 + rel) + 3.5, 0.8)
        else:                                      # bar4:短收(rel 15 减力回环)
            s.note('hook', ph['bar4'], short_vel, bt(bar0 + rel) + 3.5, 0.3)

    # ---------------- timpani:2.0 根音(72-80)+ M3@3.0(84 顿足);轮 4 双音滚保留 ----------------
    for i in range(16):
        d = 0.2 if i >= 12 else 0.4
        s.note('timpani', TIMP_ROOT[CHORDS16[i]], TIMP_VEL[i // 4], bt(bar0 + i) + 2.0, d)
        if i >= 12:
            s.note('timpani', TIMP_ROOT[CHORDS16[i]], TIMP_VEL[i // 4] - 12,
                   bt(bar0 + i) + 2.25, 0.25)
    for rel in (3, 7, 11):
        s.note('timpani', 38, 84, bt(bar0 + rel) + 3.0, 0.4)

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
    s.tempo(176, 0.0)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert build(s, 3, 0, CH) == 19
        s.flush('S5_Extract.mid')
    out = buf.getvalue()
    print(out)
    conf = out.count('[冲突]')
    warn = out.count('[音区告警]')
    inherited = out.count('synth_rhythm: 音')     # 告警应全部为 rhythm 继承项(母节 v9 同款)
    ok = conf == 0 and warn == inherited
    print(f'S5 冒烟: {"PASS" if ok else "FAIL"} S5_Extract.mid(冲突 {conf} 处,音区告警 {warn} 处=rhythm 继承项 {inherited})')
    sys.exit(0 if ok else 1)
