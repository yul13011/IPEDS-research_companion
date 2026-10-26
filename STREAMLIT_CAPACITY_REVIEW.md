# Streamlit Community Cloud capacity review

October 23, 2026. No remote app was deployed during this investigation.

## Assessment

Community Cloud is a plausible host for a limited pilot with R2 supplying immutable database files. The database package fits the published disk ceiling. Reliable memory use, cold-start behavior, and concurrent-session capacity have not been demonstrated; do not describe the app as production-capacity verified.

## Published capacity

The current official management page still labels its approximate resource figures as February 2024: CPU 0.078 cores minimum / 2 cores maximum; memory 690 MB minimum / 2.7 GB maximum; storage no minimum / 50 GB maximum. These are not guaranteed reserved resources, and the page says limits may change without notice. The maximum is not a safe operating target.

Apps sleep after 12 hours without traffic and a visitor can wake them. The same page offers applications for increased resources for educational, nonprofit, open-source, or other public-benefit uses. Eligibility and approval are not established for this project.

Sources:
- https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app
- https://docs.streamlit.io/deploy/streamlit-community-cloud/status

## Application findings

- Runtime databases total 3,057,135,616 bytes (2.8472 GiB), comfortably below the published 50 GB maximum disk figure. Dependencies, download staging, and runtime outputs need additional disk. Stream downloads directly to disk; do not collect entire database downloads in RAM.
- SQLite reads local files in read-only mode. The application does not load all annual databases into pandas at startup. Database size therefore does not equal required process RAM.
- `prototype/query_engine.py` bounds source reads at 20,000 rows per source and output at 5,000 rows. It materializes intermediate Python dictionaries and pandas frames. Multiple sources, joins, and simultaneous requests can still consume substantially more memory than the displayed results.
- `prototype/catalog.py` applies a SQLite progress-handler deadline (20 seconds by default). This bounds database work but is not an end-to-end request deadline.
- `prototype/ui.py` retains up to 30 conversation entries. Full answers can include source evidence, so per-session growth needs measurement; older README retention descriptions are not authoritative for current code.
- `prototype/exports.py` builds an openpyxl workbook and its output bytes in memory. Concurrent exports may increase peak memory.
- `prototype/unit_metadata.py` and other modules have bounded process caches. Their contribution and session retention should be profiled under representative usage.
- `prototype/catalog_planner.py` writes local proposal JSON. Configure a writable temporary location and retention, or durable storage if these records must survive host lifecycle changes.
- Cloud hosting uses Linux and launches from repository root. Test the complete package without Windows paths or project-local installed binaries.

## Measurement status and next gate

The initial local Windows probe stalled in the test runner's loopback socket creation and was interrupted. A subsequent probe with loopback access completed successfully: see `LOCAL_PERFORMANCE_REPORT.md` and `evaluations/capacity_local_results.json`. It measured approximately 202 MiB peak parent-process resident memory and 539 MiB sampled private committed memory, including two retained test UI sessions and two concurrent national backend queries. These are different memory measures, not additive. No live Claude calls were made. The local measurements support a limited pilot but do not establish Linux container memory or actual browser concurrency capacity.

Prepare a separate staging deployment and record:
1. Fresh R2 download/hash-validation time and disk usage; successful recovery from interrupted download.
2. Idle and peak memory for metadata search, ten-year analyses, broader categorical/population queries, and Excel/audit exports.
3. Repeated analysis and export cycles to check retained memory, including long conversations.
4. One, three, and five concurrent sessions, with actual end-to-end latency and errors. These are test levels, not supported-capacity claims. Bound live API use separately.
5. Restart/wake behavior, data reuse/redownload behavior, and proposal-file retention. Do not assume local files are durable across all lifecycle events.

Use a conservative staging target below the documented 690 MB lower memory figure (for example, under approximately 500 MB peak for the intended pilot workload), and treat it as a project target rather than a platform guarantee. If workload memory exceeds that target or the host throttles or restarts, optimize measured hotspots or use a host with explicitly allocated memory and persistent disk. Do not promise simultaneous-user capacity before testing it.

## Recommendation

Proceed with packaging and R2 bootstrap preparation for a new staging app. Use Community Cloud for a limited pilot only after the above checks pass. R2 solves file storage/delivery; it does not raise Community Cloud's CPU or memory limits. Preserve the original graduation-rate deployment throughout.
