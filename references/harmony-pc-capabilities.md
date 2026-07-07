# HarmonyOS PC —— 目标平台能力画像（由 harmony-pc-capabilities.json 渲染，勿手改本 .md）

> 最近联网同步：2026-06-23T11:11:18.119Z

> 鸿蒙适配评估（dim-9）的准确性 = match(源所需能力, 目标平台能力)。本文件是目标侧事实的单一权威源，库与应用的鸿蒙评估都用它（目标事实与被分析对象无关）。状态：available（已确认支持）/ partial（部分或受限）/ unavailable（已确认不支持）/ unknown（尚未核实）。skill 规则：source 所需能力，目标 available→不计阻碍；partial→partial 阻碍；unavailable→blocker/unadaptable_apis；unknown 且 required→记 target_assumptions + 下调 confidence + notes 说明，禁止据 unknown 臆断为可行。带 check 的行可由 scripts/harmony_caps.js sync 从社区 cmd-pkgs/PyPI 自动核对；非包类行需人工/社区策展。鸿蒙 PC：自研内核（非 Linux ABI），原生层 OHOS NDK（musl + POSIX 子集）。

## 语言运行时（已移植 ⇒ 该语言写的库/应用可跑在其上，运行时本身不是阻碍）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| Node.js | ✅ 已支持 | OpenHarmonyPCDeveloper/docs | 2026-06-23 | 24.13.0（已回合主社区）；JS/TS 可直接跑 |
| Python | ✅ 已支持 | OpenHarmonyPCDeveloper/docs | 2026-06-23 | 3.12.9 / 3.9.x；纯 Python 可直接跑 |
| Java (JDK) | ✅ 已支持 | OpenHarmonyPCDeveloper/docs | 2026-06-23 | JDK 17.0.x / JDK 8；字节码可跑——但 GUI/内部模块/进程能力另见下表，不等于桌面应用即可跑 |
| Rust | ✅ 已支持 | OpenHarmonyPCDeveloper/docs | 2026-06-23 | 1.89+，有 ohos target |
| Go | ✅ 已支持 | OpenHarmonyPCDeveloper/docs | 2026-06-23 | 1.24+ / 1.22 |
| Julia | ✅ 已支持 | OpenHarmonyPCDeveloper/docs | 2026-06-23 | 1.10.6 |

## JDK 内部模块开放性（Java 应用/工具常依赖）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| jdk.attach / sun.tools.attach（进程 attach） | ⬜ 未核实 |  |  | ported JDK 是否随附该模块、是否允许 --add-exports/allowAttachSelf —— 待核实 |
| jdk.internal.jvmstat / sun.jvmstat（性能计数器） | ⬜ 未核实 |  |  | jstat/jvmstat 监控依赖 —— 待核实 |
| java.management / jdk.management（JMX） | ⬜ 未核实 |  |  | 待核实 |
| JVMTI（native agent 接口） | ⬜ 未核实 |  |  | profiler/调试 agent 依赖 —— 待核实 |
| --add-opens / --add-exports 启动参数支持 | ⬜ 未核实 |  |  | 待核实 |

## 桌面 GUI / 窗口栈（GUI 应用生死攸关）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| Headful AWT (java.awt) | ⬜ 未核实 |  |  | 鸿蒙 PC JDK 是否带 headful 桌面后端 —— 待核实 |
| Swing (javax.swing) | ✅ 已支持 |  | 2026-07-07 | swing已有鸿蒙版本 |
| JavaFX | ⬜ 未核实 |  |  | 待核实（是否随附/可装） |
| SWT | ⬜ 未核实 |  |  | 待核实 |
| Qt (C/C++ GUI) | ✅ 已支持 | https://gitcode.com/OpenHarmonyPCDeveloper (人工核实) | 2026-07-07 | 社区已提供 Qt 鸿蒙版，只提供了Qt5，如果使用Qt6需要降级 |
| GTK (C GUI) | ✅ 已支持 | OpenHarmony PC C/C++ 预编译包 (gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs) — gtk | 2026-06-23 | — |
| Electron / CEF (Chromium) | ✅ 已支持 |  | 2026-07-07 | Electron已有鸿蒙版本 |
| 桌面窗口管理器 / 显示服务（是否存在桌面级多窗口环境） | ⬜ 未核实 |  |  | 鸿蒙 PC 是否提供传统桌面窗口环境 —— 待核实 |

## 桌面集成子能力

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| 系统托盘 (SystemTray) | ⬜ 未核实 |  |  | 待核实 |
| 原生文件对话框 | ⬜ 未核实 |  |  | 待核实 |
| 拖拽 (DnD) / 剪贴板 | ⬜ 未核实 |  |  | 待核实 |
| 多窗口 / docking（如 NetBeans RCP TopComponent） | ⬜ 未核实 |  |  | 待核实 |
| HiDPI / 多显示器 | ⬜ 未核实 |  |  | 待核实 |
| 字体 / 输入法 (IME) / i18n | ⬜ 未核实 |  |  | 待核实 |
| 打印 | ⬜ 未核实 |  |  | 待核实 |

## 进程 / 安全模型

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| 跨进程 attach / 检视其他进程 (Attach API / JVMTI) | ⬜ 未核实 |  |  | 沙箱/权限是否允许 —— profiler 类应用核心依赖，待核实 |
| ptrace / 调试其他进程 | ⬜ 未核实 |  |  | 待核实 |
| 启动外部进程 (exec/ProcessBuilder) | ⬜ 未核实 |  |  | 待核实是否受限 |
| 沙箱 / 权限模型 (ACL，需声明权限) | ⬜ 未核实 |  |  | 桌面应用的权限申请机制 —— 待核实 |

## 应用交付模型

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| 传统桌面应用（JVM + launcher + system JDK，zip 分发） | ⬜ 未核实 |  |  | 鸿蒙 PC 是否支持此形态 —— 决定整条打包路径，待核实 |
| ArkTS ability (.hap，签名安装) | ⬜ 未核实 |  |  | 若只支持此形态，则非 ArkTS 应用需重打包/重写 —— 待核实 |
| 安装 / 签名要求 | ⬜ 未核实 |  |  | 待核实 |

## 架构

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| arm64 (aarch64) | ✅ 已支持 | OpenHarmonyPCDeveloper | 2026-06-23 | 主力架构 |
| x86_64 | ⬜ 未核实 |  |  | 待核实覆盖情况 |

## 3D / 图形栈（GUI/渲染应用关注）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| OpenGL / OpenGL ES | 🟡 部分支持 |  |  | 鸿蒙图形栈含 OpenGL ES/EGL；桌面完整 OpenGL 覆盖与扩展程度待核实 |
| EGL | 🟡 部分支持 |  |  | 随 GLES 提供；具体版本/扩展待核实 |
| Vulkan | ⬜ 未核实 |  |  | 鸿蒙 PC 上的 Vulkan 可用性与版本待核实 |
| Skia 2D 绘制 | 🟡 部分支持 |  |  | ArkUI 绘制基于 Skia；作为三方库直接链接的覆盖待核实 |
| ArkGraphics 3D（原生 3D API） | ✅ 已支持 |  |  | 鸿蒙原生 3D 能力——但需用其 API 重写，非 drop-in |

## 媒体（音视频编解码/播放/采集）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| @ohos.multimedia（系统媒体能力） | ✅ 已支持 |  |  | 系统提供播放/采集/编解码——但需用鸿蒙 API，非 FFmpeg drop-in |
| 通用视频编解码（FFmpeg/x264 等三方） | ⬜ 未核实 |  |  | 三方编解码库在鸿蒙 PC 的可用/移植情况待核实 |
| 音频 I/O（ALSA/PulseAudio/WASAPI 等价） | ⬜ 未核实 |  |  | 底层音频 I/O 后端待核实；建议走 @ohos.multimedia.audio |
| 摄像头采集 | ⬜ 未核实 |  |  | PC 形态摄像头采集与权限待核实 |

## 硬件 / 设备访问

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| GPU 通用计算 CUDA | ❌ 不支持 |  |  | CUDA 为 NVIDIA 专有，鸿蒙无等价——相关功能无法移植 |
| OpenCL | ⬜ 未核实 |  |  | 鸿蒙 PC 上 OpenCL 可用性待核实 |
| USB / 串口 | ⬜ 未核实 |  |  | 设备访问与权限模型待核实 |
| 蓝牙 | ⬜ 未核实 |  |  | 蓝牙栈与权限待核实 |
| 传感器 | ⬜ 未核实 |  |  | PC 形态传感器可用性待核实 |

## 权限模型（鸿蒙化后需申请的 ohos.permission.*）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| ohos.permission.INTERNET | ⬜ 未核实 |  |  | 网络访问权限在 PC 形态的授予方式待核实 |
| ohos.permission.CAMERA | ⬜ 未核实 |  |  | 摄像头权限授予与 PC 形态可用性待核实 |
| ohos.permission.MICROPHONE | ⬜ 未核实 |  |  | 麦克风权限待核实 |
| ohos.permission.LOCATION | ⬜ 未核实 |  |  | 定位权限在 PC 形态待核实 |
| 读写存储（文件访问） | ⬜ 未核实 |  |  | 文件/存储权限模型待核实 |
| ohos.permission.USE_BLUETOOTH | ⬜ 未核实 |  |  | 蓝牙权限待核实 |
| 通知权限 | ⬜ 未核实 |  |  | 通知权限待核实 |
