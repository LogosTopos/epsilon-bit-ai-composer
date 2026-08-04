# 《温跃层 / Blink》游戏音乐集成规划(2026-08)

> 依据:D Agent 静态调查(`/Users/topologyw/Documents/QQ下载/Blink/Blink.exe + Blink.pck`,Godot 4.6.3,180 文件,提取物 `/tmp/blink_pck/`)+ 用户游戏设计文档(瞬移+子弹时间+热量系统)+ 搜-打-撤子节体系(母节 v9 + S1/S6 + transitions)。

---

## 1. 游戏身份(调查结论)

- 项目名 **Blink** v0.1.0,"A high-speed teleport bullet-hell combat game",Godot **4.6.3.stable**
- 主场景 `res://scenes/ui/main_menu.tscn`;游戏场景:俯视 `main.tscn` / 横版 `main_sideview.tscn`(横版有"处决!");**单场波次制**(HUD"第 X 波"),无独立关卡
- 6 个 autoload:`GameEngine / SceneManager / WeaponRegistry / GameManager / BulletPool / **AudioManager**`
- **音频现状 = 空白**:全包无 AudioStreamPlayer 节点、无总线布局(仅默认 Master)、无任何音乐文件;`audio_manager.gd` 只是武器→音效路径数据表,且引用的 `assets/sounds/gun/*.wav` 不存在(实际为 `original/shots/`)→ **该构建的枪声也加载失败,音频子系统是待建状态**

## 2. 机制 → 音乐事件源映射(代码证据)

| 游戏机制 | 代码信号/状态 | 音乐响应(子节体系) |
|---|---|---|
| 瞬移 | 输入 `teleport`,信号 **`on_player_teleported`** | 音效层(游戏端 fx 瞬移脉冲);音乐不切节(无前后摇,事件级响应) |
| 子弹时间/时停 | HUD"时停 启用/待命" + `bullet_time_tint` 调色 | **S-BT 子弹时间子节**(时间冻结人格)——TODO 新建 |
| 热量 | 武器 `heat_cost` + HUD"热量/散热 %" | 热量 >70%:引擎内混入低频轰鸣层(stems 垂直混音,不切节) |
| 护盾 | `ShieldArea`、`bullet._shield_intercept` | 音效层;瞬移清层 → 无音乐事件 |
| 换弹/弹夹 | "换弹/弹夹已空/弹药不足" | 1-2 小节呼吸微节(transitions.py 可加元素) |
| 波次 | HUD"第 X 波" | **波次切换 = 子节切换点**(见 §4) |
| 武器 | 7 武器(手枪…激光枪),单发/点射/全自动/快慢机,recoil_knockback/vibration | 音效层(不占子节);后坐力震动与音乐 kick 无冲突(低频窗口 25% 已留) |

## 3. 场景 → 子节映射(搜-打-撤体系)

**当前可用(已交付)**:SDC v1 = S1 搜刮 → 母节战斗 → S6 结算(1:42,riser/crash_stop 转场,无留白)。

| 游戏时刻 | 子节 | 状态 |
|---|---|---|
| 菜单/准备 | 母节变体或 S1 轻版(循环,可长) | 待做(需"可长时间循环"变体) |
| 波次前/搜刮间隙 | S1 搜刮·低音入场 | ✅ 已交付 |
| 常规交火 | 母节 v9(战斗高潮段,14 层满配) | ✅ 已交付 |
| 波次升级(第 3/5/7 波…) | 母节 cycle1(轮次微变)或 S4 重做版 | 母节 cycle1 ✅;S4 待按红线重做 |
| **时停瞬间** | **S-BT 子弹时间子节(TODO)** | 新建:密度骤降+心跳+时间晶体,进出用"时间折叠"转场 |
| 撤离/倒计时 | S5 重做版 | 待按红线重做(去掉 32 分两八度 riser/hook 叠置) |
| 结算 | S6 结算·尘埃落定 | ✅ 已交付 |
| 剧情抢救(主线,炸弹冲击波窗口) | S-抢救(TODO,倒计时 tick-tock + 冷静精英) | 远期 |

**子节创作红线(STATUS 教训 #8,双因)**:① 不用/弱化 stab(brass ≤ 母节 62-76 或删,M3 只留 timpani/kick/bass 三件套,riser 不加密);② 音高一律母节素材原位,不移调/不叠置/不扩展音区。S4/S5 按此重做后才可进入本映射。

## 4. Godot 集成方案(待实施,游戏侧)

1. **总线**:新建 `Music`(stems 5 条子总线或 1 条 + 5 播放器)与 `SFX` 总线;audio_manager.gd 里挂音乐播放器(AudioStreamPlayer ×5 = 5 stems 垂直混音,或单播放器播预混 SDC 成品)
2. **音乐资源**:按 `assets/sounds/` 惯例用 **.ogg**;交付 = 母节 stems ×5(24-bit 建议)+ SDC v1 预混成品 + 各子节预混成品
3. **波次切换逻辑**(游戏侧):`GameManager` 波次事件 → 音乐状态机:S1(波前)→ 母节(战斗)→ S6(结算);切换点 = 4 小节边界 + transitions 元素(游戏内只做 gain 渐变,过渡小节由音乐侧预渲染——**推荐**:音乐侧把"母节 + riser + S6"按 SDC v1 结构预混,游戏内只切换整段,简单可靠)
4. **时停**(S-BT 落地前的最低可行方案):时停时 `bullet_time_tint` 同时给 Music 总线挂低通滤波器(AudioEffectLowPassFilter,~800Hz)+ 降速(AudioEffectPitchShift 或 playback speed 0.5)——不用切子节,先用总线效果模拟时间冻结;S-BT 子节完成后切换为真正的子节切换
5. **瞬移/枪声**:全部走 SFX 总线,与音乐无关;低频窗口(25% 低频占比)已为脚步/爆炸预留
6. **响度**:stems 与成品统一 -1 dBTP 口径(E Agent 已修复压码链);游戏内按场景调增益,不做二次归一

## 5. 待办清单(优先级)

| # | 项 | 说明 |
|---|---|---|
| 1 | **S-BT 子弹时间子节** | 时间冻结人格(心跳+晶体+密度骤降)+"时间折叠"转场元素(进:音符拉长;出:32 分滚+密度骤回) |
| 2 | S4/S5 按红线重做 | 去 stab 强调 + 音高原位;S5 保留 176 BPM 与 32 分 hat 即可 |
| 3 | 菜单循环变体 | 母节/S1 的"可无限循环"菜单版(无起承转合) |
| 4 | 24-bit stems + loop 点交付 | 母节 stems(loop 2.857s 起/22.857s 长)+ zip 打包给 FMOD/Wwise 或 Godot 总线 |
| 5 | Godot 集成 demo | Music/SFX 总线 + 波次状态机 + 时停低通(AudioManager 改造) |
| 6 | S-抢救(远期) | 主线剧情场景,tick-tock + 冷静精英 |

## 6. 调查产物(供后续使用)

- `/tmp/blink_pck/`(180 文件提取)+ `/tmp/blink_pck_extract.py`(解析器)
- `/tmp/blink_gdc/` + `blink_gdc_decompress.py`(zstd 解压 .gdc 字节码)
- `/tmp/qoa_probe.c`(QOA 音频解码器,可提取音效听)
- 游戏侧事件源:`on_player_teleported`、时停 tint、波次 HUD、热量 HUD、护盾拦截
