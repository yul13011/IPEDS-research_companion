# Flexible routing and investigation

Recorded October 23, 2026. Owner-authorized implementation and findings live here.

## Plan

1. Understand message purpose before institution extraction or statistical planning. Handle greetings, thanks, and app help cheaply; preserve substantive questions and follow-up context.
2. Route documentation, discovery, categorical observations, and numerical analysis to the existing source-backed workflows. Allow a request to include documentation and analysis without silently dropping either part.
3. Give the investigative planner a bounded documentation lookup alongside its existing exact-definition, category, and analysis tools. Retain shared context and source evidence rather than introducing specialist agents.
4. Preserve deterministic validation, source restrictions, category arithmetic protections, identity confirmation, reporting periods, and explicit proxy selection.
5. Evaluate purpose routing, mixed requests, source evidence, numerical compatibility, model-call overhead, and limitations. Add a specialist only if later measurements justify it.

## Acceptance criteria

- Greetings/help do not extract institutions, resolve analytical context, or invoke the provider.
- A greeting preceding a substantive question does not consume that question.
- Documentation follow-ups still use structured prior evidence; mixed requests retain both outputs.
- Investigation can consult documentation within the existing bounded tool loop.
- No unrestricted SQL, external sources, or numerical execution bypass is added.

## Findings and validation

Implemented and activated October 23, 2026. National benchmark reconciliation remains paused; clock/contact-hour review remains separate.

### Changes against the plan

1. **Purpose before specialized work.** New `prototype/purpose.py` handles complete greetings, acknowledgments, and app-help messages locally. The UI checks these before display-change interpretation; both public analytical entry points check them before documentation, institution extraction, conversation resolution, and planning. Greeting/polite prefixes on substantive questions are normalized rather than consuming the question. Social turns do not replace structured documentation antecedents.
2. **Existing workflows retained; mixed requests supported.** Common polite explanation/interpretation wording reaches documentation. Explicit documentation-then-analysis compounds retain a separate documentation section, evidence, analytical result, and combined usage/timing. An unambiguous “it/this measure” in the analytical clause refers to the just-established documentation term. Unresolved documentation blocks guessing; exact offered term/year replies can resume the retained mixed request. Institution confirmation retains the full mixed request. Unknown compound wording stays intact for the established planner.
3. **Investigation can cross into documentation.** Added `lookup_documentation` to the catalog agent's tools, bringing its main tool list to 14. It reads owner-supplied documentation without a nested model call or statistical execution. Existing exact-definition/category/source-series tools remain available. Planner instructions explicitly permit moving between documentation and analytical investigation within the existing inspection budget. A provider-transport test exercises documentation lookup followed by a planning decision in the same loop.
4. **Validation remains authoritative.** Numerical/category execution, source scope, identity confirmation, period checks, and proxy selection retain their existing validators. Testing uncovered an existing live incompatibility with the app's canonical `Name (UNITID …)` annotations: model output could preserve the annotation, while validation and execution expected a plain name/ID. Resolution now accepts only an exact canonical name/ID pair, and reviewed model plans normalize that pair to the stable ID before execution. Conflicting name/ID pairs remain rejected. Model usage is retained on the reviewed validation/identity failure paths touched by this change.
5. **Measured rather than adding agents.** No specialist agent, additional classifier API call, unrestricted SQL, or external retrieval was introduced. Common purposes use local matching; unfamiliar substantive requests retain model planning. Exact metadata tools remain shared across analysis types because numerical plans often need categorical selectors, and mixed questions need both kinds of tools. Hard-pruning those tools would undermine investigation. There is not yet evidence that another autonomous agent would improve this app.

### Verification

| Check | Result | Evidence |
|---|---|---|
| Routing/documentation/institution/catalog/UI regression run | 51 passed, 148.284 s | `evaluations/flexible_routing_verified.log` |
| Expanded purpose, definitions, categorical observations, coverage gaps, memory/UI | 57 passed, 109.288 s | `evaluations/flexible_routing_final.log` |
| Updated identity/routing/intent safety | 36 passed, 62.483 s | `evaluations/flexible_routing_identity_final.log` |
| Final normalization/execution and documentation checks | 9 passed, 11.594 s | `evaluations/flexible_routing_execution_verified.log` |
| Real local data probes | All five completed; mixed answer retained definition and numerical result | `evaluations/flexible_routing_probes/local_summary.json` |
| Live configured-provider probes | Greeting/help direct; Pell definition source-backed; final numerical and mixed requests returned results | `evaluations/flexible_routing_live_connected.log`, `evaluations/flexible_routing_live_final.log` |
| Independent raw-source comparison | Both final live numerical cells match ADM2024 source values | `evaluations/flexible_routing_probes/independent_source_check.json` |
| Final greeting/substantive-message check | 2 passed, 0.015 s | `evaluations/flexible_routing_greeting_final.log` |
| Activation | PID 219572, port 8516, `/_stcore/health` = `ok` | `evaluations/flexible_routing_app_stdout.log` |

These runs overlap and are not a count of distinct tests. This task used focused regressions, not a fresh full-suite run. The registered runner now includes the new purpose tests.

Initial restricted live probes hit connection errors; a retry with provider connectivity worked. An early final-check attempt also hit Windows sandbox temporary-directory permissions; it was rerun with the project test-temp directory. Neither attempt is counted as a successful test run. Live analytical probes initially exposed the canonical annotation issue above; final successful runs followed the validation and execution fixes.

### Latency and cost observations

| Live message | Observed wall time | Model calls | App-estimated API cost |
|---|---:|---:|---:|
| Hi | 0.005 s | 0 | $0 |
| What can you do? | 0.001 s | 0 | $0 |
| Can you explain Pell? | 23.524 s | 1 | $0.006126 |
| Yale applicants fall 2024 (final) | 19.884 s | 2 | $0.0115124 |
| Define admission rate and show Yale admission rate fall 2024 (final) | 5.939 s | 2 | $0.0088764 |

These are individual observations under differing cache/cold-start/concurrent-test conditions, not a controlled speed comparison. Costs use the app's configured estimator, not verified provider billing. The Pell passage-selection call remains a latency hotspot; the new planner documentation tool uses local evidence only. The mixed admission-rate definition was handled locally and added no API call.

Independent source check: `ADM2024`, Yale UNITID 130794, applicants **57,517**; admission rate **3.871898742980336%**, calculated as source admissions divided by source applicants ×100. Both saved live results match. Existing benchmark warnings are retained; this check does not resume national aggregate reconciliation.

### Practical limits and next evidence to collect

- This is a conservative purpose layer, not a universal semantic intent classifier. Unrecognized social wording can still reach the established planner. The app is more flexible for the tested phrases; arbitrary conversation is not certified.
- Explicit definition-first compounds are supported. Arbitrarily interleaved or analysis-first explanatory requests still depend on the general planner. Documentation tool evidence informs planning; it is not a new unrestricted final-answer generator.
- Exact offered documentation terms/years can resume a pending mixed request. More conversational corrections may need a restated request. The task did not establish exhaustive multi-turn recovery coverage.
- The full metadata/plan tool set stays available in the catalog loop. Relevant workflow selection improved, but this implementation does not claim adaptive per-turn tool pruning.
- The planner still has its existing bounded investigation/repair limits; neither source meaning nor a missing formula can be inferred merely to finish a request.
- Follow-up evaluation should sample real user wording, reverse-order mixed questions, long histories, and ambiguous source definitions. Optimize passage selection or add a narrow specialist only if measured accuracy/latency/cost warrants it.
