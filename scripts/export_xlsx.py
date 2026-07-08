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

# Single source of truth for dim-9 derivations (porting_class/feasibility/effort.level) and
# code_partition canonicalization — shared with assemble_report.py and web/server.js. Used to
# normalize a legacy (unstamped) report on load so the export matches the panel exactly.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report_normalize  # noqa: E402

JOIN = "；"

# dim-9 难度等级 label. porting_class / feasibility / effort.level are single-sourced in
# report_normalize (persisted into report.json by assemble; a legacy report is normalized on load
# in _latest_report) — this module READS those persisted values, it no longer re-derives them.
_LEVEL_ZH = {"very_low": "极低", "low": "低", "medium": "中", "high": "高", "very_high": "极高"}


def _effort_days(ha: dict):
    e = (ha or {}).get("effort") or {}
    pd = e.get("person_days")
    if isinstance(pd, list) and len(pd) == 2:
        try:
            return [float(pd[0]), float(pd[1])]
        except (TypeError, ValueError):
            pass
    return None


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
    # A stamped report is already the single-source-of-truth form (assemble/migrate normalized it);
    # only upgrade a legacy/unstamped one in memory so the export matches the panel exactly.
    if isinstance(rep, dict) and not (isinstance(rep.get("meta"), dict) and rep["meta"].get("normalized_version")):
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
    dep, na = _dep_container(r), r.get("native_api", {})
    ha, be = r.get("harmony_adaptation", {}), r.get("build_env", {})
    return [[
        name,
        _g(r, "library", "source_url", default=""),
        _g(r, "library", "source_subpath", default=""),
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
        _g(cm, "arch_specific", "total", default=""),
        _part_loc(r, "reuse_direct"), _part_loc(r, "recompile_reuse"),
        _part_loc(r, "needs_adaptation"), _part_loc(r, "unadaptable"),
        _cap_flag(r, "gui"), _cap_flag(r, "rendering_3d"), _cap_flag(r, "media"), _cap_flag(r, "hardware"),
        _g(cm, "total", "total_lines"),
        t.get("test_files"),
        t.get("test_cases"),
        _g(r, "license", "spdx", default=""),
        _g(r, "license", "name", default=""),
        _g(r, "license", "confidence", default=""),
        _LIC_CAT_LABELS.get(_g(r, "license", "category", default=""), _g(r, "license", "category", default="")),
        dep.get("count"),
        len(dep.get("dependencies", []) or []),
        na.get("summary", ""),
        na.get("platform_dependence", ""),
        len(na.get("dynamic_libraries", []) or []),
        be.get("build_system", ""),
        be.get("language_standard", ""),
        be.get("runtime_version", ""),
        _join(be.get("platforms", []) or []),
        ha.get("porting_class") or "",
        ha.get("feasibility", ""),
        _LEVEL_ZH.get((ha.get("effort") or {}).get("level"), ""),
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
    "库名", "源地址", "子目录", "commit", "分析时间", "主语言", "语言列表", "生态", "绑定",
    "功能摘要", "领域", "目标用户", "总代码", "生产代码", "测试代码", "样例代码",
    "平台适配代码", "平台判断分支(处)", "汇编代码行",
    "直接复用LOC", "重编译复用LOC", "需适配LOC", "无法适配LOC",
    "GUI", "3D渲染", "媒体", "硬件", "总物理行", "测试文件", "测试用例", "License(SPDX)", "License名", "License置信度", "License性质",
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

_LIC_CAT_LABELS = {"commercial": "商业协议", "strong_copyleft": "强传染协议",
                   "weak_copyleft": "弱传染协议", "permissive": "友好协议",
                   "undeclared": "未声明协议"}


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


def rows_cloud_services(name, r):
    out = []
    for s in _g(r, "cloud_services", "services", default=[]) or []:
        if not s.get("vendor"):
            continue
        cats = "/".join(_CLOUD_CAT_LABELS.get(c, c) for c in (s.get("categories", []) or []))
        out.append([
            name, _VENDOR_LABELS.get(s.get("vendor"), s.get("vendor", "")),
            cats, s.get("confidence", ""),
            "/".join(s.get("via", []) or []), "/".join(s.get("endpoints", []) or []),
            _join(s.get("evidence", []) or []),
        ])
    return out


HEAD_CLOUD_SERVICES = ["库名", "厂商", "类别", "置信度", "来源", "云端域名", "证据"]


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
    for d in (_dep_container(r).get("dependencies") or []):
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
    if not isinstance(rs, dict):
        return []
    out = []
    for cat in ("network", "filesystem", "env_vars", "subprocess", "devices"):
        val = rs.get(cat)
        # 形状漂移：某些报告把 category 产成 dict/bool 概述而非条目列表 —— 跳过。
        if not isinstance(val, list):
            continue
        for it in val:
            if isinstance(it, dict):
                label = it.get("name") or it.get("detail") or ""
                out.append([name, cat, label, it.get("purpose", ""),
                            _join(it.get("evidence", []) or [])])
            elif it is not None:  # 条目偶发为字符串而非 dict
                out.append([name, cat, str(it), "", ""])
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


# ── code_partition (dim 12) + dim-9 critical deps / effort breakdown ─────────
_PART_LABELS = {"reuse_direct": "直接复用", "recompile_reuse": "重编译复用",
                "needs_adaptation": "需适配", "unadaptable": "无法适配"}
_EFFORT_COMP_LABELS = {"recompile": "重编/交叉编译", "api_adaptation": "平台API适配",
                       "gui": "GUI改造", "deps_porting": "依赖移植", "build_system": "构建系统",
                       "testing_verification": "测试验证", "packaging": "打包分发"}


# field-name tolerance (the agent occasionally emits total_loc/dir/note instead of loc/path/reason;
# the panel normalizes these serve-time, but this script reads report.json directly, so it must too)
def _bucket_loc(b):
    v = (b or {}).get("loc")
    if v is None:
        v = (b or {}).get("total_loc")
    if v is None:
        v = sum(int((m or {}).get("loc") or 0) for m in ((b or {}).get("modules") or []))
    return int(v or 0)


def _mod_path(m):
    m = m or {}
    return m.get("path") or m.get("dir") or m.get("module") or m.get("name") or ""


def _part_loc(r, cls):
    """Total LOC of one partition bucket class ('' when the block/bucket is absent)."""
    buckets = _g(r, "code_partition", "buckets", default=[]) or []
    hit = [_bucket_loc(b) for b in buckets if (b or {}).get("class") == cls]
    return sum(hit) if hit else ""


def rows_partition(name, r):
    out = []
    for b in _g(r, "code_partition", "buckets", default=[]) or []:
        cls = _PART_LABELS.get(b.get("class"), b.get("class", ""))
        mods = b.get("modules") or []
        for m in mods or [{}]:
            out.append([
                name, cls, _bucket_loc(b) or "", b.get("pct"),
                _mod_path(m), m.get("loc"), m.get("reason") or m.get("note") or "",
                _join(m.get("evidence", []) or []), b.get("basis", ""),
            ])
    return out


HEAD_PARTITION = ["库名", "分区", "桶LOC", "桶占比%", "模块", "模块LOC", "归类理由", "证据", "归类依据"]


def rows_critical_deps(name, r):
    out = []
    for c in _g(r, "harmony_adaptation", "critical_dependencies", default=[]) or []:
        pd = c.get("person_days_share") or []
        out.append([
            name, c.get("order"), c.get("name", ""), c.get("why", ""),
            _join(c.get("refs", []) or []),
            pd[0] if len(pd) == 2 else "", pd[1] if len(pd) == 2 else "",
        ])
    out.sort(key=lambda row: row[1] if isinstance(row[1], (int, float)) else 999)
    return out


HEAD_CRITICAL_DEPS = ["库名", "顺序", "依赖", "为何关键", "引用", "份额min(人天)", "份额max(人天)"]


def rows_effort_breakdown(name, r):
    out = []
    for b in _g(r, "harmony_adaptation", "effort", "breakdown", default=[]) or []:
        pd = b.get("person_days") or []
        out.append([
            name, _EFFORT_COMP_LABELS.get(b.get("component"), b.get("component", "")),
            pd[0] if len(pd) == 2 else "", pd[1] if len(pd) == 2 else "", b.get("basis", ""),
        ])
    return out


HEAD_EFFORT_BREAKDOWN = ["库名", "分项", "min(人天)", "max(人天)", "估算依据"]


SHEETS = [
    ("汇总", HEAD_OVERVIEW, rows_overview),
    ("功能分类", HEAD_CATEGORIES, rows_categories),
    ("语言分布", HEAD_LANGUAGES, rows_languages),
    ("代码分区", HEAD_PARTITION, rows_partition),
    ("平台适配代码量", HEAD_PLATFORM, rows_platform),
    ("平台判断分支", HEAD_PLATFORM_BRANCHES, rows_platform_branches),
    ("能力画像", HEAD_CAPABILITIES, rows_capabilities),
    ("云服务", HEAD_CLOUD_SERVICES, rows_cloud_services),
    ("鸿蒙权限", HEAD_PERMISSIONS, rows_permissions),
    ("依赖", HEAD_DEPS, rows_deps),
    ("系统平台API", HEAD_APIS, rows_apis),
    ("动态加载库", HEAD_DYNLIBS, rows_dynlibs),
    ("运行时交互面", HEAD_SURFACE, rows_surface),
    ("鸿蒙阻碍点", HEAD_BLOCKERS, rows_blockers),
    ("不支持API清单", HEAD_UNADAPTABLE, rows_unadaptable),
    ("关键路径依赖", HEAD_CRITICAL_DEPS, rows_critical_deps),
    ("工作量分项", HEAD_EFFORT_BREAKDOWN, rows_effort_breakdown),
    ("鸿蒙目标假设", HEAD_TARGET_ASSUMPTIONS, rows_target_assumptions),
    ("模型观察", HEAD_OBSERVATIONS, rows_observations),
]

HEAD_FILL = PatternFill("solid", fgColor="DDE6F0")
HEAD_FONT = Font(bold=True)
WRAP_COLS = {"功能摘要", "API摘要", "鸿蒙总结", "用途", "改造建议", "证据", "调用位置",
             "理由", "关键任务", "代码片段", "归类理由", "归类依据", "为何关键", "估算依据"}


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


def _write_sheet(ws, header, data):
    data = [[_cell(v) for v in row] for row in data]
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
            # 单个库某个 block 的形状漂移（off-schema）不应拖垮整包导出：
            # 该库在此 sheet 降级为跳过 + 告警，其余数据照常导出。
            try:
                data.extend(builder(name, rep))
            except Exception as e:  # noqa: BLE001 — degrade gracefully, keep exporting
                print(f"warn: skipped {name} in sheet {title!r}: {e}", file=sys.stderr)
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
