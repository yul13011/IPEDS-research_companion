# IPEDS Research Companion

A conversational application for discovering, retrieving, analyzing, visualizing, and
exporting U.S. IPEDS data across ten annual releases (2015–16 through 2024–25). Local
Streamlit app over per-release SQLite copies of the IPEDS Access databases and their
codebook catalog, with an Anthropic-backed planner that cannot execute SQL directly.

- App code and launch instructions: [prototype/README.md](prototype/README.md)
- Architecture and design history: [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md)
- Status and roadmap: [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)
- Open findings/ideas: [APP_FINDINGS_AND_IDEAS.md](APP_FINDINGS_AND_IDEAS.md)
- Latest review: [DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md](DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md)

## What is and is not in version control

Tracked: all Python, the markdown design/review docs, `requirements.txt`,
`.streamlit/config.toml`, `measure-registry/`, `release-comparison/` metadata, and small
reference CSV/JSON.

**Not tracked** (see [.gitignore](.gitignore)) — big, secret, or regenerable:

| Excluded | Why | How to restore |
| --- | --- | --- |
| `.packages/` | Vendored dependencies | `pip install -r prototype/requirements.txt` |
| `data/annual/**/*.sqlite`, `data/*.sqlite` (~3 GB) | Derived per-release databases; each 20–440 MB, over GitHub's 100 MB limit | Rebuild from the raw `IPEDS Data/` Access files (see below) |
| `data/proposed_plans/` | Regenerable planner cache | Regenerates at runtime |
| `.streamlit/secrets.toml` | Holds the Anthropic API key | Create locally (see prototype/README.md) |
| service-account `*.json` | Live Google credentials | Keep private; never commit |

## Rebuilding the data from source

The SQLite databases and catalog are derived from the raw IPEDS Access databases and
codebooks in the sibling `IPEDS Data/` folder. With Python 3.11+ from this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r prototype/requirements.txt
# Convert the annual Access databases to SQLite and build the metadata catalog:
.\.venv\Scripts\python.exe -m ingestion.import_annual
.\.venv\Scripts\python.exe -m ingestion.build_catalog
# Build the reviewed-measure registry:
.\.venv\Scripts\python.exe -m prototype.build_registry
```

See [ingestion/](ingestion/) and [prototype/README.md](prototype/README.md) for details
and verification steps. Exact module flags may differ by release; confirm against the
scripts before a full rebuild.
