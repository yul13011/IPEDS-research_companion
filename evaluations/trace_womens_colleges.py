"""Trace the owner's exact question through the production chat entry point."""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.agent import ask,DEFAULT_MODEL
from prototype.progress import reporting

if __name__=='__main__':
    question="how many women's colleges in the US"
    events=[];started=time.perf_counter()
    def progress(message):
        event={'seconds':time.perf_counter()-started,'message':message}
        events.append(event);print(json.dumps(event),flush=True)
    record={'question':question,'model':DEFAULT_MODEL,'fresh_conversation':True}
    try:
        with reporting(progress):
            record['answer']=ask(question,use_model=True,model=DEFAULT_MODEL)
    except Exception as exc:
        record.update(error_type=type(exc).__name__,error=str(exc))
    record.update(wall_seconds=time.perf_counter()-started,progress=events)
    target=ROOT/'evaluations'/('womens_colleges_gap_first_trace.json' if '--gap-first' in sys.argv else 'womens_colleges_app_trace.json')
    target.write_text(json.dumps(record,indent=2,default=str),encoding='utf-8')
    a=record.get('answer',{})
    print(json.dumps({k:a.get(k) for k in ['intent','mode','message','model_usage','latency']},default=str),flush=True)
    print(str(target),flush=True)
