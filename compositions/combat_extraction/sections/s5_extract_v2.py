#!/usr/bin/env python3
"""s5_extract_v2.py — 子节 5 v2:《逃亡冲刺》(弃叠置重做版)

用户裁决(2026-08):旧 S5 难听 = 32 分两八度 riser + hook 句头八度叠置呼喊。
本版按创作红线重做:保留 176 BPM + 32 分 hat(人格核心,速度感),母节
bass/hook 原位(不八度叠置、不扩展音区),riser 用母节 42-72 原版(不加密、
不跨八度)。

人格意象:逃亡冲刺——176 的推背感 + 32 分 hat 的心跳加速;母节 bass 16 分
密集驱动原位推进,无任何"呼喊叠置",冲刺纯粹靠速度与密度。

受控改动(相对母节 v9;红线口径 = 层开关 + 密度/力度变形,音高原位):
- 删除层:brass_stab、synth_rhythm 整层不注册(零 stab 元素;顺带消除母节
  RHY_CHORD 55/67 超音区继承告警——本版零音区告警)
- drums:母节骨架保留(3+3+2 kick 92/104、snare 2/4 98、幽灵音 45、开镲 bar3
  74、crash 轮起点 96、fill 用母节 cycle1 32 分滚奏);hat 16 分 → **32 分**(58,
  冲刺人格核心,密度变形);m18 第 4 拍轻收(回环)
- bass:母节 16 分模式三件套原位(104/重音 116,轮 2/4 模式渐进、bar3 移位
  3+2+3)、每轮 bar2 应答 BASS_ANSWER 原位(106/104/106/102)、m18 回环——
  与母节 bass_harmony 逐行一致,零改动
- hook:母节 HOOK_PHRASE/HOOK_HIGH 原位,vel 76/66(母节原值);
  **删八度叠置呼喊**(bar1 句头单音,轮 2/4 才冲 HOOK_HIGH,同母节)
- timpani/M3:母节原位(2.0 根音 66/70/74/72 + 轮 4 双音滚;rel 3/7/11 M3 齐击
  38@78)——旧版 +6 提升(72-80)与 M3 84 顿足收回;M3 只由 timpani/kick/bass
  三件套承担
- fx:riser 用母节 42-72 原版(rel 3/7/11,六音 16 分上行,RISER_VEL 原位);
  **删 32 分两八度往返版**(RISER_32 素材 + 46-78 渐强整体删除);
  0.0 低脉冲(57,42)
- piano:母节原位双音(根音 +12,64)——旧版双八度(+12+24)第三音删除
- strings/pad/choir/vln1 回声:母节原位(58/42/50/62;riser 小节缩 2.0 让位;
  m18 弦乐预挂 Em)
- CC11:母节轮起点 80/82/84/82 微弧(原位)
- BPM:build 内显式 s.tempo(176, bt(bar0))(参照旧 s5_extract 写法)
- 与母节共享:16 小节网格 / Em-C-G-D 循环 / m18 回环轻收;
  __main__ 两圈演示(32 小节 ≈ 43.6s)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS

# 16 小节和弦序(与母节共享骨架:轮1 Em Em C D,轮2-4 Em C G D)
CHORDS16 = ('Em', 'Em', 'C', 'D', 'Em', 'C', 'G', 'D',
            'Em', 'C', 'G', 'D', 'Em', 'C', 'G', 'D')

# ============ 母节素材原位(与 bass_harmony.py / riff_texture.py 逐行一致) ============
# 贝斯 16 分密集模式 × 3(v8.1 可听性重构,原样保留;不八度叠置、不扩展音区)
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

# 母节应答原位(不冲顶、不八度)
BASS_ANSWER = {
    'Em': (40, 43, 47, 52),
    'C':  (36, 43, 48, 52),
    'G':  (31, 43, 47, 50),
    'D':  (38, 45, 50, 45),
}
ANSWER_VEL = (106, 104, 106, 102)
BASS_VEL = 104                       # 母节 bass 基速(原位)
BASS_ACC = 12                        # 母节重音增量

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
STR_VEL = 58                        # 母节弦乐长音力度(原位)

CHOIR_VOICE = {
    'Em': (52, 55, 64),
    'C':  (48, 52, 55),
    'G':  (55, 62, 67),
    'D':  (50, 54, 62),
}
PIANO_ROOT = {'Em': 40, 'C': 36, 'G': 43, 'D': 38}

# fx riser:母节 42-72 原版(不加密、不跨八度;rel 3/7/11 六音五声上行)
RISER = {
    'Em': (64, 67, 69, 71, 74, 76),
    'D':  (62, 66, 69, 71, 74, 78),
}
RISER_VEL = (42, 48, 54, 60, 66, 72)

# hook 乐句:母节原位(vel 76/66 母节原值;无八度叠置)
HOOK_PHRASE = {
    'Em': {'bar1': 76, 'bar2': 74, 'bar3': (79, 78, 76), 'bar4': 74},
    'C':  {'bar1': 72, 'bar2': 74, 'bar3': (79, 76, 72), 'bar4': 74},
    'G':  {'bar1': 71, 'bar2': 74, 'bar3': (79, 76, 71), 'bar4': 74},
    'D':  {'bar1': 69, 'bar2': 71, 'bar3': (78, 74, 69), 'bar4': 71},
}
HOOK_HIGH = {'Em': 81, 'C': 77, 'G': 79, 'D': 78}
HOOK_LONG_VEL = 76                  # 母节长音(喘息点,原位)
HOOK_SHORT_VEL = 66                 # 母节短音(原位)

# timpani 母节原位(2.0 根音 + 轮 4 双音滚 + M3 齐击 38@78)
TIMP_ROOT = {'Em': 40, 'C': 36, 'G': 31, 'D': 38}
TIMP_VEL = (66, 70, 74, 72)

CC11_TIER = (80, 82, 84, 82)         # 母节轮起点 CC11 微弧(原位)

ROLES = ('drums', 'bass_electric', 'vln1', 'vln2', 'vla', 'celli',
         'piano_bang', 'synth_pad', 'choir', 'hook', 'timpani', 'fx')


def build(s, bar0, cycle, ch):
    """铺 16 小节 S5 v2(小节 = bar0 起),全程 176 BPM。返回 bar0+16。"""
    B = 'bass_electric'
    V1, V2, VA, VC = 'vln1', 'vln2', 'vla', 'celli'

    def bt(bar):
        return (bar - 1) * 4

    def riff_dense(bar, mode, prog, vel, answer=False, shift=False):
        """16 分密集驱动(母节原位);重音 3+3+2(0/1.5/3.0)或移位 3+2+3;
        answer:末 4 音换母节应答原位(对话链)"""
        pat = BASS_MODES[mode][prog]
        acc = (0, 6, 10) if shift else (0, 6, 12)
        if answer:
            pat = pat[:12] + BASS_ANSWER[prog]
        for i, p in enumerate(pat):
            if answer and i >= 12:
                v = ANSWER_VEL[i - 12]
            else:
                v = vel + (BASS_ACC if i in acc else 0)
            dur = 0.36 if (i in acc or (answer and i >= 12)) else 0.24
            s.note(B, p, v, bt(bar) + i * 0.25, dur)

    def strchord(bar, prog, vel, dur):
        c, v3, v5, r1 = VOICES[prog]
        s.note(VC, c, vel, bt(bar), dur)
        s.note(VA, v3, vel, bt(bar), dur)
        s.note(V2, v5, vel, bt(bar), dur)
        s.note(V1, r1, vel, bt(bar), dur)

    for r in ROLES:
        assert r in ch, f's5_extract_v2: 通道映射缺少角色 {r}'

    # 本子节全程 176(冲刺;撤离倒计时节奏,参照旧 s5_extract 写法)
    s.tempo(176, bt(bar0))

    # CC11 轮起点微弧(母节 80/82/84/82 原位)
    for role in ROLES:
        for i, ccv in enumerate(CC11_TIER):
            s.cc(role, 11, ccv, bt(bar0 + i * 4))

    # ---------------- drums:母节骨架 + hat 32 分(冲刺核心) ----------------
    dk = 3 if cycle == 1 else 0                    # 母节 cycle1 kick +3(轮次微变)
    for i in range(16):
        shift = (i % 4 == 2)                       # 每轮 bar3:重音移位(句法转)
        for j in range(8):
            b = j * 0.5
            if i == 15 and b == 3.0:
                continue                           # m18 第 4 拍无重音(回环)
            if shift and b == 3.0:
                vel = 92 + dk                      # 移位小节:3.0 降普通(3+2+3)
            else:
                acc = (0.0, 1.5, 2.5) if shift else (0.0, 1.5, 3.0)
                vel = 104 + dk if b in acc else 92 + dk
            s.note('drums', 36, vel, bt(bar0 + i) + b, 0.2)
        for b in ((1.0,) if i in (7, 11) else (1.0, 3.0)):   # rel 7/11 的 3.0 背拍让位 fill
            s.note('drums', 38, 98 + dk, bt(bar0 + i) + b, 0.2)
        for j in range(32):                        # **hat 32 分全程**(冲刺人格核心)
            s.note('drums', 42, 58, bt(bar0 + i) + j * 0.125, 0.08)
        if shift:
            s.note('drums', 44, 74, bt(bar0 + i) + 2.75, 0.15)   # 开镲(母节原位)
    for i in (0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14):   # 幽灵音(母节原位)
        for j in (1, 7, 9, 15):
            s.note('drums', 38, 45, bt(bar0 + i) + j * 0.25, 0.1)
    for i in (0, 4, 8, 12):                        # crash 轮起点(母节原位)
        s.note('drums', 49, 96, bt(bar0 + i), 1.0)
    for b, v in ((3.5, 96), (3.75, 88)):           # 轮1 bar4 末小 fill(母节原位)
        s.note('drums', 38, v, bt(bar0 + 3) + b, 0.2)
    for rel in (7, 11):                            # 32 分 snare 滚奏 fill(母节 cycle1 版)
        for j in range(16):
            vel = 98 if j in (0, 8) else 92
            s.note('drums', 38, vel, bt(bar0 + rel) + 2.0 + j * 0.125, 0.09)

    # ---------------- bass:母节 16 分模式原位 + 应答 + m18 回环 ----------------
    plan = BASS_PLAN if cycle == 0 else (1, 1, 1, 1, 2, 2, 2, 2, 0, 0, 0, 0, 1, 1, 1, 1)
    for i in range(15):
        riff_dense(bar0 + i, plan[i], CHORDS16[i], BASS_VEL,
                   answer=(i % 4 == 1), shift=(i % 4 == 2))
        dur = 2.0 if i in (3, 7, 11) else 3.9      # riser 让位
        strchord(bar0 + i, CHORDS16[i], STR_VEL, dur)
    strchord(bar0 + 15, 'Em', STR_VEL, 3.9)        # m18 弦乐预挂 Em(母节回环工程)
    for k in range(16):                            # m18 bass:D pattern,尾 4 音降力
        v = BASS_VEL + (BASS_ACC if k in (0, 6, 12) else 0)
        if k >= 12:
            v -= 12
        s.note(B, BASS_P1['D'][k], v, bt(bar0 + 15) + k * 0.25, 0.24)

    # vln1 回声(每轮 bar1/3 句尾,母节原位 62)
    for rel in ECHO_RELS:
        bar = bar0 + rel
        p0, p1 = ECHO_PAIR[CHORDS16[rel]]
        s.note(V1, p0, 62, bt(bar) + 3.5, 0.2)
        s.note(V1, p1, 62, bt(bar) + 3.75, 0.2)

    # ---------------- pad/choir 长音(母节原位 42/50,riser 小节缩 2.0) ----------------
    for rel in range(16):
        cname = CHORDS16[rel]
        dur = 2.0 if rel in (3, 7, 11) else 3.9
        s.chord('synth_pad', CHOIR_VOICE[cname], 42, bt(bar0 + rel), dur)
        s.chord('choir', CHOIR_VOICE[cname], 50, bt(bar0 + rel), dur)

    # ---------------- piano 0.0 锚点(母节原位双音,64;无第三八度) ----------------
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

    # ---------------- hook 乐句原位(vel 76/66;无八度叠置呼喊) ----------------
    for rel in range(16):
        cname = CHORDS16[rel]
        ph = HOOK_PHRASE[cname]
        k = rel % 4
        hi = (rel // 4) % 2 == 1                   # 轮 2/4 句头高音(母节原位)
        long_vel = HOOK_LONG_VEL - (8 if rel == 15 else 0)
        short_vel = HOOK_SHORT_VEL - (8 if rel == 15 else 0)
        if k == 0:                                 # bar1:句头长音(单音,不叠)
            p = HOOK_HIGH[cname] if hi else ph['bar1']
            s.note('hook', p, long_vel, bt(bar0 + rel) + 3.5, 0.8)
        elif k == 1:                               # bar2:短音(让位 bass 应答)
            s.note('hook', ph['bar2'], short_vel, bt(bar0 + rel) + 2.5, 0.3)
        elif k == 2:                               # bar3:短句 0.5/2.0 + 句尾长音
            p3 = ph['bar3']
            s.note('hook', p3[0], short_vel, bt(bar0 + rel) + 0.5, 0.3)
            s.note('hook', p3[1], short_vel, bt(bar0 + rel) + 2.0, 0.3)
            s.note('hook', p3[2], long_vel, bt(bar0 + rel) + 3.5, 0.8)
        else:                                      # bar4:短收(rel 15 减力回环)
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
    s.tempo(176, 0.0)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert build(s, 3, 0, CH) == 19
        assert build(s, 19, 1, CH) == 35          # 两圈演示(32 小节 ≈ 43.6s)
        s.flush('S5_Extract_v2.mid')
    out = buf.getvalue()
    print(out)
    conf = out.count('[冲突]')
    warn = out.count('[音区告警]')
    ok = conf == 0 and warn == 0
    print(f'S5v2 冒烟: {"PASS" if ok else "FAIL"} S5_Extract_v2.mid(冲突 {conf} 处,音区告警 {warn} 处,期望均 0)')
    sys.exit(0 if ok else 1)
