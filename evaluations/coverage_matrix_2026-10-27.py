"""Build the coverage matrix from coverage_sweep_raw.json. Computes Tier-1 expected
values from the annual SQLite (generic verifier) and classifies every probe. No API."""
from pathlib import Path
import sqlite3, json, re

ROOT = Path(r"C:\Users\liyuj\OneDrive\2026\IPEDS Project\agent-redesign")
DATA = ROOT / "data" / "annual"
RAW = Path(__file__).resolve().parent / "coverage_sweep_raw.json"
OUT_MD = Path(__file__).resolve().parent / "coverage_matrix.md"
OUT_JSON = Path(__file__).resolve().parent / "coverage_matrix.json"
RELDB = {"2023": "IPEDS_2023-24_Final/IPEDS20123".replace("20123","") + "IPEDS202324.sqlite",
         "2024": "IPEDS_2024-25_Provisional/IPEDS202425.sqlite"}
# fix 2023 path cleanly:
RELDB["2023"] = "IPEDS_2023-24_Final/IPEDS202324.sqlite"


def expected(spec):
    db = sqlite3.connect(DATA / RELDB[spec["rel"]])
    where = spec["where"]
    conds = " AND ".join(f'"{k}"=?' for k in where)
    col = spec["col"]; agg = spec.get("agg", "first")
    sel = f'SUM("{col}")' if agg == "sum" else f'"{col}"'
    row = db.execute(f'SELECT {sel} FROM "{spec["table"]}" WHERE {conds}',
                     list(where.values())).fetchone()
    db.close()
    return None if not row else row[0]


def app_value(rec):
    rows = rec.get("top_rows") or []
    return rows[0]["value"] if rows and rows[0].get("value") is not None else None


def close(a, b):
    try:
        a = float(a); b = float(b)
        return abs(a - b) <= max(1.0, 0.01 * abs(b))
    except Exception:
        return False


def classify(rec):
    """Return (verdict, detail)."""
    tier = rec.get("tier")
    intent = rec.get("intent"); mode = rec.get("mode") or ""; pub = rec.get("published")
    av = app_value(rec)
    if not rec.get("ok"):
        return "ERROR", rec.get("error_type", "")
    if tier == 1 and rec.get("verify"):
        try:
            exp = expected(rec["verify"])
        except Exception as e:
            exp = None; rec["_gt_err"] = str(e)[:80]
        if exp is None:
            return ("ANSWERED?" if pub else "BLOCKED"), f"no ground-truth (app={av})"
        rec["_expected"] = exp
        if not pub or av is None:
            return "BLOCKED", f"expected {exp}, app gave no number"
        return ("CORRECT" if close(av, exp) else "WRONG-NUMBER"), f"app={av} expected={exp}"
    # tier 2 behavioral
    if pub:
        return "ANSWERED", f"value={av}"
    if intent in ("definition",) or mode == "source definition":
        msg = (rec.get("message") or "").lower()
        return ("DEFINED" if "could not" not in msg and "not establish" not in msg else "DEF-MISS"), ""
    if intent in ("discover", "guide") or mode in ("data discovery", "data guide"):
        # A specific count/amount question answered with a discovery overview = misroute.
        q = rec.get("q", "").lower()
        if re.search(r"how many|how much|what (?:is|was) the", q):
            return "MISROUTED→discovery", ""
        return "DISCOVERY-OK", ""
    if intent == "clarify":
        return "CLARIFY", (rec.get("message") or "")[:60]
    return "OTHER", f"intent={intent}"


def main():
    rep = json.loads(RAW.read_text(encoding="utf-8"))
    recs = rep["records"]
    for r in recs:
        r["verdict"], r["detail"] = classify(r)
    # matrix md
    lines = ["# Coverage sweep matrix", "",
             f"Run {rep['timestamp']}. Spent **${rep['total_spent_usd']}** over "
             f"{rep['n_run']}/{rep['n_total']} probes"
             + (f" (stopped at $5 cap before `{rep['stopped_at_cap_before']}`)" if rep.get("stopped_at_cap_before") else "") + ".", ""]
    from collections import Counter
    vc = Counter(r["verdict"] for r in recs)
    lines += ["## Verdict tally", "", "| Verdict | n |", "| --- | --- |"]
    for v, n in vc.most_common():
        lines.append(f"| {v} | {n} |")
    lines += ["", "## Per-probe", "", "| Family | Probe | Verdict | Detail | ~$ |", "| --- | --- | --- | --- | --- |"]
    for r in recs:
        q = r["q"][:52].replace("|", "/")
        lines.append(f"| {r['family']} | {q} | **{r['verdict']}** | {str(r.get('detail',''))[:60].replace(chr(124),'/')} | {r.get('estimated_api_usd') or ''} |")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    OUT_JSON.write_text(json.dumps(recs, indent=2, default=str), encoding="utf-8")
    print("\n".join(lines))
    print("\nWROTE", OUT_MD)


if __name__ == "__main__":
    main()
