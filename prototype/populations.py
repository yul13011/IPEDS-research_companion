"""Code-backed directory populations for aggregate queries; no model SQL."""
import re
from .catalog import readonly,annual_path

US_FIPS=[1,2,4,5,6,8,9,10,11,12,13,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,44,45,46,47,48,49,50,51,53,54,55,56]

def aggregate_question(question):
    if re.search(r'\bunited states (?:university|military academy|naval academy|air force academy|coast guard academy|merchant marine academy)\b',question,re.I) and not re.search(r'national|nationwide|all institutions|by sector',question,re.I):return False
    return bool(re.search(r'\bnational\b|nationwide|united states|(?-i:\bUS\b|\bU\.S\.)|all (?:IPEDS |postsecondary )?institutions|by sector|by state|across (?:all |public |private )?(?:institutions|colleges|universities)|\b(public|private|for.profit|not.for.profit) (?:four.year |4.year |two.year |2.year )?(?:institutions|colleges|universities)\b|\bstatewide\b',question,re.I))

def default_population(**changes):
    return dict({'fips':US_FIPS[:],'controls':[],'levels':[],'degree_granting':None,
                 'title_iv':True,'administrative_offices':False},**changes)


# F-D: a plain count of institutions is answered from the directory population itself
# (populations.select(...)['directory_count']), not a measure aggregate. Trigger only on
# a bare institution headcount; anything with a measure, a per-category feature filter, a
# named institution, or a geography/scope the population guard rejects falls through to the
# normal pipeline (so we never turn a filtered question into a national count).
_COUNT_RE=re.compile(r'\b(?:how many|number of|count of)\b',re.I)
_UNIT_RE=re.compile(r'\binstitutions?|colleges?|universities\b',re.I)
_MEASURE_RE=re.compile(r'enroll|students?|undergrad|graduat|degrees?|\bawards?\b|complet|faculty|staff|applicants?|admit|admission|salar|retention|\baid\b|\bgrants?\b|scholarship|tuition|revenue|expenses?|\brate\b|percent',re.I)
_FEATURE_RE=re.compile(r'\boffer|offering|provid|\bwith\b|that have|accredit|religious|affiliat|\bHBCU\b|tribal|online|distance|women|men[- ]only|historically|\breport\b.*\bon\b',re.I)

def institution_count_question(question):
    q=question or ''
    if not (_COUNT_RE.search(q) and _UNIT_RE.search(q)):return False
    # "degree-granting" is a population scope, not a measure ("degree") or feature ("grant").
    scope_q=re.sub(r'degree[\s-]granting','',q,flags=re.I)
    if _MEASURE_RE.search(scope_q) or _FEATURE_RE.search(scope_q) or re.search(r'\b\d{6}\b',q):return False
    return True

def requested_count_year(question):
    years=[int(y) for y in re.findall(r'\b(20[12]\d)\b',question)]
    return max(years) if years else 2024

def population_from_question(question):
    q=question;p=default_population()
    controls=[]
    if re.search(r'\bpublic\b',q,re.I):controls.append(1)
    if re.search(r'nonprofit|not.for.profit',q,re.I):controls.append(2)
    elif re.search(r'for.profit',q,re.I):controls.append(3)
    elif re.search(r'\bprivate\b',q,re.I):controls=[2,3]
    p['controls']=sorted(set(controls))
    levels=[]
    if re.search(r'\b(?:four|4)[\s-]year\b',q,re.I):levels.append(1)
    if re.search(r'less.than.(?:two|2)[\s-]year',q,re.I):levels.append(3)
    elif re.search(r'\b(?:two|2)[\s-]year\b',q,re.I):levels.append(2)
    p['levels']=sorted(set(levels))
    if re.search(r'degree[\s-]granting',q,re.I):p['degree_granting']=True
    return p

def institution_count(question):
    """Return a bare institution-headcount answer, or None to fall through."""
    year=requested_count_year(question)
    pop=population_from_question(question)
    try:
        validate_request(pop,question,year)
        resolved=select(pop,year)
    except ValueError:
        return None
    scope=resolved['label']+(' · degree-granting' if pop['degree_granting'] else '')
    msg=(f"{resolved['directory_count']:,} institutions reported to IPEDS in the "
         f"{year}–{str(year+1)[-2:]} collection within this scope: {scope}. "
         "This counts distinct reporting institutions (directory file HD"+str(year)+") after "
         "the population filters; by default Title IV participation is required and "
         "administrative/central offices are excluded. Name a state, sector or level to narrow it.")
    return {'intent':'analyze','mode':'institution count','message':msg,
            'institution_count':{'year':year,'count':resolved['directory_count'],'scope':scope,
                                 'filters':resolved['filters'],'code_evidence':resolved['code_evidence'],
                                 'directory_sql':resolved['directory_sql'],'parameters':resolved['parameters']},
            'model_usage':{'calls':0,'estimated_api_usd':0}}

def select(population,year):
    from analysis_catalog.catalog import connection
    p=population
    if not p['fips'] or len(set(p['fips']))!=len(p['fips']):raise ValueError('Choose explicit, distinct source geography codes.')
    if len(p['fips'])>60 or len(p['controls'])>3 or len(p['levels'])>3:raise ValueError('Population filter bounds exceeded.')
    if any(x not in {1,2,3} for x in p['controls']+p['levels']):raise ValueError('Invalid control or institution-level code.')
    filters={'FIPS':p['fips'],'PSET4FLG':[1,3] if p['title_iv'] else [1,2,3,4,5,6]}
    if p['controls']:filters['CONTROL']=p['controls']
    if p['levels']:filters['ICLEVEL']=p['levels']
    if p['degree_granting'] is not None:filters['DEGGRANT']=[1 if p['degree_granting'] else 2]
    if not p['administrative_offices']:filters['SECTOR']=list(range(1,10))
    evidence=[]
    with connection() as db:
        for field,values in filters.items():
            codes=[dict(r) for r in db.execute('SELECT record_id,code_value,value_label FROM source.code_values WHERE release_id LIKE ? AND table_name=? COLLATE NOCASE AND variable_name=?',(f'IPEDS_{year}%',f'HD{year}',field)) if r['code_value'] in set(map(str,values))]
            if {c['code_value'] for c in codes}!=set(map(str,values)):raise ValueError('Population category has no exact annual codebook evidence: '+field)
            evidence.append({'field':field,'codes':codes})
    where=[];params=[]
    for field,values in filters.items():
        where.append('"'+field+'" IN ('+','.join('?' for _ in values)+')');params.extend(values)
    sql=f'SELECT UNITID,INSTNM FROM "HD{year}" WHERE '+' AND '.join(where)
    with readonly(annual_path(year)) as db: rows=db.execute(sql,params).fetchall()
    if not rows:raise ValueError('No reporting institutions match the requested population in '+str(year))
    return {'unitids':[r['UNITID'] for r in rows],'label':label(p),'directory_sql':sql,'parameters':params,
            'directory_count':len(rows),'code_evidence':evidence,'year':year,'filters':p}

def label(p):
    geo='United States' if set(p['fips'])==set(US_FIPS) else 'Selected states/areas'
    control=', '.join({1:'public',2:'private nonprofit',3:'private for-profit'}[c] for c in p['controls'])
    level=', '.join({1:'four-year',2:'two-year',3:'less-than-two-year'}[c] for c in p['levels'])
    return geo+(' · '+control if control else '')+(' · '+level if level else '')+(' · Title IV' if p['title_iv'] else '')

def validate_request(p,question,year):
    """Independent literal-scope checks; model labels do not establish coverage."""
    q=question.lower()
    from .catalog import ALIASES
    from .workflows import institution_index
    names=set(ALIASES)|{n for item in institution_index().values() for n in item['names']}
    if re.search(r'\b\d{6}\b',question) or any(name.lower() in q and re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',question,re.I) for name in names):
        raise ValueError('A named institution was requested alongside a population. This population-only plan cannot replace both scopes; request the aggregate separately or clarify which comparison to construct.')
    controls=[]
    if re.search(r'\bpublic\b',q):controls.append(1)
    if re.search(r'\bprivate\b|nonprofit|not.for.profit|for.profit',q):
        controls.extend([2] if re.search(r'nonprofit|not.for.profit',q) else [3] if re.search('for.profit',q) else [2,3])
    if controls and set(controls)!=set(p['controls'] or [1,2,3]):raise ValueError('Population control codes do not match the requested public/private scope.')
    levels=[v for pattern,v in [(r'\b(?:four|4).year (?:postsecondary )?(?:institutions|colleges)',1),(r'(?<!than )(?<!than-)\b(?:two|2).year (?:postsecondary )?(?:institutions|colleges)',2),(r'less.than.(?:two|2).year',3)] if re.search(pattern,q)]
    if levels and set(levels)!=set(p['levels']):raise ValueError('Population institution levels do not match the request.')
    from analysis_catalog.catalog import connection
    with connection() as db:
        states=[int(r['code_value']) for r in db.execute('SELECT code_value,value_label FROM source.code_values WHERE release_id LIKE ? AND table_name=? AND variable_name=?',(f'IPEDS_{year}%',f'HD{year}','FIPS')) if re.search(r'\b'+re.escape(r['value_label'].lower())+r'\b',q)]
    if states and set(states)!=set(p['fips']):raise ValueError('Population geography does not match the explicitly named state/area.')
    if not states and re.search(r'national|united states|nationwide|\bUS\b',question,re.I) and set(p['fips'])!=set(US_FIPS):raise ValueError('National scope requires all 50 states and DC unless another geography is explicit.')


# ===== merged from population_annual.py (consolidation) =====
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


# ===== merged from population_review.py (consolidation) =====
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
