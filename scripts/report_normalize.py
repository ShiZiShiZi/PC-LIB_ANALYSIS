#!/usr/bin/env python3
"""Single-source report normalizer + consistency validator (Python).

This is the ONE authoritative implementation of the serve-time derivations that
`web/server.js` used to do only in memory (never persisting), and that
`scripts/export_xlsx.py` re-implemented incompletely. Porting it here — and calling
it from `assemble_report.py` — makes `report.json` born self-consistent: the derived
`harmony_adaptation.porting_class` / `feasibility` / `effort.level`, the canonical
`code_partition` bucket shape, and the `meta.harmony_warnings` are all persisted, so
the panel, the Excel export, and any direct reader see the SAME values.

Why porting_class is derived (not trusted from the model): it must stay consistent
with the dim-12 `code_partition` buckets and the dim-9 `unadaptable_apis`. The model
occasionally contradicts its own buckets (e.g. picks `recompile_only` while dim-12 has
a 30% `needs_adaptation` bucket). We keep the model's raw pick in `porting_class_model`
(advisory; recorded once, stable across re-normalization) and derive the authoritative
value from the structured signals — mirroring how `effort.level`/`feasibility` are
already derived. Deriving from the original model pick each run keeps a
`normalized_version` bump re-derivable.

Faithful port of web/server.js: derivePortingClass / reconcilePortingClass /
needsAdaptationOverride / needsAdaptationLoc / hasUnadaptableSignal / normalizeHarmony /
normalizeCodePartition / normalizeDim8 / normalizeLicense / deriveLicenseCategory /
deriveDifficultyLevel / effortDays / validateHarmony / validateReport / validateLicense.
Keep the two in lock-step; the selftest asserts server and this module agree.

Usage:
  python3 scripts/report_normalize.py --file <report.json> [--write]
    # without --write: prints the normalized JSON to stdout (dry run)
    # with --write: normalizes in place (atomic)
"""
import argparse
import json
import os
import re
import sys

# Bump when the derivation logic changes; a report whose meta.normalized_version is
# missing/older is re-normalized by the server (serve-time) and migrate_normalize.py.
# v2: consistency warnings carry a stable {code, class} and can be dismissed by the
#     model's self-review (meta.harmony_warnings_dismissed → meta.harmony_warnings_reviewed).
# v3: effort.breakdown recompile/api_adaptation are derived from code_partition LOC at
#     configurable rates, and effort.person_days total = Σ breakdown when itemized.
NORMALIZED_VERSION = 3

# Warning classes. `actionable` = a heuristic recall/漏判 check the model's self-review
# pass may FIX (amend the source dimension with evidence) or DISMISS as a false positive
# (record {code, rationale} in meta.harmony_warnings_dismissed). `info` = a deterministic
# audit note about a value the normalizer already corrected — never dismissible.
W_ACT = "actionable"
W_INFO = "info"

# Effort rates (LOC per person-day) for the derived breakdown items — configurable via the
# panel's .panel-settings.json (recompileLocPerDay / adaptationLocPerDay). server.js reads the
# same file through its `settings`; defaults MUST match DEFAULT_SETTINGS so JS↔Python agree.
DEFAULT_RECOMPILE_LOC_PER_DAY = 3000
DEFAULT_ADAPTATION_LOC_PER_DAY = 500
_SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".panel-settings.json")


def _pos_rate(v, default):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f if f > 0 else default


def effort_rates():
    """(recompile_loc_per_day, adaptation_loc_per_day) from .panel-settings.json, else defaults.
    Read fresh each call so a settings change is picked up by the next assemble/migrate."""
    rec, adp = DEFAULT_RECOMPILE_LOC_PER_DAY, DEFAULT_ADAPTATION_LOC_PER_DAY
    try:
        with open(_SETTINGS_FILE, encoding="utf-8") as fh:
            s = json.load(fh)
        if isinstance(s, dict):
            rec = _pos_rate(s.get("recompileLocPerDay"), rec)
            adp = _pos_rate(s.get("adaptationLocPerDay"), adp)
    except (OSError, ValueError):
        pass
    return rec, adp


# ---------------------------------------------------------------------------
# small helpers (JS truthiness / Number() parity)
# ---------------------------------------------------------------------------
def _num(v, default=0.0):
    """Number(v) with a default — mirrors JS `Number(x) || default` loosely."""
    if isinstance(v, bool):
        return default
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if f != f:  # NaN
        return default
    return f


def _list(v):
    return v if isinstance(v, list) else []


def _truthy_len(v):
    """JS `(v || []).length` parity: length for a list OR a string (a non-empty string
    evidence counts as present), 0 otherwise — so a malformed string field isn't mistaken
    for 'missing'."""
    return len(v) if isinstance(v, (list, str)) else 0


def _obj(v):
    return v if isinstance(v, dict) else {}


# ---------------------------------------------------------------------------
# dim-8 (runtime_surface / build_env) double-nesting repair
# ---------------------------------------------------------------------------
_DIM8_KEYS = {
    "runtime_surface": ["summary", "network", "filesystem", "env_vars",
                        "subprocess", "devices", "services"],
    "build_env": ["language_standard", "runtime_version", "build_system",
                  "compiler_extensions", "platforms", "entry_points",
                  "packaging", "notes"],
}


def normalize_dim8(report):
    if not isinstance(report, dict):
        return report
    for key, own_keys in _DIM8_KEYS.items():
        val = report.get(key)
        if not isinstance(val, dict):
            continue
        if any(k in val for k in own_keys):
            continue  # already correctly-keyed
        inner = val.get(key)
        if isinstance(inner, dict) and any(k in inner for k in own_keys):
            report[key] = inner
    return report


# ---------------------------------------------------------------------------
# license category (5-way strict closed axis)
# ---------------------------------------------------------------------------
_LICENSE_CATEGORY_RULES = [
    ("strong_copyleft", re.compile(r"\b(agpl|affero|\bgpl|gnu\s*general\s*public|gnu\s*gpl|eupl|osl-|open\s*software\s*license|sleepycat|cecill(?!-c|-b)|gpl-[123])", re.I)),
    ("weak_copyleft", re.compile(r"\b(lgpl|lesser\s*general\s*public|mpl|mozilla\s*public|epl-|eclipse\s*public|cddl|common\s*development|cpl-|common\s*public\s*license|ms-rl|cecill-c)", re.I)),
    ("commercial", re.compile(r"\b(sspl|busl|bsl-1\.1|business\s*source|elastic-2|\belv2\b|commons-clause|proprietary|commercial|all\s*rights\s*reserved|\beula\b)", re.I)),
    ("permissive", re.compile(r"\b(mit\b|mit-0|bsd|apache|isc\b|zlib|libpng|boost|bsl-1\.0|unlicense|0bsd|cc0|wtfpl|python-2|\bpsf\b|x11|ncsa|postgresql|artistic)", re.I)),
]


def derive_license_category(report):
    lic = _obj(report.get("license") if isinstance(report, dict) else None)
    if not lic:
        return None
    if lic.get("category"):
        return lic.get("category")  # explicit (model) wins
    spdx = ("" if lic.get("spdx") is None else str(lic.get("spdx"))).strip()
    name = ("" if lic.get("name") is None else str(lic.get("name"))).strip()
    hay = (spdx + " " + name).strip()
    no_assert = (not spdx) or re.match(r"^(noassertion|unknown|none|null)$", spdx, re.I) is not None
    if not hay:
        return "undeclared"
    for cat, rex in _LICENSE_CATEGORY_RULES:
        if rex.search(hay):
            return cat
    if no_assert:
        return "undeclared"
    return None  # recognized but unmapped


def normalize_license(report):
    lic = report.get("license") if isinstance(report, dict) else None
    if not isinstance(lic, dict):
        return report
    if not lic.get("category"):
        c = derive_license_category(report)
        if c:
            lic["category"] = c
    return report


def validate_license(report):
    lic = report.get("license") if isinstance(report, dict) else None
    if not isinstance(lic, dict) or not lic.get("category"):
        return []
    derived = derive_license_category({"license": {"spdx": lic.get("spdx"), "name": lic.get("name")}})
    if derived and derived != lic.get("category"):
        return [("license_category_mismatch", W_ACT,
                 f"license.category({lic.get('category')}) 与依据 SPDX({lic.get('spdx') or '—'}) 派生的性质({derived}) 不一致，请核对")]
    return []


# ---------------------------------------------------------------------------
# dim-12 code_partition shape tolerance (synonym keys → canonical loc/path/reason)
# ---------------------------------------------------------------------------
def normalize_code_partition(report):
    cp = report.get("code_partition") if isinstance(report, dict) else None
    if not isinstance(cp, dict) or not isinstance(cp.get("buckets"), list):
        return report
    for b in cp["buckets"]:
        if not isinstance(b, dict):
            continue
        mods = b.get("modules") if isinstance(b.get("modules"), list) else []
        for m in mods:
            if not isinstance(m, dict):
                continue
            if m.get("path") is None:
                m["path"] = m.get("dir") if m.get("dir") is not None else (
                    m.get("module") if m.get("module") is not None else m.get("name"))
            if m.get("reason") is None and m.get("note") is not None:
                m["reason"] = m.get("note")
        if b.get("loc") is None:
            if b.get("total_loc") is not None:
                b["loc"] = b.get("total_loc")
            else:
                s = sum(_num(m.get("loc")) for m in mods if isinstance(m, dict))
                if s > 0:
                    b["loc"] = s
    return report


# ---------------------------------------------------------------------------
# dim-9 harmony porting-class derivation (the single source of truth)
# ---------------------------------------------------------------------------
PLATFORM_BLOCKER_RE = re.compile(
    r"win32|x11|xcb|cocoa|coregraphics|iokit|registry|wmi|sysfs|procfs|gpu|cuda|opencl|"
    r"vulkan|device|driver|kernel|syscall|ioctl|permission|hardware|_api\b|api_unavailable|platform", re.I)
_NATIVE_CAT_RE = re.compile(r"native_dependency|ffi|toolchain|posix")

NEEDS_ADAPTATION_MATERIAL_PCT = 0.05
CLAMPABLE_PORTING_CLASSES = {"no_adaptation", "recompile_only", "needs_adaptation_full"}


def has_unadaptable_signal(ha):
    if not isinstance(ha, dict):
        return False
    if isinstance(ha.get("unadaptable_apis"), list) and ha.get("unadaptable_apis"):
        return True
    if isinstance(ha.get("blockers"), list) and any(
            isinstance(b, dict) and b.get("adaptability") == "unadaptable" for b in ha["blockers"]):
        return True
    return False


def bucket_loc(report, cls):
    """Total production LOC in the given code_partition bucket class (0 if absent)."""
    cp = report.get("code_partition") if isinstance(report, dict) else None
    if not isinstance(cp, dict) or not isinstance(cp.get("buckets"), list):
        return 0.0
    return sum(_num(b.get("loc")) for b in cp["buckets"]
              if isinstance(b, dict) and b.get("class") == cls)


def needs_adaptation_loc(report):
    return bucket_loc(report, "needs_adaptation")


def needs_adaptation_override(report, cls):
    """A non-empty dim-12 needs_adaptation bucket forces cls UP to needs_adaptation_full:
    recompile_only (C/C++) means "zero source change" so ANY needs_adaptation contradicts it
    → always override; no_adaptation (ported-runtime langs) tolerates trivial cross-compile
    branches so require the bucket to be MATERIAL (>=5% of production code)."""
    if cls not in ("no_adaptation", "recompile_only"):
        return None
    need = needs_adaptation_loc(report)
    if need <= 0:
        return None
    if cls == "recompile_only":
        return "needs_adaptation_full"
    prod = _num(_obj(_obj(report.get("code_metrics")).get("production")).get("code"))
    return "needs_adaptation_full" if (prod > 0 and need >= NEEDS_ADAPTATION_MATERIAL_PCT * prod) else None


def reconcile_porting_class(report, ha, cls):
    if not cls:
        return cls
    if cls in CLAMPABLE_PORTING_CLASSES and has_unadaptable_signal(ha):
        return "needs_adaptation_partial"
    na = needs_adaptation_override(report, cls)
    if na:
        return na
    return cls


def derive_porting_class(report, base):
    """base = the model's ORIGINAL porting_class pick (or None if omitted). Trust it as the
    starting point then reconcile UP against the structured signals; when the model omits it,
    derive from feasibility/blockers/path/ecosystem (the from-scratch else-branch)."""
    ha = report.get("harmony_adaptation") if isinstance(report, dict) else None
    if not isinstance(ha, dict):
        return None
    if base:
        cls = base
    elif ha.get("feasibility") == "infeasible":
        cls = "infeasible"
    else:
        unadaptable = _list(ha.get("unadaptable_apis"))
        blk = _list(ha.get("blockers"))
        has_structured = any(isinstance(b, dict) and b.get("adaptability") for b in blk)
        if unadaptable or any(isinstance(b, dict) and b.get("adaptability") == "unadaptable" for b in blk):
            cls = "needs_adaptation_partial"
        elif any(isinstance(b, dict) and (b.get("severity") == "blocker" or b.get("adaptability") == "partial") for b in blk):
            cls = "needs_adaptation_full"
        else:
            cats = [str((b or {}).get("category") or "").lower() for b in blk if isinstance(b, dict)]
            native = any(_NATIVE_CAT_RE.search(c) for c in cats)
            if (not has_structured) and any(PLATFORM_BLOCKER_RE.search(c) for c in cats):
                cls = "needs_adaptation_full"
            else:
                path = str(ha.get("recommended_path") or "").lower()
                if "run_on_ported_runtime" in path and not native:
                    cls = "no_adaptation"
                elif native:
                    cls = "recompile_only"
                else:
                    cls = "no_adaptation"
    return reconcile_porting_class(report, ha, cls)


# ---- difficulty level (5-tier) + effort person-days -----------------------
_RANK_LEVEL = ["very_low", "low", "medium", "high", "very_high"]
_CLASS_LEVEL_FLOOR = {"no_adaptation": 0, "recompile_only": 1, "needs_adaptation_full": 2,
                      "needs_adaptation_partial": 3, "infeasible": 4}
_FEAS_FOR_CLASS = {"no_adaptation": "feasible", "recompile_only": "feasible_with_effort",
                   "needs_adaptation_full": "feasible_with_effort",
                   "needs_adaptation_partial": "hard", "infeasible": "infeasible"}


def days_bucket(days_hi):
    try:
        d = float(days_hi)
    except (TypeError, ValueError):
        return 0
    if not (d > 2):  # also catches NaN
        return 0
    if d <= 5:
        return 1
    if d <= 15:
        return 2
    if d <= 40:
        return 3
    return 4


def derive_difficulty_level(porting_class, person_days_hi):
    if not porting_class:
        return None
    floor = _CLASS_LEVEL_FLOOR.get(porting_class, 0)
    return _RANK_LEVEL[max(floor, days_bucket(person_days_hi))]


def effort_days(ha):
    if not isinstance(ha, dict):
        return None
    e = ha.get("effort")
    if isinstance(e, dict) and isinstance(e.get("person_days"), list) and len(e["person_days"]) == 2:
        lo, hi = e["person_days"]
        try:
            lo, hi = float(lo), float(hi)
        except (TypeError, ValueError):
            return None
        if lo == lo and hi == hi:  # both finite (not NaN)
            return [lo, hi]
    return None


# effort.breakdown components derived from code_partition LOC (not model-supplied).
_DERIVED_COMPONENTS = ("recompile", "api_adaptation")


def _days1(x):
    """Round half-up to 1 decimal; return an int when whole so JSON matches JS (3 not 3.0)."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return 0
    if x < 0:
        x = 0.0
    r = int(x * 10 + 0.5) / 10.0
    return int(r) if r == int(r) else r


def _sum_breakdown(bd):
    lo = hi = 0.0
    any_pd = False
    for b in bd:
        pd = b.get("person_days") if isinstance(b, dict) else None
        if isinstance(pd, list) and len(pd) == 2:
            try:
                lo += float(pd[0]); hi += float(pd[1]); any_pd = True
            except (TypeError, ValueError):
                pass
    return [lo, hi] if any_pd else None


def _apply_derived_component(bd, comp, loc, rate, zh_label):
    """Set the `comp` breakdown item's person_days = loc/rate (a point [d,d]) + a basis note,
    overriding an existing item of that component or appending one. No-op when loc<=0."""
    loc = _num(loc)
    if loc <= 0 or rate <= 0:
        return
    d = _days1(loc / rate)
    if not (d > 0):
        d = 0.1
    pd = [d, d]
    basis = f"{zh_label} {int(loc)} 行 ÷ {int(rate)} 行/天"
    for b in bd:
        if isinstance(b, dict) and b.get("component") == comp:
            b["person_days"] = pd
            b["basis"] = basis
            return
    bd.append({"component": comp, "person_days": pd, "basis": basis})


def normalize_harmony(report):
    ha = report.get("harmony_adaptation") if isinstance(report, dict) else None
    if not isinstance(ha, dict):
        return report
    # base = model's ORIGINAL pick. Recorded once in porting_class_model and read from there on
    # re-normalization, so the value stays re-derivable even after porting_class was overwritten.
    if "porting_class_model" in ha:
        base = ha["porting_class_model"]
    else:
        base = ha.get("porting_class")
    ha["porting_class_model"] = base  # persist original once (may be null if the model omitted it)

    cls = derive_porting_class(report, base)
    if cls:
        if base and base != cls:
            ha["porting_class_adjusted"] = {"from": base, "to": cls}
        ha["porting_class"] = cls
        ha["feasibility"] = _FEAS_FOR_CLASS.get(cls) or ha.get("feasibility") or None

    ha["effort"] = ha["effort"] if isinstance(ha.get("effort"), dict) else {}

    def _tag(arr, p):
        if isinstance(arr, list):
            for i, it in enumerate(arr):
                if isinstance(it, dict) and not it.get("id"):
                    it["id"] = f"{p}:{i + 1}"
    _tag(ha.get("target_assumptions"), "ta")
    _tag(ha.get("unadaptable_apis"), "ua")
    _tag(ha.get("blockers"), "bk")

    if isinstance(ha.get("required_permissions"), list):
        for p in ha["required_permissions"]:
            if isinstance(p, dict) and not p.get("harmony_status"):
                p["harmony_status"] = "unknown"

    # Effort breakdown + total. `recompile`/`api_adaptation` are DERIVED from code_partition LOC
    # at configurable rates (like effort.level). We only touch the breakdown when the model
    # provided one (had_breakdown) — never synthesise a table from nothing — so re-normalization
    # is idempotent and reports without a breakdown keep the model's holistic person_days.
    eff = ha["effort"]
    bd = eff.get("breakdown")
    had_breakdown = isinstance(bd, list) and len(bd) > 0
    model_days = effort_days(ha)                       # model's own person_days (pre-derivation)
    if had_breakdown:
        rec_rate, adp_rate = effort_rates()
        _apply_derived_component(bd, "recompile", bucket_loc(report, "recompile_reuse"), rec_rate, "重编译复用")
        _apply_derived_component(bd, "api_adaptation", bucket_loc(report, "needs_adaptation"), adp_rate, "需适配")
        bd_sum = _sum_breakdown(bd)
        total = bd_sum if bd_sum is not None else model_days   # 总量 = 分项之和（决策 Q1）
    else:
        total = model_days                              # 无分项 → 保留模型总量
    if total is not None:
        eff["person_days"] = [_days1(total[0]), _days1(total[1])]
    pd = eff.get("person_days")
    hi = pd[1] if isinstance(pd, list) and len(pd) == 2 else 0
    eff["level"] = derive_difficulty_level(cls, hi)

    if isinstance(ha.get("critical_dependencies"), list):
        for i, c in enumerate(ha["critical_dependencies"]):
            if isinstance(c, dict) and not (_num(c.get("order")) >= 1):
                c["order"] = i + 1
    return report


# ---------------------------------------------------------------------------
# consistency validators (return 中文 warning strings)
# ---------------------------------------------------------------------------
def validate_harmony(report):
    ha = report.get("harmony_adaptation") if isinstance(report, dict) else None
    if not isinstance(ha, dict):
        return []
    w = []
    cls = ha.get("porting_class") or derive_porting_class(report, ha.get("porting_class_model") or ha.get("porting_class"))
    if cls and ha.get("feasibility") and _FEAS_FOR_CLASS.get(cls) and ha.get("feasibility") != _FEAS_FOR_CLASS[cls]:
        w.append(("feas_pclass_inconsistent", W_INFO,
                  f"feasibility({ha.get('feasibility')}) 与 porting_class({cls}) 不自洽，应为 {_FEAS_FOR_CLASS[cls]}"))
    pca = ha.get("porting_class_adjusted")
    if isinstance(pca, dict) and pca.get("from") != pca.get("to"):
        reason = ("但代码分区(dim-12)存在需适配模块（非零源码改动）"
                  if pca.get("to") == "needs_adaptation_full" else "但存在无法适配的 API/阻碍点")
        w.append(("pclass_adjusted", W_INFO,
                  f"porting_class 模型原判 {pca.get('from')}，{reason}，已按\"不矛盾\"校正为 {pca.get('to')}"))
    eco = str(_obj(report.get("library")).get("ecosystem") or "").lower()
    managed_eco = eco in ["go", "python", "java", "javascript", "nodejs", "node", "typescript"]
    na = _obj(report.get("native_api"))
    native_surface = bool(
        (isinstance(na.get("dynamic_libraries"), list) and na.get("dynamic_libraries"))
        or (isinstance(na.get("groups"), list) and any(
            isinstance(g, dict) and g.get("category") in ["ffi", "platform", "system", "hardware"] for g in na["groups"]))
        or (isinstance(_obj(report.get("library")).get("bindings"), list) and _obj(report.get("library")).get("bindings")))
    if cls == "recompile_only" and managed_eco and not native_surface:
        w.append(("recompile_no_native", W_INFO,
                  f"porting_class=recompile_only 但主生态为 {eco}（已移植运行时）且无原生调用面，疑似应为 no_adaptation"))
    ua = _list(ha.get("unadaptable_apis"))
    blk = _list(ha.get("blockers"))
    ta = _list(ha.get("target_assumptions"))
    if ua and cls not in ("needs_adaptation_partial", "infeasible"):
        w.append(("ua_pclass", W_INFO,
                  f"unadaptable_apis 非空但 porting_class={cls}（应为 needs_adaptation_partial 或 infeasible）"))
    ids = set(x.get("id") for x in (ta + ua + blk) if isinstance(x, dict) and x.get("id"))
    for b in blk:
        if not isinstance(b, dict):
            continue
        for r in (_list(b.get("caused_by")) + _list(b.get("manifests_as"))):
            if r not in ids:
                w.append((f"blocker_ref:{b.get('id') or b.get('issue') or ''}:{r}", W_ACT,
                          f"blocker {b.get('id') or b.get('issue') or ''} 的引用 {r} 不存在（悬空引用）"))
    for u in ua:
        if not isinstance(u, dict):
            continue
        for r in _list(u.get("caused_by")):
            if r not in ids:
                w.append((f"ua_ref:{u.get('id') or u.get('api') or ''}:{r}", W_ACT,
                          f"unadaptable_api {u.get('id') or u.get('api') or ''} 的 caused_by {r} 不存在"))
    for a in ta:
        if isinstance(a, dict) and a.get("required") and a.get("target_status") == "unavailable":
            refed = any(isinstance(x, dict) and a.get("id") in _list(x.get("caused_by")) for x in (blk + ua))
            if not refed:
                w.append((f"ta_unref:{a.get('id') or a.get('capability') or ''}", W_ACT,
                          f"target_assumption {a.get('id') or a.get('capability') or ''} 为 required+unavailable 但无对应 blocker/unadaptable_api"))
    if any(isinstance(a, dict) and a.get("required") and a.get("target_status") == "unknown" for a in ta) and ha.get("confidence") == "high":
        w.append(("conf_high_unknown", W_ACT, "存在 required 且 unknown 的目标假设，confidence 不应为 high"))
    for p in _list(ha.get("required_permissions")):
        if isinstance(p, dict) and p.get("harmony_status") == "unavailable" and not blk:
            w.append((f"perm_unavail_noblocker:{p.get('permission') or ''}", W_ACT,
                      f"required_permission {p.get('permission') or ''} 为 unavailable 但无对应 blocker"))
    return w


_CAP_SIGNALS = [
    ("gui", re.compile(r"\b(qt|pyqt|pyside|gtk|wxwidget|imgui|tkinter|electron|swing|javafx|\bswt\b|wpf|winui)", re.I)),
    ("rendering_3d", re.compile(r"\b(opengl|libgl|gles|egl|vulkan|directx|d3d1[12]|dxgi|webgpu)", re.I)),
    ("media", re.compile(r"\b(ffmpeg|libav|gstreamer|portaudio|libasound|pulseaudio|x264|openh264|libvpx|v4l2|avfoundation)", re.I)),
    ("hardware", re.compile(r"\b(cuda|nvcc|opencl|libusb|termios|bluez|npu|fpga)", re.I)),
]
_CLOUD_SIGNALS = [
    ("google_firebase", re.compile(r"\b(firebase|firebaseio\.com|firebaseapp\.com|firebasestorage)", re.I)),
    ("aws", re.compile(r"\b(boto3|botocore|aws-sdk|aws-amplify|amazonaws\.com|awssdk)", re.I)),
    ("gcp", re.compile(r"\b(google-cloud|googleapis\.com|@google-cloud)", re.I)),
    ("azure", re.compile(r"\b(azure-|@azure\/|\.azure\.com|azurewebsites)", re.I)),
    ("alibaba_cloud", re.compile(r"\b(aliyun|aliyuncs\.com|@alicloud)", re.I)),
    ("tencent_cloud", re.compile(r"\b(tencentcloud|myqcloud\.com|tencentcloudapi)", re.I)),
    ("supabase", re.compile(r"\b(supabase)", re.I)),
    ("sentry", re.compile(r"\b(sentry-sdk|@sentry\/|sentry-native|sentry\.io)", re.I)),
]


def validate_report(report):
    if not isinstance(report, dict):
        return []
    w = []
    cap = _obj(report.get("capability_profile"))
    scen = _list(cap.get("scenarios"))
    present_keys = set(s.get("key") for s in scen if isinstance(s, dict) and s.get("present"))
    na = _obj(report.get("native_api"))
    names = ([d.get("name") for d in _list(_obj(report.get("dependencies")).get("dependencies")) if isinstance(d, dict)]
             + [d.get("name") for d in _list(na.get("dynamic_libraries")) if isinstance(d, dict)]
             + [g.get("type") for g in _list(na.get("groups")) if isinstance(g, dict)])
    names = [n for n in names if n]
    hay_parts = []
    for n in names:
        hay_parts.append(str(n))
        hay_parts.append(re.sub(r"^lib", "", str(n), flags=re.I))
    hay = "  ".join(hay_parts)
    for key, rex in _CAP_SIGNALS:
        if rex.search(hay) and key not in present_keys:
            w.append((f"cap_miss:{key}", W_ACT,
                      f"依赖/native_api 出现 {key} 强信号，但 capability_profile 未标记该场景（可能漏判）"))
    for s in scen:
        if isinstance(s, dict) and s.get("present") and not _truthy_len(s.get("evidence")):
            w.append((f"scenario_no_evidence:{s.get('key')}", W_ACT,
                      f"能力画像场景 {s.get('key')} present 但缺 evidence"))
    ha = _obj(report.get("harmony_adaptation"))
    for p in _list(ha.get("required_permissions")):
        if isinstance(p, dict) and p.get("source_capability") and p.get("source_capability") != "cloud_services" and p.get("source_capability") not in present_keys:
            w.append((f"perm_dangling_cap:{p.get('permission') or ''}", W_ACT,
                      f"required_permission {p.get('permission') or ''} 的 source_capability={p.get('source_capability')} 不在已标记场景中"))
    blk = _list(ha.get("blockers"))
    ta = _list(ha.get("target_assumptions"))
    dim_text = json.dumps([blk, ta, _list(ha.get("unadaptable_apis"))], ensure_ascii=False).lower()
    for s in scen:
        if isinstance(s, dict) and s.get("present") and s.get("harmony_status") in ("unavailable", "partial") \
                and str(s.get("key")).lower() not in dim_text and (len(blk) + len(ta)) == 0:
            w.append((f"scenario_no_dim9:{s.get('key')}", W_ACT,
                      f"场景 {s.get('key')} 鸿蒙状态为 {s.get('harmony_status')} 但 dim-9 无对应阻碍/假设（可能漏登记）"))
    cs = _obj(report.get("cloud_services"))
    csvc = _list(cs.get("services"))
    cs_vendors = set(s.get("vendor") for s in csvc if isinstance(s, dict) and s.get("vendor"))
    net_text = json.dumps(_list(_obj(report.get("runtime_surface")).get("network")), ensure_ascii=False)
    cloud_hay = (hay + "  " + net_text).lower()
    for vendor, rex in _CLOUD_SIGNALS:
        if rex.search(cloud_hay) and vendor not in cs_vendors:
            w.append((f"cloud_miss:{vendor}", W_ACT,
                      f"依赖/网络出现 {vendor} 云服务强信号，但 cloud_services 未标记该厂商（可能漏判）"))
    if cs.get("present") and csvc:
        perms = json.dumps(_list(ha.get("required_permissions")), ensure_ascii=False).lower()
        if "internet" not in perms:
            w.append(("cloud_no_internet", W_ACT, "cloud_services 涉及云端但 dim-9 未登记 ohos.permission.INTERNET（可能漏登记）"))
    cp = report.get("code_partition")
    cls = ha.get("porting_class") or derive_porting_class(report, ha.get("porting_class_model") or ha.get("porting_class"))
    ua_list = _list(ha.get("unadaptable_apis"))
    if isinstance(cp, dict) and isinstance(cp.get("buckets"), list) and cp["buckets"]:
        prod_code = _num(_obj(_obj(report.get("code_metrics")).get("production")).get("code"))
        total = sum(_num(b.get("loc")) for b in cp["buckets"] if isinstance(b, dict))
        if prod_code > 0 and abs(total - prod_code) / prod_code > 0.15:
            w.append(("cp_loc_coverage", W_INFO,
                      f"代码分区桶 LOC 之和({_intish(total)})与生产代码({_intish(prod_code)})偏差超过 15%（覆盖不足或重复计入）"))
        un_loc = sum(_num(b.get("loc")) for b in cp["buckets"] if isinstance(b, dict) and b.get("class") == "unadaptable")
        if un_loc > 0 and cls not in ("needs_adaptation_partial", "infeasible"):
            w.append(("cp_unadapt_pclass", W_INFO,
                      f"代码分区含 unadaptable 桶({_intish(un_loc)} 行)但 porting_class={cls}（应为 needs_adaptation_partial/infeasible）"))
        if needs_adaptation_override(report, cls):
            w.append(("cp_needs_full", W_INFO,
                      f"代码分区含 needs_adaptation 桶({_intish(needs_adaptation_loc(report))} 行)但 porting_class={cls}（应为 needs_adaptation_full；零源码改动才是 recompile_only）"))
        if un_loc > 0 and not ua_list:
            w.append(("cp_unadapt_no_ua", W_ACT, "代码分区含 unadaptable 桶但 dim-9 unadaptable_apis 为空（漏登记或分桶过严）"))
        if un_loc == 0 and ua_list:
            w.append(("ua_no_cp_bucket", W_ACT, "dim-9 有 unadaptable_apis 但代码分区无 unadaptable 桶（分桶可能漏标）"))
    eb = _list(ha.get("effort", {}).get("breakdown")) if isinstance(ha.get("effort"), dict) else []
    days = effort_days(ha)
    if eb and days:
        lo = hi = 0.0
        for b in eb:
            pd = b.get("person_days") if isinstance(b, dict) and isinstance(b.get("person_days"), list) and len(b.get("person_days")) == 2 else [0, 0]
            lo += _num(pd[0]); hi += _num(pd[1])
        if hi < days[0] * 0.7 or lo > days[1] * 1.3:
            w.append(("effort_breakdown", W_INFO,
                      f"effort.breakdown 分项之和([{_intish(lo)}, {_intish(hi)}])与 person_days([{_intish(days[0])}, {_intish(days[1])}])明显不符"))
    cds = _list(ha.get("critical_dependencies"))
    if cds:
        deps = _list(_obj(report.get("dependencies")).get("dependencies"))
        dep_by_name = {str(d.get("name")).lower(): d for d in deps if isinstance(d, dict) and d.get("name")}
        id_set = set(x.get("id") for x in (blk + ua_list + ta) if isinstance(x, dict) and x.get("id"))
        for c in cds:
            if not isinstance(c, dict) or not c.get("name"):
                continue
            dep = dep_by_name.get(str(c.get("name")).lower())
            if not dep:
                w.append((f"critical_dep_notfound:{c.get('name')}", W_ACT,
                          f"critical_dependencies 的 {c.get('name')} 在 dependencies 列表中找不到（名称须与 dependencies[].name 一致）"))
            elif dep.get("harmony_adapted") is True:
                w.append((f"critical_dep_adapted:{c.get('name')}", W_ACT,
                          f"critical_dependencies 列出了已鸿蒙化依赖 {c.get('name')}（官方源已有移植产物，不应列入关键路径）"))
            for r in _list(c.get("refs")):
                if r not in id_set:
                    w.append((f"critical_dep_ref:{c.get('name')}:{r}", W_ACT,
                              f"critical_dependencies {c.get('name')} 的引用 {r} 不存在（悬空引用）"))
    return w


def _intish(v):
    """Render a number like JS would in a template string: 5 not 5.0, but 5.5 kept."""
    f = _num(v)
    return int(f) if f == int(f) else f


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------
def normalize_report(report):
    """Normalize IN PLACE and attach consistency warnings + version stamp. Idempotent."""
    if not isinstance(report, dict):
        return report
    normalize_dim8(report)
    normalize_code_partition(report)   # before harmony: canonical loc/class feeds LOC对账 + class 校正
    normalize_harmony(report)
    normalize_license(report)
    raw = validate_harmony(report) + validate_report(report) + validate_license(report)
    meta = report.get("meta")
    if not isinstance(meta, dict):
        meta = {}
        report["meta"] = meta
    # The model's self-review pass may DISMISS an `actionable` warning it judged a false
    # positive, recording {code, rationale} in meta.harmony_warnings_dismissed (authored in
    # blocks/meta.json, carried through assemble). Move those to meta.harmony_warnings_reviewed;
    # everything else (incl. all `info` audit notes) stays active. `info` codes are never
    # dismissible — a dismissal targeting one is ignored.
    dismissed = {}
    for d in (meta.get("harmony_warnings_dismissed") if isinstance(meta.get("harmony_warnings_dismissed"), list) else []):
        if isinstance(d, dict) and d.get("code"):
            dismissed[d["code"]] = d.get("rationale") or ""
    active = []
    reviewed = []
    for code, cls, msg in raw:
        if cls == W_ACT and code in dismissed:
            reviewed.append({"code": code, "message": msg, "rationale": dismissed[code]})
        else:
            active.append({"code": code, "class": cls, "message": msg})
    if active:
        meta["harmony_warnings"] = active
    elif "harmony_warnings" in meta:
        del meta["harmony_warnings"]
    if reviewed:
        meta["harmony_warnings_reviewed"] = reviewed
    elif "harmony_warnings_reviewed" in meta:
        del meta["harmony_warnings_reviewed"]
    meta["normalized_version"] = NORMALIZED_VERSION
    return report


def main():
    ap = argparse.ArgumentParser(description="Normalize a report.json (single source of truth).")
    ap.add_argument("--file", required=True, help="path to report.json")
    ap.add_argument("--write", action="store_true", help="normalize in place (atomic); else print to stdout")
    args = ap.parse_args()
    try:
        with open(args.file, encoding="utf-8") as fh:
            report = json.load(fh)
    except Exception as e:  # noqa: BLE001
        print(f"report_normalize: cannot read {args.file}: {e}", file=sys.stderr)
        return 1
    normalize_report(report)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.write:
        tmp = args.file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, args.file)
        print(f"normalized {args.file} (v{NORMALIZED_VERSION})")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
