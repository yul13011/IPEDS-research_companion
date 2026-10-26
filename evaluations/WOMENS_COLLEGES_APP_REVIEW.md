# Women's-colleges question: production replay — October 21, 2026

Exact question: `how many women's colleges in the US`

Ran through `prototype.agent.ask` with AI enabled, the configured default model and a fresh conversation. This is the production chat backend, not a browser replay and not the prior assistant conversation. No application code or prompts changed.

## Actual response

The app returned `intent=clarify`, `mode=source-backed clarification`, with no numerical result:

> IPEDS has no "women's college" flag. How should we identify them?

- **A. No men enrolled (all students):** US Title IV institutions with zero men and at least one woman in total fall 2024 enrollment.
- **B. No men among undergraduates:** same criterion restricted to undergraduate enrollment.

The app explicitly labels both as proxies, warns about specialized institutions and the exclusion of women's colleges enrolling men, and waits for a selection. It did not silently publish a women's-college count. No option was selected in this review and no statistical count was executed.

## Inspected plans

Both use `EF2024`, `EFMEN=0`, `EFWOM>0`, a global `count` reducer on the selected female enrollment field and complete cases. A selects `EFLEVEL=10` (all students); B selects `EFLEVEL=20` (undergraduates). Both use 50 states plus DC, Title IV institutions, offices excluded, no degree-granting or institution-level restriction. Their codebook references validate the gender counts and level selectors. The plans do not contain a women's-college classification field.

## Comparison and explanation

The assistant's corrected recommendation was to use the College Scorecard `WOMENONLY` classification with a checked definition/reference year and an IPEDS UNITID match. The app instead proposes enrollment-based membership proxies within its local sources. Neither this app replay nor the assistant supplied a verified national number.

Causes supported by code/evidence:

1. **Different accessible sources/context.** The catalog planner has local catalog-search, table/definition/category inspection and typed-plan tools. It has no web-search or College Scorecard retrieval tool. The earlier assistant discussion and web findings were not supplied to this fresh run.
2. **Prompt pressure toward executable alternatives.** `catalog_planner.py` explicitly instructs the planner to inspect fields and offer analysis options when definitions or proxies are ambiguous. It discourages stopping at clarification before constructing complete alternatives. This favors a feasible local proxy over a clear classification-coverage answer.
3. **Validation checks execution and source scope, not concept equivalence.** `analysis_clarification.preflight` invokes `query_engine.inspect(plan, analysis['interpretation'])`. Thus the plan is checked against the rewritten proxy question. Valid gender-count fields do not establish that the selected institutions are women's colleges.
4. **A source gap becomes a user-choice question.** The original request asks for institutional identity, not enrollment composition. A proxy can be useful if explicitly requested, but choosing between A/B does not supply the missing classification. The unrestricted institution level can include specialized and non-degree institutions, as the app itself warns.
5. **Overbroad absence language.** The local file/catalog check supports absence from the loaded releases, not the blanket claim about every IPEDS product/year or related federal data product. Prefer "The loaded IPEDS files do not contain a verified women's-college classification."

Recommended response policy: state the direct classification gap first; name an independently verified source such as Scorecard when available; do not present only substitute measures as if they fully resolve the original request. Keep enrollment proxies optional, explicitly distinct and not selected by default. Add a semantic check that distinguishes institution classifications from observed population composition. This report proposes changes; it does not implement them.

## Timing and artifacts

Server answer-ready time **45.742 seconds**; **7 model calls**, **12 planning tool requests**, **0 semantic repairs**. Configured API estimate **$0.4682182**. This is one run, excluding browser rendering, and not an accuracy or latency distribution. The seven calls are sequential planning calls, not seven agents.

- `womens_colleges_app_trace.json`: complete answer, offered plans, codebook evidence, usage and progress.
- `womens_colleges_app_trace.log`: stage log and full displayed message.
- `trace_womens_colleges.py`: reproducible production entry-point harness; rerunning makes billable model requests.

National benchmark reconciliation remains paused; this was a single explicitly requested question replay.
