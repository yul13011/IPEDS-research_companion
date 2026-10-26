# Supplied-source coverage policy — October 21, 2026

Owner instruction: use only supplied sources; when the original question cannot be established from those sources or valid derivations, explain the gap first and make proxies optional. Do not investigate College Scorecard or other unprovided sources.

## Implementation

- Shared `prototype/source_policy.py` applies to the catalog planner, reviewed-measure router, discovery interpretation/writing request layer and conversational context resolver. Data tools remain local supplied-source tools; no web or external dataset tool was added.
- Added `report_coverage_gap` with structured limitation status, missing information, explanation and zero to three optional source-bound proxy plans. It requires completed local metadata inspection and retains actual tool inputs/counts as evidence, rather than accepting invented inspection citations.
- Distinguishes source coverage limitations, unresolved definitions and incomplete retrieval. An incomplete search cannot offer proxies as if it established missing coverage. Absence claims are limited to inspected supplied releases; source search failures do not prove global nonexistence.
- Code-owned response text explains the original limitation first. No alternatives is a valid completed response. If alternatives exist, ordinary preflight validates each plan, the UI labels actions **Try optional proxy A/B/C**, and no statistical values are queried before an explicit selection.
- Ordinary definition choices cannot contain proxy proposals; final plan submissions explicitly labelled as unrequested proxies receive repair feedback instead of execution. Previously selected proxy plans execute locally, preserving the non-equivalence qualification. Generic **continue/yes/go ahead** cannot silently select a pending optional proxy.
- Original question, source gap and optional plan evidence remain in the session brief. Existing valid definitions, direct calculations, bundled answers, retry and clear-conversation behavior are retained.

## Evidence

**73 regressions passed in 62.014 seconds** (`coverage_gap_tests_final.log`) across gap handling, analytical clarification, catalog planning, memory, discovery writing and interpretation. Final focused run adds an explicit unrequested-proxy submission/repair check: **8 focused tests passed in 12.644 seconds** (`coverage_gap_focused_final.log`). Seven of those focused cases overlap the 73-test run, so there are 74 distinct passing cases across the two runs, not 81. Included real local source plans, mocked provider transport, actual Streamlit UI labels and execution after explicit selection with no replanning.

Initial 64-test diagnostic run had one outdated test expectation that every newly added tool except the original plan tools must use provider strict compilation. Updated the expectation for the new plan-containing coverage tool, retaining local schema and plan validation; reruns passed. Original diagnostic log remains `coverage_gap_tests.log`.

Live replay of **how many women's colleges in the US** now returns a source coverage limitation, not A/B membership proxies. Its explanation identifies the missing classification, distinguishes people-count gender composition from institutional identity, and explicitly limits the finding to the inspected 2024 release. No external source is suggested; no statistical result or proxy is executed. **70.339 seconds**, five model calls, nine planning tool requests, configured estimate **$0.3534241**. This is one sample, not a latency improvement claim. Original pre-change run remains separately preserved.

Seven independent saved-artifact checks passed, including gap-first response, source-inspection evidence, explicit year scope, no forced options, no external suggestion and no numerical result. Evidence: `womens_colleges_gap_first_trace.json/log`, `womens_colleges_gap_first_verification.json`, verification script `verify_womens_colleges_gap_first.py`. No additional provider request is required for the verifier.

Restarted local app on port 8516, PID 157820; health checked after restart. No original data, aggregate methodology or default population changed. Full combined suite not rerun; national benchmark reconciliation remains paused.

## Limits

The model still interprets source meaning and may misclassify a limitation. Validation establishes that an optional calculation uses valid supplied fields, not that the proxy is equivalent to the original concept; the response explicitly denies that equivalence. Keyword guards catch explicitly labelled proxies, not every possible unstated semantic substitution. The live replay verifies this question and the deterministic checks cover the shared workflow; arbitrary question accuracy is not certified.
