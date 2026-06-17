"""Shared helpers: cloc runner, file classification, repo walking.

The whole pipeline runs cloc exactly once (``--by-file --json``) and shares the
per-file result with every analyzer, so language breakdown, line counts and the
production/test/example split all come from one source of truth.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Iterable

# Directories that are never part of the library's own source.
EXCLUDE_DIRS = [
    ".git", "node_modules", "vendor", "third_party", "thirdparty", "3rdparty",
    "dist", "build", "out", "target", "bin", "obj", ".venv", "venv", "env",
    ".tox", ".mypy_cache", ".pytest_cache", "__pycache__", ".idea", ".vscode",
    "cmake-build-debug", "cmake-build-release", "Pods", "Carthage",
]

# Path *components* (case-insensitive) that mark test / example code.
TEST_DIR_TOKENS = {
    "test", "tests", "testing", "__tests__", "spec", "specs",
    "unittest", "unittests", "testcase", "testcases", "gtest", "googletest",
}
EXAMPLE_DIR_TOKENS = {
    "example", "examples", "sample", "samples", "demo", "demos",
    "tutorial", "tutorials", "playground",
}

# Filename patterns (lower-cased) for test files outside a test dir.
TEST_FILE_SUFFIXES = ("_test", "_tests", ".test", ".spec", "_spec")
TEST_FILE_PREFIXES = ("test_", "test-")


@dataclass
class FileStat:
    path: str          # path relative to repo root, forward slashes
    language: str
    code: int
    comment: int
    blank: int
    category: str      # "production" | "test" | "example"


@dataclass
class ClocResult:
    files: list[FileStat] = field(default_factory=list)
    tool: str = "cloc"
    warnings: list[str] = field(default_factory=list)

    def by_category(self, category: str) -> list[FileStat]:
        return [f for f in self.files if f.category == category]


def classify_path(rel_path: str) -> str:
    """Return 'test', 'example' or 'production' for a repo-relative path."""
    parts = [p.lower() for p in rel_path.replace("\\", "/").split("/")]
    dirs, name = parts[:-1], parts[-1]
    if any(p in TEST_DIR_TOKENS for p in dirs):
        return "test"
    if any(p in EXAMPLE_DIR_TOKENS for p in dirs):
        return "example"
    stem = name.rsplit(".", 1)[0]
    if stem.startswith(TEST_FILE_PREFIXES) or stem.endswith(TEST_FILE_SUFFIXES):
        return "test"
    # JS/TS style: foo.test.ts / foo.spec.js
    if ".test." in name or ".spec." in name:
        return "test"
    # Java: FooTest.java / FooTests.java / FooIT.java
    if name.endswith(".java") and (stem.endswith("test") or stem.endswith("tests") or stem.endswith("it")):
        return "test"
    return "production"


def run_cloc(repo: str) -> ClocResult:
    res = ClocResult()
    cloc = shutil.which("cloc")
    if cloc:
        try:
            return _run_cloc_binary(cloc, repo)
        except Exception as exc:  # noqa: BLE001
            res.warnings.append(f"cloc failed ({exc}); falling back to tokei/builtin")
    tokei = shutil.which("tokei")
    if tokei:
        try:
            r = _run_tokei_binary(tokei, repo)
            r.warnings = res.warnings
            return r
        except Exception as exc:  # noqa: BLE001
            res.warnings.append(f"tokei failed ({exc}); falling back to builtin counter")
    r = _run_builtin(repo)
    r.warnings = res.warnings + r.warnings
    return r


def _run_cloc_binary(cloc: str, repo: str) -> ClocResult:
    cmd = [
        cloc, "--by-file", "--json", "--quiet",
        f"--exclude-dir={','.join(EXCLUDE_DIRS)}",
        repo,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if not out.stdout.strip():
        raise RuntimeError(out.stderr.strip() or "empty output")
    data = json.loads(out.stdout)
    res = ClocResult(tool="cloc")
    for path, info in data.items():
        if path in ("header", "SUM"):
            continue
        rel = os.path.relpath(path, repo).replace("\\", "/")
        res.files.append(FileStat(
            path=rel,
            language=info.get("language", "unknown"),
            code=int(info.get("code", 0)),
            comment=int(info.get("comment", 0)),
            blank=int(info.get("blank", 0)),
            category=classify_path(rel),
        ))
    return res


def _run_tokei_binary(tokei: str, repo: str) -> ClocResult:
    # tokei --files --output json gives per-file stats under each language.
    cmd = [tokei, "--files", "--output", "json", repo]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    data = json.loads(out.stdout)
    res = ClocResult(tool="tokei")
    for lang, info in data.items():
        if lang == "Total":
            continue
        for rep in info.get("reports", []):
            path = rep.get("name", "")
            rel = os.path.relpath(path, repo).replace("\\", "/")
            st = rep.get("stats", {})
            res.files.append(FileStat(
                path=rel, language=lang,
                code=int(st.get("code", 0)),
                comment=int(st.get("comments", 0)),
                blank=int(st.get("blanks", 0)),
                category=classify_path(rel),
            ))
    return res


# Minimal extension -> language map for the zero-dependency fallback only.
_EXT_LANG = {
    ".py": "Python", ".pyx": "Cython", ".c": "C", ".h": "C/C++ Header",
    ".cc": "C++", ".cpp": "C++", ".cxx": "C++", ".hpp": "C/C++ Header",
    ".hh": "C/C++ Header", ".java": "Java", ".js": "JavaScript",
    ".jsx": "JSX", ".ts": "TypeScript", ".tsx": "TSX", ".mjs": "JavaScript",
    ".go": "Go", ".rs": "Rust", ".cs": "C#", ".rb": "Ruby", ".kt": "Kotlin",
}


def _run_builtin(repo: str) -> ClocResult:
    res = ClocResult(tool="builtin")
    res.warnings.append("Neither cloc nor tokei found; using crude builtin line counter.")
    for stat in iter_source_files(repo):
        ext = os.path.splitext(stat)[1].lower()
        lang = _EXT_LANG.get(ext)
        if not lang:
            continue
        rel = os.path.relpath(stat, repo).replace("\\", "/")
        code = blank = 0
        try:
            with open(stat, "r", errors="ignore") as fh:
                for line in fh:
                    if line.strip():
                        code += 1
                    else:
                        blank += 1
        except OSError:
            continue
        res.files.append(FileStat(rel, lang, code, 0, blank, classify_path(rel)))
    return res


def iter_source_files(repo: str) -> Iterable[str]:
    excl = set(EXCLUDE_DIRS)
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in excl]
        for f in files:
            yield os.path.join(root, f)


def read_text(path: str, limit: int | None = None) -> str:
    try:
        with open(path, "r", errors="ignore") as fh:
            return fh.read(limit) if limit else fh.read()
    except OSError:
        return ""


def find_files(repo: str, names: Iterable[str] | None = None,
               exts: Iterable[str] | None = None,
               categories: set[str] | None = None) -> list[FileStat | str]:
    """Walk repo returning absolute paths matching basename or extension."""
    names_l = {n.lower() for n in names} if names else None
    exts_l = {e.lower() for e in exts} if exts else None
    found: list[str] = []
    for p in iter_source_files(repo):
        base = os.path.basename(p).lower()
        ext = os.path.splitext(base)[1]
        if names_l and base in names_l:
            found.append(p)
        elif exts_l and ext in exts_l:
            found.append(p)
    return found
