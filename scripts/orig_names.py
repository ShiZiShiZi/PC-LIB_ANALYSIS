#!/usr/bin/env python3
"""把分析报告(handle=克隆仓名)映射回**原始名称**。

用户流程：原始名 → (AI 补齐) → clone 地址 → 克隆分析(handle=仓名)。5 个源表记录
「原始名 → clone 地址/名称」；本模块反向匹配：
  - 4 个 URL 表：报告 library.source_url 归一(owner/repo, host 无关) ↔ 表 clone 地址。
  - nodejs xlsx(无 URL)：报告 package_name/handle/aliases 归一 ↔ 表名字列。

被 export_xlsx.py（加「原始名称」列）与 orig_name_coverage.py（未分析清单）共用。
源表路径在 .orig-name-tables.json（gitignored，本地）。
"""
import csv
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(_HERE, "..", ".orig-name-tables.json")


def _canon(url):
    """host-无关 owner/repo（小写），剥 .git / 尾斜杠 / 「（子路径…)」/#subpath / 尾部注释。"""
    if not url:
        return None
    u = str(url).strip()
    if u in ("无", "-", "") or u.startswith("无"):   # 「无（商业闭源…）」
        return None
    u = re.split(r"[\s（(]", u, 1)[0].strip()          # 去掉地址后的中文/空白注释
    u = u.split("#", 1)[0]
    m = re.search(r"(?:https?://|git://|git@|ssh://[^/]+/)([^/:]+)[/:](.+)", u, re.I)
    if not m:
        return None
    path = m.group(2)
    path = re.sub(r"\.git$", "", path).strip("/").lower()
    return path or None


def _norm(name):
    """名字归一：小写、剥 npm scope(@x/)、剥非字母数字。"""
    if not name:
        return None
    s = re.sub(r"^@[^/]+/", "", str(name).strip().lower())
    s = re.sub(r"[^a-z0-9]", "", s)
    return s or None


def _read_delim(path, sep, name_col, url_col):
    """读 CSV/TSV → [(original_name, url_raw), ...]（跳表头）。"""
    out = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh, delimiter=sep)
        rows = list(rd)
    for r in rows[1:]:
        if not r:
            continue
        name = (r[name_col].strip() if len(r) > name_col and r[name_col] else "")
        url = (r[url_col].strip() if len(r) > url_col and r[url_col] else "")
        if name:
            out.append((name, url))
    return out


def _read_xlsx_names(path, orig_headers, alt_headers, originals_sheets=None, url_headers=None):
    """读 nodejs xlsx → [(original_name, [name_keys...], is_original, url), ...]。
    name_keys=原始名+归一后名等所有名列（供匹配）；is_original=该行属于「原始清单表」（供反向覆盖，
    避免全量依赖树 5000+ 行灌进未分析清单）；url=按 url_headers 取到的克隆地址（首个非空列，无则 ""）。
    originals_sheets 为 None ⇒ 所有 sheet 都算 original。"""
    from openpyxl import load_workbook
    out = []
    wb = load_workbook(path, read_only=True, data_only=True)
    for ws in wb.worksheets:
        is_orig_sheet = (originals_sheets is None) or (ws.title in originals_sheets)
        rows = ws.iter_rows(values_only=True)
        try:
            hdr = [str(c or "") for c in next(rows)]
        except StopIteration:
            continue
        oi = next((i for i, h in enumerate(hdr) if h in orig_headers), None)
        ais = [i for i, h in enumerate(hdr) if h in alt_headers]
        uis = [i for i, h in enumerate(hdr) if h in (url_headers or [])]   # 克隆地址列（按 url_headers 顺序）
        keycols = ([oi] if oi is not None else []) + ais
        if not keycols:
            keycols = [0]                      # 兜底：第一列
        oi = oi if oi is not None else keycols[0]
        for r in rows:
            if not r or oi >= len(r) or not r[oi]:
                continue
            orig = str(r[oi]).strip()
            keys = [str(r[i]).strip() for i in keycols if i < len(r) and r[i]]
            url = next((str(r[i]).strip() for i in uis
                        if i < len(r) and r[i] and str(r[i]).strip()), "")
            if orig:
                out.append((orig, keys, is_orig_sheet, url))
    wb.close()
    return out


def load(config_path=None):
    """载 5 源表 → 匹配用 maps + originals(反向覆盖用)。配置/文件缺失时优雅跳过。返回 None 表示无配置。"""
    cfg_path = config_path or DEFAULT_CONFIG
    if not os.path.isfile(cfg_path):
        return None
    try:
        with open(cfg_path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except Exception:
        return None
    url_map, base_map, name_map, originals = {}, {}, {}, []
    for t in cfg.get("tables", []):
        path = t.get("path")
        rng = t.get("range", "?")
        if not path or not os.path.isfile(path):
            continue
        try:
            if t.get("kind") == "xlsx":
                for orig, keys, is_orig, url in _read_xlsx_names(
                        path, t.get("orig_headers", ["原始名"]), t.get("alt_headers", []),
                        t.get("originals_sheets"), t.get("url_headers")):
                    nks = {k for k in (_norm(x) for x in keys) if k}
                    for nk in nks:
                        name_map.setdefault(nk, (orig, rng))       # 匹配用：全量名字
                    # url 只用于 cov.csv 输出（克隆地址）。不进 url_map/base_map、canon/base 留 None：
                    # nodejs 单仓多包(版本变体/monorepo 兄弟)canon 大量撞车，一旦参与匹配会给 export
                    # 「原始名称」列产生错名(nan→1to2、undici→undici-types…)，故只按名匹配（既有口径）。
                    if is_orig:                                    # 覆盖用：仅「原始清单」表，避免依赖树噪声
                        originals.append({"orig": orig, "range": rng, "canon": None, "base": None, "namekeys": nks, "url": url})
            else:
                for name, url in _read_delim(path, t.get("sep", ","), t.get("name_col", 0), t.get("url_col", 1)):
                    c = _canon(url)
                    base = c.split("/")[-1] if c else None
                    if c:
                        url_map.setdefault(c, (name, rng))
                    if base:
                        base_map.setdefault(base, (name, rng))
                    nk = _norm(name)
                    if nk:                                      # 名 fallback（无 source_url 的报告靠名匹配）
                        name_map.setdefault(nk, (name, rng))
                    originals.append({"orig": name, "range": rng, "canon": c, "base": base,
                                      "namekeys": ({nk} if nk else set()), "url": url})
        except Exception:
            continue
    return {"url_map": url_map, "base_map": base_map, "name_map": name_map, "originals": originals}


def match(library, handle, maps):
    """报告 → (原始名, 来源范围)；无匹配返回 ("", "")。"""
    if not maps:
        return "", ""
    lib = library or {}
    url = lib.get("source_url") or lib.get("source_repo")
    c = _canon(url)
    if c and c in maps["url_map"]:
        return maps["url_map"][c]
    if c:
        base = c.split("/")[-1]
        if base in maps["base_map"]:
            return maps["base_map"][base]
    # 名匹配（nodejs / 无 URL）
    keys = [lib.get("package_name"), handle, lib.get("registry_name")]
    for arr in (lib.get("aliases"), lib.get("import_names")):
        if isinstance(arr, list):
            keys.extend(arr)
    for k in keys:
        nk = _norm(k)
        if nk and nk in maps["name_map"]:
            return maps["name_map"][nk]
    return "", ""
