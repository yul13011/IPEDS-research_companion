"""Read-only IPEDS retrieval regression cases from user-supplied Yale CSVs.

Expected values are read only from the supplied CSVs; never from query results.
This tests retrieval/methodology, not an LLM agent that has not yet been built.
"""
from pathlib import Path
from decimal import Decimal
import csv,hashlib,json,sqlite3,collections,sys

BASE=Path(__file__).resolve().parents[1];SOURCES=BASE/'Test cases';OUT=BASE/'evaluations'/'results';ANNUAL=BASE/'data'/'annual'
YALE=130794
FILES={'enrollment':'w005-enr-historical-by-level(in).csv','sat':'w032-first-year-sat-scores(in).csv','admissions':'w033-yale-college-admissions-summary(in).csv','graduation':'w041-yale-college-graduation-rates(in).csv','subgroups':'yale-college-grad-rates-subgroups(in).csv'}
connections={};cases=[];source_manifest=[]
definitions=json.loads((BASE/'evaluations'/'benchmark_definitions.json').read_text())
metadata=sqlite3.connect('file:'+(BASE/'data'/'metadata_catalog.sqlite').as_posix()+'?mode=ro',uri=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(family):
    path=SOURCES/FILES[family];digest=sha(path)
    with path.open(encoding='utf-8-sig',newline='') as f:values=list(csv.DictReader(f))
    source_manifest.append({'family':family,'file':str(path),'sha256':digest,'rows':len(values)})
    return enumerate(values,2)
def connection(year):
    if year not in connections:
        matches=list(ANNUAL.glob(f'IPEDS_{year}-*/*.sqlite'))
        if len(matches)!=1:raise RuntimeError('Expected exactly one source for '+str(year))
        connections[year]=(sqlite3.connect('file:'+matches[0].resolve().as_posix()+'?mode=ro',uri=True),matches[0])
    return connections[year]
def test(family,rownum,metric,expected,year,sql=None,params=(),tolerance='0',blocked=None,interpretation='',entry_year=None):
    case={'id':f'{family}-{rownum}-{metric}','family':family,'source_file':FILES[family],'source_row':rownum,'metric':metric,'expected':str(expected),'observation_year':year,'entry_year':entry_year,'interpretation':interpretation,'tolerance':tolerance}
    case['question']=f"For Yale University, report {metric} for "+(f"the {entry_year} entering cohort, observed after six years in {year}." if entry_year is not None else f"fall {year}.")
    if not 2015<=year<=2024:case.update(status='outside_coverage',reason='Required observation release is outside imported 2015–2024 data; no substitute year used.')
    elif blocked:case.update(status='needs_definition',reason=blocked)
    elif sql is None:case.update(status='unsupported_field',reason='This percentile or subgroup field was not collected in the required IPEDS release.')
    else:
        db,path=connection(year);result=db.execute(sql,params).fetchall()
        case.update(database=str(path),sql=sql,parameters=list(params))
        if len(result)!=1 or result[0][0] is None:case.update(status='missing_data',actual=None,reason=f'Expected one nonmissing value; got {result}')
        else:
            actual=result[0][0];difference=Decimal(str(actual))-Decimal(str(expected))
            case.update(actual=actual,difference=float(difference),status='pass' if abs(difference)<=Decimal(tolerance)+Decimal('0.000000000001') else 'mismatch')
    cases.append(case)

for n,r in rows('enrollment'):
    year=int(r['Fall'])
    for col,level in [('Graduate/Professional',50),('Undergraduate',20),('Total',10)]:
        test('enrollment',n,col,r[col],year,f'SELECT EFTOTAL FROM EF{year} WHERE UNITID=? AND EFLEVEL=?',(YALE,level),interpretation='Fall headcount; graduate/professional compared to IPEDS graduate category. A mismatch is retained for population/snapshot investigation.')

for n,r in rows('admissions'):
    year=int(r['Year Entered']);assert int(r['Class of'])==year+4
    for field,column in [('Total Applications','APPLCN'),('Total Admits','ADMSSN'),('Total Matrics','ENRLT')]:
        test('admissions',n,field,r[field],year,f'SELECT {column} FROM ADM{year} WHERE UNITID=?',(YALE,),interpretation='Fall first-time degree/certificate-seeking undergraduate admissions.')
    for field,expr in [('Admit Rate','1.0*ADMSSN/NULLIF(APPLCN,0)'),('Yield Rate','1.0*ENRLT/NULLIF(ADMSSN,0)')]:
        test('admissions',n,field,r[field],year,f'SELECT {expr} FROM ADM{year} WHERE UNITID=?',(YALE,),tolerance='0.0005',interpretation='Fraction scale 0–1; expected rates displayed to 0.001. Use raw counts rather than whole-percent derived fields.')

for n,r in rows('sat'):
    year=int(r['Entered']);assert int(r['Class of'])==year+4
    section={'Verbal':'SATVR','Math':'SATMT'}[r['Test']]
    for percentile in [10,25,50,75,90]:
        col=f'{section}{percentile}';supported=percentile in [25,75] or (percentile==50 and year>=2022)
        test('sat',n,f'{r["Test"]}_{percentile}',r[f'{percentile}th'],year,f'SELECT {col} FROM ADM{year} WHERE UNITID=?' if supported else None,(YALE,),interpretation='Enrolled SAT score-submitters. User Verbal label compared to annual IPEDS SATVR field; SAT redesign/score-basis mismatches must not be silently crosswalked.')

for n,r in rows('graduation'):
    entry=int(r['Entering Year'][:4]);year=entry+6
    for field,grtype in [('Number of First Year Entering Students',8),('Number of Graduates',12)]:
        test('graduation',n,field,r[field],year,f'SELECT GRTOTLT FROM GR{year} WHERE UNITID=? AND GRTYPE=?',(YALE,grtype),entry_year=entry,interpretation='Six-year bachelor subcohort; denominator is adjusted cohort after allowable exclusions, not necessarily original entrants. This interpretation is checked against supplied counts.')
    test('graduation',n,'6-yr Graduation Rate',r['6-yr Graduation Rate'],year,f'SELECT 1.0*n.GRTOTLT/NULLIF(d.GRTOTLT,0) FROM GR{year} n JOIN GR{year} d ON n.UNITID=d.UNITID AND d.GRTYPE=8 WHERE n.UNITID=? AND n.GRTYPE=12',(YALE,),tolerance='0.0005',entry_year=entry,interpretation='Raw six-year bachelor completers / adjusted cohort, fraction 0–1; expected precision 0.001.')

for n,r in rows('subgroups'):
    entry=int(r['Year of Entry']);year=entry+6;cat=r['Category'];group=r['Group']
    for metric,grtype in [('Cohort',8),('Grads',12)]:
        sql=None;params=();block=None;note=''
        if cat=='Gender':
            col={'M':'GRTOTLM','W':'GRTOTLW'}[group];sql=f'SELECT {col} FROM GR{year} WHERE UNITID=? AND GRTYPE=?';params=(YALE,grtype)
            note='Men/women within adjusted bachelor subcohort and six-year bachelor completers.'
        elif cat=='Pell':
            if year>=2016:
                if metric=='Cohort':expr='PGADJCT' if group=='Pell' else 'SSADJCT+NRADJCT'
                else:expr='PGCMBAC' if group=='Pell' else 'SSCMBAC+NRCMBAC'
                sql=f'SELECT {expr} FROM GR{year}_PELL_SSL WHERE UNITID=? AND PSGRTYPE=2';params=(YALE,)
            note='Pell receipt per IPEDS cohort definition. Non-Pell combines subsidized-loan-only and neither-Pell-nor-subsidized-loan categories; never substitute the latter category alone.'
        elif cat=='URM':
            include_unknown=definitions['include_unknown_in_non_urm']
            if group=='International':expr='GRNRALT'
            elif include_unknown is None:
                expr=None;block='User defines URM as outside White/Asian/international. Placement of race unknown is pending clarification; 2009 benchmark appears to include it in Non-URM.'
            else:
                nonurm='GRWHITT+GRASIAT'+('+GRUNKNT' if include_unknown else '')
                expr=nonurm if group=='Non-URM' else 'GRTOTLT-GRNRALT-('+nonurm+')'
            if expr:sql=f'SELECT {expr} FROM GR{year} WHERE UNITID=? AND GRTYPE=?';params=(YALE,grtype)
            note='Custom Yale grouping, not an IPEDS URM variable. International operationalized as U.S. nonresident. Non-URM/URM require an explicit unknown-category rule.'
        else:raise ValueError(cat)
        test('subgroups',n,cat+'_'+group+'_'+metric,r[metric],year,sql,params,blocked=block,entry_year=entry,interpretation=note)

# Retain source rows for later LLM response/evaluation tests. No current agent is claimed.
for item in source_manifest:assert sha(Path(item['file']))==item['sha256'],'Benchmark file changed'
OUT.mkdir(parents=True,exist_ok=True)
summary={'status_counts':dict(collections.Counter(r['status'] for r in cases)),'family_counts':{},'source_files':source_manifest,'total_cases':len(cases),'scope':'Deterministic data-retrieval regression tests. Not LLM tool-choice, conversation, chart, or export tests. Source benchmarks unchanged; no results used to change expected values.','definitions':definitions,'unresolved_definitions':['Race-unknown placement in Yale URM/Non-URM grouping'] if definitions['include_unknown_in_non_urm'] is None else [],'rounding':'Count and SAT cells: exact. Rates: fractions with absolute tolerance 0.0005 (0.05 percentage points), reflecting 3-decimal benchmark precision.'}
for family in FILES:summary['family_counts'][family]=dict(collections.Counter(r['status'] for r in cases if r['family']==family))
(OUT/'yale_cases.json').write_text(json.dumps(cases,indent=2,ensure_ascii=False),encoding='utf-8')
(OUT/'yale_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
fields=['id','family','source_file','source_row','metric','entry_year','observation_year','expected','actual','difference','tolerance','status','reason','interpretation','database','sql','parameters']
with (OUT/'yale_results.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(cases)
for con,_ in connections.values():con.close()
metadata.close()
print(json.dumps(summary,indent=2))
print('MISMATCHES')
for r in cases:
    if r['status']=='mismatch':print(json.dumps({k:r[k] for k in ['family','metric','entry_year','observation_year','expected','actual','difference']}))
sys.exit(1 if any(r['status'] in ['mismatch','missing_data'] for r in cases) else 0)
