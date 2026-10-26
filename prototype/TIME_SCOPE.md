# Longitudinal follow-up time scope

October 20, 2026: fixed endpoint years being mistaken for a complete single-year selection.

The reported conversation was replayed with the configured live planner and a confirmed Mount Holyoke identity. Before the fix, the context resolver correctly retained total fall enrollment and produced “10-year trend … ending with fall 2024.” The reviewed planner's deterministic `canonical_time` then extracted the sole four-digit date, 2024, and overwrote the model's time scope with `[2024]`. The renderer correctly produced a single-year bar for the one retrieved observation. The same occurred with “10 fall terms ending with fall 2024.” This was date binding, not lost institution memory or an inability to draw lines.

## Rules

- `time_scope.trend_years` resolves a relative duration before binding an isolated endpoint year. A ten-year window ending in 2024 means 2015–2024, inclusively.
- Supported duration forms include 10-year/ten-year/10‑year trends, past/last N years and N fall terms. Starting-year windows are also inclusive.
- A bare longitudinal/trend request retains an established multi-year interval. After a single-year result, the default is the supplied ten-year observation window. Reviewed graduation cohort trends retain cohort time and its available 2009–2018 window.
- Explicit date lists/ranges remain under existing period/cohort binding. Conflicting stated durations versus endpoints clarify; unavailable years are preserved for validation, never silently clipped. Current ten-year execution bounds remain.
- A six-year graduation population definition is not a six-observation trend window.
- Catalog annual-source selection applies a requested window before inheriting a previous single-year scope. Annual source fields/definitions still must be rebound and validated; expanding a graph alone does not create observations.
- Pure time-only trend continuations carry institution/measure context. The offline institution fallback must not treat “a 10-year trend” as a school name. Explicit institution names and UNITIDs continue through normal confirmation.
- A trend request is an analytical change, not a formatting-only edit: fetch and validate the annual data, then let the actual observation count select a line chart. All years remain labeled.

Memory-resolution instructions now ask for explicit inclusive trend endpoints while retaining population, measure and time-basis distinctions. The deterministic binder protects against the original endpoint-only rewrite even if it recurs.

## Evidence

`tests/test_trend_followup.py` covers endpoint/word/hyphen forms, shorter windows, conflicts, unavailable periods, cohorts, catalog inheritance, the exact bad context rewrite, immutable original lookup data and both actual Streamlit chat follow-ups. The latter uses the real local planner/source queries and inspects the emitted line mark and all ten year ticks.

`tests/trend_followup_live.py` replays the three prompts against the configured planner with Mount Holyoke confirmed. `evaluations/trend_followup_live_before.json` records one-year bars for both trend follow-ups. `evaluations/trend_followup_live_after.json` records ten observations and line charts for each: 6.921 seconds for “Show a 10-year trend” and 7.673 seconds for “Show a longitudinal trend.” These are single-run server answer-ready measurements, excluding browser paint; they do not establish a performance improvement. General per-test timing remains in the combined regression report.
