#!/usr/bin/env python3
"""One-shot migration: normalize + re-stamp every runs/**/report.json through the shared
`report_normalize` module, so 存量 reports become self-consistent ON DISK (single source of
truth). After this runs, the panel (/api/report serves stamped reports as-is), the Excel export
and any direct reader all agree — no re-analysis needed.

Idempotent: a second run rewrites nothing (normalize_report is idempotent and the on-disk JSON
is already in the canonical `json.dumps(indent=2, ensure_ascii=False)` form).

Usage:
  python3 scripts/migrate_normalize.py [--runs runs] [--dry-run]
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import report_normalize as rn  # noqa: E402


def _find_reports(runs_dir):
    for dirpath, _dirs, files in os.walk(runs_dir):
        if "report.json" in files:
            yield os.path.join(dirpath, "report.json")


def main():
    ap = argparse.ArgumentParser(description="Normalize every runs/**/report.json in place (single source of truth).")
    ap.add_argument("--runs", default="runs", help="runs root (default: runs)")
    ap.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    args = ap.parse_args()

    total = changed = pc_fixed = errors = 0
    for path in _find_reports(args.runs):
        total += 1
        try:
            with open(path, encoding="utf-8") as fh:
                before_text = fh.read()
            report = json.loads(before_text)
        except Exception as e:  # noqa: BLE001
            errors += 1
            print(f"  ERR read {path}: {e}", file=sys.stderr)
            continue
        before_pc = ((report.get("harmony_adaptation") or {}).get("porting_class")
                     if isinstance(report, dict) else None)
        rn.normalize_report(report)
        after_pc = ((report.get("harmony_adaptation") or {}).get("porting_class")
                    if isinstance(report, dict) else None)
        after_text = json.dumps(report, indent=2, ensure_ascii=False)
        if after_text != before_text:
            changed += 1
            if before_pc != after_pc:
                pc_fixed += 1
                print(f"  porting_class {before_pc} → {after_pc}   {os.path.relpath(path)}")
            if not args.dry_run:
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    fh.write(after_text)
                os.replace(tmp, path)

    verb = "would change" if args.dry_run else "changed"
    print(f"\n{total} report(s) scanned · {verb} {changed} · porting_class corrected {pc_fixed} · errors {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
