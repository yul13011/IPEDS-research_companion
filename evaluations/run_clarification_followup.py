from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.institution_confirmation import ask
OUT=ROOT/'evaluations/clarification_workflow'
h=[{'question':q,'answer':json.loads((OUT/f'turn_{i}.json').read_text(encoding='utf-8'))} for i,q in [
    (1,'How many ladder faculty does Southern Connecticut State University have, and what are their average salaries by academic rank?'),(2,'A')]]
question='Keep the same definitions, but combine the tenured and tenure-track counts and show only full professors.'
start=time.perf_counter()
answer=ask(question,previous=h[-1]['answer'].get('catalog_plan'),use_model=True,conversation=h)
(OUT/'turn_3.json').write_text(json.dumps(answer,indent=2,default=str),encoding='utf-8')
print(json.dumps({'question':question,'seconds':time.perf_counter()-start,'intent':answer['intent'],
    'message':answer.get('message'),'usage':answer.get('model_usage'),
    'rows':[r for a in [answer]+answer.get('related_analyses',[]) for r in a.get('result',{}).get('rows',[])]},default=str),flush=True)
