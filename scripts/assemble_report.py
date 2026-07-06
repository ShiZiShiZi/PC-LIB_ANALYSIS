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

# The output contract lives here; the shape-coercion pass keys on it.
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "references", "report_schema.json")


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Schema-driven shape coercion (harness strong-check).
#
# Weaker models occasionally emit a field with the wrong JSON *shape* — a lone
# string where the contract says string[] (e.g. an `evidence`), or an object
# where it says array (e.g. `entry_points`). Those are recoverable from model
# randomness, so instead of failing the whole run we normalise the value to the
# schema-declared type and record what we changed. Only fields the schema gives
# an explicit `type` for are touched, and the lookup is per-path — so e.g.
# `license.evidence` (declared string) is left alone while `native_api…evidence`
# (declared array) is wrapped. Nodes under oneOf/anyOf/allOf are left untouched
# (we don't guess through a choice). Genuinely unrecoverable problems (missing
# blocks, bad JSON, missing required keys) stay fatal in assemble().
# ---------------------------------------------------------------------------
def _typename(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return "unknown"


def _schema_types(schema):
    t = schema.get("type")
    if t is None:
        return None
    return set(t) if isinstance(t, list) else {t}


# Root schema for resolving local "#/definitions/…" $refs (set by coerce_report).
_ROOT_SCHEMA = None


def _resolve_ref(schema):
    """Follow local ($ref → #/…) references so coercion sees the real node
    (e.g. runtime_surface.network items → #/definitions/surfaceItem)."""
    seen = 0
    while isinstance(schema, dict) and "$ref" in schema and _ROOT_SCHEMA is not None:
        ref = schema["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/"):
            break
        node = _ROOT_SCHEMA
        for part in ref[2:].split("/"):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return schema  # unresolved → leave as-is
        schema = node
        seen += 1
        if seen > 16:
            break
    return schema


def _to_array(value):
    if isinstance(value, list):
        return value
    if value is None or value == "":
        return []
    if isinstance(value, dict):
        # A *wrapper* object groups items under one or more list-of-objects props
        # (e.g. entry_points {primary_entry_points:[{…},…], startup_type:"…"}) →
        # flatten those object-lists into the item array, dropping scalar metadata.
        # A single item object whose only list is a scalar field (e.g. its own
        # evidence:[str,…]) has no object-list → wrap the whole object as one item.
        groups = [v for v in value.values()
                  if isinstance(v, list) and any(isinstance(el, dict) for el in v)]
        if groups:
            flat = []
            for v in groups:
                flat.extend(v)
            return flat
        return [value]
    return [value]


def _to_string(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "；".join(_to_string(v) for v in value if v not in (None, ""))
    if isinstance(value, dict):
        return "；".join(f"{k}: {_to_string(v)}" for k, v in value.items())
    return str(value)


def coerce_to_schema(value, schema, path, fixes):
    """Recursively normalise `value` to the shape `schema` declares, appending a
    {path, from, to} record to `fixes` for each coercion. Returns the (possibly
    new) value; mutates dicts/lists in place where no type change is needed."""
    if not isinstance(schema, dict):
        return value
    schema = _resolve_ref(schema)
    if not isinstance(schema, dict):
        return value
    if any(k in schema for k in ("oneOf", "anyOf", "allOf")):
        return value  # a choice — don't guess which branch was intended

    types = _schema_types(schema)

    # No explicit type: only descend when the container shape already matches.
    if types is None:
        if isinstance(value, dict) and isinstance(schema.get("properties"), dict):
            return _recurse_object(value, schema, path, fixes)
        if isinstance(value, list) and isinstance(schema.get("items"), dict):
            return [coerce_to_schema(v, schema["items"], f"{path}[{i}]", fixes)
                    for i, v in enumerate(value)]
        return value

    if value is None:
        return value  # never fabricate a value for null

    actual = _typename(value)
    if actual in types or (actual == "integer" and "number" in types):
        # already conformant → recurse into structure to fix nested fields
        if actual == "object" and isinstance(schema.get("properties"), dict):
            return _recurse_object(value, schema, path, fixes)
        if actual == "array" and isinstance(schema.get("items"), dict):
            return [coerce_to_schema(v, schema["items"], f"{path}[{i}]", fixes)
                    for i, v in enumerate(value)]
        return value

    # mismatch → coerce toward a concrete target we can build safely
    if "array" in types:
        new = _to_array(value)
        fixes.append({"path": path or "$", "from": actual, "to": "array"})
        items = schema.get("items")
        if isinstance(items, dict):
            new = [coerce_to_schema(v, items, f"{path}[{i}]", fixes)
                   for i, v in enumerate(new)]
        return new
    if "string" in types:
        fixes.append({"path": path or "$", "from": actual, "to": "string"})
        return _to_string(value)
    # object/number/int/bool targets: no safe reconstruction from a wrong type → leave as-is
    return value


def _recurse_object(value, schema, path, fixes):
    props = schema.get("properties") or {}
    for k, subschema in props.items():
        if k in value and isinstance(subschema, dict):
            value[k] = coerce_to_schema(value[k], subschema,
                                        f"{path}.{k}" if path else k, fixes)
    return value


def coerce_report(report):
    """Normalise the assembled report to references/report_schema.json in place.
    Returns the list of fixes ([] if the schema can't be read → coercion skipped)."""
    global _ROOT_SCHEMA
    try:
        schema = _load(SCHEMA_PATH)
    except Exception:
        return []
    _ROOT_SCHEMA = schema
    fixes = []
    try:
        coerce_to_schema(report, schema, "", fixes)
    finally:
        _ROOT_SCHEMA = None
    return fixes


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

    # 5) schema-driven shape coercion (NON-fatal): repair recoverable model-shape
    #    drift (scalar↔array, object entry_points…) so the persisted report is
    #    contract-conformant. Record each fix in meta.warnings; never abort here.
    fixes = coerce_report(report)
    if fixes:
        meta = report.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            report["meta"] = meta
        warnings = list(meta.get("warnings") or [])
        for f in fixes:
            msg = f"shape coerced: {f['path']} {f['from']}→{f['to']}"
            if msg not in warnings:
                warnings.append(msg)
        meta["warnings"] = warnings

    # 6) validate required top-level keys present
    for k in REQUIRED_TOPLEVEL:
        if k not in report:
            errors.append(f"assembled report missing required top-level key '{k}'")

    if errors:
        return None, errors

    # 7) atomic write (tmp + os.replace) so a reader never sees a half-written report
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
    coerced = [w for w in ((report.get("meta") or {}).get("warnings") or [])
               if isinstance(w, str) and w.startswith("shape coerced:")]
    print(f"Wrote {out_path}")
    print(f"  top-level keys : {len(report)}")
    print(f"  primary lang   : {(report.get('languages') or {}).get('primary')}")
    print(f"  production code: {(cm.get('production') or {}).get('code')} lines")
    if coerced:
        print(f"  shape-coerced  : {len(coerced)} field(s) normalised to schema")
        for w in coerced:
            print(f"      - {w[len('shape coerced: '):]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
