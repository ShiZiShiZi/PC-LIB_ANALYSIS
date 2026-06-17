"""Dimension 4: test-case counting, per language.

Counts test files (from the cloc classification) and individual test cases by
matching framework idioms inside each test file.
"""
from __future__ import annotations

import os
import re
from collections import defaultdict

from common import ClocResult, read_text

# language -> (compiled regexes, framework hints)
_PATTERNS = {
    "Python": [
        (re.compile(r"^\s*def\s+test\w*\s*\(", re.M), "pytest/unittest"),
    ],
    "C++": [
        (re.compile(r"\bTEST(_F|_P)?\s*\(", re.M), "googletest"),
        (re.compile(r"\bTEST_CASE\s*\(", re.M), "Catch2/doctest"),
        (re.compile(r"\bBOOST_AUTO_TEST_CASE\s*\(", re.M), "Boost.Test"),
        (re.compile(r"\bSCENARIO\s*\(", re.M), "Catch2 BDD"),
    ],
    "C": [
        (re.compile(r"\bTEST(_F|_P)?\s*\(", re.M), "googletest"),
        (re.compile(r"\bTEST_CASE\s*\(", re.M), "Catch2/doctest"),
    ],
    "Java": [
        (re.compile(r"@Test\b", re.M), "JUnit/TestNG"),
    ],
    "JavaScript": [
        (re.compile(r"\b(it|test)\s*\(", re.M), "jest/mocha"),
    ],
    "TypeScript": [
        (re.compile(r"\b(it|test)\s*\(", re.M), "jest/mocha"),
    ],
}
# C/C++ headers share the C++ pattern set.
_PATTERNS["C/C++ Header"] = _PATTERNS["C++"]
_PATTERNS["JSX"] = _PATTERNS["JavaScript"]
_PATTERNS["TSX"] = _PATTERNS["TypeScript"]


def analyze_tests(cloc: ClocResult, repo: str) -> dict:
    test_files = cloc.by_category("test")
    by_lang: dict[str, dict] = defaultdict(lambda: {"files": 0, "cases": 0})
    frameworks: set[str] = set()
    total_cases = 0

    for f in test_files:
        pats = _PATTERNS.get(f.language)
        by_lang[f.language]["files"] += 1
        if not pats:
            continue
        text = read_text(os.path.join(repo, f.path))
        if not text:
            continue
        file_cases = 0
        for rx, fw in pats:
            hits = len(rx.findall(text))
            if hits:
                file_cases += hits
                frameworks.add(fw)
        by_lang[f.language]["cases"] += file_cases
        total_cases += file_cases

    return {
        "test_files": len(test_files),
        "test_cases": total_cases,
        "frameworks": sorted(frameworks),
        "by_language": {k: v for k, v in sorted(
            by_lang.items(), key=lambda kv: kv[1]["cases"], reverse=True)},
        "note": "Counts are regex-based idiom matches; treat as close estimates.",
    }
