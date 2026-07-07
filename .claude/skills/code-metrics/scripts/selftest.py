#!/usr/bin/env python3
"""Unit self-test for the mechanical platform counters (no external deps).

Run: python3 .claude/skills/code-metrics/scripts/selftest.py
Verifies that comments / string literals do NOT inflate platform_branches, that real
runtime branches DO count, and that platform_adaptation skips blank/comment lines.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics  # noqa: E402
from common import FileStat, ClocResult  # noqa: E402


def _cloc(files):
    """files: list of (relpath, language, category, text) — write to a temp repo."""
    d = tempfile.mkdtemp(prefix="pcmetrics-selftest-")
    stats = []
    for rel, lang, cat, text in files:
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        stats.append(FileStat(path=rel, language=lang, code=text.count("\n") + 1,
                              comment=0, blank=0, category=cat))
    return d, ClocResult(files=stats, tool="selftest")


def check(name, cond):
    print(("  ok " if cond else "  FAIL ") + name)
    if not cond:
        check.failed += 1
check.failed = 0


def test_branches_skip_comments_and_strings():
    py = (
        "import sys\n"
        "if sys.platform == 'win32':\n"          # real → count (1), platform=windows
        "    pass\n"
        "# if sys.platform == 'darwin':\n"        # commented → NOT counted
        "msg = 'sys.platform is reported here'\n"  # inside string → NOT counted
        'doc = """\n'
        "sys.platform appears in a triple-quoted string\n"  # triple string → NOT counted
        '"""\n'
        "elif sys.platform == 'linux':\n"         # real → count (2), platform=linux
        "    pass\n"
    )
    d, cloc = _cloc([("pkg/mod.py", "Python", "production", py)])
    pb = metrics.platform_branches(d, cloc)
    check("branches total == 2 (comment/string excluded)", pb["total"] == 2)
    check("by_language python hits == 2", pb.get("by_language", {}).get("python", {}).get("hits") == 2)
    check("platform windows attributed", pb.get("by_platform", {}).get("windows", 0) == 1)
    check("platform linux attributed", pb.get("by_platform", {}).get("linux", 0) == 1)


def test_branches_js_block_comment():
    js = (
        "const os = require('os');\n"
        "if (process.platform === 'win32') {}\n"   # real → count
        "/* process.platform mentioned in a block comment */\n"  # block comment → NOT
        "// const x = process.platform;\n"          # line comment → NOT
        "const label = `process.platform=${'x'}`;\n"  # backtick: process.platform here is real code? it's inside template literal text → NOT
    )
    d, cloc = _cloc([("src/index.js", "JavaScript", "production", js)])
    pb = metrics.platform_branches(d, cloc)
    check("js branches total == 1", pb["total"] == 1)


def test_adaptation_skips_comment_blank():
    c = (
        "#ifdef _WIN32\n"
        "int a = 1;\n"          # code (1)
        "// a windows-only comment\n"   # comment-only → NOT
        "\n"                     # blank → NOT
        "int b = 2;\n"          # code (2)
        "/* block\n"             # block comment start → NOT
        "still comment */\n"     # block comment → NOT
        "#endif\n"
    )
    d, cloc = _cloc([("win.c", "C", "production", c)])
    pa = metrics.platform_adaptation(d, cloc)
    win = pa.get("by_platform", {}).get("windows", {})
    check("adaptation windows code == 2 (comment/blank excluded)", win.get("code") == 2)
    check("adaptation total == 2", pa.get("total") == 2)


def test_dir_loc_depth2():
    files = [
        ("setup.py", "Python", "production", "x = 1\n"),
        ("src/core/a.py", "Python", "production", "a = 1\nb = 2\n"),
        ("src/core/deep/nested/b.py", "Python", "production", "c = 3\n"),
        ("src/util.py", "Python", "production", "d = 4\n"),
        ("tests/test_a.py", "Python", "test", "assert True\n"),
    ]
    _, cloc = _cloc(files)
    rows = {r["dir"]: r for r in metrics._dir_loc(cloc)}
    check("dir_loc root files under '.'", rows.get(".", {}).get("files") == 1)
    check("dir_loc depth capped at 2 (src/core aggregates nested)",
          rows.get("src/core", {}).get("files") == 2)
    check("dir_loc src holds direct child file", rows.get("src", {}).get("files") == 1)
    check("dir_loc excludes test files", "tests" not in rows)


def test_arch_specific():
    c_simd = (
        "#include <immintrin.h>\n"          # x86 intrinsics header → hit
        "#include <stdio.h>\n"               # not an intrinsics header
        "void f() {\n"
        "  __asm__ volatile(\"cpuid\");\n"   # inline asm → hit (x86 via line hint)
        "  // __asm__ in a comment\n"        # comment → NOT counted
        "  const char *s = \"__asm__\";\n"   # string → NOT counted
        "}\n"
    )
    rs = (
        "pub fn g() {\n"
        "  unsafe { asm!(\"nop\"); }\n"      # rust inline asm → hit
        "  // asm!(\"commented\")\n"          # comment → NOT counted
        "}\n"
    )
    files = [
        ("src/simd.c", "C", "production", c_simd),
        ("src/lib.rs", "Rust", "production", rs),
        ("arch/x86/memcpy.S", "Assembly", "production", "mov rax, rbx\nret\n"),
        ("arch/neon/blit.s", "Assembly", "production", "ret\n"),
        ("tests/opt.s", "Assembly", "test", "nop\n"),   # test → excluded
    ]
    d, cloc = _cloc(files)
    a = metrics.arch_specific(d, cloc)
    x86 = a["by_arch"].get("x86", {})
    arm = a["by_arch"].get("arm", {})
    x86_asm_loc = next(f["code"] for f in a["asm_files"] if f["file"] == "arch/x86/memcpy.S")
    arm_asm_loc = next(f["code"] for f in a["asm_files"] if f["file"] == "arch/neon/blit.s")
    check("x86 asm file LOC attributed", x86.get("loc") == x86_asm_loc)
    check("arm asm file attributed via 'neon' path token", arm.get("loc") == arm_asm_loc)
    check("x86 hits = intrinsics include + inline asm", x86.get("hits") == 2)
    check("inline_asm_hits == 2 (C + Rust; comments/strings excluded)",
          a["inline_asm_hits"] == 2)
    check("intrinsics header recorded", a["intrinsics_headers"] == ["immintrin.h"])
    check("test asm file excluded", all(f["file"] != "tests/opt.s" for f in a["asm_files"]))
    check("total == asm-file LOC sum", a["total"] == x86_asm_loc + arm_asm_loc)


if __name__ == "__main__":
    test_branches_skip_comments_and_strings()
    test_branches_js_block_comment()
    test_adaptation_skips_comment_blank()
    test_dir_loc_depth2()
    test_arch_specific()
    if check.failed:
        print(f"\n{check.failed} check(s) FAILED")
        sys.exit(1)
    print("\nall checks passed")
