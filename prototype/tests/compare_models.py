"""Same live planner cases for Sonnet/Haiku; records usage, not credentials."""
from pathlib import Path
import sys,json,datetime
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'.packages'))
from prototype.agent import ask,MODEL_LABELS

CASES=[
 ('Yale applicants, admits and admission rate for class of 2028 entering fall 2024','analyze',{'applicants','admits','admission_rate'}),
 ('How many matriculated in that year and what was the yield rate?','analyze',{'matriculants','yield_rate'}),
 ('What data do we have on faculty?','discover',set()),
 ('What percentage of Yale College students were on financial aid in 2024?','clarify',set()),
 ('Plot Yale six-year graduation rate for entering cohorts 2009 through 2018','analyze',{'graduation_rate'}),
 ('Give me applicants and admission rates for Yale, Harvard, and Princeton from 2015 through 2024','analyze',{'applicants','admission_rate'}),
 ('What percentage of Yale undergraduates received grants or scholarships in 2023–24?','analyze',{'undergraduate_grant_percent'})
]

def evaluate(model):
    records=[];previous=None
    for q,intent,metrics in CASES:
        try:
            answer=ask(q,previous,True,model)
            passed=answer['intent']==intent
            if intent=='analyze' and answer.get('result'):
                passed=passed and metrics<=set(answer['plan']['metrics'])
                rows=answer['result']['rows']
                if 'class of' in q:passed=passed and next((r['value'] for r in rows if r['metric']=='applicants'),None)==57517
                if 'cohorts' in q:passed=passed and answer['result']['observation_years']==list(range(2015,2025))
                if 'Princeton' in q:passed=passed and len({r['unitid'] for r in rows})==3 and answer['result']['observation_years']==list(range(2015,2025))
                if '2023–24' in q:passed=passed and answer['result']['observation_years']==[2024]
                previous=answer['plan']
            elif intent=='analyze':passed=False
            if intent=='discover':passed=passed and bool(answer.get('evidence'))
            record={'question':q,'passed':bool(passed),'expected_intent':intent,'actual_intent':answer['intent'],'plan':answer.get('plan'),'usage':answer.get('model_usage')}
        except Exception as exc:record={'question':q,'passed':False,'error_type':type(exc).__name__,'status_code':getattr(exc,'status_code',None)}
        records.append(record)
        print(json.dumps({'model':model,**record},ensure_ascii=False),flush=True)
    return {'model':model,'passed':sum(r['passed'] for r in records),'total':len(records),'estimated_api_usd':sum((r.get('usage') or {}).get('estimated_api_usd',0) for r in records),'cases':records}

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(evaluate,MODEL_LABELS))
    report={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'models':results,'scope':'Seven live functional planner cases per model, not a comprehensive accuracy estimate. Token usage includes cache behavior; pricing estimates exclude provider adjustments.'}
    (ROOT/'evaluations/prototype_model_comparison.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    sys.exit(0 if all(r['passed']==r['total'] for r in results) else 1)
