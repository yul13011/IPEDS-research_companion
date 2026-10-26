# Shared currency display correction — October 21, 2026

## Result

Fixed internal `monetary amount` leaking into reader-facing results. Shared source-backed presentation copies now display verified dollar values with `$`, chart axes with **US dollars (USD)** and CSV/Excel monetary rows with explicit currency/scale columns. The Mount Holyoke source value remains exactly **27,792,003**, now displayed as **$27,792,003**. No school-specific condition was added.

`prototype/units.py` reads executed codebook evidence and reviewed survey reporting conventions, keeping currency/scale separate from analytical unit categories. Thousands and millions remain on their original numeric scale and carry explicit labels. Conflicting/foreign/unsupported evidence produces **Currency/scale unverified**, without an invented dollar sign. Original raw result objects are unchanged, including saved conversations. The technical audit retains original analytical row units and adds presentation-unit evidence. Currency references and scope are documented in `prototype/CURRENCY_UNITS.md`.

Integrated with response summaries, result tables/metrics, shared charts and styled labels, CSV, Excel and JSON audit exports. The original salary versus average/nine-month salary definitions and periods are preserved. No analytical plans, source data, query methods or methodological defaults changed.

## Verification

- Final focused acceptance: **3 tests passed in 7.141 seconds**, `currency_units_focused_final.log`. Checks four monetary measures (salary outlays, nine-month-equivalent average salary, tuition, finance expenses) at Mount Holyoke, Yale and Harvard against independent raw-source SQL, exact numeric export values, currency/scale metadata, original audit rows, charts and actual Streamlit table rendering. Also checks missingness, thousands/millions, ambiguous/foreign/conflicting evidence, unchanged nonmonetary units, idempotence and immutable input results.
- Related regression run: **46 tests passed in 311.544 seconds**, `currency_units_regression.log`. Full salary chart formatting/preview/image-export workflow, salary presets, source SQL comparisons, query engine, catalog execution and calculations. Inspected freshly generated `chart_workflow/actual_preview_1200x675.png`: dollar value labels and USD axis are readable.
- Earlier chart/text/formatting run: **25 existing tests passed**; the 28-test run also included the three new acceptance tests and failed one tuition subcase. Preserved in `currency_units_tests.log`. Cause: foreign-currency code `CAD` matched part of “academic”; word boundaries corrected this, and all new acceptance tests subsequently passed. Final focused reruns also cover the added scale safeguards and evidence deduplication. This initial run is not recorded as a clean 28-test pass.
- Corrected saved-result artifacts: `currency_units_mount_holyoke_display.json`, `.csv`, `.xlsx`. No new model request was needed for formatting verification.
- Restarted local app on port 8516, PID 76584; health returned `ok`. First restart failed because Windows split an absolute launcher path containing spaces; corrected by using the project-relative launcher. Startup attempt and final logs remain separate.

The complete combined suite was not rerun. Tests do not certify every possible currency/scale phrase, model interpretation or browser visual interaction. National aggregate reconciliation remains paused.
