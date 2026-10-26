# Request, plan and result protections

Implemented October 20, 2026 after the longitudinal endpoint bug. These checks add an independent boundary around the existing source, population, arithmetic and query validators. They do not use another model call and do not require a previously validated example question.

## Request contract

`intent_checks.contract` captures checkable requirements from the current request before execution: explicit confirmed UNITIDs, requested periods/time basis, temporal intent, annual-observation count, supported gender/race breakdowns, percentage requests and undergraduate population intent. It uses the original request after institution-name confirmation, not merely the model's rewritten question. For supported follow-ups, referenced analytical context supplies unchanged scope. A new topic does not inherit old gender/percentage requirements. Formatting turns no longer become the active analytical topic.

The annual count is read separately from date-window expansion. An injected off-by-one error in the shared date binder is therefore rejected even if both the plan and its dates agree with that faulty binder. Explicit academic/fiscal periods, entering cohorts and nominal class labels retain their established distinctions.

## Before fact queries

Every analytical route is guarded: reviewed measures in `analytics.execute`, annual catalog observations in `catalog_execution.execute_catalog`, and relational queries in `query_engine.execute` after metadata inspection but before source execution.

Checks include:

- Planned confirmed institutions match the explicit named scope; additions and supported institution replacements preserve the appropriate context.
- Reviewed years match the requested interval and independently extracted observation count. A trend cannot have only one planned period.
- Annual fall-enrollment catalog plans cannot substitute a single release for the requested multi-year window. A single-release plan documented to cover only one period cannot satisfy a trend. Other multi-period wide/long source layouts are left to returned-period verification rather than assuming one release always equals one observation year.
- Familiar explicit enrollment measures cannot switch to another familiar measure. An undergraduate enrollment request cannot substitute a graduate/overall count.
- Supported gender/race breakdowns must be represented by actual selected source-field titles or grouped source dimensions. Invented output labels or assumptions cannot establish this evidence.
- Percentages require a typed percentage calculation or source-defined percentage output. Counts alone do not satisfy the request. SAT percentiles are not classified as percentages.
- Known fall-enrollment undergraduate selections are checked against source categories; first-time-only populations do not answer a broader undergraduate request. Existing population/denominator validators still run and can independently block the same mismatch.

Mismatch returns clarification/validation failure with no numerical result. This does not automatically relax the request or retry with fewer years/categories.

## Before publication and rendering

Successful executions receive `result.intent_validation` with the contract, completed checks and status. Actual returned reporting periods must match the interval and annual count. Coverage is checked for each institution, and for each reviewed measure, rather than accepting a union where another institution fills a missing year. A requested breakdown cannot silently become a single category; recognized overall totals do not count as breakdown categories. Required percentage outputs must actually have percentage units.

Cross-period changes can legitimately produce one value from two source periods; they are distinct from longitudinal series. Combined-institution reductions can legitimately have one combined output row with institution membership established by the validated plan and runtime query audit. Academic spans use their reporting-period ending year, not both calendar years as separate annual observations.

Missing values do not cause requested periods to disappear: explicit missing/suppressed/not-collected rows retain their slots. If fewer than two periods contain reported values, a material caveat states that a trend cannot be assessed. Values are not replaced by zero or invented.

Checks run before answer finalization and again at the answer/result rendering boundaries and presentation preview. An invalid cached result cannot expose its numerical summary, chart, table or data/image download controls. Older results lacking a contract retain their existing validation; the new contract is attached to newly executed answers.

## Verification and latency

`tests/test_intent_checks.py` contains 11 tests, several with multiple cases. They inject scope omissions, changed institutions/measures, count-only percentage plans, a missing gender field, wrong first-time population, a corrupted date binder, truncated result periods, per-institution omissions and invalid cached summaries. Fact-SQL compilation is prohibited in pre-execution rejection cases. Multi-turn counts → trend → percentages uses real annual source queries with mocked context-model transport; new-topic and formatting-turn behavior are also checked. Valid academic, cohort, percentile, cross-period percentage-change and combined-institution cases remain accepted. Existing memory/trend/chart tests remain in the combined runner.

`evaluations/intent_conversation_latency.json` records the local multi-turn test wall times and clearly marks mocked context transport. `evaluations/trend_followup_live_intent.json` records the configured live replay with protections enabled: lookup 21.985 seconds, ten-year trend 14.767 seconds, longitudinal follow-up 10.682 seconds in this run. The two trend results each contain ten observations and a line chart. These descriptive single-run timings were taken during regression work, exclude browser paint and do not isolate guard overhead or establish a performance change. The checks add no provider calls. Per-test timing remains in `evaluations/catalog_execution_verification.json`.

## Coverage limits

This is a bounded consistency validator, not a claim to understand every IPEDS concept through keywords. Arbitrary unfamiliar measure equivalence, all possible custom populations and every cross-survey temporal mapping are not newly certified here. Exact source semantics, units, denominators, row domains, joins, missingness and comparability continue to be validated by the existing engines. Unknown semantic equivalence is not converted into a claim that data are unavailable. The protection is general across institutions and source years; there are no Mount Holyoke-specific result rules.
