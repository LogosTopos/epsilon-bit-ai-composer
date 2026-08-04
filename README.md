# ε-bit-ai-composer

本地 AI 音乐创作流水线 + 游戏配乐系统:**LLM 设计音乐结构 → 确定性 Python 脚本生成 MIDI → FluidSynth + 真实采样音色库渲染 → ffmpeg 混音/压码 → MP3 成品**,并进一步延伸为可嵌入游戏的"母节/子节"动态音乐体系(Godot 集成)。

全流程本地运行、确定性可复现,不依赖云端服务。

## 技术路径总览

```
┌────────────────────────────────────────────────────────────────────┐
│ 作曲层   LLM 设计音乐结构(动机/和声/织体/力度曲线/人格意象)          │
│          Python 3 + mido → 确定性 MIDI(格式 1,480 TPB)             │
│          关键模式:角色化占比 / 节奏互锁表 / 动机对话链 / CC11 表情   │
├────────────────────────────────────────────────────────────────────┤
│ 渲染层   FluidSynth 2.5.7 + 双音色库叠加(顺序不可反)                │
│          MuseScore_General.sf2 + Rock_GeneralUser_GS_v1.471.sf2    │
│          (GUGS 按 per-font fallback 兜底,实测三库对比选型)          │
├────────────────────────────────────────────────────────────────────┤
│ 混音层   stems 分轨(5 组:drums/bass/strings/stab/atmosphere)       │
│          ffmpeg 并行渲染 + 增量缓存 + 侧链压缩 + 总线 glue + limiter│
├────────────────────────────────────────────────────────────────────┤
│ 编码层   encode_mp3.py:采样峰值 -1dB + alimiter 真峰值限幅          │
│          (TP ≤ -1.0 dBTP 实测校验)+ libmp3lame VBR q2 + ID3        │
├────────────────────────────────────────────────────────────────────┤
│ 验证层   audit 五维(密度/互锁/碰撞/占比/stab 辅助度)+ 渲染校验门     │
│          (时长/非静音/未削波)+ ebur128 响度输出                     │
├────────────────────────────────────────────────────────────────────┤
│ 游戏层   Godot 4.6 集成:Music/SFX 总线 + MusicManager 状态机        │
│          (5 stems 垂直混音 / 时停低通 / 热量加成 / 高波变奏 / stinger)│
└────────────────────────────────────────────────────────────────────┘
```

## 作品清单

### 当前活跃项目:《搜打撤》战斗曲 + 游戏配乐

`compositions/combat_extraction/` — 为超快节奏 PVE 搜打撤枪战游戏(温跃层/Blink)制作的战斗音乐系统:

| 成品 | 文件 | 说明 |
|---|---|---|
| 母节 v9(主成品) | `Combat_Extraction.mp3` | 168 BPM / E 小调 / 14 层满配高潮段 / 可无缝循环(22.9s) |
| 《搜-打-撤 v1》 | `Combat_Extraction_SDC_v1.mp3` | 完整流程成品:S1 搜刮 → 母节战斗 ×2 → S6 结算(1:42) |
| 六子节连播 demo | `Combat_Extraction_Playthrough.mp3` | 六种音乐人格 + 六种转场完整串演(3:01) |
| 子节 S1-S6 | `S1_Scavenge.mp3` 等 | 搜刮/探索/危机/撤离/结算,每节独立可试听 |
| stems 交付 | `export_stems.py` 生成 | 24-bit 单圈 loop stems,供 FMOD/Wwise/Godot 垂直混音 |

**核心设计(母节/子节体系)**:
- **母节 = 游戏高潮段**:16 小节全程满配(14 层:鼓/贝斯/4 弦乐/pad/合唱/钢琴/hook/铜管/定音鼓/节奏层/fx),无起承转合——起承转合全部留给子节
- **子节 = 人格化变体**:S1 低音入场 / S2 行进警觉 / S4 绝境压迫 / S5 逃亡冲刺 / S6 尘埃落定——每个子节有独立音乐人格(重写乐句,音高取母节素材原位)
- **转场 = 插入式过渡小节**:riser 升档 / down_fx 降档 / roll32 冲刺 / crash_stop 急停 / 和声预挂,衔接矩阵 36 键
- **游戏集成(已落地)**:Godot 4.6 的 MusicManager 状态机(菜单/战斗/结算三态 + 时停低通 + 热量加成 + 高波变奏 + 击杀 stinger)

### 已完成作品(早期)

| 作品 | 目录 | 说明 |
|---|---|---|
| 《深渊之战》 | `compositions/abyssal_battle/` | 战斗风格 + BPM 变速叙事(96→150),3:52 完整版 |
| 《无名之渊》 | `compositions/nameless_abyss/` | 小调叙事结构,动态跨度 13 dB |
| 《深渊回响》 | `compositions/echoes_of_the_abyss/` | 大调空灵:竖琴琶音 + 钟琴微光 + 合唱 |
| 《深渊对位》 | `compositions/contrapunctus_abyssi/` | 对位法练习,stem 分轨混音(4.1) |
| 《深渊组曲》 | `compositions/abyssal_suite/` | 多乐章组曲(总谱设计文档) |
| 《灰烬前线》 | `compositions/threshold_of_ashes/` | 三曲连作(接近/狩猎/撤离) |

每曲目录自包含:生成脚本、MIDI 源、WAV 渲染、MP3 成品、作品说明。

## 依赖清单

| 依赖 | 版本(实测) | 用途 |
|---|---|---|
| Python 3 | 3.13(Anaconda) | 作曲/混音/审计脚本 |
| mido | pip | MIDI 读写(格式 1,480 TPB) |
| FluidSynth | 2.5.7 | SF2 渲染(约 120-200× 实时,极快) |
| ffmpeg | 8.1.2 | stems 混音 / 压码 / 校验 |
| Godot Engine | 4.6.3(macOS 通用版) | 游戏运行时(直接加载 .pck 或 --path 工程) |

## 音源库(不入库,按需下载到 `soundfonts/`)

| 音色库 | 大小 | 角色 |
|---|---|---|
| MuseScore_General.sf2 | 205 MB | 古典/通用主库(Musyng Kite 继承者) |
| Rock_GeneralUser_GS_v1.471.sf2 | 31 MB | 摇滚副库(贝斯/鼓组/精确 GM 音色实测最强) |
| Rock_SGM-V2.01.sf2 | 247 MB | 备选(实测全面落败,仅存档) |

双库叠加渲染(`MuseScore_General` 先、`GUGS` 后)时,GUGS 对每个 GM program 按 per-font fallback 优先命中——这是"古典弦乐 + 摇滚鼓贝斯"混搭的关键机制。下载地址见 `docs/TECH_STACK.md`。

⚠️ 勿用 FluidSynth 自带的 `VintageDreamsWaves-v2.sf2`(314KB 单元测试库,GM 映射错乱)。

## 快速开始

```bash
cd compositions/combat_extraction

# 一键全量构建(母节双版 + 全部子节 + SDC v1 + 连播 demo)
./build_all.sh            # 并行渲染 + 增量缓存 + 校验门 + TP 压码,约 24s

# 单个母节构建(双版 + 审计 + 渲染混音 + 压码 + 主成品复制)
./build.sh

# stems 交付(24-bit 单圈 loop + zip)
python3 export_stems.py --mid Combat_Extraction.mid --loop-start 2.857 --loop-len 22.857
```

渲染命令(双库,顺序不可反):

```bash
fluidsynth -F out.wav -r 44100 -R 0.9 -C 0 -g 1.2 \
  soundfonts/MuseScore_General.sf2 soundfonts/Rock_GeneralUser_GS_v1.471.sf2 in.mid
```

## 目录结构

```
├── compositions/              # 作品(每曲一目录:脚本+MIDI+WAV+MP3+说明)
│   └── combat_extraction/     # 《搜打撤》战斗曲(当前活跃)
│       ├── layers/            # 母节三层(鼓/贝斯和声/纹理)
│       ├── sections/          # 子节体系(transitions 转场库 + S1-S6 + SDC v1)
│       ├── lib/               # Score API / 音色映射
│       ├── docs/              # STATUS(权威交接)/ 架构 / 设计 / 教程 / Mac 移植
│       ├── audit_v7.py        # 五维验收审计
│       ├── mix_stems.py       # stems 分轨渲染混音(并行+增量)
│       ├── encode_mp3.py      # TP 限幅压码
│       ├── export_stems.py    # 24-bit stems 交付
│       └── build.sh / build_all.sh
├── scripts/verify_render.py   # 渲染链路验证工具
├── soundfonts/                # 音色库(大文件不入库,按上文下载)
├── docs/                      # TECH_STACK / HANDOVER / REVISION_HISTORY
└── archive/                   # 已归档实验(legacy-8bit / infinity_reverse / ...)
```

## 技术要点(踩坑沉淀)

- **避碰撞 ≠ 好听**:声部碰撞检测是参考工具不是裁判(刺刀两次"避碰撞"越改越别扭,改和弦分解后碰撞归零且好听)
- **GUGS 完全响应 CC11**:CC11 < 80 时长号近静音(实测 0→-90dB,72→-30.7)——CC11 全程微弧线,动态交给子节层开关
- **贝斯听不见的根因**:① sidechain 抽干(kick 同拍重音被压)→ 温柔化;② 低音区 16 分短音无音高可辨度 + 消费设备切 60Hz → 高把位化(40-52)
- **子节创作红线**(用户决策):弃用 stab 元素(难调,调好也只是点缀);音高一律用母节素材原位(不移调/不叠置);子节 = 层开关 + 密度/力度变形 + 人格化乐句重写
- **渲染确定性**:并行渲染与串行 md5 逐字节一致;增量缓存按 mid+音色库内容哈希失效
- **压码真峰值**:采样峰值 -1dB ≠ 真峰值;alimiter 限幅后实测 TP ≤ -1.0 dBTP

## 许可

音乐作品为原创(风格致敬,不含原曲旋律);音色库遵循其自身许可(MuseScore_General 为开源社区发布)。项目代码许可见 [LICENSE](LICENSE)。
