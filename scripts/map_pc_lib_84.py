#!/usr/bin/env python3
"""0714-84 批次专表：origin_fixed.tsv × runs/pc-lib-84 → 增强映射表。

复用 scripts/orig_names 的三级匹配（URL-canon → URL-base → 归一名，与 cov.csv 同口径），
扫本批分析报告，输出**保留用户补充的 开源库分类 / 主编程语言 两列**的聚焦映射表：
  原始名称, 开源库地址, 开源库分类, 主编程语言, 是否已分析, 分析handle

cov.csv（跨批次、固定 5 列）由 orig_name_coverage.py 生成；本脚本是它的「本批增强视图」，
不改动 cov.csv 与报告。

  python3 scripts/map_pc_lib_84.py \
    --table /Users/yt/task/三方库分析地图工程/pc-lib-analysis/0714-84/origin_fixed.tsv \
    --runs  runs/pc-lib-84 \
    --out   /Users/yt/task/三方库分析地图工程/pc-lib-analysis/0714-84/origin_mapped.csv
"""
import argparse
import csv
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import orig_names as ON  # noqa: E402


def _latest_report(lib_dir):
    try:
        runs = sorted(d for d in os.listdir(lib_dir)
                      if os.path.isfile(os.path.join(lib_dir, d, "report.json")))
    except OSError:
        return None
    if not runs:
        return None
    try:
        with open(os.path.join(lib_dir, runs[-1], "report.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def build_index(runs_root):
    """扫 runs_root 下所有报告 → (canon, base, norm-name) → handle 索引（first-wins，与 coverage 一致）。"""
    an_canon, an_base, an_name = {}, {}, {}
    lib_dirs = set()
    for dp, _dn, files in os.walk(runs_root):
        if "report.json" in files:
            lib_dirs.add(os.path.dirname(dp))
    n = 0
    for d in sorted(lib_dirs):
        lib = os.path.basename(d)
        rep = _latest_report(d)
        if not rep:
            continue
        n += 1
        L = rep.get("library") or {}
        c = ON._canon(L.get("source_url") or L.get("source_repo"))
        if c:
            an_canon.setdefault(c, lib)
            an_base.setdefault(c.split("/")[-1], lib)
        keys = [L.get("package_name"), lib, L.get("registry_name")]
        for arr in (L.get("aliases"), L.get("import_names")):
            if isinstance(arr, list):
                keys.extend(arr)
        for k in keys:
            nk = ON._norm(k)
            if nk:
                an_name.setdefault(nk, lib)
    return (an_canon, an_base, an_name), n


def match(url, name, idx):
    """URL-canon → URL-base → 归一名（与 orig_names.match / coverage 同顺序）。返回 handle 或 None。"""
    an_canon, an_base, an_name = idx
    c = ON._canon(url)
    if c and c in an_canon:
        return an_canon[c]
    if c:
        base = c.split("/")[-1]
        if base in an_base:
            return an_base[base]
    nk = ON._norm(name)
    if nk and nk in an_name:
        return an_name[nk]
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="0714-84 origin × runs/pc-lib-84 增强映射专表")
    ap.add_argument("--table", required=True, help="源表 origin_fixed.tsv（TAB：名/URL/分类/语言）")
    ap.add_argument("--runs", default="runs/pc-lib-84", help="本批 runs 根目录")
    ap.add_argument("--out", required=True, help="输出 CSV 路径")
    args = ap.parse_args(argv)

    idx, n = build_index(args.runs)
    rows = list(csv.reader(open(args.table, encoding="utf-8-sig"), delimiter="\t"))
    data = [r for r in rows[1:] if r and r[0].strip()]

    out = [["原始名称", "开源库地址", "开源库分类", "主编程语言", "是否已分析", "分析handle"]]
    an = 0
    for r in data:
        name = r[0].strip()
        url = (r[1].strip() if len(r) > 1 and r[1] else "")
        cat = (r[2].strip() if len(r) > 2 and r[2] else "")
        lang = (r[3].strip() if len(r) > 3 and r[3] else "")
        h = match(url, name, idx)
        out.append([name, url, cat, lang, "已分析" if h else "未分析", h or ""])
        if h:
            an += 1

    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        csv.writer(fh).writerows(out)
    print(f"reports scanned: {n} · originals: {len(data)} · 已分析 {an}/{len(data)} → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
