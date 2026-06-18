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
| 7 | Low-level / platform API (Win32/POSIX/STL/FFI, dynamic-loaded libs) | model — `native-api-analysis` skill |

Dependencies (dim 6) also carry `acquisition` — how the build obtains each one
(system/vendored/fetchcontent/download_build/submodule/package_manager/prebuilt_binary)
— useful for understanding how C libs/.so are pulled in.

## Layout

```
.claude/
  agents/pc-lib-analyzer.md      # orchestrator agent — clones, runs metrics, reasons, writes report.json
  skills/
    code-metrics/                # ONLY script-backed skill (deterministic)
      scripts/{metrics.py, common.py, tests.py}
    function-summary/  license-detect/  dependency-analysis/  native-api-analysis/  # model-driven prompt skills
references/report_schema.json    # output contract — the report MUST conform
web/
  server.js                      # zero-dep Node control panel (http + SSE)
  public/{index.html, app.js, styles.css}   # two-level light-theme SPA
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
and `opencode` with a configured model.

## Web panel architecture

- **Level 1 (dashboard, `#/`):** library cards with status/metrics, batch select,
  batch + concurrent clone and analyze, system settings.
- **Level 2 (detail, `#/lib/<name>`):** run history, live log (SSE, parses
  opencode `--format json` events), rendered report.
- **Backend (`web/server.js`):** REST + SSE. Analyses go through a concurrency
  queue capped by `settings.maxConcurrent`; clones run concurrently. Endpoints:
  `/api/libraries`, `/api/library`, `/api/jobs`, `/api/clone` (batch),
  `/api/analyze` (batch), `/api/stream` (SSE), `/api/report`, `/api/runlog`,
  `/api/settings`, `/api/models`, `/api/testmodel`.

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
- The `languages` / `code_metrics` / `tests` report blocks come verbatim from
  `metrics.py`; don't recompute them by hand. Everything else is model-reasoned.
- To extend: test idioms → `code-metrics/scripts/tests.py`; classification rules
  → `common.py`; analysis method for an interpretive dimension → that skill's
  `SKILL.md`; output shape → `references/report_schema.json` + the agent's
  assembly step.
