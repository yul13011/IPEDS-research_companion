# IPEDS analytical agent: living design

Current status and work tracking: [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md). Its completed items and backlog summarize the latest implementation; dated stages below preserve earlier design/checkpoint history.

Status: Living design. The annual foundation is implemented and verified. A local Streamlit prototype with bounded conversational planning and 36 implementation-reviewed measure mappings is now implemented; see section 18. Broader analytics and public deployment remain future work.

Created: October 16, 2026

Owner: Project owner and development collaborators

## 1. Purpose

Build a conversational application that helps users discover, retrieve, analyze, visualize, and export IPEDS data across annual releases. The application should explain what the data measure, which tables and variables it uses, and where uncertainty or ambiguity affects the answer.

The agent must consult relevant codebook evidence before querying data. It should choose the actions appropriate to the request, while application code enforces analytical and execution rules.

This document records the current design, unresolved choices, acceptance criteria, and implementation sequence. It is not a claim that these capabilities already exist. Update it as source inspection and testing resolve assumptions.

## 2. User needs and expected behavior

| Request type | Example | Expected behavior |
| --- | --- | --- |
| Discover available data | What data do you have on financial aid? | Search metadata; explain measures, populations, periods, available years, and limitations; suggest relevant analyses. No data query is necessary unless it helps establish availability. |
| Retrieve and export | Give me a spreadsheet of six-year graduation rates for Yale and the other Ivy League universities. | Resolve institutions, measure, and years; retrieve validated data; produce an Excel or CSV export with sources and methodology. |
| Visualize | Draw a trendline of the percentage of Yale undergraduates receiving financial aid. | Resolve the aid definition and population; verify comparability across years; produce a chart and its underlying data. |
| Aggregate | What is the six-year graduation rate of four-year institutions in the United States? | Define scope; retrieve matching numerator and denominator counts; account for reporting units; calculate a student-weighted rate and disclose coverage. |
| Explore and follow up | Add Harvard; show the table; explain the difference. | Reuse validated results where sufficient, retrieve additional data when necessary, and preserve the user's established interpretation. |

Future exploratory capabilities should be added through tools and analytical rules without redesigning the whole application.

## 3. Current foundation and evidence

- Existing prototype: Streamlit, Anthropic SDK, Pydantic, SQLite, and chart rendering. The current application focuses on a restricted selection of graduation/completions data; the redesign expands discovery and analytical scope.
- Inspected source: `IPEDS_2015-16_Final/IPEDS201516TablesDoc.xlsx` and the corresponding Access database.
- The inspected workbook has five sheets: `Introduction`, `Tables15`, `vartable15`, `valuesets15`, and `Metadata defintions` (source spelling).
- The Access database was successfully read using Jackcess, bypassing the installed Access engine, and converted to `IPEDS_2015-16_Final/IPEDS201516.sqlite`.
- The converted database contains 52 user tables and 3,299,056 rows, including 47 data tables and five documentation tables. Row counts, per-column null counts, and SQLite integrity were checked. Conversion scripts and a verification report are in `outputs/access_conversion/`.
- Annual folders from 2015–16 through 2024–25 exist in the project directory. Their contents, schema consistency, and release completeness have not yet been inventoried. The latest folder is labeled provisional; earlier folders are labeled final.

Do not assume that every year's workbook or database has the same sheets, definitions, or table structure merely because the files look similar.

## 4. Agreed requirements

1. Support all supplied years and their codebooks, including longitudinal questions.
2. Search relevant codebook definitions before selecting tables, variables, and filters for a new analysis.
3. Explain the selected sources and material ambiguities.
4. Produce the requested output: answer, table, spreadsheet, chart, or a combination.
5. Let the agent select tools and sequence actions, subject to enforced prerequisites.
6. Keep statistical definitions, joins, aggregation rules, and missing-data handling explicit and verifiable.
7. Preserve source files and reproducible provenance.
8. Allow new exploratory capabilities later.

## 5. Proposed architecture

```text
PREPARATION: performed when sources are added or revised

Annual databases + workbooks + release documentation
                         |
                 Import and validate
                         |
         +---------------+----------------+
         |                                |
 Searchable metadata catalog     Analytical data store
         |                                |
         +----- Annual concept mappings --+

QUESTION ANSWERING: performed during a conversation

User request + relevant session context
                         |
             Agent selects next action
                         |
       Metadata discovery and interpretation
                         |
           Structured analysis plan
                         |
              Plan validation
                         |
        Read-only data query / calculation
                         |
             Result validation
                         |
      Answer / table / chart / export + provenance
```

Metadata-only requests may finish after discovery. Presentation-only follow-ups may reuse an existing validated result. New queries must pass the plan-validation checkpoint. This is a flexible tool loop with enforced prerequisites, not a mandatory identical sequence for every message.

### 5.1 Original source archive

Retain original Access databases, Excel codebooks, and accompanying release notes unchanged. Register file hashes, source paths, collection cycles, release status, import time, and importer version.

OneDrive is a local source location for preparation, not a required runtime dependency of the deployed app. Deployment storage and hosting remain an open decision.

### 5.2 Metadata catalog

Normalize documentation into searchable records for:

- Releases and survey components.
- Tables, descriptions, record grain, and keys.
- Variables, labels, long definitions, types, units, and sources.
- Categorical values and their labels, scoped to the appropriate release/table/variable.
- Reporting periods, populations, eligibility, imputation information, and revision status.
- Documentation conflicts and unresolved metadata issues.
- Exact source locations: workbook/sheet/row or database metadata table/key.

Cross-check catalog entries against actual database tables and columns. Mark documented-but-absent fields and undocumented fields explicitly. The codebook guides interpretation; database inspection establishes actual availability.

Start with exact identifier search and full-text search over labels and descriptions. Add semantic retrieval only if evaluated discovery failures justify it. Retrieved definitions must remain attributable to source records.

Import codebooks once during preparation. At runtime retrieve the relevant entries; do not load all annual workbooks into every model prompt. A query plan must reference the retrieved metadata records and their versions. Reusing a reviewed, versioned plan does not require repeating identical retrieval on every presentation follow-up.

### 5.3 Analytical data store

Proposed: DuckDB querying Parquet files organized by collection cycle, release, and source table. Preserve separate table grains. Do not flatten all surveys into one table or silently union incompatible annual schemas.

Initial foundation implementation uses one independently verified SQLite copy per annual Access source under `data/annual/`, plus `data/metadata_catalog.sqlite`. These are faithful annual sources and source metadata, not harmonized analytical views. DuckDB/Parquet remains an optional later analytical-serving choice; it is not required to complete this foundation stage.

Retain a faithful source layer and expose reviewed views for common analytical concepts. SQLite conversions can serve as intermediate imports and reference copies; DuckDB/Parquet adoption is a proposed implementation choice pending review and a small benchmark.

Preserve identifiers, leading zeros, categorical codes, nulls, and source precision. The 2015–16 SQLite conversion preserves MONEY/NUMERIC values as decimal text; a production importer must explicitly map these to suitable exact numeric types for calculations rather than treating all imported columns as analysis-ready.

### 5.4 Annual concept mappings

A concept mapping connects a human question to verified source fields for each year. It records:

- Concept identifier and plain-language definition.
- Population, unit, time basis, and reporting scope.
- Annual source tables, columns, and code filters.
- Numerator/denominator or other calculation rules.
- Valid joins, record grain, reporting-unit rules, and missing-data treatment.
- Comparability status, definition changes, and supporting metadata.
- Review status: proposed, validated, or unresolved.

Example: `six_year_bachelors_completion_rate` maps in 2015 to `DRVGR2015.GBA6RTT`; underlying counts use `GR2015.GRTOTLT` at `GRTYPE=12` and `GRTYPE=8`.

Common measures receive reviewed mappings. Catalog discovery remains available across all imported variables; the mapping registry must not become a whitelist that blocks exploration. Newly discovered plans must pass validation before execution. Unsupported methodological choices should remain unresolved or prompt clarification instead of being guessed.

## 6. Time, releases, and longitudinal comparability

Store distinct fields where applicable:

- Collection cycle.
- Academic/fiscal reporting period and its start/end dates.
- Fall reference date.
- Entering cohort year.
- Outcome date/year.
- Release status, publication date, and source version.

Do not use one generic `year` to represent all of these. A six-year graduation outcome observed in 2015 concerns an earlier entering cohort; annual degrees awarded in 2014–15 measure a different population.

Proposed default: use the latest available version of each collection cycle, preferring final over provisional. Preserve older versions and record the exact selection in every result. Label provisional observations. Never include two releases of the same observation as separate trend points.

For longitudinal plans, verify population, definition, units, categories, institutional identity, and reporting structure across requested years. Distinguish unavailable, not collected, suppressed, not applicable, and genuine zero. Show gaps and breaks in series; do not silently bridge incompatible definitions.

Resolve institution names against year-specific records. UNITID is the main source identifier, but mergers, closures, name changes, and parent/child reporting require explicit handling. Named groups such as the Ivy League need a maintained membership definition with provenance.

## 7. Agent and tool interfaces

Proposed initial stack: Streamlit + Anthropic SDK + Pydantic + validated Python tools. A separate orchestration framework is not required for the first version. Keep model integration separate from analytical logic so it can be replaced later.

| Tool | Responsibility |
| --- | --- |
| `search_catalog` | Discover candidate surveys, tables, variables, and concepts. |
| `get_metadata` | Retrieve complete definitions, categorical codes, periods, grain, keys, and source references. |
| `resolve_institutions` | Resolve names/aliases and named peer groups to verified annual identifiers. |
| `check_year_coverage` | Report available releases and comparable years for a proposed measure. |
| `validate_analysis_plan` | Check metadata support, populations, periods, columns, filters, joins, calculations, and unresolved ambiguity. |
| `execute_query` | Compile/execute approved read-only queries with bounded resources. |
| `validate_result` | Check row grain, duplicates, missingness, coverage, totals, denominator validity, and calculation consistency. |
| `render_table` / `render_chart` | Render full validated results using typed presentation specifications. |
| `export_result` | Generate CSV/Excel from full validated results with source/methodology information. |

The LLM proposes an interpretation and plan. Deterministic code validates it and compiles common operations into SQL. For novel exploratory SQL, use a restricted read-only interface with approved tables, validated identifiers, join checks, and resource limits. A query that is syntactically safe is not necessarily analytically valid.

Execution requires a validated plan ID tied to the metadata/data versions. Tool results are structured and include success/error status, coverage, warnings, and result IDs. Set finite model-turn, tool-call, retry, token, query-time, and output-size budgets. Report limitations clearly when limits are reached; do not silently return a partial result as complete.

Treat source documents and user-supplied text as data, not executable instructions. Protect credentials and keep unnecessary user text out of logs.

## 8. Structured analysis plan

The plan must include:

| Field | Meaning |
| --- | --- |
| Interpretation | What the agent understands the question to mean. |
| Output | Answer, table, chart, CSV, Excel, or combination. |
| Population | Institutions, students, programs, or cohorts included. |
| Scope | Institution group, sector, geography, eligibility. |
| Measure | Definition, unit, numerator/denominator if applicable. |
| Time | Requested years, their meaning, and selected annual periods. |
| Release selection | Exact source versions and provisional/final status. |
| Sources | Catalog references, physical tables, columns, and code filters by year. |
| Grain and joins | Expected record structure, join keys, cardinality, and duplicate prevention. |
| Calculation | Formula, aggregation, weighting, and rounding. |
| Data handling | Missingness, suppression, zero treatment, and reporting-unit rules. |
| Ambiguities | Resolved assumptions and questions requiring a user response. |
| Validation | Required checks and pass/fail evidence. |

Do not require user approval for every plan. Proceed on clear requests and state reasonable assumptions. Ask a focused clarification when materially different interpretations would change the measure or population. Where useful, present multiple supported interpretations explicitly instead of pretending one is unambiguous.

## 9. Aggregation rules

Rates generally require matched numerator and denominator counts for the same population. For a national six-year bachelor's rate, sum eligible completers and divide by the sum of their matched adjusted cohorts. Do not average institution percentages unless the user explicitly requests the average institution's rate and it is labeled accordingly.

Validate geographic scope (50 states/DC versus territories), Title IV scope, institutional level, cohort eligibility, and parent/child reporting. Account for institutions with missing components and disclose included/excluded counts and cohort coverage where measurable.

An absent count row is not automatically zero. In the exploratory national test, absent completer rows were paired with published zero rates. Production handling needs a documented source-based rule: a rounded published zero alone does not prove an exact zero count. That assumption must be resolved before certifying a national aggregate.

## 10. Results, memory, and outputs

Keep full query results in the application, not solely in the model context. Give the model a result ID, schema, bounded preview, coverage summary, and validation findings. Charts, exports, and subsequent calculations consume the full stored result.

Store provenance with every result: plan ID, query and parameters, source versions, metadata references, timestamp, calculation rules, warnings, and validation evidence. Result reuse requires matching scope, variables, periods, source versions, and completeness. A top-ten result cannot support a national total.

Session memory stores selected institutions, measure interpretation, time basis, output preferences, prior result IDs, and pending clarification. Persistent memory across visits is a separate, undecided feature.

Every analytical answer includes a concise Data used disclosure with period, population, measure, release, tables/variables, and material limitations. Put detailed SQL, definitions, mappings, and validation behind an expandable source panel. Metadata-only answers cite catalog evidence and distinguish documented availability from verified data coverage.

Charts must show meaningful time labels, units, gaps, and provisional/definition-change markers. Export the exact underlying plotted values. Excel downloads should contain data and a sources/methodology sheet. CSV should have an accompanying metadata file or equivalent visible source information. Do not truncate downloads to the model preview or UI sample.

## 11. Proposed code organization

```text
app/           Streamlit interface and conversation presentation
agent/         Model adapter, prompts, tool loop, typed plans
catalog/       Metadata import, search, release registry, concept mappings
ingestion/     Access extraction, typed conversion, source checks
analytics/     Query compiler, calculations, aggregation rules
validation/    Plan checks, result checks, coverage checks
outputs/       Chart specifications, tables, CSV/Excel generation
sessions/      Conversation state and result references
evaluations/   Discovery and analytical regression cases
```

This is a logical separation; implementation can start with a few small modules. Keep existing deployment behavior intact until the replacement passes its acceptance checks. Hosting, durable storage, concurrency, result retention, and deployment size must be decided before production migration.

## 12. Acceptance cases and regression coverage

| Case | Expected evidence/result |
| --- | --- |
| Yale versus Ivy six-year rates, 2015 outcome | Select `GBA6RTT`; Yale 97%; Harvard 98%; Princeton 97%; Brown 96%; Columbia/Penn 95%; Dartmouth 94%; Cornell 93%. Tie is based on published rounded rates. Verify using matched raw counts. |
| Yale bachelor's awards, 2014–15 | `C2015_A`, `UNITID=130794`, `AWLEVEL=5`, `CIPCODE='99'`, `MAJORNUM=1`, `CTOTALT=1327`. Detailed six-digit program counts reconcile; second majors are not added. |
| Yale financial aid, 2014–15 | Explain ambiguity. All-undergraduate grants/scholarships: `UAGRNTN=2869`, `SCUGRAD=5477`, `UAGRNTP=52`. `ANYAIDP=58` applies only to full-time first-time students; never substitute it for all undergraduates. |
| National six-year bachelor's rate | Use matching counts, explicit geography/Title IV scope, reporting-unit handling, and coverage. Exploratory result was about 59.4%; do not use it as a certified exact golden value until missing-count rules are resolved. |
| Financial-aid discovery | Find relevant tables, distinguish grants/loans/any aid and all-undergraduate/first-time populations, and report verified annual coverage. |
| Longitudinal Yale/Ivy export | Annual mappings and periods verified; one observation per institution/period/measure; source versions included; export contains the full result. Numeric expectations await annual import. |
| Financial-aid trend chart | Clarify definition, preserve gaps and definition changes, and match plotted values to the exported table. |

Also test missing years, renamed variables, changed codes, conflicting documentation, unavailable measures, duplicate joins, suppressed values, ambiguous institutions, child reporting, stale cached results, and model/tool failures. Verify table and variable selection as well as final numeric answers.

## 13. Implementation stages

### Stage 1: Inventory and compare sources

- Register annual databases, codebooks, release notes, versions, and hashes.
- Inspect the oldest and newest releases in detail; compare structures and definitions.
- Record absent files, schema differences, and metadata conflicts.

Exit: a reviewed source inventory and explicit importer requirements. No assumption of annual compatibility remains hidden.

### Stage 2: Import data and metadata

- Generalize read-only Access extraction and workbook import.
- Validate counts, types, nulls, identifiers, keys, and metadata/database correspondence.
- Build the release registry and searchable metadata catalog.

Exit: every available supplied release is queryable with import diagnostics and provenance; failures are visible.

### Stage 3: Discovery and reviewed measures

- Implement metadata tools and year coverage checks.
- Create reviewed annual mappings for graduation rates, completions, and aid.
- Resolve zero/missing-count rules and longitudinal differences.

Exit: discovery answers and analysis plans select supported fields and expose ambiguity across years.

### Stage 4: Retrieval, conversation, and exports

- Implement validated plans, query execution, stored results, and follow-up reuse.
- Deliver answers, tables, CSV, and Excel with source disclosures.

Exit: single-year and longitudinal acceptance queries pass; full exports match validated results.

### Stage 5: Charts and aggregation

- Add typed chart generation and chart-adjustment follow-ups.
- Add reviewed aggregate calculations and coverage diagnostics.

Exit: chart values reconcile with tables; aggregates pass independent numerator/denominator and reporting-unit checks.

### Stage 6: Expand and prepare deployment

- Add further domains and exploratory tools based on actual user needs.
- Evaluate hosting/storage, concurrent sessions, budgets, observability, and retention.
- Run regression cases before changing the deployed application.

Exit: agreed release criteria and a reproducible deployment/data-update process.

## 14. Open decisions for review

| Decision | Proposed starting position | Status |
| --- | --- | --- |
| Initial domains | Discover all cataloged subjects; deeply validate graduation, completions, and aid first. | Review |
| Data engine | DuckDB + Parquet; retain original sources and existing SQLite reference. | Review and benchmark |
| Agent framework | Anthropic SDK + Pydantic, small explicit tool loop. | Review |
| Release default | Latest per cycle; final preferred; label provisional. | Review |
| National geography | Default to 50 states + DC; explicitly disclose territories excluded. | Review |
| National institution scope | Propose Title IV for default national reporting; disclose and allow supported alternatives. | Review |
| Ambiguous measures | Ask or present clearly separated alternatives; never silently change population. | Required behavior; UX to refine |
| Missing completion rows | Establish a source-based exact-zero rule before certifying aggregates. | Unresolved |
| Longitudinal institutional changes | Preserve annual identities; define merger/reporting crosswalk rules where needed. | Unresolved |
| Metadata conflicts | Retain conflicting evidence, mark unresolved, and require a supported resolution for affected calculations. | Workflow to implement |
| Hosting and storage | Determine after full source inventory and size/performance assessment. | Unresolved |
| Persistent user history | Begin with session-only context; decide cross-session storage separately. | Review |

## 15. Immediate next action after design review

The user designated `C:\Users\liyuj\OneDrive\2026\IPEDS Project\IPEDS Data` as the source root. The file-presence inventory is recorded in `SOURCE_INVENTORY.md` and `SOURCE_INVENTORY.json` beside this document: ten annual folders, each containing an Access database, Excel codebook, and Word ReadMe. Nine folders are labeled final and 2024–25 is labeled provisional. These labels and file contents still require validation. The earlier paths in this document record the original test locations; resolve ongoing imports against the designated source root.

The all-release documentation/schema comparison is now recorded in `RELEASE_COMPARISON.md`, with detailed evidence in `release-comparison/`. Every codebook sheet and ReadMe was read/extracted, and every Access user-table schema and engine row count was inspected, with up to three sampled records per table. This is not yet a full-record statistical audit or harmonized annual import.

Confirmed importer requirements:

- Preserve CIP 2010 versus CIP 2020 classifications; the switch occurs in the 2020–21 release. Crosswalk program-level trends explicitly.
- Handle 2016 finance/salary changes, 2017 Outcome Measures reorganization, 2020 enrollment/distance/finance changes, 2022 aid/gender/admissions changes, and 2023 high-school enrollment additions.
- Correct documented-to-physical SFA placements for 2023–24 through reviewed overrides. For example, the workbook places UAGRNTP in SFA2223_P2, but the physical field is in sfa2223_p1. Keep both source evidence and correction provenance.
- Map the 2024–25 COST reorganization: tuition/cost fields move to COST1, net price and supporting aid information to COST2, and general aid fields are in SFA2324.
- Preserve inconsistent supplementary sheet names and unknown/absent documentation fields; an EFxxxxCP placeholder in the 2021–22 catalog does not correspond to a physical table.
- Resolve actual field locations and types per release; do not substitute year suffixes blindly or assume all text differences are meaningful definition changes.

Next review the comparison findings, then implement the generalized metadata/data importer and reviewed annual mappings for the tested measures. Full data profiling, semantic crosswalk certification and the national missing-count rule remain outstanding.

Earlier foundation-stage scope (superseded by section 18): implement annual queryable copies and the comprehensive metadata catalog only. At that stage, reviewed mappings and the conversational agent were deferred until the project owner supplied benchmarks. Conversion and metadata integrity checks are infrastructure validation, not substitutes for statistical benchmarks.

Foundation completion: ten independent annual SQLite copies are stored under `data/annual/` (554 user tables; 33,484,311 rows including source metadata). `data/metadata_catalog.sqlite` includes all 58 workbook sheets, 23,990 variable-definition entries, categorical codes, release notes, verified physical schemas and a separate discrepancy register. Full converted-value hashes, column null counts, source-file hashes, exact document-content comparisons and independent row/schema checks passed. See `DATA_FOUNDATION.md`, `data/foundation_verification.json`, and `ingestion/README.md`. No harmonized measure registry or conversational agent was implemented in this stage.

Benchmark update: the project owner supplied five Yale reference CSVs under `Test cases/` and authorized their use for testing. `evaluations/` now contains a read-only, rerunnable data-retrieval regression baseline and generated question fixtures. Initial supported comparisons show real differences in selected enrollment, admissions and SAT observations; these remain failures for reconciliation rather than being adjusted away. The project owner defined URM as excluding White, Asian and international students; treatment of race unknown remains under clarification because the benchmark appears to include it in Non-URM. See `evaluations/YALE_BENCHMARK_REVIEW.md`. This does not claim an implemented or evaluated LLM agent.

## 16. Design references

- Anthropic tool-use lifecycle: https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works
- DuckDB Parquet querying: https://duckdb.org/docs/current/data/parquet/overview
- IPEDS release definitions: https://nces.ed.gov/ipeds/help/complete-data-files

These support technology/release concepts. Annual local codebooks and datasets remain the evidence for actual IPEDS mappings and values.

## 17. Change log

| Date | Change | Decision status |
| --- | --- | --- |
| 2026-10-16 | Initial living design from architecture discussion and 2015–16 discovery/query tests. Recorded limitations of the exploratory national calculation. | Draft for joint review |
| 2026-10-16 | Registered the user-designated `IPEDS Data` source root and completed a file-presence/size inventory of ten annual source folders. | Contents and release labels pending validation |
| 2026-10-16 | Compared all ten codebooks, release notes, and Access schemas to 2015–16 and preceding releases; documented CIP/COST/population changes and metadata conflicts in RELEASE_COMPARISON.md. | Structural review complete; semantic mappings and full-record validation pending |
| 2026-10-16 | Built and verified ten faithful annual SQLite copies and the comprehensive searchable metadata catalog. Preserved source documentation and recorded physical-location issues separately. | Foundation complete; measure validation and agent build deferred pending user benchmarks |
| 2026-10-16 | Registered five user-supplied Yale benchmark files and implemented retrieval comparisons, coverage/unsupported-field classifications, and source-difference reporting. | Benchmark phase started; subgroup definition and source discrepancies unresolved; LLM agent not built |
| 2026-10-16 | User authorized the local small-agent build. Implemented Streamlit conversation/guided analysis, full-codebook discovery, checked annual mappings, deterministic date binding, source disclosure, charts and full exports. | Local prototype implemented; broader analytics and public hosting deferred |
| 2026-10-17 | User requested an explicit deployment TODO for answering unmapped questions through the catalog. Recorded discovery-to-plan validation, execution, evaluation and proposed-mapping reuse in section 19. | TODO; discovery exists, new-measure execution is not implemented |
| 2026-10-17 | Recorded the agreed two-page learning/analysis interface, multi-selection data-extract workflow and post-submission Need ideas behavior in UI_IMPLEMENTATION_PLAN.md. | Documentation only; implementation deferred until additional requests are discussed |
| 2026-10-17 | Owner authorized and completed the combined interface/model build: two main pages, topic examples, same-page chat, extract builder, downloads and Sonnet/Haiku 5.5 adapters. | Local implementation complete; 14 integration checks and 7 live planner cases per model pass |

## 18. Local prototype implementation

The user subsequently authorized building the small agent entirely locally, superseding the earlier foundation-only hold. `prototype/` now implements a working Streamlit application using the existing annual SQLite files and metadata catalog. No cloud data storage is required. Anthropic planning is optional; an offline starter parser and guided controls also work. See `prototype/README.md` for launch instructions.

The runtime registry is `measure-registry/reviewed_measures.json`: 36 implementation-reviewed measures and 340 annual mappings with original definitions, categorical evidence, definition-content hashes and checked physical columns. Implementation review is distinct from owner approval. Unresolved Yale source differences remain visible. This JSON registry implements the persistent-mapping role; the proposed separate registry SQLite database is not required yet.

The model selects a bounded plan and cannot execute SQL. Application code independently binds explicit years (including class-of/fall and entering-cohort/outcome), retrieves and verifies exact annual metadata before querying, compiles trusted mappings and executes read-only queries. Data/methodology/source/codebook sheets accompany Excel downloads; CSV and complete provenance JSON are also available. SAT score chart lines split at the 2017 protocol change. Broad discovery remains open across all imported metadata; unmapped calculations are not automatically promoted to approved plans.

Supported analytics cover admissions/yield, SAT, broad enrollment levels, six-year bachelor graduation overall and selected subgroups, bachelor awards and undergraduate grant aid. National aggregation, custom URM/Non-URM, novel filters/joins and automatic mapping approval remain deferred. The race-unknown rule is unresolved by explicit user choice.

Regression checks preserve all 242 supported Yale comparisons (229 matches, 13 discrepancies), and test source/location checks, unavailable years/fields, institution ambiguity, full exports and Streamlit chart/form execution. Live planner smoke checks and verification reports are recorded under `evaluations/`. This is not a claim of comprehensive LLM reliability, statistically reconciled source differences or production deployment readiness.

## 19. Deployment TODO: answer unmapped questions through catalog discovery

Recorded October 17, 2026 at the project owner's request. **Status: TODO — the current prototype discovers candidate definitions but does not validate and execute newly discovered measures.** Track this explicitly when preparing deployment; cloud hosting alone does not add this capability.

- [ ] For questions without an existing registry mapping, retrieve relevant annual tables, variables, definitions and categorical codes from the catalog.
- [ ] Construct a proposed analytical plan with populations, time basis, filters, joins, formulas, missing-data treatment and source references.
- [ ] Validate the plan against physical schemas, source definitions and cross-year comparability. Ask for clarification or report unsupported scope when material questions remain unresolved.
- [ ] Execute plans that pass validation through bounded read-only tools, check results, and return the requested answer/export/chart with provenance and caveats.
- [ ] Save useful new mappings as proposed entries with supporting evidence and validation findings; apply review rules before promoting them for approved reuse. Do not automatically approve a mapping because a query ran successfully.
- [ ] Evaluate genuinely unmapped questions, including ambiguous populations, changed definitions, unavailable fields, unsafe/invalid plans and longitudinal breaks, before claiming broad question-answering coverage in the deployed app.

This records future work only; it does not authorize starting implementation in this documentation turn. Until implemented and evaluated, deployment descriptions must identify unmapped measures as discovery-only.

## 20. Planned interface iteration — implementation deferred

The project owner requested a written plan before adding other requests and building the combined iteration. See [UI_IMPLEMENTATION_PLAN.md](UI_IMPLEMENTATION_PLAN.md) for the agreed Explore IPEDS landing page, topic detail/example journeys, same-page Ask & Analyze conversation, optional Build a data extract workflow, secondary definition/evaluation tools and acceptance checks.

The latest agreed interaction collapses Need ideas into a reopenable bar below the dialogue/results and above the follow-up input after submission. It preserves the last selected topic and conversation. The extract builder explicitly supports multiple institutions, multiple measures and single/selected/range years, with institution autocomplete and searchable measure selection. CSV/Excel extraction is a primary outcome.

Historical status at recording: implementation was deferred. The owner subsequently authorized the combined build; see section 21. The catalog-to-new-measure workflow in section 19 remains a separate outstanding task.

## 21. Two-page interface and model update implemented

Implemented the owner's combined plan in the local Streamlit prototype. `prototype/ui.py`, `components.py`, `workflows.py` and editable `learning_content.json` provide Explore IPEDS, six topic cards/18 examples, same-page Ask & Analyze, post-submission collapsed/reopenable ideas, institution autocomplete, multiple institution/measure selections, three year-selection modes, data preview/downloads and optional visualization. Definition lookup and evaluation/model settings are secondary tools. The original analytical engine and source mappings remain intact.

Sonnet 5.5 is the default; Haiku 5.5 is selectable. The adapter uses automatic strict tool selection, bounded retries, cached/deduplicated prompt context and local validation. Requests cannot execute without a valid plan. Both models passed seven identical live functional cases. Per-response tokens, latency and estimated API cost are recorded in results; observed costs from this small evaluation are not production guarantees.

All 14 integration checks pass, including every supported Yale gold comparison (229 matches, 13 retained discrepancies), all 18 learning examples, navigation/state preservation, ambiguous institution selection, multiple measures/year modes, extract/chart/export consistency, codebook submissions and no-plan model retries. Cloud deployment, national aggregation, custom URM and new-measure execution remain separate work. See `prototype/README.md` and `evaluations/prototype_model_comparison.json`.

## October 19 scope clarification for analytical expansion

The project owner defines all IPEDS data as all data and codebooks in the local IPEDS Data folder. See [ANALYTICAL_COVERAGE_SCOPE.md](ANALYTICAL_COVERAGE_SCOPE.md) for the agreed boundary, source inventory, loaded-versus-supported distinction and current verification. The current 36-measure restriction remains until expanded capabilities are implemented and validated.

## October 19 analytical catalog preparation

Implemented a derived read-only analytical metadata layer across the complete supplied inventory. See [ANALYTICAL_CATALOG.md](ANALYTICAL_CATALOG.md) for scope, validation and review limits. `prototype.catalog.analytical_context` exposes table/field/period/population/key/category/history evidence. Catalog-to-new-plan execution in section 19 remains the next stage; metadata preparation does not lift the existing measure allowlist.

## October 19 catalog planning implementation — step 3

Implemented [catalog-driven proposed planning](prototype/CATALOG_PLANNING.md) beyond the fixed measure vocabulary, while retaining reviewed numerical execution. Source discovery/typed plans/structural metadata validation and separate proposal persistence now exist. Numerical execution of unfamiliar plans, semantic validation, promotion rules and broad live-model evaluation in section 19 remain outstanding. Verification: 18 planner tests plus 20 existing regressions passed, using mocked model transport. No new owner methodology decision was required.


## Step 4 execution update — October 19, 2026

Catalog-discovered direct numerical observations now pass through prototype/catalog_execution.py before publication. The source-bound typed planner remains separate from the reviewed-measure route; dynamic result specs feed charts, tables and all exports. Documented composite-key equality selectors, runtime cardinality, source time periods, quoted identifiers/bound parameters, read-only connections and numeric missingness are enforced. Race/ethnicity category shares use a reviewed source partition/total relationship; arbitrary formulas, groups, range filters and fact joins remain unapproved. See prototype/CATALOG_EXECUTION.md for exact boundaries.

Live provider testing repaired compiled strict grammar size rejection (strict metadata tools; full mandatory local plan validation) and case-insensitive physical/codebook table lookup. 57 regression tests passed, with per-case timings in evaluations/catalog_execution_verification.json. Three final live unfamiliar questions answered in 8.01–11.95 seconds (median 10.49); full timing and limits in evaluations/catalog_latency.json. This supersedes earlier proposal-only status and does not imply complete all-IPEDS analytical coverage. No owner input currently blocks implemented direct lookups; future concrete methodological ambiguities must be raised explicitly.


## General source-backed calculations — latest October 19 update

The catalog executor no longer enumerates enrollment numerical field names to approve percentages. prototype/field_semantics.py derives source-grounded units, measure identity, category dimensions, period qualifiers and additivity, then proves same-row category/total or explicit source-component relationships. It also supports compatible sibling ratios, disjoint category sums and category differences; unweighted/weighted means, arbitrary joins, row aggregates and unresolved meanings remain unapproved. Descriptions for all 23,990 definitions are materialized by analysis_catalog/semantics.py; unknowns and source identity remain explicit, and runtime re-derives current evidence. No case file is required to execute an eligible new relationship.

Typed plan normalization repairs representational issues without weakening scope. The model receives deterministic preflight feedback and metadata evidence, can inspect and repair twice, and retains existing global call/tool bounds. Only deterministic validation can approve numerical execution. Exports retain structured proofs and canonical formulas, with nested values serialized safely for spreadsheets. General calculation tests, live independent-SQL comparisons, per-case latency, and an additional UI render/export check passed. See prototype/GENERAL_CALCULATIONS.md for exact coverage, 77-test accounting, latency and remaining boundaries. No owner input currently blocks this functionality.

## Relational engine completion — latest October 19 update

prototype/query_schema.py and query_engine.py implement version-2 source relations, explicit-domain grouping/aggregates, fact joins with observed cardinality, weighted means, typed acyclic multi-step calculations, signed financial values and source/cohort period validation. Catalog tools can inspect and repair these plans; agent execution, summaries, grouped charts/tables and downloads are integrated. This supersedes the earlier same-row-only execution boundary. See prototype/QUERY_ENGINE.md for acceptance criteria, limits, reports and owner-input rules. No blanket approval of every IPEDS interpretation is implied.

## Shared session conversation memory

prototype/memory.py supplies a bounded recent transcript and active analytical plan across both planner routes. A semantic resolver produces a standalone request or clarification before routing; existing validators recheck data. ContextVar state is cleared after each request. UI retains 30 turns, exposes New conversation clearing, and documents provider payload. No cross-session persistence or source-audit recall. See prototype/CONVERSATION_MEMORY.md for limits, tests and measured latency.

