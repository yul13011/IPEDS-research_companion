# Analytical expansion: agreed coverage scope

> Current status: analytical expansion steps 1–4 are implemented, including the bounded relational query/validation engine. See [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) for completed work, evidence, limits and remaining tasks; [engine scope](prototype/QUERY_ENGINE.md) defines supported primitives. Earlier proposal-only statements below are historical checkpoints.

Confirmed by project owner: October 19, 2026.

Authoritative source boundary: `C:\Users\liyuj\OneDrive\2026\IPEDS Project\IPEDS Data`.

“All IPEDS data” means all datasets, codebooks and release documentation in this folder, covering every institution, population and field represented by the supplied releases. It does not mean every publicly available IPEDS year or release. Coverage is bounded by the source files; not every concept exists in every year.

## Current inventory

| Supplied release | Imported tables | Annual variable definitions | Imported table list matches catalog |
| --- | ---: | ---: | --- |
| IPEDS_2015-16_Final | 52 | 2185 | Yes |
| IPEDS_2016-17_Final | 55 | 2159 | Yes |
| IPEDS_2017-18_Final | 54 | 2210 | Yes |
| IPEDS_2018-19_Final | 55 | 2246 | Yes |
| IPEDS_2019-20_Final | 55 | 2211 | Yes |
| IPEDS_2020-21_Final | 56 | 2439 | Yes |
| IPEDS_2021-22_Final | 56 | 2561 | Yes |
| IPEDS_2022-23_Final | 58 | 2685 | Yes |
| IPEDS_2023-24_Final | 57 | 2695 | Yes |
| IPEDS_2024-25_Provisional | 56 | 2599 | Yes |

Catalog: 554 annual table occurrences; 25,245 physical column occurrences; 23,990 variable-definition records; 124,493 category-code records. These are counts across releases, not counts of unique concepts.

The source folder contains 10 Access databases, 10 Excel codebooks, 10 Word ReadMes and one additional 2015–16 SQLite copy. The latter is not an extra annual release. Access is the canonical data source for the existing verified conversions.

## Loaded versus analytically supported

All ten releases have imported SQLite copies and catalog entries. The prototype currently exposes 36 registered analytical measures; catalog presence and imported table counts do not establish analytical support for all fields.

Step 1 is complete for the source boundary and release/file inventory. A detailed subject-area coverage matrix is still needed to track direct lookup, breakdown, calculation, join and longitudinal support as implementation expands. No additional external datasets are required to meet the agreed folder boundary; definition gaps inside that boundary may still need resolution.

## Verification

Current inspection: 30/30 cataloged source files exist; 30/30 sizes match the catalog; 20 documentation hashes match. All imported table lists checked against the catalog.

Prior foundation report records full conversion verification for 554 tables and 33,484,311 rows. Full Access hashes, all row/value comparisons and integrity checks were not repeated in this inspection. The catalog records 1,248 metadata issues; their resolution belongs to metadata validation, not source-inventory completion.

Machine-readable evidence: [coverage_scope_2026-10-19.json](data/coverage_scope_2026-10-19.json). Existing verification: [foundation_verification.json](data/foundation_verification.json) and [catalog_verification.json](data/catalog_verification.json).

## Next work

Build the subject-area coverage matrix and reconcile metadata/population/key definitions before broadening the catalog-to-query planner. First end-to-end expansion case remains Yale undergraduate enrollment by race/ethnicity.

