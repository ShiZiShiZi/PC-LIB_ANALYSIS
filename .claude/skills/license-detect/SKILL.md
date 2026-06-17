---
name: license-detect
description: Determine a third-party library's open-source license by reading and interpreting its LICENSE files, source-file headers, and manifest declarations — including uncommon licenses, dual/multi licensing, and SPDX expressions that a fixed signature table can't enumerate. Use for dimension 5 of PC library analysis. Model reasoning, not a script.
---

# License detection (model-driven)

A fixed regex table can't cover every license, exception, or dual-licensing
arrangement — so reason about it. Read the actual license text and decide.

## Where to look (gather all, then reconcile)
1. **License files** — `LICENSE*`, `COPYING*`, `COPYRIGHT*`, `NOTICE*`,
   `UNLICENSE`, `LICENSES/` dir (REUSE spec). Read the full text, not just the
   filename.
2. **Manifest declarations** — `license`/`license-expression` in `package.json`,
   `pyproject.toml`, `setup.cfg`, `<licenses>` in `pom.xml`, gradle.
3. **Source-file headers** — SPDX tags (`SPDX-License-Identifier: ...`) and
   copyright/permission banners at the top of representative source files. These
   catch cases where the repo has no top-level LICENSE, or where vendored code
   differs from the project license.
4. **README** "License" section.

## How to decide
- Map the text to the correct **SPDX identifier** (e.g. `MIT`, `Apache-2.0`,
  `BSD-3-Clause`, `GPL-3.0-only`, `LGPL-2.1-or-later`, `MPL-2.0`, `ISC`,
  `Unlicense`, `BSL-1.0`). Use a full SPDX expression for combinations
  (`Apache-2.0 OR MIT`, `GPL-2.0-only WITH Classpath-exception-2.0`).
- Detect **dual / multi licensing** (set `is_dual_licensed`).
- Flag **copyleft** (GPL/AGPL/LGPL), **weak copyleft** (MPL/LGPL), and any
  **exceptions** in `notes`, since these drive compliance obligations.
- If there is no license, an ambiguous one, or conflicting signals, set
  `spdx: "NOASSERTION"` (or `null`) and explain in `notes`.

## Output (fills report `license`)
```json
{
  "spdx": "Apache-2.0",
  "name": "Apache License 2.0",
  "confidence": "high",
  "is_dual_licensed": false,
  "license_files": ["LICENSE"],
  "evidence": "LICENSE matches Apache-2.0 text; SPDX tag in src/*.cpp confirms.",
  "notes": "Permissive; requires NOTICE preservation."
}
```

## Rules
- Base `confidence` on evidence strength: `high` = unambiguous full license text;
  `medium` = manifest field or header tag only; `low` = inference.
- Note when vendored/third-party subtrees carry a different license than the project.
