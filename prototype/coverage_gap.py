"""Explain source limitations before optional, independently validated proxies."""
from copy import deepcopy
from .query_schema import obj,array,STRING
from .analysis_clarification import OPTION_SCHEMA,prepare,draft

GAP_SCHEMA=obj({'missing_information':STRING,'explanation':STRING,
    'status':{'type':'string','enum':['coverage_gap','unresolved_definition','incomplete_search']},
    'options':array(OPTION_SCHEMA)})


def prepare_gap(payload,question,usage=None,inspections=()):
    import jsonschema
    jsonschema.validate(payload,GAP_SCHEMA)
    if not inspections:raise ValueError('Inspect the supplied catalog before reporting a coverage limitation.')
    for key in ['missing_information','explanation']:
        if not payload[key].strip() or len(payload[key])>800:raise ValueError('Keep the coverage explanation concise and specific (at most 800 characters per field).')
    if len(payload['options'])>3:raise ValueError('Offer at most three optional proxies.')
    if payload['status']=='incomplete_search' and payload['options']:
        raise ValueError('Incomplete retrieval is not a confirmed coverage gap; do not replace the request with proxies.')
    lead={'coverage_gap':"I can’t answer the original question reliably from the supplied sources inspected.",
          'unresolved_definition':"The supplied source definitions do not yet establish the requested meaning.",
          'incomplete_search':"I couldn’t complete the source check, so I can’t determine whether the supplied data cover this question."}[payload['status']]
    explanation=lead+' '+payload['explanation'].strip()
    gap={k:deepcopy(payload[k]) for k in ['missing_information','explanation','status']}
    gap['source_inspections']=deepcopy(list(inspections));gap['source_policy']='Owner-supplied sources only'
    options=deepcopy(payload['options'])
    if options:
        qualification='Optional proxy only: this measures a different concept and does not answer the original question.'
        for option in options:
            option['qualifications']=list(dict.fromkeys([qualification]+option['qualifications']))
        answer=prepare({'goal':question[:1000],'question':explanation,'options':options},question,usage,optional_proxy=True)
        answer['message']=explanation+'\n\nOptional alternatives, only if useful. These do not answer the original question; nothing has been calculated.\n\n'+'\n\n'.join(
            '**'+o['id']+'. '+o['label']+'**\n\n'+o['interpretation']+'\n\n'+' '.join(o['qualifications']) for o in answer['analysis_brief']['options'])
        answer['analysis_brief'].update(coverage_gap=gap,open_questions=[])
    else:
        answer={'intent':'clarify','message':explanation,'analysis_brief':draft(question,{'message':explanation})}
        answer['analysis_brief'].update(status='coverage_gap',coverage_gap=gap,open_questions=[])
        if usage:answer['model_usage']=usage
    answer.update(coverage_gap=gap,mode='source coverage limitation')
    return answer
