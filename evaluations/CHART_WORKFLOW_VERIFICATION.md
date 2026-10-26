# Whole chart workflow verification

October 21, 2026. **Passed within the tested scope.** This verifies the Faculty & Staff salary example and representative presentation edge cases, not every possible chart or setting combination.

## What was tested

The test starts with nine salary values independently checked against SAL2023_IS for Yale, Harvard and Princeton, with professor, associate professor and assistant professor ranks. It then exercises the actual app:

1. Initial grouped bars, legend and three matching Style color controls.
2. Harvard picker recoloring, with unchanged other colors and data.
3. Chart title, footnote, larger font and maximum bar width.
4. Hide the legend; keep the same usable color controls. Undo restores it.
5. Separate panels: all values retained, institution colors consistent and quantitative scales shared.
6. Switch to line: controls reflect its nine actual series; no manual tick-label angle selector is available.
7. Switch back to bar: controls return to three institutions; angle selection remains unavailable.
8. Prompt “Make Princeton green”: Harvard's picker edit survives and Princeton changes.
9. Open the actual presentation preview and exercise its PNG/SVG and full-/half-slide controls.
10. Reset formatting, undo Reset, then reset again; settings and data are checked at each step.

The saved result records 13 checkpoints. Planner and analytical execution functions are patched to fail during formatting operations; no data query or model planning is allowed to satisfy these tests. Original source rows must remain exactly unchanged.

## Export checks

- Default, edited/hidden-legend, separate-panel, prompt-edited and reset states are rendered to PNG and SVG at 1200×675 and 800×600.
- Check actual SVG bar marks, values, colors, bar gaps, legend presence/names, title, footnote and source/reporting-period text. PNG headers and SVG canvases must have exact dimensions.
- Synthetic fixtures cover one missing value, one absent institution/category row and long category labels at larger font/bar sizes. Missing values must not become zero bars. These fixtures are presentation tests, not new statistical findings.
- Twenty export pairs (40 files) plus four outputs captured from the actual preview function are saved under [chart_workflow](chart_workflow). Preview high-resolution PNG outputs use twice the selected canvas dimensions.
- Inspected representative rendered images: default full slide, long-label half slide, and the actual edited half-slide preview. Colors, bars, values and source notes are visible. This is sampled visual inspection alongside automated checks, not manual inspection of every exported pixel.

## Test-harness boundary

Streamlit AppTest widget runs use full-script reruns, which dismiss button-opened dialogs instead of emulating browser fragment reruns. The main-app preview-open click is tested. Subsequent dialog controls use the real `preview` function in a dedicated AppTest harness with the **exact same edited result/settings**; actual generated files are captured and verified. The preview is not mocked, but this is not a browser-based acceptance test of fragment scheduling. Initial harness failures are retained in `chart_workflow_tests.log` and `chart_workflow_ui_recheck.log` rather than reported as application failures or hidden.

## UI corrections

The owner subsequently requested removing manual axis tick-label rotation entirely. The Axes tab no longer offers an angle selector for any chart. Previously supported rotation prompts return a local unavailable response without querying data; cached manual angles and presentation presets no longer override automatic label layout. The explanatory caption still describes the applicable numeric axis: Y for lines, horizontal X for bars. This supersedes the earlier line-only angle control.

Wrapped category-label line spacing and required chart height now track the selected font size. This prevents larger multiline labels from retaining a smaller fixed line height.

No statistical calculation, data source or preset plan changed. National benchmark testing remains paused.

## Results and reproduction

- **2 new workflow tests passed in 87.699 seconds**: [final log](chart_workflow_verified_tests.log).
- **17 existing chart/formatting/prompt-edit regressions passed in 40.793 seconds**: [regression log](chart_workflow_regression.log).
- Follow-up after rotation removal: **7 chart-formatting and whole-workflow tests passed in 140.568 seconds**, recorded in [removal verification](axis_rotation_removed_tests.log); the earlier 19-test evidence above precedes this follow-up. Workflow checks now assert that angle controls are absent on both chart types and saved angles cannot override automatic layout.
- Machine-readable evidence: [workflow checkpoints and exports](chart_workflow/whole_workflow_verification.json), [edge cases](chart_workflow/edge_case_verification.json).
- Tests added to the combined regression runner; the entire combined runner was not rerun for this scoped update. These are test execution durations, not answer latency.

Run `python -m unittest prototype.tests.test_chart_workflow prototype.tests.test_charts prototype.tests.test_chart_format prototype.tests.test_chart_edits -v` using the project's Python/dependency environment with local Streamlit networking available.
