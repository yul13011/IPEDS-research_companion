# Claude-first request interpretation

Latency improvements and current measurements are recorded in [LATENCY_REVIEW.md](LATENCY_REVIEW.md). Initial interpretation now also supplies literal institution mentions, avoiding a separate extraction call while retaining local identity confirmation.

Implemented October 23, 2026 for typed requests with conversational AI enabled.

Prompt + bounded conversation/chart context → Claude interpretation → local validation → selected executor.

## Behavior

`prototype/ui.py` now calls `prototype/intent_router.py` before local greeting or chart parsers in AI mode. Claude selects conversation, discovery, definition, numerical, categorical, other analysis, mixed work, chart editing, or clarification. Explicit preset/example buttons and the extract builder remain deterministic. Offline mode retains its separately labeled starter behavior.

Context includes up to twelve recent turns through the bounded context builder and up to four distinct chart/result summaries: IDs, effective settings including format-panel overrides, series names, units, and axis roles. The chart context builder does not supply full result rows or database contents.

Chart requests produce typed setting changes. Python validates types, finite numbers, ranges, percentage limits, axis orientation, series targets, and renderability. The original result object, data and provenance remain unchanged. Arbitrary code, SQL, and Vega specifications cannot be generated through this route. Existing undo controls work with committed edits. Unsupported features such as dashed lines and label rotation clarify rather than being invented.

Definitions use explicit kinds, terms, and source years; the executor constructs the lookup from these fields. Discovery uses existing source-metadata retrieval. Analytical routes retain institution confirmation, source validation, typed categorical responses, units, and aggregate guards. The first interpretation resolves follow-up context, and `agent.ask` reuses it instead of making a duplicate conversation-resolution model call. Source investigation and identity resolution may still require additional calls.

Mixed analysis/chart requests run the complete analytical request, then apply validated formatting to the new result. Target-independent invalid settings fail before analysis; target-dependent checks run against the new chart. Failed edits publish no partial chart. Institution-confirmation continuations retain the original mixed request. AI interpretation failures do not silently fall back to local wording rules.

## Validation

- Selected offline run: 84 unittest methods passed, zero failures/errors, in 160.5 seconds. The final refined router then passed all 14 focused methods in 17.8 seconds; these overlap the earlier run and are not 14 additional distinct tests.
- Legacy local-parser UI tests explicitly select offline mode. Separate AI UI tests require the interpreter to run and assert that greeting/chart shortcuts and analytical execution are bypassed for chart-only work.
- Final live intent matrix: 13/13 passed, including the owner's reset wording, a paraphrase, compound styling, quoted title text, mixed work, unsupported edits, and source-question types. Median observed wall time was 3.04 seconds. Estimated standard API token cost for this final matrix was $0.13372, excluding development/retry runs; this is not a production cost forecast.
- Final live end-to-end workflows: 5/5 passed for an admission-rate definition, faculty discovery, Yale 2024 admission rate, a Harvard 2023 follow-up, and Smith student services. Observed wall times were approximately 9.2–14.8 seconds. This small sample is not a broad accuracy or load-capacity certification.

Live tests corrected model tool-choice compatibility, allowed chart plans without redundant rewritten prose, and exposed the need for typed definition terms rather than a generated sentence augmented with another task.

Evidence and reproducible runners are under `evaluations/`: `intent_router_verification.json`, `intent_router_live.json`, `intent_router_end_to_end.json`, and the corresponding `verify_intent_router*.py` scripts. Live runners require `--live` and incur normal provider charges. Final focused contracts are in `prototype/tests/test_intent_router.py`.

## Activation

Restarted the redesigned local app on port 8516 after validation. New PID: 253036; health endpoint returned `ok`. Refresh the app for a new session. The original graduation-rate app and source databases were not changed.
