#!/usr/bin/env python3
"""s2_explore.py — 子节 2:《探索行进版》(地图移动/警戒)

人格意象:「行进警觉」——与 S1"静态搜刮"听感可辨,多一层"走动":
bass 8 分脉冲带"步态"(每 2 小节一次小起伏:平步→抬步→冲顶),
hook 是每 2 小节一次的"扫描短句"(PING→应答→回声,短促/重复/五声),
鼓是匀速巡逻(每拍心跳 + 背拍),氛围层比 S1 稍强;
fx/riser/timpani/M3 等"战斗能量载体"全撤。

依据:ARCHITECTURE §3 子节规范(S2)+ 用户指令(2026-08):
强度介于 S1 与母节之间——警戒行进感;层开关 + 密度变形 + 乐句重写(非 vel-20)。

受控改动(相对母节 v9):
- fx(riser/低脉冲)、timpani、M3 齐击:全删(战斗能量载体不进场)
- drums:满配 8 分驱动+幽灵音+fill+crash → 匀速巡逻(kick 每拍 64 + snare 2/4 56
  + hat 8 分 46),无幽灵音/fill/crash;m18 第 4 拍轻收(回环,同 S1)
- bass:16 分密集高把位炫技 → 8 分根音脉冲(低把位根音 Em 28/C 36/G 31/D 38),
  每 2 小节一步小起伏(bar2 句尾五度→八度抬步,bar4 高把位点缀冲顶 40-52 带),
  vel 78-88(句尾重音 88),每轮 bar4 句号长音(1 拍)——行走的"步态"
- strings/pad/choir:长音 44/36/40(比 S1 稍强,氛围主导)
- piano:0.0 轻击(46,单音根音,不叠八度)
- hook:满 riff → 每 2 小节一次"扫描短句"(bar1 3.5 PING 长音 0.5 拍 vel 60 +
  bar3 0.5 应答 54 + 1.0 回声 48),音高取母节 HOOK_PHRASE 素材、和弦五声、
  下行 P4 轮廓(句法化警戒信号,拒绝碎片门铃感)
- brass:M2 刺刀密度 1/2/2/0 保留但更轻(vel 52-60),音高母节 M2 素材
- synth_rhythm:切分 2 落点 → 8 分单音行走(每小节 8 落点,两和弦音交替,vel 46)
- CC11:80-84 → 76-80 微弧(轮起点 76/78/80/78,轻档,全程 ≥70)
- 与母节共享:16 小节网格 / Em-C-G-D 循环 / 168 BPM / m18 回环轻收
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS

# 16 小节和弦序(与母节共享骨架:轮1 Em Em C D,轮2-4 Em C G D)
CHORDS16 = ('Em', 'Em', 'C', 'D', 'Em', 'C', 'G', 'D',
            'Em', 'C', 'G', 'D', 'Em', 'C', 'G', 'D')

# 行进步态 bass:8 分根音脉冲(低把位为主)。
# bar1/3 = 平步(句尾五度)、bar2 = 抬步(句尾五度→八度)、bar4 = 高把位点缀冲顶(40-52 带)
BASS_PULSE = {   # 平步
    'Em': (28, 28, 40, 28, 28, 40, 28, 35),   # E1 E1 E2 E1 E1 E2 E1 G2
    'C':  (36, 36, 48, 36, 36, 48, 36, 43),   # C2 C2 C3 C2 C2 C3 C2 G2
    'G':  (31, 31, 43, 31, 31, 43, 31, 38),   # G1 G1 G2 G1 G1 G2 G1 D2
    'D':  (38, 38, 50, 38, 38, 50, 38, 45),   # D2 D2 D3 D2 D2 D3 D2 A2
}
BASS_RAISE = {   # 抬步:句尾 G2→E2 / G2→C3 / D2→G2 / A2→D3(小起伏)
    'Em': (28, 28, 40, 28, 28, 40, 35, 40),
    'C':  (36, 36, 48, 36, 36, 48, 43, 48),
    'G':  (31, 31, 43, 31, 31, 43, 38, 43),
    'D':  (38, 38, 50, 38, 38, 50, 45, 50),
}
BASS_CLIMB = {   # 冲顶:句尾高把位点缀(母节应答音区 40-52 带)+ 句号长音
    'Em': (28, 28, 40, 28, 28, 40, 47, 52),   # ... B2 E3
    'C':  (36, 36, 48, 36, 36, 48, 48, 52),   # ... C3 E3
    'G':  (31, 31, 43, 31, 31, 43, 47, 50),   # ... B2 D3
    'D':  (38, 38, 50, 38, 38, 50, 45, 50),   # ... A2 D3
}
BASS_VEL = (78, 78, 82, 78, 78, 82, 78, 88)    # 句尾重音 88(比 S1 轻一档,但多 4 层警戒层)
CLIMB_VEL = (78, 78, 82, 78, 78, 82, 84, 88)
CC11_TIER = (76, 78, 80, 78)                   # 轮起点 CC11 微弧(轻档,全程 ≥70)

# 扫描短句 hook(句法化警戒信号):每 2 小节一次。下行 P4 轮廓 = 动机(重复感,五声和弦音)
HOOK_SCAN = {
    'Em': (76, 71),   # E5 → B4
    'C':  (72, 67),   # C5 → G4
    'G':  (71, 67),   # B4 → G4
    'D':  (69, 66),   # A4 → F#4
}

# M2 和弦分解刺刀(母节素材原样;M3 已删)
M2 = {
    'Em': (59, 62, 64, 62),
    'C':  (60, 64, 67, 64),
    'G':  (59, 62, 67, 62),
    'D':  (62, 66, 69, 66),
}
STAB_SLOTS = ((0.75,), (0.75, 1.25), (0.75, 1.25), ())   # v9 密度 1/2/2/0
STAB_VEL = ((52,), (56, 60), (56, 60), ())

# rhythm 8 分行走:两音交替。⚠️ 母节 RHY_CHORD 的 55/67/50 超出 synth_rhythm 音区
# (57,64)——本子节取和弦音并夹入音区(Em: B3/E4、C: C4/E4、G: B3/D4、D: A3/D4),
# 冒烟测试保持 0 音区告警(母节该 3 音为既有告警,子节要求干净自检)
RHY_WALK = {
    'Em': (59, 64),
    'C':  (60, 64),
    'G':  (59, 62),
    'D':  (57, 62),
}

# 弦乐和声堆叠(声部低→高:celli / vla / vln2 / vln1,母节 VOICES 原样)
VOICES = {
    'Em': (40, 64, 64, 71),
    'C':  (36, 64, 67, 72),
    'G':  (43, 62, 67, 71),
    'D':  (38, 62, 66, 69),
}
CHOIR_VOICE = {
    'Em': (52, 55, 64),
    'C':  (48, 52, 55),
    'G':  (55, 62, 67),
    'D':  (50, 54, 62),
}
PIANO_ROOT = {'Em': 40, 'C': 36, 'G': 43, 'D': 38}
ECHO_PAIR = {
    'Em': (64, 67),
    'C':  (64, 67),
    'G':  (62, 67),
}
ECHO_RELS = (0, 2, 4, 6, 8, 10, 12, 14)        # 每轮 bar1/3 句尾

ROLE_CH = {'piano_bang': 0, 'synth_pad': 1, 'vln1': 2, 'vln2': 3, 'vla': 4,
           'celli': 5, 'bass_electric': 6, 'fx': 7, 'drums': 9, 'hook': 10,
           'timpani': 11, 'brass_stab': 12, 'keys': 13, 'choir': 14,
           'synth_rhythm': 15}


def build(s, bar0, cycle, ch):
    """铺 16 小节 S2(小节 = bar0 起),返回 bar0+16。"""
    B = 'bass_electric'
    V1, V2, VA, VC = 'vln1', 'vln2', 'vla', 'celli'
    P, PA, CHO = 'piano_bang', 'synth_pad', 'choir'
    HK, BR, RY = 'hook', 'brass_stab', 'synth_rhythm'

    def bt(bar):
        return (bar - 1) * 4

    # CC11 微弧(轮起点 76/78/80/78;全程 ≥70 保 GUGS 响应可闻)
    for name in (B, V1, V2, VA, VC, P, PA, CHO, HK, BR, RY, 'drums'):
        for i, ccv in enumerate(CC11_TIER):
            s.cc(name, 11, ccv, bt(bar0 + i * 4))

    # ---------------- drums:匀速巡逻(kick 每拍 + snare 2/4 + hat 8分;无幽灵音/fill/crash) ----------------
    for i in range(16):
        for b in (0.0, 1.0, 2.0, 3.0):
            if i == 15 and b == 3.0:
                continue                       # m18 第 4 拍轻收(回环)
            s.note('drums', 36, 64, bt(bar0 + i) + b, 0.2)
        for b in (1.0, 3.0):
            s.note('drums', 38, 56, bt(bar0 + i) + b, 0.2)
        for j in range(8):
            s.note('drums', 42, 46, bt(bar0 + i) + j * 0.5, 0.15)

    # ---------------- bass:8 分根音脉冲步态(平步/抬步/冲顶)+ 每轮 bar4 句号长音 ----------------
    for i in range(16):
        prog = CHORDS16[i]
        k = i % 4
        pat = BASS_PULSE[prog] if k in (0, 2) else (BASS_RAISE[prog] if k == 1 else BASS_CLIMB[prog])
        velrow = BASS_VEL if k != 3 else CLIMB_VEL
        for j, p in enumerate(pat):
            dur = 0.95 if (k == 3 and j == 7) else 0.45   # bar4 句号长音(1 拍)
            s.note(B, p, velrow[j], bt(bar0 + i) + j * 0.5, dur)

    # ---------------- 氛围层:strings/pad/choir 长音 + piano 轻锚点 + vln1 回声 ----------------
    for i, prog in enumerate(CHORDS16):
        c, v3, v5, r1 = VOICES[prog]
        for name, pitch in ((VC, c), (VA, v3), (V2, v5), (V1, r1)):
            s.note(name, pitch, 44, bt(bar0 + i), 3.9)
        s.chord(PA, CHOIR_VOICE[prog], 36, bt(bar0 + i), 3.9)
        s.chord(CHO, CHOIR_VOICE[prog], 40, bt(bar0 + i), 3.9)
        s.note(P, PIANO_ROOT[prog], 46, bt(bar0 + i), 0.3)   # 单音根音轻击(不叠八度)
        if i in ECHO_RELS:                     # vln1 回声(bar1/3 句尾,应答 bass 句尾)
            p0, p1 = ECHO_PAIR[prog]
            s.note(V1, p0, 44, bt(bar0 + i) + 3.5, 0.2)
            s.note(V1, p1, 44, bt(bar0 + i) + 3.75, 0.2)

    # ---------------- hook 扫描短句:每 2 小节一次(bar1 PING + bar3 应答/回声) ----------------
    for i, prog in enumerate(CHORDS16):
        hi, lo = HOOK_SCAN[prog]
        k = i % 4
        if k == 0:                             # bar1:3.5 PING 长音(0.5 拍)
            s.note(HK, hi, 60, bt(bar0 + i) + 3.5, 0.5)
        elif k == 2:                           # bar3:0.5 应答 + 1.0 回声(重复感)
            s.note(HK, lo, 54, bt(bar0 + i) + 0.5, 0.3)
            s.note(HK, lo, 48, bt(bar0 + i) + 1.0, 0.25)

    # ---------------- brass:M2 刺刀 1/2/2/0(更轻,vel 52-60) ----------------
    for i, prog in enumerate(CHORDS16):
        cell = M2[prog]
        for k, b in enumerate(STAB_SLOTS[i % 4]):
            s.note(BR, cell[k], STAB_VEL[i % 4][k], bt(bar0 + i) + b, 0.35)

    # ---------------- synth_rhythm:8 分单音行走(每小节 8 落点,两和弦音交替) ----------------
    for i, prog in enumerate(CHORDS16):
        a, b2 = RHY_WALK[prog]
        for j in range(8):
            p = a if j % 2 == 0 else b2
            s.note(RY, p, 46, bt(bar0 + i) + j * 0.5, 0.25)

    return bar0 + 16


if __name__ == '__main__':
    import contextlib, io
    USED = ('drums', 'bass_electric', 'vln1', 'vln2', 'vla', 'celli',
            'synth_pad', 'choir', 'piano_bang', 'hook', 'brass_stab', 'synth_rhythm')
    s = Score(humanize=True, seed=42)
    for role in USED:
        prog_role = 'synth_lead' if role == 'hook' else role   # hook 音色 = 合成器版(主成品)
        bank, prog, (lo, hi), pan, rev = PROGS[prog_role]
        s.add_instr(role, ROLE_CH[role], bank, prog, lo, hi, pan, rev)
        s.cc(role, 7, 100, 0.0)
    s.tempo(168, 0.0)
    assert build(s, 3, 0, ROLE_CH) == 19
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        s.flush('S2_Explore.mid')
    out = buf.getvalue()
    print(out, end='')
    bad = out.count('[音区告警]') + out.count('  [冲突]')
    print(f'S2 冒烟: {"PASS" if bad == 0 else "FAIL"} S2_Explore.mid(音区告警/自检冲突 = {bad})')
    sys.exit(0 if bad == 0 else 1)
