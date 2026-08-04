# ε-bit-ai-composer

本地 AI 音乐创作流水线:**LLM 设计音乐结构 → 确定性 Python 脚本生成 MIDI → FluidSynth + 真实采样音色库渲染 → ffmpeg 编码 MP3**。全流程本地运行,不依赖云端服务。

## 成果(2026-08-04 里程碑)

两条完整产线验证成功——从一条提示词("用 MIDI 写一首来自深渊风格的音乐")到成品 MP3:

| 作品 | 目录 | 说明 |
|---|---|---|
| 《深渊之战》Battle in the Abyss | `compositions/abyssal_battle/` | **战斗风格 + BPM 变速叙事**(96→150,冲刺骤停);完整版 3:52 含插部对比段/属功能/对位/余韵收束;防削波 limiter 链路 |
| 《无名之渊》The Nameless Abyss | `compositions/nameless_abyss/` | 小调叙事结构:下行坠落动机 → 上行转调 → 全奏高潮 → 归于寂静(动态跨度 13 dB,经 RMS 分段验证) |
| 《深渊回响》Echoes of the Abyss | `compositions/echoes_of_the_abyss/` | 大调空灵风格,竖琴琶音 + 钟琴微光 + 合唱吟唱 |

每曲目录自包含:生成脚本、MIDI 源、WAV 渲染、MP3 成品、作品说明。

## 快速开始

```bash
# 生成 MIDI(可调速度/移调/输出名)
python3 compositions/nameless_abyss/compose.py --bpm 69 --transpose 0
python3 compositions/abyssal_battle/compose.py --speed 1.0   # 战斗曲,整体速度缩放

# 渲染 WAV(需先下载音色库,见下)
fluidsynth -F out.wav -r 44100 -R 0.9 -C 0 -g 1.2 \
  soundfonts/MuseScore_General.sf2 The_Nameless_Abyss.mid

# 压 MP3(峰值管理;战斗曲等峰值密度高的建议加 limiter)
ffmpeg -y -i out.wav -af "volume=<补偿dB>,alimiter=limit=0.95" -codec:a libmp3lame -q:a 2 out.mp3

# 一键验证(声部核对 + RMS 分段 + 峰值)
python3 scripts/verify_render.py --mid ... --audio ... --segments "..."
```

### 音色库(一次性准备)

```bash
# MuseScore_General.sf2(205MB,Musyng Kite 官方继承者,真实采样)
# 下载到 soundfonts/ 后校验文件头必须为 RIFF+sfbk
curl -L -o soundfonts/MuseScore_General.sf2 \
  https://github.com/jiyimeta/musescore-general-sf2-split/releases/download/unsplit/MuseScore_General.sf2
```

⚠️ 不要使用 FluidSynth homebrew 包自带的 `VintageDreamsWaves-v2.sf2`(314KB 单元测试库,FM 合成音色,GM 映射错乱)。

## 目录结构

```
├── compositions/          # 作品(每曲一目录:脚本+MIDI+WAV+MP3+说明)
├── scripts/
│   └── verify_render.py   # 渲染链路验证工具
├── soundfonts/            # 音色库(大文件,不入库,按上文下载)
├── docs/
│   ├── TECH_STACK.md      # 完整技术栈规格与决策记录
│   └── REVISION_HISTORY.md # 《深渊之战》逐轮打磨记录(6 轮修订,含技术规则沉淀)
└── archive/
    ├── legacy-8bit/       # 旧 8-bit 工作台实验(已归档,仅本地保留)
    ├── fm-renders/        # 旧 FM 测试音色库渲染产物(教训参考)
    └── references/        # 过程参考资料(参考截图/OCR)
```

## 技术要点

- **作曲层**:Python + `mido`,格式 1 MIDI,480 TPB,3/4 拍;8 通道 GM 音色分配;CC11 表情曲线做渐强渐弱;事件收集→按绝对时间排序→flush(防时间线冲突)
- **渲染层**:FluidSynth `-R 0.9` 大房间混响(还原"小编制在大空间录制"的风格诉求)
- **验证层**:生成时声部核对(调性/转调信号/动机)+ 渲染后 RMS 分段曲线 + 成品峰值 ≈ -1.0 dB
- 详细规格见 [docs/TECH_STACK.md](docs/TECH_STACK.md)
- 逐轮修订记录与技术规则沉淀(转场五件套、声部分层、对位归位)见 [docs/REVISION_HISTORY.md](docs/REVISION_HISTORY.md)

## 许可

音乐作品为原创(风格致敬《来自深渊》,不含原曲旋律);音色库遵循其自身许可(MuseScore_General 为开源社区发布)。项目代码许可见 [LICENSE](LICENSE)。
