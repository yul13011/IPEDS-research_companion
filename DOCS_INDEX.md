# Documentation index

A map of the project's design/review docs so the root isn't a wall of files. Docs are
kept in place (relative links between them still work); this is a guide, not a move.

## Start here
- [README.md](README.md) — what the app is, how to run it, what's in/out of version control.
- [SIMPLIFICATION_PLAN.md](SIMPLIFICATION_PLAN.md) — current structure-streamlining plan and progress.
- [DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md](DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md) — wrong/slow diagnosis and the F‑A…F‑E fixes.
- [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) — roadmap and status.
- [APP_FINDINGS_AND_IDEAS.md](APP_FINDINGS_AND_IDEAS.md) — running findings/ideas (F‑items).

## Architecture & data foundation
- [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) — the living design (typed plans, no LLM SQL, tool loop).
- [DATA_FOUNDATION.md](DATA_FOUNDATION.md), [ANALYTICAL_CATALOG.md](ANALYTICAL_CATALOG.md), [ANALYTICAL_COVERAGE_SCOPE.md](ANALYTICAL_COVERAGE_SCOPE.md) — data/catalog scope.
- [SOURCE_INVENTORY.md](SOURCE_INVENTORY.md), [RELEASE_COMPARISON.md](RELEASE_COMPARISON.md) — source inventory and cross-release comparison.
- [INTENT_ROUTING.md](INTENT_ROUTING.md), [FLEXIBLE_ROUTING_AND_INVESTIGATION.md](FLEXIBLE_ROUTING_AND_INVESTIGATION.md), [REQUEST_FOUNDATIONS.md](REQUEST_FOUNDATIONS.md), [UI_IMPLEMENTATION_PLAN.md](UI_IMPLEMENTATION_PLAN.md) — routing/UI design.

## Reviews & evaluations
- Models: [MODEL_COMPARISON.md](MODEL_COMPARISON.md), [MODEL_QUALIFICATION.md](MODEL_QUALIFICATION.md), [MODEL_RELIABILITY.md](MODEL_RELIABILITY.md).
- Performance: [LATENCY_REVIEW.md](LATENCY_REVIEW.md), [LOCAL_PERFORMANCE_REPORT.md](LOCAL_PERFORMANCE_REPORT.md), [STREAMLIT_CAPACITY_REVIEW.md](STREAMLIT_CAPACITY_REVIEW.md), [PROMPT_CACHING.md](PROMPT_CACHING.md).
- Feature reviews/plans: [CHART_LANGUAGE_REVIEW.md](CHART_LANGUAGE_REVIEW.md), [CATEGORICAL_VARIABLE_REPAIR_PLAN.md](CATEGORICAL_VARIABLE_REPAIR_PLAN.md), [UNIT_METADATA_REPAIR_PLAN.md](UNIT_METADATA_REPAIR_PLAN.md).

## Deployment
- [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md), [DEPLOYMENT_FEASIBILITY_2026-10-26.md](DEPLOYMENT_FEASIBILITY_2026-10-26.md), [ALWAYS_ON_HOSTING_COMPARISON_2026-10-26.md](ALWAYS_ON_HOSTING_COMPARISON_2026-10-26.md).

## Progress history (dated checkpoints)
- PROGRESS_2026-10-18 … 10-23 (`PROGRESS_2026-10-*.md`) — day-by-day development log.

## Subsystem docs
- `prototype/*.md` — per-subsystem documentation (catalog planning, query engine, charts,
  definitions, populations, conversation memory, etc.), kept alongside the code.

## Not in version control (regenerated or external)
See [.gitignore](.gitignore): vendored `.packages/`, the annual/catalog SQLite under `data/`,
`data/proposed_plans/`, `.streamlit/secrets.toml`, and generated evaluation artifacts
(`evaluations/**` logs/images). Eval scripts and data fixtures remain tracked.
