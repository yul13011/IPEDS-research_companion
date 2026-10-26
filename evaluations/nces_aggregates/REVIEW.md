# NCES aggregate benchmark baseline — October 21, 2026

## Main finding

**The current app cannot publish these national aggregate answers: all 45 analytical requests are blocked by its existing national/state/sector scope guard.** This is an application coverage gap, not 45 arithmetic failures. The guard has not been changed by this evaluation.

A separate read-only reference runner tests candidate aggregate methods against the supplied NCES values. These diagnostic results are **not production query-engine successes**. Agreement does not by itself establish that every NCES selection/filter has been recovered.

## Complete accounting

| Reference outcome | Observations |
| --- | ---: |
| Matches within benchmark precision | 311 |
| Numerical differences requiring investigation | 80 |
| Outside local source-release coverage | 375 |
| Definition/method needs clarification | 50 |
| Historical table/field mapping unresolved | 8 |
| Execution errors | 0 |
| **Total** | **824** |

## What was tested

- All 45 original workbooks, 824 year–value cells; original filenames, sheet/cell rows, titles, notes, and SHA-256 hashes retained.
- One explicit national analytical question per workbook, with its actual period labels, through `prototype.agent.ask(use_model=True)` in fresh context. The real guard returns before planning; fail-fast mocks prevent accidental provider calls. The institution-name/UI stage and browser rendering are excluded.
- Candidate source methods run against the existing 2015–2024 read-only annual databases. Each calculated observation retains the exact SQL/parameters, source field definitions and selector-code evidence, components/denominators, row counts, missingness and timing.
- No application behavior or original workbook values changed. No AI provider calls were made; estimated API cost is $0.

## Methods and interpretation

- Universe candidate: 50 states plus DC (FIPS 1–56), directory PSET4FLG 1 or 3. Per-case degree-granting, control and academic-year reporting-method filters are recorded in SQL. This candidate universe has not been approved as a complete NCES reporting-unit policy.
- Counts use source totals once. Completions use first major, all CIP programs total and AWLEVEL 15 (degrees/certificates total); summing the total and detailed award levels would double-count. This was corrected in the reference harness after inspecting the codebook, not the app.
- Rates use pooled numerators/denominators, not a simple average of institution rates. Aid/salary averages divide summed amounts by summed recipients/staff. Tuition/fees use the unweighted institutional average explicitly described in the NCES notes.
- Source table transitions are explicit: SFA parts P1 before 2024, combined SFA in 2024; student charges IC_AY before 2024, Cost1 in 2024. No source substitution across years to fill missing releases.
- Full-time staff from the salary table (9–12-month, nonmedical) are distinct from all instructional staff in the Fall Staff table. Total operating/nonoperating revenues differ from total revenues plus other additions. These distinctions were corrected in candidate methods using source descriptions.
- Missing/nonnumeric/suppressed/negative-coded values are not zeros. Reference calculations use complete source pairs/rows, with exclusions counted. This diagnostic missingness policy is not an approval to publish incomplete national totals.
- Academic-year enrollment, completions and aid periods bind to the source release ending that period; graduation cohorts map to the later outcome release. Table names alone do not prove period equivalence. Rows outside local releases stay untested.
- Counts require exact agreement; displayed dollar averages and totals in thousands allow half a displayed unit; rates allow 0.0005 as fractions (0.05 percentage points). Tolerances are recorded per row.
- A mismatch remains unresolved until NCES filters, reporting-unit exclusions, source release revisions and calculation semantics are reconciled. No mapping is selected just because it matches the benchmark.
- Release-vintage example: NCES q24 labels 2023–24 completions final, while our matching C2024 source lives in IPEDS_2024-25_Provisional. The later NCES export includes 2024–25 completions not present locally. This can explain some differences, but is not asserted as the proven cause of each mismatch.

## Clarifications and follow-up

- **Owner input requested: q8** needs the selected age category; **q200** needs the selected entering-student cohort/population and outcome. Those filters are not identified in their exports.
- **Method review: q43** needs the exact estimated/reported FTE choice and professional-practice treatment. **q110** needs the exact core-expense/FTE method, reporting-unit alignment and cross-component periods. These remain explicit pending cases.
- Investigate remaining numeric discrepancies and historical mapping gaps before treating these methods as accepted production specifications.
- Eight pending aid observations are in source year 2023: physical fields are in SFA2223_P1, while the original variable documentation places them under SFA2223_P2. Alternative documentation records are saved in the row audit; ownership is not silently substituted.
- Build national population/reporting-unit and missing-count support in the app before using these cases as end-to-end numerical acceptance tests. The current executor accepts at most 30 named institutions; raising that cap alone would not supply the missing population policy.

## Latency and cost

- Median analytical guard response: 0.0008 seconds. This measures a refusal/coverage check, **not time to calculate an unfamiliar question**.
- Median attempted reference observation, including metadata lookup and SQL: 0.124 seconds. This excludes AI planning, UI, and unsupported rows.
- API cost: $0; no provider calls. No claim about live AI aggregate latency can be made while the scope guard blocks these requests.

## Per-workbook results

| ID | Subject | Match | Difference | Outside coverage | Definition pending | Mapping pending |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| q1 | Number of postsecondary institutions in the United States that award federal student aid | 0 | 10 | 14 | 0 | 0 |
| q2 | Number of students enrolled in postsecondary institutions annually | 9 | 1 | 14 | 0 | 0 |
| q3 | Number of students enrolled in postsecondary institutions in the fall | 10 | 0 | 13 | 0 | 0 |
| q4 | Number of degree-seeking undergraduate students enrolled in postsecondary institutions in the fall who are transfer-in students | 10 | 0 | 9 | 0 | 0 |
| q5 | Number of degree-seeking undergraduate students enrolled in postsecondary institutions for the first-time in the fall | 10 | 0 | 13 | 0 | 0 |
| q8 | Number of students, by age category, enrolled in postsecondary institutions in the fall | 0 | 0 | 0 | 11 | 0 |
| q12 | Number of full-time instructional staff are employed by degree-granting postsecondary institutions | 0 | 10 | 13 | 0 | 0 |
| q13 | Revenues (in thousands) of public postsecondary institutions using GASB standards | 10 | 0 | 11 | 0 | 0 |
| q15 | Revenues (in thousands) of private not-for-profit postsecondary institutions using FASB standards | 0 | 10 | 13 | 0 | 0 |
| q17 | Revenues (in thousands) of private for-profit postsecondary institutions using FASB standards | 0 | 10 | 13 | 0 | 0 |
| q19 | Graduation rate within 150% of normal time at 4-year postsecondary institutions | 9 | 1 | 13 | 0 | 0 |
| q20 | Graduation rate within 150% of normal time for bachelor's or equivalent degree-seeking undergraduate students who received a bachelor’s or equivalent degree at 4-year postsecondary institutions. | 7 | 3 | 13 | 0 | 0 |
| q21 | Graduation rate within 150% of normal time at 2-year postsecondary institutions | 10 | 0 | 13 | 0 | 0 |
| q22 | Graduation rate within 150% of normal time at less-than 2-year postsecondary institutions | 10 | 0 | 13 | 0 | 0 |
| q24 | Number of degrees/certificates awarded at postsecondary institutions | 9 | 1 | 13 | 0 | 0 |
| q25 | Number of full-time, first-time students receiving financial aid | 8 | 1 | 13 | 0 | 1 |
| q30 | Number of people employed by postsecondary institutions | 0 | 10 | 13 | 0 | 0 |
| q32 | Full-time retention rate in postsecondary institutions | 10 | 0 | 8 | 0 | 0 |
| q33 | Part-time retention rate in postsecondary institutions | 10 | 0 | 8 | 0 | 0 |
| q34 | Percent of full-time, first-time students receiving financial aid | 8 | 1 | 13 | 0 | 1 |
| q35 | Percent of undergraduate students receiving Pell grants | 8 | 1 | 6 | 0 | 1 |
| q36 | Average amount of Pell grants for undergraduate students | 8 | 1 | 6 | 0 | 1 |
| q37 | Percent of undergraduate students receiving federal student loans | 9 | 0 | 6 | 0 | 1 |
| q38 | Average amount of federal student loans received by undergraduate students | 8 | 1 | 6 | 0 | 1 |
| q39 | Expenses (in thousands) of public postsecondary institutions using GASB standards | 10 | 0 | 5 | 0 | 0 |
| q40 | Expenses (in thousands) of private not-for-profit postsecondary institutions using FASB standards | 10 | 0 | 13 | 0 | 0 |
| q41 | Expenses (in thousands) of private for-profit  postsecondary institutions using FASB standards | 10 | 0 | 13 | 0 | 0 |
| q42 | Percent of students enrolled in distance education courses | 0 | 10 | 3 | 0 | 0 |
| q43 | Number of full-time equivalent students enroll in postsecondary institutions annually | 0 | 0 | 0 | 16 | 0 |
| q50 | Adjusted 9-month average salary | 9 | 0 | 0 | 0 | 0 |
| q51 | Number of full-time instructional staff | 10 | 0 | 1 | 0 | 0 |
| q101 | Number of applications for admission from first-time, degree/certificate-seeking undergraduate students were received by postsecondary institutions in the fall | 10 | 0 | 1 | 0 | 0 |
| q102 | Percent of first-time, degree/certificate-seeking applicants to postsecondary institutions who were granted admission to enroll in the fall | 10 | 0 | 1 | 0 | 0 |
| q103 | Percent of admitted first-time degree/certificate-seeking undergraduate students who enrolled at postsecondary institutions in the fall | 10 | 0 | 1 | 0 | 0 |
| q110 | The total core expenses per full-time equivalent enrollment of public and private not-for-profit postsecondary institutions | 0 | 0 | 0 | 15 | 0 |
| q150 | Number of degree-seeking undergraduate students enrolled in postsecondary institutions for the first time in the fall | 5 | 0 | 6 | 0 | 0 |
| q155 | Number of degree-seeking undergraduate students who enrolled in postsecondary institutions within 12-months of graduating high school for the first time in the fall | 5 | 0 | 6 | 0 | 0 |
| q200 | Percent of undergraduate degree/certificate-seeking entering students | 0 | 0 | 0 | 8 | 0 |
| q205 | Average amount of tuition and required fees for full-time undergraduate students at public postsecondary institutions operating on an academic year calendar system | 9 | 1 | 13 | 0 | 0 |
| q206 | Average amount of tuition and required fees for full-time undergraduate students at private postsecondary institutions operating on an academic year calendar system | 7 | 3 | 13 | 0 | 0 |
| q207 | Average amount of tuition and required fees for full-time graduate students at public postsecondary institutions operating on an academic year calendar system | 10 | 0 | 13 | 0 | 0 |
| q208 | average amount of tuition and required fees for full-time graduate students at private postsecondary institutions operating on an academic year calendar system | 7 | 3 | 13 | 0 | 0 |
| q210 | Number of students awarded degrees/certificates at postsecondary institutions | 9 | 1 | 4 | 0 | 0 |
| q220 | Average amount of grant or scholarship aid from the federal government, state/local government, or the institution awarded to full-time, first-time  undergraduate students | 9 | 0 | 6 | 0 | 1 |
| q221 | Average amount of student loans  awarded to full-time, first-time undergraduate students | 8 | 1 | 6 | 0 | 1 |

## Files and reproducibility

- `reference_results.csv`: convenient row-level comparison and SQL.
- `reference_results.json`: full source evidence and diagnostic detail.
- `source_manifest.json`: complete original benchmark observations, notes and hashes.
- `application_results.json`: all 45 actual guard responses and timings.
- `summary.json`, `verification.json`, `run.log`: machine-readable totals, independent checks and final run log.
- `initial_reference_results.json`: initial diagnostic run retained for transparency. It contains superseded candidate mappings (including overlapping completions totals); do not use it as the final result.
- Runner: `evaluations/run_nces_aggregate_benchmarks.py`; verifier/report builder: `evaluations/verify_nces_aggregate_benchmarks.py`. Run both from agent-redesign using the configured Python.

Artifact verification: **13 checks passed**, including source-file integrity, full row accounting and four independent SQL spot checks. These checks verify the evaluation artifacts, not full semantic validation of every candidate aggregate method.
