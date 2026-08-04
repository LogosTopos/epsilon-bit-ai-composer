#!/usr/bin/env python3
"""s4_crisis_v2.py — 子节 4 v2:《绝境压迫》(弃移调重做版)

用户裁决(2026-08):旧 S4 难听 = 滥用 stab(brass 66-80 + M3 76-80 + riser 加密)
+ 旋律层 +1 半音多调性。本版按创作红线重做:音高一律用母节已验证素材原位,
不加 brass、不加任何 stab 类元素;压迫感只来自心率鼓点与力度,不移调。

人格意象:绝境压迫——每拍"重-轻"双发心跳(心要跳出胸腔,机械恒定)+ bass
应答原位(不半音尖叫冲顶)+ hook 原位(vel 比母节 +4,压迫靠力度不靠移调)。

受控改动(相对母节 v9;红线口径 = 层开关 + 密度/力度变形 + 乐句重写,音高原位):
- 删除层:brass_stab、synth_rhythm 整层不注册(零 stab 元素;顺带消除母节
  RHY_CHORD 55/67 超音区继承告警——本版零音区告警)
- drums:母节 8 分驱动 → 心率双发(kick 每拍重 84 + 半拍轻 64,双发心跳感);
  snare 2/4(66)+ hat 16 分(46)轻点;删 crash/开镲/幽灵音/fill(压迫不放行);
  m18 第 4 拍轻收(回环)
- bass:母节 16 分密集 → 8 分简化模式(音高全部取自母节 BASS_P1/P2/P3 原位,
  28-52 区);3+3+2 重音保留(bar3 移位 3+2+3);每轮 bar2 应答用母节 BASS_ANSWER
  原位 + 母节 ANSWER_VEL(106/104/106/102)——旧版 51→52 半音尖叫冲顶已删;
  m18 回环处理保留
- hook:母节 HOOK_PHRASE/HOOK_HIGH 原位(轮 2/4 句头高音照旧),vel 比母节 +4
  (长音 80 / 短音 70,humanize 后 <84 互锁阈值)——旧版 +1 半音移调、bar3 喘息点
  "短促+重复"全部删除,恢复母节句法
- timpani/M3:母节原位(2.0 根音 66/70/74/72 + 轮 4 双音滚;rel 3/7/11 M3 齐击
  38@78)——M3 只由 timpani/kick/bass 三件套承担,无 brass 参与
- fx:riser 用母节 42-72 原版(rel 3/7/11 六音五声上行,RISER_VEL 原位,不加密、
  不加 rel 15);0.0 低脉冲(57,42)
- strings/pad/choir/vln1 回声/piano:母节原位(弦乐 62、pad 46、choir 54 比母节
  +4 提压迫;riser 小节缩 2.0 让位;m18 弦乐预挂 Em;piano 0.0 锚点双音 64)
- CC11:母节轮起点 80/82/84/82 微弧(原位)
- 与母节共享:16 小节网格 / Em-C-G-D 循环 / 168 BPM / m18 回环轻收;
  __main__ 两圈演示(32 小节 ≈ 45.7s)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS

# 16 小节和弦序(与母节共享骨架:轮1 Em Em C D,轮2-4 Em C G D)
CHORDS16 = ('Em', 'Em', 'C', 'D', 'Em', 'C', 'G', 'D',
            'Em', 'C', 'G', 'D', 'Em', 'C', 'G', 'D')

# 心率 kick 双发(规格:重-轻,落在每拍;机械恒定 = 压迫)
KICK_HVY = 84
KICK_LGT = 64

# bass 8 分简化模式:音高全部取自母节 BASS_P1/P2/P3 原位(28-52 区,不 +1 半音)
BASS_8 = {
    'Em': (28, 40, 43, 40, 47, 43, 40, 47),
    'C':  (36, 43, 48, 43, 52, 48, 43, 48),
    'G':  (31, 43, 47, 43, 50, 47, 43, 47),
    'D':  (38, 45, 50, 45, 52, 50, 45, 50),
}
BASS_VEL = 104                       # 母节 bass 基速(原位)
BASS_ACC = 12                        # 母节重音增量
# 母节应答原位(不冲顶、不半音趋近——旧版 51→52 尖叫已删)
BASS_ANSWER = {
    'Em': (40, 43, 47, 52),
    'C':  (36, 43, 48, 52),
    'G':  (31, 43, 47, 50),
    'D':  (38, 45, 50, 45),
}
ANSWER_VEL = (106, 104, 106, 102)    # 母节应答力度(原位)

# 弦乐和声堆叠(母节 VOICES 原样)
VOICES = {
    'Em': (40, 64, 64, 71),
    'C':  (36, 64, 67, 72),
    'G':  (43, 62, 67, 71),
    'D':  (38, 62, 66, 69),
}
ECHO_PAIR = {
    'Em': (64, 67), 'C': (64, 67), 'G': (62, 67), 'D': (62, 66),
}
ECHO_RELS = (0, 2, 4, 6, 8, 10, 12, 14)   # 每轮 bar1/3 句尾(vln1 回声,母节原位)

CHOIR_VOICE = {
    'Em': (52, 55, 64),
    'C':  (48, 52, 55),
    'G':  (55, 62, 67),
    'D':  (50, 54, 62),
}
PIANO_ROOT = {'Em': 40, 'C': 36, 'G': 43, 'D': 38}

# fx riser:母节 42-72 原版(不加密;rel 3/7/11 六音五声上行)
RISER = {
    'Em': (64, 67, 69, 71, 74, 76),
    'D':  (62, 66, 69, 71, 74, 78),
}
RISER_VEL = (42, 48, 54, 60, 66, 72)

# hook 乐句:母节原位(vel 比母节 +4,压迫感靠力度不靠移调)
HOOK_PHRASE = {
    'Em': {'bar1': 76, 'bar2': 74, 'bar3': (79, 78, 76), 'bar4': 74},
    'C':  {'bar1': 72, 'bar2': 74, 'bar3': (79, 76, 72), 'bar4': 74},
    'G':  {'bar1': 71, 'bar2': 74, 'bar3': (79, 76, 71), 'bar4': 74},
    'D':  {'bar1': 69, 'bar2': 71, 'bar3': (78, 74, 69), 'bar4': 71},
}
HOOK_HIGH = {'Em': 81, 'C': 77, 'G': 79, 'D': 78}
HOOK_LONG_VEL = 80                   # 母节 76 + 4
HOOK_SHORT_VEL = 70                  # 母节 66 + 4

# timpani 母节原位(2.0 根音 + 轮 4 双音滚 + M3 齐击 38@78)
TIMP_ROOT = {'Em': 40, 'C': 36, 'G': 31, 'D': 38}
TIMP_VEL = (66, 70, 74, 72)

CC11_TIER = (80, 82, 84, 82)         # 母节轮起点 CC11 微弧(原位)

ROLES = ('drums', 'bass_electric', 'vln1', 'vln2', 'vla', 'celli',
         'piano_bang', 'synth_pad', 'choir', 'hook', 'timpani', 'fx')


def build(s, bar0, cycle, ch):
    """铺 16 小节 S4 v2(小节 = bar0 起),返回 bar0+16。"""
    B = 'bass_electric'
    V1, V2, VA, VC = 'vln1', 'vln2', 'vla', 'celli'

    def bt(bar):
        return (bar - 1) * 4

    def riff_8(bar, prog, vel, answer=False, shift=False):
        """8 分简化驱动;重音 3+3+2(0/1.5/3.0)或移位 3+2+3(0/1.5/2.5);
        answer:末 4 音换母节应答原位(对话链)"""
        pat = list(BASS_8[prog])
        acc = (0, 3, 5) if shift else (0, 3, 6)
        if answer:
            pat[4:8] = BASS_ANSWER[prog]
        for i, p in enumerate(pat):
            if answer and i >= 4:
                v = ANSWER_VEL[i - 4]
            else:
                v = vel + (BASS_ACC if i in acc else 0)
            dur = 0.36 if (i in acc or (answer and i >= 4)) else 0.28
            s.note(B, p, v, bt(bar) + i * 0.5, dur)

    def strchord(bar, prog, vel, dur):
        c, v3, v5, r1 = VOICES[prog]
        s.note(VC, c, vel, bt(bar), dur)
        s.note(VA, v3, vel, bt(bar), dur)
        s.note(V2, v5, vel, bt(bar), dur)
        s.note(V1, r1, vel, bt(bar), dur)

    for r in ROLES:
        assert r in ch, f's4_crisis_v2: 通道映射缺少角色 {r}'

    # 与母节同速(显式写回,防连播拼接速度漂移)
    s.tempo(168, bt(bar0))

    # CC11 轮起点微弧(母节 80/82/84/82 原位)
    for role in ROLES:
        for i, ccv in enumerate(CC11_TIER):
            s.cc(role, 11, ccv, bt(bar0 + i * 4))

    # ---------------- drums:心率双发 kick + snare 2/4 + hat 16 分 ----------------
    for i in range(16):
        for j in range(8):                       # 每拍重-轻双发(心跳,重 84/轻 64)
            b = j * 0.5
            if i == 15 and b == 3.5:
                continue                         # m18 第 4 拍轻收(回环)
            vel = KICK_HVY if j % 2 == 0 else KICK_LGT
            s.note('drums', 36, vel, bt(bar0 + i) + b, 0.2)
        for b in (1.0, 3.0):
            s.note('drums', 38, 66, bt(bar0 + i) + b, 0.2)
        for j in range(16):
            s.note('drums', 42, 46, bt(bar0 + i) + j * 0.25, 0.15)

    # ---------------- bass:8 分简化模式(原位)+ 应答 + m18 回环 ----------------
    for i in range(15):
        riff_8(bar0 + i, CHORDS16[i], BASS_VEL,
               answer=(i % 4 == 1), shift=(i % 4 == 2))
    for k in range(8):                           # m18 回环:D 模式,尾 2 音降力
        v = BASS_VEL + (BASS_ACC if k in (0, 3, 6) else 0)
        if k >= 6:
            v -= 12
        s.note(B, BASS_8['D'][k], v, bt(bar0 + 15) + k * 0.5, 0.3)

    # ---------------- 和声层:strings 长音(62)+ pad/choir(46/54) ----------------
    for i in range(15):
        dur = 2.0 if i in (3, 7, 11) else 3.9    # riser 让位
        strchord(bar0 + i, CHORDS16[i], 62, dur)
    strchord(bar0 + 15, 'Em', 62, 3.9)           # m18 弦乐预挂 Em(母节回环工程)
    for rel in range(16):
        cname = CHORDS16[rel]
        dur = 2.0 if rel in (3, 7, 11) else 3.9
        s.chord('synth_pad', CHOIR_VOICE[cname], 46, bt(bar0 + rel), dur)
        s.chord('choir', CHOIR_VOICE[cname], 54, bt(bar0 + rel), dur)

    # vln1 回声(每轮 bar1/3 句尾,母节原位 62)
    for rel in ECHO_RELS:
        bar = bar0 + rel
        p0, p1 = ECHO_PAIR[CHORDS16[rel]]
        s.note(V1, p0, 62, bt(bar) + 3.5, 0.2)
        s.note(V1, p1, 62, bt(bar) + 3.75, 0.2)

    # ---------------- piano 0.0 锚点(母节原位双音,64) ----------------
    for rel in range(16):
        r0 = PIANO_ROOT[CHORDS16[rel]]
        s.note('piano_bang', r0, 64, bt(bar0 + rel), 0.3)
        s.note('piano_bang', r0 + 12, 64, bt(bar0 + rel), 0.3)

    # ---------------- fx:母节 42-72 原版 riser(rel 3/7/11)+ 0.0 低脉冲 ----------------
    for rel in range(16):
        s.note('fx', 57, 42, bt(bar0 + rel), 0.22)
    for rel in (3, 7, 11):
        cname = CHORDS16[rel]
        for j, p in enumerate(RISER[cname]):
            s.note('fx', p, RISER_VEL[j], bt(bar0 + rel) + 2.0 + j * 0.25, 0.22)

    # ---------------- hook 乐句原位(vel 比母节 +4:长 80 / 短 70) ----------------
    for rel in range(16):
        cname = CHORDS16[rel]
        ph = HOOK_PHRASE[cname]
        k = rel % 4
        hi = (rel // 4) % 2 == 1                 # 轮 2/4 句头高音(母节原位)
        long_vel = HOOK_LONG_VEL - (8 if rel == 15 else 0)
        short_vel = HOOK_SHORT_VEL - (8 if rel == 15 else 0)
        if k == 0:                               # bar1:句头长音(3.5,喘息)
            p = HOOK_HIGH[cname] if hi else ph['bar1']
            s.note('hook', p, long_vel, bt(bar0 + rel) + 3.5, 0.8)
        elif k == 1:                             # bar2:短音(让位 bass 应答)
            s.note('hook', ph['bar2'], short_vel, bt(bar0 + rel) + 2.5, 0.3)
        elif k == 2:                             # bar3:短句 0.5/2.0 + 句尾长音
            p3 = ph['bar3']
            s.note('hook', p3[0], short_vel, bt(bar0 + rel) + 0.5, 0.3)
            s.note('hook', p3[1], short_vel, bt(bar0 + rel) + 2.0, 0.3)
            s.note('hook', p3[2], long_vel, bt(bar0 + rel) + 3.5, 0.8)
        else:                                    # bar4:短收(rel 15 减力回环)
            s.note('hook', ph['bar4'], short_vel, bt(bar0 + rel) + 3.5, 0.3)

    # ---------------- timpani 母节原位:2.0 根音 + 轮 4 双音滚 + M3 齐击(三件套) ----------------
    for i in range(16):
        d = 0.2 if i >= 12 else 0.4
        s.note('timpani', TIMP_ROOT[CHORDS16[i]], TIMP_VEL[i // 4], bt(bar0 + i) + 2.0, d)
        if i >= 12:
            s.note('timpani', TIMP_ROOT[CHORDS16[i]], TIMP_VEL[i // 4] - 12,
                   bt(bar0 + i) + 2.25, 0.25)
    for rel in (3, 7, 11):
        s.note('timpani', 38, 78, bt(bar0 + rel) + 3.0, 0.4)

    return bar0 + 16


if __name__ == '__main__':
    import contextlib, io
    CH = {'piano_bang': 0, 'synth_pad': 1, 'vln1': 2, 'vln2': 3, 'vla': 4,
          'celli': 5, 'bass_electric': 6, 'fx': 7, 'drums': 9, 'hook': 10,
          'timpani': 11, 'choir': 14}
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
        assert build(s, 19, 1, CH) == 35          # 两圈演示(32 小节 ≈ 45.7s)
        s.flush('S4_Crisis_v2.mid')
    out = buf.getvalue()
    print(out)
    conf = out.count('[冲突]')
    warn = out.count('[音区告警]')
    ok = conf == 0 and warn == 0
    print(f'S4v2 冒烟: {"PASS" if ok else "FAIL"} S4_Crisis_v2.mid(冲突 {conf} 处,音区告警 {warn} 处,期望均 0)')
    sys.exit(0 if ok else 1)
