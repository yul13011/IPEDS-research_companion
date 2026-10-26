"""Cheap, conservative purpose routing before source or institution investigation.

Only complete conversational messages are intercepted. Unknown messages retain
the established investigative path; this is not a keyword gate on analysis.
"""
import re


def prepare(question):
    if not isinstance(question,str) or not 1<=len(question)<=4000:
        raise ValueError('Enter a question of at most 4,000 characters.')
    q=question.strip()
    if direct(q) is not None:return q
    # Strip a greeting only when separated from an actual request. Never strip
    # analytical words or bare option letters, which may select saved plans.
    q=re.sub(r'^(?:hi|hello|hey|good morning|good afternoon|good evening)[!,.:;\s]+', '', q, flags=re.I) or q
    q=re.sub(r'^(?:thanks|thank you)[!,;:]\s*','',q,flags=re.I) or q
    q=re.sub(r'^(?:(?:can|could|would) you\s+)(?:please\s+)?(?=(?:show|compare|define|explain|list|find|plot|calculate|tell)\b)','',q,flags=re.I)
    return q


def direct(question):
    q=question.strip().rstrip('.!?').strip().casefold()
    if re.fullmatch(r'(?:hi|hello|hey|good morning|good afternoon|good evening)(?: there)?|how are you(?: doing)?',q):
        message='Hello! What would you like to explore in the supplied IPEDS data?'
        kind='greeting'
    elif re.fullmatch(r'(?:thanks|thank you|thank you very much|thanks a lot)(?: for (?:that|the explanation|your help|clarifying))?',q):
        message="You're welcome."
        kind='acknowledgment'
    elif re.fullmatch(r'(?:help|what can you do|how (?:do i|can i) use (?:this|the) app|what (?:can i ask|questions can i ask)(?: you)?)',q):
        message=('I can explain definitions and labels, describe available data, look up school attributes, '
                 'find institutions matching source categories, and compare numerical measures across schools or releases. '
                 'For example: “What does Pell mean?”, “What student services does Smith College offer?”, '
                 'or “Compare undergraduate enrollment at Smith and Wellesley.” '
                 'I use the supplied IPEDS data and codebooks. If they cannot answer a question, I explain the coverage gap first.')
        kind='app_help'
    else:return None
    return {'intent':'conversation','mode':'conversation','message':message,
            'purpose':{'kind':kind,'method':'local complete-message match'},
            'model_usage':{'calls':0,'estimated_api_usd':0},'latency':{'live_model_calls':0}}


def source_context(conversation):
    # Social turns do not replace the last structured source antecedent.
    return [item for item in conversation or [] if item.get('answer',{}).get('mode')!='conversation']


def mixed(question):
    """Split explicit documentation-then-analysis requests, never arbitrary ands.

    Unrecognized compounds stay intact for the general planner. In particular,
    'difference between X and Y' is not split.
    """
    match=re.fullmatch(r'(.+?)[,;]?\s+(?:and|then|and then|also)\s+((?:show|plot|count|calculate|compare|give|how many|how much)\b.+)',question,re.I)
    if not match:return None
    from .documentation import classify
    if classify(match[1]):return match[1].rstrip(',; '),match[2]
    return None


# ===== merged from capabilities.py (consolidation) =====
"""Executable application capabilities shared by interpretation and coverage."""
CHART_TYPES=('line','bar','none')


def describe():
    return {'charts':{'line':'Line charts for numerical series',
        'bar':'Horizontal bars, including grouped comparisons',
        'none':'Tables or numerical answers without a chart'},
        'scope':'Only the data loaded in this app; no external data retrieval.',
        'task_limit':6,'coverage':'Loaded releases, reviewed measures and source-documented fields; reported values are a separate check.'}


def answer(requested=''):
    supported=requested in CHART_TYPES if requested else True
    message='I can produce line charts and horizontal bar charts, including grouped bars, or show a table.'
    if requested and not supported:message='The requested chart type ('+requested+') is not supported. '+message
    return {'intent':'capability','mode':'application capabilities','message':message,
        'capability':{'requested_chart':requested,'supported':supported,**describe()}}
