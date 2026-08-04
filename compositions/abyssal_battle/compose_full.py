#!/usr/bin/env python3
"""《Battle in the Abyss / 深渊之战》完整版(≈4 分钟)— 结构驱动的扩展编曲

相对 2:30 版的改进:
1. 结构完备:引子 → A1 → A2(和声变奏+属准备)→ B → 插部(减速对比,拨弦)
   → 高潮(铜管六度对位)→ 冲刺 → 重击 → 余韵(战斗后的寂静,闭环)
2. 和声复杂化:A2 引入 E7 属和弦(半音色彩 G#);B 段尾部 E7 属驻留;
   插部 i-iv-V7-i 卡农;高潮 F-G-Am 强力收束
3. 织体对比:插部改拨弦(Pizzicato)+ 无鼓留白;低音二分长音
4. 鼓:乐句级 fill(加花)、插部后轻鼓恢复、break(滚奏衔接)
5. 对位:高潮铜管与主旋律六度平行副旋律
6. 动机:引子预示碎片;余韵回声(钢琴动机返照,72 BPM)
"""
import argparse
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

parser = argparse.ArgumentParser(description='《深渊之战》完整版作曲生成器')
parser.add_argument('--speed', type=float, default=1.0, help='整体速度缩放(默认 1.0)')
parser.add_argument('--transpose', type=int, default=0, help='整体移调半音数(默认 0)')
parser.add_argument('--out', default='Battle_in_the_Abyss_Full.mid', help='输出 MIDI 路径')
parser.add_argument('--no-verify', action='store_true', help='跳过自检打印')
args = parser.parse_args()

TR = args.transpose
TPB = 480
BPB = 4

# Tempo map:引子96 → A1/A2 132 → B 144 → 插部120(减速对比)→ 高潮138 → 冲刺142-150 → 重击 → 余韵96→72(渐冷)
TEMPO = [(1, 96), (9, 132), (25, 132), (41, 144), (57, 120), (73, 138),
         (97, 142), (98, 144), (99, 146), (100, 148), (101, 150),
         (105, 150), (107, 96), (109, 72)]

PROGRAMS = {
    0: 0, 1: 47, 2: 48, 3: 61, 4: 52, 5: 49, 6: 33, 7: 30,
}
PIZZ = 45  # Pizzicato Strings(插部用)

mid = MidiFile(ticks_per_beat=TPB)
meta = MidiTrack()
mid.tracks.append(meta)
meta.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))

tracks = {}
for ch in range(10):
    t = MidiTrack()
    mid.tracks.append(t)
    tracks[ch] = t
    if ch in PROGRAMS:
        t.append(Message('program_change', channel=ch, program=PROGRAMS[ch], time=0))

pending = []

def ev(key, msg, beat):
    pending.append((key, beat, msg))

def note(ch, pitch, vel, sb, dur):
    p = pitch + TR
    ev(ch, Message('note_on', channel=ch, note=p, velocity=vel), sb)
    ev(ch, Message('note_off', channel=ch, note=p, velocity=0), sb + dur)

def multi(ch, notes, sb, dur):
    for p, v in notes:
        ev(ch, Message('note_on', channel=ch, note=p + TR, velocity=v), sb)
    for p, _ in notes:
        ev(ch, Message('note_off', channel=ch, note=p + TR, velocity=0), sb + dur)

def cc(ch, ctrl, val, beat):
    ev(ch, Message('control_change', channel=ch, control=ctrl, value=val), beat)

def prog(ch, p, beat):
    ev(ch, Message('program_change', channel=ch, program=p), beat)

def bar(n):
    return (n - 1) * BPB

def bar_of(beat):
    return int(beat // BPB) + 1

# ---------- 鼓 ----------
KICK, SNARE, HH, OH, CRASH, RIDE, TOM1, TOM2 = 36, 38, 42, 46, 49, 51, 45, 47
def drum(n, vel, beat, dur=0.1):
    ev(9, Message('note_on', channel=9, note=n, velocity=vel), beat)
    ev(9, Message('note_off', channel=9, note=n, velocity=0), beat + dur)

def pattern_a(sb, k=106, s=108, h=74):
    for i in range(8):
        drum(HH, h - 16 if i % 2 else h, sb + i * 0.5, 0.12)
    drum(KICK, k, sb); drum(KICK, k - 8, sb + 2.5); drum(KICK, k - 12, sb + 3.5)
    drum(SNARE, s, sb + 2); drum(SNARE, s, sb + 4)

def pattern_b(sb, k=108, s=110, h=80):
    for i in range(16):
        drum(HH, h - 18 if i % 2 else h, sb + i * 0.25, 0.08)
    for i in range(4):
        drum(KICK, k - i * 6, sb + i)
    drum(SNARE, s, sb + 2); drum(SNARE, s, sb + 4)
    drum(SNARE, s - 14, sb + 2.5); drum(SNARE, s - 14, sb + 3.5)

def pattern_c(sb, k=112, s=112, h=84):
    for i in range(16):
        drum(HH, h - 18 if i % 2 else h, sb + i * 0.25, 0.08)
    for i in range(8):
        drum(KICK, k - (0 if i % 2 else 10), sb + i * 0.5)
    drum(SNARE, s, sb + 2); drum(SNARE, s, sb + 4)
    drum(SNARE, s - 10, sb + 2.75); drum(SNARE, s - 10, sb + 3.75)

def pattern_light(sb, k=70, h=46):
    """插部后段:轻律动恢复"""
    for i in range(8):
        drum(HH, h - 8 if i % 2 else h, sb + i * 0.5, 0.12)
    drum(KICK, k, sb); drum(KICK, k - 8, sb + 3)

def pattern_a_nosnare(sb, k=100, h=70):
    """A 段渐进:无军鼓(进入时先给脉冲,backbeat 后置)"""
    for i in range(8):
        drum(HH, h - 16 if i % 2 else h, sb + i * 0.5, 0.12)
    drum(KICK, k, sb); drum(KICK, k - 8, sb + 2.5); drum(KICK, k - 12, sb + 3.5)

def pattern_b_light(sb, k=96, s=100, h=72):
    """B 段抽稀版:保留十六分脉冲,去掉切分 snare(转场前先降密度)"""
    for i in range(16):
        drum(HH, h - 18 if i % 2 else h, sb + i * 0.25, 0.08)
    drum(KICK, k, sb); drum(KICK, k - 10, sb + 3)
    drum(SNARE, s, sb + 2); drum(SNARE, s, sb + 4)

def pattern_strip(sb, h=58, k=86):
    """抽离版:只剩 HH 四分 + kick 拍 1(鼓点逐步停止的过程)"""
    for i in range(4):
        drum(HH, h - 8 if i % 2 else h, sb + i, 0.1)
    drum(KICK, k, sb)

def fill16(sb, v=100):
    """十六分填充:后半小节 HH 十六分滚入 + snare→tom 下滚(速度转场预热)"""
    for i in range(8):
        drum(HH, v - 20 if i % 2 else v - 8, sb + 2.0 + i * 0.25, 0.08)
    drum(SNARE, 104, sb + 3.0, 0.12)
    drum(TOM1, 96, sb + 3.5, 0.14)
    drum(TOM2, 88, sb + 3.75, 0.16)

def fill(sb, v=104):
    """小节末拍加花:snare 十六分 → tom"""
    drum(SNARE, v, sb + 3.0, 0.12)
    drum(SNARE, v - 6, sb + 3.25, 0.12)
    drum(TOM1, v - 10, sb + 3.5, 0.14)
    drum(TOM2, v - 16, sb + 3.75, 0.16)

def snare_roll(sb, beats, v0=36, v1=110):
    n = int(beats * 4)
    for i in range(n):
        v = int(v0 + (v1 - v0) * i / max(n - 1, 1))
        drum(SNARE, v, sb + i * 0.25, 0.12)

# ---------- 和声表 ----------
CHORDS = {}
for n in range(9, 33):
    CHORDS[n] = ['Am', 'F', 'C', 'G'][(n - 9) % 4]
for n in range(33, 37):
    CHORDS[n] = ['Am', 'F', 'C', 'E7'][n - 33]
for n in range(37, 41):
    CHORDS[n] = ['Am', 'Am', 'F', 'E7'][n - 37]
for n in range(41, 53):
    CHORDS[n] = ['Dm', 'Am', 'F', 'G'][(n - 41) % 4]
for n in range(53, 57):
    CHORDS[n] = 'E7'                                        # 属驻留
for n in range(57, 65):
    CHORDS[n] = ['Am', 'Dm', 'E7', 'Am'][(n - 57) % 4]      # 插部卡农
for n in range(65, 71):
    CHORDS[n] = ['F', 'F', 'G', 'G', 'E7', 'E7'][n - 65]
for n in range(71, 73):
    CHORDS[n] = 'Am'                                        # 留白
for n in range(73, 97):
    CHORDS[n] = ['F', 'G', 'Am'][(n - 73) % 3]              # 高潮
for n in range(97, 105):
    CHORDS[n] = 'Am'                                        # 冲刺
for n in range(105, 107):
    CHORDS[n] = 'Am'                                        # 重击
for n in range(107, 117):
    CHORDS[n] = 'Am'                                        # 余韵

BASS = {'Am': 45, 'F': 41, 'C': 48, 'G': 43, 'Dm': 50, 'E7': 40}
BASS_5 = {'Am': 52, 'F': 48, 'C': 55, 'G': 50, 'Dm': 57, 'E7': 47}
CHORD_TONES = {'Am': [57, 60, 64], 'F': [53, 57, 60], 'C': [60, 64, 67],
               'G': [55, 59, 62], 'Dm': [50, 53, 57], 'E7': [56, 59, 62]}
CHORD_TONES_LO = {'Am': [45, 52, 57], 'F': [41, 48, 53], 'C': [48, 55, 60],
                  'G': [43, 50, 55], 'Dm': [50, 57, 62], 'E7': [40, 47, 52]}
CHORD_PC = {'Am': {9, 0, 4}, 'F': {5, 9, 0}, 'C': {0, 4, 7}, 'G': {7, 11, 2},
            'Dm': {2, 5, 9}, 'E7': {4, 8, 11, 2}}   # 音级集合(A=9 C=0 E=4 …)

def counter_melody(p, chord):
    """铜管副旋律:下方六度;若与非和弦音冲突,就近归位到和弦音(±2 半音内)"""
    target = p - 9
    pc = target % 12
    if pc in CHORD_PC[chord]:
        return target
    for d in (1, 2):
        for cand in (target - d, target + d):
            if cand % 12 in CHORD_PC[chord]:
                return cand
    return target   # 找不到就保留原色彩音

def bass_riff(sb, ch, vel=96):
    r = BASS[ch]
    for i in range(8):
        p = BASS_5[ch] if i == 7 else r
        v = vel if i in (0, 4) else vel - 14
        note(6, p, v, sb + i * 0.5, 0.42)

def bass_whole(sb, ch, vel=55):
    note(6, BASS[ch], vel, sb, 4.0)

def strings_stab(sb, ch, vel=66, dur=0.4):
    for i in range(8):
        p = CHORD_TONES[ch]
        v = vel + 10 if i in (0, 4) else vel
        multi(2, [(x, v) for x in p], sb + i * 0.5, dur)

def pizz_stab(sb, ch, vel=58):
    """拨弦击奏(插部):四分音符,轻"""
    for i in range(4):
        multi(2, [(x, vel) for x in CHORD_TONES[ch]], sb + i, 0.6)

def guitar_power(sb, ch, vel=78, dur=0.3):
    for i in range(8):
        p = CHORD_TONES_LO[ch]
        v = vel if i in (0, 4) else vel - 12
        multi(7, [(x, v) for x in p], sb + i * 0.5, dur)

# ---------- 旋律 ----------
def ph1():
    return [(bar(9), 69, 1.5), (bar(9) + 1.5, 72, 0.5), (bar(9) + 2, 74, 1.0), (bar(9) + 3, 76, 1.0),
            (bar(10), 77, 0.5), (bar(10) + 0.5, 76, 0.5), (bar(10) + 1, 74, 0.5), (bar(10) + 1.5, 72, 0.5),
            (bar(10) + 2, 74, 1.0), (bar(10) + 3, 72, 0.5), (bar(10) + 3.5, 69, 0.5),
            (bar(11), 67, 1.0), (bar(11) + 1, 69, 1.0), (bar(11) + 2, 72, 1.0), (bar(11) + 3, 74, 1.0),
            (bar(12), 76, 2.0), (bar(12) + 2, 74, 1.0), (bar(12) + 3, 72, 1.0)]
def ph2():
    return [(bar(13), 72, 1.5), (bar(13) + 1.5, 76, 0.5), (bar(13) + 2, 77, 1.0), (bar(13) + 3, 79, 1.0),
            (bar(14), 81, 0.5), (bar(14) + 0.5, 79, 0.5), (bar(14) + 1, 77, 0.5), (bar(14) + 1.5, 76, 0.5),
            (bar(14) + 2, 77, 1.0), (bar(14) + 3, 76, 0.5), (bar(14) + 3.5, 72, 0.5),
            (bar(15), 67, 1.0), (bar(15) + 1, 69, 1.0), (bar(15) + 2, 72, 1.0), (bar(15) + 3, 76, 1.0),
            (bar(16), 77, 2.0), (bar(16) + 2, 76, 1.0), (bar(16) + 3, 74, 1.0)]
def ph3():
    return [(bar(17), 69, 1.5), (bar(17) + 1.5, 72, 0.5), (bar(17) + 2, 74, 1.0), (bar(17) + 3, 76, 1.0),
            (bar(18), 77, 0.5), (bar(18) + 0.5, 76, 0.5), (bar(18) + 1, 74, 0.5), (bar(18) + 1.5, 72, 0.5),
            (bar(18) + 2, 71, 1.0), (bar(18) + 3, 69, 1.0),
            (bar(19), 72, 1.0), (bar(19) + 1, 74, 1.0), (bar(19) + 2, 76, 1.0), (bar(19) + 3, 77, 1.0),
            (bar(20), 76, 1.0), (bar(20) + 1, 77, 0.5), (bar(20) + 1.5, 79, 0.5), (bar(20) + 2, 81, 2.0)]
def ph4():
    return [(bar(21), 81, 1.0), (bar(21) + 1, 79, 0.5), (bar(21) + 1.5, 77, 0.5), (bar(21) + 2, 76, 1.0), (bar(21) + 3, 74, 1.0),
            (bar(22), 76, 0.5), (bar(22) + 0.5, 77, 0.5), (bar(22) + 1, 79, 0.5), (bar(22) + 1.5, 81, 0.5),
            (bar(22) + 2, 79, 1.0), (bar(22) + 3, 76, 0.5), (bar(22) + 3.5, 72, 0.5),
            (bar(23), 74, 1.0), (bar(23) + 1, 76, 1.0), (bar(23) + 2, 77, 1.0), (bar(23) + 3, 79, 1.0),
            (bar(24), 81, 2.0), (bar(24) + 2, 76, 1.0), (bar(24) + 3, 72, 1.0)]
def ph5():
    return [(bar(25), 77, 0.25), (bar(25) + 0.25, 76, 0.25), (bar(25) + 0.5, 74, 0.25), (bar(25) + 0.75, 72, 0.25),
            (bar(25) + 1, 74, 1.0), (bar(25) + 2, 76, 1.0), (bar(25) + 3, 77, 1.0),
            (bar(26), 79, 0.5), (bar(26) + 0.5, 77, 0.5), (bar(26) + 1, 76, 0.5), (bar(26) + 1.5, 74, 0.5),
            (bar(26) + 2, 72, 1.0), (bar(26) + 3, 74, 1.0), (bar(26) + 3.5, 76, 0.5),
            (bar(27), 77, 1.0), (bar(27) + 1, 76, 1.0), (bar(27) + 2, 74, 1.0), (bar(27) + 3, 72, 1.0),
            (bar(28), 74, 2.0), (bar(28) + 2, 72, 1.0), (bar(28) + 3, 69, 1.0)]
def ph6():
    return [(bar(29), 72, 1.5), (bar(29) + 1.5, 74, 0.5), (bar(29) + 2, 76, 1.0), (bar(29) + 3, 77, 1.0),
            (bar(30), 79, 1.0), (bar(30) + 1, 81, 1.0), (bar(30) + 2, 79, 1.0), (bar(30) + 3, 77, 1.0),
            (bar(31), 76, 1.0), (bar(31) + 1, 77, 1.0), (bar(31) + 2, 79, 1.0), (bar(31) + 3, 81, 1.0),
            (bar(32), 81, 2.0), (bar(32) + 2, 79, 1.0), (bar(32) + 3, 76, 1.0)]
def phA2c():
    """A2 后段:E7 属色彩(半音 G#)"""
    return [(bar(33), 69, 1.5), (bar(33) + 1.5, 72, 0.5), (bar(33) + 2, 74, 1.0), (bar(33) + 3, 76, 1.0),
            (bar(34), 77, 0.5), (bar(34) + 0.5, 76, 0.5), (bar(34) + 1, 74, 0.5), (bar(34) + 1.5, 72, 0.5),
            (bar(34) + 2, 74, 1.0), (bar(34) + 3, 72, 1.0),
            (bar(35), 76, 2.0), (bar(35) + 2, 74, 1.0), (bar(35) + 3, 72, 1.0),
            (bar(36), 74, 0.5), (bar(36) + 0.5, 72, 0.5), (bar(36) + 1, 71, 1.0), (bar(36) + 2, 68, 1.0), (bar(36) + 3, 71, 1.0)]
def phA2d():
    return [(bar(37), 72, 1.5), (bar(37) + 1.5, 74, 0.5), (bar(37) + 2, 76, 1.0), (bar(37) + 3, 77, 1.0),
            (bar(38), 76, 1.0), (bar(38) + 1, 74, 1.0), (bar(38) + 2, 72, 1.0), (bar(38) + 3, 69, 1.0),
            (bar(39), 77, 1.0), (bar(39) + 1, 76, 1.0), (bar(39) + 2, 74, 1.0), (bar(39) + 3, 72, 1.0),
            (bar(40), 74, 1.5), (bar(40) + 1.5, 71, 0.5), (bar(40) + 2, 68, 1.0), (bar(40) + 3, 71, 1.0)]
def phB1():
    return [(bar(41), 74, 1.0), (bar(41) + 1, 77, 0.5), (bar(41) + 1.5, 81, 0.5), (bar(41) + 2, 77, 1.0), (bar(41) + 3, 74, 1.0),
            (bar(42), 76, 0.5), (bar(42) + 0.5, 77, 0.5), (bar(42) + 1, 79, 0.5), (bar(42) + 1.5, 81, 0.5),
            (bar(42) + 2, 79, 1.0), (bar(42) + 3, 76, 1.0),
            (bar(43), 81, 1.0), (bar(43) + 1, 79, 1.0), (bar(43) + 2, 77, 1.0), (bar(43) + 3, 76, 1.0),
            (bar(44), 77, 2.0), (bar(44) + 2, 74, 1.0), (bar(44) + 3, 76, 1.0)]
def phB2():
    return [(bar(45), 74, 0.25), (bar(45) + 0.25, 74, 0.25), (bar(45) + 0.5, 74, 0.25), (bar(45) + 0.75, 74, 0.25),
            (bar(45) + 1, 77, 1.0), (bar(45) + 2, 81, 1.0),
            (bar(46), 79, 0.25), (bar(46) + 0.25, 77, 0.25), (bar(46) + 0.5, 79, 0.25), (bar(46) + 0.75, 81, 0.25),
            (bar(46) + 1, 79, 1.0), (bar(46) + 2, 76, 1.0), (bar(46) + 3, 72, 1.0),
            (bar(47), 81, 1.0), (bar(47) + 1, 79, 1.0), (bar(47) + 2, 77, 1.0), (bar(47) + 3, 76, 1.0),
            (bar(48), 77, 2.0), (bar(48) + 2, 79, 1.0), (bar(48) + 3, 81, 1.0)]
def phB3():
    return [(bar(49), 81, 1.0), (bar(49) + 1, 83, 1.0), (bar(49) + 2, 81, 1.0), (bar(49) + 3, 79, 1.0),
            (bar(50), 77, 0.5), (bar(50) + 0.5, 79, 0.5), (bar(50) + 1, 81, 0.5), (bar(50) + 1.5, 83, 0.5),
            (bar(50) + 2, 81, 1.0), (bar(50) + 3, 77, 1.0),
            (bar(51), 79, 1.0), (bar(51) + 1, 81, 1.0), (bar(51) + 2, 83, 1.0), (bar(51) + 3, 84, 1.0),
            (bar(52), 81, 2.0), (bar(52) + 2, 81, 1.0), (bar(52) + 3, 79, 1.0)]
def phBend():
    """B 段尾:E7 属驻留(张力),G# 导音准备插部"""
    return [(bar(53), 71, 1.0), (bar(53) + 1, 74, 1.0), (bar(53) + 2, 76, 1.0), (bar(53) + 3, 74, 1.0),
            (bar(54), 71, 1.5), (bar(54) + 1.5, 68, 0.5), (bar(54) + 2, 69, 1.0), (bar(54) + 3, 71, 1.0),
            (bar(55), 74, 1.0), (bar(55) + 1, 72, 1.0), (bar(55) + 2, 71, 1.0), (bar(55) + 3, 68, 1.0),
            (bar(56), 71, 2.0), (bar(56) + 2, 69, 1.0), (bar(56) + 3, 68, 1.0)]
def phI1():
    """插部:抒情卡农(长音)"""
    return [(bar(57), 69, 2.0), (bar(57) + 2, 72, 1.0), (bar(57) + 3, 76, 1.0),
            (bar(58), 74, 2.0), (bar(58) + 2, 77, 1.0), (bar(58) + 3, 81, 1.0),
            (bar(59), 80, 2.0), (bar(59) + 2, 76, 1.0), (bar(59) + 3, 71, 1.0),
            (bar(60), 81, 2.0), (bar(60) + 2, 76, 1.0), (bar(60) + 3, 72, 1.0)]
def phI2():
    return [(bar(61), 71, 1.0), (bar(61) + 1, 72, 1.0), (bar(61) + 2, 74, 1.0), (bar(61) + 3, 76, 1.0),
            (bar(62), 77, 2.0), (bar(62) + 2, 76, 1.0), (bar(62) + 3, 74, 1.0),
            (bar(63), 76, 1.5), (bar(63) + 1.5, 74, 0.5), (bar(63) + 2, 72, 1.0), (bar(63) + 3, 71, 1.0),
            (bar(64), 69, 3.0)]
def phI3():
    """插部推进段:F-G 上行,回 E7 张力"""
    return [(bar(65), 77, 2.0), (bar(65) + 2, 81, 1.0), (bar(65) + 3, 77, 1.0),
            (bar(66), 76, 2.0), (bar(66) + 2, 74, 1.0), (bar(66) + 3, 72, 1.0),
            (bar(67), 74, 2.0), (bar(67) + 2, 79, 1.0), (bar(67) + 3, 74, 1.0),
            (bar(68), 72, 1.0), (bar(68) + 1, 71, 1.0), (bar(68) + 2, 69, 1.0), (bar(68) + 3, 67, 1.0),
            (bar(69), 71, 1.5), (bar(69) + 1.5, 68, 0.5), (bar(69) + 2, 69, 1.0), (bar(69) + 3, 71, 1.0),
            (bar(70), 74, 2.0), (bar(70) + 2, 71, 1.0), (bar(70) + 3, 68, 1.0)]
def phC1():
    return [(bar(73), 81, 1.5), (bar(73) + 1.5, 84, 0.5), (bar(73) + 2, 86, 1.0), (bar(73) + 3, 88, 1.0),
            (bar(74), 89, 0.5), (bar(74) + 0.5, 88, 0.5), (bar(74) + 1, 86, 0.5), (bar(74) + 1.5, 84, 0.5),
            (bar(74) + 2, 86, 1.0), (bar(74) + 3, 84, 0.5), (bar(74) + 3.5, 81, 0.5),
            (bar(75), 79, 1.0), (bar(75) + 1, 81, 1.0), (bar(75) + 2, 84, 1.0), (bar(75) + 3, 86, 1.0),
            (bar(76), 88, 2.0), (bar(76) + 2, 86, 1.0), (bar(76) + 3, 84, 1.0)]
def phC2():
    return [(bar(77), 81, 1.5), (bar(77) + 1.5, 84, 0.5), (bar(77) + 2, 86, 1.0), (bar(77) + 3, 88, 1.0),
            (bar(78), 89, 0.5), (bar(78) + 0.5, 88, 0.5), (bar(78) + 1, 86, 0.5), (bar(78) + 1.5, 84, 0.5),
            (bar(78) + 2, 83, 1.0), (bar(78) + 3, 79, 1.0), (bar(78) + 3.5, 81, 0.5),
            (bar(79), 84, 1.0), (bar(79) + 1, 86, 1.0), (bar(79) + 2, 88, 1.0), (bar(79) + 3, 89, 1.0),
            (bar(80), 88, 1.0), (bar(80) + 1, 89, 0.5), (bar(80) + 1.5, 91, 0.5), (bar(80) + 2, 88, 2.0)]
def phC3():
    return [(bar(81), 81, 0.25), (bar(81) + 0.25, 81, 0.25), (bar(81) + 0.5, 81, 0.25), (bar(81) + 0.75, 81, 0.25),
            (bar(81) + 1, 79, 1.0), (bar(81) + 2, 81, 0.5), (bar(81) + 2.5, 83, 0.5), (bar(81) + 3, 81, 1.0),
            (bar(82), 83, 0.5), (bar(82) + 0.5, 84, 0.5), (bar(82) + 1, 86, 0.5), (bar(82) + 1.5, 88, 0.5),
            (bar(82) + 2, 89, 1.0), (bar(82) + 3, 88, 1.0), (bar(82) + 3.5, 86, 0.5),
            (bar(83), 88, 1.0), (bar(83) + 1, 86, 1.0), (bar(83) + 2, 84, 1.0), (bar(83) + 3, 83, 1.0),
            (bar(84), 84, 2.0), (bar(84) + 2, 86, 1.0), (bar(84) + 3, 88, 1.0)]
def phC4():
    return [(bar(85), 89, 1.5), (bar(85) + 1.5, 88, 0.5), (bar(85) + 2, 86, 1.0), (bar(85) + 3, 84, 1.0),
            (bar(86), 86, 1.0), (bar(86) + 1, 84, 1.0), (bar(86) + 2, 81, 1.0), (bar(86) + 3, 79, 1.0),
            (bar(87), 81, 1.0), (bar(87) + 1, 84, 1.0), (bar(87) + 2, 88, 1.0), (bar(87) + 3, 81, 1.0),
            (bar(88), 81, 2.0), (bar(88) + 2, 79, 1.0), (bar(88) + 3, 76, 1.0)]
def phC5():
    return [(bar(89), 79, 1.5), (bar(89) + 1.5, 83, 0.5), (bar(89) + 2, 86, 1.0), (bar(89) + 3, 88, 1.0),
            (bar(90), 89, 0.5), (bar(90) + 0.5, 88, 0.5), (bar(90) + 1, 86, 0.5), (bar(90) + 1.5, 84, 0.5),
            (bar(90) + 2, 81, 1.0), (bar(90) + 3, 83, 1.0),
            (bar(91), 81, 1.0), (bar(91) + 1, 84, 1.0), (bar(91) + 2, 89, 1.0), (bar(91) + 3, 88, 1.0),
            (bar(92), 86, 1.5), (bar(92) + 1.5, 83, 0.5), (bar(92) + 2, 79, 1.0), (bar(92) + 3, 81, 1.0)]
def phC6():
    return [(bar(93), 81, 1.5), (bar(93) + 1.5, 84, 0.5), (bar(93) + 2, 86, 1.0), (bar(93) + 3, 88, 1.0),
            (bar(94), 89, 2.0), (bar(94) + 2, 88, 1.0), (bar(94) + 3, 86, 1.0),
            (bar(95), 88, 1.0), (bar(95) + 1, 86, 1.0), (bar(95) + 2, 84, 1.0), (bar(95) + 3, 83, 1.0),
            (bar(96), 81, 4.0)]
def phSp1():
    return [(bar(97), 81, 0.5), (bar(97) + 0.5, 84, 0.5), (bar(97) + 1, 81, 0.5), (bar(97) + 1.5, 84, 0.5),
            (bar(97) + 2, 86, 1.0), (bar(97) + 3, 84, 1.0), (bar(97) + 3.5, 81, 0.5),
            (bar(98), 77, 0.25), (bar(98) + 0.25, 79, 0.25), (bar(98) + 0.5, 81, 0.25), (bar(98) + 0.75, 83, 0.25),
            (bar(98) + 1, 84, 0.25), (bar(98) + 1.25, 86, 0.25), (bar(98) + 1.5, 88, 0.25), (bar(98) + 1.75, 89, 0.25),
            (bar(98) + 2, 88, 1.0), (bar(98) + 3, 86, 1.0),
            (bar(99), 84, 1.0), (bar(99) + 1, 88, 1.0), (bar(99) + 2, 84, 1.0), (bar(99) + 3, 88, 1.0),
            (bar(100), 81, 0.25), (bar(100) + 0.25, 81, 0.25), (bar(100) + 0.5, 81, 0.25), (bar(100) + 0.75, 81, 0.25),
            (bar(100) + 1, 81, 0.25), (bar(100) + 1.25, 81, 0.25), (bar(100) + 1.5, 81, 0.25), (bar(100) + 1.75, 81, 0.25),
            (bar(100) + 2, 76, 1.0), (bar(100) + 3, 81, 1.0)]
def phSp2():
    return [(bar(101), 81, 0.25), (bar(101) + 0.25, 81, 0.25), (bar(101) + 0.5, 81, 0.25), (bar(101) + 0.75, 81, 0.25),
            (bar(101) + 1, 84, 1.0), (bar(101) + 2, 86, 1.0), (bar(101) + 3, 88, 1.0),
            (bar(102), 89, 0.25), (bar(102) + 0.25, 88, 0.25), (bar(102) + 0.5, 86, 0.25), (bar(102) + 0.75, 84, 0.25),
            (bar(102) + 1, 83, 1.0), (bar(102) + 2, 81, 1.0), (bar(102) + 3, 79, 1.0),
            (bar(103), 81, 1.0), (bar(103) + 1, 84, 1.0), (bar(103) + 2, 88, 1.0), (bar(103) + 3, 81, 1.0),
            (bar(104), 81, 2.0), (bar(104) + 2, 76, 1.0), (bar(104) + 3, 81, 1.0)]
def phOut():
    """余韵:动机回声,渐弱"""
    return [(bar(107), 69, 2.0), (bar(107) + 2, 72, 1.0), (bar(107) + 3, 76, 1.0),
            (bar(108), 81, 3.0),
            (bar(111), 72, 1.5), (bar(111) + 1.5, 74, 0.5), (bar(111) + 2, 76, 1.0),
            (bar(112), 81, 2.0), (bar(112) + 2, 79, 1.0),
            (bar(113), 76, 2.0), (bar(113) + 2, 74, 1.0),
            (bar(114), 69, 3.0)]

# ---------- 生成 ----------
for bn, bpm in TEMPO:
    ev('meta', MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm * args.speed)), bar(bn))

# 引子(1-8,96):drone + 滚奏 + 预示碎片
multi(6, [(45, 60)], bar(1), 8 * 4)
multi(5, [(45, 42), (52, 42), (57, 42)], bar(1), 8 * 4)
for i in range(8):
    note(1, 38, 62, bar(1) + i * 4, 0.15)
snare_roll(bar(5), 16, 34, 100)
note(3, 57, 70, bar(8) + 3, 1.0)
# 预示碎片(钢琴弱奏,动机先现)
for t, p, d in [(bar(7), 69, 1.0), (bar(7) + 1, 72, 1.0), (bar(7) + 2, 74, 1.0), (bar(7) + 3, 76, 1.0)]:
    note(0, p, 40, t, d)
# 转场先现:bar 8 末尾轻 HH 八分 + kick 末拍(节奏预兆,避免鼓组满血突入)
for i in range(4):
    drum(HH, 42 if i % 2 else 50, bar(8) + 2 + i * 0.5, 0.12)
for i in range(4):
    drum(HH, 46 if i % 2 else 56, bar(9) + i * 0.5, 0.12)
drum(KICK, 72, bar(8) + 3.5, 0.15)

# A1(9-24,132):主题呈示——前 2 小节无军鼓渐进,bar 11 起完整 pattern
for n in range(9, 25):
    if n in (9, 10):
        pattern_a_nosnare(bar(n))
    else:
        pattern_a(bar(n))
    bass_riff(bar(n), CHORDS[n], 96)
    strings_stab(bar(n), CHORDS[n], 66)
for seq, v in ((ph1(), 86), (ph2(), 88), (ph3(), 88), (ph4(), 90)):
    for t, p, d in seq:
        note(0, p, v, t, d)
for n in (16, 24):
    fill(bar(n))

# A2(25-40,132):变奏 + E7 属色彩
for n in range(25, 41):
    pattern_a(bar(n))
    bass_riff(bar(n), CHORDS[n], 98)
    strings_stab(bar(n), CHORDS[n], 70)
for seq, v in ((ph5(), 90), (ph6(), 92), (phA2c(), 92), (phA2d(), 94)):
    for t, p, d in seq:
        note(0, p, v, t, d)
for n in (32,):
    fill(bar(n))
fill16(bar(40))                      # 十六分预热 → B 段(速度+密度平滑换挡)
note(3, 56, 88, bar(40) + 3, 1.0)   # 铜管 G#3(E7 三音)预告

# B(41-56,144):推进 + E7 属驻留——末 2 小节鼓密度抽离,平滑进入插部
for n in range(41, 55):
    pattern_b(bar(n))
    bass_riff(bar(n), CHORDS[n], 100)
    strings_stab(bar(n), CHORDS[n], 70)
for n in (55,):
    pattern_b_light(bar(n))
    bass_riff(bar(n), CHORDS[n], 92)
    strings_stab(bar(n), CHORDS[n], 62)
for n in (56,):
    pattern_strip(bar(n))
    bass_riff(bar(n), CHORDS[n], 80)
    multi(2, [(x, 54) for x in CHORD_TONES[CHORDS[n]]], bar(n), 4.0)
for seq, v in ((phB1(), 94), (phB2(), 95), (phB3(), 96), (phBend(), 96)):
    for t, p, d in seq:
        note(0, p, v, t, d)
prog(2, PIZZ, bar(56) + 3.5)        # 拨弦音色在击奏停止后即刻切换(避免瞬切)

# 插部(57-72,120):对比段——拨弦 + 无鼓留白 + 轻律动
for n in range(57, 65):
    bass_whole(bar(n), CHORDS[n], 55)
    pizz_stab(bar(n), CHORDS[n], 58)
    if n >= 61:                                      # 合唱延迟进入(先让拨弦独奏)
        multi(4, [(x, 50) for x in CHORD_TONES_LO[CHORDS[n]]], bar(n), 4.0)
for seq, v in ((phI1(), 78), (phI2(), 76)):
    for t, p, d in seq:
        note(0, p, v, t, d)
for n in range(65, 71):
    pattern_light(bar(n))
    bass_riff(bar(n), CHORDS[n], 74)
    pizz_stab(bar(n), CHORDS[n], 62)
    multi(4, [(x, 58) for x in CHORD_TONES_LO[CHORDS[n]]], bar(n), 4.0)
for t, p, d in phI3():
    note(0, p, 82, t, d)
# 留白(71-72)+ 滚奏衔接高潮:和声预挂 + crash 落在 73 强拍
snare_roll(bar(72), 4, 40, 112)
note(6, 41, 60, bar(72) + 2, 2.0)    # 和声预挂:滚奏后半已落到 F 低音
note(6, 45, 66, bar(72) + 3.5, 0.5)  # 低音预垫(提前抓住新速度)
prog(2, 48, bar(72) + 2)             # 弦乐音色提前切回(滚奏期间,无听觉断裂)

# 高潮(73-96,138):全奏 + 铜管六度对位——分层渐进进入:
#   bar73 骨架(鼓/低音/弦乐/旋律/铜管弱档)→ bar74-75 加吉他+合唱 → bar76 全满
for n in range(73, 97):
    pattern_c(bar(n))
    bass_riff(bar(n), CHORDS[n], 108)
    strings_stab(bar(n), CHORDS[n], 80)
    if n >= 74:                                          # 吉他分层进入
        guitar_power(bar(n), CHORDS[n], 72 if n in (74, 75) else 80)
    if n >= 75:                                          # 合唱分层进入
        multi(4, [(x, 60 if n in (75, 76) else 72) for x in CHORD_TONES_LO[CHORDS[n]]], bar(n), 4.0)
    multi(3, [(x, 70 if n == 73 else 84) for x in CHORD_TONES[CHORDS[n]]], bar(n), 1.0)
    note(3, 57, 90, bar(n) + 3, 0.8)
    if n % 4 == 1:
        drum(CRASH, 104, bar(n), 1.0)
    if n == 96:
        fill(bar(96))                                  # 衔接冲刺
for seq, v in ((phC1(), 100), (phC2(), 102), (phC3(), 103), (phC4(), 100),
               (phC5(), 103), (phC6(), 104)):
    for t, p, d in seq:
        note(0, p, v, t, d)
# 铜管副旋律:主旋律下方六度(对位),冲突音归位到和弦音
for seq, v in ((phC1(), 82), (phC3(), 84), (phC5(), 84)):
    for t, p, d in seq:
        if p - 9 >= 48:
            cp = counter_melody(p, CHORDS[bar_of(t)])
            note(3, cp, v, t, d * 0.9)

# 冲刺(97-104,142→150):密度最大
for n in range(97, 105):
    pattern_c(bar(n), k=116, s=114, h=88)
    bass_riff(bar(n), 'Am', 112)
    strings_stab(bar(n), 'Am', 84)
    guitar_power(bar(n), 'Am', 84)
for seq, v in ((phSp1(), 106), (phSp2(), 108)):
    for t, p, d in seq:
        note(0, p, v, t, d)
fill(bar(104))

# 重击(105-106):骤停
drum(KICK, 112, bar(105), 0.3)
drum(CRASH, 106, bar(105), 1.0)
drum(SNARE, 106, bar(105) + 2, 0.2)
drum(SNARE, 104, bar(105) + 3, 0.2)
note(1, 38, 106, bar(105), 2.0)
note(1, 36, 100, bar(105), 2.0)
multi(3, [(45, 100), (52, 96)], bar(105), 2.0)
note(0, 81, 104, bar(105), 2.0)
# 重击延音(bar 106):铜管 + 低音长音渐弱,与余韵重叠(避免骤停后冷启动)
multi(3, [(45, 56), (52, 52)], bar(106), 4.0)
note(6, 45, 52, bar(106), 4.0)

# 余韵(107-116,96→72):战斗后的寂静——drone + 钢琴回声渐弱
multi(6, [(45, 40)], bar(107), 5 * 4)
multi(5, [(45, 36), (52, 36), (57, 36)], bar(107), 5 * 4)
multi(6, [(45, 30)], bar(112), 5 * 4)
multi(5, [(45, 28), (52, 28), (57, 28)], bar(112), 5 * 4)
for i, (t, p, d) in enumerate(phOut()):
    note(0, p, max(30, 56 - i * 6), t, d)

# 表情(CC11:乐句级起伏;转场处斜坡化,不做跳变)
for bn, v in [(1, 50), (8, 62), (9, 72), (11, 78), (13, 82), (17, 85), (21, 88), (25, 90), (29, 94),
              (33, 96), (37, 98), (41, 100), (45, 104), (49, 106), (53, 108),
              (55, 102), (56, 92), (57, 58), (61, 66), (65, 78), (69, 86), (71, 78),
              (73, 106), (77, 110), (81, 112), (85, 114), (89, 115), (93, 116),
              (97, 116), (101, 118), (105, 120), (106, 76), (107, 52), (109, 42), (112, 32), (115, 22)]:
    cc(0, 11, v, bar(bn))
    cc(2, 11, v, bar(bn))

# 结尾尾音
tail = bar(117) + 2
ev(0, Message('control_change', channel=0, control=11, value=0), tail)

# ---------- 冲刷 ----------
def flush():
    meta_evs = sorted((x for x in pending if x[0] == 'meta'), key=lambda x: x[1])
    prev = 0
    for _, beat, msg in meta_evs:
        tick = int(beat * TPB)
        msg.time = tick - prev
        prev = tick
        meta.append(msg)
    meta.append(MetaMessage('end_of_track', time=0))
    for ch in range(10):
        e = sorted((x for x in pending if x[0] == ch), key=lambda x: x[1])
        prev = 0
        for _, beat, msg in e:
            tick = int(beat * TPB)
            msg.time = tick - prev
            prev = tick
            tracks[ch].append(msg)
        tracks[ch].append(MetaMessage('end_of_track', time=0))

flush()
out = args.out
mid.save(out)

# ---------- 自检 ----------
if not args.no_verify:
    print('=== 自检:Tempo map ===')
    for bn, bpm in TEMPO:
        print(f'  bar {bn:2d} → {bpm * args.speed:.0f} BPM')
    print('=== 自检:各通道音符数 ===')
    for ch in range(10):
        n = sum(1 for x in pending if x[0] == ch and x[2].type == 'note_on')
        if n:
            print(f'  ch{ch}: {n}')
print(f'saved {out}  (speed={args.speed}, transpose={TR:+d})')
