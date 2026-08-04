#!/usr/bin/env python3
"""《The Nameless Abyss / 无名之渊》— 原创 MIDI 作曲脚本(方法论仿 deepseek 版,音乐材料全原创)
方法论:
- 小调叙事:下行"坠落"动机 → 上行转调(深渊上升)→ 全奏高潮 → 归于寂静
- 空灵音色层:音乐盒高音闪烁 + 竖琴琶音 + 人声 Oohs + 冷 Pad + 低音提琴 drone
- CC11 表情曲线缓慢渐强渐弱
- 自检:导出主旋律/低音声部核对 + RMS 响度分段验证
"""
import argparse
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

parser = argparse.ArgumentParser(description='《The Nameless Abyss / 无名之渊》作曲生成器')
parser.add_argument('--bpm', type=int, default=69, help='速度(默认 69)')
parser.add_argument('--transpose', type=int, default=0, help='整体移调半音数(默认 0,正=升高)')
parser.add_argument('--out', default='The_Nameless_Abyss.mid', help='输出 MIDI 路径')
parser.add_argument('--no-verify', action='store_true', help='跳过声部自检打印')
args = parser.parse_args()

BPM = args.bpm
TR = args.transpose        # 所有音高统一移调
TPB = 480
BPB = 3                      # 3/4 拍

PROGRAMS = {
    0: 0,    # Acoustic Grand Piano — 主旋律
    1: 46,   # Orchestral Harp      — 琶音
    2: 48,   # String Ensemble 1    — 铺底/高潮齐奏
    3: 49,   # String Ensemble 2    — 高潮齐奏
    4: 53,   # Voice Oohs           — 空灵吟唱
    5: 10,   # Music Box            — 高音闪烁
    6: 43,   # Contrabass           — 低音 drone/根音
    7: 89,   # Pad 2 (warm)         — 氛围垫
}

mid = MidiFile(ticks_per_beat=TPB)
meta = MidiTrack()
mid.tracks.append(meta)
meta.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0))
meta.append(MetaMessage('time_signature', numerator=3, denominator=4, time=0))

tracks = {}
for ch in range(8):
    t = MidiTrack()
    mid.tracks.append(t)
    tracks[ch] = t
    t.append(Message('program_change', channel=ch, program=PROGRAMS[ch], time=0))

pending = []   # (channel, beat, msg)

def ev(ch, msg, beat):
    pending.append((ch, beat, msg))

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

# ---------- 和声设计:E小调 → F#小调(上行转调)→ 回归 E小调 ----------
# 根音 MIDI
ROOT = {'Em': 40, 'C': 36, 'G': 43, 'D': 38, 'Am': 45, 'B7': 47, 'F#m': 42, 'A': 45, 'E': 40}
QUAL = {'Em': 'min', 'Am': 'min', 'F#m': 'min', 'C': 'maj', 'G': 'maj', 'D': 'maj', 'A': 'maj', 'B7': 'maj', 'E': 'maj'}
CHORDS = {}
for n in range(1, 11):
    CHORDS[n] = 'Em'                                # 引子:Em drone
for n in range(11, 35):
    CHORDS[n] = ['Em', 'C', 'G', 'D'][(n - 11) % 4] # A段:下行主题
for n in range(35, 39):
    CHORDS[n] = ['Am', 'C', 'G', 'D'][n - 35]
CHORDS[39] = 'C'; CHORDS[40] = 'B7'; CHORDS[41] = 'B7'; CHORDS[42] = 'F#m'
for n in range(43, 49):
    CHORDS[n] = ['F#m', 'D', 'A', 'E', 'F#m', 'F#m'][n - 43]  # 新调吟唱
for n in range(49, 65):
    CHORDS[n] = ['F#m', 'D', 'A', 'E'][(n - 49) % 4]          # 高潮全奏
CHORDS[65] = 'F#m'; CHORDS[66] = 'F#m'; CHORDS[67] = 'B7'; CHORDS[68] = 'B7'
for n in range(69, 73):
    CHORDS[n] = 'Em'                                # 尾声:回归 E 小调

def harp_notes(root, qual):
    r = root + 12
    if qual == 'min':
        return [r, r + 7, r + 12, r + 15, r + 19, r + 24]
    return [r, r + 7, r + 12, r + 16, r + 19, r + 24]

# ---------- 旋律(原创) ----------
# A 段下行"坠落"主题:级进下行 E5→D5→C5→B4 + 变奏(4小节一句 ×6)
def phA1():
    return [(bar(11), 76, 2.0), (bar(11) + 2, 74, 1.0),
            (bar(12), 72, 2.0), (bar(12) + 2, 71, 1.0),
            (bar(13), 72, 3.0), (bar(14), 74, 1.5), (bar(14) + 1.5, 71, 1.5)]
def phA2():
    return [(bar(15), 69, 2.0), (bar(15) + 2, 71, 1.0),
            (bar(16), 72, 2.0), (bar(16) + 2, 76, 1.0),
            (bar(17), 74, 3.0), (bar(18), 71, 3.0)]
def phA3():
    return [(bar(19), 76, 2.0), (bar(19) + 2, 74, 1.0),
            (bar(20), 72, 2.0), (bar(20) + 2, 71, 1.0),
            (bar(21), 69, 3.0), (bar(22), 72, 1.5), (bar(22) + 1.5, 74, 1.5)]
def phA4():
    return [(bar(23), 69, 2.0), (bar(23) + 2, 71, 1.0),
            (bar(24), 72, 2.0), (bar(24) + 2, 76, 1.0),
            (bar(25), 78, 3.0), (bar(26), 74, 3.0)]
def phA5():
    return [(bar(27), 76, 2.0), (bar(27) + 2, 79, 1.0),
            (bar(28), 78, 2.0), (bar(28) + 2, 74, 1.0),
            (bar(29), 76, 3.0), (bar(30), 74, 1.5), (bar(30) + 1.5, 71, 1.5)]
def phA6():
    return [(bar(31), 72, 2.0), (bar(31) + 2, 71, 1.0),
            (bar(32), 69, 2.0), (bar(32) + 2, 67, 1.0),
            (bar(33), 71, 3.0), (bar(34), 64, 3.0)]
# B 段吟唱(转调叙事,G# 出现 = 转调信号)
def phB1():
    return [(bar(35), 69, 2.0), (bar(35) + 2, 71, 1.0),
            (bar(36), 72, 2.0), (bar(36) + 2, 76, 1.0),
            (bar(37), 74, 3.0), (bar(38), 72, 3.0)]
def phB2():
    return [(bar(39), 74, 2.0), (bar(39) + 2, 76, 1.0),
            (bar(40), 78, 2.0), (bar(40) + 2, 80, 1.0),
            (bar(41), 80, 3.0), (bar(42), 71, 3.0)]
def phB3():
    return [(bar(43), 78, 3.0), (bar(44), 81, 2.0), (bar(44) + 2, 83, 1.0),
            (bar(45), 81, 2.0), (bar(45) + 2, 80, 1.0),
            (bar(46), 78, 3.0), (bar(47), 76, 2.0), (bar(47) + 2, 74, 1.0),
            (bar(48), 78, 3.0)]
# 高潮全奏(F#m,宽广 + 连续上行"深渊上升"音列)
def phC1():
    return [(bar(49), 78, 3.0), (bar(50), 81, 2.0), (bar(50) + 2, 83, 1.0),
            (bar(51), 85, 2.0), (bar(51) + 2, 83, 1.0), (bar(52), 81, 3.0)]
def phC2():
    return [(bar(53), 80, 2.0), (bar(53) + 2, 81, 1.0), (bar(54), 83, 3.0),
            (bar(55), 81, 2.0), (bar(55) + 2, 80, 1.0), (bar(56), 78, 3.0)]
def phC3():
    return [(bar(57), 76, 1.0), (bar(57) + 1, 78, 1.0), (bar(57) + 2, 80, 1.0),
            (bar(58), 81, 1.0), (bar(58) + 1, 83, 1.0), (bar(58) + 2, 85, 1.0),
            (bar(59), 85, 3.0), (bar(60), 83, 2.0), (bar(60) + 2, 81, 1.0)]
def phC4():
    return [(bar(61), 81, 3.0), (bar(62), 80, 2.0), (bar(62) + 2, 78, 1.0),
            (bar(63), 76, 3.0), (bar(64), 78, 3.0)]
# 尾声:主题回响、回落 E 小调
def phOut():
    return [(bar(65), 78, 3.0), (bar(66), 76, 2.0), (bar(66) + 2, 74, 1.0),
            (bar(67), 73, 3.0), (bar(68), 71, 3.0),
            (bar(69), 69, 3.0), (bar(70), 67, 2.0), (bar(70) + 2, 66, 1.0),
            (bar(71), 64, 3.0)]

# ---------- 低音提琴:drone / 根音线 / 高潮八度加倍 ----------
multi(6, [(40, 50)], bar(1), 10 * 3.0)                    # 引子 E2 drone
for n in range(11, 49):
    note(6, ROOT[CHORDS[n]], 55 if n < 35 else 70, bar(n), 3.0)
for n in range(49, 65):                                    # 高潮:根音 + 高八度加倍
    multi(6, [(ROOT[CHORDS[n]], 78), (ROOT[CHORDS[n]] + 12, 68)], bar(n), 3.0)
for n in range(65, 69):
    note(6, ROOT[CHORDS[n]], 62, bar(n), 3.0)
note(6, 40, 45, bar(69), 4 * 3.0)                          # 尾声 E2 长音渐弱

# ---------- 冷 Pad(引子 + 尾声):Em9 / F#m9 色彩 ----------
PAD = {'Em': [52, 55, 59, 66], 'F#m': [54, 57, 61, 66], 'B7': [59, 63, 66, 71]}
multi(7, [(p, 42) for p in PAD['Em']], bar(1), 10 * 3.0)
multi(7, [(p, 40) for p in PAD['F#m']], bar(65), 4 * 3.0)
multi(7, [(p, 40) for p in PAD['B7']], bar(67), 2 * 3.0)
multi(7, [(p, 36) for p in PAD['Em']], bar(69), 4 * 3.0 + 8)   # 延过结尾留混响尾

# ---------- 音乐盒高音闪烁(引子 + 尾声 + 高潮跑动) ----------
for sb, seq in ((3, [79, 88, 83]), (4, [83]), (6, [79, 88]), (7, [78]), (9, [79, 83]), (10, [88]),
                (65, [78]), (67, [83]), (69, [88, 79]), (70, [83]), (71, [88]), (72, [88])):
    t = bar(sb)
    for i, p in enumerate(seq):
        note(5, p, 56, t + i * 1.5, 1.4)
# 高潮跑动:上行音列镜像(深渊上升的光点)
for i in range(12):
    note(5, [76, 78, 80, 81, 83, 85][i % 6], 62, bar(57) + i * 0.5, 0.45)

# ---------- 竖琴琶音 ----------
for n in range(11, 65):
    vel = 52 if n < 35 else (64 if n < 49 else 70)
    r = ROOT[CHORDS[n]]
    for i, p in enumerate(harp_notes(r, QUAL[CHORDS[n]])):
        note(1, p, vel, bar(n) + i * 0.5, 0.5)
for n in range(65, 69):
    r = ROOT[CHORDS[n]]
    for i, p in enumerate(harp_notes(r, QUAL[CHORDS[n]])):
        note(1, p, 46, bar(n) + i * 0.5, 0.5)

# ---------- 弦乐铺底(根音+五度;高潮 根+三+五 齐奏) ----------
def str_notes(root, qual, thick=False):
    n = [root, root + 7]
    if thick:
        n = [root, root + (3 if qual == 'min' else 4), root + 7]
    return n
for n in range(11, 49):
    multi(2, [(p, 46 if n < 35 else 62) for p in str_notes(ROOT[CHORDS[n]], QUAL[CHORDS[n]])], bar(n), 3.0)
for n in range(49, 65):
    multi(2, [(p, 80) for p in str_notes(ROOT[CHORDS[n]], QUAL[CHORDS[n]], thick=True)], bar(n), 3.0)

# ---------- 钢琴主旋律 ----------
for seq, v in ((phA1(), 62), (phA2(), 62), (phA3(), 64), (phA4(), 66),
               (phA5(), 66), (phA6(), 60), (phB1(), 68), (phB2(), 72),
               (phB3(), 74), (phC1(), 92), (phC2(), 94), (phC3(), 96),
               (phC4(), 92), (phOut(), 56)):
    for t, p, d in seq:
        note(0, p, v, t, d)

# 高潮:弦乐2 八度齐奏主旋律
for seq, v in ((phC1(), 84), (phC2(), 86), (phC3(), 88), (phC4(), 84)):
    for t, p, d in seq:
        note(3, p, v, t, d)
        note(3, p - 12, 62, t, d)

# ---------- 人声 Oohs:吟唱(B段) + 块状和声(高潮) ----------
for seq in (phB1(), phB2()):
    for t, p, d in seq:
        note(4, p - 12, 60, t, d)
for seq in (phB3(),):
    for t, p, d in seq:
        note(4, p - 12, 66, t, d)
CHOIR = {49: [57, 61, 66], 50: [62, 66, 69], 51: [57, 61, 64], 52: [64, 68, 71],
         53: [57, 61, 66], 54: [62, 66, 69], 55: [57, 61, 64], 56: [64, 68, 71],
         57: [57, 61, 66], 58: [62, 66, 69], 59: [57, 61, 64], 60: [64, 68, 71],
         61: [57, 61, 66], 62: [62, 66, 69], 63: [57, 61, 64], 64: [61, 66, 69]}
for n in range(49, 65):
    vel = 84 if n < 61 else 74
    multi(4, [(p, vel) for p in CHOIR[n]], bar(n), 3.0)

# ---------- CC11 表情曲线:缓慢渐强 → 高潮 → 渐弱 ----------
expr = [(1, 45), (11, 55), (23, 60), (35, 72), (39, 80), (43, 88),
        (49, 100), (53, 110), (57, 112), (61, 104), (65, 74),
        (67, 58), (69, 44), (71, 28), (72, 14)]
for bn, v in expr:
    cc(0, 11, v, bar(bn))
    cc(2, 11, v, bar(bn))

# ---------- 结尾尾音 + 冲刷 ----------
tail = bar(73) + 8
ev(0, Message('control_change', channel=0, control=11, value=0), tail)

def flush():
    for ch in range(8):
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

# ---------- 自检:导出主旋律与低音声部核对 ----------
if not args.no_verify:
    print('=== 自检:主旋律(钢琴)音符序列 ===')
    mel = sorted((x for x in pending if x[0] == 0 and x[2].type == 'note_on'), key=lambda x: x[1])
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    for _, beat, m in mel:
        print(f'  {m.note:3d} {names[m.note % 12]}{m.note // 12 - 1}  @bar{int(beat // 3) + 1}  vel{m.velocity}')
    print('=== 自检:低音(Contrabass)音符序列 ===')
    bas = sorted((x for x in pending if x[0] == 6 and x[2].type == 'note_on'), key=lambda x: x[1])
    for _, beat, m in bas:
        print(f'  {m.note:3d} {names[m.note % 12]}{m.note // 12 - 1}  @bar{int(beat // 3) + 1}')
print(f'saved {out}  总长 {bar(73) / 3 * 3 / BPM * 60 / 3:.1f}s ≈ 72 小节 @{BPM}BPM 3/4  transpose={TR:+d}')
