# Analytical catalog layer

This is step 2 of the analytical expansion: prepare the entire supplied catalog for evidence-backed planning. It does **not** remove the prototype's 36-measure execution restriction. Discovery-to-plan execution is the next stage.

## Scope and source preservation

The source boundary is [ANALYTICAL_COVERAGE_SCOPE.md](../ANALYTICAL_COVERAGE_SCOPE.md): the ten releases, databases and codebooks in the project's `IPEDS Data` folder. Source Access files, annual SQLite copies, original metadata and reviewed measures are opened read-only. Generated artifacts live separately under `data/`.

- `analysis_catalog.sqlite`: derived analytical metadata and profiling results.
- `analysis_catalog_verification.json`: current validation results and coverage counts.
- `analysis_table_coverage.csv`: one row per physical annual table, including metadata tables, population/period source references and observed key status.
- `analysis_catalog_review_queue.csv`: unresolved field definitions, location conflicts and multi-row grain review.
- `analysis_relationship_coverage.csv`: same-release directory joins, cardinalities and unmatched-ID review status.
- `analysis_field_example.json`: complete evidence packet for the 2024 Asian enrollment field, without answering an institution-level statistical question.

## What is connected

Every physical column has a record with its type, null count, exact definition references if present, alternative definitions where locations conflict, source issues and semantic review status. Every variable definition is retained, including definitions without a physical field. Source code sets are available with pagination and their original labels; no code is converted to a guessed meaning.

Field and table evidence packets include workbook/file hash, sheet and row, table reporting periods, descriptions of populations, coded selectors, imputation-variable references and physical availability. Unit hints help retrieval but are explicitly **not validated units**. The original definitions remain authoritative for scale, denominator, currency precision, subpopulations and periods specific to individual columns.

Release-year labels are not substituted for observation/cohort/fiscal years. Multi-period fields (for example prior-year cost and financial-aid columns) require their variable definitions, even when the table has one overall year-coverage label.

## Grain and joins

Institution data are separated from source metadata tables. All tables containing UNITID are profiled for row count, distinct institutions and null identifiers. UNITID is marked an observed institution key only when unique and nonnull across the full table. Repeated-row tables are checked against bounded code-defined key candidates (enrollment level, program/award level and similar selectors). Candidate key uniqueness is empirical evidence, **not proof of a minimal semantic key or permission to aggregate**. Every unresolved candidate remains visible in the review queue.

Prepared relationships are limited to a same-release LEFT JOIN from a data table to the directory table `HD{year}` on UNITID. The directory key is checked for uniqueness, and unmatched institution IDs are counted. Such a join is for institution attributes only. It does not authorize fact-to-fact joins, branch consolidation, national aggregation, cross-year institution matching, or summing subtotal rows. Relationships with unmatched IDs are explicitly marked for review; source rows must never disappear through an implicit inner join.

## Missing values and imputation

SQL NULL stays NULL. There is no universal negative-code decoder or zero substitution. Source category labels and release guidance are preserved for inspection; unknown race is a reporting category, not automatically a missing numeric value. A numeric value alone cannot establish suppression, noncollection, not-applicable or imputation status.

The supplied Access release notes explicitly state that item-level imputation flags are omitted. The catalog records the referenced flag names and their absence from the physical schema. This gap cannot be filled by pretending values are reported or by inventing flags. Adding files from outside the agreed folder would require a separate source-scope decision.

## Cross-year changes

Table-family/name matches provide candidate field histories across all ten releases. History includes availability, original definition fingerprints, conservative normalized-definition comparisons, code/label changes, physical-location changes, release gaps and ambiguous matches. Category frequencies are excluded from code-definition fingerprints: a changing frequency is not a changing definition.

Names and family normalization are retrieval aids. Identical names or no detected change are **not** harmonization approval. Renamed variables, CIP revisions, changing populations and accounting frameworks require reviewed crosswalks. Original definitions and category records are never overwritten.

## Read-only API and prototype entry point

`catalog.py` provides:

- `search(query, release=None, limit=20)` — source discovery with physical availability.
- `table_context(release, table)` — table grain, time/population evidence, fields, relationships and warnings.
- `field_context(release, table, column)` — exact/candidate definitions, code page, flag availability, unit hints and table evidence.
- `documented_field(release, table, variable)` — definitions even when no column exists there.
- `categories(..., offset=0, limit=100)` — paginated source categories, maximum 250 per page.
- `field_history(release, table, variable)` — availability and candidate change evidence.
- `convention_evidence(release, topic)` — source-level imputation, missing/not-applicable and revision guidance.

The prototype exposes `prototype.catalog.analytical_context(release, table, variable=None)` for the next planner stage. Existing answer planning and approved numerical execution remain unchanged. Source-catalog identity is checked before evidence is served; rebuilding either catalog invalidates the cached identity check.

## Rebuild and validation

From `agent-redesign`, using the bundled Python:

```powershell
& 'C:/Users/liyuj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m analysis_catalog.build
& 'C:/Users/liyuj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m analysis_catalog.verify
& 'C:/Users/liyuj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m unittest analysis_catalog.test_catalog -v
```

Build creates a temporary derived database and publishes it atomically after integrity and foreign-key checks. An interrupted build leaves `analysis_catalog.building.sqlite`; inspect and remove only that generated temporary file before retrying. Source files are never replaced.

`python -m analysis_catalog.refine_grains` retries unresolved key checks with an extended bounded query budget and documented comparison-institution/campus identifier candidates. It updates only the derived catalog. Run verification again afterward to refresh the inventories. Keys that become empirically unique still require semantic review.

For a CLI evidence packet:

```powershell
python -m analysis_catalog.catalog --release IPEDS_2024-25_Provisional --table EF2024A --field EFASIAT
```

## Remaining review versus next-stage implementation

This layer makes evidence and uncertainty machine-readable across the full inventory. It does not claim every field has a complete or unambiguous source definition, every row key is resolved, every unit is canonicalized, or every pair of annual fields is comparable. The verification report and review queue quantify those gaps. Resolving semantics for an intended plan is mandatory before execution; new approvals must retain evidence and validation findings. Broad new-question answering requires the subsequent typed planner, validator and query compiler.
