# Full-catalog analytical preparation — October 19, 2026

## Implemented

The derived analytical catalog covers the complete agreed source inventory. Original Access data, annual SQLite copies, metadata, and the reviewed measure registry are preserved.

- All 554 annual physical tables and 25,245 physical fields are inventoried, with exact definition links or explicit missing/conflicting-definition states.
- All 23,990 variable-definition records remain accessible, including definitions without a column at the documented location.
- All 124,493 original category-code records are available through paginated source-backed lookups.
- Source evidence includes file/hash, sheet/row, population descriptions, reporting periods, data types, null counts and imputation references.
- Institution-level and repeated-row tables are profiled. Observed unique keys and unresolved/semantic-review states are recorded.
- Same-release directory joins have explicit cardinality and unmatched-ID checks; automatic fact-to-fact joins are not permitted.
- Cross-year candidate histories track availability, definitions, code labels and location changes without claiming automatic equivalence.
- Missing/not-applicable/imputation/revision guidance is linked to the original release documentation.
- A read-only API and prototype catalog entry point expose the evidence for the next planner stage.

## Important limits found

The inventory contains **505 institution-data tables and 49 source-metadata tables**, not 554 independent statistical tables. Physical field definitions can be absent, placed in a conflicting table, or incomplete; these are review states, not guessed mappings.

The extracts omit item-level imputation flags, as explicitly documented in their release notes. The catalog records 14,817 field-to-flag references whose flags are absent from the supplied physical schemas. It cannot infer whether individual values were reported or imputed.

Units/scale and population/period interpretation are sourced from the definitions; automated unit/time hints are retrieval aids, not approved analytical semantics. Unique keys do not authorize summing subtotals, national aggregates or joining fact tables. Cross-year field matching does not authorize longitudinal harmonization.

## Verification and review

Current results: [analysis_catalog_verification.json](data/analysis_catalog_verification.json).

- [Table coverage and grain inventory](data/analysis_table_coverage.csv)
- [Definition/location/grain review queue](data/analysis_catalog_review_queue.csv)
- [Directory relationship coverage and unmatched IDs](data/analysis_relationship_coverage.csv)
- [Example field evidence packet](data/analysis_field_example.json)

Eleven new integration tests passed, covering definitions, code pagination, unknown-race semantics, key evidence, source conflicts, cross-year change detection, join boundaries, read-only access and planner integration. Existing codebook-definition checks and the entire supported numerical benchmark regression also passed. The benchmark retains its existing 229 matches / 13 mismatches; those discrepancies are not resolved by metadata preparation.

See [analysis_catalog/README.md](analysis_catalog/README.md) for rebuild commands, API functions, methods and limits.

## What this enables next

The catalog is now available as structured evidence for step 3: a planner that discovers an unfamiliar measure and constructs a validated analytical plan. The chatbot remains restricted to its existing 36 reviewed measures until that planner/validator/compiler work is implemented. Semantic gaps must be resolved or surfaced for each proposed plan; the review queue is not a blanket approval list.

Final catalog validation: 22/22 checks passed; 11 integration tests passed. All 505 institution-data tables have observed unique keys (303 UNITID keys; 202 composite candidates requiring semantic review). All 49 source-metadata tables are classified separately. Four directory relationships retain unmatched-ID review status. See the verification report for definition gaps and flag availability.


Latest analytical meaning layer: analysis_catalog/semantics.py materializes source-backed descriptions for all 23,990 variable definitions in data/field_semantics.sqlite. Recognized units: 14,794; unknown: 9,196 (including coded/non-quantitative fields). Descriptions are not execution approvals. Runtime source-based calculation validation, normalization and bounded repair are documented in prototype/GENERAL_CALCULATIONS.md.
