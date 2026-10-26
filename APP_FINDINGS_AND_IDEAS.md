# App findings and ideas

Created: October 21, 2026.

A running to-do list for small issues, observations, questions and ideas that come up while using IPEDS Research Companion. Rough notes and incomplete thoughts are welcome; no need to decide the solution or priority before recording something.

Use this file to capture findings. The [implementation checklist](IMPLEMENTATION_CHECKLIST.md) tracks the seven-step roadmap and planned work. Recording an item here does not automatically start implementation or resume paused testing.

## Open items

Captured October 21, 2026 from the user's testing notes. Items default to **Captured** unless a status/update is recorded below. Unreviewed behavior remains unverified. Work on the example questions is now authorized; unrelated aggregate evaluation testing remains paused.

### Question response

- [x] **F029 — Support categorical lookups, comparisons and institution lists.**
  Recorded October 22, 2026; completed October 23, 2026. **Status: implemented,
  validated and active locally.** 299 registered tests passed; final 18 overlapping
  categorical/display/chart-edit checks passed. Both repeats of the original three
  questions returned source-backed results; 256 cells across 19 live typed answers
  independently matched source values/labels. App PID 223968, port 8516, health ok.
  [Implementation review](evaluations/CATEGORICAL_REPAIR_IMPLEMENTATION_REVIEW.md).
  Sixteen additional exploratory live turns exposed misleading
  affiliation summaries, conditional percentage loss, identity/scope drift,
  definition/follow-up failures and a tool-batch exception. A childcare count of 20
  and a quality coverage-gap explanation worked and must be preserved.
  [Exploratory review](evaluations/IC_CATEGORICAL_EXPLORATORY_REVIEW.md).
  Smith's service lookup used a dummy record count; the Massachusetts distance
  education list exhausted planning; the three-school services comparison rejected
  categorical outputs. Source tables support the answers. Repair typed execution,
  source-code interpretation, institution lists, presentation/exports and planner
  integration while retaining numerical safeguards. Six stages and acceptance
  criteria: [categorical repair plan](CATEGORICAL_VARIABLE_REPAIR_PLAN.md).
  Related preset review remains F007; this item is the shared capability repair.

- [x] **F028 — StopIteration while rendering a single total panel.**
  Fixed October 22, 2026. The All ranks chart classification added in F026 was absent
  from a separate hard-coded row lookup in the scalar-total renderer. Panels now
  carry their exact single row; rendering no longer searches the complete result by
  a duplicate total-label list. Regression renders Smith's ranks plus the total of
  351 through Streamlit without an exception. 23 related chart/format/unit tests
  passed in 71.457 seconds. Log: `evaluations/total_panel_render_fix.log`.

- [ ] **F027 — Owner review: “clock hours” versus “contact hours” across five releases.**
  Added October 22, 2026. **Owner: user. Status: awaiting owner review.**
  Review the supplied 2020–2024 release codebooks for the sixth-largest program:
  `CIPLGTH6` prose describes clock/credit hours, while `PRGMSR6` code 1 is labelled
  “Contact hours.” Determine whether to retain the distinction or establish a
  documented harmonization rule. Until reviewed, the app preserves the exact source
  labels separately and performs no conversion.
  [Five source records and review details](evaluations/UNIT_RESOLUTION_REVIEW_ITEMS.md).
  Full workbook, sheet, row and category evidence: `evaluations/unit_resolution_review.json`.

- [x] **F026 — Inconsistent inferred units suppress staff charts and mislabel other quantities.**
  **Version 3 follow-up:** processed the original 2,484 unresolved entries: 2,459
  fixed units and 25 conditional program units. All 40,322 positive program-length
  observations have a recognized basis. Five release-specific clock/contact wording
  discrepancies remain for source review. 75 affected tests plus 16 overlapping final
  checks passed. Broader independent verification remains open.
  [Current review items](evaluations/UNIT_RESOLUTION_REVIEW_ITEMS.md).
  Implemented October 22, 2026 after saving the broad repair plan. Shared source-backed,
  versioned unit catalog covers 23,990 documented fields across ten releases, with
  explicit unresolved cases. Fixed Smith rank units and separated total from ranks;
  corrected scores, hours and student/award distinctions. Final acceptance 67 distinct
  tests; values preserved, no extra model calls. [Audit, implementation and limits](evaluations/SHARED_UNIT_METADATA_REVIEW.md).

- [x] **F025 — Classification gaps become enrollment-proxy choices.**
  Verified with the exact question “how many women's colleges in the US” in a fresh production-backend run. App offers zero-men total/undergraduate enrollment proxies, correctly qualifies them and retrieves no counts before selection, but does not answer the requested institutional classification. Local-only tools cannot retrieve Scorecard WOMENONLY; prompt encourages executable proxy alternatives and preflight validates each rewritten proxy rather than equivalence to the original concept. Source absence statement also exceeds the loaded-files scope. [Review, plans and proposed policy](evaluations/WOMENS_COLLEGES_APP_REVIEW.md). Captured only; no production fix made.
  **Implemented October 21:** owner requires supplied sources only. Added shared source policy, structured gap-first responses, optional validated proxies, explicit selection and generic-continuation guard. Exact live question now explains supplied-release classification coverage without outside-source suggestions or forced proxy choices. Verified 73 regressions, eight focused checks and seven saved-live checks. [Implementation review and limits](evaluations/COVERAGE_GAP_POLICY_REVIEW.md).

- [x] **F024 — Internal monetary unit leaks into results.**
  Fixed October 21 across summaries, tables/metrics, charts and downloads. Shared source-backed currency/scale presentation preserves original values and audit units, supports saved results, labels verified USD and flags unverified/conflicting evidence. Verified Mount Holyoke, Yale and Harvard monetary fields against independent SQL and UI/exports: 3 focused acceptance and 46 related regressions passed. [Review](evaluations/CURRENCY_UNITS_REVIEW.md). This does not resolve F023 narrative scope mismatches.

- [ ] **F023 — Validate narrative qualifications against selected fields.**
  Found during the October 21 faculty-answer pilot: the current app described a Yale option as excluding medical-school staff while selecting `EAPTOT` for all instructional staff, which includes medical-school staff. Metadata preflight did not catch the prose/plan mismatch. Derive medical/population qualifications from the actual plan and validate explanatory prose. The evaluation writer also needed a source-definition repair after narrowing instructional staff to people whose main job is teaching; the true category includes instruction combined with research/public service. [Pilot review](evaluations/FACULTY_ANSWER_PILOT_REVIEW.md). No live-app fix implemented in this evaluation.

- [ ] **F022 — Ambiguous “faculty” headcount bypasses clarification.**
  Verified October 21 in a fresh live-app session: “how many faculty does Yale have?” directly returns 3,800 instructional staff (2,995 full-time; 805 part-time), with source population “Instructional staff, total; All staff.” These numbers match the selected source rows, but the question could also mean all 5,735 staff with faculty status. Yale's instructional counts coincide with/without a faculty-status filter in 2024; that equivalence cannot be assumed elsewhere. Review when material population ambiguity must trigger clarification. The structured option workflow was not invoked; this is distinct from recognizing an A/B reply. [Evidence](evaluations/YALE_FACULTY_APP_CHECK.md). No implementation change made during this check.
  **Evaluation update:** tested a mandatory meaning review, code-bound count comparisons and constrained writing in an isolated 16-question faculty pilot using the app's current model. All 52 returned values matched independent source SQL; 16 answer/clarification routes matched expectations, with one optional extra scope row. Refined writing used two safe fallbacks and one diagnosed source-definition repair. Supports a faculty-count implementation trial, not general IPEDS readiness. [Detailed findings and samples](evaluations/FACULTY_ANSWER_PILOT_REVIEW.md). F022 remains open until production implementation and verification.

- [x] **F001 — Confirm the intended variable when definitions are similar.**
  Some variables have similar definitions. Ask users to verify which variable they mean before running the analysis.
  **Implemented October 21:** general source-preflighted analytical choices, session analysis brief, exact selection buttons/short replies, free-text revisions and qualified separate panels. Selected options execute their saved plans; failures retain the choice. Verified the Southern Connecticut ladder-faculty conversation and a combined-professor-count follow-up, 88 affected regressions, and independent source/UI checks. Ambiguity recognition remains model-dependent, not a claim that every similar definition will always be detected. [Workflow and evidence](evaluations/CLARIFICATION_WORKFLOW_REVIEW.md). Cross-session personal memory remains the separate open F013.
- [ ] **F002 — Review Display table contents.**
  Evaluate what should go into Display table, including underlying counts and data status.
- [x] **F003 — Support definition questions.**
  User reports that “what is the definition of X” questions cannot be answered. Verify the behavior and review support for this question type.
  **Implemented October 22:** dedicated source-backed definition route before institutional/statistical planning. Metadata-only exact passages with full source details, scoped variable/year support, guarded glossary/population qualifications, comparisons, follow-ups and deterministic reviewed app definitions. Verified 66 affected regressions, 13 final focused checks (69 distinct cases), eight accepted application cases and 31 independent checks. Manual review corrected initial relevance and scope issues; bounded retrieval and single-release limits remain. [Review](evaluations/DEFINITION_QUESTIONS_REVIEW.md).

### Need Ideas? window

- [ ] **F005 — Investigate excessive scrolling after selecting a preset question.**
  User reports so much scrolling that it feels dizzying. Review the scrolling behavior when clicking a preset question.
  **October 21 update:** repaired the shared conversation viewport, whose revision/pending keys caused remounts and animated top-to-bottom jumps. New requests now resume following in a stable viewport, while manual reading and menu/sidebar reruns preserve position. Eleven affected UI/memory tests, three controller tests and real-browser long-history checks passed. This addresses the shared transcript mechanism; preset-specific navigation/scroll acceptance remains open. [Evidence](evaluations/TRANSCRIPT_SCROLL_REVIEW.md).

### Analysis Tools window

- [ ] **F008 — Review the Analysis Tools title.**
  User finds the title misleading; consider a clearer name.

### Graphing

- [ ] **F009 — Expand and review chart-formatting flexibility.**
  Let users adjust chart size, title, axis tickmarks, axis labels, bar/line colors and remove categories. Assess which controls already work and where capabilities or usability need improvement.
- [ ] **F010 — Investigate a failed x-axis range request.**
  User reports that “change x-axis limits to 0 - 10%” did not work. Preserve the requested axis and percentage range when reproducing the issue.
- [ ] **F011 — Review axis-limit controls in Format chart.**
  User reports that the formatting window only allows limits to be changed for the y-axis. Review x-axis range support.
- [ ] **F012 — Test usability of chart edits through natural language.**
  Test whether users can successfully change charts through prompting, including how the app interprets and responds to edits.

### Features

- [ ] **F013 — Add user-directed memory, preferably across sessions.**
  Let users ask the app to remember personal conventions such as acronyms, shorthand and what “X” stands for. Explore retaining these between sessions. Current session memory does not establish that this requested persistent feature exists.
- [ ] **F014 — Allow a saved home school.**
- [ ] **F015 — Allow user-defined comparison groups.**

### Feedback

- [ ] **F016 — Log questions and whether they were successfully answered.**
  Capture the user's requested question/outcome tracking idea; success criteria and logging behavior remain to be defined before implementation.
- [ ] **F017 — Provide a feedback box.**

### Evaluation

- [ ] **F018 — Review evaluation results and resolve discrepancies.**
  Related work already exists in the [implementation checklist](IMPLEMENTATION_CHECKLIST.md) and [aggregate evaluation review](evaluations/nces_aggregates/POPULATION_IMPLEMENTATION_REVIEW.md). Keep this finding linked to that work. Evaluation testing remains paused until the user resumes it.

## Adding more notes

For a quick note, a single unchecked bullet is enough:

```markdown
- [ ] F001 · YYYY-MM-DD · Short description or idea.
```

When useful, add details underneath:

```markdown
  - Prompt / steps: What I asked or clicked.
  - Observed: What happened, including the exact response if helpful.
  - Expected / idea: What I wanted or would like to explore.
  - Evidence: Screenshot, result or file link, if available.
  - Status: Captured.
```

The example above is a template, not an additional task. The next available identifier is **F031**. Keep identifiers stable so we can refer to an item in conversation.

## How we will maintain this list

- Capture your wording and distinguish an observed issue from a proposed idea. Unverified observations remain unverified.
- Details and priority are optional. Use statuses **Captured**, **Needs clarification**, **Ready**, **In progress**, or **Deferred** when helpful.
- When we decide to act, link any relevant roadmap step or detailed backlog task. Keep the original finding here so it is not lost.
- After implementing and checking a fix, check the box and move the entry to Completed, keeping its identifier, completion date and a short result/evidence note.
- If an idea is declined or duplicates another item, move it to Closed with the reason or duplicate link. Do not mark it as an implemented fix.
- Update this file when we discuss or work on recorded items. It is not an automatic app feedback collector.

## Completed

- [x] **F007 — Replace Institutional Characteristics preset questions.**
  Completed October 23, 2026 under the owner's updated request for three different question types: Smith services lookup, Massachusetts undergraduate distance-education institution list, and three-school bachelor's/master's comparison. Both Explore IPEDS and Need ideas use the same reviewed typed-observation plans. All 258 categorical cells independently match supplied source data/labels, the institution list matches 83 source IDs, and all six UI clicks pass without chat/model planning. See [reviewed examples](prototype/REVIEWED_EXAMPLES.md). This latest request replaces the earlier proposed numerical-only preset direction.

- [x] **F030 — Flexible purpose routing and documentation/analysis investigation.**
  Completed October 23, 2026. Greetings/help bypass model and analytical routing; explicit mixed requests retain source documentation and validated analysis. Added bounded local documentation lookup to the existing agent loop. Live probes also exposed and repaired canonical institution-annotation handling. Focused regressions and independent source comparisons passed. Plan, measured latency/cost, activation, and limitations are recorded in [the separate implementation document](FLEXIBLE_ROUTING_AND_INVESTIGATION.md). National aggregate reconciliation remains paused.

- [x] **F021 — Inapplicable Year label angle in Format chart / Axes.**
  Reported/fixed October 21, 2026. Initially made the angle control line-only. Owner subsequently requested removing the rotation option entirely: no angle controls on any chart; formerly supported rotation prompts return a local unavailable response, and cached/preset angles no longer affect automatic layout. Captions still identify the relevant numeric axis. Whole-chart workflow tests now verify angle controls are absent on both bar and line charts, while other controls, exports and source rows remain correct. See [workflow verification](evaluations/CHART_WORKFLOW_VERIFICATION.md) and `evaluations/axis_rotation_removed_tests.log`.

- [x] **F020 — Salary chart Style tab lists nine mismatched colors.**
  Reported/fixed October 21, 2026. The editor assumed institution-by-rank line series, but grouped bars actually color by institution. Shared color controls and prompt target matching now derive names/defaults from actual rendered color mappings. Salary bars show three matching institution pickers; changing one preserves the other displayed colors and recolors its bars. Overrides also work for single-institution/category bar charts. Verified actual picker values, Harvard recoloring, follow-up Princeton color prompt, prior edit preservation and unchanged rows, while blocking planner/data execution during formatting. Eight existing chart-format/edit regressions passed; the new focused UI test passed after correcting a test-only uppercase/lowercase hex comparison. Logs: `evaluations/faculty_salary_color_controls_tests.log`, `faculty_salary_color_controls_focused.log`.

- [x] **F019 — Faculty salary comparison bars appear overlapping/crowded.**
  Reported and fixed October 21, 2026. Shared bar charts applied existing rules, but fixed bar thickness and implicit nested bands left barely visible gaps; institution order in the bands differed from the legend. Added explicit ordered offsets, spacing between bars/groups and height based on the selected bar/label sizes. Slide export retains enough plot height before fitting the complete figure to its requested canvas. Verified before/after images and all nine bar positions, default/max bar width, matching legend order and unchanged source rows. Fifteen chart/formatting tests passed. Evidence: `evaluations/faculty_salary_chart_before.png`, `faculty_salary_chart_after.png`, `faculty_salary_chart_spacing_tests.log`. This is a shared chart fix, not a salary-preset-only override.

- [x] **F006 — Replace Human Resources presets with verified Faculty & Staff numerical examples.**
  Completed October 21, 2026. Shared topic now reads Faculty & Staff. Added Yale 2024 full-/part-time instructional counts, a three-institution/three-rank 2023–24 salary comparison with explicit nine-month-equivalent/nonmedical scope, and a ten-year Yale full-/part-time staff trend. Fixed catalog plans use no AI calls. All 31 observations independently match source SQL; all three presets work from both interfaces; charts and CSV/Excel checked. Three focused plus sixteen existing regression tests pass. See [rules and evidence](prototype/REVIEWED_EXAMPLES.md). Institutional Characteristics replacements remain F007.

- [x] **F004 — Verify Yale undergraduate/graduate enrollment and correct trend presentation.**
  Completed October 21, 2026. Exact prompt: “Give me Yale undergraduate and graduate enrollment from 2015 through 2024.” All 20 values match independent annual source checks. Changed preset output from export to chart; verified two connected line series with ten observations each. Table/download controls remain available. Numerical plan, questions and routing are unchanged; no AI calls. Two direct executions took 0.336 and 0.143 seconds, excluding browser rendering. Existing all-example/navigation UI test passed. Evidence: [update verification](evaluations/preset_presentation_update.json), [UI log](evaluations/preset_presentation_ui.log).

## Closed

None yet.
