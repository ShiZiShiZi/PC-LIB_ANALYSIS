#!/usr/bin/env python3
"""Deterministic code metrics for a source tree (cloc-backed).

This is the ONLY part of the analysis that is hard-coded into a script, because
line counting and language breakdown are mechanical and must be reproducible.
Everything interpretive (function summary, license, dependencies, native API)
is left to the agent / skills.

Emits a JSON fragment with three keys ready to drop into the final report:
``languages`` (dim 2), ``code_metrics`` (dim 3), ``tests`` (dim 4).

Usage:
    python3 metrics.py --repo /path/to/checkout [--out metrics.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import ClocResult, FileStat, run_cloc  # noqa: E402
from tests import analyze_tests  # noqa: E402

# Data/markup languages that should not be picked as the implementation language.
_NON_CODE = {
    "JSON", "YAML", "Markdown", "Text", "XML", "HTML", "CSS", "TOML", "INI",
    "SVG", "make", "CMake", "Dockerfile", "Bourne Shell", "reStructuredText",
}


def _agg(files: list[FileStat]) -> dict:
    code = sum(f.code for f in files)
    comment = sum(f.comment for f in files)
    blank = sum(f.blank for f in files)
    return {"files": len(files), "code": code, "comment": comment,
            "blank": blank, "total_lines": code + comment + blank}


def _languages(cloc: ClocResult) -> dict:
    by_lang: dict[str, list[FileStat]] = defaultdict(list)
    for f in cloc.files:
        by_lang[f.language].append(f)
    total = sum(f.code for f in cloc.files) or 1

    def _cat(files: list[FileStat], cat: str) -> dict:
        sub = [f for f in files if f.category == cat]
        return {"files": len(sub), "code": sum(f.code for f in sub)}

    breakdown = [{
        "language": lang,
        "files": len(files),
        "code": sum(f.code for f in files),
        "pct": round(100.0 * sum(f.code for f in files) / total, 2),
        "production": _cat(files, "production"),
        "test": _cat(files, "test"),
        "example": _cat(files, "example"),
    } for lang, files in by_lang.items()]
    breakdown.sort(key=lambda x: x["code"], reverse=True)
    primary = next((b["language"] for b in breakdown
                    if b["language"] not in _NON_CODE), None)
    return {"primary": primary,
            "all": [b["language"] for b in breakdown[:8]],
            "breakdown": breakdown}


def _top_dirs(cloc: ClocResult, cap: int = 40) -> tuple[list[dict], dict]:
    """Per top-level directory: code lines split by category, so the model can see
    which dirs are test/example (token-classified) and recognise demo-collection
    layouts. `category` is the MAJORITY category of the dir (production wins ties),
    and `by_category` keeps the split so mixed dirs (e.g. a prod tree with nested
    tests) are visible. test_example_dirs lists the dirs whose majority is test or
    example — note token-based classification misses demo dirs named by feature
    (the model补判 those)."""
    dirs: dict[str, dict] = {}
    for f in cloc.files:
        norm = f.path.replace("\\", "/")
        top = norm.split("/", 1)[0] if "/" in norm else "."
        d = dirs.setdefault(top, {"production": 0, "test": 0, "example": 0})
        d[f.category] = d.get(f.category, 0) + f.code
    rows = []
    for name, d in dirs.items():
        code = d["production"] + d["test"] + d["example"]
        # majority category; production wins ties so a mixed dir isn't flagged test/example
        cat = max(("production", "example", "test"), key=lambda c: d[c])
        if d[cat] == d["production"]:
            cat = "production"
        rows.append({"dir": name, "code": code, "category": cat,
                     "by_category": {k: v for k, v in d.items() if v}})
    rows.sort(key=lambda r: r["code"], reverse=True)
    te = {"test": [r["dir"] for r in rows if r["category"] == "test"],
          "example": [r["dir"] for r in rows if r["category"] == "example"]}
    return rows[:cap], te


def _code_metrics(cloc: ClocResult) -> dict:
    cats = {c: cloc.by_category(c) for c in ("production", "test", "example")}
    by_lang_prod: dict[str, dict] = {}
    for f in cats["production"]:
        d = by_lang_prod.setdefault(f.language, {"files": 0, "code": 0})
        d["files"] += 1
        d["code"] += f.code
    top_dirs, test_example_dirs = _top_dirs(cloc)
    return {
        "tool": cloc.tool,
        "total": _agg(cloc.files),
        "production": _agg(cats["production"]),
        "test": _agg(cats["test"]),
        "example": _agg(cats["example"]),
        "production_by_language": dict(sorted(
            by_lang_prod.items(), key=lambda kv: kv[1]["code"], reverse=True)),
        "top_dirs": top_dirs,
        "test_example_dirs": test_example_dirs,
    }


def compute(repo: str) -> dict:
    cloc = run_cloc(repo)
    fragment = {
        "languages": _languages(cloc),
        "code_metrics": _code_metrics(cloc),
        "tests": analyze_tests(cloc, repo),
    }
    if cloc.warnings:
        fragment["_warnings"] = cloc.warnings
    return fragment


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    if not os.path.isdir(repo):
        print(f"error: not a directory: {repo}", file=sys.stderr)
        return 2
    fragment = compute(repo)
    text = json.dumps(fragment, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
        m = fragment["code_metrics"]
        print(f"Wrote {args.out}")
        print(f"  primary language : {fragment['languages']['primary']}")
        print(f"  production code   : {m['production']['code']} lines "
              f"(test {m['test']['code']}, example {m['example']['code']})")
        print(f"  test cases        : {fragment['tests']['test_cases']}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
