# IPEDS Research Companion — Example Questions

A running catalog of example / test questions the app should answer well, organized by **IPEDS
survey component**, using the official survey names from the 2024-25 codebook
(`IPEDS202425Tablesdoc.xlsx`, sheet `tables24`, column C). Each section can grow as we develop
and verify coverage.

The 12 surveys: Institutional Characteristics · Admissions and Test Scores · Fall Enrollment ·
12-month Enrollment · Completions · Graduation Rates · Outcome Measures · Student Financial Aid ·
**Cost** · Human Resources · Finance · Academic Libraries.

---

## Institutional Characteristics (IC)

_(to be added)_

## Admissions and Test Scores (ADM)

Source: `ADM{year}` — fall, first-time degree/certificate-seeking undergraduate admissions; year =
fall entry year. Ground truth recomputed from `ADM{year}` (Yale reference CSVs in
`Test cases/Yale/`: `w033-...admissions...`, `w032-...sat...`). *School-specific examples are Yale
for now.*

**Source variables:** `APPLCN` (applications received), `ADMSSN` (admitted), `ENRLT` (enrolled /
matriculated); **admit rate** = `ADMSSN`/`APPLCN`; **yield** = `ENRLT`/`ADMSSN`; **SAT** percentiles
`SATVR25`/`SATVR75` (EBRW / "reading"), `SATMT25`/`SATMT75` (math), plus `SATVR50`/`SATMT50` for
years ≥ 2022.

1. **What was Yale's admission rate in fall 2024?** → `ADMSSN`/`APPLCN` (reviewed measure), shown as a percent.
2. **How many applications did Yale receive for fall 2024?** → `APPLCN`.
3. **How many students did Yale admit and enroll in fall 2024?** → `ADMSSN` and `ENRLT`.
4. **What was Yale's yield rate for fall 2023?** → `ENRLT`/`ADMSSN`, percent.
5. **What were Yale's 25th and 75th percentile SAT scores (reading/writing and math) for the entering class of fall 2023?**
   → `SATVR25`/`SATVR75`, `SATMT25`/`SATMT75`.

> Notes: rates use raw counts (not the whole-percent derived fields), fraction scale with 0.0005
> tolerance; SAT is for enrolled score-submitters; the 10th/90th percentiles are not collected by IPEDS.

## Fall Enrollment (EF)

_(to be added)_

## 12-month Enrollment (EFFY)

_(to be added)_

## Completions (C)

_(to be added)_

## Graduation Rates (GR, GR200)

Source: `GR{year}` — six-year outcomes; observation year = entry cohort + 6 (the 2018 entering cohort
is observed in `GR2024`). Ground truth recomputed from `GR{year}` (Yale reference CSVs in
`Test cases/Yale/`: `w041-...graduation...`, `...grad-rates-subgroups...`). *Yale-only for now.*

**Source variables:** adjusted cohort = `GRTOTLT` where `GRTYPE=8`; six-year bachelor completers =
`GRTOTLT` where `GRTYPE=12`; **6-year rate** = completers / cohort. By gender: `GRTOTLM` / `GRTOTLW`.
(Pell: `GR{year}_PELL_SSL`, `PSGRTYPE=2`; international = U.S. nonresident `GRNRALT` — later pass.)

1. **What was Yale's six-year graduation rate for the 2018 entering cohort?** → `GRTOTLT`(12)/`GRTOTLT`(8), percent.
2. **How many students were in Yale's 2018 entering cohort, and how many graduated within six years?**
   → `GRTOTLT`(8) and `GRTOTLT`(12).
3. **What was Yale's six-year graduation rate by gender for the 2018 cohort?** → men `GRTOTLM`, women `GRTOTLW` (drill-down).

> Notes: the denominator is the adjusted cohort (after allowable exclusions), not original entrants;
> rates use raw counts, fraction scale with 0.0005 tolerance. URM is a custom user grouping with an
> unresolved race-unknown rule (see `benchmark_definitions.json`) — held for a later pass.

## Outcome Measures (OM)

_(to be added)_

## Student Financial Aid (SFA)

_(to be added)_

## Cost

Its own IPEDS survey (survey #19 in the 2024-25 codebook). Tables: `COST1_2024` (published
charges), `COST2_2024_NetPrice` (net price), `COST2_2024_FinancialAid`, and the derived
`DRVCOST2024` (total price / cost of attendance).

**Shared answer template** (one adaptive template, verified across the three institution types below):
- **Published total price** (sticker, living on campus) — show only the *distinct* residency figures:
  one total for a private school; in-state / out-of-state for a public school (in-district shown
  only when it differs).
- **One-line component breakdown** — tuition & fees · housing & food · books · other.
- **Average net price** — what a typical aided student actually paid (latest year), choosing the
  populated field, labeled with the aid group and year.
- **Drill-down offers** — net price by family income (only when reported), out-of-state / off-campus
  totals, a single component.

**Shared source variables** (2024-25 release; table names shift by year, e.g. `DRVCOST2023` — the eval
should recompute from whatever is current rather than rely on fixed numbers):
- Published total price (COA): `DRVCOST2024` — `CINSON` (in-state, on campus), `COTSON` (out-of-state),
  `CINDON` (in-district); off-campus `CINSOFF` / `COTSOFF` / `…FAM`.
- Component breakdown: `COST1_2024` — `chg2ay3` (in-state tuition & fees), `chg3ay3` (out-of-state t&f),
  `chg4ay3` (books & supplies), `chg5ay3` (food & housing, on campus), `chg6ay3` (other, on campus).
- Net price: `COST2_2024_NetPrice` — average = first populated of `NPIST2` ∨ `NPGRN2` ∨ `NPT42`
  (latest year, 2023-24); by income (Title IV) = `NPT412/422/432/442/452`, when reported.

> Eval note: don't hardcode dollar amounts (they change each IPEDS cycle). The eval recomputes ground
> truth from the variables above for the current release and checks the answer's *shape* and *values*.

---

**1. What is the cost of attending University of Connecticut?**  *(public flagship — UNITID 129020)*
- **Expected shape:** two published totals (in-state ≠ out-of-state); component line; average net price;
  by-income offered (reported for this school).
- **Eval checks:** in-state COA = `CINSON`; out-of-state COA = `COTSON` (must differ); components
  (`chg2ay3`+`chg4ay3`+`chg5ay3`+`chg6ay3`) sum to `CINSON`; net price from `NPIST2` (populated here).

**2. What is the cost of attending Yale University?**  *(private — UNITID 130794)*
- **Expected shape:** a *single* published total (in-state = out-of-state = in-district, so collapse to
  one); component line; average net price prominent (large sticker-vs-net gap); by-income reported.
- **Eval checks:** `CINDON` = `CINSON` = `COTSON` (one total shown); net price from `NPGRN2` — note
  `NPIST2` is **null** for Yale, so this case proves the populated-field selection is required.

**3. What is the cost of attending Southern Connecticut State University?**  *(public regional — UNITID 130493)*
- **Expected shape:** two published totals (in-district = in-state, so collapse those; out-of-state
  differs); component line; average net price; by-income **omitted** (not reported for this school).
- **Eval checks:** in-state COA = `CINSON` (= `CINDON`); out-of-state = `COTSON`; net price from
  `NPIST2` (populated; `NPGRN2`/`NPT42` null here); by-income all null → answer must omit it gracefully.

## Human Resources (HR)

_(to be added)_

## Finance (F)

_(to be added)_

## Academic Libraries (AL)

_(to be added)_
