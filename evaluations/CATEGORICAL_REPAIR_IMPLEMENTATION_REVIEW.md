# Categorical repair implementation review — F029

Implemented October 22, 2026; completed October 23, 2026.
**Status: implemented, validated within the scope below, and activated locally.**

## Implemented

- Separate typed categorical/identifier/text/bounded/quantitative observations,
  with exact source codes, labels, statuses, field/category IDs and evidence.
- Direct lookup, comparison, mixed table and institution-list plans. Unique
  institution grain, bounded output and validated source-code filters. No dummy counts.
- Source-backed conditional disability percentages and Fall 2023 student dates in
  the 2024-25 release. Numerical companion nulls no longer erase reported bounds.
- Correct per-institution summaries; table-only categorical rendering, full
  comparison matrix, CSV/Excel/source audit downloads and chart guard.
- Readable identity annotations, request identity/release/concept safeguards,
  typed conversation context and category-definition follow-ups.
- Bounded tool-batch recovery and existing numeric arithmetic/count safeguards.
- Feature rollback flag and documentation in `prototype/CATEGORICAL_OBSERVATIONS.md`.

## Deterministic verification

New source-backed tests check the three-school matrix, affiliations, explicit No
codes, degree offerings, exact institution IDs for both lists, independent SQL,
AP credit in both releases, numeric 38% versus a source-defined <=3% bound, student
dates, export bytes/workbook evidence, actual Streamlit rendering, unmapped and
negative codes, missing observations, conflicting labels, integrity checks, identity
and scope omissions, legacy adaptation, arithmetic rejection and tool-batch recovery.

Final focused run: **43 tests passed in 61.727 seconds** across observations,
institution confirmation and catalog planning.
Log: `evaluations/typed_observations_final_focused.log`.
Final incremental checks after additional boundary protections: **40 integration
tests passed in 61.375 seconds** (`typed_observations_last_integration.log`),
**15 source tests passed in 30.452 seconds** (`typed_observations_source_final.log`),
and **45 compatibility tests passed in 66.116 seconds**
(`typed_observations_final_compatibility.log`). These sets overlap; do not add them
as distinct test counts. They include two new cases added after the registered
run was launched: numerical selector dimensions retain the original executor,
and calendar plus direct undergraduate enrollment preserves its source selector.
The student-date guard also rejects Fall 2024 when a field measures Fall 2023.

An earlier affected run exposed a slow unindexed category join, annotation effects
on the legacy enrollment vocabulary, and a test contract needing the new non-strict
submission tool listed alongside existing plan submissions. Fixed the lookup with
two bounded source reads, restored deterministic identity parsing, and updated that
submission-tool fixture while retaining strict metadata inspection tools. The stale
full run was stopped; it is not counted as passing. The final registered run is
`evaluations/typed_observations_registered_final.log`.

## Live acceptance and independent source checks

- Both repeats of the original three questions returned source-backed results.
  The Smith lookup preserves Yes versus Implied no. The three-school comparison
  has all 12 service responses. Both Massachusetts lists contain the exact 83
  degree-granting institution IDs from independent source SQL.
- Broader live cases correctly returned calendar systems, religious affiliation,
  explicit admission-policy No, degree levels, both AP-credit releases, 14 combined
  service matches, and the existing valid childcare count of 20.
- Smith's disability result is 38% for Fall 2023; Bentley's result preserves
  "3 percent or less" without inventing a precise percentage.
- Category-label definitions and distance course/program follow-ups return source
  definitions and codes. The service-quality question retains the coverage gap,
  with availability offered only as an optional different question.
- A stricter authorization check initially rejected a replacement-school follow-up
  by confusing the set of allowed historical identities with the requested scope.
  Corrected it to validate both authorization and the actual request contract.
  Final live follow-up correctly answers Mount Holyoke after Smith.
- The early live percentage guard was too broad and was corrected; those blocked
  intermediate responses are retained as diagnostics, not counted as final passes.

Evidence folders: `ic_categorical_acceptance/` (original cases twice and targeted
probes), `ic_categorical_after_final/` (broader replay), and
`ic_categorical_final_checks/` (corrected follow-up and mixed result).

Independent verification: **256 cells across 19 saved live typed answers** matched
raw annual rows and exact codebook labels. Both original Massachusetts responses
also match the independent full institution-ID set. This is sampled live answer
verification, not a complete catalog audit.
See `typed_observations_live_source_verification.json` and its runner.

Actual saved-live comparison UI: four service rows, three school columns, all 12
responses present, no exception, and a forced chart remains blocked. Evidence:
`typed_comparison_ui_verification.json` and `.log`. The first stdin function-based
test harness could not expose inspectable source; the actual AppTest string/session
harness succeeded without changing app behavior.

## Latency and cost

No new classification model call is required; local category definitions use zero
model calls. Live planning remains variable. Original-question rounds and broader
replays retain per-request usage and elapsed time. Cold/concurrent runs and source
cache differences prevent a clean isolated performance comparison. Estimates use
the app's configured rates and are not independently verified billed cost.
`typed_observations_latency_comparison.json` matches all 16 exploratory turns to
their corrected responses: descriptive median 17.36 seconds, with zero model calls
for the initial code definition, its rephrasing and the contextual definition.
This is recorded sample behavior, not a guaranteed speedup or billing estimate.

## Final registered acceptance and activation

- Registered runner: **299 tests passed in 1516.377 seconds**, with zero failures
  or errors. Log: `typed_observations_registered_final.log`; machine-readable
  registered results: `catalog_execution_verification.json`.
- Final categorical/display and numerical chart-edit checks: **18 tests passed in
  171.778 seconds** (`typed_observations_display_final.log`). These include the
  final 15 source tests and overlap the registered suite; do not add the totals
  as distinct tests. Latest documentation/planner integration: 40 tests passed.
- Numerical tests cover enrollment, salary/currency, rates, arithmetic, grouped
  calculations, saved results, charts, exports, scope and conversation behavior.
- Both live repeats of the original three questions and the independent checks
  above passed within their recorded scope. Complete catalog correctness and
  future model-query reliability are not inferred from these samples.
- Restarted local server **PID 223968**, port **8516**, with filesystem watching
  disabled. Startup completed and `/_stcore/health` returned `ok`.
  Logs: `categorical_app_stdout.log`, `categorical_app_stderr.log`.
- Completion/activation record: `typed_observations_activation.json`.

## Limits retained

Numerical validity is assessed by the registered regressions and source checks,
not a claim of exhaustive correctness for every question. Some general questions
can still need explicit source selectors, methodology or ambiguity clarification.
Additional conditional fields require documented source links, not guessed generic
rules. Multi-row tables require fixed key selectors before direct projection.
Existing categorical count workarounds should be rerun, not silently relabelled.
No new external source or national benchmark reconciliation was introduced.
F027 remains awaiting owner terminology review.
