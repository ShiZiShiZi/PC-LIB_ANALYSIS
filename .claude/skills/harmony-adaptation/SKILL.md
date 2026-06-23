---
name: harmony-adaptation
description: Assess the feasibility, difficulty, and porting path of adapting a third-party library to HarmonyOS NEXT PC (self-developed kernel, ArkTS app layer, OHOS NDK native layer, Node-API bridge — no Linux ABI). A SYNTHESIS step over the already-computed native_api / runtime_surface / dependencies / build_env / library blocks. Use for dimension 9 of PC library analysis. Model reasoning, prescriptive (gives an adaptation plan).
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

**鸿蒙 PC 已移植运行时（推理依据；版本会更新，以社区为准）：**

| 运行时 | 鸿蒙 PC 版本 | 说明 |
|--------|--------------|------|
| Node.js | 24.13.0（已回合主社区） | JS/TS 库可直接跑 |
| Python | 3.12.9 / 3.9.x | 纯 Python 库可直接跑 |
| Java | JDK 17.0.x / JDK 8 | JVM 库可直接跑 |
| Rust | 1.89+ | 有 ohos target |
| Go | 1.24+ / 1.22 | OpenHarmony 社区 |
| Julia | 1.10.6 | — |

来源：OpenHarmonyPCDeveloper/docs「运行时」开源运行时汇总。**定基调时先看「该语言是否
有已移植运行时」，有就别假设没有、别据此判 `infeasible`。**

**两种部署模型（评估口径）：**
- **模型 A（默认，命令行 / 桌面库）**：库跑在上表的已移植运行时上。运行时**不是阻碍**；
  阻碍点 = 原生扩展（C/C++ via cffi/ctypes/C-API/N-API/JNI）需经 OHOS NDK 重编、C / 系统
  依赖的可移植性、平台特有系统调用 / 外部命令 / `/proc`·`/sys` / 注册表等。库分析**默认
  按此口径**。
- **模型 B（次要，ArkTS 沙箱 GUI 应用）**：应用层 **ArkTS/ArkUI**（运行在 ArkCompiler，
  **不是 Node.js**），ArkTS↔C/C++ 经 **Node-API（napi）** 桥接，应用沙箱化、硬件/系统访问
  受权限(ACL)管控；此口径下 Node 核心模块不可用、需 `@ohos.*` 平替。**仅当目标确为 ArkTS
  应用时才用此口径**，并在 `notes` 注明结论是按模型 B 收紧的。

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
4. **汇总闭轴**：`feasibility` / `overall_difficulty` / `effort_estimate`，与阻碍数量、
   严重度、推荐路径自洽。例：纯脚本库(运行时已移植 + 无原生扩展 + 无平台耦合) ⇒
   `feasible`/`low`/`XS`–`S`；少量原生扩展需重编 ⇒ `feasible_with_effort`/`medium`/`M`；
   大量 `blocker` + `arkts_rewrite` ⇒ `hard`/`very_high`/`L`|`XL`。**不要因为是 Python/Java/JS
   就判 `infeasible`——运行时已移植。** 对 FFI/ctypes 型库，**动态加载的平台库是否有鸿蒙
   等价才是定档 feasibility/难度的主因**（运行时已移植不再是主阻碍）。
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
   - （旧值 `needs_adaptation` 仍兼容，等同 partial 档；新输出请用 full/partial 二选一。）
5b. **填 `unadaptable_apis`（API 粒度，父库综合用）** —— 仅当本库存在**确实无法在鸿蒙适配**的底层
   API 时列出；这是自底向上综合的关键：服务端会把**父库的 `dependencies[].used_symbols` 与子库此清单的
   `public_entry` 求交**，命中才把该子计为父的阻碍——所以 `public_entry`（本库对外、会路由到该不支持
   API 的公共函数/符号）要尽量填准，父库不调用到就不阻塞父的迁移。每项 `{api, public_entry, reason,
   blocking_native_api, category(platform/system/hardware/ffi), evidence}`，证据复用 `native_api` 的调用点。
   纯脚本 / 仅需重编 / 全部可适配 的库此项为空。
6. **`compatible` 与 `key_tasks`**：列可顺利移植的部分(纯算法/数据结构/标准库逻辑)、
   落地推荐路径的关键工作项。

## Output (fills report `harmony_adaptation`)
示例：一个带 C 扩展的 Python 库（模型 A，跑在鸿蒙 Python 上）。
```json
{
  "target": "HarmonyOS PC (跑在已移植的 Python 3.12 运行时上; 原生扩展经 OHOS NDK/musl 重编; arm64/x86_64; 自研内核, 无 Linux ABI)",
  "feasibility": "feasible_with_effort",
  "overall_difficulty": "medium",
  "effort_estimate": "M",
  "porting_class": "recompile_only",
  "recommended_path": "run_on_ported_runtime",
  "summary": "该库为 Python 库，鸿蒙 PC 已移植 Python 3.12 运行时，纯 Python 部分可直接运行；唯一工作量在其依赖的 C 库（经 cffi 绑定），需用 OHOS NDK 交叉编译该 C 库并重新生成绑定。无外部命令调用与平台特有系统接口，整体可行。",
  "blockers": [
    {"issue": "经 cffi 绑定的原生 C 库（libfoo）需在鸿蒙上重新编译",
     "severity": "major", "category": "native_dependency", "source_dimension": "dependencies",
     "harmony_status": "partial",
     "remediation": "用 OHOS NDK（ohos.toolchain.cmake / clang + musl）交叉编译 libfoo 为 .so，再用鸿蒙 Python 重新构建 cffi 绑定；确认其自身不依赖 Linux 专有系统调用。",
     "evidence": ["setup.py:31", "src/_build.py:12"]},
    {"issue": "C 库内通过 mmap/部分 ioctl 访问设备",
     "severity": "minor", "category": "posix_subset_gap", "source_dimension": "native_api",
     "harmony_status": "partial",
     "remediation": "musl/OHOS 的 POSIX 子集多数 mmap 可用；逐项核对涉及的 ioctl 命令字是否被 OHOS 支持，缺失项做条件编译降级。",
     "evidence": ["src/native/io.c:88"]}
  ],
  "unadaptable_apis": [],
  "compatible": [
    {"aspect": "纯 Python 逻辑（解析、API 封装、数据整形）", "note": "鸿蒙 Python 3.12 直接运行，无需改动", "evidence": []}
  ],
  "key_tasks": [
    "用 OHOS NDK 交叉编译 C 依赖 libfoo 为 arm64/x86_64 .so，并在鸿蒙 Python 上重建 cffi 绑定",
    "核对 C 层 ioctl/设备访问在 OHOS POSIX 子集下的可用性，缺失项条件编译降级",
    "在鸿蒙 Python 上跑通其单元测试验证功能完整"
  ],
  "notes": "评估按模型 A（库跑在鸿蒙已移植 Python 运行时上）；若目标是 ArkTS 沙箱应用（模型 B），则 Python 运行时不可用，须整体换原生实现或重写，结论收紧为 hard/very_high。"
}
```
- **纯脚本库（无原生扩展、无平台耦合）**：`recommended_path: "run_on_ported_runtime"`、
  `feasibility: feasible`、`low`/`XS`–`S`，`blockers` 为空或仅打包/路径类 `minor`。
- **C/C++ 库**：`recommended_path: "recompile_napi"`、难度 medium、`blockers` 多为个别
  POSIX 子集缺口或 Win32 分支,`compatible` 含 STL/算法核心。
- **部分功能不可适配的库（partial 档示例）**：如某图形库的 GPU 加速路径走 `cuLaunchKernel`/特定
  设备 `ioctl`，鸿蒙无对应 → `porting_class: needs_adaptation_partial`，且
  `unadaptable_apis: [{"api":"cuLaunchKernel","public_entry":"foo_gpu_render","reason":"鸿蒙无 CUDA 运行时，无替代","blocking_native_api":"cuLaunchKernel","category":"hardware","evidence":["src/gpu.c:120"]}]`；
  其 CPU 路径（`foo_render`）仍可适配 → 父库若只调 `foo_render` 不调 `foo_gpu_render` 则不受此阻塞。
- **目标确为 ArkTS 沙箱应用的 JS 库**：才用 `arkts_rewrite`，Node 核心模块 → `@ohos.*`，
  并在 `notes` 注明是按模型 B 评估。

## Rules
- **只综合,不重扫源码** —— 结论与 `evidence` 都来自前序维度;每条 `blocker` 标
  `source_dimension` 并复用其 `file:line`。
- 闭轴(`feasibility`/`overall_difficulty`/`effort_estimate`/`porting_class`/`blockers[].severity`)
  取值**必须**落在 schema enum 内;开放词(`recommended_path`/`category`/`harmony_status`)按实际写。
  `porting_class` 必须与 `feasibility`/难度/路径自洽（见 How-to 第 5 步的映射），并与 `unadaptable_apis`
  自洽：`unadaptable_apis` 非空 ⇒ `porting_class: needs_adaptation_partial`（或 `infeasible`）；
  为空且仍需改造 ⇒ `needs_adaptation_full`。
- 闭轴之间须自洽:大量 `blocker` 不能配 `feasibility: feasible` / `low` 难度；反之
  **纯脚本库（运行时已移植 + 无原生扩展 + 无平台耦合）不能配 `infeasible`**——应是
  `feasible`/`low`。
- **默认按模型 A（库跑在鸿蒙已移植运行时上）评估**；只有目标明确是 ArkTS 沙箱应用才用
  模型 B，并在 `notes` 注明。已移植运行时（Python/Node/Java/Rust/Go/Julia）本身不计为阻碍。
- 描述要可执行:`remediation` 给具体的 `@ohos.*` 平替或裁剪决定,不空泛。
- 评估基于代码证据,不臆造鸿蒙能力;不确定写进 `notes`。

## 自我发现（反哺）
新的阻碍类别、适配路径或鸿蒙状态取值，或口径歧义，追加到顶层 `meta.observations`：
`{dimension:"harmony_adaptation", field, kind, value, rationale}`，供面板「模型观察」页人工反哺。
