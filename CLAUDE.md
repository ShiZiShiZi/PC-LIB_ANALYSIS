# CLAUDE.md

Guidance for Claude Code when working in this repo.

## What this is

An **agent + skill harness** that analyzes a PC third-party library from its git
source and emits one JSON report, plus a **web control panel** to drive it.
Input: a git URL (or local checkout) of a Python / C-C++ / Java / JS-TS library.
Output: `report.json` covering 7 dimensions.

## Core principle: model-driven, scripts only for counting

Only the mechanical, must-be-reproducible measurement (line counts, language
breakdown, test tallies) is hard-coded in a script. Every interpretive dimension
is reasoned by the model, guided by a skill prompt. Don't "fix" an interpretive
dimension by adding a parser — improve its skill prompt instead.

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
`effort_estimate`/`blockers[].severity`; open vocab is `recommended_path`/
`blockers[].category`/`harmony_status`.

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
  skills/
    code-metrics/                # ONLY script-backed skill (deterministic)
      scripts/{metrics.py, common.py, tests.py}
    function-summary/  license-detect/  dependency-analysis/  native-api-analysis/  # model-driven prompt skills
    runtime-environment/  harmony-adaptation/                                       # (dim 8 + dim 9 synthesis)
references/report_schema.json    # output contract — the report MUST conform
web/
  server.js                      # zero-dep Node control panel (http + SSE)
  public/{index.html, app.js, styles.css}   # two-level light-theme SPA
scripts/export_xlsx.py           # summary .xlsx export (openpyxl); panel /api/export spawns it
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
  deps of the deps" loop. A dep leaves this list once analyzed.
- **模型观察 (`#/observations`):** see the two-tier vocabulary section above.
- **Backend (`web/server.js`):** REST + SSE. Analyses go through a concurrency
  queue capped by `settings.maxConcurrent`; clones run concurrently. Endpoints:
  `/api/libraries`, `/api/library`, `/api/jobs`, `/api/clone` (batch),
  `/api/analyze` (batch), `/api/stream` (SSE), `/api/report`, `/api/runlog`,
  `/api/depgraph`, `/api/observations`, `/api/pending-deps`, `/api/settings`,
  `/api/models`, `/api/testmodel`, `/api/export` (xlsx).
- **导出 Excel (`/api/export`):** dashboard 「导出 Excel」按钮 → server spawns
  `scripts/export_xlsx.py` (Python + **openpyxl**) which flattens every library's
  latest `report.json` into one multi-sheet summary workbook (汇总 + 依赖/系统平台API/
  动态加载库/鸿蒙阻碍点/语言分布/… detail sheets, one row per nested item), streamed back
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
