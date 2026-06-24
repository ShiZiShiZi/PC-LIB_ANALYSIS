# pc-lib-analysis

An **agent + skill harness** for analyzing a PC open-source software project — a
third-party **library OR an application** — from its git source. The core deliverable
is the **`pc-lib-analyzer` agent**: give it a git URL (or local checkout) of a
Python / C-C++ / Java / JS-TS library or application and it returns a single
`report.json`.

## Design principle

The analysis is **model-driven**. Only the mechanical, must-be-reproducible part —
counting lines and classifying files — is固化 (hard-coded) into a script. Every
interpretive dimension is reasoned by the model, guided by a skill prompt:

| # | Dimension | Owner |
|---|-----------|-------|
| 1 | Function summary + classification | **model** — skill `function-summary` |
| 2 | Language identification | **script** — `code-metrics` (cloc) |
| 3 | Code volume (prod / test / example, by language) | **script** — `code-metrics` (cloc) |
| 4 | Test-file / test-case counts | **script** — `code-metrics`, model refines |
| 5 | Open-source license | **model** — skill `license-detect` |
| 6 | Dependencies | **model** — skill `dependency-analysis` |
| 7 | Low-level / platform API (Win32, POSIX, STL, FFI…) | **model** — skill `native-api-analysis` |

## Layout

```
.claude/
  agents/
    pc-lib-analyzer.md          # the agent: orchestrates everything -> report.json
  skills/
    code-metrics/               # deterministic (cloc) — the only script-backed skill
      SKILL.md
      scripts/{metrics.py, common.py, tests.py}
    function-summary/SKILL.md    # model-driven prompt skills
    license-detect/SKILL.md
    dependency-analysis/SKILL.md
    native-api-analysis/SKILL.md
references/
  report_schema.json            # output contract (the agent conforms to this)
web/
  server.js                     # zero-dep Node control panel (HTTP + SSE)
  public/{index.html,app.js,styles.css}
repos/                          # cloned libraries (gitignored)
runs/   <lib>/<timestamp>/      # per-run report.json + run.log.jsonl + meta.json (gitignored)
```

## Usage

### Web control panel (the intended workflow)
Configure, clone, analyze and view results from a page; opencode's live I/O is
streamed to the browser **and** persisted per run.

```bash
npm start          # or: node web/server.js   ->  http://localhost:8765
```

In the page:
1. **Repository** — paste a Git URL → *Clone*. The repo lands in `repos/<name>`
   (gitignored) and git progress streams live.
2. **Analysis** — pick a library, choose a `model` (dropdown is populated from
   `opencode models`), optionally tweak the opencode command / prompt template,
   → *Analyze*. The server runs (default):
   ```
   opencode run -m <model> --print-logs "<prompt pointing at .claude/agents/pc-lib-analyzer.md, write report to runs/<name>/<ts>/report.json>"
   ```
   Every stdout/stderr line streams to the **Live log** and is appended to
   `runs/<name>/<ts>/run.log.jsonl` (with timestamps); the input command/prompt
   is recorded too.
3. **Report** — when the agent finishes, `report.json` is rendered (summary,
   language bars, code metrics, tests, license, deps, native API) with raw-JSON
   and download. **History** lists past runs; click one to replay its log + report.

Run the panel from the project root so opencode (cwd = root) can read `.claude/`.
Override the port with `PORT=9000 npm start`.

### As an agent (headless / scripted)
Invoke the agent on a library; it does all 7 dimensions and writes `report.json`.
From an external script or UI you can drive it headless, e.g.:

```bash
claude --agent pc-lib-analyzer -p "Analyze https://github.com/owner/lib.git"
# (or the equivalent opencode invocation, run from this project directory)
```

Run it from this project root so the agent can read its skills and the schema.

### Just the deterministic metrics
```bash
python3 .claude/skills/code-metrics/scripts/metrics.py --repo <checkout> --out metrics.json
```

## Requirements
- `git`, `python3` (3.11+ for native TOML), and `cloc` (preferred) or `tokei` on
  PATH. Without a counter, a builtin fallback runs and records a warning.

## Extending
- Counting / classification rules → `.claude/skills/code-metrics/scripts/`
- Analysis method for an interpretive dimension → edit that skill's `SKILL.md`
- Output shape → `references/report_schema.json` (and the agent's assembly step)
- New language: add test idioms in `scripts/tests.py`; the model skills already
  generalize across ecosystems via their prompts.
