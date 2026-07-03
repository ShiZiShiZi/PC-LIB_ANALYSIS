#!/usr/bin/env python3
"""Assemble the final report.json from per-dimension block files + the deterministic
metrics fragment, then write it ATOMICALLY.

This replaces the agent hand-writing (and re-transcribing metrics.json into) one giant
report.json at the end of a run. Instead the model streams each dimension to
``<run-dir>/blocks/<name>.json`` as it reasons, and this script splices them together
deterministically — spreading the output over the whole run, keeping the deterministic
metrics byte-exact (no hand-copy errors), and letting a crashed run keep its partial
blocks.

Block-file contract: ``<blocks>/<name>.json`` where ``<name>`` is a top-level report key
and the file's content IS that block's JSON value. The deterministic blocks
(languages/code_metrics/tests) come ONLY from metrics.json — any blocks/languages.json
etc. is ignored so the mechanical numbers can never be overwritten by the model.

On any error (missing required block, bad JSON, missing metrics key) NOTHING is written
and the exit code is non-zero, so the server's "exit 0 but no report.json = failure"
check marks the run errored rather than shipping a broken report.

Usage:
  python3 scripts/assemble_report.py --run-dir <runDir>
  # or override individually:
  python3 scripts/assemble_report.py --blocks <dir> --metrics <metrics.json> --out <report.json>
"""
import argparse
import datetime
import json
import os
import sys

# Deterministic blocks — spliced from metrics.json, NEVER from the model's blocks/.
METRICS_KEYS = ["languages", "code_metrics", "tests"]
# Model-reasoned blocks written to blocks/<name>.json (filename == top-level key).
REASONED_REQUIRED = ["function_summary", "license", "dependencies", "native_api",
                     "runtime_surface", "build_env", "harmony_adaptation", "library", "meta"]
REASONED_OPTIONAL = ["capability_profile", "cloud_services"]
# Full required top-level set per references/report_schema.json.
REQUIRED_TOPLEVEL = ["library", "function_summary", "languages", "code_metrics", "tests",
                     "license", "dependencies", "native_api", "runtime_surface",
                     "build_env", "harmony_adaptation", "meta"]


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def assemble(blocks_dir, metrics_path, out_path):
    """Return (report_dict, errors). Writes out_path atomically only when errors is []."""
    errors = []

    # 1) deterministic fragment (languages / code_metrics / tests) from metrics.json
    metrics = {}
    if not os.path.isfile(metrics_path):
        errors.append(f"metrics fragment not found: {metrics_path}")
    else:
        try:
            metrics = _load(metrics_path)
        except Exception as e:
            errors.append(f"metrics fragment not valid JSON ({metrics_path}): {e}")

    report = {}
    for k in METRICS_KEYS:
        if k in metrics:
            report[k] = metrics[k]
        else:
            errors.append(f"metrics fragment missing '{k}' (run metrics.py first)")

    # 2) model-reasoned blocks from blocks/<name>.json
    def read_block(name, required):
        p = os.path.join(blocks_dir, name + ".json")
        if not os.path.isfile(p):
            if required:
                errors.append(f"missing required block: {os.path.join(blocks_dir, name + '.json')}")
            return None
        try:
            return _load(p)
        except Exception as e:
            errors.append(f"block {name}.json not valid JSON: {e}")
            return None

    for name in REASONED_REQUIRED:
        v = read_block(name, required=True)
        if v is not None:
            report[name] = v
    for name in REASONED_OPTIONAL:
        v = read_block(name, required=False)
        if v is not None:
            report[name] = v

    # 3) deterministic meta fields — model-set fields (confidence_overall/observations)
    #    are preserved; these are guaranteed even if the model omitted them.
    meta = report.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    meta.setdefault("schema_version", "1.0")
    meta["analyzer"] = "pc-lib-analyzer"
    tool = (metrics.get("code_metrics") or {}).get("tool")
    if tool and not meta.get("counter_tool"):
        meta["counter_tool"] = tool
    # carry metrics warnings into meta.warnings (union, no dup)
    mw = metrics.get("_warnings") or []
    if mw:
        warnings = list(meta.get("warnings") or [])
        for w in mw:
            if w not in warnings:
                warnings.append(w)
        meta["warnings"] = warnings
    report["meta"] = meta

    # 4) library.analyzed_at deterministic fallback (ISO-8601 UTC)
    lib = report.get("library")
    if isinstance(lib, dict) and not lib.get("analyzed_at"):
        lib["analyzed_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 5) validate required top-level keys present
    for k in REQUIRED_TOPLEVEL:
        if k not in report:
            errors.append(f"assembled report missing required top-level key '{k}'")

    if errors:
        return None, errors

    # 6) atomic write (tmp + os.replace) so a reader never sees a half-written report
    text = json.dumps(report, indent=2, ensure_ascii=False)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, out_path)
    return report, []


def main():
    ap = argparse.ArgumentParser(
        description="Assemble report.json from blocks/ + metrics.json (atomic).")
    ap.add_argument("--run-dir", help="run directory; derives blocks/, metrics.json, report.json")
    ap.add_argument("--blocks", help="override blocks dir (default <run-dir>/blocks)")
    ap.add_argument("--metrics", help="override metrics.json path (default <run-dir>/metrics.json)")
    ap.add_argument("--out", help="override output report path (default <run-dir>/report.json)")
    args = ap.parse_args()

    if not args.run_dir and not (args.blocks and args.metrics and args.out):
        print("error: provide --run-dir (or all of --blocks/--metrics/--out)", file=sys.stderr)
        return 2
    blocks_dir = args.blocks or os.path.join(args.run_dir, "blocks")
    metrics_path = args.metrics or os.path.join(args.run_dir, "metrics.json")
    out_path = args.out or os.path.join(args.run_dir, "report.json")

    report, errors = assemble(blocks_dir, metrics_path, out_path)
    if errors:
        print("assemble_report: FAILED — report.json NOT written:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    cm = report.get("code_metrics", {})
    print(f"Wrote {out_path}")
    print(f"  top-level keys : {len(report)}")
    print(f"  primary lang   : {(report.get('languages') or {}).get('primary')}")
    print(f"  production code: {(cm.get('production') or {}).get('code')} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
