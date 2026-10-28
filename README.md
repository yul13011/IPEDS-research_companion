# IPEDS Research Companion

**▶ Live app: https://ipeds-research-companion.onrender.com**

A conversational application for exploring U.S. higher-education data. Ask a plain-English question
about a college — or about the nation as a whole — and it finds the right federal **IPEDS** data,
retrieves it, and returns an answer with the exact source definitions, a table, and (where it helps)
a chart. An Anthropic-backed planner interprets each question, but it **never writes or runs SQL
directly**: it proposes a typed, source-bound plan that deterministic code validates and executes.

---

## What it does

It answers questions across the full breadth of IPEDS — ten years of data (2015–16 through 2024–25)
for thousands of institutions — spanning every survey component. Examples:

- **Cost** — *"What is the cost of attending Yale?"* → published tuition & fees, total price of
  attendance (by residency for public schools), and average net price after aid.
- **Admissions & test scores** — *"What was Yale's admission rate in fall 2024?"*, applications,
  yield, SAT percentiles.
- **Enrollment** — *"How many undergraduates were enrolled at Smith in fall 2023?"*, by level.
- **Graduation** — *"What was the six-year graduation rate for the 2018 cohort?"*, with subgroups
  (gender, Pell, nonresident).
- **Completions** — degrees awarded, by level and program.
- **National aggregates** — *"How many bachelor's degrees were awarded nationally in 2023?"*,
  total U.S. enrollment, institution counts.
- Plus financial aid, faculty & staff salaries, institutional finance, and academic libraries.

**How it behaves, by design:**
- **Asks before guessing** — clarifies ambiguous institutions ("did you mean U.S. nonresident, not
  all international students?") and ambiguous measures, rather than inventing an answer.
- **Never fabricates** — suppressed or missing values are reported as *"not reported,"* never zero.
- **Shows its sources** — every answer carries the source table, variable definitions, reporting
  period, and the assumptions it made.
- **Deterministic where it counts** — common, high-value topics (e.g. cost) use source-bound routes
  so they return the complete, correct columns every time instead of relying on the model's guess.

## How it works

The planner uses a **typed-plan engine**: the language model proposes a *typed, source-bound plan*
(which institutions, which release years, which exact IPEDS variables, what calculation) — it does
**not** emit raw SQL. Deterministic code then validates that plan against the metadata catalog and
the physical database schema, compiles it to a **bounded, read-only SQLite** query, executes it, and
validates the results before anything is shown.

Two answer routes:
1. **Reviewed measures** — a curated set of source-bound measures (admission rate, graduation rate,
   salaries, …) that run deterministically, fast, with no model call.
2. **Catalog planner** — for everything else, a two-stage model pass (**Haiku 5.5** interprets the
   question, **Sonnet 5.5** plans against the >500-table catalog), always validated by the same
   deterministic executor.

**Stack:** Python · Streamlit · SQLite · Anthropic API (Claude). Deployed on Render; the data is
served from a Hugging Face dataset. See [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md).

## Data scope

- **Ten annual IPEDS releases**, 2015–16 Final through 2024–25 Provisional (the 2024–25 figures are
  provisional and may be revised).
- **~500 source tables** per the IPEDS Access databases, ~24,000 variable definitions and ~124,000
  category codes in the metadata catalog.
- **All twelve IPEDS survey components** (official codebook names): Institutional Characteristics,
  Admissions and Test Scores, Fall Enrollment, 12-month Enrollment, Completions, Graduation Rates,
  Outcome Measures, Student Financial Aid, **Cost**, Human Resources, Finance, Academic Libraries.
- Stored as per-release **SQLite** copies of the IPEDS databases plus catalog/metadata databases
  (~3.1 GB total).
- Conventions to know: an unqualified "graduation rate" means the **six-year bachelor's** rate; a
  six-year cohort is observed six years after entry; finance "YYYY-YY" names the **fiscal year** by
  its end year; net price covers aid recipients and lags the sticker year by the IPEDS cycle.

## Quality & evaluation

- **[EXAMPLE_QUESTIONS.md](EXAMPLE_QUESTIONS.md)** — a catalog of example/test questions organized by
  survey, each with its expected answer shape and the exact source variables.
- **[evaluations/eval_harness.py](evaluations/eval_harness.py)** — runs those questions through the
  real pipeline, recomputes ground truth from the live data (never hardcoded), and reports pass/fail
  as a regression suite. The `prototype/tests/` unit tests guard the code logic alongside it.

## Running locally

Python 3.11+. From this directory, with the data present (the per-release SQLite under `data/` — see
"Rebuilding the data" — or an `IPEDS_DATA_DIR` pointing at it):

```bash
pip install -r prototype/requirements.txt
export ANTHROPIC_API_KEY=sk-...        # or put it in .streamlit/secrets.toml
streamlit run prototype/app.py
```

On Windows, `prototype/run.ps1` launches it with the bundled interpreter. See
[prototype/README.md](prototype/README.md) for details.

## Deployment

Live on **Render** (always-on web service). The ~3.1 GB of data is not in the repo; it lives in a
Hugging Face **dataset** and is pulled once to the service's persistent disk on first boot
(`prototype/data_bootstrap.py`), after which SQLite is read locally. Full runbook:
[DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md).

## More documentation

- Architecture & design history: [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md)
- Cost variable reference: [COST_VARIABLES_REFERENCE.md](COST_VARIABLES_REFERENCE.md)
- App code & launch: [prototype/README.md](prototype/README.md)

## What is and is not in version control

Tracked: all Python, the markdown design/review docs, `requirements.txt`, `.streamlit/config.toml`,
`measure-registry/`, `release-comparison/` metadata, and small reference CSV/JSON.

**Not tracked** (see [.gitignore](.gitignore)) — big, secret, or regenerable:

| Excluded | Why | How to restore |
| --- | --- | --- |
| `.packages/` | Vendored dependencies | `pip install -r prototype/requirements.txt` |
| `data/annual/**/*.sqlite`, `data/*.sqlite` (~3 GB) | Derived per-release databases; each 20–440 MB, over GitHub's 100 MB limit | Rebuild from the raw `IPEDS Data/` Access files (below), or pull from the Hugging Face dataset |
| `data/proposed_plans/` | Regenerable planner cache | Regenerates at runtime |
| `.streamlit/secrets.toml` | Holds the Anthropic API key | Create locally (see prototype/README.md) |
| build artifacts, logs (`*.class`, `*.pyc`, `*.log`, `local_logs/`) | Not source | Regenerate as needed |

## Rebuilding the data from source

The SQLite databases and catalog are derived from the raw IPEDS Access databases and codebooks in
the sibling `IPEDS Data/` folder. With Python 3.11+ from this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r prototype/requirements.txt
# Convert the annual Access databases to SQLite and build the metadata catalog:
.\.venv\Scripts\python.exe -m ingestion.import_annual
.\.venv\Scripts\python.exe -m ingestion.build_catalog
# Build the reviewed-measure registry:
.\.venv\Scripts\python.exe -m prototype.build_registry
```

See [ingestion/](ingestion/) and [prototype/README.md](prototype/README.md) for details and
verification steps. Exact module flags may differ by release; confirm against the scripts before a
full rebuild.

## Caveats

This is a **demonstration**, not a validated reporting tool. Figures should be checked against the
official IPEDS sources (College Navigator / the IPEDS Data Center) before any decision or
publication; 2024–25 is provisional. The application code is provided as-is, and the underlying data
is public U.S. federal data from the National Center for Education Statistics.
