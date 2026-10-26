# General source-backed calculations

October 21 update: this is a historical milestone. Current national/state/sector population support is documented in [POPULATION_AGGREGATES.md](POPULATION_AGGREGATES.md); the former blanket restriction below is superseded.


Latest October 19 update: relational execution, grouping, weighted analysis, joins and multi-step formulas are documented in [QUERY_ENGINE.md](QUERY_ENGINE.md). Its scope supersedes the earlier same-row-only limits below.

Implemented October 19, 2026. This supersedes the earlier percentage allowlist in `catalog_execution.py`. Numerical answers no longer require an enrollment variable name or a matching example in `Test cases`.

## What changed

| Proposed change | Implementation |
| --- | --- |
| Describe analytical meaning | `field_semantics.py` derives units, category dimensions, measure identity, additivity, source periods, field-specific time qualifiers, population evidence, required row selectors, missingness policy and source references. |
| General validator | Calculation eligibility follows source meanings, compatible scope, and a category/total or explicit source-component relationship. It does not enumerate approved numerical field IDs. |
| Normalize plans | Split ambiguous per-category percentage representations into one numerator per output when that matches the question; collapse identical outputs; remove redundant grouping by an equality-fixed dimension. Preserve actual populations, categories, denominator and requested scope. |
| Check results | Propagate missingness; leave zero-denominator results empty; check share bounds, nonfinite arithmetic, source reconciliation and total/component consistency. Do not assume incomplete category selections sum to 100%. |
| Inspect and repair | The catalog model receives deterministic preflight feedback and source descriptions, can inspect definitions/category codes, and can repair twice within its eight-call/sixteen-tool-request limit. It cannot override validation. |
| Broader evaluation | Cross-survey calculations, held-out institution/year combinations, paraphrases, invalid relationships, repair/rejection, full exports, UI and latency are tested separately from old Yale benchmark cases. |

## Full field catalog

`analysis_catalog/semantics.py` generates `data/field_semantics.sqlite` from the original catalog evidence. It describes all **23,990 variable definitions**:

- 14,768 have a recognized unit in this first parser version.
- 9,222 retain an explicit unknown unit. This includes coded fields and definitions whose quantitative unit the parser cannot establish; it is not a count of unavailable source values.
- Every descriptor has `execution_approved=false`: a description never grants blanket calculation approval.
- Source identity, definition hashes, parser version and source-record references are retained. Original data and codebooks are unchanged.

The generated catalog is an inspectable snapshot. Runtime validation re-derives descriptions from the exact current source definitions and table evidence, so stale or model-supplied descriptions cannot authorize arithmetic. `read_definition` exposes the same descriptions to the planner.

These are conservative source-text parsers, not a claim that every field has been understood or human-reviewed. Recognized units or matching titles alone do not establish calculation eligibility.

## Calculation checks

The existing structural/catalog binder remains mandatory. Numerical fields must exist at their documented physical location, category filters must have exact source code evidence, institutions must resolve, and repeated source tables need all documented key selectors. SQL remains compiled locally with quoted catalog identifiers, bound values, read-only connections and a query deadline.

For arithmetic, the validator also requires:

1. The exact same source release/table and selected institution/population row. No implicit fact joins or cross-row aggregation.
2. Recognized compatible units and additive numerical observations. Rates, medians, averages and FTEs are not automatically treated as additive counts.
3. Compatible source reporting periods and title-specific time qualifiers. Release labels do not replace observation or cohort periods.
4. A supported relationship proven from source category meanings or an explicit component named in the denominator's own sum definition. Convenient numerical values, model labels and model interpretations are not evidence.
5. An operation that the user actually requested. An unqualified breakdown defaults to counts; an unsolicited percentage is returned for re-planning.

Supported generic operations now include:

- **Percentage:** one contained category divided by its matching total, multiplied by 100.
- **Ratio:** a contained category/total, or a comparison of compatible disjoint sibling categories. A sibling ratio can exceed 1; it is not mislabeled as a percentage share.
- **Sum:** proven disjoint source categories of the same measure. A total plus its subtotal is rejected.
- **Difference:** compatible sibling categories or a total minus a contained component. Legitimate calculated category differences can be negative; a component exceeding its total fails validation.

The parser recognizes source category dimensions such as gender, official race/ethnicity, attendance, physical/electronic medium and current/noncurrent classifications across survey components. It retains the rest of each source title as the measure identity: applicants and admissions, for example, cannot become interchangeable merely because both count students.

Gender unknown/another-gender categories can overlap with allocated Men/Women counts, so they are not automatically additive to those counts. No remainder is labeled as unknown or another gender. Existing population-specific source safeguards remain.

Means/weights, arbitrary formulas, multi-stage derived expressions, cross-table/cross-period ratios, grouped row aggregates, national/sector methods, custom URM definitions, signed source financial values and unresolved units still need further semantic support or a concrete methodological decision. This work does not make every IPEDS question executable.

## Repair behavior and audit

On a rejected proposed plan, the model receives the exact deterministic reasons, source field descriptions and calculation findings. It can retrieve more metadata and repair the original request. Two semantic repair attempts are allowed; the original overall request bounds remain. No numerical query runs during repair. Schema, physical-location, row-key and calculation checks are applied again immediately before execution.

The system should ask the owner only for a genuinely missing choice of intent or method. It should not ask the owner to select database columns, approve ordinary formulas, or work around a coding limitation. If source evidence remains insufficient after bounded inspection, the response retains that limitation without publishing numerical results.

Audit files retain field descriptions, calculation proofs, normalization notes, source records, typed calculations, deterministic formula descriptions, repair history, query parameters and timings. Excel and CSV serialize nested calculation evidence as JSON text rather than invalid spreadsheet cells. Chat keeps the existing Display table, Definitions & sources and Download Data controls; no new diagnostic dropdown is introduced.

## Validation and latency

The final combined regression run passed **76 tests**, followed by the newly added full-catalog coverage/no-blanket-approval test, which also passed. The suite now contains **77 tests**. A separate Streamlit AppTest confirmed a generic calculated answer, its two existing popovers and its Excel download, with no exceptions; the measured server rerun was 0.56 seconds, excluding browser paint.

Final live model evaluation, using independent read-only SQL for expected numerators and denominators:

| Unfamiliar question | Numerator / denominator | Answer | Answer ready | Model calls |
| --- | --- | ---: | ---: | ---: |
| Women as share of Yale fall 2024 applicants | 32,540 / 57,517 | 56.57% | 17.05 s | 3 |
| Women as share of Yale bachelor's awards, July 2023–June 2024, first major/all fields | 843 / 1,665 | 50.63% | 17.17 s | 4 |
| Physical collection units as share of Yale total library collection, fiscal 2024 | 9,661,648 / 12,825,381 | 75.33% | 12.61 s | 3 |

All three numerical results and exports passed. Median answer-ready latency was 17.05 seconds, range 12.61–17.17 seconds. Validation took about 0.035–0.053 seconds and query/execution about 0.004–0.007 seconds; most latency was catalog/model planning and first-process initialization. Excel serialization took 0.52 seconds cold and approximately 0.07 seconds warm. These are a small serial sample with possible cache effects, not a latency guarantee; browser transport/paint is excluded.

No semantic repair was necessary in these three final live cases. Controlled mocked-provider tests separately verify a rejected plan, additional source inspection, successful repair, and bounded unresolved rejection. They are not represented as live repair latency measurements.

An earlier run produced correct numerical answers but exposed an Excel serialization failure; that report is retained separately. The export fix has a regression test. Old Yale source discrepancies remain unchanged.

Evidence:

- `data/field_semantics_verification.json`
- `evaluations/catalog_execution_verification.json`
- `evaluations/general_catalog_description_verification.json`
- `evaluations/general_calculation_latency.json`
- `evaluations/general_calculation_latency_before_export_fix.json`
- `evaluations/general_calculation_ui_verification.json`

## Owner input

**No input is required to use the implemented functionality or continue routine development.** Sources, codebooks and credentials already configured for the prototype were sufficient. No additional test-case files or column mappings are needed from the owner.

Ask for input only when a concrete analysis needs an unresolved method, such as defining a custom URM grouping, a reporting unit/geography/missingness policy for an aggregate, or which population the user actually intends. Unrecognized parser wording or a missing implementation is developer work, not an owner methodology decision.

Optional acceptance feedback: try real questions across different topics and provide the exact wording and any mismatch with the intended interpretation. This is useful feedback, not a prerequisite.

## Reproduce

Run from `agent-redesign` using the bundled Python:

```powershell
& 'C:/Users/liyuj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m analysis_catalog.semantics
& 'C:/Users/liyuj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' prototype/tests/verify_catalog_execution.py
& 'C:/Users/liyuj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' prototype/tests/general_calculation_latency.py --live
```

Only the last command makes live provider requests and incurs normal API usage.

