"""Conservative automatic model selection; every executor keeps its validators."""
from contextvars import ContextVar
import time

AUTOMATIC='automatic'
DEFAULT_STRATEGY=AUTOMATIC
HAIKU='claude-haiku-5-5'
ACTIVE=ContextVar('automatic_model_policy',default=False)


def source_model(requested):
    from .agent import DEFAULT_MODEL
    return DEFAULT_MODEL if ACTIVE.get() else requested


def _deterministic_cost_answer(question,previous,history):
    """Answer current-year cost/tuition/price questions deterministically, above all stochastic
    routing, so they always return the complete, correct columns instead of sometimes clarifying
    or taking a different planner path. Returns None to fall through for anything cost_plan does
    not confidently handle (related-but-different questions, historical years, unresolved names)."""
    from .catalog_planner import cost_plan
    det=cost_plan(question,previous)
    if not det or not det.get('catalog_proposal'):return None
    from .catalog_execution import execute_catalog
    from .responses import finalize_answer
    from .conversation import from_history,update
    from .request_tasks import status
    answer=execute_catalog(det,question)
    if 'result' not in answer:return None   # a source/validation block: let the normal path try
    answer=finalize_answer(answer,question)
    answer['working_analysis']=update(from_history(history),answer,question,len(history or [])+1)
    answer['task_tracking']={'tasks':[{'id':'t1','request':question,'depends_on':[],'status':status(answer)}],
                             'complete':status(answer) in {'answered','unavailable','unsupported'}}
    answer.setdefault('model_usage',{'calls':0,'latency_seconds':0,'estimated_api_usd':0})
    return answer


def _deterministic_aid_answer(question,previous,history):
    """Answer current-year financial-aid / student-loan questions deterministically (full-time first-year
    default), above stochastic routing, so they return the complete grant/net-price/loan columns instead
    of clarifying. Returns None to fall through for anything aid_plan does not confidently handle."""
    from .catalog_planner import aid_plan,aid_narrative
    det=aid_plan(question,previous)
    if not det or not det.get('catalog_proposal'):return None
    from .catalog_execution import execute_catalog
    from .responses import finalize_answer
    from .conversation import from_history,update
    from .request_tasks import status
    answer=execute_catalog(det,question)
    if 'result' not in answer:return None
    answer=finalize_answer(answer,question)
    narrative=aid_narrative(answer.get('result',{}).get('rows',[]))
    if narrative:answer['custom_message']=answer['message']=narrative   # grouped panel; custom_message survives re-finalize
    answer['working_analysis']=update(from_history(history),answer,question,len(history or [])+1)
    answer['task_tracking']={'tasks':[{'id':'t1','request':question,'depends_on':[],'status':status(answer)}],
                             'complete':status(answer) in {'answered','unavailable','unsupported'}}
    answer.setdefault('model_usage',{'calls':0,'latency_seconds':0,'estimated_api_usd':0})
    return answer


def _deterministic_debt_deflection(question,previous,history):
    """Intercept student-debt / debt-at-graduation / loan-default questions with an honest scope note
    (IPEDS reports aid awarded per year, not debt owed or default — that is College Scorecard), above
    all routing so they never get tuition or awarded-loan figures. Returns None when not applicable."""
    from .catalog_planner import scorecard_deflection
    ans=scorecard_deflection(question,previous)
    if ans is None:return None
    from .conversation import from_history,update
    from .request_tasks import status
    ans['working_analysis']=update(from_history(history),ans,question,len(history or [])+1)
    ans['task_tracking']={'tasks':[{'id':'t1','request':question,'depends_on':[],'status':status(ans)}],'complete':True}
    ans.setdefault('model_usage',{'calls':0,'latency_seconds':0,'estimated_api_usd':0})
    return ans


def handle(question,previous,history,executor,*,overrides=None,institution_choices=None):
    from .agent import DEFAULT_MODEL
    from .intent_router import handle as dispatch,InterpretationError
    started=time.perf_counter();failed=[];router=HAIKU
    token=ACTIVE.set(True)
    try:
        answer=_deterministic_debt_deflection(question,previous,history)
        if answer is not None:
            router='deterministic scope note (debt/default)'
        elif (cost:=_deterministic_cost_answer(question,previous,history)) is not None:
            answer=cost;router='deterministic cost route'
        elif (aid:=_deterministic_aid_answer(question,previous,history)) is not None:
            answer=aid;router='deterministic aid route'
        else:
            try:
                answer=dispatch(question,previous,HAIKU,history,executor,overrides,institution_choices)
            except InterpretationError as exc:
                # Retry only rejected/incomplete interpretation, before an executor ran.
                # Legitimate ambiguity/identity choices and source gaps are not retries.
                failed.append({'stage':'initial interpretation','reason':str(exc),'usage':exc.usage})
                router=DEFAULT_MODEL
                answer=dispatch(question,previous,DEFAULT_MODEL,history,executor,overrides,institution_choices)
    finally:ACTIVE.reset(token)
    usage=dict(answer.get('model_usage',{}))
    for attempt in failed:
        for key in ['calls','latency_seconds','estimated_api_usd','input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens']:
            usage[key]=(usage.get(key,0) or 0)+(attempt['usage'].get(key,0) or 0)
    usage['model']=AUTOMATIC
    if usage.get('usage_complete') is False:usage['estimated_api_usd']=None
    usage['stages']=[a['usage'] for a in failed]+usage.get('stages',[])
    answer['model_usage']=usage
    answer['model_policy']={'strategy':'conservative automatic','router_model':router,
        'reviewed_planner_model':router,'catalog_planner_model':DEFAULT_MODEL,
        'discovery_writer_model':DEFAULT_MODEL,'interpretation_retries':failed,
        'limits':'Model selection is not an accuracy guarantee. Source and chart validators remain mandatory.'}
    answer['latency']={**answer.get('latency',{}),'answer_ready_seconds':time.perf_counter()-started,'live_model_calls':usage.get('calls',0)}
    if answer.get('result') and answer.get('mode')!='presentation adjustment':answer['result']['latency']=dict(answer['latency'])
    return answer
