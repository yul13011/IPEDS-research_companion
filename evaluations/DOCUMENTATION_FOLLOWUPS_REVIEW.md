# Documentation intent and follow-up review — October 22, 2026

Implemented a shared documentation entry point before identity/statistical planning
in both `agent.ask` and `institution_confirmation.ask`. Supports discovery, concept
definitions, label explanations and calculation questions as initial requests or
unambiguous immediate follow-ups. Explicit topics override context; multiple labels
or releases trigger clarification with named-label/year replies supported.

Formula explanations reuse reviewed registry expressions and source definitions.
For other fields the answer distinguishes an unestablished app formula from whatever
the original codebook says about the reported measure. No invented numerator or
denominator, statistical query, external source or added context-resolution model call.

Validation:

- 49 tests passed in 169.475 seconds across documentation (six cases at that point),
  definitions, discovery, memory and institution confirmation. Includes Streamlit tests.
- Final seven documentation tests passed in 2.227 seconds, including added multiyear
  clarification/year selection. 50 distinct tests across the overlapping runs.
- Five actual offline application turns using supplied metadata saved in
  `documentation_followups_application.json`: Pell discovery → ambiguous label
  clarification → UPGRNTN explanation → calculation follow-up → discovery follow-up.
- Restarted local app PID 190412 on port 8516; health endpoint returned `ok`.

Logs: `documentation_followups_regression.log`, `documentation_followups_focused.log`.
No full combined run, new provider-backed quality evaluation or browser walkthrough.
These checks do not establish arbitrary-phrasing coverage or comparative latency gains.
Iterative retrieval, caching and broader source-context improvements remain future work.
