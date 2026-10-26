# App simplification plan

Created: October 26, 2026.

Status: In progress. The Lever A **module consolidation (Phases 3–4) is done** on branch
`refactor/consolidate-modules` (7 commits, each tested): **53 → 33 `.py` files (~30 app
modules)**, no functionality removed. Phase 2 non-app bulk relocation is also done
(tracked files 970 → 668). Still open: Phase 0 decisions (D1–D3), Phase 1 feature
inventory, Phase 5 prune/architecture. This is the
tracking document for streamlining the IPEDS Research Companion's structure **without
losing intended functionality**. Check items off as they land; record evidence and
decisions inline. Companion review:
[DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md](DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md).

## Goal

Make the app meaningfully easier to read, review, and maintain — closer in spirit to the
single, well-documented Gradrate `app.py` — while preserving the question types and
answer quality the owner intends. "Simpler" means fewer files, less non-app clutter, and
less accidental complexity; it does **not** mean dropping functionality unless explicitly
decided below.

## Guiding principles

- [ ] Preserve functionality by default; every drop is an explicit owner decision. *(held: consolidation removed no features)*
- [x] Work behind the git safety net (repo is now under version control).
- [x] Each change is small, reviewable, and keeps the existing test suites green. *(one group per commit; group tests green per batch)*
- [x] Measure before/after (lines of code, file count) so progress is visible.
- [x] Analysis before surgery; no large rewrite without an agreed target map. *(✅ groups approved before the merges)*

## Baseline (2026-10-26, before simplification)

| Metric | Baseline | Target (tentative) |
| --- | --- | --- |
| App code (prototype/*.py, non-test) | 9,516 lines | — |
| App modules (non-test) | 53 `.py` (~45 est.) | ~15–18 · **now ~30 (33 `.py`) after consolidation** |
| Test code | 6,780 lines / 63 files | keep coverage |
| Evaluation artifacts in repo | 642 files | **302 output artifacts untracked (639 → 351 in `evaluations/`)** |
| Cached proposed plans (`data/proposed_plans/`) | 273 files | **already gitignored (0 tracked)** |
| Design/review docs (top-level + prototype) | ~55 `.md` | **indexed in place via DOCS_INDEX.md** |
| Vendored deps (`.packages/`) | present | **already gitignored (0 tracked); kept on disk to run/test** |
| Total tracked files in repo | 970 | **now 668** |
| Data scope (context, not reducible) | 10 releases · ~509 tables · 23,990 variables · ~124k category codes · ~25 survey components | unchanged |

Reference point: Gradrate is a single 1,570-line `app.py` because it lets the model write
SQL against one fixed table. This app forbids LLM-written SQL and instead validates/compiles
typed plans over the full raw catalog across ~8 answer routes — that architecture choice,
not waste, drives most of the size.

## The three levers

- **A — Reorganize (low risk, no behavior change):** relocate non-app bulk; consolidate
  ~45 modules into ~15–18. Big gain in reviewability; modest code reduction.
- **B — Prune features (owner decision):** drop answer routes that aren't wanted; removes
  real code.
- **C — Change architecture (pivotal decision):** introduce curated analytical views +
  guarded SQL for common domains (Gradrate-style), keeping the typed-plan engine only for
  open-ended cases. The only lever that can shrink the essential core — trades away some
  safety/coverage guarantees. Decide explicitly before acting.

## Phase 0 — Decisions needed (do first)

- [ ] **D1. Feature inventory reviewed.** Owner marks each feature keep / simplify / drop
      (see Phase 1).
- [ ] **D2. Architecture fork chosen (Lever C).** Keep "typed plans everywhere / no LLM
      SQL", or move common domains to curated views + guarded SQL. This decision gates
      Phase 5.
- [ ] **D3. Target module map approved** (Phase 3 output) before any module moves.

## Phase 1 — Functionality inventory

- [ ] Enumerate every supported question type / feature, each with a concrete example and
      the module(s) that implement it (routes: reviewed measures, catalog discovery,
      definitions, documentation, data guide, aggregates/populations, categorical
      observations, charts/presentation, exports, conversation memory/clarification,
      institution confirmation).
- [ ] For each, record owner decision: **keep / simplify / drop**, with a one-line reason.
- [ ] Output: a feature → module map that the rest of the plan references.

## Phase 2 — Non-app bulk relocation (Lever A, safe)

- [x] `evaluations/`: untracked **302** pure-output artifacts (`.log`/`.png`/`.svg`/`.jpg`/`.pdf`/`.xlsx` under `evaluations/` and `design-mockups/`) via `.gitignore` + `git rm --cached` — kept on disk (tests unaffected), kept eval scripts (`*.py`) and data fixtures/results (`*.json`/`*.csv`/`*.md`) tracked. `evaluations/` tracked 639 → 351. *Not physically moved: several tests read/write `evaluations/` paths.*
- [x] `data/proposed_plans/`: already gitignored at git-init (0 tracked) — nothing to relocate; regenerated at runtime.
- [x] `.packages/`: already gitignored (0 tracked). **Kept on disk** — it's what runs/tests the app here without a venv; a fresh env uses `prototype/requirements.txt`.
- [x] Docs: added [DOCS_INDEX.md](DOCS_INDEX.md) mapping the 34 root docs by category **in place** (not moved — preserves cross-links). Physically moving them is a later option if root clutter still bothers.
- [x] Verified: app imports 30/30 clean; untracking leaves local files intact so tests still run. Net: tracked files **970 → 668**.

## Phase 3 — Target module map (Lever A)

- [x] Draft and execute the safe ("✅") consolidation groups. Landed ~30 modules (the full
      ~15–18 target would need the deferred ◻ merges and/or Lever B/C). Actual outcomes:
  - [x] discovery: `discovery` + `discovery_interpretation` + `discovery_narrative` **+ `data_guide`** → `discovery`
  - [x] populations: `populations` + `population_annual` + `population_review` → `populations`
  - [x] charts: `charts` + `chart_format` → `charts`; **`chart_controls` → `components`** (UI, not charts)
  - [x] units/semantics: `units` + `unit_metadata` + `unit_observations` + `field_semantics` → `semantics`
  - [x] definitions/docs: `definitions` + `documentation` + `category_documentation` → `definitions` (**`data_guide` went to `discovery`** instead)
  - [x] results/presentation: `responses` + `result_text` → `responses`; `observations` + `observation_ui` → `observations` (kept two cohesive modules, not one)
  - [x] also merged: `capabilities` → `purpose`; `coverage_gap` + `source_policy` → `coverage`; `memory` + `working_analysis` + `analysis_clarification` → `conversation`; `transcript_scroll` → `components`
  - [ ] deferred (◻): `intent_router`/`request_tasks`/`model_policy` → `router`; `time_scope`, `query_schema`; the `institutions.py` rename; `progress.py` kept standalone (leaf util; folding it into `components` would cause import cycles)
- [x] Map approved before moving code (D3 satisfied for the ✅ groups; full ~15–18 map not finalized).

## Phase 4 — Module consolidation (Lever A)

- [x] Execute the approved consolidation incrementally, one group per commit, tests green.
      Done on `refactor/consolidate-modules` (7 commits `27d07fa`→`0c1692a`): batch 1 (6
      modules), 2 (observations+charts), 3 (definitions), 4 (discovery), 5 (semantics), 6
      (conversation), 7 (UI helpers). Each merge resolved name collisions explicitly
      (e.g. `category_answer`, `INTERP_SCHEMA`/`INTERP_SYSTEM`, `guide_answer`,
      `catalog_search`, duplicate `VERSION`) and redirected all importers incl. module-style
      imports and test patches.
- [x] Re-measure module count + LOC: **53 → 33 `.py` files (~30 app modules)**; app LOC
      ~9,550 (essentially unchanged — consolidation relocates code, it does not delete it;
      line reduction comes from Phase 2 bulk relocation and Phase 5 pruning, not this phase).
- [ ] Final gate: full combined suite (`verify_catalog_execution.py`, ~238 tests) +
      the five new regression tests green, then push the branch.

## Phase 5 — Feature pruning / architecture change (Levers B & C)

- [ ] Apply Phase 1 "drop/simplify" decisions (removes code per decision).
- [ ] If D2 chose curated views + guarded SQL: design the curated views, the guarded-SQL
      path, and which domains move to it; keep the typed-plan engine for the rest.
- [ ] Re-measure; confirm preserved functionality via tests + live checks.

## Phase 6 — Validation & wrap-up

- [ ] All existing suites green; new consolidations covered.
- [ ] Before/after metrics recorded in the table above.
- [ ] Short migration note so the structure is self-explanatory.

## Open decisions log

| ID | Decision | Status |
| --- | --- | --- |
| D1 | Feature inventory keep/simplify/drop | Pending |
| D2 | Architecture fork (typed-plan everywhere vs. curated views + guarded SQL) | Pending |
| D3 | Target module map approval | Pending |

## Change log

| Date | Change |
| --- | --- |
| 2026-10-26 | Plan created from the structure investigation. Module consolidation observed already underway on `refactor/consolidate-modules` (uncommitted). |
| 2026-10-26 | Lever A consolidation (Phases 3–4) completed: 7 commits on `refactor/consolidate-modules`, 53 → 33 `.py` files (~30 app modules), no functionality removed, each group's tests green. Combined suite 348/349 (1 pre-existing env failure); branch pushed. |
| 2026-10-26 | Phase 2 non-app bulk relocation: untracked 302 generated eval/mockup artifacts; confirmed `.packages`/`proposed_plans`/annual-SQLite already gitignored; added DOCS_INDEX.md. Tracked files 970 → 668. Phases 0/1/5 (decisions, feature inventory, prune/architecture) still open. |
