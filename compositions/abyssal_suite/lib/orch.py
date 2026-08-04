#!/usr/bin/env python3
"""orch.py — 管弦乐配器库:《深渊四章》共享底层

设计:
- 每音色一条 MIDI 轨(格式 1),通道共享(弦乐分部/木管/铜管轮换同通道)
- bank select(CC0/CC32)+ program change 访问 MuseScore_General 扩展音色库
- CC11 表情曲线驱动 Expr 音色动态(实测 CC11: 0=静音 → 120≈ff)
- 事件收集 → 按绝对时间排序 → flush(承袭既有项目的防时间线冲突模式)
- 生成时自检:音色切换冲突 / 同刻同音高重叠 / 音区越界
"""
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

TPB = 480

# ---------------- 通道规划 ----------------
# 注意:通道 9(0-based)= GM 打击乐通道(1-based 的 "10")
CH = dict(
    piano=0, harp=1, vln1=2, vln2=3, vla=4, celli=5, bass=6,
    flute=7, oboe=8, drums=9, clarinet=10, timpani=11, horns=12,
    brass=13, choir=14, keys=15,
)

# ---------------- 音色注册表(bank, prog, 音区) ----------------
# Expr 变体(CC11 动态);非 Expr 用于拨弦/打击性音色
PROGS = {
    # 键盘
    'piano':        (0, 0, (21, 108)),
    'harp':         (0, 46, (28, 103)),
    'celesta':      (0, 8, (60, 108)),
    'glock':        (0, 9, (79, 108)),
    'organ':        (0, 19, (36, 84)),
    'church_bell':  (8, 14, (48, 96)),
    'pad':          (17, 89, (48, 84)),
    # 弦乐分部:slow/fast/trem 用 Expr, pizz 用非 Expr
    'vln1_slow': (21, 49, (55, 105)), 'vln1_trem': (21, 44, (55, 105)), 'vln1_pizz': (20, 45, (55, 105)),
    'vln2_slow': (26, 49, (55, 100)), 'vln2_trem': (26, 44, (55, 100)), 'vln2_pizz': (25, 45, (55, 100)),
    'vla_slow':  (31, 49, (48, 96)),  'vla_trem':  (31, 44, (48, 96)),  'vla_pizz':  (30, 45, (48, 96)),
    'celli_slow':(41, 49, (36, 76)),  'celli_trem':(41, 44, (36, 76)),  'celli_pizz':(40, 45, (36, 76)),
    'bass_slow': (51, 49, (28, 60)),  'bass_pizz': (50, 45, (28, 60)),
    # 木管
    'flute':    (17, 73, (60, 96)), 'piccolo': (17, 72, (74, 108)),
    'oboe':     (17, 68, (58, 91)), 'eng_horn': (17, 69, (55, 84)),
    'clarinet': (17, 71, (50, 91)), 'bassoon': (17, 70, (34, 65)),
    # 铜管
    'horn':     (17, 60, (41, 74)), 'brass_sec': (17, 61, (41, 81)),
    'trumpet':  (17, 56, (55, 93)), 'trombone': (17, 57, (40, 70)), 'tuba': (17, 58, (26, 53)),
    # 合唱
    'choir':    (17, 52, (48, 91)),
    # 打击乐
    'timpani':  (0, 47, (26, 60)), 'cbdrum': (8, 116, (28, 60)),
}


class Score:
    def __init__(self):
        self.pending = []        # (track_name, beat, msg)
        self.meta_msgs = []      # (beat, msg) tempo/meter
        self.tracks = {}         # track_name -> MidiTrack
        self.channel = {}        # track_name -> ch
        self.range = {}          # track_name -> (lo, hi)
        self.chan_prog = {}      # ch -> (bank, prog) 通道级当前音色(共享通道的关键)
        self._meter = (4, 4)

    # ---------- 注册与音色 ----------
    def add_instr(self, name, ch, bank=0, prog=0, lo=0, hi=127):
        assert name not in self.tracks, f'重复音轨: {name}'
        t = MidiTrack()
        self.tracks[name] = t
        self.channel[name] = ch
        self.range[name] = (lo, hi)
        # 仅当该通道尚无音色时在 0 拍声明;共享通道的后续音色由 prog() 在首次出现处切换
        if ch not in self.chan_prog:
            self.prog(name, bank, prog, 0.0)

    def prog(self, name, bank, prog, beat):
        """切换通道音色:bank select + program change(须落在该通道无声区)"""
        ch = self.channel[name]
        if self.chan_prog.get(ch) == (bank, prog):
            return
        self.chan_prog[ch] = (bank, prog)
        self._ev(name, beat, Message('control_change', channel=ch, control=0, value=(bank >> 7) & 0x7f))
        self._ev(name, beat, Message('control_change', channel=ch, control=32, value=bank & 0x7f))
        self._ev(name, beat, Message('program_change', channel=ch, program=prog))

    # ---------- 事件 ----------
    def _ev(self, name, beat, msg):
        self.pending.append((name, beat, msg))

    def note(self, name, pitch, vel, beat, dur):
        ch = self.channel[name]
        lo, hi = self.range[name]
        if not (lo <= pitch <= hi):
            print(f'  [音区告警] {name}: 音 {pitch} 超出 {lo}-{hi}')
        self._ev(name, beat, Message('note_on', channel=ch, note=pitch, velocity=vel))
        self._ev(name, beat + dur, Message('note_off', channel=ch, note=pitch, velocity=0))

    def chord(self, name, pitches, vel, beat, dur):
        for p in pitches:
            self.note(name, p, vel, beat, dur)

    def cc(self, name, ctrl, val, beat):
        self._ev(name, beat, Message('control_change', channel=self.channel[name], control=ctrl, value=val))

    def tempo(self, bpm, beat):
        self.meta_msgs.append((beat, MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm))))

    def meter(self, num, den, beat):
        self.meta_msgs.append((beat, MetaMessage('time_signature', numerator=num, denominator=den)))
        self._meter = (num, den)

    # ---------- 织体助手 ----------
    def arp(self, name, pitches, vel, beat, dur_each, loop=1, gap=0.0, vel_decay=0):
        """竖琴式琶音:pitches 循环 loop 轮"""
        t = beat
        for _ in range(loop):
            for i, p in enumerate(pitches):
                v = max(1, vel - vel_decay * i)
                self.note(name, p, v, t, dur_each * 0.9)
                t += dur_each
            t += gap

    def ostinato(self, name, pattern, vel, beat, loops=1, vel_fn=None):
        """重复节奏型:pattern = [(pitch, dur), ...]"""
        t = beat
        for _ in range(loops):
            for i, (p, d) in enumerate(pattern):
                v = vel_fn(i) if vel_fn else vel
                if p:
                    self.note(name, p, v, t, d * 0.92)
                t += d
        return t

    def roll(self, name, pitch, v0, v1, start, end, step=0.25, n=None):
        """滚奏渐强:start→end(拍),速度 v0→v1"""
        t = start
        i = 0
        while t < end:
            f = (t - start) / max(end - start, 1e-9)
            v = int(v0 + (v1 - v0) * f)
            self.note(name, pitch, v, t, step * 0.8)
            t += step
            i += 1

    # ---------- 冲刷 ----------
    def flush(self, path, verbose=True):
        # meta 轨
        meta = MidiTrack()
        meta.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
        prev = 0
        for beat, msg in sorted(self.meta_msgs, key=lambda x: x[0]):
            tick = int(round(beat * TPB))
            msg.time = tick - prev
            prev = tick
            meta.append(msg)
        meta.append(MetaMessage('end_of_track', time=0))

        # 各轨
        active = {}   # (ch, pitch) -> count, 用于冲突检查
        for name, t in self.tracks.items():
            evs = sorted((x for x in self.pending if x[0] == name), key=lambda x: x[1])
            prev = 0
            for _, beat, msg in evs:
                tick = int(round(beat * TPB))
                msg.time = tick - prev
                prev = tick
                t.append(msg)
            t.append(MetaMessage('end_of_track', time=0))

        mid = MidiFile(ticks_per_beat=TPB)
        mid.tracks.append(meta)
        for name in self.tracks:
            mid.tracks.append(self.tracks[name])
        mid.save(path)

        if verbose:
            self.report(path)

    def report(self, path):
        """自检:按通道合并事件,检查音色切换冲突与同刻同音重叠"""
        import collections
        by_ch = collections.defaultdict(list)
        for name, beat, msg in self.pending:
            by_ch[self.channel[name]].append((beat, name, msg))
        issues = 0
        for ch in sorted(by_ch):
            evs = sorted(by_ch[ch], key=lambda x: x[0])
            on = {}   # pitch -> (name, beat)
            for beat, name, msg in evs:
                if msg.type == 'note_on' and msg.velocity > 0:
                    key = (ch, msg.note)
                    if msg.note in on:
                        print(f'  [冲突] ch{ch} {msg.note} 同刻重叠: {on[msg.note][0]}@{on[msg.note][1]:.2f} vs {name}@{beat:.2f}')
                        issues += 1
                    on[msg.note] = (name, beat)
                elif msg.type == 'note_off':
                    if msg.note in on and on[msg.note][0] == name:
                        del on[msg.note]
                    elif msg.note in on:
                        # 另一轨的同音 note_off(程序切换前未停干净)
                        pass
                elif msg.type in ('program_change',):
                    # 音色切换时该通道须无活动音符
                    if on:
                        for p, (nm, bt) in sorted(on.items()):
                            print(f'  [切换冲突] ch{ch} @{beat:.2f} 切音色时 {nm} 的 {p} 仍在响(自 {bt:.2f})')
                        issues += 1
                        on.clear()
                elif msg.type == 'control_change':
                    if msg.control == 0 and on:
                        # bank select 属 program_change 前导,不重复告警
                        pass
        print(f'saved {path}  (自检完成,冲突 {issues} 处)')
        return issues
