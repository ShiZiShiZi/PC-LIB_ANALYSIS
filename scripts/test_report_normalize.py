#!/usr/bin/env python3
"""Fixture selftest for scripts/report_normalize.py — the single-source dim-9 normalizer.

Asserts the porting_class derivation (the axis the model kept getting wrong) is correct and
self-consistent across the key cases, that it is a FLOOR that only clamps UP, and that
normalization is idempotent (so migrate / re-serve never drift). Run:

  python3 scripts/test_report_normalize.py     # exit 0 = pass

The full-corpus JS↔Python parity (web/server.js mirror vs this module) is asserted separately;
keep the two in lock-step when either changes.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report_normalize as rn  # noqa: E402

_FAILS = []


def check(name, got, want):
    if got != want:
        _FAILS.append(f"{name}: got {got!r}, want {want!r}")


def norm(report):
    r = copy.deepcopy(report)
    rn.normalize_report(r)
    return r


# ── Fixture A: the uSockets bug — model says recompile_only, but dim-12 has a needs_adaptation
#    bucket → must clamp UP to needs_adaptation (3-value), keep the model pick in porting_class_model.
A = {
    "code_metrics": {"production": {"code": 1000}},
    "code_partition": {"buckets": [
        {"class": "recompile_reuse", "loc": 700},
        {"class": "needs_adaptation", "loc": 300}]},
    "harmony_adaptation": {"porting_class": "recompile_only",
                           "effort": {"person_days": [3, 8]}, "blockers": [], "unadaptable_apis": []},
    "library": {"ecosystem": "cpp"},
}
a = norm(A)["harmony_adaptation"]
check("A.porting_class", a.get("porting_class"), "needs_adaptation")
check("A.porting_class_model", a.get("porting_class_model"), "recompile_only")
check("A.no_feasibility", "feasibility" in a, False)
check("A.effective_class", (a.get("adaptation_assessment") or {}).get("effective_class"), "needs_adaptation")
check("A.overall", (a.get("adaptation_assessment") or {}).get("overall"), "adaptable")
check("A.effort.level", a["effort"].get("level"), "medium")
check("A.adjusted.from", (a.get("porting_class_adjusted") or {}).get("from"), "recompile_only")

# ── Fixture B: unadaptable_apis tagged CORE → porting_class needs_adaptation, effective_class
#    needs_adaptation_core_partial, overall core_blocked (the CUDA-core case).
B = {
    "code_metrics": {"production": {"code": 1000}},
    "code_partition": {"buckets": [
        {"class": "needs_adaptation", "loc": 500},
        {"class": "unadaptable", "loc": 100},
        {"class": "recompile_reuse", "loc": 400}]},
    "harmony_adaptation": {"porting_class": "needs_adaptation_full",
                           "effort": {"person_days": [10, 20]},
                           "unadaptable_apis": [{"api": "cuLaunchKernel", "reason": "无 CUDA 运行时",
                                                 "functionality_class": "core"}],
                           "blockers": []},
    "library": {"ecosystem": "cpp"},
}
b = norm(B)["harmony_adaptation"]
check("B.porting_class", b.get("porting_class"), "needs_adaptation")
check("B.effective_class", (b.get("adaptation_assessment") or {}).get("effective_class"), "needs_adaptation_core_partial")
check("B.overall", (b.get("adaptation_assessment") or {}).get("overall"), "core_blocked")
check("B.core.adaptable", (b["adaptation_assessment"]["core"]).get("adaptable"), False)
check("B.core.unadaptable", (b["adaptation_assessment"]["core"]).get("unadaptable"), ["ua:1"])
check("B.platform.adaptable", (b["adaptation_assessment"]["platform_specific"]).get("adaptable"), True)
check("B.effort.level", b["effort"].get("level"), "very_high")
check("B.ua.id", (b["unadaptable_apis"][0]).get("id"), "ua:1")   # id backfilled
check("B.ua.not_defaulted", (b["unadaptable_apis"][0]).get("functionality_class_defaulted"), None)

# ── Fixture B2: unadaptable_apis UNTAGGED with a non-infeasible base → defaults platform_specific
#    → effective_class platform_partial, overall adaptable_with_tailoring, and a defaulted warning.
B2 = {
    "code_metrics": {"production": {"code": 1000}},
    "code_partition": {"buckets": [
        {"class": "recompile_reuse", "loc": 900}, {"class": "unadaptable", "loc": 100}]},
    "harmony_adaptation": {"porting_class": "recompile_only",
                           "effort": {"person_days": [8, 12]},
                           "unadaptable_apis": [{"api": "SomeWin32Cd", "reason": "无对应"}],
                           "blockers": []},
    "library": {"ecosystem": "cpp"},
}
b2r = norm(B2)
b2 = b2r["harmony_adaptation"]
check("B2.porting_class", b2.get("porting_class"), "needs_adaptation")
check("B2.effective_class", (b2.get("adaptation_assessment") or {}).get("effective_class"), "needs_adaptation_platform_partial")
check("B2.overall", (b2.get("adaptation_assessment") or {}).get("overall"), "adaptable_with_tailoring")
check("B2.ua.func_class", (b2["unadaptable_apis"][0]).get("functionality_class"), "platform_specific")
check("B2.ua.defaulted", (b2["unadaptable_apis"][0]).get("functionality_class_defaulted"), True)
b2_codes = [x.get("code") for x in (b2r["meta"].get("harmony_warnings") or [])]
check("B2.defaulted_warning", any(c and c.startswith("ua_func_class_defaulted") for c in b2_codes), True)
# idempotency: the defaulted flag + class persist unchanged across a re-normalize.
b2b = norm(b2r)["harmony_adaptation"]
check("B2.idempotent.func_class", (b2b["unadaptable_apis"][0]).get("functionality_class"), "platform_specific")
check("B2.idempotent.effective", (b2b.get("adaptation_assessment") or {}).get("effective_class"), "needs_adaptation_platform_partial")

# ── Fixture C: pure-script lib, model omits porting_class → from-scratch derivation
#    (no blockers, no needs_adaptation bucket) → no_adaptation.
C = {
    "code_metrics": {"production": {"code": 500}},
    "code_partition": {"buckets": [{"class": "reuse_direct", "loc": 500}]},
    "harmony_adaptation": {"effort": {"person_days": [0, 2]}, "blockers": [], "unadaptable_apis": []},
    "library": {"ecosystem": "python"},
}
c = norm(C)["harmony_adaptation"]
check("C.porting_class", c.get("porting_class"), "no_adaptation")
check("C.porting_class_model", c.get("porting_class_model"), None)   # model omitted → null
check("C.overall", (c.get("adaptation_assessment") or {}).get("overall"), "adaptable")
check("C.effort.level", c["effort"].get("level"), "very_low")

# ── Fixture D: legacy report with porting_class=infeasible (pre-v4) → collapses to needs_adaptation;
#    untagged unadaptable_api defaults to CORE (legacy infeasible meant core-unadaptable) →
#    effective_class core_partial, overall core_blocked. Pure collapse ≠ clamp → no adjustment.
D = {
    "code_metrics": {"production": {"code": 2000}},
    "code_partition": {"buckets": [
        {"class": "unadaptable", "loc": 1500},
        {"class": "recompile_reuse", "loc": 500}]},
    "harmony_adaptation": {"porting_class": "infeasible", "effort": {"person_days": [40, 60]},
                           "unadaptable_apis": [{"api": "cuLaunchKernel", "reason": "核心 CUDA"}],
                           "blockers": []},
    "library": {"ecosystem": "cpp"},
}
d = norm(D)["harmony_adaptation"]
check("D.porting_class", d.get("porting_class"), "needs_adaptation")
check("D.porting_class_model", d.get("porting_class_model"), "infeasible")   # raw legacy preserved
check("D.effective_class", (d.get("adaptation_assessment") or {}).get("effective_class"), "needs_adaptation_core_partial")
check("D.overall", (d.get("adaptation_assessment") or {}).get("overall"), "core_blocked")
check("D.ua.func_class(legacy core)", (d["unadaptable_apis"][0]).get("functionality_class"), "core")
check("D.no_adjustment(pure collapse)", d.get("porting_class_adjusted"), None)
check("D.effort.level", d["effort"].get("level"), "very_high")

# ── Fixture E: no_adaptation lib with a TRIVIAL (<5% of prod) needs_adaptation bucket → NOT
#    clamped up (materiality gate protects genuinely-no_adaptation Go/Rust libs).
E = {
    "code_metrics": {"production": {"code": 10000}},
    "code_partition": {"buckets": [
        {"class": "reuse_direct", "loc": 9800},
        {"class": "needs_adaptation", "loc": 200}]},   # 2% < 5%
    "harmony_adaptation": {"porting_class": "no_adaptation",
                           "effort": {"person_days": [1, 2]}, "blockers": [], "unadaptable_apis": []},
    "library": {"ecosystem": "go"},
}
e = norm(E)["harmony_adaptation"]
check("E.porting_class(materiality)", e.get("porting_class"), "no_adaptation")
check("E.overall", (e.get("adaptation_assessment") or {}).get("overall"), "adaptable")

# ── Fixture F: the esptool case — model says no_adaptation (lib's own .py needs zero change),
#    with only PARTIAL, target-side blockers (caused_by target_assumptions: serial/permission
#    prerequisites), no needs_adaptation bucket, no unadaptable_apis. porting_class (code axis)
#    must STAY no_adaptation — partial/target-side blockers surface via functional_viability
#    (viable_with_work), orthogonal to the code axis. Guards against a regression that would
#    clamp on partial blockers (the SKILL.md overstatement we corrected).
F = {
    "code_metrics": {"production": {"code": 34000}},
    "code_partition": {"buckets": [{"class": "reuse_direct", "loc": 34000}]},
    "harmony_adaptation": {"porting_class": "no_adaptation", "effort": {"person_days": [6, 13]},
                           "unadaptable_apis": [],
                           "target_assumptions": [
                               {"id": "ta:usb_serial", "required": True, "target_status": "partial"},
                               {"id": "ta:terminal_tty", "required": True, "target_status": "partial"}],
                           "blockers": [
                               {"id": "bk:pyserial", "severity": "major", "adaptability": "partial",
                                "category": "native_dependency", "caused_by": ["ta:usb_serial", "ta:terminal_tty"]},
                               {"id": "bk:modem_control", "severity": "minor", "adaptability": "adaptable",
                                "category": "posix_subset_gap", "caused_by": ["ta:terminal_tty"]}]},
    "library": {"ecosystem": "python"},
}
f = norm(F)["harmony_adaptation"]
check("F.porting_class(partial blocker no clamp)", f.get("porting_class"), "no_adaptation")
check("F.effective_class", (f.get("adaptation_assessment") or {}).get("effective_class"), "no_adaptation")
check("F.overall", (f.get("adaptation_assessment") or {}).get("overall"), "adaptable")
check("F.functional_viability", f.get("functional_viability"), "viable_with_work")

# ── Idempotency: normalizing an already-normalized report changes nothing material.
A_once = norm(A)
A_twice = norm(A_once)
check("idempotent.porting_class", A_twice["harmony_adaptation"].get("porting_class"), "needs_adaptation")
check("idempotent.porting_class_model", A_twice["harmony_adaptation"].get("porting_class_model"), "recompile_only")
check("idempotent.stamp", A_twice["meta"].get("normalized_version"), rn.NORMALIZED_VERSION)

# ── Stamp + warning presence
check("A.stamp", norm(A)["meta"].get("normalized_version"), rn.NORMALIZED_VERSION)
if not norm(A)["meta"].get("harmony_warnings"):
    _FAILS.append("A: expected a porting_class_adjusted harmony_warning")

# ── Warnings are objects with {code, class, message} (shape v2).
aw = (norm(A)["meta"].get("harmony_warnings") or [{}])[0]
check("A.warning.is_obj.code", aw.get("code"), "pclass_adjusted")
check("A.warning.is_obj.class", aw.get("class"), "info")
if not aw.get("message"):
    _FAILS.append("A: warning object missing message")

# ── Fixture F: an ACTIONABLE warning (scenario present but no evidence) dismissed by the
#    model's self-review → moved out of active into harmony_warnings_reviewed with rationale.
F = {
    "code_metrics": {"production": {"code": 800}},
    "code_partition": {"buckets": [{"class": "recompile_reuse", "loc": 800}]},
    "harmony_adaptation": {"porting_class": "recompile_only",
                           "effort": {"person_days": [2, 5]}, "blockers": [], "unadaptable_apis": []},
    "library": {"ecosystem": "cpp"},
    "capability_profile": {"scenarios": [{"key": "media", "present": True, "evidence": []}]},
    "meta": {"harmony_warnings_dismissed": [
        {"code": "scenario_no_evidence:media", "rationale": "media 仅在 examples/ 出现，非生产代码"}]},
}
fm = norm(F)["meta"]
f_active_codes = [x.get("code") for x in (fm.get("harmony_warnings") or [])]
f_reviewed = fm.get("harmony_warnings_reviewed") or []
check("F.active_excludes_dismissed", "scenario_no_evidence:media" in f_active_codes, False)
check("F.reviewed_code", (f_reviewed[0] if f_reviewed else {}).get("code"), "scenario_no_evidence:media")
check("F.reviewed_rationale", (f_reviewed[0] if f_reviewed else {}).get("rationale"),
      "media 仅在 examples/ 出现，非生产代码")

# ── Fixture G: dismissing an INFO code (pclass_adjusted) is a no-op — audit留痕 stays active.
G = copy.deepcopy(A)
G["harmony_adaptation"]["porting_class"] = "recompile_only"   # will be clamped → pclass_adjusted (info)
G["meta"] = {"harmony_warnings_dismissed": [{"code": "pclass_adjusted", "rationale": "试图驳回 info"}]}
gm = norm(G)["meta"]
g_active_codes = [x.get("code") for x in (gm.get("harmony_warnings") or [])]
check("G.info_not_dismissible", "pclass_adjusted" in g_active_codes, True)
check("G.info_not_in_reviewed", any(x.get("code") == "pclass_adjusted" for x in (gm.get("harmony_warnings_reviewed") or [])), False)

# ── Fixture H: effort breakdown — recompile/api_adaptation DERIVED from code_partition LOC
#    (recompile_reuse 9000 ÷ 3000 = 3; needs_adaptation 2000 ÷ 500 = 4), and person_days total =
#    Σ breakdown (gui[1,2] + recompile[3,3] + api_adaptation[4,4] = [8,9]).
H = {
    "code_metrics": {"production": {"code": 12000}},
    "code_partition": {"buckets": [
        {"class": "recompile_reuse", "loc": 9000},
        {"class": "needs_adaptation", "loc": 2000},
        {"class": "reuse_direct", "loc": 1000}]},
    "harmony_adaptation": {"porting_class": "needs_adaptation_full",
                           "effort": {"person_days": [6, 12],
                                      "breakdown": [{"component": "gui", "person_days": [1, 2], "basis": "x"}]},
                           "blockers": [], "unadaptable_apis": []},
    "library": {"ecosystem": "cpp"},
}
he = norm(H)["harmony_adaptation"]["effort"]
_hbd = {b.get("component"): b.get("person_days") for b in he.get("breakdown", [])}
check("H.recompile", _hbd.get("recompile"), [3, 3])
check("H.api_adaptation", _hbd.get("api_adaptation"), [4, 4])
check("H.person_days(Σ)", he.get("person_days"), [8, 9])
check("H.level", he.get("level"), "medium")
_hbasis = next((b.get("basis") for b in he["breakdown"] if b.get("component") == "recompile"), None)
check("H.basis", _hbasis, "重编译复用 9000 行 ÷ 3000 行/天")
# idempotency: re-normalizing keeps the same derived values + total (no drift, no dup)
H2 = norm(norm(H))["harmony_adaptation"]["effort"]
check("H.idempotent.person_days", H2.get("person_days"), [8, 9])
check("H.idempotent.breakdown_len", len(H2.get("breakdown", [])), 3)

# ── Fixture I: no model breakdown → derived items NOT synthesised, model person_days kept.
I = {
    "code_metrics": {"production": {"code": 1000}},
    "code_partition": {"buckets": [
        {"class": "recompile_reuse", "loc": 700}, {"class": "needs_adaptation", "loc": 300}]},
    "harmony_adaptation": {"porting_class": "needs_adaptation_full", "effort": {"person_days": [3, 8]},
                           "blockers": [], "unadaptable_apis": []},
    "library": {"ecosystem": "cpp"},
}
ie = norm(I)["harmony_adaptation"]["effort"]
check("I.person_days_kept", ie.get("person_days"), [3, 8])
check("I.no_breakdown_synthesised", "breakdown" in ie, False)

# ── Fixture J: custom rates via effort_rates override → recompile 9000/1500=6, adaptation 2000/250=8.
_orig_rates = rn.effort_rates
rn.effort_rates = lambda: (1500, 250)
try:
    je = norm(H)["harmony_adaptation"]["effort"]
    _jbd = {b.get("component"): b.get("person_days") for b in je.get("breakdown", [])}
    check("J.recompile(custom 1500)", _jbd.get("recompile"), [6, 6])
    check("J.api_adaptation(custom 250)", _jbd.get("api_adaptation"), [8, 8])
    check("J.person_days(Σ custom)", je.get("person_days"), [1 + 6 + 8, 2 + 6 + 8])
finally:
    rn.effort_rates = _orig_rates


# ── Fixture K: functional_viability — target-side prerequisite verdict derived from
#    target_assumptions[].target_status (REQUIRED only), worst-wins, ORTHOGONAL to porting_class.
def _fv(tas, eco="go", pc="no_adaptation"):
    rep = {
        "code_metrics": {"production": {"code": 500}},
        "code_partition": {"buckets": [{"class": "reuse_direct", "loc": 500}]},
        "harmony_adaptation": {"porting_class": pc, "effort": {"person_days": [0, 2]},
                               "blockers": [], "unadaptable_apis": [], "target_assumptions": tas},
        "library": {"ecosystem": eco},
    }
    return norm(rep)["harmony_adaptation"]


k1 = _fv([{"capability": "rt", "required": True, "target_status": "available"}])
check("K1.viable", k1.get("functional_viability"), "viable")
check("K1.porting_class_untouched", k1.get("porting_class"), "no_adaptation")
k2 = _fv([{"capability": "x", "required": True, "target_status": "partial"},
          {"capability": "y", "required": True, "target_status": "available"}])
check("K2.viable_with_work", k2.get("functional_viability"), "viable_with_work")
k3 = _fv([{"capability": "x", "required": True, "target_status": "partial"},
          {"capability": "y", "required": True, "target_status": "unknown"}])
check("K3.unverified(>partial)", k3.get("functional_viability"), "unverified")
k4 = _fv([{"capability": "nmap", "required": True, "target_status": "unavailable"},
          {"capability": "y", "required": True, "target_status": "unknown"}])
check("K4.blocked_external(>unknown)", k4.get("functional_viability"), "blocked_external")
check("K4.porting_class_untouched", k4.get("porting_class"), "no_adaptation")   # code axis unmoved
check("K4.overall_untouched", (k4.get("adaptation_assessment") or {}).get("overall"), "adaptable")
check("K4.target_status_model", k4["target_assumptions"][0].get("target_status_model"), "unavailable")
k5 = _fv([{"capability": "opt", "required": False, "target_status": "unavailable"},
          {"capability": "y", "required": True, "target_status": "available"}])
check("K5.optional_unavailable_ignored", k5.get("functional_viability"), "viable")
check("K6.empty_ta", _fv([]).get("functional_viability"), "viable")

# ── Fixture L: required+unknown deterministically caps confidence high→medium (was only warned);
#    confidence_model preserves the original; idempotent; emits an INFO audit warning.
L = {
    "code_metrics": {"production": {"code": 500}},
    "code_partition": {"buckets": [{"class": "reuse_direct", "loc": 500}]},
    "harmony_adaptation": {"porting_class": "no_adaptation", "confidence": "high",
                           "effort": {"person_days": [0, 2]}, "blockers": [], "unadaptable_apis": [],
                           "target_assumptions": [{"capability": "x", "required": True, "target_status": "unknown"}]},
    "library": {"ecosystem": "go"},
    "meta": {"confidence_overall": "high"},
}
lr = norm(L)
la = lr["harmony_adaptation"]
check("L.confidence_capped", la.get("confidence"), "medium")
check("L.confidence_model", la.get("confidence_model"), "high")
check("L.meta_capped", lr["meta"].get("confidence_overall"), "medium")
check("L.fv_unverified", la.get("functional_viability"), "unverified")
l_codes = [x.get("code") for x in (lr["meta"].get("harmony_warnings") or [])]
check("L.capped_warning", "confidence_capped_unknown" in l_codes, True)
check("L.capped_warning_is_info",
      next((x.get("class") for x in lr["meta"]["harmony_warnings"] if x.get("code") == "confidence_capped_unknown"), None), "info")
l2 = norm(lr)["harmony_adaptation"]
check("L.idempotent_confidence", l2.get("confidence"), "medium")
check("L.idempotent_model", l2.get("confidence_model"), "high")

# ── Fixture L2: high confidence but NO required+unknown → confidence stays high (no false cap, restore path).
L2 = copy.deepcopy(L)
L2["harmony_adaptation"]["target_assumptions"] = [{"capability": "x", "required": True, "target_status": "available"}]
l2r = norm(L2)
check("L2.high_kept", l2r["harmony_adaptation"].get("confidence"), "high")
check("L2.meta_high_kept", l2r["meta"].get("confidence_overall"), "high")
check("L2.fv_viable", l2r["harmony_adaptation"].get("functional_viability"), "viable")
l2_codes = [x.get("code") for x in (l2r["meta"].get("harmony_warnings") or [])]
check("L2.no_capped_warning", "confidence_capped_unknown" in l2_codes, False)


# ── Fixture M: v6 field-rename migration — legacy harmony_status on blocker/permission is moved to
#    remediation_status/grantability; the capability_profile scenario harmony_status is KEPT. Idempotent.
M = {
    "harmony_adaptation": {
        "porting_class": "needs_adaptation",
        "blockers": [{"issue": "x", "harmony_status": "replace_with_ohos", "adaptability": "adaptable"}],
        "required_permissions": [{"permission": "ohos.permission.CAMERA", "harmony_status": "restricted"}],
    },
    "capability_profile": {"scenarios": [{"key": "gui", "present": True, "harmony_status": "partial"}]},
    "meta": {},
}
m = norm(M)["harmony_adaptation"]
check("M.blocker_renamed", m["blockers"][0].get("remediation_status"), "replace_with_ohos")
check("M.blocker_old_gone", "harmony_status" in m["blockers"][0], False)
check("M.perm_renamed", m["required_permissions"][0].get("grantability"), "restricted")
check("M.perm_old_gone", "harmony_status" in m["required_permissions"][0], False)
# scenario status is a DIFFERENT field — must be untouched.
check("M.scenario_kept", norm(M)["capability_profile"]["scenarios"][0].get("harmony_status"), "partial")
# a report already using the new names normalizes to itself (no double-move / no resurrection of old key).
m2 = norm(norm(M))["harmony_adaptation"]
check("M.idempotent_blocker", m2["blockers"][0].get("remediation_status"), "replace_with_ohos")
check("M.idempotent_perm", m2["required_permissions"][0].get("grantability"), "restricted")

if _FAILS:
    print("FAIL:")
    for f in _FAILS:
        print("  -", f)
    raise SystemExit(1)
print("report_normalize selftest: all checks passed")
