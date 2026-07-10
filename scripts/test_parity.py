#!/usr/bin/env python3
"""Minimal JS↔Python parity harness for the dim-9 normalizer mirror.

Asserts web/server.js `normalizeHarmony` and scripts/report_normalize.`normalize_harmony`
produce an identical `harmony_adaptation` (+ meta confidence) on real reports — the two MUST
stay byte-for-byte equivalent (CLAUDE.md). Run:

  python3 scripts/test_parity.py [N]     # N reports sampled across the corpus (default 12)

Exit 0 = agree. Requires `node` + a populated runs/ tree.
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import report_normalize as rn  # noqa: E402

HELPER = os.path.join(ROOT, "scripts", "_parity_helper.js")


def py_side(path):
    with open(path, encoding="utf-8") as fh:
        r = json.load(fh)
    rn.normalize_harmony(r)
    meta = r.get("meta") or {}
    return {"ha": r.get("harmony_adaptation"),
            "meta": {"confidence_overall": meta.get("confidence_overall"),
                     "confidence_overall_model": meta.get("confidence_overall_model")}}


def js_side(path):
    fd, out = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        res = subprocess.run(["node", HELPER, path, out], capture_output=True, text=True, cwd=ROOT)
        if res.returncode != 0:
            raise RuntimeError(f"node helper failed:\n{res.stderr}")
        with open(out, encoding="utf-8") as fh:
            return json.load(fh)
    finally:
        os.unlink(out)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    reports = sorted(glob.glob(os.path.join(ROOT, "runs", "*", "*", "*", "report.json")))
    if not reports:
        print("parity: no reports under runs/ — nothing to check")
        return
    if len(reports) > n:                       # deterministic spread across the corpus
        step = len(reports) // n
        reports = reports[::step][:n]
    fails, checked = [], 0
    for p in reports:
        try:
            js = js_side(p)
        except Exception as e:                 # noqa: BLE001
            fails.append(f"{os.path.relpath(p, ROOT)}: JS side error: {e}")
            continue
        py = py_side(p)
        checked += 1
        if js != py:
            pha, jha = (py.get("ha") or {}), (js.get("ha") or {})
            fails.append(f"{os.path.relpath(p, ROOT)}: MISMATCH "
                         f"(py.fv={pha.get('functional_viability')} js.fv={jha.get('functional_viability')} "
                         f"py.conf={pha.get('confidence')} js.conf={jha.get('confidence')})")
    if fails:
        print(f"PARITY FAIL ({len(fails)} of {checked} checked):")
        for f in fails:
            print("  -", f)
        raise SystemExit(1)
    print(f"parity: {checked} reports — JS and Python normalizeHarmony agree")


if __name__ == "__main__":
    main()
