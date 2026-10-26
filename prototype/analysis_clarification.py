"""Source-bound analytical choices and session-only clarification state.

The model proposes choices; the ordinary query validator approves their structure.
Selecting a choice never asks a model to reconstruct its query.
"""
from copy import deepcopy
from hashlib import sha256
import json
import re
from .query_schema import QUERY_SCHEMA, obj, array, STRING

OPTION_SCHEMA = obj({'id': {'type':'string','enum':['A','B','C']},
    'label':STRING, 'interpretation':STRING, 'qualifications':array(STRING), 'plan':QUERY_SCHEMA})
OPTION_SCHEMA['properties']['additional_analyses']=array(obj({'label':STRING,'interpretation':STRING,
    'qualifications':array(STRING),'plan':QUERY_SCHEMA}))
CLARIFICATION_SCHEMA = obj({'question':STRING, 'goal':STRING, 'options':array(OPTION_SCHEMA)})
ANALYSIS_SCHEMA=obj({'label':STRING,'interpretation':STRING,'qualifications':array(STRING),'plan':QUERY_SCHEMA})
BUNDLE_SCHEMA=obj({'goal':STRING,'analyses':array(ANALYSIS_SCHEMA)})


def preflight(analysis,qualifications=()):
    from .query_engine import inspect
    for k in ['label','interpretation']:
        if not analysis[k].strip() or len(analysis[k])>2000:raise ValueError('Each panel needs a concise complete interpretation.')
    if len(analysis['qualifications'])>6 or any(not q.strip() or len(q)>1000 for q in analysis['qualifications']):raise ValueError('Keep panel qualifications concise.')
    plan=deepcopy(analysis['plan'])
    plan['assumptions']=list(dict.fromkeys(plan['assumptions']+list(qualifications)+analysis['qualifications']))
    checked=inspect(plan,analysis['interpretation'])
    if not plan.get('annual_years'):plan=checked['plan']
    return {**deepcopy(analysis),'plan':plan,'evidence':{'definitions':list(checked['definitions'].values()),
        'categories':checked['evidence']['category_evidence'],'catalog_identity':checked['evidence']['catalog_identity']}}


def prepare(payload, question, usage=None, optional_proxy=False):
    """Metadata preflight every offered option; never retrieve statistical values."""
    import jsonschema
    jsonschema.validate(payload, CLARIFICATION_SCHEMA)
    if not (1 if optional_proxy else 2) <= len(payload['options']) <= 3:raise ValueError('Offer two or three distinct source-backed choices, or one to three optional proxies after a coverage gap.')
    if not optional_proxy and re.search(r'\bprox(?:y|ies)\b',json.dumps(payload),re.I):
        raise ValueError('Use report_coverage_gap for proxy alternatives. Explain the original coverage limitation first; proxies are optional, not equivalent definitions.')
    if len({o['id'] for o in payload['options']}) != len(payload['options']):raise ValueError('Choice IDs must be unique.')
    if any(not payload[k].strip() or len(payload[k]) > 1000 for k in ['question','goal']):raise ValueError('Keep the clarification concise.')
    choices=[]
    for option in payload['options']:
        if any(not option[k].strip() or len(option[k]) > 2000 for k in ['label','interpretation']):raise ValueError('Each choice needs a concise label and complete interpretation.')
        if len(option['qualifications']) > 6 or any(not q.strip() or len(q)>1000 for q in option['qualifications']):raise ValueError('Keep consequential qualifications concise.')
        if len(option.get('additional_analyses',[]))>2:raise ValueError('Use at most three separate analyses per option.')
        prepared=[]
        for analysis in [option]+option.get('additional_analyses',[]):
            prepared.append(preflight(analysis,option['qualifications']))
        prepared[0]['additional_analyses']=prepared[1:]
        choices.append(prepared[0])
    # Choosing a measure must not silently choose a different institution/year scope.
    scope=lambda o:json.dumps({k:o['plan'].get(k) for k in ['institutions','population','source_years','annual_years']},sort_keys=True)
    if len({scope(a) for o in choices for a in [o]+o['additional_analyses']})!=1:raise ValueError('Keep institution and year scopes identical across measure choices; ask separately about ambiguous dates or institutions.')
    brief={'version':1,'status':'pending','goal':payload['goal'],'original_question':question,
        'question':payload['question'],'options':choices,'selected_option':None,
        'confirmed_decisions':[],'open_questions':[payload['question']]}
    brief['id']=sha256(json.dumps(brief,sort_keys=True).encode()).hexdigest()[:16]
    message=payload['question']+'\n\n'+'\n\n'.join(
        '**'+o['id']+'. '+o['label']+'**\n\n'+o['interpretation']+
        ('\n\n'+ ' '.join(o['qualifications']) if o['qualifications'] else '') for o in choices)
    answer={'intent':'clarify','message':message,'analysis_brief':brief,'mode':'source-backed clarification'}
    if usage:answer['model_usage']=usage
    return answer


def prepare_bundle(payload,question,usage=None):
    """Finish an already specified multi-panel request without asking again."""
    import jsonschema
    jsonschema.validate(payload,BUNDLE_SCHEMA)
    if not 2<=len(payload['analyses'])<=3:raise ValueError('Use two or three separate panels.')
    panels=[preflight(a) for a in payload['analyses']]
    institutions=[json.dumps(p['plan'].get('institutions'),sort_keys=True) for p in panels]
    if len(set(institutions))!=1:raise ValueError('Panel institutions must match the requested comparison scope.')
    option={**panels[0],'id':'confirmed',
        'label':payload['goal'],'additional_analyses':panels[1:],
        'qualifications':list(dict.fromkeys(q for p in panels for q in p['qualifications']))}
    brief=draft(question,{})
    brief.update(status='ready',goal=payload['goal'],options=[option],open_questions=[])
    answer={'intent':'analysis_bundle','message':'Prepared separate source-bound analyses.','analysis_bundle':option,'analysis_brief':brief,'mode':'source-bound multi-panel plan'}
    if usage:answer['model_usage']=usage
    return answer


def latest(history):
    answer=(history or [{}])[-1].get('answer',{})
    if answer.get('analysis_brief'):return answer['analysis_brief']
    briefs=[t['answer']['analysis_brief'] for t in answer.get('task_results',[]) if t.get('answer',{}).get('analysis_brief')]
    pending=[b for b in briefs if b.get('status') in {'pending','failed'}]
    return pending[0] if len(pending)==1 else None if pending else briefs[-1] if briefs else None


def scope(plan):
    """Facts from the validated plan, never an inferred answer from chat prose."""
    if not plan:return {}
    return {'institutions':plan.get('institutions',[]),'population':plan.get('population'),
        'years':plan.get('annual_years') or plan.get('source_years') or plan.get('years',[]),
        'measures':plan.get('outputs') or plan.get('metrics',[]),
        'breakdowns':[s.get('group_by_record_ids',[]) for s in plan.get('sources',[])],
        'time_basis':plan.get('time_basis') or plan.get('requested_time'),
        'assumptions':plan.get('assumptions',[])}


def draft(question,answer):
    plan=answer.get('catalog_plan') or answer.get('plan') or answer.get('result',{}).get('catalog_plan') or answer.get('result',{}).get('plan')
    return {'version':1,'id':sha256(question.encode()).hexdigest()[:16],
        'status':'completed' if answer.get('result') else 'awaiting_information',
        'goal':question,'original_question':question,'question':answer.get('message',''),
        'scope':scope(plan),'options':[],'selected_option':None,'confirmed_decisions':[],
        'open_questions':[] if answer.get('result') else [answer.get('message','')]}


def select(question, history):
    """Only exact selections/ordinals retry a saved plan. Modified choices replan."""
    brief=latest(history)
    if not brief or brief['status'] not in {'pending','failed'}:return None
    text=question.strip().casefold().strip('.!? ')
    match=re.fullmatch(r'(?:i (?:choose|want)|use|choose|select|try)?\s*(?:(?:option|(?:optional )?proxy)\s*)?\(?([abc123])\)?',text)
    ordinal={'first':'A','first option':'A','the first one':'A','second':'B','second option':'B','the second one':'B','third':'C','third option':'C','the third one':'C'}
    selected=(match[1].upper() if match else ordinal.get(text))
    if selected and selected.isdigit():selected=chr(64+int(selected))
    if text in {'retry','try again','run it','run that','continue'} and brief['status']=='failed':selected=brief.get('selected_option')
    if selected:
        option=next((o for o in brief['options'] if o['id']==selected),None)
        return (deepcopy(brief),deepcopy(option)) if option else (deepcopy(brief),None)
    return None


def execute_selection(brief, option):
    from .query_engine import proposal_answer, execute_answer
    if option is None:return {'intent':'clarify','message':'Please choose one of the displayed options, or describe the change you want.','analysis_brief':brief}
    brief.update(selected_option=option['id'],status='failed',open_questions=[],
        confirmed_decisions=[{'option':option['id'],'interpretation':option['interpretation'],'qualifications':option['qualifications']}])
    brief['scope']=[scope(a['plan']) for a in [option]+option.get('additional_analyses',[])]
    try:
        answers=[execute_answer(proposal_answer(a['plan'],a['interpretation']),a['interpretation']) for a in [option]+option.get('additional_analyses',[])]
        blocked=[a for a in answers if not a.get('result')]
        answer=blocked[0] if blocked else answers[0]
        if not blocked and len(answers)>1:
            answer['related_analyses']=answers[1:]
            for a,part in zip(answers[1:],option['additional_analyses']):
                a['message']=part['label']+'. '+' '.join(part['qualifications'])
                a['result']['warnings']=list(dict.fromkeys(a['result'].get('warnings',[])+option['qualifications']+part['qualifications']))
    except (ValueError, RuntimeError) as exc:
        answer={'intent':'clarify','message':'Your choice is saved, but execution could not complete. '+str(exc)+' You can retry or revise the request.','mode':'clarification execution limitation'}
    if answer.get('result'):
        brief['status']='completed'
        answer['result']['warnings']=list(dict.fromkeys(answer['result'].get('warnings',[])+option['qualifications']))
        answer['message']='Using '+option['label']+'.'+(' '+' '.join(option['qualifications']) if option['qualifications'] else '')
    else:
        answer['message']=answer.get('message','Execution could not complete.')+' Your selected definition is saved. You can retry or revise it.'
    answer['analysis_brief']=brief
    answer['resolved_question']=brief['original_question'] if option['id']=='confirmed' else option['interpretation']
    answer['model_usage']={'calls':0,'latency_seconds':0,'estimated_api_usd':0,'stage':'saved clarification selection'}
    return answer


def summary(brief):
    if not brief:return None
    return {**{k:v for k,v in brief.items() if k!='options'},'options':[
        {k:v for k,v in o.items() if k not in {'plan','evidence','additional_analyses'}} |
        {'source_scope':{'institutions':o['plan']['institutions'],'years':o['plan'].get('annual_years') or o['plan']['source_years'],
            'tables':[s['table'] for a in [o]+o.get('additional_analyses',[]) for s in a['plan']['sources']],
            'outputs':[out for a in [o]+o.get('additional_analyses',[]) for out in a['plan']['outputs']]}}
        for o in brief['options']]}
