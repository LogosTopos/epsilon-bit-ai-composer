#!/usr/bin/env python3
"""progs.py — 《搜打撤》战斗曲音色角色映射(Agent A 实测定稿)

实测方法:fluidsynth 2.5.7 渲染短测试 MIDI(vel≈100-118,60bpm 校准时间轴),
wave 分析 RMS/peak(口径 20*log10(rms/32768)),三库对比:
MuseScore_General.sf2(205MB,古典/通用) / Rock_GeneralUser_GS_v1.471.sf2(29.8MB) /
Rock_SGM-V2.01.sf2(236MB)。SGM 在全部角色对比中均败北(鼓组尤其弱),未采用。

== 渲染命令(必须双库,顺序不可反)==
fluidsynth -F out.wav -r 44100 -R 0.9 -C 0 -g 1.2 \
  soundfonts/MuseScore_General.sf2 soundfonts/Rock_GeneralUser_GS_v1.471.sf2 in.mid

实测:FluidSynth 对后加载库(GUGS)按 per-font fallback 优先,GUGS 对每个 GM program
均有 (bank=prog, prog=0) 布局的主音色兜底 → 双库渲染时:
* bass/guitar/drums 命中 GUGS 摇滚音色(实测全库最强:贝斯 E1 -16.6dB、失真吉他 -18.0dB、
  Power 套件 kick/snare/crash ≈ -22/-22/-24dB,M1 动机 pattern -19.1dB)
* 其余角色命中 GUGS 对应 GM 音色(弦乐 Strings Slow -24.9、合唱 Concert Choir -23.0、
  小号 Trumpet -22.0、钢琴 Stereo Grand -18.6、管风琴 Pipe Organ -21.2);
  频谱验证 timpani 低频占比 29%(打击感正常)、pad 为持续垫音
* 注意:GUGS 不响应 CC11(实测 0/60/110 三档响度相同);双库渲染下动态由力度承担
  (层代码 vel 分档 72-104 仍有效);若需 CC11 Expr 动态曲线,须改单库 MuseScore 渲染,
  本表在单库 MuseScore 下同样成立(各角色退回 MuseScore 音色)

== 鼓组结论 ==
标准套件(128/0)snare -38.5dB、crash -30.3dB 偏弱(印证 HANDOVER);
Power 套件(128/16)为 MuseScore 最强(kick -22.0/snare -28.1/crash -24.4);
GUGS Power(128/16)三库最强 → drums 用 128/16。
"""
PROGS = {
    'piano_bang': (0, 0, (36, 84), 64, 40),
    'synth_pad':  (0, 89, (48, 84), 64, 70),
    'vln1':       (21, 49, (55, 96), 30, 55),
    'vln2':       (26, 49, (55, 96), 45, 55),
    'vla':        (31, 49, (55, 88), 60, 55),
    'celli':      (41, 49, (36, 76), 80, 55),
    # GUGS Finger Bass:三库实测最响(E1 -16.6dB vs MuseScore 33 -24.3/SGM -26.8),
    # E1→E2 响度一致(-16.6/-17.8),riff 根音区 28-40 支撑最好
    'bass_electric': (0, 33, (28, 52), 64, 30),
    # GUGS Power Kit(128/16):kick -22.5/snare -22.3/crash -23.9 三库最强,
    # M1 动机 pattern -19.1dB;MuseScore Power 备选(-20.7dB)
    'drums':      (128, 16, (0, 127), 64, 20),
    # GUGS Distortion Guitar:实测 -18.0dB(peak -7.3)最响最冲;
    # MuseScore 0/30 -20.4 备选;31/27/28 均更弱(28 muted 近静音)
    'guitar_dist':   (0, 30, (40, 88), 40, 45),
    'timpani':    (0, 47, (26, 60), 64, 30),
    # MuseScore Expr Trumpet:CC11=110 时 -16.3dB,比 GM 0/56(-25.2)响 9dB;
    # 双库渲染下实际由 GUGS Trumpet 兜底(-22.0dB,GS 标尺内正常)
    'brass_stab': (17, 56, (55, 88), 60, 45),
    'choir':      (17, 52, (48, 84), 64, 70),
    'keys':       (0, 19, (48, 96), 64, 60),
}
