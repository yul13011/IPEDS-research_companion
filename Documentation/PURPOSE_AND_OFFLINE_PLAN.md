# Post-v1 Refactor: Capability Split + Drop Offline Path + Resolver Pre-Gate

**Status:** planned. Runs **after** `V1_RETIREMENT_PLAN.md`. Drafted 2026-11-07.
**Decisions already made:** AI always on (drop the offline mode); keep `direct` as a zero-cost pre-gate in front of the resolver; keep `prepare`'s length guard at the resolver entry; split the capability helpers out of `purpose.py`.

> **Correction captured from a caller grep:** dropping the offline path does **NOT** dead-code `agent.ask` / `institution_confirmation.ask`. Those `ask()` functions are the analytical **harness entry** used by ~25 eval/test scripts with `use_model=True` (e.g. `evaluations/run_nces_aggregate_benchmarks.py`, `prototype/tests/live_smoke.py`, and many `tests/*`). After this refactor they become **production-unreachable** (production is `ui → resolver_v2.handle → agent._answer`) but remain the test/eval entry. **Do not tear them out here.**

This is two sequenced steps, done together, both after v1 is retired.

---

## Step 2 — Split capability helpers out of `purpose.py`

`purpose.py` currently bolts two unrelated concerns together (see its line 61 comment, `merged from capabilities.py`). Pull the capability concern back out.

**Move → new `prototype/capabilities.py`:** `describe()`, `answer()`, `CHART_TYPES`. They're self-contained (`answer()` uses `CHART_TYPES`; `describe()` stands alone).

- **Live importer to repoint:** `catalog_planner.py:1091` (`describe`).
- **v1 importers (archived anyway by the v1 plan):** `intent_router.py:16` (`CHART_TYPES`), `:159` (`describe`); `request_tasks.py:218` (`answer`).
- **VERIFY:** `answer()`'s only current importer is v1 `request_tasks.py`. Once v1 is archived it may be orphaned. If no v2 path answers "what charts can you make," either (a) wire it into v2 capability handling, or (b) let it ride to legacy.
- Low risk, independent. Land first, suite green.
- *Open:* `capabilities.py` (proposed) vs. putting `CHART_TYPES` in `charts.py`. One home is cleaner.

---

## Step 3 — Drop the offline mode + add the resolver pre-gate

### 3a. Scope decision up front (two different things)

- **(i) Remove the user-facing offline MODE** — delete the "Use conversational AI" toggle (`ui.py:584`); the app is always AI-on. *This is what was decided.*
- **(ii) Remove the `use_ai=False` CODE PATH** (`local_plan` + `ask`'s offline branch) entirely.

These are **not** the same. **(ii) hits ~20 tests** that deliberately set `use_ai=False` as a cheap, deterministic, no-API test path (`test_chart_*`, `test_prototype`, `test_memory`, … — comment: "Explicit offline path; AI routing has separate tests").

**Recommendation:** do **(i)** now — it's the production change requested. Treat **(ii)** as optional later cleanup: keep `local_plan` / the `use_ai=False` path as a **test-only affordance** unless/until we migrate those ~20 tests. Flagged as an open decision.

### 3b. UI changes (production always-on)

- Remove the toggle (`ui.py:584`) and the `use_ai` session state; default to AI.
- Remove the offline branch `ui.py:108–113` (`else: direct(...) / adjust_presentation`) and the `:120–123` `ask(use_model=False)` fallback. Under v2 `handle` always returns an answer, so `:123` is already production-dead — this deletes the dead fallback and the toggle together.
- `ui.py` always calls `resolver_v2.handle`.
- Update the caption at `ui.py:434` (drop the "Offline starter parser" text).
- **No-API-key UX:** the toggle was `disabled` without an API key (`ui.py:584`). With always-on, decide what the app shows when no key is configured (clear error/help vs. builder-only). Open decision.

### 3c. Resolver pre-gate (the kept optimization)

At the top of `resolver_v2.handle`, **before** the Haiku `resolve()` call (around the FAQ layer, lines 243–254):

1. `prepare(question)` — the length guard (1–4,000 chars). Rejects empty or over-long input **before any model call** — prevents a blank submit and caps a runaway/abusive prompt from becoming a wasted API call.
2. `direct(question)` — if it matches a greeting / thanks / help, return that answer immediately (**zero model calls**). Keep its `conversation` output shape consistent with the resolver's own `conversation` operation so the two don't disagree.

Keep `prepare`/`direct` **in `purpose.py`** (still used by the `agent.ask` harness path) and import them into `resolver_v2`. Minimal churn; no dissolve.

### 3d. What remains in `purpose.py` after this

- `prepare`, `direct`, `source_context`, `mixed` stay — used by the `agent.ask` / `institution_confirmation.ask` test/eval entries, and now `direct`/`prepare` also by `resolver_v2`.
- Only the capability helpers leave (Step 2).
- So `purpose.py` is **trimmed, not dissolved**. Its two live roles become: (a) the resolver pre-gate (`direct`/`prepare`), and (b) the test/eval `ask()` harness.

---

## Tests & evals affected

- **Step 2:** repoint `catalog_planner`'s `describe` import; fix any test asserting the helpers' location.
- **Step 3b:** ~20 tests set `use_ai=False` — **unaffected if** we keep the `use_ai=False` code path (recommended). If we remove it (3a-ii), they must migrate. Update the ~2 settings/UI tests that assert the toggle.
- `agent.ask` / `institution_confirmation.ask` callers (~25 eval+test scripts) keep working — they pass `use_model=True` and never touch the toggle.

---

## Follow-on: retire the legacy context bundle (after offline is dropped)

Dropping the offline mode is what finally makes the **legacy context bundle** disposable, so its cleanup belongs here — as a step **after** 3b lands, not before.

**What "legacy context bundle" refers to (exact code):** the old, detailed conversation-memory mechanism that v2 does **not** use — v2 uses `resolver_v2._history_summary` (5 turns, no message text) instead. It is this set of functions in **`prototype/conversation.py`**:

| Function | Line | Role |
|---|---|---|
| `context()` | `conversation.py:16` | builds the bundle dict: `recent_turns` (last **12**, `LIMIT=12` at `:6`; trimmed to **48 KB** at `:35-36`, and **includes each turn's answer message**), `active_analysis`, `working_analysis`, `analysis_brief`, `policy` |
| `resolve()` | `conversation.py:45` | the legacy follow-up-rewriting LLM call |
| `resolve_option()` | `conversation.py:102` | binds a bare letter (a/b/c) to a pending labelled choice |
| `local_resolve()` | `conversation.py:123` | the offline (no-model) follow-up continuation |
| `validate_transition()` | `conversation.py:303` | the subject-signature scope-drift guard (legacy/v1 path only) |

**Which scripts use it, and which parts:**

- `prototype/agent.py:447-462` — inside **`agent.ask`** (the offline + test/eval entry): builds `bundle = context(conversation)` (`:448`) and calls `resolve` / `resolve_option` / `local_resolve`. *This is the live user today, via offline mode.*
- `prototype/intent_router.py:149,154` — v1 builds `context(history)`. *Archived with v1.*
- `prototype/request_tasks.py:272` — v1 calls `validate_transition`. *Archived with v1.*

**Why it survives v1 retirement:** `agent.ask` keeps calling `context()` as long as offline mode exists. Once 3b removes the offline path, `agent.ask`'s only remaining callers are the ~25 test/eval scripts (`use_model=True`). At that point the bundle is **test-only** and can be retired.

**The one caveat that makes this its own step:** those ~25 `agent.ask` tests exercise the **legacy** resolution (`context` + `resolve`), **not** the v2 resolver. So retiring the bundle means first **migrating those tests onto the v2 path** (`resolver_v2.handle`) or demoting them to lower-level planner/core tests. Until that migration is done, keep the bundle.

**Do NOT confuse this with the rest of `conversation.py`.** Most of that file is shared and live under v2 and stays: `recent_result`, `results`, `latest`, `subject_for`/`update`/`from_history`/`prompt_context`, and the clarification/`analysis_brief` machinery (`prepare`, `prepare_bundle`, `draft`, `scope`, `select`, `execute_selection`, the schemas — reached via `catalog_planner`, `coverage`, and `agent._answer:395-397`). Only the five functions in the table above are the "legacy context bundle."

---

## Explicitly NOT doing here

- Not tearing out `agent.ask` / `institution_confirmation.ask` / `local_plan` (they're the test/eval harness).
- Not building multi-question decomposition (separate future feature; it supersedes `mixed()`).
- Not retiring the legacy context bundle *yet* — that's the follow-on step above, gated on migrating the `agent.ask` tests to the v2 path.

## Open decisions

1. Capability home: `capabilities.py` vs. `charts.py` for `CHART_TYPES`.
2. `answer()`: wire into v2, or let it ride to legacy with v1?
3. Offline code path (3a-ii): keep `use_ai=False` as a test-only affordance, or migrate the ~20 tests and delete it?
4. No-API-key UX once the toggle is gone.
