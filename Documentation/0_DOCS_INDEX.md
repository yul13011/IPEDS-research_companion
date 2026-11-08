# Documentation index

A map of the project's design/review docs. They live in this `Documentation/` folder; the
idea/improvement docs are under `Ideas for Improvement/`. `README.md` stays in the project root.

## Start here
- [README.md](../README.md) — what the app is, how to run it, what's in/out of version control.
- [SIMPLIFICATION_PLAN.md](<Ideas for Improvement/SIMPLIFICATION_PLAN.md>) — current structure-streamlining plan and progress.
- [DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md](DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md) — wrong/slow diagnosis and the F‑A…F‑E fixes.
- [IMPLEMENTATION_CHECKLIST.md](<Ideas for Improvement/IMPLEMENTATION_CHECKLIST.md>) — roadmap and status.
- [APP_FINDINGS_AND_IDEAS.md](<Ideas for Improvement/APP_FINDINGS_AND_IDEAS.md>) — running findings/ideas (F‑items).
- [IMPROVEMENT_PLAN.md](<Ideas for Improvement/IMPROVEMENT_PLAN.md>) — directional plan: rewrite the "decides-meaning" layer, keep the "fetches-values" core.
- [STRATEGY_query-routes.md](<Ideas for Improvement/STRATEGY_query-routes.md>) — chat-vs-app routes for querying IPEDS; recommends wrapping the engine as MCP/Action.

## Architecture & data foundation
- [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) — the living design (typed plans, no LLM SQL, tool loop).
- [TECH_STACK_AND_ARCHITECTURE.md](TECH_STACK_AND_ARCHITECTURE.md) — concise build/stack overview and request lifecycle; [architecture-review-notes.md](architecture-review-notes.md) — manual walkthrough notes for discussion.
- [DATA_FOUNDATION.md](DATA_FOUNDATION.md), [ANALYTICAL_CATALOG.md](ANALYTICAL_CATALOG.md), [ANALYTICAL_COVERAGE_SCOPE.md](ANALYTICAL_COVERAGE_SCOPE.md) — data/catalog scope.
- [SOURCE_INVENTORY.md](SOURCE_INVENTORY.md), [RELEASE_COMPARISON.md](RELEASE_COMPARISON.md) — source inventory and cross-release comparison.
- [COST_VARIABLES_REFERENCE.md](COST_VARIABLES_REFERENCE.md) — IPEDS cost variable names and descriptions (2024‑25 release).
- [INTENT_ROUTING.md](INTENT_ROUTING.md), [FLEXIBLE_ROUTING_AND_INVESTIGATION.md](<Ideas for Improvement/FLEXIBLE_ROUTING_AND_INVESTIGATION.md>), [REQUEST_FOUNDATIONS.md](REQUEST_FOUNDATIONS.md), [UI_IMPLEMENTATION_PLAN.md](UI_IMPLEMENTATION_PLAN.md) — routing/UI design.

## Reviews & evaluations
- Models: [MODEL_COMPARISON.md](MODEL_COMPARISON.md), [MODEL_QUALIFICATION.md](MODEL_QUALIFICATION.md), [MODEL_RELIABILITY.md](MODEL_RELIABILITY.md).
- Performance: [LATENCY_REVIEW.md](LATENCY_REVIEW.md), [LOCAL_PERFORMANCE_REPORT.md](LOCAL_PERFORMANCE_REPORT.md), [STREAMLIT_CAPACITY_REVIEW.md](STREAMLIT_CAPACITY_REVIEW.md), [PROMPT_CACHING.md](PROMPT_CACHING.md).
- Feature reviews/plans: [CHART_LANGUAGE_REVIEW.md](CHART_LANGUAGE_REVIEW.md), [CATEGORICAL_VARIABLE_REPAIR_PLAN.md](CATEGORICAL_VARIABLE_REPAIR_PLAN.md), [UNIT_METADATA_REPAIR_PLAN.md](UNIT_METADATA_REPAIR_PLAN.md).
- Coverage & questions: [EXAMPLE_QUESTIONS.md](EXAMPLE_QUESTIONS.md) — example/test question catalog; [COVERAGE_SWEEP_2026-10-27.md](COVERAGE_SWEEP_2026-10-27.md) — correctness sweep across survey families; [ERROR_LOG.md](ERROR_LOG.md) — running log of user-reported issues.

## Deployment
- [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md), [DEPLOYMENT_FEASIBILITY_2026-10-26.md](DEPLOYMENT_FEASIBILITY_2026-10-26.md), [ALWAYS_ON_HOSTING_COMPARISON_2026-10-26.md](ALWAYS_ON_HOSTING_COMPARISON_2026-10-26.md).

## Plans (forward work)
- [V1_RETIREMENT_PLAN.md](V1_RETIREMENT_PLAN.md) — retire the v1 engine (planned).
- [PURPOSE_AND_OFFLINE_PLAN.md](PURPOSE_AND_OFFLINE_PLAN.md) — post‑v1 capability split, drop the offline path, add a resolver pre‑gate (planned).
- [DEGREES_BREAKDOWN_PLAN.md](DEGREES_BREAKDOWN_PLAN.md) — degrees‑breakdown feature build spec.

## Subsystem docs
- `prototype/*.md` — per-subsystem documentation (catalog planning, query engine, charts,
  definitions, populations, conversation memory, etc.), kept alongside the code.

## Not in version control (regenerated or external)
See [.gitignore](../.gitignore): vendored `.packages/`, the annual/catalog SQLite under `data/`,
`data/proposed_plans/`, `.streamlit/secrets.toml`, and generated evaluation artifacts
(`evaluations/**` logs/images). Eval scripts and data fixtures remain tracked.
