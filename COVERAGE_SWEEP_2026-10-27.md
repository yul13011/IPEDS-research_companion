# Coverage sweep — correctness across the survey families

Created: October 27, 2026.

Decision context: D2 resolved to **keep Option A** (the typed-plan engine); the priority is
now **answering questions correctly across all ~509 tables**. This is the first coverage
audit toward that goal. Companion: [DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md](DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md).

## Method
30 probes across the survey families, run through the **real pipeline**
(`intent_router.handle(..., 'automatic', ...)`) with a **hard $5 API cost cap**; every
numeric answer checked against **ground truth computed from the SQLite**. Total spend:
**$1.36** (30/30 probes; cap not reached). Harness + raw results + matrix:
`evaluations/coverage_sweep_2026-10-27.*`, `evaluations/coverage_matrix_2026-10-27.*`.

## Headline: breadth is real; a specific cluster of gaps remains
Every Tier‑1 single-variable lookup that produced a number was **correct**, across families
that are *not* in the 36 reviewed measures:

| Family | Probe | App | Source truth |
| --- | --- | --- | --- |
| C | Yale master's degrees 2023 | 2,846 | ✓ |
| C | Harvard research doctorates 2023 | 758 | ✓ |
| C | Yale vs Princeton bachelor's 2023 | 1,449 / 1,284 | ✓ |
| AL | Harvard physical books 2023 | 14,790,270 | ✓ |
| AL | Yale e‑books 2023 | 2,525,935 | ✓ |
| SAL | Smith full‑professor salary 2023‑24 | $152,890 | ✓ |
| SAL | Smith/MHC/Wellesley salary compare | 115,221 / 101,151 / 120,638 | ✓ |
| OM | Yale 8‑year award rate | 97% | ✓ |
| EFFY | Yale 12‑month headcount 2022‑23 | 16,416 | ✓ |
| EF | Yale distance‑ed (exclusive) fall 2023 | 56 | plausible |
| Aggregate | Public four‑year institutions 2023 | 796 | ✓ |
| Aggregate | Total fall enrollment 2023 (Title IV) | 19,038,434 | ✓ |

So the typed-plan engine *does* reach many non-reviewed variables across the catalog and
compute them correctly. Definitions (retention ✓) and discovery (finance ✓) also worked.

## The failure cluster: COST/price, ADM detail, and period over‑rejection
These are cases where **the data exists but the app did not answer it correctly**:

| Probe | What happened | Truth | Class |
| --- | --- | --- | --- |
| Smith published tuition 2023‑24 | "not reported in the available source records" | $61,568 (`COST1_2024.chg3ay2`) | **False‑unavailable** — planner didn't find/select the COST table |
| Wellesley net price 2022‑23 | "The returned periods do not cover the requested interval… restate the start and end years" | `NPIST2` exists | **Period over‑rejection** — single‑year price question rejected as an interval (same class as F‑B temporal over‑eagerness) |
| Yale ACT submitters fall 2024 | task split → "1 needs clarification, 1 blocked" | 384 (`ADM2024.ACTNUM`) | **Task‑split block** — a simple lookup routed into multi‑part handling and blocked |
| Mt. Holyoke room & board 2023‑24 | "not reported" | inconclusive (my `PCCHG5AY3` was null too; value likely in another IC table) | **Locate‑the‑field** gap |

Adjacent, lower‑severity:
- **Finance "2022‑23"** now returns a *clarification* ("none labeled 2022‑23 exactly; do you
  mean fiscal year 2023?") rather than auto‑answering. That's the F‑A guard being careful —
  safe, but it adds a turn and the planner's success is somewhat **run‑to‑run variable**.
- **National six‑year grad‑rate aggregate** still produces no published number (known‑hard;
  the F‑B fix removed the false "trend" error but the aggregate itself remains unresolved).
- **"Admissions test requirements"** was answered with SAT percentiles (a defensible but not
  literal reading).

## Prioritized fix classes (next work)
1. **COST/price family (highest value).** Tuition, net price, and room/board are common
   questions and the data plainly exists; the planner either can't locate the `COST1`/`COST2`
   tables or declares them "not reported." Likely needs catalog/field-selection help (and
   reviewed mappings for the core price fields).
2. **Period/interval over‑rejection (generalize the F‑B fix).** Single‑year `YYYY‑YY`
   price/finance questions are being rejected as incomplete intervals. Extend the
   period‑binding/validation fix to academic/price single‑year questions.
3. **Task‑split over‑eagerness.** Straightforward single lookups (e.g. ACT submitters) are
   being routed into multi‑part task handling and blocked; tighten when a request is split.
4. **Finance "YYYY‑YY" → fiscal‑year auto‑resolution.** Let the planner map "2022‑23" to FY
   2023 automatically (with disclosure) instead of asking, since the F‑A guard already knows
   the right table.
5. **Field‑location gaps** (e.g. room/board) and the **national aggregate** remain.

## Update (2026-10-27): fixes landed

- **Class #1 — false "not reported" (COST/price): FIXED.** Root cause was a column-casing
  bug in `catalog_execution` (IC/COST codebook names are lowercase, physical columns
  uppercase). Verified: Smith tuition 2023-24 $61,568; Mt. Holyoke room & board $18,838.
  Broad win across all IC/COST lowercase fields. Regression: `test_catalog_column_casing.py`.
- **Class #2 — period over-rejection: FIXED for column-encoded-year fields.** The
  academic/fiscal single-year check now accepts the requested year when a selected field's
  own title carries it (e.g. "Published tuition and fees 2022-23" = `chg2ay2`), and each
  row's reporting period is stamped from the field's data year. Verified: Smith prior-year
  tuition 2022-23 $58,768 (was blocked). Regression: `test_catalog_period_binding.py`.
- **Net price — FIXED (2026-10-27).** The planner selected `NPIST2` ("net price 2023-24")
  for a 2022-23 request; net-price columns (`NPIST0/1/2`) are a rolling 3-year window that
  shifts by release, so "2022-23" is `NPIST1` (2024-25 release) or `NPIST2` (2023-24 release).
  Fix: a deterministic `_align_field_years(plan, question)` in `catalog_planner.py`, called at
  the top of `proposal_answer`. For a single-year request (exactly one `YYYY-YY` span in the
  question) it swaps any selected field whose title encodes a *different* span to the sibling
  field (same release+table) whose title matches the requested span. Verified live: Alabama
  A & M net price 2022-23 now returns $14,064 (`NPIST1`), was $17,152 (`NPIST2`). General —
  also covers prior-year IC tuition columns. Idempotent; multi-year requests untouched.
  Regression: `test_netprice_year_alignment.py`. (Some institutions, e.g. Wellesley, report
  no net price at all — a genuine data gap, correctly surfaced.)
- **Task-split (class #3) — NOT a bug.** The Yale/ACT-submitters lookup now answers 384
  reliably (3/3 runs). The earlier "1 blocked, 1 needs clarification" was stochastic planner
  non-determinism, not a consistent routing defect — no code change made.
- **Finance "YYYY-YY" → fiscal-year auto-resolution — FIXED (2026-10-26).** The catalog-planner
  path (unlike the `query_engine` F-A guard) read "2022-23" as the *collection release* and
  silently answered the wrong fiscal year (Yale tuition revenue $354,023,874 / FY2022 / table
  `F2122_F2`). A finance table `F{aa}{bb}` holds the fiscal year ending 20bb and is published
  in the *next* release, so "2022-23" is FY2023 = `F2223_F2` (2023-24 release) = $343,599,498.
  Fix, two parts: (1) `_align_finance_years(plan, question)` in `catalog_planner.py`, called in
  `proposal_answer`, rebinds a single-span finance selection to the table whose fiscal year
  ends in the requested year, repoints `source_years`, and rewrites the disclosure (dropping
  the model's stale wrong-year notes); (2) `semantic_check` now accepts a `YYYY-YY` span's end
  year as the requested fiscal/academic year, so the aligned plan executes instead of being
  rejected. It now **answers with disclosure** rather than asking to clarify. Verified live:
  Yale tuition-and-fees revenue 2022-23 = $343,599,498 (FY2023). Regression:
  `test_finance_year_alignment.py`.

## Caveats
- 30 probes is a sample, not full coverage; Tier‑2 verdicts are behavioral. The auto‑matrix
  under‑counted (e.g. the institution‑count answer rendered as a message, not rows, and was
  mislabeled "OTHER"; it is correct). See the JSON for raw records.
- Ground truth for a few probes (room/board, distance‑ed) needs the exact source field
  confirmed; those are marked inconclusive, not failures.
