# Measure registry

## Working prototype update

`reviewed_measures.json` now contains 36 implementation-reviewed measures and 340 explicit annual mappings. It is the prototype's runtime registry, rebuilt by `prototype/build_registry.py`. Definitions, formulas, annual codebook IDs, categorical labels, physical locations and reviewed location corrections are explicit. Runtime rechecks the evidence before querying.

These are implementation reviews, not owner approvals. Known Yale discrepancies remain unresolved. Custom URM and national aggregation are excluded. New chat questions do not automatically approve mappings. The earlier `.example.json` is illustrative and is not loaded by the app. All ten annual SQLite copies now exist. See `../prototype/README.md`.

## Original design explanation

This folder demonstrates the proposed persistent store for reusable measure definitions and annual source mappings. These are application configuration files, separate from the original data and codebooks. They contain instructions and evidence, not copies of student or institution observations.

Start with one JSON file per measure. JSON is plain text organized into named fields and lists, readable by both people and Python. A production registry could later move to a dedicated SQLite database, without changing the role it plays. That would be an additional metadata database, not an edit to any annual source database.

`undergraduate_grant_aid_percent.example.json` is an illustrative draft, not a runtime-approved mapping. Its source table/column locations were observed in the annual Access inspection. The 2016–17 SQLite path is a planned output and does not yet exist. The example explicitly records that distinction and leaves longitudinal certification pending.

At question time the agent retrieves a matching measure entry, checks its status and annual coverage, resolves the requested institutions, and builds a validated query plan. It reads values from the annual databases and constructs a result table. It does not take numeric answers from this registry.

For a new concept, the agent can save a proposed entry with supporting codebook references and validation findings. Only entries meeting the established review/validation rules become approved reusable mappings. Source changes require revalidation, and edits should retain version history.
