# Lower-cost model policy: completed qualification

October 25, 2026. The owner restored Anthropic account access and the interrupted trials resumed. Completed outcomes were retained; unavailable attempts were retried without replacing completed failures.

## Implemented decision

**Automatic is the default for new Streamlit sessions.** Existing session selections are preserved. About → Model settings → Model strategy still offers manual Sonnet and Haiku.

Automatic uses Haiku for initial interpretation, reviewed numerical planning and chart instructions. It uses Sonnet for broader catalog planning (including categorical source plans) and discovery writing. A rejected or incomplete interpretation gets one Sonnet retry before execution. Genuine ambiguities, institution confirmations and source coverage gaps are not overridden. Both attempts are charged to the usage audit. All source, population, arithmetic, identity and chart checks remain active.

The decision rests on lower measured cost, successful routine and advanced-source checks, and targeted post-repair verification. It is not a claim of general model superiority or production reliability. The per-request policy is isolated with ContextVar; the provider model identifiers and rate calculations remain distinct from the UI's Automatic strategy.

## Direct Haiku versus Sonnet

Twenty-six predeclared tasks, two repeats per model: 104 task attempts. This is an app-workflow comparison, not a pure model-capability test.

| Measure | Sonnet | Haiku |
| --- | ---: | ---: |
| Application checks passed | 49/52 | 46/52 |
| Estimated task API cost, including failed attempts | $1.5763 | $0.1093 |
| Median time on the same 43 successful pairs | 6.83 s | 7.37 s |
| Discovery narrative rewrites accepted in the live pipeline | 4/4 | 0/4 |

Haiku cost about 93% less in this direct comparison, but did not reliably complete the salary queries and had a rejected follow-up interpretation and a categorical coverage failure. Its discovery results retained verified templates when optional writing failed. Those writing failures are reported separately from the core discovery checks.

The three Sonnet application failures were mixed requests affected by the annotation bug diagnosed below. They should not be described as evidence that Sonnet omitted the institutions. Original scores remain recorded rather than being rewritten after the code repair.

## Automatic versus Sonnet

A separate paired run used the same 26 tasks, two repeats per strategy. Cost includes every metered provider response, including failed application attempts, cache reads/writes and both automatic interpretation retries. Warmups are excluded from task cost and latency.

| Main run, before the final annotation repair | Sonnet | Automatic |
| --- | ---: | ---: |
| Application checks passed | 48/52 | 51/52 |
| Estimated task API cost | $1.4943 | $0.9939 |
| Median time on the same 48 successful pairs | 8.77 s | 9.34 s |
| Accepted discovery rewrites | 4/4 | 4/4 |

Automatic saved **33.49%** in estimated API charges. It was approximately 0.57 seconds slower at the matched-success median. This supports a cost reduction, not a latency improvement. Do not extrapolate the exact percentage to a different workload; discovery and catalog-heavy usage still incur Sonnet charges.

The main-run scores include one local SQLite `OperationalError: interrupted` for each strategy on the same mixed prompt. This coincided with a concurrent regression run; resource contention is a plausible cause, not an established diagnosis. Both failures remain in the raw results and the main-run denominator. An isolated follow-up had no SQLite timeouts: Automatic passed 4/4, while Sonnet's 0/4 exposed the annotation mismatch described next.

No failed statistical case in these checks published incorrect numerical values. That is a bounded observation about these cases, not proof that the validators catch every possible semantic error.

## Final mixed-request repair

The diagnostic captured Sonnet returning both requested institutions as `Yale University (130794)` and `Harvard University (166027)`. The app accepted only the `(UNITID 130794)` spelling. Consequently, the original missing-institution validation message was misleading: the model included both schools, but the resolver did not recognize the representation.

Both annotation spellings now resolve only when the complete official name matches the stated ID in the local directory. Case/spacing differences are normalized. Conflicting pairs such as `Yale University (166027)`, invented campuses and `Yale College (130794)` remain unresolved. Reviewed and catalog execution paths use the same checked identity. No fuzzy campus selection or unverified name/ID override was added.

The repaired mixed requests were run twice each against both strategies, in a separate artifact:

| Post-repair targeted verification | Sonnet | Automatic |
| --- | ---: | ---: |
| Correct source-backed result and requested blue bars | 4/4 | 4/4 |

These checks do not replace the original failures or form a second full 104-attempt qualification. The repair changes identity normalization, not model prompts, source fields or calculations. Offline regressions also cover identity conflicts and the affected source executors.

Two additional reliability improvements were retained: reviewed literal safe aliases cannot disappear solely because model extraction omitted them, and rejected reviewed plans retain their charged API usage in the app's audit. A metering discrepancy observed in the old rejected-plan path did not affect the benchmark costs, which were recorded independently at the provider boundary.

## Narrative experiment

Three fixed deterministic evidence packages, two repeats and four configurations: all 24 trials completed. The same evidence hash was supplied to each configuration per topic. This isolates writer settings; it differs from the model-expanded discovery packages in the app's live workflow.

| Configuration | Accepted | Median writer time | Estimated six-trial cost |
| --- | ---: | ---: | ---: |
| Sonnet, current 3,500-token allowance | 4/6 | 7.45 s | $0.4077 |
| Haiku, current 3,500-token allowance | 2/6 | 16.13 s | $0.0272 |
| Haiku, 7,000-token allowance | 3/6 | 20.59 s | $0.0335 |
| Haiku, reasoning disabled | 1/6 | 5.14 s | $0.0212 |

The larger Haiku allowance improved completion by one trial but remained unreliable and slower. Disabling reasoning was faster but had the lowest acceptance. Sonnet's two rejections exceeded the reading budget. Haiku rejections also included unsupported claims/numbers, incomplete output, merged concepts, invalid coverage and dates/formatting. Validators were not loosened. Automatic keeps Sonnet writing at the existing allowance and retains the verified template if writing fails. Manual Haiku's writing defaults are unchanged.

## Grading and limits

The school lists use exact source-derived institution sets; salaries use independently specified source SQL; categorical answers use exact codes; chart edits preserve immutable results and seed histories. All attempted tasks, including failures and retries, remain recorded.

Two grading representations were corrected without changing model responses or rerunning completed tasks to improve scores:

- CSS `red` and `#ff0000` (likewise `blue` and `#0000ff`) are identical. The initial grader incorrectly required the named spelling in one Haiku result.
- A yield answer may additionally show the admitted-student denominator when both requested values and that extra denominator match independent source SQL. One Sonnet answer had been marked wrong solely for this correct explanatory row. Extra unknown measures or an incorrect denominator are still rejected.

The raw direct-run grades are preserved. `model_reliability_summary.json` documents these corrections and reports corrected checks. No factual guard or requested institution/period check was relaxed.

The trials used read-only local sources and the configured model effort settings. Two repeats of 26 tasks are a development acceptance sample, not a statistical reliability certificate. The direct run spans the interruption/resumption; the Automatic run included a period of concurrent offline tests. Timing is observational. The isolated follow-ups are separate evidence. API costs use configured standard token-rate estimates, not an invoice, and exclude hosting, taxes and provider adjustments.

## Evidence and regression verification

**158 selected regression methods passed, zero failures/errors/skips**, in a single final run after the annotation repair and Automatic-default change. Coverage spans model policy and metering, identity confirmation, initial routing, request contracts, reviewed execution, catalog planning, relational queries, typed observations, populations, narrative validation, latency safeguards and Streamlit integration. This includes the original salary-population regression and preservation of existing manual model selections. No live performance trial ran concurrently with this final regression batch.

- `evaluations/model_reliability_comparison.json`: completed direct comparison; original unavailable attempts retained separately inside the artifact.
- `evaluations/model_policy_comparison.json`: full Automatic-versus-Sonnet run, including the SQLite failures and actual retry/call usage.
- `evaluations/model_policy_followup.json`: isolated follow-up before the annotation repair; original failures preserved.
- `evaluations/reviewed_scope_diagnostic.json`: actual returned school annotations, effective question and proposal.
- `evaluations/model_policy_annotation_fix.json`: post-repair 4/4 checks per strategy.
- `evaluations/narrative_settings_comparison.json`: all 24 fixed-evidence writing trials; earlier unavailable attempts retained.
- `evaluations/model_reliability_summary.json`: derived scores, matched-success latency, costs, grading corrections and separate follow-ups.
- `evaluations/model_qualification_verification.json` and `model_qualification_regressions.log`: final affected regression run.

No public deployment or original graduation-rate prototype changes were made. The existing five-minute prompt caching remains enabled.
