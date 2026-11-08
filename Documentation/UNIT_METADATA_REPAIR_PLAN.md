# Shared unit metadata repair plan

Recorded October 22, 2026 at the owner's request.

**Status: shared implementation active; broader independent verification remains open.**
The original 2,484-entry unresolved batch has been processed under rule version 3:
2,459 fixed classifications and 25 conditional program units. See
`evaluations/UNIT_RESOLUTION_IMPLEMENTATION_REVIEW.md` and the source terminology
review list. This does not mean every catalog assignment has been manually verified.
National aggregate benchmark reconciliation remains paused.

## Problem and evidence

Unit assignment currently relies on scattered label/description parsers in
`prototype/field_semantics.py` and a fallback in `prototype/catalog_execution.py`.
Reviewed measures have separate mappings; `prototype/units.py` handles monetary
presentation. These paths can disagree or confuse population with quantity.

The actual replay of “show Smith College's Full-time instructional staff by academic
rank” returned seven observations. Six were classified as employees, but SISINST
was unresolved and displayed as “source units.” The supplied title is “Intructors,”
which fails the rank-label spelling pattern. Mixed units suppressed the default
bar chart. The values themselves were not changed by these assignments.

Artifacts: `evaluations/smith_rank_display_trace.json` and `.log`.

A preliminary scan of the 2024 source release classified 2,227 documented numeric
continuous fields; 486 received the generic fallback. This is NOT a count of errors:
the set includes identifiers, coded fields and genuinely unresolved quantities.
Confirmed parser problems include SAT/ACT percentile scores classified as percent
(substring match), undergraduate credit hours classified as students, and unresolved
units for total enrollment and student-to-faculty ratio. This scan is not a complete
audit of all releases or all execution paths.

Artifact: `evaluations/unit_metadata_audit_2024.json` (parser output, not ground truth).

## Design

1. Separate quantity type, population and dimensions. Credit hours for undergraduates
   measure hours; undergraduates describe the population. Numeric storage does not
   imply a measurable quantity: identifiers/codes must be distinguished explicitly.
2. Establish units from explicit codebook evidence, then documented table context,
   then reviewed variable mappings. Resolve contradictions explicitly. Keywords can
   retrieve evidence but must not alone establish a verified unit. Do not simply
   add a spelling exception for SISINST or propagate units to all fields in a table.
3. Build a reusable unit catalog keyed by source release/table/variable identity.
   Store quantity type, canonical unit, currency/scale when applicable, verification
   status, evidence references/passages and derivation/version provenance. Distinguish
   source-reported fields from app-derived results. Define the exact schema during
   implementation and retain unresolved/conflicting states.
4. Make reviewed and catalog-driven execution consume the shared assignments.
   Preserve evidence and original precision/scale through answers, charts, calculations,
   exports and saved-result display. No automatic rescaling of source values.
5. Replace the user-facing “source units” placeholder with honest unresolved handling.
   Avoid meaningless suffixes. Require verified compatible units for arithmetic and
   shared chart axes; explain a relevant limitation instead of inventing a unit.
6. Perform unit preparation during metadata processing, not with a new model request
   for every question. Normal questions should incur no additional model call for
   unit lookup. Use only owner-supplied sources; assess any existing reporting rules
   against that policy rather than introducing new external evidence.

## Delivery stages

### Stage 1 — catalog proposal and audit; no answer changes

- Inventory every unit-producing/consuming path, including reviewed mappings,
  calculation results, charts, summaries, table suffixes and CSV/Excel/audit exports.
- Build proposed assignments alongside existing behavior across all ten loaded
  releases (2015–2024 source years).
- Produce an inspectable report of old/proposed units, evidence and verification
  status. Flag unknowns, incompatible assignments within related fields, conflicting
  evidence and cross-year changes. Do not assume definitions are stable across years.
- Separate confirmed errors from unresolved cases and fields needing no measurement
  unit. Review ambiguous groups before assigning verification.

### Stage 2 — integration and verification

- Apply verified assignments through the shared system; retain explicit unresolved
  states for remaining fields. Remove or constrain conflicting legacy inference.
- Revalidate unit-dependent calculations; do not silently loosen compatibility or
  additivity safeguards to make a chart or calculation pass.
- Handle existing saved answers deliberately: do not retain incorrect units or mutate
  historical data/audit provenance without an explicit version/evidence policy.
- Verify behavior across source releases and affected app surfaces. Run focused tests
  followed by required affected regressions; record results and remaining limitations.

## Acceptance examples

- Smith academic-rank staff counts, including SISINST, are supported employee counts.
- SAT/ACT percentile observations are scores, not percentages.
- Instructional activity credit hours are hours, not student counts; distinguish
  credit and clock/contact hours where the source distinguishes them.
- Enrollment counts, percentages, FTEs and ratios remain distinct.
- Currency evidence and scales remain explicit and source-backed.
- IDs/codes do not acquire spurious count units.
- Ambiguous/missing evidence remains unresolved; no guessing from observed values.
- Unit evidence is inspectable, outputs retain values, and all consumers agree.
- Common questions require no extra provider call to establish already-prepared units.

## Separate chart follow-up

Distinguish “All ranks” totals from component academic ranks in charts. Do not plot
the total as another peer category or discard it from requested tables/downloads.
This needs a separate source-backed category/total presentation rule, not a unit
exception. Also verify the automatic bar-chart decision after unit repair.

## Resume point

Review `evaluations/UNIT_RESOLUTION_REVIEW_ITEMS.md` for the clock/contact source
terminology issue; continue independent verification and broader regression coverage.
Do not mistake the original 2024 parser scan for verified assignments. Preserve the
proposal/review/activation workflow for future rule changes.
