"""Session-derived analytical subject and verified artifact, never model facts."""
from copy import deepcopy
import re


def results(answer):
    """All visible results, including independently tracked question answers."""
    if answer.get('result'):yield answer
    for task in answer.get('task_results',[]):
        yield from results(task.get('answer',{}))
    for child in answer.get('related_analyses',[]):yield from results(child)


def plan_for(answer):
    result=answer.get('result',{})
    return (result.get('observation_plan') or result.get('catalog_plan') or
            answer.get('observation_plan') or answer.get('catalog_plan') or result.get('plan') or answer.get('plan'))


def population_signature(plan):
    if not plan:return {}
    filters=plan.get('filters',[]) + [f for s in plan.get('sources',[]) for f in s.get('filters',[])]
    ids={f['record_id'] for f in filters}
    names={}
    if ids:
        from analysis_catalog.catalog import connection
        with connection() as db:
            names={r[0]:re.sub(r'(?:19|20)\d{2}','{year}',r[2])+'.'+r[1] for r in db.execute('SELECT record_id,variable_name,table_name FROM definitions WHERE record_id IN ('+','.join('?' for _ in ids)+')',list(ids))}
    signature={}
    for f in filters:
        name=names.get(f['record_id'],str(f['record_id']))
        op=f.get('operator','eq')
        value=['domain' if op in {'eq','in'} else op,sorted(set(map(str,f.get('values',[]))))]
        signature.setdefault(name,[])
        if value not in signature[name]:signature[name].append(value)
    population=deepcopy(plan.get('population'))
    if population:
        for key in ['fips','controls','levels']:
            if key in population:population[key]=sorted(set(population[key]))
    return {'directory_population':population,
            'selectors':{k:sorted(v) for k,v in sorted(signature.items())}}


def quantity_fields(plan):
    """Source quantity lineage of published outputs, not unused selections."""
    if not plan:return []
    ids=set()
    if plan.get('metrics'):
        from .analytics import measures
        registry=measures()
        for metric in plan['metrics']:
            for year in plan.get('years',[]):
                observation=year+6 if plan.get('time_basis')=='entry_cohort' else year-4 if plan.get('time_basis')=='class' else year
                ids.update(registry.get(metric,{}).get('annual',{}).get(str(observation),{}).get('definition_record_ids',[]))
    elif plan.get('version')==1 and 'selections' in plan:
        if plan.get('calculations'):
            for calc in plan['calculations']:
                ids.update(calc['input_record_ids'])
                if calc.get('denominator_record_id'):ids.add(calc['denominator_record_id'])
        else:ids.update(s['record_id'] for s in plan['selections'] if s['role']=='measure')
    else:
        lineage={}
        for src in plan.get('sources',[]):
            sid=src['id'] if 'id' in src else ''
            for rid in src.get('field_record_ids',[])+src.get('group_by_record_ids',[]):lineage['f'+sid+'_'+str(rid)]={rid}
            for aggregate in src.get('aggregates',[]):
                lineage['a'+sid+'_'+aggregate['id']]={r for r in [aggregate.get('record_id'),aggregate.get('weight_record_id')] if r is not None}
        for expression in plan.get('expressions',[]):
            lineage['x'+expression['id']]=set().union(*(lineage.get(ref,set()) for ref in expression['inputs']))
        for output in plan.get('outputs',[]):ids.update(lineage.get(output['reference'],set()))
    if not ids:return []
    from analysis_catalog.catalog import connection
    with connection() as db:
        return sorted({re.sub(r'(?:19|20)\d{2}','{year}',r['table_name'])+'.'+r['variable_name']
            for r in db.execute('SELECT d.table_name,d.variable_name,v.format FROM definitions d JOIN source.variable_docs v USING(record_id) WHERE record_id IN ('+','.join('?' for _ in ids)+')',list(ids)) if r['format']=='Cont'})


def subject_for(answer,question=''):
    plan=deepcopy(plan_for(answer) or {})
    result=answer.get('result',{})
    ids=list(dict.fromkeys(r['unitid'] for r in result.get('rows',[]) if r.get('unitid') is not None))
    if not ids and plan.get('institutions'):
        from .institution_confirmation import resolve
        from .catalog import IVY
        for name in plan['institutions']:
            if str(name).casefold() in {'ivy','ivy league','ivies'}:ids.extend(IVY)
            else:
                uid=resolve(str(name),{})
                if uid is not None:ids.append(uid)
    fields=[s['record_id'] for s in plan.get('selections',[]) if s.get('role')=='measure']
    fields+= [rid for s in plan.get('sources',[]) for rid in s.get('field_record_ids',[])]
    return {'question':question,'plan':plan,'measure_ids':list(plan.get('metrics',[])),
        'field_record_ids':list(dict.fromkeys(fields)),
        'institutions':list(map(str,ids)) or list(plan.get('institutions',[])),
        'periods':list(plan.get('years') or plan.get('source_years') or result.get('observation_years',[])),
        'time_basis':plan.get('time_basis','observation'),
        'population_signature':population_signature(plan),'quantity_fields':quantity_fields(plan)}


def update(state,answer,question='',turn=None):
    state=deepcopy(state)
    lookup=answer.get('definition_lookup') or {}
    if lookup.get('status')=='defined':
        metric=lookup.get('reviewed_measure')
        fields=[r['record_id'] for r in answer.get('evidence',[]) if r.get('kind')=='variable_definition']
        state['subject']={'question':question,'plan':{},'measure_ids':[metric] if metric else [],
            'field_record_ids':[] if metric else fields,'institutions':[],
            'periods':lookup.get('source_years',[]),'time_basis':'observation' if metric else 'source_release',
            'population_signature':{},'topic':lookup.get('term','')}
    elif answer.get('mode')=='data discovery':
        state['subject']={'question':question,'plan':{},'measure_ids':[],'field_record_ids':[],
            'institutions':[],'periods':[],'time_basis':'source_release','population_signature':{},'topic':answer.get('query','')}
    coverage=answer.get('coverage')
    if coverage:
        state['last_coverage']=deepcopy(coverage)
        if coverage.get('scope'):
            state['subject']=deepcopy(coverage['scope'])
    for child in results(answer):
        if not child['result'].get('result_id'):continue
        subject=subject_for(child,child.get('resolved_question') or question)
        state['subject']=subject
        state['artifact']={'result_id':child['result']['result_id'],'turn':turn,'subject':subject}
    return state


def from_history(history):
    state={'version':1,'subject':None,'artifact':None,'last_coverage':None}
    for i,item in enumerate(history or [],1):
        answer=item.get('answer',{})
        if answer.get('working_analysis'):
            state=deepcopy(answer['working_analysis'])
            if state.get('artifact') and state['artifact'].get('turn') is None:state['artifact']['turn']=i
        else:state=update(state,answer,item.get('question',''),i)
    if state.get('artifact'):
        rid=state['artifact']['result_id']
        positions=[i for i,item in enumerate(history or [],1) if any(a['result'].get('result_id')==rid for a in results(item.get('answer',{})))]
        if positions:state['artifact']['turn']=positions[-1]
        else:state['artifact']=None
    return state


def recent_result(history):
    for item in reversed(history or []):
        children=list(results(item.get('answer',{})))
        if children:return children[-1]
    return None


def prompt_context(state):
    """Keep exact execution plans in session state, bounded summaries in prompts."""
    from .memory import compact_plan
    compact=deepcopy(state)
    for subject in [compact.get('subject'),(compact.get('artifact') or {}).get('subject')]:
        if subject:
            subject['plan']=compact_plan(subject.get('plan'))
            fields=subject.get('field_record_ids',[])
            if len(fields)>40:
                subject['field_record_count']=len(fields);subject['field_record_ids']=fields[:40]
                subject['field_record_ids_bounded']=True
    coverage=compact.get('last_coverage')
    if coverage:
        compact['last_coverage']={k:coverage.get(k) for k in ['operation','time_basis','requested_periods','available_periods','requested_status','status','limits']}
    return compact


def validate_transition(previous,answer,changes):
    """Reject unrequested changes to independently verified execution scope."""
    if not previous or not answer.get('result') or answer.get('mode')=='presentation adjustment':return
    current=subject_for(answer)
    if 'institutions' not in changes and previous.get('institutions') and set(current['institutions'])!=set(previous['institutions']):
        raise ValueError('The follow-up changed the institution scope without a requested institution change.')
    if 'period' not in changes and previous.get('periods') and set(current['periods'])!=set(previous['periods']):
        raise ValueError('The follow-up changed the reporting periods without a requested period change.')
    old=previous.get('population_signature') or {}
    new=current.get('population_signature') or {}
    if 'population' not in changes and old and old!=new:
        raise ValueError('The follow-up changed the source population or row selectors. The previous population has been preserved; no changed-scope result was published.')
    if not {'measure','period'}.intersection(changes) and not set(previous.get('quantity_fields',[]))<=set(current.get('quantity_fields',[])):
        raise ValueError('The follow-up dropped a previously requested source quantity/category. No incomplete replacement result was published.')
