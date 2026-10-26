# Redesign deployment plan

Startup latency follow-up, October 26: [Always running hosting comparison](ALWAYS_ON_HOSTING_COMPARISON_2026-10-26.md) recommends a paid Render application instance plus persistent disk at a $27.50/month base price if predictable first visits take priority. It also compares lower-cost DigitalOcean and usage-based Railway. This is a researched alternative to the free-host pilot, not an approved purchase.

Current resumption document: [IPEDS App Deployment Plan](<IPEDS App Deployment Plan.docx>), prepared October 26, 2026. It includes implementation phases, launch checks, areas of concern, open decisions and supporting-file references. The [October 26 feasibility review](DEPLOYMENT_FEASIBILITY_2026-10-26.md) and `evaluations/deployment_feasibility_inventory.json` provide the current investigation and exact candidate runtime inventory. The October 23 notes below are historical context.

Prepared October 23, 2026. Planning only; no deployment or account changes performed.

## Recommended approach

Use the original graduation-rate prototype's GitHub → Streamlit hosting pattern as the starting point. Deploy the redesign as a separate staging app and preserve the original app, repository deployment settings, credentials, and URL. Test Streamlit Community Cloud first; retain it only if measured startup, resource use, and concurrent-user behavior are acceptable. Otherwise deploy the same Streamlit application to a container host with persistent local storage. No database-service migration is required for this pilot.

The original deployment is documented in `../Gradrates/PROJECT_HANDOFF_College_Graduation_Rate_Explorer.md` and `../Gradrates/README.md`. Its historical public URL is https://college-graduation-rate-explorer.streamlit.app/ ; its current live status was not checked for this plan.

## What carries over and what changes

| Area | Original prototype | Redesign deployment |
| --- | --- | --- |
| Interface | Streamlit and Altair | Retain Streamlit and Altair |
| AI | Claude API | Retain configured Claude models; separate deployment key and usage tracking |
| Database | One approximately 6 MiB SQLite file | Ten annual SQLite files plus metadata, analytical, field-semantics, and unit catalogs; approximately 3 GiB total runtime data |
| Source control | GitHub-connected deployment | Separate deployment repository recommended, with a reproducible release manifest |
| Secrets | Streamlit hosted secrets | Same pattern; no local secrets or service-account files in deployment bundle |
| Feedback | Google Sheets question/feedback tabs | Explicitly implement and validate equivalent feedback if wanted; do not assume the redesign already includes it |
| Conversation | Session state | Verify isolation between users; explain that refreshing/restarting can lose session context |

## 1. Prepare a portable deployment package

- Package `agent-redesign` as the deployment repository root. Keep `prototype`, `analysis_catalog`, `measure-registry`, required data files, and root `.streamlit/config.toml` in their current relative layout.
- Use `prototype/app.py` as the hosted entry point. It adds the project root to the Python import path. The Windows `run.ps1` and bundled Codex Python path are local launch conveniences, not hosted startup requirements.
- Install dependencies from a verified requirements file; select and pin a supported Python version after a clean Linux install. Check all imports against that environment, including Excel export and chart rendering.
- Exclude `.packages`, caches, original Access databases, local credentials, conversion tooling, historical evaluation outputs, and development mockups from the runtime bundle. Preserve those in the local project/archive.
- Enumerate all runtime file dependencies, including JSON, JavaScript, and other UI assets. Verify no live feature still depends on a deleted cleanup artifact.
- Runtime dependency review on October 23 identified ten annual databases (2,410.77 MiB) and three runtime catalogs: `metadata_catalog.sqlite` (439.11 MiB), `analysis_catalog.sqlite` (21.34 MiB), and `unit_catalog.sqlite` (44.29 MiB). Together these are 3,057,135,616 bytes, or 2.8472 GiB. `field_semantics.sqlite` (67.17 MiB) is referenced by preparation/test code, not the inspected runtime; exclude it from the hosted runtime bundle while preserving it locally. Build an explicit size/SHA-256 manifest and verify this selection in a clean deployment before launch.
- Preserve `evaluations/results/yale_cases.json` in the runtime package: `prototype/analytics.py` uses it to attach known discrepancy warnings. Other historical evaluation outputs need not be bundled wholesale. Keep `prototype/population_benchmark_guards.json` and the registry/example/learning JSON files used by runtime modules.
- Audit stored paths as well as Python paths. Catalogs and exports contain original Windows source-file references. Preserve original provenance internally, but display portable release/file identifiers in public results. Avoid changing catalog identity-bearing records without rebuilding dependent catalogs and verification.

## 2. Decide and test data delivery

Do not commit these large databases as ordinary Git blobs. For the first staging trial, evaluate Git LFS, which Streamlit Community Cloud supports, against the account's current storage and bandwidth allowances. Measure fresh-clone/deployment behavior before committing to it.

If LFS is unsuitable, keep immutable, versioned database artifacts in object storage and download them to local disk at startup. Verify hashes before exposing the app, publish a complete matching data release atomically, and reuse downloaded files when available. SQLite must query local files, not an object-storage URL. Account for cold-start downloads and host disk limits.

Do not select a paid storage/hosting plan until current allowances, costs, and the pilot's measured requirements are reviewed.

## 3. Resolve runtime writes and secrets

- Load `ANTHROPIC_API_KEY` from hosted secrets; use a separate deployment credential so staging usage can be identified and revoked independently.
- Review API configuration, available models, timeouts, bounded retries, per-request limits, and error messages in the deployed environment.
- `prototype/catalog_planner.py` currently writes proposals to `data/proposed_plans`. Decide whether these are temporary session artifacts or durable records. Use a writable location, unique identifiers, and a retention policy; do not assume host-local writes survive redeployment.
- Preserve database read-only access. Keep session results and downloads isolated across users. Ensure shared caches do not expose another user's question or answer.
- For a public pilot, add request/concurrency limits and an operator-controlled AI spending cutoff. Record latency, token usage, errors, and application/data release IDs without logging credentials.
- If restoring Google Sheets feedback, use separate sheets/tabs for the redesign and keep logging failures from blocking answers. Define question-logging disclosure and retention before collecting questions.

## 4. Deploy a separate staging app

1. Create the deployment repository/package and record the exact application revision and data manifest.
2. Run a clean Linux installation with only packaged dependencies and data. Do not rely on `.packages`, Codex tooling, OneDrive, or Windows paths.
3. Run the registered regression suite, plus focused export, source-citation, unit/categorical, and session-isolation checks. Keep known benchmark discrepancies visible and retain existing unsupported-query safeguards.
4. Configure a new Community Cloud app using the repository, staging branch, and `prototype/app.py`. Add secrets through the hosting settings.
5. Measure cold-start time, warm latency, disk use, peak memory, and behavior during simultaneous sessions. Database file size alone does not establish memory requirements.
6. Test admissions, graduation trends, faculty, categorical comparisons, follow-ups, clarification, missing data, charts, CSV/Excel/audit downloads, API failures, and browser refresh.
7. Begin concurrency checks with 1, 3, and 5 active sessions. Use representative requests, bound live API spending, and agree a pilot capacity/latency target before treating these checks as launch acceptance.

## 5. Launch gate and rollback

Launch a limited pilot only when the clean deployment reproduces expected behavior, all data hashes match, session isolation passes, resource tests support the intended audience, and operators can inspect failures and disable AI requests. Existing known discrepancies must remain disclosed or blocked as appropriate; passing tests do not certify all IPEDS answers.

If Community Cloud cannot reliably fit the data/resource profile, move the same application to a container host with persistent local disk and sufficient measured memory headroom. Add TLS, health checks, restart policy, and backups for durable writes. SQLite can remain the read-only analytical backend.

Keep the previous working application revision and matching data release. Roll back code and data together. Pilot the redesign at a new URL; do not redirect or replace the original graduation-rate app during this phase.

## Deliverables before deployment approval

- Reviewed runtime bundle, dependency lock, and data manifest.
- Clean Linux verification and bounded concurrency/resource report.
- Staging URL, startup/operating instructions, usage controls, and rollback procedure.
- Hosting/data-delivery choice with current cost estimate based on measured needs.
- Owner review of the staging app before public launch.

## Official hosting references

- File organization and Git LFS: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization
- Deployment configuration: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- Secrets: https://docs.streamlit.io/deploy/concepts/secrets
- Resource troubleshooting: https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app
