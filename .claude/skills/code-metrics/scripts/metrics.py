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


def _dir_loc(cloc: ClocResult, depth: int = 2, cap: int = 80) -> list[dict]:
    """Production LOC aggregated per directory (path truncated at `depth` components).
    The mechanical baseline the dim-12 code_partition buckets must reconcile against:
    a bucket's module LOC should quote these numbers, and the bucket sum ≈ production
    total. Root-level files aggregate under '.'."""
    dirs: dict[str, dict] = {}
    for f in cloc.by_category("production"):
        parts = f.path.replace("\\", "/").split("/")
        d = "/".join(parts[:-1][:depth]) or "."
        row = dirs.setdefault(d, {"files": 0, "code": 0})
        row["files"] += 1
        row["code"] += f.code
    rows = [{"dir": d, **v} for d, v in dirs.items()]
    rows.sort(key=lambda r: r["code"], reverse=True)
    return rows[:cap]


def _code_metrics(cloc: ClocResult) -> dict:
    cats = {c: cloc.by_category(c) for c in ("production", "test", "example")}
    top_dirs, test_example_dirs = _top_dirs(cloc)
    return {
        "tool": cloc.tool,
        "total": _agg(cloc.files),
        "production": _agg(cats["production"]),
        "test": _agg(cats["test"]),
        "example": _agg(cats["example"]),
        "top_dirs": top_dirs,
        "test_example_dirs": test_example_dirs,
        "dir_loc": _dir_loc(cloc),
    }


import re  # noqa: E402

# Compile-macro families → platform. A #if/#ifdef block whose (positive) condition
# names one of these is counted as that platform's adaptation code.
_PLATFORM_MACROS = {
    "windows": {"_WIN32", "_WIN64", "WIN32", "WIN64", "_MSC_VER", "__MINGW32__",
                "__MINGW64__", "__CYGWIN__", "_WINDOWS", "__WIN32__"},
    "macos":   {"__APPLE__", "__MACH__", "TARGET_OS_MAC", "TARGET_OS_OSX", "__OSX__"},
    "linux":   {"__linux__", "__linux", "linux", "__gnu_linux__"},
    "posix":   {"__unix__", "__unix", "unix", "_POSIX_VERSION", "_POSIX_C_SOURCE", "__posix"},
}
_MACRO_TO_PLATFORM = {m: p for p, ms in _PLATFORM_MACROS.items() for m in ms}
_CXX_EXT = (".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hpp", ".hh", ".hxx",
            ".m", ".mm", ".cu", ".cuh")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NEG_DEFINED_RE = re.compile(r"!\s*defined\s*\([^)]*\)")

# Per-language comment/string masking so platform idioms inside comments or string
# literals don't inflate the mechanical counts. cfg: line-comment marker, C-style
# /* */ block comments, Python triple-quoted strings, backtick raw/template strings.
_MASK_CFG = {
    "python":     {"line": "#",  "block": False, "triple": True,  "backtick": False},
    "javascript": {"line": "//", "block": True,  "triple": False, "backtick": True},
    "java":       {"line": "//", "block": True,  "triple": False, "backtick": False},
    "go":         {"line": "//", "block": True,  "triple": False, "backtick": True},
    "rust":       {"line": "//", "block": True,  "triple": False, "backtick": False},
    "csharp":     {"line": "//", "block": True,  "triple": False, "backtick": False},
    "cpp":        {"line": "//", "block": True,  "triple": False, "backtick": False},
}


def _masked_lines(lines, cfg):
    """Yield (lineno, masked) where comment + string-literal content is replaced by
    spaces (structure preserved). Tracks /* */ block comments and Python triple quotes
    across lines. Single-line ' " (and backtick when enabled) strings are blanked too."""
    line_c = cfg.get("line")
    blk = cfg.get("block")
    triple_on = cfg.get("triple")
    tick = cfg.get("backtick")
    in_block = False
    triple = None
    for i, raw in enumerate(lines, 1):
        s = raw.rstrip("\n")
        out = []
        j, n = 0, len(s)
        instr = None
        while j < n:
            c = s[j]
            two = s[j:j + 2]
            if in_block:
                if two == "*/":
                    in_block = False; out.append("  "); j += 2; continue
                out.append(" "); j += 1; continue
            if triple is not None:
                if s[j:j + 3] == triple:
                    triple = None; out.append("   "); j += 3; continue
                out.append(" "); j += 1; continue
            if instr is not None:
                out.append(" ")
                if c == "\\" and j + 1 < n:
                    out.append(" "); j += 2; continue
                if c == instr:
                    instr = None
                j += 1; continue
            if triple_on and (s[j:j + 3] == '"""' or s[j:j + 3] == "'''"):
                triple = s[j:j + 3]; out.append("   "); j += 3; continue
            if blk and two == "/*":
                in_block = True; out.append("  "); j += 2; continue
            if line_c and s[j:j + len(line_c)] == line_c:
                break  # rest of line is a comment
            if c in ("'", '"') or (tick and c == "`"):
                instr = c; out.append(" "); j += 1; continue
            out.append(c); j += 1
        yield i, "".join(out)


def _platforms_in_condition(cond: str) -> set:
    # drop negated `!defined(X)` so e.g. `#if !defined(_WIN32)` isn't miscounted as windows
    cond = _NEG_DEFINED_RE.sub(" ", cond)
    out = set()
    for tok in _IDENT_RE.findall(cond):
        if tok in _MACRO_TO_PLATFORM:
            out.add(_MACRO_TO_PLATFORM[tok])
    return out


def platform_adaptation(repo: str, cloc: ClocResult) -> dict:
    """Count production C/C++/ObjC LOC wrapped in platform compile-macro guards.

    Mechanical preprocessor scan: tracks #if/#ifdef/#elif/#else/#endif nesting; lines
    inside a region whose enclosing guard positively names a platform macro are counted
    for that platform. #ifndef / !defined(...) are treated as negative (not counted).
    Heuristic (no full C preprocessor): comments inside guards are counted as code.
    """
    by = {p: {"files": 0, "code": 0, "macros": set()} for p in _PLATFORM_MACROS}
    for f in cloc.by_category("production"):
        if not f.path.lower().endswith(_CXX_EXT):
            continue
        try:
            with open(os.path.join(repo, f.path), encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        # mask comments/strings so blank/comment-only lines aren't counted as guarded code
        masked = [m for _, m in _masked_lines(lines, _MASK_CFG["cpp"])]
        stack = []          # each frame: set of platforms active in the current branch
        file_hit = set()
        for s in (mk.strip() for mk in masked):
            m = re.match(r"#\s*(ifdef|ifndef|if|elif|else|endif)\b(.*)", s)
            if m:
                d, rest = m.group(1), m.group(2)
                if d == "ifdef":
                    stack.append(_platforms_in_condition(rest))
                elif d == "ifndef":
                    stack.append(set())                       # negative guard → no platform
                elif d == "if":
                    stack.append(_platforms_in_condition(rest))
                elif d == "elif":
                    if stack:
                        stack[-1] = _platforms_in_condition(rest)
                elif d == "else":
                    if stack:
                        stack[-1] = set()                     # else of a platform guard = other platforms
                elif d == "endif":
                    if stack:
                        stack.pop()
                continue
            if not s:                                          # blank or comment-only → not code
                continue
            active = set().union(*stack) if stack else set()  # any enclosing guard names a platform
            for p in active:
                by[p]["code"] += 1
                file_hit.add(p)
        for p in file_hit:
            by[p]["files"] += 1
            for s in (mk.strip() for mk in masked):            # record which macros were seen for this platform
                mm = re.match(r"#\s*(?:ifdef|ifndef|if|elif)\b(.*)", s)
                if mm:
                    for tok in _IDENT_RE.findall(mm.group(1)):
                        if _MACRO_TO_PLATFORM.get(tok) == p:
                            by[p]["macros"].add(tok)
    out = {p: {"files": v["files"], "code": v["code"], "macros": sorted(v["macros"])}
           for p, v in by.items() if v["code"]}
    return {
        "by_platform": out,
        "total": sum(v["code"] for v in out.values()),
        "notes": "机械计数：仅生产代码中 C/C++/ObjC 文件、被平台编译宏(#ifdef _WIN32/__APPLE__/__linux__…)"
                 "正向包裹的代码行；#ifndef/!defined 不计；嵌套/多平台守卫按命中平台分别计；空行与注释行已剔除。",
    }


# ── Runtime platform-detection branches (language-level, not compile macros) ──
# Pure-language libs branch on the platform at runtime (if/else/switch on
# sys.platform / process.platform / os.name / runtime.GOOS / cfg!(target_os) …).
# These ALSO need adaptation but carry no #ifdef, so platform_adaptation misses
# them. We count occurrences of the detection idioms per language with sample
# sites — a reproducible signal dim-9 (model + codegraph) then interprets.
_BRANCH_LANG_EXT = {
    "python": (".py",),
    "javascript": (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"),
    "java": (".java", ".kt"),
    "go": (".go",),
    "rust": (".rs",),
    "csharp": (".cs",),
}
_EXT_TO_BRANCH_LANG = {e: lang for lang, exts in _BRANCH_LANG_EXT.items() for e in exts}
_BRANCH_PATTERNS = {
    "python": re.compile(
        r"\bsys\.platform\b|\bos\.name\b|\bos\.uname\s*\(|"
        r"\bplatform\.(?:system|machine|uname|platform|release|version|architecture)\s*\("),
    "javascript": re.compile(
        r"\bprocess\.platform\b|\bprocess\.arch\b|\bos\.(?:platform|type|arch|release)\s*\(|"
        r"\bnavigator\.(?:platform|userAgent)\b"),
    "java": re.compile(r"""System\.getProperty\(\s*["']os\.(?:name|arch|version)["']"""),
    "go": re.compile(r"\bruntime\.GO(?:OS|ARCH)\b"),
    "rust": re.compile(r"cfg!\s*\(\s*target_os|#\[\s*cfg\s*\(\s*target_os|std::env::consts::(?:OS|ARCH)\b"),
    "csharp": re.compile(
        r"RuntimeInformation\.IsOSPlatform|Environment\.OSVersion|Environment\.Is64BitOperatingSystem"),
}
# Heuristic platform attribution from keywords on the matched line.
_BRANCH_PLAT_KEYWORDS = {
    "windows": ("win32", "win64", "windows", "_nt", "msvc", "mingw", "cygwin", "msys"),
    "macos":   ("darwin", "macos", "mac_os", "osx", "apple", "mach"),
    "linux":   ("linux",),
    "posix":   ("unix", "posix", "bsd", "solaris", "aix", "sunos"),
}
_BRANCH_SAMPLE_CAP = 30


def platform_branches(repo: str, cloc: ClocResult) -> dict:
    """Count production runtime platform-detection idioms per language + sample sites."""
    by_lang = {}
    by_plat = {p: 0 for p in _BRANCH_PLAT_KEYWORDS}
    samples = []
    total = 0
    for f in cloc.by_category("production"):
        ext = os.path.splitext(f.path)[1].lower()
        lang = _EXT_TO_BRANCH_LANG.get(ext)
        if not lang:
            continue
        pat = _BRANCH_PATTERNS[lang]
        try:
            with open(os.path.join(repo, f.path), encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        file_hit = False
        cfg = _MASK_CFG.get(lang, {})
        for i, masked in _masked_lines(lines, cfg):
            # Match the IDIOM on the masked line (so commented-out / stringified
            # mentions don't count); attribute the PLATFORM on the raw line (the
            # platform value lives in a string literal, e.g. == "linux").
            if not pat.search(masked):
                continue
            raw = lines[i - 1]
            total += 1
            file_hit = True
            agg = by_lang.setdefault(lang, {"files": 0, "hits": 0})
            agg["hits"] += 1
            low = raw.lower()
            for p, kws in _BRANCH_PLAT_KEYWORDS.items():
                if any(k in low for k in kws):
                    by_plat[p] += 1
            if len(samples) < _BRANCH_SAMPLE_CAP:
                samples.append({"language": lang, "file": f.path, "line": i,
                                "text": raw.strip()[:160]})
        if file_hit:
            by_lang[lang]["files"] += 1
    return {
        "by_language": by_lang,
        "by_platform": {p: n for p, n in by_plat.items() if n},
        "samples": samples,
        "total": total,
        "notes": "机械计数（启发式）：生产代码中运行时平台判断惯用法"
                 "(sys.platform/os.name、process.platform、System.getProperty(\"os.name\")、"
                 "runtime.GOOS、cfg!(target_os)、RuntimeInformation…)的出现次数与样例位置；"
                 "C/C++ 编译宏由 platform_adaptation 覆盖，本项不计；by_platform 依命中行平台关键字"
                 "启发式归类，可能漏判/多判；注释与字符串字面量内的命中已剔除。",
    }


# ── Architecture-specific code (assembly / SIMD intrinsics / inline asm) ──
# x86-only asm or intrinsics with no arm fallback is hard porting work (or a
# blocker) on HarmonyOS PC arm64 — a third mechanical adaptation signal for
# dim-9/dim-12 alongside platform_adaptation and platform_branches.
_ASM_EXTS = (".s", ".asm")
_ARCH_PATH_TOKENS = {
    "x86":   {"x86", "x64", "i386", "i486", "i586", "i686", "amd64", "intel",
              "mmx", "sse", "sse2", "sse3", "ssse3", "sse41", "sse42", "avx",
              "avx2", "avx512"},
    "arm":   {"arm", "arm64", "armv6", "armv7", "armv8", "armv9", "aarch64",
              "neon", "sve", "thumb"},
    "riscv": {"riscv", "riscv32", "riscv64", "rv32", "rv64"},
}
_ARCH_TOKEN_PREFIXES = (("x86", ("sse", "avx")), ("arm", ("armv", "neon")))
_INTRIN_HEADER_ARCH = {
    "x86": ("mmintrin", "xmmintrin", "emmintrin", "pmmintrin", "tmmintrin",
            "smmintrin", "nmmintrin", "wmmintrin", "ammintrin", "immintrin",
            "avxintrin", "avx2intrin", "avx512", "x86intrin", "x86gprintrin",
            "cpuid", "intrin"),
    "arm": ("arm_neon", "arm_acle", "arm_sve", "arm_fp16", "arm_bf16",
            "arm64intr", "arm64_neon", "armintr"),
    "riscv": ("riscv_vector", "riscv_crypto", "riscv_bitmanip"),
}
_INLINE_ASM_RE = re.compile(r"__asm__|\b__asm\b|\b_asm\b|\basm\s*(?:volatile|goto)?\s*[({]")
_RUST_ASM_RE = re.compile(r"\b(?:core::arch::)?(?:global_)?asm!\s*[({[]")
_INCLUDE_RE = re.compile(r'#\s*include\s*[<"]([^>"]+)[>"]')
# x86/arm register & mnemonic hints for attributing an inline-asm LINE to an arch.
_ARCH_LINE_HINTS = {
    "x86": re.compile(r"\b(?:[re]?[abcd]x|[re]?(?:si|di|sp|bp)|xmm\d|ymm\d|zmm\d|cpuid|rdtsc)\b", re.I),
    "arm": re.compile(r"\b(?:aarch64|neon|vld\d|vst\d|dmb|dsb|isb|w(?:zr|sp)|mrs|msr)\b", re.I),
}
# SIMD intrinsic *usage* (call sites / vector types), not just the header include —
# this is the real architecture-specific work in header-only / intrinsics-heavy libs
# (e.g. hnswlib). Counted as simd_loc (lines), so a file that pulls the intrinsic
# header *transitively* (no direct #include of its own) is still attributed. The names
# are identical in C/C++ and Rust core::arch, so both are scanned. Case-sensitive on
# purpose (real intrinsics are lowercase; UPPER_CASE macros like _MM_SHUFFLE are skipped).
_SIMD_INTRIN_ARCH = (
    ("x86", re.compile(
        r"\b_mm(?:256|512)?_[a-z]"            # _mm_/_mm256_/_mm512_ calls
        r"|\b__m(?:128|256|512)\w*\b")),      # __m128/__m256/__m512(i/d) vector types
    ("arm", re.compile(
        r"\b(?:float|u?int|poly)(?:8|16|32|64)x\d+(?:x\d+)?_t\b"          # NEON types: float32x4_t, uint8x16x2_t
        r"|\bv[a-z][a-z0-9]*_(?:[su](?:8|16|32|64)|f(?:16|32|64)|p(?:8|16|64))\b"  # NEON intrinsics: vld1q_f32
        r"|\bsv(?:float|u?int|bool)\w*_t\b")),                             # SVE types: svfloat32_t
    ("riscv", re.compile(
        r"\b__riscv_\w+"                       # RVV intrinsics: __riscv_vfadd_vv_f32m1
        r"|\bv(?:float|u?int)\w*m\d+_t\b")),   # RVV types: vfloat32m1_t
)


def _arch_of_path(path: str) -> str | None:
    toks = set(re.split(r"[^a-z0-9]+", path.lower()))
    for arch, vocab in _ARCH_PATH_TOKENS.items():
        if toks & vocab:
            return arch
    for arch, prefixes in _ARCH_TOKEN_PREFIXES:
        if any(t.startswith(prefixes) for t in toks):
            return arch
    return None


def _arch_of_header(header: str) -> str | None:
    base = os.path.basename(header).lower().rsplit(".", 1)[0]
    for arch, prefixes in _INTRIN_HEADER_ARCH.items():
        if base.startswith(prefixes):
            return arch
    return None


def arch_specific(repo: str, cloc: ClocResult) -> dict:
    """Count production architecture-specific code: standalone assembly files (LOC,
    arch from path tokens), SIMD-intrinsics includes, and inline-asm sites in
    C/C++/Rust (comment/string hits masked out). Heuristic but reproducible."""
    by = {a: {"files": set(), "hits": 0, "loc": 0, "simd_loc": 0} for a in ("x86", "arm", "riscv", "generic")}
    asm_files, headers, samples = [], set(), []
    inline_hits = 0

    def sample(kind, file, line, text, arch):
        if len(samples) < _BRANCH_SAMPLE_CAP:
            samples.append({"kind": kind, "file": file, "line": line,
                            "text": (text or "").strip()[:160], "arch": arch})

    for f in cloc.by_category("production"):
        low = f.path.lower()
        # 1) standalone assembly files
        if f.language == "Assembly" or low.endswith(_ASM_EXTS):
            arch = _arch_of_path(f.path) or "generic"
            by[arch]["files"].add(f.path)
            by[arch]["loc"] += f.code
            if len(asm_files) < 40:
                asm_files.append({"file": f.path, "code": f.code, "arch": arch})
            sample("asm_file", f.path, 1, None, arch)
            continue
        is_cxx = low.endswith(_CXX_EXT)
        is_rust = low.endswith(".rs")
        if not (is_cxx or is_rust):
            continue
        try:
            with open(os.path.join(repo, f.path), encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        file_arch = _arch_of_path(f.path)
        cfg = _MASK_CFG["rust" if is_rust else "cpp"]
        asm_re = _RUST_ASM_RE if is_rust else _INLINE_ASM_RE
        for i, masked in _masked_lines(lines, cfg):
            s = masked.strip()
            if not s:
                continue
            # 2) SIMD-intrinsics includes (C/C++; system headers use <...>)
            if is_cxx and s.startswith("#") and "include" in s:
                m = _INCLUDE_RE.search(lines[i - 1])
                arch = _arch_of_header(m.group(1)) if m else None
                if arch:
                    headers.add(os.path.basename(m.group(1)))
                    by[arch]["files"].add(f.path)
                    by[arch]["hits"] += 1
                    sample("intrinsics", f.path, i, lines[i - 1], arch)
                continue
            # 3) inline asm (masked line, so comments/strings don't count)
            if asm_re.search(s):
                raw = lines[i - 1]
                arch = file_arch
                if not arch:
                    for a, hint in _ARCH_LINE_HINTS.items():
                        if hint.search(raw):
                            arch = a
                            break
                arch = arch or "generic"
                inline_hits += 1
                by[arch]["files"].add(f.path)
                by[arch]["hits"] += 1
                sample("inline_asm", f.path, i, raw, arch)
                continue
            # 4) SIMD intrinsic *usage* (call sites / vector types) — counted per line
            #    as simd_loc, so a file that pulls the intrinsic header transitively
            #    (no #include of its own, e.g. hnswlib space_l2.h) is still attributed.
            for a, rx in _SIMD_INTRIN_ARCH:
                if rx.search(s):
                    by[a]["simd_loc"] += 1
                    by[a]["files"].add(f.path)
                    sample("simd", f.path, i, lines[i - 1], a)
                    break
    out = {a: {"files": len(v["files"]), "hits": v["hits"], "loc": v["loc"], "simd_loc": v["simd_loc"]}
           for a, v in by.items() if v["files"] or v["hits"] or v["loc"] or v["simd_loc"]}
    return {
        "by_arch": out,
        "asm_files": asm_files,
        "inline_asm_hits": inline_hits,
        "intrinsics_headers": sorted(headers),
        "samples": samples,
        "total": sum(v["loc"] for v in out.values()),
        "simd_total": sum(v["simd_loc"] for v in out.values()),
        "notes": "机械计数（启发式）：生产代码中的架构相关代码——独立汇编文件(.s/.asm，LOC 按路径"
                 "关键字归 x86/arm/riscv/generic)、SIMD intrinsics 头(#include <immintrin.h/"
                 "arm_neon.h…>)、SIMD intrinsic 使用行(_mm*/__m256/vld1q_f32/…，含仅 transitive "
                 "include 的文件，计入 by_arch.simd_loc 与 simd_total)、C/C++/Rust 内联汇编"
                 "(__asm__/asm!/…)命中；注释与字符串内命中已剔除；total=汇编文件 LOC 之和、"
                 "simd_total=SIMD 使用行之和。仅 x86 有 simd_loc/汇编而无 arm 回退的部分是 arm64 "
                 "鸿蒙 PC 上的适配点（补 NEON 或退标量），供 dim-9/dim-12 判读（samples 可作 "
                 "codegraph 追踪种子）。",
    }


def compute(repo: str) -> dict:
    cloc = run_cloc(repo)
    cm = _code_metrics(cloc)
    cm["platform_adaptation"] = platform_adaptation(repo, cloc)
    cm["platform_branches"] = platform_branches(repo, cloc)
    cm["arch_specific"] = arch_specific(repo, cloc)
    fragment = {
        "languages": _languages(cloc),
        "code_metrics": cm,
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
        with open(args.out, "w", encoding="utf-8") as fh:
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
