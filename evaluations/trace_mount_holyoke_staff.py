"""Run the owner's exact question through the production chat entry point."""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.agent import ask,DEFAULT_MODEL

if __name__=='__main__':
    question='cost of Mount Holyoke College staff'
    started=time.perf_counter()
    try:
        answer=ask(question,use_model=True,model=DEFAULT_MODEL)
        report={'question':question,'model':DEFAULT_MODEL,'fresh_conversation':True,
                'wall_seconds':time.perf_counter()-started,'answer':answer}
    except Exception as exc:
        report={'question':question,'wall_seconds':time.perf_counter()-started,
                'error_type':type(exc).__name__,'error':str(exc)}
    path=ROOT/'evaluations/mount_holyoke_staff_trace.json'
    path.write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    print(str(path),flush=True)
    print(json.dumps({k:v for k,v in report.items() if k!='answer'}),flush=True)
    if 'answer' in report:
        a=report['answer']
        print(json.dumps({k:a.get(k) for k in ['intent','message','mode','model_usage']},default=str),flush=True)
