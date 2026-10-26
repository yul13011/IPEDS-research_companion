"""Broad diagnostic batch over the real IPEDS pipeline (same code the UI calls).
Runs ask(q, previous, use_model=True, model='automatic') per case and records
intent, whether a numeric result was published, top values, latency, model cost.
Read-only; no app files changed. Prints one JSON line per case and writes a report.
"""
from pathlib import Path
import sys, json, time, datetime

ROOT = Path(r"C:\Users\liyuj\OneDrive\2026\IPEDS Project\agent-redesign")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".packages"))

from prototype.agent import ask  # noqa: E402
from prototype.intent_router import handle  # noqa: E402
from prototype.working_analysis import recent_result  # noqa: E402

OUT = Path(__file__).resolve().parent / "batch_probe_results.json"

# (id, category, question, followup_of_id or None)
CASES = [
    ("rev_adm",   "reviewed",      "What was Yale's admission rate in fall 2024?", None),
    ("rev_grad",  "reviewed-trend","Plot Yale's six-year graduation rate for entering cohorts 2009 through 2018.", None),
    ("cat_lib",   "catalog-1inst", "How many books were in Harvard's library collection in 2023?", None),
    ("cat_enr",   "catalog-1inst", "What was Smith College's total fall enrollment in 2023?", None),
    ("cat_fin",   "catalog-1inst", "What was Yale's total revenue from tuition and fees in 2022-23?", None),
    ("cat_ret",   "catalog-1inst", "What was the first-year student retention rate at Mount Holyoke College in 2023?", None),
    ("agg_grad",  "aggregate",     "What was the overall six-year graduation rate for four-year institutions in the United States for the 2016 entering cohort?", None),
    ("agg_count", "aggregate",     "How many degree-granting institutions reported to IPEDS in 2023?", None),
    ("agg_enr",   "aggregate",     "What was the total fall enrollment across all U.S. degree-granting institutions in 2023?", None),
    ("cmp_grad",  "comparison",    "Compare the six-year graduation rates of Yale, Harvard, and Princeton for the 2015 entering cohort.", None),
    ("cmp_sal",   "comparison",    "Compare the average full-time instructional faculty salary at Smith, Mount Holyoke, and Wellesley in 2023-24.", None),
    ("amb_fac",   "ambiguous",     "How many faculty does Yale have?", None),
    ("amb_aid",   "ambiguous",     "What is Yale's financial aid?", None),
    ("trd_awd",   "catalog-trend", "Plot the number of bachelor's degrees Yale awarded each year from 2015 to 2024.", None),
    ("def_grad",  "definition",    "What is the definition of the six-year graduation rate?", None),
    ("disc_aid",  "discovery",     "What data do you have on student financial aid?", None),
    ("edge_urm",  "unsupported",   "What is the URM six-year graduation rate at Yale?", None),
    ("fu_base",   "followup",      "How many bachelor's degrees did Yale award in 2015?", None),
    ("fu_next",   "followup",      "What about Harvard?", "fu_base"),
]


def summarize(ans):
    res = ans.get("result") or {}
    rows = res.get("rows") or []
    top = []
    for r in rows[:6]:
        top.append({
            "metric": r.get("metric"),
            "value": r.get("value"),
            "unitid": r.get("unitid"),
            "period": r.get("period") or r.get("year"),
            "label": r.get("label") or r.get("institution"),
        })
    lat = ans.get("latency") or {}
    usage = ans.get("model_usage") or {}
    plan = ans.get("plan") or ans.get("catalog_plan") or {}
    msg = ans.get("message") or ""
    return {
        "intent": ans.get("intent"),
        "mode": ans.get("mode"),
        "published": bool(rows),
        "n_rows": len(rows),
        "observation_years": res.get("observation_years"),
        "metrics": (plan.get("metrics") if isinstance(plan, dict) else None),
        "top_rows": top,
        "message": msg[:400],
        "answer_ready_seconds": lat.get("answer_ready_seconds"),
        "live_model_calls": lat.get("live_model_calls"),
        "estimated_api_usd": usage.get("estimated_api_usd"),
        "n_evidence": len(ans.get("evidence") or []),
    }


def main():
    answers = {}  # id -> answer dict (for building follow-up history)
    records = []
    for cid, cat, q, fu in CASES:
        if fu and fu in answers:
            history = [{"question": next(c[2] for c in CASES if c[0] == fu), "answer": answers[fu]}]
            previous = recent_result(history)
        else:
            history, previous = [], None
        rec = {"id": cid, "category": cat, "question": q, "followup_of": fu}
        t0 = time.perf_counter()
        try:
            ans = handle(q, previous, "automatic", history, ask)
            rec.update(summarize(ans))
            rec["ok"] = True
            answers[cid] = ans
        except Exception as exc:
            rec.update({"ok": False, "error_type": type(exc).__name__, "error": str(exc)[:400]})
        rec["wall_seconds"] = round(time.perf_counter() - t0, 2)
        records.append(rec)
        print(json.dumps({k: rec.get(k) for k in
                          ["id", "category", "intent", "published", "n_rows",
                           "wall_seconds", "live_model_calls", "estimated_api_usd",
                           "ok", "error_type"]}, ensure_ascii=False), flush=True)
    report = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "n_cases": len(records),
        "cases": records,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
