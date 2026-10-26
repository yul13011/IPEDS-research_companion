"""Replay the reported trend follow-up; record source scope and answer latency."""
from pathlib import Path
import sys,json,time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.institution_confirmation import ask
from prototype.agent import api_key
from prototype.responses import presentation_for
if not api_key():raise SystemExit('No model credential configured.')
history=[];records=[]
for q in ['how many students does mount holyoke have','Show a 10-year trend.','Show a longitudinal trend']:
    start=time.perf_counter()
    a=ask(q,use_model=True,conversation=history,institution_choices={'mount holyoke':166939})
    if a.get('intent')=='institution_confirmation':raise ValueError('Unexpected institution confirmation')
    result=a.get('result',{});p=a.get('presentation') or (presentation_for(result,q) if result else {})
    record={'question':q,'intent':a.get('intent'),'message':a.get('message'),'resolved_question':a.get('resolved_question'),
        'plan':a.get('catalog_plan') or a.get('plan') or result.get('plan'),'years':sorted({r['observation_year'] for r in result.get('rows',[])}),
        'unitids':sorted({r['unitid'] for r in result.get('rows',[])}),'chart_type':p.get('chart_type'),'rows':len(result.get('rows',[])),
        'answer_ready_seconds':time.perf_counter()-start,'latency':a.get('latency')}
    records.append(record);history.append({'question':q,'answer':a});print(json.dumps(record,ensure_ascii=True),flush=True)
(ROOT/'evaluations'/('trend_followup_live'+('_'+sys.argv[1] if len(sys.argv)>1 else '')+'.json')).write_text(json.dumps(records,indent=2),encoding='utf-8')
