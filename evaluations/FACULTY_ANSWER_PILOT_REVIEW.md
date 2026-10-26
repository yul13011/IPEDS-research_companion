# Faculty-answer workflow pilot — October 21, 2026

**Assessment: promising within this faculty-count pilot; revise the writing/qualification safeguards before production rollout.** The experiment demonstrates that the app's existing configured model can produce the requested direct answer with clearly labelled alternative populations. It does not require a model switch. The live app has not been changed.

## What was actually tested

An evaluation-only implementation uses the configured **Claude Sonnet 5.5**, a mandatory structured meaning review, exact local codebook evidence, the existing version-2 validator/executor, independent original-source SQL and a constrained answer writer. Code renders all numbers, the comparison table, medical-school scope, reporting institution, period, source and provisional/final status. Model prose cannot introduce numeric claims. Scope rows are never summed.

The proposed methodological default—unqualified faculty means staff with faculty status across occupations, with instructional faculty shown as a related population—was supplied explicitly to the model. This is a tested proposed policy, not a newly adopted production default or a discovery that IPEDS has a single universal meaning of faculty.

Evidence retrieval was deliberately limited to the relevant annual EAP codebook/table, with confirmed institution identities supplied. The review model did **not** receive expected answers or counts. It chose occupation, faculty status, employment and medical scope from source-backed categories. Code then bound the numerical fields and source keys. This tests interpretation/answer assembly after relevant documentation is found; it does **not** test unrestricted cross-survey discovery, general institution matching, arbitrary calculations, conversation memory or browser rendering.

Sixteen questions covered Yale and a paraphrase, Harvard, Smith College, Southern Connecticut State University, Fall 2020, full-time/nonmedical restrictions, part-time restrictions, explicit all-occupation faculty, instructional staff versus instructional faculty, missing institution, Yale College scope, percentages, ladder-faculty salary and unavailable future dates. Each question was run once in the completed suite; these are not repeated-run accuracy estimates.

## Findings

| Check | Observed result |
|---|---|
| Answer versus clarify | All 16 selected the expected route: 11 count answers and 5 clarification/limitation responses. |
| Leading population and explicit restrictions | Correct in the 11 count cases, including year, employment and medical scope. |
| Exact requested scope set | 10 of 11 matched exactly. “Instructional staff” also received an optional faculty-status subset row; its primary population was correct, but relevance/verbosity needs tighter control. |
| Numerical checks | All **52 returned cells** matched independent original-source SQL. Benchmark predicates used OCCUPCAT/FACSTAT, independently of the compiled EAPCAT row selection. |
| Yale target | Overall faculty status: **4,688 full-time + 1,047 part-time = 5,735**. Instructional faculty status: **2,995 + 805 = 3,800**. |
| Institution with unequal instructional populations | Smith: **422** all staff with faculty status; **406** instructional staff with faculty status. Separate source check: all instructional staff is **416**. The pilot used 406 for instructional faculty rather than confusing it with 416. |
| Initial readability | All answers fit the coarse 220-word limit, but explanations repeated scope qualifications. Median full-answer length: **165 words**. |
| Stricter writing pass | Median **122 words** after revision/fallback, about 26% shorter. Nine drafts met the length/sentence checks; two used a deterministic fallback after producing three sentences. |
| Source fidelity beyond numbers | Manual review caught one of those nine structurally accepted drafts calling instructional work “main job is teaching,” which is too narrow. Extra exact occupational-definition evidence and a targeted rewrite corrected it to include instruction combined with research/public service. Final disposition: **8 directly accepted drafts, 2 writing fallbacks, 1 source-definition repair**. |

Final reader-facing examples, including the Yale table: [final_answers.md](faculty_answer_pilot/final_answers.md). Raw initial answers remain in [answers.md](faculty_answer_pilot/answers.md). The final examples combine the original verified interpretation/results with the tested second writing pass; they are not screenshots or outputs of a deployed app.

Required medical-school inclusion/exclusion, reporting-unit, observation-period, release-status and overlap qualifications are code-owned and retained in the final examples. That prevents omission by the writer, but does not by itself prevent contradictory additional prose. The instructional-definition defect shows why source-constrained paraphrasing, semantic checks and a verified fallback remain necessary. Manual review is not an automated proof of arbitrary narrative correctness.

## Latency and estimated cost

The completed initial pilot measured full server-side evidence preparation, meaning review, execution, independent SQL checks and writing. It excluded general catalog discovery, institution-name extraction/clarification, network/browser rendering and UI download generation. Relevant documentation was preselected. Use these as scoped measurements, not production performance guarantees.

| Measurement | Observed |
|---|---:|
| Median count-answer time, 11 cases | **8.67 seconds** |
| Count-answer range | **6.95–17.52 seconds** |
| Yale initial complete pilot | **14.35 seconds; $0.035822** |
| Median initial count-answer API estimate | **$0.035462** |
| Completed 16-question pilot API estimate | **$0.487522** |
| Separate 11-answer writing refinement | **$0.162636** additional evaluation cost |
| Targeted instructional-definition repair | **3.87 seconds; $0.015740** additional evaluation cost |

All costs use the app's existing configured token-price estimator; they are not provider invoices. The writing refinement replaces the initial writing stage in a future implementation; the evaluation paid for both drafts. Early aborted development attempts are preserved separately and are not included in completed-suite totals. Their costs are not fully recorded; no all-development-spend total is asserted.

## Matched current-app baselines

Fresh conversations used the actual current analytical entry point, same configured model and same question text. No test prompt changes were applied to the app.

| Question | Current app in this run | Time | Estimated cost |
|---|---|---:|---:|
| How many faculty does Yale have? | Asked A/B between all instructional staff and instructional faculty; did not offer all-occupation faculty or a direct two-population count answer. | 30.04 s | $0.213984 |
| How many faculty does Smith College have? | Asked A/B between instructional faculty and all instructional staff; omitted the broader 422 faculty-status population. | 18.40 s | $0.175845 |
| Full-time Yale faculty excluding medical school | Returned **1,475** from the salary instructional population, rather than leading with the broader faculty-status count **1,731**, alongside instructional faculty **1,475**. | 15.72 s | $0.110071 |

The Yale baseline also described one option as excluding medical-school staff while its plan selected `EAPTOT` for all instructional staff; that field includes medical-school staff. This is a material prose/plan mismatch, even though metadata preflight accepted the option. Recorded separately as F023. These baselines differ from the earlier browser check that directly returned 3,800, demonstrating model-output variability rather than a code change between those observations.

The pilot's lower timings/costs cannot be credited solely to improved interpretation instructions: it had a deliberately smaller, preselected evidence package and deterministic count compilation. The current app also performs institution extraction and bounded catalog searching. No browser-latency comparison was made.

## Implementation implications

1. Make the meaning review mandatory and record its selected/alternative populations before execution. Use source-backed policies rather than expecting an unconstrained planner to rediscover the preferred definition on every call.
2. Compile simple headcount comparisons from verified scope selectors; keep related populations distinct and preserve user restrictions.
3. Derive medical scope, time, reporting unit and source qualifications from the actual selected fields. Validate prose against those facts; do not trust a model-written option label as evidence.
4. Give the writer the needed population definitions, including combined instructional/research/public-service work. Prefer structured short sentence blocks over a prose-only length instruction, and provide a safe verified fallback without discarding good results.
5. Tighten the rule for when an extra definition is useful. The exact-profile mismatch was over-answering, not a wrong primary count.
6. Run repeated, broader-topic and actual chat/UI follow-up checks before claiming this is a general IPEDS solution. The present experiment supports a faculty-count implementation trial, not universal deployment.

## Reproducible artifacts and development findings

- `faculty_answer_pilot.py`: interpretation, source binding, independent SQL checks, initial writer and matched baselines.
- `faculty_answer_pilot/results.json`, `api_calls.json`, annual evidence/result JSON files: full completed-suite audit.
- `refine_faculty_pilot_writing.py`, `writing_refinement.json`, `writing_refinement_calls.json`: stricter writing trial, including rejected outputs.
- `repair_faculty_pilot_paraphrase.py`, `semantic_repair.json`: diagnosed semantic repair and exact source record.
- `finalize_faculty_pilot.py`, `final_writing_results.json`, `summary.json`: safe fallback/final example assembly and summary metrics.
- `test_faculty_answer_pilot.py`: four guard tests passed, covering original-source counts, invalid evidence/categories/years, unconfirmed identity, invented narrative numbers/citations and required qualifications.
- Two early attempts are preserved in `faculty_answer_pilot_attempt1` and `faculty_answer_pilot_attempt2`. They exposed an over-strict requirement to duplicate numeric-field citations and a missing source-key filter in the experimental compiler. Numeric field binding was moved to code; all 11 expected count-plan shapes were verified offline before the completed live suite. These aborted attempts are not counted as successful tests.

Original source databases/codebooks and production app code were not modified. National/sector aggregate benchmarking remains paused.
