# Evaluation Set Design (Step 1 of IMPROVEMENT_PLAN)

_Created 2026-11-02. Design for a single frozen eval set that scores the current
app (v1) and any future v2 **identically**, so "is the rewrite better?" becomes a
measurement instead of a guess — and so a v2 can't silently regress on the
Yale/NCES behavior v1 already handles._

## Principle

- **Frozen.** Cases and their expected values are immutable, like the Yale CSVs.
  Changing an expected value requires evidence or a user ruling, not "make it fit
  the output." (Same rule as `benchmark_definitions.json` today.)
- **Ground truth by SQL, not by model.** Wherever a number is expected, it is
  computed by a direct read-only query against the release SQLite (the data core),
  so grading never depends on the thing being graded.
- **Multi-turn is first-class.** The clunkiness lives in follow-ups, so follow-up
  sequences are a top-level category, not an afterthought.
- **Refusals count as answers.** Declining a question the data can't support is a
  correct outcome and is graded as such; fabricating a number is the worst failure.

## What already exists (reuse — do not rebuild)

| Asset | What it gives us |
|---|---|
| `coverage_sweep_2026-10-27.py` PROBES (30 cases) | Case schema `{id, family, tier, q, verify}`; tier-1 = ground-truth SQL spec; 15 survey families |
| `compare_models_current.py` CASES | Multi-turn pattern (`yield_followup` ← `admissions`), chart edits, SQL-derived `expected`, cost cap, paired runner |
| `Test cases/Yale/*.csv` | Immutable Yale expected values (enrollment, SAT, admissions, grad rates, subgroups) |
| `Test cases/NCES/*.xlsx` | ~45 NCES Trend Generator exports = national/aggregate trend ground truth |
| `benchmark_definitions.json` | Recorded interpretation rulings (URM, international, unknown handling) |
| `COST_CAP_USD` pattern | Hard cumulative API-cost cap in every runner |

## What's new (the gap this set fills)

1. **Follow-up sequences** — the category the whole rewrite is about; barely covered today.
2. **FAQs** — the example chips + cost questions, frozen with vetted expected framing.
3. **Should-refuse / graceful-decline** — no explicit category exists today.
4. **Traps** — faculty ambiguity, net-price lag, not-reported vs. zero, medical-scope — labeled as traps with expected handling.
5. **One unified frozen manifest + one runner + one scorecard** so v1 and v2 are scored the same way.

## Unified case schema (`evaluations/eval_set.jsonl`, one JSON object per line)

```jsonc
{
  "id": "fu_netprice_narrow",
  "category": "followup",          // numeric | behavioral | followup | faq | refuse | trap
  "family": "COST/IC (price)",     // survey family, for coverage reporting
  "turns": [                        // 1+ turns; single-turn cases have one
    {
      "q": "What is Yale's net price compared to other Ivy League schools?",
      "expect": {
        "kind": "numeric_set",      // numeric | numeric_set | behavioral | refuse | display_edit
        "institutions": 8,
        "verify": [                 // ground truth by SQL against the release db
          {"rel":"2024","table":"COST2_2024_NetPrice","col":"NPT42","where":{"unitId":130794},"value":23777},
          {"rel":"2024","table":"COST2_2024_NetPrice","col":"NPGRN2","where":{"unitId":130794},"value":22408}
        ]
      }
    },
    {
      "q": "I only need the average net price for students awarded grant or scholarship aid, 2023-24.",
      "expect": {
        "kind": "numeric_set",
        "institutions": 8,
        "measures_present": ["NPGRN2"],
        "measures_absent": ["NPT42"],
        "must_not_refuse": true,     // the v1 failure mode: spurious IntentMismatch
        "verify": [
          {"rel":"2024","table":"COST2_2024_NetPrice","col":"NPGRN2","where":{"unitId":130794},"value":22408}
        ]
      }
    }
  ]
}
```

Grading reads `expect.kind` per turn. `verify` reuses the coverage_sweep spec
(`rel, table, col, where, agg`) plus an expected `value`.

## Grading rubric

| kind | Pass condition | Notes |
|---|---|---|
| `numeric` / `numeric_set` | Published value == SQL ground truth | counts exact; rates within **0.0005** (Yale 3-decimal precision rule) |
| `behavioral` | Structured assertions hold (entity count, measure present, caveat present); else LLM-judge against a written rubric | judge is a separate model call, logged |
| `display_edit` | Result reused, **no new fetch**, requested view change applied | detects re-plan |
| `refuse` | Declines **and** emits no number; bonus if it names what's missing/why | answering with a number = hard fail |
| `followup` turn | Resolves to intended operation, `must_not_refuse` honored, values match | **false refusal recorded as its own failure mode** |

Every turn also records `wall_seconds`, `model_calls`, `cum_cost_usd` for the
cost/latency comparison.

## Category plan + seed cases

### A. Numeric core (reuse) — ~30 cases
Keep all `coverage_sweep` tier-1 probes as the data-core regression layer, plus
the Yale CSV and NCES trend checks. These should stay green no matter what; they
guard the KEEP layer.

### B. Follow-up sequences (new) — target ~12 sequences
- **fu_netprice_narrow** — the reported failure (schema above). T2 must NOT refuse.
- **fu_swap_institution** — T1 "Yale's admission rate, fall 2024" → T2 "What about Harvard?" (expect ADM2024 UNITID=166027, same metric/year).
- **fu_add_year** — T1 "Yale's 12-month enrollment in 2024" → T2 "Show 2015–2024 as a trend" (legitimate fetch; expect success, not a trend-validator refusal).
- **fu_resort** — T1 net-price comparison chart → T2 "sort by net price" (display edit, no re-fetch).
- **fu_rechart** — T2 "make it a bar chart" (display edit).
- **fu_go_back** — T1 compare → T2 narrow → T3 "actually, go back to the full comparison" (returns T1 result).
- **fu_change_measure** — T1 grad rate → T2 "show the degree counts instead" (swap measure, same schools/year).
- **fu_add_institution** — T1 Yale vs Harvard → T2 "add Princeton" (expect 3 schools; needs fetch).
- Plus 4 more drawn from real transcripts once collected.

### C. FAQs (new, frozen framing) — the example chips + cost
- "What was Yale's admission rate in fall 2024?" (verify ADM2024)
- "How much does it cost to attend Harvard College in 2024-25?" (verify cost/IC)
- "What percentage of undergraduates received grants or scholarships in 2023-24? Compare eight Ivy League institutions."
- "How many bachelor's degrees did Yale award in 2014-15?" (verify C2015_A)
- "How many full-time and part-time instructional staff did Yale have in Fall 2024?" (verify EAP)
- "What student services did Smith College report in 2024-25…" (verify IC2024)
- "Which Massachusetts degree-granting institutions reported undergraduate distance education in 2024-25?" (verify HD+IC join)
- Cost questions routed through `model_policy` today — pin expected framing.

### D. Should-refuse / graceful-decline (new) — target ~8
- "What is the average SAT score of Yale's **faculty**?" (SAT is a student measure — decline)
- "How many **nonbinary** faculty does Smith employ?" (IPEDS gender is binary — decline + explain)
- "What is Yale's faculty salary **by academic field**?" (salary not reported by field — decline)
- "What was Harvard's graduation rate in **2030**?" (outside corpus — decline)
- "What is the average **student loan debt** at Yale?" (the debt-deflection case — pin expected behavior)
- "List every Yale student's **name and GPA**." (not in IPEDS — decline)

### E. Traps (new) — target ~8
- **Faculty ambiguity:** "How many faculty does Yale have?" → expect a stated default population (full-time instructional faculty) **or** a clarify, never a silent wrong pick.
- **Net-price lag:** "What's Yale's net price for 2024-25?" → latest is 2023-24; expect the lag surfaced, not a fabricated current-year figure.
- **Not-reported vs zero:** a Yale null measure → expect "not reported," not 0.
- **Medical scope:** "average faculty salary at Yale" → SAL is nonmedical instructional only; expect the scope caveat.
- **Cohort vs fiscal year naming** → expect correct basis labeling.

## Harness mechanics

- **Manifest:** `evaluations/eval_set.jsonl` — frozen; a `eval_set_meta.json` records
  schema version + ground-truth provenance.
- **Runner:** `evaluations/run_eval_set.py` — adapt `coverage_sweep` + `compare_models_current`:
  load manifest; for each case, replay turns through `prototype.agent.ask(q, previous=…, conversation=…)`
  building the conversation object exactly as the UI does; apply graders; enforce `COST_CAP_USD`; write results.
- **Outputs:** `eval_set_results_<engine>_<date>.json` (per-turn detail) +
  `eval_set_scorecard_<engine>_<date>.md` (headline numbers).
- **Scorecard dimensions:** overall pass rate; per-category pass rate; **false-refusal count**
  (the clunkiness headline); numeric accuracy; cost/answer; median latency.
- **Baseline:** run once against v1 now → the number every v2 run is compared to.

## Headline metric

**False-refusal rate on follow-ups** — how often a valid follow-up is wrongly
refused or mis-answered. That single number is the clunkiness thesis made
measurable, and it's what the rewrite must drive down without hurting numeric
accuracy or the refuse-correctly rate.

## Open questions
- LLM-judge model + rubric wording for `behavioral` cases (keep judge cheap, logged, deterministic-ish via low temperature).
- How many follow-up sequences are enough to be representative (start 12, grow from real transcripts via the question log).
- Whether FAQ expected-framing is asserted structurally or by judge.
