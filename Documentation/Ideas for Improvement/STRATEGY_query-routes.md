# Is there an easier way to let people query IPEDS?

**Strategy note · IPEDS Research Companion**
Prepared for colleagues at Yale OIR / OLR · 6 Nov 2026

> Four routes for answering plain-English questions about U.S. colleges from
> federal IPEDS data — and why the fastest win is not scrapping the app, but
> putting a familiar chat face on the engine it already runs.

Shareable version (artifact): https://claude.ai/artifact/36aRoW1ZfXFvP2EP8afZgd

---

## The question: should people just use Claude or ChatGPT instead of a dedicated app?

It's a fair challenge. IPEDS is public; the chat tools are already open on
everyone's desktop. If someone can upload the data and ask away, why maintain a
separate app at all?

The honest answer is that the two tools solve for different users. The deciding
question is not *which interface is nicer* — it's **who stands behind the number**.

| The human guarantees it — *Chat + uploaded data* | The system guarantees it — *The Companion app* |
|---|---|
| The model picks the table, variable, filter and year each time, then runs SQL or Python on it. Fast and flexible — but correctness rests on an expert reading the output and catching the IPEDS traps themselves. | The model proposes a typed, source-bound *plan*; deterministic code validates it against the catalog and physical schema before any query runs. The same question gives the same audited number to anyone. |

So the real choice isn't app-versus-chat. It's: do you want an **expert's power
tool**, or **reliable self-serve for non-experts**? The audience we care about —
colleagues who need a number they can put in a report without second-guessing it
— is the second group.

---

## Four routes, compared

Each route is scored on what matters for institutional research, not on how
modern it feels. Legend: ✅ strength · ⚠️ trade-off · ❌ real gap.

| What matters | Chat + upload (ChatGPT ADA / Claude Analysis) | Custom GPT / Project (RAG, no backend) | **Chat front end + this engine (MCP / Action)** ⭐ | The current app (Streamlit, as built) |
|---|---|---|---|---|
| **Setup effort** | ✅ minutes — upload a file, ask | ✅ hours — drop in docs | ⚠️ days — wrap existing engine | ❌ done, but weeks sunk |
| **Accuracy / trust** | ⚠️ model's guess — right SQL, wrong field | ❌ unreliable — RAG can't do exact math | ✅ validated — same guarantees as app | ✅ validated |
| **Reproducible / auditable** | ❌ no — answer drifts per run | ❌ no | ✅ yes — plan + SQL + sources returned | ✅ yes |
| **Data coverage** | ⚠️ subset only — can't fit ~3 GB / 500 tables | ⚠️ subset only | ✅ full catalog — engine owns the DB | ✅ full catalog |
| **Familiar interface** | ✅ yes — tool they already use | ✅ yes | ✅ yes — lives inside Claude/ChatGPT | ⚠️ new app to adopt |
| **Governance / defensible** | ❌ weak — no shared source of truth | ❌ weak | ✅ strong — one audited backend | ✅ strong |
| **Maintenance** | ✅ none — but re-done every time | ⚠️ doc upkeep | ⚠️ one engine + thin layer | ⚠️ whole app + UI |

⭐ = recommended route.

Two of the "easy" routes collapse on the same fact: **you cannot load all of
IPEDS into a chat.** ~500 tables and ~3.1 GB is a billion-plus tokens, and RAG
over data tables is unreliable for exact counts, joins and aggregates. The only
workable path in a bare chat is a *code sandbox over a curated subset* — which
works, but hands every IPEDS judgment call back to the model.

> A sandbox runs SQL deterministically — but the model still chooses the table,
> variable, filter and year each time, with nothing validating that choice. That
> is exactly where IPEDS bites.

The traps are specific and unforgiving: fiscal-year off-by-one, a "not reported"
value silently treated as a real 0, residency and cohort splits, grand-total
versus per-award-level fields. These are the precise failure modes the
Companion's validation layer exists to catch. A chat sandbox has no such layer,
so its answers are non-reproducible and carry no audit trail — fine for an
expert's one-off exploration, not for a number that goes into a report.

---

## Recommendation: don't rebuild. Wrap what you have.

> **Expose the existing validated engine as an MCP server (for Claude) and/or a
> Custom GPT Action (for ChatGPT).**

Users keep the chat interface they already trust. Every number still flows
through the *same* plan → validate → execute pipeline — so they get
guaranteed-correct, source-cited answers without ever opening a new app. You
reuse the engine you already built instead of re-solving IPEDS validation inside
a sandbox where it can't be solved.

This also reframes the LinkedIn/colleague story cleanly: the Companion isn't
competing with ChatGPT — it's the **trustworthy backend** that makes "just ask
an AI about IPEDS" actually safe to act on. The chat is the face; the validated
engine is the guarantee.

A Custom GPT *without* Actions is just RAG, and unreliable for tabular math. A
Custom GPT *with* Actions calls an API you host — which means you still need a
validated backend either way. You already have it.

---

## What the wrapper actually takes

Good news from the code: the engine's public entry point already returns a fully
structured, JSON-serializable result. The audit trail isn't something you'd have
to build for the API — it's already the shape the engine hands back.

### One entry point does the work

Everything routes through `agent.ask()` in `agent-redesign/prototype/agent.py`.
It takes a question (plus optional prior conversation) and returns a dict already
carrying the answer, the validated plan, the rows, and full provenance:

```python
# prototype/agent.py — already exists, unchanged
answer = agent.ask(question, previous=None, use_model=True,
                   model=..., conversation=history)

# answer['result'] already contains, per the execution code
# (catalog_execution.py ~line 333):
{
  "rows":        [ {institution, unitid, metric, value,
                   numerator, denominator, source_value,
                   release, provisional, unit_metadata, ...} ],
  "sources":     [ {table, columns, filters, sql,        # raw SQL run
                   parameters, codebook_evidence, database} ],
  "catalog_plan": {...},   # the validated, source-bound plan
  "definitions":  {...},   # what each measure means
  "warnings":     [...],
  "review_status": "Catalog-bound observations; units, periods,
                   missingness validated...",
  "result_id":    "<content hash — reproducibility key>"
}
```

### The wrapper is a thin translation layer

An MCP tool (or GPT Action endpoint) is essentially one function that calls
`ask()` and reshapes the result into a compact response the chat model narrates:

```python
def ipeds_query(question: str, history=None) -> dict:
    answer = agent.ask(question, use_model=True, conversation=history)
    r = answer.get("result", {})
    return {
      "answer":    answer.get("message"),      # prose
      "data":      r.get("rows"),              # the numbers
      "sources":   r.get("sources"),           # table / SQL / codebook
      "plan":      r.get("catalog_plan"),      # audit trail
      "result_id": r.get("result_id"),         # cite this to reproduce
      "warnings":  r.get("warnings"),
    }
```

For MCP: expose that one function as a tool in a small MCP server (the engine
already runs on Render, so the server sits beside it with access to the SQLite
DB). For a GPT Action: the same function behind one POST endpoint with an
OpenAPI schema. Either way the engine, the DB, and the validation stay exactly
as they are.

### What to expose, minimally

- **`ipeds_query`** — the main tool above. One question in, validated answer +
  data + sources out.
- **`ipeds_define`** (optional) — wraps `definitions.handle()` for "what does
  this measure mean" questions, so the model doesn't guess definitions either.
- **`ipeds_discover`** (optional) — wraps the discovery route for "what's
  available about X" catalog browsing.

Start with just the first. It covers the questions people actually ask.

### Rough effort

| Effort | Scope |
|---|---|
| **~1–2 days** | MCP server: wrap `ask()`, serialize result, deploy beside the engine. The hard part — validation — is already done. |
| **~2–3 days** | GPT Action: same function behind a hosted endpoint + OpenAPI schema + auth. Mostly plumbing, not logic. |
| **0 days** | Engine changes. `ask()` already returns JSON-ready output; nothing in the pipeline needs touching. |

The real work is serialization hygiene (the result dict nests a few Python
objects to clean up), latency (the engine makes live model calls — an MCP call
inside a chat adds a round trip, so cache the FAQ/example questions as the app
already does), and auth on the hosted endpoint. None of it is the IPEDS problem
— that part is solved.

---

## Bottom line — the one-paragraph version for colleagues

You can absolutely explore IPEDS by uploading a subset into ChatGPT or Claude
and running code on it — and for a seasoned analyst doing a one-off, that's often
the right move. But for a *number that goes into a report*, the chat tool is only
as reliable as the person watching it, because the model re-guesses the table,
field and year every time with nothing to check it. The Companion's value was
never the Streamlit UI; it's the validation layer underneath. So the easiest
high-value move isn't to abandon the app or to re-do its logic inside a sandbox —
it's to expose that validated engine as an MCP connector or Custom GPT Action, so
people get the familiar chat interface *and* the guaranteed number. That's a few
days of wrapping, not a rebuild.

---

*Routes assessed: chat + uploaded subset · Custom GPT / Claude Project (RAG) ·
chat front end over the existing engine (MCP / Action) · the current Streamlit
app. Engine entry point referenced: `agent-redesign/prototype/agent.py :: ask()`.*
