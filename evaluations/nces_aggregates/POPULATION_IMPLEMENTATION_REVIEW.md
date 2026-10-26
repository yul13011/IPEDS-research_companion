# Population aggregates: implementation and NCES verification

**National and sector aggregates are enabled through the general source-bound query engine. The former blanket restriction is removed. Known mismatching methods/periods remain guarded; unresolved definitions and unavailable data do not produce figures.**

## What users can do

- Ask for national totals, pooled rates/percentages from matching counts, unweighted institutional means, and explicitly weighted means using source-backed fields.
- Filter annual populations by geography, public/private control, institution level, degree-granting status and Title IV status; group by source-coded sector/control/state fields.
- Ask for multi-year aggregate trends. Each annual query selects that year’s population and source evidence independently.
- Use the existing chart, formatting, presentation, table and download controls. Definitions & sources now includes aggregate scope; Excel includes population reporting units.

## Actual executor benchmark outcomes

| Outcome | Observations |
| --- | ---: |
| Matches original NCES precision | 393 |
| Numerical discrepancy: method/scope under review | 21 |
| Outside local source releases | 392 |
| Definition/ownership/method unresolved | 18 |
| **Total** | **824** |

These numbers come from the production population executor, not the separate reference SQL baseline. Expected values come only from the 45 supplied NCES workbooks. Counts require exact agreement, rates allow 0.05 percentage points, displayed dollar averages and financial totals in thousands allow half a displayed unit. All cases, including failures, are retained.

The original baseline classified missing-definition cases before checking local release years. This run checks the required source release first, so its outside-coverage count differs. No observations disappeared.

## What changed in the methods

- Institution counts exclude administrative offices. Salary/staff and financial reporting scopes include offices where that source definition requires them, with a visible caveat.
- Finance revenue fields distinguish operating/nonoperating revenue from all revenues plus additions and full FASB revenue totals. This resolved the systematic revenue discrepancies.
- Nonmedical 9–12-month instructional staff, all full-time instructional staff and all employees are separate populations. In EAP, graduate assistants occupy a separate category and are included when the requested total includes them.
- Pooled rates sum source counts, then divide. Complete-case numerator and denominator reducers use the same contributing reporting units. Missing values are not unconditional zeros.
- Source codebook counts/amounts, staff/student units, prior-cohort retention periods, FTE exposures and required-fee units are validated. Every categorical row key and join cardinality is still checked.
- Annual cohort labels are read from source evidence; an entering cohort is not a renamed release year. A one-year template binds actual field and category records separately in each release.

## Remaining discrepancies and unavailable methods

- 21 exact method/scope signatures with unresolved NCES differences are blocked from publication. The production guard stores fingerprints/reasons, not expected statistical values. It checks each output, so adding other outputs does not waive a known block.
- The guard is not a whitelist of allowed questions: unfamiliar source-backed queries still use the general unit/population/row/join validator. Its signatures are exact source methods, not a proof of equivalence for all possible alternative expressions.
- Some differences may reflect newer NCES final/revised values versus local older/provisional releases. That explanation is not assumed to resolve individual mismatches.
- Q8 age category was confirmed by the user as **25 and above** on October 21, 2026. All five locally covered observations (2015, 2017, 2019, 2021 and 2023) now match exactly. Annual EF age code 7 selects the existing 25-and-over subtotal once; all-student code 1 and grand-total EFAGE09 include full/part-time men and women. Unknown ages are excluded. The six older observations remain outside local releases. Selection evidence is saved separately in benchmark_clarifications.json; the original export is unchanged.
- Q200 was clarified by the user and added workbook notes: all undergraduate degree/certificate-seeking entering students, award completion within eight years, at U.S. Title IV degree-granting institutions. All eight cohorts (2009-10 through 2016-17) match NCES precision. For 2016-17, 2,889,755 completers / 6,106,613 adjusted-cohort students = 47.3217%, rounding to 47.3%, across exactly 3,473 institutions. Pool counts from OMCHRT=50; do not average institutional rates or add overlapping subcohort rows. Annual source evidence verifies the eight-year relationship between the entering cohort and outcome date.
- Q42 is now clarified as any distance-education participation (some or exclusively distance courses), across all fall students at U.S. Title IV institutions. All ten local years 2015–2024 match NCES precision; three earlier years remain outside local releases. In 2024, (5,218,918 exclusively + 5,569,198 some) / 20,066,904 total = 53.7607%, rounding to 53.8%. The source-bound plan explicitly opts into distance-partition reconciliation: blank categories are derived as zero only when the remaining nonnegative whole-student counts already sum exactly to the reported total. Suppressed, invalid and unresolved cells stay missing; contradictory partitions block publication. Each derived cell is audited and explained in sources. A typed source relationship validates the sum of these two disjoint categories as a percent of that same total.
- q110 still needs the precise national core-expense/FTE/reporting-unit method; its benchmark recipe remains blocked, not quietly omitted.
- Eight aid observations for source year 2023 have documentation assigning fields to SFA2223_P2 while physical values reside in SFA2223_P1. Existing ownership checks remain enforced; no automatic relocation was introduced.
- A national count adds institutional reports; it is not a deduplicated person count. Institutions with consolidated reporting and unmatched or missing records remain visible in coverage/audit information.
- National and named-institution scopes cannot be silently interchanged. A combined institutional/national comparison still needs a separate, explicit comparison construction.

## Tests and UI verification

- **116 regression tests passed** in 141.960 seconds, covering aggregate math, existing named-institution routes, percentages, source guards, conversation, charts, exports and Streamlit UI.
- Direct checks include national enrollment, graduation/retention and aid rates, institutional counts, staff counts, revenues, tuition means, state/sector scope checks, matched missing pairs, subtotal/rate-sum rejection, annual coverage, source-alias normalization and known-discrepancy publication blocks.
- Q200 update: **42 aggregate/calculation/query regressions passed** in 42.870 seconds, including an independent source-SQL count/rate comparison and negative checks for mismatched cohort years and four-year outcome substitution. The first sandboxed UI test attempt was interrupted and retained; the complete run with local networking available passed. Source-only Q200 rerun took 13.205 seconds (eight annual calculations 0.845–1.762 seconds each), with no model calls or API cost. These are executor timings, not full chatbot latency.
- Q42 update: **44 aggregate/calculation/query regressions passed** in 56.452 seconds. Tests preserve unresolved/suppressed blanks, reject negative and inconsistent counts, require the exact source family, verify national numerator/denominator and percent units, and retain UI/export coverage. Source-only Q42 timing is recorded in population_engine_summary.json; no model calls or API cost were used, so it does not measure full chatbot latency.
- Sector values are independently compared with source SQL and reconcile to the national total. A real live ten-year trend matches all ten NCES cells; the actual chat renders it as a line chart with two response popovers and no exceptions.
- **29 artifact/live-output verification checks passed**; 43 original workbook hashes remain unchanged. Q200 added notes and a Q42 byte-level revision (same parsed content) are recorded with original/current hashes and unchanged expected cells in source_revisions.json.

## Live latency and estimated cost

| Question | Answer-ready wall time | Estimated API USD | Result |
| --- | ---: | ---: | --- |
| enrollment | 39.69 s | $0.2124 | NCES exact count |
| sectors | 23.47 s | $0.1088 | 9 sectors reconcile |
| trend | 33.72 s | $0.1385 | 10/10 annual NCES values |
| graduation | 32.75 s | $0.1873 | 64.79%; 2018 cohort / 2024 outcome |

Median of these four successful live checks: **33.24 seconds**; total estimated provider cost **$0.6471**. This is a small descriptive sample, not an SLA; browser paint and download serialization are excluded.

Development failures are retained: the first enrollment plan had an alias/reducer representation problem, and the first graduation plan used an inner join despite a retain-missing policy. Their costs/timings are not erased or counted as successful runs; see the initial live files. A corrected source plan replay and a fresh successful graduation run are saved separately. The initial sandbox connection failure returned no usage and is not assigned a fabricated cost.

Numerical benchmark runs use no model calls ($0 API cost). The full pass and targeted local timeout recheck have separate recorded wall times. One transient salary-source timeout passed on the targeted recheck; its original failure is preserved in previous_attempt. Population fact scans now have a bounded 60-second read deadline; named reads retain 20 seconds. A timeout publishes no partial figures.

## Detailed outcomes by workbook

| ID | Subject | Match | Difference | Outside releases | Blocked method |
| --- | --- | ---: | ---: | ---: | ---: |
| q1 | Number of postsecondary institutions in the United States that award federal student aid | 10 | 0 | 14 | 0 |
| q2 | Number of students enrolled in postsecondary institutions annually | 9 | 1 | 14 | 0 |
| q3 | Number of students enrolled in postsecondary institutions in the fall | 10 | 0 | 13 | 0 |
| q4 | Number of degree-seeking undergraduate students enrolled in postsecondary institutions in the fall who are transfer-in students | 10 | 0 | 9 | 0 |
| q5 | Number of degree-seeking undergraduate students enrolled in postsecondary institutions for the first-time in the fall | 10 | 0 | 13 | 0 |
| q8 | Number of students, by age category, enrolled in postsecondary institutions in the fall | 5 | 0 | 6 | 0 |
| q12 | Number of full-time instructional staff are employed by degree-granting postsecondary institutions | 10 | 0 | 13 | 0 |
| q13 | Revenues (in thousands) of public postsecondary institutions using GASB standards | 10 | 0 | 11 | 0 |
| q15 | Revenues (in thousands) of private not-for-profit postsecondary institutions using FASB standards | 10 | 0 | 13 | 0 |
| q17 | Revenues (in thousands) of private for-profit postsecondary institutions using FASB standards | 10 | 0 | 13 | 0 |
| q19 | Graduation rate within 150% of normal time at 4-year postsecondary institutions | 9 | 1 | 13 | 0 |
| q20 | Graduation rate within 150% of normal time for bachelor's or equivalent degree-seeking undergraduate students who received a bachelor’s or equivalent degree at 4-year postsecondary institutions. | 7 | 3 | 13 | 0 |
| q21 | Graduation rate within 150% of normal time at 2-year postsecondary institutions | 10 | 0 | 13 | 0 |
| q22 | Graduation rate within 150% of normal time at less-than 2-year postsecondary institutions | 10 | 0 | 13 | 0 |
| q24 | Number of degrees/certificates awarded at postsecondary institutions | 9 | 1 | 13 | 0 |
| q25 | Number of full-time, first-time students receiving financial aid | 8 | 1 | 13 | 1 |
| q30 | Number of people employed by postsecondary institutions | 10 | 0 | 13 | 0 |
| q32 | Full-time retention rate in postsecondary institutions | 10 | 0 | 8 | 0 |
| q33 | Part-time retention rate in postsecondary institutions | 10 | 0 | 8 | 0 |
| q34 | Percent of full-time, first-time students receiving financial aid | 8 | 1 | 13 | 1 |
| q35 | Percent of undergraduate students receiving Pell grants | 8 | 1 | 6 | 1 |
| q36 | Average amount of Pell grants for undergraduate students | 8 | 1 | 6 | 1 |
| q37 | Percent of undergraduate students receiving federal student loans | 9 | 0 | 6 | 1 |
| q38 | Average amount of federal student loans received by undergraduate students | 8 | 1 | 6 | 1 |
| q39 | Expenses (in thousands) of public postsecondary institutions using GASB standards | 10 | 0 | 5 | 0 |
| q40 | Expenses (in thousands) of private not-for-profit postsecondary institutions using FASB standards | 10 | 0 | 13 | 0 |
| q41 | Expenses (in thousands) of private for-profit  postsecondary institutions using FASB standards | 10 | 0 | 13 | 0 |
| q42 | Percent of students enrolled in distance education courses | 10 | 0 | 3 | 0 |
| q43 | Number of full-time equivalent students enroll in postsecondary institutions annually | 9 | 1 | 6 | 0 |
| q50 | Adjusted 9-month average salary | 9 | 0 | 0 | 0 |
| q51 | Number of full-time instructional staff | 10 | 0 | 1 | 0 |
| q101 | Number of applications for admission from first-time, degree/certificate-seeking undergraduate students were received by postsecondary institutions in the fall | 10 | 0 | 1 | 0 |
| q102 | Percent of first-time, degree/certificate-seeking applicants to postsecondary institutions who were granted admission to enroll in the fall | 10 | 0 | 1 | 0 |
| q103 | Percent of admitted first-time degree/certificate-seeking undergraduate students who enrolled at postsecondary institutions in the fall | 10 | 0 | 1 | 0 |
| q110 | The total core expenses per full-time equivalent enrollment of public and private not-for-profit postsecondary institutions | 0 | 0 | 5 | 10 |
| q150 | Number of degree-seeking undergraduate students enrolled in postsecondary institutions for the first time in the fall | 5 | 0 | 6 | 0 |
| q155 | Number of degree-seeking undergraduate students who enrolled in postsecondary institutions within 12-months of graduating high school for the first time in the fall | 5 | 0 | 6 | 0 |
| q200 | Percent of undergraduate degree/certificate-seeking entering students | 8 | 0 | 0 | 0 |
| q205 | Average amount of tuition and required fees for full-time undergraduate students at public postsecondary institutions operating on an academic year calendar system | 9 | 1 | 13 | 0 |
| q206 | Average amount of tuition and required fees for full-time undergraduate students at private postsecondary institutions operating on an academic year calendar system | 7 | 3 | 13 | 0 |
| q207 | Average amount of tuition and required fees for full-time graduate students at public postsecondary institutions operating on an academic year calendar system | 10 | 0 | 13 | 0 |
| q208 | average amount of tuition and required fees for full-time graduate students at private postsecondary institutions operating on an academic year calendar system | 7 | 3 | 13 | 0 |
| q210 | Number of students awarded degrees/certificates at postsecondary institutions | 9 | 1 | 4 | 0 |
| q220 | Average amount of grant or scholarship aid from the federal government, state/local government, or the institution awarded to full-time, first-time  undergraduate students | 9 | 0 | 6 | 1 |
| q221 | Average amount of student loans  awarded to full-time, first-time undergraduate students | 8 | 1 | 6 | 1 |

## Files

- `population_engine_results.csv` / `.json`: production expected/actual values, plans, provenance and all outcomes.
- `population_engine_summary.json`: complete accounting and timing; `population_engine_run.log` and `population_engine_retry.log` retain full/recheck runs.
- `population_implementation_verification.json`, `population_regression_final.log`, `population_ui.json`: verification evidence.
- `population_live_enrollment.json`, `population_live.json`, `population_live_graduation_final.json`, `population_graduation_replay.json`: actual provider plans/responses, usage and development history.
- `REVIEW.md`, original reference files and application_results.json: frozen pre-change baseline (all 45 aggregate requests blocked). These are historical, not current app behavior.
- Reproduce with `evaluations/run_population_engine_benchmarks.py`, then this verifier. `--retry-timeouts` reruns only saved local query interruptions. `--q 8` reruns Q8 and retains other observations; earlier attempts are preserved. population_q8_run.log records the targeted comparison (no model calls/API cost).
- Current implementation rules: `prototype/POPULATION_AGGREGATES.md`. No original IPEDS data or NCES workbook was changed.
