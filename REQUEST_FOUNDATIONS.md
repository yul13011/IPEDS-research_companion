# Conversational request foundations

Implemented October 26, 2026 in the redesigned prototype. The original graduation-rate prototype is unchanged.

## Beginner orientation

[The data guide](data/DATA_GUIDE.md) describes twelve subject areas in everyday language, with example questions and supporting codebook references. Its companion `data/data_guide_index.json` retains the underlying table descriptions. The interpreter receives a compact topic index; the guide executor retrieves matching sections without another model call. General orientation does not require a survey name or an exact variable.

The guide combines reviewed editorial explanations with local table documentation. Only documented tables present in the loaded annual databases are included. A source fingerprint refreshes the in-memory guide when the metadata catalog, annual files or guide definitions change. Rebuild the portable documents with `python -B -m prototype.data_guide` from this directory. Changes to the meaning of new surveys still require editorial review.

## Exact availability

`prototype/coverage.py` is shared by availability checks, year lists and latest-available dependencies. Answers distinguish source releases, fall observations, entering cohorts and nominal graduation classes. A failed request for Fall 2025 does not filter the subsequent list of available years.

For reviewed measures, the service verifies annual mappings, physical columns and, when institutions are specified, reported values. Catalog-field coverage verifies physical field presence and source period labels; it does not certify institutional reporting, selectors or comparability. A bounded search without a match is inconclusive, never evidence that IPEDS lacks the topic.

General year questions return the loaded source releases. A topic-guide follow-up can list component release years, explicitly qualified as source coverage. Exact observation years require a bound measure or field. The guide never turns a component-wide release range into a guarantee about every variable.

## Working analysis

`prototype/working_analysis.py` stores the discussion subject separately from the latest verified result. Scope includes institutions, periods, population selectors, source quantities and the executed plan. Definitions and coverage can change the discussion subject while retaining the chart artifact. Unsupported charts and failed requests do not replace verified results.

The interpreter declares requested scope changes. Executors check unchanged institutions, periods, population selectors and output quantity lineage. Explicit references bind to a verified result ID; history trimming rebases its UI turn. These checks reduce silent scope changes but do not prove arbitrary natural-language interpretations correct.

## Multiple questions

`prototype/request_tasks.py` validates a single Claude interpretation into at most six tasks. Each task retains its literal prompt span, standalone meaning, dependencies and subject binding. Validation rejects omitted meaningful prompt text, invalid references and forward dependencies before execution. This structural check cannot establish that every interpretation is semantically correct.

Every part receives a status: answered, unavailable, unsupported, needs clarification, blocked or failed. Independent tasks continue when another cannot finish. Latest-available analysis consumes coverage facts instead of guessing a year. Supported percentage calculations can complete alongside an unsupported chart request. The UI displays each task and its result; unresolved task descriptions remain in conversation state for clarification.

Supported charts remain line and standard bar charts. These changes do not add 100% stacked bars or expand the validated calculation language.

## Verification

`prototype/tests/test_request_tasks.py` exercises coverage, references, dependency execution, population preservation, output lineage and Streamlit rendering. `prototype/tests/test_data_guide.py` checks source-backed orientation, topic retrieval and qualified year answers. `evaluations/verify_request_foundations.py --live` runs bounded real-model conversational cases and saves provider usage and outcomes in `evaluations/request_foundations_live.json`. Earlier failed trials are retained separately; a passing small suite is not a production reliability estimate.

Final October 26 acceptance run: 11/11 live cases passed, at $0.2618 estimated provider cost. The preceding guide/alias trial passed 9/11; its blocked institution comparison and dependent scope failure are preserved in `evaluations/request_foundations_confirmed_alias_trial.json`. A separate regression run covered 179 tests; two test-fixture issues were corrected and all 28 tests in the affected modules passed on rerun. Details: `evaluations/request_foundations_regressions.json`.

## Running-app correction, October 26

A user received the former bounded discovery answer to “Which years do you have?”. The local process on port 8516 had started October 25 with `--server.fileWatcherType none`, before these foundations were implemented. File-based acceptance tests exercised current code, but that existing process retained imported modules. It was restarted with polling and run-on-save enabled, excluding `data`, `.packages` and `evaluations` from watching. A healthy local endpoint alone verifies server readiness, not an individual model response.

The interpreter's older base instructions also still directed broad information questions toward discovery. They now agree with the request-plan instructions: orientation uses the guide, year/availability questions use coverage, and detailed field/table searches use discovery. Year enumeration following legacy discovery uses qualified component/global release inventory instead of running another keyword search. Empty-topic discovery falls back to the guide.

Coverage validation rejects silently clearing a bound measure for a global year inventory unless the interpretation declares the explicit scope change. Automatic mode can retry this rejected interpretation once with Sonnet before any executor runs. This structural check does not prove semantic interpretation universally correct. `evaluations/verify_year_routing.py --live` checks fresh, guide, legacy-discovery and exact-measure contexts, plus explicit whole-database switching and controls for detailed metadata and definitions. The initial 8/9 trial, including a dropped SAT context, is retained as `evaluations/year_routing_scope_trial.json`.

Final year-routing verification: 55 focused regression tests passed; 10/10 live routing cases passed at $0.0567 estimated provider cost. Full records: `evaluations/year_routing_live.json`; operational verification: `evaluations/year_routing_verification.json`.
