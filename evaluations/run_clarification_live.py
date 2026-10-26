"""Opt-in live clarification evaluation; writes no credentials or source files."""
from pathlib import Path
import json,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.institution_confirmation import ask

OUT=ROOT/'evaluations/clarification_workflow'
OUT.mkdir(exist_ok=True)
history=[];report=[]
for index,question in enumerate([
    'How many ladder faculty does Southern Connecticut State University have, and what are their average salaries by academic rank?',
    'A',
]):
    start=time.perf_counter()
    try:
        answer=ask(question,use_model=True,conversation=history)
        history.append({'question':question,'answer':answer})
        (OUT/f'turn_{index+1}.json').write_text(json.dumps(answer,indent=2,default=str),encoding='utf-8')
        row={'question':question,'seconds':time.perf_counter()-start,'intent':answer['intent'],
            'message':answer.get('message'),'usage':answer.get('model_usage'),
            'brief_status':answer.get('analysis_brief',{}).get('status'),
            'rows':answer.get('result',{}).get('rows',[])}
    except Exception as exc:
        row={'question':question,'seconds':time.perf_counter()-start,'error':str(exc),'trace':traceback.format_exc()}
    report.append(row)
    (OUT/'live_summary.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    print(json.dumps({k:v for k,v in row.items() if k not in {'rows','trace'}},default=str),flush=True)
    if index==0 and not history[-1]['answer'].get('analysis_brief'):break
