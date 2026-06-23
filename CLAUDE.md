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
`test_example_dirs` 作为基线；但 token **会漏判按功能命名的 demo 目录**（如 PyQt 的
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
| 9 | HarmonyOS PC adaptation assessment (可行性/难度/路径/工作量) — **synthesis** of dims 1/6/7/8 | model — `harmony-adaptation` skill |

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
porting plan (feasibility/difficulty/path/blockers/effort), reusing their `evidence`
rather than re-scanning source. **Default口径: HarmonyOS PC with already-ported
language runtimes** (Python/Node.js/Java/Rust/Go/Julia are ported) — a pure-script
library runs on the ported runtime (`run_on_ported_runtime`), so the runtime itself
is NOT a blocker and such libs are NOT auto-`infeasible`; the real work is native
extensions / C deps / platform APIs. The strict ArkTS-sandbox model is a secondary口径
used only when the target is an ArkTS app. Its closed axes are `feasibility`/`overall_difficulty`/
`effort_estimate`/`porting_class` (no_adaptation/recompile_only/**needs_adaptation_full**(全部可适配)/
**needs_adaptation_partial**(部分可适配)/infeasible — the dep-topology page's 5-way bucket; legacy
`needs_adaptation` kept as a partial alias)/`blockers[].severity`; open vocab is `recommended_path`/
`blockers[].category`/`harmony_status`.

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
（`{capability, required, target_status, impact, source}`）：`available`→不阻碍，`partial`→partial 阻碍，
`unavailable`→blocker/unadaptable_apis，**`unknown` 且 required → 记假设 + 下调 `meta.confidence_overall`
+ notes 说明，禁止据未知臆断为可行**。对**应用**尤为关键（GUI 工具包/headful AWT、跨进程 attach、
JDK 内部模块开放性、应用交付形态多为决定性且常 unknown）。面板鸿蒙段展示假设表 + 「N 项未核实」
提示；xlsx 有「鸿蒙目标假设」sheet。参考文件是**人工维护的事实源**——把核实到的事实填回去，下次
分析即受益（验证：把某项 unknown 改成 available 重分析，对应假设翻转、阻碍降级、置信回升）。

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
  Plus dim 9's `harmony_adaptation.feasibility`/`overall_difficulty`/`effort_estimate`/
  `blockers[].severity`.
- **Open detail vocabulary (model may coin)**: `dependencies[].acquisition`,
  `native_api.groups[].type`, `harmony_adaptation.recommended_path`/`blockers[].category`/
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
repos/   <lib>/                  # cloned libraries (gitignored)
runs/    <lib>/<ts>/             # per-run report.json + run.log.jsonl + meta.json (gitignored)
.panel-settings.json             # panel settings (gitignored)
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
  batch + concurrent clone and analyze, system settings.
- **Level 2 (detail, `#/lib/<name>`):** run history, live log (SSE, parses
  opencode `--format json` events), rendered report.
- **待分析依赖 (`#/pending-deps`):** cross-library aggregation of dependencies that
  analyzed libraries depend on but that are NOT themselves analyzed yet (matched via
  the same `ecosystem+name` index as the dep tree). Each row can be cloned into
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
  status: **已鸿蒙化** (mirror) / **未分析** / one of 5 未鸿蒙化 classes — **无需适配**
  (pure script), **仅需重新编译** (C/C++, no platform API), **全部可适配** (needs work but all
  used functionality portable), **部分可适配** (some APIs unportable — listed in `unadaptable_apis`),
  **无法适配** (core/specific hardware). `/api/dep-topology?name=`
  builds the DAG via `buildDepTopology` (runtime/optional + non-local deps, `resolveDepLib`
  for alias matching) and sets each node's class from `harmony_adaptation.porting_class`
  (closed axis the agent emits) or `derivePortingClass()` — a serve-time derivation from the
  existing feasibility/difficulty/path/blockers/unadaptable_apis, so **存量 reports are classified
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
- **导出 Excel (`/api/export`):** dashboard 「导出 Excel」按钮 → server spawns
  `scripts/export_xlsx.py` (Python + **openpyxl**) which flattens every library's
  latest `report.json` into one multi-sheet summary workbook (汇总 + 依赖/系统平台API/
  动态加载库/鸿蒙阻碍点/不支持API清单/语言分布/… detail sheets, one row per nested item), streamed back
  as a download. `?names=a,b` exports only selected libs. The script is standalone
  (CI/offline) too; openpyxl is the **only** third-party dep (web/ stays zero-dep).

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
- The `languages` / `code_metrics` / `tests` report blocks come verbatim from
  `metrics.py`; don't recompute them by hand. Everything else is model-reasoned.
- To extend: test idioms → `code-metrics/scripts/tests.py`; classification rules
  → `common.py`; analysis method for an interpretive dimension → that skill's
  `SKILL.md`; output shape → `references/report_schema.json` + the agent's
  assembly step.
