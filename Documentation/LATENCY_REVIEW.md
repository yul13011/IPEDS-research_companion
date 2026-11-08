# Latency review and improvements

Completed October 25, 2026. Scope: redesigned app startup, Claude routing/planning, context, discovery evidence, source reads, rendering, exports, and hosting implications. Original graduation-rate prototype and databases were preserved.

## Conclusion

The principal waits are model round trips and generation, plus avoidable work during chat redraws. SQL/database storage is not the dominant measured bottleneck. Warm admission-rate definition lookup without a model took a median 12.6 ms in three local checks. A larger database host alone would not address the model waits.

Implemented improvements preserve Claude-first interpretation, institution confirmation, source evidence, units, typed observations, and validation. No smaller model was silently substituted and no unvalidated answer is streamed to the user.

## Changes and measured effects

| Change | Evidence |
| --- | --- |
| Extract institution mentions in the initial interpretation; reuse them in directory confirmation | Numerical requests dropped from three model calls to two; the categorical example dropped from five to four. Literal wording validation, full-name completion, directory matching and ambiguity confirmation remain. |
| Deduplicate exact discovery passages before sending them to the writer | Controlled faculty package: 207,778 → 78,897 characters, 62% smaller. All 916 passage occurrences are represented by 294 distinct exact texts with scoped source aliases; no distinct passage is truncated. |
| Generate Excel/CSV/audit downloads only when clicked | Controlled five-answer redraw median: 2.886 → 1.505 seconds, 48% faster. One-answer redraw: 0.583 → 0.338 seconds, 42% faster. Zero files generated during redraw versus 15 and three respectively. |
| Build chart context series names without constructing Altair charts | Five-sample median for the tested 80-row trend: 146.7 → 13.0 ms, 91% less time. Names match actual rendered domains across chart types and panel layouts. |
| Reuse bounded SDK clients and request connections | Shared transport retains connection pooling across stages; cached objects contain no questions or model responses. Credentials and transport factories are isolated. |
| Add explicit caching for stable interpreter/discovery instructions | Live requests showed cached prefix reads. This reduces repeated prefix processing, but does not eliminate generation time. |

Downloads use Streamlit's native deferred-data callable and avoid an app rerun on click. File contents are checked against the existing export functions. See [Streamlit download API](https://docs.streamlit.io/1.65.0/develop/api-reference/widgets/st.download_button). Client reuse uses SDK/HTTP connection pooling; see [HTTPX clients](https://www.python-httpx.org/advanced/clients/). Prefix caching follows [Claude's documented mechanism](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).

The full discovery package remains in the local audit. Only the writer transport is compacted. Returned compact citations are mapped back to exact original record/paragraph IDs belonging to the cited topic and then run through the original factual, topic, scope, number, and qualification checks. Unknown or wrongly scoped citation aliases fail validation.

## Live timing limits

The historical observations in `evaluations/latency_baseline.json` are not a controlled before/after trial. Provider load, cold imports, prefix/schema warmup and generated search interpretations vary. The controlled local benchmark holds the rest of the code constant and emulates the former eager export generation; it excludes browser paint and network time.

| Workflow | Historical seconds | Final observed seconds | Model calls before → after |
| --- | ---: | ---: | ---: |
| Definition, first request in process | 9.2 | 37.3 | 1 → 1 |
| Faculty discovery | 14.8 | 19.6 | 3 → 3 |
| Yale numerical lookup | 11.3 | 13.5 | 3 → 2 |
| Harvard numerical follow-up | 9.5 | 16.1 | 3 → 2 |
| Smith categorical services | 14.8 | 17.8 | 5 → 4 |

An earlier optimized pass observed 10.8 seconds for the numerical lookup and 6.9 seconds for its follow-up. These ranges do not establish a consistent end-to-end speedup. The final discovery writer used 32,513 total input tokens versus 78,132 historically, but model-selected source expansions differ between live runs; the controlled package-size comparison above is the cleaner evidence. The final narrative passed the unchanged source validator.

A live pass also exposed a routing ambiguity between "what data do you have on student services" and "what services does Smith College offer". The interpreter contract now explicitly distinguishes metadata discovery from an institution's categorical facts. This remains a Claude decision, not a new keyword router. The final live source workflows passed after that clarification.

## Verification

- 132 selected offline regression methods passed, zero failures/errors: `evaluations/latency_verification.json`.
- Five focused latency tests and related discovery tests passed after fixture corrections. They check source-passage preservation, scoped citations, client isolation, identity confirmation, rendered series domains, and deferred files.
- Final live intent/chart matrix: 13/13 passed, including the owner's axis reset and natural variations: `evaluations/intent_router_live.json`.
- Final live source-backed workflows: 5/5 passed: `evaluations/intent_router_end_to_end.json`.
- Controlled local comparison: `evaluations/latency_local_comparison.json`; runner: `evaluations/measure_latency_local.py`.

No full registered-suite or public-host capacity claim is made. Local UI tests use AppTest; actual browser/Streamlit Cloud behavior still requires staging verification.

## Remaining opportunities, in priority order

1. Measure repeated warm live requests and provider phases separately. The interpreter now records context construction, client setup, and provider time so another pass can target actual waits rather than database size.
2. A/B test the existing smaller-model option or reduced reasoning effort for initial routing only. Promote it only if ambiguous references, mixed requests, categorical questions and source scope remain reliable; leave source planning on the stronger model until separately qualified.
3. Show already verified results while optional narrative rewriting finishes. This could improve time to useful content, but needs explicit UI lifecycle/cancellation work so partial or unvalidated output is never mistaken for a final result.
4. Long conversations still redraw all saved charts and evidence. Consider collapsed historical result cards or carefully tested rendering caches, with current unit/source invalidation and no cross-user response sharing. Avoid changing history behavior without a usability check.
5. For hosting, benchmark R2 cold downloads separately from warm question latency. Stream files to disk and reuse verified local copies; downloading data for each question would add unnecessary delay.

Deliberately avoided: skipping factual checks, caching user answers globally, assuming database size equals RAM demand, or promising a cloud response-time improvement from this local sample.

## Local activation

The previous local app was no longer listening when work resumed. Started the updated redesigned app on the verified free port 8516 (PID 225260); its health endpoint returned `ok`. Open or refresh http://127.0.0.1:8516. The original graduation-rate prototype was not started or changed.
