#!/usr/bin/env python3
"""Regression test for assemble_report.py — run: python3 scripts/test_assemble_report.py

Covers: metrics splice is byte-exact, model blocks preserved, deterministic meta filled,
optional blocks omittable, a missing REQUIRED block fails with NO report written and no
leftover .tmp, and the atomic write leaves a clean output.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "assemble_report.py")

METRICS = {
    "languages": {"primary": "C++", "all": ["C++", "Python"],
                  "breakdown": [{"language": "C++", "code": 100, "files": 5}]},
    "code_metrics": {"tool": "cloc 1.98", "production": {"code": 100}, "total": {"code": 120}},
    "tests": {"test_files": 3, "test_cases": 12, "frameworks": ["gtest"]},
    "_warnings": ["cloc: skipped 1 binary file"],
}
REQUIRED_BLOCKS = {
    "function_summary": {"summary": "示例库", "categories": []},
    "license": {"spdx": "MIT", "confidence": "high", "category": "permissive"},
    "dependencies": {"count": 0, "dependencies": []},
    "native_api": {"summary": "", "groups": [], "platform_dependence": "portable"},
    "runtime_surface": {}, "build_env": {},
    "harmony_adaptation": {"feasibility": "feasible", "porting_class": "no_adaptation"},
    "library": {"name": "demo", "source_url": "https://github.com/x/demo", "ecosystem": "cpp"},
    "meta": {"confidence_overall": "high", "observations": []},
}
OPTIONAL_BLOCKS = {
    "cloud_services": {"present": False, "services": []},
    "code_partition": {
        "summary": "纯 C++ 库，全部可重编译复用",
        "coverage": {"production_code": 100, "partitioned_code": 100, "pct": 100.0},
        "buckets": [{"class": "recompile_reuse", "loc": 100, "pct": 100.0,
                     "modules": [{"path": "src", "loc": 100, "reason": "纯算法"}],
                     "basis": "native_api 无平台组"}],
    },
}
REQUIRED_TOPLEVEL = ["library", "function_summary", "languages", "code_metrics", "tests",
                     "license", "dependencies", "native_api", "runtime_surface",
                     "build_env", "harmony_adaptation", "meta"]


def _setup(include_optional=True):
    d = tempfile.mkdtemp()
    blocks = os.path.join(d, "blocks")
    os.makedirs(blocks)
    with open(os.path.join(d, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(METRICS, fh, ensure_ascii=False)
    all_blocks = dict(REQUIRED_BLOCKS)
    if include_optional:
        all_blocks.update(OPTIONAL_BLOCKS)
    for k, v in all_blocks.items():
        with open(os.path.join(blocks, k + ".json"), "w", encoding="utf-8") as fh:
            json.dump(v, fh, ensure_ascii=False)
    return d


def _run(d):
    return subprocess.run([sys.executable, SCRIPT, "--run-dir", d],
                          capture_output=True, text=True)


def test_happy_path():
    d = _setup()
    r = _run(d)
    assert r.returncode == 0, r.stderr
    rep = json.load(open(os.path.join(d, "report.json"), encoding="utf-8"))
    for k in ("languages", "code_metrics", "tests"):
        assert rep[k] == METRICS[k], f"deterministic block {k} not byte-exact"
    assert rep["meta"]["schema_version"] == "1.0"
    assert rep["meta"]["analyzer"] == "pc-lib-analyzer"
    assert rep["meta"]["counter_tool"] == "cloc 1.98"
    assert rep["meta"]["confidence_overall"] == "high"          # model field preserved
    assert "cloc: skipped 1 binary file" in rep["meta"]["warnings"]
    assert rep["library"]["analyzed_at"].endswith("Z")          # deterministic fill
    assert "cloud_services" in rep                              # optional present
    assert rep["code_partition"]["buckets"][0]["class"] == "recompile_reuse"
    for k in REQUIRED_TOPLEVEL:
        assert k in rep, f"missing required top-level {k}"
    assert not os.path.exists(os.path.join(d, "report.json.tmp"))
    print("ok test_happy_path")


def test_optional_omitted():
    d = _setup(include_optional=False)
    r = _run(d)
    assert r.returncode == 0, r.stderr
    rep = json.load(open(os.path.join(d, "report.json"), encoding="utf-8"))
    assert "cloud_services" not in rep
    assert "code_partition" not in rep
    print("ok test_optional_omitted")


def test_missing_required_block_fails_clean():
    d = _setup()
    os.remove(os.path.join(d, "blocks", "harmony_adaptation.json"))
    r = _run(d)
    assert r.returncode != 0, "must fail when a required block is missing"
    assert not os.path.exists(os.path.join(d, "report.json")), "must NOT write report on error"
    assert not os.path.exists(os.path.join(d, "report.json.tmp")), "no leftover tmp on error"
    assert "harmony_adaptation" in r.stderr
    print("ok test_missing_required_block_fails_clean")


def test_missing_metrics_fails():
    d = _setup()
    os.remove(os.path.join(d, "metrics.json"))
    r = _run(d)
    assert r.returncode != 0
    assert not os.path.exists(os.path.join(d, "report.json"))
    print("ok test_missing_metrics_fails")


# The canonical failure: the model writes the *combined* dim-8 object into BOTH
# blocks/runtime_surface.json and blocks/build_env.json (double-nested). The
# gate must deterministically UNWRAP it (non-fatal) so the dimension survives.
_CONFLATED_DIM8 = {
    "runtime_surface": {"summary": "无网络", "network": [], "filesystem": [{"detail": "x"}],
                        "env_vars": [], "subprocess": [], "devices": [], "services": []},
    "build_env": {"language_standard": "C++17", "build_system": "CMake",
                  "platforms": [{"os": "linux", "arch": "x86_64"}], "entry_points": []},
}


def test_conflated_dim8_unwrapped():
    d = _setup()
    for name in ("runtime_surface", "build_env"):
        with open(os.path.join(d, "blocks", name + ".json"), "w", encoding="utf-8") as fh:
            json.dump(_CONFLATED_DIM8, fh, ensure_ascii=False)
    r = _run(d)
    assert r.returncode == 0, r.stderr
    rep = json.load(open(os.path.join(d, "report.json"), encoding="utf-8"))
    # both blocks unwrapped to their own value → flat paths reachable again
    assert isinstance(rep["runtime_surface"].get("network"), list), rep["runtime_surface"]
    assert rep["runtime_surface"]["filesystem"][0]["detail"] == "x"
    assert rep["build_env"]["language_standard"] == "C++17"
    assert "runtime_surface" not in rep["build_env"], "build_env still double-nested"
    warns = rep["meta"].get("warnings") or []
    assert any("unwrapped conflated dim-8" in w for w in warns), warns
    print("ok test_conflated_dim8_unwrapped")


def test_malformed_block_fails_clean():
    """A block with alien keys and no inner sub-object to unwrap is unrecoverable
    → fatal, no report written, error names the block (agent must re-fill it)."""
    d = _setup()
    with open(os.path.join(d, "blocks", "build_env.json"), "w", encoding="utf-8") as fh:
        json.dump({"foo": 1, "bar": 2}, fh, ensure_ascii=False)
    r = _run(d)
    assert r.returncode != 0, "malformed alien-keyed block must fail"
    assert not os.path.exists(os.path.join(d, "report.json"))
    assert not os.path.exists(os.path.join(d, "report.json.tmp"))
    assert "build_env" in r.stderr, r.stderr
    print("ok test_malformed_block_fails_clean")


def test_missing_required_subfield_fails():
    """license without its schema-required spdx/confidence is fatal."""
    d = _setup()
    with open(os.path.join(d, "blocks", "license.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": "MIT License"}, fh, ensure_ascii=False)
    r = _run(d)
    assert r.returncode != 0
    assert not os.path.exists(os.path.join(d, "report.json"))
    assert "license" in r.stderr, r.stderr
    print("ok test_missing_required_subfield_fails")


def main():
    test_happy_path()
    test_optional_omitted()
    test_missing_required_block_fails_clean()
    test_missing_metrics_fails()
    test_conflated_dim8_unwrapped()
    test_malformed_block_fails_clean()
    test_missing_required_subfield_fails()
    print("ALL ASSEMBLE TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
