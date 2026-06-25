---
name: harmony-adaptation
description: Assess the feasibility, difficulty, and porting path of adapting a third-party library or application to HarmonyOS NEXT PC (self-developed kernel, ArkTS app layer, OHOS NDK native layer, Node-API bridge — no Linux ABI). A SYNTHESIS step over the already-computed native_api / runtime_surface / dependencies / build_env / library blocks. Use for dimension 9 of PC library/application analysis. Model reasoning, prescriptive (gives an adaptation plan).
---

# HarmonyOS PC adaptation assessment (model-driven, synthesis)

The final, **prescriptive** dimension. Earlier dimensions describe *what the library
is and what it touches*; this one answers **"how hard is it to port to 鸿蒙 PC, and
which path do we take"** and produces a concrete adaptation plan with difficulty,
path, blockers, and effort.

This is a **synthesis** step: you do NOT re-scan the source. You reason over the
already-filled blocks — `library.ecosystem`/`bindings`, `native_api` (groups +
`category`/`platform`, **以及 `native_api.dynamic_libraries`** —— 运行时经
ctypes/dlopen/LoadLibrary/JNA 动态加载的库), `runtime_surface`
(subprocess/filesystem/network/env/devices), `dependencies`, `build_env` —— and
**reuse their `evidence`** (the same `file:line`).

## 主旨与原则
**输出契约（下方 Output）是唯一硬约束。** 闭轴取值固定、UI 依赖它们；开放词可自创。
与 dim 8 相反——本维度**给适配建议**（这就是交付物），且是**前序维度的综合产物**，不重扫源码。
遇到清单外的阻碍类型或路径，尽力归类、自创一个简洁小写值，并在 `meta.observations` 记录。

### 目标平台：HarmonyOS PC（两种部署模型，库默认走「运行时模型」）
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
已移植运行时」，有就别假设没有、别据此判 `infeasible`。**

**准确性 = match(源所需能力, 目标能力)。结论必须建立在参考里的目标事实上，未核实(unknown)的不要臆测**
（见下「目标匹配」步）。

**两种部署模型（评估口径）：**
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

## How to assess
00. **先看 `capability_profile`（dim-10 场景画像）作为阻碍线索的入口**：它已把本项目是否涉及
   **GUI / 3D 渲染 / 媒体 / 特定硬件** 标好（`scenarios[].key/present/kind/via/harmony_status/specific_hardware`）。
   对每个 `present:true` 的场景：`harmony_status=unavailable`（或 `specific_hardware:true` 无替代）→**必产** `blocker`
   （多数还进 `unadaptable_apis`，category 取 hardware/platform），`porting_class` 升 `needs_adaptation_partial`/`infeasible`、
   `person_days` 上调；`partial`→产 partial `blocker`、`person_days` 上调；`unknown`→记 `target_assumptions` 并下调 `confidence`。
   把对应目标能力写进 `target_assumptions`，与场景 `key` 交叉引用（`blocker.caused_by`/`unadaptable_apis.caused_by`）。
0c. **产 `required_permissions[]`（鸿蒙化后运行所需权限）**：媒体/硬件/定位/网络等场景常需申请鸿蒙权限
   （`ohos.permission.CAMERA/MICROPHONE/LOCATION/INTERNET/读写存储/USE_BLUETOOTH…`）。逐项填 `{permission, reason,
   source_capability(=capability_profile 的场景 key), harmony_status, evidence}`；`harmony_status` 对照
   `harmony-pc-capabilities.json` 的**权限模型段**——`restricted/unavailable`→酌情产 blocker；`unknown` 且该权限为运行必需
   →下调 `confidence` 并 notes 注明。无需权限则 `[]`。
0. **先按 `library.kind` 选模型**：`application` → **模型 C（整包桌面应用）**，据
   GUI 工具包 / 窗口·桌面集成 / 启动器·打包 / 运行期服务（见上）判阻碍与分级；其它（库）→
   模型 A（默认）/ 仅当目标是 ArkTS 应用才 B。下面的「由 ecosystem 定基调」对两类都适用
   （决定运行时是否已移植），但**应用的阻碍重心在 GUI/打包/服务，而非「被链接进别的代码」**。
0b. **目标匹配（关键，决定准确性）—— 读 `references/harmony-pc-capabilities.json`，把本项目「所需的
   目标能力」逐项对照目标状态**，并把每一项写进 `target_assumptions[]`（`{capability, required,
   target_status, impact, source}`）：
   - 需列出的「所需能力」：（应用尤其）所用 **GUI 工具包**(Swing/AWT/JavaFX/Qt…) 与窗口/桌面集成项、
     所需 **JDK 内部模块**(jdk.attach/jvmstat/JVMTI…)、**进程/attach 模型**、**应用交付形态**；
     （库）通常只有「该语言运行时已移植」一条。
   - 给每条假设一个稳定 `id`（如 `ta:swing`），供下游 `blockers`/`unadaptable_apis` 的 `caused_by` 回指。
   - 据 `target_status` **显式驱动**下游（同一事实只登记一次、其余引用，不重复计入难度）：
     `available`→不计阻碍；`partial`→**必产**一条 `blocker`（`adaptability: partial`）`caused_by` 指回该假设 id；
     `unavailable`→**必产**一条 `blocker`（`adaptability: unadaptable`），若为具体 API 再进 `unadaptable_apis`
     并让 blocker 的 `manifests_as` 指向它；**`unknown`→`target_assumptions` 记一条且若 `required` 则
     **把本维度 `confidence` 下调至多 `medium`**、在 `notes` 注明「结论依赖未核实的目标事实：…」——禁止据
     unknown 臆断为 `feasible`/`no_adaptation`**。
   - 一项 `required:true` 且 `unavailable` ⇒ 该形态多半 `infeasible` 或需换形态（在 summary 说清）。
1. **由 `library.ecosystem` 定基调与默认路径**（默认走模型 A：跑在已移植运行时上）：
   - `python` → 默认 `run_on_ported_runtime`：跑在鸿蒙 Python 3.12 上。**纯 Python 无原生
     扩展 → `feasible`/`low`/`S`**；含 C 扩展（cffi/ctypes/C-API，如 cairocffi/pypdfium2）
     → 扩展需经 OHOS NDK 重编 = 真正工作量，难度由该原生依赖的可移植性决定（medium/high）。
   - `nodejs`/JS-TS → 默认 `run_on_ported_runtime`：跑在鸿蒙 Node.js 24 上，Node 核心模块
     基本可用。含 N-API 原生插件 → 插件需 OHOS NDK 重编。**仅当目标是 ArkTS 沙箱应用时**
     才走 `arkts_rewrite`（此时 Node 核心模块不可用、需 `@ohos.*` 重写，并在 notes 注明）。
   - `java` → 默认 `run_on_ported_runtime`：跑在鸿蒙 JDK 17 上。含 JNI 原生库 → 原生库需
     OHOS NDK 重编。
   - `rust`/`go` → `cross_compile`：Rust 有 ohos target(较顺),Go 支持较好 → 难度低/中。
   - `cpp`/`c` → 默认 `recompile_napi`：经 OHOS NDK 重编 + Node-API 暴露给 ArkTS；难度
     由 POSIX 子集缺口 + `native_api` 里的 `platform`/`system`/`hardware` 组数量决定。
   - **运行时已移植 ⇒ 别再据「无运行时」判 `infeasible`/`abandon`**；`infeasible` 仅留给
     运行时未移植 **且** 重度平台耦合且无替代的真正无解情形。
2. **逐组消费前序维度,生成 `blockers`**（每条带来源维度的 `evidence`）：
   - `native_api`：每个 `category` 为 `platform`/`system`/`hardware` 的组 → 候选阻碍；
     `standard`/`portable`（STL、musl 支持的 POSIX、ArkTS 有对应的）通常不算或 `minor`。
   - `native_api.dynamic_libraries`（ctypes/dlopen/LoadLibrary/JNA 运行时加载的库）→
     **逐个**判其**自身**在鸿蒙 PC 上是否存在/可移植（看 `acquisition`/`source`：`system`
     平台库 vs `self_build` 包装器）：
     · 平台专有 GUI/图形/系统库（X11/XCB、Win32 `user32`/`gdi32`、macOS CoreGraphics 等）→
       鸿蒙无等价 → `blocker`，`harmony_status: replace_with_ohos`（改用 @ohos 图形/显示能力）
       或 `unavailable`（须重写该功能）；
     · 跨平台且已移植到 OHOS 的通用库 → `minor`/`partial`，重编/重定位即可。
     每条复用该库的加载点 `evidence`(file:line)，`source_dimension: native_api`。
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
3. **判每条阻碍的 `harmony_status` 与 `remediation`**：能用 `@ohos.*` 平替的写
   `replace_with_ohos` + 具体 API；需权限的 `needs_permission`;部分支持 `partial`;
   彻底没有 `unavailable`。
4. **汇总：估 `effort.person_days` 区间 + 判 `feasibility`**（难度 `effort.level` 由 server 派生，**你无需自填**）。
   你只输出两个**可观测**的量：`porting_class`（见第 5 步，权威机器轴）与 `effort.person_days:[min,max]`
   人-天区间（区间宽度表达不确定性）。`feasibility` 与 porting_class 确定性对应（no_adaptation→feasible；
   recompile_only/needs_adaptation_full→feasible_with_effort；needs_adaptation_partial→hard；infeasible→infeasible），
   照填即可。**person_days 估算锚点（同 server 派 level 的 rubric）**：

   | 量级 | person_days | 典型 porting_class | 特征 |
   |---|---|---|---|
   | 极低 | 0–2 | no_adaptation | 纯脚本跑已移植运行时，零原生/平台耦合，至多打包 |
   | 低 | 2–5 | recompile_only | 仅 OHOS NDK 重编/交叉编译，无平台 API 改动 |
   | 中 | 5–15 | needs_adaptation_full（量小） | 用到功能全可适配，阻碍点少且都有 @ohos 替代/重编路径 |
   | 高 | 15–40 | partial 或 full（量大） | 有少量 unadaptable_apis 但核心可用，或阻碍点多/含 GUI·桌面集成大改 |
   | 极高 | 40+ | infeasible（或近） | 核心依赖无解平台·硬件 API，或需 arkts_rewrite 整体重写 |

   **不要因为是 Python/Java/JS 就判 `infeasible`——运行时已移植。** 对 FFI/ctypes 型库，
   **动态加载的平台库是否有鸿蒙等价才是定 person_days/feasibility 的主因**（运行时已移植不再是主阻碍）。
   **两个平台适配机械信号（都在 `code_metrics` 里，作复杂度依据）**：
   - `code_metrics.platform_adaptation`（**编译型**：C/C++ 各平台编译宏 `#ifdef _WIN32/__APPLE__/__linux__…` 包裹的代码量）——
     守卫代码越多 → 鸿蒙需新增/适配的平台分支越多 → `person_days` 上调、更可能产 toolchain/posix_subset_gap 类
     `blocker`（C/C++ 库尤甚）；为空或很小 → 平台耦合轻。
   - `code_metrics.platform_branches`（**运行时**：脚本/JVM/Go/Rust/C# 的 `sys.platform`/`os.name`/`process.platform`/
     `runtime.GOOS`/`cfg!(target_os)`… 命中数 + `samples` 样例位置）——补上一信号漏掉的纯语言平台分支。**用法**：把
     `samples` 当**追踪种子**，对每个平台分支用 codegraph（`codegraph_trace`/`callees`）顺着追到它**守卫的下游平台特有调用**，
     再对照 `references/harmony-pc-capabilities.json` 判鸿蒙有无等价——有等价 → 仅 `person_days` 略增；**无等价**（如仅
     Windows 的注册表/COM、`/proc`、`fork`/信号路径）→ 记 `blocker`/`unadaptable_apis`、`porting_class` 升 `needs_adaptation_*`，
     并把该能力登记到 `target_assumptions`。分支越多 → `person_days` 越高。两数都为空 → 平台耦合轻。
5. **定 `porting_class`（闭轴，依赖拓扑图用）** —— 把本库归入 5 类之一，与上面自洽：
   - `no_adaptation`：纯脚本（Python/Java/JS…）跑在已移植运行时上，无原生扩展、无平台耦合
     （≈ `feasible`/`run_on_ported_runtime`/无 blocker）。
   - `recompile_only`：C/C++ 等只需经 OHOS NDK **重新编译**即可，不依赖平台/底层 API、无平台差异
     （≈ `recompile_napi`/`cross_compile`，阻碍仅 native_dependency/posix 子集/toolchain 等 ≤major）。
   - `needs_adaptation_full`（**全部可适配**）：需改造，但**用到的功能全部能在鸿蒙适配/有替代**，
     无因平台/硬件 API 而彻底无法适配的功能（≈ 有平台类 `blocker`/`major` 但都给得出 `remediation`；
     `unadaptable_apis` 为空）。
   - `needs_adaptation_partial`（**部分可适配**）：**部分功能因平台/硬件 API 无对应实现而无法适配**
     （这些必须逐个列入 `unadaptable_apis`），但核心仍可用（≈ `feasible_with_effort`/`hard`，
     `unadaptable_apis` 非空）。
   - `infeasible`：核心不可适配 / 依赖特定硬件 / 无解（≈ `feasibility: infeasible`）。
   - **应用（模型 C）下重新诠释**：`no_adaptation`=纯运行时应用且 GUI 工具包鸿蒙已具备、直接跑；
     `recompile_only`=仅原生启动器/JNI agent 需重编；`needs_adaptation_full`=GUI/窗口/桌面集成需改
     但都能适配；`needs_adaptation_partial`=部分功能（如依赖无 OHOS 版的预编译 agent、特定桌面能力）
     无法适配并列入 `unadaptable_apis`；`infeasible`=核心依赖鸿蒙缺失的桌面环境/硬件且无替代。
5b. **填 `unadaptable_apis`（API 粒度，父库综合用）** —— 仅当本库存在**确实无法在鸿蒙适配**的底层
   API 时列出；这是自底向上综合的关键：服务端会把**父库的 `dependencies[].used_symbols` 与子库此清单的
   `public_entry` 求交**，命中才把该子计为父的阻碍——所以 `public_entry` 要尽量填准，父库不调用到就不阻塞父的迁移。
   每项 `{id, api, public_entry, reason, blocking_native_api, category(platform/system/hardware/ffi), evidence, caused_by?}`，
   `id` 形如 `ua:culaunch`，证据复用 `native_api` 的调用点。纯脚本 / 仅需重编 / 全部可适配 的库此项为空。
   - **`public_entry` 命名约定（决定 rollup 能否命中，务必遵守）**：填**父库实际 import/调用本库时引用的那个名字**，
     与依赖维度的 `dependencies[].used_symbols` **同一约定**——Python 用 `module.func` / `Class.method`；
     JS/TS 用导出名（`pkg.export` 或具名导出）；C/C++ 用自由函数名或 `Class::method`；Java 用 `Class.method` 或 `pkg.Class`。
     避免填内部静态函数名（父库引用不到 → rollup 漏判）。
   - **自底向上填写顺序（先粒度、后引用，避免同一事实写三遍）**：① 先填 `unadaptable_apis`（最细粒度）；
     ② 再写 `blockers`，把对应项的 `manifests_as` 指向 `ua:*`、`caused_by` 指向根因 `ta:*`；③ `target_assumptions` 作根因层。
     一个事实只在其主清单写完整内容，其余清单只用 id 引用。
6. **`compatible` 与 `key_tasks`**：列可顺利移植的部分(纯算法/数据结构/标准库逻辑)、
   落地推荐路径的关键工作项。

## Output (fills report `harmony_adaptation`)
示例：一个带 C 扩展的 Python 库（模型 A，跑在鸿蒙 Python 上）。
```json
{
  "target": "HarmonyOS PC (跑在已移植的 Python 3.12 运行时上; 原生扩展经 OHOS NDK/musl 重编; arm64/x86_64; 自研内核, 无 Linux ABI)",
  "porting_class": "recompile_only",
  "feasibility": "feasible_with_effort",
  "effort": {"person_days": [3, 6]},
  "confidence": "high",
  "recommended_path": "run_on_ported_runtime",
  "summary": "该库为 Python 库，鸿蒙 PC 已移植 Python 3.12 运行时，纯 Python 部分可直接运行；唯一工作量在其依赖的 C 库（经 cffi 绑定），需用 OHOS NDK 交叉编译该 C 库并重新生成绑定。无外部命令调用与平台特有系统接口，整体可行。",
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
  "notes": "评估按模型 A（库跑在鸿蒙已移植 Python 运行时上）；若目标是 ArkTS 沙箱应用（模型 B），则 Python 运行时不可用，须整体换原生实现或重写，结论收紧为 hard、person_days 大幅上升。"
}
```
- **纯脚本库（无原生扩展、无平台耦合）**：`porting_class: no_adaptation`、`recommended_path: "run_on_ported_runtime"`、
  `feasibility: feasible`、`effort.person_days:[0,2]`（派生 level=极低），`blockers` 为空或仅打包/路径类 `minor`。
- **C/C++ 库**：`porting_class: recompile_only`、`recommended_path: "recompile_napi"`、`effort.person_days` 约 `[3,8]`、
  `blockers` 多为个别 POSIX 子集缺口或 Win32 分支,`compatible` 含 STL/算法核心。
- **应用 + 目标假设示例（VisualVM 类桌面 profiler，模型 C）**：`target_assumptions` 形如
  `[{"capability":"headful Swing/AWT","required":true,"target_status":"unknown","impact":"不支持则整个 GUI 无法运行","source":"harmony-pc-capabilities.json#gui.swing"},`
  `{"capability":"跨进程 attach (Attach API/JVMTI)","required":true,"target_status":"unknown","impact":"profiler 核心功能依赖","source":"…#5"},`
  `{"capability":"jdk.internal.jvmstat/sun.tools.attach 开放","required":true,"target_status":"unknown","impact":"性能计数器/attach 启动依赖","source":"…#2"}]`；
  这些 `required+unknown` ⇒ **把 `confidence` 下调至多 `medium`、notes 注明依赖未核实事实**；其各平台预编译
  JNI agent `libprofilerinterface` 无 OHOS 版 → 进 `unadaptable_apis`/`blocker`。
- **部分功能不可适配的库（partial 档示例）**：如某图形库的 GPU 加速路径走 `cuLaunchKernel`/特定
  设备 `ioctl`，鸿蒙无对应 → `porting_class: needs_adaptation_partial`、`effort.person_days` 约 `[15,30]`，且
  `unadaptable_apis: [{"id":"ua:culaunch","api":"cuLaunchKernel","public_entry":"foo.gpu_render","reason":"鸿蒙无 CUDA 运行时，无替代","blocking_native_api":"cuLaunchKernel","category":"hardware","evidence":["src/gpu.c:120"],"caused_by":["ta:cuda"]}]`，
  对应 blocker `manifests_as:["ua:culaunch"]`；其 CPU 路径（`foo.render`）仍可适配 → 父库若只调 `foo.render` 不调 `foo.gpu_render` 则不受此阻塞。
- **目标确为 ArkTS 沙箱应用的 JS 库**：才用 `arkts_rewrite`，Node 核心模块 → `@ohos.*`，
  并在 `notes` 注明是按模型 B 评估。

## Rules
- **只综合,不重扫源码** —— 结论与 `evidence` 都来自前序维度;每条 `blocker` 标
  `source_dimension` 并复用其 `file:line`。
- **生产范围** —— 因 dims 6/7/8 已限定生产代码（排除测试/示例/演示），`blockers` 与
  `unadaptable_apis` 自然也是：**只在测试/示例里用到的平台 API 不是迁移阻碍**，不要列入。
  若整仓是**示例/教程集合**（生产代码≈0），据库本体收敛——`porting_class` 不按 demo 定档，
  `unadaptable_apis` 近空，`notes` 注明「本仓为示例集合，平台 API 仅见于示例」。
- 闭轴(`feasibility`/`porting_class`/`confidence`/`blockers[].severity`/`blockers[].adaptability`/`effort.level`)
  取值**必须**落在 schema enum 内;开放词(`recommended_path`/`category`/`harmony_status`)按实际写。
  **`effort.level` 由 server 派生，你不必填**；你填 `porting_class` + `effort.person_days` + `feasibility`。
  `porting_class` 必须与 `feasibility`/路径自洽（见 How-to 第 4/5 步映射），并与 `unadaptable_apis`
  自洽：`unadaptable_apis` 非空 ⇒ `porting_class: needs_adaptation_partial`（或 `infeasible`）；
  为空且仍需改造 ⇒ `needs_adaptation_full`。
- 引用完整性 + 去重：每个 `caused_by`/`manifests_as` 引用的 id 必须在对应清单存在；同一事实只在主清单
  写完整内容、其余引用，避免重复计入难度。任一 `blocker.adaptability: unadaptable` 应同时在 `unadaptable_apis`
  有对应项（除非不是具体 API）。**单一登记源**：场景"是否涉及 + 鸿蒙状态"登记在 `capability_profile`、
  权限登记在 `required_permissions`、不可适配 API 登记在 `unadaptable_apis`、目标能力假设登记在
  `target_assumptions`、结果阻碍登记在 `blockers`——dim-9 引用（`source_capability`/`caused_by`/`manifests_as`）
  而非把同一 GUI/3D/媒体/硬件/权限事实在多处重述，否则会被 rollup 双计 person_days。
- 闭轴之间须自洽:大量 `blocker` / 长 `person_days` 不能配 `feasibility: feasible`；反之
  **纯脚本库（运行时已移植 + 无原生扩展 + 无平台耦合）不能配 `infeasible`**——应是
  `feasible`/`person_days:[0,2]`。required+unknown 假设存在时 `confidence` 至多 `medium`。
- **默认按模型 A（库跑在鸿蒙已移植运行时上）评估**；只有目标明确是 ArkTS 沙箱应用才用
  模型 B，并在 `notes` 注明。已移植运行时（Python/Node/Java/Rust/Go/Julia）本身不计为阻碍。
- 描述要可执行:`remediation` 给具体的 `@ohos.*` 平替或裁剪决定,不空泛。
- 评估基于代码证据,不臆造鸿蒙能力;不确定写进 `notes`。

## 自我发现（反哺）
新的阻碍类别、适配路径或鸿蒙状态取值，或口径歧义，追加到顶层 `meta.observations`：
`{dimension:"harmony_adaptation", field, kind, value, rationale}`，供面板「模型观察」页人工反哺。
