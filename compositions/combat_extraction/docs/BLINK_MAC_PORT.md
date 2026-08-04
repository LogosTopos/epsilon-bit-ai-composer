# Blink(温跃层)Mac 适配方案 — 可行性报告与操作手册(2026-08)

> 依据:A Agent 实测(Apple Silicon / macOS 15.7.4 / Godot 4.6.3-stable macOS 通用版 /
> gdsdecomp v2.6.3)。**关键结论:方案 A(直接跑 pck)与方案 B(反编译还原工程)均已实测通过。**

---

## 1. 可行性矩阵

| 方案 | 可行性 | 验证状态 | 工作量 |
|---|---|---|---|
| **A. Mac 版 Godot 直接跑 pck** | ★★★★★ | **已实测:headless 180 帧 exit 0 零报错** | 5 分钟 |
| **B. 反编译还原 + Mac 重导出 .app** | ★★★★★ | **已实测:gdsdecomp 还原工程,编辑器打开零报错,运行 120 帧零错误** | 1-2 小时 |
| C. Wine/Whisky 跑 Windows 版 | ★★★☆ | 未实测(需装 Whisky) | 30-60 分钟 |
| D. UTM 虚拟机 Windows 11 ARM | ★★★☆ | 未实测(UTM 已装) | 1-2 小时 |
| E. 拿到源码直接导出 | ★★★★★ | 取决于用户(QQ 记录/云盘/旧设备) | 20 分钟 |

**技术前提(已实测确认)**:pck 含 project.binary(main_scene = main_menu.tscn,6 autoload);
.gdc 字节码 TOKENIZER_VERSION = **101** = Godot 4.6.3 源码一致(与 4.5.0 相同,
gdsdecomp 自动检测 + `--force-bytecode-version=4.5.0-stable` 均可)。

## 2. 方案 A:直接跑(推荐,5 分钟)

```bash
# 1. 下载官方 Godot 4.6.3 macOS 通用版(153.7MB)
#    https://godotengine.org/download/archive/4.6.3-stable/
unzip Godot_v4.6.3-stable_macos.universal.zip -d ~/Applications/Godot463
xattr -dr com.apple.quarantine ~/Applications/Godot463/Godot.app   # 解除 Gatekeeper

# 2. 运行(核心就一条命令)
~/Applications/Godot463/Godot.app/Contents/MacOS/Godot --main-pack \
  "/Users/topologyw/Documents/QQ下载/Blink/Blink.pck"

# 3. 若 Forward+(Vulkan/MoltenVK)异常,加回退参数:
#    --rendering-driver opengl3
```

无需导出/模板/签名(直接跑终端二进制,不受 Gatekeeper 公证限制)。
**唯一未闭环**:GPU 实际渲染(headless 已验证逻辑层;M 系 GPU + MoltenVK 跑 2D 基本无风险,
闪退就用 opengl3 兜底)。

## 3. 方案 B:反编译还原工程(想要 .app / 改代码时,1-2 小时)

```bash
# 1. 还原工程(gdsdecomp v2.6.3,产物在 /tmp/blink_recovered,已验证)
"/tmp/gdre/Godot RE Tools.app/Contents/MacOS/Godot RE Tools" --headless \
  --recover="Blink.pck" --output=~/Projects/blink-recovered

# 2. 下载导出模板(含 macOS universal 模板,约 1GB)
#    Godot_v4.6.3-stable_export_templates.tpz → 编辑器 Editor/Manage Export Templates

# 3. 编辑器打开还原工程 → 导出 → 新增 macOS 预设
#    CodeSign: ad-hoc(codesign -s -)+ 勾选 "Disable Library Validation"

# 4. 导出 .app 本地运行;公证仅对外分发才需要
```

还原质量:project.godot + 21 个 .gd 反编译脚本 + 6 个 .tscn,main.gd 近乎源码。
**限制**:① 15 个音频 .sample→wav 源不可恢复(缓存文件完好,可运行);② 反编译脚本
格式与源码有细微差异(命名/注释丢失);③ .tscn 为二进制反推,重导出前建议编辑器过一遍。

## 4. 推荐决策

- **只想玩/试**:方案 A,5 分钟。
- **想改代码/做音乐集成 demo**:方案 B(还原工程 → 加 Music/SFX 总线 → 波次状态机 → 导出 .app)。
- **最想要源码**:方案 E——向用户要 project.godot + 源码,20 分钟导出,后续可改可发。

## 5. 研究产物(可复用)

- `/tmp/godot463/`(Godot 4.6.3 macOS 通用版)
- `/tmp/gdre/`(Godot RE Tools v2.6.3)
- `/tmp/blink_recovered/`(还原工程,已实测零报错)
- `/tmp/blink_pck/`(180 文件提取)+ `/tmp/blink_gdc/`(zstd 解压字节码)
