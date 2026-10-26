# IPEDS agent evaluation log

This is the durable record of evaluation runs, interpretation decisions and unresolved findings. Append new entries when results or approved definitions change. Preserve prior results and do not revise expected values solely to match IPEDS.

## 2026-10-16 — Initial Yale benchmark evaluation

### Scope

Five user-supplied Yale reference CSVs in `../Test cases/` were compared with the ten imported annual IPEDS SQLite copies. These are deterministic data-retrieval checks, not evaluations of an implemented LLM agent, tool selection, conversation, charts or exports.

The input files remain unchanged. Their SHA-256 hashes, source row references, exact queries, expected values and actual results are retained in the saved evaluation evidence.

### Results

| Family | Matches | Numeric mismatches | Outside coverage | Unsupported field | Definition pending |
| --- | ---: | ---: | ---: | ---: | ---: |
| Enrollment | 26 | 4 | 123 | 0 | 0 |
| Admissions/yield | 46 | 4 | 200 | 0 | 0 |
| SAT percentiles | 41 | 5 | 400 | 54 | 0 |
| Overall graduation | 30 | 0 | 69 | 0 | 0 |
| Graduation subgroups | 86 | 0 | 28 | 4 | 36 |
| **Total** | **229** | **13** | **820** | **58** | **36** |

There are 1,156 numeric-cell fixtures, of which 242 currently support a numeric comparison: 229 match and 13 differ. These counts are cells, not independent natural-language scenarios or independent root causes. Unsupported, out-of-coverage and definition-pending cells are excluded from numeric pass/fail totals.

Count and SAT-score comparisons are exact. Rate comparisons use fractions on a 0–1 scale with an absolute tolerance of 0.0005, reflecting three-decimal benchmark precision (0.05 percentage points). Counts, source years and tolerances were not changed to force agreement.

### All retained numeric discrepancies

Differences below are IPEDS minus the supplied Yale benchmark. Year means fall/entering year for these observations.

| Year | Measure | Yale benchmark | IPEDS | Difference |
| --- | --- | ---: | ---: | ---: |
| 2015 | Graduate/professional enrollment | 6,855 | 6,853 | −2 |
| 2015 | Total enrollment | 12,387 | 12,385 | −2 |
| 2022 | Graduate/professional enrollment | 8,161 | 8,131 | −30 |
| 2022 | Total enrollment | 14,806 | 14,776 | −30 |
| 2016 | Matriculants | 1,371 | 1,367 | −4 |
| 2016 | Yield rate | 69.0% | 68.7626% | −0.2374 percentage points |
| 2018 | Applicants | 35,307 | 35,301 | −6 |
| 2018 | Admits | 2,241 | 2,240 | −1 |
| 2017 | SAT verbal/reading, 25th percentile | 710 | 730 | +20 |
| 2017 | SAT verbal/reading, 75th percentile | 800 | 780 | −20 |
| 2017 | SAT math, 25th percentile | 710 | 730 | +20 |
| 2018 | SAT math, 25th percentile | 730 | 740 | +10 |
| 2018 | SAT math, 75th percentile | 790 | 800 | +10 |

Undergraduate headcounts match in the enrollment rows above; total differences follow from graduate/professional differences. Raw EF, detailed EFA and derived graduate enrollment agree within IPEDS for those observations. The 2016 yield difference follows from the matriculant discrepancy. Reporting snapshots, revisions and population differences remain possible explanations, not established causes.

### Definition decisions

1. **Graduation time:** entering cohort year plus six selects the outcome release. Overall-cohort denominators match IPEDS adjusted bachelor cohorts (after allowable exclusions), even though the benchmark labels them first-year entering students.
2. **Pell:** non-Pell combines subsidized-loan-only recipients and students receiving neither Pell nor subsidized loans. It is not the latter category alone.
3. **International:** operationalized as IPEDS U.S. nonresident; all covered international subgroup cells match. This is not a general equivalence to every foreign-born student.
4. **URM:** the user defined URM as anyone who is not White, Asian or international. The placement of race/ethnicity unknown remains explicitly unresolved by user choice. The benchmark suggests unknown is included in Non-URM, but this must not be inferred into an approved mapping. Keep the 36 affected in-coverage checks pending.
5. **SAT population:** IPEDS describes enrolled first-time degree/certificate-seeking undergraduates submitting relevant scores, including prior-summer entrants. This aligns broadly with Yale College first-year students, rather than applicants or all admits.
6. **SAT score treatment:** official 2017–18/2018–19 instructions require the new 2016 SAT scale and concordance of older scores. Exact Yale score-selection/conversion practices are not documented in the supplied CSV. This is a confirmed comparability issue to investigate, not a demonstrated explanation for all five mismatches. Leave the numeric differences unresolved.

### Coverage limits

- Annual admission, enrollment and SAT observation coverage is 2015–2024. Earlier observations and 2025 are retained as unavailable fixtures.
- Six-year graduation outcomes cover entering cohorts 2009–2018. A 2019 entering cohort requires the 2025 outcome release.
- SAT 10th/90th percentiles are not collected in these IPEDS tables; medians begin in fall 2022.
- Pell-specific graduation fields are unavailable for the 2015 outcome release in this corpus.

### Evidence

- [Detailed review](YALE_BENCHMARK_REVIEW.md)
- [Cell-by-cell results](results/yale_results.csv)
- [Question fixtures, queries and outcomes](results/yale_cases.json)
- [Run summary and benchmark source hashes](results/yale_summary.json)
- [Definitions and user clarification](benchmark_definitions.json)
- [SAT definition verification and official sources](SAT_DEFINITION_VERIFICATION.md)
- [Rerunnable evaluator](run_yale_benchmarks.py)

### Next actions

- Preserve the 13 discrepancies for source reconciliation; obtain Yale source footnotes, snapshot dates or reporting methods where available.
- Leave race-unknown classification unresolved until the project owner supplies an explicit rule.
- Do not certify these unresolved cells as matching golden answers or overwrite them with IPEDS values.
- When the conversational agent is implemented, add evaluations for discovery, source selection, period interpretation, ambiguity handling, unavailable requests and requested outputs. This run establishes the retrieval baseline only.

## 2026-10-16 — Local prototype build and verification

User authorized the small local agent. Implemented `prototype/` with 36 source-reviewed measures and 340 explicit annual mappings; review means implementation review, not owner approval or benchmark reconciliation. Sources and gold CSVs remain unchanged. The prototype does not execute national aggregates or unresolved custom URM groupings.

The prototype regression suite queries the actual annual copies through the new engine and rechecks every supported numeric gold comparison. It preserves **229 matches and the same 13 mismatches** across 242 cells. Other integration checks cover calendar/class/cohort interpretation, unsupported observations, missing-not-zero behavior, Ivy resolution, ambiguous names, aid table-location correction, full Excel/CSV/provenance exports, read-only execution and Streamlit form/chart rendering.

Five live Anthropic planner cases check first-year admissions for class 2028/fall 2024, contextual yield follow-up, faculty discovery, financial-aid ambiguity and a graduation cohort trend. The first live run exposed a model date error: it paired year 2024 with class-of time, yielding fall 2020. This was fixed by application-side date binding, independent of model arithmetic. A regression was added and the five live cases subsequently passed. These smoke checks are a small functional sample, not a broad accuracy estimate.

See `prototype_verification.json` and `prototype_live_smoke.json` for machine-readable results; `../prototype/tests/` contains rerunnable checks. Remaining work includes broader paraphrase/filter/ambiguity evaluation, user review of mappings and answers, source discrepancy reconciliation and eventually production deployment/load testing.

## 2026-10-17 — Codebook search submission repair

The user reported `StreamlitWidgetAlreadyInstantiatedError` when submitting Explore codebooks. The form and results both used the `discovery` state key. Earlier UI coverage exercised guided analytics but not the codebook form submission, so it missed this failure. Form and result keys are now separate, and a regression submits a real search, repeats it with a different query/year, and checks blank/no-result handling.

Clarified that this tab searches definitions rather than institution values. Added table/variable-first lookup with optional category/release-documentation search, exact-identifier ranking, a full-definition selector, category-code labels and original source references. A read-only detail lookup avoids displaying truncated raw metadata as the variable definition. Catalog/source contents and runtime measure mappings were not changed.

All 12 integration tests passed, preserving the 229 Yale matches and 13 known discrepancies. This repair does not implement the proposed topic-card landing page or unmapped-measure execution workflow.

## 2026-10-17 — Learning interface, data extracts and two-model integration

Owner authorized the combined UI and model plan. Implemented the two main pages, six learning topics/18 examples, preserved conversation/tool state, collapsed/reopenable suggestions, institution autocomplete, multi-measure search/selection, single/selected/range year modes, full extracts and optional charts. CSV and Excel/provenance downloads retain complete validated results; compatible measures also have an institution-year CSV.

All 14 integration tests passed, preserving all 242 supported gold comparisons (229 matching, 13 discrepant). Tests now cover learning examples, multiple institution/measure selections across searches, all year modes, chart switching without changing the result, source lookup and model-setting preservation. Expected values were not changed. Original gold file hashes were checked unchanged.

The same seven live functional cases passed on Sonnet 5.5 and Haiku 5.5. An initial strict-tool request failed because the API subset does not support maxItems; transport now omits that keyword while local schema and plan validation preserve array/request bounds. Automatic tool selection is used and no-plan responses receive at most one follow-up request. Failed validation never triggers a statistical query. Existing five-case Sonnet 4.6 smoke evidence is retained as historical evidence.

The new comparison records usage, latency and standard-price cost estimates: about $0.107 across seven Sonnet requests and $0.0066 across seven Haiku requests, including the observed prompt-cache behavior. These samples are not comprehensive accuracy or production-cost estimates. Browser verification also confirmed example-to-conversation navigation, an additive Harvard follow-up retaining Yale, and a downloaded six-row/two-institution CSV. See `prototype_model_comparison.json` and `prototype_verification.json`.

### October 17, 2026 — Explore interface refinements
Replaced header radio navigation with tab-style buttons. Topic details appear immediately after their card row and include a Close control. Example categories are muted and separate from left-aligned question buttons. All 15 integration tests passed, including new checks for both row placements, closing, category/question separation and navigation; source benchmark remains 229 matches and 13 retained discrepancies. No live model calls were required for these interface checks.

### October 17, 2026 — Scrolling conversation
Moved message history into a fixed-height Streamlit chat container with native autoscroll; kept Need ideas and the follow-up composer outside it. Reviewed the original Gradrates chat layout. All 16 integration tests passed. Browser checks with two real-data examples confirmed four retained message bubbles, automatic scrolling to the bottom, scroll-back to the first exchange, and a visible composer on a 1440 by 1000 viewport.

### October 17, 2026 — Wider Ask & Analyze workspace
Removed the conversation/tools column split. Ask & Analyze now uses the available browser width with 32-pixel desktop margins (16 pixels on small screens). Moved extract builder, definition lookup and New conversation into the native collapsible sidebar. Browser verified approximately 1,526 pixels of chat width on a 1,600-pixel viewport and working expand/collapse controls. Existing 16 integration tests passed, including tool navigation and retained conversation state.

### October 17, 2026 — Two optional side panels
Need ideas is now on the left and analysis tools on the right, with both open by default. Independent labeled Collapse/Show controls preserve selections and conversation while reallocating the center width. Browser checks confirmed approximately 1,536 pixels of center width on a 1,600-pixel viewport when both panels close, reopening each, and executing an example with both still visible. All 16 tests passed; the follow-up/navigation test now checks panel defaults, independent collapse/reopen and selected-topic preservation.

### October 17, 2026 — Compact panel controls and introduction
Replaced full-width collapse buttons with small heading-adjacent chevrons and hover descriptions. Moved What would you like to learn and the institutions/year guidance above Need ideas in the left column. Removed the empty reopen-control row when both panels are visible, so the question form aligns with the workspace top. Browser checked collapse/reopen and approximately 29-pixel-wide chevron controls.

### October 17, 2026 — Chat-first empty state
Replaced the initial text-area form with the same bottom chat composer used for follow-ups. An empty conversation area is visible before the first question. Increased the center column share from 3/5 to 4.5/6.5 with both side panels open. Browser verified zero messages, a 500-pixel-high blank conversation area and bottom composer; all 16 integration tests passed, including submission through the new initial chat input.

### October 17, 2026 — Remove unnecessary horizontal conversation scrolling
Default result table now shows Institution, Period, Measure and formatted Value (including units/status). The 11-column detail table remains expandable and full exports are unchanged. Browser also revealed small horizontal overflow on the transcript itself; set its overflow-x to hidden while retaining vertical scrolling and internal table controls. All 16 integration tests passed for the table change.

### October 17, 2026 — Compact banner and primary question heading
Reduced banner top padding and brand size, put the local-prototype label inline, and replaced the roomy header divider with a compact rule. Ask & Analyze now uses What would you like to learn? as its main heading with the institutions/year guidance as subtitle. Removed the duplicate guidance from the left panel. All 16 tests passed; browser confirmed a single instance of the new heading.

### October 17, 2026 — Matching analysis-tool cards
Standardized Build a data extract and Browse definitions to the same compact heading/description/button format. Removed the Institutions to Preview steps caption, shortened the builder button, and used consistent text spacing in both cards. Both tool navigation smoke checks passed before the final typography-only refinement.

### October 17, 2026 — Matched panel heights
Made the left and center workspace stretch to the same row height. The message history fills remaining center space above the bottom composer, retaining vertical scrolling. Browser verified equal heights before a question (approximately 774 pixels each) and after a real-data example (approximately 830 pixels each).

### October 17, 2026 — Apply main graduation-prototype response rules
Added source-bound 2–5-sentence summaries shared by typed questions, examples and extracts; chart-first defaults (line trends, bar comparisons), table/export overrides, friendly labels and missing/not-collected wording. Added selective follow-up context and interpretation notes, ambiguity clarification, stronger aggregation guard and local presentation edits that retain the exact result/provenance. No new statistical mapping or gold values changed. The full 19-test suite passed; five targeted tests passed again after the final chart-responsive/context-guard refinements. Benchmark remains 229 matches and 13 disclosed discrepancies. Browser verified a chart-first Ivy comparison and Show me the table without a new query. No live model calls were made; planner transport was mocked, and all statistics came from real local sources. Rules and supported chart-edit limits are recorded in prototype/RESPONSE_RULES.md.
