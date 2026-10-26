# Institutional Characteristics exploratory question review

October 22, 2026. **Assessment: needs revision.** This is an exploratory review of
the current app, not verification of an implemented repair. Only evaluation scripts
and documents were changed. The repair plan remains unaccepted and unimplemented.

## Method and evidence

- Twelve new initial questions, two contextual follow-ups and two targeted probes:
  **16 additional live turns**, beyond the original three IC questions.
- Invoked `prototype.institution_confirmation.ask(use_model=True)` with the app's
  configured default model, followed by `responses.finalize_answer`, as in the UI.
  Follow-ups used actual preceding answers and the UI's prior-plan/history convention.
  Fresh independent cases had no conversation context. No alternate offline parser.
- Independent source expectations came from read-only SQL on the supplied annual
  databases and the ingested original codebook records, including category mappings
  and workbook/sheet/row references. No outside source was used.
- Up to three independent cases ran concurrently; each conversation was sequential.
  These are recorded single-run outcomes, not a planner success-rate estimate or
  isolated latency benchmark. Cold initialization, concurrency and cache state
  affect timings. No UI rendering/export test or full numerical regression suite
  was run; the application code did not change.
- Runner: [probe script](probe_ic_categorical.py). Initial run log:
  [live log](ic_categorical_probes.log). Targeted probes:
  [follow-on log](ic_categorical_followon.log). Each turn's JSON under
  `ic_categorical_probes/` retains its exact question, answer, stage events, usage
  when available and exception when applicable.
- [Independent expectations](ic_categorical_probes/source_expectations.json) and
  [Bentley source row](ic_categorical_probes/threshold_source.json).

## Question-by-question findings

### 1. Calendar system — partial answer through a workaround

**Question:** What academic calendar system did Smith College use in 2024-25?

Source: IC2024.CALSYS=1, Semester. App found Semester, but returned an institution
count of 1 grouped by calendar system rather than the categorical observation.
92.94 seconds. [Actual response](ic_categorical_probes/calendar.json).

**Follow-up:** And Mount Holyoke College?

Source: Semester. App preserved the school-change intent and year, but again used
a count of 1. 19.08 seconds. This is evidence that some context resolution works,
not a clean categorical-answer pass.
[Actual response](ic_categorical_probes/calendar_followup.json).

### 2. Religious affiliation — correct rows, misleading summary

**Question:** Compare the religious affiliations of Boston College and Smith College
in 2024-25.

Source: RELAFFIL=30, Roman Catholic, for Boston College; RELAFFIL=-2, Not applicable,
for Smith. CNTLAFFI supplies additional control/affiliation context if needed; do
not silently change the meaning of Not applicable to a different category.

The app decoded both rows correctly but counted 1 for each. Its summary said:
"Religious affiliation: Roman Catholic ... Boston College: 1; Smith College: 1."
The generic single-metric summarizer uses the first row's category-bearing label
for all institutions, obscuring Smith's different response. Presentation metadata
selected a bar chart with the table hidden; actual browser rendering was not tested.
93.00 seconds. [Actual response](ic_categorical_probes/affiliation.json).

**Priority:** semantic correctness, not just readability. Add per-cell narrative
checks and prevent dummy-count charts for availability/attribute questions.

### 3. Explicit Yes/No — blocked

**Question:** Did Bunker Hill Community College and Smith College have open admission
policies in 2024-25?

Source: OPENADMP=1, Yes, for Bunker Hill; OPENADMP=2, No, for Smith. These are not
the service fields' 1/0 response codes. App rejected categorical numerical outputs.
93.93 seconds. [Actual response](ic_categorical_probes/open_admission.json).

### 4. Multiple award levels — blocked

**Question:** Did Smith College, Mount Holyoke College, and Wellesley College offer
bachelor's and master's degrees in 2024-25?

Source: LEVEL5=1 for all three. LEVEL7=1 for Smith and Mount Holyoke; LEVEL7=0,
Implied no, for Wellesley. App rejected categorical numerical outputs.
25.69 seconds. [Actual response](ic_categorical_probes/award_levels.json).

This asks about award levels offered, not actual awards conferred or every subject
available. The repaired app must retain that distinction.

### 5. Two-condition institution list — tool-batch exception

**Question:** Which Massachusetts degree-granting institutions offered both study
abroad and on-campus childcare for students' children in 2024-25? List their names.

Independent query joins HD2024 and IC2024 by UNITID, selects STABBR=MA,
DEGGRANT=1, SLO6=1 and STUSRV8=1. It finds **14** institution IDs, saved in source
expectations. The app raised ValueError: "Too many planning tool requests in one
call." The outer UI would display a request error; no list was produced.
19.12 seconds. [Actual exception/stages](ic_categorical_probes/combined_services.json).

Code inspection: `catalog_planner.model_plan` rejects more than four model tool
requests before its per-tool repair handler. More categorical projection support
alone will not fix this failure path. Do not claim every list fails for this reason.

### 6. Categorical filter plus numerical count — passed source check

**Question:** How many Massachusetts degree-granting institutions offered on-campus
childcare for students' children in 2024-25?

App returned **20**, matching the independent source query and institution IDs.
The plan uses code-backed state, degree-granting and Yes filters, retains unmatched
rows for coverage auditing, and counts complete cases. It does not sum Yes codes.
28.83 seconds. [Actual response](ic_categorical_probes/service_count.json).

Preserve this valid functionality. This scoped Massachusetts check does not resume
the paused national aggregate benchmark reconciliation.

### 7. Related concepts — blocked, including explanatory follow-up

**Question:** Did Wellesley College offer undergraduate distance education courses,
complete undergraduate distance education programs, or both in 2024-25?

Source: DSTNUGC=1, Yes; DSTNUGP=0, Implied no. The codebook defines a distance
program as one for which all required coursework can be completed through distance
courses. App rejected categorical numerical outputs. 21.40 seconds.
[Actual response](ic_categorical_probes/distance_distinction.json).

**Follow-up:** What is the difference between those two categories?

The app attempted another statistical plan and failed with "This aggregate needs
a numerical field or distinct identifier." It should explain the two inspected
concepts or clarify a genuinely ambiguous reference, even after a blocked answer.
25.08 seconds.
[Actual response](ic_categorical_probes/distance_definition_followup.json).

### 8. Cross-release category lookup — blocked and scope reduced

**Question:** Did Smith College accept Advanced Placement (AP) credits in both
2015-16 and 2024-25?

Source: CREDITS3=1, Yes, in both IC2015 and IC2024. App ultimately failed with
"Aggregate input is not a continuous numeric observation." Its final blocked
plan contained only 2024 despite the two requested releases. No incorrect partial
answer was published, but fixing the type error alone must not activate that
scope-reduced plan. 37.54 seconds.
[Actual response](ic_categorical_probes/temporal.json).

### 9. Numerical question with categorical dependency — identity confusion

**Question:** What percentage of Smith College undergraduates were formally registered
with disability services in the 2024-25 Institutional Characteristics release?
State the student observation year.

Source: DISAB=2, More than 3 percent; DISABPCT=38.00. Source variable definitions
identify **Fall 2023 undergraduates**, despite the 2024-25 release/table coverage.

App asked: "Which institution has the 167,835 undergraduates you mean?" It had
already identified Smith's UNITID 167835 but interpreted the rewritten bare number
as enrollment. It correctly mentioned the Fall 2023 population in the clarification,
but never answered 38%. 16.71 seconds.
[Actual response](ic_categorical_probes/conditional_numeric.json).

### 10. Mixed calendar/percentage answer — blocked

**Question:** For Smith College in the 2024-25 Institutional Characteristics release,
show its academic calendar system and the percentage of undergraduates formally
registered with disability services. State the student observation year.

Expected: Semester; 38% of Fall 2023 undergraduates. App selected CALSYS, DISAB and
DISABPCT but rejected the categorical outputs. 37.39 seconds.
[Actual response](ic_categorical_probes/mixed.json).

### 11. Code-label interpretation — two different failures

**Question:** In the 2024-25 Institutional Characteristics codebook, what does
"Implied no" mean for on-campus childcare, and how is it different from "Not reported"?

Source mappings: STUSRV8 has 0=Implied no, -1=Not reported, -2=Not applicable,
1=Yes, within a check-all-that-apply service question. The app routed this to the
statistical planner and exhausted its search limit. 23.66 seconds.
[Actual response](ic_categorical_probes/code_definition.json).

**Targeted rephrasing:** Define the label Implied no for on-campus childcare in the
2024-25 Institutional Characteristics codebook.

This reached the documentation route but treated the label plus topic, year and
survey as one definition term and returned bounded no-match. 0.10 seconds; no
model usage recorded. It did not falsely declare global source absence, but still
missed available code mappings.
[Actual response](ic_categorical_probes/definition_rephrase.json).

### 12. Unsupported quality inference — correct limitation, rough presentation

**Question:** Using only Institutional Characteristics, which has better academic
counseling services in 2024-25: Smith College or Mount Holyoke College?

App correctly said availability does not establish quality and did not rank the
schools or execute a proxy. However, it exposed numerical institution IDs and
internal numerical-only tool limitations. This is a substantive source-gap pass
with presentation issues, not a categorical retrieval pass. 39.07 seconds.
[Actual response](ic_categorical_probes/quality_gap.json).

### 13. Threshold category with a null companion value — incorrect interpretation

**Targeted probe:** In 2024-25 IPEDS Institutional Characteristics, what percentage
of undergraduates at Bentley University were formally registered with disability
services? Explain whether an exact percentage is available.

Source: DISAB=1, **3 percent or less**; DISABPCT is null. This supplies a bounded
response, not an exact percentage and not ordinary nonresponse. Variable prose
contains differing threshold phrasing; preserve the actual code label rather than
silently inventing a boundary convention.

App queried only DISABPCT and said the requested values were Not reported. It
labelled the row Academic year 2024-25 without identifying Fall 2023 student
observations. It preserved null instead of substituting zero, but lost the valid
categorical bound and source-date meaning. 62.46 seconds.
[Actual response](ic_categorical_probes/threshold.json).

## Changes required in the repair plan

1. Add typed categorical outputs, retaining existing numerical safeguards and the
   demonstrated working category-filter/count path.
2. Prevent summary misattribution and dummy-count charts. Validate row-level
   meaning across summary, table, source evidence and exports.
3. Represent conditional quantitative responses and source-defined bounds; inspect
   companion category fields before declaring numerical data missing.
4. Carry institution IDs structurally and retain readable names. Preserve original
   institutions, periods, fields, logical operators and answer type across repairs.
5. Extend documentation routing/retrieval to scoped category labels and contextual
   comparisons, including inspected fields from blocked statistical answers.
6. Recover safely from bounded tool-batch failures, retain diagnostics and avoid
   spending repeated model calls searching for a numerical workaround.
7. Make this exploratory matrix part of acceptance, with source SQL checks and
   deterministic regressions followed by representative live tests. Keep unknown
   cases distinct from demonstrated failures; no all-field correctness claim.

## Latency and cost observations

Recorded median answer-ready time was **27.26 seconds**, maximum **93.93 seconds**.
The first three cases were unusually slow relative to later cases; concurrent cold
execution makes these unsuitable as isolated performance claims. Answer-producing
calendar queries still used six or seven model calls to produce a dummy count.

The saved successful-return paths record 87 model calls and a combined app estimate
of $2.716. The tool-batch exception has no completed usage record, so these are
incomplete telemetry totals, not verified billed cost. Pricing was not independently
rechecked. The plan should improve targeted evidence retrieval and failure accounting
without adding a new classification model call to numerical questions.

## Limits and status

No application repairs, preset replacements, server activation or full regression
claims are part of this review. Existing correct counts and source-gap behavior
must remain protected. Negative cases for unknown codes, duplicate mappings,
additional releases and broader numerical functionality remain planned tests.
F027 owner wording review and national aggregate benchmark reconciliation retain
their previous statuses. The revised repair plan is ready for owner review.
