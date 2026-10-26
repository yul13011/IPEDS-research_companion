# Local IPEDS Research Companion

**October 25 completed model qualification:** Automatic is the default for new sessions: Haiku interpretation/reviewed planning, Sonnet catalog planning/writing, and one bounded interpretation retry. It saved about 33% in the paired workload. Existing manual selections are preserved. The school name/ID annotation repair passed 4/4 affected live checks per strategy. See [MODEL_QUALIFICATION.md](../MODEL_QUALIFICATION.md) for completed results, timing tradeoffs, validation and limitations; [MODEL_RELIABILITY.md](../MODEL_RELIABILITY.md) retains the implementation history.

**Latency review:** Downloads are generated on click, chart context avoids full rendering, initial interpretation supplies institution mentions, repeated discovery passages are shared losslessly, and API clients/connections are reused. See [LATENCY_REVIEW.md](../LATENCY_REVIEW.md) for measurements and remaining limitations.

**October 23 routing update:** In conversational AI mode, every typed prompt now reaches Claude's intent interpreter with relevant conversation/chart context before a validated executor is selected. Chart edits use typed settings rather than local wording rules. Offline mode retains its labeled starter parser. See [INTENT_ROUTING.md](../INTENT_ROUTING.md) for implementation, live validation, and limits.

Current implementation status and remaining work: [IMPLEMENTATION_CHECKLIST.md](../IMPLEMENTATION_CHECKLIST.md). Analytical expansion steps 1–4, session memory and institution confirmation are implemented. Older milestone notes below are historical checkpoints.

**October 17 interface update implemented:** The app now opens on **Explore IPEDS**, with **Ask & Analyze** as the second main page. The agreed design is recorded in [UI_IMPLEMENTATION_PLAN.md](../UI_IMPLEMENTATION_PLAN.md).

Progress and resumption notes: [October 18 handoff](../PROGRESS_2026-10-18.md).

October 19 analytical expansion: [full-catalog evidence layer](../ANALYTICAL_CATALOG.md) is implemented for future planning. Statistical execution remains limited to the existing reviewed measures.

October 19 step 3: [catalog-driven planning](CATALOG_PLANNING.md) now handles questions outside the reviewed-measure list. It prepares source-backed proposals using the full catalog; numerical execution of these new plans remains step 4. Reviewed statistical answers keep their existing route. This supersedes older discovery-only descriptions below.

## Current interface

Analysis Tools defaults to an “Under development” notice with its unfinished controls hidden. To resume development or testing, open **About this prototype → Developer settings → Enable development mode**. The switch lasts for the browser session and preserves the existing tool implementations and conversation. Turn it off to restore the normal panel.

October 18: Statistical chatbot answers use three primary controls: Display table, Definitions & sources, and a Download Data menu (Excel + sources, CSV, technical audit JSON). Counts/status are optional within the table view. Query plans, SQL, separate extract layouts, selection-edit buttons and model diagnostics are omitted from chatbot answers; full provenance remains downloadable. Important caveats stay visible.

Response behavior is documented in [RESPONSE_RULES.md](RESPONSE_RULES.md): concise source-bound answers, chart/table defaults, selective follow-up context, missing-data semantics and presentation-only edits that reuse results.

- The header uses tab-style navigation for Explore IPEDS and Ask & Analyze.
- Ask & Analyze uses nearly the full browser width with small side margins. Need ideas is a left panel and analysis tools are a right panel, both open by default. Labeled Collapse/Show controls independently hide or reopen each panel; the conversation expands into the available width. Explore IPEDS retains its card-grid width.
- Explore IPEDS has six topic cards, one topic-detail panel immediately below the selected card's row, a Close control and 18 examples. Example rows have muted category labels beside left-aligned clickable questions. Statistical examples execute predefined validated plans without an LLM call; discovery examples remain definition-only.
- Ask & Analyze answers in a bounded, automatically scrolling conversation area. New exchanges appear at the bottom; users can scroll up to earlier exchanges while the follow-up input stays below the transcript. Side panels retain their open/closed state after submission, and Need ideas retains its selected topic when hidden.
- Before the first question, the same conversation area is empty with a chat composer at its bottom. The center has extra width relative to the side panels; there is no separate initial question form.
- Build a data extract opens a spacious four-step workspace: Institutions, Measures, Years, Preview & download. Institution autocomplete shows location/UNITID, allows multiple explicit selections and supports an editable Ivy League group. Measure search retains a selection basket across queries. Years support one, selected or range modes with explicit time meaning.
- Preview/download uses the same validated engine as chat. Full long-format CSV/Excel/provenance exports are retained. Compatible measures also offer a one-row-per-institution/year CSV with status columns. Visualization is optional.
- Browse definitions is a secondary tool. About this prototype contains evaluation/coverage and model settings. Page/tool navigation preserves in-session conversation and selections.

## Models and cost controls

Default: **Sonnet 5.5** (`claude-sonnet-5-5`). Optional: **Haiku 5.5** (`claude-haiku-5-5`), selectable in About this prototype → Model settings. Both are explicitly available; there is no automatic model downgrade or untested automatic routing.

The planner uses automatic strict tool selection, local schema/plan validation and at most two calls when no plan is returned. Strict-tool transport omits unsupported array bounds, while application validation retains the bounds. Sonnet uses between-tools thinking at medium effort; Haiku uses adaptive thinking at low effort. Static instructions/measure descriptions are cached, family definitions are deduplicated, and retrieved metadata is bounded. Successful responses show token usage, latency and estimated standard API cost. Access depends on the configured API account.

Seven live cases per model passed: admissions dates/counts, contextual yield, faculty discovery, ambiguous aid, graduation cohorts, multiple institutions/years and aid reporting periods. For this small cached sample, estimated total token costs were approximately $0.107 for Sonnet and $0.0066 for Haiku; this is not a forecast of production costs or a broad accuracy estimate. Source: `evaluations/prototype_model_comparison.json`. Rerun with `python prototype/tests/compare_models.py` (normal API charges apply).

Migration references: [Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide), [Haiku 5.5](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide), [pricing](https://platform.claude.com/docs/en/about-claude/pricing).

The earlier sections below describe the original prototype foundation; their former four-tab layout is superseded by this update. `app.py` is the entry point, `ui.py` renders the workspace, `components.py` renders evidence/results and `workflows.py` implements reusable learning/extract helpers. `learning_content.json` holds topic descriptions and example plans.

Working local Streamlit prototype over ten verified annual SQLite copies and their codebook catalog. No Supabase, R2, or cloud database is required. Original sources and Yale reference CSVs are unchanged.

## Open on this computer

```powershell
Set-Location 'C:\Users\liyuj\OneDrive\2026\IPEDS Project\agent-redesign'
.\prototype\run.ps1
```

Open http://127.0.0.1:8516. Leave the terminal running; Ctrl+C stops it. The launcher uses the project's `.venv` if present, otherwise this computer's bundled Python and project-local `.packages`. The server listens locally only.

For another computer with Python 3.11+, prepare the annual data/catalog at the same project-relative locations, then:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r prototype/requirements.txt
.\.venv\Scripts\python.exe -m prototype.build_registry
.\prototype\run.ps1
```

## Try these questions

- What data do we have on faculty?
- Yale applicants, admits and admission rate for class of 2028 entering fall 2024
- How many matriculated in that year and what was the yield rate?
- Plot Yale six-year graduation rate from 2015 through 2024
- Compare Yale and other Ivy League universities' six-year graduation rates in 2015
- How many bachelor's degrees did Yale award in 2015?
- Plot Yale undergraduates receiving grants/scholarships from 2015 through 2024

The tabs offer conversation, guided analysis, source-codebook search and evaluation status. Guided analysis accepts institution names or UNITIDs separated by semicolons, plus an Ivy League alias. Each name is resolved in each year's HD table; ambiguous names require clarification.

### Explore codebooks: definition lookup

This tab searches source documentation, not institution statistics. Enter a topic (for example `financial aid`), a table (`ADM2024`), or a variable (`APPLCN`); choose release years and click **Search codebooks**. It defaults to table/variable definitions. An optional checkbox also searches coded categories and release documentation. Exact table/variable identifiers are ranked first. Results are a bounded ranked list, not an exhaustive inventory.

Choose **Read a definition** to see the full variable description, coded-category meanings where applicable, physical-location status and documentation issues. **Original source reference** shows the workbook/sheet/row and record ID. To retrieve Yale or other institution values, use **Ask a question** or **Guided analysis** instead. No API key is required for this lookup.

October 17 fix: search results use a separate session-state key from the form, resolving the reported `StreamlitWidgetAlreadyInstantiatedError`. Submission, repeated queries/year changes, no-result and blank searches are covered by an integration test. This technical lookup remains separate from the proposed topic-card landing page.

Conversational AI uses `ANTHROPIC_API_KEY` in the environment or a top-level entry in `agent-redesign/.streamlit/secrets.toml` or the existing parent project's secrets file. Keys are never displayed or copied into code. The model name is configurable. AI sends the question, previous structured plan and bounded codebook excerpts to Anthropic, incurring normal API charges. Statistical queries/calculations and exports run locally. Without AI, a limited starter parser, guided analysis and source search work offline.

## Scope and operation

The runtime registry, `../measure-registry/reviewed_measures.json`, contains **36 implementation-reviewed measures / 340 explicit annual mappings**: admissions/yield, SAT scores and participation, fall enrollment by broad level, six-year bachelor graduation counts/rates overall and selected subgroups, bachelor awards and all-undergraduate grants/scholarships percentage. Each mapping includes annual codebook IDs, categorical labels and physical column locations. Reviewed SFA location corrections preserve the original documentation. New concepts remain discovery-only until reviewed; this is not an all-variable query engine yet.

The model selects a bounded typed plan; it cannot execute SQL. Application code binds explicit dates, validates the plan against codebook and physical metadata, compiles trusted mapping expressions and uses read-only SQLite with bound institution parameters. Duplicate records, missing fields and invalid values are checked; missing/not-collected observations never become zero. Query time and request size are bounded (30 institutions, 12 measures and 10 years).

Results include interpretation, definitions, tables/variables, SQL and workbook/sheet/row references. Downloads contain the complete data: Excel with methodology/sources/codebook sheets, CSV, and full provenance JSON. Charts preserve missing observations and split SAT score series at the 2017 protocol change. Latest data are labeled provisional. In-session follow-ups reuse the preceding plan. The last eight conversation results are retained; there is no automatic cross-session memory or mapping promotion.

## Limits retained from evaluation

- Mapping review is implementation/source review, not project-owner approval or certification of agreement with every Yale reference value. All 13 known differences remain discrepancies and appear in affected answers.
- National/state/sector population queries use the general typed engine with explicit geography, control, level, reporting-unit and missing-pair rules. Known NCES discrepancies remain blocked; see POPULATION_AGGREGATES.md. Custom URM/Non-URM is blocked while race-unknown placement remains unresolved.
- Observation years are 2015–2024. Graduation entering cohorts are 2009–2018. SAT medians start in 2022; 10th/90th percentiles and graduate admissions are unsupported.
- Codebook search returns ranked excerpts, not an exhaustive inventory. Yale SAT score-selection comparability remains unresolved. Grant-aid trends have no supplied longitudinal benchmark.
- Guided analysis only supports mapped measures; broader language/filter interpretation needs more adversarial/paraphrase evaluation. This app has not been load-tested for public hosting. Provenance downloads include local source paths.

## Verification

On this computer, from `agent-redesign`:

```powershell
& 'C:\Users\liyuj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' prototype/tests/test_prototype.py
# Optional: five live API requests with the existing local credential
& 'C:\Users\liyuj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' prototype/tests/live_smoke.py
```

The deterministic regression reproduces **229 matches and 13 mismatches across all 242 supported Yale numeric comparisons**, without editing expectations. A passing regression preserves that evidence; it does not resolve the mismatches. Tests also cover dates, missing fields, read-only connections, institution resolution, complete exports and Streamlit forms/chart rendering. Reports are `../evaluations/prototype_verification.json` and `../evaluations/prototype_live_smoke.json`. Live smoke checks are not a broad reliability estimate.

## Files

| File | Role |
| --- | --- |
| `app.py` | Streamlit interface and session state |
| `agent.py` | Anthropic adapter, starter parser, deterministic date binding |
| `catalog.py` | Read-only search, source evidence and institution resolution |
| `build_registry.py` | Rebuild explicit annual mappings from source metadata |
| `analytics.py` | Validate plans, compile queries, calculate and retain provenance |
| `exports.py` | Full data and audit exports |
| `tests/` | Real-data regressions, UI checks and optional live smoke checks |

Next review real user questions in the running prototype and expand language/ambiguity tests before novel-measure SQL, national aggregation or public deployment.

## Deployment TODO: catalog workflow for unmapped questions

Recorded October 17, 2026. Discovery is implemented; answering newly discovered measures is still TODO. Extend the workflow from catalog search to a proposed analysis plan, validate definitions/physical availability/comparability, execute passing plans read-only, and return results with provenance. Save new mappings as proposals for review and future reuse. Evaluate unmapped-question scenarios before advertising broad analytical coverage. Full checklist: `../AGENT_ARCHITECTURE.md`, section 19. No implementation change is included in this TODO entry.

Definitions & sources and Download Data appear as adjacent buttons on one row.

October 18 height update: Ask & Analyze uses available viewport height on desktop, with a flexible scrolling transcript and a composer outside it. Side panels scroll independently. Narrow screens use a viewport-relative chat height; very short desktop windows retain a minimum usable page height with page scrolling. Refresh after restarting the server.

October 18: Ask & Analyze offers Hide introduction / Show introduction to collapse or restore the main heading and explanatory text. The choice persists within the session across questions and navigation; the conversation uses the recovered height. Narrow-screen chat sizing also accounts for the collapsed introduction.


General source-backed calculations are implemented beyond the original reviewed-measure list. See [GENERAL_CALCULATIONS.md](GENERAL_CALCULATIONS.md) for source semantics, eligible arithmetic, bounded planner repair, evaluation/latency evidence and remaining limits. A matching question in Test cases is not required.

October 26: [Conversational request foundations](../REQUEST_FOUNDATIONS.md) add shared source coverage, explicit working-analysis scope and tracked multi-part requests. [What information is available?](../data/DATA_GUIDE.md) is the searchable beginner guide generated from local codebook documentation.

