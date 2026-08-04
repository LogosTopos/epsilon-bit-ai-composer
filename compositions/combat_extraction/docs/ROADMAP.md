# 未来发展方向 — ROADMAP(2026-08)

> 目标:把《搜打撤》战斗曲从"单曲"升级为"可嵌入游戏的音频系统"。
> 三段路线:短期(母节质量)→ 中期(子节体系)→ 长期(工具链沉淀)。

---

## 短期:母节 v8.2 ✅ 完成(用户验收"够上及格线")+ 子节 1 ✅ 完成

> 母节历经 v1→v8.2 共 12 轮打磨(全量版本史见 STATUS.md §7)。
> 下一对话首选任务见「中期」:转场元素库 + 子节 2~6。

依据 `DIAGNOSIS_v6.md`,完成 7 项改造:
1. 节奏互锁表落地
2. 一提音型降 8 度 + 动机对话链
3. 持续段补层
4. 加节奏吉他(57-64 区 8 分切分)
5. 加 riser/下行 FX 音色(用现有库:合成器 0/89 或 0/81 上行扫频?若音色库无 riser,用 16 分音阶上行模拟)
6. 军鼓幽灵音 + 镲滚
7. 八度叠置(档3)

**验收**:DIAGNOSIS §3 的标准全过,产出 v7 MP3 交用户试听。

## 中期:子节体系(架构落地,进行中)

按 `ARCHITECTURE.md` 实现(S1 已完成,见 sections/s1_scavenge.py):
2. 写 `sections/` 六个子节模块(S1 搜刮/S2 探索/S3 战斗/S4 危机/S5 撤离/S6 结算)
3. 写 `sections/transitions.py` 转场元素库(riser/downFX/roll/预挂)
4. 产出"六子节连播 demo"(S1→S2→S3→S4→S3→S5→S6,带转场)
5. stems 交付:5 组 stems 供 FMOD/Wwise 垂直混音

**验收**:任意子节顺序切换 ≤2 拍无感;游戏端可截断。

## 长期:工具链沉淀(复用)

1. **模板化**:把"角色化占比模型 + 节奏互锁表 + 动机对话链"沉淀为通用作曲模板
   (`compositions/_template/`),新曲目直接套用
2. **音色库扩展**(已下载):MuseScore_General(古典)+ GeneralUser GS(摇滚)
   + SGM-V2.01(通用,247MB 待删/留)+ Timbres of Heaven(管风琴,待下载完)
   —— 按曲目风格选库或双库叠加(已验证机制)
3. **程序化合成**(远期):当前音色受限于 SF2 采样;未来可自研合成器
   (numpy 直接合成,确定性渲染)——电子音乐/芯片音乐的音色天花板打开
   (参考 infinity_reverse 的 ChipSynth 经验)
4. **无反馈自检协议**:密度/占比/互锁/碰撞/频谱五维验证脚本沉淀为
   `scripts/audit_composition.py`,任何曲目一键审计

## 当前资产清单

```
compositions/combat_extraction/
├── docs/COMPOSITION_PLAN.md   母节音乐规划(168BPM/E小调/动机库)
├── docs/ARCHITECTURE.md       母节/子节体系 + 转场规范(新)
├── docs/DIAGNOSIS_v6.md       母节问题诊断 + v7 改造清单(新)
├── docs/ROADMAP.md            本文件(新)
├── layers/                    母节四层(intro_outro/drums/bass_harmony/riff_texture)
├── lib/orch.py                Score API(含 bend 滑音)
├── lib/progs.py               音色映射(GUGS+MuseScore 双库)
├── compose.py                 总装
├── mix_stems.py               5 组 stems 混音(侧链)
└── Combat_Extraction_v6.mp3   当前母节成品
```

## 版本历史

| 版本 | 内容 | 提交 |
|---|---|---|
| v1 | 母节初版(规划→4 子Agent并行→总装) | ed29c87 |
| v2 | 切入切出渐变 + 高音修复 | d61dc66 |
| v3 | Bass 主角化 + stab 音色破案(管风琴 fallback) | 0750417 |
| v4 | 删呼吸段,鼓/贝斯全程驱动 | a1ac6dd |
| v5 | 声部和谐修复(碰撞 412→180) | 4ed3815 |
| v6 | 角色化占比重构(氛围全程/亮点稳定) | ae1c3c0 |
| v7 | **高潮段满配重构**:删硬摇滚音色(库乐队 Hard Rock 验证)+ 14 层全程 + 节奏互锁 + 对话链 + CC11 勘误(80-84 微弧)+ 双版本(小号/合成器) | 9e063e3 |
| v7.1 | 重心转移:Bass 为总旋律重心,合成器降为稀疏辅助;鼓/贝斯混音加大 | 7d46b19 |
| v7.2 | 重要音符句法化(重音移位 3+2+3)+ 层内微变化(防机械) | 4c47b16 |
| v8 | stab 层大修:刺刀半音外音锯齿 → 和弦分解(碰撞 0) | 3af40d4 |
| v8.1 | 贝斯可听性大修(sidechain 温柔化 + 高把位化 + EQ) | 2bf909e |
| v8.2 | stab 去碎片化:刺刀密度 2/4/3/2 + hook 乐句化(长音喘息) | 5e5e459 |
| S1 | 子节1《低音入场版》:删 stab + bass 平和化(8 分脉冲) | 63d0b9d |
| S1.1 | 去 bass bend 弹簧音效 | 851cd66 |
