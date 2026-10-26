"""Live replay of the reported clarification; records latency and SQL cross-checks."""
from pathlib import Path
import datetime,json,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.institution_confirmation import ask
from prototype.catalog import readonly,annual_path

question='number of faculty of Yale University in the past 10 years'
message='Which faculty count do you want for Yale University (UNITID 130794), Fall 2015-2024? Options: (a) instructional staff with faculty status (full- plus part-time, EAP table), (b) full-time instructional staff only (Fall Staff tables), or (c) all staff with faculty status (including research/public-service faculty)? If you have no preference, I will use (a), total instructional staff with faculty status, as a count per fall year.'
history=[{'question':question,'answer':{'intent':'clarify','message':message,
    'catalog_context':{'kind':'catalog_clarification','question':question,'previous_plan':None},
    'institution_identity':{'unitids':[130794],'confirmed_choices':{'yale university':130794}}}}]
start=time.perf_counter();report={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'question':question,'reply':'(a)'}
try:
    answer=ask('(a)',use_model=True,conversation=history)
    report['answer']=answer
    rows=answer.get('result',{}).get('rows',[])
    checks=[]
    for row in rows:
        year=row['observation_year']
        with readonly(annual_path(year)) as db:
            raw=db.execute(f'SELECT EAPFT,EAPPT FROM EAP{year} WHERE UNITID=130794 AND OCCUPCAT=210 AND FACSTAT=10').fetchall()
        expected=float(raw[0][0])+float(raw[0][1]) if len(raw)==1 else None
        checks.append({'year':year,'value':row['value'],'independent_source_value':expected,'passed':row['value']==expected})
    report['source_checks']=checks
    report['passed']=len(rows)==10 and {c['year'] for c in checks}==set(range(2015,2025)) and all(c['passed'] for c in checks)
except Exception as exc:
    report.update(passed=False,error_type=type(exc).__name__,error=str(exc))
report['test_wall_seconds']=time.perf_counter()-start
(ROOT/'evaluations/faculty_clarification_live.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='answer'},indent=2))
if report.get('answer'):print(json.dumps({k:report['answer'].get(k) for k in ['intent','message','latency','model_usage']},indent=2))
sys.exit(not report['passed'])
