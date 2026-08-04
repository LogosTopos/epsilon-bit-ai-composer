#!/usr/bin/env python3
"""verify_render.py — 渲染链路通用验证工具

生成时:核对 MIDI 声部(每通道音色/音符数/主旋律与低音音符序列)
渲染后:分段 RMS 响度曲线 + 峰值检查(用 wave/audioop,无需额外依赖)

用法:
  python3 scripts/verify_render.py --mid compositions/nameless_abyss/The_Nameless_Abyss.mid \
      --audio compositions/nameless_abyss/The_Nameless_Abyss_v2.wav \
      --segments "0-26:引子,26-89:A段,89-126:B段,126-168:高潮,168-196:尾声"
"""
import argparse
import audioop
import math
import wave

import mido

GM = {0: 'Acoustic Grand Piano', 1: 'Bright Acoustic Piano', 8: 'Celesta',
      10: 'Music Box', 32: 'Acoustic Bass', 43: 'Contrabass', 46: 'Orchestral Harp',
      48: 'String Ensemble 1', 49: 'String Ensemble 2', 52: 'Choir Aahs',
      53: 'Voice Oohs', 89: 'Pad 2 (warm)'}
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def check_midi(path, melody_ch=0, bass_ch=6, max_notes=60):
    mid = mido.MidiFile(path)
    print(f'=== MIDI: {path} ===')
    print(f'格式 {mid.type}, {len(mid.tracks)} 轨, {mid.ticks_per_beat} TPB')
    tempo = None
    for t in mid.tracks[0]:
        if t.type == 'set_tempo':
            tempo = t.tempo
    if tempo:
        print(f'tempo: {tempo} ({mido.tempo2bpm(tempo):.0f} BPM)')
    # 每轨:通道、音色、音符数
    for i, track in enumerate(mid.tracks):
        chs = {}
        prog = {}
        notes = 0
        for m in track:
            if m.type == 'program_change':
                prog[m.channel] = m.program
            if m.type == 'note_on' and m.velocity > 0:
                notes += 1
        desc = ', '.join(f'ch{c}:{GM.get(p, p)}' for c, p in sorted(prog.items()))
        print(f'  轨{i}: {notes:4d} 音符  [{desc}]')
    # 主旋律与低音核对
    def dump(ch, label):
        ons = []
        for track in mid.tracks:
            for m in track:
                if m.type == 'note_on' and m.velocity > 0 and m.channel == ch:
                    ons.append(m.note)
        print(f'--- {label} (ch{ch}) 前 {min(max_notes, len(ons))} 音:')
        print('   ' + ' '.join(f'{NOTE_NAMES[n % 12]}{n // 12 - 1}' for n in ons[:max_notes]))
    dump(melody_ch, '主旋律')
    dump(bass_ch, '低音')
    return mid


def check_audio(path, segments):
    w = wave.open(path)
    rate = w.getframerate()
    n = w.getnframes()
    dur = n / rate
    sw = w.getsampwidth()
    print(f'=== 音频: {path} ===')
    print(f'时长 {dur:.1f}s, {rate}Hz, {w.getnchannels()}ch, {sw * 8}bit')
    if segments:
        print(f'{"时间":<14}{"段落":<16}{"RMS":>8}  {"dB":>7}')
        for s, e, name in segments:
            s = min(s, dur); e = min(e, dur)
            w.setpos(int(s * rate))
            data = w.readframes(int((e - s) * rate))
            rms = audioop.rms(data, sw) / (2 ** (sw * 8) - 1)
            db = 20 * math.log10(rms) if rms > 0 else -99
            print(f'{s:>5.0f}-{e:<7.0f}{name:<16}{rms:>8.4f}  {db:>+6.1f}dB')
    # 峰值
    w.setpos(0)
    data = w.readframes(n)
    peak = audioop.max(data, sw) / (2 ** (sw * 8) - 1)
    print(f'峰值: {20 * math.log10(peak):+.1f} dB (建议 ≈ -1.0 dB,留余量防削波)')


def main():
    ap = argparse.ArgumentParser(description='渲染链路验证:声部核对 + RMS 分段 + 峰值')
    ap.add_argument('--mid', required=True, help='MIDI 文件')
    ap.add_argument('--audio', help='渲染的 WAV 文件(可选)')
    ap.add_argument('--segments', default='',
                    help='RMS 分段,如 "0-26:引子,26-89:A段"(可选)')
    ap.add_argument('--melody-ch', type=int, default=0)
    ap.add_argument('--bass-ch', type=int, default=6)
    args = ap.parse_args()
    check_midi(args.mid, args.melody_ch, args.bass_ch)
    if args.audio:
        segs = []
        if args.segments:
            for part in args.segments.split(','):
                rng, name = part.split(':')
                s, e = rng.split('-')
                segs.append((float(s), float(e), name))
        check_audio(args.audio, segs)


if __name__ == '__main__':
    main()
