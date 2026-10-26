"""Bounded request plans, dependency validation and an explicit outcome ledger."""
from copy import deepcopy
import json,re,time
from . import working_analysis as working

COVERAGE_SCHEMA={'type':'object','properties':{
    'operation':{'type':'string','enum':['none','check','periods','releases','overview','capabilities']},
    'measure_ids':{'type':'array','items':{'type':'string'}},
    'field_record_ids':{'type':'array','items':{'type':'integer'}},
    'institutions':{'type':'array','items':{'type':'string'}},'topic':{'type':'string'},
    'time_basis':{'type':'string','enum':['observation','entry_cohort','class','source_release','working']},
    'requested_years':{'type':'array','items':{'type':'integer'}},
    'inherit_working':{'type':'boolean'},'requested_chart':{'type':'string'}},
    'additionalProperties':False}
COVERAGE_SCHEMA['required']=list(COVERAGE_SCHEMA['properties'])
COVERAGE_SCHEMA['properties']['scope_mode']={'type':'string','enum':['context','explicit','dataset']}
COVERAGE_SCHEMA['required'].append('scope_mode')
CHANGES=['institutions','measure','population','period','calculation','presentation']


def schema(core):
    properties=deepcopy(core['properties'])
    properties.update({'id':{'type':'string'},'request':{'type':'string'},
        'depends_on':{'type':'array','items':{'type':'string'}},
        'binding':{'type':'string','enum':['new','working','referenced']},
        'subject_result_id':{'type':'string'},
        'changes':{'type':'array','items':{'type':'string','enum':CHANGES}},
        'period_selection':{'type':'string','enum':['as_requested','latest_available']},
        'coverage':COVERAGE_SCHEMA})
    task={'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    return {'type':'object','properties':{'tasks':{'type':'array','items':task}},'required':['tasks'],'additionalProperties':False}


INSTRUCTIONS='''
Return a REQUEST PLAN with tasks, not a single route. Use route_request once.
One integrated comparison of several measures may be one task. Separate distinct
questions/actions, including coverage, definitions, calculations, and chart requests.
Account for every part of the prompt. At most six tasks, in dependency order, IDs t1,
t2, ... . request must copy the exact original substring for that part (including
literal titles); question is its complete standalone interpretation. No sentence may
be silently omitted. If a part is unsupported or unclear, retain it as a task.
depends_on lists earlier task IDs whose facts or result are necessary. Independent
tasks continue when another task is unavailable. Never describe partial work as full.

For broad orientation such as what data or information are available, use route
coverage, operation=overview, scope_mode=dataset, inherit_working=false. Use the
data_guide_topics to select a topic, or empty topic for the whole beginner guide.
Do not require users to know a survey or variable name. For general years without
a bound analytical measure, use releases with empty topic and dataset scope; the
service distinguishes source releases from observation periods.
Discovery is for specific source tables, variables and available breakdowns, not for
general orientation or year availability. A previous discovery answer does not make
a year question another discovery task. If no exact measure/field is bound, answer
with qualified source-release coverage rather than unrelated table search results.

Use route coverage for whether data exist, available years/periods, earliest/latest,
or source releases. This is NOT broad topic discovery and NOT a statistical query.
coverage.operation=check for requested periods, periods for all available periods,
releases for the global release inventory. Select exact supplied measure_ids or
verified field_record_ids, or inherit_working=true for the current analytical subject.
For coverage/capability use institution_mentions=[]; put coverage institutions in
coverage.institutions (or inherit the verified working scope).
Coverage scope_mode=context is the default: a different requested year alone does
not clear the current institutions/population. A matching measure retains that scope.
Use explicit for expressly named coverage institutions, and dataset only when the
user explicitly requests dataset-wide coverage rather than the current analysis.
If the measure is not bound, provide topic and leave IDs empty; never invent IDs.
For inherited coverage use time_basis=working unless the user requests another basis.
For 'Which years do we have?' enumerate periods across the subject's sources: do not
retain the previously unavailable requested year as a filter. Distinguish fall dates,
release labels, cohort entry years and nominal class-of. Availability is LOCAL, never
a claim about everything IPEDS has published. Never answer source availability from
memory in conversation/clarify prose; the coverage service supplies the facts.
When working_analysis.subject has exact measure_ids or field_record_ids, a bare year
question refers to that subject by default: binding=working, inherit_working=true,
scope_mode=context, operation=periods, time_basis=working. For example, after a median
SAT result, do not answer with the entire database's release years. Only an explicit
request for the whole database clears that subject; declare changes=['measure'] when
doing so, scope_mode=dataset, operation=releases. Without a bound measure/field, the
global source-release inventory is appropriate. Preserve this distinction for 'you'
as well as 'we' in year questions.

Use route capability and coverage.operation=capabilities for chart/app capabilities.
For an unsupported requested chart, requested_chart names it; no chart_edits. Return
that task separately from any supported numerical/percentage request, which should
still execute. Current chart types are in application_capabilities. Do not invent a
capability or ask permission to perform an already requested supported calculation.

binding=working for follow-ups to the active working analysis, referenced for an
explicit earlier result, new for a fully specified independent question. Preserve
the working population, institution, period, row selectors and method except the
changes the USER requests. changes enumerates only those requested dimensions.
A counts-to-percentages request changes calculation, not graduate to undergraduate.
Use the most recent relevant verified result by default, not an earlier undergraduate
result when graduate enrollment is active. Unsupported requests and failed searches
do not replace the verified working result. Preserve explicitly selected earlier turns.
For binding=referenced, set subject_result_id to the verified earlier result ID;
each chart supplies its exact analytical scope. For other bindings leave it empty.
subject_result_id='task:t1' can reference a dependency's new result. Do not select
an earlier population merely because the requested operation is unsupported.

For an edit of a result produced by another task, target_result_id='task:t1' (its
actual producer ID), depends_on=['t1'], referenced_turns=[]. Other chart edits use
existing result IDs/turns. For an analysis explicitly requesting latest AVAILABLE
data use period_selection=latest_available and depend on a coverage task; do not
guess a year. It is not permission to replace an explicitly requested unavailable date.
For noncoverage/capability tasks use coverage.operation=none and empty lists/text,
time_basis=observation, inherit_working=false. For all other tasks use
period_selection=as_requested. Open tasks in working_analysis may be clarified by
later replies; do not rerun already answered parts unless the user requests it.
'''


def validate(plan,original,history,answers,core):
    import jsonschema
    from .intent_router import validate_decision,normalize_decision
    jsonschema.validate(plan,schema(core))
    tasks=plan['tasks']
    if not 1<=len(tasks)<=6:raise ValueError('Please limit a request to six distinct questions or actions.')
    if sum(len(t['question']) for t in tasks)>12000:raise ValueError('The request plan exceeds the bounded interpretation budget.')
    covered=[False]*len(original);seen=set();normalized=[];state=working.from_history(history)
    for i,t in enumerate(tasks,1):
        t=deepcopy(t)
        if t['id']!='t'+str(i) or not set(t['depends_on'])<=seen or len(set(t['depends_on']))!=len(t['depends_on']):
            raise ValueError('Task dependencies must refer to earlier, uniquely numbered tasks.')
        if not t['request'].strip() or t['request'] not in original:raise ValueError('Every task must retain its literal part of the original request.')
        start=0
        while (position:=original.find(t['request'],start))>=0:
            covered[position:position+len(t['request'])]=[True]*len(t['request']);start=position+len(t['request'])
        d=normalize_decision({k:deepcopy(t[k]) for k in core['properties']},t['request'])
        if t['binding']=='working':
            artifact=state.get('artifact') or {}
            if d['route']=='chart_edit' and not d['target_result_id'] and artifact.get('result_id') in answers:
                d['target_result_id']=artifact['result_id'];d['relationship']='followup'
            if d['relationship']=='followup' and not d['referenced_turns'] and history:
                d['referenced_turns']=[artifact.get('turn') or len(history)]
        if t['binding']=='referenced' and not t['subject_result_id'] and d['route']=='chart_edit' and d['target_result_id'] in answers:
            t['subject_result_id']=d['target_result_id']
        if t['binding']=='referenced' and t['subject_result_id'] in answers and not d['referenced_turns']:
            d['referenced_turns']=[j for j,item in enumerate(history or [],1) if any(a['result']['result_id']==t['subject_result_id'] for a in working.results(item.get('answer',{})))][-1:]
        if t['binding']=='referenced' and not t['subject_result_id']:raise ValueError('Identify the earlier analytical result to reuse.')
        if t['subject_result_id'] and not t['subject_result_id'].startswith('task:') and t['subject_result_id'] not in answers:raise ValueError('The referenced analytical result is unavailable.')
        if t['subject_result_id'].startswith('task:') and t['subject_result_id'][5:] not in t['depends_on']:raise ValueError('A new analytical subject must come from a declared dependency.')
        probe=deepcopy(d)
        if t['depends_on'] and not probe['referenced_turns'] and probe['relationship']=='followup':
            # Its antecedent may be a task that has not executed yet, rather
            # than an earlier chat turn. Bind that reference at execution.
            probe['relationship']='new'
        if t['depends_on'] and d['route']=='chart_edit':
            probe.update(route='mixed',relationship='new',referenced_turns=[],target_result_id='')
        validate_decision(probe,t['request'],history,answers)
        q=t['coverage']
        if len(q['measure_ids'])>12 or len(q['field_record_ids'])>40 or len(q['institutions'])>30 or len(q['requested_years'])>30 or len(q['topic'])>500:raise ValueError('Coverage request bounds exceeded.')
        if d['route']=='coverage' and q['operation'] not in {'check','periods','releases','overview'}:raise ValueError('Specify the coverage operation.')
        if d['route']=='capability' and q['operation']!='capabilities':raise ValueError('Specify the capability operation.')
        if d['route'] not in {'coverage','capability'} and q['operation']!='none':raise ValueError('Coverage parameters belong to a coverage task.')
        if q['operation']=='check' and not q['requested_years']:raise ValueError('Specify the periods whose availability should be checked.')
        subject=state.get('subject') or {}
        if (d['route']=='coverage' and q['operation'] in {'periods','releases'} and q['scope_mode']=='dataset'
                and not q['measure_ids'] and not q['field_record_ids']
                and (subject.get('measure_ids') or subject.get('field_record_ids')) and 'measure' not in t['changes']
                and not any(n['coverage']['operation']=='overview' for n in normalized)):
            raise ValueError('A bound analytical subject cannot be silently cleared for a year question. Inherit its coverage scope unless the user explicitly requests the whole database; only that explicit switch declares a measure change.')
        if t['period_selection']=='latest_available' and (not t['depends_on'] or d['route'] not in {'numerical','analysis','categorical','mixed'}):raise ValueError('Latest-available analysis requires a coverage dependency.')
        normalized.append({**t,**d});seen.add(t['id'])
    rest=''.join(' ' if covered[i] else c for i,c in enumerate(original))
    if any(w.casefold() not in {'and','also','then','please'} for w in re.findall(r'\w+',rest)):
        raise ValueError('The request plan did not account for every part of the prompt. No task was executed.')
    return {'tasks':normalized}


def status(answer):
    if answer.get('capability',{}).get('supported') is False:return 'unsupported'
    c=answer.get('coverage') or {}
    if c.get('status')=='inconclusive':return 'needs_clarification'
    if c.get('unavailable_periods'):return 'unavailable'
    if answer.get('definition_lookup',{}).get('status')=='not_established':return 'needs_clarification'
    if answer.get('mode')=='data discovery' and not answer.get('discovery',{}).get('topics'):return 'needs_clarification'
    if answer.get('intent') in {'clarify','institution_confirmation'}:
        return 'blocked' if answer.get('intent_validation') or answer.get('mode')=='intent validation' else 'needs_clarification'
    return 'answered'


def combine_usage(stages,model):
    result={'model':model,'stages':stages,'usage_complete':all(s.get('usage_complete',True) for s in stages)}
    for key in ['calls','latency_seconds','input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens']:
        result[key]=sum(s.get(key,0) or 0 for s in stages)
    result['estimated_api_usd']=sum(s.get('estimated_api_usd',0) or 0 for s in stages) if result['usage_complete'] else None
    return result


def execute(plan,original,previous,model,history,executor,usage,overrides=None,institution_choices=None):
    from .intent_router import dispatch,charts_context,SCHEMA
    from .coverage import answer as coverage_answer,CoverageQuestion
    from .purpose import answer as capability_answer
    started=time.perf_counter();state=working.from_history(history);virtual=list(history or []);outcomes=[];by_id={};task_turns={};stages=[usage]
    for task in plan['tasks']:
        answer=None;outcome=None
        dependencies=[by_id[k] for k in task['depends_on']]
        if any(d['status'] in {'failed','blocked','needs_clarification','unsupported'} for d in dependencies):
            answer={'intent':'clarify','message':'This part depends on an unresolved earlier part: '+', '.join(task['depends_on'])+'.'};outcome='blocked'
        try:
            d={k:deepcopy(task[k]) for k in SCHEMA['properties']}
            _,subject_answers=charts_context(virtual,overrides)
            subject_id=task['subject_result_id'];reference=None
            if subject_id.startswith('task:'):
                producer=by_id.get(subject_id[5:]);candidates=list(working.results(producer['answer'])) if producer else []
                if len(candidates)!=1:raise ValueError('The dependent analytical subject needs one verified result.')
                reference=candidates[0]
            elif subject_id:reference=subject_answers.get(subject_id)
            if reference and not d['referenced_turns']:
                rid=reference['result']['result_id']
                d['referenced_turns']=[i for i,item in enumerate(virtual,1) if any(a['result']['result_id']==rid for a in working.results(item.get('answer',{})))][-1:]
            task_state=state
            if reference:task_state={**state,'subject':working.subject_for(reference)}
            if answer is None and d['route']=='coverage':answer=coverage_answer(task['coverage'],task_state)
            elif answer is None and d['route']=='capability':answer=capability_answer(task['coverage']['requested_chart'])
            elif answer is None:
                if task['period_selection']=='latest_available':
                    choices=[set(o['answer'].get('coverage',{}).get('available_periods',[])) for o in dependencies if o['answer'].get('coverage')]
                    years=set.intersection(*choices) if choices else set()
                    if not years:raise ValueError('No jointly verified available period was established for this analysis.')
                    latest=max(years)
                    if re.search(r'\b(?:19|20)\d{2}\b',d['question']):raise ValueError('Latest-available analysis must not silently replace a stated year.')
                    basis=dependencies[-1]['answer']['coverage']['time_basis']
                    label={'entry_cohort':'entering cohort','class':'nominal class-of','source_release':'source release','observation':'observation'}[basis]
                    d['question']+=' Use the verified '+label+' year '+str(latest)+'.'
                charts,answers=charts_context(virtual,overrides)
                if reference:answers[reference['result']['result_id']]=reference
                target=d['target_result_id']
                if target.startswith('task:'):
                    producer=by_id.get(target[5:])
                    candidates=list(working.results(producer['answer'])) if producer else []
                    if len(candidates)!=1:raise ValueError('The dependent chart edit needs one unambiguous verified result.')
                    target=candidates[0]['result']['result_id'];d['target_result_id']=target
                if task['binding']=='working' and d['route']=='chart_edit' and not target:
                    target=(state.get('artifact') or {}).get('result_id');d['target_result_id']=target or ''
                if d['route']=='chart_edit' and target in answers:
                    d['referenced_turns']=[next(c['turn'] for c in charts if c['result_id']==target)];d['relationship']='followup'
                if d['relationship']=='followup' and not d['referenced_turns'] and task['depends_on']:
                    d['referenced_turns']=[task_turns[k] for k in task['depends_on']]
                if task['binding']=='working' and d['relationship']=='followup' and not d['referenced_turns'] and state.get('artifact'):
                    d['referenced_turns']=[state['artifact']['turn']]
                old_subject=working.subject_for(reference) if reference else state.get('subject') if task['binding']=='working' else None
                prior=working.recent_result(virtual) or previous
                if task['binding']=='working' and d['route']!='chart_edit' and not (state.get('subject') or {}).get('plan'):prior=None
                answer=dispatch(task['request'],prior,model,virtual,executor,d,{},answers,institution_choices,subject_answer=reference)
                if old_subject:
                    try:working.validate_transition(old_subject,answer,task['changes'])
                    except ValueError as exc:
                        exc.model_usage=answer.get('model_usage',{});raise
            outcome=outcome or status(answer)
            if d['route'] in {'numerical','categorical','analysis','mixed'} and outcome=='answered' and answer.get('mode')!='institution count' and not list(working.results(answer)):
                answer={**answer,'message':'This part did not produce a validated analytical result. '+answer.get('message','')}
                outcome='blocked'
        except CoverageQuestion as exc:
            answer={'intent':'clarify','mode':'source coverage','message':str(exc)};outcome='needs_clarification'
        except ValueError as exc:
            answer={'intent':'clarify','mode':'intent validation','message':str(exc),'model_usage':getattr(exc,'model_usage',{})};outcome='blocked'
        except Exception as exc:
            answer={'intent':'clarify','message':'This part could not finish because its source or model service was unavailable. Other independent parts are retained.',
                'error_type':type(exc).__name__,'model_usage':{'usage_complete':False}};outcome='failed'
        if answer.get('model_usage'):stages.append(answer['model_usage'])
        item={'id':task['id'],'request':task['request'],'depends_on':task['depends_on'],'status':outcome,'answer':answer}
        outcomes.append(item);by_id[item['id']]=item
        task_turns[item['id']]=len(virtual)+1
        state=working.update(state,answer,task['question'],len(virtual)+1)
        virtual.append({'question':task['question'],'answer':answer})
    created={a['result']['result_id'] for o in outcomes for a in working.results(o['answer'])}
    if state.get('artifact') and state['artifact']['result_id'] in created:state['artifact']['turn']=len(history or [])+1
    state['open_tasks']=[{'id':o['id'],'request':o['request'],'status':o['status'],
        'question':plan['tasks'][i]['question'],'route':plan['tasks'][i]['route'],
        'depends_on':o['depends_on']} for i,o in enumerate(outcomes) if o['status'] not in {'answered','unavailable','unsupported'}]
    ledger=[{k:v for k,v in o.items() if k!='answer'} for o in outcomes]
    if len(outcomes)==1:
        answer={**outcomes[0]['answer']}
        answer['intent_interpretation']={k:plan['tasks'][0][k] for k in SCHEMA['properties']}
        answer['intent_interpretation']['original_question']=original
    else:
        counts={s:sum(o['status']==s for o in outcomes) for s in dict.fromkeys(o['status'] for o in outcomes)}
        answer={'intent':'task_response','mode':'tracked request','message':'Request status: '+', '.join(str(n)+' '+s.replace('_',' ') for s,n in counts.items())+'.','task_results':outcomes}
    combined=combine_usage(stages,model)
    answer.update(task_tracking={'tasks':ledger,'all_parts_accounted_for':True,'complete':all(o['status'] in {'answered','unavailable','unsupported'} for o in outcomes)},
        request_plan=plan,working_analysis=state,model_usage=combined,
        latency={'answer_ready_seconds':time.perf_counter()-started+usage.get('latency_seconds',0),'live_model_calls':combined['calls']})
    return answer
