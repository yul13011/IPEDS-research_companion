# Analytical clarification

Implemented October 21, 2026. Applies to the general catalog planner, not a Yale, Southern Connecticut, or faculty-only route.

The model interprets everyday terminology, identifies meaningful ambiguity, retrieves source definitions, proposes alternatives and interprets free-text revisions. Code validates the source fields, category evidence, reporting periods, units, row domains, joins and calculations. Successful metadata preflight is structural eligibility, not proof that a model's interpretation matches every user's intent.

## Conversation contract

- Maintain a session-only analysis brief: original goal, validated scope, proposed options, confirmed decisions, qualifications, selected option, revised request and open questions. Source evidence and complete executable plans remain in session history; the model receives bounded summaries. Clearing the conversation clears the brief. A new topic creates a fresh brief.
- For materially different meanings, offer two or three source-bound alternatives using `offer_analysis_options`. Every primary and additional panel must pass metadata preflight before any option appears. Offering an option never executes statistical queries. Existing catalog grain/profile metadata can be inspected.
- Each option has a label, complete interpretation, qualifications and version-2 plan. Optional additional analyses provide up to two independent panels. Institution and release scopes must match across measure choices. Tables, fields and category evidence are available in the clarification's scope/definitions popover.
- Resolve exact selections locally: A, (a), option B, use A, 1/2/3, first/second/third, and “the second one.” Only the latest pending clarification is actionable. Invalid choices preserve the pending question. A modified choice such as “A, but only professors” goes through contextual interpretation and fresh validation, never the unchanged saved plan.
- Exact selections skip both institution-mention extraction and analytical replanning. The established institution authorization remains enforced. Revalidate and execute the exact saved plans. On execution failure retain the selected definition and plans; “retry” reruns those plans. A modified request invalidates the old execution shortcut even when replanning fails.
- A fully specified multi-panel follow-up uses `submit_analysis_bundle`, without asking the same definition question again. Every panel must succeed before any panel is published. Each panel has its own table/chart, definitions, source evidence and data downloads; no cross-panel arithmetic is inferred.
- Put consequential scope qualifications in result warnings and source/plan assumptions. Never describe salaries of all instructional staff as salaries of tenured/tenure-track staff. Preparing alternatives must not be deferred until after the user chooses an unvalidated prose promise. Unresolved intent can still require an open question; technical planning failure does not establish data absence.

## Validation repairs found during evaluation

Salary table coverage cells such as “2024–25” have a matching “Academic year 2024–25” table title. The period parser can use that exact, matching source title to type the period while retaining the original coverage text. A different title's dates cannot type it.

Wide staff tables sometimes label a numerical column only “Professors.” Employee-count units are established only when the table definition explicitly says each record contains counts of staff by academic rank and the continuous field has a rank label. Rank words in a mixed salary table are insufficient. The count evidence is retained in the semantic descriptor. The ordinary disjoint-category and missingness checks still govern sums.

Catalog planning is bounded at eight model calls, sixteen tool requests, four tools per response and two semantic repair attempts. Non-strict plan tools still undergo complete local JSON-schema validation. Bounded JSON-array strings from the provider may be decoded into their declared container before those same checks; no code or SQL is evaluated.

## Evidence and limits

See `evaluations/CLARIFICATION_WORKFLOW_REVIEW.md` for live timings, estimated costs, source SQL checks and UI verification. General interpretation and identification of ambiguous concepts remain model-dependent. These checks establish the tested workflow, not universal unfamiliar-question accuracy. Cross-session personal memory, blanket new methodological defaults and paused national aggregate benchmarks are outside this change.
# Owner-supplied source boundary and coverage gaps — October 21, 2026

Only owner-supplied sources exposed by local app tools may support answers. Do not investigate or recommend unprovided external sources to fill gaps. When inspected sources and valid derivations cannot establish the original meaning, use `report_coverage_gap`: explain the limitation first, then optionally offer zero to three independently preflighted proxies. Proxies are not equivalent definitions or mandatory choices. Buttons say **Try optional proxy**; selection is explicit, and generic continuation cannot select one. Incomplete retrieval is not proof of missing data. Source inspections and gap status remain in the session brief. This supersedes earlier advice treating definition ambiguity and proxy substitutions identically. [Verification and limits](../evaluations/COVERAGE_GAP_POLICY_REVIEW.md).

