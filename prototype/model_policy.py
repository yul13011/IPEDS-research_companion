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


def handle(question,previous,history,executor,*,overrides=None,institution_choices=None):
    from .agent import DEFAULT_MODEL
    from .intent_router import handle as dispatch,InterpretationError
    started=time.perf_counter();failed=[];router=HAIKU
    token=ACTIVE.set(True)
    try:
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
