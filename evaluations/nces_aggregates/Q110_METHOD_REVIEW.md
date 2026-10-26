# Q110 source-method diagnosis

October 21, 2026. No further owner information is requested. This is a source-SQL diagnostic, not a passing production-executor benchmark.

The supplied workbook already defines the scope: U.S. Title IV public and nonprofit postsecondary institutions, administrative-office expenses excluded, current dollars, finance core expenses divided by 12-month FTE enrollment.

Source documentation identifies `DRVF` fields `F1COREXP` (GASB) and `F2COREXP` (FASB) as total core-expense dollars. `DRVEF12.FTE12MN` defines 12-month enrollment, including doctoral professional practice. The candidate method chooses the populated accounting-standard expense total once per reporting unit, matches it to positive annual FTE, sums expenses and FTE across the same units, then divides. No selected unit in any tested year has both expense alternatives populated. Missing expense alternatives are not treated as general zeros.

The candidate matches the original benchmark's displayed dollar precision in **9 of 10 local years**. In 2024, $567,188,035,790 / 14,779,867 FTE = $38,375.7199, rounding to **$38,376**, across 3,542 reporting units. In 2022, the local result is **$35,362.8964** versus the benchmark's **$35,324**. This discrepancy remains open; do not force-fit it or assume a source-vintage explanation without evidence.

Full annual SQL, parameters, source totals, overlap checks, counts and timing are in `q110_source_diagnostic.json`. The ten queries use no AI calls or API cost; their execution timings do not measure chatbot latency. Fiscal years 2010–2014 remain outside local release coverage and were not evaluated.

Remaining work: verify the accounting-alternative selection and annual population/period semantics within the production typed engine, run all Q110 observations there, and investigate the 2022 numerator, denominator and source revision. The existing production benchmark counts remain unchanged; diagnostic matches are not promoted to production passes. No original workbook or source data was edited.
