"""Explicit optional live API smoke test. Never prints credentials/provider errors."""
from pathlib import Path
import sys,json,datetime,time
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root));sys.path.insert(0,str(root/'.packages'))
from prototype.agent import ask,DEFAULT_MODEL

cases=[
 ('Yale applicants, admits and admission rate for class of 2028 entering fall 2024','analyze',{'applicants','admits','admission_rate'}),
 ('How many matriculated in that year and what was the yield rate?','analyze',{'matriculants','yield_rate'}),
 ('What data do we have on faculty?','discover',set()),
 ('What percentage of Yale College students were on financial aid in 2024?','clarify',set()),
 ('Plot Yale six-year graduation rate for entering cohorts 2009 through 2018','analyze',{'graduation_rate'}),
]
records=[];previous=None
for question,intent,metrics in cases:
    started=time.perf_counter()
    try:
        answer=ask(question,previous,use_model=True)
        ok=answer['intent']==intent
        if intent=='analyze':
            ok=ok and metrics.issubset(set(answer.get('plan',{}).get('metrics',[])))
            if 'class of' in question:
                rows={r['metric']:r for r in answer['result']['rows']}
                ok=ok and rows.get('applicants',{}).get('value')==57517 and rows.get('admits',{}).get('value')==2227
            if 'cohorts' in question:
                ok=ok and sorted(answer['result']['observation_years'])==list(range(2015,2025))
            if answer.get('plan'):previous=answer['plan']
        if intent=='discover':ok=ok and bool(answer.get('evidence'))
        record={'question':question,'expected_intent':intent,'actual_intent':answer['intent'],'passed':bool(ok),
                'plan':answer.get('plan'),'message':answer.get('message'),'evidence_records':len(answer.get('evidence',[])),
                'latency':answer.get('latency')}
    except Exception as exc:
        record={'question':question,'passed':False,'error_type':type(exc).__name__}
    record['test_wall_seconds']=time.perf_counter()-started
    records.append(record)
    print(json.dumps({k:v for k,v in record.items() if k not in {'message'}},ensure_ascii=False),flush=True)
report={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model':DEFAULT_MODEL,
        'passed':sum(r['passed'] for r in records),'total':len(records),'cases':records,
        'scope':'Five live planner smoke cases only; not comprehensive natural-language reliability certification.'}
(root/'evaluations/prototype_live_smoke.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
sys.exit(0 if all(r['passed'] for r in records) else 1)
