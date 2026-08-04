# Blink(温跃层)架构研究 + 音乐插入方案(2026-08)

> 依据:还原工程(/tmp/blink_recovered/,gdsdecomp 反编译,21 脚本 4804 行)逐文件阅读。
> 游戏 = Godot 4.6.3,俯视(main.tscn)+ 横版(main_sideview.tscn)双模式,波次制。

---

## 1. 架构总览

```
autoload(6,均 process_mode=ALWAYS)
  GameEngine       FPS 设置(enemy_count_test=5 测试波敌数)
  SceneManager     场景切换
  WeaponRegistry   武器数据表(7 武器)
  GameManager      全局状态:score / wave / enemies_alive / game_running / inventory_open
  BulletPool       子弹池
  AudioManager     音频中枢(动态 AudioStreamPlayer + 并发限制 + 变速)

场景
  main_menu.tscn → main.tscn(俯视)/ main_sideview.tscn(横版)+ settings_menu
  主场景结构:GameCamera / Player(CharacterBody2D,含 GunPivot/MuzzlePoint/MuzzleLight)
             / Enemies(Node2D,enemy_basic 实例)/ Walls / Floor(程序化生成)
  enemy_basic:状态机 Idle/Chase/Attack/Hit(attack/chase/idle/hit 四文件)
  bullet.tscn + bullet_pool

战斗循环(main.gd)
  _update_waves:enemies_alive==0 → 2s 后 _spawn_wave()
  _spawn_wave:wave+=1,敌数 = enemy_count_test + wave,随机点生成
```

## 2. 玩家机制(实测代码,player.gd 1102 行)

| 输入 | 动作 |
|---|---|
| WASD / 方向键 | 移动 |
| 鼠标左键 | 射击(按住是否连发取决于快慢机) |
| 鼠标右键 | 瞬移(heat_per_teleport=6.67,清空护盾充能) |
| **Space 按住** | 时停(bullet_time_scale=0.1,Engine.time_scale;松开退出;时停中持续产热 5/s 且无法散热) |
| R / Shift+R | 换弹 / 切快慢机(single/burst/auto 或 slow/fast) |
| V | 散热 venting(heat_dissipation=5/s) |
| 1/2/3 | 切武器 |

热量:capacity 100;瞬移 6.67 / 处决 10(横版)/ 普通枪 0.3-3.0 / 激光 2.0;
时停中 heat_rate 5/s 且不散热 → 时停有总时长上限。护盾:充能层数,瞬移清空。

**状态源(音乐状态机的输入,全部可直接读取)**:
- `GameManager.wave / enemies_alive / game_running`
- `player.heat / heat_capacity`(HUD 已实时显示百分比)
- `player.bullet_time_active`(HUD 用 tint 显示)
- `player.shield_charges / is_reloading / ammo`
- `Engine.time_scale`(=0.1 时停中)

## 3. 音频现状(实测)

- **AudioManager autoload**:每次播放动态 `AudioStreamPlayer.new()` + 并发上限(`_limit_concurrency`)+ 播放完 queue_free
- **枪声已做时停变速**:`play_shot(wid, bullet_time_active)` — 时停中 pitch×0.4、vol-3dB(正是竞品研究的"音效侧变速"路线,已实现!)
- `_load_wav` 手写 WAV 解析(读头+data → AudioStreamWAV);路径 `res://assets/sounds/gun/*.wav`(pck 内是否实际存在待实测——D 调查称引用路径不存在,玩家试玩可确认是否有枪声)
- **无 Music 总线、无音乐播放器、无音乐文件** — 音乐是绿地

## 4. 音乐插入方案(架构级,待实施)

### 4.1 总线(改 AudioManager._ready,约 3 行)
```gdscript
var music_bus = AudioServer.get_bus_index("Master")
AudioServer.add_bus(); AudioServer.set_bus_name(AudioServer.bus_count-1, "Music")
AudioServer.add_bus(); AudioServer.set_bus_name(AudioServer.bus_count-1, "SFX")
# 现有动态播放器挂 SFX:play_shot 等 add_child 后 player.bus = "SFX"
```

### 4.2 MusicManager(新 autoload 或 AudioManager 扩展,~120 行)
- **双模式**:① 5 stems 垂直混音(`AudioStreamPlayer` ×5,stream 来自 `export_stems.py` 的
  24-bit 单圈 loop stems,`loop_mode=LOOP_FORWARD`,母节 loop 2.857s/22.857s)
  ② 预混成品单轨(菜单/波前/SDC 段落)
- **状态机输入**:`GameManager.wave/enemies_alive` + `player.heat` + `bullet_time_active` + `game_running`
- **输出映射**(THERMOCLINE_MUSIC_DESIGN 档位):
  - 菜单/准备 → 准备循环(音量 -∞ 渐入)
  - 波前(enemies_alive==0,wave>0)→ 呼吸段(S1 stems 权重)
  - 战斗 → 母节(stems 全权重;高波 wave≥5 时 bass/drums +3dB)
  - 热量 >70% → 热噪层(stab/atmosphere stems 混入,或 Master 低通)
  - 时停 → **不变速**:Music 总线 AudioEffectLowPassFilter(cutoff 800Hz)+ 抽高频 stems
    (atmosphere/stab 权重 -12dB),保留 drums/bass 心跳——音乐继续 168BPM 走,
    **变速只给音效**(枪声已实现 pitch×0.4)
  - 结算 → S6 stems
- **切换对齐**:段落间切换点对齐小节边界;stems 版用 loop 起点(2.857s 整数倍)估算对齐;
  或预混版直接切整段(插入式转场已在音乐侧渲染,游戏端只做 gain 交叉淡化 0.5-1s)

### 4.3 stinger(事件 → 短促重音)
- 击杀:enemy_base.gd 死亡处理处调用 `MusicManager.stinger("kill")`
  → timpani 38 单音(vel 84)或 fx 短脉冲,落 16 分网格,避让 kick 重音槽(0/1.5/3.0)
- 换弹完成:player.gd `_reload` 完成处 → stinger("reload")
- 波次开始:_spawn_wave() → 短 riser(半小节)

### 4.4 实施清单(改还原工程,重新导出 .app)
1. AudioManager:加 Music/SFX 总线 + 现有播放器挂 SFX(3 行)
2. 新建 `scripts/autoload/music_manager.gd`(状态机 + stems 播放器 + stinger + 低通)
3. project.godot 注册 autoload MusicManager
4. 音频资源:assets/music/ 放 stems 或预混(24-bit .wav 或 .ogg;从本仓库 `dist/stems_24bit/` 复制)
5. main.gd / player.gd / enemy_base.gd 插 3-5 个调用点(状态刷新 + stinger)
6. 导出 macOS .app(ad-hoc 签名,见 BLINK_MAC_PORT.md 方案 B)

### 4.5 实施状态(2026-08 已落地,工作副本 ~/Projects/blink-recovered)
✅ 已实施:① Music/SFX 总线(AudioManager/MusicManager 幂等创建,枪声挂 SFX)
② music_manager.gd 三态状态机(PREPARE=S1 预混循环 / BATTLE=母节 5 stems 垂直
/ CALM=S6 预混),段落切换 0.8s 交叉淡化
③ 时停:Music 总线低通 800Hz 渐入/出(音乐不变速,枪声变速为原版已有)
④ 热量 >70%:bass/drums +2dB
⑤ 场景挂点:main_menu→PREPARE / main._ready→BATTLE / player 死亡→CALM
⑥ 游戏内教程:tutorial.tscn(7 步,复用 main 场景,完成判定基于真实状态)
   + 主菜单"教 程"按钮(替换禁用占位)
✅ 资源:assets/music/prepare_loop.wav(S1 预混 55s 循环)/ calm_once.wav(S6)
   / battle_stems/*.wav(母节 5 stems 16-bit 单圈 22.857s loop)
✅ 验证:--headless --import 零报错;main/tutorial 场景 180 帧零 ERROR
✅ v2(用户试玩反馈):① 战斗音乐循环修复(loop 属性 + finished 重播双保险,
   解决"战斗没结束音乐就停");② 触控板适配:瞬移/处决加 K 键替代右键
   (player/sideview/tutorial 三处);③ 音乐变奏:高波(wave≥4)bass/drums +2.5dB、
   stab/atmosphere -3dB;④ stinger 落地:击杀 → M3 音头短重音(限流 1.5s,
   素材 stinger.wav 自 drums stem 5.357s 处截取)
⏳ 未做:热噪层(热量专用层);.app 重导出(当前 `Godot --path` 直跑)

### 4.6 先做哪个(建议顺序)
1. ✅ 总线 + 预混成品单轨播放(已完成)
2. ✅ stems 垂直 + 状态机(已完成,含时停低通/热量加成)
3. ⏳ stinger 系统(击杀/换弹短促重音,素材规格见 THERMOCLINE_MUSIC_DESIGN §3)

## 5. 输入速查(给教程 Agent 的交叉验证)

移动 WASD/方向键;射击左键;瞬移右键;时停 Space(按住);换弹 R;快慢机 Shift+R;
散热 V;切枪 1/2/3;横版另有处决(近距离)。全部来自 project.godot InputMap + player.gd/_input 实测。
