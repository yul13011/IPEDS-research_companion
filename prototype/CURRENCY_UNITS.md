# Currency display rules

`units.py` separates analytical unit categories from display units. Internal `monetary amount` remains available for calculation validation; it is never a reader-facing unit suffix.

For monetary results, `display_result` resolves the executed source's codebook evidence by metric, source year and institution. Explicit field dollar/scale definitions and reviewed IPEDS reporting conventions establish USD and scale. The checked convention families are salary tables, finance F1/F2/F3 tables, Cost I/II, academic-year IC student charges and SFA monetary fields. References are retained alongside the local codebook record identifiers. These rules do not turn counts/percentages in those tables into currency and do not use a model-authored output label as evidence.

Reviewed references:

- [2024 HR collection](https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2024/human%20resources/package_1_44.pdf): annual base salary outlays, instructional and non-instructional scope; [NCES salary survey description](https://nces.ed.gov/pubs/96855.pdf): whole-dollar outlays.
- [Finance reporting instructions](https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2023/finance/package_5_12.pdf): financial amounts in whole dollars.
- [Cost reporting form](https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2024/cost%20i/package_11_73.pdf) and [CEDS IPEDS tuition mapping](https://ceds.ed.gov/connectReport.aspx?uid=31034): student charges in US dollars.
- [SFA reporting instructions](https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2024/student%20financial%20aid/package_7_20.pdf): student counts distinguished from aid dollar amounts.

Explicit thousands/millions override unscaled reporting conventions without multiplying stored values. Conflicting currency/scales or unsupported evidence produce **Currency/scale unverified** and no dollar prefix. Existing reviewed `dollars` mappings without source documentation retain their explicit unit. A salary keyword alone establishes neither currency nor scale.

Answers, tables, charts and their styled labels use the presentation units. CSV/Excel preserve numeric precision and expose `unit`, `source_unit`, `currency`, and `currency_scale` for monetary rows. Excel methodology and audit JSON include display-unit evidence. Audit JSON retains original analytical row units; original source definitions, formulas and SQL stay intact. Display normalization is idempotent, works with saved result objects, and does not requery or mutate them.

This is a formatting/evidence change, not a currency conversion, inflation adjustment, population change or reconciliation of aggregate benchmarks. Ambiguous monetary fields remain explicitly unverified. The framework does not certify every unencountered phrasing of a currency/scale definition.

Verification: `tests/test_units.py` checks salary totals, nine-month-equivalent means, tuition and finance expenses at Mount Holyoke, Yale and Harvard against independent raw-source queries, CSV/Excel/audit and actual Streamlit table rendering. Synthetic checks cover scaled values, missingness, conflicting/foreign currencies and unchanged count/percent/FTE rows. Related chart and engine regression evidence is in `../evaluations/CURRENCY_UNITS_REVIEW.md`.
