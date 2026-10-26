# Shared unit metadata repair — October 22, 2026

Implemented the saved two-stage plan. Stage 1 produced a proposed catalog and
old/new CSV audit before analytical integration; review corrected candidate mistakes
in degree recipients versus awards, table population inference and monetary/FTE/hour
precedence. Stage 2 activated a shared versioned resolver/catalog across source
descriptors, execution and presentation. No original metadata or numeric values changed.

## Audit

- `unit_catalog_proposal.csv`: all 23,990 documented fields across 2015–2024 releases,
  original/proposed semantic units, status and assignment basis.
- `unit_catalog_proposal_summary.json`: counts, changed assignments and five cross-year
  flags. This remains a proposal-scope artifact; active catalog is `data/unit_catalog.sqlite`.
- 2,484 fields remain unresolved. Identifiers/codes are separate categories, not failed
  measurement-unit assignments. Currency quantity classification is distinct from
  currency/scale verification; existing display rules remain in place.
- Prepared catalog entries include source evidence, rule version and per-field/context
  fingerprints. Checked all 23,990 entries have the current version and actual staff,
  score and credit-hour lookups hit and equal the live resolver.

## Behavior

Reexecuted the saved Smith College rank plan without provider calls. All seven values
match the original replay, every rank has employee units, and the default is a bar
chart. All ranks is a separate total panel. Preserved the original codebook label
“Intructors”; source text is not silently rewritten. Artifacts:
`smith_rank_units_fixed.json`, `smith_rank_units_panel_1.png`,
`smith_rank_units_panel_2.png`.

Other acceptance cases cover all ten releases for rank counts and SAT scores; ACT
scores, undergraduate/graduate credit hours, retention/graduation percentages, staff
new hires, student/award distinctions, library counts/transactions, identifiers,
unknown arithmetic rejection, explicit currency/scale conflicts, prepared-entry
freshness and saved direct/derived results. Saved direct display migration never
recalculates values. Old unverified derived answers require a rerun; audit keeps the
historical unit with the new interpretation recorded separately.

## Validation and limits

An intermediate affected run passed 64 tests in 146.695 seconds; a prepared-catalog
run passed 64 in 187.460 seconds. Final acceptance results are in
`shared_units_acceptance.log`; final counts/timing recorded in daily progress.
Final acceptance passed **66 tests in 148.025 seconds**. An additional forced-axis
UI guard passed in 9.175 seconds: **67 distinct tests** across the final runs.
Restarted production app PID 186012 on port 8516; health `ok`. The Smith chart PNG
was rendered and visually inspected; the full live browser conversation was not replayed.
The non-escalated initial run was interrupted at Streamlit local-socket UI testing;
subsequent UI runs used the established local-socket permission and project temp path.

No new provider calls were needed for the unit repair/reexecution. No new external
sources were investigated. Unit preparation is offline and normal requests use bounded
cached metadata lookups. A complete combined suite and broad provider-backed quality
benchmark were not run. Parsed verification is evidence/rule-backed, not a manual audit
of every field. Unresolved fields and flagged release differences remain inspectable.
National aggregate benchmark reconciliation stays paused.
