# Degrees breakdown: build spec

Recorded: November 7, 2026

**Status: Design approved from mockups; not yet built.** This specifies the answer for a single-school "how many degrees" question: instead of returning one number (and guessing whether "degrees" includes certificates), the app returns the institution's full award composition — degree levels and certificate levels — with both subtotals shown. Groups and longitudinal sets are explicitly out of scope here (see §8).

## 1. Problem

"How many degrees did X award?" is ambiguous between degrees-only (IPEDS award-level total, code 12) and degrees-plus-certificates (code 15). The two diverge materially at schools with real certificate programs (Harvard ~18%, Southern Connecticut State ~6%) and are identical at schools without them. Picking one definition silently is a guess, and the LM planner currently flips between the two run-to-run, so the same question can return different numbers.

Resolution: for a single school, **stop guessing and show the composition.** A "degrees" question is usually a request for the shape of what a school produces, not a single scalar. Showing degrees by level, certificates by level, and both subtotals answers the literal question (degrees total) while making the certificate context visible without inflating the degree count.

## 2. Scope

In scope: one institution, one award year (default: latest release), the generic "degrees"/"awards" question with no specific level named.

Out of scope for this build: multiple institutions (groups), multiple years (longitudinal), and a level-specific question ("how many master's did X award"), which keeps its existing single-number answer. The group/longitudinal design is sketched in §8 and deferred.

## 3. Answer shape

1. **Two totals** as metric cards: `Degrees` (code 12) and `With certificates` (code 15), the latter annotated with `+N certificates`.
2. **Segmented bar** summarizing the mix: degree levels in the blue ramp, certificate levels in the amber ramp, widths as share of all awards (code 15).
3. **Two-section table:**
   - `Degrees — by academic level`, ordered ascending: associate's → bachelor's → master's → doctoral (research) → doctoral (professional) → doctoral (other). Closes on `Degrees total`.
   - `Certificates — by award level`, ordered ascending by length/level: under 1 year → 1–2 years → 2–4 years → postbaccalaureate → post-master's. Closes on `Certificates total`.
   - Final `All awards` row = code 15.
   - Share column is within each section (section subtotals = 100%).
4. **Every nonzero level is shown; zero levels are omitted.** Trivial-but-nonzero levels (e.g. a single doctoral-other) are kept so the rows reconcile exactly to the subtotals and totals. (Owner decision, Nov 7.)

Rendering should reuse the app's existing answer-card styling (metric cards + table), not the standalone HTML of the mockups. The mockups (`design-mockups/`) are the visual reference.

## 4. IPEDS award-level reference (Completions, CIPCODE=99, MAJORNUM=1)

Degrees:

| AWLEVEL | Meaning |
| --- | --- |
| 3 | Associate's degree |
| 5 | Bachelor's degree |
| 7 | Master's degree |
| 17 | Doctor's degree — research/scholarship |
| 18 | Doctor's degree — professional practice |
| 19 | Doctor's degree — other |
| **12** | **Degrees total** (= 3+5+7+17+18+19) |

Certificates:

| AWLEVEL | Meaning |
| --- | --- |
| 1 | Award of less than 1 academic year |
| 2 | Award of at least 1 but less than 2 academic years |
| 4 | Award of at least 2 but less than 4 academic years |
| 6 | Postbaccalaureate certificate |
| 8 | Post-master's certificate |
| **15** | **Degrees and certificates total** (grand total) |

Certificates total = code 15 − code 12. (Codes 13/14/20 are intermediate certificate subtotals IPEDS also publishes; the app computes its own certificate subtotal and does not need them.)

Verified against live data (2023–24): Southern Connecticut State (UNITID 130493) — degrees 2,234 = 1,575+625+34; certificates 134 = 22+30+82; all awards 2,368. Yale (UNITID 130794) — degrees 5,179 = 1,665+2,757+438+318+1; certificates 84 = 2+74+8; all awards 5,263.

## 5. Registry additions (`prototype/build_registry.py`)

Already present (degree levels): `associates_degrees` (3), `bachelors_degrees` (5), `masters_degrees` (7), `doctoral_research_degrees` (17), `doctoral_professional_degrees` (18), `total_degrees` (12), `total_awards` (15).

To add, same pattern — `add(id,label,'completions','degrees',['CTOTALT','AWLEVEL','CIPCODE','MAJORNUM'],'CTOTALT',{'AWLEVEL':N,'CIPCODE':'99','MAJORNUM':1})`:

- `doctoral_other_degrees` — AWLEVEL 19
- `certificate_undergraduate_lt1yr` — AWLEVEL 1
- `certificate_undergraduate_1to2yr` — AWLEVEL 2
- `certificate_undergraduate_2to4yr` — AWLEVEL 4
- `certificate_postbaccalaureate` — AWLEVEL 6
- `certificate_postmasters` — AWLEVEL 8

Rebuild with `python -m prototype.build_registry`; confirm the new annual mappings pass the existing codebook-evidence recheck in `analytics.execute`.

## 6. Assembly

A deterministic completions-breakdown builder (sibling to `catalog_planner.cost_plan` / `aid_plan`), given one confirmed UNITID and one year:

1. Execute every degree-level and certificate-level measure plus `total_degrees` and `total_awards` for the UNITID/year (one `Plan`, many metrics).
2. Keep nonzero levels; order per §3; compute within-section shares.
3. Reconciliation checks (hard): sum of degree-level values == `total_degrees`; sum of certificate-level values == `total_awards` − `total_degrees`. On mismatch, block the answer rather than show numbers that do not add up (consistent with `analytics.execute`'s duplicate/validity guards).
4. Emit a result the render layer turns into the two-card + table layout.

## 7. Wiring

Route to the breakdown when: family is completions, exactly one institution, one year, and no specific award level named in the question. Detect "awards/credentials/completions" wording to label the default emphasis, but the breakdown shows both totals regardless, so the old degrees-vs-certificates routing coin-flip is removed. A level-specific question ("bachelor's", "master's") keeps the existing single-measure answer. More than one school or year falls back to current behavior until §8 is built.

## 8. Deferred: groups and longitudinal sets

Design sketched, not specified here. Principles agreed: one definition governs the whole result set (never mixed per cell); a single global toggle flips the entire set; the "include certificates" offer is surfaced only when the gap is material somewhere in the set; the accompanying note localizes where it matters (which years, which schools). Materiality is a magnitude test (e.g. certificates ≥ ~3% of degrees), since nearly every school has a few certificates (Yale 1.6%). Per-school rows vs. a single summed figure for groups is still open.

## 9. Also parked

The one-line / narrative "degrees" answer (where no table is shown) still needs a default between `total_degrees` and `total_awards`; the breakdown view does not resolve that case. Revisit with §8.

## 10. Verification

- Reconcile SCSU and Yale to the numbers in §4.
- A community-college case (associate's present, certificate-heavy) and a school with professional doctorates, to exercise ordering and the amber-heavy bar.
- Unit test: for a sample of institutions/years, sum of degree-level measures == code 12 and sum of certificate-level measures == code 15 − code 12.
- Confirm the bachelor's-at-Yale curated example and other level-specific questions are unaffected.
