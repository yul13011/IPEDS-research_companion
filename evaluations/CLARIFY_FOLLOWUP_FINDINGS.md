# Clarification follow-ups & case investigation (v2)

_Generated 2026-11-03. Live multi-turn runs through the v2 engine: each question
was asked, the app's clarifying question was answered with a realistic reply, and
we recorded whether the app then produced a source-bound number._

## Answers given to clarifications → did the app then answer?

| Case | Question | Clarification reply given | Result after clarification |
|---|---|---|---|
| trap_faculty_ambiguity | How many faculty does Yale have? | "Full-time instructional staff, for 2024." | ✅ Yale, Fall 2024, all ranks: **2,995** |
| trap_netprice_lag | Yale's average net price for 2024-25? | "Yes, 2023-24 instead." | ✅ Yale 2023-24 net price (grant-aided): **$22,408** |
| trap_medical_scope | Average faculty salary at Yale? | "Full professors, 9-month, 2023-24, excl. medical." | ✅ Yale 2023-24 9-month avg: **$279,433** |
| fu_change_measure T1 | Yale's six-year grad rate, 2016 entering cohort | "Students who entered fall 2016." | ✅ Yale six-year rate (outcome 2022): **97.81%** |
| probe_sal_prof_smith | Avg salary of full professors, Smith, 2023-24 | "Full professors, 9-month, nonmedical." | ✅ Smith 2023-24 9-month avg: **$153,223** |
| probe_sal_cmp | Avg instructional salary, Smith/MtHolyoke/Wellesley | "All full-time nonmedical instructional, 9-month." | ✅ 3 schools: **$115,221 / $101,151 / $120,638** |
| probe_s_total_smith | Total staff at Smith, 2023 | "All staff, full- and part-time combined." | ✅ Smith Fall 2023 grand total: **1,483** |

Every clarify case resolved to a real number in one extra turn.

## #6 — why did v2 "fail" the full-professor-salary probe?

The **execution core answers it immediately** — calling `agent._answer()` directly
(bypassing the resolver) returns Smith 2023-24 average instructional salary
($152,890) on both Haiku and Sonnet. So the core is not the problem: the **v2
resolver over-clarified**. Its prompt tells it to pin the scope on "average
faculty salary" questions (correct for the bare `trap_medical_scope` case), and it
wrongly applied that to a question that already names the rank ("full professors")
and year. Fix for the port: only clarify faculty-salary scope when neither rank
nor appointment is specified; when a rank is named, fetch.

Caveat on the number: the reviewed salary measure is the **total instructional**
average equated to a 9-month contract, not a per-rank figure. True "full
professors only" needs a rank-filtered catalog plan (SAL by ARANK); the app
currently answers with the instructional-staff total. That is a measure-coverage
limitation, not a refusal.

## Notes on the other questions

- **PASS-EDIT** (grader term): the follow-up changed only the *display* of the
  previous result (sort order, chart type) and the app reused that immutable
  result with **no new data query** — exactly the desired behavior. Grader rule:
  the answer has numbers AND its mode is a presentation adjustment (or zero model
  calls). fu_resort and fu_rechart earned it in v2.
- **IC / categorical questions** (faq_services_smith, faq_ma_distance,
  probe_cat_city_smith): the app **did answer** ("Academic/career counseling:
  Yes", "83 institutions match…", "Northampton"), but these are categorical
  labels with no numeric `value`, and the frozen grader counts a pass only when a
  row carries a number. So they score NO-RESULT despite a correct answer — a
  grader limitation, identical for v1 and v2.
- **faq_bach_yale_1415**: the app returns **1,327**, which is the correct
  bachelor's grand total (C2015_A, CIPCODE 99). The frozen spec sums CTOTALT over
  *every* CIP row (5,308), double-counting program rows plus the total row — so
  the test is wrong, not the app. Same WRONG-NUMBER for v1 and v2.
