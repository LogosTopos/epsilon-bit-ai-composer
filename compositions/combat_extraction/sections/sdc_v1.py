#!/usr/bin/env python3
"""sdc_v1.py — 《搜打撤》搜-打-撤 完整版 v1

用户决策(2026-08):S1(搜刮)→ 母节(战斗)→ S6(结算)已构成"搜-打-撤"循环,
此版本 = 三段的完整成品:无 m1-2 留白、无 intro/outro,两个插入式转场连接。
(子 Agent 的 S2/S4/S5 因 stab 滥用/难听未入选本版——见 STATUS 决策史)

结构(168 BPM,无留白,直接从 m1 开始):
  S1 搜刮(m1-16,22.9s)→ riser 升档(m17-18)→ 母节战斗 ×2 圈(m19-50,45.7s)
  → crash_stop 急停(m51)→ S6 结算(m52-67,22.9s)  总 ≈ 67 小节 95.7s

转场依据衔接矩阵:S1→S3 = riser(升档,进入方和弦 Em);S3→S6 = crash_stop
(急停,进入方和弦 Em——战斗骤止,尘埃落定)。transitions.py 元素,CC11 ≥70 纪律。

用法:
  python3 sections/sdc_v1.py            # 生成 Combat_Extraction_SDC_v1.mid
  python3 sections/sdc_v1.py --render   # 另用 fluidsynth 双库渲染 /tmp/sdc_raw.wav
运行前清缓存:rm -rf __pycache__ lib/__pycache__ layers/__pycache__ sections/__pycache__
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.orch import Score
from lib.progs import PROGS
import compose                                   # ROLE_CH(唯一通道表来源)
import sections.transitions as T
import sections.s1_scavenge as S1
import sections.s6_calm as S6
import layers.drums as L_drums
import layers.bass_harmony as L_bass
import layers.riff_texture as L_riff

ROLE_CH = compose.ROLE_CH


def build(s):
    """组装搜-打-撤完整版(无留白,从 m1 起),返回结束小节游标。"""
    L_riff.VOICE_BOOST = 6                       # 合成器嗓力度补偿(主成品口径)
    s.tempo(168, 0.0)
    b = 1
    b = S1.build(s, b, 0, ROLE_CH)               # S1 搜刮 m1-16
    b = T.riser(s, b, ROLE_CH, chord='Em')       # 升档 m17-18(进入方 = 母节首和弦 Em)
    for cycle in (0, 1):                         # 母节战斗 ×2 圈 m19-50(轮次微变防机械)
        for layer in (L_drums, L_bass, L_riff):
            layer.build(s, b, cycle, ROLE_CH)
        b += 16
    b = T.crash_stop(s, b, ROLE_CH, chord='Em', tempo=168)   # 急停 m51(进入方 = S6 首和弦 Em)
    b = S6.build(s, b, 0, ROLE_CH)               # S6 结算 m52-67(Em 长音淡出收束)
    return b


def render(out_mid):
    """fluidsynth 双库渲染 /tmp/sdc_raw.wav,验证无崩溃(不做混音)。"""
    import shutil, subprocess
    if shutil.which('fluidsynth') is None:
        print('[render] 未找到 fluidsynth,跳过')
        return
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sf2 = [os.path.join(root, '..', '..', 'soundfonts', f)
           for f in ('MuseScore_General.sf2', 'Rock_GeneralUser_GS_v1.471.sf2')]
    cmd = ['fluidsynth', '-F', '/tmp/sdc_raw.wav', '-r', '44100', '-R', '0.9',
           '-C', '0', '-g', '1.2', *sf2, out_mid]
    subprocess.run(cmd, check=True)
    print('[render] 渲染完成 /tmp/sdc_raw.wav(无崩溃验证)')


def main():
    s = Score(humanize=True, seed=42)
    for role, chn in ROLE_CH.items():
        if role == 'hook':
            bank, prog, (lo, hi), pan, rev = PROGS[compose.HOOK_VOICES['synth']]
        else:
            bank, prog, (lo, hi), pan, rev = PROGS[role]
        s.add_instr(role, chn, bank, prog, lo, hi, pan, rev)
        s.cc(role, 7, 100, 0.0)
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'Combat_Extraction_SDC_v1.mid')
    b = build(s)
    s.flush(out)
    nbars = b - 1
    dur = nbars * 4 / 168 * 60
    print(f'[sdc_v1] 已生成 {out}({nbars} 小节,≈{dur:.1f}s)')
    print('  结构:S1 搜刮 m1-16 → riser m17-18 → 母节战斗 m19-50(×2 圈)'
          ' → crash_stop m51 → S6 结算 m52-67')
    if '--render' in sys.argv:
        render(out)


if __name__ == '__main__':
    main()
