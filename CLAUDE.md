# CLAUDE.md

Guidance for Claude Code when working in this repo.

## What this is

An **agent + skill harness** that analyzes a PC open-source software project — a
third-party **library OR an application** (e.g. VisualVM) — from its git source and
emits one JSON report, plus a **web control panel** to drive it.
Input: a git URL (or local checkout) of a Python / C-C++ / Java / JS-TS project.
Output: `report.json` covering the dimensions below.

**库 vs 应用（`library.kind`）**：库被别的代码以 API 调用、靠重编/链接移植；应用被终端用户
启动运行——其应用画像归入既有维度：入口/启动器/打包 → `build_env.entry_points`/`packaging`，
集成的运行期服务（attach/JMX/IPC）→ `runtime_surface.services`，GUI 工具包与 JDK 内部/Attach
API → `native_api`。`library.kind` 还决定 dim-9 鸿蒙口径：库走模型 A/B（重编+链接/桥接），
应用走**模型 C**（整包桌面应用——按 GUI 工具包/窗口·桌面集成/启动器·打包/运行期服务判可移植性）。
内部标识（agent 文件名 `pc-lib-analyzer`、`/api/library` 路由、package name）沿用旧名不影响。

## Core principle: model-driven, scripts only for counting

Only the mechanical, must-be-reproducible measurement (line counts, language
breakdown, test tallies) is hard-coded in a script. Every interpretive dimension
is reasoned by the model, guided by a skill prompt. Don't "fix" an interpretive
dimension by adding a parser — improve its skill prompt instead.

**生产范围（贯穿解释维度 1/6/7/8/9）**：结论只覆盖**生产代码**，排除测试与示例/演示代码——
一个只在 `tests/`、`examples/`、`demo/` 里出现的平台 API/依赖/阻碍点**不进** `native_api` /
`dependencies` / `harmony_adaptation` 结论。`code-metrics` 按目录名 token 分类并在
`metrics.json` 暴露 `code_metrics.top_dirs`（每个顶层目录 {dir,code,category}）+
`test_example_dirs` 作为基线；还机械统计 `code_metrics.platform_adaptation`（各平台
`{windows,macos,linux,posix}` 被编译宏 `#ifdef _WIN32/__APPLE__/__linux__…` **正向**包裹的
生产代码行 + total，`#ifndef`/`!defined` 不计），作为 dim-9 适配复杂度信号（守卫代码越多→
重编/适配工作量越大、`person_days` 上调）。**第二个平台适配信号** `code_metrics.platform_branches`
机械计数**运行时平台判断分支**（脚本/JVM/Go/Rust/C# 的 `sys.platform`/`os.name`/`process.platform`/
`runtime.GOOS`/`cfg!(target_os)`… 命中数 + `by_language`/`by_platform` + `samples` 样例位置；C/C++ 编译宏
归 `platform_adaptation` 不重复计）——补纯语言库无编译宏却仍需适配的平台分支；dim-9 把 `samples` 当
codegraph 追踪种子，顺分支追下游平台调用判鸿蒙等价性（无等价→blocker/`needs_adaptation_*`）。但 token **会漏判按功能命名的 demo 目录**（如 PyQt 的
`QLabel/`/`QThread/`/`QAxWidget/`），模型据结构/README **补判**为示例。仓库若是**示例/教程
集合**（生产代码≈0）则如实判定并收敛——不把 demo 的 Win32/COM/DLL 当作库的迁移阻碍。
此为模型产出口径，**存量报告需重新分析才生效**。

| # | Dimension | Owner |
|---|-----------|-------|
| 1 | Function summary + classification (**output in 简体中文**) | model — `function-summary` skill |
| 2 | Language identification | script — `code-metrics` (cloc) |
| 3 | Code volume (prod/test/example, by language) | script — `code-metrics` (cloc) |
| 4 | Test file / case counts | script — `code-metrics`, model may refine |
| 5 | Open-source license | model — `license-detect` skill |
| 6 | Dependencies | model — `dependency-analysis` skill |
| 7 | System & platform API calls (portability classes 标准/平台特有/系统内核/硬件/FFI; per-API name+purpose+call-site) | model — `native-api-analysis` skill |
| 8 | Runtime & build environment (external-interaction surface + toolchain/platform matrix) | model — `runtime-environment` skill |
| 9 | HarmonyOS PC adaptation assessment (移植分级两维:核心功能vs平台差异功能/是否可适配/难度/工作量) — **synthesis** of dims 1/6/7/8/10/11 | model — `harmony-adaptation` skill |
| 10 | Capability profile — GUI/3D 渲染/媒体/特定硬件 场景标志 + 鸿蒙支持状态 — **synthesis** of dims 1/6/7/8 | model — `capability-profile` skill |
| 11 | Cloud service involvement — 是否涉及云端服务 + 云厂商推测 (auth/存储/数据库/函数/推送/分析/崩溃上报…) — **synthesis** of dims 1/6/8 | model — `cloud-service-analysis` skill |
| 12 | Code partition — 生产代码按鸿蒙迁移复用性分桶（直接复用/重编译复用/需适配/无法适配 + LOC）— **synthesis** of dims 3/7/10/6 | model — `code-partition` skill |

**能力画像（dim 10，`capability_profile`）**：聚焦镜头，复用已算出的 native_api/runtime_surface/
dependencies/function_summary 把项目触及的**鸿蒙适配重点场景**结构化标出——`scenarios[]`，每个
`{key(gui/rendering_3d/media/hardware，开放可扩), present, kind[], specific_hardware, via[],
harmony_status(对照 caps), adaptation, evidence}`。回答"**是否涉及 X**"，dim-9 据此判修改量/能否移植：
present 场景 `harmony_status=unavailable` 或 `specific_hardware` → blocker/unadaptable_api（标 functionality_class）+ person_days 上调
（核心功能则 `overall:core_blocked`）。**两层契约（去重）：GUI/3D/媒体/硬件 四类的鸿蒙支持状态以 `capability_profile` 为权威源
——查 caps 定 `harmony_status`/`specific_hardware` 只在 dim-10 做一次；dim-9 直接消费（经 `source_capability`/
`caused_by` 回指场景 key）、不对这四类重查 caps 或从 native_api 重扫，只把状态翻译成 blocker/effort/remediation。
`adaptation` 是描述性提示、不下移植结论（那是 dim-9 的 remediation）。** `target_assumptions` 只登记 dim-10
覆盖不到的目标能力（运行时已移植性/JDK 内部模块/attach·进程模型/应用交付形态/桌面集成）。dim-9 还产 **`harmony_adaptation.required_permissions[]`**（鸿蒙化后所需
`ohos.permission.*`，`{permission, reason, source_capability(交叉引用场景 key), harmony_status, evidence}`，
对照 caps **权限模型段**）。目标侧 `references/harmony-pc-capabilities.json` 新增 **3D 图形栈 / 媒体 /
硬件设备 / 权限模型** 4 段事实供对照（多为 unknown/partial，经面板 `#/harmony-caps` 人工核实后翻转）。
`normalizeHarmony` 给缺失的 permission `harmony_status` 补 unknown，`validateHarmony` 校验 unavailable
权限须有对应 blocker。**存量报告需重新分析才有 capability_profile/required_permissions**；caps 新段与
面板/xlsx（「能力画像」+「鸿蒙权限」sheet、汇总 GUI/3D/媒体/硬件 列）即时生效。

**云服务画像（dim 11，`cloud_services`）**：又一聚焦镜头，复用已算出的 `dependencies` / `runtime_surface.network`
（硬编码云端域名）/ `native_api.dynamic_libraries` / `function_summary`，回答"**是否涉及云端服务**"并**推测云厂商**——
`{present, summary, services[]}`，每个 service `{vendor（google_firebase/aws/gcp/azure/阿里云/腾讯云/supabase/sentry…，
开放可扩，推不准记 unknown+low）, categories[]（auth/cloud_storage/database/cloud_functions/push/analytics/
crash_reporting/…，开放）, confidence（闭轴 high/medium/low）, via[], endpoints[], evidence[]}`。**范围＝广义**：任何
绑定云厂商的能力都算（登录/存储/数据库/函数/推送/分析/崩溃上报/远程配置/地图/AI 云推理/广告，含 REST 直连云端域名），
但只覆盖**生产代码**（排除 tests/examples/demo）。**与 dim-9 轻度联动**：`present` ⇒ dim-9 在 `required_permissions[]`
登记 `ohos.permission.INTERNET`（`source_capability:"cloud_services"`）；某厂商原生 SDK 无鸿蒙移植 → 记
`target_assumptions`/`blocker`（`caused_by` 引用，遵循单一登记源不重述）。`validateReport`（serve-time）用 `CLOUD_SIGNALS`
启发式查漏判（deps/网络出现云厂商 SDK/域名但 `cloud_services` 未标、或 present 却无 INTERNET 权限）。**存量报告需重新
分析才有 cloud_services**；面板「云服务」区块 + xlsx「云服务」sheet 即时生效（缺块降级为不渲染）。

**代码分区（dim 12，`code_partition`）**：鸿蒙迁移**工作量评估的量化底座**——把生产代码按迁移复用性分 **4 桶**
（闭轴 `buckets[].class`：`reuse_direct` 直接复用 / `recompile_reuse` 重编译复用 / `needs_adaptation` 需适配 /
`unadaptable` 无法适配），模块/目录粒度 + LOC。**LOC 必须引用 `code_metrics.dir_loc`**（metrics.py 新增的
目录级生产 LOC 底数，depth≤2 cap 80）做对账：桶和 ≈ `production.code`（`coverage.pct` ≥90%，serve-time
`validateReport` 校验偏差 >15% 告警）。综合 dir_loc / platform_adaptation / platform_branches /
**`arch_specific`**（第三个机械信号：汇编文件 LOC 按 x86/arm/riscv 归类 + SIMD intrinsics 头 + C/C++/Rust
内联汇编命中，注释/字符串已剔除——仅 x86 无 arm 回退 ⇒ arm64 适配硬点）/ native_api 调用点 / capability_profile，
**不重扫源码**。**单一登记源**：`unadaptable` 桶只登记模块+LOC，API 粒度引用 dim-9 `ua:*` 不重述。dim-9 据此定
`effort.person_days` 并拆 **`effort.breakdown[]`** 分项（component 推荐集 recompile/api_adaptation/gui/
deps_porting/build_system/testing_verification/packaging）。**其中 `recompile`/`api_adaptation` 两项由归一
（`report_normalize.py`/`server.js` 镜像）据 code_partition LOC **确定性派生**并覆盖模型值：`recompile =
recompile_reuse 桶 LOC ÷ 速率`、`api_adaptation = needs_adaptation 桶 LOC ÷ 速率`（速率读 `.panel-settings.json`
`recompileLocPerDay`/`adaptationLocPerDay`，默认 3000/500 行/天，面板「系统设置」可调；改后新分析即时生效、
存量重跑 `migrate_normalize.py` 回填）。**模型产出 breakdown 时，`effort.person_days` 总量由归一重算为「各分项之和」**
（含派生两项 + 模型其余分项），`effort.level` 随之派生；模型无 breakdown 时保留其整体 person_days。
另产 **`harmony_adaptation.critical_dependencies[]`**（迁移关键路径依赖，有序：未鸿蒙化 + 阻塞核心推进才列，
`name` 与 `dependencies[].name` 逐字一致，`refs` 引用 bk:/ua:/ta: id）。**serve-time 派生互补**：拓扑 rollup
（`rollupAdaptation`）额外算每节点 `criticalPath[]`（沿贡献人天最大的已分析子依赖下钻的链）+ `blockingChildren`
按人天排序——**存量报告不重跑即有**；`code_partition`/`critical_dependencies`/`breakdown` 是模型产出，
**存量报告需重新分析才有**。面板「代码分区」堆叠条 + 鸿蒙段「工作量分项/关键路径依赖」表 + 拓扑关键路径高亮；
xlsx 汇总加 汇编代码行+4 桶 LOC 列，新增「代码分区/关键路径依赖/工作量分项」sheet。

**单一登记源（防双计）**：同一事实只在其主清单登记一次——`capability_profile.scenarios` 是"涉及哪些场景 +
鸿蒙状态"的登记源、`required_permissions` 是权限登记源、`unadaptable_apis` 是不可适配 API 的粒度源、
`target_assumptions` 是目标能力假设源、`blockers` 是结果层——dim-9 的 blocker/unadaptable 用
`caused_by`/`source_capability` **引用**而非重述，避免 person_days 被重复计入。**跨维一致性校验**
`validateReport`(`web/server.js`，serve-time，与 `validateHarmony` 合入 `meta.harmony_warnings`)
启发式查 capability_profile↔native_api↔dependencies↔dim-9 的漏判/矛盾（如 deps 有 Qt/cuda 但 capability_profile
漏标、场景缺 evidence、权限 source_capability 悬空、present+unavailable 场景在 dim-9 无登记），面板「数据
一致性提示」展示。**每条告警带稳定 `{code, class}`**（`report_normalize.py`/`server.js` 镜像同产）：`class` 闭轴
`actionable`（召回/漏判启发式）/ `info`（归一器已确定性修好的审计留痕，如 `pclass_adjusted`）。**告警的模型
自我复核（analyze 时 in-agent，agent 步骤 4b，单趟）**：agent 读回首次 assemble 的 `meta.harmony_warnings`，只处理
`actionable` 的——**真漏**带 file:line 证据回改源维度块（capability_profile/cloud_services/dependencies/
target_assumptions/evidence，**不碰派生轴**），**误报**在 `blocks/meta.json` 写 `meta.harmony_warnings_dismissed`
（`[{code, rationale}]`）——重跑 assemble 后归一把被驳回的从 `harmony_warnings` 移入 **`meta.harmony_warnings_reviewed`**
（`[{code, message, rationale}]`，面板「已复核」折叠区展示），active 只剩未驳回项。护栏：新增须有证据（拿不出→
判误报别硬补）、单趟不清零、`info` 不可驳。**存量报告需重新分析才有自我复核**；warnings 形状升级（字符串→对象）
由 `migrate_normalize.py` 确定性回填、`NORMALIZED_VERSION` 随之 bump。**计数准确性**：platform_adaptation/
platform_branches 已剔除注释与字符串字面量内的命中（`_masked_lines`），并有 `code-metrics/scripts/selftest.py` 单测固化。

Dependencies (dim 6) carry `acquisition` (how the build obtains each one:
system/vendored/fetchcontent/download_build/submodule/package_manager/prebuilt_binary)
+ `source` + `declared_in`, distinguishing 本地/远端/系统 deps. `ecosystem` is a
**language only** (build-tool nature goes in `scope:build`; the panel groups
build/test-scope deps under 构建/工具链). Runtime dynamically-loaded libs
(`native_api.dynamic_libraries`, each with `acquisition`/`source` — e.g. self_build
wrappers vs external libs) are also shown under dependencies in the panel.
`native_api.groups[].apis[].count` gives per-API call-site counts. `library.bindings` lists the binding languages of a
polyglot library (e.g. a C++ core with Python/Java bindings). Dim 8 is purely
descriptive (no adaptation advice). Dim 9 (`harmony_adaptation`) is the opposite —
**prescriptive and a synthesis**: it reasons over the already-filled dims (ecosystem,
native_api, runtime_surface, dependencies, build_env) to produce a HarmonyOS PC
porting plan (移植分级两维/difficulty/blockers/effort), reusing their `evidence`
rather than re-scanning source. **Default口径: HarmonyOS PC with already-ported
language runtimes** (Python/Node.js/Java/Rust/Go/Julia are ported) — a pure-script
library runs on the ported runtime, so the runtime itself
is NOT a blocker and such libs are NOT auto-blocked; the real work is native
extensions / C deps / platform APIs. The strict ArkTS-sandbox model is a secondary口径
used only when the target is an ArkTS app. **移植分级重构（核心功能 vs 平台差异功能两维）**：
`porting_class` is the single authoritative **3-value** machine axis
(no_adaptation 无需适配 / recompile_only 仅交叉编译 / needs_adaptation 需适配). Within needs_adaptation the
model tags each `unadaptable_apis[].functionality_class` (**core** = the Win/Linux/mac 功能交集 / **platform_specific**
= 平台特有) and the normalizer DERIVES `adaptation_assessment` = `{core, platform_specific}`两维小结 +
a 5-way `effective_class` (no_adaptation / recompile_only / needs_adaptation / needs_adaptation_platform_partial /
needs_adaptation_core_partial — the dep-topology page's 5-way bucket color) + an `overall` 是否可适配 verdict
(adaptable / adaptable_with_tailoring / core_blocked). **`feasibility` and `recommended_path` are REMOVED**;
`overall` (derived from whether core functionality has unadaptable points) replaces the old feasibility verdict.
The model only estimates `effort.person_days:[lo,hi]` (numeric → aggregates up
the dep tree); the **5-tier difficulty `effort.level`** (very_low…very_high / 极低…极高) is
**server-DERIVED** (`deriveDifficultyLevel` = `effective_class` floor × person_days bucket, take-higher)
— NOT an independent model axis, so it can't drift from the migration class. `confidence` (high/medium/low)
drops to ≤medium when a required target_assumption is `unknown`, and propagates min up the rollup.
Other closed axes: `blockers[].severity`/`blockers[].adaptability`(adaptable/partial/unadaptable —
the structured signal `derivePortingClass` reads instead of regex over open-vocab category).
Open vocab: `blockers[].category`/`harmony_status`. The three problem lists are a
**single-source-of-truth model with cross-refs**: a fact is登记 once in its primary list
(`target_assumptions`=root cause, `unadaptable_apis`=granular machine layer for rollup, `blockers`=result)
and referenced elsewhere by stable `id` via `caused_by`/`manifests_as` (no duplicate prose → no
double-counted difficulty). **Single source of truth (`scripts/report_normalize.py`):** the dim-9/dim-12
derivations (`porting_class` reconcile — model's pick is a FLOOR clamped UP to needs_adaptation by the dim-12
`needs_adaptation`/`unadaptable` buckets + `unadaptable_apis`, never lowered; the model's raw pick kept in
`harmony_adaptation.porting_class_model`), `adaptation_assessment`/`effort.level`, `code_partition` canonicalization,
and the `validate*` consistency checks are implemented ONCE in Python and run at **assemble time** so
`report.json` is **born normalized + stamped `meta.normalized_version`** — the panel, the Excel export
(`export_xlsx.py` reads the persisted value, no longer re-derives), and any direct reader all agree.
`web/server.js` keeps a byte-identical JS **mirror** (a full-corpus parity test asserts they match) only
to upgrade legacy/older-stamp reports at serve time; `/api/report` serves a current-stamp report as-is.
`scripts/migrate_normalize.py` back-fills 存量 reports on disk; bump both `NORMALIZED_VERSION`s together on
a logic change. (`scripts/test_report_normalize.py` fixtures the derivation.) The rollup also aggregates
`rollupEffort`(Σ person_days of actually-depended children)/`rollupLevel`/`rollupConfidence`.

**API-granular un-adaptability + bottom-up roll-up.** When some functionality is truly
unportable, dim 9 lists it at **API granularity** in `harmony_adaptation.unadaptable_apis[]`
(`{api, public_entry, reason, blocking_native_api, category, evidence}`) — `public_entry` is the
library's own public function that routes to the unsupported native API. Dim 6 records, per
dependency, the symbols this library actually calls in `dependencies[].used_symbols[]`. The panel
then computes each node's **effective (含依赖) adaptation class bottom-up** at serve time
(`rollupAdaptation` in `web/server.js`, deepest-first worst-wins over the dep DAG): a child's
un-adaptable API only drags the parent up if `parent.used_symbols ∩ child.unadaptable_apis[].public_entry`
is non-empty (else it falls back to dependency scope — optional/peer non-blocking). harmonized deps
are sealed leaves; an unanalyzed child sets `rollup_uncertain`. This is serve-time/derivational
(like `derivePortingClass`) — **存量 reports get self+rollup classes without a re-run**; only the new
`unadaptable_apis`/`used_symbols` model outputs need a re-analyze (the recursive driver covers the tree).

**目标平台能力 + 假设显式化（准确性核心）.** 鸿蒙判定的准确性 = match(**源所需能力**, **目标
平台能力**)。目标侧事实的**权威源是 `references/harmony-pc-capabilities.json`**（`.md` 是其渲染视图，
勿手改 .md）——运行时、JDK 内部模块、桌面 GUI/窗口栈、桌面集成、进程/安全模型、应用交付形态、arch；
状态 available/partial/unavailable/**unknown**。**该画像对库与应用通用**（目标事实与被分析对象无关）。
**补充/更新机制**：① Tier1 自动同步——`node scripts/harmony_caps.js sync`（或面板「�wildcard」按钮）对带
`check{via:'cmd-pkgs'|'pypi'}` 的行复用 `web/harmony-mirror.js` 联网核对（面板「🔄 联网同步」按钮亦可；命中⇒available+来源+日期；
未命中不降级），与 `dependencies[].harmony_adapted` 同一数据源；② Tier3 人工策展——面板
`#/harmony-caps` 页（`/api/harmony-caps` GET/sync/row）展示并高亮 unknown/过期行，可内联「标记已核实」
写回 JSON（并自动 `render` 出 .md）。dim-9 把项目所需目标能力逐项对照该参考，写入 `harmony_adaptation.target_assumptions[]`
（`{capability, capability_key, required, target_status, impact, source}`）：`available`→不阻碍，`partial`→partial 阻碍，
`unavailable`→blocker/unadaptable_apis，**`unknown` 且 required → 记假设 + 下调 `meta.confidence_overall`
+ notes 说明，禁止据未知臆断为可行**。对**应用**尤为关键（GUI 工具包/headful AWT、跨进程 attach、
JDK 内部模块开放性、应用交付形态多为决定性且常 unknown）。面板鸿蒙段展示假设表 + 「N 项未核实」
提示；xlsx 有「鸿蒙目标假设」sheet。参考文件是**人工维护的事实源**——把核实到的事实填回去，下次
分析即受益（验证：把某项 unknown 改成 available 重分析，对应假设翻转、阻碍降级、置信回升）。
**反哺闭环（模型观察 → 目标能力研究优先级）**：每条 `target_assumptions` 带 `capability_key`（命中 caps 行的**叶 id**，
如 `swing`/`jdk_attach`/`dotnet`）——`web/server.js` 的 `/api/harmony-caps` 据此跨报告聚合每行 `demand`（`{count,unknown,libs}`
＝「被 N 个分析需要」），面板 `#/harmony-caps`「研究优先级」列展示、未核实+高需求置顶。对**不上 caps 任何行的必需能力**，
模型另记一条 `meta.observations{dimension:"harmony_caps", kind:"caps_gap"}` 提案补行，经既有 `/api/observations` 汇入
`#/observations`（标签「目标能力缺口」）供人工把缺失能力补进参考——下次分析即可对号入座。**存量报告需重新分析才有
`capability_key`/`caps_gap`**（面板 demand 聚合与标签对已分析报告即时生效）。
**目标侧事实源分两层**：PC 形态可用性 = `harmony-pc-capabilities.json`（权威）；API 级存在性/权限精确名
（ohos.permission.\*）/SysCap = **opencode 全局鸿蒙文档 skill**（辅助）——`~/.config/opencode/skills/` 下的
`harmonyos-sdk-api-lookup`（4000+ 篇 API 参考）与 `harmonyos-docs-lookup`（2860 篇指南/FAQ）。server 启动时探测
（`HARMONY_DOC_SKILLS`）、analyze prompt 经 `{harmonySkillsHint}` 告知 agent（设置 `enableHarmonyDocSkills` 可关；
headless 下 opencode 内置 `skill` 工具默认放行、skill 目录外部读可用——已探针验证，无需 OPENCODE_PERMISSION）。
dim-9/10 按 harmony-adaptation SKILL.md「目标侧 API 事实核查」使用：判等价 API/写 remediation/填权限名前查文档
（每库 ≤10 次、文件名过滤优先、evidence 引文档文件名），**文档存在 ≠ PC 可用、冲突时 caps JSON 优先、
unknown 不因文档翻转**；降级链 skill 工具 → 直接 Grep 目录 → 仅 caps JSON+warning。`arkts-rules` 评估默认不用。

## Skill authoring convention (principle-first, open-vocabulary, self-capturing)

Maximize the model's reasoning; we only fix the **output contract**. Every
interpretive skill (dims 1, 5, 6, 7, 8, 9) follows this shape:

1. **主旨与原则 (Goal & principles)** — what the dimension is for and what a good
   answer looks like, up top. Plus the **meta-rule**: *"The output contract is the
   only hard constraint. The taxonomy below is a recommended starting set, not a
   closed list — if a scenario doesn't fit, classify it as best you can, coin a
   concise lowercase value, and record it in `meta.observations`."*
2. **输出契约 (Output contract)** — the JSON shape. The one hard requirement.
3. **思路 (Approach)** — adaptable guidance, NOT mandatory numbered steps.
4. **常见情形 / 推荐取值 (Common cases / recommended values)** — recall aids
   (manifest lists, API families, …); explicitly "common, not exhaustive".
5. **自我发现 (Self-capture)** — record novel values / gaps / ambiguities in
   `meta.observations`.

**Two-tier vocabulary** — keep classification consumable yet open:
- **Stable closed axes (model-set)**: `library.ecosystem`/`bindings`,
  `dependencies[].locality` (local/remote/system/runtime), `native_api.groups[].category`
  (standard/platform/system/hardware/ffi) and `.platform`. The UI relies on these.
  Plus dim 9's `harmony_adaptation.porting_class`(3-value)/`unadaptable_apis[].functionality_class`(core/platform_specific)/
  `confidence`/`effort.level`(server-derived)/`adaptation_assessment.effective_class`+`.overall`(server-derived)/
  `blockers[].severity`/`blockers[].adaptability`. Plus dim 5's `license.category`
  (commercial/strong_copyleft/weak_copyleft/permissive/undeclared) — **a STRICT closed axis**:
  unlike the open词表 below, the model may **not** coin new values or log them to `meta.observations`;
  it must map to exactly one of the five. Server `deriveLicenseCategory`/`normalizeLicense`
  backfills it from `spdx`/`name` for 存量 reports (model value wins), like `derivePortingClass`.
- **Open detail vocabulary (model may coin)**: `dependencies[].acquisition`,
  `native_api.groups[].type`, `harmony_adaptation.blockers[].category`/
  `blockers[].harmony_status`, etc. The UI degrades unknown values to the raw string.

`meta.observations` (`{dimension, field, kind, value, rationale}`) is aggregated by
`/api/observations` and shown on the panel's **模型观察 / 词表反哺** page (`#/observations`)
for human review — promote recurring coined values into a skill's recommended set
over time. Do NOT auto-rewrite skills.

## Layout

```
.claude/
  agents/pc-lib-analyzer.md      # orchestrator agent — clones, runs metrics, reasons, writes report.json
  agents/repo-resolver.md        # on-demand agent — judges a C/C++ dep's source-repo URL (or system/no-repo)
  skills/
    code-metrics/                # ONLY script-backed skill (deterministic)
      scripts/{metrics.py, common.py, tests.py}
    function-summary/  license-detect/  dependency-analysis/  native-api-analysis/  # model-driven prompt skills
    runtime-environment/  harmony-adaptation/                                       # (dim 8 + dim 9 synthesis)
references/report_schema.json    # output contract — the report MUST conform
web/
  server.js                      # zero-dep Node control panel (http + SSE)
  resolve.js                     # zero-dep repo-URL resolver (registry APIs) for /api/resolve-repo
  harmony-mirror.js              # zero-dep OpenHarmony-PC-mirror adapted-package check
  public/{index.html, app.js, styles.css}   # two-level light-theme SPA
  public/vendor/cytoscape.min.js  # vendored graph lib (dep-topology page only; no build step)
scripts/export_xlsx.py           # summary .xlsx export (openpyxl); panel /api/export spawns it
scripts/harmony_adapted.js       # CLI over harmony-mirror.js; agent stamps deps[].harmony_adapted
requirements.txt                 # python deps (openpyxl, for export only)
repos/   <group>/<lib>/          # cloned libraries, grouped by workspace (gitignored)
runs/    <group>/<lib>/<ts>/     # per-run report.json + run.log.jsonl + meta.json (gitignored)
.panel-settings.json             # panel settings (gitignored)
.panel-library-tags.json         # per-library 来源标签 {"<group>/<lib>":["primary","passive"]} (gitignored)
```

## Running

- **Panel:** `npm start` (or `node web/server.js`) → http://localhost:8765
  (`PORT=9000` to override). Run from the project root so opencode (cwd = root)
  can read `.claude/`.
- **Deterministic metrics only:**
  `python3 .claude/skills/code-metrics/scripts/metrics.py --repo <checkout> --out <in-project-path>/metrics.json`
- **Agent headless (what the panel does):**
  `opencode run -m <model> --format json "<prompt → .claude/agents/pc-lib-analyzer.md>"`

Requires: `git`, `python3` (3.11+ for `tomllib`), `cloc` (preferred) or `tokei`,
and `opencode` with a configured model. Excel export additionally needs
`openpyxl` (`pip install -r requirements.txt`).

## Web panel architecture

- **Level 1 (dashboard, `#/`):** library cards with status/metrics, batch select,
  batch + concurrent clone and analyze, system settings. Each library carries 来源标签
  (`主软件`=primary / `被动依赖`=passive, stored in `.panel-library-tags.json`, union-merged):
  manual clone defaults primary (chooser in the clone dialog), recursion + pending-deps
  「加入列表」auto-tag passive, and the 🏷 row button edits them (`POST /api/library-tags`).
  Tags drive a homepage 标签 filter. Pagination supports selectable page size (localStorage)
  + jump-to-page; batch selection persists across pages.
- **分组（工作空间隔离）：** every library lives in a group — directories are nested
  `repos/<group>/<lib>` + `runs/<group>/<lib>/<ts>`, so clone/analyze/report/recursion/
  topology/pending-deps/export are all scoped to a group and never cross-contaminate
  (same lib can be cloned independently into different groups). 'default' always exists;
  on first start `migrateToGroups()` moves any pre-grouping flat `repos/<lib>`/`runs/<lib>`
  into `default/` (idempotent, re-keys the tags file). The active group is a localStorage
  state (`activeGroup`); the dashboard has a group selector + 「＋ 分组」(`/api/groups`
  GET/POST). Server fns take a `group` param (`safeGroup` validates `[A-Za-z0-9._-]`,
  blocking traversal); recursion inherits the root's group. Every group-scoped endpoint
  accepts `?group=`/`body.group` (default 'default').
- **codegraph 索引：** when codegraph is installed+enabled the server pre-builds the
  structural index **right after a successful clone** (`ensureCodegraphIndex` → `codegraph
  init -i <repoPath>`, or `sync` if `.codegraph/` already exists), and again best-effort at
  analyze start. The analyze prompt tells the agent the index is pre-built (query it; fall
  back to grep if a call fails) instead of building it itself.
- **Level 2 (detail, `#/lib/<name>`):** run history, live log (SSE, parses
  opencode `--format json` events), rendered report.
- **库身份 & 依赖关联（多键，URL 优先）：** a library's storage **handle** is its git
  basename (`repoNameFromUrl`), but its **identity** is a set of keys, joined primarily by the
  **owner-qualified canonical repo URL** (`canonicalRepoKey(url)` = `host/owner[/subgroup…]/repo`,
  host-agnostic, keeps full path; returns null → falls back to name keys for registries/tarballs/
  fake-homepage `.git`, never force-links a junk URL). `buildIdentityIndex` indexes every analyzed
  lib by `byUrl`(canonicalRepoKey of `source_url` + the clone-time `.identity.json`) and `byName`
  (`nameKeys`: eco-scoped variants of package_name/handle/repo-basename/`aliases`/`import_names`,
  handling lib-prefix `libpng↔png` + version suffix). `resolveDepLib(d, idx)` matches a dep **URL-first**
  — repo URL from the dep's own text, its model-emitted `source_repo` (dim-6), or the panel's
  `.resolve-cache.json` (`resolve.cacheGet`) — then by name variants. This fixes "依赖名≠源码仓名"
  假阴 and owner-blind 假阳. **L2 撞名**: `startClone` disambiguates the handle (`zlib__madler`) when the
  basename collides with a DIFFERENT upstream repo (by `.identity.json`), instead of erroring/overwriting;
  existing handles are never disturbed. L1/L2 是 serve-time/克隆时（对存量报告即时生效）；dim-6/dim-1 的
  `source_repo`/`registry_name`/`aliases`/`import_names` 需重分析才富集。
- **待分析依赖 (`#/pending-deps`):** cross-library aggregation of dependencies that
  analyzed libraries depend on but that are NOT themselves analyzed yet (matched via
  the unified identity index — URL-first then name variants — as the dep tree). Each row can be cloned into
  `repos/` ("加入列表") — best-effort prefilling a git URL extracted from the dep's
  `source`/`version` — and then analyzed in place. Drives the iterative "analyze the
  deps of the deps" loop. A dep leaves this list once analyzed. The git URL can also be
  **resolved online** from the package registry (per-row 🔎 or 「一键填充全部」) via
  `/api/resolve-repo` → `web/resolve.js` (zero-dep `https`): PyPI/npm/crates.io/Maven
  Central by registry API. **C/C++** has no central registry and CMake `find_package`
  names are interface/module names, not repos — so it resolves in layers: a curated
  `CPP_KNOWN` map (common CMake names → repo, e.g. ZLIB→madler/zlib, PNG→libpng) which
  also flags **interface/virtual packages** (BLAS/LAPACK/OpenGL/Threads…) as
  `interface:true` with implementation candidates rather than one wrong repo → then a
  **vcpkg** port-homepage lookup (detects "Metapackage" interfaces) → then GitHub
  search (low confidence). The panel shows a per-row candidate picker for interface /
  multi-candidate results instead of auto-filling. Results cache to `.resolve-cache.json`
  (gitignored, 7-day TTL); gated by the `enableNetworkResolve` setting.
  On C/C++ rows a second **「🤖 智能解析」** button escalates to an **LLM agent**
  (`.claude/agents/repo-resolver.md`, spawned via `opencode --agent repo-resolver`):
  it reads the dep's description/context (scope/locality/purpose + the dependent libs'
  checkouts) and `curl`s GitHub search to judge odd names a blind search can't — and
  recognises **system/platform libs with no repo** (e.g. a generic `log` → Android NDK
  `liblog`, `is_system:true`). `POST /api/resolve-repo-agent` queues the job (cap 2,
  separate from analyses) → `GET …?job=<id>` polls; the server verifies the URL with
  `git ls-remote` (demotes unreachable to a candidate) and merges the verdict (with
  中文 `reasoning`) into `.resolve-cache.json` via `resolve.cachePut`, so a later 🔎
  hits it too. Scratch results live in `.resolve-agent/` (gitignored); gated by
  `enableAgentResolve`.
- **模型观察 (`#/observations`):** see the two-tier vocabulary section above.
- **Backend (`web/server.js`):** REST + SSE. Analyses go through a concurrency
  queue capped by `settings.maxConcurrent`; clones run concurrently. Endpoints:
  `/api/libraries`, `/api/library`, `/api/jobs`, `/api/clone` (batch),
  `/api/analyze` (batch), `/api/stream` (SSE), `/api/report`, `/api/runlog`,
  `/api/depgraph`, `/api/observations`, `/api/pending-deps`, `/api/settings`,
  `/api/models`, `/api/testmodel`, `/api/export` (xlsx), `/api/resolve-repo`,
  `/api/harmony-status`, `/api/resolve-repo-agent` (POST start / GET poll),
  `/api/dep-topology`.
- **依赖拓扑 (`#/topology`):** pick an analyzed library → a **runtime-only transitive
  dependency graph** (Cytoscape.js, breadthfirst layout), each node colored by HarmonyOS
  status: **已鸿蒙化** (mirror) / **未分析** / one of 5 未鸿蒙化 `effective_class` buckets — **无需适配**
  (pure script), **仅交叉编译** (C/C++, no platform API), **需适配·全部可适配** (needs work but all
  used functionality portable), **需适配·平台差异有不可适配点** (only platform-specific功能 unportable, core OK),
  **需适配·核心有不可适配点** (core functionality has unadaptable points — most severe). `/api/dep-topology?name=`
  builds the DAG via `buildDepTopology` (runtime/optional + non-local deps, `resolveDepLib`
  for alias matching) and sets each node's class from the derived `adaptation_assessment.effective_class`
  (via `effectivePortingClass()`), a serve-time derivation from the
  existing porting_class/blockers/unadaptable_apis[].functionality_class, so **存量 reports are classified
  without a re-run** (re-analyze upgrades to the agent's value). The page has a **本体 / 含依赖(综合)**
  toggle: 含依赖 colors by the bottom-up `rollupClass` (`rollupAdaptation`, see dim-9 above), with a
  「含未分析依赖」flag and a per-node list of which child deps (via which symbols) raised the class.
  Indirect deps are only visible for
  deps that are themselves analyzed (else 未分析). Cytoscape is **vendored** as a single
  `web/public/vendor/cytoscape.min.js` and lazy-loaded only on this page — a deliberate,
  scoped exception to the panel's zero-dep rule (still no build step / no npm).
- **已鸿蒙化检测 (`/api/harmony-status`):** `web/harmony-mirror.js` (zero-dep, Node
  `https`) checks whether a dependency is already ported to HarmonyOS PC, per ecosystem:
  - **Python** ('simple'): the OpenHarmony PC PyPI mirror (pypi.cnb.cool/
    OpenHarmonyPCDeveloper) is a full PyPI proxy with no listable root (404s), so we
    probe each package page on demand — the port signal is a native **`ohos` wheel**
    (e.g. numpy `*-ohos_aarch64.whl`), not mere presence. Cached per-package.
  - **C/C++** ('list'): the cmd-pkgs README (gitcode.com/OpenHarmonyPCDeveloper/
    cmd-pkgs) lists every prebuilt package in its install commands (`sh -s -- <name>
    <ver>`, ~1245 pkgs: zlib/openssl/boost/eigen/cairo/…); membership (with name
    variants — strip/add `lib`, drop trailing digits) ⇒ adapted. The list is cached.
  Both cache to `.harmony-mirror-cache.json` (gitignored). The
  panel badges 🟢 已鸿蒙化 on deps (report dep list, dep tree, pending-deps) + shows
  N/M counts + a 「只看未鸿蒙化」filter; gated by the `enableHarmonyMirror` setting.
  For dim 9: `scripts/harmony_adapted.js` (same module) stamps
  `dependencies[].harmony_adapted` so an adapted dep is **not** a blocker — this
  extends the earlier "ported runtimes" 口径 from language runtimes to individual libs.
- **导出 Excel (`/api/export`):** dashboard 「导出 Excel(定制表)」按钮 → server spawns
  `scripts/export_xlsx.py` (Python + **openpyxl**) which flattens every library's
  latest `report.json` into **一张宽表**「分析汇总」(两级表头, 每库一行), streamed back
  as a download. 列组含 基本信息/开源协议/代码量/平台适配/代码分区/能力画像/云服务/鸿蒙适配评估,
  外加 **鸿蒙移植·阻碍/假设/关键路径** 组三列——内容**和报告 dim-9 一样详细**(富文本多行单元格:
  分布 headline + 逐条完整字段): `移植阻碍点(严重度分布)`(逐条 severity·adaptability·category·source·
  鸿蒙状态 + `问题`/`改造`/`证据`, 按归一后 `severity` 整格上色)、`目标能力假设(阻碍分布)`(逐条
  能力·必需性·`target_status` emoji + `影响`/caps键, required 优先·状态重→轻排, 按最严重 required 上色)、
  `关键路径依赖(建议移植顺序)`(按 `critical_dependencies[].order` 升序逐条 名称·人天分担·`为何关键`·关联, 中性)。
  数据格**按值语义配色**
  (`_Styled` str 子类携 fill_key + `_SEMANTIC_FILL` 软色, 与面板 badge 一致): 移植分级/代码适配/运行前提/
  难度 + 上述新列均随值上色, 未命中的普通格仍走斑马纹。**存量报告需重新分析才有 target_assumptions/
  blockers/critical_dependencies**——缺失时新列优雅显示 `无`/`—` 不报错。`?names=a,b` exports only
  selected libs. The script is standalone (CI/offline) too; openpyxl is the **only** third-party dep (web/ stays zero-dep).

## Gotchas (learned the hard way)

- **opencode blocks on an open stdin pipe** — always spawn it with
  `stdio: ['ignore','pipe','pipe']` (stdin EOF). Otherwise it hangs forever with
  no output.
- **opencode headless auto-rejects external directories** (`/tmp/*` etc.). The
  agent must write the clone, metrics, report, and ALL scratch **inside the
  project** (under the run dir). The analyze prompt pins `--out {metricsPath}`
  for exactly this reason.
- **An analyze that exits 0 but writes no `report.json` is a failure**, not
  success — `Job.end` marks it `error`.
- opencode's session DB can corrupt/bloat (`~/.local/share/opencode/opencode.db`,
  error `NOT NULL constraint failed: session_message.seq`). Fix: move the
  `opencode.db*` files aside; opencode recreates a fresh DB.

## Conventions

- Keep `web/server.js` and `web/public/*` **zero-dependency** (Node stdlib +
  vanilla JS, no build step).
- Repos are **shallow-cloned** (`git clone --depth 1`). After a **successful** analyze,
  the server prunes `repos/<name>/.git` to save disk (setting `pruneGitAfterAnalyze`,
  default on). The working tree stays, so cloc / re-analyze still work — but a
  re-analyze can't read `library.commit` unless you re-clone; turn the setting off to keep `.git`.
- **Monorepo 子目录分析**：粘贴 `…/tree/<分支>/<子目录>` 形式的 URL（或克隆弹窗填「子目录」字段）即可
  只分析大仓的某个子目录（如 chromium 的 `components/cronet`）。`parseRepoUrl` 从 URL 解析出 `{gitUrl,ref,subpath}`；
  有 subpath 时 `startClone` 用 **稀疏部分克隆**（`--depth 1 --filter=blob:none --sparse` + `sparse-checkout set --cone <subpath>`，
  cone 模式自带仓根文件 DEPS/BUILD.gn，巨仓从 GB 降到数十 MB），handle=子目录叶名（`cronet`），
  `.identity.json` 存 `subpath`/`ref` 且 `canonicalKey` 带 `#<subpath>` 判别符（同仓不同子目录 = 不同库，不互相覆盖/别名）。
  **存储模型 = 每子目录一个独立库**（handle==目录==分析单元 不变式保持）。分析时 `createAnalyzeJob` 把
  `{repoPath}` 指向子目录、新增 `{repoRoot}`=克隆根、codegraph 只索引子树，prompt `{monorepoNote}` 告知 agent：
  metrics/native_api/依赖以子目录为范围、可读仓根 manifests、git commit 用仓根、写 `library.source_subpath`/`monorepo`。
  metrics.py 无需改动（`--repo` 接受任意目录）。非 monorepo 路径逐字不变（无 subpath 时 `{repoPath}=={repoRoot}`）。
- The `languages` / `code_metrics` / `tests` report blocks come verbatim from
  `metrics.py`; don't recompute them by hand. Everything else is model-reasoned.
- To extend: test idioms → `code-metrics/scripts/tests.py`; classification rules
  → `common.py`; analysis method for an interpretive dimension → that skill's
  `SKILL.md`; output shape → `references/report_schema.json` + the agent's
  assembly step.
