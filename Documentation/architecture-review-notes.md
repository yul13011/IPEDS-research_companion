# IPEDS Research Companion: manual architecture review notes

Local notes for discussion. Not part of the repo. Paths are relative to `agent-redesign/`.

## Guide diagram

We use this diagram as the guide for understanding the architecture. Scope: a user-typed question only (a clicked chip bypasses it).

![Intent resolution and route selection](../assets/request-flow-intent-detail.svg)

Source file: `assets/request-flow-intent-detail.svg`

## Two entrances

- **Typed question**: `ui.py` pending_action type `chat` -> `resolver_v2.handle` -> FAQ lookup -> resolver -> ... (the SVG covers this path).
- **Clicked example chip**: `ui.py` pending_action type `example` -> `execute_example(id)` directly (ui.py:90-91). Skips `handle`, `faq_v2`, `_norm`, the resolver and the planner.

## 1. FAQ layer (`prototype/faq_v2.py`)

Verified so far:

- `_norm(text)`: cosmetic normalizer (lowercase, strip accents, curly -> straight quotes, en/em-dash/minus -> hyphen, collapse whitespace). Applied to both the chip questions (when the index is built) and the typed question (in `lookup`).
- `_chip_index()`: no arguments, never sees the user's question. Reads every example in `learning_content.json` and returns `{normalized question: example id}`. Cached with `lru_cache`, so built once.
- `lookup(question)`: normalizes the typed question, then looks it up in the index. Returns an example id string or `None`. Match is exact after normalization; rewording, word order and missing `?` all miss.
- `run_faq(example_id, question)`: calls `execute_example(example_id)`, tags `mode='curated FAQ'`, `faq.example_id`, and records 0 model calls / $0 with `model='faq'`. The `question` argument is unused in the body.
- A miss is not an error: the question continues to the Haiku resolver, which receives the original text.

Data:

- `topics()` (`workflows.py:12`) reads `prototype/learning_content.json`, no caching. 6 topics: admissions, enrollment, aid, outcomes, faculty, institution.
- 18 examples in total (3 per topic), all `kind: analyze`.
- `example_by_id()` returns the first example dict with a matching id, else raises `ValueError('Unknown example.')`.
- Only one example has `cost_route: true`: `aid-point`, "How much does it cost to attend Harvard College in 2024-25?"

`execute_example` (`workflows.py:23-49`) paths:

1. `cost_route` -> `_deterministic_cost_answer`
2. `observation_plan_key` -> `institution_example_plans.json` via `observations.answer`
3. `catalog_plan_key` -> `faculty_example_plans.json` via `query_engine.execute`
4. otherwise inline `plan` -> `Plan(**plan)` then `execute`
5. non-`analyze` kind -> codebook search (currently unreachable: no example has a `query` key)

### Open questions / unverified

- [ ] Does `_deterministic_cost_answer` ever return nothing for the Harvard chip today? If it does, the user sees "This cost example could not be resolved from the loaded data." with intent `clarify`, logged as `needs_clarification` (inaccurate label: nothing is being clarified).
- [ ] `want_narrative` (ui.py:243): could it replace that message with generated text? Not read.
- [ ] `_md` (ui.py): does it reformat the message? Not read.
- [ ] `log_question`: how is the outcome value actually written to the log? Not read.
- [ ] Why does the `discover` kind exist in `execute_example` if no example uses it? (`git log` on `workflows.py` / `learning_content.json` might show.)

## 2. Resolve intent (`prototype/resolver_v2.py`)

Notes to add.

- Resolver is Haiku on both passes; Sonnet only runs the retry re-fetch/planner.

## 3. Deterministic core routes (debt, cost, aid; `model_policy.py`)

Notes to add.

## 4. Route cascade (`agent._ask`)

Notes to add.

## 5. Reviewed-measures planner and catalog planner

Notes to add.

## 6. Validation gates and execution (`analytics.py`)

Notes to add.

## Observations and questions for discussion

### FAQ lookup is mostly useless (owner's take; an opinion to revisit as more data is collected)

- The FAQ lookup (`faq_v2.lookup`, called at `resolver_v2.py:244-250`) only fires when a user types the exact text of a chip question. The match is exact after cosmetic normalization (`_norm`: case, whitespace, accents, quote and dash styles). Any rewording misses and goes to the Haiku resolver.
- Most users would click the chip instead. A click bypasses the lookup entirely: `ui.py:90-91` calls `execute_example(id)` directly, never reaching `intent_router`, `resolver_v2` or `faq_v2`.
- So the lookup serves only users who type or paste a chip question word for word.
- Hit rate, first measurement (question log read 2026-11-07, first tab, all filters cleared: 81 rows, 50 sessions, Nov 5-7):
  - 24 rows have text exactly matching one of the 18 chip questions. 21 (87.5%) were chip clicks (`served_by = reviewed example`) and 3 (12.5%) were typed FAQ hits (`served_by = curated FAQ`, `route = faq`).
  - Typed FAQ hits are 3 of 81 rows overall (3.7%).
  - By session: 16 sessions clicked a chip, 3 sessions typed one, out of 50 sessions. No session did both.
  - The 3 typed hits were in 3 different sessions, all on Nov 6 within about 100 minutes, all on app version `8f666f6`. Each logged 0 model calls and $0, with `narrative` = TRUE.
  - Caveats: small sample; owner testing can't be separated from other users; only the first tab was read (not any `internal` tab); clicks are identified from `served_by` (inferred from the code, and all 21 such rows are exact chip text); a typed near-miss (for example a chip question without its question mark) would not match the FAQ and can't be picked out in the log.
  - Reading so far: most chip-question traffic is clicks, but typed hits are not zero. Revisit with more data.
- Related facts: the lookup ignores conversation context. A typed FAQ hit still gets the Sonnet summary rewrite at display time, which is not counted in the logged cost. The FAQ index is built from the 18 chip questions only; cost is not a separate source.
