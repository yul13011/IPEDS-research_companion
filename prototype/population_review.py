"""Known benchmark discrepancies block only their exact aggregate method/scope.

New source-backed questions still use the general validator. This is not a list
of permitted questions or values. No expected statistical answers enter execution.
"""
from contextvars import ContextVar
from hashlib import sha256
from pathlib import Path
import json

EVALUATING=ContextVar('population_benchmark_evaluation',default=False)
POLICY=Path(__file__).with_name('population_benchmark_guards.json')

def fingerprint(plan):
    from analysis_catalog.catalog import connection
    from .query_engine import signed_allowed
    refs={};contexts={}
    with connection() as db:
        for s in plan['sources']:
            ids=set(s['field_record_ids']+s['group_by_record_ids']+[f['record_id'] for f in s['filters']])
            ids|={rid for a in s['aggregates'] for rid in [a['record_id'],a['weight_record_id']] if rid is not None}
            docs={rid:dict(db.execute('SELECT * FROM source.variable_docs WHERE record_id=?',(rid,)).fetchone()) for rid in ids}
            filters=sorted([[docs[f['record_id']]['variable_name'].upper(),f['operator'],sorted(f['values'])] for f in s['filters']
                if not(f['operator']=='gte' and f['values']==['0'] and not signed_allowed(docs[f['record_id']]))])
            contexts[s['id']]=[s['year'],s['table'].upper(),filters,sorted(docs[r]['variable_name'].upper() for r in s['group_by_record_ids'])]
            if s.get('reconcile_distance_partition'):contexts[s['id']].append('verified distance partition zeros')
            for rid,d in docs.items():refs[f"f{s['id']}_{rid}"]=['field',s['year'],s['table'].upper(),d['variable_name'].upper(),filters]
            for a in s['aggregates']:
                refs[f"a{s['id']}_{a['id']}"]=['source reducer',a['operator'],refs.get(f"f{s['id']}_{a['record_id']}"),refs.get(f"f{s['id']}_{a['weight_record_id']}")]
    for e in plan['expressions']:
        values=[refs.get(r,r) for r in e['inputs']]
        if e['operator'] in {'add','multiply'}:values=sorted(values,key=lambda v:json.dumps(v,sort_keys=True))
        refs['x'+e['id']]=[e['operator'],values,[refs.get(g,g) for g in e['group_by_references']]]
    population={k:sorted(v) if isinstance(v,list) else v for k,v in plan['population'].items()}
    joins=[[contexts[j['left_source']],contexts[j['right_source']],j['left_columns'],j['right_columns'],j['how'],j['cardinality'],j['period_alignment']] for j in plan['joins']]
    payload=[population,sorted(contexts.values(),key=lambda v:json.dumps(v,sort_keys=True)),joins,
             sorted([refs[o['reference']] for o in plan['outputs']],key=lambda v:json.dumps(v,sort_keys=True))]
    return sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()

def check(plan):
    if not plan.get('population') or EVALUATING.get() or not POLICY.exists():return
    guards=json.loads(POLICY.read_text(encoding='utf-8')).get('blocked',{})
    matches=[guards.get(fingerprint({**plan,'outputs':[out]})) for out in plan['outputs']]
    match=next((m for m in matches if m),None)
    if match:raise ValueError('This aggregate method for source year '+str(match['source_year'])+' has an unresolved difference from the NCES benchmark. It remains under review; no statistical result is published. Other validated periods and aggregate methods remain available.')
