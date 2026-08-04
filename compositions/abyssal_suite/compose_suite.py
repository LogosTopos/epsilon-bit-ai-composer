#!/usr/bin/env python3
"""compose_suite.py — 《深渊四章》组曲总装:合并四乐章为单曲 + 渲染 + 压码

用法:
  python3 compose_suite.py                # 生成各乐章 MIDI + 组曲 MIDI
  python3 compose_suite.py --render       # 加渲染 WAV
  python3 compose_suite.py --mp3          # 加压 MP3(峰值管理 + limiter)
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SF2 = os.path.join(ROOT, 'soundfonts', 'MuseScore_General.sf2')

MOVEMENTS = [
    ('Mvmt1_Descent.mid', 'mvmt1_descent.py'),
    ('Mvmt2_Coruscation.mid', 'mvmt2_coruscation.py'),
    ('Mvmt3_Slumber.mid', 'mvmt3_slumber.py'),
    ('Mvmt4_Awakening.mid', 'mvmt4_awakening.py'),
]
GAP_S = 2.0


def gen_movements():
    for mid_name, py in MOVEMENTS:
        if not os.path.exists(mid_name):
            print(f'生成 {mid_name} ...')
            subprocess.run([sys.executable, py], cwd=HERE, check=True)
        else:
            print(f'复用 {mid_name}')


def concat_midis(paths, out):
    import mido
    from mido import MidiTrack
    files = [mido.MidiFile(p) for p in paths]
    tpb = files[0].ticks_per_beat
    offset = 0
    out_tracks = []
    for f in files:
        last_abs = 0
        for track in f.tracks:
            new_track = MidiTrack()
            prev = 0
            abs_t = 0
            for msg in track:
                abs_t += msg.time
                target = abs_t + offset
                m = msg.copy()
                m.time = target - prev
                prev = target
                new_track.append(m)
                last_abs = max(last_abs, target)
            out_tracks.append(new_track)
        # 2 秒休止:按该乐章结尾 tempo 换算 tick
        tempo = 500000
        for t in f.tracks[0]:
            if t.type == 'set_tempo':
                tempo = t.tempo
        gap_ticks = int(GAP_S * 1000000 / tempo * tpb)
        offset = last_abs + gap_ticks
    mid = mido.MidiFile(ticks_per_beat=tpb)
    mid.tracks = out_tracks
    mid.save(out)
    # 总时长:按全曲结尾 tempo 换算
    tempo = 500000
    for t in out_tracks[0]:
        if t.type == 'set_tempo':
            tempo = t.tempo
    dur_s = offset / tpb * tempo / 1e6
    print(f'组曲已保存: {out} ({len(out_tracks)} 轨, 总长 {int(dur_s // 60)}:{int(dur_s % 60):02d})')


def render(mid, wav, gain='1.2'):
    print(f'渲染 {mid} → {wav}')
    subprocess.run(['fluidsynth', '-F', wav, '-r', '44100', '-R', '0.9', '-C', '0',
                    '-g', gain, SF2, mid], check=True, stdout=subprocess.DEVNULL)


def master(wav, mp3):
    """峰值管理:volumedetect → 提升到 -1.2 dB → alimiter 保护"""
    r = subprocess.run(['ffmpeg', '-i', wav, '-af', 'volumedetect', '-f', 'null', '-'],
                       capture_output=True, text=True)
    max_db = None
    for line in r.stderr.splitlines():
        if 'max_volume' in line:
            max_db = float(line.split('max_volume:')[1].split('dB')[0].strip())
    boost = round(-1.2 - max_db, 1)
    print(f'峰值 {max_db:+.1f} dB → 补偿 {boost:+.1f} dB')
    subprocess.run(['ffmpeg', '-y', '-i', wav,
                    '-af', f'volume={boost}dB,alimiter=limit=0.95',
                    '-codec:a', 'libmp3lame', '-q:a', '2', mp3], check=True)


def main():
    ap = argparse.ArgumentParser(description='《深渊四章》组曲总装')
    ap.add_argument('--render', action='store_true', help='渲染 WAV')
    ap.add_argument('--mp3', action='store_true', help='压 MP3(隐含渲染)')
    ap.add_argument('--regen', action='store_true', help='强制重新生成 MIDI')
    args = ap.parse_args()

    gen_movements()
    mid_paths = [os.path.join(HERE, n) for n, _ in MOVEMENTS]
    suite_mid = os.path.join(HERE, 'Suite_of_the_Deep.mid')
    concat_midis(mid_paths, suite_mid)

    if args.render or args.mp3:
        for mid_name, _ in MOVEMENTS:
            wav = os.path.join(HERE, mid_name.replace('.mid', '.wav'))
            render(os.path.join(HERE, mid_name), wav)
        suite_wav = os.path.join(HERE, 'Suite_of_the_Deep.wav')
        render(suite_mid, suite_wav)
    if args.mp3:
        for mid_name, _ in MOVEMENTS:
            wav = os.path.join(HERE, mid_name.replace('.mid', '.wav'))
            mp3 = os.path.join(HERE, mid_name.replace('.mid', '.mp3'))
            master(wav, mp3)
        master(os.path.join(HERE, 'Suite_of_the_Deep.wav'),
               os.path.join(HERE, 'Suite_of_the_Deep.mp3'))


if __name__ == '__main__':
    main()
