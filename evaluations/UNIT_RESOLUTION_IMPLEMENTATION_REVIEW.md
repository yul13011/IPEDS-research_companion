# Resolution of the 2,484-entry batch — October 22, 2026

Owner authorized resolving source-supported cases first, then reviewing genuine
remaining uncertainty. Frozen starting assignments are preserved in
`unit_catalog_before_resolution.sqlite`; version 3 is active in the derived unit
catalog. Original codebooks and annual observations were not modified.

## Outcomes

- 2,459 of the original 2,484 annual field entries now have a fixed source-supported
  quantity/unit classification.
- 25 require a same-institution program-unit selector. These are five program-length
  fields in each of five releases, not 25 missing definitions.
- No unclassified static unit remains in that batch. This is not a claim of independent
  manual verification of every other catalog assignment or every currency/scale.
- Related first-program lengths were also corrected: older sources explicitly use
  contact hours; newer ones require the same-row selector. There are 30 conditional
  fields in the full catalog. Explicit week durations now precede population parsing.
- Inspected 40,322 positive program-length observations across those 30 fields. Every
  observation has a recognized source unit code. Missing/unreported/unrecognized codes
  still leave a future observation unresolved; the app never substitutes a basis.

## Source handling

Long field definitions establish monetary quantities, award counts, housing capacity,
meal frequency, durations and identifiers even where labels are short or misspelled.
Finance section headings provide additional evidence for terse 2015 descriptions such
as “Instruction-All other.” Sections are reread from the supplied metadata, checked
against the field identity/title/definition, included in assignment evidence and
fingerprinted. A reused ID with changed evidence cannot inherit the section's unit.

Program lengths use PRGMSR1–6 from the same institution/release/table. The auxiliary
read is read-only, bounded to one unique institution record, and restricted to source
metadata identifiers. Codebook category records establish clock, credit or contact
hours. Evidence retains selector value, category record, SQL and parameters. Numeric
lengths are unchanged. Direct catalog and relational results share this presentation
resolution; unresolved conditional quantities cannot authorize arithmetic beforehand.

Monetary display now accepts the resolver's actual field evidence when the label alone
does not say salary/expense/etc. The existing finance reporting convention includes
the F1A table suffix. Currency and scale are still checked separately; no foreign
currency conversion or value rescaling is introduced.

Saved direct assignments from older rule versions can be revalidated. A saved derived
result whose input unit evidence changes requires rerunning, rather than silently
endorsing the prior computation. Historical values and units remain in audit exports.

## Remaining source issue to review

For the sixth-largest program in 2020–2024, prose describes clock/credit hours but
PRGMSR6 code 1 is labelled “Contact hours.” Display preserves that literal source
category; clock and contact are not silently harmonized. One issue repeated across
five releases is listed in [review items](UNIT_RESOLUTION_REVIEW_ITEMS.md).

An intermediate diagnostic falsely flagged 2,056 observations because its accepted
labels omitted “Contact hours.” Inspecting their actual code records corrected the
diagnostic and runtime label handling; final missing-basis count is zero. No data
values or category codes were altered to achieve that result.

## Verification

Evidence-rich before/after records, original workbook/sheet/row references and category
locations are in `unit_resolution_review.json`. Regression logs are
`unit_resolution_acceptance_final.log` and `unit_resolution_saved_results_final.log`;
the latter passed 16 focused checks in 20.889 seconds after final saved-result changes.
Final wide-run result is recorded in daily progress. The first wide run exposed a
test fixture that omitted its rule version, allowing correct source revalidation;
the fixture now explicitly represents a current unresolved unit to test axis blocking.

The affected run passed **75 tests in 154.152 seconds**. The final 16-test focused
recheck overlaps that run; it is not 91 distinct tests. Complete combined regression
coverage has not been run in this follow-up.

No model calls or external-source investigation were needed. No complete combined
suite or broad provider-backed evaluation was run. National aggregate reconciliation
remains paused. Broader independent verification of the whole unit catalog remains open.
