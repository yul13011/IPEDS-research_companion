# IPEDS agent eval set — the 54 cases, the questions asked, and v1 vs v2 results

_Generated 2026-11-03 from the frozen `evaluations/eval_set.py` and the run files. Ground truth for numeric cases is computed by direct SQL against the release SQLite, never by the model. v2 reflects the resolver after the salary-scope and cohort fixes; faq_bach is re-graded under the user-approved spec correction._

## Headline

| | v1 baseline | v2 |
|---|---|---|
| Overall pass | 33/54 | **42/54** |
| False refusals on follow-ups | 3 | **0** |
| Spend (USD, $5 cap) | $2.3836 | $0.905 |

| Category | v1 pass | v2 pass | total |
|---|---|---|---|
| A. Follow-up sequences | 2 | 8 | 8 |
| B. FAQs (example chips + cost) | 3 | 5 | 7 |
| C. Should-refuse / graceful decline | 6 | 6 | 6 |
| D. Traps (needs a subtlety) | 2 | 3 | 3 |
| E. Numeric core (reused coverage-sweep probes) | 9 | 8 | 12 |
| F. Behavioral core (reused probes) | 11 | 12 | 18 |

Verdict glossary: CORRECT = number matches SQL ground truth; ANSWERED = produced a result (behavioral); PASS-REFUSE / PASS-CLARIFY = correctly declined/clarified; PASS-EDIT = reused prior result with a view change, no re-fetch; FALSE-REFUSAL = a valid follow-up wrongly blocked; WRONG-NUMBER = answered but value != ground truth; CONSTRAINT-MISS = right values, wrong institution/measure count; BLOCKED/CLARIFY/NO-RESULT = did not answer; NO-GROUND-TRUTH = the frozen spec could not be resolved against the data.

Note: several v2 "fails" are test-set/grader limitations, not app errors — see the footnotes. A few single probes vary run-to-run (low-temperature resolver nondeterminism).

## A. Follow-up sequences

### `fu_netprice_narrow`  —  COST/IC (price)
Case result: v1 **fail**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What is Yale's net price compared to other Ivy League schools? | WRONG-NUMBER | CORRECT |
| T2 | I only need the average net price for students awarded grant or scholarship aid, 2023-24. | WRONG-NUMBER | CORRECT |

### `fu_swap_institution`  —  ADM (admissions)
Case result: v1 **fail**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | Show Yale's admission rate for fall 2024. | CORRECT | CORRECT |
| T2 | What about Harvard? | FALSE-REFUSAL | CORRECT |

### `fu_add_year`  —  EFFY (12-mo enroll)
Case result: v1 **fail**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What was Yale's 12-month unduplicated headcount for 2022-23? | ANSWERED | ANSWERED |
| T2 | Now plot it from 2015 through 2024 as a trend. | FALSE-REFUSAL | ANSWERED |

### `fu_resort`  —  COST/IC (price)
Case result: v1 **fail**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | Compare net price for grant-aided students across the Ivy League in 2023-24. | BLOCKED | ANSWERED |
| T2 | Sort them from lowest to highest. | REVIEW-EDIT | PASS-EDIT |

### `fu_rechart`  —  COST/IC (price)
Case result: v1 **fail**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | Compare net price for grant-aided students across the Ivy League in 2023-24. | BLOCKED | ANSWERED |
| T2 | Make it a bar chart. | FALSE-REFUSAL | PASS-EDIT |

### `fu_go_back`  —  COST/IC (price)
Case result: v1 **fail**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | Compare net price for grant-aided students across the Ivy League in 2023-24. | BLOCKED | ANSWERED |
| T2 | Just Yale and Harvard. | NO-RESULT | ANSWERED |
| T3 | Actually, go back to all eight. | ANSWERED | ANSWERED |

### `fu_change_measure`  —  GR / C
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What was Yale's six-year bachelor's graduation rate for the 2016 entering cohort? | ANSWERED | ANSWERED |
| T2 | Show the number of bachelor's degrees it awarded instead. | ANSWERED | ANSWERED |

### `fu_add_institution`  —  ADM (admissions)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | Compare Yale and Harvard admission rates in fall 2024. | ANSWERED | ANSWERED |
| T2 | Add Princeton. | CORRECT | CORRECT |

## B. FAQs (example chips + cost)

### `faq_admrate_yale`  —  ADM (admissions)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What was Yale's admission rate in fall 2024? | CORRECT | CORRECT |

### `faq_cost_harvard`  —  COST/IC (price)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How much does it cost to attend Harvard College in 2024-25? | ANSWERED | ANSWERED |

### `faq_grant_pct_ivies`  —  SFA (aid)
Case result: v1 **fail**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What percentage of undergraduates received grants or scholarships in 2023-24? Compare eight Ivy League institutions. | CLARIFY | ANSWERED |

### `faq_bach_yale_1415`  —  C (completions)
Case result: v1 **fail**, v2 **PASS**  (re-graded CORRECT under the user-approved spec fix: CIPCODE=99 grand total = 1327)

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How many bachelor's degrees did Yale award in 2014-15? | WRONG-NUMBER | CORRECT |

### `faq_instr_staff_yale`  —  EAP/S (staff)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How many full-time and part-time instructional staff did Yale have in fall 2024? | ANSWERED | ANSWERED |

### `faq_services_smith`  —  IC (categorical)
Case result: v1 **fail**, v2 **fail**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What student services did Smith College report in the 2024-25 IPEDS release: academic counseling, career placement, and on-campus childcare? | NO-RESULT | NO-RESULT |

### `faq_ma_distance`  —  IC (distance ed)
Case result: v1 **fail**, v2 **fail**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | Which Massachusetts degree-granting institutions reported undergraduate distance education in the 2024-25 IPEDS release? | NO-RESULT | NO-RESULT |

## C. Should-refuse / graceful decline

### `refuse_faculty_sat`  —  (none)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What is the average SAT score of Yale's faculty? | PASS-REFUSE | PASS-REFUSE |

### `refuse_nonbinary_faculty`  —  EAP/S (staff)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How many nonbinary faculty does Smith College employ? | PASS-REFUSE | PASS-REFUSE |

### `refuse_salary_by_field`  —  SAL (salaries)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What is Yale's faculty salary by academic field? | SOFT-DECLINE | PASS-REFUSE |

### `refuse_gradrate_2030`  —  GR
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What was Harvard's graduation rate in 2030? | SOFT-DECLINE | PASS-REFUSE |

### `refuse_student_debt`  —  (none)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What is the average student loan debt of Yale graduates? | SOFT-DECLINE | PASS-REFUSE |

### `refuse_student_names`  —  (none)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | List every Yale student's name and GPA. | PASS-REFUSE | PASS-REFUSE |

## D. Traps (needs a subtlety)

### `trap_faculty_ambiguity`  —  EAP/S (staff)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How many faculty does Yale have? | PASS-CLARIFY | PASS-CLARIFY |

### `trap_netprice_lag`  —  COST/IC (price)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What is Yale's average net price for 2024-25? | PASS-CLARIFY | PASS-CLARIFY |

### `trap_medical_scope`  —  SAL (salaries)
Case result: v1 **fail**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What is the average faculty salary at Yale? | REVIEW-ANSWERED | PASS-CLARIFY |

## E. Numeric core (reused coverage-sweep probes)

### `probe_c_mast_yale`  —  C (completions)
Case result: v1 **PASS**, v2 **fail**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How many master's degrees did Yale award in 2023? | CORRECT | WRONG-NUMBER |

### `probe_c_doc_harv`  —  C (completions)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How many research doctoral degrees did Harvard award in 2023? | CORRECT | CORRECT |

### `probe_al_books_harv`  —  AL (libraries)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How many physical books were in Harvard's library collection in 2023? | CORRECT | CORRECT |

### `probe_al_ebooks_yale`  —  AL (libraries)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How many digital/electronic books does Yale's library have in 2023? | CORRECT | CORRECT |

### `probe_sal_prof_smith`  —  SAL (salaries)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What was the average salary of full professors at Smith College in 2023-24? | CORRECT | CORRECT |

### `probe_f_tuitrev_yale`  —  F (finance)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What was Yale's revenue from tuition and fees in 2022-23? | CORRECT | CORRECT |

### `probe_om_rate_yale`  —  OM (outcomes)
Case result: v1 **fail**, v2 **fail**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What share of Yale's entering degree-seeking cohort earned an award within 8 years (2023)? | BLOCKED | BLOCKED |

### `probe_effy_yale`  —  EFFY (12-mo enroll)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What was Yale's 12-month unduplicated headcount for 2022-23? | CORRECT | CORRECT |

### `probe_cost_tuit_smith`  —  COST/IC (price)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What was the published tuition and fees at Smith College for 2023-24? | CORRECT | CORRECT |

### `probe_cost_roomboard_mh`  —  COST/IC (price)
Case result: v1 **fail**, v2 **fail**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What was the on-campus room and board charge at Mount Holyoke College for 2023-24? | NO-GROUND-TRUTH | NO-GROUND-TRUTH |

### `probe_cost_netprice_we`  —  COST/IC (price)
Case result: v1 **fail**, v2 **fail**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What was the average net price for grant-aided students at Wellesley in 2022-23? | BLOCKED | NO-GROUND-TRUTH |

### `probe_adm_act_yale`  —  ADM (admissions)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How many of Yale's admitted students submitted ACT scores for fall 2024? | CORRECT | CORRECT |

## F. Behavioral core (reused probes)

### `probe_c_cmp_bach`  —  C (completions)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | Compare the number of bachelor's degrees Yale and Princeton awarded in 2023. | ANSWERED | ANSWERED |

### `probe_sal_cmp`  —  SAL (salaries)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | Compare the average instructional faculty salary at Smith, Mount Holyoke, and Wellesley in 2023-24. | ANSWERED | ANSWERED |

### `probe_f_expenses_yale`  —  F (finance)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What were Yale's total expenses in 2022-23? | ANSWERED | ANSWERED |

### `probe_f_endow_harv`  —  F (finance)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What was the value of Harvard's endowment at year end 2022-23? | ANSWERED | ANSWERED |

### `probe_eap_fac_yale`  —  EAP/S (staff)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How many full-time instructional faculty with faculty status does Yale have in fall 2023? | ANSWERED | ANSWERED |

### `probe_s_total_smith`  —  EAP/S (staff)
Case result: v1 **PASS**, v2 **fail**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How many total staff does Smith College employ in 2023? | ANSWERED | CLARIFY |

### `probe_om_behav`  —  OM (outcomes)
Case result: v1 **fail**, v2 **fail**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What is the 8-year completion rate for Pell recipients at Arizona State University? | CLARIFY | NO-RESULT |

### `probe_ef_dist_yale`  —  EF (distance ed)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How many Yale students were enrolled exclusively in distance education in fall 2023? | ANSWERED | ANSWERED |

### `probe_ef_race_yale`  —  EF (enrollment)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | Show Yale's undergraduate enrollment by race and ethnicity for fall 2023. | ANSWERED | ANSWERED |

### `probe_adm_req_yale`  —  ADM (admissions)
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What are Yale's admissions test score requirements? | ANSWERED | ANSWERED |

### `probe_agg_gradrate`  —  Aggregate
Case result: v1 **fail**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What was the overall six-year graduation rate for four-year institutions in the United States for the 2016 entering cohort? | NO-RESULT | ANSWERED |

### `probe_agg_instcount`  —  Aggregate
Case result: v1 **fail**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | How many public four-year institutions are there in 2023? | NO-RESULT | ANSWERED |

### `probe_agg_totalenr`  —  Aggregate
Case result: v1 **PASS**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What was the total fall enrollment across all U.S. degree-granting institutions in 2023? | ANSWERED | ANSWERED |

### `probe_def_retention`  —  Definition
Case result: v1 **fail**, v2 **fail**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What is the definition of the first-year retention rate? | NO-RESULT | NO-RESULT |

### `probe_disc_finance`  —  Discovery
Case result: v1 **fail**, v2 **fail**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What data do you have on institutional finances? | NO-RESULT | NO-RESULT |

### `probe_trend_effy_yale`  —  Trend
Case result: v1 **fail**, v2 **PASS**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | Plot Yale's 12-month enrollment from 2015 to 2024. | NO-RESULT | ANSWERED |

### `probe_cat_housing_smith`  —  IC (categorical)
Case result: v1 **PASS**, v2 **fail**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | Does Smith College provide on-campus housing? | ANSWERED | NO-RESULT |

### `probe_cat_city_smith`  —  HD (directory)
Case result: v1 **fail**, v2 **fail**

| Turn | Question asked | v1 verdict | v2 verdict |
|---|---|---|---|
| T1 | What city is Smith College located in? | NO-RESULT | NO-RESULT |
