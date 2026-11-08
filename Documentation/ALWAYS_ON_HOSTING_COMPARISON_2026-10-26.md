# Always running hosting with persistent storage

Researched October 26, 2026. No hosting account or subscription was created. Prices are USD before tax unless stated otherwise; Claude API use, optional domain registration and extra network/backup charges are separate.

## Recommendation for this app

Given the owner's priority of avoiding first-visitor wake and database-download delays, prefer a paid Render web service with 1 CPU, 2 GB RAM and a 10 GB persistent disk. The base hosting calculation is **$25 + 10 × $0.25 = $27.50/month**, about $330/year before extras. This is the recommended balance of manageable deployment, predictable base cost and compatibility with the existing Streamlit/SQLite design.

DigitalOcean is the better lower-fixed-cost choice if someone accepts responsibility for Linux server administration. Railway is a worthwhile managed pilot alternative when keeping costs below Render matters more than a fixed bill and roomy disk capacity.

This refines the earlier free-Community-Cloud pilot recommendation in light of the owner's stronger startup-latency requirement. It is a hosting recommendation, not an approved purchase or revised performance guarantee.

## Relevant application requirements

- The candidate runtime data is 13 databases totaling 3.057 GB or 2.847 GiB. It does not all need to reside in RAM.
- Existing Windows tests observed about 202 MiB resident memory and 539 MiB private committed memory; the measures are not additive and do not establish Linux/container billing or a current peak requirement.
- Use 2 GB RAM as a conservative first paid-host test target. A 512 MB instance offers inadequate margin against the existing observations; a 1 GB server is a budget experiment, not the preferred public starting point.
- Keep one application process/instance for the initial pilot, with concurrent-request limits and real-session measurements. No user-capacity commitment follows from these specifications.
- Retain Streamlit as the framework and SQLite as the validated execution layer. Changing the host does not require replacing them.

## Cost comparison

| Option | Proposed configuration | Monthly base or illustrative cost | Main tradeoff |
| --- | --- | --- | --- |
| Render | Paid web service, 1 CPU, 2 GB RAM, 10 GB persistent disk | **$27.50** | Simplest predictable managed option; disk-backed deployment has brief downtime |
| DigitalOcean Basic Droplet | Shared 1 vCPU, 2 GiB RAM, included 50 GiB SSD | **$12.00**; **$14.40** with the optional weekly percentage-priced backup plan | Lower fixed infrastructure cost; we operate the Linux server |
| Railway Hobby | Always active container, persistent volume within documented 5 GB allowance | **About $6–13 in the illustrative low-load scenario below** | Variable bill; less update/storage headroom |
| DigitalOcean budget experiment | Shared 1 vCPU, 1 GiB RAM, included 25 GiB SSD | **$6.00**; **$7.20** with optional weekly percentage-priced backups | Lowest fixed-cost candidate here, but memory headroom must be proved |

DigitalOcean's published Basic rates are $6 for 1 GiB and $12 for 2 GiB, including the stated SSD capacity. Its optional basic weekly backup plan adds 20% of Droplet cost. The annual base cost for the recommended 2 GiB candidate is $144, or $172.80 with that backup option. [Droplet pricing](https://www.digitalocean.com/pricing/droplets), [backup pricing](https://docs.digitalocean.com/products/backups/details/pricing/).

### Render

Paid compute does not idle-spin down. Data survives normal redeployments and restarts only when placed under the persistent disk mount. The free workspace tier and paid application instance are separate: the proposed base calculation does not require adding a paid Pro workspace. Configure sufficient network allowance/alerts; the currently rendered pricing page lists 5 GB included outbound bandwidth on the Hobby workspace and $0.15/GB beyond it. This is not an all-inclusive fixed bill. [Pricing](https://render.com/pricing), [service behavior](https://render.com/docs/faq).

The public pricing page contains distinct application, Postgres and Key Value tables. Raw HTML inspection verified the web-service row `1 CPU / $25/month / 2 GB RAM / 1c-2g`; the $40 2 GB row belongs to Postgres. Public evidence is saved in `evaluations/always_on_hosting_price_evidence.json`.

Render's persistent disk is available to one instance at runtime, not during builds. Disk-backed services cannot scale horizontally and do not have zero-downtime deployments. Expect a brief interruption during ordinary deployments. This is acceptable for the proposed small pilot but is not high availability. [Disk behavior and limitations](https://render.com/docs/disks).

### DigitalOcean

A Droplet is a virtual Linux server rather than a managed application deployment service. Its included SSD is suitable for the 3 GB read-only data package, with room for the OS, code and a second release. Keep it powered on, start the application automatically after reboots and bind any container to a persistent host data directory.

We would maintain security updates, SSH access, a firewall, HTTPS/reverse proxy, deployment scripts, monitoring and recovery. The lower infrastructure bill does not include that work. R2 plus versioned code can restore the read-only application data; a full-server backup additionally shortens recovery of the configured OS and service. Deleting or rebuilding the server is a different event from rebooting it and still requires a recovery plan.

This is the recommended budget route if ongoing administration is acceptable. Start the public pilot on the 2 GiB option rather than choosing solely by the smallest advertised price.

### Railway

The published container rates are $10/GB-month RAM, $20/vCPU-month CPU and $0.15/GB-month volume storage. Hobby has a $5 minimum that includes $5 usage, not a $5 fee added on top of the same usage. For illustration, average RAM of 0.5–1 GB, CPU of 0.02–0.1 vCPU and 5 GB billed volume storage produce **$6.15–$12.75/month**, before egress and other extras. These are assumptions, not measurements of this app. Actual container memory accounting, filesystem cache, background work and traffic can make the bill higher. [Rates and included usage](https://docs.railway.com/pricing/plans).

Disable Serverless/app sleeping to prioritize first-visitor response. Attach persistent storage and measure steady memory and CPU before estimating a normal monthly bill. Spending hard limits can stop workloads; choose alerts and operational limits with uptime in mind. [Serverless and cost controls](https://docs.railway.com/pricing/cost-control).

Railway's documented Hobby allowance is 5 GB, versus 3.057 GB of current databases. It fits one current copy but not two complete releases, which would exceed 6 GB. Documentation discusses live resizing, but lists Hobby at 5 GB; do not assume a larger Hobby allowance without checking the account. Pro starts at $20 minimum and offers more storage. Volume billing is based on used space, including filesystem metadata. Disk-backed services have deployment downtime and cannot use replicas. [Volume behavior](https://docs.railway.com/volumes/reference), [plan limits](https://docs.railway.com/pricing/plans).

## Other inexpensive candidates considered

Hetzner's cost-optimized CX23 offers 2 shared vCPUs, 4 GB RAM and 40 GB NVMe, but the current product page marks it unavailable. Regional prices, IPv4 and tax also need checking. It requires server administration like DigitalOcean. An attractive advertised server that cannot currently be ordered is not a dependable launch recommendation. [Current product availability](https://www.hetzner.com/cloud/cost-optimized/).

## What the user experience would change

After deployment and verified data loading, the app stays running with its databases on persistent disk. A new visitor normally avoids both the free-host inactivity wake and a fresh 3 GB transfer. Page initialization and Claude/query response time remain. Deployments, maintenance, resource exhaustion or failures can still interrupt service; always running is not a guarantee of uninterrupted availability.

On Render or Railway, mount the data at the actual directory the application reads, or make the data path configurable. Download the release at runtime once, verify checksums, and reuse it on restarts. Do not mistakenly store databases outside the persistent mount or inside an unmounted disposable container layer.

R2 remains useful as a source of immutable releases and recovery copies. It is no longer in the normal per-visitor data path. The app's API spending controls, public developer/model restrictions and analytical safeguards remain necessary regardless of host.

## Next step

If the approximately $28/month managed-host budget is acceptable, prepare a Render preview using a 2 GB paid instance and 10 GB disk. Verify fresh deployment, ordinary redeployment with retained data, browser sessions, memory/CPU peaks, exports, model cost and request limits before sharing the URL. Set network and cost alerts. Use DigitalOcean's 2 GiB Droplet instead if keeping the hosting bill near $12–15/month is more important and a maintainer will operate the server. No account changes or deployment have been made during this research.
