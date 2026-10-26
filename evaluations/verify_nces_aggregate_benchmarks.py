"""Verify saved benchmark artifacts against independent source checks; write review."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.catalog import readonly,annual_path
OUT=ROOT/'evaluations/nces_aggregates'


def main():
    manifest=json.loads((OUT/'source_manifest.json').read_text(encoding='utf-8'))
    rows=json.loads((OUT/'reference_results.json').read_text(encoding='utf-8'))
    app=json.loads((OUT/'application_results.json').read_text(encoding='utf-8'))
    summary=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
    checks=[]
    def check(label,condition):
        if not condition:raise AssertionError(label)
        checks.append(label)
    check('All 45 supplied files and 824 observations represented',len(manifest)==45 and len(rows)==824)
    check('Each source cell occurs exactly once',len({(r['source_file'],r['source_sheet'],r['source_row']) for r in rows})==824)
    check('Original workbooks unchanged',all(hashlib.sha256(Path(m['file']).read_bytes()).hexdigest()==m['sha256'] for m in manifest))
    check('Summary reconciles with all row outcomes',dict(Counter(r['status'] for r in rows))==summary['reference_status'])
    check('No reference execution errors',not any(r['status']=='execution_error' for r in rows))
    check('Application guard tested for all cases; zero provider calls',len(app)==45 and all(a['status']=='blocked_national_scope' and a['model_calls']==0 for a in app))
    check('No fabricated values for unresolved cases',all(r['actual'] is None for r in rows if r['status'] in {'definition_pending','mapping_pending','outside_local_release_coverage'}))
    calculated=[r for r in rows if r['status'] in {'match','mismatch'}]
    check('Every numerical comparison has source definitions and SQL',all(r.get('sql') and (r.get('field_evidence') or r['q']==1) for r in calculated))
    check('Pass/fail flags obey recorded precision',all((abs(r['actual']-r['expected'])<=r['tolerance']+1e-10)==(r['status']=='match') for r in calculated))
    with readonly(annual_path(2024)) as db:
        independent={
            3:db.execute('SELECT SUM(e.EFTOTAL) FROM EF2024 e JOIN HD2024 h USING(UNITID) WHERE e.EFLEVEL=10 AND h.FIPS BETWEEN 1 AND 56 AND h.PSET4FLG IN (1,3)').fetchone()[0],
            24:db.execute("SELECT SUM(c.CTOTALT) FROM C2024_A c JOIN HD2024 h USING(UNITID) WHERE c.CIPCODE='99' AND c.MAJORNUM=1 AND c.AWLEVEL=15 AND h.FIPS BETWEEN 1 AND 56 AND h.PSET4FLG IN (1,3)").fetchone()[0],
            32:db.execute('SELECT 1.0*SUM(e.RET_NMF)/SUM(e.RRFTCTA) FROM EF2024D e JOIN HD2024 h USING(UNITID) WHERE e.RET_NMF>=0 AND e.RRFTCTA>=0 AND h.FIPS BETWEEN 1 AND 56 AND h.PSET4FLG IN (1,3)').fetchone()[0],
            207:db.execute('SELECT AVG(c.TUITION6+c.FEE6) FROM Cost1_2024 c JOIN HD2024 h USING(UNITID) WHERE c.TUITION6>=0 AND c.FEE6>=0 AND h.FIPS BETWEEN 1 AND 56 AND h.PSET4FLG IN (1,3) AND h.CONTROL=1 AND h.RPTMTH IN (1,3)').fetchone()[0],
        }
    for q,value in independent.items():
        result=next(r for r in rows if r['q']==q and r['source_year']==2024)
        check(f'Independent 2024 SQL reproduces q{q}',abs(value-result['actual'])<1e-8)
    artifact={'checks_passed':len(checks),'checks':checks,'benchmark_code_sha256':hashlib.sha256((ROOT/'evaluations/run_nces_aggregate_benchmarks.py').read_bytes()).hexdigest()}
    (OUT/'verification.json').write_text(json.dumps(artifact,indent=2),encoding='utf-8')
    counts=summary['reference_status']
    lines=['# NCES aggregate benchmark baseline — October 21, 2026','',
        '## Main finding','',
        '**The current app cannot publish these national aggregate answers: all 45 analytical requests are blocked by its existing national/state/sector scope guard.** This is an application coverage gap, not 45 arithmetic failures. The guard has not been changed by this evaluation.','',
        'A separate read-only reference runner tests candidate aggregate methods against the supplied NCES values. These diagnostic results are **not production query-engine successes**. Agreement does not by itself establish that every NCES selection/filter has been recovered.','',
        '## Complete accounting','',
        '| Reference outcome | Observations |','| --- | ---: |']
    lines += [f'| {label} | {counts.get(status,0)} |' for status,label in [
        ('match','Matches within benchmark precision'),('mismatch','Numerical differences requiring investigation'),
        ('outside_local_release_coverage','Outside local source-release coverage'),('definition_pending','Definition/method needs clarification'),
        ('mapping_pending','Historical table/field mapping unresolved'),('execution_error','Execution errors')]]
    lines+=['| **Total** | **824** |','',
        '## What was tested','',
        '- All 45 original workbooks, 824 year–value cells; original filenames, sheet/cell rows, titles, notes, and SHA-256 hashes retained.',
        '- One explicit national analytical question per workbook, with its actual period labels, through `prototype.agent.ask(use_model=True)` in fresh context. The real guard returns before planning; fail-fast mocks prevent accidental provider calls. The institution-name/UI stage and browser rendering are excluded.',
        '- Candidate source methods run against the existing 2015–2024 read-only annual databases. Each calculated observation retains the exact SQL/parameters, source field definitions and selector-code evidence, components/denominators, row counts, missingness and timing.',
        '- No application behavior or original workbook values changed. No AI provider calls were made; estimated API cost is $0.',
        '', '## Methods and interpretation','',
        '- Universe candidate: 50 states plus DC (FIPS 1–56), directory PSET4FLG 1 or 3. Per-case degree-granting, control and academic-year reporting-method filters are recorded in SQL. This candidate universe has not been approved as a complete NCES reporting-unit policy.',
        '- Counts use source totals once. Completions use first major, all CIP programs total and AWLEVEL 15 (degrees/certificates total); summing the total and detailed award levels would double-count. This was corrected in the reference harness after inspecting the codebook, not the app.',
        '- Rates use pooled numerators/denominators, not a simple average of institution rates. Aid/salary averages divide summed amounts by summed recipients/staff. Tuition/fees use the unweighted institutional average explicitly described in the NCES notes.',
        '- Source table transitions are explicit: SFA parts P1 before 2024, combined SFA in 2024; student charges IC_AY before 2024, Cost1 in 2024. No source substitution across years to fill missing releases.',
        '- Full-time staff from the salary table (9–12-month, nonmedical) are distinct from all instructional staff in the Fall Staff table. Total operating/nonoperating revenues differ from total revenues plus other additions. These distinctions were corrected in candidate methods using source descriptions.',
        '- Missing/nonnumeric/suppressed/negative-coded values are not zeros. Reference calculations use complete source pairs/rows, with exclusions counted. This diagnostic missingness policy is not an approval to publish incomplete national totals.',
        '- Academic-year enrollment, completions and aid periods bind to the source release ending that period; graduation cohorts map to the later outcome release. Table names alone do not prove period equivalence. Rows outside local releases stay untested.',
        '- Counts require exact agreement; displayed dollar averages and totals in thousands allow half a displayed unit; rates allow 0.0005 as fractions (0.05 percentage points). Tolerances are recorded per row.',
        '- A mismatch remains unresolved until NCES filters, reporting-unit exclusions, source release revisions and calculation semantics are reconciled. No mapping is selected just because it matches the benchmark.',
        '- Release-vintage example: NCES q24 labels 2023–24 completions final, while our matching C2024 source lives in IPEDS_2024-25_Provisional. The later NCES export includes 2024–25 completions not present locally. This can explain some differences, but is not asserted as the proven cause of each mismatch.',
        '', '## Clarifications and follow-up','',
        '- **Owner input requested: q8** needs the selected age category; **q200** needs the selected entering-student cohort/population and outcome. Those filters are not identified in their exports.',
        '- **Method review: q43** needs the exact estimated/reported FTE choice and professional-practice treatment. **q110** needs the exact core-expense/FTE method, reporting-unit alignment and cross-component periods. These remain explicit pending cases.',
        '- Investigate remaining numeric discrepancies and historical mapping gaps before treating these methods as accepted production specifications.',
        '- Eight pending aid observations are in source year 2023: physical fields are in SFA2223_P1, while the original variable documentation places them under SFA2223_P2. Alternative documentation records are saved in the row audit; ownership is not silently substituted.',
        '- Build national population/reporting-unit and missing-count support in the app before using these cases as end-to-end numerical acceptance tests. The current executor accepts at most 30 named institutions; raising that cap alone would not supply the missing population policy.',
        '', '## Latency and cost','',
        f'- Median analytical guard response: {summary["application_median_seconds"]:.4f} seconds. This measures a refusal/coverage check, **not time to calculate an unfamiliar question**.',
        f'- Median attempted reference observation, including metadata lookup and SQL: {summary["reference_median_seconds"]:.3f} seconds. This excludes AI planning, UI, and unsupported rows.',
        '- API cost: $0; no provider calls. No claim about live AI aggregate latency can be made while the scope guard blocks these requests.',
        '', '## Per-workbook results','',
        '| ID | Subject | Match | Difference | Outside coverage | Definition pending | Mapping pending |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for case in summary['case_status']:
        c=case['counts'];lines.append(f'| q{case["q"]} | {case["title"].replace("|","/")} | '+ ' | '.join(str(c.get(k,0)) for k in ['match','mismatch','outside_local_release_coverage','definition_pending','mapping_pending'])+' |')
    lines+=['','## Files and reproducibility','',
        '- `reference_results.csv`: convenient row-level comparison and SQL.',
        '- `reference_results.json`: full source evidence and diagnostic detail.',
        '- `source_manifest.json`: complete original benchmark observations, notes and hashes.',
        '- `application_results.json`: all 45 actual guard responses and timings.',
        '- `summary.json`, `verification.json`, `run.log`: machine-readable totals, independent checks and final run log.',
        '- `initial_reference_results.json`: initial diagnostic run retained for transparency. It contains superseded candidate mappings (including overlapping completions totals); do not use it as the final result.',
        '- Runner: `evaluations/run_nces_aggregate_benchmarks.py`; verifier/report builder: `evaluations/verify_nces_aggregate_benchmarks.py`. Run both from agent-redesign using the configured Python.',
        '',f'Artifact verification: **{len(checks)} checks passed**, including source-file integrity, full row accounting and four independent SQL spot checks. These checks verify the evaluation artifacts, not full semantic validation of every candidate aggregate method.','']
    (OUT/'REVIEW.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(artifact,indent=2))


if __name__=='__main__':main()
