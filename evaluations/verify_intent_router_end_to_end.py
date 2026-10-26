"""Small live source-backed smoke through the actual new dispatcher."""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.intent_router import handle
from prototype.institution_confirmation import ask
from prototype.agent import DEFAULT_MODEL
from prototype.analytics import execute,Plan
from prototype.responses import finalize_answer

def main():
    if '--live' not in sys.argv:raise SystemExit('Pass --live to make provider requests.')
    records=[];history=[]
    for label,q in [('definition','What does admission rate mean?'),
                    ('discovery','What data do you have on faculty?'),
                    ('numerical','Show Yale University admission rate in fall 2024.'),
                    ('followup','What about Harvard University in fall 2023?'),
                    ('categorical','What student services does Smith College offer, such as academic counseling, career placement, and on-campus childcare?')]:
        start=time.perf_counter();record={'case':label,'question':q}
        try:
            previous=next((i['answer'] for i in reversed(history) if i['answer'].get('result')),None)
            answer=handle(q,previous,DEFAULT_MODEL,history,ask)
            if answer.get('result'):answer=finalize_answer(answer,q)
            record.update(answer=answer,passed=answer.get('intent') not in {'clarify','institution_confirmation'})
            if label in {'numerical','followup','categorical'}:record['passed']&=bool(answer.get('result'))
            if label=='followup':record['passed']&=all(r['observation_year']==2023 and r['unitid']==166027 for r in answer.get('result',{}).get('rows',[]))
            if label=='definition':record['passed']&=bool(answer.get('evidence'))
            if label=='discovery':record['passed']&=answer.get('mode')=='data discovery'
            history.append({'question':q,'answer':answer})
        except Exception as exc:record.update(passed=False,error_type=type(exc).__name__,error=str(exc)[:500])
        record['wall_seconds']=round(time.perf_counter()-start,3);records.append(record)
        (ROOT/'evaluations/intent_router_end_to_end.json').write_text(json.dumps({'model':DEFAULT_MODEL,'passed':sum(r['passed'] for r in records),'total':len(records),'cases':records},indent=2),encoding='utf-8')
        print(json.dumps({k:record[k] for k in ['case','passed','wall_seconds']}|{'route':record.get('answer',{}).get('intent_interpretation',{}).get('route'),'intent':record.get('answer',{}).get('intent'),'error':record.get('error')}),flush=True)
    return 0 if all(r['passed'] for r in records) else 1

if __name__=='__main__':raise SystemExit(main())
