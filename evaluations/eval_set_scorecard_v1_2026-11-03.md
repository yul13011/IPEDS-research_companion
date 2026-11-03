# Eval scorecard — v1

Run 2026-11-03T13:19:12.046232+00:00. Spent **$2.3836** / $5.0 cap. Cases: 54.

## Headline

- **Overall pass:** 33/54
- **False refusals (follow-ups wrongly blocked):** 3

## By category

| Category | Pass | Total |
| --- | --- | --- |
| behavioral | 11 | 18 |
| faq | 3 | 7 |
| followup | 2 | 8 |
| numeric | 9 | 12 |
| refuse | 6 | 6 |
| trap | 2 | 3 |

Median turn latency: 16.4s over 62 turns.

## Per-case

| Case | Cat | Pass | Turn verdicts |
| --- | --- | --- | --- |
| fu_netprice_narrow | followup | ❌ | WRONG-NUMBER → WRONG-NUMBER |
| fu_swap_institution | followup | ❌ | CORRECT → FALSE-REFUSAL |
| fu_add_year | followup | ❌ | ANSWERED → FALSE-REFUSAL |
| fu_resort | followup | ❌ | BLOCKED → REVIEW-EDIT |
| fu_rechart | followup | ❌ | BLOCKED → FALSE-REFUSAL |
| fu_go_back | followup | ❌ | BLOCKED → NO-RESULT → ANSWERED |
| fu_change_measure | followup | ✅ | ANSWERED → ANSWERED |
| fu_add_institution | followup | ✅ | ANSWERED → CORRECT |
| faq_admrate_yale | faq | ✅ | CORRECT |
| faq_cost_harvard | faq | ✅ | ANSWERED |
| faq_grant_pct_ivies | faq | ❌ | CLARIFY |
| faq_bach_yale_1415 | faq | ❌ | WRONG-NUMBER |
| faq_instr_staff_yale | faq | ✅ | ANSWERED |
| faq_services_smith | faq | ❌ | NO-RESULT |
| faq_ma_distance | faq | ❌ | NO-RESULT |
| refuse_faculty_sat | refuse | ✅ | PASS-REFUSE |
| refuse_nonbinary_faculty | refuse | ✅ | PASS-REFUSE |
| refuse_salary_by_field | refuse | ✅ | SOFT-DECLINE |
| refuse_gradrate_2030 | refuse | ✅ | SOFT-DECLINE |
| refuse_student_debt | refuse | ✅ | SOFT-DECLINE |
| refuse_student_names | refuse | ✅ | PASS-REFUSE |
| trap_faculty_ambiguity | trap | ✅ | PASS-CLARIFY |
| trap_netprice_lag | trap | ✅ | PASS-CLARIFY |
| trap_medical_scope | trap | ❌ | REVIEW-ANSWERED |
| probe_c_mast_yale | numeric | ✅ | CORRECT |
| probe_c_doc_harv | numeric | ✅ | CORRECT |
| probe_c_cmp_bach | behavioral | ✅ | ANSWERED |
| probe_al_books_harv | numeric | ✅ | CORRECT |
| probe_al_ebooks_yale | numeric | ✅ | CORRECT |
| probe_sal_prof_smith | numeric | ✅ | CORRECT |
| probe_sal_cmp | behavioral | ✅ | ANSWERED |
| probe_f_tuitrev_yale | numeric | ✅ | CORRECT |
| probe_f_expenses_yale | behavioral | ✅ | ANSWERED |
| probe_f_endow_harv | behavioral | ✅ | ANSWERED |
| probe_eap_fac_yale | behavioral | ✅ | ANSWERED |
| probe_s_total_smith | behavioral | ✅ | ANSWERED |
| probe_om_rate_yale | numeric | ❌ | BLOCKED |
| probe_om_behav | behavioral | ❌ | CLARIFY |
| probe_effy_yale | numeric | ✅ | CORRECT |
| probe_ef_dist_yale | behavioral | ✅ | ANSWERED |
| probe_ef_race_yale | behavioral | ✅ | ANSWERED |
| probe_cost_tuit_smith | numeric | ✅ | CORRECT |
| probe_cost_roomboard_mh | numeric | ❌ | NO-GROUND-TRUTH |
| probe_cost_netprice_we | numeric | ❌ | BLOCKED |
| probe_adm_act_yale | numeric | ✅ | CORRECT |
| probe_adm_req_yale | behavioral | ✅ | ANSWERED |
| probe_agg_gradrate | behavioral | ❌ | NO-RESULT |
| probe_agg_instcount | behavioral | ❌ | NO-RESULT |
| probe_agg_totalenr | behavioral | ✅ | ANSWERED |
| probe_def_retention | behavioral | ❌ | NO-RESULT |
| probe_disc_finance | behavioral | ❌ | NO-RESULT |
| probe_trend_effy_yale | behavioral | ❌ | NO-RESULT |
| probe_cat_housing_smith | behavioral | ✅ | ANSWERED |
| probe_cat_city_smith | behavioral | ❌ | NO-RESULT |