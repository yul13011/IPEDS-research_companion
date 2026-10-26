"""Route documentation questions before identity/statistical planning.

Conversation supplies references, never new source evidence. No model call is
needed to classify these common intents or resolve an unambiguous reference.
"""
import re
from . import definitions


def classify(question):
    if not isinstance(question,str) or not 1<=len(question)<=4000:return None
    q=question.strip().rstrip('?.!').strip()
    # A mixed request must reach the general planner intact.
    if re.search(r'\b(?:and|also|then)\s+(?:show|plot|count|calculate|compare|give|how many|how much)\b',q,re.I):return None
    patterns=[
        ('calculation',r'how (?:is|are|was|were)\s+(.+?)\s+(?:calculated|computed|derived)'),
        ('calculation',r'how do you\s+(?:calculate|compute)\s+(.+)'),
        ('calculation',r'(?:what is|explain|show me)\s+(?:the )?(?:formula|calculation|method)\s+(?:for|behind|of)\s+(.+)'),
        ('label',r'what does\s+(?:the\s+)?label\s+(.+?)\s+mean'),
        ('label',r'(?:explain|define)\s+(?:the\s+)?label\s+(.+)'),
        ('discovery',r'what (?:data|information|variables|tables)\s+(?:do you have|are available)\s+(?:on|about|for)\s+(.+)'),
        ('discovery',r'what (?:else|other data|other information)\s+do you have\s+(?:on|about|for)\s+(.+)'),
    ]
    for kind,pattern in patterns:
        m=re.fullmatch(pattern,q,re.I)
        if m:return {'kind':kind,'term':m[1].strip(' \"“”\'')}
    parsed=definitions.request(question)
    if parsed and definitions.can_answer(question):
        kind='label' if re.fullmatch(r'(?:this|that|the) label',parsed['term'],re.I) else 'definition'
        return {'kind':kind,'term':parsed['term']}
    if not parsed:
        for pattern in [r'(?:explain|help me understand)\s+(.+)',r'how (?:should|do) I interpret\s+(.+)',r'tell me what\s+(.+?)\s+means']:
            m=re.fullmatch(pattern,q,re.I)
            if m and not re.match(r'(?:why|how|whether)\b',m[1],re.I):
                return {'kind':'label','term':m[1].strip(' \"“”\'')}
    return None


def references(answer):
    """Only structured answer fields are eligible antecedents, not model prose."""
    lookup=answer.get('definition_lookup',{})
    if lookup.get('comparison'):return lookup.get('terms',[]),lookup.get('source_years',[])
    if lookup.get('term'):return [lookup['term']],lookup.get('source_years',[])
    if answer.get('documentation_context'):
        ctx=answer['documentation_context'];return ctx.get('terms',[]),ctx.get('source_years',[])
    if answer.get('mode')=='data discovery' and answer.get('query'):
        return [answer['query']],answer.get('discovery',{}).get('requested_release_years',[])
    result=answer.get('result',{})
    rows=result.get('rows',[])
    terms=list(dict.fromkeys(r['measure'] for r in rows if r.get('measure')))
    plan=result.get('plan') or answer.get('plan') or {}
    from .analytics import measures
    specs=measures()
    if not terms:terms=[specs[m]['label'] for m in plan.get('metrics',[]) if m in specs]
    years=plan.get('source_years') or plan.get('years') or []
    return terms,years


def handle(question,use_model=False,model=None,conversation=None,previous=None):
    from .category_documentation import handle as category_answer
    categorical=category_answer(question,conversation)
    if categorical is not None:return categorical
    parsed=classify(question)
    if not parsed and conversation:
        last=conversation[-1].get('answer',{})
        pending=last.get('documentation_context',{})
        if last.get('intent')=='clarify' and pending.get('kind'):
            match=next((t for t in pending.get('terms',[]) if definitions.normalized(t)==definitions.normalized(question)),None)
            if match:parsed={'kind':pending['kind'],'term':match}
            year=re.fullmatch(r'\s*((?:19|20)\d{2})[.!?\s]*',question)
            if year and int(year[1]) in pending.get('source_years',[]) and len(pending.get('terms',[]))==1:
                parsed={'kind':pending['kind'],'term':pending['terms'][0]+' in '+year[1]}
    if not parsed:return None
    kind=parsed['kind'];term=parsed['term'];years=[]
    pending=(conversation or [{}])[-1].get('answer',{}).get('documentation_context',{})
    if pending.get('kind')==kind and term in pending.get('terms',[]):years=pending.get('source_years',[])
    contextual=bool(re.fullmatch(r'(?:this|that|it|this label|that label|this measure|that measure|the measure|the label|these|those)',term,re.I))
    if contextual:
        last=(conversation or [{}])[-1].get('answer',{})
        terms,years=references(last)
        if kind in {'label','calculation'} and last.get('mode')=='data discovery':
            terms=list(dict.fromkeys(r['title'] for r in last.get('evidence',[]) if r.get('variable_name') and r.get('title')))
        if not terms and previous:
            terms,years=references({'plan':previous})
        if len(terms)!=1:
            choices=' Available labels: '+ '; '.join(terms[:8])+'.' if terms else ''
            return {'intent':'clarify','mode':'source definition',
                    'message':'Which label, measure, or topic do you mean?'+choices,
                    'documentation_context':{'kind':kind,'terms':terms,'source_years':years}}
        term=terms[0]
        if kind!='discovery' and len(years)>1:
            return {'intent':'clarify','mode':'source definition',
                    'message':'The earlier answer covers multiple source releases ('+', '.join(map(str,years))+'). Which release should I use to explain **'+term+'**? I will not assume definitions or calculations are unchanged across years.',
                    'documentation_context':{'kind':kind,'terms':[term],'source_years':years}}
    # Resolve a bare answer to an immediately pending documentation clarification.
    if kind=='discovery':
        from .discovery import overview
        effective='What data do you have on '+term
        if contextual and years:effective+=' in '+ ' and '.join(map(str,years))
        result=overview(effective,use_model=use_model,model=model)
    else:
        effective='Define '+term if kind in {'label','calculation'} else question
        if contextual:effective='Define '+term
        if len(years)==1 and not re.search(r'(?:19|20)\d{2}',term):effective+=' in '+str(years[0])
        result=definitions.answer(effective,use_model,model,conversation)
        if kind=='calculation' and result.get('intent')!='clarify':
            mapping=result.get('definition_lookup',{}).get('reviewed_measure')
            if not mapping:
                result['message']='I have not established an app calculation formula for **'+term+'**. The source documentation below may describe how the reported field is constructed; I will not infer a formula from its label.\n\n'+result['message']
            else:
                from .analytics import measures
                expression=measures()[mapping].get('expression')
                if expression and 'Calculation:' not in result['message']:
                    result['message']='App calculation expression: `'+expression+'`. This is the reviewed app computation, not a new calculation of institutional values.\n\n'+result['message']
    result['documentation_context']={'kind':kind,'terms':[term],
        'source_years':result.get('definition_lookup',{}).get('source_years',years),
        'context_resolved':contextual}
    return result
