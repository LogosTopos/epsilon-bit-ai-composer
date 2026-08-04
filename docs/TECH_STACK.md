# TECH_STACK.md — 音乐创作技术栈(2026-08 快照)

> 本文档记录 ε-bit-ai-composer 当前端到端音乐创作链路:从作曲构思到 MP3 成品。
> 目标是让任何人在本机(或同类 macOS 环境)用本文档即可复现整条流水线。
> 含两套栈:§A 战斗曲/游戏配乐栈(当前活跃,combat_extraction)+ §B 深渊系作品栈(早期)。

---

## §A 战斗曲/游戏配乐技术栈(combat_extraction,当前活跃)

### A.1 母节/子节体系(设计核心)

- **母节 = 游戏高潮段**:168 BPM / E 小调 / Em-C-G-D 循环(无终止式,天然可循环);
  16 小节 14 层满配(drums/bass/4 弦乐/pad/choir/piano/hook/brass/timpani/rhythm/fx),无档位渐进;
  内部只做横向乐思(4 轮对话链:句头→回声→刺刀→应答→M3 收束→riser)
- **子节 = 人格化变体**:起承转合全部留给子节(层开关/密度/力度变形);
  每子节一个音乐人格(S1 低音入场 / S2 行进警觉 / S4 绝境压迫 / S5 逃亡冲刺 / S6 尘埃落定)
- **转场 = 插入式过渡小节**(transitions.py):riser(2 小节升档)/ down_fx / roll32 / crash_stop / 和声预挂;
  衔接矩阵 TRANSITIONS 36 键(9 合法),切换只发生在 4 小节边界,CC11 ≥ 70
- **创作红线**(用户决策):子节弃用 stab 元素;音高一律母节素材原位;节奏型可新写

### A.2 混音链(5 stems 垂直混音)

| stem | 通道 | 链(ffmpeg) |
|---|---|---|
| drums | 9,11 | 瞬态压缩 + volume 1.28 |
| bass | 6 | highpass 30 + 110Hz +3dB EQ + volume 1.65 + **侧链**(鼓 key,0.08/3/8ms 温柔让位) |
| strings | 2-5 | highpass 60 + volume 0.75 |
| stab | 10,12,7,15 | compressor -26dB + volume 0.95(v9 完全辅助化) |
| atmosphere | 0,1,13,14 | volume 0.7 |

总线:acompressor -16dB + alimiter 0.95。实测占比:bass 主导,stab 垫底(-35.9dB)。

### A.3 渲染链路 v2(自动化)

- **并行渲染**:5 stems 同时渲染(ThreadPool),实测 2.46×,与串行 md5 逐字节一致
- **增量缓存**:stems/<midbase>/ 按 mid+音色库内容哈希失效,双版仅重渲染差异组
- **校验门**:渲染后非空/时长下限/未削波;混音后 RMS 区间断言
- **压码**(encode_mp3.py):采样峰值 -1dB + alimiter=limit=0.891:level=0(**真峰值限幅**,实测 TP ≤ -1.0 dBTP)+ lame q2 + ID3 + ebur128 输出
- **audit_v7.py 五维**:密度(≥12 层)/ 互锁(重音层同槽 ≤2)/ 碰撞(≤150)/ 占比 / **stab 辅助度**(每圈 ≤110 音、hook≤84、其余≤78)
- **一键构建**:build_all.sh(母节双版 + 6 子节 + SDC + 连播,约 24s)

### A.4 游戏集成(Godot 4.6,已落地)

- **Music/SFX 总线**(幂等创建);枪声挂 SFX
- **MusicManager 状态机**:PREPARE(S1 循环)/ BATTLE(母节 5 stems 垂直,loop 双保险)/ CALM(S6 播一遍);0.8s 交叉淡化
- **时停**:Music 总线低通 800Hz(音乐不变速——变速只给音效,枪声 pitch×0.4 原版已实现)
- **变奏**:热量 >70% bass/drums +2dB;wave≥4 高波 bass/drums +2.5dB、stab/atmosphere -3dB;击杀 stinger(M3 音头,限流 1.5s)
- **外部资产**:Blink.pck 静态分析(180 文件)+ gdsdecomp 反编译还原工程(21 脚本)+ Godot 4.6.3 直接 --main-pack 运行(Mac 适配)

---

## §B 深渊系作品技术栈(早期,abyssal_* / nameless / echoes / contrapunctus)

## 1. 分层总览

```
┌─────────────────────────────────────────────────────────┐
│ 作曲层   Python 3.13 + mido → 程序化 MIDI(格式 1)        │
│          LLM 设计音乐结构(调性/动机/和声/织体/力度曲线)     │
├─────────────────────────────────────────────────────────┤
│ 渲染层   FluidSynth 2.5.7 + MuseScore_General.sf2       │
│          (真实采样 GM 音色库,大房间混响)                  │
├─────────────────────────────────────────────────────────┤
│ 编码层   ffmpeg 8.1.2 + libmp3lame(VBR q2)              │
│          + 峰值管理(volumedetect → volume 补偿)          │
├─────────────────────────────────────────────────────────┤
│ 验证层   生成时声部核对 + 渲染后分段 RMS + 峰值检查        │
└─────────────────────────────────────────────────────────┘
```

## 2. 各层规格

### 2.6 转场与分层技术规则(沉淀自《深渊之战》打磨轮次)

**转场五件套**(段落衔接不突兀):
1. 节奏先现:新段核心节奏型在前段末 1-2 小节弱力度先现
2. 密度渐进:鼓点抽离(全 pattern → 抽稀 → 仅 HH+kick)或渐进恢复(无鼓 → 轻律动 → 全速)
3. 音色提前切换:program change 放在无声区(如滚奏中),避免听觉瞬间切换
4. 和声预挂:滚奏/留白后半小节先落新段落低音,爆发落在已准备的和声上
5. 速度中间值:大幅变速用中间速度过渡(如 150→96→72,而非直接 150→72)

**爆发点进入原则**:新段落头 1-4 小节分层叠满(骨架=鼓+低音+弦乐+旋律 → 加层 → 全满),不瞬间全奏。

**声部分层原则**(低频浑浊与齐奏的预防):
- 每个声部有专属音区;110Hz 附近(如 A2)只允许一个声部
- 和弦三音职责唯一(留给弦乐),其他声部用根+五开放排列
- 参考音区分配:低音 41-52 / 吉他 53-69 / 弦乐 53-64 / 合唱 60-72 / 铜管 53-81 / 旋律 76-91

**平行对位规则**:平行六度副旋律遇和弦外音时,就近(±2 半音)归位到和弦音。

详见 [docs/REVISION_HISTORY.md](REVISION_HISTORY.md) 的逐轮打磨记录。

### 2.1 作曲层(compose_*.py)

| 项 | 规格 |
|---|---|
| 语言/库 | Python 3.13 + `mido` |
| MIDI 格式 | 格式 1(每通道独立 Track),480 ticks/beat |
| 节拍 | 3/4 拍,69 BPM(参数可调) |
| 通道数 | 8(钢琴/竖琴/弦乐×2/人声/音乐盒/低音提琴/Pad) |
| 音色分配 | GM program:0 钢琴、46 竖琴、48/49 弦乐、53 Oohs、10 Music Box、43 Contrabass、89 Pad |
| 动态控制 | CC11 表情曲线(块状渐强/渐弱,如 45→112→14) |
| 关键代码模式 | 事件收集 `pending[]` → 按通道绝对时间排序 → flush(避免同通道时间倒退) |
| 并发音符 | `multi()` 处理同刻多音(和弦/双音),禁止对同一通道连续排布不同起始时间的事件 |

### 2.2 渲染层(FluidSynth)

```bash
fluidsynth -F out.wav -r 44100 -R 0.9 -C 0 -g 1.2 \
  soundfonts/MuseScore_General.sf2 input.mid
```

| 参数 | 值 | 说明 |
|---|---|---|
| `-R 0.9` | 大房间混响 | 还原 Penkin 式"小编制在大空间录制" |
| `-C 0` | 关合唱效果 | 避免染色 |
| `-g 1.2` | 增益 | 采样库默认输出偏低,渲染后仍需响度补偿 |
| `-r 44100` | 采样率 | 44.1kHz/16bit 输出 |

### 2.3 音色库(关键资产)

- **文件**:`abyss_music/soundfonts/MuseScore_General.sf2`(205.6 MB)
- **来源**:GitHub release 直链
  `jiyimeta/musescore-general-sf2-split` → release `unsplit` → `MuseScore_General.sf2`
- **出身**:MuseScore 官方音色库,整合 FluidR3 + **Musyng Kite**(钢琴等音色直接沿用 Musyng Kite),CC 许可,开源社区现行推荐
- **校验**:文件头必须为 `RIFF` + `sfbk`;下载后应立即校验
- **⚠️ 历史教训(重要)**:homebrew 安装 FluidSynth 时自带的
  `VintageDreamsWaves-v2.sf2`(**314 KB**)是官方**单元测试**用 FM 合成演示库,
  GM 映射完全错乱(钢琴→"FM Bells 1"、合唱→"Harsh FM Bass"、竖琴→"Oink Grind")。
  用它对 128 个 GM program 里大多数会渲染出错误音色。**禁止用于正式渲染。**

### 2.4 编码层(ffmpeg)

```bash
# 响度检查
ffmpeg -i in.wav -af volumedetect -f null -   # 看 mean/max_volume
# 压 MP3(峰值提升至约 -1.0 dB 留余量,防削波)
ffmpeg -y -i in.wav -af "volume=<补偿 dB>" -codec:a libmp3lame -q:a 2 out.mp3
```

- `-q:a 2` = VBR 高质量档(~190-220 kbps 动态)
- 补偿原则:先 `volumedetect` 得到 max_volume,再提升到峰值 ≈ -1.0 dB

### 2.5 验证层(交付标准)

1. **生成时声部核对**:导出主旋律/低音声部音符序列,核对调性、转调信号、动机落点
2. **渲染后 RMS 分段验证**:引子低 → 高潮峰 → 尾声静(典型动态跨度 ~13 dB)
3. **成品峰值检查**:max_volume ≈ -1.0 dB(有余量、无削波)

## 3. 文件布局

```
abyss_music/
├── compose_*.py            # 作曲生成脚本(可参数化重生成)
├── *.mid                   # 标准 MIDI 源
├── *_v2.wav / *_v2.mp3     # 用 MuseScore_General 渲染的成品
├── *.wav / *.mp3           # 旧音色库产物(保留做 A/B 对比,可清理)
├── soundfonts/
│   └── MuseScore_General.sf2
└── 作品说明.md              # 每首作品的风格映射与自检记录
```

## 4. 端到端复现(从零到 MP3)

```bash
cd abyss_music

# 1) 生成 MIDI(作曲)
python3 compose_nameless_abyss.py          # 输出 The_Nameless_Abyss.mid + 声部自检

# 2) 渲染 WAV(合成)
fluidsynth -F out.wav -r 44100 -R 0.9 -C 0 -g 1.2 \
  soundfonts/MuseScore_General.sf2 The_Nameless_Abyss.mid

# 3) RMS 分段验证(用 python wave + audioop,见 compose 输出或手动脚本)

# 4) 峰值检查 + 压 MP3
ffmpeg -i out.wav -af volumedetect -f null -
ffmpeg -y -i out.wav -af "volume=1.7dB" -codec:a libmp3lame -q:a 2 out.mp3
```

## 5. 网络与依赖备忘

- 本机走 HTTP 代理 `127.0.0.1:7897`;GitHub release 直链 ~350-550 KB/s
- archive.org 大文件实测 27 KB/s(不可用于 1GB 级下载);polyphone.io / musical-artifacts 直连被拒
- `gh` CLI 可用于 GitHub 搜索/API(`gh api repos/<repo>/releases/latest`)
- macOS `stat` 参数坑:`stat -f%z` 与 GNU 语法冲突,脚本内一律用 Python `os.path.getsize`

## 6. 已知局限与下一步

- 合成链路的上限是"高质量虚拟管弦乐";要录音级质感需换音频域生成(Stable Audio Open 等)或专业采样器(Kontakt/Spitfire + 卷积混响)
- 混音环节(压缩/EQ/立体声)目前只做了峰值管理,未做母带链
- 音色库是纯 GM 通用库,特殊音色(如深渊系合成器质感)需自定义 SFZ/SF2

## 7. 决策记录(ADR 简版)

| 日期 | 决策 | 原因 |
|---|---|---|
| 2026-08-04 | 采用 MuseScore_General.sf2 作为唯一正式音色库 | 真实采样;Musyng Kite 继承者;GitHub 可稳定获取;205MB 平衡质量与体积 |
| 2026-08-04 | 弃用 VintageDreamsWaves-v2.sf2 | 314KB 单元测试库,FM 合成音色,GM 映射错乱 |
| 2026-08-04 | 渲染统一 `-R 0.9` 大混响 | 风格核心诉求("大空间录制") |
| 2026-08-04 | 成品峰值统一压到 -1.0 dB | 留余量防削波,同时最大化响度 |
