# Catalog-driven planning — step 3

October 21 update: this is a historical milestone. Current national/state/sector population support is documented in [POPULATION_AGGREGATES.md](POPULATION_AGGREGATES.md); the former blanket restriction below is superseded.


> Current status: step 4 now executes eligible catalog-backed direct observations and the enrollment race/ethnicity acceptance case. See [CATALOG_EXECUTION.md](CATALOG_EXECUTION.md) for boundaries and live latency results. Earlier proposal-only statements below describe the step 3 checkpoint.

Implemented October 19, 2026. The fixed measure list is now one route, rather than the sole planning vocabulary. This stage prepares unfamiliar analyses; their numerical execution remains step 4.

## Routes

1. **Reviewed questions** keep the existing `Plan` validator, reviewed mappings, read-only execution, result presentation and exports.
2. **Unfamiliar statistical questions** use `catalog_planner.py`. Known extra dimensions route here before the legacy model can reduce them to overall totals. The legacy model tool can also select intent `catalog` for other unfamiliar concepts.
3. **Definition/discovery questions** retain source search without pretending to answer institution statistics.

Removed blanket mapping-based prohibitions for enrollment breakdowns, admissions breakdowns, other graduation time spans and combined graduation subgroups. These can now be investigated and proposed, not automatically executed. Methodological guards for custom URM groupings and cross-institution/national/sector aggregation remain until their methods are settled. Existing verified source limits such as SAT 10th/90th percentile collection remain distinct from mapping limitations.

## General planning vocabulary

The proposed-plan schema has no fixed measure-ID enumeration. It supports:

- Named institutions and annual source-release scope.
- Requested time meaning independently of release labels.
- Exact source definition IDs for measures, dimensions, identifiers and denominators.
- Typed equality/inclusion/range filters; categorical filters carry exact source code-record IDs and code values.
- Grouping references and typed sum, difference, ratio, percent, mean and count proposals.
- Proposed joins with source year, table names, physical key columns and purpose. UNITID does not require a nonexistent per-table variable-definition ID; physical key evidence is checked instead.
- Output preference, assumptions and explicit clarification questions.

The plan has no SQL, Python expressions or arbitrary executable formulas. All extra properties are rejected.

## Metadata tools

The configured model can use only `search_catalog`, `inspect_table`, `read_definition`, `category_values`, `submit_catalog_plan` and `ask_clarification` in this route. These inspect the complete supplied catalog through the read-only evidence layer. They cannot execute statistical queries or read arbitrary files.

Search and definition/category inspection are bounded and paginated. Initial table cards cover all institution-data tables in a relevant supplied release; the model can inspect other releases through tools. A run allows at most eight model calls, sixteen tool requests, and four tool requests per response. Tool errors are returned for bounded repair, not treated as successful plans. If retrieval remains incomplete, ask the user to narrow the request rather than claim that the source data is absent.

## Proposal validation and persistence

Before saving a proposal, deterministic code checks schema bounds, exact source definition IDs, physical availability, category-code ownership and values, selected evidence for every source year, named institution resolution, and physical join keys. Location conflicts and unreviewed joins remain explicit blocks. Plans retain complete source definition/category/table evidence, resolved institution IDs, catalog identity and validation findings.

Saved proposals live in `data/proposed_plans/{proposal_id}.json`. They are **not** inserted into `reviewed_measures.json`. Every proposal explicitly has `execution_approved: false` and lists the remaining semantic checks, including complete question coverage, populations, units/denominators, time meaning, missingness, joins, aggregation and longitudinal comparability. Matching metadata is not a claim that these checks are complete.

## First acceptance case

“Show Yale's undergrad population by race and ethnicity” now produces a source-backed proposal rather than an unavailable-data response. A deterministic offline acceptance route binds each requested annual `EF{year}A` codebook, undergraduate selector `EFALEVEL=2`, nine official race/ethnicity reporting fields and total headcount. Unknown race and U.S. nonresident remain separate. Percent requests carry an explicit total-undergraduate denominator.

This route contains no statistical values. It rejects unrecognized extra scope (such as income, disability, attendance status or exclusions) instead of silently dropping it. Its current bounded size permits up to four annual count breakdowns or one annual percentage breakdown. Other questions use model tools when conversational AI is enabled; offline mode otherwise returns source evidence and an explicit planning limitation.

Existing latest-year behavior is retained: unspecified fall enrollment uses 2024. This is not a new claim that the latest supplied release answers every period. Explicit unavailable dates are not replaced automatically. A user can correct a date through a clarification reply.

## Conversation and presentation

Proposals are shown as source-backed plans with a clear statement that no numerical analysis has run. Definitions & sources remains one popover. No data-download control or fabricated table/chart is shown for an unexecuted plan.

Catalog context is kept separate from reviewed-result context. Short replies to pending clarifications retain the original request; new self-contained questions reset that pending scope. A display-only request after a proposal does not resurrect an older numerical answer. Opening the reviewed-measure extract builder after a proposal does not copy unsupported metrics into it.

## Input required from the project owner

No new methodological choice was required for this implementation. The acceptance case follows source-defined categories, the explicit undergraduate selector and existing year defaults. If a future request needs custom race grouping, unresolved population/denominator/time interpretation, reporting-unit aggregation or a source conflict, surface the exact issue before claiming an answer. Do not ask the owner to choose database columns or approve routine metadata inspection.

## Validation

### Annual source series and labelled clarifications (October 19)

`read_source_series` takes previously inspected definition IDs, requested years and selected category values. It independently looks up each annual table, field definition and category-code evidence ID. It returns missing/ambiguous evidence explicitly, marks truncated definitions, and exposes each annual table's required population selectors. It accepts at most 40 field/year combinations; it does not infer comparability, harmonize categories, execute SQL supplied by a model, or bypass validation. Tables without one unambiguous four-digit annual token require separate inspection.

The planner is instructed to include every annual field and filter explicitly, use an existing reported total where appropriate, and satisfy every required population-key selector. This reduces repeated metadata requests for ten-year questions across survey families. Current eight-call/16-tool bounds and semantic checks remain.

`submit_annual_plan` accepts a complete one-release version-1 template and requested years. The server expands exact field/category evidence IDs independently for each release, rejects missing/ambiguous fields or changed category labels, and runs the ordinary proposal and runtime checks. It does not join years or assume that identically named fields are comparable. It supports independent lookups and same-row arithmetic within the existing 40 field/year retrieval bound. Version-1 filters are bounded at 40, allowing ten years with three required selectors per year. Grouped analyses and joins continue to use the relational engine.

Population keys can be documented by exact variable definitions and codebook categories as well as table prose. A literal variable abbreviation need not appear in a table description when its own definition and selected category evidence document it. Equality filters and observed row uniqueness remain required. Generic employee measure titles are qualified with the selected source population so a filtered faculty count is not described as all employees.

A bare labelled choice such as `(a)` or `option b` is bound locally to the immediately pending clarification when its labels are unambiguous. The original request, selected definition and explicit fall-year range are retained. Unlabelled or ambiguous replies continue through semantic resolution. No additional model call is needed for this exact selection path.

Tests use real local catalog evidence and mocked model transport, with no live API charges. They cover non-registry academic-library planning, the enrollment acceptance case, typed calculations and joins, source conflicts, rejected SQL/unknown IDs, exact categorical filters, year preservation, clarifications, context separation, UI rendering and continued reviewed execution.

Run from `agent-redesign`:

```powershell
& 'C:/Users/liyuj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' prototype/tests/test_catalog_planner.py -v
& 'C:/Users/liyuj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' prototype/tests/test_prototype.py
```

This is not a live-model accuracy evaluation or proof that every unfamiliar question produces a complete plan. General live-model phrasing, cost/latency and adversarial coverage still need evaluation. Existing Yale benchmark discrepancies are retained.

## Next stage

Step 4 must semantically validate unfamiliar plans, compile eligible operations into bounded read-only queries, validate results and adapt chart/table/export rendering to dynamic measures. Do not remove the execution barrier simply because a typed proposal exists. Existing reviewed mappings remain the numerical baseline.


## Source-bound clarification workflow (October 21, 2026)

The current general planner uses `offer_analysis_options` for preflighted executable alternatives and `submit_analysis_bundle` for confirmed multi-panel requests. Exact choices execute their saved plans locally; modified choices retain the analysis brief and are freshly validated. See [Analytical clarification](ANALYTICAL_CLARIFICATION.md) for the current contract and [evaluation](../evaluations/CLARIFICATION_WORKFLOW_REVIEW.md) for live evidence. The earlier proposal-only next-stage description above is historical; the general validator and executor are implemented within their documented bounds.
