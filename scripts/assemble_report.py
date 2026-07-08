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
REASONED_OPTIONAL = ["capability_profile", "cloud_services", "code_partition"]
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


# ---------------------------------------------------------------------------
# Structural completeness gate (harness HARD-check).
#
# Shape coercion above only repairs *type* drift (scalar↔array). A weaker model
# can instead emit an object whose KEYS are entirely wrong yet whose TYPE is
# right — it still passes `type:object`, and `_recurse_object` only touches keys
# shared with the schema, so the wrong keys are never examined. The canonical
# failure: the model writes the *combined* dim-8 object
# `{runtime_surface:{…}, build_env:{…}}` into BOTH blocks/runtime_surface.json
# and blocks/build_env.json, double-nesting each block one level too deep — so
# report.runtime_surface.network / report.build_env.language_standard vanish and
# the whole dimension renders empty downstream.
#
# Two passes, run AFTER coercion, BEFORE the required-top-level check:
#   (a) unwrap_conflated_dim8  — deterministic, safe, NON-fatal (record a warning)
#   (b) check_block_shapes     — FATAL for genuinely-malformed required blocks,
#       so assemble() writes no report and the agent (still in-session) re-fills
#       the named block and re-runs.
# ---------------------------------------------------------------------------

# Declared property keys of each dim-8 block (from report_schema.json). A block
# object sharing NONE of its own block's keys but carrying the OTHER key is the
# double-nesting signature we can safely unwrap.
_DIM8_KEYS = {
    "runtime_surface": {"summary", "network", "filesystem", "env_vars",
                        "subprocess", "devices", "services"},
    "build_env": {"language_standard", "runtime_version", "build_system",
                  "compiler_extensions", "platforms", "entry_points",
                  "packaging", "notes"},
}


def unwrap_conflated_dim8(report):
    """Repair the double-nested dim-8 blocks in place. Returns a list of the
    block names unwrapped (for a meta.warnings note). Safe/deterministic: only
    acts when the block is an object that shares NONE of its own declared keys
    yet contains a nested sub-object under its own name."""
    unwrapped = []
    for key, own_keys in _DIM8_KEYS.items():
        val = report.get(key)
        if not isinstance(val, dict):
            continue
        if own_keys & set(val.keys()):
            continue  # already correctly-keyed → leave alone
        inner = val.get(key)
        if isinstance(inner, dict) and (own_keys & set(inner.keys())):
            report[key] = inner
            unwrapped.append(key)
    return unwrapped


def _schema_props_for(schema, key):
    node = (schema.get("properties") or {}).get(key)
    if isinstance(node, dict):
        return node
    return None


def check_block_shapes(report, schema):
    """Return a list of FATAL error strings for structurally-malformed required
    blocks. Only structural malformation is caught (never 'content looks thin'):
      - a required block that is not an object where the schema says object;
      - a block missing a schema-declared `required` sub-field;
      - a NON-EMPTY object whose keys share NOTHING with the schema's declared
        properties (an alien-keyed / mis-nested block).
    An empty {} correctly-typed block is allowed (a legitimately-empty dimension,
    e.g. runtime_surface with everything []). Runs AFTER unwrap_conflated_dim8."""
    errors = []
    for name in REASONED_REQUIRED:
        if name == "meta":
            continue
        node = _schema_props_for(schema, name)
        if node is None:
            continue
        types = _schema_types(node)
        if not types or "object" not in types:
            continue
        val = report.get(name)
        if not isinstance(val, dict):
            errors.append(
                f"block '{name}' 结构畸形：期望对象，实为 {_typename(val)}；"
                f"按对应 skill 重填 blocks/{name}.json")
            continue
        req = node.get("required")
        if isinstance(req, list):
            missing = [k for k in req if k not in val]
            if missing:
                errors.append(
                    f"block '{name}' 缺必填子字段 {'/'.join(missing)}；"
                    f"按对应 skill 重填 blocks/{name}.json")
                continue
        declared = set((node.get("properties") or {}).keys())
        if val and declared and not (declared & set(val.keys())):
            expect = "/".join(list(declared)[:5])
            got = "/".join(list(val.keys())[:5])
            errors.append(
                f"block '{name}' 结构畸形：期望键之一 {expect}…，实为 {got}；"
                f"疑似维度块被错误嵌套/张冠李戴，按对应 skill 重填 blocks/{name}.json")
    return errors


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

    def _add_warnings(msgs):
        meta = report.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            report["meta"] = meta
        warnings = list(meta.get("warnings") or [])
        for m in msgs:
            if m not in warnings:
                warnings.append(m)
        meta["warnings"] = warnings

    # 5) structural repair — deterministically UNWRAP the known double-nested
    #    dim-8 conflation FIRST, so the real inner content is exposed before
    #    coercion normalises its field types. Safe/deterministic → warn, not fatal.
    unwrapped = unwrap_conflated_dim8(report)
    if unwrapped:
        _add_warnings([f"unwrapped conflated dim-8 block: {name}" for name in unwrapped])

    # 6) schema-driven shape coercion (NON-fatal): repair recoverable model-shape
    #    drift (scalar↔array, object entry_points…) so the persisted report is
    #    contract-conformant. Runs AFTER unwrap so it sees the real dim-8 fields.
    fixes = coerce_report(report)
    if fixes:
        _add_warnings([f"shape coerced: {f['path']} {f['from']}→{f['to']}" for f in fixes])

    # 6b) HARD structural gate — alien-keyed / missing-required required blocks are
    #     fatal (no report written → the in-session agent re-fills the named block
    #     and re-runs). Schema unreadable → skip. Runs after unwrap so a recoverable
    #     nesting doesn't trip the gate.
    try:
        _schema = _load(SCHEMA_PATH)
    except Exception:
        _schema = None
    if isinstance(_schema, dict):
        errors.extend(check_block_shapes(report, _schema))

    # 7) validate required top-level keys present
    for k in REQUIRED_TOPLEVEL:
        if k not in report:
            errors.append(f"assembled report missing required top-level key '{k}'")

    if errors:
        return None, errors

    # 7b) NORMALIZE (single source of truth) — derive the authoritative
    #     harmony_adaptation.porting_class/feasibility/effort.level from the dim-12 buckets +
    #     unadaptable_apis (keeping the model's raw pick in porting_class_model), canonicalize
    #     code_partition, attach meta.harmony_warnings, and stamp meta.normalized_version. This
    #     is the SAME logic web/server.js used to run only at serve-time (never persisting) and
    #     export_xlsx.py re-implemented incompletely — running it here makes report.json born
    #     self-consistent so the panel, the Excel export, and any direct reader agree.
    try:
        _here = os.path.dirname(os.path.abspath(__file__))
        if _here not in sys.path:
            sys.path.insert(0, _here)
        import report_normalize
        report_normalize.normalize_report(report)
    except Exception as e:  # never fail assembly on a normalize hiccup — serve-time re-normalizes
        _add_warnings([f"normalize skipped: {e}"])

    # 8) atomic write (tmp + os.replace) so a reader never sees a half-written report
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
    ha = report.get("harmony_adaptation") or {}
    pc, pcm = ha.get("porting_class"), ha.get("porting_class_model")
    print(f"Wrote {out_path}")
    print(f"  top-level keys : {len(report)}")
    print(f"  primary lang   : {(report.get('languages') or {}).get('primary')}")
    print(f"  production code: {(cm.get('production') or {}).get('code')} lines")
    if pc:
        adj = f" (模型原判 {pcm}，已校正)" if pcm and pcm != pc else ""
        print(f"  porting_class  : {pc}{adj}")
    if coerced:
        print(f"  shape-coerced  : {len(coerced)} field(s) normalised to schema")
        for w in coerced:
            print(f"      - {w[len('shape coerced: '):]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
