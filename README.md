# pc-lib-analysis

An **agent + skill harness** for analyzing a PC third-party library from its git
source. The core deliverable is the **`pc-lib-analyzer` agent**: give it a git URL
(or local checkout) of a Python / C-C++ / Java / JS-TS library and it returns a
single `report.json`.

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
```

## Usage

### As an agent (the intended path)
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
