# Shared unit metadata

`unit_metadata.resolve` is the shared quantity resolver. Prepared assignments live
in `data/unit_catalog.sqlite`, keyed by source record and release/table/variable.
Each assignment records a quantity type, unit, status, source excerpts and rule
version. Explicit monetary currency/magnitude evidence is stored separately from
the quantity classification; existing source-backed currency display refinement
in `units.py` still verifies currency/reporting conventions before displaying USD.
No unit lookup calls a model or visits an external source.

Assignments distinguish a quantity from its population: credit hours for students
are hours, salaries per FTE remain monetary, percentile scores are scores, and
students receiving degrees are distinct from degrees awarded. Short academic-rank
labels require the table's explicit staff-count statement; the supplied SISINST
spelling is supported by its variable identity and instructor definition. IDs,
source codes and coordinates are explicitly distinguished from ordinary counts.

Source metadata and numeric observations are never edited. Runtime lookups check
the complete relevant field/population fingerprint and rule version before using a
prepared entry. A mismatch falls back to the same resolver against current evidence;
it does not reuse stale assignments. Cache entries are bounded per record and catalog
file version. Unknowns remain `unknown`; there is no “source units” inference fallback.

`field_semantics.describe_field` retains the existing dimension, population and
period proofs but obtains unit/readiness/additivity from the shared resolver.
Both catalog execution and relational queries consume it. Reviewed measures register
their existing reviewed unit/formula with definition IDs. Derived results retain
validated input unit evidence. Explicit currency/scale incompatibilities block
same-row arithmetic; existing join, overlap and denominator checks remain in force.

Charts and UI suppress measurement axes for unknown, coded and identifier units,
including when a user forces visualization. Values remain available in tables without
the meaningless suffix. Academic-rank totals have a separate chart panel; requested
tables and exports retain them.

Saved direct catalog fields can be reinterpreted for display using their original
source IDs and re-read metadata. Matching direct relational references can also be
revalidated. Values are unchanged and the original unit is preserved in `source_unit`.
Old derived results without unit evidence require a rerun; their display unit becomes
unknown instead of silently endorsing the historical calculation. Audit export restores
the historical row unit while recording the display interpretation separately. CSV,
Excel and chart preparation use the shared presentation copy; new result rows carry
unit evidence directly. Presentation copies are idempotent.

## Preparation and review

Run `python evaluations/prepare_unit_catalog.py` to build a proposed SQLite catalog,
CSV old/proposed-unit audit and JSON summary for all loaded releases. Review unknowns,
changed assignments and cross-year differences. Run with `--activate` to publish the
derived catalog after review. Original source databases are never modified. The frozen
legacy classifier remains only for reproducing audit baselines and non-unit descriptor
extraction; its unit result is overwritten before analytical use.

Current scope: 23,990 documented fields, ten releases, rule version 3. The original
2,484 unresolved entries were processed: 2,459 fixed classifications and 25 with
documented institution-specific unit selectors. There are 30 conditional program-length
fields in the full catalog, including related first-program fields corrected alongside
that batch. `unit_observations.py` reads the same-row selector at presentation time;
clock, credit and contact hours remain separate source categories. Missing basis stays
unresolved and cannot authorize arithmetic. No cross-year harmonization is assumed.
Evidence-based parsing is bounded and is not a claim that every definition has been
independently manually verified. See `evaluations/UNIT_RESOLUTION_REVIEW_ITEMS.md`.
