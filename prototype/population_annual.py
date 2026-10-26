"""Independent annual queries, with actual per-release field binding."""
from copy import deepcopy
from hashlib import sha256
import json,time,re

def annual_plans(plan):
    from analysis_catalog.catalog import connection
    from analysis_catalog.build import normalize_text
    years=plan['annual_years']
    if not (plan.get('population') or 1<=len(plan.get('institutions',[]))<=30) or len(plan['source_years'])!=1 or not 1<=len(years)<=10 or len(set(years))!=len(years) or any(type(y)is not int or not 2015<=y<=2024 for y in years):
        raise ValueError('Annual templates need named institutions or an explicit population, one source release and 1–10 distinct available annual releases.')
    seedyear=plan['source_years'][0];output=[]
    with connection() as db:
        for year in years:
            result=deepcopy(plan);result.pop('annual_years');result['source_years']=[year];refs={}
            for s in result['sources']:
                if s['year']!=seedyear:raise ValueError('Annual templates cannot join across years.')
                original=db.execute('SELECT family FROM tables WHERE year=? AND table_name=? COLLATE NOCASE',(seedyear,s['table'])).fetchone()
                if not original:raise ValueError('Unknown seed table.')
                candidates=[r[0] for r in db.execute('SELECT table_name FROM tables WHERE year=? AND family=?',(year,original[0]))]
                # Documented split/combined transitions. Physical-location conflicts
                # remain blocked by the normal field ownership validator.
                if not candidates and s['table'].upper().startswith('SFA'):
                    candidates=[f'SFA{str(year-1)[2:]}{str(year)[2:]}'+('_P1' if year<2024 else '')]
                if not candidates and (s['table'].upper().startswith('COST1_') or s['table'].upper().startswith('IC') and s['table'].upper().endswith('_AY')):
                    candidates=[f'Cost1_{year}' if year==2024 else f'IC{year}_AY']
                if len(candidates)!=1:raise ValueError(f'Annual table binding missing or ambiguous in {year}.')
                table=candidates[0]
                ids=set(s['field_record_ids']+s['group_by_record_ids']+[f['record_id'] for f in s['filters']])
                ids|={rid for a in s['aggregates'] for rid in [a['record_id'],a['weight_record_id']] if rid is not None}
                mapping={}
                for rid in ids:
                    old=db.execute('SELECT * FROM source.variable_docs WHERE record_id=?',(rid,)).fetchone()
                    new=db.execute('SELECT * FROM source.variable_docs WHERE release_id LIKE ? AND table_name=? COLLATE NOCASE AND variable_name=? COLLATE NOCASE',(f'IPEDS_{year}%',table,old['variable_name'])).fetchall()
                    if len(new)!=1:raise ValueError(f"Annual field evidence unavailable in {year}: {old['variable_name']}.")
                    new=new[0]
                    if normalize_text(old['title'],seedyear)!=normalize_text(new['title'],year):raise ValueError('Annual field title changed; inspect the exact release rather than assuming comparability.')
                    mapping[rid]=new['record_id'];refs[f"f{s['id']}_{rid}"]=f"f{s['id']}_{new['record_id']}"
                s.update(year=year,table=table,field_record_ids=[mapping[r] for r in s['field_record_ids']],group_by_record_ids=[mapping[r] for r in s['group_by_record_ids']])
                for f in s['filters']:
                    oldlabels=[r[0] for r in db.execute('SELECT value_label FROM source.code_values WHERE record_id IN ('+','.join('?' for _ in f['code_record_ids'])+') ORDER BY code_value',f['code_record_ids'])] if f['code_record_ids'] else []
                    f['record_id']=mapping[f['record_id']];f['code_record_ids']=[]
                    field=db.execute('SELECT variable_name FROM definitions WHERE record_id=?',(f['record_id'],)).fetchone()
                    codes=[r for r in db.execute('SELECT record_id,code_value,value_label FROM source.code_values WHERE release_id LIKE ? AND table_name=? COLLATE NOCASE AND variable_name=? COLLATE NOCASE ORDER BY code_value',(f'IPEDS_{year}%',table,field[0])) if r['code_value'] in f['values']]
                    if oldlabels and [normalize_text(x,seedyear) for x in oldlabels]!=[normalize_text(r['value_label'],year) for r in codes]:raise ValueError('Annual category label changed or is absent.')
                    f['code_record_ids']=[r['record_id'] for r in codes]
                for a in s['aggregates']:
                    for k in ['record_id','weight_record_id']:
                        if a[k] is not None:a[k]=mapping[a[k]]
            for e in result['expressions']:
                e['inputs']=[refs.get(r,r) for r in e['inputs']];e['group_by_references']=[refs.get(r,r) for r in e['group_by_references']]
            for o in result['outputs']:o['reference']=refs.get(o['reference'],o['reference'])
            output.append(result)
    return output

def execute_annual(plan,question):
    from .query_engine import execute
    from .intent_checks import CURRENT,check_plan,stamp
    start=time.perf_counter();results=[];contract=CURRENT.get();token=CURRENT.set(None)
    try:
        for annual in annual_plans(plan):results.append(execute(annual,re.sub(r'\b(?:19|20)\d{2}\b','',question)))
    finally:CURRENT.reset(token)
    merged=deepcopy(results[0]);merged['catalog_plan']=plan
    for key in ['rows','sources','query_audit','join_validation']:
        merged[key]=[item for r in results for item in r[key]]
    merged['warnings']=list(dict.fromkeys(w for r in results for w in r['warnings']))
    merged['definitions']={k:v for r in results for k,v in r['definitions'].items()}
    merged['metric_specs']={k:v for r in results for k,v in r['metric_specs'].items()}
    merged['population_evidence']={k:v for r in results for k,v in r['population_evidence'].items()}
    merged['plan'].update(metrics=list(merged['metric_specs']),years=plan['annual_years'])
    merged['observation_years']=sorted(plan['annual_years'])
    merged['coverage']={'requested_cells':len(merged['rows']),'available_cells':sum(r['status']=='ok' for r in merged['rows'])}
    merged['latency']={'validation_and_query_seconds':time.perf_counter()-start}
    check=check_plan(plan,question,{'definition_evidence':[d for r in results for d in r['catalog_evidence']['definition_evidence']],
        'output_units':[r['unit'] for r in merged['rows']]})
    merged['result_id']=sha256(json.dumps(merged,sort_keys=True).encode()).hexdigest()[:16]
    return stamp(merged,check)
