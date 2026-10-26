# IPEDS Research Companion implementation checklist

Last updated: October 22, 2026.

- [x] Shared unit metadata repair: **implemented**, with explicit unresolved cases.
  First build an evidence-backed catalog proposal and audit without changing answers;
  then integrate verified assignments across all consumers. Includes Smith rank counts,
  percentile scores, credit hours, ratios, currency scales and unresolved handling.
  [Saved plan and resume point](UNIT_METADATA_REPAIR_PLAN.md).
  [Implementation, audit and verification](evaluations/SHARED_UNIT_METADATA_REVIEW.md).
  Version 3 processes the original unresolved batch: 2,459 fixed units and 25
  institution-dependent program units. Broader independent verification remains open.
  [Current outcomes and remaining source review](evaluations/UNIT_RESOLUTION_IMPLEMENTATION_REVIEW.md).

Definition questions (F003) implemented: metadata-only answers route before institution/statistical planning; exact source passages, complete glossary qualifiers, explicit year/table/variable scope, reviewed formulas and bounded no-match handling. Verified 66 related regressions, 13 final focused tests (69 distinct cases), eight accepted application cases and 31 independent saved-source checks. App restarted. [Review, development corrections and limits](evaluations/DEFINITION_QUESTIONS_REVIEW.md).

Chat layout: Clear conversation now sits to the right of the input in the same row. Ten existing scroll/memory/clear UI checks passed; browser screenshot `evaluations/chat_composer_inline.png` verifies alignment. App restarted; numerical behavior unchanged.

Owner-supplied-source policy and gap-first responses implemented: explain a source coverage limitation before optional proxies; support no alternatives; require explicit proxy selection and retain source/method distinctions. Shared policy covers routing, catalog planning, discovery and session context. Verified 73 regressions plus 8 focused checks (74 distinct cases), seven saved-live checks and the exact women's-colleges question. [Review](evaluations/COVERAGE_GAP_POLICY_REVIEW.md). F025 completed; next findings ID F026.

Latest shared display fix: source-backed currency units replace the internal “monetary amount” suffix across summaries, result tables, charts and exports, including saved results. Values retain original precision/scale; unknown/conflicting evidence is explicitly unverified. Final acceptance: 3 focused tests plus 46 related regressions passed; 25 existing chart/text checks also passed in an earlier diagnostic run. App restarted and health checked. [Review and limits](evaluations/CURRENCY_UNITS_REVIEW.md).

Latest combined verification: **238 regressions passed in 801.422 seconds**, plus **3 JavaScript transcript-controller tests**. Added previously omitted clarification, scrolling and category-density modules to the combined runner; future runs print individual test names. Sandbox temporary-file/socket-pair failures were diagnosed separately before the successful run. Application behavior and defaults unchanged; aggregate benchmark reconciliation remains paused. [Scope and evidence](evaluations/REGRESSION_REVIEW_2026-10-21.md).

Evaluation only: completed a 16-question faculty-answer feasibility pilot for mandatory interpretation review, labelled alternative headcounts and constrained writing. All 52 output values matched original-source SQL; one answer added an unnecessary comparison row. Stricter writing required two fallbacks and one source-definition repair. Median initial count-answer latency was 8.67 seconds and estimated cost $0.035462 with preselected relevant documentation. Production behavior/defaults remain unchanged; F022/F023 remain open. [Pilot scope, baselines, samples and limits](evaluations/FACULTY_ANSWER_PILOT_REVIEW.md).

Conversation scrolling repair: stable transcript identity replaces revision/pending-dependent remounts; a single scroll controller follows new submissions and growing answers while respecting manual reading and formatting. Eleven affected UI/memory checks and three JavaScript controller checks passed, with additional real-browser long-conversation verification. See `evaluations/TRANSCRIPT_SCROLL_REVIEW.md`.

Chart readability update: single-period comparisons with more than 12 categories now default to the full table, with an explanation and explicit chart override. Years and clustered data cells do not inflate category counts. No data are dropped. Fifteen affected tests passed; see `evaluations/chart_density_tests.log` and `prototype/CHART_READABILITY.md`.

Latest implementation: source-bound analytical clarification and session analysis briefs. Offered alternatives are metadata validated before display; exact selections run saved plans without model replanning, and free-text revisions retain confirmed definitions. Qualified count/salary comparisons can use independent panels. Verified with 88 affected regressions, a final panel-period regression, 26 independent source/UI checks and the live Southern Connecticut faculty conversation. [Review, timing, cost and limits](evaluations/CLARIFICATION_WORKFLOW_REVIEW.md). This advances clarification under steps 4–6; it does not complete all methodological defaults, coverage validation or the paused aggregate benchmarks.

This is the current implementation tracker. Dated PROGRESS files preserve the history of changes and earlier checkpoints. Update this checklist after each completed development task, recording evidence, remaining limits and any owner decision needed.

Small testing observations and informal ideas are captured separately in [App findings and ideas](APP_FINDINGS_AND_IDEAS.md). Link them to this roadmap when they become planned work; capturing a note does not start implementation.

**Current focused work:** user requested review of the shared Need ideas?/Explore IPEDS examples (F004/F006/F007). Initial findings and verified counts are in [preset review](evaluations/PRESET_QUESTION_REVIEW.md). This supports steps 6–7; unrelated aggregate testing remains paused and step 5 remains the next unfinished roadmap step.

Approved preset update: F004 complete—all 20 Yale counts verified and the ten-year preset now renders two line series. Five topic descriptions/scopes refreshed. Both direct executions and existing all-example/navigation UI check pass ([evidence](evaluations/preset_presentation_update.json), [UI log](evaluations/preset_presentation_ui.log)). Routing, example wording and topic labels remain unchanged pending owner decisions; preserve predictable low-latency numerical plans.

Latest preset decision: owner wants **all examples to be numerical**, using predefined validated source plans and fresh local data retrieval, rather than AI planning per click. Existing twelve numerical examples already follow this policy. Choose the six replacement Faculty & Staff/Institutional Characteristics questions in the next discussion, then implement/verify their source plans. Current six discovery presets remain unchanged until replacements are agreed; no new routing code has been applied yet.

Step 5/6 supporting review: all six expanded-topic caveats traced to loaded source documentation and relevant app behavior; admissions scope, SAT median availability, C reporting periods and six-year example cohorts checked across the loaded releases. Topic/example definitions must not be presented as universal IPEDS rules. [Review and proposed wording](evaluations/TOPIC_CAVEAT_REVIEW.md), [source evidence](evaluations/topic_caveat_source_evidence.json). No UI wording/default changes in this review; aggregate benchmarks remain paused.

Approved caveat corrections are now implemented for all six topics. Verified the final text in all six expanded Explore IPEDS info boxes with no UI exceptions ([UI evidence](evaluations/topic_caveat_ui_verification.json)). This is an explanatory-text update; no query rules, routing or methodological defaults changed. Need ideas? shares the topic/example definitions but does not display these blue boxes. Source review above records the pre-change findings; aggregate testing remains paused.

Faculty preset implementation: **F006 completed**. Three new numerical Faculty & Staff presets run fixed source-bound catalog plans in both Explore IPEDS and Need ideas?. Thirty-one values independently verified, all six UI click paths passed, CSV/Excel work, and the ten-year chart has two connected series. Three focused tests plus sixteen existing regressions passed. Source-year salary scope explicitly uses SAL2023_IS for 2023–24 and nine-month-equivalent nonmedical salaries. Named annual templates retain existing source and scope checks. [Rules/evidence](prototype/REVIEWED_EXAMPLES.md), [results/timing](evaluations/faculty_examples_verification.json). F007 Institutional Characteristics questions remain to be selected; general aggregate benchmarks remain paused.

Faculty salary chart follow-up: **F019 completed**. Shared grouped bars now have explicit gaps, legend-consistent institution order and height responsive to bar/label sizes. Preserved spacing in slide exports; no data changes. Before/after images inspected, rendered bar positions tested at default/max width, and fifteen chart/formatting checks passed ([log](evaluations/faculty_salary_chart_spacing_tests.log)).

Color-control follow-up: **F020 completed**. Style controls and prompt color targets now use the actual rendered color mapping. Salary bars list three institution colors, matching the legend; picker/prompt changes preserve other colors and data. Eight existing formatting/edit checks passed plus the focused real-UI recoloring check ([focused log](evaluations/faculty_salary_color_controls_focused.log)).

Whole-chart acceptance / **F021 completed**: two integrated workflow/edge-case tests pass, plus seventeen existing chart/formatting/edit regressions. Verifies nine independent salary source values, actual UI edits/legend/controls, separate panels/shared scales, chart-type changes, Reset/Undo and PNG/SVG outputs at both slide sizes. Tests source/missingness preservation and larger bars/fonts/long labels. Reporting-period label angle is now shown only for line charts; wrapped category spacing follows font size. Preview controls use the actual function with an exact-state dialog harness because AppTest full reruns dismiss button-opened dialogs. [Scope, limitations and evidence](evaluations/CHART_WORKFLOW_VERIFICATION.md). This supports steps 6–7 without claiming universal chart coverage or resuming national benchmarks.

Latest owner decision supersedes the line-only angle control: manual axis tick-label rotation is removed for now, from Format chart and previously supported prompt edits. Automatic label layout remains; cached/manual/preset angle overrides are ignored. Updated formatting/workflow checks and evidence in `evaluations/axis_rotation_removed_tests.log`. Other chart capabilities and aggregate-testing pause remain unchanged.

**Current milestone:** original analytical expansion steps **1–4 are implemented within documented bounds**. **Step 5 is next and partially implemented; steps 6 and 7 have partial progress.** Aggregate testing is paused at the user's request. No testing or methodological-default changes are started by this documentation update. Comprehensive all-question IPEDS coverage and production readiness remain open. Earlier combined regression evidence includes 163 passing tests; the Q42 update passed 44 relevant regressions and 29 artifact checks. These are different test scopes, not additive coverage percentages.

## Original seven-step roadmap and current progress

This is the original implementation list, preserved in its original order. The numbered steps are the primary roadmap; R1–R11 below are supporting task identifiers, not replacements for steps 5–7. Implementing a rule along the way does not complete its entire roadmap step. No requirement to map every IPEDS variable manually is placed on the owner.

### 1. Define the coverage target — completed for supplied data

- Decide whether “all IPEDS data” means **all data already supplied** or **all publicly available IPEDS datasets and years**.
- Inventory the loaded years, survey components, tables, and codebooks.
- Identify missing datasets or documentation and acquire them.
- Create a coverage report showing what is loaded, discoverable, and analytically supported.

**Progress:** Owner defined the scope as all data and codebooks in `C:\Users\liyuj\OneDrive\2026\IPEDS Project\IPEDS Data`. Ten releases, 2015–16 through 2024–25 (latest provisional), were inventoried. This completion does not claim to include every public IPEDS release or establish analytical support for every loaded variable. Evidence: [scope](ANALYTICAL_COVERAGE_SCOPE.md), [inventory](data/coverage_scope_2026-10-19.json).

### 2. Make the full catalog usable for analysis — implemented, known conflicts retained

- Connect every physical field to its definition, category codes, reporting period, population, and unit.
- Document each table’s row structure and unique keys.
- Define valid relationships between tables.
- Record missing-value conventions, imputation flags, provisional status, and known documentation conflicts.
- Track variable and definition changes across years.

**Progress:** Searchable catalog, source bindings, key/period/population evidence and annual inspection are implemented. Unknown units, missing documentation and ownership conflicts remain explicit; completion means they can be inspected and validated, not that all meanings and relationships have been resolved. Evidence: [catalog](ANALYTICAL_CATALOG.md), [verification](data/analysis_catalog_verification.json). Further conflict/crosswalk work is tracked by R2–R4.

### 3. Replace the fixed-measure restriction — implemented

- Preserve existing reviewed measures as a reliable route for familiar questions.
- Add a discovery route for questions outside that list.
- Let the planner propose fields, filters, groupings, calculations, and joins using catalog evidence.
- Expand the plan format beyond the current institution–measure–year selections.
- Remove blanket prohibitions only as the corresponding capabilities become validated.

**Progress:** Reviewed and catalog routes coexist; typed source-bound plans support unfamiliar questions without a historical test-case whitelist. Models cannot supply executable SQL. National/sector aggregate support was subsequently added with source validation and known-discrepancy guards. Evidence: [planning](prototype/CATALOG_PLANNING.md), [query engine](prototype/QUERY_ENGINE.md), [aggregates](prototype/POPULATION_AGGREGATES.md).

### 4. Build a general query and validation engine — implemented within bounds

- Compile evidence-backed plans into bounded, read-only queries.
- Validate fields, category codes, populations, years, and join relationships before execution.
- Support breakdowns, percentages, trends, comparisons, and appropriate aggregations.
- Prevent duplicate counting and invalid combinations of populations.
- Check totals, denominators, missingness, and cross-year comparability.
- Return clarification or a specific limitation when validation fails.

**Progress:** Engine primitives, runtime grain/cardinality checks, request/plan/result checks, global population reducers and independent annual queries are implemented. Validation does not certify every possible formula, interpretation or historical crosswalk. Q8, Q200 and Q42 benchmark methods are verified for locally covered observations. Q110 still needs production integration/validation; aid ownership conflicts and numerical discrepancies remain open. Evidence: [engine](prototype/QUERY_ENGINE.md), [intent checks](prototype/INTENT_VALIDATION.md), [current aggregate review](evaluations/nces_aggregates/POPULATION_IMPLEMENTATION_REVIEW.md).

### 5. Establish methodological defaults — next; partially implemented

These are the decisions where owner input matters most:

- Define defaults for ambiguous terms such as “enrollment,” “graduation rate,” and “financial aid.”
- Decide how to present unknown race, nonresident students, and other reporting categories.
- Define rules for national/sector totals, institutional branches, and changing institution identifiers.
- Define when to ask the user for clarification.
- Document defaults and disclose consequential assumptions in answers.

**Progress:** Institution confirmation, remembered session naming conventions, reporting-institution caveats, source-specific populations, pooled percentages, missingness disclosures and explicit aggregate scope rules exist. These scattered rules have **not** been consolidated into an owner-reviewed methodological-defaults policy. Custom race/ethnicity groupings, ambiguous measure defaults and institution-change handling are not comprehensively settled. Existing evidence: [institution rules](prototype/INSTITUTION_CONFIRMATION.md), [answer/source rules](prototype/RESULT_TEXT_RULES.md), [aggregate rules](prototype/POPULATION_AGGREGATES.md).

**Next action when authorized:** inventory current rules, distinguish existing behavior from proposed defaults, identify gaps, and present concrete choices with consequences for owner decisions. Do not silently establish new defaults during this documentation task. Related tasks: R4–R6; aggregate implementation progress is already recorded below. No owner variable mapping is required.

### 6. Extend answers and downloads — partially implemented

- Support dynamically discovered measures in charts, tables, definitions, and exports.
- Include the population, time basis, calculation, and source evidence.
- Distinguish “not implemented” from “not available in the source.”
- Retain important warnings and missing-data distinctions.
- Save validated mappings for reuse without treating successful execution alone as proof of correctness.

**Progress:** Dynamic validated results feed charts, tables, Definitions & sources and Excel/CSV/provenance downloads. Chart formatting/presentation exports and aggregate scope/reporting-unit evidence are implemented. Discovery has catalog-grounded interpretation and evidence-linked AI writing. Broader consistency of limitation wording and a systematic reviewed-mapping reuse workflow still need an explicit audit; step 6 is not fully certified. Evidence: [answer rules](prototype/RESULT_TEXT_RULES.md), [presentation charts](prototype/PRESENTATION_CHARTS.md), [discovery](prototype/DATA_DISCOVERY.md), [aggregate review](evaluations/nces_aggregates/POPULATION_IMPLEMENTATION_REVIEW.md).

### 7. Validate coverage before claiming it — partially implemented; testing paused

- Start with **Yale undergraduate enrollment by race/ethnicity** as the first end-to-end case.
- Build reference questions across every loaded survey component.
- Test multiple institutions, years, breakdowns, calculations, and joins.
- Test ambiguous questions, unavailable data, and changing definitions.
- Keep existing regression checks and investigate discrepancies.
- Publish a coverage matrix and expand it as capabilities pass validation.

**Progress:** Numerous institution, breakdown, percentage, trend, follow-up, clarification, chart/export and aggregate checks are saved. A comprehensive survey-family/question-type coverage matrix and held-out acceptance suite remain open (R1/R8); passed samples do not establish universal IPEDS coverage. Latest production aggregate accounting: **824 observations: 393 matches, 21 numerical discrepancies, 392 outside local coverage, 18 unresolved definition/ownership/method observations**. Those 18 comprise ten Q110 years and eight 2022–23 aid observations (Q25/Q34/Q35/Q36/Q37/Q38/Q220/Q221). Q110's separate 9/10 diagnostic matches are not production passes. Evidence: [current review](evaluations/nces_aggregates/POPULATION_IMPLEMENTATION_REVIEW.md), [Q110 diagnosis](evaluations/nces_aggregates/Q110_METHOD_REVIEW.md).

**Pause:** User asked to set testing aside on October 21, 2026. Preserve results and resume later; no additional owner research is currently required. Establishing step 5 defaults is the next roadmap item, not automatic authorization to resume tests.

## Implementation evidence for completed steps 1–4

- [x] **1. Define and inventory “all IPEDS data.”** Scope is all data/codebooks in the supplied `IPEDS Data` folder: ten releases, 2015–16 through 2024–25, with the latest provisional. Imported physical table coverage and source/document identities were checked. Evidence: [coverage scope](ANALYTICAL_COVERAGE_SCOPE.md), [inventory verification](data/coverage_scope_2026-10-19.json).
- [x] **2. Make the full catalog usable for analysis.** Searchable evidence covers 554 physical tables (505 institution-data, 49 metadata), 25,245 physical fields, 23,990 variable definitions and 124,493 category-code records. Period/population, key, physical-location and cross-year evidence are inspectable. Conflicts and unavailable imputation flags remain explicit. Evidence: [catalog documentation](ANALYTICAL_CATALOG.md), [catalog checks](data/analysis_catalog_verification.json).
- [x] **3. Replace the fixed-measure restriction.** Familiar reviewed measures retain their route; unfamiliar questions can inspect the full catalog and submit typed source-bound plans. A matching historical test case is not required. Models cannot submit executable SQL. Evidence: [catalog planning](prototype/CATALOG_PLANNING.md), [general calculations](prototype/GENERAL_CALCULATIONS.md).
- [x] **4. Build a general query and validation engine.** Implemented bounded grouped extracts, explicit-domain aggregates, one-to-one/many-to-one fact joins, weighted means, acyclic multi-step formulas, percentage change, cohort/period checks, signed financial values and missingness rules. Metadata validation is followed by observed grain/cardinality/result checks. Summaries, charts, tables and exports use the validated result. Evidence: [engine acceptance criteria and limits](prototype/QUERY_ENGINE.md), [combined regression report](evaluations/catalog_execution_verification.json), [live engine checks and latency](evaluations/query_engine_latency.json).

Step 4 completion covers the engine primitives and their documented bounds. It does not approve every variable interpretation, crosswalk, population definition or possible formula. Existing limits include 30 named institutions, 20 relations, 20,000 selected rows per source and 5,000 output rows. National/state/sector population selection was subsequently implemented; remaining methodological and benchmark issues are documented below.

## Completed supporting work

- [x] **Independent request → plan → result protections.** Original-request contracts check explicit institutions/time windows, independently extracted observation counts, supported source-backed breakdowns/percentages and known enrollment populations before fact queries. Returned coverage is checked per institution and reviewed measure; invalid summaries, cached charts, tables and downloads are withheld. Missing values retain period slots and get a material caveat when too few values remain for a trend. Eleven new injected-failure/conversation tests cover all three execution routes, real annual counts → trend → percentages, new topics, legitimate cross-period/academic/cohort cases, population mismatches and cached display protection. No model calls are added. Evidence: [rules and bounded coverage](prototype/INTENT_VALIDATION.md), [combined verification](evaluations/catalog_execution_verification.json), [conversation timings](evaluations/intent_conversation_latency.json), [live replay](evaluations/trend_followup_live_intent.json).

- [x] **Trend follow-ups bind complete time windows.** Fixed “10-year trend ending with Fall 2024” being reduced to a single 2024 observation. Shared date binding expands inclusive windows before endpoint extraction; catalog windows take precedence over inherited single years, and pure time-only requests retain institution context. Explicit dates, cohort/class distinctions and validation bounds remain. Actual Streamlit follow-ups render a line with all ten year ticks; live before/after replay confirms ten observations for both reported prompts. Evidence: [time rules and cause](prototype/TIME_SCOPE.md), [live replay/latency](evaluations/trend_followup_live_after.json), [regression report](evaluations/catalog_execution_verification.json).

- [x] **Presentation chart workflow.** Format chart offers Layout/Text/Style/Axes controls sharing settings with prompt edits. Per-series colors, fonts, labels, legends, markers, gridlines, number formats, separate panels and reference lines are supported, with Undo/Reset. Preview & download chart creates complete PNG/SVG figures at fixed full/half-slide dimensions, including titles and actual sources/material caveats. Formatting never queries or changes data. Five additional tests check compound commands, analytical routing, gaps, actual rendered styles, exact PNG dimensions/SVG contents, real UI → chat → preview → undo/reset. Evidence: [presentation rules and limits](prototype/PRESENTATION_CHARTS.md), [combined report](evaluations/catalog_execution_verification.json). Native/editable PowerPoint, persistent personal themes and advanced chart types remain future presentation work.

- [x] **Chart edits verified through the chat UI.** Fixed natural axis-label wording (`Change x-axis to "Year"`) and retained the last available result after a rejected edit. Three focused tests use real Mount Holyoke/Smith results and inspect actual emitted charts, not only settings: line/bar type, chart/axis titles, numeric range/reset, named/hex color, bar ordering, table show/hide, native table/count-status controls, tooltips and percentage bounds. Supported edits preserve full results and do not call the analytical/model pipeline. All 142 combined regressions passed. Evidence: [verified controls](prototype/CHART_READABILITY.md), [UI control matrix](prototype/tests/test_chart_edits.py).

- [x] **Official College names and reliable exact matching.** Literal full directory names override incomplete model mentions; unique full-name formatting variants can resolve without confirmation. Ambiguous/colliding formats and non-exact shorthand still require selection, even with one candidate. Institutions named College do not receive a separate-college warning merely because of that word or a confirmed spelling variant. Genuine reporting-scope changes retain a carefully worded caveat, with no unsupported claim that a record is absent; legacy displays are corrected from identity mappings. Twenty focused tests and all 139 combined regressions passed. Exact Mount Holyoke College live prompt returned all ten source-verified enrollment counts without institution clarification or a false warning (10.963 s); shorthand still required selection (2.094 s). Evidence: [matching rules](prototype/INSTITUTION_CONFIRMATION.md), [live replay](evaluations/institution_exact_name_live.json).

- [x] **Informative table-level Sources.** Definitions & sources now shows exact IPEDS release/status, survey, year coverage and TableName, grouped under descriptive codebook table titles. Metadata is read for executed sources, deduplicated by release/table and never inferred from workbook filenames. Missing/conflicting metadata is explicit; full workbook/sheet/row references remain in Excel/JSON. Eight focused source/text/export/UI tests and the final 136-test combined suite passed, including all ten annual undergraduate gender source tables, reviewed and joined results, and missing/conflicting metadata. Evidence: [source display rules](prototype/RESULT_TEXT_RULES.md), [source tests](prototype/tests/test_result_text.py).

- [x] **Ten-year undergraduate gender counts and percentages through chat.** Broadened the existing first-time source-bound planner to total undergraduate populations and explicit attendance scopes. Counts remain the default; shares bind each annual numerator and denominator independently. Raised the bounded version-1 calculation allowance from 12 to 40, supporting 20 annual shares. Conversation paraphrases retain scope, and offline percentage continuations do not become institution names. Three live chat cases passed with all numerical values independently checked: counts 10.861 s, explicit percentages 2.481 s, follow-up percentages 5.649 s (one descriptive run). Latest combined suite passed 132 tests; seven gender tests were repeated after final conversation-handoff changes. Evidence: [live cases and latency](evaluations/enrollment_gender_latency.json), [population rules](prototype/CATALOG_EXECUTION.md).

- [x] **Connected annual catalog trend lines.** Fixed per-release series identifiers that turned catalog line charts into isolated dots. New catalog results use a stable line segment; the renderer also handles older saved per-release identifiers. Explicit source-protocol breaks and missing-value gaps remain. Real ten-year Yale undergraduate gender results verify two ten-point line groups. Nine chart plus ten catalog-execution tests passed; latest combined evidence remains the prior 129-test run.

- [x] **Every year labelled on longitudinal charts.** Time axes retain every reporting-period/year label in chronological order, including cohort years, rather than selecting four ticks. More than six labels use a 45-degree angle; label skipping is disabled. All eight chart regressions passed, including all ten 2015–2024 labels across multi-panel institution trends. Latest combined evidence remains the prior 129-test run.

- [x] **Actual working-stage messages in chat.** Replaced the fixed spinner phrase with a single muted line updated by real institution, conversation, planning, metadata, validation, annual-read, join/calculation and answer-preparation operations. Status remains in the assistant bubble, clears on completion/failure and uses a request-scoped callback. No additional model calls, invented percentages or countdown. Three loading/progress tests verify actual offline stages, bubble placement/cleanup and callback isolation; repeated after the final muted styling. Latest combined suite: 129 passing tests.

- [x] **Labelled clarification and annual faculty planning.** Bare `(a)` replies retain the selected population and years. General annual metadata retrieval and compact template submissions bind exact evidence for each release and use the ordinary validator. Version-1 filters now allow 40, accommodating ten years with three selectors per year; source-defined categorical keys need not be repeated literally in table prose. Generic employee labels include the selected population. Live Yale faculty replay returned all ten years with all values independently verified; answer-ready latency 42.266 seconds in one run. Evidence: [annual planning rules](prototype/CATALOG_PLANNING.md), [live replay and source checks](evaluations/faculty_clarification_live.json), [October 20 progress](PROGRESS_2026-10-20.md). These are general mechanisms, not Yale-specific coverage.

- [x] **Conversation context across query routes.** Up to 12 recent turns plus active analytical context are supplied within a bounded payload; 30 exchanges are retained for display. Semantic resolution supports institution changes, percentages, topic switches and earlier references. New conversation clears session state. Evidence: [memory design and limits](prototype/CONVERSATION_MEMORY.md), [live five-turn checks](evaluations/memory_latency.json).
- [x] **Institution confirmation before analysis.** Original wording is checked before conversational rewriting. Non-exact, unconfirmed names require an explicit selection with no default. Exact names/UNITIDs and a narrow documented alias set may proceed. A request-local guard blocks unconfirmed campus substitution. Evidence: [institution rules](prototype/INSTITUTION_CONFIRMATION.md), [live Michigan check](evaluations/institution_confirmation_live.json).
- [x] **Remember clarified naming conventions.** Confirmed name-to-UNITID mappings persist for the session, including across topics and transcript trimming. They clear with New conversation. Gender-to-race reuse of “Yale College” was verified live. Evidence: [convention memory check](evaluations/institution_convention_memory.json).
- [x] **Relevant institution candidates and confirmation layout.** Distinctive name/location evidence is required; shared “College” alone cannot qualify Salem College for Yale College. Conservative spelling variants remain searchable. The institution selector appears above the refinement input; Continue and Cancel are tested.
- [x] **College versus reporting-institution distinction.** Longer typed College/School/Campus wording cannot be swallowed by a shorter alias. Selecting a university does not establish a separate college record. The exact Yale College ten-year question was tested with all annual counts independently checked. Evidence: [Yale College check](evaluations/yale_college_confirmation.json).
- [x] **Response controls and workspace.** Display table, adjacent Definitions & sources and Download Data controls; Excel/CSV/audit exports; loading inside the conversation; transcript scrolling; revised page spacing and shared Hide Menu/Expand Menu control.
- [x] **Clear conversation near the composer.** A compact control appears above the chat input when messages, a confirmation or an error exists, including an error on the first question. It clears messages, error state, pending selections and remembered institution choices. The existing New conversation control remains available in Tools.
- [x] **Latency and usage instrumentation.** Server answer-ready time includes planning, conversation and institution resolution. Query/validation phases, model calls and estimated usage/cost are retained; export timings are separately tested. Human confirmation wait and browser paint are excluded.

## Remaining work

These are supporting tasks linked to the original roadmap above. They do not replace the seven steps or change their order. Original step 5 is next; testing tasks remain paused at the user's request.

| ID | Status / priority | Task | Completion evidence | Owner input |
| --- | --- | --- | --- | --- |
| R1 | Open / testing paused; step 7 | Build a survey-family and question-type coverage matrix; expand held-out live acceptance cases across institutions, years, paraphrases and follow-ups. | Matrix distinguishes successful execution, safe clarification, source limitation and implementation gap; independent source checks, selection accuracy and latency for each case. | None to start when testing resumes; real user questions are useful optional feedback. |
| R2 | Open / high | Improve unresolved numeric semantics and planner retrieval based on R1 failures. | Source-supported repairs plus regression cases; unresolved meanings remain explicit. | Only concrete analytical ambiguities; no owner field mapping required. |
| R3 | Open / high | Review source/documentation conflicts, unmatched relationships and existing benchmark discrepancies. | Each issue is corrected with evidence or documented as an accepted source limitation; no guessed mappings. | Only if choosing between genuinely defensible interpretations is necessary. |
| R4 | Open / high | Expand cross-year comparability, classification crosswalks and institutional-change handling. | Reviewed examples for changed definitions/codes, renamed/merged institutions and reporting-unit changes; gaps and breaks disclosed. | Method decisions when a source change permits multiple interpretations. |
| R5 | Implemented capability / methodology review remains; steps 4–5/7 | National/state/sector population selection and aggregate methodology are implemented. Consolidate existing scope rules into step 5 defaults; retain unresolved method/benchmark limits. | Source-bound population queries, current aggregate review and saved test evidence; universal coverage is not certified. | Review consequential default choices in step 5; no new decision is presumed from implementation alone. |
| R6 | Open / feature expansion | Add requested custom groupings and metrics, including custom URM definitions. | Written definitions, disjointness/denominator evidence and positive/negative tests. | The requested custom definition; do not invent a default grouping. |
| R7 | Open / performance | Reduce discovery/context overhead and benchmark latency systematically. | Cold/warm and multi-turn latency distributions, failure/timeouts, call counts and cost; correctness unchanged. | Agree acceptable response-time/cost targets before treating them as release gates. |
| R8 | Open / release preparation | Define release gates and run broader end-to-end user acceptance. | Accuracy/clarification/latency targets met on a held-out suite; charts, tables and all downloads reconcile; critical defects closed. | Owner acceptance priorities and representative workflows. |
| R9 | Open / deployment preparation | Decide hosting, data updates, concurrency, observability, budgets and retention; implement a reproducible deployment/update process. | Deployment and rollback rehearsal, isolated concurrent sessions, source-version checks and documented retention/access behavior. | Intended audience, hosting/access model, budget and retention policy. |
| R10 | Optional / undecided | Add saved conversations or cross-session preferences. | Explicit save/reopen/delete behavior and retention/access tests. | Whether durable memory is wanted and what should be retained. Current memory is session-only. |
| R11 | Open / reliability | Handle oversized planning-tool batches gracefully. The reported “Too many planning tool requests in one call” guard can still fire. | Bounded planner feedback/repair or a clear recoverable response, without bypassing tool limits or executing an unvalidated plan. | None to start. Clear conversation is available for reset; the underlying limit handling is separate work. |

Original **step 5, Establish methodological defaults**, is the next roadmap item. R1 remains part of step 7 when testing resumes. Logging this backlog does not start implementation, change methodological defaults or resume paused testing automatically.

## Known limits to retain in evaluations

- Semantic parser version 2 describes all 23,990 definitions; 14,768 have recognized units and 9,222 retain explicit unknowns. Unknowns include categorical/non-quantitative fields, so 9,222 is not a count of unavailable numeric measures. Evidence: [semantic snapshot verification](data/field_semantics_verification.json).
- Supplied extracts omit item-level imputation flags; the app cannot infer whether each value was imputed. Source-location conflicts and historical classification changes still require evidence.
- The reviewed Yale benchmark retains 229 matches and 13 source discrepancies; the engine expansion has not resolved those discrepancies.
- Passing 124 regressions is not a percentage of the entire IPEDS question space. Live case reports are small samples. Recent unfamiliar-answer timings range from roughly 8 seconds to 50 seconds across different tests; inspect each report's scope before comparing timings.
- Confirmed school/college wording refers to the selected reporting institution; separate subdivision figures are not automatically established.

## Maintenance procedure

1. Keep completed items checked and preserve their supporting reports.
2. When starting a remaining task, mark its status In progress and record scope/acceptance criteria.
3. Before marking it Complete, record what changed, verification and remaining limitations. Ask the owner only for an actual pending decision.
4. Append a short entry to the dated progress log and update this checklist's date, current milestone and regression count. Keep older reports/history as dated evidence.

## Chart readability milestone — October 19, 2026

- [x] Shared readable renderer: horizontal bars, automatic titles/scope, source-based labels, direct values, adaptive sizing, meaningful sorting, zero/percent axes, shared comparable scales and four-series trend panels.
- [x] Keep totals separate, preserve Unknown/Nonresident, source timing and protocol gaps, and retain every requested observation.
- [x] Preserve existing table/source/download controls and full-precision results; bar-type follow-ups keep distinct years.

Evidence and remaining visual limits: [CHART_READABILITY.md](prototype/CHART_READABILITY.md), chart tests in the combined regression report and browser preview images. Final verification is recorded in the dated progress log.


## Reader-facing answer/source separation — October 19, 2026

- [x] Separate substantive highlighted caveats from planner/validation technical notes.
- [x] Replace raw repeated source text with concise definitions, population/period, plain-language calculation and codebook references.
- [x] Retain full originals, formulas, SQL, proofs and technical notes in downloads; preserve actual scope/missingness/comparability/provisional warnings.

Evidence and limits: [RESULT_TEXT_RULES.md](prototype/RESULT_TEXT_RULES.md), result-text tests and combined regression report.


## Active-query panel controls — October 20, 2026

- [x] Preserve submitted questions across Streamlit interruptions from collapsing Need ideas or Analysis tools.
- [x] Clear pending requests only after committed completion or a handled failure.
- [x] Regression tests exercise both collapse controls after interruption and verify one completed exchange. Four loading/lifecycle tests passed (9.195 seconds).

Limit: panel reruns can restart interrupted processing; this does not provide background execution or cross-session recovery.

- [x] Editable custom chart footnote in Text, shared with prompt edits and included in preview/PNG/SVG; preserve source attribution and required caveats. Verified October 20 in chart-format UI/export tests.

## Topic data discovery — October 20, 2026

- [x] Answer explicit topic availability questions with source-backed data areas, survey/reporting-period/table references and example fields.
- [x] Keep raw evidence under Definitions & sources; distinguish local catalog coverage from institution-level completeness.
- [x] Use metadata-only retrieval without institutional clarification or statistical queries; retain bounded-search/no-match safeguards. AI mode now adds a separate evidence-linked writing step (see below).
- [x] Log per-topic latency and include discovery tests in the regression runner. Final focused/related verification: 33 tests passed; see dated progress log and prototype/DATA_DISCOVERY.md.

Remaining limits: keyword/synonym recall and eight-family display cap; semantic or exhaustive catalog coverage and institution-specific completeness are not guaranteed by an overview.

## Discovery concept grouping safeguards — October 20, 2026

- [x] Group annual versions using source descriptions, populations and schema evidence before ranking/capping features.
- [x] Separate cohort coverage from outcome dates; remove singular annual/cohort labels from stable headings and preserve source gaps/mixed dates.
- [x] Retrieve physically verified examples separately per concept; keep complete source references under Definitions & sources.
- [x] Validate annual-record uniqueness, reporting/cohort coverage and example labels before display; explain conservative separation.
- [x] Cross-survey regressions and latency evidence: 21 related tests passed, followed by eight final discovery checks and the final source-label guard check. See dated progress log and prototype/DATA_DISCOVERY.md.

## Evidence-linked AI discovery writing (step 5) — October 20, 2026

- [x] Keep retrieval/grouping unchanged; provide full structured source evidence to the selected model for writing only.
- [x] Validate source-passage/topic references, reading/scope constraints and mandatory qualifications; retain detailed coverage and model audit under Definitions & sources.
- [x] Fall back to the verified template on unavailable/invalid writing, preserving actual usage and unknown-cost distinctions.
- [x] Test readability, source accuracy, omitted qualifications, latency and cost: 50 related tests passed, nine final writing checks passed, five final live cases accepted; about 26% shorter final rendering, median 6.83 seconds, $0.035-$0.168 estimated writing cost per answer.

Evidence and limits: evaluations/DISCOVERY_WRITING_REVIEW.md, evaluations/discovery_writing_live.json, prototype/DATA_DISCOVERY.md. Semantic paraphrase checks are bounded; evaluator scores are diagnostic, not proof. No owner input required.

- [x] College-tuition discovery fallback: generic institution wording no longer dilutes a specific topic; bounded editorial word tolerance and audited, source-verified annual heading cleanup preserve valid AI summaries. Exact live question accepted; 20 focused tests plus final academic-period check and chat UI replay passed. See October 20 progress log and tuition-discovery evaluation files.

## Discovery step 1: assisted interpretation

- [x] Propose possible concepts and search phrases in AI mode; retain original keywords and original searches.
- [x] Verify proposed concepts/phrases against documented physical catalog records in the requested releases; reject unsupported suggestions without claiming data absence.
- [x] Preserve ambiguity and uncertainty, original-search fallback and inspectable source-level audit; keep analytical questions on their existing route.
- [x] Aggregate interpretation and writing latency/cost by stage, retaining unknown-usage handling.
- [x] Verify with 64 related tests, 11 final interpretation checks and five live everyday-wording cases. Final source-title probes 5/5 versus original 4/5; original hits retained throughout. Median added interpretation/verification 3.63 seconds and about $0.005 per answer in this sample.

Evidence/limits: evaluations/DISCOVERY_INTERPRETATION_REVIEW.md, evaluations/discovery_interpretation_final.json and prototype/DATA_DISCOVERY.md. Source matches establish catalog existence, not guaranteed semantic equivalence or complete reporting.

## NCES national aggregate benchmarks — October 21, 2026

- [x] Inventory all 45 NCES exports and preserve all 824 expected observations, original notes and file hashes.
- [x] Exercise the production analytical route with explicit national scope; record existing scope blocks separately from arithmetic results.
- [x] Run separate read-only source-SQL reference comparisons, preserving formulas, source evidence, missingness, discrepancies, latency and cost.
- [x] Save reproducible runners and human/machine-readable results under evaluations/nces_aggregates; independently verify row accounting, unchanged inputs and representative SQL calculations.
- [x] Implement explicit national population, geography, reporting-unit and missing-pair policies in the app. Population scopes now use the general engine, separate from the 30-named-institution bound; see the implementation review below.
- [ ] Reconcile numerical discrepancies, historical documentation-location gaps, FTE/core-expense methods and missing NCES selections before accepting all benchmarks.

Evidence: evaluations/nces_aggregates/REVIEW.md and summary.json. Source-SQL agreement is diagnostic, not successful chatbot aggregation. Owner clarification requested for q8 age category and q200 student population/outcome.

## Population aggregate implementation — October 21, 2026

- [x] Replace the legacy blanket ban with source-bound directory populations, global reducers, sector/state/control grouping and independent annual queries.
- [x] Pool matching source numerator/denominator counts; retain coverage, missing pairs, reporting-unit scope and office exclusions. Preserve key, subtotal, unit, period and cardinality checks.
- [x] Exercise the actual production executor against all 824 NCES cells: 393 matches, 21 discrepancies guarded, 392 outside source releases and 18 unresolved methods/definitions after Q8/Q200/Q42 clarifications. Preserve earlier failed attempts and passing rechecks.
- [x] Keep known mismatching source-method/scope signatures from publishing figures; unfamiliar valid source-backed questions do not require a benchmark whitelist.
- [x] Verify 116 regressions, 15 artifact/live-output checks, four successful live question types and actual chat UI rendering. Record latency and provider usage separately from source-only execution.
- [x] Include aggregate scope in Definitions & sources and reporting-unit sheets in Excel; retain the existing table, chart, formatting and download controls.
- [x] Record the user-confirmed Q8 age category, **25 and above**, separately from the unchanged export. All five locally covered observations match exactly; six earlier observations remain outside local source releases. Targeted rerun took 7.788 seconds with no model calls or API cost; 21 artifact/live-output checks passed.
- [x] Verify Q200 eight-year award completion for all entering degree/certificate-seeking undergraduates: all eight cohorts match NCES precision. Latest cohort rounds to 47.3% across exactly 3,473 institutions. Annual documentation validates the cohort/outcome relationship; institution percentages are not averaged. Retain user-added notes and original/current workbook hashes separately.
- [x] Verify Q42 any-distance participation (exclusive plus some courses): all ten local years match NCES displayed precision. Add explicit source-policy opt-in to derive blank component zeros only when a nonnegative count partition proves they are zero; audit each cell, retain unresolved/suppressed missingness, reject contradictions, preserve same-contributor pooled counts. 44 regressions and 29 artifact checks pass.
- [ ] Reconcile the remaining NCES discrepancies and metadata/definition gaps before enabling those affected methods/periods. Q110 source diagnosis now reproduces 9/10 local years using documented GASB/FASB core expenses and 12-month FTE; 2022 still differs. These are reference SQL diagnostics, not production executor passes; current 824-cell production accounting is unchanged. No more Q110 information is requested from the user. Complete source-method validation/integration and investigate the 2022 discrepancy; eight aid metadata ownership conflicts also need review. Q8/Q200/Q42 no longer require owner clarification.

Current evidence: evaluations/nces_aggregates/POPULATION_IMPLEMENTATION_REVIEW.md, population_engine_results.csv/json, population_implementation_verification.json; implementation rules in prototype/POPULATION_AGGREGATES.md. REVIEW.md is the frozen pre-change baseline.
