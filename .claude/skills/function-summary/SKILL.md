---
name: function-summary
description: Summarize and classify what a third-party library does, by reading its source — README/docs, public API surface, module layout, and key implementation files. Produces a prose summary plus capability categories with evidence. Use for dimension 1 of PC library analysis. This is model reasoning, not a script.
---

# Function summary & classification (model-driven)

Decide what the library *is for* and break its capabilities into categories. This
is judgment work — read the source, don't pattern-match keywords.

## 主旨与原则
**输出契约（下方 Output）是唯一硬约束。** 下面的清单与取值是**推荐起点，不是封闭清单** ——
遇到不匹配的场景，尽力归类，必要时**自造一个简洁的小写值**，并写进 `meta.observations`。
方法仅是参考思路，可按仓库实际调整；把推理空间留给自己，只要产出符合契约即可。

## Evidence to gather (in priority order)
1. **Manifest / package metadata** — the strongest signal for the library's
   ecosystem. Look for:
   - `pyproject.toml`, `setup.py`, `setup.cfg` → Python
   - `pom.xml`, `build.gradle*` → Java
   - `package.json` → Node.js
   - `Cargo.toml` → Rust
   - `go.mod` → Go
   - `*.csproj`, `*.fsproj` → .NET
2. **README / docs** — `README*`, `docs/`, project website links, the package
   description in `package.json` / `pyproject.toml` / `pom.xml`. This is the
   authors' own framing; weight it heavily but verify against code.
3. **Public API surface** — exported symbols: Python `__all__` and top-level
   `def`/`class` in package `__init__.py`; C/C++ public headers (`include/`);
   Java public classes; JS package `main`/`exports`. The public API reveals the
   intended capabilities better than internal files. When codegraph is available
   (the agent will tell you), use `codegraph context "<area>" -p repos/<name>` and
   `codegraph files -p repos/<name>` to map the symbol/module surface fast; fall
   back to grep/Read when it isn't.
4. **Module / directory layout** — top-level dirs often map to feature areas.
5. **A few key implementation files** — open the largest or most central
   production files to confirm what the API actually does.

## Determine the ecosystem
Before classifying capabilities, decide which ecosystem the library belongs to.
Use the manifest signal first; if ambiguous, fall back to the primary language
from the code-metrics output. Allowed values are exactly:

| Value    | Meaning |
|----------|---------|
| `python` | Python package (pip / poetry / setuptools) |
| `java`   | Java library / JAR (Maven / Gradle) |
| `nodejs` | Node.js / JavaScript package (npm / yarn / pnpm) |
| `cpp`    | C or C++ library |
| `rust`   | Rust crate |
| `go`     | Go module |
| `dotnet` | .NET library (C# / F#) |
| `other`  | Unclear or none of the above |

Rules:
- If multiple manifests exist, prefer the one that declares the primary package.
- If the repo is a polyglot binding wrapper (e.g. a Python package wrapping a C
  extension), classify by the package's distribution language/ecosystem.
- If no manifest is present and the primary language is mixed or unclear, use
  `other`.

## How to classify
- Group capabilities into **3–7 categories**, each a coherent feature area
  (e.g. "HTTP client", "Connection pooling", "TLS/SSL", "Async I/O").
- Each category needs concrete **evidence**: the file(s), module(s) or symbol(s)
  that implement it. No evidence → don't claim it.
- Identify the **domain** (networking / graphics / ML / crypto / data / GUI / …)
  and the **target users** (app developers? other libraries? CLI users?).

## Output (fills report `function_summary`)
```json
{
  "summary": "2-4 sentences: what it does and for whom.",
  "categories": [
    {"name": "...", "description": "...", "evidence": ["src/http/client.py", "Session"]}
  ],
  "domain": "networking",
  "target_users": "Python application developers",
  "ecosystem": "python"
}
```
Also set `library.one_liner` (<=120 chars), `library.ecosystem` (the **core**
ecosystem, one of the allowed values above), and `library.package_name` — the
**distribution/package name** declared in the manifest (`[project].name` / `name`
in `package.json` / Maven `artifactId` / `Cargo.toml` `name`), which may differ
from the repo dir name. Set it to `null` if there is no manifest or it is uncertain.

Set `library.bindings` — the languages the library exposes **bindings/wrappers**
for beyond its core ecosystem (so a polyglot library isn't shown as single-language).
E.g. a C++ core with Boost.Python + SWIG Java/C# bindings → `["python","java","dotnet"]`;
a JS package with a WASM/native core → list accordingly. Look for binding dirs/tools
(`*.pyx`/`pybind11`/Boost.Python, `*.i` SWIG, JNI `*Wrappers`, N-API, emscripten/CFFI).
Use `[]` if it only targets its core ecosystem.

## Language
- Write `summary`, every category `name`/`description`, `domain`, `target_users`,
  and `library.one_liner` in **简体中文 (Simplified Chinese)**. Keep proper nouns
  (library/API/dependency names, language names) in their original form.

## Rules
- Ground every claim in something you actually read. Never invent features.
- If docs and code disagree, trust the code and note it.
- If the library is large, sample breadth over depth — cover all top-level areas
  rather than fully reading one.

## 自我发现（反哺）
若发现「推荐取值覆盖不到的新场景(new_value) / 契约或分类的盲区(gap) / 难归类的歧义(ambiguity)」，
追加到顶层 `meta.observations`：`{dimension:"function_summary", field, kind, value, rationale}`，
供面板「模型观察」页人工反哺 skill。
