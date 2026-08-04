# DDRKirby(ISQ) — 《Infinity》逆向分析报告

> 目标:对 `/Users/topologyw/Music/网易云音乐/DDRKirby(ISQ) - Infinity.mp3`
> 设计算法管线,尝试还原其音色与音轨,并给出可行性判断。
> 方法:经典 DSP + 统计建模(非深度学习),全程本机运行。

---

## 0. 结论先行:这件事好做吗?

**中等难度偏上,但值得做。** 分层回答:

| 层面 | 难度 | 达成度 |
|---|---|---|
| 节奏/调性/结构 | 容易 | ✅ 172.3 BPM、F♯ minor、8 段结构全部锁定 |
| 旋律/低音转录 | 容易~中等 | ✅ lead 487 音、bass 732 音,12-TET 精确对齐 |
| 和弦进行 | 中等 | ✅ 185 小节 → F♯m 为主 + D–E 回环 |
| 鼓组模式 | **难** | ⚠️ 结论:主段**没有常规鼓组层**(详见 §4) |
| 音色还原(波形类) | 中等 | 🟡 识别出 pulse 族 + 滤波包络 + 12Hz vibrato,但无法逐音符锁定 duty |
| 逐样本还原 | **几乎不可能** | ❌ MP3 有损 + 混音母带(压缩/限幅/立体声处理)不可逆 |

**关键认知**:9-bit 风格(8-bit 音色基底 + 大量音色调制机制)让"波形级"还原
比纯 NES 更复杂——同一乐句内 duty 切换、滤波包络、滑音是常态,静止波形模型
拟合必然不稳定。但**音乐层信息**(音符/和声/节奏)恢复得非常好。

---

## 1. 管线总览(每阶段一个脚本,可复现)

```
analyze_global.py   全局分析:节奏网格锁定、调性、结构分段
separate.py         HPSS 音源分离 → 谐波/打击乐 stem + 频带拆分
transcribe.py       梳状掩蔽(挖掉 bass 及其 12 次谐波) → pyin 双声部转录
transcribe_arp.py   高频带(4-16kHz)琶音声部转录,16 分网格量化
timbre.py           谐波剖面拟合(duty/波形)、vibrato、包络、鼓分类
audit_modulation.py NMF 声部数、音内谐波演化、滑音、噪声特性
harmony_drums2.py   每小节和弦估计 + k-means 鼓聚类 + 网格位置分析
reconstruct.py      numpy 芯片合成器重建 + 动态匹配 + 量化对比 + MIDI 导出
```

依赖:Python 3.13 + librosa / numpy / scipy / soundfile / mido / ffmpeg。

---

## 2. 音乐分析发现

### 2.1 全局参数
- **BPM 172.27**(四分音符 348.3ms;用 onset 间隔直接测得;太鼓次郎谱面标 170)
- **调性:F♯ minor**(Krumhansl 相关 0.74;全曲稳定;相对大调 D♯ major 是第二候选)
- **结构**:8 段,含三段 ~19.9s 的重复回环段(恰好 = D–E–F♯m 进行段)
- 动态范围 ~10dB(p95/p10),响度战争级压缩;谱心 4.3kHz,rolloff 15kHz
- 立体声:低音近单声(侧/中 0.14),高频加宽(0.60)——典型的 9-bit 混音

### 2.2 声部清单(4 个旋律性声部 + 无常规鼓组)

| 声部 | 频带 | 特征 |
|---|---|---|
| **Bass** | 30–190Hz | F♯2/F♯1 八度泵动 8 分音符;方波特征;**真实失谐 -7 cents**(自相关法校准) |
| **Lead** | 150–4kHz | pulse 族(12.5/25/50% duty 各段不一);**12Hz vibrato**;**滤波包络**(attack 亮→sustain 暗,h3 谐波系统性衰减);6% 音符间隙有滑音 |
| **Arp** | 4–16kHz | F♯ 小调五声音阶点缀,中位时长 87ms(=1 个 16 分),每小节中位 2 音 |
| **Pad** | 中频 | F♯m 长音和声;D–E–F♯m(VI–VII–i)回环段 |
| 鼓 | — | 仅开场 ~3 个真实鼓击;主段无鼓组 |

### 2.3 鼓组之谜(重要发现)
用四种独立方法交叉验证(频带能量网格直方图、k-means 特征聚类、低频峰值轨迹
下扫检测、瞬态/持续比):主段 **1–12kHz 频带能量在 8 分网格上完全平坦**,
无 kick/snare/hat 落点。结论:**该曲的律动由 bass 拨奏瞬态 + 琶音纹理驱动**,
没有常规鼓组层(与部分 9-bit 极简曲目一致)。HPSS 打击乐 stem 中的"鼓事件"
实为各芯片音色的噪声瞬态(谱平坦度 0.924 ≈ 白噪声)。

### 2.4 音色指纹(9-bit 调制机制的实证)
- NMF 秩分析:同时发声源 ≥6,织体密集
- **音内谐波演化**:长音中 h2 可暴涨 5–10 倍(如 2.59s 处 [2.79→14.98→2.38]),
  h3 系统性衰减([2.48→0.58→0.03])= **attack 亮→sustain 暗的滤波包络**,
  以及疑似 duty 扫掠——这就是"9-bit 音色调制"的声学证据
- vibrato:12.05Hz、深度 ~3 cents(浅而快,典型的芯片 vibrato)
- 包络:attack ~5ms(利落起音)
- 混响:snare 尾音 -20dB 仅 13ms —— **鼓完全干声**

---

## 3. 重建结果(三版对比)

### v1 — 乐谱骨架(单声道,存档)
纯 pulse/triangle 静态音色、单声道、无效果链。mel 0.376。
**坦率评价:不像一首歌**——只是把转录结果用最简音色念了一遍,
且带转录污染(bass 别名音、八度错误)和逐小节乱跳的和弦。

### v2 — 制作版(推荐试听:audio/reconstruction_v2.mp3)
`clean_notes.py` + `produce.py` 流水线:
- **转录清洗**:自相关法逐音符校验,剔除 95 个 bass 污染音符与八度错误
- **和弦平滑**:5 小节中值滤波 + **F♯ 小调音阶兼容约束**(吸附 41 个离调和弦)
- **制作链**:lead 失谐合唱(±5c 宽声场)、琶音乒乓延迟(8 分,LP 6kHz)、
  pad 双失谐宽声像、Schroeder 混响发送(鼓保持干声,与原曲一致)、
  平滑动态匹配 + 软限幅

### v3 — FluidSynth + MuseScore_General.sf2(项目自家管线)
同一份 MIDI(`Infinity_reconstruction_v2.mid`)用项目标准管线渲染,
真实采样音色 → audio/reconstruction_sf.mp3。

**量化对比(原曲 vs 各版本,8 个结构段均值):**

| 版本 | Mel 谱余弦 | Chroma | RMS 3.5s | 听感定位 |
|---|---|---|---|---|
| v1 芯片骨架 | 0.376 | 0.91 | 0.82 | 乐谱骨架,不像歌 |
| **v2 制作版** | **0.473** | **0.917** | **0.911** | 芯片风编曲成品,接近"歌" |
| v3 音色库版 | 0.412 | 0.875 | — | 真实乐器版,质感好但芯片味丢 |

**v2 听感预期**:旋律/低音/和声/速度完整,立体声与混响在场,段落力度跟随原曲;
与真正的原曲仍有差距——音色是近似、无鼓组、无原曲的采样细节与效果链。

---

## 4. 已知局限与后续方向

1. **Lead 转录覆盖率 ~60-80%**:多音同时发声(双音 lead/和声织体)时 pyin 只取
   单音。改进方向:CQT 谐波叠加 + NMF 双声部分离,或深度模型(SPICE/Basicsound)
2. **Duty 无法逐音符锁定**:谐波剖面被 pad 污染。改进:用开场独奏段 + 背景减法
3. **无鼓组结论基于经典方法**:若原曲确实有被混音掩盖的鼓,需源分离模型验证
4. **音色仍是近似**:v2 用 pulse 族近似,原曲音色库/采样细节不可逆;
   深度音色匹配(用原曲片段做参考波形合成)是下一步
5. 可选:为重建写一个 ChipSynth 音色库,让 v2 更接近原曲音色

---

## 5. 文件清单

```
analyze_global.py / separate.py / transcribe.py / transcribe_arp.py /
timbre.py / audit_modulation.py / harmony_drums2.py / drum_sweep.py /
clean_notes.py / reconstruct.py(v1) / produce.py(v2) /
Infinity_reconstruction.mid(v1) / Infinity_reconstruction_v2.mid /
audio/reconstruction.mp3(v1) / reconstruction_v2.mp3 / reconstruction_sf.mp3
audio/*.wav  stem 分离件与成品
plots/01_global.png ... 05_recon_compare.png
data/*.json|.npy  全部中间数据(转录、和弦、指标)
```

> 注:`audio/ data/ plots/` 在 .gitignore 中,不入库;脚本、MIDI、本报告入库。
