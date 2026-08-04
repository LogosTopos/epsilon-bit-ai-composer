# Undertale - Megalovania

- 社区扒谱来源：https://www.vgmusic.com/file/e84eb434ddd44a792ec9f6e837f904b6.html
- Sequenced by: Jay Reichard
- MIDI tracks: 15
- Notes: 8784
- Duration: 312.0s / 624.0 beats
- Estimated key: D minor
- Common tempo BPM: [(120.0, 2)]
- Role counts: {'lead_or_counter': 10, 'bass': 2, 'drums': 3}

## 分层观察

- Staff-5: role=lead_or_counter, notes=160, density/4bar=1.7, range=[70, 86], median_vel=127.0, fast4=42
- Staff-13: role=lead_or_counter, notes=64, density/4bar=0.48, range=[57, 77], median_vel=110.0, fast4=12
- Staff: role=lead_or_counter, notes=640, density/4bar=4.1, range=[46, 62], median_vel=110.0, fast4=177
- Staff-9: role=lead_or_counter, notes=60, density/4bar=0.59, range=[74, 91], median_vel=110.0, fast4=0
- Staff-8: role=lead_or_counter, notes=136, density/4bar=1.33, range=[70, 86], median_vel=110.0, fast4=32
- Staff-7: role=lead_or_counter, notes=68, density/4bar=0.72, range=[70, 86], median_vel=75.0, fast4=2
- Staff-10: role=lead_or_counter, notes=480, density/4bar=4.07, range=[53, 85], median_vel=127.0, fast4=256
- Staff-11: role=lead_or_counter, notes=160, density/4bar=1.36, range=[50, 77], median_vel=127.0, fast4=52
- Staff-12: role=lead_or_counter, notes=40, density/4bar=0.3, range=[46, 53], median_vel=108.0, fast4=0
- Staff-6: role=bass, notes=3168, density/4bar=21.12, range=[34, 58], median_vel=110.0, fast4=1728
- Staff-1: role=bass, notes=1288, density/4bar=8.59, range=[34, 51], median_vel=110.0, fast4=64
- Staff-3: role=drums, notes=488, density/4bar=3.25, range=[None, None], median_vel=110.0, fast4=0
- Staff-4: role=drums, notes=616, density/4bar=4.11, range=[None, None], median_vel=75.0, fast4=0
- Staff-2: role=drums, notes=1416, density/4bar=9.44, range=[None, None], median_vel=110.0, fast4=0

## 抽象重复细胞

- track=Staff-5, count=16, contour=['same', 'up', 'down'], ioi=['sixteenth', 'sixteenth', 'eighth'], dur=['sixteenth', 'sixteenth', 'sixteenth', 'sixteenth'], intervals=(0, 12, -5), first_beat=32.0
- track=Staff-5, count=16, contour=['up', 'down', 'step'], ioi=['sixteenth', 'eighth', 'quarter'], dur=['sixteenth', 'sixteenth', 'sixteenth', 'sixteenth'], intervals=(12, -5, -1), first_beat=32.25
- track=Staff-13, count=8, contour=['up', 'down', 'up'], ioi=['very_fast', 'eighth', 'very_fast'], dur=['eighth', 'eighth', 'eighth', 'eighth'], intervals=(12, -8, 12), first_beat=217.75
- track=Staff-13, count=8, contour=['up', 'down', 'up'], ioi=['very_fast', 'sixteenth', 'very_fast'], dur=['sixteenth', 'sixteenth', 'sixteenth', 'sixteenth'], intervals=(12, -9, 12), first_beat=219.25
- track=Staff, count=64, contour=['same', 'up', 'down'], ioi=['sixteenth', 'sixteenth', 'eighth'], dur=['sixteenth', 'sixteenth', 'sixteenth', 'sixteenth'], intervals=(0, 12, -5), first_beat=0.0
- track=Staff, count=64, contour=['up', 'down', 'step'], ioi=['sixteenth', 'eighth', 'quarter'], dur=['sixteenth', 'sixteenth', 'sixteenth', 'sixteenth'], intervals=(12, -5, -1), first_beat=0.25
- track=Staff-9, count=4, contour=['same', 'same', 'same'], ioi=['eighth', 'sixteenth', 'eighth'], dur=['eighth', 'sixteenth', 'sixteenth', 'sixteenth'], intervals=(0, 0, 0), first_beat=80.0
- track=Staff-9, count=4, contour=['down', 'step', 'step'], ioi=['eighth', 'eighth', 'eighth'], dur=['eighth', 'eighth', 'eighth', 'eighth'], intervals=(-5, -2, -2), first_beat=88.0
- track=Staff-8, count=4, contour=['same', 'same', 'same'], ioi=['sixteenth', 'eighth', 'eighth'], dur=['sixteenth', 'sixteenth', 'sixteenth', 'eighth'], intervals=(0, 0, 0), first_beat=64.5
- track=Staff-8, count=4, contour=['same', 'same', 'down'], ioi=['eighth', 'eighth', 'eighth'], dur=['sixteenth', 'sixteenth', 'eighth', 'sixteenth'], intervals=(0, 0, -3), first_beat=64.75

## 快速四音节候选

- track=Staff-5, start=35.25, span=1.0, contour=['up', 'step', 'down'], intervals=[3, 2, -7], vel=127.0
- track=Staff-5, start=35.5, span=1.0, contour=['step', 'down', 'same'], intervals=[2, -7, 0], vel=127.0
- track=Staff-5, start=35.75, span=1.0, contour=['down', 'same', 'up'], intervals=[-7, 0, 12], vel=127.0
- track=Staff-5, start=39.25, span=1.0, contour=['up', 'step', 'down'], intervals=[3, 2, -8], vel=127.0
- track=Staff-5, start=39.5, span=1.0, contour=['step', 'down', 'same'], intervals=[2, -8, 0], vel=127.0
- track=Staff-13, start=219.25, span=0.5, contour=['up', 'down', 'up'], intervals=[12, -9, 12], vel=110.0
- track=Staff-13, start=219.25, span=0.75, contour=['down', 'up', 'down'], intervals=[-9, 12, -10], vel=110.0
- track=Staff-13, start=219.5, span=0.5, contour=['up', 'down', 'up'], intervals=[12, -10, 12], vel=110.0
- track=Staff-13, start=223.25, span=0.5, contour=['up', 'down', 'up'], intervals=[12, -9, 12], vel=110.0
- track=Staff-13, start=223.25, span=0.75, contour=['down', 'up', 'down'], intervals=[-9, 12, -10], vel=110.0
- track=Staff, start=3.25, span=1.0, contour=['up', 'step', 'down'], intervals=[3, 2, -7], vel=110.0
- track=Staff, start=3.5, span=1.0, contour=['step', 'down', 'same'], intervals=[2, -7, 0], vel=110.0

## 4小节密度

- block 1: notes=40, tonal=40, drums=0, active_tracks=1, median_pitch=54.0
- block 2: notes=82, tonal=80, drums=2, active_tracks=4, median_pitch=47.5
- block 3: notes=340, tonal=263, drums=77, active_tracks=8, median_pitch=47.0
- block 4: notes=341, tonal=264, drums=77, active_tracks=9, median_pitch=47.0
- block 5: notes=276, tonal=199, drums=77, active_tracks=7, median_pitch=43.0
- block 6: notes=311, tonal=234, drums=77, active_tracks=7, median_pitch=45.0
- block 7: notes=325, tonal=248, drums=77, active_tracks=6, median_pitch=46.0
- block 8: notes=325, tonal=248, drums=77, active_tracks=7, median_pitch=46.0
- block 9: notes=325, tonal=248, drums=77, active_tracks=6, median_pitch=46.0
- block 10: notes=325, tonal=248, drums=77, active_tracks=7, median_pitch=46.0
- block 11: notes=121, tonal=45, drums=76, active_tracks=5, median_pitch=35.0
- block 12: notes=121, tonal=45, drums=76, active_tracks=5, median_pitch=38.0
- block 13: notes=161, tonal=85, drums=76, active_tracks=6, median_pitch=47.0
- block 14: notes=163, tonal=117, drums=46, active_tracks=7, median_pitch=53.0
- block 15: notes=264, tonal=172, drums=92, active_tracks=5, median_pitch=41.0
- block 16: notes=264, tonal=172, drums=92, active_tracks=5, median_pitch=41.0
