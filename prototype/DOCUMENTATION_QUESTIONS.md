# Documentation questions and conversation

`documentation.handle` runs before institution confirmation and statistical planning
in both public question entry points. It distinguishes data discovery, label meaning,
concept definitions and calculation explanations. Discovery reuses the source-backed
overview; labels and definitions reuse the metadata-only definition lookup. Reviewed
calculations use the app registry and its supporting source definitions; other fields
are explicitly described as having no established app formula, with source passages
available for inspection. No statistics are computed by this route.

Common follow-ups such as “What does that label mean?”, “How is it calculated?” and
“What other data do you have on that?” bind to structured fields in the immediately
preceding answer. Repeated rows for the same measure count as one reference. Multiple
labels, compared terms or source releases require clarification. A user can respond
with an offered label or release year. An explicit new topic overrides old context.
History is never mutated or treated as source evidence; source lookup runs again.

Intent and unambiguous reference resolution require no model request. The underlying
definition and discovery workflows retain their existing model budgets and source-only
policies. This change does not implement iterative retrieval, a cache, vector search,
or general natural-language resolution of arbitrary distant conversation references.
Mixed definition-and-statistics requests remain with the general planner.

Focused tests: `prototype.tests.test_documentation`. Existing definition, discovery,
memory and identity tests cover shared routing. Provider-backed answer-quality and
latency comparisons remain separate from these deterministic regression checks.
