# Chart readability standard

Implemented October 19, 2026 in `charts.py`; shared by chat results, examples and extract previews through `components.render_result`. Chart preparation copies validated rows and never changes calculations, source results or exports. Explicit chart/table requests and supported presentation edits remain available.

| Area | Standard |
| --- | --- |
| Selection | Trends default to lines; comparisons default to horizontal bars; single lookups include a prominent value. Explicit user requests take priority. A bar edit of a time series keeps years distinct and chronological by default. |
| Category limit | Single-period comparisons with more than 12 category labels default to the full table, with a short explanation. Count distinct measures/categories or institutions within a unit, not cells or reporting years. Different units are assessed separately. Explicit chart requests and subsequent chart-type edits can override this default. No categories are removed, combined or truncated. |
| Titles/scope | Neutral automatic titles, institution labels, actual reporting periods and documented population selectors. Preserve custom titles. Cohort queries use entering-cohort years when that is their requested time basis. Never label all charts with a generic source-release year. |
| Labels | Readable source-based labels; technical generated variable labels can use the numerator's source-definition title. Full original measures/periods remain in tooltips and source controls. Wrapped category labels stay horizontal, with 13-pixel axis labels. |
| Ordering | Comparisons rank largest first by default. Degree-level and chronological sequences retain meaningful order. User alphabetical/ascending/descending edits take priority. |
| Values | Bar values are directly labeled: counts use commas, percentages one decimal plus %, currency dollar formatting, ratios up to four decimals. Full precision stays in tables/downloads. Missing rows are never labeled zero. |
| Size | Bar height adapts to category count, label wrapping and institution clusters; typically at least 36 pixels per category with more room for wrapped labels. Line panels use 320 pixels. Width follows the containing page. |
| Colors | One restrained color when axis labels already identify categories/institutions. Multiple trend/cluster series use a four-color palette and consistent mapping within the result. Trend dash patterns provide another distinction. Compact top legends identify multiple series. |
| Axes | Default bar scales include zero; signed values extend on both sides. Percentage comparison bars use 0–100. Percentage trends may focus the range, with a visible note and bounds within 0–100. User-selected ranges are disclosed. |
| Time ticks | Show every reporting year/period in a longitudinal result, in chronological order; never thin the labels to four ticks. Axes with more than six periods use 45-degree labels to help fit them. Automatic overlapping-label removal is disabled. Entering-cohort trends follow the same rule. |
| Panels | Up to four trend series per panel. Additional panels preserve all requested series/observations. Same-unit comparable panels share a domain; different units are separated. Multiple institutions in a single-measure bar comparison can remain together rather than arbitrarily splitting at four. |
| IPEDS categories | Unknown and Nonresident stay visible. Recognized overall totals are separate from component bars; a single total is presented as a separate prominent value. No categories are silently combined into Other. |
| Integrity | Missing observations remain gaps. Existing source-protocol series segments remain separate. Chart restructuring never aggregates source rows or omits requested series to meet a visual limit. |

The Display table, Definitions & sources and Download Data controls are unchanged. Source periods, status, provisional status and full measures remain available in tooltips. Source warnings remain visible.

Verification includes real-source race counts/percentages, eight-institution comparisons, eight-series trends, category trends, cohort axes, signed scale behavior, currency/percentage formatting, data immutability, separate totals, chart-type follow-ups, Streamlit rendering and existing export checks. `tests/chart_gallery.py` supports normal (900-pixel) and narrow (360-pixel) container inspection without model calls. Browser previews are retained in `evaluations/chart-readability-*.png`.

Limits: this is a first shared standard, not exhaustive accessibility certification. Large single-period comparisons now default to tables under the category limit above; explicitly requested charts and large trends may still produce scrollable panels. Narrow-container checks do not certify every mobile browser. Display labels are conservative transformations; unsupported semantic relabeling must retain source wording. Native chart/table controls and full-precision downloads remain the way to inspect exact observations.

Final verification: 119 combined regression tests passed. Eight chart-specific tests passed again after final legend/axis adjustments. Browser checks confirmed readable wrapped category labels at normal/narrow widths, four-series panel legends, and compact temporal ticks retaining both endpoints. Preview images and evaluations/chart_readability_verification.json retain the evidence. The temporary gallery was stopped; the app remains available on port 8516.

October 20 update: the every-year time-tick rule above supersedes the earlier four-label thinning. Existing dated preview images show the earlier design. The chart regression now checks all ten 2015–2024 labels in every panel of an eight-institution trend.

October 20 line-connection fix: annual source-release provenance is not a line break. The catalog executor now emits a stable segment for independent annual observations; chart preparation also normalizes the older generated `source release YYYY` markers without changing stored results. Explicit protocol/scope segments remain separate, and missing values still break lines. A real-source ten-year Yale undergraduate gender regression checks two ten-point line groups, legacy-result rendering, immutability, explicit protocol segments and a missing-value gap. Nine chart and ten catalog-execution checks passed.

## Verified user controls (October 20)

Chat edits are parsed locally and reuse the latest available result. A rejected/clarifying edit does not erase the prior chart as an editing target. No analytical/model request is needed for supported display edits.

| Control | Verified wording |
| --- | --- |
| Chart type | `Make it a bar chart`; `Use a line chart` |
| Chart title | `Set chart title to "Enrollment comparison"` |
| Axis labels | `Change x-axis to "Year"`; `Change y-axis to "Students"`; explicit `axis label`/`axis title`, spaced `x axis`, and `Rename the x-axis to ...` variants |
| Numeric range | `Set y-axis range to 1,000–4,000`; `Reset y-axis range`. Signed limits are supported. In horizontal bars this legacy command targets the numeric x-axis. Percentage-only results require bounds within 0–100. An unquoted x-axis year range is not mistaken for a text-label edit. |
| Overall color | `Make the lines blue`; `Make the bars #24658A` |
| Bar order | `Sort bars in ascending order`; `Sort bars in descending order`; `Sort bars alphabetically` |
| Table | `Show the table`; `Hide the table`; direct Display table toggle; underlying counts/data-status checkbox |
| Inspection | Hover tooltips contain institution, period, measure, value and data status. |

`tests/test_chart_edits.py` drives the Streamlit chat UI using real Mount Holyoke College and Smith College total-enrollment results. It inspects emitted charts, native tables and preserved data. Three focused tests passed at that checkpoint.

October 20 presentation update: font, legend, gridline, marker and per-series color settings are now supported through a shared Format chart panel and local prompt edits. Default readability and data-integrity rules above remain; users may override presentation settings. Presentation preview exports complete PNG/SVG figures with fixed slide canvases, titles and source/caveat text. See [PRESENTATION_CHARTS.md](PRESENTATION_CHARTS.md) for controls, commands, export behavior and remaining roadmap.

October 20 trend follow-up fix: a request such as “Show a 10-year trend” changes the analytical time scope and re-queries annual source data. A ten-year window ending in Fall 2024 binds to all ten 2015–2024 observations before chart selection. It must not be treated as a formatting-only conversion of the earlier single-year lookup. See [TIME_SCOPE.md](TIME_SCOPE.md).
# Grouped-bar spacing correction — October 21, 2026

Whole-workflow acceptance is now covered by `tests/test_chart_workflow.py`: independently verified values, actual app legend/control/color consistency, picker and prompt edits, separate panels/shared scales, chart-type changes, Reset/Undo, and actual PNG/SVG exports at both slide sizes. Missing/absent category and long-label fixtures preserve missingness. Category line height follows font size. Manual tick-label rotation is removed at the owner's request: no angle selectors, no preset/cached overrides, and formerly supported rotation prompts return an unavailable response locally. Automatic chart label layout remains. Bar captions describe the horizontal numeric axis. Scope/evidence and the preview-dialog harness boundary are documented in `evaluations/CHART_WORKFLOW_VERIFICATION.md`.

Color controls use the actual rendered chart color domains/ranges, including overall colors and custom overrides, rather than assuming line-series identities for every chart. Thus institution-colored grouped bars show institution pickers (three for the salary comparison), while multi-category line charts retain their separate line-series controls. Picker defaults match the displayed colors; editing one preserves the other displayed colors. Prompt color targets use the same mapping. Tests exercise actual Style pickers, bar encodings and a subsequent prompt edit without requerying data.

Grouped horizontal bars use an explicit institution offset domain in the same order as the legend. Bar and label layers share that offset. Category/offset bands include visible gaps, and plot height accounts for the selected bar thickness, label size and institutions per group. Slide exports preserve the required plot height before scaling the complete figure to the requested canvas. This prevents fixed-width bars from becoming crowded when several institutions share one category or when users increase bar width.

The faculty salary comparison is verified with all nine observations at default 18-pixel and maximum 40-pixel bar widths, both in chart specifications rendered to SVG and in slide specifications. Tests measure at least six pixels between neighboring unscaled bar rectangles and assert Yale/Harvard/Princeton order matches the legend. No source rows are changed. Before/after PNG/SVG evidence and the 15-test passing chart/formatting log are in `evaluations/faculty_salary_chart_*`.

