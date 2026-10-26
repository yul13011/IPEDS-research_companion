"""Live chat replay of ten-year gender counts, shares and a percentage follow-up."""
from pathlib import Path
import datetime,json,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.institution_confirmation import ask
from prototype.catalog import annual_path,readonly

question='Yale undergraduates by gender in the past 10 years'
cases=[];history=[]
for label,q,conversation,want_percent in [('counts',question,[],False),('percentages',question+' as percentages',[],True),('percentage follow-up','show percentages',history,True)]:
    started=time.perf_counter();case={'label':label,'question':q}
    try:
        answer=ask(q,use_model=True,conversation=conversation)
        case['answer']=answer
        rows=answer.get('result',{}).get('rows',[]);checks=[]
        for row in rows:
            year=row['observation_year']
            with readonly(annual_path(year)) as db:
                raw=db.execute(f'SELECT EFTOTLM,EFTOTLW,EFTOTLT FROM EF{year}A WHERE UNITID=130794 AND EFALEVEL=2').fetchone()
            gender='women' if 'women' in row['measure'].lower() else 'men' if 'men' in row['measure'].lower() else 'total'
            expected=raw[{'men':0,'women':1,'total':2}[gender]]
            if want_percent:expected=expected/raw[2]*100
            checks.append({'year':year,'measure':row['measure'],'value':row['value'],'expected':expected,'passed':row['value'] is not None and abs(row['value']-expected)<1e-9})
        case.update(checks=checks,passed=len(rows)==(20 if want_percent else 30) and {r['observation_year'] for r in rows}==set(range(2015,2025)) and all(c['passed'] for c in checks))
        if label=='counts':history.append({'question':q,'answer':answer})
    except Exception as exc:case.update(passed=False,error_type=type(exc).__name__,error=str(exc))
    case['test_wall_seconds']=time.perf_counter()-started;cases.append(case)
    (ROOT/'evaluations/enrollment_gender_latency.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cases':cases,'scope':'Live configured model for institution/context resolution; gender plans use exact source evidence. Server answer-ready excludes independent SQL checks and browser paint. Small sample, not a latency guarantee.'},indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in case.items() if k not in {'answer','checks'}},indent=2),flush=True)
    print(json.dumps({k:case.get('answer',{}).get(k) for k in ['intent','message','resolved_question','latency']},indent=2),flush=True)
sys.exit(not all(c['passed'] for c in cases))
