#!/usr/bin/env python3
"""themes.py — 旋律变换工具与循环动机原语

序列表示:seq = [(beat_off, pitch, dur), ...](相对起点,拍为单位)
纯函数变换,供各乐章做"多旋律变奏":移调/倒影/逆行/增时/减缩/切分。
"""
import copy

def T(seq, semitones):
    """移调"""
    return [(b, p + semitones, d) for b, p, d in seq]

def invert(seq, axis_pitch):
    """倒影:绕 axis_pitch 翻转音高,节奏不变"""
    return [(b, 2 * axis_pitch - p, d) for b, p, d in seq]

def retrograde(seq, total_beats=None):
    """逆行:节奏反向;total_beats 给整句长度(默认取句末+尾音时长)"""
    if total_beats is None:
        total_beats = max(b + d for b, p, d in seq)
    out = []
    for b, p, d in seq:
        nb = total_beats - (b + d)
        out.append((nb, p, d))
    out.sort(key=lambda x: x[0])
    return out

def augment(seq, factor):
    """增时:时长与起始时间按 factor 放大"""
    return [(b * factor, p, d * factor) for b, p, d in seq]

def diminish(seq, factor):
    """减缩"""
    return [(b / factor, p, d / factor) for b, p, d in seq]

def shift(seq, beats):
    """整体平移"""
    return [(b + beats, p, d) for b, p, d in seq]

def slice(seq, start, end):
    """截取片段"""
    return [(b, p, d) for b, p, d in seq if b + d > start and b < end]

def sustain_last(seq, beats):
    """把句尾音延长(收束用)"""
    if not seq:
        return seq
    out = copy.deepcopy(list(seq))
    b, p, d = out[-1]
    out[-1] = (b, p, d + beats)
    return out

def phrase(notes, bpb=4, start_bar=1):
    """notes: [(拍内偏移, pitch, dur), ...] → 绝对拍序列"""
    base = (start_bar - 1) * bpb
    return [(base + b, p, d) for b, p, d in notes]

# ---------- 循环动机原语 ----------
# 深渊动机 X:d 小调 D–C#–A,节奏 ♩. ♪ ♪
MOTIF_X = [(0.0, 62, 1.5), (1.5, 61, 0.5), (2.0, 57, 0.5)]
# 倒影 X-inv(上行):A–B–D
MOTIF_X_INV = [(0.0, 57, 1.5), (1.5, 59, 0.5), (2.0, 62, 0.5)]

def motif_x(pitch_root=62, bpb=4):
    """生成 X 的给定根音版本(根音=起点音)"""
    d = pitch_root - 62
    return [(b, p + d, du) for b, p, du in MOTIF_X]
