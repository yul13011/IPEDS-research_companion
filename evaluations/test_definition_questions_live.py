"""Live definition acceptance through the same outer entry point as the app."""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.institution_confirmation import ask
from prototype.agent import DEFAULT_MODEL

QUESTIONS=['What is the definition of instructional staff?', 'What does UNITID mean?',
           'Define graduation rate','How is full-time undergraduate enrollment defined?',
           'What is faculty?', 'What does SAL2023_IS.SAOUTLT mean?', 'What is admission rate?',
           'Define quantum banana index']

if __name__=='__main__':
    if '--live' not in sys.argv:raise SystemExit('Use --live for configured provider calls.')
    results=[]
    for q in ([QUESTIONS[2]] if '--graduation' in sys.argv else [QUESTIONS[6]] if '--reviewed-rate' in sys.argv else QUESTIONS):
        start=time.perf_counter();record={'question':q}
        try:
            a=ask(q,use_model=True,model=DEFAULT_MODEL)
            lookup={r['record_id']:r for r in a.get('evidence',[])}
            checks={'definition_route':a.get('mode')=='source definition','no_statistics':'result' not in a,
                    'exact_source_passages':all(p['excerpt'] in lookup[p['record_id']]['definition'] for p in a.get('definition_lookup',{}).get('passages',[]))}
            if 'quantum' in q:checks['bounded_unknown']=a.get('definition_lookup',{}).get('status')=='not_established'
            else:checks['definition_found']=a.get('definition_lookup',{}).get('status')=='defined'
            record.update(answer=a,checks=checks,passed=all(checks.values()))
        except Exception as exc:record.update(passed=False,error_type=type(exc).__name__,error=str(exc))
        record['wall_seconds']=time.perf_counter()-start;results.append(record)
        target='definition_questions_graduation_recheck.json' if '--graduation' in sys.argv else 'definition_questions_reviewed_rate_recheck.json' if '--reviewed-rate' in sys.argv else 'definition_questions_live_refined.json' if '--refined' in sys.argv else 'definition_questions_live.json'
        (ROOT/'evaluations'/target).write_text(json.dumps({'model':DEFAULT_MODEL,'cases':results},indent=2,default=str),encoding='utf-8')
        print(json.dumps({k:v for k,v in record.items() if k!='answer'}),flush=True)
    raise SystemExit(not all(r['passed'] for r in results))
