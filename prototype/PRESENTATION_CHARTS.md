# Chart formatting and presentation exports

Implemented October 20, 2026. The chart editor and local chat edits share session settings keyed by validated result ID. An edit to either surface is carried into the next edit; source rows, calculations, query plans and data downloads remain unchanged. Repeated displays of the same result share its formatting. Clear conversation clears formatting and undo history.

## Interface

Below a chart, **Format chart** opens a bounded, scrollable editor beside the plot. Layout, Text, Style and Axes tabs expose supported controls. Ordinary controls update immediately; the two numeric bounds and reference-line inputs have explicit Apply buttons so incomplete inputs cannot reach the renderer. Undo retains the last 20 presentation states per result. Reset restores automatic defaults. Opening an editor disables transcript autoscroll while editing; submitting another question closes editors and restores new-answer scrolling.

**Preview & download chart** opens Presentation preview. It is also accessible from Format chart → Layout → Presentation preview. Choose full-slide 16:9 or half-slide 4:3, PNG or SVG, and standard/high resolution. Multiple chart panels are selectable and exported individually. The preview is the actual PNG produced from the same complete figure specification as the download.

## Controls

- Line/bar chart type; bar ordering; separate trend-series panels with shared comparable limits.
- Title, subtitle and physical X/Y axis titles. An empty edited subtitle hides it.
- Supported font family and separate title, axis/legend and value-label sizes.
- Per-series colors, markers, line width, marker size, bar width, numeric gridlines and background/transparent output.
- Top/bottom/left/right/hidden legend or direct line-end labels.
- Automatic/no/latest/endpoints/all line-value labels. Bar labels can be shown or hidden. Direct labels continue to identify series when value labels are hidden.
- Compact/standard numbers, decimals and suggested numeric tick count. Every year remains visible; tick-label angles are automatic and manual rotation is unavailable for now.
- Validated numeric limits/reset, reference-line value and label. Numeric limits target Y for lines and X for horizontal bars, preserving the older command convention. Percentage-only bounds remain within 0–100.
- Built-in Presentation preset: larger fonts, latest values and direct labels. Tick-label layout stays automatic. Other existing defaults are retained until selected.

## Prompt examples

All supported commands run locally without an analytical query/model call. Existing chart-type, title/axis-title, table, ordering, overall-color and numeric-range commands remain.

```
Make Mount Holyoke blue, Smith gray, label the latest values, and change the title to "Enrollment trends"
Set font size to 18
Set title size to 28
Set font to Georgia
Hide markers
Hide gridlines
Move legend to bottom
Use direct labels
Label endpoints
Set decimals to 2
Use compact numbers
Use separate panels
Use presentation preset
Use half slide layout
Add reference line at 2500 labeled Benchmark
Remove reference line
Make background transparent
```

Series names may use an unambiguous substring of an actual displayed series. Ambiguous matches are rejected. Compound commands apply atomically, preserving quoted titles and numeric commas. Unsupported wording returns clarification rather than partially applying commands. Comma-separated analytical questions continue to the analytical pipeline.

## Export integrity

`chart_format.py` styles copied Vega-Lite specs and composes titles, subtitles, actual executed table metadata, release status, panel notes and material warnings into one figure. Annual sources are abbreviated only when they belong to one survey/table family. Other source rows remain explicit. Missing values, source-protocol segments, category membership, separate totals and all year ticks are retained. `vl-convert-python` is installed project-locally and recorded in requirements. PNG output is exactly 1200×675 or 800×600 at standard resolution, doubled at high resolution; SVG has the matching vector canvas. Long notes are wrapped and the figure scales to fit without dropping provenance.

## Scope and remaining roadmap

This implements the approved formatting-panel and PNG/SVG presentation workflow. It does not implement native/editable PowerPoint export, saved cross-session personal themes, free-placement callouts, shaded bands, collision-free automatic labels, arbitrary custom canvas sizes, series hiding/renaming, or new stacked/scatter chart types. Dense direct labels may overlap; users can use separate panels or a legend. Font appearance depends on fonts available in the browser and exporter. The existing compact conversation chart remains responsive; exports have a fixed canvas.

## Verification

Five new tests cover compound edits, ambiguity and analytical routing; immutable source results and gaps; actual styling, references and shared-scale panels; actual PNG/SVG render content and exact dimensions; and real Streamlit controls → chat → preview → undo/reset with the analytical entry point prohibited. Existing chart-edit tests remain. The combined regression report and dated progress log record completed runs. `tests/presentation_gallery.py` is a local-only visual QA fixture and is not used by the production app.
