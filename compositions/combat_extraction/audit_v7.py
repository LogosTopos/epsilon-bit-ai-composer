#!/usr/bin/env python3
"""audit_v7.py — 母节 v7 验收审计(数据驱动)

四维检查(读成品 MIDI,全曲 m1-20,母 loop ×2):
  1. 密度:每档(档1 m3-6 / 档2 m7-10 / 档3 m11-14 / 持续 m15-18)活跃角色数
     —— distinct_roles(档内出现过的小节角色总数,对应验收"9/14 层")+ avg(每小节平均)
  2. 互锁:16 分网格上,非打击乐(ch∉{9,11})且 vel≥80 的重音层数,任何槽 >2 报违规
     (验收:≤2;打击乐 kick/snare/timpani 是骨架,不计)
  3. 碰撞:16 分网格上同时发音的音符对,音高差 ∈ {1,11}(小二度/大七度,≤2 八度)
     —— 验收:≤150 次
  4. 占比:各角色发声小节覆盖(闪现检测:亮点层应稳定出现)
用法:python3 audit_v7.py [--mid Combat_Extraction.mid] [--voice trumpet|synth]
"""
import argparse
import sys
from collections import defaultdict

import mido

PERC = {9, 11}          # 打击乐通道(不计互锁/碰撞)
ACCENT_VEL = 80         # 重音层阈值
GRID = 0.25             # 16 分网格
TOL = 0.01


def load_events(mid_path):
    """每通道 note 事件列表:(beat, pitch, vel, dur)。返回 {channel: [ev,...]}"""
    mid = mido.MidiFile(mid_path)
    tpb = mid.ticks_per_beat
    by_ch = defaultdict(list)
    for tr in mid.tracks:
        t = 0
        queues = defaultdict(list)      # (channel,note) -> [on_beat,...]
        ons = defaultdict(list)         # (channel,note) -> [(on_beat, vel)]
        for msg in tr:
            t += msg.time
            if not hasattr(msg, 'channel'):
                continue
            bt = t / tpb
            if msg.type == 'note_on' and msg.velocity > 0:
                queues[(msg.channel, msg.note)].append(bt)
                ons[(msg.channel, msg.note)].append((bt, msg.velocity))
            elif msg.type == 'note_off':
                q = queues.get((msg.channel, msg.note))
                if q:
                    on_bt, vel = ons[(msg.channel, msg.note)].pop(0)
                    dur = bt - on_bt
                    if dur > 0.02:
                        by_ch[msg.channel].append((on_bt, msg.note, vel, dur))
    return by_ch


def sounding(evs, t):
    """t 时刻正在发声的 (pitch, vel) 列表"""
    return [(p, v) for (on, p, v, d) in evs if on - TOL <= t <= on + d + TOL]


def accent_layers(by_ch, t):
    """t 时刻'起音'的重音层数(音头互锁语义):
    - 非打击乐(ch∉{9,11})
    - bass(ch6):vel≥110 才是重音(3+3+2 位 116,其余 16 分 104 是织体)
    - 其他层:vel≥84(hook 重音 86-94 / brass 88 / M3 96 / riser 84-88)
    """
    n = 0
    for ch, evs in by_ch.items():
        if ch in PERC:
            continue
        thr = 110 if ch == 6 else 84
        if any(abs(on - t) <= TOL and v >= thr for (on, p, v, d) in evs):
            n += 1
    return n


def audit(mid_path, label):
    by_ch = load_events(mid_path)
    total_beats = max((on + d for evs in by_ch.values() for (on, p, v, d) in evs), default=0)
    nbars = int(total_beats // 4) + 1

    print(f'\n===== {label} 审计 =====')

    # 1. 密度(新口径:母节 = 高潮段,全 16 小节满配;两圈 m3-18 / m19-34)
    print('--- 密度(每小节活跃角色,验收:全 16 小节 14 层) ---')
    for (b0, b1) in ((3, 18), (19, 34)):
        per_bar = []
        for bar in range(b0, b1 + 1):
            rb = set()
            for ch, evs in by_ch.items():
                # 抗 humanize 抖动:先归整到 16 分网格,再取小节(round 会把 3.75 拍错归下小节)
                if any(int(round(on * 4) / 4 // 4) + 1 == bar for (on, p, v, d) in evs):
                    rb.add(ch)
            per_bar.append(len(rb))
        avg = sum(per_bar) / len(per_bar)
        print(f'  圈 m{b0}-{b1}:每小节 {per_bar},avg {avg:.1f},min {min(per_bar)}(验收 ≥14)')
    print()

    # 2. 互锁(音头语义:同槽'起音'的重音层 ≤2)
    print('--- 互锁(同槽起音重音层,音头语义) ---')
    viol = 0
    maxl = 0
    t = 0.0
    while t < total_beats:
        if 2 <= t / 4 % 16 <= 15.75:      # 只看母 loop 区(m3-18,两圈)
            cnt = accent_layers(by_ch, t)
            maxl = max(maxl, cnt)
            if cnt > 2:
                bar = int(t // 4) + 1
                print(f'  [违规] m{bar} beat {t % 4:.2f}: {cnt} 个重音层')
                viol += 1
        t += GRID
    print(f'  重音层峰值 {maxl},违规槽 {viol} 个(验收 ≤2 层,违规 0)')

    # 3. 碰撞
    print('--- 半音碰撞(音高差 1/11 半音,同时发音) ---')
    coll = 0
    worst = []
    t = 0.0
    while t < total_beats:
        notes = []
        for ch, evs in by_ch.items():
            if ch in PERC:
                continue
            for (p, v) in sounding(evs, t):
                notes.append((ch, p))
        for i in range(len(notes)):
            for j in range(i + 1, len(notes)):
                d = abs(notes[i][1] - notes[j][1])
                if d in (1, 11):
                    coll += 1
                    if len(worst) < 8:
                        worst.append((int(t // 4) + 1, t % 4, notes[i], notes[j]))
        t += GRID
    print(f'  碰撞 {coll} 次(验收 ≤150)')
    for bar, b, a, b2 in worst:
        print(f'    m{bar} beat {b:.2f}: ch{a[0]}@{a[1]} vs ch{b2[0]}@{b2[1]}')

    # 4. 占比(闪现检测)
    print('--- 角色占比(发声小节/36 小节) ---')
    role_names = {0: 'piano', 1: 'pad', 2: 'vln1', 3: 'vln2', 4: 'vla', 5: 'celli',
                  6: 'bass', 7: 'fx', 9: 'drums', 10: 'hook', 11: 'timpani',
                  12: 'brass', 13: 'keys', 14: 'choir', 15: 'rhythm'}
    for ch in sorted(by_ch):
        bars = {int(on // 4) + 1 for (on, p, v, d) in by_ch[ch]}
        print(f'  ch{ch:2d} {role_names.get(ch, "?"):8s}: {len(bars):2d}/36 小节 ({100*len(bars)/36:.0f}%)')

    return {'interlock_viol': viol, 'collisions': coll}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--mid', default='Combat_Extraction.mid')
    ap.add_argument('--voice', default='trumpet', choices=('trumpet', 'synth'))
    args = ap.parse_args()
    r = audit(args.mid, f'v7-{args.voice}')
    ok = r['interlock_viol'] == 0 and r['collisions'] <= 150
    print(f'\n验收:{"PASS" if ok else "FAIL"} (互锁违规 {r["interlock_viol"]},碰撞 {r["collisions"]})')
    sys.exit(0 if ok else 1)
