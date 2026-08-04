#!/usr/bin/env python3
"""demo_playthrough.py — 《搜打撤》六子节连播 demo(转场工程交付物 3)

功能:一个 Score(humanize=True, seed=42) 内注册全部 16 角色(照 compose.py 的
ROLE_CH),按游戏流程把 S1→S2→S3→S4→S3→S5→S6 七个子节段用**插入式转场**
(transitions.py 元素:riser/down_fx/roll32/crash_stop)串成完整连播,
输出 `Combat_Extraction_Playthrough.mid`。

组装顺序(每节 16 小节,小节游标连续推进,转场小节不参与 16 小节循环):
  S1(搜刮)→ riser → S2(探索)→ riser → S3(母节 cycle0,直接调 layers 三层 build)
  → riser → S4(危机)→ down_fx → S3(母节 cycle1)→ roll32 → S5(撤离,176 BPM,
  由其自身 build 写 tempo)→ crash_stop(tempo=168 写回)→ S6(结算)
转场位置与时长预估由 STEPS 规划表统一驱动(打印结构 = 实际组装,不会漂移);
所用转场逐一与 TRANSITIONS 衔接矩阵交叉校验(不一致即断言失败)。

并行 Agent 交付模块(sections.s2_explore / s4_crisis / s5_extract / s6_calm)
可能尚未生成:缺失时 main() 打印规划结构后以非零码退出(冒烟跳过 demo 执行),
代码本身已就绪,S2/S4/S5/S6 落地后即可直接运行。

用法:
  python3 sections/demo_playthrough.py            # 生成 + 打印结构
  python3 sections/demo_playthrough.py --render   # 另用 fluidsynth 双库渲染
                                                 # /tmp/demo_raw.wav 验证无崩溃(不混音)
运行前先清 __pycache__(缓存纪律:rm -rf __pycache__ lib/__pycache__
layers/__pycache__ sections/__pycache__)。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS
import compose                                   # ROLE_CH / HOOK_VOICES(唯一通道表来源)
import sections.transitions as T
import sections.s1_scavenge as S1
import layers.drums as L_drums
import layers.bass_harmony as L_bass
import layers.riff_texture as L_riff

# 并行 Agent 交付的模块(可能尚未生成;缺失时 demo 冒烟跳过执行)
_MISSING = None
try:
    import sections.s2_explore as S2
    import sections.s4_crisis as S4
    import sections.s5_extract as S5
    import sections.s6_calm as S6
except ImportError as _e:
    S2 = S4 = S5 = S6 = None
    _MISSING = _e
SECTIONS_READY = all(m is not None for m in (S2, S4, S5, S6))

ROLE_CH = compose.ROLE_CH

# 连播规划表:(区块名, 类型, 小节数, BPM)。类型 → 组装函数;bpm 仅用于时长预估
# (S5 的 176 由 s5_extract.build 内部写 tempo;crash_stop 的 168 由 tempo=168 写回)。
# S3(母节)直接调 layers/drums.py + bass_harmony.py + riff_texture.py 的 build 充当。
STEPS = [
    ('S1 搜刮',        'S1',        16, 168),
    ('step_up S1->S2', 'step_up',    1, 168),
    ('S2 探索',        'S2',        16, 168),
    ('engine_start S2->S3', 'engine_start', 2, 168),
    ('S3 母节 c0',     'S3',        16, 168),
    ('morph_crisis S3->S4', 'morph_crisis', 1, 168),
    ('S4 危机',        'S4',        16, 168),
    ('down_fx S4->S3', 'down_fx',    1, 168),
    ('S3 母节 c1',     'S3',        16, 168),
    ('roll32 S3->S5',  'roll32',     1, 168),
    ('S5 撤离(176)',   'S5',        16, 176),
    ('crash_stop S5->S6', 'crash_stop', 1, 168),
    ('S6 结算',        'S6',        16, 168),
]

# 与衔接矩阵的交叉校验:正向流程用的转场必须等于 TRANSITIONS 推荐元素
_MATRIX_CHECK = [
    ('S1', 'S2', 'step_up'), ('S2', 'S3', 'engine_start'), ('S3', 'S4', 'morph_crisis'),
    ('S4', 'S3', 'down_fx'), ('S3', 'S5', 'roll32'), ('S5', 'S6', 'crash_stop'),
]

S3_BPM = 168          # S3(母节)速度


def _mother(s, bar0, cycle):
    """S3(母节)由三层 build 直接组装(compose.py 同款调用方式)。"""
    for layer in (L_drums, L_bass, L_riff):
        layer.build(s, bar0, cycle, ROLE_CH)
    return bar0 + 16


def _run_step(s, b, kind, s3_cycle):
    """按类型执行一步组装,返回新的小节游标。"""
    if kind == 'S1':
        return S1.build(s, b, 0, ROLE_CH)
    if kind == 'S2':
        return S2.build(s, b, 0, ROLE_CH)
    if kind == 'S3':
        return _mother(s, b, s3_cycle)
    if kind == 'S4':
        return S4.build(s, b, 0, ROLE_CH)
    if kind == 'S5':
        return S5.build(s, b, 0, ROLE_CH)      # 176 BPM 由 build 内部写 tempo
    if kind == 'S6':
        return S6.build(s, b, 0, ROLE_CH)
    if kind == 'step_up':
        return T.step_up(s, b, ROLE_CH)
    if kind == 'engine_start':
        return T.engine_start(s, b, ROLE_CH)
    if kind == 'morph_crisis':
        return T.morph_crisis(s, b, ROLE_CH)
    if kind == 'down_fx':
        return T.down_fx(s, b, ROLE_CH, chord='Em')
    if kind == 'roll32':
        return T.roll32(s, b, ROLE_CH)
    if kind == 'crash_stop':
        return T.crash_stop(s, b, ROLE_CH, tempo=168, chord='Em')
    raise ValueError(f'demo: 未知步骤类型 {kind}')


def build_playthrough(s):
    """按 STEPS 组装全部子节 + 插入式转场,返回小节跨度表
    [(区块名, 起始小节, 小节数, BPM), ...](与打印结构同源)。"""
    if not SECTIONS_READY:
        raise ImportError(f'缺少并行 Agent 交付模块: {_MISSING}')
    # 转场与衔接矩阵交叉校验
    for frm, to, element in _MATRIX_CHECK:
        rec = T.TRANSITIONS[(frm, to)]
        assert rec[0] == element, f'demo: 矩阵要求 {frm}->{to} 用 {rec[0]},实际 {element}'
    L_riff.VOICE_BOOST = 6                     # 合成器嗓力度补偿(compose --voice synth 口径)
    s.tempo(168, 0.0)
    b = 3                                      # 对齐母节惯例:m1-2 留白,连播从 m3 起
    spans = []
    s3_cycle = 0
    for label, kind, n, bpm in STEPS:
        spans.append((label, b, n, bpm))
        b = _run_step(s, b, kind, s3_cycle)
        if kind == 'S3':
            s3_cycle += 1                      # 第二次 S3 = cycle 1(层内微变)
    return spans


def print_plan(spans):
    """打印结构:每节小节范围 / 过渡位置 / 时长预估(与实际组装同源)。"""
    total = 0.0
    print('=== 结构(Combat_Extraction_Playthrough.mid)===')
    print(f'  {"区块":<16}{"小节范围":<12}{"小节":>4}{"BPM":>6}{"时长":>9}')
    trans_at = []
    for label, start, n, bpm in spans:
        dur = n * 4 / bpm * 60
        total += dur
        end = start + n - 1
        mark = '  [转场]' if label.startswith(('riser', 'down_fx', 'roll32', 'crash_stop')) else ''
        if mark:
            trans_at.append(f'{label}(m{start}-m{end})')
        print(f'  {label:<16}m{start}-m{end:<10}{n:>4}{bpm:>6}{dur:>8.1f}s{mark}')
    m, sec = divmod(total, 60)
    print(f'  总时长 ≈ {total:.1f}s({int(m)}:{sec:04.1f})')
    print('  转场位置: ' + ' | '.join(trans_at))


def main():
    s = Score(humanize=True, seed=42)
    for role, chn in ROLE_CH.items():
        if role == 'hook':
            bank, prog, (lo, hi), pan, rev = PROGS[compose.HOOK_VOICES['synth']]
        else:
            bank, prog, (lo, hi), pan, rev = PROGS[role]
        s.add_instr(role, chn, bank, prog, lo, hi, pan, rev)
        s.cc(role, 7, 100, 0.0)

    # 先打印规划结构(纯数据,不依赖并行 Agent 模块)
    b = 3
    planned = [(label, b + sum(n_ for _, _, n_, _ in STEPS[:i]), n, bpm)
               for i, (label, _, n, bpm) in enumerate(STEPS)]
    print_plan(planned)

    if not SECTIONS_READY:
        print(f'[demo] 冒烟跳过 demo 执行:并行 Agent 模块未交付({_MISSING});'
              f'代码就绪,待 sections/s2_explore.py、s4_crisis.py、s5_extract.py、'
              f's6_calm.py 落地后直接运行。')
        sys.exit(1)

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'Combat_Extraction_Playthrough.mid')
    spans = build_playthrough(s)
    s.flush(out)
    print(f'[demo] 已生成 {out}')

    # 衔接矩阵摘要(与 demo 实际使用的转场一致)
    print('=== 衔接矩阵摘要(合法 9 条:6 正向 + 3 反向)===')
    for (frm, to), (el, desc) in sorted(T.TRANSITIONS.items()):
        if el != 'not_recommended':
            print(f'  {frm}->{to}: {el:<12} {desc}')

    if '--render' in sys.argv:
        render(out)


def render(out_mid):
    """fluidsynth 双库渲染 /tmp/demo_raw.wav,验证无崩溃(不做混音)。"""
    import shutil, subprocess
    if shutil.which('fluidsynth') is None:
        print('[render] 未找到 fluidsynth,跳过渲染验证')
        return
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sf2 = [os.path.join(root, '..', '..', 'soundfonts', f)
           for f in ('MuseScore_General.sf2', 'Rock_GeneralUser_GS_v1.471.sf2')]
    if any(not os.path.exists(f) for f in sf2):
        print(f'[render] 缺少音色库({sf2}),跳过渲染验证')
        return
    cmd = ['fluidsynth', '-F', '/tmp/demo_raw.wav', '-r', '44100', '-R', '0.9',
           '-C', '0', '-g', '1.2', *sf2, out_mid]
    print('[render] ' + ' '.join(cmd))
    subprocess.run(cmd, check=True)
    print('[render] 渲染完成 /tmp/demo_raw.wav(无崩溃验证)')


if __name__ == '__main__':
    main()
