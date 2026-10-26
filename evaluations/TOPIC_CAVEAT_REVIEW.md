# Explore IPEDS caveats: source and scope review

October 21, 2026. **Share with caveats; review complete for the six supplied texts.** No UI text, analysis defaults or source data changed. The six blue boxes are editorial summaries, not quoted NCES survey instructions or universal statements about every IPEDS field.

**Implementation update:** The owner subsequently approved the corrections. All six stored topic caveats are now updated in `prototype/learning_content.json`; verified the exact final text in each expanded Explore IPEDS blue box with no UI exceptions. See [UI verification](topic_caveat_ui_verification.json). The findings and proposed wording below preserve the pre-change review; the clarity issues identified there have been addressed by this update. Source definitions, query behavior, preset routing and methodological defaults are unchanged. Need ideas? uses the shared topic data for examples but does not itself display these blue scope boxes.

## Scope and verification

Inspected the local source codebooks and physical-field inventory for the ten loaded releases, 2015–16 Final through 2024–25 Provisional; checked the reviewed graduation example bindings and the app's source-year institution selection. For every loaded release, checked ADM table scope, Completions A reporting periods and the six-year GR example cohort mapping. Checked both documented and physical SAT median fields across the full inventory. Enrollment, aid, HR and institutional identity distinctions were traced to representative exact definitions and table descriptions; this is not a review of every field, school or source conflict.

Evidence: [local source records and annual checks](topic_caveat_source_evidence.json). Variable records retain original codebook paths, worksheet names, row numbers and record IDs; table provenance is saved separately in the same file. No statistical benchmark queries or provider model calls were needed.

## Findings by caveat

### 1. Admissions — correct within the loaded ADM scope; clarify availability

All ten ADM table descriptions limit the collected admissions population to entering first-time degree/certificate-seeking undergraduates at institutions without open admissions. This supports the undergraduate-only/no-graduate-admissions interpretation of these ADM tables. It does not mean the app has no graduate enrollment, awards or other graduate data. It also does not describe every admissions practice or later, unloaded IPEDS releases.

All ten ADM tables identify Fall 2015–2024 coverage. This is the loaded admissions observation span, not the reporting period for all app data. Source-year labels elsewhere include academic years, fiscal years and entering cohorts.

SATVR50 and SATMT50 are documented and physically present only in ADM2022, ADM2023 and ADM2024. Their physical null counts are 981, 979 and 1,006 per field, respectively. Thus “SAT medians begin in 2022” is verified for reported reading/writing and math 50th-percentile fields in the loaded data. It is not a guarantee for every school or a claim that SAT data of all kinds start in 2022. Earlier percentile measures are different fields; averaging 25th/75th percentiles does not establish a reported median.

**Suggested text:** “In the loaded 2015–2024 admissions data, figures describe first-time, degree/certificate-seeking undergraduates at institutions without open admission; graduate admissions are not included. Reported SAT section medians are available from Fall 2022 where institutions report them.”

### 2. Enrollment — supported as a general interpretive principle

EF defines enrollment at the official fall reporting date or October 15. EFFY counts unduplicated enrollment over a 12-month period. EFIA derives 12-month FTE from instructional activity; the catalog also has a distinct fall FTE measure. FTE is an enrollment-equivalent measure, not interchangeable with either student headcount. The caveat does not assert that counts must always differ numerically.

Year variation is documented: EFFY2024 describes additional undergraduate attendance/entering-status breakdowns beginning with the 2019–20 data collected in 2020–21. A field/table existing does not guarantee a reported value at every institution. The Definitions & sources instruction describes an app control.

**Suggested text:** “Fall headcount, 12-month unduplicated enrollment, and full-time equivalent enrollment are different measures. Available breakdowns and reporting periods vary; check Definitions & sources for the population, period, and enrollment measure used.”

### 3. Financial aid — supported; specify the exact student group

SFA ANYAIDN includes work-study, student loans and grants/scholarships for the full-time, first-time degree/certificate-seeking undergraduate cohort; it is broader than grant/scholarship receipt. SCUGRAD and SCUGFFN describe different eligible student groups. First-time students are a subset, not a separate disjoint population to add to all undergraduates. Some net-price measures further restrict eligibility, and average aid amounts can use recipients as their denominator rather than all eligible students.

The SFA codebooks also distinguish academic-term versus program-reporting populations/periods. Therefore an SFA denominator must not automatically be replaced with any convenient EF/E12 enrollment total. Some local aid ownership conflicts remain unresolved; generic source instructions do not certify those fields.

**Suggested text:** “Grant/scholarship aid, loans, and any financial aid are different measures. Results may cover all undergraduates or a specified subgroup, such as full-time, first-time degree/certificate-seeking students. Check Definitions & sources for eligibility, the denominator, reporting period, and missing values.”

### 4. Outcomes — correct specifically for the examples; contains app-policy statements

The reviewed six-year bachelor example uses GRTYPE 8 (adjusted bachelor's subcohort) and 12 (bachelor completers within 150% of normal time), in four-year institutions, for full-time first-time bachelor's-seeking students. All ten annual GR titles support outcome year minus six: 2015–2024 maps to entering cohorts 2009–2018. This does not describe all GR cohorts or all Student outcomes data.

Other source tables differ: two-year GR cohorts have a three-year follow-up; OM has full-/part-time and first-/non-first-time cohorts and four/six/eight-year status points. OM2015 and OM2024 also have different cohort windows, so an entry cohort must not be assigned by merely relabeling the release year. All ten C A table periods are July 1 of the prior year through June 30 of the source year. Annual awards are not the same as students receiving awards or cohort completion rates.

“Custom groupings need an explicit definition” and blocking unresolved methods/discrepancies describe app methodology/validation policy. They are not definitions supplied by every outcome table. Graduation completion/cohort rules cannot be extended to finance, enrollment or HR data.

**Suggested text:** “These six-year bachelor graduation examples follow first-time, full-time bachelor's-seeking adjusted cohorts: outcomes in 2015–2024 correspond to entry in 2009–2018. Other completion measures use different populations and follow-up periods. Annual awards cover July–June and are distinct from cohort graduation rates.” Keep app validation/custom-group guidance separate from this survey note.

### 5. Faculty and staff — supported; academic rank is not a filter for every staff measure

EAP FACSTAT explicitly distinguishes faculty designation from the work to which a person is assigned. Instructional activity and faculty status must not be used as synonyms. Staff populations vary by full-/part-time employment, medical-school scope, occupation and faculty/tenure status; salary tables can additionally distinguish academic rank and appointment period. It would be too broad to imply every employee count depends on an academic rank or every salary field uses the same employee group.

The EAP2024 description documents multi-year and indefinite contracts being separated starting in 2016, whereas earlier years combined them. Compatible definitions and population/period checks are a sound analytical requirement, not proof that all cross-year comparisons are automatically harmonized.

**Suggested text:** “Faculty status and instructional work are different classifications. Staff counts depend on the employment and occupational groups selected; salary measures may also differ by academic rank and appointment period. Definitions can change across years, so compare compatible populations and periods.”

### 6. Institutional characteristics — supported, but clarify which year and who resolves uncertainty

HD directory documentation describes an annual institutional universe. NEWID identifies the UNITID where merged-school data are found; DEATHYR records deletion year; activity/status fields distinguish closed, merged and inactive records. These establish that current names/status cannot simply be assumed across time. They do not establish a complete automatic institutional-history crosswalk.

The reviewed analytics route resolves institutions and reads HD labels for each source year. The general engine and explicit directory populations likewise bind to annual source-year records. A source year need not be the historical observation/entry year: GR2024 outcomes for a 2018 cohort use 2024 release/directory context. Discovery may search multiple releases; institution candidate matching can use latest labels and prior names. Thus “each analysis uses the selected year's institution records” needs source/release-year wording and is not a universal statement about every lookup.

Branch/consolidation differences are a reporting-scope warning, not a claim that every campus is consolidated. An ambiguous intended institution can require user clarification; a broken source relationship may need technical investigation rather than asking the user to supply a mapping.

**Suggested text:** “Institution names, characteristics, and reporting status can change over time. Analyses use institution records associated with the relevant source release. Branches or campuses may report separately or as part of a larger institution; confirm the reporting institution when the intended scope is unclear.”

## Cross-checks against NCES publications

Local historical definitions control this app's loaded-year claims. Current NCES pages can cover later/unloaded changes and are not used to extend this app's coverage. Targeted external checks support the core distinctions:

- [NCES Fall 2022 admissions table](https://nces.ed.gov/ipeds/search/viewtable?returnUrl=%2Fipeds%2Fsearch&tableId=36028): first-time degree/certificate-seeking undergraduates, non-open-admission institutions.
- [NCES Human Resources overview](https://nces.ed.gov/ipeds/survey-components/3/human-resources): separate occupational activity, faculty status, employment status, academic rank and contract/teaching period.
- [NCES financial-aid table](https://nces.ed.gov/ipeds/search/viewtable?returnUrl=%2Fsearch&tableId=36532): explicit full-time first-time denominator and loan exclusions.
- [NCES 2023 data-file listing](https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx?gotoReportId=7&rtid=7&year=2023): distinguishes fall observations, July–June completions and 12-month measures.

Two direct NCES page/PDF fetches timed out; no unavailable PDF contents were invented. The complete local source-record evidence supplies the primary verification.

## Review coverage and remaining defects

Counts below refer to the six supplied text blocks, not all app data. No changed UI needs visual acceptance; the shared renderer maps these stored scope texts directly to its blue info boxes. This was a content/provenance review, not a screen-layout, mathematical-benchmark or chart review.

| Category | Observed defects | Assessment |
| --- | --- | --- |
| Usefulness/completeness | 0 / 6 | All six supplied caveats reviewed; wording improvements are identified below. No certification of every source field. |
| Analytical clarity | 4 / 6 | Admissions needs loaded-field availability wording; outcomes mixes example-specific scope and policy; HR can imply all dimensions apply universally; institution wording confuses source and observation year. |
| Visual/interaction consistency | N/A | No visual or interaction changes requested or made. |

| Category | Observed defects | Assessment |
| --- | --- | --- |
| Source authority/confidence | 0 / 6 | Principal distinctions traced to local codebook records and relevant implementation; annual/date/physical coverage claims checked across ten releases. |
| SQL/value accuracy | N/A | No statistical result is being validated; source inventory checks retained in evidence. |
| Within-chart agreement | N/A | No charts in scoped artifact. |
| Complete source details | 6 / 6 | Blue boxes have no claim-specific visible source references; evidence is now retained in this companion file. |
| Cross-artifact consistency | 0 / 6 | Text checked against topic/example scopes and pertinent implementation; latest-year candidate matching is distinguished from annual analysis. |
| Data-quality controls | N/A | No eligibility/missingness calculation changes; this does not validate every implemented check. |
| Conclusion support | 0 / 6 | Supported as qualified topic guidance; not universal rules for all IPEDS data. |

Prioritized proposed fixes: (1) explicitly limit admissions dates/SAT median availability to loaded source fields; (2) distinguish six-year examples from other outcome populations and separate app policy; (3) specify source-release year for institutional records; (4) use measure-specific HR dimensions. No demonstrated numerical error was found in these texts. All wording changes remain proposed; no new analytical default or automatic policy has been imposed.
