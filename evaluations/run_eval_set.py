"""Run the frozen eval set (eval_set.py) through the real app pipeline and score it.

  python run_eval_set.py --validate      # no API: check every ground-truth spec resolves + grader self-test
  python run_eval_set.py --smoke 3       # live: first 3 cases only
  python run_eval_set.py                  # live: all cases, under the cost cap
  python run_eval_set.py --only fu_       # live: cases whose id starts with fu_

Grades v1 today; run the same file against v2 later for an apples-to-apples compare.
Ground truth is computed by SQL against the release SQLite, never by the model.
"""
from pathlib import Path
import argparse, datetime, json, sqlite3, statistics, sys, time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / ".packages"), str(ROOT)]
DATA = ROOT / "data" / "annual"

from eval_set import all_cases, YALE, HARV, PRIN  # noqa: E402

COST_CAP_USD = 5.00
PASS = {"CORRECT", "PASS-REFUSE", "SOFT-DECLINE", "PASS-CLARIFY", "PASS-EDIT", "ANSWERED"}
REVIEW = {"REVIEW", "REVIEW-ANSWERED", "REVIEW-EDIT", "NO-GROUND-TRUTH"}


# --- ground truth --------------------------------------------------------
def reldb(rel):
    hit = next(iter(sorted(DATA.glob(f"IPEDS_{rel}-*/*.sqlite"))), None)
    return hit


def expected(spec):
    path = reldb(spec["rel"])
    if not path:
        return None
    db = sqlite3.connect(path)
    try:
        where = spec.get("where", {})
        conds = " AND ".join(f'"{k}"=?' for k in where)
        if "expr" in spec:
            sel = spec["expr"]
        else:
            col = spec["col"]
            sel = f'SUM("{col}")' if spec.get("agg") == "sum" else f'"{col}"'
        q = f'SELECT {sel} FROM "{spec["table"]}"' + (f" WHERE {conds}" if conds else "")
        row = db.execute(q, list(where.values())).fetchone()
        return None if not row else row[0]
    finally:
        db.close()


# --- answer inspection ---------------------------------------------------
def rows_of(ans):
    return (ans.get("result") or {}).get("rows") or []


def has_number(ans):
    return any(r.get("value") is not None for r in rows_of(ans))


def is_refusal(ans):
    if ans.get("intent") == "clarify":
        return True
    return (ans.get("intent_validation") or {}).get("status") == "blocked"


def distinct(ans, key):
    return len({r.get(key) for r in rows_of(ans) if r.get(key) is not None})


def app_values(ans, unitid):
    return [r.get("value") for r in rows_of(ans)
            if r.get("value") is not None and (unitid is None or r.get("unitid") == unitid)]


def close(a, b):
    try:
        a, b = float(a), float(b)
        return abs(a - b) <= max(1.0, 0.01 * abs(b))
    except Exception:
        return False


def _uid(spec):
    w = spec.get("where", {})
    return w.get("UNITID") or w.get("unitId") or w.get("unitid")


# --- grader --------------------------------------------------------------
def grade_turn(turn, ans):
    e = turn["expect"]; kind = e["kind"]; refusal = is_refusal(ans)
    if e.get("must_not_refuse") and refusal:
        return "FALSE-REFUSAL", (ans.get("message") or "")[:90], {"false_refusal": True}

    if kind == "refuse":
        if has_number(ans):
            return "FAIL-ANSWERED-ANYWAY", f"n_rows={len(rows_of(ans))}", {}
        if refusal:
            return "PASS-REFUSE", "", {}
        return "SOFT-DECLINE", (ans.get("message") or "")[:80], {}

    if kind == "trap":
        if e.get("forbid_number") and has_number(ans):
            return "FAIL-FABRICATED", "published a number for a lagged/absent measure", {}
        if refusal:
            return "PASS-CLARIFY", "", {}
        if has_number(ans):
            return "REVIEW-ANSWERED", "verify caveat by hand", {}
        return "REVIEW", (ans.get("message") or "")[:60], {}

    if kind == "display_edit":
        mode = (ans.get("mode") or "").lower()
        reused = "adjust" in mode or "presentation" in mode or (ans.get("model_usage") or {}).get("calls", 1) == 0
        if has_number(ans) and reused:
            return "PASS-EDIT", mode, {}
        if has_number(ans):
            return "REVIEW-EDIT", f"mode={mode}", {}
        return "FAIL-EDIT", (ans.get("message") or "")[:60], {}

    if kind == "numeric":
        if refusal:
            return "BLOCKED", (ans.get("message") or "")[:60], {}
        det = ""
        if e.get("institutions") and distinct(ans, "unitid") != e["institutions"]:
            det = f'inst={distinct(ans, "unitid")} want {e["institutions"]}'
        if e.get("distinct_measures") and distinct(ans, "metric") != e["distinct_measures"]:
            det = (det + f' measures={distinct(ans, "metric")} want {e["distinct_measures"]}').strip()
        checks = []
        for spec in e.get("verify", []):
            exp = expected(spec)
            vals = app_values(ans, _uid(spec))
            if exp is None:
                checks.append(("NOGT", exp, vals))
            elif any(close(v, exp) for v in vals):
                checks.append(("OK", exp, vals))
            else:
                checks.append(("BAD", exp, vals))
        states = [c[0] for c in checks]
        if "BAD" in states:
            verdict = "WRONG-NUMBER"
        elif checks and "OK" not in states and "NOGT" in states:
            verdict = "NO-GROUND-TRUTH"
        elif not checks:
            verdict = "ANSWERED" if has_number(ans) else "BLOCKED"
        else:
            verdict = "CORRECT"
        if det and verdict == "CORRECT":
            verdict = "CONSTRAINT-MISS"
        return verdict, (det or str([(c[0], c[1]) for c in checks])[:90]), {}

    # behavioral
    if refusal:
        return "CLARIFY", (ans.get("message") or "")[:60], {}
    if e.get("min_institutions") and distinct(ans, "unitid") < e["min_institutions"]:
        return "FEW-INSTITUTIONS", f'inst={distinct(ans, "unitid")}', {}
    if has_number(ans):
        return "ANSWERED", f"rows={len(rows_of(ans))}", {}
    return "NO-RESULT", (ans.get("message") or "")[:60], {}


# --- live driving --------------------------------------------------------
def run_case(case, spent):
    from prototype.intent_router import handle
    from prototype.agent import ask
    history, previous, out = [], None, []
    for t in case["turns"]:
        if spent[0] >= COST_CAP_USD:
            out.append({"q": t["q"], "verdict": "SKIPPED-CAP"}); break
        t0 = time.perf_counter()
        try:
            ans = handle(t["q"], previous, "automatic", history, ask)
            verdict, detail, flags = grade_turn(t, ans)
        except Exception as exc:
            ans = {"intent": "error", "message": f"{type(exc).__name__}: {exc}"}
            verdict, detail, flags = "ERROR", type(exc).__name__, {}
        usd = (ans.get("model_usage") or {}).get("estimated_api_usd") or 0.0
        spent[0] += usd
        out.append({"q": t["q"], "kind": t["expect"]["kind"], "verdict": verdict, "detail": detail,
                    "false_refusal": flags.get("false_refusal", False), "intent": ans.get("intent"),
                    "mode": ans.get("mode"), "n_rows": len(rows_of(ans)),
                    "wall_s": round(time.perf_counter() - t0, 1), "usd": round(usd, 4),
                    "message": (ans.get("message") or "")[:160]})
        history = history + [{"question": t["q"], "answer": ans}]
        previous = ans
    passed = bool(out) and all(o.get("verdict") in PASS for o in out)
    return {"id": case["id"], "category": case["category"], "family": case["family"],
            "passed": passed, "false_refusal": any(o.get("false_refusal") for o in out), "turns": out}


# --- modes ---------------------------------------------------------------
def validate():
    cases = all_cases()
    print(f"{len(cases)} cases, {sum(len(c['turns']) for c in cases)} turns")
    bad, warn, nspec = [], [], 0
    for c in cases:
        reused = c["id"].startswith("probe_")  # inherited from coverage_sweep
        for ti, t in enumerate(c["turns"]):
            for spec in t["expect"].get("verify", []):
                nspec += 1
                try:
                    v = expected(spec)
                except Exception as exc:
                    v = f"ERR:{exc}"
                if v is None or (isinstance(v, str) and v.startswith("ERR")):
                    (warn if reused else bad).append((c["id"], ti, spec, v))
    print(f"ground-truth specs: {nspec}, unresolved in NEW cases: {len(bad)}, stale in reused probes: {len(warn)}")
    for b in bad:
        print("  UNRESOLVED(new)", b[0], "turn", b[1], b[2], "->", b[3])
    for w in warn:
        print("  warn(reused probe, non-fatal)", w[0], w[2].get("table"), w[2].get("col"))
    # grader self-tests (no API)
    gt = {"rel": "2024", "table": "COST2_2024_NetPrice", "col": "NPGRN2", "where": {"UNITID": YALE}}
    exp = expected(gt)
    fake = {"intent": "analyze", "result": {"rows": [{"metric": "npgrn2", "value": exp, "unitid": YALE}]},
            "model_usage": {"estimated_api_usd": 0}}
    print("self-test numeric  (want CORRECT):      ", grade_turn({"expect": {"kind": "numeric", "verify": [gt]}}, fake)[0], f"(Yale NPGRN2 ground truth=${exp})")
    print("self-test refuse   (want PASS-REFUSE):  ", grade_turn({"expect": {"kind": "refuse"}}, {"intent": "clarify", "message": "x"})[0])
    print("self-test no-refuse(want FALSE-REFUSAL):", grade_turn({"expect": {"kind": "numeric", "must_not_refuse": True, "verify": []}}, {"intent": "clarify"})[0])
    ok = not bad and exp is not None
    print("VALIDATE", "OK" if ok else "FAILED — fix unresolved NEW-case specs above")
    return ok


def scorecard(results, spent, engine):
    from collections import Counter
    cats = sorted({r["category"] for r in results})
    lines = [f"# Eval scorecard — {engine}", "",
             f"Run {datetime.datetime.now(datetime.timezone.utc).isoformat()}. "
             f"Spent **${spent:.4f}** / ${COST_CAP_USD} cap. Cases: {len(results)}.", "",
             "## Headline", "",
             f"- **Overall pass:** {sum(r['passed'] for r in results)}/{len(results)}",
             f"- **False refusals (follow-ups wrongly blocked):** {sum(r['false_refusal'] for r in results)}",
             "", "## By category", "", "| Category | Pass | Total |", "| --- | --- | --- |"]
    for c in cats:
        rs = [r for r in results if r["category"] == c]
        lines.append(f"| {c} | {sum(r['passed'] for r in rs)} | {len(rs)} |")
    lats = [o["wall_s"] for r in results for o in r["turns"] if o.get("wall_s")]
    lines += ["", f"Median turn latency: {statistics.median(lats):.1f}s over {len(lats)} turns." if lats else "", ""]
    lines += ["## Per-case", "", "| Case | Cat | Pass | Turn verdicts |", "| --- | --- | --- | --- |"]
    for r in results:
        vs = " → ".join(o.get("verdict", "?") for o in r["turns"])
        lines.append(f"| {r['id']} | {r['category']} | {'✅' if r['passed'] else '❌'} | {vs} |")
    return "\n".join(lines)


def run(cases, engine):
    spent = [0.0]; results = []
    for c in cases:
        if spent[0] >= COST_CAP_USD:
            print("COST CAP hit before", c["id"]); break
        r = run_case(c, spent)
        results.append(r)
        print(json.dumps({"id": r["id"], "passed": r["passed"], "fr": r["false_refusal"],
                          "verdicts": [o.get("verdict") for o in r["turns"]], "cum_usd": round(spent[0], 4)}), flush=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d")
    (HERE / f"eval_set_results_{engine}_{stamp}.json").write_text(
        json.dumps({"engine": engine, "spent_usd": round(spent[0], 4), "results": results}, indent=2, default=str), encoding="utf-8")
    card = scorecard(results, spent[0], engine)
    (HERE / f"eval_set_scorecard_{engine}_{stamp}.md").write_text(card, encoding="utf-8")
    try:
        print("\n" + card)
    except UnicodeEncodeError:  # Windows cp1252 console can't encode the ✅/❌ glyphs
        print("\n" + card.encode("ascii", "replace").decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true", help="no API; check ground-truth specs + grader")
    ap.add_argument("--smoke", type=int, default=0, help="live: run only the first N cases")
    ap.add_argument("--only", default="", help="live: only cases whose id startswith this")
    ap.add_argument("--engine", default="v1", help="label for output files")
    args = ap.parse_args()
    if args.validate:
        sys.exit(0 if validate() else 1)
    cases = all_cases()
    if args.only:
        cases = [c for c in cases if c["id"].startswith(args.only)]
    if args.smoke:
        cases = cases[:args.smoke]
    run(cases, args.engine)


if __name__ == "__main__":
    main()
