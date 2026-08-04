#!/usr/bin/env python3
"""《Echoes of the Abyss / 深渊回响》— 原创 MIDI 作曲脚本
风格:向《来自深渊》(Kevin Penkin)配乐语言致敬,旋律为原创。

风格映射:
- 3/4 拍、66 BPM 缓慢摇曳(摇篮曲般的悠远感)
- D 调为主,bVII(C)、vi(Bm) 等色彩和弦(仿 Hanezeve 的和声色彩)
- 低音 drone(深渊的黑暗)+ 竖琴琶音 + 钟琴高音点缀(垂直空间感)
- 小编制声部 + 靠后期大混响营造"大空间录制"的空旷感
- 合唱 Aahs 空灵吟唱;情绪弧线:静谧 → 涌起 → 回归空灵
"""
import argparse
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

parser = argparse.ArgumentParser(description='《Echoes of the Abyss / 深渊回响》作曲生成器')
parser.add_argument('--bpm', type=int, default=66, help='速度(默认 66)')
parser.add_argument('--transpose', type=int, default=0, help='整体移调半音数(默认 0,正=升高)')
parser.add_argument('--out', default='Echoes_of_the_Abyss.mid', help='输出 MIDI 路径')
args = parser.parse_args()

BPM = args.bpm
TR = args.transpose        # 所有音高统一移调
TPB = 480
BEATS_PER_BAR = 3

# ---------- 通道与音色(GM) ----------
PROGRAMS = {
    0: 0,    # Acoustic Grand Piano   — 主旋律
    1: 46,   # Orchestral Harp        — 琶音
    2: 48,   # String Ensemble 1      — 弦乐铺底
    3: 52,   # Choir Aahs             — 空灵合唱
    4: 8,    # Celesta                — 高音钟琴微光
    5: 89,   # Pad 2 (warm)           — 氛围 pad(引子/尾声)
    6: 32,   # Acoustic Bass          — 低音 drone
}

mid = MidiFile(ticks_per_beat=TPB)

meta = MidiTrack()
mid.tracks.append(meta)
meta.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0))
meta.append(MetaMessage('time_signature', numerator=3, denominator=4, time=0))

tracks = {}
for ch in range(7):
    t = MidiTrack()
    mid.tracks.append(t)
    tracks[ch] = t
    t.append(Message('program_change', channel=ch, program=PROGRAMS[ch], time=0))

pending = []   # (channel, beat, msg) 收集后统一排序写入

def ev(ch, msg, beat):
    pending.append((ch, beat, msg))

def flush():
    for ch in range(7):
        e = sorted((x for x in pending if x[0] == ch), key=lambda x: x[1])
        prev = 0
        for _, beat, msg in e:
            tick = int(beat * TPB)
            msg.time = tick - prev
            prev = tick
            tracks[ch].append(msg)
        tracks[ch].append(MetaMessage('end_of_track', time=0))

def note(ch, pitch, vel, start_beat, dur_beat):
    p = pitch + TR
    ev(ch, Message('note_on', channel=ch, note=p, velocity=vel), start_beat)
    ev(ch, Message('note_off', channel=ch, note=p, velocity=0), start_beat + dur_beat)

def cc(ch, ctrl, val, beat):
    ev(ch, Message('control_change', channel=ch, control=ctrl, value=val), beat)

def multi(ch, notes_list, start_beat, dur_beat):
    """同一通道、同一时刻开始的一组音(如和弦/双音)"""
    for p, v in notes_list:
        ev(ch, Message('note_on', channel=ch, note=p + TR, velocity=v), start_beat)
    for p, _ in notes_list:
        ev(ch, Message('note_off', channel=ch, note=p + TR, velocity=0), start_beat + dur_beat)

def bar(n):            # 小节起始拍(1-based)
    return (n - 1) * BEATS_PER_BAR

# ---------- 和弦表(小节 → 根音) ----------
# 根音 MIDI:D2=38 C2=36 G2=43 A2=45 B2=47
ROOT = {'D': 38, 'C': 36, 'G': 43, 'A': 45, 'Bm': 47}
SUS = [50, 52, 57, 62]          # D3 E3 A3 D4 (Dsus2, 引子/尾声 pad)
CHORDS = {}
for n in range(1, 9):
    CHORDS[n] = 'D'             # 引子(实际只出 pad/drone)
seq_a = ['D', 'C', 'G', 'D', 'D', 'C', 'G', 'A',
         'D', 'C', 'G', 'D', 'Bm', 'G', 'A', 'D']
for i, r in enumerate(seq_a):
    CHORDS[9 + i] = r
    CHORDS[25 + i] = r          # A 段与 A2 段同和声
seq_b = ['Bm', 'G', 'D', 'A', 'Bm', 'G', 'D', 'A',
         'C', 'G', 'D', 'A', 'C', 'D', 'D', 'D']
for i, r in enumerate(seq_b):
    CHORDS[41 + i] = r
for n in range(57, 69):
    CHORDS[n] = 'D'             # 尾声回 Dsus2

def harp_notes(root):
    """6 音琶音:根 五 根8 三8 五8 根15"""
    r = root + 12
    if root == 47:              # Bm
        return [r, r + 7, r + 12, r + 15, r + 19, r + 24]
    return [r, r + 7, r + 12, r + 16, r + 19, r + 24]

def string_notes(root):
    return [root, root + 7]     # 低音区 根+五度

# ---------- 旋律 ----------
def ph1(shift):
    return [(bar(9 + shift), 74, 3.0), (bar(10 + shift), 78, 1.5), (bar(10 + shift) + 1.5, 81, 1.5),
            (bar(11 + shift), 79, 3.0), (bar(12 + shift), 76, 2.0), (bar(12 + shift) + 2, 74, 1.0),
            (bar(13 + shift), 72, 1.5), (bar(13 + shift) + 1.5, 76, 1.5),
            (bar(14 + shift), 78, 2.0), (bar(14 + shift) + 2, 81, 1.0),
            (bar(15 + shift), 83, 1.5), (bar(15 + shift) + 1.5, 81, 1.5),
            (bar(16 + shift), 79, 2.0), (bar(16 + shift) + 2, 78, 1.0)]

def ph2(shift):
    return [(bar(17 + shift), 81, 3.0), (bar(18 + shift), 79, 1.5), (bar(18 + shift) + 1.5, 76, 1.5),
            (bar(19 + shift), 78, 3.0), (bar(20 + shift), 74, 2.0), (bar(20 + shift) + 2, 76, 1.0),
            (bar(21 + shift), 76, 1.5), (bar(21 + shift) + 1.5, 78, 1.5),
            (bar(22 + shift), 81, 3.0), (bar(23 + shift), 83, 1.5), (bar(23 + shift) + 1.5, 81, 1.5),
            (bar(24 + shift), 78, 2.0), (bar(24 + shift) + 2, 74, 1.0)]

def phB():
    return [(bar(41), 81, 3.0), (bar(42), 83, 1.5), (bar(42) + 1.5, 86, 1.5),
            (bar(43), 81, 3.0), (bar(44), 78, 2.0), (bar(44) + 2, 79, 1.0),
            (bar(45), 76, 3.0), (bar(46), 78, 1.5), (bar(46) + 1.5, 81, 1.5),
            (bar(47), 83, 3.0), (bar(48), 81, 2.0), (bar(48) + 2, 78, 1.0),
            (bar(49), 79, 3.0), (bar(50), 81, 1.5), (bar(50) + 1.5, 83, 1.5),
            (bar(51), 86, 3.0), (bar(52), 83, 2.0), (bar(52) + 2, 81, 1.0),
            (bar(53), 81, 3.0), (bar(54), 83, 1.5), (bar(54) + 1.5, 81, 1.5),
            (bar(55), 78, 3.0), (bar(56), 74, 3.0)]

# ---------- 低音 drone / 每小节低音 ----------
# 引子:bar1-8 持续 D2
note(6, 38, 45, bar(1), 8 * 3.0)
for n in range(9, 57):
    vel = 55 if n < 41 else 78
    note(6, ROOT[CHORDS[n]], vel, bar(n), 3.0)
# 尾声:bar57-68 持续 D2
note(6, 38, 40, bar(57), 12 * 3.0)

# ---------- 氛围 pad(引子 1-8 + 尾声 57-68) ----------
multi(5, [(p, 42) for p in SUS], bar(1), 8 * 3.0)
multi(5, [(p, 38) for p in SUS], bar(57), 12 * 3.0 + 7)  # 延过结尾,留混响尾

# ---------- 钟琴微光(引子 + 尾声) ----------
for sb, seq in ((3, [81, 88, 93]), (6, [86, 90, 93]), (61, [86, 81, 88]), (63, [90, 86]), (66, [88, 86]), (67, [86]), (68, [86])):
    t = bar(sb)
    for i, p in enumerate(seq):
        note(4, p, 58, t + i * 1.5, 1.4)

# ---------- 竖琴琶音(A/A2/B/尾声开头) ----------
for n in list(range(9, 41)) + list(range(41, 57)) + list(range(57, 61)):
    vel = 55 if n < 41 else (72 if n < 57 else 46)
    r = ROOT[CHORDS[n]]
    for i, p in enumerate(harp_notes(r)):
        note(1, p, vel, bar(n) + i * 0.5, 0.5)

# ---------- 弦乐铺底(9-56) ----------
for n in range(9, 57):
    vel = 48 if n < 41 else 80
    multi(2, [(p, vel) for p in string_notes(ROOT[CHORDS[n]])], bar(n), 3.0)

# ---------- 钢琴旋律 ----------
for seq, v in ((ph1(0), 62), (ph2(0), 62), (ph1(16), 74), (ph2(16), 74)):
    for t, p, d in seq:
        note(0, p, v, t, d)
# B 段:旋律 + 低八度加厚
for t, p, d in phB():
    multi(0, [(p, 96), (p - 12, 68)], t, d)
# 尾声:主题回响
note(0, 74, 60, bar(57), 3.0)
note(0, 78, 56, bar(58), 1.5)
note(0, 81, 56, bar(58) + 1.5, 1.5)

# ---------- 合唱 Aahs ----------
# A2 段(25-40):下方纯五度应和,跟随钢琴旋律
for seq in (ph1(16), ph2(16)):
    for t, p, d in seq:
        note(3, p - 7, 64, t, d)
# B 段(41-56):三声部块状长音
choir_blocks = {
    41: [62, 66, 71], 42: [62, 67, 71], 43: [62, 66, 69], 44: [61, 64, 69],
    45: [62, 66, 71], 46: [62, 67, 71], 47: [62, 66, 69], 48: [61, 64, 69],
    49: [64, 67, 72], 50: [62, 67, 71], 51: [62, 66, 69], 52: [61, 64, 69],
    53: [64, 67, 72], 54: [62, 66, 69], 55: [62, 66, 69], 56: [62, 66, 69],
}
for n in range(41, 57):
    vel = 84 if n < 53 else 72
    multi(3, [(p, vel) for p in choir_blocks[n]], bar(n), 3.0)

# ---------- 表情(CC11 渐强/渐弱,通道 0/2) ----------
expr = [(1, 50), (9, 60), (17, 66), (25, 72), (33, 78), (41, 90), (45, 100),
        (49, 110), (51, 115), (53, 100), (54, 88), (55, 74), (57, 58),
        (61, 48), (65, 40), (67, 32), (68, 26)]
for bn, v in expr:
    cc(0, 11, v, bar(bn))
for bn, v in [(41, 70), (49, 110), (55, 60), (57, 50), (65, 38), (67, 30)]:
    cc(2, 11, v, bar(bn))

# ---------- 结尾:推进时间留混响尾 ----------
tail = bar(69) + 7
ev(0, Message('control_change', channel=0, control=11, value=0), tail)

flush()

out = args.out
mid.save(out)
print('saved', out, '≈ 3:06 (68 bars @', BPM, 'bpm 3/4 + reverb tail, transpose=', TR, ')')
