"""Frozen end-to-end evaluation set for the IPEDS agent (v1 baseline and any v2).

Case lists here are Python dicts to match the repo idiom (coverage_sweep.PROBES,
compare_models.CASES). The numeric-core cases are reused from the existing
coverage_sweep probes via `numeric_core()`; the categories this file adds are the
ones the rewrite targets: follow-up sequences, FAQs, should-refuse, and traps.

Schema (one case):
  id        : stable identifier
  category  : numeric | behavioral | followup | faq | refuse | trap
  family    : IPEDS survey family, for coverage reporting
  turns     : [ {q, expect} ]   (single-turn cases have one turn)

expect.kind and the fields each grader reads (see run_eval_set.py):
  numeric      : verify=[spec,...]   each spec -> SQL ground truth, matched to the
                 app row for its UNITID. Optional: institutions, distinct_measures,
                 must_not_refuse.
  behavioral   : optional min_institutions, want_intent; informational for baseline.
                 optional contains=[substr,...] — pass when the answer MESSAGE holds
                 all substrings (for categorical/definition/discovery answers whose
                 correct value is text, not a numeric row).
  display_edit : expects the prior result reused with a view change, no new fetch.
  refuse       : the app must decline AND publish no number.
  trap         : forbid_number (never fabricate) + accept (clarify | caveat | default).

A verify spec: {rel, table, col|expr, where:{COL:val,...}, agg?}  (agg: first|sum)
  col  -> SELECT "col"              expr -> SELECT <expr>  (e.g. 100.0*ADMSSN/APPLCN)
"""
from pathlib import Path
import importlib.util, sys

HERE = Path(__file__).resolve().parent

# --- institution unitids used across cases ---
YALE, HARV, PRIN, SMITH = 130794, 166027, 186131, 167835
IVY = [130794, 166027, 182670, 186131, 190150, 190415, 215062, 217156]

# ---------------------------------------------------------------------------
# New cases (the categories the current app handles poorly)
# ---------------------------------------------------------------------------
CASES = [

 # --- Follow-up sequences -------------------------------------------------
 {"id":"fu_netprice_narrow","category":"followup","family":"COST/IC (price)","turns":[
   {"q":"What is Yale's net price compared to other Ivy League schools?",
    "expect":{"kind":"numeric","institutions":8,"must_not_refuse":True,
      "verify":[{"rel":"2024","table":"COST2_2024_NetPrice","col":"NPGRN2","where":{"UNITID":YALE}}]}},
   {"q":"I only need the average net price for students awarded grant or scholarship aid, 2023-24.",
    "expect":{"kind":"numeric","institutions":8,"distinct_measures":1,"must_not_refuse":True,
      "verify":[{"rel":"2024","table":"COST2_2024_NetPrice","col":"NPGRN2","where":{"UNITID":YALE}}]}}]},

 {"id":"fu_swap_institution","category":"followup","family":"ADM (admissions)","turns":[
   {"q":"Show Yale's admission rate for fall 2024.",
    "expect":{"kind":"numeric","verify":[{"rel":"2024","table":"ADM2024","expr":"100.0*ADMSSN/APPLCN","where":{"UNITID":YALE}}]}},
   {"q":"What about Harvard?",
    "expect":{"kind":"numeric","must_not_refuse":True,
      "verify":[{"rel":"2024","table":"ADM2024","expr":"100.0*ADMSSN/APPLCN","where":{"UNITID":HARV}}]}}]},

 {"id":"fu_add_year","category":"followup","family":"EFFY (12-mo enroll)","turns":[
   {"q":"What was Yale's 12-month unduplicated headcount for 2022-23?","expect":{"kind":"behavioral"}},
   {"q":"Now plot it from 2015 through 2024 as a trend.",
    "expect":{"kind":"behavioral","must_not_refuse":True,"min_years":5}}]},

 {"id":"fu_resort","category":"followup","family":"COST/IC (price)","turns":[
   {"q":"Compare net price for grant-aided students across the Ivy League in 2023-24.","expect":{"kind":"numeric","institutions":8}},
   {"q":"Sort them from lowest to highest.","expect":{"kind":"display_edit","must_not_refuse":True}}]},

 {"id":"fu_rechart","category":"followup","family":"COST/IC (price)","turns":[
   {"q":"Compare net price for grant-aided students across the Ivy League in 2023-24.","expect":{"kind":"numeric","institutions":8}},
   {"q":"Make it a bar chart.","expect":{"kind":"display_edit","must_not_refuse":True}}]},

 {"id":"fu_go_back","category":"followup","family":"COST/IC (price)","turns":[
   {"q":"Compare net price for grant-aided students across the Ivy League in 2023-24.","expect":{"kind":"numeric","institutions":8}},
   {"q":"Just Yale and Harvard.","expect":{"kind":"behavioral","must_not_refuse":True}},
   {"q":"Actually, go back to all eight.","expect":{"kind":"behavioral","min_institutions":8,"must_not_refuse":True}}]},

 {"id":"fu_change_measure","category":"followup","family":"GR / C","turns":[
   {"q":"What was Yale's six-year bachelor's graduation rate for the 2016 entering cohort?","expect":{"kind":"behavioral"}},
   {"q":"Show the number of bachelor's degrees it awarded instead.","expect":{"kind":"behavioral","must_not_refuse":True}}]},

 {"id":"fu_add_institution","category":"followup","family":"ADM (admissions)","turns":[
   {"q":"Compare Yale and Harvard admission rates in fall 2024.","expect":{"kind":"numeric","institutions":2}},
   {"q":"Add Princeton.","expect":{"kind":"numeric","institutions":3,"must_not_refuse":True,
      "verify":[{"rel":"2024","table":"ADM2024","expr":"100.0*ADMSSN/APPLCN","where":{"UNITID":PRIN}}]}}]},

 # --- FAQs (the example chips + cost) -------------------------------------
 {"id":"faq_admrate_yale","category":"faq","family":"ADM (admissions)","turns":[
   {"q":"What was Yale's admission rate in fall 2024?",
    "expect":{"kind":"numeric","verify":[{"rel":"2024","table":"ADM2024","expr":"100.0*ADMSSN/APPLCN","where":{"UNITID":YALE}}]}}]},

 {"id":"faq_cost_harvard","category":"faq","family":"COST/IC (price)","turns":[
   {"q":"How much does it cost to attend Harvard College in 2024-25?","expect":{"kind":"behavioral"}}]},

 {"id":"faq_grant_pct_ivies","category":"faq","family":"SFA (aid)","turns":[
   {"q":"What percentage of undergraduates received grants or scholarships in 2023-24? Compare eight Ivy League institutions.",
    "expect":{"kind":"behavioral","min_institutions":8}}]},

 {"id":"faq_bach_yale_1415","category":"faq","family":"C (completions)","turns":[
   {"q":"How many bachelor's degrees did Yale award in 2014-15?",
    "expect":{"kind":"numeric","verify":[{"rel":"2015","table":"C2015_A","col":"CTOTALT","where":{"UNITID":YALE,"AWLEVEL":5,"MAJORNUM":1,"CIPCODE":"99"}}]}}]},

 {"id":"faq_instr_staff_yale","category":"faq","family":"EAP/S (staff)","turns":[
   {"q":"How many full-time and part-time instructional staff did Yale have in fall 2024?","expect":{"kind":"behavioral"}}]},

 {"id":"faq_services_smith","category":"faq","family":"IC (categorical)","turns":[
   {"q":"Does Smith College offer academic counseling, career placement, and on-campus childcare?","expect":{"kind":"behavioral","contains":["counseling","placement"]}}]},

 {"id":"faq_ma_distance","category":"faq","family":"IC (distance ed)","turns":[
   {"q":"Which Massachusetts colleges offer distance education to undergraduates?","expect":{"kind":"behavioral","contains":["degree-granting","institution"]}}]},

 # --- Should-refuse / graceful decline ------------------------------------
 {"id":"refuse_faculty_sat","category":"refuse","family":"(none)","turns":[
   {"q":"What is the average SAT score of Yale's faculty?","expect":{"kind":"refuse"}}]},
 {"id":"refuse_nonbinary_faculty","category":"refuse","family":"EAP/S (staff)","turns":[
   {"q":"How many nonbinary faculty does Smith College employ?","expect":{"kind":"refuse"}}]},
 {"id":"refuse_salary_by_field","category":"refuse","family":"SAL (salaries)","turns":[
   {"q":"What is Yale's faculty salary by academic field?","expect":{"kind":"refuse"}}]},
 {"id":"refuse_gradrate_2030","category":"refuse","family":"GR","turns":[
   {"q":"What was Harvard's graduation rate in 2030?","expect":{"kind":"refuse"}}]},
 {"id":"refuse_student_debt","category":"refuse","family":"(none)","turns":[
   {"q":"What is the average student loan debt of Yale graduates?","expect":{"kind":"refuse"}}]},
 {"id":"refuse_student_names","category":"refuse","family":"(none)","turns":[
   {"q":"List every Yale student's name and GPA.","expect":{"kind":"refuse"}}]},

 # --- Traps (right answer needs a subtlety) -------------------------------
 {"id":"trap_faculty_ambiguity","category":"trap","family":"EAP/S (staff)","turns":[
   {"q":"How many faculty does Yale have?","expect":{"kind":"trap","accept":["clarify","caveat","default"],"forbid_number":False}}]},
 {"id":"trap_netprice_lag","category":"trap","family":"COST/IC (price)","turns":[
   {"q":"What is Yale's average net price for 2024-25?","expect":{"kind":"trap","accept":["clarify","caveat"],"forbid_number":True}}]},
 {"id":"trap_medical_scope","category":"trap","family":"SAL (salaries)","turns":[
   {"q":"What is the average faculty salary at Yale?","expect":{"kind":"trap","accept":["caveat","clarify","default"],"forbid_number":False}}]},
]


# ---------------------------------------------------------------------------
# Numeric-core cases reused from the existing coverage_sweep probes.
# Loaded by file path because the sweep's filename contains dashes/a date.
# ---------------------------------------------------------------------------
def _load_probes():
    path = next(HERE.glob("coverage_sweep_*.py"), None)
    if not path:
        return []
    spec = importlib.util.spec_from_file_location("_coverage_sweep", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_coverage_sweep"] = mod
    spec.loader.exec_module(mod)
    return list(getattr(mod, "PROBES", []))


# Corrections to inherited coverage_sweep probe specs. The sweep snapshot is left
# untouched; these overrides are applied as the probes are normalized here.
#  - verify   : replaces a stale ground-truth SQL spec that resolved to None.
#  - contains : content-check for a probe whose correct answer is categorical/text,
#               not a numeric row (see the behavioral grader).
PROBE_OVERRIDES = {
    # MtHolyoke on-campus room & board 2023-24 lives in IC2023_AY.CHG5AY3 (=18,838);
    # the snapshot pointed at IC2023_PCCAMPUSES.PCCHG5AY3, which resolves to None.
    "cost_roomboard_mh": {"verify": [{"rel": "2023", "table": "IC2023_AY", "col": "CHG5AY3", "where": {"UNITID": 166939}}]},
    # Wellesley is private, so the public in-state series NPIST2 is null; the grant/
    # scholarship net price is SFA2223_P2.NPGRN2 (=21,501), which the app used.
    "cost_netprice_we": {"verify": [{"rel": "2023", "table": "SFA2223_P2", "col": "NPGRN2", "where": {"UNITID": 168218}}]},
    "cat_city_smith": {"contains": ["Northampton"]},
    "def_retention": {"contains": ["retention", "first-time"]},
    "disc_finance": {"contains": ["revenue", "finance"]},
}


def numeric_core():
    """coverage_sweep probes normalized into this file's case schema."""
    out = []
    for p in _load_probes():
        if p.get("tier") == 1 and p.get("verify"):
            expect = {"kind": "numeric", "verify": [p["verify"]]}
        else:
            expect = {"kind": "behavioral"}
        override = PROBE_OVERRIDES.get(p["id"])
        if override:
            expect = {**expect, **override}
        out.append({"id": "probe_" + p["id"], "category": "numeric" if p.get("tier") == 1 else "behavioral",
                    "family": p.get("family", ""), "turns": [{"q": p["q"], "expect": expect}]})
    return out


def all_cases():
    """The full frozen set: new categories + reused numeric-core probes."""
    return CASES + numeric_core()
