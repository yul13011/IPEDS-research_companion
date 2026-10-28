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
def near(a, b):
    return a is not None and b is not None and abs(float(a) - float(b)) < 1


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


def main():
    p, t = run(COST_CASES, cost_ground_truth, cost_checks, "Cost")
    print(f"\n==================== TOTAL: {p}/{t} ====================")


if __name__ == "__main__":
    main()
