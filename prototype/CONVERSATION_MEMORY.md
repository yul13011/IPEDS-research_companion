# Conversation memory

Implemented October 19, 2026. This supersedes the last-plan-only memory behavior.

The Streamlit session retains 30 question/answer exchanges for display. `memory.py` builds a request-local shared context from up to 12 recent turns, subject to a 48,000-character turn budget; unusually large plans are summarized. It includes user questions, resolved interpretations, answer summaries, query plans, bounded definitions, pending clarification and presentation settings. SQL, source audit payloads and full numerical result tables are excluded from the model context. The latest analytical plan is identified as the active analysis regardless of whether it came from the reviewed or catalog route.

When AI is enabled and history exists, one bounded model call resolves the current question into a standalone request or a necessary clarification. It can replace/add institutions, preserve population/period/grouping/denominator/method, apply corrections, or return to a referenced earlier analysis. A fully specified new question overrides earlier scope. Ambiguous references should ask a concise question before any numerical query. Explicit current-question years must survive resolution, and referenced turn numbers must exist.

Both planners receive the same context through a ContextVar scoped to the request. The context is reset even after errors and is not shared across sessions. The resolver cannot retrieve source values or execute calculations. Resolved queries pass the usual metadata, population, arithmetic and runtime checks; historical answers are not fresh statistical evidence. The interpretation is shown when a follow-up produces results, and the original question, resolved request and referenced turns are included in audit metadata.

Display-only edits still reuse the previous validated result locally. Without AI, a small fallback handles simple institution replacements and percentage continuations; general conversational interpretation requires AI.

Memory is session-only. New conversation clears history and the previous plan. A new/reconnected session or server restart can lose it. Saved source/query audits are not searched as conversation memory. There is no cross-session user profile, automatic learning from corrections, or unlimited recall. This change does not expand the engine's statistical methods.

The settings caption describes the expanded provider payload. Answer-ready latency and model usage/cost include context resolution; the separate conversation-resolution timing is retained. Live follow-ups in the acceptance sample took 8.17–15.59 seconds total; context resolution itself took 2.56–4.87 seconds. This is a small sequential sample, not an SLA.

Verification:

- `tests/test_memory.py`: bounded history, offline continuations, request isolation, clarification without execution, usage accounting, explicit-year/reference checks, supported provider transport, actual institution/scope continuation, and UI history forwarding/clearing.
- `tests/memory_latency.py --live`: Yale race counts → now Harvard → percentages → new Yale admissions question → return to Harvard race counts. All five outputs matched independent source SQL; report in `evaluations/memory_latency.json`.
- Combined regression results and per-test timings: `evaluations/catalog_execution_verification.json`.

No owner input is required. No cross-session persistence was added.

Final combined verification: 101 tests passed with zero failures/errors. The app was restarted with these changes and its health endpoint returned ok.

Clear conversation control: a compact button above the composer resets session context and errors, including an error before any first answer is stored. The control also clears pending institution confirmation and remembered conventions. Ten targeted memory/loading checks passed, including recovery from the reported planning-tool-request limit. The underlying planner guard remains in place.
