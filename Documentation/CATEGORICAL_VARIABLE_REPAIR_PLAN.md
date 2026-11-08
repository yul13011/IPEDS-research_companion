# Categorical question repair plan

Recorded October 22, 2026 at the user's request.

**Status: implemented and activated; six stages completed within the documented
validation scope.** Finding F029. Completed October 23, 2026.
See `evaluations/CATEGORICAL_REPAIR_IMPLEMENTATION_REVIEW.md` for evidence and limits.
National aggregate benchmark reconciliation remains paused. Owner terminology review
F027 remains open. This plan does not change either status.

## Goal and scope

Answer categorical lookups, comparisons and institution-list questions from supplied
IPEDS codebooks and tables. Support mixed categorical/numerical answers without
changing numerical calculations, unit rules or arithmetic safeguards. Implement a
shared capability rather than exceptions for particular schools or services.

Only user-provided sources are allowed. Explain genuine coverage gaps before
offering optional proxies. Distinguish unavailable source data from retrieval,
planning, validation or execution failures. Do not reinterpret a failed query as
evidence of source absence. No outside sources or new framework are required.

## Observed evidence

- Smith service lookup decoded the right categories but represented the answer as
  a grouped record count of 1. Existing completion checks accepted that workaround.
- Massachusetts undergraduate distance-education list exhausted the planning search
  limit. Categorical output limitations are relevant, but its precise planning
  failure has not yet been isolated.
- Three-college student-services comparison was blocked with: "Categorical codes
  must be group labels, not numerical measure outputs."
- Simpler executor accepts only continuous numeric measures. Relational executor
  allows categories as filters/groups but rejects direct categorical outputs.
  The narrative formatter also assumes numeric values.

Artifacts: `evaluations/ic_question_replay.json`,
`evaluations/ic_services_comparison_replay.json`,
`evaluations/ic_direct_source_answers.json`, and
`evaluations/MA_UNDERGRADUATE_DISTANCE_EDUCATION_2024.md`.

Metadata classification and label decoding already exist. This is not evidence
that every field or every release has correct categorical semantics.

### Broader exploratory testing and revised priorities

Sixteen additional live turns (12 initial questions, two contextual follow-ups and
two targeted probes) were checked against supplied source tables/code mappings.
See `evaluations/IC_CATEGORICAL_EXPLORATORY_REVIEW.md` for exact questions,
outcomes and limits. Raw files: `evaluations/ic_categorical_probes/`.

- Calendar lookup/follow-up found Semester but used dummy counts. Religious
  affiliation rows decoded Roman Catholic versus Not applicable correctly, but
  the summary reused Boston College's category heading for Smith. It also proposed
  a bar chart of two meaningless per-institution counts of 1.
- Explicit Yes/No admission policies, award levels, distance courses versus
  programs and mixed category/percentage output hit categorical-output blocks.
- A two-service institution list raised an uncaught planning tool-batch-limit error.
- A childcare institution count correctly returned 20. Preserve this working path.
- A two-release AP-credit question produced a blocked final plan containing only
  2024, dropping 2015. No incomplete statistical answer was published, but repair
  attempts need stronger original-intent preservation.
- A Smith disability percentage question reinterpreted confirmed UNITID 167835 as
  an undergraduate count and asked the user to identify the institution again.
- Category-label definition phrasing missed documentation routing. A direct
  definition rephrasing routed correctly but concatenated label, field and release
  into one unsuccessful search term. A definition follow-up after a blocked
  distance comparison attempted another statistical query instead of explanation.
- Bentley's DISAB=1 means "3 percent or less" and DISABPCT is null by design.
  The app queried only DISABPCT, said Not reported, and labelled the period academic
  year 2024-25 rather than identifying the Fall 2023 student observations.
- The quality-ranking question correctly explained availability cannot establish
  quality, but exposed numerical IDs and internal tool limitations.

**Priority order:** prevent misleading summaries and conditional-value
interpretations; preserve identity and original scope; implement typed outputs;
complete documentation, follow-up and planner recovery support. All are required
before activation. No application implementation was changed during this review.

## Stage 1 — Establish contracts and independent acceptance fixtures

- Trace both entry points, catalog-plan versions, source metadata, validators,
  execution, summaries, table/chart rendering, exports and conversation context.
- Preserve current numerical regression expectations before changing behavior.
- Define explicit output types: quantitative observation, categorical observation,
  institution list, and mixed table. Reuse common source/institution/period evidence.
  Keep field storage type, semantic role and requested output shape separate.
- Establish categorical field roles from source definitions and code mappings:
  category, identifier and text are distinct; numeric storage does not imply quantity.
  Treat conflicting or insufficient evidence as unresolved, with evidence attached.
- Record independent expected results from read-only source SQL and exact codebook
  mappings. Fixtures must not be generated by the implementation under test.

Deliverable: documented result contract and three source-backed acceptance fixtures.

Additional Stage 1 requirements from the probes:
- Carry institution identity as structured context with readable names and explicit
  ID annotations. Replacing names with bare numbers in prose is insufficient.
  Verify every route treats UNITID as identity, never enrollment.
- Preserve an immutable original-request contract (institutions, fields, periods,
  logical operators and output kind) through repair attempts. A plan dropping a
  year must not become executable after an unrelated type repair.
- Include category-code definitions/comparisons as documentation intents. Parse
  label, variable/topic, survey and release separately. Retrieve exact category
  records with variable definitions; do not invent explanatory definitions absent
  from source text.

## Stage 2 — Add typed categorical execution

- Extend the existing relational plan with explicit typed projection, including
  non-aggregate categorical outputs and row-list outputs. Maintain compatibility
  with numerical plans; version the changed schema rather than silently changing
  the meaning of existing saved plans.
- Return institution ID/name, field ID/title, raw code, exact source label,
  interpretation status, release/reporting period and variable/category evidence.
  Keep codes and labels in separate fields; never put label strings in an existing
  numeric value field or use a dummy count to satisfy the result schema.
- Decode using the exact release/table/variable mapping. Preserve zero, negative
  codes, blanks and nulls before interpretation. Keep Implied no, Not reported,
  Not applicable, missing observation and unknown/unmapped code distinct.
- Reject ambiguous duplicate code mappings. Unknown codes retain raw evidence and
  an explicit unresolved label rather than becoming No or a numerical measure.
- Preserve measurement type/unit for quantitative fields in mixed results.
- Represent source-defined conditional values explicitly. DISAB=1 means "3 percent
  or less" while DISABPCT can be null by design. Return the bound and reason, never
  zero, exactly 3%, generic Not reported or an invented precise value. Keep bounds
  distinct from exact measurements in tables, calculations and exports.
- Inspect linked category selectors before interpreting companion quantitative
  fields. Preserve conflicting source threshold wording for review rather than
  guessing a boundary.
- Apply existing read-only, identifier validation, parameterization, query bounds,
  institution identity, source location and period constraints to all new outputs.

Deliverable: deterministic categorical retrieval that works without a model call.

## Stage 3 — Support filtered institution lists and safe category operations

- Support evidence-backed categorical filters and projections across documented
  directory/source joins. Verify keys and cardinality before returning schools.
- State the institution universe, geography and reporting period. Do not silently
  equate all reporting institutions with degree-granting colleges or Title IV schools.
- Default list grain to one institution per relevant period; do not deduplicate
  genuine campus/reporting units by similar names. Show truncation and coverage.
- Keep related concepts distinct: distance courses versus complete distance
  programs; availability versus participation, capacity or service quality.
- Count matching institutions using institution identity and declared period/grain,
  not by summing Yes codes or indiscriminately counting joined rows.
- Allow frequency/percentage summaries only with explicit population, denominator
  and treatment of nonresponse/inapplicability. Block arithmetic on nominal codes.
  Ordinal categories require a documented method before numerical interpretation.
- Trace and fix the Massachusetts planning failure using its saved tool trace;
  do not assume adding categorical projections alone resolves it.

Deliverable: validated school lists and categorical filters, without fabricated metrics.

## Stage 4 — Render, export and preserve context by result type

- Single school: service/response rows. Multiple schools: comparable fields by
  institution. Lists: school identity and the relevant matching response/evidence.
- Summaries must answer availability/comparison questions directly; suppress dummy
  record counts and internal schema instructions in user-facing answers.
- Build each institution's narrative from its own typed response cells. Never
  reuse the first row's category-bearing label for all institutions. Require
  agreement between narrative, table, chart and exports; correct table rows do
  not excuse a misleading summary.
- Preserve source category distinctions in labels and explain Implied no briefly.
  Never imply Yes establishes quality, usage or complete remote program availability.
- Default categorical results to tables. Numerical charts retain existing rules;
  category codes cannot become measurement axes. Valid frequency charts use counts.
- CSV/Excel exports retain raw codes, labels, statuses, release/period and source
  references. Check source panels and other existing download paths for safe handling
  of typed tables; disable unsupported visual exports with a clear explanation.
- Follow-up context stores field IDs, filters, institutions, periods and output type;
  it must not reconstruct analytical intent from answer prose. Test changing school,
  changing year, "which of these?" and follow-ups requesting counts or numerical data.
- Preserve relevant inspected field references from blocked answers as documentation
  context without treating failed plans as validated data. A question about the
  difference between two previously selected categories must explain the concepts
  or clarify the reference, rather than become another counting query.
- Version persisted answers. Old numerical answers remain readable; old categorical
  count workarounds are not silently reinterpreted as newly validated observations.

Deliverable: complete table, summary, evidence, export and follow-up support.

## Stage 5 — Integrate planning with bounded latency and cost

- Teach the existing planner to request typed categorical projections, comparisons,
  lists and mixed outputs. Use metadata roles and category evidence rather than
  trusting the model's proposed type.
- Avoid a separate classification model call. Retrieve a bounded relevant set of
  definitions and code mappings; reuse them within the request. Any cache must be
  keyed to source identity/release and invalidated when source metadata changes.
- Replace guidance that forces categories into group labels with the typed-output
  contract while retaining numerical-only arithmetic rules.
- Validation feedback should identify a repairable type/shape error and preserve
  user intent. Do not turn every unresolved implementation detail into a user question.
- Handle provider tool batches above the local per-call limit through bounded,
  actionable recovery. Do not crash or silently omit required inspections. Return
  a user-facing planning limitation if the budget is exhausted. Test this
  deterministically rather than increasing every search/call limit.
- Prefer targeted field-plus-code evidence over repeated broad searches. Retain
  traceable failure stage/reason and usage accounting on failed paths.
- Require semantic completion checks: requested institutions/periods/fields and
  categorical answer cells must exist; a record count does not satisfy availability.
- Clarify genuinely ambiguous concepts; describe source gaps before optional proxies.
  Never silently substitute a simpler concept to achieve execution.

Deliverable: live app handling through the same user-facing route used in production.

## Stage 6 — Acceptance, numerical regression and controlled activation

### Required Institutional Characteristics examples

1. "What student services does Smith College offer, such as academic counseling,
   career placement, and on-campus childcare?"
   Expected for 2024–25 provisional: counseling, employment and placement Yes;
   childcare Implied no. No artificial record count.
2. "Which Massachusetts colleges offer distance education at the undergraduate level?"
   Under an explicitly stated degree-granting scope, 83 reporting institutions:
   52 report distance programs and 31 report courses with programs Implied no.
   Broader source scope includes 86 institutions (three nondegree). Verify exact IDs,
   codes and completeness, not just counts; all 86 report undergraduate distance courses.
3. "Compare the student services offered by Smith College, Mount Holyoke College,
   and Wellesley College, including counseling, student employment, career placement,
   and on-campus childcare."
   Expected: 12 cells; each college has the same three Yes responses and childcare
   Implied no. Preserve institution identity, field meaning, period and source evidence.

### Additional meaningful checks

The full exploratory question matrix in
`evaluations/IC_CATEGORICAL_EXPLORATORY_REVIEW.md` becomes an acceptance set in
addition to the original three. Reproduce observed failures deterministically,
then live replay representative cases; one model run is not a reliable pass rate.
Prioritize affiliation summary errors, lost temporal scope, identity confusion
and source-dependent percentage interpretation.

- Source-code handling: Yes, explicit No where documented, Implied no, Not reported,
  Not applicable, null/blank, unknown codes, duplicate mapping conflicts and codes
  whose meanings differ across releases. Include numeric- and text-stored codes.
- Safety: sum/mean of categories and IDs blocked; counting distinct matching
  institutions valid; joins cannot inflate lists/counts; multi-period rows not
  miscounted as distinct institutions. No source-backed classification by school name.
- Numerical compatibility: enrollment, salary/currency scale, rates, ratios, totals,
  grouped counts, charts, missing values, reviewed measures, exports and saved results.
  Compare values, units, scope and evidence against established expectations.
- Mixed categorical/numerical output and conversational follow-ups through the
  outer institution-confirmation route; actual Streamlit render and export checks.
- Correct source observation dates independent of release dates: DISAB/DISABPCT
  in the 2024-25 release describe Fall 2023 undergraduates. Cross-release categories
  need per-release mappings, not a shared unverified label dictionary.
- Role-sensitive negative codes: OPENADMP uses 2=No; selected service fields use
  0=Implied no. RELAFFIL=-2 remains Not applicable, not Not reported or an inferred
  religious-affiliation claim.
- Preserve the valid count of 20 childcare institutions and verify all 14 source
  institution IDs for the combined study-abroad/childcare list independently.
- Quality questions must explain the source coverage gap, offer availability only
  as an optional alternative, and keep internal IDs/errors out of the narrative.
- Run the complete registered regression runner, including numerical tests, after
  targeted checks pass. Fix introduced regressions before declaring completion;
  distinguish pre-existing failures and environment/provider issues explicitly.
- Live replay all three questions; compare every response against independent SQL
  and source labels. Repeat at least once to detect planner variability. Record
  model calls, tokens, estimated API cost and answer-ready latency against the
  saved baseline. Numerical requests should acquire no new mandatory model call.

### Activation and completion standard

- Keep new typed behavior isolated until execution, rendering, exports and planner
  contracts pass. Retain an explicit rollback switch for the new route; do not
  weaken numerical validation to enable categorical answers.
- Update technical docs and findings with stages completed, test commands/results,
  source evidence, live latency/cost and remaining limitations. Verify the active
  local server uses the tested code after restart.
- Mark implementation complete only after deterministic tests, registered numerical
  regressions, live acceptance and UI/export checks pass. Automated checks are not
  a claim that every catalog field or release was independently reviewed.

## Intended code touchpoints

`prototype/field_semantics.py`, `prototype/catalog_planner.py`,
`prototype/catalog_execution.py`, `prototype/query_engine.py`,
`prototype/responses.py`, `prototype/components.py`, `prototype/ui.py`,
plus export, context and test modules identified in Stage 1.
Keep categorical decoding shared rather than duplicating mappings across components.

## Status checklist

- [x] Stage 1: contracts and independent fixtures
- [x] Stage 2: typed execution
- [x] Stage 3: institution lists and safe operations
- [x] Stage 4: display, exports and context
- [x] Stage 5: planner integration and bounded retrieval
- [x] Stage 6: regression, live acceptance and activation
