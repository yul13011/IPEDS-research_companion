# AI-assisted discovery interpretation

Discovery questions now have two optional model stages: proposing possible concepts/search phrases, then writing from verified catalog evidence. Original keyword searches remain in every AI-mode search audit. Analytical planning is unchanged.

## What was checked

- Fabricated concepts cannot pass by supplying an unrelated valid word such as enrollment: concept and phrase tokens must co-occur in one documented, physically present record.
- Verification honors source-release year filters. Suggestions cannot add dates or execute SQL. No matching documentation produces a rejected suggestion, not a claim that the requested data are absent.
- Original hits remain in the merged audit; unavailable/invalid interpretation preserves original ranking and topics. Verified matches and direct original-title matches receive display priority when an expansion is available.
- Table and variable searches have reserved result allocations. Singular/plural variants such as salary/salaries remain inside required concept tokens. This avoids missing salary-outlay tables while keeping conjunctions strict.
- Annual derived fall-enrollment titles are normalized before grouping; annual copies no longer crowd the display or provoke inappropriate model merges.
- Ambiguity and tentative mappings remain in the source audit and mandatory narrative qualifications. Catalog matching establishes existence, not semantic equivalence to the user's wording.
- Source/writing validators, offline mode and bounded fallback remain active. Usage and cost are aggregated by stage; unknown usage is not reported as zero.

## Final live examples

| Everyday wording | Verified proposed concepts, among others | Original target probe | Expanded target probe |
|---|---|---|---|
| What families actually pay | Net price; cost of attendance; tuition and fees; grant aid received | Found | Found |
| Teachers' pay | Instructional staff salaries; salaries of all staff | Found | Found |
| Students who leave | Retention rate; transfer-out rate; graduation/completion status | Found | Found |
| Students from overseas | U.S. nonresident enrollment; enrollment by race/ethnicity; residence of first-time students | Not found | Found |
| College tuition | Tuition and fees; cost of attendance; net price | Found | Found |

All five final answers passed writing checks and retained original search hits in the audit. These probes look for expected documented-title substrings, not comprehensive semantic precision/recall. Peripheral matches and tentative mappings remain possible; nonresident is not asserted to be equivalent to every meaning of overseas/international students, and retention or transfer is not treated as synonymous with dropping out.

## Measured latency and cost

The final five-case set combines four cases from a sequential pass and one family-cost retest after allowing a fourth bounded alternative. It is not a homogeneous performance benchmark.

- Median complete server answer time: **11.27 seconds**; range **8.60–17.68 seconds**.
- Median interpretation-plus-catalog-verification time: **3.63 seconds**.
- Estimated interpretation cost: **$0.024954 for five answers**, approximately **$0.005 per answer**.
- Estimated combined interpretation/writing cost: **$0.575488 for five answers**.

Browser rendering is excluded. One run per phrase is not an SLA or a p95. Costs use actual returned token counts and the app's documented standard provider rates; invoice adjustments are excluded. Initial runs are retained, including a 33-second case that safely fell back to original search when the model proposed four concepts against the original cap of three. The prompt still targets three; a hard cap of four now receives the same catalog verification without dropping all useful alternatives. Excessive proposals remain rejected. No additional retries were added.

## Regression evidence

**64 related tests passed in 52.023 seconds**, followed by **11 final interpretation tests passing in 6.061 seconds** after the proposal-budget tolerance and pipeline-label refinement. These include real catalog queries, adversarial proposals, timeout/no-key behavior, original search retention, year scope, ambiguity, source writing, stage-cost accounting and an actual Streamlit two-stage chat flow with mocked provider transport.

Evidence files:

- `discovery_interpretation_final.json`: final combined five-case set and per-stage metrics.
- `discovery_interpretation_live.json`: final sequential pass, including the preserved original-search fallback.
- `discovery_interpretation_family_retest.json`: successful family-cost retest with all four proposals source-checked.
- `discovery_interpretation_live_initial.json`: initial findings that motivated result-type balancing and annual title normalization.
- `discovery-interpretation-regression-final.log`, `discovery-interpretation-focused-final.log`: passing tests.

This change improves assisted retrieval; it does not certify arbitrary mappings, exhaustively cover the catalog or establish institution-level reporting completeness. Exact sources remain available under Definitions & sources.
