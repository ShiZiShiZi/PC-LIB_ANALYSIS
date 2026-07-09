#!/usr/bin/env python3
"""Export analyzed PC-library reports into ONE styled wide-table .xlsx.

Standalone (CI/offline) and also invoked by the web panel's /api/export endpoint.
Reads each library's LATEST run report.json under <runs>/<lib>/<ts>/report.json and
flattens the business-facing fields into a single "分析汇总" sheet with a two-level
header (grouped 一级/二级 表头), 微软雅黑 font, merged group headers and light styling —
one row per library.

Usage:
  python3 scripts/export_xlsx.py --runs <runs_dir> --out <path.xlsx> [--names a,b,c]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# Single source of truth for dim-9 derivations (porting_class/adaptation_assessment/effort.level) and
# code_partition canonicalization — shared with assemble_report.py and web/server.js. Used to
# normalize a legacy (unstamped) report on load so the export matches the panel exactly.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report_normalize  # noqa: E402

JOIN = "；"


# ── report loading (reused verbatim) ─────────────────────────────────────────

def _latest_report(lib_dir: str):
    """Return the parsed report.json of the newest run (ISO-timestamp dir) or None."""
    try:
        runs = sorted(
            d for d in os.listdir(lib_dir)
            if os.path.isfile(os.path.join(lib_dir, d, "report.json"))
        )
    except OSError:
        return None
    if not runs:
        return None
    path = os.path.join(lib_dir, runs[-1], "report.json")
    try:
        with open(path, encoding="utf-8") as fh:
            rep = json.load(fh)
    except (OSError, ValueError):
        return None
    # A report stamped at the CURRENT version is already the single-source-of-truth form; only
    # upgrade a legacy/unstamped/older-stamp one in memory so the export matches the panel exactly
    # (same version gate as web/server.js's /api/report serve path).
    stamp = rep.get("meta", {}).get("normalized_version") if isinstance(rep, dict) else None
    if isinstance(rep, dict) and (not isinstance(stamp, int) or stamp < report_normalize.NORMALIZED_VERSION):
        try:
            report_normalize.normalize_report(rep)
        except Exception:  # noqa: BLE001 — export must not fail on a normalize hiccup
            pass
    return rep


def _collect(runs_dir: str, names: set[str] | None):
    out = []
    try:
        libs = sorted(os.listdir(runs_dir))
    except OSError:
        return out
    for name in libs:
        lib_dir = os.path.join(runs_dir, name)
        if not os.path.isdir(lib_dir):
            continue
        if names and name not in names:
            continue
        rep = _latest_report(lib_dir)
        if rep is not None:
            out.append((name, rep))
    return out


# ── generic accessors (reused) ───────────────────────────────────────────────

def _g(obj, *path, default=None):
    """Safe nested get."""
    cur = obj
    for key in path:
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            return default
        if cur is None:
            return default
    return cur


def _dep_container(r):
    """`dependencies` 正常是 schema dict {count, dependencies:[...]}，但部分模型运行
    直接产出裸数组。统一返回 dict 视图。"""
    d = r.get("dependencies")
    if isinstance(d, list):
        return {"dependencies": d}
    return d if isinstance(d, dict) else {}


def _join(items, key=None):
    if not items:
        return ""
    if key is None:
        return JOIN.join(str(x) for x in items if x not in (None, ""))
    vals = []
    for it in items:
        v = it.get(key) if isinstance(it, dict) else None
        if v not in (None, ""):
            vals.append(str(v))
    return JOIN.join(vals)


def _cell(v):
    """把模型形状漂移里混入的非标量值（dict/list）强制转成可写字符串，避免单个异常
    字段（如 build_env.build_system 偶发产出对象而非字符串）拖垮整包导出。"""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, (list, tuple)):
        return _join([_cell(x) for x in v])
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return str(v)


def _effort_days(ha: dict):
    e = (ha or {}).get("effort") or {}
    pd = e.get("person_days")
    if isinstance(pd, list) and len(pd) == 2:
        try:
            return [float(pd[0]), float(pd[1])]
        except (TypeError, ValueError):
            pass
    return None


def _cap_flag(r, key):
    for s in _g(r, "capability_profile", "scenarios", default=[]) or []:
        if s.get("key") == key and s.get("present"):
            return "是"
    return ""


# code_partition (dim 12) bucket LOC — field-name tolerance mirrors the panel's serve-time
# normalization (the agent occasionally emits total_loc/dir instead of loc/path).
def _bucket_loc(b):
    v = (b or {}).get("loc")
    if v is None:
        v = (b or {}).get("total_loc")
    if v is None:
        v = sum(int((m or {}).get("loc") or 0) for m in ((b or {}).get("modules") or []))
    return int(v or 0)


def _part_loc(r, cls):
    """Total LOC of one partition bucket class ('' when the block/bucket is absent)."""
    buckets = _g(r, "code_partition", "buckets", default=[]) or []
    hit = [_bucket_loc(b) for b in buckets if (b or {}).get("class") == cls]
    return sum(hit) if hit else ""


# ── label maps ───────────────────────────────────────────────────────────────

_LIC_CAT_LABELS = {"commercial": "商业协议", "strong_copyleft": "强传染协议",
                   "weak_copyleft": "弱传染协议", "permissive": "友好协议",
                   "undeclared": "未声明协议"}
_LEVEL_ZH = {"very_low": "极低", "low": "低", "medium": "中", "high": "高", "very_high": "极高"}
_PLAT_LABELS = {"windows": "Windows", "macos": "macOS", "linux": "Linux", "posix": "POSIX"}
_VENDOR_LABELS = {
    "google_firebase": "Firebase (Google)", "aws": "AWS", "gcp": "Google Cloud",
    "azure": "Azure", "alibaba_cloud": "阿里云", "tencent_cloud": "腾讯云",
    "huawei_cloud": "华为云", "supabase": "Supabase", "sentry": "Sentry",
    "cloudflare": "Cloudflare", "unknown": "未知厂商",
}
_CLOUD_CAT_LABELS = {
    "auth": "登录鉴权", "cloud_storage": "云存储", "database": "云数据库",
    "cloud_functions": "云函数", "push": "推送", "messaging": "消息",
    "analytics": "分析统计", "crash_reporting": "崩溃上报", "remote_config": "远程配置",
    "maps": "地图", "ml_ai": "AI 云推理", "ads": "广告", "hosting": "托管",
}
_KIND_LABELS = {"library": "库", "application": "应用", "framework": "框架",
                "tool": "工具", "cli": "命令行", "service": "服务", "plugin": "插件"}
_HSTATUS_LABELS = {"available": "可用", "partial": "部分", "unavailable": "不可用",
                   "unknown": "未知", "restricted": "受限"}
# 移植分级 5 档 effective_class（派生）——与 app.js TOPO_STATUS 一致
_PCLASS_LABELS = {"no_adaptation": "无需适配", "recompile_only": "仅交叉编译",
                  "needs_adaptation": "需适配·全部可适配",
                  "needs_adaptation_platform_partial": "需适配·平台差异有不可适配点",
                  "needs_adaptation_core_partial": "需适配·核心有不可适配点"}
# adaptation_assessment.overall — 是否可适配总判（派生，替代旧 feasibility）
_OVERALL_LABELS = {"adaptable": "可适配", "adaptable_with_tailoring": "可适配（部分平台特性需裁剪）",
                   "core_blocked": "核心功能不完全可适配"}


# ── per-column value functions ───────────────────────────────────────────────

def _v_name(name, r):
    return _g(r, "library", "name", default="") or name


def _v_source(name, r):
    url = _g(r, "library", "source_url", default="") or ""
    sub = _g(r, "library", "source_subpath", default="")
    return f"{url}（子目录: {sub}）" if sub else url


def _v_kind_form(name, r):
    """library.kind → 中文基名 + 综合推断的形态（GUI/命令行/服务），如「应用·GUI」。"""
    kind = _g(r, "library", "kind", default="library") or "library"
    base = _KIND_LABELS.get(kind, kind)
    types = set()
    for e in _g(r, "build_env", "entry_points", default=[]) or []:
        if isinstance(e, dict) and e.get("type"):
            types.add(e["type"])
        # entry_points 偶发混入裸字符串 —— 忽略即可
    gui = _cap_flag(r, "gui") == "是"
    forms = []
    if gui:
        forms.append("GUI")
    if "console_script" in types or kind == "cli":
        forms.append("命令行")
    if "service" in types or "framework_startup" in types or kind == "service":
        forms.append("服务")
    if not forms and ("launcher" in types or "main" in types):
        forms.append("GUI" if gui else "命令行")
    seen = []
    for f in forms:
        if f not in seen:
            seen.append(f)
    return base + ("·" + "/".join(seen) if seen else "")


def _v_desc(name, r):
    return _g(r, "function_summary", "summary", default="")


def _v_eco(name, r):
    eco = _g(r, "library", "ecosystem", default="") or ""
    bindings = _g(r, "library", "bindings", default=[]) or []
    extra = _join([b for b in bindings if b and b != eco])
    return f"{eco}（+{extra}）" if extra else eco


def _v_primary(name, r):
    return _g(r, "languages", "primary", default="")


def _v_license_name(name, r):
    return _g(r, "license", "name", default="") or _g(r, "license", "spdx", default="")


def _v_license_cat(name, r):
    c = _g(r, "license", "category", default="")
    return _LIC_CAT_LABELS.get(c, c or "")


def _v_dep_count(name, r):
    return len(_dep_container(r).get("dependencies", []) or [])


def _v_code(field):
    def fn(name, r):
        return _g(r, "code_metrics", field, "code")
    return fn


def _v_plat(key):
    def fn(name, r):
        v = _g(r, "code_metrics", "platform_adaptation", "by_platform", key, "code")
        return v if v not in (None, "") else 0
    return fn


def _v_part(cls):
    def fn(name, r):
        return _part_loc(r, cls)
    return fn


def _v_cap(key):
    def fn(name, r):
        for s in _g(r, "capability_profile", "scenarios", default=[]) or []:
            if s.get("key") == key and s.get("present"):
                st = _HSTATUS_LABELS.get(s.get("harmony_status"), s.get("harmony_status") or "")
                return f"是·{st}" if st else "是"
        return "—"
    return fn


def _v_cloud_vendors(name, r):
    seen = []
    for s in _g(r, "cloud_services", "services", default=[]) or []:
        v = s.get("vendor")
        if not v:
            continue
        label = _VENDOR_LABELS.get(v, v)
        if label not in seen:
            seen.append(label)
    return JOIN.join(seen) if seen else "—"


def _v_cloud_cats(name, r):
    seen = []
    for s in _g(r, "cloud_services", "services", default=[]) or []:
        for c in s.get("categories", []) or []:
            label = _CLOUD_CAT_LABELS.get(c, c)
            if label not in seen:
                seen.append(label)
    return "/".join(seen) if seen else "—"


def _v_pclass(name, r):
    # 移植分级 = 5 档派生 effective_class（回退到 3 值 porting_class）
    c = (_g(r, "harmony_adaptation", "adaptation_assessment", "effective_class", default="")
         or _g(r, "harmony_adaptation", "porting_class", default=""))
    return _PCLASS_LABELS.get(c, c or "")


def _v_overall(name, r):
    o = _g(r, "harmony_adaptation", "adaptation_assessment", "overall", default="")
    return _OVERALL_LABELS.get(o, o or "")


def _v_level(name, r):
    lv = _g(r, "harmony_adaptation", "effort", "level", default="")
    return _LEVEL_ZH.get(lv, lv or "")


def _v_days(name, r):
    d = _effort_days(r.get("harmony_adaptation") or {})
    if not d:
        return ""
    lo, hi = d
    fmt = lambda x: (str(int(x)) if float(x).is_integer() else str(x))
    return f"{fmt(lo)}–{fmt(hi)}"


def _v_summary(name, r):
    return _g(r, "harmony_adaptation", "summary", default="")


# ── column spec (一级 → 二级) ────────────────────────────────────────────────
# Each entry: (top_title | None, [(sub_title, value_fn), ...]).
# top_title None → standalone column, header merged vertically across the two header rows.
GROUPS = [
    ("基本信息", [
        ("名称", _v_name), ("源码仓地址", _v_source), ("类型", _v_kind_form),
        ("描述", _v_desc), ("生态", _v_eco), ("主语言", _v_primary),
    ]),
    ("开源协议", [("协议类型", _v_license_name), ("协议友好类型", _v_license_cat)]),
    (None, [("依赖库数量", _v_dep_count)]),
    ("代码量(行)", [
        ("总体", _v_code("total")), ("生产", _v_code("production")),
        ("测试", _v_code("test")), ("样例", _v_code("example")),
    ]),
    ("平台适配代码量(行)", [
        ("Windows", _v_plat("windows")), ("macOS", _v_plat("macos")),
        ("Linux", _v_plat("linux")), ("POSIX", _v_plat("posix")),
    ]),
    ("代码分区(迁移复用性·工作量底座, LOC)", [
        ("直接复用", _v_part("reuse_direct")), ("重编译复用", _v_part("recompile_reuse")),
        ("需适配", _v_part("needs_adaptation")), ("无法适配", _v_part("unadaptable")),
    ]),
    ("能力画像", [
        ("GUI界面", _v_cap("gui")), ("3D渲染", _v_cap("rendering_3d")),
        ("媒体", _v_cap("media")), ("硬件/设备", _v_cap("hardware")),
    ]),
    ("云服务", [("厂商", _v_cloud_vendors), ("用途", _v_cloud_cats)]),
    ("鸿蒙适配评估", [
        ("移植分级", _v_pclass), ("是否可适配", _v_overall), ("难度", _v_level),
        ("工作量(人天)", _v_days), ("评估总结", _v_summary),
    ]),
]

# per-column presentation overrides keyed by sub-title
WRAP_WIDTH = {"描述": 58, "评估总结": 58, "源码仓地址": 42, "用途": 22}

# ── styling ──────────────────────────────────────────────────────────────────
FONT_NAME = "微软雅黑"
_TOP_FILL = PatternFill("solid", fgColor="B7C9E2")   # 一级表头（深）
_SUB_FILL = PatternFill("solid", fgColor="DDE6F0")    # 二级表头（浅）
_PART_TOP_FILL = PatternFill("solid", fgColor="E8D9B5")  # 代码分区组用暖色区分
_PART_SUB_FILL = PatternFill("solid", fgColor="F3ECD8")
_ZEBRA_FILL = PatternFill("solid", fgColor="F7F9FC")
_THIN = Side(style="thin", color="B0B8C4")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_H_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
_CELL_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=False)
_WRAP_ALIGN = Alignment(horizontal="left", vertical="top", wrap_text=True)


def _flat_columns():
    """Flatten GROUPS into ordered [(sub_title, fn)] and remember group spans."""
    cols, spans, ci = [], [], 1
    for top, subs in GROUPS:
        start = ci
        for sub, fn in subs:
            cols.append((sub, fn))
            ci += 1
        spans.append((top, start, ci - 1))   # inclusive col range (1-based)
    return cols, spans


def build(entries, out_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "分析汇总"
    cols, spans = _flat_columns()
    ncols = len(cols)

    # header rows 1 (一级) + 2 (二级)
    for top, c1, c2 in spans:
        is_part = top and top.startswith("代码分区")
        top_fill = _PART_TOP_FILL if is_part else _TOP_FILL
        sub_fill = _PART_SUB_FILL if is_part else _SUB_FILL
        if top is None:                       # standalone → vertical merge over both header rows
            ws.merge_cells(start_row=1, start_column=c1, end_row=2, end_column=c1)
            cell = ws.cell(row=1, column=c1, value=cols[c1 - 1][0])
            cell.fill = sub_fill
        else:
            if c2 > c1:
                ws.merge_cells(start_row=1, start_column=c1, end_row=1, end_column=c2)
            tcell = ws.cell(row=1, column=c1, value=top)
            for c in range(c1, c2 + 1):
                ws.cell(row=1, column=c).fill = top_fill
            for c in range(c1, c2 + 1):
                scell = ws.cell(row=2, column=c, value=cols[c - 1][0])
                scell.fill = sub_fill
        # (data written below)

    # header styling
    for row in (1, 2):
        for c in range(1, ncols + 1):
            cell = ws.cell(row=row, column=c)
            cell.font = Font(name=FONT_NAME, bold=True, size=11)
            cell.alignment = _H_ALIGN
            cell.border = _BORDER
    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 22

    # data rows (start row 3)
    for ri, (name, rep) in enumerate(entries):
        r = 3 + ri
        for ci, (sub, fn) in enumerate(cols, start=1):
            try:
                val = _cell(fn(name, rep))
            except Exception as e:  # noqa: BLE001 — one bad field must not sink the row
                print(f"warn: {name} 列 {sub!r}: {e}", file=sys.stderr)
                val = ""
            cell = ws.cell(row=r, column=ci, value=val)
            cell.font = Font(name=FONT_NAME, size=10)
            cell.border = _BORDER
            cell.alignment = _WRAP_ALIGN if sub in WRAP_WIDTH else _CELL_ALIGN
            if ri % 2 == 1 and sub not in WRAP_WIDTH:
                cell.fill = _ZEBRA_FILL

    ws.freeze_panes = "C3"                     # freeze both header rows + 名称/源码仓 两列
    last_col = get_column_letter(ncols)
    ws.auto_filter.ref = f"A2:{last_col}{ws.max_row}"

    # column widths
    for ci, (sub, fn) in enumerate(cols, start=1):
        letter = get_column_letter(ci)
        if sub in WRAP_WIDTH:
            ws.column_dimensions[letter].width = WRAP_WIDTH[sub]
            continue
        longest = len(str(sub))
        # measure from the already-rendered cells (rows 3..)
        for r in range(3, ws.max_row + 1):
            v = ws.cell(row=r, column=ci).value
            if v is not None:
                longest = max(longest, min(len(str(v)), 24))
        ws.column_dimensions[letter].width = max(8, min(longest + 2, 26))

    wb.save(out_path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Export library reports to a styled wide-table .xlsx")
    ap.add_argument("--runs", required=True, help="runs/ directory")
    ap.add_argument("--out", required=True, help="output .xlsx path")
    ap.add_argument("--names", default="", help="comma-separated library names (default: all)")
    args = ap.parse_args(argv)

    names = {n.strip() for n in args.names.split(",") if n.strip()} or None
    entries = _collect(args.runs, names)
    if not entries:
        print("no analyzed libraries found", file=sys.stderr)
        return 2
    build(entries, args.out)
    print(f"exported {len(entries)} libraries -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
