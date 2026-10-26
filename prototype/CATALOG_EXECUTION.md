# Catalog execution and latency — October 19, 2026

October 21 update: this is a historical milestone. Current national/state/sector population support is documented in [POPULATION_AGGREGATES.md](POPULATION_AGGREGATES.md); the former blanket restriction below is superseded.


Latest October 19 update: relational execution, grouping, weighted analysis, joins and multi-step formulas are documented in [QUERY_ENGINE.md](QUERY_ENGINE.md). Its scope supersedes the earlier same-row-only limits below.

> Latest update: [GENERAL_CALCULATIONS.md](GENERAL_CALCULATIONS.md) replaces the numerical field allowlist with general source-backed calculation validation, full-catalog descriptions, plan normalization and bounded model repair. Earlier direct-only and percentage-specific statements below describe the previous checkpoint.

Step 4 adds a guarded execution path for catalog-discovered numerical observations. This supersedes step 3 statements that all unfamiliar plans remain unexecuted. It does not certify every IPEDS question or authorize every operation expressible by the planning schema.

## Implemented

- `catalog_execution.py` revalidates the complete local schema, source field locations, exact category-code ownership, institution resolution and source evidence immediately before execution.
- Numerical direct lookups can use any supplied survey table with continuous numeric definitions and a usable institution key. This is independent of the 36-measure registry. Composite keys require source-documented key columns and explicit equality selectors; runtime cardinality must be zero or one record per institution/table/release.
- No arbitrary SQL or expressions come from the model. Catalog identifiers are quoted; values are bound parameters. Annual databases open read-only with query_only and a query deadline. Fetches stop at two records to detect ambiguous row selectors; plan/institution/year bounds limit output.
- Reporting periods come from source metadata, independently of collection release labels. Fall year coverage is checked against explicit requested years. Fiscal/academic period mismatches and unsupported cohort alignment are blocked. Per-field period nuance and general natural-language scope interpretation still depend on correct source selection by the planner; this is not a proof of complete semantic coverage.
- The original Yale undergraduate race/ethnicity question now executes EFALEVEL=2, nine official categories plus total. Percentages use category/total headcount × 100, preserve unknown/nonresident categories, check numerator bounds, propagate missing/zero denominators, and check the full partition against total when available.
- Dynamic measure labels, definitions, charts, tables, CSV, Excel with sources, and JSON audit files work without adding fixed registry entries. Catalog follow-up context remains separate from the reviewed extract builder.
- Missing/nonnumeric/nonfinite values remain empty. Negative values are conservatively withheld pending field-specific sign/sentinel interpretation, with a warning and raw values in audit rows. This can withhold valid signed financial values; such fields need further semantic support. No reported/imputed status is inferred.
- Multiple releases retain their own definitions and distinct series segments; no growth rate or automatic harmonization is inferred.

## Deliberate execution boundaries

Unverified formulas/denominators, grouped row extracts, arbitrary subtotal reductions, range filters, fact-table joins, cohort alignment without a source mapping, signed financial values and custom/national/sector aggregates remain blocked or withheld. The planner can discover/propose them; existence in the catalog is not execution approval. Directory joins remain unnecessary for direct queries because names resolve separately through the annual directory. Source-location conflicts are never silently relocated.

Thus the step 4 foundation and first end-to-end expansions are implemented; generalized grouped extracts, calculations and joins still need further work. Do not describe all supplied data as fully analytically supported.

## Live provider repair

Live testing exposed the provider's compiled strict-grammar size limit for the full plan schema. Metadata tools remain provider-strict. `submit_catalog_plan` uses ordinary tool transport and retains mandatory complete local JSON-schema, catalog and execution validation. No source or execution checks were removed. A separate physical/codebook table capitalization mismatch was repaired and covered by a regression test.

## Latency metrics

`ask()` records answer-ready wall time, planning/catalog binding, semantic validation, query execution and live model calls. The reviewed route reports a combined reviewed/discovery pipeline time rather than mislabeling its existing SQL as planning. Timings live in answer/audit metadata; they do not add chat controls.

`tests/catalog_latency.py --live` measures fresh unfamiliar questions with the configured Sonnet model, then separately serializes CSV/Excel/JSON. No previous plan is supplied. The same process and provider caches can warm. Browser transport/paint is excluded. Failures retain elapsed time and error type; failures are not counted as successful answers. `tests/verify_catalog_execution.py` records wall time for each deterministic/mocked regression case. Existing `tests/live_smoke.py` now also records latency.

Final live sample (`evaluations/catalog_latency.json`):

| Case | Answer ready | Outcome |
| --- | ---: | --- |
| Enrollment acceptance shortcut, no model | 0.21 s | Numerical answer |
| Unfamiliar library physical books, fiscal 2024 | 11.95 s | Numerical answer, 2 model calls |
| Unfamiliar out-of-state undergraduate tuition, academic 2024–25 | 8.01 s | Numerical answer, 2 model calls |
| Library repeat, no conversation history | 10.49 s | Numerical answer, 2 model calls |

Three successful live model requests: median 10.49 s, range 8.01–11.95 s. This small sample is not a latency guarantee. Earlier successful first-run library timing was 20.73 s; caches/startup/provider variation matter. Final query time was approximately 0.006–0.008 s and validation 0.038–0.049 s. Most latency is planning/provider interaction and process initialization. Excel serialization for those unfamiliar results took 0.031–0.070 s. The source values were independently checked against local annual SQL by deterministic regression tests: library books 9,042,536; tuition 67,250 dollars. This confirms retrieval from supplied data, not independent certification of institutional statistics.

A separate actual Streamlit AppTest chat rerun for the enrollment acceptance case took 0.64 s, including server answer work, chart serialization and eager export preparation, with no UI exceptions (`evaluations/catalog_render_latency.json`). It excludes browser paint and is not directly additive to model-only timings. Earlier test failures remain in `catalog_latency_before_case_fix.json`; provider grammar rejection is documented above.

## Owner input

Nothing is required to use or test the implemented direct-look-up path. No new source files, database-column choices, or routine implementation approvals are needed.

For later methodological expansion, ask for a concrete decision only when a question requires it: for example where race-unknown belongs in a custom URM grouping; the reporting unit, geography and missingness rule for an aggregate; or the intended population/period when the question is genuinely ambiguous. Do not require those decisions to answer source-defined direct observations.

Useful optional user acceptance work: try several real research questions in Ask & Analyze and report the exact wording plus any interpretation that differs from what was intended. This is optional feedback, not a prerequisite to continue development.

## Reproduce

From agent-redesign, using the bundled Python:

```powershell
& 'C:/Users/liyuj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' prototype/tests/verify_catalog_execution.py
& 'C:/Users/liyuj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' prototype/tests/catalog_latency.py --live
```

The second command makes live provider requests and incurs normal API usage. Original IPEDS files and annual SQLite data remain unchanged. Existing benchmark discrepancies are retained.


## Correction after user wording test

The wording “show Yale's undergraduate population's race/ethnicity break down” bypassed the bounded starter because “break down” was not normalized to “breakdown”. The generated model proposal included a dimension, which the executor correctly blocked under its current boundary. Normalize the equivalent phrase (including break-down) before the vocabulary guard; unrelated extra scope still goes to general planning.

A source-code review during this repair also found a more serious earlier starter error: EFALEVEL=20 is “All students, Undergraduate, Other degree/certificatee-seeking, Continuing”, not all undergraduates. The starter now resolves the exact category label “All students, Undergraduate total” in each annual codebook (code 2 in all ten supplied releases). A separate semantic guard blocks a subgroup substituted for an unqualified all-undergraduate race request. The earlier enrollment shortcut values and acceptance assertions were invalid for total-undergraduate scope; historical latency reports are annotated, and their timings do not validate the old numerical result. Library and tuition results are unaffected. Corrected Yale fall 2024 total is 6,814 from the supplied source; the previous continuing subgroup was 5,181. See evaluations/race_breakdown_wording_fix.json. No source data was modified.


## First-time undergraduate gender breakdown

October 20 update: the same source-bound planner also supports **all undergraduates**, in addition to first-time undergraduates. It resolves exact annual population labels: all-undergraduate total, full-/part-time undergraduate total, or the corresponding first-time degree/certificate-seeking population. The plain prompt “Yale undergraduates by gender in the past 10 years” returns counts for the ten supplied falls, 2015–2024. Explicit shares produce Men/total and Women/total separately for each year. The version-1 calculation bound is now 40, permitting the 20 required annual gender-share calculations while retaining the 40-selected-field bound. Denominator relationship, reconciliation, population filters and missingness checks remain mandatory. Equivalent all-attendance and Men/Women wording from conversation resolution preserves this route; offline percentage continuations are not mistaken for institution names. This mechanism applies across institutions, not only Yale. Live numerical checks and latency: `evaluations/enrollment_gender_latency.json`.

The source-bound starter now supports first-year/first-time undergraduate gender or sex breakdowns with annual exact population category evidence. Default output is Men, Women and total counts, not an unsolicited ratio. Full-/part-time scope is explicit when requested; no numeric-zero substitution is made for an absent row. Source-defined Men/total and Women/total percentages on the same selected population row are permitted only as one numerator per output and after reconciliation; arbitrary arithmetic remains blocked.

“First-year” is explicitly interpreted as IPEDS first-time degree/certificate-seeking undergraduate students, excluding transfers. Yale College wording discloses institution-level Yale University reporting. Unknown/another-gender detailed first-time counts are not collected and are not inferred from remainders (the source Men/Women categories can include allocated students). The exact user request returns 782 men, 772 women and total 1,554 for fall 2024. No year requested defaults to latest supplied fall 2024. See evaluations/first_year_gender_verification.json for actual latency and exact source selector evidence.

The planner prompt now avoids unsolicited calculations for breakdowns and specifies one numerator per requested share. Semantic validation checks first-time population and attendance selectors. Short clarification replies retain the original question during execution validation. Four added tests cover direct source counts, explicit percentages, wrong-population and multi-numerator rejection, attendance/missingness, date corrections and unknown extra scope.

