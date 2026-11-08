# Planner prompt caching

Implemented October 25, 2026. Existing router, reviewed-measure planner and discovery-writer instruction caching remains in place.

The catalog planner now sends the same information in two user content blocks: a stable release-specific catalog block first, then the question, previous plan and conversation context. Table cards have deterministic table/release ordering. The catalog block has an explicit cache breakpoint, alongside the existing system breakpoint. A changed release or changed catalog text produces a different prefix automatically; no local response cache or stale catalog snapshot is introduced.

Top-level automatic caching adds a moving breakpoint to the growing tool conversation. Earlier messages and metadata results remain append-only, so successive planning steps can reuse them. All breakpoints retain Anthropic's default five-minute duration; no one-hour cache is enabled. Instructions, tool permissions, model selection, source validation, repair budgets and execution approval rules are unchanged.

The installed and pinned Anthropic SDK supports top-level `cache_control`. Cache reuse requires an identical prefix and the same model, and depends on timing and provider minimum sizes. Changing tools or instructions also invalidates the relevant prefix. Caching saves input processing; output and reasoning generation are still charged normally. Cache writes have a premium, so the net benefit depends on reuse.

## Verification and measurement

The regression in `prototype/tests/test_catalog_planner.py` checks stable prefixes across different institutions, invalidation across release years, separation of conversation context, append-only tool messages, default-duration controls, and accumulation of provider cache usage. Existing source-binding and execution tests remain applicable.

`evaluations/measure_planner_cache.py` is a manually invoked live metadata-only probe capped at twelve API calls. It records per-call ordinary input, cache creation, cache reads, output, provider duration and estimated cost in `evaluations/planner_cache_probe.json`. It prepares proposals without executing statistical queries and isolates saved proposal artifacts in a temporary directory. Running it incurs API charges.

This probe demonstrates cache reuse, not an incremental savings percentage versus the old implementation. A controlled comparison must run the same workload with the old and new request structures, account for initial writes, distinguish cold and warm requests, and use separate stable prefixes to avoid warming one experiment from the other. Actual usage gaps matter; measure those before paying for a one-hour duration.

October 25 verification: 55 selected tests passed across catalog planning, latency improvements, the query engine and observations. The live Sonnet probe prepared Yale and Harvard academic-library expense proposals in seven API calls; both passed schema/catalog binding with no binding blocks (semantic execution approval remains a separate step). Cache reads represented 79.35% of total input tokens, including the first cold call. The first Harvard call reused 28,476 input tokens from the shared prefix after Yale, and later steps reused tool history. Total estimated probe cost was $0.1643. This small sample is not a general latency or savings guarantee.

Reference: [Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), supplied by the owner.
