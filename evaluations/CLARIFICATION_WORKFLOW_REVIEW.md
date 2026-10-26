# Analytical clarification workflow review — October 21, 2026

Implemented a general catalog-planner clarification route with source-preflighted options, saved executable plans, a session-only analysis brief, local exact-option selection, source-qualified multi-panel results and free-text revisions. This is not limited to the faculty example.

## Verification

- **88 affected regressions passed in 61.581 seconds.** Scope: new clarification tests, memory, catalog planning, query engine, institution identity, independent intent checks and trend follow-ups. Log: `clarification_workflow_tests.log`. After a final panel-period fix, the updated real-source bundle regression also passed (`clarification_workflow/bundle_period_regression.log`); it verifies two executions, Fall 2024 counts and academic-year 2024–25 salaries separately.
- **26 independent source/UI checks passed.** Fourteen count observations and ten salary-panel observations match original source SQL; the modified follow-up matches the independently calculated professor sum and source salary; actual app button selection renders two results without model calls, then Clear conversation clears the state. `clarification_workflow/verification.json`, `verification.log` and `verify_clarification_workflow.py`. UI checks use Streamlit AppTest, not a visual browser acceptance test.
- Unit tests reject unknown output references, changing institutions between options, invalid choices and premature statistical queries; preserve selection on execution failure; retry saved plans; invalidate stale plans after modifications; drop old choices on new topics; and prevent partial publication when one panel fails. Provider tools remain locally schema-checked. Institution authorization is retained on the local selection route.

## Live model conversation

Configured Sonnet 5.5; actual client/server elapsed time, including institution resolution. Timings are single observations, not percentiles or a performance guarantee. Costs are the app's configured token-price estimates, not a provider invoice.

| Turn | Outcome | Answer-ready wall time | Model calls | Estimated API cost |
|---|---|---:|---:|---:|
| Ladder faculty counts and average salaries by rank, Southern Connecticut State University | Source-preflighted A/B choices; no statistical result queried | 29.919 s | 4 | $0.168575 |
| A | Executes saved count and contextual salary panels | 0.410 s | 0 | $0 |
| Keep definitions, combine tenured and tenure-track counts, only full professors | Fresh validated multi-panel analysis, no repeated A/B question | 34.496 s | 6, including contextual resolution | $0.299927 |
| First question through A | Complete clarification and answer | 30.329 s | 4 | $0.168575 |
| Whole three-turn conversation | Includes the modified follow-up | 64.825 s | 10 | $0.468502 |

Artifacts: `clarification_workflow/turn_1.json`, `turn_2.json`, `turn_3.json`, `live_summary.json`, `followup.log`. Scripts are opt-in and use the existing configured API credentials without recording credentials. Development attempts and retries incurred additional costs; table totals describe the final recorded conversation only.

Direct original-source checks show **191 tenured + 1 tenure-track full professors = 192** in Fall 2024 at UNITID 130493. The separate academic-year 2024–25 Professor salary observation is **$115,453**, nine-month-equivalent, for all full-time nonmedical instructional professors; the salary reporting population has **193 professors**. That salary is not a ladder-only salary or a calculated salary for those 192 people. The source files were not modified.

## Issues found and corrected

Early development attempts still exhausted planning or offered counts and salaries as mutually exclusive alternatives. Added complete multi-panel options, a confirmed bundle submission route, stronger interpretation guidance and a bounded eight-call planning budget. Initial tests also exposed source typing gaps: bare salary coverage labels lacked their explicitly documented academic-year type, and wide staff rank counts had unresolved units despite explicit table-level count definitions. Both now use source evidence and retain the ordinary validation checks. The follow-up initially returned separate tenure rows after failing the sum; after the employee-unit binding repair it returns the requested 192. The final panel-period regression prevents a combined request's two period types from being incorrectly required in each individual panel.

## Remaining limits

Recognizing ambiguity and proposing useful meanings still depends on model interpretation; preflight cannot prove every paraphrase or user intention. Initial preparation and substantive revisions remain materially slower and more expensive than a bare selection. Each panel has independent definitions and downloads; the implementation does not claim a single combined multi-panel export or universal formatting-prompt targeting. Session context is bounded and is not cross-session personal memory. National aggregate benchmarks remain paused, and no blanket new methodological defaults or all-question coverage claim is made.
