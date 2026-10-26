# Discovery writing evaluation — October 20, 2026

Step 5 now uses the selected model to write a readable answer from the verified keyword-search evidence. Retrieval, concept selection and statistical execution have not changed.

## Final sample

Five fresh topic questions used real local codebooks and the configured Sonnet 5.5 API. Each made one production writing call and a separate evaluation-only reviewer call. All five drafts passed code validation. The reviewer is a diagnostic, not independent ground truth; its comments include both valid cautions and overflags of supported statements.

| Topic | Template words | Final rendered words | Readability / 5 | Source accuracy / 5 | Qualification retention / 5 |
|---|---:|---:|---:|---:|---:|
| Graduation rates | 475 | 311 | 5 | 4 | 4 |
| Faculty | 379 | 270 | 5 | 5 | 4 |
| Expenses | 338 | 283 | 5 | 4 | 4 |
| Institution characteristics | 293 | 257 | 3 | 4 | 4 |
| Academic libraries | 435 | 307 | 5 | 4 | 4 |

Final prose is approximately **26% shorter overall**. Final word counts include the provisional-release qualification appended by code after the live evaluation; saved live drafts were replayed through the final renderer without additional model calls. Reviewer scores apply to the live drafts before that final note. The institution-characteristics answer remains the weakest readability case, with several source series describing mission statements. Surface word counts do not measure human comprehension.

All required qualification statements were retained. Annual coverage, source-specific definitions and original codebook wording remain in **Definitions & sources → Detailed catalog coverage**. That panel is intentionally more detailed than the narrative. Reviewer comments about details moved there should not be interpreted as data deletion.

## Latency and cost

Final live server answer-ready times ranged from **6.16 to 22.27 seconds**, with a **6.83-second median**. Estimated production writing costs ranged from **$0.035 to $0.168 per answer**, totaling **$0.559** for five answers. Separate reviewer calls cost an estimated **$0.580** and do not run in production. Browser rendering is excluded. This is one run per topic, not an SLA or a p95 benchmark. Large full-definition evidence packages drive input-token costs.

Costs use returned provider token counts and the standard rates in [Anthropic's pricing documentation](https://platform.claude.com/docs/en/about-claude/pricing), checked October 20, 2026. They are estimates, not invoice reconciliation. Rejected drafts still count toward cost when usage is returned. A provider failure without usage is recorded as unknown cost, not free.

## Source and qualification review

- The initial live tests caught a genuine semantic error: calling 150% completion “on-time.” This wording is now explicitly prohibited and rejected in code for extended completion windows.
- Initial checks also overrejected the legitimate unit “full-time-equivalent” and ordinary words such as “sector.” Focused regressions cover those false positives.
- The writer now selects existing source passage IDs rather than reconstructing quotations. Every point must reference its actual source topics and passages; missing/unknown citations, unsupported numeric terms, dropped topics and excess reading budgets reject the draft.
- Different source concepts cannot be merged into one point; identical source descriptions may be summarized together. This prevents aid/gender and staff-count/salary relationships from being blurred. The nonmedical population qualifier is specifically protected.
- The final sample contains no 150%-as-on-time error. Source reviews scored 4–5/5, with residual cautions about scope nuances, broad paraphrases and source-specific reporting rules. These remain limitations: code checks do not prove that every paraphrase is entailed, and an evaluator model can also make mistakes.
- All original retrieval evidence, source issues, annual labels, cohort mappings, model input hashes, structured drafts and validation outcomes remain inspectable. No statistical values are invented or queried by this route.

## Verification evidence

- `discovery-writing-regression-final.log`: 50 related unit/integration checks passed in 70.067 seconds before the final deterministic provisional note.
- `discovery-writing-unit-final.log`: nine writing checks passed again in 10.499 seconds for the final qualification addition.
- `discovery_writing_live.json`: live baseline/candidate text, complete evidence packages, source checks, per-answer latency/usage and reviewer comments.
- `discovery_writing_replay_final.json`: final rendering replay, required qualifications and source validation, including the provisional note.
- `discovery_writing_live_initial.json`, `discovery_writing_live_second.json`, `discovery_writing_live_third.json`: retained development findings; these are not the final benchmark.

Offline mode, missing credentials, invalid narratives and unavailable providers retain the verified template. One bounded writing attempt is allowed, with no automatic SDK retry. Retrieval recall, the eight-concept cap and institutional reporting completeness remain outside this writing-only change.
