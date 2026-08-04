#!/usr/bin/env python3
"""mix_stems.py — 《搜打撤》战斗曲 stem 混音

通道组:drums(9,11)/bass(6)/strings(2-5)/stab(10,12)/atmosphere(0,1,13,14)
混音链(战斗曲激进版):
- drums:瞬态压缩(收住 GUGS Power 鼓组的尖峰)
- bass:highpass + **sidechain(以鼓为 key,鼓点让位 → 冲击感)**
- strings:低切 + 平衡
- stab:吉他/铜管中高频,轻微压缩
- atmosphere:弱化(垫底)
- 总线:glue 压缩 + alimiter + 峰值补偿
用法:python3 mix_stems.py [--out 成品.wav] [--render-stems]
"""
import argparse
import audioop
import hashlib
import math
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SF2S = ['../../soundfonts/MuseScore_General.sf2', '../../soundfonts/Rock_GeneralUser_GS_v1.471.sf2']

STEMS = [
    ('drums',      [9, 11]),
    ('bass',       [6]),
    ('strings',    [2, 3, 4, 5]),
    ('stab',       [10, 12, 7, 15]),   # v7:hook/brass + fx(7) + synth_rhythm(15)
    ('atmosphere', [0, 1, 13, 14]),
]

# 混音链(v8.1 贝斯可听性,用户反馈:听不见贝斯手)
# 关键修复:sidechain 从'抽干式'(threshold 0.03/ratio 8)改为'温柔让位'
# (0.08/3)——bass 重音与 kick 同拍,旧参数把 bass 最重要音符全压掉了
CHAIN = {
    'drums':      'acompressor=threshold=-18dB:ratio=3:attack=5:release=100,volume=1.28',
    # bass:中低频峰提升(110Hz +3dB,音高可辨)+ 音量 1.65(主角)
    'bass':       'highpass=f=30,equalizer=f=110:t=q:w=1:g=3,volume=1.65',
    'strings':    'highpass=f=60,volume=0.75',
    'stab':       'acompressor=threshold=-26dB:ratio=2:attack=10:release=150,volume=0.95',  # v9:更柔,完全辅助
    'atmosphere': 'volume=0.7',
}


def split_stems(mid_path, out_dir):
    import mido
    mid = mido.MidiFile(mid_path)
    meta = mid.tracks[0]
    by_group = {name: [] for name, _ in STEMS}
    for t in mid.tracks[1:]:
        chans = {m.channel for m in t if hasattr(m, 'channel')}
        assert len(chans) == 1, f'多通道轨 {chans}'
        ch = chans.pop()
        for name, chans2 in STEMS:
            if ch in chans2:
                by_group[name].append(t)
                break
    paths = {}
    for name, _ in STEMS:
        out = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)
        out.tracks.append(meta)
        for t in by_group[name]:
            out.tracks.append(t)
        p = os.path.join(out_dir, f'stem_{name}.mid')
        out.save(p)
        paths[name] = p
    return paths


def _sf_sig():
    """音色库签名(内容哈希,库文件变更 → 全部重渲染)。"""
    h = hashlib.sha256()
    for p in SF2S:
        try:
            with open(p, 'rb') as f:
                h.update(f.read())
        except FileNotFoundError:
            h.update(p.encode())
    return h.hexdigest()


def _stale(mid_path, wav_path):
    """增量缓存判定:mid 内容 + 音色库签名一致且 wav 存在 → 不重渲染。
    (E Agent 审计:旧逻辑只看 wav 是否存在,而 build.sh 总是 rm,缓存形同虚设;
    双版仅 stab 组不同 → 第二版只重渲染 1/5,实测省 75%)"""
    if not os.path.exists(wav_path):
        return True
    h = hashlib.sha256(open(mid_path, 'rb').read() + _sf_sig().encode()).hexdigest()
    hp = wav_path + '.hash'
    try:
        return open(hp).read().strip() != h
    except FileNotFoundError:
        return True


def render(src_mid, out_wav):
    cmd = ['fluidsynth', '-F', out_wav, '-r', '44100', '-R', '0.9', '-C', '0', '-g', '1.2']
    cmd += SF2S + [src_mid]
    subprocess.run(cmd, check=True, capture_output=True)
    verify_wav(out_wav, src_mid)   # 渲染校验门(链路 v2):非空/时长/未削波


def verify_wav(wav_path, src_mid=None):
    """渲染校验门:文件非空、时长下限、未削波。失败即抛异常(防坏成品进交付)。"""
    import wave as _wave
    with _wave.open(wav_path, 'rb') as w:
        n = w.getnframes()
        rate = w.getframerate()
        sw = w.readframes(min(n, 44100 * 30))   # 峰值只需采样头 30s
        p = audioop.max(sw, 2) / 32768.0 if sw else 0.0
    dur = n / rate
    assert n > 44100, f'校验失败: {wav_path} 渲染为空/过短({dur:.1f}s)'
    if src_mid:
        import mido
        mid = mido.MidiFile(src_mid)
        tpb = mid.ticks_per_beat
        last = 0.0
        for tr in mid.tracks:
            t = 0
            for m in tr:
                t += m.time
                if m.type in ('note_on', 'note_off'):
                    last = max(last, t)
        expected = last / tpb / 168 * 60 * 0.9   # 保守:按 168BPM 估算,0.9 容差
        assert dur >= expected, f'校验失败: {wav_path} 时长 {dur:.1f}s < 预期 {expected:.1f}s'
    assert p < 0.99, f'校验失败: {wav_path} 采样峰值 {p*100:.0f}% 接近削波'
    return dur


def mix(out_wav, stem_dir='stems'):
    inputs = []
    flt = []
    for i, (name, _) in enumerate(STEMS):
        inputs += ['-i', f'{stem_dir}/stem_{name}.wav']
        flt.append(f'[{i}:a]{CHAIN[name]}[s{i}]')
    # bass 以 drums 为 key 做 sidechain(温柔让位:threshold 0.08/ratio 3/attack 8ms——
    # 不再抽干 bass 重音;鼓点保留冲击但 bass 音头可过)
    flt.append('[s1][s0]sidechaincompress=threshold=0.08:ratio=3:attack=8:release=120[bass_sc]')
    others = ''.join(f'[s{i}]' for i in range(len(STEMS)) if i != 1)
    flt.append(f'[bass_sc]{others}amix=inputs={len(STEMS)}:normalize=0[mix]')
    flt.append('[mix]acompressor=threshold=-16dB:ratio=2:attack=10:release=200,alimiter=limit=0.95[out]')
    cmd = (['ffmpeg', '-y', '-loglevel', 'error'] + inputs +
           ['-filter_complex', ';'.join(flt), '-map', '[out]', '-c:a', 'pcm_s16le', out_wav])
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mid', default='Combat_Extraction.mid')
    ap.add_argument('--out', default='stems/_mix.wav')
    ap.add_argument('--render-stems', action='store_true')
    args = ap.parse_args()
    os.makedirs('stems', exist_ok=True)
    if args.render_stems:
        # 增量缓存按 mid 分目录(stems/<midbase>/):同一 mid 二次构建命中,
        # 不同 mid 互不驱逐(旧版共用 stem_*.wav 会互相覆盖,缓存形同虚设)
        midbase = os.path.splitext(os.path.basename(args.mid))[0]
        cache_dir = os.path.join('stems', midbase)
        os.makedirs(cache_dir, exist_ok=True)
        paths = split_stems(args.mid, cache_dir)
        # 增量缓存 + 并行渲染(E Agent 审计:串行→并行实测 2.46×,md5 逐字节一致)
        todo = [(name, wav, mid) for name, mid in paths.items()
                for wav in [os.path.join(cache_dir, f'stem_{name}.wav')]
                if _stale(mid, wav)]
        for name, _, _ in todo:
            print(f'渲染 {name}...')

        def _render(item):
            name, wav, mid = item
            render(mid, wav)
            h = hashlib.sha256(open(mid, 'rb').read() + _sf_sig().encode()).hexdigest()
            open(wav + '.hash', 'w').write(h)
        if todo:
            with ThreadPoolExecutor(max_workers=5) as ex:
                list(ex.map(_render, todo))
        else:
            print('  (全部命中增量缓存,跳过渲染)')
    else:
        midbase = os.path.splitext(os.path.basename(args.mid))[0]
        cache_dir = os.path.join('stems', midbase)
    mix(args.out, stem_dir=cache_dir)
    # 混音后校验:非静音(RMS 区间)/未削波
    import wave as _wave
    with _wave.open(args.out, 'rb') as w:
        sw = w.readframes(w.getnframes())
    rms = 20 * math.log10(max(audioop.rms(sw, 2) / 32768.0, 1e-9))
    pk = 20 * math.log10(max(audioop.max(sw, 2) / 32768.0, 1e-9))
    assert -40 < rms < -5, f'混音校验失败: RMS {rms:.1f}dB 异常(静音或过载)'
    assert pk < 0, f'混音校验失败: 峰值 {pk:.1f}dB 削波'
    dur = len(sw) // 4 / 44100              # 16-bit 双声道:4 bytes/frame
    print(f'混音完成: {args.out}  RMS {rms:.1f} dB  峰值 {pk:.1f} dB  {dur:.1f}s')


if __name__ == '__main__':
    main()
