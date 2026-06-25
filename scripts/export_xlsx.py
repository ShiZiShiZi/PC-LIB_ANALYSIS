#!/usr/bin/env python3
"""Export analyzed PC-library reports into one summary .xlsx workbook.

Standalone (CI/offline) and also invoked by the web panel's /api/export endpoint.
Reads each library's LATEST run report.json under <runs>/<lib>/<ts>/report.json and
flattens every field into a normalized multi-sheet workbook: one "汇总" row per
library plus detail sheets (one row per nested item, keyed by library name).

Usage:
  python3 scripts/export_xlsx.py --runs <runs_dir> --out <path.xlsx> [--names a,b,c]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

JOIN = "；"

# dim-9 difficulty rubric (mirrors web/server.js deriveDifficultyLevel/effortDays) so the
# standalone export shows the derived 难度等级 + person_days even for legacy reports.
_LEVEL_ZH = {"very_low": "极低", "low": "低", "medium": "中", "high": "高", "very_high": "极高"}
_RANK_LEVEL = ["very_low", "low", "medium", "high", "very_high"]
_CLASS_FLOOR = {"no_adaptation": 0, "recompile_only": 1, "needs_adaptation_full": 2,
                "needs_adaptation_partial": 3, "infeasible": 4}


def _effort_days(ha: dict):
    e = (ha or {}).get("effort") or {}
    pd = e.get("person_days")
    if isinstance(pd, list) and len(pd) == 2:
        try:
            return [float(pd[0]), float(pd[1])]
        except (TypeError, ValueError):
            pass
    return None


def _days_bucket(hi) -> int:
    try:
        d = float(hi)
    except (TypeError, ValueError):
        return 0
    if d <= 2:
        return 0
    if d <= 5:
        return 1
    if d <= 15:
        return 2
    if d <= 40:
        return 3
    return 4


def _difficulty_level(ha: dict):
    cls = (ha or {}).get("porting_class")
    days = _effort_days(ha)
    if (ha or {}).get("effort", {}).get("level"):
        return _LEVEL_ZH.get(ha["effort"]["level"], ha["effort"]["level"])
    if not cls:
        return ""
    floor = _CLASS_FLOOR.get(cls, 0)
    rank = max(floor, _days_bucket(days[1] if days else 0))
    return _LEVEL_ZH[_RANK_LEVEL[rank]]


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
            return json.load(fh)
    except (OSError, ValueError):
        return None


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


def _cat_names(categories):
    """function_summary.categories -> list of (name, evidence) tolerant of shapes."""
    out = []
    for c in categories or []:
        if isinstance(c, dict):
            name = c.get("name") or c.get("category") or c.get("capability") or ""
            ev = c.get("evidence") or []
            out.append((str(name), _join(ev)))
        else:
            out.append((str(c), ""))
    return out


# ── per-sheet row builders ──────────────────────────────────────────────────

def rows_overview(name, r):
    cm, t = r.get("code_metrics", {}), r.get("tests", {})
    dep, na = r.get("dependencies", {}), r.get("native_api", {})
    ha, be = r.get("harmony_adaptation", {}), r.get("build_env", {})
    return [[
        name,
        _g(r, "library", "source_url", default=""),
        _g(r, "library", "commit", default=""),
        _g(r, "library", "analyzed_at", default=""),
        _g(r, "languages", "primary", default=""),
        _join(_g(r, "languages", "all", default=[])),
        _g(r, "library", "ecosystem", default=""),
        _join(_g(r, "library", "bindings", default=[])),
        _g(r, "function_summary", "summary", default=""),
        _g(r, "function_summary", "domain", default=""),
        _g(r, "function_summary", "target_users", default=""),
        _g(cm, "total", "code"),
        _g(cm, "production", "code"),
        _g(cm, "test", "code"),
        _g(cm, "example", "code"),
        _g(cm, "platform_adaptation", "total", default=""),
        _g(cm, "platform_branches", "total", default=""),
        _cap_flag(r, "gui"), _cap_flag(r, "rendering_3d"), _cap_flag(r, "media"), _cap_flag(r, "hardware"),
        _g(cm, "total", "total_lines"),
        t.get("test_files"),
        t.get("test_cases"),
        _g(r, "license", "spdx", default=""),
        _g(r, "license", "name", default=""),
        _g(r, "license", "confidence", default=""),
        dep.get("count"),
        len(dep.get("dependencies", []) or []),
        na.get("summary", ""),
        na.get("platform_dependence", ""),
        len(na.get("dynamic_libraries", []) or []),
        be.get("build_system", ""),
        be.get("language_standard", ""),
        be.get("runtime_version", ""),
        _join(be.get("platforms", []) or []),
        ha.get("porting_class", ""),
        ha.get("feasibility", ""),
        _difficulty_level(ha),
        (_effort_days(ha) or ["", ""])[0],
        (_effort_days(ha) or ["", ""])[1],
        ha.get("confidence", "") or _g(r, "meta", "confidence_overall", default=""),
        ha.get("recommended_path", ""),
        ha.get("summary", ""),
        len(ha.get("blockers", []) or []),
        len(ha.get("unadaptable_apis", []) or []),
        _join(ha.get("key_tasks", []) or []),
        _g(r, "meta", "confidence_overall", default=""),
    ]]


HEAD_OVERVIEW = [
    "库名", "源地址", "commit", "分析时间", "主语言", "语言列表", "生态", "绑定",
    "功能摘要", "领域", "目标用户", "总代码", "生产代码", "测试代码", "样例代码",
    "平台适配代码", "平台判断分支(处)", "GUI", "3D渲染", "媒体", "硬件", "总物理行", "测试文件", "测试用例", "License(SPDX)", "License名", "License置信度",
    "运行时依赖数", "依赖总数", "API摘要", "平台依赖", "动态库数", "构建系统",
    "语言标准", "运行时版本", "支持平台", "移植分级", "鸿蒙可行性", "鸿蒙难度",
    "工作量min(人天)", "工作量max(人天)", "鸿蒙置信度",
    "推荐路径", "鸿蒙总结", "阻碍点数", "不支持API数", "关键任务", "整体置信度",
]


def rows_categories(name, r):
    return [[name, cat, ev] for cat, ev in _cat_names(_g(r, "function_summary", "categories", default=[]))]


HEAD_CATEGORIES = ["库名", "功能分类", "证据"]


def rows_languages(name, r):
    out = []
    for b in _g(r, "languages", "breakdown", default=[]) or []:
        p, t, e = b.get("production", {}), b.get("test", {}), b.get("example", {})
        out.append([
            name, b.get("language", ""), b.get("files"), b.get("code"),
            p.get("code"), p.get("files"), t.get("code"), t.get("files"),
            e.get("code"), e.get("files"), b.get("pct"),
        ])
    return out


HEAD_LANGUAGES = [
    "库名", "语言", "文件", "代码", "生产代码", "生产文件", "测试代码", "测试文件",
    "样例代码", "样例文件", "占比%",
]


_PLAT_LABELS = {"windows": "Windows", "macos": "macOS", "linux": "Linux", "posix": "POSIX"}


def rows_platform(name, r):
    by = _g(r, "code_metrics", "platform_adaptation", "by_platform", default={}) or {}
    out = []
    for k, v in by.items():
        v = v or {}
        out.append([
            name, _PLAT_LABELS.get(k, k), v.get("code"), v.get("files"),
            "/".join(v.get("macros", []) or []),
        ])
    return out


HEAD_PLATFORM = ["库名", "平台", "代码行", "文件数", "命中编译宏"]


_BRANCH_LANG_LABELS = {"python": "Python", "javascript": "JS/TS", "java": "Java/Kotlin",
                       "go": "Go", "rust": "Rust", "csharp": "C#"}


def rows_platform_branches(name, r):
    out = []
    for s in _g(r, "code_metrics", "platform_branches", "samples", default=[]) or []:
        lang = s.get("language", "")
        out.append([
            name, _BRANCH_LANG_LABELS.get(lang, lang), s.get("file", ""),
            s.get("line", ""), s.get("text", ""),
        ])
    return out


HEAD_PLATFORM_BRANCHES = ["库名", "语言", "文件", "行号", "代码片段"]


_CAP_LABELS = {"gui": "GUI 界面", "rendering_3d": "3D 渲染", "rendering_2d": "2D 绘制",
               "media": "媒体", "hardware": "硬件/设备"}


def rows_capabilities(name, r):
    out = []
    for s in _g(r, "capability_profile", "scenarios", default=[]) or []:
        if not s.get("present"):
            continue
        out.append([
            name, _CAP_LABELS.get(s.get("key"), s.get("key", "")),
            "/".join(s.get("kind", []) or []),
            "是" if s.get("specific_hardware") else "",
            s.get("harmony_status", ""), "/".join(s.get("via", []) or []),
            s.get("adaptation", ""), _join(s.get("evidence", []) or []),
        ])
    return out


HEAD_CAPABILITIES = ["库名", "场景", "具体技术", "特定硬件", "鸿蒙状态", "来源", "适配说明", "证据"]


def rows_permissions(name, r):
    out = []
    for p in _g(r, "harmony_adaptation", "required_permissions", default=[]) or []:
        out.append([
            name, p.get("permission", ""), p.get("source_capability", ""),
            p.get("harmony_status", ""), p.get("reason", ""),
            _join(p.get("evidence", []) or []),
        ])
    return out


HEAD_PERMISSIONS = ["库名", "权限", "来源场景", "鸿蒙可授予", "原因", "证据"]


def _cap_flag(r, key):
    for s in _g(r, "capability_profile", "scenarios", default=[]) or []:
        if s.get("key") == key and s.get("present"):
            return "是"
    return ""


def rows_deps(name, r):
    out = []
    for d in _g(r, "dependencies", "dependencies", default=[]) or []:
        out.append([
            name, d.get("name", ""), d.get("ecosystem", ""), d.get("scope", ""),
            d.get("version", ""), d.get("locality", ""), d.get("acquisition", ""),
            d.get("source", ""), d.get("purpose", ""), _join(d.get("declared_in", []) or []),
            _join(d.get("used_symbols", []) or []),
        ])
    return out


HEAD_DEPS = [
    "库名", "名称", "生态", "作用域", "版本", "本地/远端", "获取方式", "来源", "用途",
    "声明位置", "调用符号",
]


def rows_apis(name, r):
    out = []
    for g in _g(r, "native_api", "groups", default=[]) or []:
        gtype, cat, plat = g.get("type", ""), g.get("category", ""), g.get("platform", "")
        apis = g.get("apis") or []
        if apis:
            for a in apis:
                out.append([
                    name, gtype, cat, plat, a.get("name", ""), a.get("purpose", ""),
                    a.get("count"), "是" if a.get("conditional") else "",
                    _join(a.get("evidence", []) or []),
                ])
        else:  # legacy: only flat symbols
            out.append([name, gtype, cat, plat, _join(g.get("symbols", []) or []),
                        "", None, "", ""])
    return out


HEAD_APIS = [
    "库名", "组类型", "类别", "平台", "API", "用途", "调用次数", "条件编译", "调用位置",
]


def rows_dynlibs(name, r):
    out = []
    for d in _g(r, "native_api", "dynamic_libraries", default=[]) or []:
        out.append([
            name, d.get("name", ""), d.get("mechanism", ""), d.get("acquisition", ""),
            d.get("source", ""), d.get("purpose", ""),
        ])
    return out


HEAD_DYNLIBS = ["库名", "名称", "加载机制", "获取方式", "来源", "用途"]


def rows_surface(name, r):
    rs = r.get("runtime_surface", {})
    out = []
    for cat in ("network", "filesystem", "env_vars", "subprocess", "devices"):
        for it in rs.get(cat, []) or []:
            label = it.get("name") or it.get("detail") or ""
            out.append([name, cat, label, it.get("purpose", ""),
                        _join(it.get("evidence", []) or [])])
    return out


HEAD_SURFACE = ["库名", "类别", "名称/明细", "用途", "证据"]


def rows_blockers(name, r):
    out = []
    for b in _g(r, "harmony_adaptation", "blockers", default=[]) or []:
        out.append([
            name, b.get("id", ""), b.get("issue", ""), b.get("severity", ""),
            b.get("adaptability", ""), b.get("category", ""),
            b.get("source_dimension", ""), b.get("harmony_status", ""),
            b.get("remediation", ""), _join(b.get("caused_by", []) or []),
            _join(b.get("manifests_as", []) or []), _join(b.get("evidence", []) or []),
        ])
    return out


HEAD_BLOCKERS = [
    "库名", "ID", "阻碍点", "严重度", "可适配性", "类别", "来源维度", "鸿蒙状态",
    "改造建议", "根因(caused_by)", "体现为(manifests_as)", "证据",
]


def rows_unadaptable(name, r):
    out = []
    for u in _g(r, "harmony_adaptation", "unadaptable_apis", default=[]) or []:
        out.append([
            name, u.get("id", ""), u.get("api", ""), u.get("public_entry", ""), u.get("reason", ""),
            u.get("blocking_native_api", ""), u.get("category", ""),
            _join(u.get("caused_by", []) or []), _join(u.get("evidence", []) or []),
        ])
    return out


HEAD_UNADAPTABLE = [
    "库名", "ID", "不支持API", "公共入口", "原因", "阻碍根源API", "类别", "根因(caused_by)", "证据",
]


def rows_target_assumptions(name, r):
    out = []
    for a in _g(r, "harmony_adaptation", "target_assumptions", default=[]) or []:
        out.append([
            name, a.get("id", ""), a.get("capability", ""), "是" if a.get("required") else "否",
            a.get("target_status", ""), a.get("impact", ""), a.get("source", ""),
        ])
    return out


HEAD_TARGET_ASSUMPTIONS = [
    "库名", "ID", "目标能力", "必需", "目标状态", "影响", "来源",
]


def rows_observations(name, r):
    out = []
    for o in _g(r, "meta", "observations", default=[]) or []:
        out.append([
            name, o.get("dimension", ""), o.get("field", ""), o.get("kind", ""),
            o.get("value", ""), o.get("rationale", ""),
        ])
    return out


HEAD_OBSERVATIONS = ["库名", "维度", "字段", "类型", "取值", "理由"]


SHEETS = [
    ("汇总", HEAD_OVERVIEW, rows_overview),
    ("功能分类", HEAD_CATEGORIES, rows_categories),
    ("语言分布", HEAD_LANGUAGES, rows_languages),
    ("平台适配代码量", HEAD_PLATFORM, rows_platform),
    ("平台判断分支", HEAD_PLATFORM_BRANCHES, rows_platform_branches),
    ("能力画像", HEAD_CAPABILITIES, rows_capabilities),
    ("鸿蒙权限", HEAD_PERMISSIONS, rows_permissions),
    ("依赖", HEAD_DEPS, rows_deps),
    ("系统平台API", HEAD_APIS, rows_apis),
    ("动态加载库", HEAD_DYNLIBS, rows_dynlibs),
    ("运行时交互面", HEAD_SURFACE, rows_surface),
    ("鸿蒙阻碍点", HEAD_BLOCKERS, rows_blockers),
    ("不支持API清单", HEAD_UNADAPTABLE, rows_unadaptable),
    ("鸿蒙目标假设", HEAD_TARGET_ASSUMPTIONS, rows_target_assumptions),
    ("模型观察", HEAD_OBSERVATIONS, rows_observations),
]

HEAD_FILL = PatternFill("solid", fgColor="DDE6F0")
HEAD_FONT = Font(bold=True)
WRAP_COLS = {"功能摘要", "API摘要", "鸿蒙总结", "用途", "改造建议", "证据", "调用位置",
             "理由", "关键任务", "代码片段"}


def _write_sheet(ws, header, data):
    ws.append(header)
    for c in ws[1]:
        c.font = HEAD_FONT
        c.fill = HEAD_FILL
        c.alignment = Alignment(vertical="center")
    for row in data:
        ws.append(row)
    ws.freeze_panes = "A2"
    last_col = get_column_letter(len(header))
    ws.auto_filter.ref = f"A1:{last_col}{ws.max_row}"
    # column widths (cap), wrap long-text columns
    for idx, title in enumerate(header, start=1):
        letter = get_column_letter(idx)
        longest = len(str(title))
        for row in data:
            v = row[idx - 1] if idx - 1 < len(row) else None
            if v is not None:
                longest = max(longest, min(len(str(v)), 60))
        if title in WRAP_COLS:
            ws.column_dimensions[letter].width = 48
            for row_cells in ws.iter_rows(min_row=2, min_col=idx, max_col=idx):
                row_cells[0].alignment = Alignment(wrap_text=True, vertical="top")
        else:
            ws.column_dimensions[letter].width = max(8, min(longest + 2, 40))


def build(entries, out_path):
    wb = Workbook()
    wb.remove(wb.active)
    for title, header, builder in SHEETS:
        ws = wb.create_sheet(title)
        data = []
        for name, rep in entries:
            data.extend(builder(name, rep))
        _write_sheet(ws, header, data)
    wb.save(out_path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Export library reports to a summary .xlsx")
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
