#!/usr/bin/env python3
"""orch.py v2 — 配器库(修订版):《深渊对位》

相对 v1 的新增层(补混音与演奏层的缺口):
1. **声像(CC10)**:管弦乐摆位(一提左 / 大提右 / 铜管中 / 竖琴右 …),随音色切换一并发出
2. **混响发送(CC91)**:分层混响(竖琴/钢片琴近场亮、打击乐干、合唱远)——实测 FluidSynth 按 CC91 缩放每通道混响
3. **CC11 连续斜坡**:表情曲线节点间线性插值(整拍步进),渐强渐弱不再跳变
4. **人性化**:种子化时间/力度抖动(±0.006 拍,±2 力度),去机械感,可复现
5. 承袭 v1:通道级音色状态、bank select、生成时自检(切换冲突/同音重叠/音区)
"""
import random
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

TPB = 480

# ---------------- 通道规划(0-based;9 = GM 打击乐) ----------------
CH = dict(
    piano=0, harp=1, vln1=2, vln2=3, vla=4, celli=5, bass=6,
    flute=7, oboe=8, drums=9, clarinet=10, timpani=11, horns=12,
    brass=13, choir=14, keys=15,
)

# ---------------- 音色注册表: (bank, prog, 音区, pan, rev) ----------------
PROGS = {
    'piano':      (0, 0, (21, 108), 64, 70),
    'harp':       (0, 46, (28, 103), 100, 100),
    'celesta':    (0, 8, (60, 108), 46, 90),
    'glock':      (0, 9, (79, 108), 44, 88),
    'organ':      (0, 19, (36, 84), 64, 70),
    'church_bell':(8, 14, (48, 96), 64, 95),
    'vln1_slow': (21, 49, (55, 105), 34, 62), 'vln1_trem': (21, 44, (55, 105), 34, 62), 'vln1_pizz': (20, 45, (55, 105), 34, 55),
    'vln2_slow': (26, 49, (55, 100), 50, 62), 'vln2_trem': (26, 44, (55, 100), 50, 62), 'vln2_pizz': (25, 45, (55, 100), 50, 55),
    'vla_slow':  (31, 49, (48, 96),  62, 62), 'vla_trem':  (31, 44, (48, 96),  62, 62), 'vla_pizz':  (30, 45, (48, 96),  62, 55),
    'celli_slow':(41, 49, (36, 76),  80, 62), 'celli_trem':(41, 44, (36, 76),  80, 62), 'celli_pizz':(40, 45, (36, 76),  80, 55),
    'bass_slow': (51, 49, (28, 60),  74, 45), 'bass_pizz': (50, 45, (28, 60),  74, 45),
    'flute':    (17, 73, (60, 96),  52, 78),
    'oboe':     (17, 68, (58, 91),  58, 78),
    'clarinet': (17, 71, (50, 91),  62, 78),
    'bassoon':  (17, 70, (34, 65),  44, 70),
    'horn':     (17, 60, (41, 74),  66, 58),
    'trumpet':  (17, 56, (55, 93),  64, 52),
    'hmn_trumpet': (17, 59, (55, 93), 64, 52),
    'trombone': (17, 57, (40, 70),  64, 50),
    'tuba':     (17, 58, (26, 53),  64, 42),
    'choir':    (17, 52, (48, 91),  64, 85),
    'timpani':  (0, 47, (26, 60),   64, 40),
}


class Score:
    def __init__(self, humanize=True, seed=42):
        self.pending = []
        self.meta_msgs = []
        self.tracks = {}
        self.channel = {}
        self.range = {}
        self.chan_prog = {}
        self.track_pan = {}     # 音轨 -> (pan, rev)
        self._cc_last = {}      # (name, ctrl) -> (beat, val)
        self._cc_all = {}       # (name, ctrl) -> [(beat, val), ...]
        self._rng = random.Random(seed) if humanize else None

    # ---------- 注册与音色 ----------
    def add_instr(self, name, ch, bank=0, prog=0, lo=0, hi=127, pan=64, rev=60):
        assert name not in self.tracks, f'重复音轨: {name}'
        t = MidiTrack()
        self.tracks[name] = t
        self.channel[name] = ch
        self.range[name] = (lo, hi)
        self.track_pan[name] = (pan, rev)
        if ch not in self.chan_prog:
            self.prog(name, bank, prog, 0.0)

    def prog(self, name, bank, prog, beat):
        """切换音色:bank select + program change + 声像/混响(随音色走)"""
        ch = self.channel[name]
        if self.chan_prog.get(ch) != (bank, prog):
            self.chan_prog[ch] = (bank, prog)
            self._ev(name, beat, Message('control_change', channel=ch, control=0, value=(bank >> 7) & 0x7f))
            self._ev(name, beat, Message('control_change', channel=ch, control=32, value=bank & 0x7f))
            self._ev(name, beat, Message('program_change', channel=ch, program=prog))
        pan, rev = self.track_pan.get(name, (64, 60))
        self._ev(name, beat, Message('control_change', channel=ch, control=10, value=pan))
        self._ev(name, beat, Message('control_change', channel=ch, control=91, value=rev))

    # ---------- 事件 ----------
    def _ev(self, name, beat, msg):
        self.pending.append((name, beat, msg))

    def note(self, name, pitch, vel, beat, dur):
        if self._rng is not None:
            beat = max(0.0, beat + self._rng.uniform(-0.006, 0.006))
            vel = max(1, min(127, vel + self._rng.randint(-2, 2)))
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
        """CC 事件;CC11 自动在相邻节点间线性插值(整拍步进),消除阶梯感"""
        if ctrl == 11:
            key = (name, ctrl)
            prev = self._cc_last.get(key)
            if prev is not None:
                t0, v0 = prev
                known = self._cc_all.get(key, [])
                if beat - t0 > 1.0 and not any(t0 < b < beat for b, _ in known):
                    t = float(int(t0) + 1)
                    while t < beat:
                        f = (t - t0) / (beat - t0)
                        iv = int(round(v0 + (val - v0) * f))
                        self._ev(name, t, Message('control_change', channel=self.channel[name], control=ctrl, value=iv))
                        t += 1.0
            self._cc_last[key] = (beat, val)
            self._cc_all.setdefault(key, []).append((beat, val))
        self._ev(name, beat, Message('control_change', channel=self.channel[name], control=ctrl, value=val))

    def bend(self, name, semis, beat, dur, bend_time=0.25):
        """滑音:音符尾部 bend_time 秒内线性滑向 +semis 半音(推弦/滑弦),音尾复位。
        贝斯手的"手"感来源。semis 建议 1-3。"""
        ch = self.channel[name]
        start = beat + max(0.0, dur - bend_time)
        steps = max(3, int(bend_time * 10))
        target = min(8191, int(4096 * semis))  # 有符号 pitch -8192..8191;4096 = +1 半音
        for i in range(steps + 1):
            f = i / steps
            v = int(round(target * f))
            self._ev(name, start + bend_time * f, Message('pitchwheel', channel=ch, pitch=v))
        self._ev(name, beat + dur + 0.03, Message('pitchwheel', channel=ch, pitch=0))

    def tempo(self, bpm, beat):
        self.meta_msgs.append((beat, MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm))))

    def tempo_ramp(self, bpm0, bpm1, beat0, beat1, steps=6):
        """速度渐变:beat0→beat1 线性插值(steps 段),避免硬切。"""
        for i in range(steps + 1):
            f = i / steps
            bpm = bpm0 + (bpm1 - bpm0) * f
            self.tempo(bpm, beat0 + (beat1 - beat0) * f)

    def meter(self, num, den, beat):
        self.meta_msgs.append((beat, MetaMessage('time_signature', numerator=num, denominator=den)))

    # ---------- 织体助手 ----------
    def arp(self, name, pitches, vel, beat, dur_each, loop=1, gap=0.0):
        t = beat
        for _ in range(loop):
            for i, p in enumerate(pitches):
                self.note(name, p, vel, t, dur_each * 0.9)
                t += dur_each
            t += gap

    def ostinato(self, name, pattern, vel, beat, loops=1):
        t = beat
        for _ in range(loops):
            for p, d in pattern:
                if p:
                    self.note(name, p, vel, t, d * 0.92)
                t += d
        return t

    def roll(self, name, pitch, v0, v1, start, end, step=0.25):
        t = start
        while t < end:
            f = (t - start) / max(end - start, 1e-9)
            v = int(v0 + (v1 - v0) * f)
            self.note(name, pitch, v, t, step * 0.8)
            t += step

    # ---------- 冲刷与自检 ----------
    def flush(self, path, verbose=True):
        meta = MidiTrack()
        meta.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
        prev = 0
        for beat, msg in sorted(self.meta_msgs, key=lambda x: x[0]):
            tick = int(round(beat * TPB))
            msg.time = tick - prev
            prev = tick
            meta.append(msg)
        meta.append(MetaMessage('end_of_track', time=0))
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
        import collections
        by_ch = collections.defaultdict(list)
        for name, beat, msg in self.pending:
            by_ch[self.channel[name]].append((beat, name, msg))
        issues = 0
        for ch in sorted(by_ch):
            evs = sorted(by_ch[ch], key=lambda x: x[0])
            # 预配对:每个 (note, on_beat) 的结束拍(人性化抖动下仍按 FIFO 配对)
            off_at = {}
            queues = collections.defaultdict(list)
            for beat, name, msg in evs:
                if msg.type == 'note_on' and msg.velocity > 0:
                    queues[msg.note].append(beat)
                elif msg.type == 'note_off':
                    q = queues.get(msg.note)
                    if q:
                        off_at[(msg.note, q.pop(0))] = beat
            on = {}
            for beat, name, msg in evs:
                if msg.type == 'note_on' and msg.velocity > 0:
                    if msg.note in on:
                        ob = off_at.get((msg.note, on[msg.note][1]), beat)
                        if ob - beat > 0.025:      # 真重叠(>25ms 才报,容忍抖动邻接)
                            print(f'  [冲突] ch{ch} {msg.note} 重叠 {ob - beat:.3f}拍: {on[msg.note][0]}@{on[msg.note][1]:.2f} vs {name}@{beat:.2f}')
                            issues += 1
                    on[msg.note] = (name, beat)
                elif msg.type == 'note_off':
                    if msg.note in on and on[msg.note][0] == name:
                        del on[msg.note]
                elif msg.type == 'program_change':
                    # 仅报"真正被切"的音:既非切换前 0.05 拍内新起(新段首音抖动),
                    # 也非 0.05 拍内即将结束(旧段尾音抖动)
                    real = {p: (nm, bt) for p, (nm, bt) in on.items()
                            if bt <= beat - 0.05 and off_at.get((p, bt), beat) > beat + 0.05}
                    if real:
                        for p, (nm, bt) in sorted(real.items()):
                            print(f'  [切换冲突] ch{ch} @{beat:.2f} 切音色时 {nm} 的 {p} 仍在响(延至 {off_at.get((p, bt), beat):.2f})')
                        issues += 1
                        on.clear()
        print(f'saved {path}  (自检完成,冲突 {issues} 处)')
        return issues
