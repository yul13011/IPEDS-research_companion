"""Bounded source-code label explanations, including blocked-query follow-ups."""
import re
from .catalog import readonly, DATA, definition_detail


def handle(question, conversation=None):
    if not isinstance(question,str) or not 1<=len(question)<=4000:return None
    low=question.casefold()
    if not re.search(r'what does|\bdefine\b|\bmeaning\b|difference between|\bexplain\b', low):return None
    if re.search(r'\b(?:and|also|then)\s+(?:show|count|calculate|how many|how much)\b',low):return None
    last=(conversation or [{}])[-1].get('answer',{})
    contextual=bool(re.search(r'those two|these two|those categories|these categories',low))
    labels=[s for s in ['Implied no','Not reported','Not applicable'] if s.casefold() in low]
    quoted=re.findall(r'["“]([^"”]{1,100})["”]',question)
    if quoted:
        with readonly(DATA/'metadata_catalog.sqlite') as db:
            labels+= [r[0] for text in quoted[:4] for r in db.execute('SELECT DISTINCT value_label FROM code_values WHERE value_label=? COLLATE NOCASE LIMIT 2',(text,))]
        labels=list(dict.fromkeys(labels))
    if not labels:
        match=re.search(r'(?:define|explain) (?:the )?label (.+?) (?:for|in)\b',question,re.I)
        if match:
            with readonly(DATA/'metadata_catalog.sqlite') as db:
                labels=[r[0] for r in db.execute('SELECT DISTINCT value_label FROM code_values WHERE value_label=? COLLATE NOCASE LIMIT 2',(match[1].strip(),))]
    if not labels and not contextual:return None
    prior_years=(last.get('observation_plan') or last.get('definition_lookup') or {}).get('source_years')
    years=list(dict.fromkeys(map(int,re.findall(r'\b((?:19|20)\d{2})(?:[-–/]\d{2})?\b',question)))) or prior_years or [2024]
    if len(years)!=1 or years[0] not in range(2015,2025):
        return {'intent':'clarify','mode':'source definition','message':'Which supplied source release should I use to explain these category labels?'}
    year=years[0];ids=[]
    if contextual:
        ids=[r['record_id'] for r in last.get('result',{}).get('rows',[]) if r.get('record_id')]
        p=last.get('observation_plan') or last.get('catalog_plan') or {}
        ids+= [rid for s in p.get('sources',[]) for rid in s.get('field_record_ids',[])]
        ids=list(dict.fromkeys(ids))
        if not 1<=len(ids)<=8:
            return {'intent':'clarify','mode':'source definition','message':'Which source categories do you mean? Please name the labels or variables so I can explain their documented difference.'}
    with readonly(DATA/'metadata_catalog.sqlite') as db:
        if not contextual:
            # Anchor category lookup to the source variable's actual wording.
            terms=re.findall(r'[a-z]{3,}',low)
            stop={'what','does','mean','define','the','label','for','and','how','different','from','institutional','characteristics','codebook','implied','not','reported','applicable','explain','meaning','no'}
            terms=[t for t in terms if t not in stop]
            terms=[('care' if t=='childcare' else t) for t in terms]
            if not terms:return None
            pairs={tuple(r) for r in db.execute('SELECT DISTINCT table_name,variable_name FROM code_values WHERE release_id LIKE ? AND value_label IN ('+','.join('?' for _ in labels)+')',('%'+str(year)+'-%',*labels))}
            candidates=db.execute("SELECT record_id,table_name,variable_name,title,body FROM records WHERE kind='variable_definition' AND release_id LIKE ? LIMIT 20001",('%'+str(year)+'-%',)).fetchall()
            if len(candidates)>20000:return {'intent':'clarify','mode':'source definition','message':'Which source table or variable should I use for these category labels?'}
            rows=[r for r in candidates if (r['table_name'],r['variable_name']) in pairs]
            scored=[(sum(4*(t in r['title'].casefold())+(t in r['body'].casefold()) for t in set(terms)),r['record_id']) for r in rows]
            top=max((s for s,_ in scored),default=0)
            ids=[rid for s,rid in scored if s==top and s>0]
            if not 1<=len(ids)<=4:return {'intent':'clarify','mode':'source definition','message':'Which source variable or service do you mean? These category labels occur in multiple fields.'}
    try:details=[definition_detail(rid) for rid in ids]
    except ValueError:
        return {'intent':'clarify','mode':'source definition','message':'The earlier field references could not be verified. Which source variables or labels should I explain?'}
    if contextual and len(details)<2:return None
    evidence=[];parts=[]
    for d in details:
        mappings=[c for c in d['codes'] if not labels or c['value_label'] in labels]
        if not contextual and not mappings:continue
        parts.append('**'+d['title']+'**: '+d['definition']+('\n\nSource responses: '+'; '.join(str(c['code_value'])+' = '+c['value_label'] for c in mappings) if mappings else ''))
        with readonly(DATA/'metadata_catalog.sqlite') as db:
            present=bool(db.execute('SELECT 1 FROM physical_columns WHERE release_id=? AND table_name=? COLLATE NOCASE AND column_name=? COLLATE NOCASE',(d['release_id'],d['table_name'],d['variable_name'])).fetchone())
        evidence.append({**d,'excerpt':d['definition'],'issues':[],'physical_column_present':present})
    if not parts:return None
    return {'intent':'definition','mode':'source definition','message':'\n\n'.join(parts)+'\n\nThese are distinct source response categories; an unavailable or unreported response must not be interpreted as No.',
        'evidence':evidence,'definition_lookup':{'term':'source category labels','terms':[d['title'] for d in details],'source_years':[year],'comparison':len(details)>1},
        'documentation_context':{'kind':'label','terms':[d['title'] for d in details],'source_years':[year]},
        'model_usage':{'calls':0,'estimated_api_usd':0},'latency':{'live_model_calls':0}}
