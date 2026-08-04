#!/usr/bin/env python3
"""transitions.py — 《搜打撤》子节转场元素库(插入式转场)

设计(父会话拍板,2026-08):
- **插入式转场**:切换点 = 前节最后一小节结束后,插入 1-2 小节独立过渡小节,
  再进入后节;过渡小节不参与 16 小节循环(游标照常连续推进)。
- 每个过渡元素 = 独立小节模板函数,签名统一
  `def <name>(s, bar0, ch, **kw) -> bar0+n`(bar0 为 1-based 起始小节号)。
- 所有元素只用现有角色(fx / drums / bass_electric / synth_pad / vln2 / vla / celli),
  不新增音色素材;全部与母节共享 Em-C-G-D 骨架与 168 BPM 网格
  (唯一例外:crash_stop 的 `tempo` 关键字参数做 BPM 回写,S5→S6 用 176→168)。

⚠️ GUGS 响应 CC11:所有音符所在角色 CC11 ≥ 70(riser 渐强段起始允许 60-70),
否则近静音——本库每个元素在落音前先写 CC11 节点(70-84)。

元素一览:
  riser(s, bar0, ch, chord='Em') ............ 2 小节 16 分五声上行渐强(vel 40→72)
                                               + 弦乐/pad 挂留(根音+纯五度,vel 40)
  down_fx(s, bar0, ch, chord='Em') .......... 1 小节 4 音五声下行(vel 64→52)
                                               + 后 2 拍进入方根音低音预挂(vel 60)
  roll32(s, bar0, ch) ....................... 1 小节 snare 32 分滚奏渐强(vel 40→80)
                                               + 小节末 kick 重击(92)
  crash_stop(s, bar0, ch, tempo=None, chord='Em')
                                         ..... 1 小节急停:crash(90)+ 根音长音(66,3 拍)
                                               + 第 2 拍起休止;tempo 用于 BPM 回写(s.tempo)
  harmony_prehang(s, bar0, ch, chord='Em') .. 1 小节和声预挂:根音低音 2 拍(64)
                                               + pad 轻和声(vel 40)
  time_fold(s, bar0, ch, chord='Em') ......... 1 小节 时间折叠(交火→时停,落 S-BT 入口):
                                               低频挂留渐隐(bass 根音 + vla 五度,CC11 74→62
                                               = 低通感)+ fx 五声下行快拂(60→44)+ 末拍
                                               心跳 kick 双发预告(80/68);≤1 小节边界
  time_unfold(s, bar0, ch) ................... 1 小节 时间展开(时停→交火):32 分 snare
                                               滚奏渐强 2 拍(40→88)+ 密度骤回(kick/crash/
                                               snare 交火短语,落母节/交火段入口)
  loop_return(s, bar0, ch) ................... 2 小节 循环预伏(无缝回环,S6→S1 专用):
                                               小节 1 静息延续(弦乐/pad 恢复长音,CC11 回升);
                                               小节 2 = S1 首小节逐字复刻(bass 8 分脉冲 +
                                               kick/snare/hat/crash)——循环点两侧为两个
                                               相同小节,接缝不可察觉
  step_up(s, bar0, ch) ....................... 1 小节 轻升档桥(S1→S2):S1 素材本体延续,
                                               snare 58→62 + hat 48→50(步态变警觉)
  engine_start(s, bar0, ch) .................. 2 小节 引擎启动桥(S2→母节):小节 1 怠速
                                               (8 分步态 + kick 3+3+2 轻入),小节 2 全速
                                               (bass BASS_P1 16 分原位 + kick 满 + hat 16 分)
  morph_crisis(s, bar0, ch) .................. 1 小节 塌缩变形桥(母节→S4):满配层撤空 +
                                               kick 3+3+2→心率双发 + bass 16 分→8 分
  accel_roll(s, bar0, ch) .................... 1 小节 加速滚奏桥(S4→S5):snare 32 分滚奏
                                               + hat 32 分渐入 + bass 根音脉冲(176 由 S5 处理)

衔接矩阵 TRANSITIONS:节点 'S1'..'S6'(S3 = 母节)+ 'S-BT'(时停),键 (from, to) →
(元素名, 说明)。合法衔接(游戏流程内)14 条:4 动机桥 + 3 反向 + 2 时停 + 2 循环
(('S6','S1') → loop_return 无缝回环 / ('S5','S1') → loop_return 冲刺直回)+ 1 冲刺
(('S4','S5') → accel_roll)+ 2 备用(('S3','S5') → roll32 / 简单场景可用 riser)。
⚠️ 大循环/连播成品一律用**动机桥**(step_up/engine_start/morph_crisis/accel_roll):
素材取自相邻段落(节奏密度渐变 + 音色预伏),听感 = 段落自然变形,不是插入式音效;
riser/down_fx/roll32 保留为简单场景与反向衔接备用。
demo 连播(六子节)依据本矩阵插转场,见 sections/demo_playthrough.py;
大循环成品见 sections/build_loop.py。

冒烟测试:python3 sections/transitions.py → /tmp/smk_trans.mid
(4 小节 S1 风格骨架 + 连续插入 riser/down_fx/roll32/crash_stop/harmony_prehang/
time_fold/time_unfold,断言 0 音区告警 / 0 冲突 / 小节数正确)。运行前先清 __pycache__(缓存纪律)。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS

# ---------------------------------------------------------------------------
# 和弦表(与母节共享骨架;根音取母节 bass 锚点口径)
# ---------------------------------------------------------------------------
# 低音根音(贝斯预挂/急停长音用;与母节 BASS_P1 锚点一致:Em→E1 C→C2 G→G1 D→D2)
ROOT_LOW = {'Em': 28, 'C': 36, 'G': 31, 'D': 38}
# 五声音阶基准音(进入方第 1 和弦根音,取可入 fx 音区 55-90 的八度;与母节 timpani 根音一致)
SCALE1 = {'Em': 40, 'C': 36, 'G': 31, 'D': 38}
# 五声音阶(从根音起算的音程):Em 小调五声 / C G D 大调五声
PENTA = {'Em': (0, 3, 5, 7, 10), 'C': (0, 2, 4, 7, 9),
         'G': (0, 2, 4, 7, 9), 'D': (0, 2, 4, 7, 9)}
# riser 挂留(根音+纯五度,各角色可演奏八度):celli 根音 / vla 五度 / vln2 根音 / pad 根音+五度
SUSP = {
    'Em': {'celli': 40, 'vla': 59, 'vln2': 64, 'synth_pad': (64, 71)},
    'C':  {'celli': 36, 'vla': 55, 'vln2': 60, 'synth_pad': (60, 67)},
    'G':  {'celli': 31, 'vla': 62, 'vln2': 55, 'synth_pad': (55, 62)},
    'D':  {'celli': 38, 'vla': 57, 'vln2': 62, 'synth_pad': (62, 69)},
}
# 挂留参与角色(riser 用;弦乐/pad 铺 2 小节长音)
SUSP_ROLES = ('celli', 'vla', 'vln2', 'synth_pad')


def _penta_ascent(chord):
    """从根音起算的五声上行 11 音(root+24 → root+48,跨 2 个八度,全部落在 fx 55-90 内)。"""
    root = SCALE1[chord]
    penta = PENTA[chord]
    return [root + 24 + penta[k % 5] + 12 * (k // 5) for k in range(11)]


# ---------------------------------------------------------------------------
# 过渡元素(每个 = 独立小节模板函数,插入式:不参与 16 小节循环)
# ---------------------------------------------------------------------------

def riser(s, bar0, ch, **kw):
    """2 小节:16 分五声上行(fx,vel 40→72 渐强,从进入方第 1 和弦根音起算音阶,
    结尾落在进入方根音 +2 八度)+ 弦乐/pad 铺进入方和弦挂留(根音+纯五度,轻 vel 40)。"""
    chord = kw.get('chord', 'Em')
    assert chord in PENTA, f'riser: 未知和弦 {chord}'
    for r in SUSP_ROLES + ('fx',):
        assert r in ch, f'riser: 通道映射缺少角色 {r}'
    t0 = (bar0 - 1) * 4
    ascent = _penta_ascent(chord)
    ceil = SCALE1[chord] + 48                      # 顶格 = 进入方根音(+2 八度,55-90 内)
    # CC11:fx 70→84 渐强(riser 渐强段起始允许 60-70,取上限 70);挂留角色 78(全部 ≥70)
    s.cc('fx', 11, 70, t0)
    s.cc('fx', 11, 84, t0 + 8)
    for r in SUSP_ROLES:
        s.cc(r, 11, 78, t0)
    # 挂留:2 小节长音(根音+纯五度,vel 40)
    for r, p in SUSP[chord].items():
        if isinstance(p, tuple):
            s.chord(r, p, 40, t0, 7.9)
        else:
            s.note(r, p, 40, t0, 7.9)
    # 16 分五声上行 32 音:前 11 音级进上行,到顶后保持(顶格推进),vel 40→72
    for i in range(32):
        p = ascent[i] if i < 11 else ceil
        v = 40 + round(32 * i / 31)
        s.note('fx', p, v, t0 + i * 0.25, 0.2)
    return bar0 + 2


def down_fx(s, bar0, ch, **kw):
    """1 小节:fx 4 音五声下行(vel 64→52,从顶格 root+48 起)+ 后 2 拍和声预挂
    (进入方和弦根音低音,vel 60)。"""
    chord = kw.get('chord', 'Em')
    assert chord in PENTA, f'down_fx: 未知和弦 {chord}'
    for r in ('fx', 'bass_electric'):
        assert r in ch, f'down_fx: 通道映射缺少角色 {r}'
    t0 = (bar0 - 1) * 4
    ascent = _penta_ascent(chord)
    descent = ascent[10:6:-1]                      # 顶格向下 4 音(五声级进)
    s.cc('fx', 11, 76, t0)
    s.cc('bass_electric', 11, 78, t0)
    for i, p in enumerate(descent):
        s.note('fx', p, (64, 60, 56, 52)[i], t0 + i * 0.25, 0.2)
    s.note('bass_electric', ROOT_LOW[chord], 60, t0 + 2.0, 1.9)   # 后 2 拍预挂
    return bar0 + 1


def roll32(s, bar0, ch, **kw):
    """1 小节:snare(38)32 分滚奏渐强(vel 40→80)+ 小节末 kick(36)重击(92)。"""
    assert 'drums' in ch, 'roll32: 通道映射缺少角色 drums'
    t0 = (bar0 - 1) * 4
    s.cc('drums', 11, 80, t0)
    for i in range(32):
        v = 40 + round(40 * i / 31)
        s.note('drums', 38, v, t0 + i * 0.125, 0.09)
    s.note('drums', 36, 92, t0 + 3.75, 0.2)        # 小节末重击,滚入进入方(0.2 拍,不与下节首音重叠)
    return bar0 + 1


def crash_stop(s, bar0, ch, **kw):
    """1 小节急停:0.0 crash(49,vel 90)+ 进入方和弦低音根音长音(vel 66,3 拍)
    + 第 2 拍起休止(静默,仅根音尾音)。
    `tempo` 关键字用于 BPM 回写(s.tempo)——S5→S6 用 crash_stop(..., tempo=168) 176→168。"""
    chord = kw.get('chord', 'Em')
    tempo = kw.get('tempo')
    assert chord in ROOT_LOW, f'crash_stop: 未知和弦 {chord}'
    for r in ('drums', 'bass_electric'):
        assert r in ch, f'crash_stop: 通道映射缺少角色 {r}'
    t0 = (bar0 - 1) * 4
    if tempo is not None:
        s.tempo(tempo, t0)                         # BPM 回写(进入方速度)
    s.cc('drums', 11, 84, t0)
    s.cc('bass_electric', 11, 80, t0)
    s.note('drums', 49, 90, t0, 1.9)               # crash(第 2 拍起无新攻击,休止)
    s.note('bass_electric', ROOT_LOW[chord], 66, t0, 2.9)   # 根音长音 3 拍(0.0-3.0)
    return bar0 + 1


def time_fold(s, bar0, ch, **kw):
    """1 小节:交火→时停(时间折叠,落在 S-BT 入口)。高频打击乐抽离(无 snare/hat),
    只剩低频挂留(bass 根音 + vla 五度,CC11 74→62 渐隐 = 低通感)+ fx 五声下行快拂
    (vel 60→44,折叠手势)+ 末拍心跳 kick 双发预告(80/68 = S-BT 心跳模式)。
    响应 ≤1 小节边界(时停是玩家主动触发)。"""
    chord = kw.get('chord', 'Em')
    assert chord in ROOT_LOW, f'time_fold: 未知和弦 {chord}'
    for r in ('bass_electric', 'vla', 'fx', 'drums'):
        assert r in ch, f'time_fold: 通道映射缺少角色 {r}'
    t0 = (bar0 - 1) * 4
    s.cc('bass_electric', 11, 74, t0)
    s.cc('bass_electric', 11, 62, t0 + 3.5)
    s.cc('vla', 11, 74, t0)
    s.cc('vla', 11, 62, t0 + 3.5)
    s.cc('fx', 11, 74, t0)
    s.cc('fx', 11, 58, t0 + 3.5)
    s.cc('drums', 11, 80, t0)
    # 低频挂留(低通感:高频层淡出,只剩低音呼吸)
    s.note('bass_electric', ROOT_LOW[chord], 44, t0, 3.5)
    s.note('vla', SUSP[chord]['vla'], 36, t0, 3.5)
    # fx 五声下行快拂(16 分 5 音,vel 60→44)——时间折叠手势
    ascent = _penta_ascent(chord)
    for i, p in enumerate(ascent[10:5:-1]):
        s.note('fx', p, 60 - i * 4, t0 + 0.5 + i * 0.25, 0.2)
    # 末拍心跳 kick 双发(80/68):时停心跳提前一拍预告,S-BT 0.0 接管
    s.note('drums', 36, 80, t0 + 3.0, 0.2)
    s.note('drums', 36, 68, t0 + 3.5, 0.18)
    return bar0 + 1


def time_unfold(s, bar0, ch, **kw):
    """1 小节:时停→交火(时间展开,落在母节/交火段入口)。前 2 拍 snare 32 分
    滚奏渐强(vel 40→88,16 音)→ 2.0 起密度骤回:kick 重击 + crash + snare 背拍
    + kick 3+3+2(92/88/92 交火短语),下节 0.0 满配接管。"""
    assert 'drums' in ch, 'time_unfold: 通道映射缺少角色 drums'
    t0 = (bar0 - 1) * 4
    s.cc('drums', 11, 84, t0)
    # 32 分 snare 滚奏 2 拍(16 音,0.125 拍间隔,vel 40→88 渐强)
    for i in range(16):
        v = 40 + round(48 * i / 15)
        s.note('drums', 38, v, t0 + i * 0.125, 0.09)
    # 密度骤回(2.0-3.75 交火短语:kick 3+3+2 + crash + snare 背拍)
    s.note('drums', 36, 92, t0 + 2.0, 0.2)
    s.note('drums', 49, 84, t0 + 2.0, 1.0)
    s.note('drums', 38, 88, t0 + 3.0, 0.2)
    s.note('drums', 36, 92, t0 + 3.5, 0.2)
    return bar0 + 1


def harmony_prehang(s, bar0, ch, **kw):
    """1 小节和声预挂:进入方和弦根音低音 2 拍(vel 64)+ pad 轻和声(vel 40)。"""
    chord = kw.get('chord', 'Em')
    assert chord in ROOT_LOW, f'harmony_prehang: 未知和弦 {chord}'
    for r in ('bass_electric', 'synth_pad'):
        assert r in ch, f'harmony_prehang: 通道映射缺少角色 {r}'
    t0 = (bar0 - 1) * 4
    s.cc('bass_electric', 11, 78, t0)
    s.cc('synth_pad', 11, 80, t0)
    s.note('bass_electric', ROOT_LOW[chord], 64, t0, 1.9)
    s.chord('synth_pad', SUSP[chord]['synth_pad'], 40, t0, 1.9)
    return bar0 + 1


def loop_return(s, bar0, ch, **kw):
    """2 小节:循环预伏(无缝回环,S6→S1 专用,2026-08-05 设计)。
    原理:循环点两侧 = 两个相同小节(loop_return 末小节 ≡ S1 首小节逐字复刻),
    和声 Em→Em 连续(全段共享骨架),能量从 S6 余烬经 1 小节静息回升到 S1 档。
    小节 1(静息延续):弦乐/pad/choir Em 长音恢复(vel 34/28/32,承接 S6 余烬),
    bass 根音轻留(28,vel 50);小节 2(S1 rel0 复刻):bass 8 分脉冲
    (28,28,40,28,28,40,28,35,vel 82-96)+ kick 每拍 70 + snare 2/4 58 + hat 8 分 48
    + crash 轻 70 + 弦乐长音 40 + pad/choir 30/36 + piano 锚 40/52 + vln1 回声。"""
    for r in ('bass_electric', 'drums', 'celli', 'vla', 'vln2', 'vln1',
              'synth_pad', 'choir', 'piano_bang'):
        assert r in ch, f'loop_return: 通道映射缺少角色 {r}'
    t0 = (bar0 - 1) * 4
    # ---- 小节 1:静息延续(Em 长音恢复,CC11 回升 78-80)----
    for r in ('bass_electric', 'celli', 'vla', 'vln2', 'vln1',
              'synth_pad', 'choir', 'piano_bang', 'drums'):
        s.cc(r, 11, 78, t0)
    s.note('celli', 40, 34, t0, 3.9)
    s.note('vla', 64, 34, t0, 3.9)
    s.note('vln2', 64, 34, t0, 3.9)
    s.note('vln1', 71, 34, t0, 3.9)
    s.chord('synth_pad', (52, 55, 64), 28, t0, 3.9)
    s.chord('choir', (52, 55, 64), 32, t0, 3.9)
    s.note('bass_electric', 28, 50, t0, 2.0)     # 根音轻留(心跳隐现)
    # ---- 小节 2:S1 rel0 逐字复刻(与 sections/s1_scavenge.py 首小节一致)----
    t1 = t0 + 4
    for r in ('bass_electric', 'celli', 'vla', 'vln2', 'vln1',
              'synth_pad', 'choir', 'piano_bang', 'drums'):
        s.cc(r, 11, 80, t1)
    for b in (0.0, 1.0, 2.0, 3.0):
        s.note('drums', 36, 70, t1 + b, 0.2)     # kick 每拍
    for b in (1.0, 3.0):
        s.note('drums', 38, 58, t1 + b, 0.2)     # snare 2/4
    for j in range(8):
        s.note('drums', 42, 48, t1 + j * 0.5, 0.15)   # hat 8 分
    s.note('drums', 49, 70, t1, 1.0)             # crash 轻(起点)
    for j, (p, v) in enumerate(zip((28, 28, 40, 28, 28, 40, 28, 35),
                                   (82, 82, 88, 82, 82, 88, 82, 96))):
        s.note('bass_electric', p, v, t1 + j * 0.5, 0.45)   # S1 bass 8 分脉冲
    s.note('celli', 40, 40, t1, 3.9)
    s.note('vla', 64, 40, t1, 3.9)
    s.note('vln2', 64, 40, t1, 3.9)
    s.note('vln1', 71, 40, t1, 3.9)
    s.chord('synth_pad', (52, 55, 64), 30, t1, 3.9)
    s.chord('choir', (52, 55, 64), 36, t1, 3.9)
    s.note('piano_bang', 40, 40, t1, 0.3)
    s.note('piano_bang', 52, 40, t1, 0.3)
    s.note('vln1', 64, 40, t1 + 3.5, 0.2)        # S1 vln1 回声(Em 对)
    s.note('vln1', 67, 40, t1 + 3.75, 0.2)
    return bar0 + 2


def step_up(s, bar0, ch, **kw):
    """1 小节:S1→S2 轻升档桥(素材 = S1 本体 + snare 增强,2026-08-05 设计)。
    不用通用音效:S1 的 8 分 bass 脉冲原样延续,仅 snare 从 58 提到 62、
    hat 48→50——'步态'开始警觉,听感 = S1 的第 17 小节,而非插入式转场。"""
    for r in ('bass_electric', 'drums', 'celli', 'vla', 'vln2', 'vln1',
              'synth_pad', 'choir'):
        assert r in ch, f'step_up: 通道映射缺少角色 {r}'
    t0 = (bar0 - 1) * 4
    for r in ('bass_electric', 'celli', 'vla', 'vln2', 'vln1',
              'synth_pad', 'choir', 'drums'):
        s.cc(r, 11, 78, t0)
        s.cc(r, 11, 80, t0 + 2.0)
    for b in (0.0, 1.0, 2.0, 3.0):
        s.note('drums', 36, 70, t0 + b, 0.2)           # kick 每拍(S1 原位)
    for b in (1.0, 3.0):
        s.note('drums', 38, 62, t0 + b, 0.2)           # snare 58→62(巡逻感)
    for j in range(8):
        s.note('drums', 42, 50, t0 + j * 0.5, 0.15)    # hat 8 分 48→50
    for j, (p, v) in enumerate(zip((28, 28, 40, 28, 28, 40, 28, 35),
                                   (84, 84, 90, 84, 84, 90, 84, 96))):
        s.note('bass_electric', p, v, t0 + j * 0.5, 0.45)   # S1 bass 原位
    for name, p in (('celli', 40), ('vla', 64), ('vln2', 64), ('vln1', 71)):
        s.note(name, p, 40, t0, 3.9)                   # 弦乐长音接续
    s.chord('synth_pad', (52, 55, 64), 30, t0, 3.9)
    s.chord('choir', (52, 55, 64), 36, t0, 3.9)
    return bar0 + 1


def engine_start(s, bar0, ch, **kw):
    """2 小节:S2→母节 引擎启动桥(2026-08-05 设计)。
    不用 riser 音阶:节奏密度渐变——小节 1 怠速(bass 8 分步态 + kick 3+3+2 轻入
    + hat 16 分预演),小节 2 全速(bass 母节 BASS_P1 16 分原位 + kick 3+3+2 满 +
    hat 16 分 + snare 84)。听感 = 引擎从怠速到全速,母节是'长出来的'。"""
    for r in ('bass_electric', 'drums', 'celli', 'vla', 'vln2', 'vln1',
              'synth_pad', 'choir'):
        assert r in ch, f'engine_start: 通道映射缺少角色 {r}'
    t0 = (bar0 - 1) * 4
    # ---- 小节 1:怠速 ----
    for r in ('bass_electric', 'drums', 'celli', 'vla', 'vln2', 'vln1',
              'synth_pad', 'choir'):
        s.cc(r, 11, 78, t0)
    for b in (0.0, 1.0, 2.0):
        s.note('drums', 36, 70, t0 + b, 0.2)          # kick 每拍(3.0 由 3+3+2 承担)
    for b in (1.0, 3.0):
        s.note('drums', 38, 62, t0 + b, 0.2)
    for j in range(8):
        s.note('drums', 42, 44, t0 + j * 0.5, 0.15)
    s.note('drums', 36, 66, t0 + 1.5, 0.2)             # kick 3+3+2 轻入
    s.note('drums', 36, 72, t0 + 3.0, 0.2)
    for j, (p, v) in enumerate(zip((28, 28, 40, 28, 28, 40, 28, 35),
                                   (80, 80, 86, 80, 80, 86, 80, 92))):
        s.note('bass_electric', p, v, t0 + j * 0.5, 0.4)
    for name, p in (('celli', 40), ('vla', 64), ('vln2', 64), ('vln1', 71)):
        s.note(name, p, 44, t0, 3.9)
    s.chord('synth_pad', (52, 55, 64), 34, t0, 3.9)
    s.chord('choir', (52, 55, 64), 40, t0, 3.9)
    # ---- 小节 2:全速(母节轮 1 引擎)----
    for r in ('bass_electric', 'drums', 'celli', 'vla', 'vln2', 'vln1',
              'synth_pad', 'choir'):
        s.cc(r, 11, 82, t0 + 4)
    for b, v in ((4.0, 88), (5.5, 82), (7.0, 90)):
        s.note('drums', 36, v, t0 + b, 0.2)          # kick 3+3+2 满(母节档)
    s.note('drums', 38, 84, t0 + 5.0, 0.2)
    s.note('drums', 38, 84, t0 + 7.0, 0.2)
    for j in range(16):
        s.note('drums', 42, 52, t0 + 4.0 + j * 0.25, 0.12)   # hat 16 分(母节档)
    for k, p in enumerate((28, 40, 43, 47, 40, 43, 47, 40,
                           43, 47, 43, 40, 47, 43, 40, 28)):
        s.note('bass_electric', p, 92, t0 + 4.0 + k * 0.25, 0.22)   # BASS_P1['Em'] 原位
    for name, p in (('celli', 40), ('vla', 64), ('vln2', 64), ('vln1', 71)):
        s.note(name, p, 50, t0 + 4.0, 3.9)
    s.chord('synth_pad', (52, 55, 64), 38, t0 + 4.0, 3.9)
    s.chord('choir', (52, 55, 64), 44, t0 + 4.0, 3.9)
    return bar0 + 2


def morph_crisis(s, bar0, ch, **kw):
    """1 小节:母节→S4 塌缩变形桥(2026-08-05 设计)。
    不用转场音效:满配战斗层(hook/brass/fx/timpani)在 1 小节内撤空,
    kick 3+3+2 直接变形为心率双发(84/64)、bass 16 分简化为 8 分(母节素材原位)、
    hat 16 分降 8 分——听感 = 战斗'塌缩'成绝境心跳,S4 是母节变出来的。"""
    for r in ('bass_electric', 'drums', 'celli', 'vla', 'vln2', 'vln1',
              'synth_pad', 'choir'):
        assert r in ch, f'morph_crisis: 通道映射缺少角色 {r}'
    t0 = (bar0 - 1) * 4
    for r in ('bass_electric', 'drums', 'celli', 'vla', 'vln2', 'vln1',
              'synth_pad', 'choir'):
        s.cc(r, 11, 82, t0)
        s.cc(r, 11, 80, t0 + 2.0)
    for j in range(8):                                 # 心率双发(84/64 每拍重-轻)
        s.note('drums', 36, 84 if j % 2 == 0 else 64, t0 + j * 0.5, 0.18)
    for b in (1.0, 3.0):
        s.note('drums', 38, 60, t0 + b, 0.2)           # snare 轻
    for j in range(8):
        s.note('drums', 42, 40, t0 + j * 0.5, 0.12)    # hat 8 分(16 分撤)
    for j, (p, v) in enumerate(zip((28, 28, 40, 28, 28, 40, 28, 35),
                                   (88, 88, 92, 88, 88, 92, 88, 96))):
        s.note('bass_electric', p, v, t0 + j * 0.5, 0.42)   # 8 分简化(母节素材)
    for name, p in (('celli', 40), ('vla', 64), ('vln2', 64), ('vln1', 71)):
        s.note(name, p, 60, t0, 3.9)                   # 弦乐保持(压迫垫)
    s.chord('synth_pad', (52, 55, 64), 44, t0, 3.9)
    s.chord('choir', (52, 55, 64), 50, t0, 3.9)
    return bar0 + 1


def accel_roll(s, bar0, ch, **kw):
    """1 小节:S4→S5 加速滚奏桥(2026-08-05 设计,roll32 的动机化增强)。
    snare 32 分滚奏渐强(40→88)保留为'速度感'动机,叠加 hat 32 分渐入
    (40→54,预演 S5 的 32 分 hat)+ bass 根音 8 分脉冲轻入(预演 S5 bass 原位),
    小节末 kick 重击——176 进入时 hat 已就位,加速是'长出来的'。"""
    for r in ('drums', 'bass_electric'):
        assert r in ch, f'accel_roll: 通道映射缺少角色 {r}'
    t0 = (bar0 - 1) * 4
    s.cc('drums', 11, 80, t0)
    s.cc('drums', 11, 84, t0 + 2.0)
    s.cc('bass_electric', 11, 80, t0)
    for i in range(16):                                # snare 32 分滚奏(0.0-1.875)
        v = 40 + round(48 * i / 15)
        s.note('drums', 38, v, t0 + i * 0.125, 0.09)
    for i in range(24):                                # hat 32 分渐入(1.0-3.875)
        v = 40 + round(14 * i / 23)
        s.note('drums', 42, v, t0 + 1.0 + i * 0.125, 0.07)
    for b in (0.0, 1.0, 2.0, 3.0):
        s.note('bass_electric', 28, 70, t0 + b, 0.3)   # 根音脉冲(轻,S5 bass 原位)
    s.note('drums', 36, 92, t0 + 3.75, 0.2)            # 末拍重击,滚入 176
    return bar0 + 1




# ---------------------------------------------------------------------------
# 衔接矩阵:(from, to) → (元素名, 说明);节点 'S1'..'S6'(S3 = 母节)
# ---------------------------------------------------------------------------
# 合法衔接 8 条(游戏流程内):6 条正向 + 3 条反向(规格拍板)
_LEGAL = {
    ('S1', 'S2'): ('step_up', '轻升档桥:步态渐变(素材=S1 本体+snare 增强,非通用 riser)'),
    ('S2', 'S3'): ('engine_start', '引擎启动桥:2 小节怠速→全速(母节 kick 3+3+2 + bass 16 分预演)'),
    ('S3', 'S4'): ('morph_crisis', '塌缩变形桥:满配→心率压迫(1 小节,S4 v2 无移调)'),
    ('S4', 'S3'): ('down_fx', '降档回原位调'),
    ('S3', 'S5'): ('roll32', '冲刺,BPM 168→176 由 S5 build 内部处理(简单场景备用)'),
    ('S4', 'S5'): ('accel_roll', '加速滚奏桥:32 分 hat 渐入 + snare 滚奏,176 由 S5 build 处理'),
    ('S5', 'S6'): ('crash_stop', '急停,BPM 176→168 由 crash_stop 的 tempo 参数写回'),
    ('S2', 'S1'): ('down_fx', '反向合法:降档回搜刮'),
    ('S3', 'S2'): ('down_fx', '反向合法:降档回探索'),
    ('S3', 'S1'): ('down_fx', '反向合法:降档回搜刮'),
    ('S3', 'S-BT'): ('time_fold', '交火→时停:高频抽离+折叠淡出,1 小节(玩家主动,≤1 小节边界)'),
    ('S-BT', 'S3'): ('time_unfold', '时停→交火:32 分滚奏渐强(2 拍)+ 密度骤回'),
    ('S6', 'S1'): ('loop_return', '循环预伏:无缝回环(大循环成品专用)'),
    ('S5', 'S1'): ('loop_return', '循环预伏备用:冲刺直回搜刮(无 S6 的快循环)'),
}
_NODES = ('S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S-BT')
TRANSITIONS = {
    (a, b): _LEGAL.get((a, b), ('not_recommended', '游戏流程外'))
    for a in _NODES for b in _NODES
}


if __name__ == '__main__':
    # ---- 冒烟测试:4 小节 S1 风格骨架 + 连续插入全部 5 个过渡元素 ----
    import contextlib, io
    CH = {'piano_bang': 0, 'synth_pad': 1, 'vln1': 2, 'vln2': 3, 'vla': 4,
          'celli': 5, 'bass_electric': 6, 'fx': 7, 'drums': 9, 'hook': 10,
          'timpani': 11, 'brass_stab': 12, 'keys': 13, 'choir': 14, 'synth_rhythm': 15}
    s = Score(humanize=True, seed=42)
    for role, chn in CH.items():
        bank, prog, (lo, hi), pan, rev = PROGS['synth_lead' if role == 'hook' else role]
        s.add_instr(role, chn, bank, prog, lo, hi, pan, rev)
        s.cc(role, 7, 100, 0.0)
    s.tempo(168, 0.0)

    # 骨架:4 小节轻铺(Em C G D,S1 风格:长音 + 根音脉冲 + kick)
    SKEL = {'Em': (40, 64), 'C': (36, 64), 'G': (43, 62), 'D': (38, 62)}
    for i, prog in enumerate(('Em', 'C', 'G', 'D')):
        t0 = i * 4
        r0, c3 = SKEL[prog]
        s.note('celli', r0, 50, t0, 3.9)
        s.note('vln2', c3, 50, t0, 3.9)
        s.chord('synth_pad', (c3, c3 + 7), 40, t0, 3.9)
        s.note('bass_electric', ROOT_LOW[prog], 60, t0, 0.9)
        s.note('drums', 36, 70, t0, 0.2)
        for r in ('celli', 'vln2', 'synth_pad', 'bass_electric', 'drums'):
            s.cc(r, 11, 80, t0)

    # 连续插入全部过渡元素(骨架 4 小节 + 元素,覆盖全部和弦表)
    b = riser(s, 5, CH, chord='Em')            # m5-6
    b = down_fx(s, b, CH, chord='C')           # m7
    b = roll32(s, b, CH)                       # m8
    b = crash_stop(s, b, CH, tempo=168, chord='G')   # m9
    b = harmony_prehang(s, b, CH, chord='D')   # m10
    b = time_fold(s, b, CH, chord='Em')        # m11
    b = time_unfold(s, b, CH)                  # m12
    b = loop_return(s, b, CH)                  # m13-14
    b = step_up(s, b, CH)                      # m15
    b = engine_start(s, b, CH)                 # m16-17
    b = morph_crisis(s, b, CH)                 # m18
    b = accel_roll(s, b, CH)                   # m19

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        s.flush('/tmp/smk_trans.mid', verbose=False)
        issues = s.report('/tmp/smk_trans.mid')   # flush 不返回自检数,须显式 report
    out = buf.getvalue()
    bad = out.count('[音区告警]') + out.count('[冲突]')
    ok_bar = (b == 20)                          # 骨架 4 + riser 2 + 其余 1×9 + loop_return 2 = 19 小节,游标 20
    print(out)
    print(f'smoke transitions: {"PASS" if (bad == 0 and issues == 0 and ok_bar) else "FAIL"}'
          f' (告警+冲突={bad}, 自检冲突={issues}, 游标 b={b}, 期望 13)')
    sys.exit(0 if (bad == 0 and issues == 0 and ok_bar) else 1)
