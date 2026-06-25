---
name: code-metrics
description: Produce deterministic, reproducible code metrics for a source checkout — language breakdown, lines of code split into production vs test vs example, and test-file/test-case counts. This is the ONE hard-coded (cloc-backed) part of PC library/application analysis. Use when you need objective line/test numbers; do NOT use it for license, dependency, function, or API analysis (those are model-reasoned).
---

# Code metrics (deterministic)

Counting lines and classifying files is mechanical and must be reproducible, so
it is固化 into a script rather than reasoned by the model. Everything else in the
analysis is model-driven.

## Run it

```bash
python3 .claude/skills/code-metrics/scripts/metrics.py --repo <CHECKOUT> --out metrics.json
```

The `--out` path must be **inside the project** (e.g. the current run directory).
Do not write to `/tmp` or any external directory — under the headless opencode
runner external paths are auto-rejected, which aborts the analysis.

Outputs a JSON fragment with three keys, ready to drop into the final report:
- `languages` — dim 2: per-language file/code counts, `primary` implementation language.
- `code_metrics` — dim 3: `total` / `production` / `test` / `example` line aggregates (+ platform_adaptation / platform_branches signals).
- `tests` — dim 4: `test_files`, `test_cases`, detected `frameworks`, `by_language`.

Requires `cloc` (preferred) or `tokei` on PATH; falls back to a builtin counter
and records `_warnings` if neither is present.

## How it classifies (so you can sanity-check)
- **test**: path contains a dir like `test/tests/spec/__tests__/unittest`, or a
  filename like `test_*`, `*_test.*`, `*.spec.*`, `*Test.java`.
- **example**: dir like `example(s)/sample(s)/demo(s)/tutorial`.
- **excluded entirely**: `.git`, `node_modules`, `vendor`, `third_party`, build
  output dirs, virtualenvs, caches.
- **production**: everything else.

## When to override
The script is conservative and idiom-based. If the repo uses an unusual layout
(tests in `src/.../__tests__`, examples under `docs/`, a custom test macro),
note it and adjust the report's `tests.notes` — but keep the script's line
numbers as the source of truth for code volume.

## Extending
- Test-case idioms per language: `scripts/tests.py`
- Classification rules / excluded dirs: `scripts/common.py`
