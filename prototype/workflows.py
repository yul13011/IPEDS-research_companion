"""Reusable learning content and extract selection, independent of Streamlit."""
from functools import lru_cache
from pathlib import Path
import json
import re
import unicodedata
import pandas as pd
from .catalog import annual_path, readonly, IVY
from .analytics import Plan, execute, measures


def topics():
    return json.loads((Path(__file__).parent/'learning_content.json').read_text(encoding='utf-8'))['topics']


def example_by_id(example_id):
    for topic in topics():
        for example in topic['examples']:
            if example['id']==example_id:return example
    raise ValueError('Unknown example.')


def execute_example(example_id):
    from .catalog import search
    example=example_by_id(example_id)
    if example['kind']=='analyze':
        if example.get('observation_plan_key'):
            from .observations import answer
            plans=json.loads((Path(__file__).parent/'institution_example_plans.json').read_text(encoding='utf-8'))
            reviewed=answer(plans[example['observation_plan_key']],example['question'])
            reviewed['mode']='reviewed example'
            return reviewed
        if example.get('catalog_plan_key'):
            from .query_engine import execute as execute_query
            plans=json.loads((Path(__file__).parent/'faculty_example_plans.json').read_text(encoding='utf-8'))
            result=execute_query(plans[example['catalog_plan_key']],example['question'])
            result['plan']['output']='chart' if len(result['rows'])>1 else 'table'
        else:
            plan=Plan(**example['plan']);result=execute(plan)
        return {'intent':'analyze','plan':result['plan'],'result':result,'mode':'reviewed example',
                'message':'This example uses a predefined source-reviewed plan. Values were retrieved from the annual datasets.'}
    return {'intent':'discover','message':'This topic currently supports definition discovery. New statistical extracts need a reviewed plan.',
            'evidence':search(example['query'],limit=30),'mode':'codebook search'}


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(text)).lower() if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def institution_index():
    """Latest available label per UNITID, retaining prior names for name search."""
    index={}
    for year in range(2024,2014,-1):
        with readonly(annual_path(year)) as db:
            for row in db.execute(f'SELECT UNITID,INSTNM,CITY,STABBR FROM HD{year}'):
                unitid=int(row['UNITID'])
                if unitid not in index:
                    index[unitid]={'unitid':unitid,'name':row['INSTNM'],'city':row['CITY'] or '',
                                   'state':row['STABBR'] or '','latest_year':year,'names':[],'years':[]}
                item=index[unitid];item['years'].append(year)
                if row['INSTNM'] not in item['names']:item['names'].append(row['INSTNM'])
    return index


def institution_label(unitid):
    item=institution_index()[unitid]
    suffix=f" · last reported {item['latest_year']}" if item['latest_year']<2024 else ''
    return f"{item['name']} · {item['city']}, {item['state']} · UNITID {unitid}{suffix}"


def institution_matches(query,limit=30):
    q=normalized(query).strip()
    if not q:return []
    tokens=q.split();matched=[]
    for unitid,item in institution_index().items():
        names=[normalized(n) for n in item['names']]
        if q==str(unitid) or any(all(t in n for t in tokens) for n in names):
            rank=0 if q==str(unitid) or q in names else 1 if any(n.startswith(q) for n in names) else 2
            matched.append((rank,item['name'],unitid))
    return [x[2] for x in sorted(matched)[:limit]]


def measure_matches(query='',topic_id='all',limit=6):
    specs=measures();families=None
    if topic_id!='all':families=next(t['families'] for t in topics() if t['id']==topic_id)
    stop={'what','how','many','the','and','for','does','data','give','me','of','in','on','a','are','students'}
    tokens=[t for t in re.findall(r'[a-z0-9_]+',normalized(query)) if t not in stop]
    matches=[]
    for metric,spec in specs.items():
        if families is not None and spec['family'] not in families:continue
        identifiers=[metric]+spec['columns']+[a['table'] for a in spec['annual'].values()]
        direct=normalized(query).strip() in [normalized(x) for x in identifiers] if query.strip() else False
        title=normalized(spec['label']+' '+metric.replace('_',' '))
        body=title+' '+normalized(spec['definition']+' '+' '.join(identifiers)+' '+spec['family'])
        score=1000 if direct else sum(10 if t in title else 1 for t in tokens if t in body)
        if not tokens or score:
            matches.append((-score,spec['label'],metric))
    return [x[2] for x in sorted(matches)[:limit]]


def extract_plan(metric_ids,unitids,years,time_basis='observation'):
    # Do not resolve ambiguous text here: the UI only submits explicit UNITID choices.
    plan=Plan(list(metric_ids),[str(x) for x in unitids],list(years),time_basis,'export')
    plan.validate()
    return plan


def compatible_wide(result):
    """Optional one-row-per-institution/year extract, only for compatible populations."""
    specs=measures();metrics=result['plan']['metrics']
    families={specs[m]['family'] for m in metrics}
    if len(families)>1:
        raise ValueError('These measures use different source populations or periods. Download the detailed long-format table instead.')
    family=next(iter(families))
    if family in {'graduation','pell'}:
        # A wide extract is only offered within one explicit subgroup.
        prefixes={m.split('graduation_')[0] for m in metrics}
        if len(prefixes)>1:raise ValueError('These graduation measures use different subgroups. Keep them in the detailed long-format table.')
    frame=pd.DataFrame(result['rows'])
    keys=['institution','unitid','observation_year','reporting_period','release','provisional']
    wide=frame.pivot(index=keys,columns='metric',values='value').reset_index()
    statuses=frame.pivot(index=keys,columns='metric',values='status').reset_index()
    statuses=statuses.rename(columns={m:m+'__status' for m in metrics})
    return wide.merge(statuses,on=keys,validate='one_to_one').sort_values(['institution','observation_year'])
