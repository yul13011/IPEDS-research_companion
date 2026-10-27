# Deployment runbook — IPEDS Research Companion on Render

Created: October 27, 2026. **Decision:** host the Streamlit app on **Render** (Starter, always-on),
keep the 3.1 GB of data in the **Hugging Face Dataset repo** `yul13011/ipeds-data` (already
uploaded, free), and give the Render service a small **persistent disk** so the data loads once
and survives restarts. Render Starter is always-on, so **no keep-warm ping is needed** and a
LinkedIn visitor never hits a cold boot.

Why Render over the alternatives: it's the **Git-push flow you already know** (no Docker, no CLI),
it's **always-on** (unlike Streamlit Community Cloud, which sleeps), and at **~$8/mo** it's cheaper
than Hugging Face hosting (which now needs $9 PRO + $5 disk = ~$14/mo just to run a Docker Space).

Steps are marked:
- 👉 **YOU (browser)** — click around the Render/GitHub websites
- 💻 **YOU (terminal)** — a git push, like before
- 🤖 **CODE (I make these)** — small code edits in one commit

---

## Architecture at a glance

| Piece | Where | Cost |
| --- | --- | --- |
| App | **Render** Web Service (Starter, 512 MB, always-on) | $7/mo |
| Working copy of data | Render **persistent disk** (4 GB, mounted at `/var/data`) | ~$1/mo |
| Data (master) | **HF Dataset repo** `yul13011/ipeds-data` (public, free) | $0 |
| Code | **GitHub** (`IPEDS-research_companion`) | $0 |
| Model calls | **Anthropic API** (~$0.04/answer) | metered |

Flow: on first deploy the Render service pulls the 3.1 GB from the HF Dataset repo **once** onto
its persistent disk → every visitor talks to that one always-on server, which reads the data
locally. **No per-user download; no cold-start sleep.** Memory measured at ~260 MB peak, so 512 MB
is enough.

---

## 1. Prerequisites (👉 YOU, browser — ~3 min)

1. Create a free **Render account** at render.com — sign up **with GitHub** so Render can see your
   repo.
2. Have your **Anthropic API key** handy (the one in `.streamlit/secrets.toml`).
3. ✅ Already done: HF account, and the 3.1 GB uploaded to `yul13011/ipeds-data` (verified: 70
   files, all 10 annual DBs + 4 catalog DBs).

> Note — Render bills **two separate layers**, don't confuse them:
> - **Workspace plan:** stay on **Hobby = $0/mo** ("plus compute costs"). The **Pro $25** workspace
>   is about team seats/features and is **not needed**.
> - **Compute instance type** (picked per web service in §4, *not* on the workspace-plan page):
>   choose **Starter ($7/mo, 512 MB, always-on)**. The Free instance spins down after 15 min of
>   inactivity (slow first click), so we use Starter.

---

## 2. Code changes (🤖 CODE — I make all of these in one commit)

Your app logic, UI, and query engine are **unchanged**. Four small edits so the app finds its data
on Render (and still works locally). Say "make the Render changes" and I'll do them:

1. **`prototype/catalog.py`** — read the data folder from an env var, defaulting to today's local
   `data/`:  `DATA = Path(os.environ.get("IPEDS_DATA_DIR", BASE / "data"))` (+ `import os`).
2. **New `prototype/data_bootstrap.py`** — an `ensure_data()` that, when `IPEDS_DATA_DIR` is set and
   the data isn't there yet, downloads the HF Dataset repo into it once
   (`huggingface_hub.snapshot_download`), and is a fast no-op once the data is present.
3. **`prototype/app.py`** — call `ensure_data()` **before** importing the UI.
4. **`prototype/requirements.txt`** — add `huggingface_hub`.

No Dockerfile and no HF `README.md` header are needed on Render (that was the HF path).

> How the one-time pull behaves on Render: `streamlit run` opens the web port immediately (so
> Render sees the service as healthy), and `ensure_data()` runs when the **first page view**
> happens — that first visit downloads the 3.1 GB (a few minutes) to the persistent disk, and
> every visit after that skips it. So **you** open the app once after deploying and wait for it,
> then share the link (see §6).

---

## 3. Data is already in place ✅

The 3.1 GB lives in `yul13011/ipeds-data` (public HF Dataset repo). Nothing to do here — Render
will pull from it. Keep that repo id; it goes in the `IPEDS_DATASET_REPO` variable in §5.

---

## 4. Create the Render web service (👉 YOU, browser — ~5 min)

1. Render dashboard → **New → Web Service**.
2. **Connect** your GitHub repo `IPEDS-research_companion` (authorize Render if asked). Pick the
   branch to deploy (e.g. `main`, or your current branch).
3. Render asks for build/run settings — set:
   - **Language/Runtime:** Python 3
   - **Build Command:** `pip install -r prototype/requirements.txt`
   - **Start Command:**
     `streamlit run prototype/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false`
   - **Instance Type:** **Starter ($7/mo)** — this is the per-service compute size; your workspace
     stays on **Hobby ($0)**
4. Create the service (it'll start a first build — that's fine; we finish config next).

---

## 5. Add the persistent disk + environment variables (👉 YOU, browser — ~3 min)

In the service's settings:
1. **Disks → Add Disk:** Name `ipeds-data`, **Mount Path** `/var/data`, **Size** `4` GB (~$1/mo).
2. **Environment → add variables:**
   - **Secret** `ANTHROPIC_API_KEY` = your Anthropic key
   - `IPEDS_DATA_DIR` = `/var/data/ipeds`
   - `IPEDS_DATASET_REPO` = `yul13011/ipeds-data`
   - `PYTHON_VERSION` = `3.11.9`  *(pins a Python the deps support)*
3. **Save** — Render redeploys with the disk and variables attached.

---

## 6. First deploy & the one-time data load (👉 YOU)

1. Watch the **Logs** tab until the build finishes and the service is **Live**.
2. Open the service's URL **yourself**. The first page view triggers the one-time 3.1 GB pull to
   `/var/data/ipeds` — the page will show a loading state for a few minutes. Watch the logs for the
   download to finish.
3. Once it loads, **ask it a test question** and confirm the answer is correct.
4. From now on the data is on the persistent disk, so restarts and redeploys **don't** re-download
   it, and visitors never wait for it.

---

## 7. Before you share the link — guardrails (strongly recommended)

A public link means **you** pay for every visitor's questions (~$0.04/answer, ~$0.12/visitor →
~$24/mo at 50 visitors/week; ~$120 if a post hits 1,000 visitors).

🤖 **CODE (I can add these):**
1. **Daily spend cap** — the app already computes `estimated_api_usd` per answer; sum it per day and
   show "demo budget reached, back tomorrow" past a threshold you set.
2. **Per-session rate limit** — e.g. N questions / 10 min.
3. **Example-question landing** — 3–5 clickable questions, at least one on the reviewed fast path
   (instant, $0) so the first click feels immediate.

👉 **YOU (browser):** also set a **usage limit on the Anthropic key** in the Anthropic console as a
hard backstop.

---

## 8. Launch checklist

1. ✅ Data in the HF Dataset repo (`yul13011/ipeds-data`).
2. Code changes (§2) committed and pushed to GitHub.
3. Render service created; Starter instance; build/start commands set (§4).
4. Persistent disk mounted at `/var/data`; secret + variables set (§5).
5. First deploy opened by you; one-time 3.1 GB pull finished; test question correct (§6).
6. Guardrails in place; Anthropic key budget set (§7).
7. **Only now** post the LinkedIn link. Visitors hit a warm, data-loaded, always-on app and wait
   only ~15–35 s model time per question.

---

## 9. Latency & cost summary

| | Estimate |
| --- | --- |
| First-visitor wait | ~**15–35 s** model time per question (no cold wake, no data wait) |
| Reviewed fast-path questions | **< 2 s** (no AI call) |
| One-time data load | a few minutes, on **your** first visit after deploy, once |
| Infra cost | **~$8/mo** ($7 Starter + ~$1 disk) |
| API cost | ~$0.04/answer, ~$0.12/visitor — cap it (§7) |

---

## 10. Updating the app and the data

- **App code:** `git push` to GitHub → Render auto-deploys. The persistent disk keeps the data, so
  deploys don't re-download it.
- **Data (≈ once a year):** run the `ingestion/` pipeline to add the new release and **rebuild the
  catalog DBs** (`metadata_catalog`, `field_semantics`, `unit_catalog`, `analysis_catalog` are
  cross-release, so they regenerate — not just one new file). Re-upload with
  `huggingface-cli upload yul13011/ipeds-data ./data . --repo-type=dataset`, then in Render either
  point `IPEDS_DATA_DIR` at a new subfolder (e.g. `/var/data/ipeds_2025`) or clear `/var/data/ipeds`
  and restart, so it pulls the new version. Do the same when 2024-25 Provisional becomes Final.

---

*Latency figures: model time from this project's diagnostic/coverage runs; memory from a direct
measurement (~260 MB peak). Infra pricing from current Render figures (Oct 2026) — confirm on
render.com/pricing. Anthropic rates are those recorded in `prototype/agent.py` (checked 2026-10-17).*
