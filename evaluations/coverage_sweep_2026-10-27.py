"""Wide coverage sweep across IPEDS survey families, through the real pipeline, with a
hard cumulative API-cost cap. Saves raw results (incl. each probe's ground-truth spec)
for the separate matrix builder. Read-only; no app files changed."""
from pathlib import Path
import sys, json, time, datetime

ROOT = Path(r"C:\Users\liyuj\OneDrive\2026\IPEDS Project\agent-redesign")
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / ".packages"))
from prototype.agent import ask            # noqa: E402
from prototype.intent_router import handle  # noqa: E402

OUT = Path(__file__).resolve().parent / "coverage_sweep_raw.json"
COST_CAP_USD = 5.00

# unitids
Y, H, P, SM, MH, WE = 130794, 166027, 186131, 167835, 166939, 168218

# Each probe: id, family, q, tier(1=has ground-truth spec, 2=behavioral).
# verify (tier 1): {rel, table, col, where:{COL:val}, agg:'first'|'sum'}
PROBES = [
 # Completions
 {"id":"c_mast_yale","family":"C (completions)","tier":1,"q":"How many master's degrees did Yale award in 2023?",
  "verify":{"rel":"2023","table":"C2023_A","col":"CTOTALT","where":{"UNITID":Y,"AWLEVEL":"7","CIPCODE":"99","MAJORNUM":"1"}}},
 {"id":"c_doc_harv","family":"C (completions)","tier":1,"q":"How many research doctoral degrees did Harvard award in 2023?",
  "verify":{"rel":"2023","table":"C2023_A","col":"CTOTALT","where":{"UNITID":H,"AWLEVEL":"17","CIPCODE":"99","MAJORNUM":"1"}}},
 {"id":"c_cmp_bach","family":"C (completions)","tier":2,"q":"Compare the number of bachelor's degrees Yale and Princeton awarded in 2023."},
 # Library
 {"id":"al_books_harv","family":"AL (libraries)","tier":1,"q":"How many physical books were in Harvard's library collection in 2023?",
  "verify":{"rel":"2023","table":"AL2023","col":"LPBOOKS","where":{"UNITID":H}}},
 {"id":"al_ebooks_yale","family":"AL (libraries)","tier":1,"q":"How many digital/electronic books does Yale's library have in 2023?",
  "verify":{"rel":"2023","table":"AL2023","col":"LEBOOKS","where":{"UNITID":Y}}},
 # Salaries
 {"id":"sal_prof_smith","family":"SAL (salaries)","tier":1,"q":"What was the average salary of full professors at Smith College in 2023-24?",
  "verify":{"rel":"2023","table":"SAL2023_IS","col":"SAEQ9AT","where":{"UNITID":SM,"ARANK":1}}},
 {"id":"sal_cmp","family":"SAL (salaries)","tier":2,"q":"Compare the average instructional faculty salary at Smith, Mount Holyoke, and Wellesley in 2023-24."},
 # Finance
 {"id":"f_tuitrev_yale","family":"F (finance)","tier":1,"q":"What was Yale's revenue from tuition and fees in 2022-23?",
  "verify":{"rel":"2023","table":"F2223_F2","col":"F2D01","where":{"UNITID":Y}}},
 {"id":"f_expenses_yale","family":"F (finance)","tier":2,"q":"What were Yale's total expenses in 2022-23?"},
 {"id":"f_endow_harv","family":"F (finance)","tier":2,"q":"What was the value of Harvard's endowment at year end 2022-23?"},
 # Faculty / staff
 {"id":"eap_fac_yale","family":"EAP/S (staff)","tier":2,"q":"How many full-time instructional faculty with faculty status does Yale have in fall 2023?"},
 {"id":"s_total_smith","family":"EAP/S (staff)","tier":2,"q":"How many total staff does Smith College employ in 2023?"},
 # Outcome measures
 {"id":"om_rate_yale","family":"OM (outcomes)","tier":1,"q":"What share of Yale's entering degree-seeking cohort earned an award within 8 years (2023)?",
  "verify":{"rel":"2023","table":"DRVOM2023","col":"OM1TOTLAWDP8","where":{"UNITID":Y}}},
 {"id":"om_behav","family":"OM (outcomes)","tier":2,"q":"What is the 8-year completion rate for Pell recipients at Arizona State University?"},
 # Enrollment / 12-month
 {"id":"effy_yale","family":"EFFY (12-mo enroll)","tier":1,"q":"What was Yale's 12-month unduplicated headcount for 2022-23?",
  "verify":{"rel":"2023","table":"EFFY2023","col":"EFYTOTLT","where":{"UNITID":Y,"EFFYLEV":1}}},
 {"id":"ef_dist_yale","family":"EF (distance ed)","tier":2,"q":"How many Yale students were enrolled exclusively in distance education in fall 2023?"},
 {"id":"ef_race_yale","family":"EF (enrollment)","tier":2,"q":"Show Yale's undergraduate enrollment by race and ethnicity for fall 2023."},
 # Cost / price / IC
 {"id":"cost_tuit_smith","family":"COST/IC (price)","tier":1,"q":"What was the published tuition and fees at Smith College for 2023-24?",
  "verify":{"rel":"2024","table":"COST1_2024","col":"chg3ay2","where":{"UNITID":SM}}},
 {"id":"cost_roomboard_mh","family":"COST/IC (price)","tier":1,"q":"What was the on-campus room and board charge at Mount Holyoke College for 2023-24?",
  "verify":{"rel":"2023","table":"IC2023_PCCAMPUSES","col":"PCCHG5AY3","where":{"UNITID":MH}}},
 {"id":"cost_netprice_we","family":"COST/IC (price)","tier":1,"q":"What was the average net price for grant-aided students at Wellesley in 2022-23?",
  "verify":{"rel":"2023","table":"SFA2223_P2","col":"NPIST2","where":{"unitid":WE}}},
 # Admissions detail
 {"id":"adm_act_yale","family":"ADM (admissions)","tier":1,"q":"How many of Yale's admitted students submitted ACT scores for fall 2024?",
  "verify":{"rel":"2024","table":"ADM2024","col":"ACTNUM","where":{"UNITID":Y}}},
 {"id":"adm_req_yale","family":"ADM (admissions)","tier":2,"q":"What are Yale's admissions test score requirements?"},
 # Aggregates / populations
 {"id":"agg_gradrate","family":"Aggregate","tier":2,"q":"What was the overall six-year graduation rate for four-year institutions in the United States for the 2016 entering cohort?"},
 {"id":"agg_instcount","family":"Aggregate","tier":2,"q":"How many public four-year institutions are there in 2023?"},
 {"id":"agg_totalenr","family":"Aggregate","tier":2,"q":"What was the total fall enrollment across all U.S. degree-granting institutions in 2023?"},
 # Definitions / discovery
 {"id":"def_retention","family":"Definition","tier":2,"q":"What is the definition of the first-year retention rate?"},
 {"id":"disc_finance","family":"Discovery","tier":2,"q":"What data do you have on institutional finances?"},
 # Trend
 {"id":"trend_effy_yale","family":"Trend","tier":2,"q":"Plot Yale's 12-month enrollment from 2015 to 2024."},
 # Categorical / IC attributes
 {"id":"cat_housing_smith","family":"IC (categorical)","tier":2,"q":"Does Smith College provide on-campus housing?"},
 {"id":"cat_city_smith","family":"HD (directory)","tier":2,"q":"What city is Smith College located in?"},
]


def summarize(ans):
    res = ans.get("result") or {}
    rows = res.get("rows") or []
    top = [{"metric": r.get("metric"), "value": r.get("value"), "unitid": r.get("unitid"),
            "label": r.get("label") or r.get("institution")} for r in rows[:4]]
    lat = ans.get("latency") or {}; usage = ans.get("model_usage") or {}
    return {"intent": ans.get("intent"), "mode": ans.get("mode"), "published": bool(rows),
            "n_rows": len(rows), "top_rows": top, "message": (ans.get("message") or "")[:300],
            "answer_ready_seconds": lat.get("answer_ready_seconds"),
            "estimated_api_usd": usage.get("estimated_api_usd")}


def main():
    records = []; spent = 0.0; stopped = None
    for pr in PROBES:
        if spent >= COST_CAP_USD:
            stopped = pr["id"]; break
        rec = {k: pr.get(k) for k in ("id", "family", "tier", "q", "verify")}
        t0 = time.perf_counter()
        try:
            ans = handle(pr["q"], None, "automatic", [], ask)
            s = summarize(ans); rec.update(s); rec["ok"] = True
            spent += (s.get("estimated_api_usd") or 0.0)
        except Exception as exc:
            rec.update({"ok": False, "error_type": type(exc).__name__, "error": str(exc)[:200]})
        rec["wall_seconds"] = round(time.perf_counter() - t0, 1)
        rec["cum_cost_usd"] = round(spent, 4)
        records.append(rec)
        print(json.dumps({k: rec.get(k) for k in ("id","family","intent","published","wall_seconds","cum_cost_usd","ok")}), flush=True)
    report = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "cost_cap_usd": COST_CAP_USD, "total_spent_usd": round(spent, 4),
              "n_run": len(records), "n_total": len(PROBES), "stopped_at_cap_before": stopped,
              "records": records}
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"SPENT ${spent:.4f} over {len(records)}/{len(PROBES)} probes"
          + (f" (cap hit before {stopped})" if stopped else ""), flush=True)
    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
