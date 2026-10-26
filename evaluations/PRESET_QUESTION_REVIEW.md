# Shared example questions: initial review

October 21, 2026. Scope: shared Need ideas?/Explore IPEDS presets, especially F004/F006/F007. This review does not resume the paused national aggregate evaluation work. No app code or preset text was changed.

## Shared behavior

Both views read the same six topics and 18 examples from `prototype/learning_content.json`, render them with `example_buttons`, and submit `queue_example`. `run_pending` calls `execute_example` rather than the ordinary chatbot `ask` route. Twelve examples execute reviewed fixed plans; six use legacy document search. Existing preset tests check intent and nonempty output, which does not establish that a discovery response answers its question.

## Yale undergraduate and graduate enrollment (F004)

Exact question: “Give me Yale undergraduate and graduate enrollment from 2015 through 2024.” All 20 returned counts match independent annual EF A source rows. Annual codebook checks confirm EFALEVEL=2 is all undergraduates and EFALEVEL=12 is all graduates. Latest values: 6,814 undergraduates and 8,750 graduates in fall 2024.

Presentation issue: this example is labeled “Explore a trend” but its plan sets output to export. Final presentation has chart_type=none and show_table=true, so clicking it produces a table rather than a longitudinal chart. The initial narrative highlights one 2015 undergraduate count rather than describing both full series. These are presentation issues, not detected numeric discrepancies.

The first exploratory reference comparison mistakenly used EFALEVEL=3 for graduates. Codebook inspection showed that code means undergraduate degree/certificate-seeking. Corrected the review comparison to code 12 and verified every annual category label; the app's graduate counts were correct. This review correction is retained in the JSON note.

## Human Resources (F006)

| Example | Actual behavior | Issue |
| --- | --- | --- |
| What data does IPEDS collect about faculty and instructional staff? | Returns 30 codebook records; leading records repeat instructional-staff category codes across releases. | Does not use the current readable discovery answer. |
| What faculty salary variables are available? | Returns 30 codebook records, including salary variables. | Relevant evidence is present, but no synthesized answer groups available salary measures or explains scope. |
| What documentation is available for new-hire and salary definitions? | Returns 30 codebook records; leading hits are repeated historic new-hire category labels. | Search results do not establish a focused explanation of the requested documentation or definition changes. |

All three display the legacy message that statistical extracts need a reviewed plan. The topic description says statistical extracts are not mapped yet, which is stale after general query-engine/faculty work.

## Institutional Characteristics (F007)

| Example | Actual behavior | Issue |
| --- | --- | --- |
| What institutional characteristics can I find in IPEDS? | Returns 30 records led by annual imputation-method fields. | Search ranking fails to provide a useful overview of characteristics. |
| What are UNITID and the institution’s location fields? | Returns 30 records led by state category labels. | Does not directly define UNITID or explain the location fields. |
| How does IPEDS classify public and private institutions? | Returns 30 records led by institutional control/affiliation definitions across years. | Needs a direct explanation of public/private nonprofit/private for-profit categories, grounded in the intended directory field, rather than repeated search hits. |

The topic still labels arbitrary profile/filter extracts discovery-only; that statement needs revision against current source-bound engine capabilities and actual limitations.

## Related stale text

Enrollment still labels demographic breakdowns discovery-only. Outcomes still says national aggregation is deferred. Both conflict with capabilities added since these topic descriptions were authored. Update such descriptions with source-backed qualifications rather than implying universal analytical support.

## Proposed next changes

1. Make the Yale enrollment trend preset show a two-series line chart while preserving the verified data and table/download options.
2. Route discovery presets through the current evidence-backed discovery workflow; handle direct definition/category questions explicitly so a list of search hits is not mistaken for an answer.
3. Update topic descriptions and limitations to reflect current capabilities.
4. Verify answers to all six Human Resources/Institutional Characteristics questions, not just that records were returned; compare preset behavior with typed questions.
5. Review the reported scrolling issue separately (F005), using the actual interaction before changing scroll behavior.

Saved execution evidence: `preset_question_review_2026-10-21.json` contains the seven executed presets, exact responses, source comparisons and execution times. No model calls were made. Timings measure this direct preset path, not ordinary chatbot planning or browser rendering.

## Approved presentation and description changes

October 21, 2026: owner approved correcting the trend and refreshing descriptions, and requested explanation before any routing change. Changed only `prototype/learning_content.json`: Yale enrollment output is chart; enrollment, aid, outcomes, faculty and institution descriptions/scopes now reflect current capabilities and consequential source limits. Questions, plans' numerical selections, topic titles and routing remain unchanged. Faculty/institution text explicitly says the current examples search documentation; analytical capability is described separately without claiming every question works.

Verified both line series contain all ten observations and all 20 values still match independent source expectations. Two direct executions took 0.336 and 0.143 seconds, with zero model calls; no latency guarantee is inferred from two samples. The existing test exercising all 18 presets and home-to-chat navigation passed (one test, 9.958 seconds). Evidence: `preset_presentation_update.json`, `preset_presentation_ui.log`. Table/download options are retained. No app restart is needed for this JSON content change; views load the file on rerender.

Routing remains a pending design decision. Numerical presets can retain fixed validated plans and fresh local data retrieval. Discovery answers could use fixed reviewed explanations or current AI-assisted discovery with separately measured latency and repeatability; no such change is authorized or implemented yet. Owner values predictable answers and low click latency. Replacement Faculty & Staff/Institutional Characteristics questions are not finalized.

## Owner decision: numerical examples with validated preset plans

October 21, 2026: owner approved updating preset routing and chose to replace all six discovery presets with numerical questions. The agreed target is that every example retrieves/calculates current local source values using a predefined validated analysis plan, preserving predictable calculations and low latency. Do not route these clicks through fresh AI planning or implement an AI discovery rewrite for the six examples.

The existing twelve numerical examples already follow the intended route and remain unchanged. Select the replacement Faculty & Staff and Institutional Characteristics questions with the owner in the next discussion, then bind and validate their source plans and update both shared views together. The six current discovery examples remain unchanged until replacements are chosen; they have not been relabeled or presented as working numerical presets. This decision records the target routing policy; no runtime routing change or question replacement has yet been made. General discovery questions typed in chat remain a separate capability.

## Implemented Faculty & Staff replacements

Owner approved three numerical questions and implementation in both interfaces. Replaced all three faculty discovery presets with fixed reviewed version-2 catalog plans; their original IDs are retained for stable UI keys. Current totals: **15 numerical examples and 3 Institutional Characteristics discovery examples**, 18 overall. Faculty & Staff labels are consistent in both views. The salary question explicitly states nine-month-equivalent, nonmedical full-time instructional staff and 2023–24 (SAL2023_IS); the two count questions use EAP total instructional staff with/without faculty status, including medical-school staff where reported.

Verified all 31 observations against independent source rows, all six click paths, line/bar chart defaults, stable ten-point trend series and CSV/Excel serialization. No model planning or API calls. Three focused tests passed in 25.194 seconds and sixteen existing regressions in 57.091 seconds. Detailed rules and timings: `prototype/REVIEWED_EXAMPLES.md`, `evaluations/faculty_examples_verification.json`, `faculty_examples_tests.log`, `faculty_examples_regression.log`. Earlier initial findings remain historical; F006 is complete. F007 and the scrolling finding remain open.
