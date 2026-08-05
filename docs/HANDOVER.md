# 交接文档 — ε-bit-ai-composer(2026-08 会话全量交接)

> **给新 Agent 的开工指引**:先读本文档,再读 `compositions/combat_extraction/docs/STATUS.md`(音乐侧权威)、`compositions/combat_extraction/docs/BLINK_ARCHITECTURE.md`(游戏侧权威)、`README.md`(对外口径)。所有结论均来自实际执行与实测。

---

## 1. 项目现状一句话

两条主线全部贯通:
1. **音乐创作流水线**:LLM 设计 → Python/mido 确定性 MIDI → FluidSynth 双音色库渲染 → stems 混音 → TP 限幅压码 → 五维审计,一键全量 24 秒(`build_all.sh`)
2. **游戏配乐集成**:母节/子节动态音乐体系已实际接入 Godot 游戏《Blink》(温跃层原型),含游戏内教程、死亡结算界面、触控板适配;仓库已推送到 GitHub(public)

## 2. 本会话历程(按阶段,含提交号)

### 阶段一:母节 v9(stab 完全辅助化)
- 用户判定 v8 及格但 stab 层有缺陷 → 分析 4 缺陷(力度超标/密度过剩/音区挤占/功能冗余)→ v9 落地(`7dadc60`):brass 1/2/2/0 + vel 62-76、rhythm 只轮 2/4 反拍、riser 42-72、M3 76、混音 0.95/-26dB;**audit 新增第 5 维"stab 辅助度"**(每圈 ≤110 音、hook≤84、其余≤78 含 humanize 口径)
- 实测:stab 占比 -28dB"旋律可闻" → **-35.9dB 垫底**;用户验收通过
- v2-v8 实验归档:`archive/combat_extraction/pre_v9_mother/`(`aa35956`,git rename 100%)

### 阶段二:子节体系(平行 3 Agent)
- 转场 Agent:transitions.py(5 插入式元素 + 衔接矩阵 36 键)+ demo_playthrough.py;我修复 roll32 kick 跨小节重叠(0.3→0.2 拍)
- 子节 Agent:交付 S2(行进警觉)/S4(绝境压迫)/S5(逃亡冲刺)/S6(尘埃落定),全部人格化(用户教哲学:S1 样板 = 每子节一个音乐人格,素材受控但乐句自由重写)
- `5af0cd6` 子节体系落地 + `3c1d81e` 子节转音频

### 阶段三:用户裁决与红线(重要,不可违背)
- **S4/S5 难听**(用户判定,双因):① 滥用 stab ② 瞎调音高(S4 的 +1 半音多调性、S5 的 32 分两八度 riser/hook 八度叠置)
- **红线永久化**(STATUS 教训 #8):子节创作弃用 stab 元素;音高一律母节素材原位(不移调/不叠置/不扩展音区);子节 = 层开关 + 密度/力度变形 + 人格化乐句重写
- 高质量范例:S1/S2/S6/母节 v9

### 阶段四:SDC v1 与温跃层转向
- **SDC v1**(`ab2713b`):搜-打-撤完整版(S1→riser→母节×2→crash_stop→S6,删 m1-2 留白,1:42),`sections/sdc_v1.py`
- 渲染链路审计(E Agent)→ P0 落地(`3dc2bed`):压码制度化(encode_mp3.py,TP 限幅修复 **-0.5→-1.0 dBTP**)、并行渲染(2.46×,md5 一致)、增量缓存
- 链路 v2(我手工,`66acbc6`):校验门、按 mid 分目录的增量修复、export_stems.py(24-bit 单圈 loop + zip)、build_all.sh
- 温跃层音乐设计 v2(`ce07c26`,B Agent 竞品研究校准):时停**音乐不变速**(168 保持,低通 800Hz 抽层,变速只给音效);转场只动 stem 权重;14 层归并 5 档;stinger 系统

### 阶段五:Blink 游戏本体(调查 + 适配 + 集成)
- D Agent 调查:`Blink.exe + Blink.pck` = **温跃层早期原型**(Godot 4.6.3,180 文件,波次制);机制信号全找到(teleport/时停 tint/heat_cost/ShieldArea);**音频子系统空白**(无总线无音乐,连枪声路径都是坏的)
- Mac 适配(A Agent):**Godot 4.6.3 直接 `--main-pack` 跑 pck 实测通过**;gdsdecomp 反编译还原工程实测通过(`/tmp/blink_recovered`,21 脚本)
- 安装 Godot → `/Applications/Godot.app`;桌面「启动Blink.command」
- 架构研究 + 音乐插入方案:`docs/BLINK_ARCHITECTURE.md`(我逐文件阅读 4804 行)
- 教程:文档教程(`docs/BLINK_TUTORIAL.md`)+ 游戏内教程(Agent 超时失败后我亲手写 tutorial.gd/.tscn,7 步真实状态判定)

### 阶段六:游戏集成三轮迭代(工作副本 `~/Projects/blink-recovered`)
- **v1**(`28287c0`):Music/SFX 总线 + MusicManager 三态状态机(PREPARE=S1 循环/BATTLE=母节 5 stems 垂直/CALM=S6)+ 时停低通 + 热量>70% 加成 + 枪声路径修复
- **v2**(`4dcca6d`,用户试玩反馈):**K 键替代右键瞬移**(触控板适配,player/sideview/tutorial 三处);音乐循环双保险修复(finished 重播);高波变奏(wave≥4);stinger 击杀重音(M3 音头素材,限流 1.5s)
- **v3**(`d086bc4`):死亡结算界面(波次/得分 + 重新开始/返回/退出按钮);无限波次确认;教程内死亡 R 重开;横版死亡补 CALM
- 验证:headless 各场景 180-240 帧零 ERROR

### 阶段七:整理与发布
- README 重写(技术路径图/作品清单/依赖/音源库/快速开始/踩坑沉淀)+ TECH_STACK §A(`ba5126c`)
- GitHub:`LogosTopos/epsilon-bit-ai-composer`(public,master=ba5126c);早期内容存档分支 `archive/github-legacy`;误建空仓库 `ai-music-composer` 未删(缺 delete_repo scope)

## 3. 当前状态清单

### 音乐侧产物(compositions/combat_extraction/)
| 产物 | 文件 | 说明 |
|---|---|---|
| 母节 v9 双版 | Combat_Extraction(.mid/.mp3)+ v9_synth/v9_trumpet | 主成品 = 合成器版 |
| SDC v1 | Combat_Extraction_SDC_v1.mid/.mp3 | 搜-打-撤完整版 1:42 |
| 子节成品 | S1/S2/S6 + **S4/S5 v2(红线重做)** + **S-BT(子弹时间)** | 旧 S4/S5 已归档 → archive/combat_extraction/deprecated_s4_s5/ |
| 连播 demo | Combat_Extraction_Playthrough.mid/.mp3 | 3:01(动机桥转场,已切 v2) |
| **无缝大循环** | Combat_Extraction_Loop.mid/.mp3 | **3:03,128 小节宏观框架版(4 幕×32 小节×8 小节演化档,单一连续发展非拼贴),循环点自然闭合,可单曲循环**;build_loop.py --cycle N |
| 转场库 | sections/transitions.py | 12 元素:5 基础 + time_fold/unfold + loop_return + 4 动机桥(step_up/engine_start/morph_crisis/accel_roll);衔接矩阵 14 条 |
| 渲染链路 v2 | build_all.sh / build.sh / mix_stems.py / encode_mp3.py / export_stems.py / audit_v7.py | 一键全量;循环成品自动裁混响尾 |
| 文档 | docs/STATUS.md(权威)/ ARCHITECTURE / THERMOCLINE_MUSIC_DESIGN / BLINK_ARCHITECTURE / BLINK_MAC_PORT / BLINK_TUTORIAL |
| 归档 | GAME_THERMOCLINE(集成规划,已被 BLINK_ARCHITECTURE 取代)/ COMPOSITION_PLAN / DIAGNOSIS_v6 / PLAN_v7 / ROADMAP → archive/combat_extraction/pre_status_docs/ | |

### 游戏侧工程(~/Projects/blink-recovered,非 git 仓库)
- 还原工程 + 集成:MusicManager(autoload)、tutorial 场景、死亡界面、K 键、枪声修复
- 音频资源 assets/music/:prepare_loop.wav(S1)/ calm_once.wav(S6)/ battle_stems/*.wav(母节 5 stems)/ stinger.wav
- 运行:桌面「启动Blink.command」= `Godot --path ~/Projects/blink-recovered`;原版 = `--main-pack ".../QQ下载/Blink/Blink.pck"`
- 原版 pck 位置:`/Users/topologyw/Documents/QQ下载/Blink/`

## 4. 环境与工具(实测版本)

| 项 | 值 |
|---|---|
| Python | /opt/anaconda3/bin/python3(3.13)|
| FluidSynth | 2.5.7(渲染 120-200× 实时)|
| ffmpeg | 8.1.2 |
| Godot | 4.6.3 → /Applications/Godot.app |
| 音色库 | soundfonts/(MuseScore_General 205MB + GUGS 31MB + SGM 247MB,不入库)|
| 网络 | Clash Verge 代理 127.0.0.1:7897;git/gh 需 -c http.proxy |
| 缓存纪律 | 运行 Python 前 `rm -rf __pycache__ lib/__pycache__ layers/__pycache__ sections/__pycache__`;stems 增量缓存按 mid 分目录,勿整体 rm(除非 --full)|

## 5. 已知问题与待办(优先级排序)

1. **S-BT 子弹时间子节**(设计已定稿,未实现):时间冻结人格,禁 stab,音乐不变速(低通抽层),time_fold/time_unfold 转场元素
2. **S4/S5 按红线重做**:弃移调/弃叠置/弃 stab 强调(S5 保留 176 BPM + 32 分 hat 即可)
3. **横版 main_sideview.gd 缺 BATTLE 音乐挂点**(进横版战斗不切 BATTLE,一行:MusicManager.set_section)
4. **热噪层**(热量专用素材,当前只有 bass/drums +2dB 近似)
5. **.app 正式打包**(当前 `Godot --path` 直跑;方案 B 流程见 BLINK_MAC_PORT.md)
6. S-抢救(主线剧情场景,远期)/ 菜单循环变体
7. ~~ai-music-composer 空仓库删除~~(2026-08-05 核实:仓库已不存在,已删),遗留:GH_TOKEN 环境变量阻碍 token refresh(不影响日常使用)
8. 横版教程覆盖(tutorial 目前只用俯视 main.tscn)

## 6. 给新 Agent 的纪律清单

- 子节创作:禁 stab、音高原位、人格化(见 STATUS 教训 #8)——**用户裁决,不可回退**
- 缓存纪律、双库渲染顺序不可反(§4)
- 子 Agent 分工时:文件所有权隔离、交接走文件、完成后父会话验证(trust but verify)
- 渲染/压码一律走 build_all.sh / encode_mp3.py,不要手工 ffmpeg 裸压(TP 口径)
- 改游戏工程前先读 ~/Projects/blink-recovered 对应脚本 + docs/BLINK_ARCHITECTURE.md;headless 验证:`Godot --headless --path ~/Projects/blink-recovered res://scenes/... --quit-after 180`
- 提交:音乐侧改动提交到本仓库;游戏工程非 git,改动记录更新到 BLINK_ARCHITECTURE.md 实施状态节
