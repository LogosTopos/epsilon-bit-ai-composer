# MIDI to MP3 Render Chain Check

本项目已有系统化 MIDI/结构谱到 MP3 的方法，不需要恢复旧 chat 才能渲染：

- `src/ebit/renderer.py` 提供 `Renderer.render_multi_stereo()` / `Renderer.render_stereo()`，把结构化 note timeline 渲染为 WAV buffer。
- `Renderer.save_mp3()` 通过 ffmpeg 把临时 WAV 转为 MP3。
- `examples/highspeed_reference_midi_v1/` 已经用同一渲染器把 `高速战斗参考MIDI_v1/midi/*.mid` 批量转为 MP3。
- 该参考脚本还包含 GM program 到本项目波形的大致映射：bass -> triangle，lead/brass/fx -> sawtooth，guitar/organ -> pulse_25，bell/pipe -> fm_bell，pad/strings -> wavetable，drums -> kick/snare/hat/cymbal 分类。

本轮原创曲不是直接让系统播放器播放 MIDI，而是：

1. 用 Python note timeline 作为权威源。
2. 用项目 renderer 渲染 WAV/MP3，保持音色可控。
3. 同时导出标准 MIDI，方便后续外部审谱或重配器。

注意：外部 MIDI 播放器会按自己的 GM 音源播放，听感不会等同于本目录 MP3。
