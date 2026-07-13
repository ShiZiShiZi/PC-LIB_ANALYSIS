# HarmonyOS PC —— 目标平台能力画像（由 harmony-pc-capabilities.json 渲染，勿手改本 .md）

> 最近联网同步：2026-07-08T03:23:04.395Z

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
| .NET / CLR 运行时（C#/F#） | ❌ 不支持 | 用户确认 .NET 当前鸿蒙不支持 + 真机 HNP 无 dotnet/mono | 2026-07-13 | .NET / CLR / Mono 运行时当前**鸿蒙 PC 不支持**（用户确认；真机设备 3BT0124820000152 HNP 无 dotnet/mono；社区已移植运行时清单不含 .NET）。C#/.NET 库运行前提=不支持（functional_viability=blocked_external）；若社区后续提供 .NET 移植可翻转。 |
| PyTorch / libtorch | ❌ 不支持 | 真机实测(设备 3BT0124820000152, HongMeng 1.12.0, 2026-07-13) | 2026-07-13 | 真机 HNP 无 libtorch；无 PyTorch 移植证据；FBGEMM 等依赖无法运行。 |
| TensorFlow / libtensorflow | ❌ 不支持 | 真机实测(设备 3BT0124820000152, HongMeng 1.12.0, 2026-07-13) | 2026-07-13 | 真机 HNP 无 libtensorflow；无 TF 移植证据；tensorflow-onnx 依赖无法运行。 |
| Bare JavaScript 运行时 | ❌ 不支持 | 真机实测(设备 3BT0124820000152, HongMeng 1.12.0, 2026-07-13) | 2026-07-13 | 真机无 Bare 运行时；bare-fs/bare-os 依赖（libuv 本身经 Node 可用，但 Bare 运行时缺）。 |
| Tauri (Rust webview 框架) | ❌ 不支持 | 真机实测(设备 3BT0124820000152, HongMeng 1.12.0, 2026-07-13) | 2026-07-13 | 真机无 Tauri webview/窗口/事件循环支持；plugins-workspace 依赖（系统 ArkWeb 存在但非 Tauri 绑定）。 |
| MPI (MPICH) | ❌ 不支持 | 真机实测(设备 3BT0124820000152, HongMeng 1.12.0, 2026-07-13) | 2026-07-13 | 真机 HNP 无 MPICH；MPICH_jll 需 arm64 交叉编译产物，当前无。 |
| libjulia 嵌入 + CPython/Julia 双运行时共存 | ❌ 不支持 | 真机实测(设备 3BT0124820000152, HongMeng 1.12.0, 2026-07-13) | 2026-07-13 | 真机 HNP 无 julia；jnumpy 需可嵌入 libjulia(jl_init_with_image)+ 与 CPython 同进程双 GC 共存，未证。基座 Julia 运行时另见 runtimes.julia（社区版可装）。 |

## 命令行工具 / 外部二进制（shell-out 型库/应用依赖的独立可执行程序在鸿蒙 PC 的可用性）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| nmap 网络扫描工具 | ❌ 不支持 | 人工核实：OpenHarmony PC C/C++ 预编译包(cmd-pkgs) 未收录 nmap；且 nmap 的 raw socket/抓包扫描依赖鸿蒙 PC 沙箱/自研内核不提供的底层网络能力 | 2026-07-09 | shell-out 型库(如 Ullaakut/nmap 的 Go 封装)依赖此外部二进制：库代码本身纯语言、可交叉编译(porting_class 可为 no_adaptation)，但目标缺此工具则功能受阻(functional_viability=blocked_external)。check 置 null 为人工策展——不因 cmd-pkgs 是否收录该包而自动翻转(能否运行还取决于 raw socket 能力)。若鸿蒙后续提供等价网络探测工具，可经使用端 WithBinaryPath 指定替代二进制 |
| Chromium / CDP 可控浏览器(远程调试自动化) | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-electron-vite-React应用-OHElectron-HAP.md | 2026-07-13 | Chromium 114 内核存在(OH-Electron 25;系统 ArkWeb 亦 Chromium 系)。但独立 Chromium 暴露 --remote-debugging-port / CDP 自动化端点(rod/puppeteer 式)未确认——浏览器自动化库依赖此外部端点。 |
| 设备端构建工具链 (CMake/ninja/make/git/binutils/clang-llvm) | ✅ 已支持 | 真机实测(设备 3BT0124820000152, HarmonyOS HongMeng 1.12.0, root 域探针, 2026-07-13) + memory/platform/鸿蒙PC-HNP包与PATH.md | 2026-07-13 | 设备端 HNP 实测已装:cmake/ninja/make/gawk/grep/binutils/bash/gdb/git(2.49.0)/ohos-sdk(clang-llvm)/node/python/ruby/perl/pkg-config/patchelf/**autoconf/bison/flex/m4/gettext/gperf/groff**——故 **on-device autotools 完整可用**(crosstool-NG 类 configure+make 可跑，纠正旧「autoconf/automake 未确认」)；aarch64 端上原生编译(clang+cmake+ninja)可行。 |

## JDK 内部模块开放性（Java 应用/工具常依赖）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| jdk.attach / sun.tools.attach（进程 attach） | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-VisualVM-JVM-Swing应用移植.md | 2026-07-13 | OH-AWT JDK 为 JRE(无 tools.jar)须补 com.sun.tools.attach；OH libattach.so 已导出 attach 所需 native；attach socket 目录为沙箱路径。VisualVM 真机 attach 验证。 |
| jdk.internal.jvmstat / sun.jvmstat（性能计数器） | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-VisualVM-JVM-Swing应用移植.md | 2026-07-13 | jvmstat/hsperfdata 本地进程发现真机可用(纯 Java)；完整计数器读取随 attach 通道。 |
| java.management / jdk.management（JMX） | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-VisualVM-JVM-Swing应用移植.md | 2026-07-13 | JMX 依赖 attach/management-agent 通道，须匹配 OH tools.jar/provider；随 attach 一并可用。 |
| JVMTI（native agent 接口） | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-VisualVM-JVM-Swing应用移植.md | 2026-07-13 | JVMTI native agent 接口——OH libattach.so 导出所需 native；profiler/调试 agent 可挂载(受签名/权限约束)。 |
| --add-opens / --add-exports 启动参数支持 | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-VisualVM-JVM-Swing应用移植.md | 2026-07-13 | BishengJDK 基于 OpenJDK，--add-opens/--add-exports/allowAttachSelf 启动参数标准支持。 |

## 桌面 GUI / 窗口栈（GUI 应用生死攸关）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| Headful AWT (java.awt) | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-VisualVM-JVM-Swing应用移植.md | 2026-07-13 | OH-AWT BishengJDK 8 带 headful 桌面后端(AWT 后端 X11→原生 libawt_xawt.so，XComponent/EGL/GLES 渲染)，VisualVM(Swing/AWT)真机运行。 |
| Swing (javax.swing) | ✅ 已支持 |  | 2026-07-07 | swing已有鸿蒙版本 |
| JavaFX | ⬜ 未核实 |  |  | 待核实（是否随附/可装） |
| SWT | ⬜ 未核实 |  |  | 待核实 |
| Qt (C/C++ GUI) | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-Qt6-CMake-GUI应用移植.md、鸿蒙PC-Qt6-qtdeclarative-QtQuick交叉编译.md；third_party_adapters/notepadnext | 2026-07-13 | 社区已提供 Qt 鸿蒙版；Qt6(6.5.6, ohos23)已真机验证——QPA 插件 libplugins_platforms_qopenharmony.so，NotepadNext(Qt6/CMake)已发布，QtQuick 需禁 JIT(QV4_FORCE_INTERPRETER)；Qt5 亦可用。桌面 Qt6/CMake 应用可移植(此前"仅 Qt5"结论已更正)。 |
| GTK (C GUI) | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-GTK应用broadway-ArkWeb-HAP.md、鸿蒙PC-cmd-pkgs预编译GTK栈不可用.md | 2026-07-13 | broadway→ArkWeb(broadwayd HTTP/WS + Web 组件)或源码构建 gdk-ohos(XComponent CPU-blit)路线已真机(nmap GTK GUI .hap)；仅需 ohos.permission.INTERNET(broadway)。⚠ cmd-pkgs 预编译 GTK 栈不可用(glib 静态烘焙冲突/64KB 页崩)，须源码编 glib+GTK。 |
| Electron / CEF (Chromium) | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-electron-vite-React应用-OHElectron-HAP.md、鸿蒙PC-opencode-HAP化-Electron壳.md | 2026-07-13 | OH-Electron 25(引擎 25.3.2, Chromium 114, Node 18.15)真机；纯 JS 应用可直接嵌(appium-inspector 已发)、重应用配 Node24 sidecar(opencode 已发)。注意:<28 无 ESM main/preload、多 BrowserWindow 合成不稳(用单窗)。 |
| 桌面窗口管理器 / 显示服务（是否存在桌面级多窗口环境） | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/platform/鸿蒙PC-窗口几何控制无native只ArkTS.md、鸿蒙PC-XComponent-CPU像素渲染与输入缝.md；memory/adaptation/Qt6/VLC/VisualVM | 2026-07-13 | @ohos.window/Rosen 提供桌面级多窗口环境，Qt6/VLC/VisualVM 已真机多窗运行；无 X11/Wayland，原生窗口几何(resize/move/min/max)无 NDK 通路、须反向桥 ArkTS @ohos.window。 |

## 桌面集成子能力

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| 系统托盘 (SystemTray) | ⬜ 未核实 |  |  | 待核实 |
| 原生文件对话框 | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机) + HarmonyOS SDK 文档：@ohos.file.picker(选择器,DocumentViewPicker,Core File Kit) | 2026-07-13 | @ohos.file.picker(DocumentViewPicker/文档选择器)API 具备；非 Win/GTK 原生文件对话框 drop-in，须经其 picker 适配。 |
| 拖拽 (DnD) / 剪贴板 | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机) + HarmonyOS SDK 文档：@ohos.pasteboard/oh_pasteboard.h(剪贴板)、@ohos.data.unifiedDataChannel/udmf.h(UDMF 拖拽) | 2026-07-13 | 剪贴板经 @ohos.pasteboard(ArkTS)/oh_pasteboard.h(C) API；拖拽经 ArkUI dragController + UDMF(@ohos.data.unifiedDataChannel/udmf.h)。API 具备但非 Qt/GTK 剪贴板/DnD drop-in，须适配。 |
| 多窗口 / docking（如 NetBeans RCP TopComponent） | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-Qt6-CMake-GUI应用移植.md、鸿蒙PC-VisualVM-JVM-Swing应用移植.md | 2026-07-13 | Qt6 Advanced Docking System / NetBeans RCP TopComponent docking 真机运行(NotepadNext/VisualVM)，须绕开 X11 路径改走工具包非 X11 通路。 |
| HiDPI / 多显示器 | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机) + HarmonyOS SDK 文档：@ohos.display(屏幕属性)、oh_display_manager.h/oh_display_info.h | 2026-07-13 | @ohos.display(densityDPI/densityPixels/多屏 getAllDisplays)+ C API OH_DisplayManager 具备，MateBook HiDPI 真机；Win GetDpiForWindow 无 drop-in、须换 @ohos.display。 |
| 字体 / 输入法 (IME) / i18n | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机) + HarmonyOS SDK 文档：字体 freetype/fontconfig/harfbuzz 交叉编译(Qt/VLC 真机渲字)；@ohos.inputMethod(IME Kit) | 2026-07-13 | 字体渲染真机可用(freetype/fontconfig/harfbuzz + Qt/VLC 渲字)；IME 走 @ohos.inputMethod(IME Kit)、i18n 走 ICU。需集成、非直接替换。 |
| 打印 | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机) + HarmonyOS SDK 文档：@ohos.print(打印)、ohprint.h/OH_Print(Basic Services Kit) | 2026-07-13 | @ohos.print(ArkTS)+ ohprint.h/OH_Print(C API)+ PrintExtensionAbility 具备打印框架 API；Ghostscript/CUPS 式打印管线非 drop-in、须经其 API 适配，PC 形态实际可用性待核实。 |
| 屏幕截图 / 显示捕获 | 🟡 部分支持 | 真机实测(设备 3BT0124820000152, HongMeng 1.12.0, 2026-07-13) + KB | 2026-07-13 | root 域 snapshot_display 真机可截屏；native AVScreenCapture NDK 存在；app 域受限、需权限。napi_screenshot/node-screenshots 依赖。 |
| 全局输入注入 / UI 自动化 | 🟡 部分支持 | 真机实测(设备 3BT0124820000152, HongMeng 1.12.0, 2026-07-13) + KB | 2026-07-13 | root/host 域 uinput/uitest 可注入键鼠、驱动 native 控件（GPU-surface UI 除外）；第三方 app 经无障碍/UiTest 向他应用注入受安全策略限制。iohook/pywinauto 依赖。 |
| 设备唯一标识获取 | 🟡 部分支持 | HarmonyOS SDK @ohos.deviceInfo | 2026-07-13 | @ohos.deviceInfo(serial/ODID)提供设备标识；非 D-Bus/getprop drop-in，Node 库需经该 API 适配。devtools-shared 依赖。 |

## 进程 / 安全模型

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| 跨进程 attach / 检视其他进程 (Attach API / JVMTI) | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-VisualVM-JVM-Swing应用移植.md | 2026-07-13 | VisualVM 跨进程 JVM attach 真机：本地进程发现(hsperfdata)纯 Java 即可；完整 attach(堆/线程 dump)须 OH 匹配 tools.jar(LinuxVirtualMachine/LinuxAttachProvider)，OH libattach.so 已导出所需 10 native；attach socket 目录为沙箱路径(非 /tmp)。 |
| ptrace / 调试其他进程 | ⬜ 未核实 | 人工核实(无 app 可用证据)：harmony-pc 知识库仅平台 faultlogger、无 ptrace/minidump 端口 | 2026-07-13 | 截至 2026-07-13 无 app 可用 ptrace / minidump / crashpad / breakpad / libunwind 的真机证据；平台 faultlogger(/data/log/faultlog/faultlogger/cppcrash-*，含信号+syscall#+符号化栈)为独立崩溃捕获手段、非 ptrace 等价。libunwind 需——待核实。 |
| 启动外部进程 (exec/ProcessBuilder) | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/platform/鸿蒙PC-app域执行二进制与JIT限制.md、鸿蒙PC-HNP二进制SELinux-exec限制.md | 2026-07-13 | fork()+execv() 私有 HNP(hnpPackages type=private)内二进制真机可用；公有 HNP node 可直接 spawn。app 域仅能执行私有 HNP 路径 ELF(其余 /data/local/tmp、libs/ 受 XPM/dmverity 非执行限制)；root(hdc shell)域可执行 PIE ELF。 |
| 沙箱 / 权限模型 (ACL，需声明权限) | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/platform/鸿蒙PC-app访问PC用户目录.md | 2026-07-13 | HAP ACL/权限模型完备:module.json5 声明权限 + 运行时 requestPermissionsFromUser 弹窗授予；atm dump -t -b <bundle> 查授予状态。system_grant/user_grant/system_basic 分级。 |

## 应用交付模型

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| 传统桌面应用（JVM + launcher + system JDK，zip 分发） | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-Qt6-CMake-GUI应用移植.md §9、鸿蒙PC-VisualVM-JVM-Swing应用移植.md | 2026-07-13 | 传统「JVM+launcher+system JDK, zip 分发」形态不支持，须重打包为 HAP(hvigor assembleHap)；但桌面 GUI 应用确能以 HAP 交付并真机运行(NotepadNext/VLC/VisualVM)。改造=重打包、非阻断。 |
| ArkTS ability (.hap，签名安装) | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-Qt6-CMake-GUI应用移植.md §9、memory/platform/鸿蒙PC-HNP包与PATH.md | 2026-07-13 | HAP 是鸿蒙 PC 应用交付形态:hvigorw assembleHap 打包、hdc install -r 安装、aa start -b <bundle> -a EntryAbility 启动；原生 .so/资源随包。非 ArkTS 应用亦经 HAP 承载(壳+native/HNP)。 |
| 安装 / 签名要求 | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-VisualVM-JVM-Swing应用移植.md、鸿蒙PC-Qt6-CMake-GUI应用移植.md §9 | 2026-07-13 | DevEco 调试签名(~/.ohos/config profile)绑 bundleName、须注册设备 UDID；CLI 签名可行(VisualVM)。第三方 HAP 从任意源安装受限。受约束但可用。 |

## 架构

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| arm64 (aarch64) | ✅ 已支持 | OpenHarmonyPCDeveloper | 2026-06-23 | 主力架构 |
| x86_64 | ⬜ 未核实 |  | 2026-07-13 | 待核实覆盖情况。现有 OHOS NDK 工具链仅 aarch64-unknown-linux-ohos、已知设备均 arm64(Maleoon/Kunpeng)，未见 x86_64 正/负证据——保持 unknown，勿据此臆断，勿依赖 x86 专有汇编/intrinsics。 |

## 3D / 图形栈（GUI/渲染应用关注）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| OpenGL / OpenGL ES | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-GLFW视窗后端-EGL-XComponent.md | 2026-07-13 | GLES 3.2 真机确认(GL_VERSION=OpenGL ES 3.2)，设备提供 libEGL.so+libGLESv3.so(非 .so.1/GLESv2)。桌面完整 OpenGL(desktop GL)不可用——仅 GLES 子集；GLEW 等 desktop-GL loader 不适用，须直连 GLES。 |
| EGL | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-GLFW视窗后端-EGL-XComponent.md | 2026-07-13 | EGL 真机可用:eglCreateWindowSurface 于 XComponent 的 OHNativeWindow，用 EGL_DEFAULT_DISPLAY；GLFW 的 EGL/GLES 后端已真机(旋转三角形)。 |
| Vulkan | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-GLFW视窗后端-EGL-XComponent.md | 2026-07-13 | Vulkan 真机可用，带 VK_OHOS_surface 扩展(vkCreateSurfaceOHOS，VK_STRUCTURE_TYPE_SURFACE_CREATE_INFO_OHOS，NDK vulkan/vulkan_ohos.h)，非 stub。 |
| Skia 2D 绘制 | 🟡 部分支持 |  |  | ArkUI 绘制基于 Skia；作为三方库直接链接的覆盖待核实 |
| ArkGraphics 3D（原生 3D API） | ✅ 已支持 |  |  | 鸿蒙原生 3D 能力——但需用其 API 重写，非 drop-in |
| Coin3D (Open Inventor 场景图) | ⬜ 未核实 |  | 2026-07-13 | Coin3D(coin3d.org)未见鸿蒙移植记录，且其依赖桌面完整 OpenGL(当前鸿蒙 PC 仅 GLES 子集)——须端口 + desktop-GL→GLES 适配，可行性待核实。Quarter(Qt↔Coin 胶合)随之。 |

## 媒体（音视频编解码/播放/采集）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| @ohos.multimedia（系统媒体能力） | ✅ 已支持 |  |  | 系统提供播放/采集/编解码——但需用鸿蒙 API，非 FFmpeg drop-in |
| 通用视频编解码（FFmpeg/x264 等三方） | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-VLC-autotools媒体应用移植.md | 2026-07-13 | 社区 ohos_FFmpeg(FFmpeg 8.0.1, 非 stub, 4KB 页对齐)可用；VLC 289 插件+libavcodec 交叉编译、h264 播放真机。须交叉编译、非 drop-in；DVD/蓝光与专有硬解(VAAPI/VDPAU/NVDEC/DXVA)不可用。 |
| 音频 I/O（ALSA/PulseAudio/WASAPI 等价） | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-VLC-autotools媒体应用移植.md §8-9 | 2026-07-13 | OHAudio NDK(<ohaudio/*.h>, libohaudio.so, pull/callback 模型)真机出声，裸 root CLI 进程亦可发声；非 ALSA/PulseAudio/WASAPI drop-in，须走 @ohos.multimedia.audio/OHAudio。 |
| 摄像头采集 | ⬜ 未核实 |  |  | PC 形态摄像头采集与权限待核实 |

## 硬件 / 设备访问

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| GPU 通用计算 CUDA | ❌ 不支持 |  |  | CUDA 为 NVIDIA 专有，鸿蒙无等价——相关功能无法移植 |
| OpenCL | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-OpenCL-SDK-适配要点.md | 2026-07-13 | OpenCL 3.0 真机(HUAWEI Maleoon 916 GPU；"HUAWEI OpenCL 3.0 B301")，KhronosGroup/OpenCL-SDK 零改编译、SAXPY 内核跑通(~23GB/s)。须设 OCL_ICD_FILENAMES=/vendor/lib64/passthrough/libOpenCL.so(无标准 ICD 配置)，CL_DEVICE_TYPE 返回非标值。 |
| USB / 串口 | 🟡 部分支持 | OpenHarmony PC C/C++ 预编译包(cmd-pkgs: gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs) + KB | 2026-07-13 | libusb **cmd-pkgs 已预编译**→用户态 USB 访问库可用；USB HID/串口设备**访问权限 app 域受限**(kernel 权限非普通 HAP 可授)、root 域可枚举。@ohos.usbManager 提供 app 层 USB API。libusb/libmtp/usbmuxd/openocd/python-fido2/avrdude/libserialport 依赖。 |
| 蓝牙 | ⬜ 未核实 |  |  | 蓝牙栈与权限待核实 |
| 传感器 | ⬜ 未核实 |  |  | PC 形态传感器可用性待核实 |
| GPU 驱动框架 / DRM-KMS / VAAPI | ❌ 不支持 | 真机实测(设备 3BT0124820000152, HongMeng 1.12.0, 2026-07-13) | 2026-07-13 | 鸿蒙无 Linux DRM/KMS 子系统与 VAAPI；GPU 走 OpenCL/Vulkan/ArkGraphics，libva 类 Linux 显存/显示抽象无等价。 |
| 智能卡 / PC-SC | ⬜ 未核实 | 待查 | 2026-07-13 | @ohos 未见 PC/SC 等价智能卡服务 API；OpenSC 依赖——待查文档确认。 |

## 权限模型（鸿蒙化后需申请的 ohos.permission.*）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| ohos.permission.INTERNET | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-GTK应用broadway-ArkWeb-HAP.md、鸿蒙PC-VisualVM-JVM-Swing应用移植.md、鸿蒙PC-opencode-HAP化-Electron壳.md | 2026-07-13 | ohos.permission.INTERNET 为 system_grant(常授)，网络访问恒可用；本地 loopback HTTP/WS(broadwayd/opencode)真机。 |
| ohos.permission.CAMERA | ⬜ 未核实 |  |  | 摄像头权限授予与 PC 形态可用性待核实 |
| ohos.permission.MICROPHONE | ⬜ 未核实 |  |  | 麦克风权限待核实 |
| ohos.permission.LOCATION | ⬜ 未核实 |  |  | 定位权限在 PC 形态待核实 |
| 读写存储（文件访问） | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/platform/鸿蒙PC-app访问PC用户目录.md | 2026-07-13 | app 沙箱数据目录恒可读写；用户目录 READ_WRITE_DOCUMENTS_DIRECTORY/READ_WRITE_DOWNLOAD_DIRECTORY 为 normal 级、运行时申请授予后按物理路径直接读写；DESKTOP(READ_WRITE_DESKTOP_DIRECTORY)为 system_basic、普通签名不可授；任意路径需 FILE_ACCESS_MANAGER/更高 APL。 |
| ohos.permission.USE_BLUETOOTH | ⬜ 未核实 |  |  | 蓝牙权限待核实 |
| 通知权限 | ⬜ 未核实 |  |  | 通知权限待核实 |

## 原生 / NDK 层（POSIX 子集 · 系统调用 · 工具链 · 常用原生库）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| POSIX/BSD Socket API (socket/bind/connect/send/recv) | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-nmap-autotools交叉编译与真机扫描.md | 2026-07-13 | musl NDK 提供 BSD Socket API，__linux__+__OHOS__ 双宏、多数网络代码零改编译；nmap connect-scan 真机。raw socket/PF_PACKET 仅 root 域(app 域 kernel.net.raw 不可授)。 |
| epoll (epoll_create1/ctl/wait) | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/platform/鸿蒙PC-app域执行二进制与JIT限制.md | 2026-07-13 | libuv epoll 后端真机(opencode 运行)；io_uring 被 seccomp 杀(SIGSYS)须回落 epoll(app 域 LD_PRELOAD 强制 ENOSYS)。 |
| timerfd / eventfd | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：memory/platform/鸿蒙PC-app域执行二进制与JIT限制.md | 2026-07-13 | libuv epoll 回落路径依赖 timerfd(定时器)+eventfd(异步唤醒)，随 epoll 后端真机可用。 |
| POSIX 终端 / TTY / termios(raw-mode 控制台输入) | 🟡 部分支持 | 真机实测(设备 3BT0124820000152, HarmonyOS HongMeng 1.12.0, root 域探针, 2026-07-13) + third_party_adapters/node-pty | 2026-07-13 | termios/tty/raw-mode 真机可用；**PTY 完整:posix_openpt/grantpt/unlockpt/openpty/forkpty 真机 OK**(node-pty 已跑)。但 HAP GUI 无 TTY、纯 TUI 无标准窗口交付形态；setsid/TIOCSCTTY 于 app 沙箱待确认。Go GOOS=ohos 的 x/sys/unix 终端绑定随 Go 运行时。 |
| OpenMP (clang -fopenmp / libomp) | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-C++库交叉编译要点.md | 2026-07-13 | OHOS NDK clang 支持 -fopenmp；libomp 运行时可随应用打包(可移植 C)。NDK 是否预置 libomp 待实测——可静态链接/自带。 |
| BLAS / LAPACK (OpenBLAS) | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/platform/鸿蒙PC-设备Python运行时.md(numpy 预装) | 2026-07-13 | numpy 2.2.1(内置 OpenBLAS)预装且真机可跑——证 BLAS 数值栈运行。独立 OpenBLAS 未入 cmd-pkgs，须交叉编译(C/汇编 aarch64 kernel 可行；LAPACK 需 Fortran，OHOS NDK Fortran 支持待实测)。 |
| libpcap (数据包抓取) | 🟡 部分支持 | 人工核实：harmony-pc 工程实践(真机)：memory/adaptation/鸿蒙PC-nmap-autotools交叉编译与真机扫描.md | 2026-07-13 | nmap raw socket 抓包扫描(-sS/-O/-sV)真机——root 域可用；app 域缺 raw-capture 权限(kernel.net.raw system 级不可授)。离线 pcap 解析不受限。 |
| musl libc / POSIX 子集 (NDK 原生基座) | 🟡 部分支持 | 真机实测(设备 3BT0124820000152, HarmonyOS HongMeng 1.12.0, root 域探针, 2026-07-13) + memory/adaptation/鸿蒙PC-C++库交叉编译要点.md、memory/platform/鸿蒙PC-app域执行二进制与JIT限制.md | 2026-07-13 | OHOS NDK=musl(子集)+libc++；__linux__+__OHOS__+__MUSL__ 三宏、多数 C/C++ 零改编译(triple aarch64-unknown-linux-ohos)。【root 域真机探针 45/46 OK】fork/exec/setsid/posix_spawn、mmap-RWX/mprotect→EXEC/madvise/mlock(W^X 于 1.12.0 放开)、getrandom/getentropy、signals(sigaction/sigaltstack/sigprocmask/SIGWINCH)、thread_local、进程共享互斥锁、AF_INET/AF_UNIX(含抽象)+SCM_RIGHTS、epoll/timerfd/eventfd/signalfd/memfd_create、statx/inotify、文件 I/O(fdatasync/fcntl-lock/flock/hardlink/symlink) 全 OK。**纠正旧记录:pthread_cancel 与 pthread_attr_setaffinity_np 符号在 1.12.0 存在(旧 musl 缺)**；**仍缺:robust mutex(pthread_mutexattr_setrobust)**、open_memstream 静默丢写、SO_PEERCRED/ucred。**app 域叠加限制(KB)**:io_uring 被 seccomp 杀→回落 epoll、raw socket 需系统权限、AF_UNIX bind SELinux EPERM、exec 仅私有 HNP、非系统进程不能 JIT(mprotect EXEC EINVAL→node --jitless/禁 WASM)。🔴 64KB 页对齐 .so dlopen 崩→链接 -Wl,-z,max-page-size=0x1000。 |
| Node N-API / 原生 .node 插件加载 (node-gyp/node-addon-api) | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：third_party_adapters/node-pty、parcel-watcher；plugin/shared/skills/pc-knowledge-lookup case-studies §2-3 | 2026-07-13 | 原生 C/C++ Node 插件(.node)经 OHOS NDK+CMake 直编真机(node-pty→node.napi.node、parcel-watcher→watcher.node；绕过无 OHOS 分支的 node-gyp，PREFIX ''/SUFFIX .node + node-addon-api 头)、process.dlopen 加载。注意:app 域内 spawn 的 node 需 --jitless(禁 WASM)，但 N-API 插件加载本身不受影响。 |
| CPython C-API / ctypes / libpython 嵌入 | ✅ 已支持 | 人工核实：harmony-pc 工程实践(真机)：third_party_adapters/9LIBS-ACCEPTANCE.md、TEST-RESULTS.md、memory/adaptation/鸿蒙PC-pyGLFW-Python绑定库迁移.md；pc-knowledge-lookup errors/E045,E068 | 2026-07-13 | Python C 扩展交叉编译真机(pycosat 30/30、PyWavelets 1031 pass、pyzmq、PyCxx)；libpython3.12 可嵌入(pyGLFW HAP 内 Py_Initialize+PyRun 端到端真机)；ctypes 可用(pyGLFW 纯 ctypes 绑定、OpenCL-SDK 经 ctypes dlopen libOpenCL)。坑:ctypes.util.find_library 崩(无 /sbin/ldconfig)→打补丁返回 None；CFUNCTYPE/libffi 闭包需 W^X，1.12.0 内核已放开。PyTorch/libtensorflow 无证据、不含。 |
| POSIX 共享内存 (shm_open/mmap/进程共享互斥锁) | ✅ 已支持 | 真机实测(设备 3BT0124820000152, HarmonyOS HongMeng 1.12.0, root 域探针, 2026-07-13) | 2026-07-13 | shm_open+ftruncate+mmap(MAP_SHARED)、pthread process-shared mutex(PTHREAD_PROCESS_SHARED)真机 OK；app 域 /dev/shm 可写(1GB tmpfs, KB 已证)。崩溃/卸载残留段不自动清理。 |
| POSIX 命名信号量 (sem_open/sem_close) | ✅ 已支持 | 真机实测(设备 3BT0124820000152, HarmonyOS HongMeng 1.12.0, root 域探针, 2026-07-13) | 2026-07-13 | sem_open(O_CREAT)/sem_close/sem_unlink 真机 OK；sem_unlink 偶报 FileNotFound(KB E022，小差异)。 |
| AF_UNIX 域套接字 (含抽象命名空间 / SCM_RIGHTS) | 🟡 部分支持 | 真机实测(设备 3BT0124820000152, HarmonyOS HongMeng 1.12.0, root 域探针, 2026-07-13) | 2026-07-13 | root 域真机 OK：pathname bind+listen、**抽象命名空间(\0 前缀)bind、SCM_RIGHTS fd 传递(sendmsg/recvmsg)** 全通过(纠正 KB「抽象/fd 传递无证据」)。**app 域** bind 受 SELinux EPERM(KB E024)→需 TCP 回退；SO_PEERCRED/struct ucred 仍缺(E086)。故整体 partial。 |
| 动态加载 (dlopen/dlsym/dlclose) | ✅ 已支持 | 真机实测(设备 3BT0124820000152, HarmonyOS HongMeng 1.12.0, root 域探针, 2026-07-13) | 2026-07-13 | dlopen(libc.so/libc++_shared.so, RTLD_NOW)+dlsym+dlclose 真机 OK(ctypes/原生插件/延迟加载依赖)。注:ctypes.util.find_library 需补丁(无 /sbin/ldconfig, KB E068)。 |
| 文件系统事件通知 (inotify) | ✅ 已支持 | 真机实测(设备 3BT0124820000152, HarmonyOS HongMeng 1.12.0, root 域探针, 2026-07-13) | 2026-07-13 | inotify_init1(IN_NONBLOCK)+inotify_add_watch 真机 OK(fsevents/ReadDirectoryChanges 等价)。 |
| 进程自省 (/proc/self/mem·maps) | 🟡 部分支持 | 真机实测(设备 3BT0124820000152, HarmonyOS HongMeng 1.12.0, root 域探针, 2026-07-13) | 2026-07-13 | root 域 /proc/self/mem、/proc/self/maps 真机可读(崩溃处理/backtrace/自省)；app 域 /proc 部分 SELinux 受限(KB E031)、**跨进程 ptrace/mach_vm_read 未证**(crashpad/breakpad 自崩溃处理可用、他进程调试受限)→partial。 |
| libffi (FFI 动态调用) | ✅ 已支持 | 真机实测(设备 3BT0124820000152, HarmonyOS HongMeng 1.12.0, root 域探针, 2026-07-13) | 2026-07-13 | 设备 HNP 已装 libffi.org；dlopen/闭包(CFUNCTYPE)真机可用(W^X 于 1.12.0 放开, KB E045)。pyobjc-core 等 FFI 库依赖。 |
| GLib / GObject / GIO / GModule | ✅ 已支持 | 真机实测(设备 3BT0124820000152, HarmonyOS HongMeng 1.12.0, root 域探针, 2026-07-13) | 2026-07-13 | 设备 HNP 已装 glib.org；gstreamer 等依赖 GLib 栈可用(注:GTK 场景另见 gui.gtk，cmd-pkgs 预编译 GTK 栈不可用须源码编, KB)。 |
| macOS Objective-C 运行时桥 (Cocoa/Quartz/CoreText) | ❌ 不支持 | 真机实测(设备 3BT0124820000152, HongMeng 1.12.0, 2026-07-13) | 2026-07-13 | pyobjc 依赖 macOS ObjC 运行时 + Foundation/CoreGraphics/CoreText，鸿蒙无等价 ObjC 桥；文本排版须改 @ohos.graphics.text，属重写而非移植。 |

## 原生 C/C++ 库移植状态（cmd-pkgs 预编译 / 需交叉编译）

| 能力 | 状态 | 来源 | 核对时间 | 说明 |
|------|------|------|----------|------|
| SDL2 / SDL3 | ✅ 已支持 | OpenHarmony PC C/C++ 预编译包(cmd-pkgs: gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs) | 2026-07-13 | cmd-pkgs 已预编译 SDL2/SDL3；SDL_image/mixer/ttf 等依赖其运行时（音频/IO/互斥/原子后端随 SDL3）。 |
| Cairo / Pango / HarfBuzz | ✅ 已支持 | OpenHarmony PC C/C++ 预编译包(cmd-pkgs: gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs) | 2026-07-13 | cmd-pkgs 已预编译 cairo/pango/harfbuzz 图形排版栈。 |
| FreeType / FontConfig | ✅ 已支持 | OpenHarmony PC C/C++ 预编译包(cmd-pkgs: gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs) | 2026-07-13 | cmd-pkgs 已预编译 freetype/fontconfig 字体栈。 |
| ncurses / readline | ✅ 已支持 | OpenHarmony PC C/C++ 预编译包(cmd-pkgs: gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs) | 2026-07-13 | cmd-pkgs 已预编译 ncurses/readline。 |
| libogg (Ogg 容器) | ✅ 已支持 | OpenHarmony PC C/C++ 预编译包(cmd-pkgs: gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs) | 2026-07-13 | cmd-pkgs 已预编译 libogg/ogg；theora 等依赖。 |
| APR (Apache Portable Runtime) | ✅ 已支持 | OpenHarmony PC C/C++ 预编译包(cmd-pkgs: gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs) | 2026-07-13 | cmd-pkgs 已预编译 apr；apr-util/apr-iconv 依赖。 |
| BoringSSL (Chromium) | ⬜ 未核实 | cmd-pkgs 未预编译，需 OHOS NDK 交叉编译核实 | 2026-07-13 | cmd-pkgs 未预编译，需 OHOS NDK 交叉编译核实（openssl 已预编译可替代部分；cronet 需 BoringSSL 特定实现，Chromium //base //net 一并较重）。 |
| Apache Xerces-C++ (XML) | ⬜ 未核实 | cmd-pkgs 未预编译，需 OHOS NDK 交叉编译核实 | 2026-07-13 | cmd-pkgs 未预编译，需 OHOS NDK 交叉编译核实（libE57Format 依赖 XercesC 3.2）。 |
| Lua / liblua | ⬜ 未核实 | cmd-pkgs 未预编译，需 OHOS NDK 交叉编译核实 | 2026-07-13 | cmd-pkgs 未预编译，需 OHOS NDK 交叉编译核实（NLua/KeraLua 需原生 liblua5x；库小、交叉编译成本低）。 |
| OpenCASCADE (几何引擎) | ⬜ 未核实 | cmd-pkgs 未预编译，需 OHOS NDK 交叉编译核实 | 2026-07-13 | cmd-pkgs 未预编译，需 OHOS NDK 交叉编译核实（IfcOpenShell 依赖；OCCT 依赖链庞大、交叉编译重）。 |
| Ghostscript | ⬜ 未核实 | cmd-pkgs 未预编译，需 OHOS NDK 交叉编译核实 | 2026-07-13 | cmd-pkgs 未预编译，需 OHOS NDK 交叉编译核实（ghostpdl/Ghostscript_jll 需 gs 二进制/库）。 |
| glibmm / libxml++ | ⬜ 未核实 | cmd-pkgs 未预编译，需 OHOS NDK 交叉编译核实 | 2026-07-13 | cmd-pkgs 未预编译，需 OHOS NDK 交叉编译核实（libepub 依赖；C++ 绑定层需 glib 之上再编）。 |
