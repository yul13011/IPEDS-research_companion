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

- [x] Enumerated every supported feature → current (post-consolidation) module.
- [x] Owner stance (stated 2026-10-26): **keep all functionality.** No features marked drop.
      A few are flagged ⚠ *simplify-candidate* — streamline without losing the capability,
      owner to confirm. D1 satisfied as "keep all; simplify-candidates pending owner yes/no".
- [x] Output table below; the rest of the plan references it.

| # | Feature (example) | Module(s) | Disposition |
| --- | --- | --- | --- |
| 1 | Greetings/thanks/help ("what can you do?") | `purpose` | Keep |
| 2 | Capability answers ("what chart types?") | `purpose` | Keep |
| 3 | Data-area overview + interpretation + AI narrative + beginner guide | `discovery` | Keep · ⚠ the AI-narrative writing step could be optional/trimmed |
| 4 | Coverage / years available | `coverage` | Keep |
| 5 | Definitions / labels / codes / "how calculated" | `definitions` | Keep |
| 6 | Reviewed measures (36: admissions, SAT, enrollment, grad rates, awards, aid) | `analytics` + `measure-registry/` | Keep (fast path) |
| 7 | Catalog-discovered measures (anything outside the 36) | `catalog_planner` + `catalog_execution` | Keep (core) |
| 8 | General calculations / joins / weighted means / % change | `query_engine` + `query_schema` | Keep (core) |
| 9 | National/state/sector aggregates + institution counts | `populations` | Keep |
| 10 | Units / currency / field semantics | `semantics` | Keep (core) |
| 11 | Categorical lookups & institution lists | `observations` | Keep |
| 12 | Intent routing (classify every prompt) | `intent_router` | Keep (core) |
| 13 | Multi-part requests / task tracking | `request_tasks` | Keep · ⚠ simplify-candidate (extra complexity; confirm it's needed) |
| 14 | Conversation memory / follow-ups / clarification / working-analysis | `conversation` | Keep |
| 15 | Institution confirmation / aliases / named groups | `institution_confirmation` | Keep |
| 16 | Independent request/plan/result validation | `intent_checks` | Keep (core safety) |
| 17 | Time / period binding (cohort vs observation vs class; trends) | `time_scope` | Keep (core) |
| 18 | Answer text / source disclosure / "Data used" | `responses` | Keep |
| 19 | Charts (line/bar/grouped/panels) + formatting + NL chart edits | `charts`, `components` | Keep · ⚠ NL chart-edit surface is large (see F009–F012); could narrow |
| 20 | Exports (Excel+methodology / CSV / provenance JSON) | `exports` | Keep |
| 21 | Explore / Ask&Analyze / Build-extract / Browse-defs / About pages | `ui`, `workflows`, `components` | Keep · ⚠ Build-a-data-extract wizard and Browse-definitions overlap the chat path |
| 22 | Model policy (Automatic Haiku/Sonnet, retries, cost) | `model_policy`, `api_client` | Keep |
| 23 | Progress messages | `progress` | Keep |
| 24 | Catalog search / institution resolution / source evidence | `catalog` | Keep (core) |

No features recommended for removal. The ⚠ items (#3, #13, #19, #21) are the only places
Lever B (prune/simplify) would remove code, and each needs an explicit owner yes/no.

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

## D2 — Architecture fork analysis (for owner decision)

The feature inventory shows **no features to drop**, so Lever B frees little code. The only
lever that can shrink the *essential core* (`catalog_planner` 824 + `query_engine` 782 +
`catalog_execution` + `intent_checks` + `semantics` ≈ 2,800 LOC) is **Lever C — the
architecture**. This is the pivotal choice.

### Why the core is big
This app forbids LLM-written SQL. Instead the model emits a **typed plan**, deterministic
code **validates** it against the real metadata/physical schema and **compiles** it to
bounded read-only SQL over the full raw catalog (10 releases · ~509 tables · 24k variables),
then validates the result. That safety/breadth is exactly what makes it ~6× Gradrate, whose
single 1,570-line file just lets the model write SQL against **one** fixed, tiny table.

### Option A — keep "typed plans everywhere / no LLM SQL" (status quo)
- **Pros:** strongest safety (no arbitrary SQL), structured provenance on every answer,
  uniform handling across all 509 tables, already built and tested.
- **Cons:** the core stays ~2,800 LOC; every new capability needs plan-schema + validator +
  compiler support; multi-call planning is the main latency/cost driver (cold ~38s, up to
  ~$0.11/answer); hardest lever for the owner to extend.
- **Net:** after consolidation + Phase 2 the app is far more navigable; if the owner's pain
  was reviewability, Option A may already be "good enough" and C is unnecessary.

### Option C — curated analytical views + guarded SQL for common domains
Build a **small number of clean, documented, year-harmonized views** (DuckDB/SQLite) for the
domains that carry most questions — e.g. enrollment, completions/grad rates, admissions/SAT,
finance, faculty/salary, aid — one tidy table each (Gradrate-style). Let the model write SQL
against **only those views** through a read-only guarded executor (view allowlist, read-only
connection, SQL parse/validate, row/time limits). Keep the typed-plan engine only for the
open-ended long tail (arbitrary variables, novel joins).
- **Pros:** collapses most of the planner/compiler for the common 80% (the model does
  schema-reading + SQL over a tiny curated schema, like Gradrate); **faster** (one SQL gen,
  not multi-call planning); **easy to extend** (add a view); closest to the Gradrate
  simplicity the owner liked.
- **Cons / risks:** (1) you must **build and verify** the harmonized views across 10 years of
  schema drift (CIP 2010→2020, finance/COST reorg, aid moves) — real data-engineering with
  its own correctness burden; (2) LLM SQL reintroduces wrong-join/filter/hallucinated-column
  risk (mitigated because the curated schema is tiny + validated + read-only, as Gradrate
  shows); (3) less fine-grained provenance than typed plans unless re-added; (4) two engines
  to maintain during transition; (5) the open methodology questions (the 13 Yale
  discrepancies, national-aggregate rules) must be re-decided *inside* the views.

### Recommendation: a de-risked, incremental hybrid
Do **not** rewrite the engine wholesale. Instead:
1. Pick **one** high-traffic domain (candidate: six-year graduation rates, or fall
   enrollment — both already well-understood and benchmarked).
2. Build a single curated, year-harmonized view for it, plus a guarded read-only SQL path.
3. Run both engines on the same question set; compare **code size, latency, cost, and
   accuracy** (reuse the diagnostic batch harness).
4. Expand to more domains only if the pilot clearly wins; keep the typed-plan engine as the
   long-tail fallback either way.

This matches the plan's "analysis before surgery" principle and makes D2 an evidence-based
call rather than a bet. **Owner decision needed:** (a) stay on Option A (stop here — the app
is already much simpler), or (b) authorize the Option C pilot on one domain.

## Open decisions log

| ID | Decision | Status |
| --- | --- | --- |
| D1 | Feature inventory keep/simplify/drop | Done — keep all; ⚠ simplify-candidates #3/#13/#19/#21 pending owner yes/no |
| D2 | Architecture fork (typed-plan everywhere vs. curated views + guarded SQL) | Analysis done; recommend **Option C pilot on one domain**. Owner to choose A (stop) vs C (pilot) |
| D3 | Target module map approval | Satisfied for the ✅ consolidation groups (done); full ~15–18 map not finalized |

## Change log

| Date | Change |
| --- | --- |
| 2026-10-26 | Plan created from the structure investigation. Module consolidation observed already underway on `refactor/consolidate-modules` (uncommitted). |
| 2026-10-26 | Lever A consolidation (Phases 3–4) completed: 7 commits on `refactor/consolidate-modules`, 53 → 33 `.py` files (~30 app modules), no functionality removed, each group's tests green. Combined suite 348/349 (1 pre-existing env failure); branch pushed. |
| 2026-10-26 | Phase 2 non-app bulk relocation: untracked 302 generated eval/mockup artifacts; confirmed `.packages`/`proposed_plans`/annual-SQLite already gitignored; added DOCS_INDEX.md. Tracked files 970 → 668. Phases 0/1/5 (decisions, feature inventory, prune/architecture) still open. |
