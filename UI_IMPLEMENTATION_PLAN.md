# IPEDS prototype: interface implementation plan

Recorded: October 17, 2026

**October 18 chatbot response revision (implemented):** Statistical answers expose Display table, Definitions & sources, and Download Data. Definitions & sources and Download Data are adjacent popover buttons on the same row. Counts/status are optional within the table; full technical evidence stays downloadable. Separate source/detail expanders, extract-layout/edit controls and model diagnostics are removed from chatbot results. This supersedes earlier per-answer control requirements below. Handoff and validation details: [PROGRESS_2026-10-18.md](PROGRESS_2026-10-18.md).

**Latest layout revision:** Ask & Analyze uses the browser width with small margins, a left Need ideas panel and a right analysis-tools panel. Both start open, with explicit independent Collapse/Show controls. The center conversation expands when either panel closes; panel visibility and selected topic persist after questions. This supersedes the below-conversation Need ideas bar and earlier single-sidebar arrangements described below.

**Status: Implemented in the local prototype, October 17, 2026, following the owner's authorization to build the combined plan.** The original design requirements below remain the implementation reference. The app defaults to Sonnet 5.5; Haiku 5.5 is selectable for comparison. Broader new-measure execution remains a separate TODO.

## 1. Purpose and priorities

Help people discover what IPEDS contains, ask questions, and extract the correct data across institutions and time. Serve parents/students as well as institutional researchers. Make CSV/Excel extraction a primary outcome; visualization is an additional option rather than a required step before downloading.

Preserve the existing analytical engine, annual SQLite sources, metadata catalog, reviewed mappings, source disclosure and evaluation findings. This interface work is separate from the outstanding catalog-to-new-measure execution workflow in `AGENT_ARCHITECTURE.md`, section 19.

## 2. Main navigation

Provide two main pages within the existing local Streamlit app:

Use tab-style navigation with an active underline, rather than radio buttons.

1. **Explore IPEDS** — default landing page and introduction to available data.
2. **Ask & Analyze** — questions, conversation, results, data extraction and optional visualization.

Share conversation state, selected topic, analysis scope and results between pages and tools. Returning to Explore IPEDS or opening a tool must not discard the current conversation. Existing session-only retention and bounded result storage remain unless a later request changes them.

Move evaluation/coverage information into a secondary **About this prototype** entry in the header. Keep it available without competing with the two primary journeys.

## 3. Explore IPEDS landing page

### Default view

- Introduce IPEDS in plain language, identify the source/coverage, and label the latest release provisional.
- Provide a prominent **Ask a question** route for users who already know their question.
- Show six topic cards in a two-row, three-column desktop grid:

| Friendly title | Source topic |
| --- | --- |
| Getting in | Admissions |
| Who attends | Enrollment |
| Paying for college | Costs and financial aid |
| Graduation & degrees | Graduation outcomes and completions |
| Faculty & staff | Human resources |
| About the institution | Institutional characteristics |

Each card contains a small icon, title, short description and **Explore topic** action. Adapt the grid to narrower screens.

### Explore topic interaction

- Keep the cards on the same page and open a detail panel immediately after the selected card's row. Include an explicit Close control. Display each example as a muted category label beside a left-aligned clickable question.
- Open one topic panel at a time; selecting another card replaces its contents.
- Include a short description, a material population/coverage limitation, and three examples illustrating a single data point, an institutional comparison and a longitudinal analysis when supported.
- Offer **Ask your own question about this topic**. Open Ask & Analyze with the topic selected and the question box ready; do not submit an invented question.
- A supported example opens Ask & Analyze, displays its question in the conversation and executes a predefined validated request. Resolve dates, institutions and outputs through the existing validated engine.
- A discovery-only example is labeled **Explore available data** and opens source discovery. It must not imply that an unmapped calculation can already execute.

Store topic descriptions and example definitions in reusable editable content/configuration files. The landing page and question suggestions should use the same content source. Verify content against the local source documentation, and avoid implying that every variable or survey already has a reviewed analytical mapping.

## 4. Ask & Analyze: initial state

- Give most of the width and visual prominence to the question/conversation area.
- Lead with **What would you like to learn?** and a question box. Explicitly invite one or multiple institutions, one year, selected years or a range, and table/CSV/chart requests.
- Before the first question, show **Need ideas?** with topic choices and a short set of examples for one selected topic. Examples should demonstrate lookups, institution comparisons and trends.
- Provide secondary entry points for **Build a data extract** and **Browse definitions**, as shown in the revised main-page mockup. The full builder opens into a roomier focused workspace rather than placing all controls in the main page's narrow rail.
- Keep evaluation/coverage under **About this prototype** in the header.

The initial prompt area transitions into the conversation workspace after submission. No navigation to a separate answer page is required.

## 5. Ask & Analyze: after submission

- Display the submitted question and answer on the same page.
- Give the requested result priority: a contextual value for a lookup, a comparison table/chart for an institutional comparison, or a trend/table for a longitudinal request.
- Keep the executed scope visible: measure(s), institutions/group, periods and their meanings. Show missing data, comparability issues, provisional status and retained benchmark discrepancies as applicable.
- Provide prominent data downloads with definitions/source documentation. Charts must consume the same validated data as exports.
- Retain contextual follow-ups such as adding institutions, changing the period, showing counts, switching display or downloading the table. Reuse validated scope and apply the usual checks to changes.

### Agreed Need ideas behavior

After the first submission, collapse the introductory suggestions into a slim, expandable **Need ideas? Explore topics and sample questions** bar **below the dialogue/results and immediately above the compact follow-up input**.

```text
Conversation and result
Table/chart and download actions

▸ Need ideas? Explore topics and sample questions

[ Ask a follow-up question… ]
```

- Expanding the bar reopens the topics and examples in place.
- Remember the previously selected topic.
- Opening/closing it must preserve the conversation, scope and results.
- Selecting an executable example appends its question to the conversation, executes it, and collapses the suggestions again. Discovery-only actions remain explicitly labeled.
- Allow users to close it without choosing an example.

This records the latest agreed behavior. Earlier discussion of a permanent left inspiration panel is superseded by this expandable bar. The initial-state image shows suggestions expanded; it does not show this post-submission state.

## 6. Optional Build a data extract workflow

Use the title **Build a data extract**. It is an alternative input method for the same analytical engine and can be prefilled from a conversational request. Preserve scope while moving between the builder and conversation. Provide a clear return route.

Use a spacious four-step layout: **Institutions → Measures → Years → Preview & download**. Permit revisiting earlier steps without losing other selections. A completed extract should be reusable for a subsequent visualization request.

### Institutions

- Label clearly: **Institutions — select one or more**.
- Provide search/autocomplete by institution name or UNITID.
- Show distinct matches with full name, city/state and UNITID. Require explicit selection when names are ambiguous; never silently pick the first match.
- Show selected institutions as removable chips and retain them while searching for another institution.
- Offer supported comparison groups, initially the existing Ivy League group. Show group membership and allow inspection/adjustment.
- Check institutional identity/availability for requested annual sources before execution. A matching modern name is not proof of historical availability.

### Measures: search and selection

- Replace the long measure dropdown with **What data do you need?** search.
- Accept concepts/questions and exact source variable names as proposed search entry points; validate the actual analytical selection independently of search ranking.
- Show a short ranked result list with optional topic filters and a way to request more matches.
- Each result shows a friendly name, concise definition, population/unit and relevant availability. Put annual table/variable details and methodology behind an expandable **Definition & sources** control.
- Give results explicit **Add** actions and show a persistent **Your extract** selection list with removal controls. Keep selections across successive searches.
- Support multiple measures, subject to the existing bounds and checks for compatible scope/grain/time. Do not expand resource limits silently.
- Distinguish **Ready to extract** reviewed mappings from **Discovery only** source definitions. New-variable execution still depends on the separate validated-plan workflow; this UI work must not bypass it.
- Keep institution statistics out of the mapping content; retrieve actual values through validated read-only queries.

Search must avoid requiring users to open nested hundreds-item menus. Topic examples and source definitions should also help users who do not know the correct search term. Do not claim that a short ranked list is exhaustive.

### Years and time meaning

- Explicit choices: **One year**, **Selected years**, **Year range**.
- Show the appropriate control for the chosen mode and summarize how many years are selected.
- Explain measure-specific time meaning: fall observations, reporting periods, graduation entry cohorts versus outcome years, and nominal class-of labels.
- Preserve application-side date binding, available-year checks and comparability requirements. Unavailable years must not be silently replaced.

### Preview & download

- Show the selected institutions, measures, periods and their interpretation before presenting the data preview.
- Make **Download CSV** and **Download Excel** prominent. Provide data dictionary/methodology/source information with the extract; retain the existing provenance download.
- Offer **Visualize this data** as an additional action.
- Use compatible institution/year/measure structure for combined results. Keep incompatible populations or grains explicit; partition outputs or ask for clarification instead of forcing misleading joins.
- Download complete results, not only visible preview rows. Preserve missing/not-collected statuses, provisional flags and comparability warnings.

## 7. Secondary tools

**Browse definitions:** retain the repaired technical lookup with topic/table/variable search, year filters, full definitions, coded categories, physical-location issues and source references. Its purpose is source understanding; it does not execute statistics for unmapped measures. Preserve both the search result and conversation when opening/closing this tool.

**About this prototype:** house coverage, implemented capabilities, known limitations and evaluation findings. Preserve the 229 matching/13 discrepant Yale comparison baseline and unresolved definitions; do not relabel unresolved results as passing statistical validation.

## 8. Later implementation sequence

- [x] Collect and append the owner's additional requests before starting the combined build.
- [x] Refactor the current interface into reusable page, conversation, discovery, builder and result components while keeping analytical rules separate.
- [x] Add shared topic/example content and two-page navigation with session-state preservation.
- [x] Implement topic-panel navigation and executable/discovery-only examples.
- [x] Implement initial/post-submission question layouts and the agreed expandable Need ideas behavior.
- [x] Implement autocomplete, multiple institution/measure selections and explicit year modes in the data-extract workflow.
- [x] Connect builder and chat to the same validated plans, data previews, downloads and optional charts.
- [x] Relocate definition lookup and evaluation/coverage access without losing their current functionality.
- [x] Verify the integrated journeys and document remaining limitations before review.

Do not add cloud provisioning, novel-measure execution, national aggregation, custom URM definitions or automatic mapping approval as an implicit part of this interface work. Those remain separate scoped tasks unless the owner adds them.

## 9. Acceptance checks for the combined build

- Topic cards and direct question entry work; only one topic detail panel is open at a time.
- A supported example executes once and appears in the conversation; a discovery-only example stays in discovery.
- Questions answer on the same page. Need ideas collapses below the dialogue, can reopen, remembers its topic and preserves results.
- Page/tool navigation preserves conversation and selections; widget/form/result keys remain distinct to prevent the earlier codebook-search state collision.
- Autocomplete distinguishes ambiguous names such as Smith; multiple selections and removal work.
- Measure searches retain selections, show definitions and clearly distinguish extract-ready from discovery-only results.
- Single-year, selected-year and range modes produce the intended periods. Existing cohort/class-year safeguards still apply.
- A multi-institution, multi-year, multi-measure extract returns complete downloadable data with sources; no forced visualization step is required.
- Charts, tables and downloads use the same validated result. Missing/unsupported values and definition changes remain visible.
- Existing retrieval regressions remain intact; add UI tests for the new flows and inspect desktop/narrow-screen layouts.

## 10. Design references and outstanding additions

Images in `design-mockups/2026-10-17/` are static concepts, not implemented screens:

- `explore-ipeds-v1.png`: default landing page.
- `ask-and-analyze-v2.png`: revised initial main workspace.
- `institution-autocomplete-v1.png`: institution selection.
- `measure-search-v1.png`: measure finder and selected-measure list.

This written plan governs later clarifications, including the post-submission Need ideas bar not pictured in the mockups. Earlier narrow single-institution/single-year query-builder controls are superseded by the multi-selection extract workflow.

**Build record:** The owner approved the combined build, including Sonnet 5.5 and Haiku 5.5. Implemented two-page navigation, six topic cards/18 examples, same-page conversation, a reopenable Need ideas bar, a four-step multiple-selection extract builder, definition lookup, evaluation/model settings, long and compatible institution-year CSVs, and charts from the same result. The 14 integration tests pass; both models passed the same seven live planner cases. See `evaluations/prototype_verification.json` and `evaluations/prototype_model_comparison.json`. This is a functional prototype, not comprehensive model reliability or production load certification.
