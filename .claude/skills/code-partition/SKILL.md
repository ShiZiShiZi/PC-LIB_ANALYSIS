---
name: code-partition
description: Partition a library's or application's production code by HarmonyOS-PC-porting reusability — directly reusable / recompile-and-reuse / needs adaptation / unadaptable — at module/directory granularity with LOC statistics grounded in the mechanical code-metrics numbers, by synthesizing the already-computed code_metrics (dir_loc / platform_adaptation / platform_branches / arch_specific), native_api call sites, capability_profile and dependencies. Use for dimension 12 of PC library/application analysis. Model synthesis; feeds dim-9's effort estimate.
---

# Code partition — 鸿蒙迁移复用性代码分区（model synthesis）

A focused lens that answers **"这个项目的生产代码里，有多少行能直接复用、多少行重编译就能复用、
多少行需要适配改造、多少行无法适配"** —— 按模块/目录分桶并给出 LOC 统计。这是鸿蒙化**工作量
评估的量化底座**：dim-9 的 `effort.person_days`/`effort.breakdown` 要以本分区（尤其
`needs_adaptation`/`unadaptable` 桶的 LOC）为主要依据。**职责分工**：本维度只做"代码 → 桶 + LOC"
的归属与对账，**不**下移植结论/不估人天（那是 dim-9）。**综合层，见 `pc-lib-analyzer.md`「两层契约」——
只消费特征层、不重扫源码、结论不与 dim-9 矛盾（`porting_class` 由归一据本 4 桶 + dim-9 `unadaptable_apis` 派生）。**

## 主旨与原则

**输出契约（下方 Output）是唯一硬约束。** `buckets[].class` 是**闭轴 4 值**（UI/xlsx 依赖它），
不可自创桶名；拿不准归哪个桶时按"就低不就高"（宁可归 `needs_adaptation` 也别臆断 `unadaptable`），
并在 `meta.observations` 记录歧义。

**这是综合维度，不要重扫源码。** 复用本次分析**已算出**的：
- `code_metrics.dir_loc` —— **每个桶模块的 LOC 必须引用这里的机械数字**（这是对账底数）；
- `code_metrics.platform_adaptation`（C/C++ 平台编译宏包裹行）/ `platform_branches`（运行时平台
  分支 + samples）/ `arch_specific`（`by_arch.<arch>.simd_loc`＝SIMD intrinsic 使用行数、汇编 LOC、
  内联汇编 + samples）—— 哪些目录有平台/架构耦合；**`simd_loc` 给 SIMD 模块的行量**（对头文件库尤要，
  汇编 LOC 常为 0 但 simd_loc 才是真实工作量）；
- `native_api.groups[].apis[].evidence`（file:line 调用点）—— 平台/系统/硬件 API 落在哪些目录；
- `capability_profile.scenarios[].via/evidence` —— GUI/3D/媒体/硬件层在哪些模块；
- `dependencies[].declared_in` / `library.ecosystem`/`bindings` —— 原生扩展/绑定层的位置。
必要时用 codegraph/Read 点开一两个关键文件确认归属，但**不做全仓扫描**。

**LOC 对账（本维度的硬要求）**：
- 模块尽量取 `dir_loc` 里的目录（`dir` 字段原样），`loc` 直接引用其 `code`；
- 一个目录要**拆到子目录/按比例分**时（如 `src/` 里只有 `src/win32/` 需适配），在该模块的
  `reason` 说明估算依据（子目录在 dir_loc 有行则引用之；没有则按文件数/调用点密度估）；
- `coverage.partitioned_code` = 各桶 `loc` 之和，`coverage.production_code` =
  `code_metrics.production.code`，`pct` 应 **≥90%**——归不进明确桶的长尾目录并入其生态的
  默认桶（脚本语言→`reuse_direct`，C/C++→`recompile_reuse`）并在 `notes` 说明。

**生产代码口径**：只分区**生产代码**（`dir_loc` 本身已排除测试/示例）；模型补判出的
示例目录（按功能命名的 demo）也不进分区，在 `notes` 说明扣除了哪些。

## 输出契约（Output，fills report `code_partition`）

```json
{
  "summary": "中文：约 78% 代码可直接重编译复用，主要适配点在平台抽象层与 GUI 层（约 4.1k 行），另有 CUDA 加速路径约 600 行无法适配",
  "coverage": {"production_code": 21340, "partitioned_code": 20950, "pct": 98.2},
  "buckets": [
    {"class": "recompile_reuse", "loc": 16600, "pct": 77.8,
     "modules": [
       {"path": "src/core", "loc": 12400, "reason": "纯算法与数据结构，仅用 STL/POSIX 可移植子集", "evidence": []},
       {"path": "src/io", "loc": 4200, "reason": "标准文件 IO，无平台 API 调用点", "evidence": []}],
     "basis": "native_api 在这些目录无 platform/system/hardware 调用点；platform_adaptation 为 0"},
    {"class": "needs_adaptation", "loc": 3750, "pct": 17.6,
     "modules": [
       {"path": "src/platform", "loc": 2100, "reason": "平台抽象层：Win32/Cocoa/X11 三套实现，需新增 OHOS 后端", "evidence": ["src/platform/win32_window.cpp:88", "src/platform/x11_window.cpp:41"]},
       {"path": "src/simd", "loc": 1650, "reason": "x86 SSE/AVX intrinsics 为主，NEON 路径不全，需补 arm 实现", "evidence": ["src/simd/blend_avx2.c:12"]}],
     "basis": "platform_adaptation.by_platform 与 arch_specific.by_arch.x86 集中在这两个目录；native_api 平台组调用点同位"},
    {"class": "unadaptable", "loc": 600, "pct": 2.8,
     "modules": [
       {"path": "src/gpu", "loc": 600, "reason": "CUDA 加速路径，见 ua:culaunch（鸿蒙无 CUDA 运行时）", "evidence": ["src/gpu/kernel.cu:120"]}],
     "basis": "capability_profile hardware 场景 specific_hardware:true；对应 dim-9 unadaptable_apis"}
  ],
  "notes": "docs/ 与构建脚本（约 390 行）不参与分区；src/ 下长尾工具文件并入 recompile_reuse"
}
```

- `class` 闭轴 4 值：`reuse_direct` / `recompile_reuse` / `needs_adaptation` / `unadaptable`。
  **归一（`report_normalize.py`）据本 4 桶确定性派生 dim-9 `porting_class`**——本分区就是 porting_class 的事实源之一，
  分桶准则 porting_class 准：
  `recompile_reuse` = 该模块 **OHOS NDK 重编、零源码改动** → `recompile_only`；
  `needs_adaptation` = 需要为鸿蒙**改动源码/加 OHOS 分支/换后端**（哪怕只靠构建开关切换后端）→ `needs_adaptation`；
  `unadaptable` = 机制/硬件/闭源层无鸿蒙等价 → 仍是 `needs_adaptation`（该模块须与 dim-9 `unadaptable_apis` 交叉引用，
  核心 vs 平台差异两维细分由 `functionality_class` 决定、归一派生 `adaptation_assessment`）。**因此：C/C++ 等原生模块只要需要任何鸿蒙适配动作就归
  `needs_adaptation`，别塞进 `recompile_reuse`——否则归一会把 porting_class 误派生成 `recompile_only`。**
  ⚠️ **例外——已移植运行时语言（Go/Rust/Python/Java…）的纯跨平台文件不算 needs_adaptation**：靠 `GOOS`/`cfg!(target_os)`/
  运行时自动选择、鸿蒙上**交叉编译即过、零改动**的平台分支文件（如 `app_unix.go`/`app_windows.go` 只做信号处理），
  归 `reuse_direct`/`recompile_reuse`，**不要**单列 `needs_adaptation` 桶（否则会把本应 `no_adaptation` 的纯 Go/Rust 库
  误升档；服务端对 `no_adaptation` 的 needs_adaptation 桶设了 5% 规模阈值兜底，但你应从源头分对）。
- **字段名逐字用 `loc`/`path`/`reason`**（桶 LOC=`loc`、模块路径=`path`、归类理由=`reason`）——
  **不要**写成 `total_loc`/`dir`/`note`，面板与 xlsx 只认前者，写错会显示**空模块名 + 0 行**。
- 某桶为 0 行可省略。纯脚本库常只有一个 `reuse_direct` 桶（loc = production.code）。
- **`unadaptable` 桶与 dim-9 单一登记源约定**：API 粒度的完整登记在 dim-9
  `unadaptable_apis`（`ua:*`）；本桶只登记**模块 + LOC**，`reason` 用 `ua:*` id 引用而不重述。
  （分块产出顺序上本维度先写、dim-9 后写——此时引用你**打算**登记的 ua id 即可，dim-9 落笔时保持一致。）

## 思路（Approach，可调整）

1. **先立底数**：读 `code_metrics.dir_loc` + `production.code`，把要分区的目录清单和总行数定下来。
2. **标出"脏"目录**：把 `native_api` 各 platform/system/hardware/ffi 组的调用点 file:line、
   `platform_adaptation`/`platform_branches`/`arch_specific` 的 samples、`capability_profile`
   各场景的 evidence 按目录聚类——调用点集中的目录就是 `needs_adaptation`（或 `unadaptable`）候选。
3. **给"干净"目录定默认桶**（按 `library.ecosystem`）：
   - 脚本语言（python/nodejs/java 字节码…）无原生耦合的模块 → `reuse_direct`（跑已移植运行时零改动）；
   - C/C++/Rust/Go 无平台调用点的模块 → `recompile_reuse`（OHOS NDK/交叉编译即可）；
   - 多语言库（如 C++ 核心 + Python 绑定）按目录的实际语言分别归桶。
4. **`needs_adaptation` vs `unadaptable` 判别（分桶最易错）**——判据**同 dim-9 SKILL「需适配 vs 无法适配」**（单一登记源，
   含"某功能因依赖未鸿蒙化而被关掉 ≠ 自动降级、要看那依赖能不能移植"那条判点）：一句话——**能否用鸿蒙可用 API 或自行
   实现把该功能重建出来？**
   - **能 → `needs_adaptation`**：典型平台抽象层（多后端加 OHOS 后端；epoll/kqueue/io_uring→鸿蒙 I/O 多路复用/poll 回退）、
     GUI 层（对应 capability_profile gui 场景，ArkUI 重写也归此桶、reason 注明重写）、Win32/POSIX 差异换 @ohos、DirectX/Metal→
     鸿蒙图形栈、运行时平台分支密集模块、**x86-only SIMD/asm intrinsics**（`arch_specific.by_arch.x86.simd_loc>0`
     且无 arm 键——补 NEON 或退标量；桶 LOC 引用该模块的 `dir_loc`、以 `simd_loc` 佐证脏度。**即便已有标量回退、
     ARM64 能正确编译运行，仍归 `needs_adaptation`**：达到性能对等需补 NEON，标量降级本身也是一项适配决策——
     **不因"回退存在"就降为 `recompile_reuse`**）。**"没有 drop-in 等价"≠ 无法适配。**
   - **不能 → `unadaptable`（从严）**：CUDA/专有 GPU、闭源二进制/无源码预编译 agent、专有内核特性/驱动、绑定特定硬件无替代
     （与 capability_profile 的 `unavailable`/`specific_hardware`、dim-9 `unadaptable_apis` 对应）。
   - **条件编译的守卫行数 ≠ 桶 LOC**——桶按模块整体归属，编译宏行数只是"该模块脏"的信号。
5. **对账收尾**：桶和 vs production.code，覆盖率 <90% 时把长尾并入默认桶；`summary` 一句话给出
   各桶占比结论。

## 常见情形（recall aids，非穷举）

- **纯 Python/JS 库**：一个 `reuse_direct` 桶打满；若含 cffi/N-API 原生扩展目录，该目录归
  `recompile_reuse`（无平台 API 时）或 `needs_adaptation`。
- **跨平台 C/C++ 库**：核心目录 `recompile_reuse`；`src/platform/`、`os/`、`arch/` 类目录
  `needs_adaptation`；`#ifdef` 总量小且分散时可整库 `recompile_reuse` + notes 说明零星守卫。
- **桌面应用（模型 C）**：GUI/窗口/启动器层通常整层 `needs_adaptation`（ArkUI/鸿蒙窗口重写）；
  业务逻辑层按语言归 `reuse_direct`/`recompile_reuse`；依赖无 OHOS 版预编译 agent 的功能模块归
  `unadaptable`。
- **示例/教程集合**（生产代码≈0）：`buckets` 近空、coverage 如实，`notes` 注明"本仓为示例集合"。

## 自我复核（一致性告警）
组装后若 `meta.harmony_warnings` 含 `cp_unadapt_no_ua`（有 unadaptable 桶但 dim-9 无 unadaptable_apis）
或 `ua_no_cp_bucket`（dim-9 有 unadaptable_apis 但无 unadaptable 桶），说明本维度分桶与 dim-9 API 登记
对不齐——按 agent 步骤 4b 复核：要么补齐缺的一侧（带证据），要么判为分桶从严/口径差异并在
`blocks/meta.json` 的 `harmony_warnings_dismissed` 记 `{code, rationale}`。`cp_loc_coverage`（覆盖率偏差）
是 `info` 留痕，通过并入长尾默认桶解决即可，不走 dismiss。

## 自我发现（反哺）

四桶装不下的情形（如"需换替代依赖后重编"这种介于 recompile 与 adaptation 之间的形态）、
LOC 估算口径歧义，记入 `meta.observations`：`{dimension:"code_partition", field, kind, value, rationale}`。
