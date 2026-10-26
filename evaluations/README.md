# Yale regression cases

The project owner supplied five validated Yale CSV tables in `../Test cases/`. These remain the immutable expected values. This folder contains deterministic data-layer retrieval checks and generated question fixtures for the future agent, not a completed agent implementation.

Run `run_yale_benchmarks.py` with the bundled Python executable. It writes results even when differences occur, then exits 1 if any supported numeric value mismatches or is missing. Unsupported fields, years outside the imported corpus, and unresolved grouping definitions are separately labeled. Run `write_yale_report.py` after an evaluation to regenerate the review document.

Definitions and user clarifications are recorded in `benchmark_definitions.json`. Do not change them, expected source values, or tolerances merely to fit IPEDS outputs. A definition change requires evidence/user clarification; unresolved differences stay visible.

Results contain expected/actual values, exact SQL, parameters, source file/row, annual database, interpretation and precision. Counts and SAT scores compare exactly; fraction-valued rates allow 0.0005 based on the benchmark's three-decimal display precision.

No LLM API is called; no user source CSV, original IPEDS source, annual SQLite copy or production app is modified. See `YALE_BENCHMARK_REVIEW.md` for outcomes and limits.
