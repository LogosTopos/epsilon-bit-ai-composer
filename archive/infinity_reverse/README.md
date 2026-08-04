# DDRKirby(ISQ) — 《Infinity》逆向分析报告

> ⚠️ **归档说明(2026-08-04)**:本目录为实验性探索(v1→v5 五轮迭代),
> 全部音频产物(MP3/WAV)已按用户要求删除。脚本与数据完整保留,
> 重新运行各脚本即可复现分析、转录与编曲生成(音频重建需先恢复 `audio/`)。
> 结论摘要:分析部分(节奏/调性/结构/转录)价值较高;创作部分(v3-v5 编曲)
> 经评审不达预期,已终止。

---

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

> 目标演进:v1/v2 以还原原曲为目标;v3 起**以创作目标取代还原目标**——
> 更复杂、更好听、更成熟。因此 v3 与原曲的相似度指标下降是**有意为之**。

### v1 — 乐谱骨架(单声道,存档)
纯 pulse/triangle 静态音色、单声道、无效果链。mel 0.376。
**坦率评价:不像一首歌**——只是把转录结果用最简音色念了一遍,
且带转录污染(bass 别名音、八度错误)和逐小节乱跳的和弦。

### v2 — 制作版(还原向最佳)
`clean_notes.py` + `produce.py`:转录清洗、和弦平滑+音阶约束、
立体声制作链。mel 0.473 / chroma 0.917 —— 还原向的参考基准。

### v3 — 编曲版(创作向,推荐试听:audio/arrangement_v3.mp3)
`arrange.py`,在原始时间线上(185.5 小节,段落边界对齐原曲分段)重新编曲:

**结构(13 段,动态弧线 -23.7dB → -16.7dB → -24.1dB)**:
intro 动机预示 → build 密度渐进 → A1 全奏 → turn 抽稀 → A2 加层 →
turn → **B 段转调(i-iv-VII-VI:F♯m-Bm-E-D)** → climax 双倍 kick →
break 气口 → reprise → turn3 → **finale 八度主题** → outro 余韵渐弱

**复杂度提升手段(项目工艺):**
- 7 层声部:lead + 三度/六度对位 + bass(音阶吸附)+ 生成式 16 分琶音 +
  padA/padB 双层 + 程序化 halftime 鼓组(kick 1&3/snare 3/8 分 hats/16 分 fill)
- 转场五件套:节奏先现(15.75 小节 crash)、密度渐进(build 段鼓分层进入)、
  和声预挂、fill 衔接;breakdown 后 reprise 轻律动恢复
- 制作链:lead 失谐合唱 + slap 延迟、琶音乒乓延迟、双 pad 宽声像、
  Schroeder 混响发送、glue 压缩 + 真软限幅(峰值 0.97,零削波)
- 声部事件:lead 375 / counter 209 / bass 680 / arp 2051 / pads 654 / drums 1685

**与素材源对比(仅参考,非目标)**:mel 0.381 / chroma 0.707(低于 v2 属预期)
**项目验证工具**:RMS 分段动态 8dB 跨度、峰值 -0.3dB

**听感定位**:一首以《Infinity》主题素材为基础的完整编曲——有鼓组驱动的
律动、段落对比与转调发展、对位织体、完整的动态弧线。

### v4 — 变奏编曲版(推荐试听:audio/arrangement_v4.mp3)
`arrange_v4.py`:在小节内变奏与音色组合上深度加工:

**节奏变奏引擎(音符变短变密)**:
- bass:6 种 pattern(pump8/octave8/16run/syncop/walk/double16),4-8 小节轮换,
  共 32 种(段×pattern)组合;16 分网格 + ghost 力度;16 分先现进 A1/climax/finale
- lead:长音拆 8 分重复(力度 0.82^k 衰减)、句末(乐句第 4 小节)16 分和弦音
  装饰跑、音前 16 分先现
- counter:长音拆分 + 16 分错拍对位
- arp:4 种 pattern(A updown/B broken/C wide/D endflam)按段轮换,climax 32 分双击
- drums:4 小节变奏循环(ghost snare/开镲/力度重音位轮换/fill 变体)

**音色组合优化(分段落音色映射)**
- lead:intro/outro triangle, build/a2/reprise pulse25, a1/b/climax/finale
  pulse12.5(亮), turn* square50(暗对比)
- bass:square 为主,B 段换 triangle(让新和声呼吸);counter:climax square50
- arp:轻段落 triangle、密段落 pulse12.5;pad:break/outro 换 triangle
- 新增 glock 高八度点缀层(intro/outro)

**数据**:MIDI 事件 14307(+25% vs v3);声部事件 lead 540 / counter 263 /
bass 1647 / arp 2054 / drums 1912;段落 RMS 弧线 -24.2dB → -16.3dB → -24.8dB
(项目 verify_render.py 验证通过)

### v5 — 创作缺陷修复版(推荐试听:audio/arrangement_v5.mp3)
`arrange_v5.py`,针对 v4 自我审查结论逐项修复:

**P0 和声戏剧性(82% i 和弦 → 加入属功能)**
- **7 处 C♯7(V)注入**:三个 turn 尾、B 段尾、climax 尾 3 小节属驻留、finale 尾
  → 形成 D–E–C♯7–F♯m 真终止回旋;climax 属驻留后 break 在 F♯m 上释放
- **outro 写 V→i 真终止替代 fade**:C♯7 两小节 → F♯m 终和弦(含主题末句
  时值伸缩 ×2 的收束陈述 + glock 回声),bass 在终和弦前停,和弦保持至曲终

**P0 织体分层(修复同频段堆叠)**
- pad 改**根+五度空三音**(三音职责留给旋律/对位)并下移音区;arp 上移八度
  至 83-95 闪亮区 → 频段: bass 30-47 | pad 54-66 | lead/counter 57-95 | arp 83-95
- bass pattern 按**乐句内 lead 密度**选择(lead 密→bass 8 分,lead 疏→bass 16 分,
  问答式);hats 4 小节呼吸(第 3 小节只打反拍);混响按段落参与(turn 干 0.16
  / break 湿 0.45 / climax 0.40)

**P1 动机与乐句**
- climax 换**下行和弦音对题**(替代机械平行三度);finale 对位改六度
- **乐句检测**:以旋律间隙划分乐句,bass/arp 的 pattern 周期从乐句头起算
  (伴奏不再与旋律乐句错位)
- **滑音渲染**:邻近音(间隙 0.02-0.12s、跨 2-7 半音)间画指数滑音——
  实现原曲实测到的 slide 特征
- **build 段 lead 滤波渐开**(700Hz→6kHz)+ climax 前滤波收窄;三处
  noise riser 转场(A1/climax/finale 进入)

**P2 首尾**:intro 第 4 小节鼓先入、第 6 小节 bass 进入(hook 前移);
长音拆分保留呼吸空拍(每 3 个 8 分停 1 个);旋律离调音保留(原曲性格)

**验证**:V7 织体在位(bass C♯2 泵动 24 音/pad [C♯4,G♯4,B4]);bass 第 6 小节
进入、182.7 后归零;段落 RMS -23.1dB → -16.6dB → -24.2dB,outro 以 -18.9dB
终止和弦收束(不再渐弱);项目 verify_render.py 通过。

### 附 — FluidSynth 音色库渲染(项目自家管线)
各版 MIDI 均可走 `fluidsynth -F out.wav -r 44100 -R 0.9 -C 0 -g 1.2
soundfonts/MuseScore_General.sf2 xxx.mid` 渲染真实采样音色版本
(audio/reconstruction_sf.mp3、audio/arrangement_v3_sf.mp3)。

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
clean_notes.py / reconstruct.py(v1) / produce.py(v2) / arrange.py(v3) /
arrange_v4.py(v4) / arrange_v5.py(v5) /
Infinity_reconstruction.mid(v1) / Infinity_reconstruction_v2.mid /
Infinity_arrangement_v3.mid / Infinity_arrangement_v4.mid / Infinity_arrangement_v5.mid /
audio/reconstruction.mp3(v1) / reconstruction_v2.mp3 / arrangement_v3.mp3 /
audio/arrangement_v4.mp3 / arrangement_v5.mp3 / arrangement_v3_sf.mp3 /
arrangement_v4_sf.mp3 / arrangement_v5_sf.mp3 / reconstruction_sf.mp3
audio/*.wav  stem 分离件与成品
plots/01_global.png ... 05_recon_compare.png
data/*.json|.npy  全部中间数据(转录、和弦、指标)
```

> 注:`audio/ data/ plots/` 在 .gitignore 中,不入库;脚本、MIDI、本报告入库。
