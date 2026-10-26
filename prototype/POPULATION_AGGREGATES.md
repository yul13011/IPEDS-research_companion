# Population aggregates

October 21, 2026. Supersedes the former blanket national/state/sector restriction.

The version-2 catalog query engine now accepts an optional `population` in place
of named institutions. Questions use the same catalog inspection, source field
IDs, typed operators and parameterized SQL as other analyses. It is not limited
to questions in a benchmark list. The 30-institution bound remains for explicitly
named comparisons; it does not limit a directory population.

## Population and reporting units

- Explicit annual FIPS geography codes, institutional control, institution level,
  optional degree-granting status, Title IV status and administrative-office policy.
- US default: 50 states plus DC, Title IV PSET4FLG 1/3, administrative offices
  excluded. Territories require explicit geography. State/control/level names in
  the question are independently checked against the plan.
- Administrative offices are included only as an explicit source reporting scope,
  e.g. applicable finance or salary/staff counts. A visible caveat identifies this.
- The annual directory is selected with documented category codes. Fact tables
  contain reporting units, which can differ from directory entries. The complete
  directory selection, source coverage, unmatched units and exclusions are audited.
- Aggregate counts sum institutional reports. They do not deduplicate individuals
  applying, attending, receiving awards or working at multiple institutions.

## Calculations and validation

- Global expression reducers combine reporting institutions. Source reducers still
  work within an institution. A population output must actually reduce the scope;
  listing some institutions cannot substitute for a national result.
- Rates pool numerator and denominator counts. Institutional percentages cannot
  be summed. A mean of institution rates requires an explicit unweighted request.
- For complete-case pooled ratios, the engine uses the same complete reporting
  units in both sums. Missing paired counts never contribute to just one side.
  Propagate remains available. Missing values are never unconditionally zeros.
- Explicit `reconcile_distance_partition=true` on an EF annual A_DIST source
  requires the exact documented EFDEEXC/EFDESOM/EFDENON/EFDETOT fields.
  Exclusive, some and no-distance students partition total enrollment. Blank
  components can be derived as zero only when the other nonnegative integer
  counts already equal the reported total. Suppression, invalid values and
  unresolved blanks stay missing; contradictions block execution. Each derived
  cell is audited and explained; original source cells are unchanged. This is
  opt-in, not a general missing-as-zero rule. The disjoint exclusive+some union
  has a typed relationship to its own source total and can produce a percentage.
  Q42 all ten local years match; 2024 is 10,788,116 / 20,066,904 = 53.7607%.
- Source category/decomposition and row-containment proofs remain required for
  percent shares. Reviewed annual count relationships include retention, financial
  aid, admissions and graduation counts. Unknown relationships still block.
- Source-defined prior-cohort/current-enrollment retention relationships are valid
  period relationships, not accidental mismatches of year labels.
- Numeric unit recognition uses field-specific student/cohort wording before a
  multi-purpose table-wide hint; monetary aid amounts and required fees are money,
  not headcounts. FTE exposures may be summed across disjoint institutions.
- All source keys, row-domain filters, subtotal overlap and join cardinality checks
  remain enforced. Unmatched null keys are not mistaken for duplicated fact rows.
- Directory state/sector/control fields can be joined and grouped. The requested
  grouping must survive the global reduction. Groups default to bars in one year;
  multi-year results use the existing line-chart rules.

## Annual trends and follow-ups

`annual_years` applies a one-year population query independently in each available
release. Each field and category is read from that release. Missing/ambiguous
fields, substantive title/category changes and physical ownership conflicts block
the affected request; no source-year substitution or quiet omission is allowed.
Source queries do not cross-join annual facts or freeze the population to the first
year. Final request/result coverage checks run on the complete combined answer.

Entering cohorts use source-coded labels or explicit source-table cohort evidence;
release years are not relabeled as cohorts. Session context retains population and
annual scope. Tables, chart formatting, presentation exports and data downloads
use the existing response flow. Definitions & sources shows aggregate scope and
directory counts. Excel adds aggregate-scope and reporting-unit sheets; JSON keeps
the full audit.

## Benchmarks and known discrepancies

`evaluations/run_population_engine_benchmarks.py` runs the actual production
executor against NCES spreadsheet expectations, preserving all original periods
and tolerances. These are independent expected values, not model-calculated values.
Numerical discrepancies are not counted as passes or automatically blamed on
arithmetic: local provisional/older releases can differ from later NCES finals.

The runner generates `population_benchmark_guards.json` for known mismatching
method/scope signatures. Those exact methods/years remain under review and cannot
publish figures. The guard stores source-method fingerprints and reasons, not
expected answers. It is not a whitelist: unfamiliar valid methods continue through
the ordinary engine checks. The evaluation runner can measure guarded methods via
a code-only context, never a model/user plan field. Review a discrepancy and rerun
the benchmark before removing a guard. Signatures identify exact methods and do
not prove semantic equivalence of arbitrary alternative expressions.

The original `evaluations/nces_aggregates/REVIEW.md` is the pre-change baseline;
current findings are in `POPULATION_IMPLEMENTATION_REVIEW.md` in the same folder.
The old application guard test runner is a historical baseline, not a current
end-to-end population test. Q8's age category is user-confirmed as 25 and above;
all five locally covered observations match exactly. Q200's outcome is confirmed
as award completion within eight years for all entering degree/certificate-seeking
undergraduates at U.S. Title IV degree-granting institutions; all eight cohorts
match displayed NCES precision. Use OMCHRT=50 once and pool OMAWDN8/OMACHRT
counts from the same institutions. The annual codebook must link the adjusted
entering cohort to the eight-year award outcome; the differing dates are retained.
For 2016-17 (OM2024), 2,889,755 / 6,106,613 = 47.3217% across 3,473 institutions.
The production validator verifies the annual cohort and outcome titles and count
definitions before accepting this documented relationship. Pending exports without selected filters,
unknown source methods and unavailable releases are not accepted numerical tests.

## Remaining limits

20 source relations, 100 exact field IDs, 20,000 source rows per relation and 5,000
output rows remain bounded. Population fact queries have a 60-second read deadline
(named-institution reads retain 20 seconds); national scans can touch much larger
tables. Dense historical fact scans can still reach that limit. A timeout publishes no partial result. Crosswalks, reporting-unit revisions,
deduplicated people, unknown denominators and undocumented groups are not inferred.
Live model planning is tested separately with latency and usage; source-executor
timings are not advertised as chatbot answer latency.
