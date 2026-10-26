# Local performance and hosting estimate

October 23, 2026. Offline tests against the current application and real local databases. No Claude calls or changes to application source/database files. The probe and result records are in `evaluations/capacity_local.py`, `evaluations/capacity_local_results.json`, and `evaluations/capacity_local_startup_results.json`.

## Conclusion

The measured workloads support trying Streamlit Community Cloud for a one-to-two-user pilot. Memory did not approach multiple gigabytes. A host budget of approximately 0.6–1 GiB RAM and approximately one available CPU core is a reasonable initial planning allowance, not a measured requirement or capacity guarantee. Prefer 1 GiB or more explicitly allocated RAM if buying a host. Free Community Cloud should be tried before paying, with deployed memory monitoring.

## Method and limits

Windows, Python 3.12.14, 12 logical CPUs reported by the machine. Used Windows GetProcessMemoryInfo for current and lifetime peak working set and private committed memory, sampled about every 20 ms. Stages include total Python process CPU time, not utilization as a fraction of all machine cores. Short-lived memory peaks can be missed by polling; the overall lifetime resident peak was 201.93 MiB.

Streamlit AppTest rendered two separate retained test sessions sequentially. Concurrent application backend work used two threads in the same process while those UI objects remained retained. This is a backend concurrency approximation, not a two-browser load test or full Streamlit server measurement. Windows private commit and resident working set measure different things and must not be added together; neither directly predicts Linux container accounting. Shared libraries, subprocesses if any, OS page cache, actual HTTP/WebSocket server overhead, and host resource enforcement are not comprehensively measured by this parent-process probe.

The restricted-sandbox attempt stalled in Windows socketpair creation before app rendering. The successful runs used local loopback access outside the sandbox. Thus that stall was not evidence of application startup performance.

All successful-run stages passed without recorded exceptions. Disk data and libraries were already present locally; fresh process startup does not imply cold filesystem cache. No R2 data download, network latency, Claude planning/summary, or browser painting was measured. Test-runner warnings about missing ScriptRunContext were expected for direct backend calls and did not fail UI rendering. Timings are single observations except the ten-cycle batch; not percentile or worst-case claims.

## Results

Memory figures below include the process baseline and earlier retained test state; they are not incremental per-user memory.

| Stage | Local wall seconds | Process CPU seconds | Resident memory MiB | Private committed memory MiB |
| --- | ---: | ---: | ---: | ---: |
| Fresh-process UI initialization (no prior backend workloads) | 4.79 | 4.48 | 151.33 lifetime peak at this point | 467.72 sampled peak |
| Add second empty UI test session | 0.55 | 0.56 | 145.95 sampled stage peak | 468.75 sampled peak |
| Yale admissions, five measures, one year | 0.07 | 0.06 | 89.99 sampled stage peak | 415.44 sampled peak |
| Eight Ivy League institutions, graduation rates, ten years (80 rows) | 0.13 | 0.13 | 90.59 sampled stage peak | 416.99 sampled peak |
| Catalog-driven awards query | 0.37 | 0.36 | 95.51 sampled stage peak | 422.13 sampled peak |
| CSV, Excel, audit exports for 80-row trend | 0.60 | 0.52 | 105.86 sampled stage peak | 437.15 sampled peak |
| National distance-education percentage | 2.07 | 1.53 | 127.52 sampled stage peak | 456.61 sampled peak |
| One query/export workload, after retaining two populated UI sessions | 0.43 | 0.38 | 183.62 sampled stage peak | 516.58 sampled peak |
| Two simultaneous 80-row query/export workloads | 0.74 | 1.00 | 186.89 sampled stage peak | 524.52 sampled peak |
| Two simultaneous national analyses | 2.41 | 3.14 | 201.93 sampled stage peak | 539.05 sampled peak |
| Retain 30 independent 80-row answer copies for each of two simulated users | 0.64 | 0.61 | 199.22 sampled stage peak | 525.44 sampled peak |
| Ten repeated query/export cycles in second fresh process, two empty UI sessions retained | 3.42 total | 3.00 total | 173.51 lifetime peak at this point | 496.93 sampled peak |

The retained-history case uses deep copies of the same structured trend answer. It checks that particular answer size, not 60 heterogeneous maximum-sized results. The ten-cycle batch ends at 169.06 MiB resident and 496.92 MiB private commit versus 147.38 / 470.15 before the batch. This limited sample shows modest growth; it does not establish absence of leaks.

## Estimating Community Cloud

Published Community Cloud figures remain approximate and dated February 2024: memory 690 MB minimum to 2.7 GB maximum, CPU 0.078 to 2 cores, disk up to 50 GB; limits may change. Source: https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app

Memory: the largest observed parent-process values were approximately 202 MiB resident and 539 MiB private commit. This supports a small pilot; it does not guarantee fitting the host's lower memory range once Linux/server overhead, larger results, and real sessions are included. Use approximately 0.6–1 GiB as an initial budget with headroom, then replace it with staging measurements. The 2.85 GiB on-disk database package is not loaded wholesale into RAM.

CPU: common data operations in this sample required approximately 0.06–0.52 CPU seconds; a national analysis required approximately 1.53. With one similarly performing core available, data processing should plausibly remain on the order of subsecond-to-a-few-second work for these samples. Heavily throttled CPU can make it much slower. For illustration, 1.53 CPU seconds requires at least about 3.1 seconds at 0.5 effective core or 15.3 seconds at 0.1 effective core, before I/O and other overhead, assuming equal per-core speed. Two national workloads consumed 3.14 CPU seconds together. These are capacity arithmetic examples, not predicted host latency or guaranteed CPU allocation.

End-to-end conversational latency additionally includes provider calls, source retrieval iterations, rendering, and network waits. These tests provide no estimate for Claude response time or first deployment/R2 download time. Repeat on staging with one and two actual browser sessions and representative live questions before public launch.

## Next deployment checks

1. Stream R2 downloads to disk, verify hashes, and reuse completed matching files. Measure fresh deployment and wake/restart behavior separately.
2. Monitor Linux process/container memory through one and two actual sessions, including national queries and simultaneous exports.
3. Include larger supported outputs and longer varied conversations; bound session retention or export work if measurement shows pressure.
4. Record idle, peak, and retained memory plus CPU time, latency, and failures; do not promise a user capacity from this small offline sample.
