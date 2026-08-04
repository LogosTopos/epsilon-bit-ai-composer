#!/usr/bin/env python3
"""《Battle in the Abyss / 深渊之战》— 原创战斗风 MIDI 作曲脚本

核心挑战:BPM 可变(不再是匀速行进)。
变速乐理设计:
  - 引子 96 BPM(黑暗铺垫,定音鼓滚奏渐强)
  - 主题爆发 132 BPM(段落切换,能量跃升)
  - B 段推进 144 BPM(加速推进)
  - 过渡 ritardando 132→120(喘息,弦乐长音 + 军鼓滚奏)
  - 高潮 138 BPM(全奏再次爆发)
  - 尾声 142→150 逐小节加速(冲刺)→ 重击骤停

战斗乐理语言:
  - 4/4 快板,A 小调;和声驱动 i-VI-III-VII(Am-F-C-G)+ iv(Dm)
  - 鼓组:八分脉冲闭镲 + backbeat 军鼓 + 切分底鼓;滚奏渐强
  - 低音八分音符 riff(根音脉冲 + 末拍五音导向)
  - 旋律:切分动机、十六分冲刺、模进、重复音驱动
  - 织体:弦乐 staccato 击奏、铜管重音、失真吉他强力和弦、合唱长音、定音鼓
"""
import argparse
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

parser = argparse.ArgumentParser(description='《Battle in the Abyss / 深渊之战》作曲生成器')
parser.add_argument('--speed', type=float, default=1.0, help='整体速度缩放(作用于所有 BPM,默认 1.0)')
parser.add_argument('--transpose', type=int, default=0, help='整体移调半音数(默认 0)')
parser.add_argument('--out', default='Battle_in_the_Abyss.mid', help='输出 MIDI 路径')
parser.add_argument('--no-verify', action='store_true', help='跳过自检打印')
args = parser.parse_args()

TR = args.transpose
TPB = 480
BPB = 4                          # 4/4 拍

# ---------- Tempo map:小节 → BPM(变速核心) ----------
TEMPO = [(1, 96), (9, 132), (33, 144), (45, 132), (46, 120),
         (47, 138), (63, 142), (64, 144), (65, 146), (66, 148), (67, 150)]

PROGRAMS = {
    0: 0,    # Acoustic Grand Piano — 主旋律
    1: 47,   # Timpani              — 定音鼓(滚奏/重击)
    2: 48,   # String Ensemble 1    — 击奏 riff/齐奏
    3: 61,   # Brass Section        — 重音/长音
    4: 52,   # Choir Aahs           — 高潮长音
    5: 49,   # String Ensemble 2    — 长音垫
    6: 33,   # Electric Bass        — 低音八分 riff
    7: 30,   # Distortion Guitar    — 强力和弦击奏
    # ch9 = 鼓(打击乐通道,无 program)
}

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

pending = []   # (key, beat, msg); key = 'meta' 或通道号

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

def bar(n):
    return (n - 1) * BPB

# ---------- 鼓(通道 9,GM 打击乐) ----------
KICK, SNARE, HH, OH, CRASH, RIDE = 36, 38, 42, 46, 49, 51
def drum(n, vel, beat, dur=0.1):
    ev(9, Message('note_on', channel=9, note=n, velocity=vel), beat)
    ev(9, Message('note_off', channel=9, note=n, velocity=0), beat + dur)

def pattern_a(sb, k=106, s=108, h=74):
    """A 段:闭镲八分 + 底鼓切分 + 军鼓 backbeat"""
    for i in range(8):
        drum(HH, h - 16 if i % 2 else h, sb + i * 0.5, 0.12)
    drum(KICK, k, sb)
    drum(KICK, k - 8, sb + 2.5)
    drum(KICK, k - 12, sb + 3.5)
    drum(SNARE, s, sb + 2)
    drum(SNARE, s, sb + 4)

def pattern_b(sb, k=108, s=110, h=80):
    """B 段:闭镲十六分(能量↑)+ 底鼓四平推进"""
    for i in range(16):
        drum(HH, h - 18 if i % 2 else h, sb + i * 0.25, 0.08)
    for i in range(4):
        drum(KICK, k - i * 6, sb + i)
    drum(SNARE, s, sb + 2)
    drum(SNARE, s, sb + 4)
    drum(SNARE, s - 14, sb + 2.5)
    drum(SNARE, s - 14, sb + 3.5)

def pattern_c(sb, k=112, s=112, h=84):
    """C 段:闭镲十六分 + 底鼓八分 drive + 军鼓双 backbeat"""
    for i in range(16):
        drum(HH, h - 18 if i % 2 else h, sb + i * 0.25, 0.08)
    for i in range(8):
        drum(KICK, k - (0 if i % 2 else 10), sb + i * 0.5)
    drum(SNARE, s, sb + 2)
    drum(SNARE, s, sb + 4)
    drum(SNARE, s - 10, sb + 2.75)
    drum(SNARE, s - 10, sb + 3.75)

def snare_roll(sb, beats, v0=36, v1=110):
    """军鼓十六分滚奏渐强"""
    n = int(beats * 4)
    for i in range(n):
        v = int(v0 + (v1 - v0) * i / max(n - 1, 1))
        drum(SNARE, v, sb + i * 0.25, 0.12)

# ---------- 和声/低音 ----------
CHORDS = {9: 'Am', 10: 'F', 11: 'C', 12: 'G', 13: 'Am', 14: 'F', 15: 'C', 16: 'G',
          17: 'Am', 18: 'F', 19: 'C', 20: 'G', 21: 'Am', 22: 'F', 23: 'C', 24: 'G',
          25: 'Am', 26: 'F', 27: 'C', 28: 'G', 29: 'Am', 30: 'F', 31: 'C', 32: 'G',
          33: 'Dm', 34: 'Am', 35: 'F', 36: 'G', 37: 'Dm', 38: 'Am', 39: 'F', 40: 'G',
          41: 'Dm', 42: 'Am', 43: 'F', 44: 'G',
          47: 'F', 48: 'G', 49: 'Am', 50: 'F', 51: 'G', 52: 'Am', 53: 'F', 54: 'G',
          55: 'Am', 56: 'F', 57: 'G', 58: 'Am', 59: 'F', 60: 'G', 61: 'Am', 62: 'F'}
# (bar 45-46 过渡无和声;bar 63-66 尾声回归 Am)
BASS = {'Am': 45, 'F': 41, 'C': 48, 'G': 43, 'Dm': 50}      # 八分 riff 根音
BASS_5 = {'Am': 52, 'F': 48, 'C': 55, 'G': 50, 'Dm': 57}    # 末拍五音
CHORD_TONES = {'Am': [57, 60, 64], 'F': [53, 57, 60], 'C': [60, 64, 67],
               'G': [55, 59, 62], 'Dm': [50, 53, 57]}       # 弦乐击奏和弦
CHORD_TONES_LO = {'Am': [45, 52, 57], 'F': [41, 48, 53], 'C': [48, 55, 60],
                  'G': [43, 50, 55], 'Dm': [50, 57, 62]}    # 低八度(垫/吉他)

def bass_riff(sb, ch, vel=96):
    r = BASS[ch]
    for i in range(8):
        p = BASS_5[ch] if i == 7 else r
        v = vel if i in (0, 4) else vel - 14
        note(6, p, v, sb + i * 0.5, 0.42)

def strings_stab(sb, ch, vel=66, dur=0.4):
    for i in range(8):
        p = CHORD_TONES[ch]
        v = vel + 10 if i in (0, 4) else vel
        multi(2, [(x, v) for x in p], sb + i * 0.5, dur)

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
def ph7():
    return [(bar(33), 74, 1.0), (bar(33) + 1, 77, 0.5), (bar(33) + 1.5, 81, 0.5), (bar(33) + 2, 77, 1.0), (bar(33) + 3, 74, 1.0),
            (bar(34), 76, 0.5), (bar(34) + 0.5, 77, 0.5), (bar(34) + 1, 79, 0.5), (bar(34) + 1.5, 81, 0.5),
            (bar(34) + 2, 79, 1.0), (bar(34) + 3, 76, 1.0),
            (bar(35), 81, 1.0), (bar(35) + 1, 79, 1.0), (bar(35) + 2, 77, 1.0), (bar(35) + 3, 76, 1.0),
            (bar(36), 77, 2.0), (bar(36) + 2, 74, 1.0), (bar(36) + 3, 76, 1.0)]
def ph8():
    return [(bar(37), 74, 0.25), (bar(37) + 0.25, 74, 0.25), (bar(37) + 0.5, 74, 0.25), (bar(37) + 0.75, 74, 0.25),
            (bar(37) + 1, 77, 1.0), (bar(37) + 2, 81, 1.0),
            (bar(38), 79, 0.25), (bar(38) + 0.25, 77, 0.25), (bar(38) + 0.5, 79, 0.25), (bar(38) + 0.75, 81, 0.25),
            (bar(38) + 1, 79, 1.0), (bar(38) + 2, 76, 1.0), (bar(38) + 3, 72, 1.0),
            (bar(39), 81, 1.0), (bar(39) + 1, 79, 1.0), (bar(39) + 2, 77, 1.0), (bar(39) + 3, 76, 1.0),
            (bar(40), 77, 2.0), (bar(40) + 2, 79, 1.0), (bar(40) + 3, 81, 1.0)]
def ph9():
    return [(bar(41), 81, 1.0), (bar(41) + 1, 83, 1.0), (bar(41) + 2, 81, 1.0), (bar(41) + 3, 79, 1.0),
            (bar(42), 77, 0.5), (bar(42) + 0.5, 79, 0.5), (bar(42) + 1, 81, 0.5), (bar(42) + 1.5, 83, 0.5),
            (bar(42) + 2, 81, 1.0), (bar(42) + 3, 77, 1.0),
            (bar(43), 79, 1.0), (bar(43) + 1, 81, 1.0), (bar(43) + 2, 83, 1.0), (bar(43) + 3, 84, 1.0),
            (bar(44), 81, 2.0), (bar(44) + 2, 81, 1.0), (bar(44) + 3, 79, 1.0)]
def ph10():
    return [(bar(47), 81, 1.5), (bar(47) + 1.5, 84, 0.5), (bar(47) + 2, 86, 1.0), (bar(47) + 3, 88, 1.0),
            (bar(48), 89, 0.5), (bar(48) + 0.5, 88, 0.5), (bar(48) + 1, 86, 0.5), (bar(48) + 1.5, 84, 0.5),
            (bar(48) + 2, 86, 1.0), (bar(48) + 3, 84, 0.5), (bar(48) + 3.5, 81, 0.5),
            (bar(49), 79, 1.0), (bar(49) + 1, 81, 1.0), (bar(49) + 2, 84, 1.0), (bar(49) + 3, 86, 1.0),
            (bar(50), 88, 2.0), (bar(50) + 2, 86, 1.0), (bar(50) + 3, 84, 1.0)]
def ph11():
    return [(bar(51), 81, 1.5), (bar(51) + 1.5, 84, 0.5), (bar(51) + 2, 86, 1.0), (bar(51) + 3, 88, 1.0),
            (bar(52), 89, 0.5), (bar(52) + 0.5, 88, 0.5), (bar(52) + 1, 86, 0.5), (bar(52) + 1.5, 84, 0.5),
            (bar(52) + 2, 83, 1.0), (bar(52) + 3, 79, 1.0), (bar(52) + 3.5, 81, 0.5),
            (bar(53), 84, 1.0), (bar(53) + 1, 86, 1.0), (bar(53) + 2, 88, 1.0), (bar(53) + 3, 89, 1.0),
            (bar(54), 88, 1.0), (bar(54) + 1, 89, 0.5), (bar(54) + 1.5, 91, 0.5), (bar(54) + 2, 88, 2.0)]
def ph12():
    return [(bar(55), 81, 0.25), (bar(55) + 0.25, 81, 0.25), (bar(55) + 0.5, 81, 0.25), (bar(55) + 0.75, 81, 0.25),
            (bar(55) + 1, 79, 1.0), (bar(55) + 2, 81, 0.5), (bar(55) + 2.5, 83, 0.5), (bar(55) + 3, 81, 1.0),
            (bar(56), 83, 0.5), (bar(56) + 0.5, 84, 0.5), (bar(56) + 1, 86, 0.5), (bar(56) + 1.5, 88, 0.5),
            (bar(56) + 2, 89, 1.0), (bar(56) + 3, 88, 1.0), (bar(56) + 3.5, 86, 0.5),
            (bar(57), 88, 1.0), (bar(57) + 1, 86, 1.0), (bar(57) + 2, 84, 1.0), (bar(57) + 3, 83, 1.0),
            (bar(58), 84, 2.0), (bar(58) + 2, 86, 1.0), (bar(58) + 3, 88, 1.0)]
def ph13():
    return [(bar(59), 89, 1.5), (bar(59) + 1.5, 88, 0.5), (bar(59) + 2, 86, 1.0), (bar(59) + 3, 84, 1.0),
            (bar(60), 86, 1.0), (bar(60) + 1, 84, 1.0), (bar(60) + 2, 81, 1.0), (bar(60) + 3, 79, 1.0),
            (bar(61), 81, 1.0), (bar(61) + 1, 84, 1.0), (bar(61) + 2, 88, 1.0), (bar(61) + 3, 81, 1.0),
            (bar(62), 81, 2.0), (bar(62) + 2, 79, 1.0), (bar(62) + 3, 76, 1.0)]
def ph14():
    return [(bar(63), 81, 0.5), (bar(63) + 0.5, 84, 0.5), (bar(63) + 1, 81, 0.5), (bar(63) + 1.5, 84, 0.5),
            (bar(63) + 2, 86, 1.0), (bar(63) + 3, 84, 1.0), (bar(63) + 3.5, 81, 0.5),
            (bar(64), 77, 0.25), (bar(64) + 0.25, 79, 0.25), (bar(64) + 0.5, 81, 0.25), (bar(64) + 0.75, 83, 0.25),
            (bar(64) + 1, 84, 0.25), (bar(64) + 1.25, 86, 0.25), (bar(64) + 1.5, 88, 0.25), (bar(64) + 1.75, 89, 0.25),
            (bar(64) + 2, 88, 1.0), (bar(64) + 3, 86, 1.0),
            (bar(65), 84, 1.0), (bar(65) + 1, 88, 1.0), (bar(65) + 2, 84, 1.0), (bar(65) + 3, 88, 1.0),
            (bar(66), 81, 0.25), (bar(66) + 0.25, 81, 0.25), (bar(66) + 0.5, 81, 0.25), (bar(66) + 0.75, 81, 0.25),
            (bar(66) + 1, 81, 0.25), (bar(66) + 1.25, 81, 0.25), (bar(66) + 1.5, 81, 0.25), (bar(66) + 1.75, 81, 0.25),
            (bar(66) + 2, 76, 1.0), (bar(66) + 3, 81, 1.0)]
def phFinal():
    return [(bar(67), 81, 2.0)]   # 重击长音

# ---------- 生成 ----------
# Tempo map(变速核心)
for bn, bpm in TEMPO:
    ev('meta', MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm * args.speed)), bar(bn))

# 引子(bar 1-8,96 BPM):drone + 定音鼓滚奏渐强 + 弦乐长音
multi(6, [(45, 60)], bar(1), 8 * 4)                      # A2 drone
multi(5, [(45, 42), (52, 42), (57, 42)], bar(1), 8 * 4)  # Am 长音垫
for i in range(8):
    note(1, 38, 62, bar(1) + i * 4, 0.15)                # 定音鼓小节头
snare_roll(bar(5), 16, 34, 104)                          # 军鼓滚奏渐强(临近爆发)
note(3, 57, 70, bar(8) + 3, 1.0)                         # 铜管预告音

# A 段(bar 9-32,132 BPM):鼓 + 低音 riff + 弦乐击奏 + 旋律
for n in range(9, 33):
    pattern_a(bar(n))
    bass_riff(bar(n), CHORDS[n], 96)
    strings_stab(bar(n), CHORDS[n], 66)
for seq, v in ((ph1(), 86), (ph2(), 88), (ph3(), 88), (ph4(), 90),
               (ph5(), 90), (ph6(), 92)):
    for t, p, d in seq:
        note(0, p, v, t, d)
# A 段尾铜管重音(bar 32 末)
note(3, 57, 92, bar(32) + 3, 1.0)

# B 段(bar 33-44,144 BPM):十六分镲 + 四平底鼓 + 旋律
for n in range(33, 45):
    pattern_b(bar(n))
    bass_riff(bar(n), CHORDS[n], 100)
    strings_stab(bar(n), CHORDS[n], 70)
for seq, v in ((ph7(), 94), (ph8(), 95), (ph9(), 96)):
    for t, p, d in seq:
        note(0, p, v, t, d)

# 过渡(bar 45-46):ritardando 132→120,军鼓滚奏渐强,弦乐长音
multi(5, [(57, 60), (60, 60), (64, 60)], bar(45), 2 * 4)
snare_roll(bar(45), 8, 40, 112)
note(3, 57, 80, bar(45), 4.0)
note(3, 57, 88, bar(46), 4.0)

# C 段(bar 47-62,138 BPM):全奏,铜管 + 合唱 + 吉他强力和弦
for n in range(47, 63):
    pattern_c(bar(n))
    bass_riff(bar(n), CHORDS[n], 108)
    strings_stab(bar(n), CHORDS[n], 80)
    guitar_power(bar(n), CHORDS[n], 80)
    multi(4, [(x, 72) for x in CHORD_TONES_LO[CHORDS[n]]], bar(n), 4.0)   # 合唱长音
    multi(3, [(x, 84) for x in CHORD_TONES[CHORDS[n]]], bar(n), 1.0)      # 铜管重音
    note(3, 57, 90, bar(n) + 3, 0.8)                                      # 铜管尾拍
for seq, v in ((ph10(), 100), (ph11(), 102), (ph12(), 103), (ph13(), 100)):
    for t, p, d in seq:
        note(0, p, v, t, d)

# 尾声(bar 63-67):冲刺 142→150,密度拉满
for n in range(63, 67):
    pattern_c(bar(n), k=116, s=114, h=88)
    bass_riff(bar(n), 'Am', 112)
    strings_stab(bar(n), 'Am', 84)
    guitar_power(bar(n), 'Am', 84)
for seq, v in ((ph14(), 106),):
    for t, p, d in seq:
        note(0, p, v, t, d)

# 重击(bar 67):定音鼓 + 鼓 + 铜管长音;bar 68 骤停
# (力度控在 112 以下,避免多声部叠加时在合成器内部削波)
drum(KICK, 112, bar(67), 0.3)
drum(CRASH, 106, bar(67), 1.0)
drum(SNARE, 106, bar(67) + 2, 0.2)
drum(SNARE, 104, bar(67) + 3, 0.2)
note(1, 38, 106, bar(67), 2.0)
note(1, 36, 100, bar(67), 2.0)
multi(3, [(45, 100), (52, 96)], bar(67), 2.0)
for t, p, d in phFinal():
    note(0, p, 104, t, d)

# 表情(CC11 段落化)
for bn, v in [(1, 50), (9, 78), (33, 90), (45, 70), (47, 108), (55, 112), (63, 116), (67, 120), (68, 30)]:
    cc(0, 11, v, bar(bn))
    cc(2, 11, v, bar(bn))

# 结尾尾音(留混响)
tail = bar(69) + 2
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
    print('=== 自检:Tempo map(小节 → BPM)===')
    for bn, bpm in TEMPO:
        print(f'  bar {bn:2d} → {bpm * args.speed:.0f} BPM')
    print('=== 自检:各通道音符数 ===')
    for ch in range(10):
        n = sum(1 for x in pending if x[0] == ch and x[2].type == 'note_on')
        print(f'  ch{ch}: {n}')
print(f'saved {out}  (speed={args.speed}, transpose={TR:+d})')
