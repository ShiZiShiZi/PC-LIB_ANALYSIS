---
name: harmony-adaptation
description: Assess the HarmonyOS-NEXT-PC migration class of a third-party library or application along two dimensions — core functionality (the Windows/Linux/macOS intersection) vs platform-difference functionality — judging which capabilities are adaptable vs unadaptable, plus effort, targeting HarmonyOS NEXT PC (self-developed kernel, ArkTS app layer, OHOS NDK native layer, Node-API bridge — no Linux ABI). A SYNTHESIS step over the already-computed native_api / runtime_surface / dependencies / build_env / library blocks. Use for dimension 9 of PC library/application analysis. Model reasoning, prescriptive (gives an adaptation plan).
---

# HarmonyOS PC adaptation assessment (model-driven, synthesis)

The final, **prescriptive** dimension. Earlier dimensions describe *what the library
is and what it touches*; this one answers **"这个库在鸿蒙 PC 上是否可适配、哪些能力不能适配、
要多少工作量"** —— 把移植分级沿**核心功能 vs 平台差异功能**两维评估，逐个判可适配/不可适配，
产出一份带阻碍点、不可适配点清单与工作量的适配方案。

This is a **synthesis** step (综合层，见 `pc-lib-analyzer.md`「两层契约」): you do NOT re-scan the
source, and you **do NOT re-judge facts a feature dimension already established** —— 尤其
GUI/3D/媒体/硬件的鸿蒙支持状态由 `capability_profile`(dim-10) 权威判定，本维度**直接消费**其
`harmony_status`/`specific_hardware`（经 `source_capability`/`caused_by` 回指场景 key），不重查 caps、不重扫。
You reason over the already-filled blocks — `library.ecosystem`/`bindings`, `native_api` (groups +
`category`/`platform`, **以及 `native_api.dynamic_libraries`** —— 运行时经
ctypes/dlopen/LoadLibrary/JNA 动态加载的库), `runtime_surface`
(subprocess/filesystem/network/env/devices), `dependencies`, `build_env`, `capability_profile`, **以及
dim-12 的 `code_partition`（生产代码按复用性分桶的 LOC 统计——工作量估算的量化底座）** —— and
**reuse their `evidence`** (the same `file:line`).

**"不重扫"的确切含义**（避免误伤 `unadaptable_apis[].public_entry`）：指**不重新*发现/推导* dim-6/7/8 已建立的特征事实**
（别再去重新扫平台 API、依赖、场景）；但**查预建 codegraph 索引，把一个已知调用点映射到它的公共入口**——如填
`unadaptable_apis[].public_entry`（见 step 7）——**不算重扫**，那正是"拿前序 `evidence` 当种子追路由"。

## 主旨与原则
**输出契约（下方 Output）是唯一硬约束。** 闭轴取值固定、UI 依赖它们；开放词可自创。
与 dim 8 相反——本维度**给适配建议**（这就是交付物），且是**前序维度的综合产物**，不重扫源码（"不重扫"确切含义见开篇 synthesis 说明——查预建索引把已知调用点映射到 `public_entry` 不算，见 step 7）。
遇到清单外的阻碍类型或路径，尽力归类、自创一个简洁小写值，并在 `meta.observations` 记录。

### 你产出什么 / 归一派生什么（先看这张表，下面各步不再重复这条边界）
`scripts/report_normalize.py` 组装时确定性派生一批字段并**覆盖**你的值（`web/server.js` 是等价镜像，升级存量报告）——
你只产出**可观测量**，派生轴不用填、填了也以派生为准：

| 你（模型）产出 | 归一确定性派生 + 覆盖（单一真相源） |
|---|---|
| `porting_class`（三档**下限**） | `porting_class`：**只升不降**（据 dim-12 `needs_adaptation`/`unadaptable` 桶、`unadaptable_apis`、任一 `blockers[].adaptability` partial/unadaptable）；你的原判留存 `porting_class_model` |
| `unadaptable_apis[].functionality_class`（core/platform_specific，**必填**） | `adaptation_assessment`：核心/平台差异两维小结 + `effective_class`（5 档，拓扑上色 / 难度 floor）+ `overall`（是否可适配总判） |
| `effort.person_days:[lo,hi]` | `effort.level`（5 档：`effective_class` floor × person_days 上界分桶，取高） |
| `effort.breakdown` 的 gui/deps_porting/build_system/testing_verification/packaging 分项 | `effort.breakdown` 的 **recompile** & **api_adaptation**（= 桶 LOC ÷ 速率）；**⚠️ 一旦你产出 breakdown，`person_days` 总量即被丢弃、重算为各分项之和** |
| `blockers`/`target_assumptions`/`required_permissions`/`critical_dependencies`/`compatible`/`key_tasks`/`summary`/`notes` | `meta.harmony_warnings`{code,class} / `_reviewed`；`meta.normalized_version` |

**你的三个关键动作**（其余都是它们的支撑）：① 走判定树定 `porting_class` 三档**下限**；
② 把用到的不可适配功能点填进 `unadaptable_apis` 并标准 `functionality_class`；③ 估 `effort.person_days` 区间。

### 核心框架：移植分级——三档 + 两维（本维度唯一权威定义，后面步骤只引用不重述）

**顶层 `porting_class` 三档闭轴**（你给"下限"，归一只升不降）——三档边界最易混，务必分清：
- **`no_adaptation`（无需适配）**：跑在已移植运行时（Python/Node/Java/**Go/Rust**/Julia）上、**无原生扩展、无平台特有 API**，
  源码零改动即可运行（纯 Go/纯 Rust 交叉编译属工具链重定向，也归此档）。**⚠️ Go/Rust 交叉编译（`GOOS=ohos`/`--target`）
  属工具链自动重定向、不算"适配"——纯 Go/纯 Rust 库就是 `no_adaptation`**，即使有个别 `sys.platform`/`x/sys/unix` 分支，
  只要那些系统调用鸿蒙也提供，仍是 `no_adaptation`。
- **`recompile_only`（仅交叉编译）**：**专指 C/C++ 等原生代码**，只需 OHOS NDK **重新编译**、**零源码改动**、不碰平台/底层特有 API。
  ❌ 不要给纯 Go/Rust/脚本库套 `recompile_only`（它们不需要你手动 NDK 重编）。
- **`needs_adaptation`（需适配）**：**需要真正改动源码**（加鸿蒙平台分支、把某平台 API 换成 @ohos 等价、GUI 层用 ArkUI 重写、换后端…）
  **或有任何用到的功能不可适配**。**⚠️ 与 dim-12 `code_partition` 必须一致**：`recompile_only`/`no_adaptation` 都断言"零源码改动"，
  等价于代码分区里**只有** `reuse_direct`+`recompile_reuse` 两桶；**只要 dim-12 有非空 `needs_adaptation`/`unadaptable` 桶（含换后端、
  加平台分支、禁用某后端——即使只靠构建开关切换），本档就是 `needs_adaptation`。**

**判定树（best-guess 下限，命中即止）**：
> **Q1｜要不要改动源码**（新增鸿蒙分支/换 @ohos API/GUI 层重写/换后端…）**或有任何用到的功能不可适配？**
>   · 要（含有 `unadaptable_apis`）→ **`needs_adaptation`**（再靠给每条不可适配点标 `functionality_class` 让归一分核心/平台差异两维）
>   · 不要 → 继续 Q2
> **Q2｜是不是 C/C++/原生代码、需要手动用 OHOS NDK 重编（只是重编、零源码改动、无平台 API）？**
>   · 是 → **`recompile_only`**
>   · 不是（已移植运行时语言，工具链自动重定向即可跑）→ **`no_adaptation`**

**两维（对 `needs_adaptation` 展开评估）——你给每条不可适配点标 `functionality_class`，归一自动分档、你不必手填 porting_class 细分：**
1. **核心功能（core）** = Windows、Linux、macOS 等平台功能的**交集**（库在各平台都提供的主体能力）。核心功能有不可适配点＝该库核心在鸿蒙上做不全，是最重的情形。
2. **平台差异功能（platform_specific）** = 非交集、**平台特有**的功能（只在某些平台提供）。这类做不到只丢失该平台特性，影响较小。

归一据 `unadaptable_apis[].functionality_class` 派生 `adaptation_assessment`：有 `functionality_class:"core"` 的不可适配点
→ `effective_class:needs_adaptation_core_partial`、`overall:core_blocked`（核心不完全可适配，最重）；仅有 `platform_specific`
→ `effective_class:needs_adaptation_platform_partial`、`overall:adaptable_with_tailoring`；无不可适配点（`unadaptable_apis` 为空）
→ `effective_class:needs_adaptation`、`overall:adaptable`。

**功能点是否可适配（决定进 `blockers` 还是 `unadaptable_apis`）——只问一句：能否用鸿蒙可用的 API 或自行实现把这个功能重建出来？**
- **能 → `adaptable`（进 `blockers`，不进 `unadaptable_apis`）**：功能能在鸿蒙实现，只是**要换成鸿蒙的 API/方案**。
  典型：系统摄像头（各平台接口不同）→ 鸿蒙摄像头 API；X11 窗口 → 鸿蒙 XComponent；epoll/kqueue/io_uring → 鸿蒙 I/O 多路复用/poll 回退；
  Win32/POSIX 差异 → 换 @ohos 或 POSIX 子集；DirectX/Metal → 鸿蒙图形栈；termios/控制台 → 鸿蒙终端 API；注册表 → 鸿蒙配置存储。
  **"没有 drop-in 等价"不等于"不可适配"——能重建就是 adaptable。**
- **不能 → `unadaptable`（进 `unadaptable_apis`，并标 `functionality_class`）**：卡在**机制/硬件/闭源**层、鸿蒙无任何等价且无法自行实现。
  典型：**CUDA/专有 GPU 计算**、**CD 刻录（鸿蒙 PC 无光驱）/NVIDIA 驱动软件**、**闭源二进制库/无源码的预编译 agent**、
  **鸿蒙无法操作的专有内核特性/驱动**、绑定特定硬件设备且无替代。
- **判点：某功能因依赖未鸿蒙化而"被关掉"（如构建时关 `WITH_X`）≠ 自动 `unadaptable`。** 先看那个依赖**能不能移植**：
  开源、可交叉编译/可自行实现的原生库（如 uSockets 的 QUIC 依赖 lsquic）→ **`adaptable`**（把它一起移植、功能不丢，
  移植量计入 `effort.breakdown` 与 `critical_dependencies`），**不进** `unadaptable_apis`；只有当该功能
  **无任何鸿蒙落地路径**（CUDA/闭源/特定硬件）才 `unadaptable`。**按"能不能移植"判，不按"默认关没关"判。**

**场景无法穷举——发挥你的判断力。** 上面是常见判据、不是封闭清单：遇到新场景，据"能否在鸿蒙重建该功能"如实判可适配/不可适配，
据"是各平台交集还是某平台特有"判 core/platform_specific，并在 `meta.observations` 记录新型判据。

**⚠️ 常见误判（据实测报告归纳，务必自查）**：
- ❌ **纯 Go/Rust/脚本库标成 `needs_adaptation`/`recompile_only`** → 应是 `no_adaptation`。有 adaptable 阻碍点不代表要改源码；除非你确实要为鸿蒙改代码，否则别升档。
- ❌ **把"没有现成鸿蒙 API"当成 `unadaptable`** → 能重建就是 `adaptable`（进 `blockers`，不进 `unadaptable_apis`）。`unadaptable` 只留给硬件/闭源/内核机制（CUDA、闭源库、专有内核、CD 刻录、NVIDIA 驱动）。
- ❌ **把某平台特有的不可适配点标成 `core`（或反之）** → 只在 Win/Linux/mac **各平台都提供**的能力才是 `core`（核心功能）；只在某平台提供的是 `platform_specific`（平台差异功能）。标错会让 `overall` 总判偏严/偏松。
- ❌ **"该功能可选/量小"就不列进 `unadaptable_apis`** → 只要用到的功能确实不可适配就**列入并标 `functionality_class`**；"可选/量小/不影响核心"用**低 `person_days` + `notes` 说明** + 标 `platform_specific`（而非 core）表达，让 `overall` 保持 `adaptable_with_tailoring` 而非 `core_blocked`。
- ❌ **dim-12 有 `needs_adaptation`/`unadaptable` 桶却把模块塞进 `recompile_reuse`** → "换后端/加平台分支只是改构建开关不算改源码"是常见误区：只要有模块需要为鸿蒙做**任何**适配动作，就不是"零源码改动"，该模块应进 dim-12 的 `needs_adaptation` 桶。

## 目标平台：HarmonyOS PC（两种部署模型，库默认走「运行时模型」）
鸿蒙 PC 自研内核（**非 Linux ABI**，不能直接跑 Linux ELF / 用 Linux 系统调用）；
原生层 **OHOS NDK**（musl libc + **POSIX 子集**，clang/CMake `ohos.toolchain.cmake`，
产物 `.so`）；架构 arm64 / x86_64。**关键事实：鸿蒙 PC 已移植主流语言运行时**——一个
PC 第三方**库**的自然部署方式是「跑在已移植的运行时上」，运行时本身**不是阻碍**，
真正的移植工作只在它的**原生扩展 / C 依赖 / 平台特有 API**。

**目标平台能力是单一事实源：`references/harmony-pc-capabilities.json`**（机器权威源；`.md` 是它的
渲染视图）。评估前必读——它维护鸿蒙 PC 的语言运行时、JDK 内部模块开放性、桌面 GUI/窗口栈、桌面集成、
进程/安全模型、应用交付模型、架构等能力及其状态（available/partial/unavailable/**unknown**）。
**该画像对库与应用通用**（目标事实与被分析对象无关：一个 Qt **库**与一个 Qt **应用**同样受「Qt 是否
已鸿蒙化」这条事实约束）。基调：**主流语言运行时已移植**（Node/Python/Java/Rust/Go/Julia），所以一个
**库**的运行时本身不是阻碍；但**应用**能否跑还取决于 GUI/进程/交付等目标能力。**先看「该语言是否有
已移植运行时」，有就别假设没有、别据此把可适配的功能判成不可适配。**

**准确性 = match(源所需能力, 目标能力)。结论必须建立在参考里的目标事实上，未核实(unknown)的不要臆测**
（见下 step 4「目标匹配」）。

### 目标侧 API 事实核查（鸿蒙文档技能，可选但优先使用）

运行环境（opencode）可能装有两个全局文档技能（run prompt 会提示可用性）：
**`harmonyos-sdk-api-lookup`**（4000+ 篇官方 API 参考：@ohos 模块/API 签名/**ohos.permission.\* 精确名与授权类型**/
SysCap/起始版本，文件名自带 Kit+模块名）与 **`harmonyos-docs-lookup`**（2860 篇开发指南/FAQ/错误码）。
`arkts-rules` 技能是写 ArkTS 代码的语言规则，评估**默认不用**（仅当目标确为 ArkTS 沙箱应用、
需要佐证 GUI 层重写量时可参考）。

**何时查**（只查驱动结论的项，每库 **≤10 次检索**）：
- 判 platform/hardware 类 blocker 的 `harmony_status`、写 `remediation` 的 `replace_with_ohos` 具体 API 之前；
- 填 `required_permissions[]` 时——**权限名以文档为准**（抄 `ohos.permission.*` 全名 + user_grant/system_grant），
  不要凭记忆拼权限名；PC 形态**可授予性**仍对照 caps JSON 权限模型段；
- 把某 API 判 `unadaptable` 之前——先按「文件名过滤 → 内容搜索」查一轮，**检索无果**才有底气记
  `unadaptable_apis`（rationale 注明「检索无对应 @ohos 能力」）；查到等价 → 降级为 adaptable blocker + remediation；
- 细化 `target_assumptions` 里 unknown 项的 `impact`/`source`。

**怎么查（降级链）**：① 用 opencode 内置 `skill` 工具按名加载（返回文档目录路径与方法说明），
在其目录内按**文件名过滤 → 内容 Grep → 精读**三步检索（文件名信息量大，先 Glob `*关键词*.md`）；
② `skill` 工具不可用 → 直接 Glob/Grep `~/.config/opencode/skills/<name>/`；③ 都不可用 → 按现状仅用
caps JSON，并在 `meta.warnings` 记「未能访问鸿蒙文档技能」。技能自带的 `scripts/*.py` **不要运行**
（保持三脚本白名单），用 Glob/Grep 达到同样效果。

**口径护栏（防误用，必须遵守）**：
- `references/harmony-pc-capabilities.json` **仍是 PC 形态可用性的唯一权威**——SDK 文档是通用
  HarmonyOS（多为手机口径），**API 在文档中存在 ≠ 鸿蒙 PC 可用**；两者冲突时 caps JSON 优先。
- caps JSON 为 unknown 的 required 能力：文档查到 API 存在**不翻转 unknown**、confidence 下调规则
  不变——只把 assumption 写得更具体（如「@ohos.multimedia.audio 在鸿蒙存在（见文档 X.md），PC 形态待核实」）。
- 引用过的文档以**文件名**写入 `evidence`/`source`（如 `系统-网络-Connectivity Kit…-@ohos.wifiManager (WLAN).md`）。

### 两种部署模型（评估口径）
- **模型 A（默认，命令行 / 桌面库）**：库跑在上表的已移植运行时上。运行时**不是阻碍**；
  阻碍点 = 原生扩展（C/C++ via cffi/ctypes/C-API/N-API/JNI）需经 OHOS NDK 重编、C / 系统
  依赖的可移植性、平台特有系统调用 / 外部命令 / `/proc`·`/sys` / 注册表等。库分析**默认
  按此口径**。
- **模型 B（次要，ArkTS 沙箱 GUI 应用）**：应用层 **ArkTS/ArkUI**（运行在 ArkCompiler，
  **不是 Node.js**），ArkTS↔C/C++ 经 **Node-API（napi）** 桥接，应用沙箱化、硬件/系统访问
  受权限(ACL)管控；此口径下 Node 核心模块不可用、需 `@ohos.*` 平替。**仅当目标确为 ArkTS
  应用时才用此口径**，并在 `notes` 注明结论是按模型 B 收紧的。
- **模型 C（整包桌面应用，当 `library.kind == application`）**：被分析对象是**终端用户启动运行
  的应用**（如 VisualVM 这类桌面工具），移植问题 = 「能否在鸿蒙 PC 上**打包并启动运行**」。
  运行时（JRE/Node 等）已移植可复用、不是阻碍；按这些维度判阻碍：
  - **GUI 工具包在 OHOS 是否可用**：Swing/AWT 取决于鸿蒙 JDK 的 AWT/桌面支持；JavaFX/SWT/Qt/
    GTK/Electron 各自判（无对应即重度阻碍）；RCP 平台（NetBeans `org.openide`/Eclipse）要整套
    窗口/模块系统都能跑。
  - **窗口系统 / 桌面集成**：多窗口/docking、系统托盘、文件对话框、拖拽、剪贴板、全局快捷键 ——
    鸿蒙桌面有无对应能力。
  - **启动器与打包**：原生 launcher（`*.exe`/C++ 启动器）需重编；分发格式 → 鸿蒙应用包。
  - **运行期服务**（`runtime_surface.services`）：进程 attach、jvmstat/jstatd、JMX、JNI 原生
    agent —— 若依赖各平台预编译二进制且**无 OHOS 版**（如 VisualVM 的 `libprofilerinterface`），
    列入 `unadaptable_apis`/`blockers`。
  应用走模型 C，**不要**套用「重编 + Node-API 暴露给 ArkTS」的库口径（那是把库链接进别的代码）。

**无论哪种模型，下列仍是真实阻碍点：**
- **外部命令 shell-out**：`dmidecode`/`lspci`/`wmic`/`powershell`/`ioreg`/`smartctl`
  等 —— 沙箱/受限环境不允许或这些工具鸿蒙上不存在 → 多为 `blocker`。
- **内核伪文件 / 平台接口**：`/proc`·`/sys`、Windows 注册表/WMI、Win32 API、macOS
  Cocoa/IOKit —— 无对应或需经 `@ohos.*` 系统能力替代。
- **POSIX 子集缺口**：`fork`、System V IPC、`epoll`/`inotify`、部分 `ioctl`/信号 ——
  musl/OHOS 可能缺失或受限,逐项判 `partial`。
- **Node 核心模块（仅模型 B 下）**：`child_process`、ArkTS 版缺失的 `fs`/`os`/`net`/
  `http`/`process` —— 跑在鸿蒙 Node.js 上时（模型 A）这些基本可用，无需改写。

## 评估步骤（How to assess）
顺序：**框定（1–4）→ 产问题清单（5–9）→ 量化（10–11）→ 收尾（12）**。移植分级的三档/两维/可适配判据/
常见误判**已在上「核心框架」定义**，下面步骤只引用不重述。

1. **先按 `library.kind` 选部署模型**：`application` → **模型 C（整包桌面应用）**，据
   GUI 工具包 / 窗口·桌面集成 / 启动器·打包 / 运行期服务（见上「两种部署模型」）判阻碍与分级；其它（库）→
   模型 A（默认）/ 仅当目标是 ArkTS 应用才 B。下一步「由 ecosystem 定基调」对两类都适用
   （决定运行时是否已移植），但**应用的阻碍重心在 GUI/打包/服务，而非「被链接进别的代码」**。

2. **由 `library.ecosystem` 定基调**（决定运行时是否已移植——这是**推理**，不再 emit 为字段）：默认走模型 A（跑在已移植运行时上）。
   - `python` → 跑在鸿蒙 Python 3.12 上。**纯 Python 无原生扩展 → `no_adaptation`**；含 C 扩展
     （cffi/ctypes/C-API，如 cairocffi/pypdfium2）→ 扩展需经 OHOS NDK 重编 = 真正工作量，据该原生依赖可移植性判档。
   - `nodejs`/JS-TS → 跑在鸿蒙 Node.js 24 上，Node 核心模块基本可用。含 N-API 原生插件 → 插件需 OHOS NDK 重编。
     **仅当目标是 ArkTS 沙箱应用时**才需 `@ohos.*` 重写（此时 Node 核心模块不可用，`needs_adaptation`，并在 notes 注明）。
   - `java` → 跑在鸿蒙 JDK 17 上。含 JNI 原生库 → 原生库需 OHOS NDK 重编。
   - `rust`/`go` → 交叉编译（`GOOS=ohos`/`--target`，工具链自动重定向）→ 纯 Rust/Go 库即 `no_adaptation`，难度低/中。
   - `cpp`/`c` → 默认 `recompile_only`（经 OHOS NDK 重编）；一旦要碰平台特有 API/加鸿蒙分支即 `needs_adaptation`，
     难度由 POSIX 子集缺口 + `native_api` 里的 `platform`/`system`/`hardware` 组数量决定。
   - **运行时已移植 ⇒ 别再据「无运行时」把功能判成不可适配**；核心功能不可适配（`overall:core_blocked`）仅留给
     运行时未移植 **且** 重度平台耦合且无替代的真正无解情形。

3. **消费 `capability_profile`（dim-10 场景画像）——它是 GUI / 3D 渲染 / 媒体 / 特定硬件 四类的鸿蒙支持
   权威源，你在这四类上「消费不重判」。** 它已把本项目是否涉及这四类标好，并**已判定**每个场景的
   `harmony_status`/`specific_hardware`（查过 `harmony-pc-capabilities.json`）。**直接采用这些状态，不要对这四类
   场景重查 caps、也不要从 `native_api`/`dependencies` 重扫 GUI/图形/媒体/硬件面**（那已由 dim-10 归纳）。你的活是把
   dim-10 的状态**翻译成移植计划**：对每个 `present:true` 的场景——`harmony_status=unavailable`（或
   `specific_hardware:true` 无替代）→**必产** `blocker`（多数还进 `unadaptable_apis`，category 取 hardware/platform，
   并标 `functionality_class`——GUI/3D/媒体这类跨平台主体能力多为 `core`，某平台专有硬件为 `platform_specific`），
   `porting_class` 升 `needs_adaptation`、`person_days` 上调；`partial`→产 partial `blocker`、
   `person_days` 上调；`unknown`→记 `target_assumptions` 并下调 `confidence`。**每条 blocker/unadaptable_api 用
   `caused_by`/`source_capability` 回指场景 `key`**（单一登记源：dim-10 判"鸿蒙有没有"，dim-9 判"于是要做什么"）。

4. **目标匹配（关键，决定准确性）—— 读 `references/harmony-pc-capabilities.json`，把本项目「所需的
   目标能力」逐项对照目标状态**，并把每一项写进 `target_assumptions[]`（`{capability, capability_key,
   required, target_status, impact, source}`）：
   - **只登记 capability_profile 覆盖不到的目标能力**（GUI/3D/媒体/特定硬件的鸿蒙支持状态已由 dim-10 判定，
     见 step 3，**不在这里重列/重查**——它们的 blocker 用 `source_capability`=场景 key 回指即可）：所需
     **JDK 内部模块**(jdk.attach/jvmstat/JVMTI…)、**进程/attach 模型**、**应用交付形态**、**桌面集成**(系统托盘/
     文件关联/自启)、**运行时是否已移植**；（库）通常只有「该语言运行时已移植」一条。
   - 给每条假设一个稳定 `id`（如 `ta:jdk_attach`），供下游 `blockers`/`unadaptable_apis` 的 `caused_by` 回指。
   - **`capability_key`（反哺研究优先级，关键）**：命中 `references/harmony-pc-capabilities.json` 某行时填其**叶 id**
     （如 `swing`/`jdk_attach`/`cross_attach`/`dotnet`/`x86_64`，见该文件各 section 的 `rows[].id`），供面板
     `#/harmony-caps` 跨报告聚合「该目标能力**被 N 个分析需要**」的研究优先级。**对不上任何 caps 行**（参考里尚无此能力）
     则 `capability_key: null`，并**追加一条** `meta.observations`：`{dimension:"harmony_caps", field:"<段 id 如
     gui/runtimes/graphics_3d>", kind:"caps_gap", value:"<目标能力名>", rationale:"<为何需要 + 建议补进哪一段>"}`，
     提案把这项缺失的目标能力补进 caps 参考（下次分析即可对号入座）。**只对 `required` 的目标能力提案，避免噪声。**
   - 据 `target_status` **显式驱动**下游（同一事实只登记一次、其余引用，不重复计入难度）：
     `available`→不计阻碍；`partial`→**必产**一条 `blocker`（`adaptability: partial`）`caused_by` 指回该假设 id；
     `unavailable`→**必产**一条 `blocker`（`adaptability: unadaptable`），若为具体 API 再进 `unadaptable_apis`
     （标 `functionality_class`）并让 blocker 的 `manifests_as` 指向它；**`unknown`→`target_assumptions` 记一条且若 `required` 则
     **把本维度 `confidence` 下调至多 `medium`**、在 `notes` 注明「结论依赖未核实的目标事实：…」——禁止据
     unknown 臆断为可适配/`no_adaptation`**。
   - 一项 `required:true` 且 `unavailable` ⇒ 若它承载**核心功能**则该库核心不完全可适配（把对应
     `unadaptable_apis` 标 `functionality_class:"core"`，归一据此判 `overall:core_blocked`）或需换形态（在 summary 说清）。

5. **逐组消费前序特征,生成 `blockers`——但 GUI/3D/媒体/硬件面已由 capability_profile 归纳（step 3），
   本步只处理 dim-10 覆盖不到的面**（平台 I/O、syscall、subprocess、fs/注册表/设备伪文件、arch/SIMD、
   构建工具链、及应用的 JDK 内部/attach/交付形态），**不要对这四类再从 native_api 重扫**（每条带来源维度 `evidence`）。
   `unadaptable` 类阻碍的粒度项在 step 7 `unadaptable_apis`——按 step 7「自底向上填写顺序」先填 ua、再回填本步 blocker 的 `manifests_as`：
   - `native_api`：每个 `category` 为 `platform`/`system` 的组（epoll/kqueue/win32/posix 差异、ioctl、syscall…）
     → 候选阻碍；`hardware` 组（GPU/CUDA/OpenCL/SIMD）**已归 capability_profile 的 rendering_3d/hardware 场景**，
     经 step 3 处理、此处不重判；`standard`/`portable`（STL、musl 支持的 POSIX、ArkTS 有对应的）通常不算或 `minor`。
   - `native_api.dynamic_libraries`（ctypes/dlopen/LoadLibrary/JNA 运行时加载的库）→
     **逐个**判其**自身**在鸿蒙 PC 上是否存在/可移植（看 `acquisition`/`source`：`system`
     平台库 vs `self_build` 包装器）。**属 GUI/图形/媒体/硬件能力的动态库（X11/XCB、libGL、libcudart、ffmpeg…）
     已由 capability_profile 对应场景覆盖，走 step 3**；本处只判**非能力类**运行时库（crypto/压缩/网络等，如
     libssl/libz）。平台专有系统库（Win32 `user32`/`gdi32` 等）鸿蒙无等价 → `blocker`，`harmony_status:
     replace_with_ohos`（改用 @ohos 能力）或 `unavailable`；跨平台且已移植到 OHOS 的通用库 → `minor`/`partial`，
     重编/重定位即可。每条复用该库的加载点 `evidence`(file:line)，`source_dimension: native_api`。
   - `runtime_surface.subprocess` → 调用具体平台命令(dmidecode/wmic/ioreg…)通常 `blocker`；
     仅为通用 shell-out 且鸿蒙有等价工具的 `minor`/`partial`（模型 B 沙箱下统一更严，多 `blocker`）。
   - `runtime_surface.filesystem/devices` 里的 `/proc`·`/sys`·`/dev`、注册表路径 → 阻碍。
   - `dependencies`：每个 `native`/`remote`/`system` 依赖须自身可移植；不可移植 → 阻碍。
     **但先看是否已鸿蒙化**：依赖若带 `harmony_adapted: true`（已在 OpenHarmony PC 官方源提供
     移植产物——**Python** 包在 pypi.cnb.cool/OpenHarmonyPCDeveloper 有 `*-ohos_*.whl`，如
     numpy/scipy/pandas；**C/C++** 库在 cmd-pkgs 预编译清单里，如 zlib/openssl/boost/eigen/
     cairo/freetype）→ **不计阻碍**，直接用鸿蒙版；这类依赖越多，难度/工作量越低。仅对**未**
     鸿蒙化且不可移植的依赖才记 `blocker`/`major`。
   - `build_env`：工具链(CMake/musl 兼容性)、`compiler_extensions`(MSVC/GCC 特有)、
     是否覆盖 arm64/x86_64 → 阻碍或注意点。

6. **判每条阻碍的 `harmony_status` 与 `remediation`**：能用 `@ohos.*` 平替的写
   `replace_with_ohos` + 具体 API；需权限的 `needs_permission`;部分支持 `partial`;
   彻底没有 `unavailable`。**具体 @ohos API 名与「彻底没有」的判定优先经「目标侧 API 事实核查」
   查文档确认**（查到等价 → remediation 写准确模块名；两步检索无果 → 才写 `unavailable`/进
   `unadaptable_apis`），evidence 附文档文件名。

7. **填 `unadaptable_apis`（API 粒度，父库综合用）** —— 仅当本库存在**确实无法在鸿蒙适配**的底层
   API 时列出（可适配 vs 不可适配判据见上「核心框架」）；这是自底向上综合的关键：服务端会把**父库的
   `dependencies[].used_symbols` 与子库此清单的 `public_entry` 求交**，命中才把该子计为父的阻碍——所以
   `public_entry` 要尽量填准，父库不调用到就不阻塞父的迁移。
   每项 `{id, api, public_entry, reason, blocking_native_api, category(platform/system/hardware/ffi), functionality_class(core/platform_specific), evidence, caused_by?}`，
   `id` 形如 `ua:culaunch`，证据复用 `native_api` 的调用点。**`functionality_class` 必填**（core=各平台交集的核心功能、
   platform_specific=某平台特有功能；漏填归一会默认 platform_specific 并记 `ua_func_class_defaulted` 告警提醒你补标）。纯脚本 / 仅交叉编译 / 用到功能全可适配 的库此项为空。
   - **`public_entry` 命名约定（决定 rollup 能否命中，务必遵守）**：填**父库实际 import/调用本库时引用的那个名字**，
     与依赖维度的 `dependencies[].used_symbols` **同一约定**——Python 用 `module.func` / `Class.method`；
     JS/TS 用导出名（`pkg.export` 或具名导出）；C/C++ 用自由函数名或 `Class::method`；Java 用 `Class.method` 或 `pkg.Class`。
     避免填内部静态函数名（父库引用不到 → rollup 漏判）。
   - **`public_entry` 怎么推导（关键，别只靠猜）**：`public_entry` **无上游来源**（native_api 只记调用点，不记路由到它的公共函数），
     必须你来定。方法：以本条复用的 `native_api` 调用点 `evidence`(file:line) 为**种子**，用**预建的 codegraph**
     （`codegraph_callers`/`codegraph_trace`）从该调用点**向上追**到本库最近的**导出/公共符号**（跨过内部私有帧），那个符号即 `public_entry`。
     这与 step 10「把 `samples` 当 codegraph 追踪种子」**同一手法**、也正是本维度「**复用前序 evidence**」——你不是重新扫去*找*这个 API
     （dim-7 已找到并给了 file:line），只是拿它的 evidence 当种子追**路由**（查预建索引 ≠ 重扫，见开篇 synthesis 说明）。
     codegraph 不可用时降级：读 `function_summary` 的公共 API 列表 + 定向 `Read` 该 file:line 所在文件的导出边界，并在 `notes` 注明 `public_entry` 为 best-effort。
   - **自底向上填写顺序（先粒度、后引用，避免同一事实写三遍）**：① 先填 `unadaptable_apis`（最细粒度）；
     ② 再写 `blockers`（step 5），把对应项的 `manifests_as` 指向 `ua:*`、`caused_by` 指向根因 `ta:*`；③ `target_assumptions`（step 4）作根因层。
     一个事实只在其主清单写完整内容，其余清单只用 id 引用。

8. **定 `porting_class`（三档闭轴）——你只给"下限"，归一据信号只升不降。** 判定树 Q1/Q2、三档边界、两维、
   可适配判据、常见误判**详见上「核心框架」**，此处不重述。你的动作：走判定树定 `porting_class` 下限 →（若 needs_adaptation）
   逐个把用到的功能分核心/平台差异两维、判可适配/不可适配，据判据填 `unadaptable_apis`（step 7）并标 `functionality_class`。
   `scripts/report_normalize.py` 组装时据 dim-12 `code_partition` 桶 + `unadaptable_apis` 把它**只升不降**并写回
   `report.json`（`adaptation_assessment`/`effort.level` 同为派生；web/server.js 是等价镜像；你的原判留存 `porting_class_model`）。
   **构造上不可能落盘自相矛盾的值**：dim-12 有 `needs_adaptation`/`unadaptable` 桶、或 `unadaptable_apis` 非空、
   或任一 blocker `adaptability` 为 partial/unadaptable → 归一自动升到 `needs_adaptation`。
   - **应用（模型 C）下重新诠释**：`no_adaptation`=纯运行时应用且 GUI 工具包鸿蒙已具备、直接跑；
     `recompile_only`=仅原生启动器/JNI agent 需重编；`needs_adaptation`=GUI/窗口/桌面集成需改——若都能适配则两维皆 `adaptable`，
     若部分功能（如依赖无 OHOS 版的预编译 agent、特定桌面能力）无法适配则列入 `unadaptable_apis` 并按核心/平台差异标 `functionality_class`。

9. **产 `required_permissions[]`（鸿蒙化后运行所需权限）**：媒体/硬件/定位/网络等场景常需申请鸿蒙权限
   （`ohos.permission.CAMERA/MICROPHONE/LOCATION/INTERNET/读写存储/USE_BLUETOOTH…`）。逐项填 `{permission, reason,
   source_capability(=capability_profile 的场景 key), harmony_status, evidence}`；**权限名优先经「目标侧 API
   事实核查」查 `harmonyos-sdk-api-lookup` 文档核实**（抄全名与授权类型，evidence 引文档文件名），
   不要凭记忆拼；`harmony_status` 对照 `harmony-pc-capabilities.json` 的**权限模型段**——**⚠️ 该轴闭轴取值刻意为
   `available/restricted/unavailable/unknown`（用 `restricted` 而非其它状态轴的 `partial`），别混用**：
   `restricted/unavailable`→酌情产 blocker；`unknown` 且该权限为运行必需 →下调 `confidence` 并 notes 注明。无需权限则 `[]`。

10. **汇总：估 `effort.person_days` 区间**（难度 `effort.level` 与 `adaptation_assessment`/`overall` 由归一派生，见开篇边界表，**你无需自填**）。
   你只输出两个**可观测**的量：`porting_class`（step 8，三档下限）与 `effort.person_days:[min,max]`
   人-天区间（区间宽度表达不确定性）。**person_days 估算锚点（同归一派 level 的 rubric）**：

   | 量级 | person_days | 典型情形 | 特征 |
   |---|---|---|---|
   | 极低 | 0–2 | 无需适配 | 纯脚本跑已移植运行时，零原生/平台耦合，至多打包 |
   | 低 | 2–5 | 仅交叉编译 | 仅 OHOS NDK 重编/交叉编译，无平台 API 改动 |
   | 中 | 5–15 | 需适配·全部可适配（量小） | 用到功能全可适配，阻碍点少且都有 @ohos 替代/重编路径 |
   | 高 | 15–40 | 平台差异功能有不可适配点，或阻碍点多/含 GUI·桌面集成大改 | 核心可用但有少量 `platform_specific` unadaptable，或改动量大 |
   | 极高 | 40+ | 核心功能有不可适配点（`overall:core_blocked`） | 核心依赖无解平台·硬件 API，或需整体重写 |

   **不要因为是 Python/Java/JS 就把核心功能判成不可适配——运行时已移植。** 对 FFI/ctypes 型库，
   **动态加载的平台库是否有鸿蒙等价才是定 person_days 与核心/平台差异可适配性的主因**（运行时已移植不再是主阻碍）。
   **person_days 的首要量化依据是 dim-12 的 `code_partition`**：`needs_adaptation` 桶的 LOC 与模块
   （平台抽象层/GUI 层/asm 补路径各自的量）决定改造量级，`unadaptable` 桶界定放弃范围，
   `recompile_reuse`/`reuse_direct` 桶只贡献重编/打包的小头。**填 `effort.breakdown[]`**（分项
   可审计）：每项 `{component, person_days:[lo,hi], basis}`，component 推荐集
   `recompile / api_adaptation / gui / deps_porting / build_system / testing_verification / packaging`
   （开放词，可扩并记 observations）。
   **⚠️ `recompile` 与 `api_adaptation` 两项由归一确定性派生、你不必填**（同 `effort.level`）：归一按
   `recompile = recompile_reuse 桶 LOC ÷ 速率`、`api_adaptation = needs_adaptation 桶 LOC ÷ 速率`
   （速率取 `.panel-settings.json`，默认 3000 / 500 行/天）算出并**覆盖**你填的值；你只需**itemize其余分项**
   （gui/deps_porting/build_system/testing_verification/packaging），`basis` 引用 code_partition 桶/LOC 或 blockers。
   **只要你产出了 breakdown，归一就把 `effort.person_days` 总量重算为「各分项之和」**（含派生的 recompile/adaptation
   + 你的其余分项），`effort.level` 随之派生——所以**分项要itemize齐全**（漏项会低估总量）。无 code_partition 时
   （存量/降级）按信号估 `effort.person_days` 并在 notes 说明。
   **三个平台/架构适配机械信号（都在 `code_metrics` 里，作复杂度依据）**：
   - `code_metrics.platform_adaptation`（**编译型**：C/C++ 各平台编译宏 `#ifdef _WIN32/__APPLE__/__linux__…` 包裹的代码量）——
     守卫代码越多 → 鸿蒙需新增/适配的平台分支越多 → `person_days` 上调、更可能产 toolchain/posix_subset_gap 类
     `blocker`（C/C++ 库尤甚）；为空或很小 → 平台耦合轻。
   - `code_metrics.platform_branches`（**运行时**：脚本/JVM/Go/Rust/C# 的 `sys.platform`/`os.name`/`process.platform`/
     `runtime.GOOS`/`cfg!(target_os)`… 命中数 + `samples` 样例位置）——补上一信号漏掉的纯语言平台分支。**用法**：把
     `samples` 当**追踪种子**，对每个平台分支用 codegraph（`codegraph_trace`/`callees`）顺着追到它**守卫的下游平台特有调用**，
     再对照 `references/harmony-pc-capabilities.json` 判鸿蒙有无等价——有等价 → 仅 `person_days` 略增；**无等价**（如仅
     Windows 的注册表/COM、`/proc`、`fork`/信号路径）→ 记 `blocker`/`unadaptable_apis`（标 `functionality_class`）、`porting_class` 升 `needs_adaptation`，
     并把该能力登记到 `target_assumptions`。分支越多 → `person_days` 越高。
   - `code_metrics.arch_specific`（**架构**：独立汇编文件 LOC 按 x86/arm/riscv 归类 + SIMD intrinsics 头 +
     C/C++/Rust 内联汇编命中 + `samples`）——鸿蒙 PC 是 arm64/x86_64：**只有 x86 实现而无 arm/NEON/标量回退**的
     汇编或 intrinsics 路径是硬适配点（补 NEON 或退标量 → `person_days` 上调、产 `blocker` category 如
     `arch_specific_asm`），若该路径可关（构建开关/运行时探测降级）记 `partial`；已有 arm 对应实现（by_arch 里
     arm 与 x86 并存）→ 只算重编验证量。`samples` 同样当 codegraph 追踪种子。三个信号都为空 → 平台/架构耦合轻。

11. **填 `critical_dependencies[]`（迁移关键路径依赖，有序）** —— 从 `dependencies` 里挑出
   **不先移植它们整个迁移就无法推进**的依赖，按建议移植顺序排 `order`（1 起，越先做越关键）：
   - 入选口径：runtime/必需 scope + **未鸿蒙化**（`harmony_adapted:true` 的**不进清单**——官方源已有
     移植产物，直接用）+ 被本库核心功能实际使用（`used_symbols` 非空或明显核心）+ 自身需要移植工作
     （原生库/含平台 API）。纯脚本依赖、optional/dev/test 依赖、系统标准库不列。
   - 排序依据：被阻塞面越大越靠前（核心路径 > 可选特性）；被 `blockers` 引用的靠前。
   - 每项 `{name(=dependencies[].name 原文), order, why(中文，一句话说明为何关键), refs:[bk:/ua:/ta: id],
     person_days_share:[lo,hi]?}`——`why` 细节**引用 refs 不重述**（单一登记源）；`person_days_share`
     是该依赖占本库 `effort.person_days` 的份额（含在总数内，不另计）。无关键依赖 → `[]`。

12. **`compatible` 与 `key_tasks`**：列可顺利移植的部分(纯算法/数据结构/标准库逻辑)、
   落地推荐路径的关键工作项。

## Output (fills report `harmony_adaptation`)
示例：一个带 C 扩展的 Python 库（模型 A，跑在鸿蒙 Python 上）。
```json
{
  "target": "HarmonyOS PC (跑在已移植的 Python 3.12 运行时上; 原生扩展经 OHOS NDK/musl 重编; arm64/x86_64; 自研内核, 无 Linux ABI)",
  "porting_class": "recompile_only",
  "effort": {"person_days": [3, 6],
    "breakdown": [
      {"component": "deps_porting", "person_days": [2, 4],
       "basis": "OHOS NDK 交叉编译 libfoo 并重建 cffi 绑定（code_partition recompile_reuse 桶约 1.8k 行 C）"},
      {"component": "testing_verification", "person_days": [1, 2],
       "basis": "在鸿蒙 Python 上跑通单元测试（tests 计数 210 例）"}]},
  "confidence": "high",
  "critical_dependencies": [
    {"name": "libfoo", "order": 1, "why": "唯一原生依赖，不重编则 cffi 绑定整体不可用", "refs": ["bk:libfoo"],
     "person_days_share": [2, 4]}
  ],
  "summary": "该库为 Python 库，鸿蒙 PC 已移植 Python 3.12 运行时，纯 Python 部分可直接运行；唯一工作量在其依赖的 C 库（经 cffi 绑定），需用 OHOS NDK 交叉编译该 C 库并重新生成绑定。无外部命令调用与平台特有系统接口，核心功能全部可适配。",
  "blockers": [
    {"id": "bk:libfoo", "issue": "经 cffi 绑定的原生 C 库（libfoo）需在鸿蒙上重新编译",
     "severity": "major", "adaptability": "adaptable", "category": "native_dependency", "source_dimension": "dependencies",
     "harmony_status": "partial",
     "remediation": "用 OHOS NDK（ohos.toolchain.cmake / clang + musl）交叉编译 libfoo 为 .so，再用鸿蒙 Python 重新构建 cffi 绑定；确认其自身不依赖 Linux 专有系统调用。",
     "evidence": ["setup.py:31", "src/_build.py:12"]},
    {"id": "bk:ioctl", "issue": "C 库内通过 mmap/部分 ioctl 访问设备",
     "severity": "minor", "adaptability": "partial", "category": "posix_subset_gap", "source_dimension": "native_api",
     "harmony_status": "partial",
     "remediation": "musl/OHOS 的 POSIX 子集多数 mmap 可用；逐项核对涉及的 ioctl 命令字是否被 OHOS 支持，缺失项做条件编译降级。",
     "evidence": ["src/native/io.c:88"]}
  ],
  "unadaptable_apis": [],
  "target_assumptions": [],
  "compatible": [
    {"aspect": "纯 Python 逻辑（解析、API 封装、数据整形）", "note": "鸿蒙 Python 3.12 直接运行，无需改动", "evidence": []}
  ],
  "key_tasks": [
    "用 OHOS NDK 交叉编译 C 依赖 libfoo 为 arm64/x86_64 .so，并在鸿蒙 Python 上重建 cffi 绑定",
    "核对 C 层 ioctl/设备访问在 OHOS POSIX 子集下的可用性，缺失项条件编译降级",
    "在鸿蒙 Python 上跑通其单元测试验证功能完整"
  ],
  "notes": "评估按模型 A（库跑在鸿蒙已移植 Python 运行时上）；归一将据 unadaptable_apis(此处为空) 派生 adaptation_assessment（核心/平台差异均全可适配、overall=adaptable）。若目标是 ArkTS 沙箱应用（模型 B），则 Python 运行时不可用，须整体换原生实现或重写，person_days 大幅上升。"
}
```
（`adaptation_assessment`/`effort.level` 由归一派生，示例中省略。）
- **纯脚本库（无原生扩展、无平台耦合）**：`porting_class: no_adaptation`、`effort.person_days:[0,2]`
  （派生 level=极低、overall=adaptable），`blockers` 为空或仅打包/路径类 `minor`。
- **C/C++ 库**：`porting_class: recompile_only`、`effort.person_days` 约 `[3,8]`、
  `blockers` 多为个别 POSIX 子集缺口或 Win32 分支（adaptable），`compatible` 含 STL/算法核心。
- **应用 + 目标假设示例（VisualVM 类桌面 profiler，模型 C）**：`target_assumptions` 形如
  `[{"capability":"headful Swing/AWT","capability_key":"swing","required":true,"target_status":"unknown","impact":"不支持则整个 GUI 无法运行","source":"harmony-pc-capabilities.json#gui.swing"},`
  `{"capability":"跨进程 attach (Attach API/JVMTI)","capability_key":"cross_attach","required":true,"target_status":"unknown","impact":"profiler 核心功能依赖","source":"…#process_security.cross_attach"},`
  `{"capability":"jdk.internal.jvmstat/sun.tools.attach 开放","capability_key":"jdk_jvmstat","required":true,"target_status":"unknown","impact":"性能计数器/attach 启动依赖","source":"…#jdk_internals.jdk_jvmstat"}]`；
  这些 `required+unknown` ⇒ **把 `confidence` 下调至多 `medium`、notes 注明依赖未核实事实**；其各平台预编译
  JNI agent `libprofilerinterface` 无 OHOS 版 → 进 `unadaptable_apis`/`blocker`。
- **核心功能有不可适配点（`overall:core_blocked` 示例）**：如某图形库的 GPU 加速属其核心能力、走 `cuLaunchKernel`，
  鸿蒙无对应 → `porting_class: needs_adaptation`、`effort.person_days` 约 `[15,30]`，且
  `unadaptable_apis: [{"id":"ua:culaunch","api":"cuLaunchKernel","public_entry":"foo.gpu_render","reason":"鸿蒙无 CUDA 运行时，无替代","blocking_native_api":"cuLaunchKernel","category":"hardware","functionality_class":"core","evidence":["src/gpu.c:120"],"caused_by":["ta:cuda"]}]`，
  归一据此派生 `effective_class:needs_adaptation_core_partial`、`overall:core_blocked`。对应 blocker `manifests_as:["ua:culaunch"]`；
  其 CPU 路径（`foo.render`）仍可适配 → 父库若只调 `foo.render` 不调 `foo.gpu_render` 则不受此阻塞。
- **仅平台差异功能不可适配（`overall:adaptable_with_tailoring` 示例）**：某库主体跨平台可适配，仅一个
  Windows 专有的托盘闪烁特性无鸿蒙等价 → 标 `functionality_class:"platform_specific"`，归一派生
  `effective_class:needs_adaptation_platform_partial`、`overall:adaptable_with_tailoring`（核心可用、裁剪该平台特性）。
- **目标确为 ArkTS 沙箱应用的 JS 库**：`porting_class: needs_adaptation`，Node 核心模块 → `@ohos.*` 重写，
  并在 `notes` 注明是按模型 B 评估。

## Rules
- **只综合,不重扫源码** —— 结论与 `evidence` 都来自前序维度;每条 `blocker` 标
  `source_dimension` 并复用其 `file:line`。**唯一例外（不算重扫）**：填 `unadaptable_apis[].public_entry` 时以前序
  `native_api.evidence`(file:line) 为种子、用预建 codegraph 向上追到公共入口（见 step 7）——复用前序 evidence 追**路由**，非重新发现特征事实。
- **生产范围** —— 因 dims 6/7/8 已限定生产代码（排除测试/示例/演示），`blockers` 与
  `unadaptable_apis` 自然也是：**只在测试/示例里用到的平台 API 不是迁移阻碍**，不要列入。
  若整仓是**示例/教程集合**（生产代码≈0），据库本体收敛——`porting_class` 不按 demo 定档，
  `unadaptable_apis` 近空，`notes` 注明「本仓为示例集合，平台 API 仅见于示例」。
- 闭轴(`porting_class`/`unadaptable_apis[].functionality_class`/`confidence`/`blockers[].severity`/`blockers[].adaptability`/`effort.level`)
  取值**必须**落在 schema enum 内;开放词(`blockers[].category`/`harmony_status`)按实际写。**产出/派生分工见开篇边界表**——
  你只给 `porting_class` 下限 + `effort.person_days` 区间 + `unadaptable_apis`（含 `functionality_class`）+ dim-12 分桶填准，其余归一确定性算出、落盘不自相矛盾（原判留存 `porting_class_model`）。
- 引用完整性 + 去重：每个 `caused_by`/`manifests_as`/`critical_dependencies[].refs` 引用的 id 必须在
  对应清单存在；同一事实只在主清单写完整内容、其余引用，避免重复计入难度。任一
  `blocker.adaptability: unadaptable` 应同时在 `unadaptable_apis` 有对应项（除非不是具体 API）。
- **与 dim-12 `code_partition` 的自洽由归一保证（你只需分桶准）**：归一据分区桶把 porting_class 只升不降——
  `unadaptable` 桶 / `unadaptable_apis` 非空 / `needs_adaptation` 桶非空 ⇒ `needs_adaptation`
  （`recompile_only`/`no_adaptation` = 零源码改动 = 分区只有 reuse_direct/recompile_reuse）。
  例外：`no_adaptation` 的已移植运行时库若只有个别纯跨平台交叉编译文件被 dim-12 误列 needs_adaptation，归一按 5%
  规模阈值容忍不升档——但正解是 dim-12 本就不该把这类文件列入 needs_adaptation。**你的责任**：桶内模块 reason 引用的
  `ua:*` 要真实存在；`needs_adaptation` 桶很大而 `person_days` 很小（或反之）在 notes 给理由；`effort.breakdown`
  分项之和落在 `effort.person_days` 区间附近（归一校验告警）。
- `critical_dependencies` 只列**未鸿蒙化**且真正阻塞推进的依赖（`harmony_adapted:true` 不列）；
  `name` 必须与 `dependencies[].name` 逐字一致（面板据此关联）。**单一登记源**：场景"是否涉及 + 鸿蒙状态"登记在 `capability_profile`、
  权限登记在 `required_permissions`、不可适配 API 登记在 `unadaptable_apis`、目标能力假设登记在
  `target_assumptions`、结果阻碍登记在 `blockers`——dim-9 引用（`source_capability`/`caused_by`/`manifests_as`）
  而非把同一 GUI/3D/媒体/硬件/权限事实在多处重述，否则会被 rollup 双计 person_days。
- 闭轴之间须自洽:**纯脚本库（运行时已移植 + 无原生扩展 + 无平台耦合）应是 `no_adaptation`/
  `overall:adaptable`/`person_days:[0,2]`**，不要把可适配的功能塞进 `unadaptable_apis`。
  required+unknown 假设存在时 `confidence` 至多 `medium`。
- **默认按模型 A（库跑在鸿蒙已移植运行时上）评估**；只有目标明确是 ArkTS 沙箱应用才用
  模型 B，并在 `notes` 注明。已移植运行时（Python/Node/Java/Rust/Go/Julia）本身不计为阻碍。
- 描述要可执行:`remediation` 给具体的 `@ohos.*` 平替或裁剪决定,不空泛。
- 评估基于代码证据,不臆造鸿蒙能力;不确定写进 `notes`。

## 自我复核（一致性告警）
组装后 `meta.harmony_warnings` 会带一批**跨维一致性告警**（`{code, class, message}`）。`class=="actionable"`
的那些是"可能漏判/矛盾"的启发式信号（如 `scenario_no_dim9:*`=某 present+unavailable 场景在 dim-9 无
对应 blocker/假设、`ua_no_cp_bucket`/`cp_unadapt_no_ua`=dim-9 与 dim-12 的 unadaptable 登记对不齐、
`*_ref:*`/`ta_unref:*`=悬空引用）。按 agent 流程**步骤 4b** 单趟复核：**真漏**就带 file:line 证据补进
对应源维度（本 skill 的 blocker/target_assumption/unadaptable_apis 或 capability_profile/cloud_services），
**误报**就在 `blocks/meta.json` 的 `harmony_warnings_dismissed` 记 `{code, rationale}`（别臆造数据消告警）。
`class=="info"` 的是归一器已确定性修好的留痕（如 `pclass_adjusted`），**不处理**。

## 自我发现（反哺）
新的阻碍类别、适配路径或鸿蒙状态取值，或口径歧义，追加到顶层 `meta.observations`：
`{dimension:"harmony_adaptation", field, kind, value, rationale}`，供面板「模型观察」页人工反哺。
