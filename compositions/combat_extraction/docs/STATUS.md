# 《搜打撤》战斗曲 — 当前状态交接(STATUS)

> **本文件是权威交接文档**(2026-08 定稿)。新会话开工**先读本文件**,
> 再读 `ARCHITECTURE.md`(母节/子节体系)与 `作品说明.md`(成品口径)。
> 历史规划文档(`COMPOSITION_PLAN.md`/`DIAGNOSIS_v6.md`/`PLAN_v7.md`/`ROADMAP.md`)
> 已归档至 `archive/combat_extraction/pre_status_docs/`,仅作背景参考。

---

## 0. 一句话现状

**母节 v9(stab 完全辅助化,用户验收)+ 子节体系(S1-S6 + 转场库 + SDC v1)已全部交付;**
**温跃层/Blink 游戏集成已完成三轮迭代(~/Projects/blink-recovered:音乐状态机/时停低通/
stinger/游戏内教程/死亡界面/K 键触控板适配),仓库已推 GitHub(LogosTopos/epsilon-bit-ai-composer)。**
用户判定:子 Agent 最大缺陷 = ①滥用 stab ②瞎调音高;红线 = 子节弃 stab + 音高原位。
下一步:S-BT 子弹时间子节 ✅ 已实现(待用户试听验收,含 time_fold/unfold 转场);S4/S5 重做版已产出(v2,待用户试听验收)。
本会话全量交接见仓库根 docs/HANDOVER.md。

## 1. 当前成品(文件)

| 文件 | 说明 |
|---|---|
| `Combat_Extraction.mid/.mp3` | **主成品 = 母节 v9 合成器版**(Hook = 方波 0/80,stab 完全辅助化) |
| `Combat_Extraction_v9_trumpet.mid/.mp3` | 小号版(对比保留,用户听感:合成器 > 小号) |
| `S1_Scavenge.mid/.mp3` | **子节 1《低音入场版》**(搜刮/开场氛围) |
| `Combat_Extraction_Loop.mid/.mp3` | **无缝大循环成品(3:23,可单曲循环,首尾无缝,开头无留白)**——S1→S2→母节→S-BT→母节→S4→S5→S6→loop_return 回 S1;`build_loop.py --cycle N` 遍间轮转;转场全部为动机桥 |
| `stems/stem_*.wav` | 5 组 stems 混音缓存(改层后必须删了重渲染) |

## 2. 音乐架构(定稿,勿改大方向)

- **母节 = 游戏高潮段**:16 小节全程满配(**14 层每小节在场**),无档位渐进;
  起承转合(层开关/密度/力度)全部留给子节(用户决策)
- **横向乐思 = 4 轮对话链**:bass 乐句 → 一提回声 → 刺刀插入 → bass 高把位应答
  → M3 齐奏收束 → riser 推进;轮次微变防机械(重音移位/力度波/开镲/切分位移)
- **重心在 Bass**(用户决策):bass 是总旋律主角(16 分密集 + 4 轮模式渐进);
  合成器 hook 是**稀疏辅助**(每轮一句五声短句 + 0.8 拍长音喘息)
- **stab 组完全辅助(v9)**:brass 刺刀 1/2/2/0 密度 vel 62-76、rhythm 只轮 2/4 反拍
  2 落点 vel 58、riser 42-72、M3 brass 76——混音后与 strings/atmosphere 同档垫底
- 和声 Em-C-G-D 循环(无终止式),168 BPM,4/4;母 loop = m3-18(22.9s),两圈演示
- **14 层**(v9:rhythm 只轮 2/4 出场,轮 1/3 为 13 层):drums / bass / vln1(回声) / vln2 / vla / celli / hook(合成器) /
  brass_stab(刺刀+M3) / timpani / pad / choir / piano / synth_rhythm / fx

## 3. 音色表(当前,lib/progs.py)

| ch | 角色 | (bank,prog) | 音区 | 角色定位 |
|---|---|---|---|---|
| 0 | piano_bang | (0,0) | 36-84 | 0.0 锚点重击(八度) |
| 1 | synth_pad | (0,89) | 48-84 | 氛围垫 |
| 2-5 | vln1/2/vla/celli | MuseScore Expr | — | 和声长音 + vln1 回声(64-71 带) |
| 6 | bass_electric | (0,33) | 28-52 | **主角**:16 分模式(40-52 高把位区为主) |
| 7 | fx | (0,80) | 55-90 | 轮末五声 riser + 0.0 低脉冲(57) |
| 9 | drums | (128,16) | — | kick/snare/hat/幽灵音/开镲/fill |
| 10 | hook | (0,80) | 55-88 | 稀疏五声乐句(辅助) |
| 11 | timpani | (0,47) | 26-60 | 2.0 根音 + M3 齐击 |
| 12 | brass_stab | (57,0) | 55-88 | **和弦分解刺刀**(v8 重写)+ M3 |
| 14 | choir | (17,52) | 48-84 | 长音 |
| 15 | synth_rhythm | (0,80) | 57-64 | 切分和声(轮 2/4 位移) |

**已删除音色**:`guitar_dist(0,30)`——库乐队 GM 映射 prog30 = Hard Rock.patch,
全曲唯一跨流派音色(用户发现,`GM_Instrument_Mapping.plist` 验证)。

## 4. 用户决策史(为什么是现在这样 —— 最重要的经验)

| 版本 | 改动 | 用户/诊断依据 |
|---|---|---|
| v1 | 母节初版(4 子 Agent 并行) | 规划→执行→验收流水线 |
| v2 | 切入切出渐变 + 高音修复 | 用户试听 |
| v3 | Bass 主角化 + stab 音色破案(管风琴 fallback) | "要能被人看见的贝斯手" |
| v4 | 删呼吸段,鼓/贝斯全程驱动 | "不做为呼吸而呼吸的空闲段" |
| v5 | 声部和谐修复(碰撞 412→180) | 数据驱动碰撞分析 |
| v6 | 角色化占比重构 | "突兀感=音色占比失当" |
| **v7** | **高潮段满配重构 + 删硬摇滚音色 + 互锁/对话链 + CC11 勘误** | ①"母节=高潮段,起承转合留给子节"②库乐队 Hard Rock 发现 |
| v7.1 | 重心转移:Bass 为主,合成器稀疏辅助;鼓/贝斯混音加大 | "合成器应给稀疏音符,重心在 Bass" |
| v7.2 | 重要音符句法化 + 层内微变化 | "3+3+2 全程不变 + 全层完全反复 = 机械" |
| **v8** | **刺刀重写:半音外音锯齿 → 和弦分解** | "stab 不和谐、旋律进展不符合预期"——避碰撞≠好听 |
| v8.1 | 贝斯可听性大修(sidechain 温柔化 + 高把位化 + EQ) | "听不见贝斯手" |
| v8.2 | stab 去碎片化:刺刀 2/4/3/2 密度 + hook 乐句化(长音喘息) | "太碎,门铃感,喘不上气;主旋律单拎怪" |
| **v9** | **stab 完全辅助化:brass 1/2/2/0 + vel 62-76、rhythm 只轮 2/4 反拍、riser 42-72、M3 76;混音 0.95/-26dB** | 用户分析:v8 及格但 stab 层仍有缺陷,弱化为完全辅助角色 |
| **S2/S6** | 子节 2《行进警觉》+ 子节 6《尘埃落定》(人格化,steer 后重写乐句) | 平行子 Agent B |
| **S4/S5** | 子节 4《绝境压迫》+ 子节 5《逃亡冲刺》 | 平行子 Agent C |
| **转场** | transitions.py 5 元素 + 衔接矩阵 + 连播 demo | 平行子 Agent A |
| **SDC v1** | **搜-打-撤完整版:S1-母节×2-S6(riser/crash_stop 转场,删留白)** | **用户:S1-母节-S6 已构成搜-打-撤循环;S4/S5 因 stab 滥用难听,不入选** |
| **S1** | 子节 1:删 stab + bass 平和化(8 分脉冲) | 用户指令 |
| S1.1 | 去掉 bass bend 推弦 | "弹簧一样的音效" |

### 关键教训(踩过的坑,新 Agent 避免重犯)

1. **避碰撞 ≠ 好听**:刺刀两次"降 5 度避碰撞"(v5/v7)越改越别扭;
   v8 改和弦分解后碰撞归零且好听。检测器(碰撞/互锁)是**参考工具,不是裁判**。
2. **GUGS 响应 CC11**(v6 文档"不响应"是错误结论):CC11<80 时长号近静音
   (实测 0→-90dB,72→-30.7,84→-28)。母节 CC11 全程 80-84 微弧。
3. **贝斯听不见的根因不是音量**:① sidechain 抽干(thr 0.03/ratio 8 把与 kick
   同拍的 bass 重音全压掉)→ 温柔化(0.08/3/attack 8ms);② 低音区 16 分短音无
   音高可辨度 + E1(28Hz)消费设备放不出 → 高把位化(40-52 为主,根音留首尾锚点)。
4. **碎片化 = 门铃感**:全短音、无句法、无长音 → 乐句化(密度松紧 2/4/3/2、
   0.8 拍长音喘息、五声下行倾向句)。
5. **bend 滑音(pitch wheel 推弦)听起来像"弹簧"**,用户不要(仅 S1 用过,已删)。
6. **缓存纪律**:运行 Python 前永远 `rm -rf __pycache__ lib/__pycache__ layers/__pycache__ sections/__pycache__` + `rm -f stems/stem_*`(mix_stems 有 stems 缓存,不删会渲染旧数据)。已沉淀为 `build.sh`。
7. **edit 工具多块编辑原子失败**:一次调用里任何一块匹配失败 → 全部不生效,
   且无报错提示(只提示第 N 块)。改完必须验证实际值。
8. **子 Agent 最大作曲缺陷 = ①滥用 stab ②瞎调音高(2026-08 用户判定,双因)**:
   凡"无 stab / 未强调 stab + 不瞎调音高"的都高质量(S1/S2/S6/母节 v9);
   凡强调 stab 或瞎调音高的都难听(S4:brass 66-80 + M3 76-80 + riser 加密
   + **旋律层 +1 半音多调性**;S5:32 分两八度 riser + **hook 八度叠置呼喊**)。
   **红线(2026-08 用户决策,永久)**:
   ① **子节创作中不再使用 stab 元素**——brass_stab 刺刀一律不用(难调,调好也只是
   点缀级);M3 齐奏只保留 timpani/kick/bass 三件套;riser 用母节 42-72 原版不加密;
   ② 音高一律用母节已验证素材原位(不移调/不叠置/不扩展音区);
   ③ 子节只做:层开关 + 密度/力度变形 + 人格化乐句重写(节奏型可新写,音高取母节素材)。
   可留:hook 乐句(旋律辅助)/ synth_rhythm(和声节奏)/ fx riser(转场工具)。
   温跃层向完整段落设计见 docs/THERMOCLINE_MUSIC_DESIGN.md。

## 5. 技术要点(新 Agent 必读)

```bash
# 生成(清缓存后)
./build.sh   # 清缓存 → 双版生成 → 双版审计 → 渲染混音(全自动)

# 手工流程
python3 compose.py --voice synth --out Combat_Extraction.mid   # voice: synth/trumpet
python3 sections/s1_scavenge.py                                 # 子节 1
# 渲染(双库,顺序不可反)
fluidsynth -F out.wav -r 44100 -R 0.9 -C 0 -g 1.2 \
  ../../soundfonts/MuseScore_General.sf2 ../../soundfonts/Rock_GeneralUser_GS_v1.471.sf2 in.mid
# 混音
rm -f stems/stem_* && python3 mix_stems.py --mid in.mid --render-stems
# 压码:峰值补 -1dB + libmp3lame -q:a 2 + ID3
```

- **audit_v7.py**:五维审计(密度 ≥12 层,v9 口径 / 互锁重音层 ≤2 / 碰撞 ≤150 / 占比 /
  **stab 辅助度**:每圈 ≤110 音、hook≤84、其余≤78)。当前母节:0 冲突 / 0 违规 / 碰撞 0 /
  **stab 105 音/圈(216 减半)**,混音后 stab 占比 ≈ -35.9dB(与 strings/atmosphere 同档垫底)。
- **混音链(mix_stems.py)**:drums 1.28 / bass 1.65+110Hz EQ+3dB / strings 0.75 /
  **stab 0.95+threshold -26dB(v9 更柔)** / atmosphere 0.7;bass sidechain **温柔化**(0.08/3/8ms)。
- **音色陷阱**:双库渲染下 MuseScore Expr bank(17,x)会 fallback 到 GUGS 怪音色;
  用 GUGS 精确布局 (bank=prog, prog=0)——brass=(57,0),trumpet=(56,0)。
- **强度弧线(高潮段口径)**:全曲平稳(轮间 ≤1.6dB),无档位落差;回环连续。

## 6. 下一步(路线,2026-08-05 更新)

已完成(历史):转场元素库 ✅ / 子节 2~6 ✅ / 连播 demo ✅ / stems 交付 ✅(export_stems.py) /
无缝大循环 ✅(build_loop.py,2026-08-05)。
转场体系 2026-08-05 重构:大循环/连播改用**动机桥**(step_up/engine_start/morph_crisis/
accel_roll——素材取相邻段落、节奏密度渐变、音色预伏,非插入式音效);
riser/down_fx/roll32 保留为简单场景与反向衔接备用。

当前待办(优先级从高到低,详见仓库根 docs/HANDOVER.md §5):

1. **S-BT 子弹时间子节 ✅ 已实现**(sections/s_bt.py → S_BT.mid/.mp3,待用户试听):
   心跳 kick 每拍 8 分双发(80/68)+ 时间晶体(hook 每 2 小节 1-2 音,69-81 带)
   + 弦乐 4.0 无隙长音 vel 40;无 16 分驱动;tempo 恒 168;hat/ghost/开镲/crash 全撤;
   transitions.py 新增 time_fold(1 小节低频挂留渐隐 + 末拍心跳预告)/ time_unfold
   (32 分 snare 滚奏渐强 2 拍 + 密度骤回),矩阵注册 ('S3','S-BT')/('S-BT','S3');
   父会话修正①:C 和弦晶体音 77(F5,母节未发声且非 C 五声)→ 79(G5 和弦音);
   父会话修正②(用户试听反馈'旋律不对'):时间晶体改为轮弧线设计——旧版轮头 8 次全 81、
   主音 81/79 机械交替;新版轮 1 高开(81→76)→轮 2 下沉(71)→轮 3 呼应(E5 色彩)
   →轮 4 低收(79→74→71 落底),cycle1 轮中换色彩音;
   已程序化验证:全部音高 ⊆ 母节音高集、零音区告警、brass_stab 零引用
2. **S4/S5 红线重做 ✅ 已产出 v2,待用户试听验收**:
   `S4_Crisis_v2.mid/.mp3`(心率 kick 双发 84/64 + bass 原位应答 + hook vel+4,12 层无 brass)、
   `S5_Extract_v2.mid/.mp3`(176 BPM + 32 分 hat,riser 母节 42-72 原版,无八度叠置);
   已程序化验证:两版全部音符音高 ⊆ 母节音高集,零音区告警,brass_stab 零代码引用
3. **横版 main_sideview.gd BATTLE 音乐挂点**(一行 MusicManager.set_section,目前缺失)
4. **热噪层**(热量>70% 垂直 stems:fx 高频嘶声 + pad 根音 16 分脉冲)
5. 远期:S-抢救主线场景 / 菜单循环变体 / 横版教程覆盖 / .app 正式打包
6. 工具链:audit 泛化为 `scripts/audit_composition.py`(任意曲目一键审计,低优先)

## 7. 版本历史(全量,提交号)

| 版本 | 内容 | 提交 |
|---|---|---|
| v1 | 母节初版 | ed29c87 |
| v2 | 切入切出渐变 + 高音修复 | d61dc66 |
| v3 | Bass 主角化 + stab 音色破案 | 0750417 |
| v4 | 删呼吸段,鼓/贝斯全程 | a1ac6dd |
| v5 | 声部和谐修复(碰撞 412→180) | 4ed3815 |
| v6 | 角色化占比重构 | ae1c3c0 |
| v7 | 高潮段满配 + 删硬摇滚音色 + CC11 勘误 | 9e063e3 |
| v7.1 | 重心转移(Bass 为主)+ 混音加大 | 7d46b19 |
| v7.2 | 重要音符句法化 + 层内微变化 | 4c47b16 |
| v8 | 刺刀→和弦分解 | 3af40d4 |
| v8.1 | 贝斯可听性大修 | 2bf909e |
| v8.2 | stab 乐句化(去碎片) | 5e5e459 |
| **v9** | **stab 完全辅助化(力度退让+密度减半+混音垫底)** | 7dadc60 |
| S1 | 子节1 低音入场版 | 63d0b9d |
| S2/S6/S4/S5 + 转场 + 连播 | 子节体系落地(人格化四子节 + transitions 5 元素 + demo) | 5af0cd6 |
| 子节音频 | S2/S4/S5/S6 转 MP3 | 3c1d81e |
| **SDC v1** | **搜-打-撤完整版(S1-母节×2-S6,riser/crash_stop 转场,删留白)** | — |
| S1.1 | 去 bend 弹簧音效 | 851cd66 |
