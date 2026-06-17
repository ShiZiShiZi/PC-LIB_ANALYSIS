---
name: function-summary
description: Summarize and classify what a third-party library does, by reading its source — README/docs, public API surface, module layout, and key implementation files. Produces a prose summary plus capability categories with evidence. Use for dimension 1 of PC library analysis. This is model reasoning, not a script.
---

# Function summary & classification (model-driven)

Decide what the library *is for* and break its capabilities into categories. This
is judgment work — read the source, don't pattern-match keywords.

## Evidence to gather (in priority order)
1. **README / docs** — `README*`, `docs/`, project website links, the package
   description in `package.json` / `pyproject.toml` / `pom.xml`. This is the
   authors' own framing; weight it heavily but verify against code.
2. **Public API surface** — exported symbols: Python `__all__` and top-level
   `def`/`class` in package `__init__.py`; C/C++ public headers (`include/`);
   Java public classes; JS package `main`/`exports`. The public API reveals the
   intended capabilities better than internal files.
3. **Module / directory layout** — top-level dirs often map to feature areas.
4. **A few key implementation files** — open the largest or most central
   production files to confirm what the API actually does.

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
  "target_users": "Python application developers"
}
```
Also set `library.one_liner` (<=120 chars).

## Rules
- Ground every claim in something you actually read. Never invent features.
- If docs and code disagree, trust the code and note it.
- If the library is large, sample breadth over depth — cover all top-level areas
  rather than fully reading one.
