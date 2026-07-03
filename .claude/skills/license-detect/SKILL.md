---
name: license-detect
description: Determine a third-party library's open-source license by reading and interpreting its LICENSE files, source-file headers, and manifest declarations — including uncommon licenses, dual/multi licensing, and SPDX expressions that a fixed signature table can't enumerate. Use for dimension 5 of PC library analysis. Model reasoning, not a script.
---

# License detection (model-driven)

A fixed regex table can't cover every license, exception, or dual-licensing
arrangement — so reason about it. Read the actual license text and decide.

## 主旨与原则
**输出契约（下方 Output）是唯一硬约束。** 下面的清单与取值是**推荐起点，不是封闭清单** ——
遇到不匹配的场景（罕见许可、自定义条款、SPDX 表里没有的组合），尽力判断，必要时给出最贴近的
SPDX 表达式或 `NOASSERTION`，并把疑难写进 `meta.observations`。方法仅是参考思路，可按仓库调整。

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
- **归类协议性质到闭轴 `category`（5 选 1，见下表）** —— 与 spdx 判定并行给出。

### `category` — 协议性质（严格闭轴，只能映射不能新增）
把协议映射到**恰好一个**下列值（英文 key）：

| category | 含义 | 常见许可 |
|---|---|---|
| `strong_copyleft` | 强传染（整体传染） | GPL-2.0/3.0（含 -only/-or-later）、AGPL-3.0、EUPL、OSL |
| `weak_copyleft` | 弱传染（文件/库级） | LGPL-2.1/3.0、MPL-1.1/2.0、EPL-1.0/2.0、CDDL、CPL、Ms-RL |
| `permissive` | 友好（宽松） | MIT、BSD-2/3/4-Clause、Apache-2.0、ISC、Zlib、BSL-1.0、Unlicense、0BSD、CC0、Python-2.0 |
| `commercial` | 商业/源码可见非自由 | 专有/商业 EULA、保留所有权利、SSPL、BUSL-1.1、Elastic-2.0、Commons-Clause |
| `undeclared` | 未声明/无法判定 | 无 LICENSE、`null`、`NOASSERTION`、证据不足 |

- **双许可/多选一**（如 `GPL-2.0 OR MIT`）：按对使用者**最宽松**的那支归类（此例 → `permissive`），并在 `notes` 说明可选另一支。
- **WITH 例外**（如 `GPL-2.0 WITH Classpath-exception`）：仍按主许可家族归类（strong/weak），例外写 `notes`。

## Output (fills report `license`)
```json
{
  "spdx": "Apache-2.0",
  "name": "Apache License 2.0",
  "confidence": "high",
  "category": "permissive",
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
- **`category` 是严格闭轴的例外**：与本仓其它维度的"开放词表可扩"元规则**不同**，`category`
  **只能**是上表 5 个 key 之一——**禁止 coin 新值、禁止写入 `meta.observations`**。拿不准时选最贴近的一类
  （证据实在不足才用 `undeclared`）。`spdx`/`notes` 仍照常记录疑难。

## 自我发现（反哺）
遇到 SPDX 表难以覆盖的许可/例外/组合，或证据冲突的歧义，追加到顶层 `meta.observations`：
`{dimension:"license", field, kind, value, rationale}`，供面板「模型观察」页人工反哺 skill。
