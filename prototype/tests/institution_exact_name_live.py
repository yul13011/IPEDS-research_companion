"""Live institution-resolution replay: full official name versus shorthand."""
from pathlib import Path
import datetime,json,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.institution_confirmation import ask
from prototype.catalog import annual_path,readonly
from prototype.result_text import visible_warnings

cases=[]
for question,expect_confirmation in [('how many students does Mount Holyoke College have? Show 10-year trend.',False),('how many students does Mount Holyoke have? Show 10-year trend.',True)]:
    started=time.perf_counter();case={'question':question}
    try:
        answer=ask(question,use_model=True);case['answer']=answer
        if expect_confirmation:
            unresolved=answer.get('institution_confirmation',{}).get('unresolved',[])
            case['passed']=answer['intent']=='institution_confirmation' and len(unresolved)==1 and unresolved[0]['candidates']==[166939] and 'result' not in answer
        else:
            rows=answer.get('result',{}).get('rows',[]);checks=[]
            for row in rows:
                year=row['observation_year']
                with readonly(annual_path(year)) as db:
                    expected=db.execute(f'SELECT EFTOTLT FROM EF{year}A WHERE UNITID=166939 AND EFALEVEL=1').fetchone()[0]
                checks.append({'year':year,'value':row['value'],'expected_total_enrollment':expected,'passed':row['unitid']==166939 and row['value']==expected})
            case['checks']=checks
            case['visible_warnings']=visible_warnings(answer['result']) if answer.get('result') else []
            case['passed']=answer['intent']=='analyze' and len(checks)==10 and {c['year'] for c in checks}==set(range(2015,2025)) and all(c['passed'] for c in checks) and not any('separate' in w.lower() for w in case['visible_warnings'])
    except Exception as exc:case.update(passed=False,error_type=type(exc).__name__,error=str(exc))
    case['test_wall_seconds']=time.perf_counter()-started;cases.append(case)
    (ROOT/'evaluations/institution_exact_name_live.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cases':cases,'scope':'Live exact-name and shorthand replay. Answer-ready excludes browser paint and independent source checks. Original session input/extraction state is unavailable; this does not establish the exact trigger of the reported historical prompt.'},indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in case.items() if k!='answer'},indent=2),flush=True)
    print(json.dumps({k:case.get('answer',{}).get(k) for k in ['intent','message','latency']},indent=2),flush=True)
sys.exit(not all(c['passed'] for c in cases))
