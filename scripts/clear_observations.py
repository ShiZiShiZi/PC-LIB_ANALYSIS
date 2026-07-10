#!/usr/bin/env python3
"""One-off: empty meta.observations[] in every runs/**/report.json.

Clears the #/observations (模型观察/词表反哺) panel page, which is computed live
from each latest report's meta.observations. Sets the array to [] (keeps the key
so the report shape stays schema-valid) and leaves all other meta fields intact.
Back up runs/ first — it is gitignored.
"""
import glob
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs")

changed = 0
scanned = 0
for path in glob.glob(os.path.join(ROOT, "**", "report.json"), recursive=True):
    scanned += 1
    try:
        with open(path, encoding="utf-8") as f:
            rep = json.load(f)
    except Exception as e:
        print(f"skip (unreadable): {path}: {e}")
        continue
    meta = rep.get("meta")
    if not isinstance(meta, dict) or "observations" not in meta:
        continue
    if meta["observations"] == []:
        continue
    meta["observations"] = []
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    changed += 1

print(f"scanned {scanned} report.json, cleared observations in {changed}")
