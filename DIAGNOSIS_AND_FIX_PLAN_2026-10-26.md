# Interpretation-layer diagnosis and prioritized fix plan

Created: October 26, 2026.

Status: Diagnosis complete. **All five findings (F-A–F-E) are now fixed on branch
`fix/interp-layer-p0`**, each as a focused commit with its own regression test; the
latency track remains. This document records the original live, evidence-backed review of
why the IPEDS Research Companion returned wrong or slow answers, the prioritized fix plan,
and (in section 7) the implementation status.

## 1. Summary

The app was exercised live over 19 representative questions spanning reviewed measures,
single-institution catalog lookups, aggregates, comparisons, trends, ambiguous terms,
definitions, discovery, an unsupported measure, and a follow-up pair. Each answer was
checked against ground truth computed directly from the annual SQLite databases.

**Headline: the data/execution layer is reliable; every failure is in the LLM
interpretation/routing/period layer.** Of the 19 cases, 14 were good and 5 were wrong.
Every value that actually executed matched ground truth — including the two whose
*interpretation* was wrong (the finance answer executed the number it bound correctly;
it simply bound the wrong fiscal year). The failures, and nearly all of the latency and
cost, come from how the question is classified, scoped in time, and bound to source
periods — not from the queries or the data.

Method and raw evidence:
- Harness (drives the real pipeline via `intent_router.handle(..., 'automatic', ..., ask)`,
  the same entry the UI uses): [evaluations/diagnostic_batch_2026-10-26.py](evaluations/diagnostic_batch_2026-10-26.py).
- Per-case results (intent, published/blocked, values, latency, model calls, API cost):
  [evaluations/diagnostic_batch_2026-10-26.json](evaluations/diagnostic_batch_2026-10-26.json).
- Ground truth was recomputed from `data/annual/*/IPEDS*.sqlite` for each numeric case.

## 2. What works (14 / 19)

| Case | Question | App result | Ground-truth check |
| --- | --- | --- | --- |
| rev_adm | Yale admission rate, fall 2024 | 3.87% | ✓ 2,227 / 57,517 |
| rev_grad | Yale six-year graduation trend (cohorts 2009–18) | 10 points, ~96–98% | ✓ cohort→outcome-year mapping correct |
| cat_enr | Smith total fall enrollment 2023 | 2,830 | ✓ exact (EF2023A, all students) |
| cat_ret | Mount Holyoke first-year retention 2023 | 90% full-time | ✓ exact (EF2023D RET_PCF) |
| agg_enr | Total US fall enrollment 2023 | 19,038,434 (Title IV) | ✓ well-scoped national sum |
| cmp_grad | Yale/Harvard/Princeton six-year grad (2015 cohort) | 96.9 / 96.7 / 97.6% | ✓ correctly used 2021 outcome year |
| cmp_sal | Smith/MHC/Wellesley avg FT faculty salary 2023–24 | 115,221 / 101,151 / 120,638 | ✓✓ all exact (SAL2023_IS SAEQ9AT, all ranks) |
| trd_awd | Yale bachelor's each year 2015–24 | 10 points, 2015 = 1,327 | ✓ |
| amb_fac | "How many faculty does Yale have?" | A/B clarification offered | ✓ desired behavior (prior F022 concern) |
| amb_aid | "What is Yale's financial aid?" | asks which measure | ✓ |
| edge_urm | URM six-year grad rate at Yale | explains unavailable, lists subgroups | ✓ graceful |
| disc_aid | "What data on financial aid?" | data-area guide | ✓ discovery |
| fu_base | Yale bachelor's 2015 | 1,327 | ✓ |
| fu_next | follow-up "What about Harvard?" | Harvard 1,757 | ✓ context carried |

## 3. Breakage map (5 / 19)

### F-A (P0) — Finance period-binding returns a confident wrong number

- **Case:** cat_fin — "What was Yale's total revenue from tuition and fees in 2022-23?"
- **App answer:** $354,023,874, labeled "Fiscal year 2022".
- **Ground truth:** $343,599,498 (FY2022–23). $354,023,874 is the **FY2021–22** value.
- **Root cause:** The catalog planner (model) selects the physical finance table. IPEDS
  finance for FY2022–23 is stored in the *next* collection as table `F2223` (inside the
  2023–24 release DB); the plan bound `F2122` (FY2021–22) instead. `contract()` sets no
  period constraint for this phrasing (verified: `temporal=False`, `expected_years=None`),
  and the fiscal-year validator at `prototype/query_engine.py:233-235` only triggers when
  the text literally says "fiscal year YYYY" — a hyphenated "2022-23" is not caught.
  `prototype/catalog_execution.py:117-119` only emits a soft warning.
- **Severity:** Highest. Returns a plausible, undetectable wrong number.

### F-B (P0) — "four-year institutions" misread as "four years"

- **Case:** agg_grad — "…six-year graduation rate for four-year institutions in the United
  States for the 2016 entering cohort?"
- **App answer:** No result after ~25s: "Only one reporting period was returned for a
  longitudinal request. No trend has been published; please restate the interval."
- **Root cause (verified by calling `contract()` directly):** the duration regex in
  `prototype/time_scope.py:22` matches **"for four-year institutions"** (lead-in `for` +
  number word `four` + `year`), so `trend_years()` returns `[2013, 2014, 2015, 2016]`.
  `contract()` then sets `temporal=True` and `period_count=4` (`prototype/intent_checks.py:51`),
  and the single-cohort result is rejected at `prototype/intent_checks.py:205`.
  The sector descriptor "four-year" (institution type) is being read as a 4-year window.
- **Severity:** High and broad — "four-year", "two-year", etc. appear constantly in
  higher-ed questions, so this silently corrupts time windows well beyond this one case.

### F-C (P1) — Specific count misrouted to discovery

- **Case:** cat_lib — "How many books were in Harvard's library collection in 2023?"
- **App answer:** a data-area overview ("Here are the main data areas found…"); no number.
- **Ground truth:** answerable — `AL2023.LPBOOKS` = 14,790,270 physical books
  (total collection `LTCLLCT` = 20,478,777).
- **Root cause:** routing is fully model-driven by the prompt in
  `prototype/intent_router.py:56-71`; the model chose `discovery` instead of
  `numerical`. There is no deterministic backstop for a "how many … at <institution>"
  question.
- **Severity:** Medium — users get a non-answer for data that exists.

### F-D (P1) — Institution counts unsupported

- **Case:** agg_count — "How many degree-granting institutions reported to IPEDS in 2023?"
- **App answer:** "Request status: 1 needs clarification, 1 blocked." No number.
- **Ground truth:** 4,153 degree-granting (4,096 active) of 6,163 HD2023 rows.
- **Root cause:** routed into `prototype/request_tasks.py` and blocked; there is no
  "count institutions" aggregate. `prototype/populations.py` builds population filters,
  but the engine counts measure rows, not distinct institutions.
- **Severity:** Medium — a common, simple question is unanswerable.

### F-E (P2) — Definition recall misses core terms

- **Case:** def_grad — "What is the definition of the six-year graduation rate?"
- **App answer:** "I could not establish a direct definition … from this bounded search."
- **Root cause:** `prototype/definitions.py:180` (`answer()`) runs a bounded codebook
  search; the derived measure (DRVGR `GBA6RTT`) and the reviewed-measure definitions are
  not search sources, and there is no synonym expansion for core measure names.
- **Severity:** Low–medium — a central term is undefined despite F003 being marked done.

## 4. Prioritized fix plan

Recommended order: **F-B → F-A → F-C → F-D → F-E → latency track.**
(F-B first because it is a tiny, surgical change with the broadest correctness impact;
F-A next because it is the only silently-wrong *number*.)

| ID | Priority | Fix | Primary location | Effort | Risk if unfixed |
| --- | --- | --- | --- | --- | --- |
| F-B | P0 | Stop a number followed by a sector noun ("year institutions/colleges/schools/students/programs/degrees/levels") from matching the duration regex (negative lookahead after `years?\|terms?\|periods?`). Add regression cases for "four-year institutions", "two-year colleges". | `prototype/time_scope.py:22` (with knock-on at `intent_checks.py:51,205`) | Small | High, broad |
| F-A | P0 | Add deterministic finance-period binding: map `YYYY-YY` to its fiscal-year end and the correct `F{YY}{YY}` table/release, and make the validator **reject** (not warn) a plan whose finance table's fiscal year ≠ the requested one. | `prototype/query_engine.py:233-235`, `prototype/catalog_execution.py:117-119` | Medium | High (silent bad data) |
| F-C | P1 | Strengthen routing: a "how many / what is the number of **X** at **<institution>**" is `numerical`/`analysis`, even for unfamiliar topics; add a lightweight deterministic guard so a count question with a resolved institution does not resolve to `discovery`. | `prototype/intent_router.py:56-71` | Small–medium | Medium |
| F-D | P1 | Add a `count distinct UNITID` aggregate over a population/filter (DEGGRANT, sector, state), with routing and a validator. | `prototype/populations.py`, `prototype/query_engine.py`, `prototype/request_tasks.py` | Medium | Medium |
| F-E | P2 | Add the 36 reviewed-measure definitions (`measure-registry/reviewed_measures.json`) as a definition source and expand common synonyms so core measure names resolve. | `prototype/definitions.py:180` | Small–medium | Low–medium |

### Cross-cutting — latency and cost (separate track)

Not caused by the bugs above, but worth a dedicated pass:
- Cold start ~38s for the first query of a process (even a reviewed measure).
- Catalog/clarification questions: 18–28s, 2–5 model calls, up to ~$0.11 per answer.
- Data retrieval is not the bottleneck; multi-call LLM planning is. Candidate work:
  warm the catalog/metadata at startup; reduce planner round-trips; cache interpretation.

## 5. Prerequisite before implementing

`agent-redesign/` is **not under version control** (it is untracked in the parent repo).
Before editing this dense ~9,400-line codebase, put it under git so every change is
reversible and reviewable, and so each fix can land with a regression test and a
re-run of the relevant batch cases.

## 7. Implementation status (branch `fix/interp-layer-p0`)

All five findings are fixed, each as one commit with a regression test. Existing suites
(intent_checks, query_engine, intent_router, populations, request_tasks, definitions) all
still pass.

| ID | Commit | Fix | Live result |
| --- | --- | --- | --- |
| F-B | `12d924c` | Negative lookahead in `time_scope.py`/`intent_checks.py` so "N-year <sector>" is not a window | 2016 four-year-cohort question no longer errors with a false "longitudinal request" |
| F-A | `7babfdd` | `check_fiscal_year()` in `query_engine.py` rejects a finance table bound to the wrong fiscal year | "tuition and fees 2022-23" returns $343,599,498 (was $354,023,874) |
| F-C | `25e5d60` | `normalize_decision()` reclassifies a fresh "how many/how much" count from discovery to analysis; sharper prompt | library question reaches the numerical path (clarifies physical books vs total collection) |
| F-D | `1599bf0` | `populations.institution_count()` answers a bare headcount from the directory population (Title IV default) | "degree-granting institutions in 2023" returns 3,841 with disclosed scope |
| F-E | `285f555` | `definitions.reviewed()` matches a measure's core label (subgroup/bachelor stripped, 6↔six) | "six-year graduation rate" returns the reviewed definition |

Tests: `prototype/tests/test_time_scope_sector.py`, `test_finance_fiscal_year.py`,
`test_routing_count.py`, `test_institution_count.py`, `test_definition_recall.py`.
Owner decision recorded: F-D uses the Title IV directory-population scope.
Remaining: the latency / cost track (section 4, cross-cutting).

## 6. Evidence index

- Live harness: [evaluations/diagnostic_batch_2026-10-26.py](evaluations/diagnostic_batch_2026-10-26.py)
- Per-case results: [evaluations/diagnostic_batch_2026-10-26.json](evaluations/diagnostic_batch_2026-10-26.json)
- Related existing trackers: [APP_FINDINGS_AND_IDEAS.md](APP_FINDINGS_AND_IDEAS.md),
  [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)
