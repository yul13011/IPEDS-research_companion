"""Example-question eval harness.

Runs each example question through the REAL pipeline (the same handle() the live app uses),
recomputes ground truth from the current IPEDS data (so nothing is hardcoded or goes stale),
and reports per-check pass/fail. Mirrors EXAMPLE_QUESTIONS.md; seeded with the Cost section.

Run with the bundled Python (makes real API calls; ~$0.3 for the cost set):
    <python> evaluations/eval_harness.py
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / ".packages"), str(ROOT)]
from prototype.agent import ask
from prototype.intent_router import handle
from prototype.semantics import display_result, is_currency
from prototype.catalog import annual_path, readonly


# ---- ground truth, recomputed from the data (never hardcoded) --------------------------------
def cost_ground_truth(unitid):
    with readonly(annual_path(2024)) as db:
        cind, cins, cots = db.execute(
            "SELECT CINDON,CINSON,COTSON FROM DRVCOST2024 WHERE UNITID=?", (unitid,)).fetchone()
        npr = db.execute(
            "SELECT NPIST2,NPGRN2,NPT42 FROM COST2_2024_netprice WHERE UNITID=?", (unitid,)).fetchone()
    net = next((x for x in npr if x is not None), None)   # first populated net-price field
    return {"in_state": cins, "out_state": cots, "single_total": cins == cots, "net_price": net}


# ---- cases (mirror EXAMPLE_QUESTIONS.md -> Cost) ----------------------------------------------
COST_CASES = [
    {"id": "cost_uconn", "q": "What is the cost of attending University of Connecticut?", "unitid": 129020},
    {"id": "cost_yale",  "q": "What is the cost of attending Yale University?",            "unitid": 130794},
    {"id": "cost_scsu",  "q": "What is the cost of attending Southern Connecticut State University?", "unitid": 130493},
]


# ---- checks ----------------------------------------------------------------------------------
def near(a, b, tol=0.5):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def cost_checks(answer, gt):
    res = answer.get("result") or {}
    rows = display_result(res)["rows"] if res.get("rows") else []
    vals = [r.get("value") for r in rows]
    units = [r.get("unit") for r in rows]
    out = [("answered (not a clarify/error)", answer.get("intent") == "analyze" and bool(rows))]
    out.append(("in-state total present & correct", any(near(v, gt["in_state"]) for v in vals)))
    if gt["single_total"]:
        n = sum(1 for v in vals if near(v, gt["in_state"]))
        out.append(("private: one published total (no duplicate residency row)", n == 1))
    else:
        out.append(("public: out-of-state total present & differs from in-state",
                    any(near(v, gt["out_state"]) for v in vals) and not near(gt["in_state"], gt["out_state"])))
    out.append(("totals shown in currency (USD)", any(is_currency(u) for u in units)))
    out.append(("average net price present & correct", any(near(v, gt["net_price"]) for v in vals)))
    return out


def run(cases, gt_fn, check_fn, label):
    print(f"\n########## {label} ##########")
    total = passed = 0
    for c in cases:
        gt = gt_fn(c["unitid"])
        ans = handle(c["q"], None, "automatic", [], ask)
        print(f"\n=== {c['id']}: {c['q']}")
        print(f"    ground truth: in-state={gt['in_state']} out-of-state={gt['out_state']} "
              f"single_total={gt['single_total']} net_price={gt['net_price']}")
        for name, ok in check_fn(ans, gt):
            total += 1; passed += bool(ok)
            print(f"    [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n{label}: {passed}/{total} checks passed")
    return passed, total


# ---- value cases: a question with one or more expected numbers present in the answer ----------
def run_value_cases(build, label):
    print(f"\n########## {label} ##########")
    total = passed = 0
    for c in build():
        ans = handle(c["q"], None, "automatic", [], ask)
        rows = display_result(ans["result"])["rows"] if (ans.get("result") or {}).get("rows") else []
        vals = [r.get("value") for r in rows]
        checks = [("answered (not a clarify/error)", ans.get("intent") == "analyze" and bool(vals))]
        for e in c["expect"]:
            checks.append((f"contains {e:g}", any(near(v, e, c.get("tol", 0.5)) for v in vals)))
        print(f"\n=== {c['id']}: {c['q']}")
        print(f"    expected {['%g' % e for e in c['expect']]}  |  got {['%g' % v for v in vals if v is not None][:8]}")
        for name, ok in checks:
            total += 1; passed += bool(ok); print(f"    [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n{label}: {passed}/{total} checks passed")
    return passed, total


def adm_grad_cases():
    """Yale admissions + graduation, ground truth recomputed from ADM/GR per the verified benchmark
    (evaluations/run_yale_benchmarks.py). Mirrors EXAMPLE_QUESTIONS.md -> Admissions / Graduation."""
    Y = 130794
    with readonly(annual_path(2024)) as db:
        appl, adm, enr = db.execute("SELECT APPLCN,ADMSSN,ENRLT FROM ADM2024 WHERE UNITID=?", (Y,)).fetchone()
        g8 = db.execute("SELECT GRTOTLT FROM GR2024 WHERE UNITID=? AND GRTYPE=8", (Y,)).fetchone()[0]
        g12 = db.execute("SELECT GRTOTLT FROM GR2024 WHERE UNITID=? AND GRTYPE=12", (Y,)).fetchone()[0]
    with readonly(annual_path(2023)) as db:
        adm23, enr23 = db.execute("SELECT ADMSSN,ENRLT FROM ADM2023 WHERE UNITID=?", (Y,)).fetchone()
        v25, v75, m25, m75 = db.execute("SELECT SATVR25,SATVR75,SATMT25,SATMT75 FROM ADM2023 WHERE UNITID=?", (Y,)).fetchone()
    return [
        {"id": "adm_rate",  "q": "What was Yale's admission rate in fall 2024?",          "expect": [100*adm/appl], "tol": 0.1},
        {"id": "adm_apps",  "q": "How many applications did Yale receive for fall 2024?", "expect": [appl],          "tol": 0.5},
        {"id": "adm_admit_enroll", "q": "How many students did Yale admit and enroll in fall 2024?", "expect": [adm, enr], "tol": 0.5},
        {"id": "adm_yield", "q": "What was Yale's yield rate for fall 2023?",             "expect": [100*enr23/adm23], "tol": 0.2},
        {"id": "sat",       "q": "What were Yale's 25th and 75th percentile SAT scores for the entering class of fall 2023?", "expect": [v25, v75, m25, m75], "tol": 0.5},
        {"id": "grad_rate", "q": "What was Yale's six-year graduation rate for the 2018 entering cohort?", "expect": [100*g12/g8], "tol": 0.6},
        {"id": "grad_counts", "q": "How many students were in Yale's 2018 entering cohort, and how many graduated within six years?", "expect": [g8, g12], "tol": 0.5},
    ]


def fall_enrollment_cases():
    """Yale fall enrollment by level, recomputed from EF2023. Mirrors EXAMPLE_QUESTIONS.md -> Fall Enrollment."""
    Y = 130794
    with readonly(annual_path(2023)) as db:
        tot = db.execute("SELECT EFTOTAL FROM EF2023 WHERE UNITID=? AND EFLEVEL=10", (Y,)).fetchone()[0]
        ug = db.execute("SELECT EFTOTAL FROM EF2023 WHERE UNITID=? AND EFLEVEL=20", (Y,)).fetchone()[0]
        gr = db.execute("SELECT EFTOTAL FROM EF2023 WHERE UNITID=? AND EFLEVEL=50", (Y,)).fetchone()[0]
    return [
        {"id": "enr_total",     "q": "How many students were enrolled at Yale in fall 2023?", "expect": [tot], "tol": 0.5},
        {"id": "enr_undergrad", "q": "How many undergraduates were enrolled at Yale in fall 2023?", "expect": [ug], "tol": 0.5},
        {"id": "enr_grad",      "q": "How many graduate and professional students were enrolled at Yale in fall 2023?", "expect": [gr], "tol": 0.5},
    ]


def grad_subgroup_cases():
    """Yale six-year graduation-rate subgroups (2018 cohort -> GR2024), recomputed per the benchmark."""
    Y = 130794
    with readonly(annual_path(2024)) as db:
        m8, w8, nr8 = db.execute("SELECT GRTOTLM,GRTOTLW,GRNRALT FROM GR2024 WHERE UNITID=? AND GRTYPE=8", (Y,)).fetchone()
        m12, w12, nr12 = db.execute("SELECT GRTOTLM,GRTOTLW,GRNRALT FROM GR2024 WHERE UNITID=? AND GRTYPE=12", (Y,)).fetchone()
        pga, pgc = db.execute("SELECT PGADJCT,PGCMBAC FROM GR2024_PELL_SSL WHERE UNITID=? AND PSGRTYPE=2", (Y,)).fetchone()
    return [
        {"id": "grad_gender", "q": "What was Yale's six-year graduation rate by gender for the 2018 entering cohort?", "expect": [100*m12/m8, 100*w12/w8], "tol": 0.6},
        {"id": "grad_pell",   "q": "What was Yale's six-year graduation rate for Pell recipients in the 2018 entering cohort?", "expect": [100*pgc/pga], "tol": 0.6},
        {"id": "grad_intl",   "q": "What was Yale's six-year graduation rate for nonresident students in the 2018 entering cohort?", "expect": [100*nr12/nr8], "tol": 0.6},
    ]


def aggregate_cases():
    """National aggregates, recomputed with the Title IV degree-granting universe (FIPS 1-56,
    PSET4FLG 1/3). Degree counts match exactly; the grad rate carries a small universe tolerance.
    (National enrollment is universe-sensitive, so it is documented but not strictly eval-checked.)"""
    U = "h.FIPS BETWEEN 1 AND 56 AND h.PSET4FLG IN (1,3)"
    with readonly(annual_path(2023)) as db:
        bach = db.execute(f"SELECT SUM(c.CTOTALT) FROM C2023_A c JOIN HD2023 h ON c.UNITID=h.UNITID WHERE c.CIPCODE='99' AND c.MAJORNUM=1 AND c.AWLEVEL=5 AND {U}").fetchone()[0]
        mast = db.execute(f"SELECT SUM(c.CTOTALT) FROM C2023_A c JOIN HD2023 h ON c.UNITID=h.UNITID WHERE c.CIPCODE='99' AND c.MAJORNUM=1 AND c.AWLEVEL=7 AND {U}").fetchone()[0]
    with readonly(annual_path(2022)) as db:
        g12 = db.execute(f"SELECT SUM(g.GRTOTLT) FROM GR2022 g JOIN HD2022 h ON g.UNITID=h.UNITID WHERE g.GRTYPE=12 AND {U}").fetchone()[0]
        g8 = db.execute(f"SELECT SUM(g.GRTOTLT) FROM GR2022 g JOIN HD2022 h ON g.UNITID=h.UNITID WHERE g.GRTYPE=8 AND {U}").fetchone()[0]
    return [
        {"id": "agg_bachelors", "q": "How many bachelor's degrees were awarded nationally in 2023?", "expect": [bach], "tol": 0.5},
        {"id": "agg_masters",   "q": "How many master's degrees were awarded nationally in 2023?",   "expect": [mast], "tol": 0.5},
        {"id": "agg_gradrate",  "q": "What was the national six-year graduation rate for the 2016 entering cohort?", "expect": [100*g12/g8], "tol": 0.6},
    ]


def main():
    p1, t1 = run(COST_CASES, cost_ground_truth, cost_checks, "Cost")
    p2, t2 = run_value_cases(adm_grad_cases, "Admissions & Graduation (Yale)")
    p3, t3 = run_value_cases(fall_enrollment_cases, "Fall Enrollment (Yale)")
    p4, t4 = run_value_cases(grad_subgroup_cases, "Graduation subgroups (Yale)")
    p5, t5 = run_value_cases(aggregate_cases, "Aggregate / National")
    P, T = p1+p2+p3+p4+p5, t1+t2+t3+t4+t5
    print(f"\n==================== TOTAL: {P}/{T} ====================")


if __name__ == "__main__":
    main()
