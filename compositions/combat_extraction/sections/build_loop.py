#!/usr/bin/env python3
"""build_loop.py — 《搜打撤》无缝大循环 v2(宏观框架版,2026-08-05 用户反馈重构)

用户裁决(2026-08-05):拼贴版(段落方块 + 桥)生硬——节奏型/音区/密度三重裸跳,
听众毫无预期(如 bass 8 分根音 → 16 分高把位)。
本版**不再拼段落**:128 小节 = 单一连续发展,4 幕 × 32 小节,每 8 小节一演化档,
档间是**递进**不是切换——所有声部沿各自演化轴连续渐变,素材 100% 取自母节
v9 已验收体系(音高/音色/乐句原样),恒速 168(无 176 变速),Em-C-G-D 连续轮转。

宏观框架(起承转合):
  第一幕 起(1-32): 引入——bass 根音 8 分 → 8分+尾16 微升;hat 8→16 分;hook 句头
  第二幕 承(33-64): 展开——bass P1→P2 全 16 分;kick 3+3+2;ghost/fill/timpani 进入;
                    brass 轻进;hook 完整乐句
  第三幕 转(65-96): 满配高点 → 抽离(层渐撤,bass 降 8 分)→ 心跳(kick 双发 +
                    hook 高区闪烁)→ 解冻(32 分 hat 渐入 + 心跳重音)
  第四幕 合(97-128): 冲刺(全层 + 32 分 hat + 鼓最重)→ 回落 → 预伏(回到第一幕
                    入口能量,循环点自然闭合)

演化轴(解决裸跳;每轴 4-6 档,每档 ≥8 小节):
  bass:ROOT8 → ROOT8T16 → P1 → P2 → P3 → ROOT8T16 → ROOT8H → ROOT8T16 → P1 → ROOT8T16 → ROOT8
  kick:每拍 → 3+3+2 → 双发心跳 → 心跳+重音 → 3+3+2 → 每拍
  hat: 8 分 → 16 分 →(抽离)→ 32 分 → 16 分 → 8 分
  vel/CC11: 74 → 84 → 74 → 84 → 76(全程连续曲线,无台阶)

用法:python3 sections/build_loop.py [--cycle N]
输出:Combat_Extraction_Loop.mid(128 小节 ≈ 183s;渲染后须按 MIDI 长度裁剪混响尾)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS
import compose                                   # ROLE_CH(唯一通道表来源)
from layers.drums import TIMP_ROOT
from layers.bass_harmony import (BASS_P1, BASS_P2, BASS_P3, BASS_ANSWER,
                                  ANSWER_VEL, VOICES, ECHO_PAIR)
from layers.riff_texture import (HOOK_PHRASE, HOOK_HIGH, CHOIR_VOICE, RHY_CHORD,
                                  RISER, RISER_VEL, M2, M3_PITCH)

# ---------------- 和弦轮转(母节骨架,128 小节连续) ----------------
CHORDS16 = ('Em', 'Em', 'C', 'D', 'Em', 'C', 'G', 'D',
            'Em', 'C', 'G', 'D', 'Em', 'C', 'G', 'D')

# ---------------- 素材:根音 8 分脉冲(S1 已验证 ⊆ 母节音高集) ----------------
ROOT8 = {
    'Em': (28, 28, 40, 28, 28, 40, 28, 40),   # 末音 40(E2,母节验证;S1 原 35=G2 母节无此音)
    'C':  (36, 36, 48, 36, 36, 48, 36, 43),
    'G':  (31, 31, 43, 31, 31, 43, 31, 38),
    'D':  (38, 38, 50, 38, 38, 50, 38, 45),
}
ROOT8H = {   # 心跳版:仅根音 8 分(更静)
    'Em': (28, 28, 28, 28, 28, 28, 28, 28),
    'C':  (36, 36, 36, 36, 36, 36, 36, 36),
    'G':  (31, 31, 31, 31, 31, 31, 31, 31),
    'D':  (38, 38, 38, 38, 38, 38, 38, 38),
}
PIANO_ROOT = {'Em': 40, 'C': 36, 'G': 43, 'D': 38}
# HOOK_HIGH 的 C=77(F5)母节从未发声且非 C 五声(S-BT 教训)→ C 用 79(G5 和弦音)
HOOK_HIGH_FIX = dict(HOOK_HIGH, C=79)
# 刺刀密度/力度(母节 v9 完全辅助口径)
STAB_SLOTS = ((0.75,), (0.75, 1.25), (0.75, 1.25), ())
STAB_VEL = ((66,), (70, 76), (70, 76), ())

# ---------------- 演化档(16 档 × 8 小节 = 128) ----------------
# 字段:bass 模式 / bass vel / kick 模式 / kick vel / snare / hat / ghost / fill /
#       hook / brass / riser / timpani / CC11 / 弦乐 vel / pad vel
# bass:ROOT8 ROOT8T16 P1 P2 P3 ROOT8H | kick:EVERY HEAVY HEART HEART_ACC
# hook:NONE HEAD FULL HIGH FLASH
STAGES = [
    # ---- 第一幕 起(1-32):引入 ----
    dict(bass='ROOT8', bvel=72, kick='EVERY', kvel=66, snare=54, hat=8,
         ghost=0, fill=0, hook='NONE', brass=0, riser=0, timp=0, cc=74, svel=40, pvel=28),
    dict(bass='ROOT8', bvel=76, kick='EVERY', kvel=70, snare=58, hat=8,
         ghost=0, fill=0, hook='NONE', brass=0, riser=0, timp=0, cc=76, svel=42, pvel=30),
    dict(bass='ROOT8T16', bvel=80, kick='EVERY', kvel=72, snare=58, hat=16,
         ghost=0, fill=0, hook='HEAD', brass=0, riser=0, timp=0, cc=76, svel=44, pvel=32),
    dict(bass='ROOT8T16', bvel=84, kick='EVERY', kvel=74, snare=60, hat=16,
         ghost=0, fill=0, hook='HEAD', brass=0, riser=0, timp=0, cc=78, svel=46, pvel=34),
    # ---- 第二幕 承(33-64):展开 ----
    dict(bass='P1', bvel=90, kick='HEAVY', kvel=86, snare=62, hat=16,
         ghost=1, fill=0, hook='FULL', brass=0, riser=0, timp=52, cc=80, svel=50, pvel=38),
    dict(bass='P1', bvel=92, kick='HEAVY', kvel=92, snare=64, hat=16,
         ghost=1, fill=0, hook='FULL', brass=0, riser=1, timp=56, cc=82, svel=52, pvel=40),
    dict(bass='P2', bvel=94, kick='HEAVY', kvel=96, snare=66, hat=16,
         ghost=1, fill=1, hook='HIGH', brass=1, riser=1, timp=60, cc=82, svel=54, pvel=42),
    dict(bass='P2', bvel=96, kick='HEAVY', kvel=100, snare=68, hat=16,
         ghost=1, fill=1, hook='HIGH', brass=1, riser=1, timp=64, cc=84, svel=56, pvel=44),
    # ---- 第三幕 转(65-96):满配高点 → 抽离 → 心跳 → 解冻 ----
    dict(bass='P3', bvel=98, kick='HEAVY', kvel=104, snare=72, hat=16,
         ghost=1, fill=1, hook='HIGH', brass=1, riser=1, timp=68, cc=84, svel=58, pvel=46),
    dict(bass='ROOT8T16', bvel=88, kick='EVERY', kvel=90, snare=64, hat=8,
         ghost=0, fill=0, hook='HEAD', brass=0, riser=0, timp=56, cc=80, svel=54, pvel=42),
    dict(bass='ROOT8H', bvel=74, kick='HEART', kvel=80, snare=0, hat=0,
         ghost=0, fill=0, hook='FLASH', brass=0, riser=0, timp=0, cc=74, svel=46, pvel=36),
    dict(bass='ROOT8T16', bvel=84, kick='HEART_ACC', kvel=86, snare=60, hat=32,
         ghost=0, fill=0, hook='HEAD', brass=0, riser=0, timp=0, cc=78, svel=50, pvel=38),
    # ---- 第四幕 合(97-128):冲刺 → 回落 → 预伏 ----
    dict(bass='P1', bvel=96, kick='HEAVY', kvel=108, snare=76, hat=32,
         ghost=1, fill=1, hook='HIGH', brass=1, riser=1, timp=74, cc=84, svel=58, pvel=46),
    dict(bass='P2', bvel=94, kick='HEAVY', kvel=104, snare=72, hat=16,
         ghost=1, fill=1, hook='HIGH', brass=1, riser=1, timp=72, cc=84, svel=58, pvel=46),
    dict(bass='ROOT8T16', bvel=90, kick='EVERY', kvel=92, snare=66, hat=16,
         ghost=0, fill=0, hook='HEAD', brass=0, riser=0, timp=60, cc=80, svel=52, pvel=40),
    dict(bass='ROOT8', bvel=74, kick='EVERY', kvel=70, snare=58, hat=8,
         ghost=0, fill=0, hook='NONE', brass=0, riser=0, timp=0, cc=76, svel=42, pvel=30),
]


def _hook_head(prog, hi):
    return HOOK_HIGH_FIX[prog] if hi else HOOK_PHRASE[prog]['bar1']


def build(s, loop_cycle=0):
    """铺 128 小节无缝大循环(小节 1-128)。"""
    def B(i):
        return (i - 1) * 4                     # 小节 i(1-based)首拍

    for si, st in enumerate(STAGES):
        bar0 = si * 8 + 1
        # CC11 档值(档内恒定,档间渐变;GUGS 响应 CC11,全 ≥74 保可闻)
        for r in ('drums', 'bass_electric', 'vln1', 'vln2', 'vla', 'celli',
                  'synth_pad', 'choir', 'piano_bang', 'hook', 'timpani',
                  'brass_stab', 'fx', 'synth_rhythm'):
            s.cc(r, 11, st['cc'], B(bar0))

        for rel in range(8):
            i = bar0 + rel                     # 绝对小节(1-based)
            prog = CHORDS16[(i - 1) % 16]
            t = B(i)
            wheel = ((i - 1) // 4) % 4         # 轮次(0-3)
            hi = wheel % 2 == 1                # 轮 2/4(句头高音)
            last_bar = (si == 15 and rel == 7)  # 整曲最后一小节(轻收回环)

            # ---------- bass(节奏型演化轴) ----------
            mode, bv = st['bass'], st['bvel']
            if mode == 'ROOT8':
                for j, p in enumerate(ROOT8[prog]):
                    dur = 0.9 if (last_bar and j == 7) else 0.45
                    s.note('bass_electric', p, bv + (6 if j == 7 else 0),
                           t + j * 0.5, dur)
            elif mode == 'ROOT8H':
                for j in range(8):
                    s.note('bass_electric', ROOT8H[prog][j], bv, t + j * 0.5, 0.35)
            elif mode == 'ROOT8T16':
                for j in range(6):             # 前 3 拍根音 8 分
                    s.note('bass_electric', ROOT8[prog][j], bv, t + j * 0.5, 0.4)
                for j, p in enumerate(BASS_P1[prog][12:16]):   # 第 4 拍 16 分尾
                    s.note('bass_electric', p, bv + 6, t + 3.0 + j * 0.25, 0.22)
            else:                              # P1/P2/P3 全 16 分(3+3+2,bar3 移位)
                table = {'P1': BASS_P1, 'P2': BASS_P2, 'P3': BASS_P3}[mode]
                pat = BASS_P2[prog] if (loop_cycle % 2 and mode == 'P1') else table[prog]
                shift = (rel % 4 == 2)
                acc = (0, 6, 10) if shift else (0, 6, 12)
                for j, p in enumerate(pat):
                    v = bv + (12 if j in acc else 0)
                    if rel % 4 == 1 and j >= 12:       # 轮 bar2 对话链应答(原位)
                        p = BASS_ANSWER[prog][j - 12]
                        v = ANSWER_VEL[j - 12]
                    dur = 0.36 if (j in acc or (rel % 4 == 1 and j >= 12)) else 0.24
                    s.note('bass_electric', p, v, t + j * 0.25, dur)

            # ---------- drums(鼓模式演化轴) ----------
            kk, kv = st['kick'], st['kvel']
            if kk == 'EVERY':
                for b in (0.0, 1.0, 2.0, 3.0):
                    if last_bar and b == 3.0:
                        continue               # 整曲末第 4 拍轻收(回环)
                    s.note('drums', 36, kv, t + b, 0.2)
            elif kk == 'HEAVY':
                shift = (rel % 4 == 2)
                for j in range(8):
                    b = j * 0.5
                    if last_bar and b == 3.0:
                        continue
                    acc = (0.0, 1.5, 2.5) if shift else (0.0, 1.5, 3.0)
                    v = kv + 10 if b in acc else kv
                    s.note('drums', 36, v, t + b, 0.2)
            elif kk == 'HEART':                # 双发心跳(重 80/轻 64)
                for j in range(8):
                    s.note('drums', 36, kv if j % 2 == 0 else kv - 16,
                           t + j * 0.5, 0.18)
            elif kk == 'HEART_ACC':            # 心跳+3+3+2 重音(解冻过渡)
                for j in range(8):
                    v = kv if j % 2 == 0 else kv - 16
                    if j in (0, 4, 6):
                        v += 10                # 0.0/2.0/3.0(3+3+2 位)
                    s.note('drums', 36, v, t + j * 0.5, 0.18)
            if st['snare']:
                bs = (1.0,) if (st['fill'] and rel in (3, 7)) else (1.0, 3.0)
                for b in bs:
                    s.note('drums', 38, st['snare'], t + b, 0.2)
            if st['hat'] == 8:
                for j in range(8):
                    s.note('drums', 42, 44, t + j * 0.5, 0.15)
            elif st['hat'] == 16:
                for j in range(16):
                    s.note('drums', 42, 52, t + j * 0.25, 0.12)
            elif st['hat'] == 32:
                for j in range(32):
                    s.note('drums', 42, 58 if j % 4 else 50, t + j * 0.125, 0.08)
            if st['ghost'] and rel % 4 != 3:   # 幽灵音(bar4 让位 fill/M3)
                for j in (1, 7, 9, 15):
                    s.note('drums', 38, 45, t + j * 0.25, 0.1)
            if st['fill'] and rel in (3, 7):   # 轮末 fill(16 分 8 音)
                for j in range(8):
                    v = 98 if j in (0, 4) else 90
                    s.note('drums', 38, v, t + 2.0 + j * 0.25, 0.2)
            if kk == 'HEAVY' and rel % 4 == 0:
                s.note('drums', 49, 96, t, 1.0)     # 轮起点 crash

            # ---------- timpani / M3(满配档) ----------
            if st['timp']:
                d = 0.2 if wheel == 3 else 0.4
                s.note('timpani', TIMP_ROOT[prog], st['timp'], t + 2.0, d)
                if wheel == 3:
                    s.note('timpani', TIMP_ROOT[prog], st['timp'] - 12, t + 2.25, 0.25)
                if st['riser'] and rel % 4 == 3:     # 轮末 M3(仅 D 和弦,三件套)
                    s.note('timpani', 38, 78, t + 3.0, 0.4)

            # ---------- fx riser(轮末 D 和弦,母节 42-72 原版) ----------
            if st['riser']:
                s.note('fx', 57, 42, t, 0.22)        # 0.0 低脉冲
                if rel % 4 == 3 and prog == 'D':
                    for j, p in enumerate(RISER['D']):
                        s.note('fx', p, RISER_VEL[j], t + 2.0 + j * 0.25, 0.22)

            # ---------- brass(M2 和弦分解刺刀,母节 v9 完全辅助口径 1/2/2/0) ----------
            if st['brass']:
                k = rel % 4
                cell = M2[prog]
                for idx, b in enumerate(STAB_SLOTS[k]):
                    s.note('brass_stab', cell[idx], STAB_VEL[k][idx], t + b, 0.35)
                if st['riser'] and rel % 4 == 3 and prog == 'D':
                    s.note('brass_stab', M3_PITCH['D'], 76, t + 3.0, 0.3)  # M3 齐奏

            # ---------- synth_rhythm(轮 2/4 出场,母节 v9 口径) ----------
            if st['riser'] and hi and rel % 4 != 3:
                for b in (0.25, 2.0):
                    s.chord('synth_rhythm', RHY_CHORD[prog], 58, t + b, 0.25)

            # ---------- hook(乐句演化轴) ----------
            hm = st['hook']
            ph = HOOK_PHRASE[prog]
            k = rel % 4
            if hm == 'HEAD' and k == 0:
                s.note('hook', _hook_head(prog, hi), 64, t + 3.5, 0.8)
            elif hm in ('FULL', 'HIGH'):
                base = 70 if hm == 'HIGH' else 66
                if k == 0:
                    s.note('hook', _hook_head(prog, hi), base, t + 3.5, 0.8)
                elif k == 1:
                    s.note('hook', ph['bar2'], base - 4, t + 2.5, 0.3)
                elif k == 2:
                    s.note('hook', ph['bar3'][0], base - 4, t + 0.5, 0.3)
                    s.note('hook', ph['bar3'][1], base - 4, t + 2.0, 0.3)
                    s.note('hook', ph['bar3'][2], base, t + 3.5, 0.8)
                else:
                    s.note('hook', ph['bar4'], base - 4, t + 3.5, 0.3)
            elif hm == 'FLASH' and rel % 2 == 0:     # 高区闪烁(心跳幕,弧线)
                flash = {0: (81, 76), 2: (79,), 4: (81, 78), 6: (71,)}[rel % 8]
                for j, p in enumerate(flash):
                    s.note('hook', p, 70 if j == 0 else 64,
                           t + (2.5 if j == 0 else 3.5), 0.45)

            # ---------- 弦乐 / pad / choir / piano ----------
            sv, pv = st['svel'], st['pvel']
            c, v3, v5, r1 = VOICES[prog]
            dur = 2.0 if (st['riser'] and rel % 4 == 3) else 3.9
            for name, p in (('celli', c), ('vla', v3), ('vln2', v5), ('vln1', r1)):
                s.note(name, p, sv, t, dur)
            s.chord('synth_pad', CHOIR_VOICE[prog], pv, t, dur)
            s.chord('choir', CHOIR_VOICE[prog], pv + 4, t, dur)
            s.note('piano_bang', PIANO_ROOT[prog], 36, t, 0.3)
            s.note('piano_bang', PIANO_ROOT[prog] + 12, 36, t, 0.3)
            if rel % 4 in (0, 2) and prog in ECHO_PAIR:
                p0, p1 = ECHO_PAIR[prog]
                s.note('vln1', p0, 46, t + 3.5, 0.2)
                s.note('vln1', p1, 46, t + 3.75, 0.2)

    return 128


if __name__ == '__main__':
    import contextlib, io
    loop_cycle = 0
    if '--cycle' in sys.argv:
        loop_cycle = int(sys.argv[sys.argv.index('--cycle') + 1])
    s = Score(humanize=True, seed=42)
    for role, chn in compose.ROLE_CH.items():
        if role == 'hook':
            bank, prog, (lo, hi), pan, rev = PROGS['synth_lead']
        else:
            bank, prog, (lo, hi), pan, rev = PROGS[role]
        s.add_instr(role, chn, bank, prog, lo, hi, pan, rev)
        s.cc(role, 7, 100, 0.0)
    s.tempo(168, 0.0)
    build(s, loop_cycle)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        s.flush('Combat_Extraction_Loop.mid')
    out = buf.getvalue()
    bad = out.count('[音区告警]') + out.count('  [冲突]')
    print(out, end='')
    print(f'LOOP v2 冒烟: {"PASS" if bad == 0 else "FAIL"} Combat_Extraction_Loop.mid'
          f'(cycle={loop_cycle}, 128 小节, 告警+冲突 = {bad})')
    sys.exit(0 if bad == 0 else 1)
