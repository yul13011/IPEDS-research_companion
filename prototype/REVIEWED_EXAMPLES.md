# Reviewed example questions

The Explore IPEDS and Need ideas? interfaces share `learning_content.json` and `execute_example` in `workflows.py`. Numerical presets execute fixed reviewed source plans, with no model planning or API cost. Values are read from local annual databases each time; expected test values are never used to answer questions.

Existing measure-registry examples use their `plan`. Faculty examples use `catalog_plan_key` to select a fixed version-2 plan in `faculty_example_plans.json`; the ordinary query engine still checks exact source definition/category IDs, physical ownership, grain, units, periods and institutions before reading data. Do not replace a failed plan with guessed values or silently fall back to AI. Source-ID changes after rebuilding a catalog require revalidation of preset plans.

## Faculty & Staff presets

- **One data point:** Yale full-/part-time instructional staff, Fall 2024. Source EAP2024, EAPCAT=21000, OCCUPCAT=210, FACSTAT=0, EAPFT/EAPPT. This is total instructional staff, with/without faculty status and including medical-school instructional staff where reported. Snapshot is November 1; employment status is institution-defined. Source per-institution sums operate on a single selected population row, never overlapping subtotals.
- **Compare institutions:** Yale, Harvard and Princeton professor/associate/assistant professor average base salaries, academic year 2023–24. Source SAL2023_IS (not SAL2024_IS), ARANK=1/2/3, SAEQ9AT. This is the source's nine-month-equivalent salary for full-time nonmedical instructional staff, with 9–12-month appointments. Salary supplements, overloads and bonuses are excluded. The question explicitly names the equivalent-month and medical-school scope. No unweighted average of different contract-length averages is computed.
- **Explore a trend:** Yale instructional staff counts by full-/part-time status, Fall 2015–2024. Independently rebind the EAP source fields/categories in each year, verify stable titles/category labels, then run the named-institution plan for that release. Stable source-aggregate references preserve two connected series. General annual templates now accept either an explicit population or 1–30 named institutions; each annual child retains normal validation. The ten-year, unique-year and no-cross-year-join template bounds remain.

Both the point and comparison default to bar charts; the ten-year result defaults to a line chart. Existing table, definitions/source, chart-formatting and download controls operate on these validated results. Short descriptions are updated and the shared heading avoids repeating identical title/subtitle text.

## Verification — October 21, 2026

All **31 observations** (2 point, 9 salary, 20 trend) agree with independent raw-source SQL checks. Yale Fall 2024 is 2,995 full-time and 805 part-time instructional staff. All three presets were clicked through both real Streamlit UI paths (six clicks), with chat planning patched to fail if invoked; all succeeded. The trend chart specification contains two line series with ten points each. CSV and Excel serialization succeeds for each result. Invalid annual template scope/year cases remain blocked.

Three focused tests passed in 25.194 seconds (`evaluations/faculty_examples_tests.log`). Sixteen existing population/example regressions passed in 57.091 seconds (`evaluations/faculty_examples_regression.log`). Added the focused tests to the combined regression runner; the entire combined runner was not rerun for this update.

One direct execution per example took 0.335 seconds (point), 0.191 seconds (salary) and 7.692 seconds (ten-year trend), with zero model calls/API cost. The trend measurement ran alongside regression activity; these are descriptive server times, excluding browser rendering, not a latency guarantee. Full answers, plans, sources and timings are saved in `evaluations/faculty_examples_verification.json`.

The original Institutional Characteristics discovery presets were replaced October 23, 2026, as described below. General discovery in typed chat is unchanged. National benchmark testing remains paused; related population regression checks here verify the annual-helper change, not a new benchmark campaign.

## Institutional Characteristics presets — October 23, 2026

Both surfaces now share three different categorical question types from the 2024–25 release:

- **Look up a school:** Smith academic counseling, career placement, and on-campus childcare. IC2024 fields STUSRV2/STUSRV4/STUSRV8; three source responses, Yes/Yes/Implied no.
- **Find matching institutions:** Massachusetts degree-granting reporting institutions with undergraduate distance education (DSTNCED1=1). The predefined population uses Massachusetts FIPS 25, degree-granting status, no additional Title IV restriction, and excludes administrative offices. Result: 83 institutions. DSTNCED1/DSTNUGC/DSTNUGP retain overall availability and the distinction between courses and complete programs.
- **Compare institutions:** Smith, Mount Holyoke, and Wellesley bachelor's/master's offerings (LEVEL5/LEVEL7). Six source responses: bachelor's Yes at all three; master's Yes at Smith/Mount Holyoke and Implied no at Wellesley.

`observation_plan_key` selects fixed exact field/category IDs in `institution_example_plans.json`. The ordinary typed-observation binder and executor validate the plans and read current local source values. No model planning, external source, arithmetic on category codes, or dummy count is used. Results use tables, source definitions, original codes/labels, and downloads. Release labels are explicit; this does not assert current institutional offerings.

Two focused tests passed in 13.832 seconds (`evaluations/institution_examples_tests.log`): all **258 cells** independently match raw IC2024 values and exact source code labels, the 83-ID population matches an independent HD/IC query, and all six example clicks succeed across Explore IPEDS and Need ideas with chat planning blocked. The new tests are registered in the combined runner; the full suite was not rerun for this preset change.

The existing all-topic example/session-navigation regression also passed (one test, 18.120 seconds; `evaluations/institution_examples_navigation.log`).

## Follow-up: salary grouped-bar readability

User reported overlapping-looking salary bars. Existing rules rendered all values, but default nested-band spacing left roughly one pixel between adjacent 18-pixel bars and placed institutions in a different order from the legend. The shared chart renderer now explicitly orders institution offsets, provides gaps and calculates height from chosen bar/label size and institutions per group. Slide exports preserve sufficient plot height. All nine data values are unchanged. Inspected before/after raster images and added a rendered-SVG geometry/order test at default/max bar size in both on-screen and slide specifications. Fifteen chart/formatting tests passed in 26.103 seconds; `evaluations/faculty_salary_chart_spacing_tests.log` and before/after image/spec artifacts retain evidence. Earlier value/UI tests did not establish adequate visual spacing; this additional regression covers it.

## Follow-up: Style colors match chart colors

The salary Style tab previously enumerated nine institution/rank combinations using line-series logic, although the bars use three institution colors. Picker keys did not match the bar color domain. Shared controls and prompt color targets now read the actual chart's rendered color domains/ranges (including current overrides/overall colors). The salary editor lists Yale, Harvard and Princeton with their displayed colors; selecting one color preserves other displayed colors. Bar overrides apply even for a single institution with multiple categories. Actual UI test verifies picker count/default values, Harvard picker recoloring and subsequent Princeton prompt recoloring with no planner/data query and no changed result rows. Eight existing chart-format/edit regressions passed; the new focused test passed in 7.737 seconds after correcting a test-only hex-case expectation. The first log retains that assertion failure rather than describing the initial nine-test run as fully passed. See `faculty_salary_color_controls_tests.log` and `faculty_salary_color_controls_focused.log` in evaluations.
