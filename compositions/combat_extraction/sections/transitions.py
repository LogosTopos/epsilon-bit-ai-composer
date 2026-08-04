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

衔接矩阵 TRANSITIONS:节点 'S1'..'S6'(S3 = 母节),键 (from, to) → (元素名, 说明)。
合法衔接(游戏流程内)8 条;其余组合一律 ('not_recommended', '游戏流程外')。
demo 连播(六子节)依据本矩阵插转场,见 sections/demo_playthrough.py。

冒烟测试:python3 sections/transitions.py → /tmp/smk_trans.mid
(4 小节 S1 风格骨架 + 连续插入 riser/down_fx/roll32/crash_stop/harmony_prehang,
断言 0 音区告警 / 0 冲突 / 小节数正确)。运行前先清 __pycache__(缓存纪律)。
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


# ---------------------------------------------------------------------------
# 衔接矩阵:(from, to) → (元素名, 说明);节点 'S1'..'S6'(S3 = 母节)
# ---------------------------------------------------------------------------
# 合法衔接 8 条(游戏流程内):6 条正向 + 3 条反向(规格拍板)
_LEGAL = {
    ('S1', 'S2'): ('riser', '低→中升档'),
    ('S2', 'S3'): ('riser', '升档'),
    ('S3', 'S4'): ('riser', '升档,S4 旋律层 +1 半音,riser 掩盖调性跳变'),
    ('S4', 'S3'): ('down_fx', '降档回原位调'),
    ('S3', 'S5'): ('roll32', '冲刺,BPM 168→176 由 S5 build 内部处理'),
    ('S5', 'S6'): ('crash_stop', '急停,BPM 176→168 由 crash_stop 的 tempo 参数写回'),
    ('S2', 'S1'): ('down_fx', '反向合法:降档回搜刮'),
    ('S3', 'S2'): ('down_fx', '反向合法:降档回探索'),
    ('S3', 'S1'): ('down_fx', '反向合法:降档回搜刮'),
}
_NODES = ('S1', 'S2', 'S3', 'S4', 'S5', 'S6')
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

    # 连续插入 5 个元素(各用不同和弦,覆盖全部和弦表)
    b = riser(s, 5, CH, chord='Em')            # m5-6
    b = down_fx(s, b, CH, chord='C')           # m7
    b = roll32(s, b, CH)                       # m8
    b = crash_stop(s, b, CH, tempo=168, chord='G')   # m9
    b = harmony_prehang(s, b, CH, chord='D')   # m10

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        s.flush('/tmp/smk_trans.mid', verbose=False)
        issues = s.report('/tmp/smk_trans.mid')   # flush 不返回自检数,须显式 report
    out = buf.getvalue()
    bad = out.count('[音区告警]') + out.count('[冲突]')
    ok_bar = (b == 11)                          # 骨架 4 + riser 2 + 其余 1×4 = 10 小节,游标 11
    print(out)
    print(f'smoke transitions: {"PASS" if (bad == 0 and issues == 0 and ok_bar) else "FAIL"}'
          f' (告警+冲突={bad}, 自检冲突={issues}, 游标 b={b}, 期望 11)')
    sys.exit(0 if (bad == 0 and issues == 0 and ok_bar) else 1)
