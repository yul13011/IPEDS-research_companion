# Step 4: general query and validation engine

October 21 update: national/state/sector directory populations and independent
annual aggregate queries are now supported. The former named-institution-only
boundary below is historical. See [POPULATION_AGGREGATES.md](POPULATION_AGGREGATES.md)
for current population, missing-pair, benchmark discrepancy and release rules.

October 19, 2026. This supersedes the earlier same-row-only execution boundaries in CATALOG_EXECUTION.md and GENERAL_CALCULATIONS.md. The full local catalog remains the data scope; no new original source files were changed.

## Acceptance criteria and implementation

| Capability | Implementation and verification |
| --- | --- |
| Grouped extracts | Explicit source key dimensions become codebook labels. Award counts by award level match independent source SQL. Category codes cannot become numerical measures. |
| Row aggregates | Sum, mean, weighted mean, count, distinct count, min and max on an explicit source domain. Totals mixed with components, hierarchical ancestors and unresolved overlapping categories are rejected. |
| Fact joins | Explicit source aliases, keys, periods, one-to-one or many-to-one cardinality. Metadata preflight followed by observed uniqueness, unmatched-key and row-multiplication checks. No implicit or many-to-many joins. |
| Multi-step calculations | Typed acyclic expression graph: addition, subtraction, multiplication, division, share percentage, percentage change, and reducers. No model-authored SQL, Python or arbitrary expressions. Percentage-change inputs are NEW then OLD baseline. |
| Weighted analysis | Source-rank salary means use matching contract headcounts; joined tuition/enrollment can use explicitly requested enrollment weights. Zero-weight missing values contribute nothing; missing positive-weight values propagate by default. |
| Time and cohort alignment | Source observation periods, field qualifiers, successive-period comparisons, explicit cross-period comparisons, and coded entering cohorts are checked. Graduation completers and adjusted-cohort selectors must establish the source population relationship. No release-year substitution. |
| Signed values and missingness | Documented missing codes take precedence. Financial balances with source evidence can retain genuine negatives. Negative counts remain missing. Zero denominators produce missing results; negative growth baselines require a different explicit method. Missing selected institutions propagate into combined calculations unless complete cases were requested. |
| Chat integration | Bounded catalog tools submit version-2 plans, receive validation feedback and repair at most twice. Result summaries, grouped charts, tables and all three exports use the normal result controls. Version-1 and reviewed routes remain supported. |

`query_schema.py` defines the closed plan vocabulary; `query_engine.py` binds, validates, compiles and executes it. All field IDs, physical columns and categorical codes are revalidated against exact source records. Definitions, filters, formulas, SQL parameters, source identity, join results, missingness and timing remain in downloads.

Limits: 30 named institutions, 20 source relations, 100 distinct fields in a plan, 40 fields per relation, 24 expression nodes, 20,000 selected rows per source and 5,000 output rows. Annual databases stay read-only with query deadlines. Non-institution join keys need matching documented meanings and compatible code labels; changed classifications require a reviewed crosswalk. A reducer cannot double-count a scalar repeated by a join.

The semantic-description snapshot was rebuilt with parser version 2: all 23,990 definitions described, 14,768 with recognized units and 9,222 explicit unknowns (including categorical fields). A descriptor is not execution approval. Unknown numeric meanings, conflicting source locations, insufficient relationship evidence or genuinely ambiguous methods still block the affected calculation.

## Validation evidence

- `prototype/tests/test_query_engine.py`: independent SQL comparisons for grouped awards, rank sums, weighted salary, fact joins, chained formulas, same-table population comparisons, cross-year change, cohort rates and combined institutional means; negative checks and Streamlit chat/download checks.
- `prototype/tests/verify_catalog_execution.py`: combined regression run, including earlier catalog, calculation, planner, loading, legacy and source checks. Per-case wall times in `evaluations/catalog_execution_verification.json`.
- `prototype/tests/query_engine_latency.py --live`: unfamiliar questions through the actual chatbot, independent expected values and CSV/Excel/audit serialization. Results in `evaluations/query_engine_latency.json`. Failed development runs exposed categorical codes as outputs and reversed growth inputs; both now have validation checks and regression tests.

Current live examples: grouped awards 26.01 seconds; weighted salary 11.89 seconds; applicant growth 16.56 seconds. Small serial sample, no conversation history, excludes browser paint. Source queries take a small fraction of total time; model discovery/planning dominates. Additional joined-question measurements are recorded in the same report.

## Completion boundary and owner input

Step 4's query-engine primitives are implemented. This is not a claim that every IPEDS interpretation, custom metric or question is validated. Catalog/planner recall, unknown field semantics and source inconsistencies can still prevent an answer, and broader coverage evaluation remains necessary.

No owner input is required for these engineering changes. Ask a user only for an actual unresolved analytical choice, such as a custom URM definition, pooled versus unweighted rates, a national/sector reporting-unit policy or an unspecified weight population. Do not ask users for database mappings or prior test cases. National/state/sector universe selection and custom category policies remain outside the named-institution engine; unsupported requests must state the actual limitation without saying the source data is absent.

Final verification: 93/93 combined regressions passed. Four live unfamiliar questions matched independent SQL and exported successfully. Answer-ready times 11.89–30.04 seconds; median 21.29 seconds. The joined Yale/Harvard tuition/enrollment weighted mean took 30.04 seconds. These timings are a small sample, not an SLA.
