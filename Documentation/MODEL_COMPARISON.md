# Sonnet versus Haiku in the current app

**Historical initial comparison.** The larger completed qualification, final annotation repair and current Automatic default are documented in [MODEL_QUALIFICATION.md](MODEL_QUALIFICATION.md). The original measurements below are preserved.

Compared October 25, 2026. Models: `claude-sonnet-5-5` and `claude-haiku-5-5`. No application defaults or production behavior were changed.

## Main result

Haiku was approximately 11.6 times cheaper in this workload, with similar speed on matched successful cases. Core task completion was close: Sonnet 21/26, Haiku 22/26. This small difference is not evidence that either model is generally more accurate. The failure types and the app's validators matter more than this one-task difference.

| Measure | Sonnet 5.5 | Haiku 5.5 |
| --- | ---: | ---: |
| Core checks passed | 21/26 | 22/26 |
| Median time, same 18 successful case pairs | 6.50 s | 6.68 s |
| Estimated cost, all 26 attempts including failures | $0.91074 | $0.07834 |
| Provider calls, excluding warmup | 53 | 66 |
| Output tokens, excluding warmup | 20,159 | 42,139 |
| Discovery AI narratives accepted | 2/2 | 0/2 |

Haiku saved approximately 91.4% in estimated token charges. Total estimated benchmark spend including both warmups was $1.00027. Usage was available for every recorded request. These are public standard-rate estimates from returned usage, not an invoice; taxes, provider adjustments, hosting and local compute are excluded.

## Method

Thirteen distinct tasks were run twice per model, 52 task attempts plus two excluded warmups. Each pair ran concurrently, with submission order alternated. Both models received the same standardized source-backed seed history for follow-ups and chart edits. Other tasks started without conversation. Timing includes initial interpretation, source/planning model calls, local validation and query execution; it excludes browser rendering and download generation.

The current app settings were retained rather than equalizing reasoning effort: the router uses each model's default behavior; analytical planning uses Sonnet's configured medium effort and Haiku's configured low effort. Consequently, this is a comparison of the app's two configured options, not an isolated model-capability benchmark.

Numerical answers were checked against independently specified SQLite queries. Categorical responses were checked against actual source codes; school lists against exact source-derived institution sets. Chart edits had to preserve the original result and apply the requested settings. The aid-ambiguity case required relevant clarification without an invented result. Discovery's core check required source-backed topics/evidence; acceptance of its optional AI narrative is reported separately. A verified template fallback therefore passes the core discovery check, but is not counted as a successful AI rewrite.

Cost was metered around every provider response, including unsuccessful application attempts. Prefix caching and extra planning calls are reflected in the estimates. The benchmark did not retry failed tasks to improve scores. Only the school-list grading reference was corrected after source review, as documented below.

## Task results

Each pass count is out of two. Times are medians of both attempts, including failed attempts; they must be read alongside completion counts.

| Task | Sonnet passed | Haiku passed | Sonnet seconds | Haiku seconds |
| --- | ---: | ---: | ---: | ---: |
| Greeting | 2 | 2 | 3.42 | 1.74 |
| Admission-rate definition, 2024–25 release | 2 | 0 | 2.22 | 3.21 |
| Faculty data discovery | 2 | 2 | 15.79 | 25.89 |
| Yale applicants, admits, admission rate | 2 | 2 | 7.35 | 9.10 |
| Contextual matriculants and yield | 2 | 2 | 7.72 | 9.06 |
| Ten-year graduation cohort trend | 2 | 2 | 7.20 | 7.02 |
| Smith student-service categories | 2 | 2 | 10.14 | 13.79 |
| Massachusetts distance-course institution list | 0 | 2 | 3.34 | 15.03 |
| Numeric chart-axis reset | 2 | 2 | 4.56 | 6.45 |
| Compound color/legend/font/title edit | 2 | 2 | 4.20 | 5.57 |
| Ambiguous financial-aid request | 2 | 2 | 3.34 | 3.08 |
| Weighted salary across three ranks | 1 | 0 | 26.91 | 40.46 |
| Numerical comparison plus blue bars | 0 | 2 | 2.37 | 8.76 |

Median time across all attempts was 5.14 s for Sonnet and 7.55 s for Haiku, but Sonnet's quick failures make that comparison misleading. The 6.50 versus 6.68 s matched-success medians in the main table use only task/round pairs that both models completed correctly.

## What failed

### Haiku

- Both definition requests expanded the single source release "2024–25" into source years 2024 and 2025. The local year validator blocked the unavailable year; no incorrect definition was published.
- Both advanced salary requests failed to complete. One remained an unexecuted source proposal; the other was blocked because a population query also contained a named institution.
- Both discovery narratives exhausted the 3,500-output-token budget without a complete accepted structured narrative. The app retained its source-verified template. Haiku produced more output tokens and made more provider calls overall, so its lower token rate did not translate to uniformly lower latency.

### Sonnet

- Both Massachusetts-list requests mistakenly extracted "Massachusetts" as an institution. The identity resolver asked which institution was meant instead of executing the state filter.
- Both mixed analysis/chart requests attached chart changes to a route that the dispatcher rejects. These were blocked before analysis.
- The second salary calculation returned an incorrect value that passed current local validation. The model selected the men's average salary field `SA09MAM` but weighted it with the all-staff count `SA09MCT`; its prose assumptions incorrectly named the all-staff average `SA09MAT`. The correct all-staff weighted mean is **$239,023.53**. The returned value was **$244,824.97**. The first Sonnet attempt selected the correct field and matched the independent query.

That last result is a substantive validation gap, not merely a routing inconvenience. Units and periods matched, but the value and weight populations did not. Gender/population compatibility between averages and weights must be enforced before relying on either model for unrestricted weighted calculations. A more expensive model alone does not solve this.

## Grading-reference correction

The initial school-list fixture used `DSTNCED1=1`, which means undergraduate programs/courses offered through distance education and yields 83 degree-granting Massachusetts institutions. The question asked broadly about institutional distance-course offerings; its direct field is `DISTCRS=1`, which yields 95. The codebook identifies `DISTCRS` as "Distance education courses offered" (record 136131).

Haiku selected that broader course field and returned the correct 95-institution set in both passes. The summary corrects the grade against the proper source definition. Prompts, model answers and timing/cost records were not changed. Original grades remain in the raw record; the summary preserves `raw_passed` alongside corrected checks. The benchmark script's fixture was corrected for future runs.

## Recommendation

Do not switch the whole app to Haiku or assume Sonnet is uniformly safer based on these results. Haiku is a promising economical option for routine numerical questions, categorical lookups, chart edits and mixed requests. Keep Sonnet available for escalation and source-grounded writing, but retain validation regardless of model.

Before adopting a default-plus-fallback policy, address source-release normalization, geography-versus-institution extraction, mixed-route consistency, and the salary population/weight validation gap. Then rerun these fixed cases and a larger varied set. Haiku's narrative generation budget/effort can be tested separately; increasing it may improve completion at a latency cost.

No app default was changed during this comparison. Two repeats of thirteen tasks cannot establish production reliability or general model superiority.

## Pricing and evidence

Official rates checked October 25: Sonnet input/output $2/$10 per million tokens; Haiku $0.10/$0.50 for prompts up to 100,000 tokens, with higher rates above that threshold. All benchmark prompts were below 100,000 tokens (maximums approximately 37,593 Sonnet and 45,448 Haiku). Cache prices and token usage differ, explaining why the measured saving was 11.6-fold rather than the 20-fold base-rate difference. See [Sonnet pricing](https://platform.claude.com/docs/en/models/sonnet-5-5/overview) and [Haiku pricing](https://platform.claude.com/docs/en/models/haiku-5-5/overview).

- `evaluations/model_comparison_current.json`: original task outcomes, compact answers/plans, provider usage and per-call timings.
- `evaluations/model_comparison_summary.json`: corrected grades, matched-success latency, cost and failure details.
- `evaluations/compare_models_current.py`: reproducible paired benchmark; requires `--live`, incurs normal API charges, and stops further task pairs at a $5 estimated spend cap.
- `evaluations/summarize_model_comparison.py`: source-reference correction and summary generation; makes no provider calls.
