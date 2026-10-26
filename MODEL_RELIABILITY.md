# Model reliability and lower-cost strategy

Implemented October 25, 2026. **The interrupted qualification is now complete; Automatic is the default for new sessions.** See [MODEL_QUALIFICATION.md](MODEL_QUALIFICATION.md) for final results, the subsequent verified name/ID annotation repair, and limitations. The partial-run tables below are retained as implementation history. The original graduation-rate prototype and source databases are unchanged.

## Repairs

- Explicit adjacent-year source-release labels in definition requests normalize to the starting release year: `2024–25 release` and `2024–2025 release` mean `[2024]`. Distinct release labels and non-adjacent observation windows are preserved. Unexpected years are not silently discarded.
- The interpreter contract explicitly excludes geographic filters from institution extraction, while preserving full institution names and campus qualifiers. Geography remains in the analytical question for source-backed population filtering. Directory confirmation remains mandatory; ambiguous institution identities are not guessed.
- Analytical routes carrying a typed chart patch normalize to `mixed` before validation. The analytical question and all edits are retained; unsupported/conflicting patches still fail atomically. A conversation with edits remains invalid.
- Salary means and employee weights must have matching source-derived gender dimensions, actual/equated basis and contract lengths. Unqualified staff questions cannot substitute gender-restricted means. The same guard covers source weighted aggregates, weighted-mean expressions and salary × employee-count products, including sum/product/divide constructions. A user saying “weighted by” cannot override salary population incompatibility. Explicit cross-measure weighting such as tuition weighted by enrollment remains available under existing checks.
- Source-planner instructions reinforce matching salary counts, inspected rank selectors, and the distinction between named institutions and directory populations.

`prototype/tests/fixtures/salary_population_regression.json` retains the original correct and incorrect Sonnet plans. The incorrect men's-salary/all-staff-count product is rejected; the correct all-staff plan still matches independent SQLite arithmetic. This is a targeted population guard, not proof that arbitrary natural-language source semantics are fully understood.

## Conservative automatic strategy

Available in **About this prototype → Model settings → Model strategy → Automatic**, now the default for new sessions. Existing selections are preserved. Manual Sonnet and Haiku remain available.

| Stage | Model |
| --- | --- |
| Initial interpretation, greetings, chart edits | Haiku |
| Reviewed numerical planning and definition interpretation | Haiku |
| Broader catalog planning, including categorical source plans | Sonnet |
| Discovery source-grounded narrative | Sonnet |
| Rejected/incomplete initial interpretation | One Sonnet retry |

The automatic strategy intentionally keeps categorical catalog planning on Sonnet pending broader qualification, even though direct Haiku categorical results are promising. It chooses the source-planning stage rather than using a wording-based “easy question” classifier. Existing deterministic examples and extracts keep their existing path.

Only a structured interpretation failure triggers the one retry, before execution. Valid ambiguity, institution confirmation and source coverage gaps are not retried or overridden. Service/account failures do not trigger a redundant request to the same provider. Both attempts' returned usage is included if a retry succeeds. Every executor retains local schema, source, calculation and chart validation. A wrong interpretation that passes validation remains a risk; escalation cannot detect every such error.

The request-scoped policy uses a ContextVar, so manual model selections and concurrent requests remain isolated. The answer audit records the selected strategy, configured models and any interpretation retry. Manual Sonnet and Haiku settings remain available. API usage-limit failures now display an account-limit message in the UI.

## Initial live evidence and interruption (historical)

The expanded benchmark predeclared 26 distinct requests, including the original 13 plus reworded questions, long release labels, California geography, a male-only salary calculation and follow-up/chart variants. It planned two repeats per model (104 task attempts). It uses independent source SQL, exact category codes/institution sets, immutable-chart checks, unchanged seed histories and provider token metering. New results are stored separately from the original benchmark.

Anthropic's configured account usage limit interrupted the run after ten completed tasks per model. The provider explicitly reported that access resumes **2026-11-01 at 00:00 UTC** (October 31, 8 p.m. in America/New_York). Remaining unavailable requests are excluded from model correctness and latency; they are not evidence of model failures. The original raw attempt records remain for audit. The runner now stops on this account-limit error and supports resuming completed tasks without rerunning them to improve scores.

| Completed subset only | Sonnet | Haiku |
| --- | ---: | ---: |
| Passed / completed | 10/10 | 10/10 |
| Median end-to-end time | 10.82 s | 10.37 s |
| Estimated task API cost | $0.3753 | $0.0212 |

The completed cases were greeting, admission-rate definition, faculty discovery, admissions quantities, contextual yield, cohort trend, Smith services, Massachusetts distance-course list, axis reset and compound chart edits. The repaired definition and Massachusetts examples both passed. The mixed and weighted-salary fixes have offline coverage but were not reached by this live run. The reworded cases were not live-qualified. No automatic-policy live run completed. These results do not justify changing the default or projecting the automatic strategy's total savings.

Both live experiments ran concurrently, so timing should not be compared directly with earlier benchmark runs. Costs are estimates from returned usage, include caching, and exclude hosting/taxes/provider adjustments.

## Initial controlled narrative experiment (historical partial results)

Three fixed deterministic evidence packages (faculty, graduation rates, admissions), two repeats, four settings were predeclared. Every model/configuration received the same evidence digest per topic. This isolates writing settings but differs from live discovery's model-expanded source retrieval. The account limit also interrupted this experiment.

| Setting | Accepted / completed | Unavailable | Median writing time |
| --- | ---: | ---: | ---: |
| Sonnet, current 3,500-token budget | 4/5 | 1 | 7.49 s |
| Haiku, current 3,500-token budget | 2/5 | 1 | 15.97 s |
| Haiku, 7,000-token budget | 2/5 | 1 | 23.86 s |
| Haiku, reasoning disabled | 1/4 | 2 | 5.14 s |

The larger budget did not improve acceptance in this small sample. Failures included incomplete output, unsupported numeric claims, merged source concepts, dates/formatting and universal/equivalence claims. Sonnet also had a word-budget rejection. No validator was relaxed. Failed writing retains the source-verified template. No writing budget or reasoning default was changed; these are explicit experiment settings only.

## Verification and resumption

Offline tests cover release labels/windows, mixed-route normalization, the original salary failure, matching all-staff and male-only salary calculations, invalid weights, bounded retries, failed-attempt cost accounting, request isolation and Streamlit automatic-mode integration. A combined 112-method run passed 111 methods; a new UI fixture addressed the follow-up input before any conversation existed. After correcting that fixture, affected batches passed 7/7, 30/30 and finally 8/8, including the automatic UI and benchmark stop-on-limit checks. There are no unresolved test failures. This verifies the selected methods across a combined run and focused reruns, not a full registered-suite pass. Exact batches are recorded in `evaluations/model_reliability_verification.json`.

Evidence:

- `evaluations/model_reliability_comparison.json`: raw partial model run and provider failures, annotated for availability.
- `evaluations/model_reliability_summary.json`: completed-only correctness, latency/cost and narrative results.
- `evaluations/narrative_settings_comparison.json`: per-setting writing outcomes, evidence hashes and usage.
- `evaluations/summarize_model_reliability.py`: rebuilds the summary without provider calls.
- `evaluations/model_reliability_verification.json`: regression scope and final affected-test results.

After account access is restored, from `agent-redesign` with the project's Python environment:

```powershell
python -B -u evaluations/compare_models_reliability.py --live --resume
python -B -u evaluations/compare_models_reliability.py --live --automatic
python -B -u evaluations/compare_narrative_settings.py --live
python -B -u evaluations/summarize_model_reliability.py
```

The first command resumes direct Sonnet/Haiku qualification, retaining prior completed outcomes. The second writes a separate automatic-versus-Sonnet comparison. The writer probe is a fresh run and overwrites its experiment artifact; archive that artifact first if retaining both experiments. Live commands incur API charges; the paired runner stops at a $5 estimated spend cap and the writer probe at a $2 estimated spend check between batches. These are bounded benchmark budgets, not changes to the Anthropic account limit.

The initial adoption prerequisites were completion of the expanded comparisons, review of source-selection failures, and measurement of total cost including retries. That work and the separate post-annotation-repair checks are recorded in [MODEL_QUALIFICATION.md](MODEL_QUALIFICATION.md). No broader reliability claim is made from these bounded samples.
