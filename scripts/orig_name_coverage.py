#!/usr/bin/env python3
"""反向覆盖：5 个源表里的每个**原始名称**，是否被某个分析报告覆盖到（=已分析）。

输出 CSV（来源范围, 原始名称, 克隆地址, 是否已分析, 分析handle），直接筛「未分析」即答
「哪些原始名没被分析过」。匹配口径与 export_xlsx 的「原始名称」列一致（共用 scripts/orig_names）。

  python3 scripts/orig_name_coverage.py --runs runs/pc-lib-3456.0710 --out coverage.csv
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


def main(argv=None):
    ap = argparse.ArgumentParser(description="源表原始名 × 分析报告 覆盖表（找未分析的库）")
    ap.add_argument("--runs", default="runs", help="runs 根目录（默认 runs，递归扫所有分组；也可传单个分组目录）")
    ap.add_argument("--out", required=True, help="输出 CSV 路径")
    ap.add_argument("--config", default=None, help="源表配置（默认 .orig-name-tables.json）")
    args = ap.parse_args(argv)

    maps = ON.load(args.config)
    if not maps:
        print("no .orig-name-tables.json config found — nothing to do", file=sys.stderr)
        return 1

    # 递归找所有 lib 目录（含 report.json 的 run 的父目录）→ 覆盖所有分组
    lib_dirs = set()
    for dp, _dn, files in os.walk(args.runs):
        if "report.json" in files:
            lib_dirs.add(os.path.dirname(dp))    # dp=run 目录，父=lib 目录

    # 遍历报告 → analyzed 索引（canon / basename / norm-name → handle）
    an_canon, an_base, an_name = {}, {}, {}
    n_reports = 0
    for d in sorted(lib_dirs):
        lib = os.path.basename(d)
        rep = _latest_report(d)
        if not rep:
            continue
        n_reports += 1
        libd = rep.get("library") or {}
        c = ON._canon(libd.get("source_url") or libd.get("source_repo"))
        if c:
            an_canon.setdefault(c, lib)
            an_base.setdefault(c.split("/")[-1], lib)
        keys = [libd.get("package_name"), lib, libd.get("registry_name")]
        for arr in (libd.get("aliases"), libd.get("import_names")):
            if isinstance(arr, list):
                keys.extend(arr)
        for k in keys:
            nk = ON._norm(k)
            if nk:
                an_name.setdefault(nk, lib)

    # 每个源表原始名 → 是否命中某报告
    rows = []
    stat = {}
    for o in maps["originals"]:
        rng = o["range"]
        handle = None
        if o.get("canon") and o["canon"] in an_canon:
            handle = an_canon[o["canon"]]
        elif o.get("base") and o["base"] in an_base:
            handle = an_base[o["base"]]
        else:
            for nk in o.get("namekeys") or ():
                if nk in an_name:
                    handle = an_name[nk]
                    break
        analyzed = handle is not None
        url = o.get("url") or ""
        no_repo = (not url) or url.strip().startswith("无")
        status = "已分析" if analyzed else ("未分析(无仓)" if no_repo else "未分析")
        rows.append((rng, o["orig"], url, status, handle or ""))
        s = stat.setdefault(rng, [0, 0])
        s[0] += 1
        if analyzed:
            s[1] += 1

    rows.sort(key=lambda r: (r[0], r[3] != "已分析", r[1].lower()))
    # 去重（同一 range+原始名可能在表里重复）
    seen, uniq = set(), []
    for r in rows:
        k = (r[0], r[1])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)

    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["来源范围", "原始名称", "克隆地址", "是否已分析", "分析handle"])
        w.writerows(uniq)

    print(f"reports scanned: {n_reports} · originals(源表去重后): {len(uniq)} → {args.out}")
    print("覆盖率（各源表 已分析/总数）:")
    for rng in sorted(stat):
        tot, an = stat[rng]
        print(f"  {rng:8} {an}/{tot}  未分析 {tot - an}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
