# IPEDS Research Companion — Improvement Plan

_Created 2026-11-02. Living document: update the Status section as we go._

## Goal

Make the app answer IPEDS questions with the flexibility of a capable agent
(the way Claude Code does in conversation), while **guaranteeing every number is
real and traceable to a source variable**, and keeping **tight, curated control
over a set of FAQs**.

## The key idea: "deterministic" is two different things

The app has two kinds of deterministic code doing opposite jobs. Telling them
apart is the whole decision.

- **Code that decides WHAT YOU MEANT** — which path to take, is this a trend, is
  this a cost question, rewrite the follow-up. Brittle, accreted one patch at a
  time, the source of the clunkiness. → **REWRITE**
- **Code that FETCHES VALUES SAFELY** once the meaning is known — bind to a
  source variable, run a bounded read-only query, return a traceable number.
  Solid, hard-won. → **KEEP**

The split is **"decides meaning" vs. "fetches values,"** not
deterministic-vs-flexible.

## The app in four layers

### KEEP — Execution / data core (fetches values; the asset)
- `query_engine.py` — bounded relational executor: source binding, joins, safe SQL
- `analytics.py` — validates plans against evidence, runs read-only queries
- `catalog_execution.py`, `observations.py` — bounded execution of source-bound observations
- `catalog.py`, `coverage.py`, `populations.py` — read-only source docs, data locations, directory scoping
- `data_bootstrap.py`, `build_registry.py`, `query_schema.py`, `api_client.py`, `time_scope.py` — plumbing
- `data/*.sqlite`, `measure-registry/reviewed_measures.json` — the data + curated measures

### REWRITE — Interpretation / resolution (decides meaning; the scar tissue)
- `intent_router.py` — the ROUTES list (the routing)
- `model_policy.py` — deterministic cost/price route + deflections
- `purpose.py` — pre-gate that routes before investigating
- `intent_checks.py` — `contract()` regex + refuse-on-mismatch validators (killed the net-price follow-up)
- `conversation.py` — follow-up rewrite / `select` / `validate_transition`
- `agent.py` — orchestration that stitches the above together
- `catalog_planner.py` (~1,253 lines), `request_tasks.py` — "how do I plan this" logic (part interpretation, part bridge-format into the core)
- `discovery.py`, `definitions.py`, `institution_confirmation.py` — mode / entity-resolution handlers

### PRESERVE — Domain knowledge (extract, carry into v2)
- Yale + NCES eval cases (`evaluations/`, `REVIEWED_EXAMPLES.md`)
- group semantics — Ivy League, Seven Sisters (`catalog.py` GROUPS), `semantics.py`
- FAQs — cost questions, example/"need ideas" chips (`workflows.py`, `learning_content.json`), reviewed measures
- design-intent `.md` docs

### KEEP (light touch) — Presentation / UI
- `ui.py`, `components.py`, `charts.py`, `responses.py`, `exports.py`

## What "rewrite the interpretation layer" means

Replace the meaning-deciding machinery (the REWRITE list) with **one
model-owned resolver** that outputs a **structured decision** (operation, scope,
measures, edit-vs-fetch) and calls the **same untouched execution core** to fetch
numbers — plus a **small, intentional FAQ layer** we control. Not a rebuild of
the thing that gets data; a replacement of the rules that decide *what* to get.

## Target architecture (v2)

1. **FAQ layer** (deterministic, curated — our control): known questions →
   vetted answers / framings. Small and intentional, not sprawling.
2. **Model-owned resolver** (flexible): interprets intent over the held result +
   conversation; emits a structured decision; can query the core in a loop
   (propose read-only query → see result → refine), the way an agent does.
3. **Execution core** (unchanged): fetches and binds every number; fails loud if
   a value can't be traced.

---

## Next steps

### Step 1 — Build the evaluation harness  ◐ (designed — see `evaluations/EVAL_SET_DESIGN.md`)
_Why: turns "is a rewrite worth it?" into a measurement, and protects the
Yale/NCES behavior from regressing._
_Discovery: the skeleton already exists — `coverage_sweep` (30 ground-truth-by-SQL
probes), `compare_models_current` (multi-turn + cost cap), the immutable Yale CSVs
and NCES Trend Generator exports. Step 1 = consolidate + extend, not build from zero._
- ☑ Decide grading: numeric (SQL ground truth, max(1.0, 1%) tolerance) + behavioral + refusal + false-refusal metric
- ☑ Design unified case schema (single + multi-turn) and category taxonomy
- ☑ Freeze the manifest `evaluations/eval_set.py` (Python case lists, matching the repo's PROBES/CASES idiom; new follow-up/FAQ/refuse/trap cases + reused coverage_sweep probes via `numeric_core()`) — 54 cases / 63 turns
- ☑ Write the runner `evaluations/run_eval_set.py` (drives `handle` multi-turn, grades by SQL ground truth, cost cap, scorecard; `--validate` checks specs with no API)
- ☑ Validate with no API: all 19 new-case ground-truth specs resolve; grader self-tests pass (2 stale reused-probe specs flagged non-fatal)
- ☑ Baseline the current app (v1) → `evaluations/eval_set_scorecard_v1_2026-11-03.md` (spent $2.38 / $5 cap, 54 cases)

**v1 baseline headline:** overall **33/54**. By category — refuse **6/6**, numeric **9/12**, behavioral **11/18**, trap **2/3**, FAQ **3/7**, **follow-up 2/8 with 3 outright false-refusals**. Median turn latency 16.4s.
_Trustworthy signals: numeric (SQL-graded), refuse, and follow-up false-refusals. The behavioral/FAQ fails are partly grader-conservative — text, categorical yes/no, definition, and discovery answers don't surface as numeric rows, so they read as NO-RESULT; these need the deferred LLM-judge or manual review. So 33/54 is a floor, and the clean story is: **follow-ups are where v1 breaks** (net-price comparison blocked or wrong across phrasings; "what about Harvard?", the trend follow-up, and "make it a bar chart" all wrongly refused)._
_To verify: `fu_netprice_narrow` scored WRONG-NUMBER on both turns — confirm whether that's a real v1 wrong-number or a grader value-matching artifact._
_Fixed a Windows-console UnicodeEncodeError on the final scorecard print (files were already written; run no longer exits 1)._

### Step 2 — Spike a v2 interpretation layer (separate conversation)  ☑
- ☑ New session reused the data/catalog/execution core unchanged (no data-pipeline rebuild)
- ☑ Model-owned resolver emits structured decisions (`prototype/resolver_v2.py`)
- ☑ Query-in-a-loop against the core (cheap Haiku fetch → on empty/clarify, restate + re-run on Sonnet)
- ☑ Minimal curated FAQ layer (`prototype/faq_v2.py` → proven chip recipes)
- ☑ Reached through the frozen runner via `--engine v2` (`prototype/engine_select.py` + 3-line dispatch in `intent_router.handle`); v1 untouched
- **Result:** v2 **41/54** vs v1 33/54; **false refusals 0 vs 3** (headline met); follow-ups 6/8 vs 2/8; refuse 6/6 and numeric 9/12 held (no regression); cost $0.92 vs $2.38. Scorecards dated 2026-11-03.

### Step 3 — Compare and decide  ☑
- ☑ Ran the spike against the SAME eval set (`--engine v2`)
- ☑ Compared to baseline: v2 41/54 vs 33/54; false refusals 0 vs 3; follow-ups 6/8 vs 2/8; refuse 6/6 and numeric 9/12 held; cost $0.92 vs $2.38
- ☑ Decision (2026-11-03): the v2 direction is validated — proceed with it; committed. Follow-ups: net-price determinism, the two resolver framing fixes, the `faq_bach` spec fix (re-grade pending), and an LLM-judge for non-numeric cases

---

## Decisions / open questions
- How to grade narrative (non-numeric) answers automatically
- Nondeterminism tolerance for a public tool (low temperature? cache answers? route high-stakes questions through the FAQ layer?)
- Where the FAQ list lives and who curates it
- Cost/latency budget for a query-in-a-loop design (traffic expected to be low)

## Status
- **2026-11-02** — Plan created. Layer map done.
- **2026-11-02** — Step 1 **designed** (`evaluations/EVAL_SET_DESIGN.md`). Found the harness skeleton already exists (coverage_sweep probes, compare_models runner, Yale/NCES ground truth). Grading rubric + unified schema decided.
- **2026-11-02** — Step 1 **built + validated (no API)**. Manifest `evaluations/eval_set.py` (54 cases / 63 turns) + runner `evaluations/run_eval_set.py`. `--validate` green.
- **2026-11-03** — **v1 baseline run complete** (33/54; follow-ups 2/8, 3 false-refusals; refuse 6/6). Scorecard committed-pending in `evaluations/`. Step 1 **done**. Step 2 (v2 spike) running in its own session. Open follow-up work: add an LLM-judge for non-numeric behavioral/FAQ cases so those stop under-scoring; verify the `fu_netprice_narrow` WRONG-NUMBER.
