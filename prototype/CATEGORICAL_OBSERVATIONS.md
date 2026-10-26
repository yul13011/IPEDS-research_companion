# Typed source observations

Implemented October 22, 2026 for F029. Numerical plans remain version 1/2 on their
existing executors. The separate `submit_observation_plan` tool has its own version
1 schema; answers identify `result_schema_version=2` and an `observation_plan`.
This is a direct source projection, not a new arithmetic engine or external source.

## Source binding and interpretation

`observations.py` reuses `catalog_planner.validate_proposal` for exact physical
fields, release ownership, source-code filter evidence and institution binding.
The source grain must include UNITID; every other key must be fixed to one exact
category. Selected source rows must actually be unique by UNITID. Population
lists intersect validated predicates within each release, preserving reporting
institution IDs rather than deduplicating similar school names. Oversized sources
or outputs fail without publishing a partial list.

Field storage and semantics are separate. Categorical responses carry a null
numerical value, original code, exact release/field label, response status and
category record IDs. Missing, Not reported, Not applicable, Implied no and unmapped
codes remain distinct. Conflicting mappings fail validation. Text and identifier
observations have explicit types; quantities use the existing unit descriptors.
Codes are not summed or averaged. Existing numerical queries still perform valid
counts/frequencies of institutions matching categorical conditions.

The source-backed DISABPCT companion rule verifies its DISAB definition and mappings
for each release. A low-range response supplies a bound with no fabricated exact
value. An unavailable precise value with a More than X percent selector retains
that lower bound. Nulls do not become zero. Disability student observation dates
come from the actual variable definition, separately from academic release coverage.
This rule covers institutions uniformly; it does not harmonize unrelated measures
or convert every source-defined conditional field automatically.

## Planning, identity and context

The planner can submit categorical/mixed projections directly. Simple legacy
projection plans can be adapted losslessly; aggregates, joins and calculations
are never silently converted. Existing numerical arithmetic validators remain.
Dummy count-of-one plans are rejected for direct categorical lookups. Typed plans
retain explicit release labels and source concept anchors; immutable request
institution checks prevent dropping schools. Every returned response cell is
covered by the projection's integrity record.

Models receive the readable institution name with an explicit UNITID annotation,
instead of a bare number that can be mistaken for enrollment. Legacy deterministic
parsers invert only those exact verified annotations, preserving their established
vocabulary. Context stores typed source plans; definition follow-ups may explain
inspected field references even when an earlier statistical plan was blocked.
The source definition route retrieves category labels and variable evidence locally,
without adding a classification model call.

Provider tool batches exceeding four requests receive bounded split-batch feedback,
not an uncaught exception. Overall inspection/call limits remain. Exhaustion returns
a planning limitation with recorded usage/trace, not a claim of unavailable data.

## Display and persistence

Typed results default to tables and cannot be forced into a numerical chart.
Comparisons pivot source response cells by institution; mixed source periods stay
visible. Summaries group only identical actual responses, avoiding first-row label
reuse. CSV/Excel/audit downloads retain codes, labels, statuses, bounds and evidence.
Old numerical results remain readable; old categorical count workarounds are not
silently reinterpreted as validated typed observations and should be rerun.

Disable the new execution route with environment variable
`IPEDS_TYPED_OBSERVATIONS=0` and restart the app. This blocks new typed execution;
it does not weaken numerical validation or erase saved source evidence.

## Validation and scope

Tests: `prototype/tests/test_observations.py` plus the complete registered regression
runner. Live source comparisons: `evaluations/verify_live_observations.py`.
Implementation evidence and final run status belong in
`evaluations/CATEGORICAL_REPAIR_IMPLEMENTATION_REVIEW.md`.

This is not a claim that every source field/release has been independently reviewed.
Multi-row facts need fixed source selectors or the existing relational numerical
route. Service availability cannot establish quality, capacity or usage. No external
data source, new orchestration framework or vector database was added. F027 owner
terminology review and the paused national benchmark retain their prior statuses.
