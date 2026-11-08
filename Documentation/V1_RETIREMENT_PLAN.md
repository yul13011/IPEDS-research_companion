# V1 Retirement Plan

**Status:** planned, not started. Drafted 2026-11-07.
**Decision basis:** v2 beat v1 on the shared 54-case eval set (2026-11-03: v2 41/54 vs v1 33/54, 0 vs 3 false refusals, ~60% cheaper; latest v2 2026-11-05 = 53/54). So the runtime engine switch is unnecessary. v2 becomes the sole wired engine; v1 is kept only as **archived reference source, imported by nothing**.

> This is a substantial refactor, bigger than "archive three files." Several modules are *mixed* (part v1, part shared-and-live) and must be **split**, not moved. The test suite also shares fixtures across v1 and non-v1 tests. Read the inventory before touching code. Runs as its **own coding session**, v2 test suite green afterward. No commits/pushes without explicit approval.

---

## 1. Guiding principle

- **v1 = a full, redundant LLM engine.** Retire it (archive as reference).
- **Shared/live helpers that happen to live in v1 files** = keep them, by splitting them out of the v1 files first.
- **v2's one live dependency on the v1 file** (`apply_chart_edits`) = relocate it to its real home (`charts.py`).
- Do **not** break the deterministic cost/aid/debt routes, question logging, or the offline (no-API-key) path.

---

## 2. Inventory (from a repo-wide grep of `intent_router|engine_select|request_tasks|model_policy|active_engine`)

### 2a. Pure v1 — archive to `legacy/` (imported by nothing live)
- `intent_router.py` v1 body: `interpret`, `dispatch`, `validate_decision`, `normalize_decision`, `charts_context`, `source_release_years`, `SYSTEM`, `SCHEMA`, `ROUTES`, `DOC_SCHEMA`, `InterpretationError`, and the v1 half of `handle` (lines 337–352).
- `request_tasks.py` task-plan machinery: `schema`, `INSTRUCTIONS`, `COVERAGE_SCHEMA`, `validate`, `execute`, `combine_usage`.
- `model_policy.py` v1 `AUTOMATIC` handler (the part importing `intent_router.handle as dispatch` at line 78).

### 2b. MIXED files — must be SPLIT (do not archive wholesale)
- **`request_tasks.py`** — these helpers are imported by LIVE code and must stay:
  - `status`  ← used by `model_policy.py:27,48,69` (deterministic routes v2 uses)
  - `log_outcome`  ← used by `ui.py:7` (`question_status`)
  - `usable`  ← used by `question_log.py:238`
  - → Move `status`/`log_outcome`/`usable` to a live module (e.g. new `outcomes.py`, or fold into `question_log.py`/`conversation.py`). Archive only the task-plan machinery.
- **`model_policy.py`** — KEEP (live, used by v2): `_deterministic_debt_deflection`, `_deterministic_cost_answer`, `_deterministic_aid_answer`, `source_model`, `AUTOMATIC`, `DEFAULT_STRATEGY`, `HAIKU`, `ACTIVE`. Archive only the v1 `handle`/AUTOMATIC dispatch path.
  - Live importers to preserve: `resolver_v2.py:165`, `workflows.py:29`, `catalog_planner.py:823`, `discovery.py:508`, `ui.py:11`.

### 2c. v2-live dependency on the v1 file — RELOCATE
- `resolver_v2.py:199` → `from .intent_router import apply_chart_edits`. Move `apply_chart_edits` (+ its chart constants: TEXT/BOOLEANS/BOUNDS/ENUMS/RANGE/SETTINGS/EDIT_SCHEMA, and `CHART_TYPES` usage) to `charts.py`; repoint this import.

### 2d. Inert v1 coordination — REMOVE
- `agent.py:454` and `institution_confirmation.py:94`: `from .intent_router import INTERPRETED` — always `None` under v2, readers already fall through. Remove the reads and the contextvar.

### 2e. The engine switch itself — REMOVE
- `engine_select.py` (`active_engine()`), `intent_router.py:333–334` (the switch), `result_narrative.py:20,51` (`active_engine()=='v2'` → make unconditional).
- `ui.py:105` `from .intent_router import handle` → `from .resolver_v2 import handle` (resolver_v2 already mirrors the handle signature; its unused `executor` arg can be dropped in a follow-up cleanup).

---

## 3. Entry-point rewiring

Today: `ui.py` → `intent_router.handle` → (switch) → `resolver_v2.handle`.
After: `ui.py` → `resolver_v2.handle` directly.
- Consider renaming `resolver_v2.py` → `resolver.py` (it is now *the* resolver). Optional; adds churn to importers. Decide at implementation time.
- Note: the `executor`/`ask` callback `ui.py` passes is already **dead under v2** (resolver_v2.handle never calls it). Dropping it is cleanup, not behavior change.

---

## 4. Eval scripts (`evaluations/`)

**Repoint (need only the live entry `handle`):** `coverage_sweep_2026-10-27.py`, `diagnostic_batch_2026-10-26.py`, `diagnose_reviewed_scope.py`, `eval_harness.py`, `run_eval_set.py`, `verify_intent_router_end_to_end.py`, `verify_request_foundations.py`, `verify_year_routing.py` → point `handle` at `resolver_v2`.

**KEEP but repoint imports (model/writer-settings comparisons — NOT engine comparisons):**
- `compare_models_current.py:12` (`handle`, `charts_context`) + `:180` (`interpret`). `handle` → clean repoint; `charts_context` + `interpret` are v1-era → adapt (seed chart state from v2's path, or retire these specific cases).
- `compare_models_reliability.py`, `compare_narrative_settings.py` (extend the above / independent).

**Retire or archive with v1 (v1-specific verification):** `verify_intent_router_live.py` (`interpret`, `apply_chart_edits`), `verify_intent_router.py` + `verify_latency.py` (run `test_intent_router`), `verify_policy_followup.py`, `summarize_model_reliability.py` (reads v1 policy JSON).

---

## 5. Tests — the fixture-sharing trap

- **`test_intent_router.py` exports `decision` and `USAGE`**, imported by `test_model_policy.py:10`, `test_discovery_interpretation.py:120`, `test_discovery_narrative.py:174`. Relocate those fixtures to a shared `tests/_fixtures.py` (or inline) BEFORE retiring `test_intent_router.py`, or the consumers break.
- **Retire** (v1 behavior): `test_intent_router.py`, `test_request_tasks.py`, v1 parts of `test_model_policy.py`, `test_routing_count.py`. `test_data_guide.py:4` imports from `test_request_tasks` → repoint to relocated fixtures.
- **KEEP** (test shared deterministic routes): `test_aid_route.py`, `test_cost_route.py` (import `model_policy._deterministic_*` — unaffected).
- Tests that patch `prototype.intent_router.interpret` (`test_discovery_interpretation.py:131`, `test_discovery_narrative.py:179`, `test_model_evaluations.py:16`) must be rewritten to patch the v2 resolver, or retired.
- **Goal:** v2 suite green after. This also clears the stale-v1-test noise (previously 45 red from v1 tests running under default v2).

---

## 6. Suggested execution order (each step leaves tests green)

1. **Grep baseline** — re-run the inventory grep; confirm nothing new imports v1.
2. **Split the shared helpers out of `request_tasks.py`** (`status`/`log_outcome`/`usable` → live module); repoint `ui.py`, `question_log.py`, `model_policy.py`. Suite still green.
3. **Relocate `apply_chart_edits` (+constants) → `charts.py`**; repoint `resolver_v2.py:199`. Green.
4. **Remove the `INTERPRETED` reads** in `agent.py`/`institution_confirmation.py`. Green.
5. **Relocate test fixtures** (`decision`/`USAGE`) to a shared module; repoint consumers. Green.
6. **Remove the switch**: `ui.py` → `resolver_v2.handle`; make `result_narrative` v2-unconditional; delete `engine_select.py`. Green.
7. **Archive v1**: move the pure-v1 code (2a) + v1 `AUTOMATIC` handler to `legacy/`; delete the v1 half of `intent_router.handle`. Repoint/retire eval scripts (§4) and tests (§5). Green.
8. **Final sweep** — no live import reaches `legacy/`; full v2 suite green.

---

## 7. Explicitly KEPT
- Deterministic cost/aid/debt routes and `model_policy` constants.
- Question logging (`log_outcome`, `usable`, `status`).
- `purpose.py` (offline-mode router + capability helpers) — offline mode is being retired in `PURPOSE_AND_OFFLINE_PLAN.md`, but `purpose.py` itself is trimmed, not deleted.
- The `compare_models_*` / `compare_narrative_settings.py` scripts (model & writer-settings comparison).
- **The "legacy context bundle" — OUT OF SCOPE for v1 (do not delete here).** It is tied to `agent.ask`, not to `intent_router`, so archiving v1 does not remove its last caller. See the inventory + cleanup plan in `PURPOSE_AND_OFFLINE_PLAN.md` → "Follow-on: retire the legacy context bundle." It becomes test-only *after* offline mode is dropped, and is retired then — not now. During v1 retirement, **leave `conversation.context` / `resolve` / `resolve_option` / `local_resolve` / `validate_transition` in place** (don't sweep them into the v1 archive just because `intent_router` also referenced them).

## 8. Consciously DEFERRED (not lost)
- **Multi-question decomposition** — v1's `request_tasks` plan machinery is archived, but the *capability* (split one long prompt into tracked sub-questions) is to be **rebuilt natively in v2** as its own future feature.

## 9. Open decisions for implementation time
- Rename `resolver_v2.py` → `resolver.py`? (churn vs clarity)
- Where exactly do the shared outcome helpers land? (`outcomes.py` vs fold into `question_log.py`)
- Keep the dead `executor` arg on `handle` for signature stability, or drop it?
- Archive location: `legacy/` package vs `archive/v1/` outside the import path.
