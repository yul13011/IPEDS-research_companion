# Internet deployment feasibility

Reviewed October 26, 2026. Investigation only: no account configuration, uploads, repository pushes or remote deployment. The original graduation-rate app remains separate.

## Recommendation

Deploy the redesign as a new, initially limited app using GitHub, Streamlit Community Cloud and Cloudflare R2 Standard storage. This is a credible low-cost pilot architecture. The current app needs deployment preparation and public-use controls before anonymous access. No database migration or application rewrite appears necessary for that pilot. Capacity for a broad audience remains unverified.

Community Cloud is free and connects to GitHub repositories. A private code repository can serve a public app by changing app visibility. Keep the redesign in a new repository and URL rather than pushing this mixed local workspace into the original app's repository. The workspace currently has the original graduation-rate Git remote. [Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud), [sharing and visibility](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app).

## Proposed arrangement

| Service | Responsibility |
| --- | --- |
| GitHub | Application code, requirements, configuration, small JSON/JavaScript assets, versioned data manifest |
| Streamlit Community Cloud | Python application, browser sessions, charts, read-only SQLite queries and server-side Claude calls |
| Private R2 Standard bucket | Durable, versioned copies of the runtime database files |
| Anthropic API | Paid model inference using a deployment-specific credential and spending controls |

The Streamlit server downloads matching database files from R2 to local disk, then queries them using the existing SQLite code. R2 is object storage, not a replacement SQL query server. Users do not download all databases to their browsers. The current ordinary `sqlite3` connection cannot simply be pointed at an R2 object URL.

## Data package verified locally

`evaluations/deployment_feasibility_inventory.json` records the candidate runtime inventory and exact sizes:

- Ten annual databases, 2015–16 Final through 2024–25 Provisional.
- `metadata_catalog.sqlite` — 460,443,648 bytes.
- `analysis_catalog.sqlite` — 22,380,544 bytes.
- `unit_catalog.sqlite` — 46,436,352 bytes.
- Total: **3,057,135,616 bytes = 3.057 GB = 2.847 GiB**, across 13 databases.

The application imports the original source descriptions and physical-schema evidence from these catalogs. It does not need the original Access files, conversion outputs, full source workbook collection or the old prototype to serve queries. Static inspection found `field_semantics.sqlite` referenced by a preparation builder, not production runtime; omit it provisionally and confirm in a clean-package smoke test. This is packaging analysis, not authorization to delete anything.

The package also needs `prototype`, `analysis_catalog`, `measure-registry/reviewed_measures.json`, the JSON/JavaScript assets beside the Python modules and root `.streamlit/config.toml`. Preserve the relative directory layout. The guide can be generated from the packaged metadata and definitions; its portable Markdown/JSON can accompany the release. Exclude `.packages`, local environments, secrets, proposal logs, test outputs and data-preparation tools from the deployment bundle.

## Hosting and storage costs

R2 Standard currently includes 10 GB-month storage, one million Class A operations and ten million Class B operations monthly; direct egress has no charge. The 3.057 GB current release fits the storage allowance if other account usage leaves room. Storage above the allowance is $0.015/GB-month, with separately priced requests. Use Standard rather than Infrequent Access for this small frequently accessed package. An R2 subscription must be enabled even when usage remains within included allowances. [Pricing](https://developers.cloudflare.com/r2/pricing/), [setup](https://developers.cloudflare.com/r2/get-started/).

Expected initial infrastructure bill: $0/month for Community Cloud and potentially $0/month for R2 within included usage. Claude usage is additional and is likely the main variable expense. Current mixed test runs are not a reliable fixed price per visitor/question. A custom domain is unnecessary for the initial Streamlit URL. No paid-host estimate is needed until free-host staging measurements show a reason to move.

## Resource feasibility

The official Community Cloud page currently retains approximate figures labeled February 2024: 0.078–2 CPU cores, 690 MB–2.7 GB memory and up to 50 GB disk. These are variable limits, not reserved capacity. Apps without traffic for 12 hours hibernate. This supports trying the data package on the service, not promising availability or performance. [Resource and hibernation documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app).

The October 23 local test observed about 202 MiB peak resident memory and 539 MiB sampled private committed memory. These measures are not additive. Two retained test UI sessions plus two concurrent backend workloads completed. The test used Windows, pre-existing local data and offline model execution; it was not a hosted browser load test. It predates the latest request-task and guide features. See `LOCAL_PERFORMANCE_REPORT.md` for methods and qualifications.

SQLite reads files on disk instead of loading all 3 GB into RAM. This is favorable for a one-to-two-active-user pilot. It does not establish capacity for dozens of simultaneous visitors. National queries, intermediate frames, long histories, chart rendering and concurrent Excel exports can increase CPU/memory demand. Current source/output limits help but are not a server-wide concurrency or spending limit. Some population queries have a 60-second SQLite deadline, so CPU throttling needs testing.

Local host storage is not durable. Reboots, redeployments or other lifecycle events must be recoverable from R2. Avoid promising a particular cold-start download time until measured. [Local-storage persistence qualification](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data).

## Work needed before deployment

### 1. Reproducible R2 bootstrap

There is no R2 downloader in the current application, and its requirements do not include an S3 client. Add one before the UI's missing-catalog check runs. For the first deployment, fetch the complete candidate package; current guide/coverage inventory inspects all annual sources, so a year-by-year lazy-download promise would require additional refactoring.

Use a release manifest containing object keys, relative local paths, sizes and SHA-256 checksums. Stream downloads to disk, bound parallelism, use partial files and atomic completion, and guard concurrent initialization across sessions. Verify downloaded files, reuse the completed matching release, and fail clearly instead of serving mismatched catalogs. Keep code and data versions paired for rollback. Do not fetch the full package on every Streamlit rerun or per user.

R2 supports Python access through its S3-compatible interface. Give the app a bucket-scoped **Object Read only** credential; keep upload permissions separate. Store credentials server-side. No public bucket, custom-domain routing or browser-side storage credentials are necessary. [Python SDK integration](https://developers.cloudflare.com/r2/examples/aws/boto3/), [token permissions](https://developers.cloudflare.com/r2/api/tokens/).

### 2. Clean hosted package

Use `prototype/app.py` as entry point and Python 3.12 as the first test target, matching the locally tested major/minor version. The declared requirements already cover Streamlit, Anthropic, pandas, Altair, image conversion, Excel and JSON Schema. Add the selected downloader dependency and lock the tested versions. Do not upload Windows-installed `.packages` binaries.

Community Cloud executes from repository root; the configuration must live at root, and requirements can be at root or next to the entry point. Verify Linux installation, SQLite full-text support, file-name case, chart/image exports and fonts. No clean Linux install was performed during this investigation. [File/dependency organization](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization).

### 3. Secrets and public-use controls

The existing key loader accepts `ANTHROPIC_API_KEY` from the environment and local secret-file locations. Configure the deployed key in Streamlit secrets, not GitHub. Configure R2 secrets there too. A visitor can use the application without receiving those credentials. [Hosted secrets](https://docs.streamlit.io/deploy/concepts/secrets).

Use a dedicated Anthropic workspace/key, configure workspace spending and rate limits, and add app-level request limits, bounded simultaneous model work and an operator-controlled AI cutoff. Per-session counters alone are insufficient because sessions can be recreated. Provider limits should remain the backstop if app-local counters reset. [Anthropic workspace controls](https://platform.claude.com/docs/en/manage-claude/workspaces).

Current About-page controls allow every visitor to change model strategy and enable development tools. The development-mode switch is a UI convenience, not administrator authorization. Before public launch, enforce developer/model overrides through server configuration or authenticated operator access. Keep the intended economical model policy for ordinary visitors. For the initial pilot, invite-only access or authenticated users make usage attribution easier; anonymous public access needs stronger abuse/cost controls.

`catalog_planner.py` also writes proposal JSON to `data/proposed_plans`. This can contain question/context information. Decide what needs retention, move temporary records to a bounded writable location and avoid accumulating every public request indefinitely. Do not treat local files as durable feedback storage or silently introduce question logging.

## Deployment sequence and acceptance

1. Build a clean, separate repository bundle and checksum manifest. Keep the original prototype and URL unchanged.
2. Enable R2 and upload the reviewed database release; use separate upload and app-read credentials.
3. Implement/bootstrap data, public-mode settings and usage controls; verify a clean install without OneDrive or local dependency folders.
4. Deploy a preview app through GitHub → Streamlit with hosted secrets. Measure first boot, restart/wake behavior, repeat access and integrity failures.
5. Test one and two real browser sessions first, then five active sessions. Include year/guide questions, Ivy comparisons, categorical/national queries, graduate percentages, multi-part requests, concurrent downloads and API-limit failures. Monitor memory, CPU, latency, session separation and token costs.
6. Publish a limited pilot once its measured behavior is acceptable. If resource or cold-start behavior fails, use a host with explicitly allocated memory/CPU and persistent disk while retaining SQLite and R2 backup/release delivery.

No account provisioning, Linux build, R2 transfer or hosted concurrency test has happened yet. Those are the remaining evidence needed to move from feasible design to a working internet deployment.
