"""Definition questions read supplied metadata, never institution statistics."""
import json,re,time
from .catalog import DATA,readonly
from .progress import report

STOP=set('the a an of in ipeds data codebook definition meaning defined please for'.split())


def stem(word):
    if word in {'enrollment','enrolled','enrollments'}:return 'enroll'
    if word.endswith('ies') and len(word)>5:return word[:-3]+'y'
    if word.endswith('s') and len(word)>5 and not word.endswith(('ss','us')):return word[:-1]
    return word


def words(text):
    return re.findall(r'[a-z0-9_]+',text.casefold())


def normalized(text):return ' '.join(words(text))


def tokens(text):
    return [w for w in words(text) if w not in STOP and not re.fullmatch(r'(?:19|20)\d{2}',w)]


def request(question):
    """Recognize explicit definitions; leave mixed definition/statistical requests intact."""
    if not isinstance(question,str) or len(question)>4000:return None
    q=question.strip().rstrip('?.!').strip()
    if re.search(r'\b(?:and|also|then)\s+(?:show|plot|count|calculate|compare|give|how many|how much)\b',q,re.I):return None
    patterns=[r'(?:please\s+)?define\s+(.+)',r'what (?:is|are) (?:the )?definitions? of\s+(.+)',
              r'what does\s+(.+?)\s+(?:mean|stand for)(?:\s+in IPEDS)?',r'how (?:is|are)\s+(.+?)\s+defined(?:\s+in IPEDS)?',
              r'(?:explain|what is) (?:the )?(?:meaning|definition) of\s+(.+)',
              r'(?:what is|explain) the difference between\s+(.+)']
    term=None;explicit=True
    for pattern in patterns:
        m=re.fullmatch(pattern,q,re.I)
        if m:term=m[1];break
    if term is None:
        m=re.fullmatch(r'what (?:is|are)\s+(.+)',q,re.I)
        if not m:return None
        term=m[1];explicit=False
    term=re.sub(r'\s+(?:according to|in) (?:the )?IPEDS(?: codebooks?)?\s*$','',term,flags=re.I)
    term=re.sub(r'^(?:the )?term\s+','',term,flags=re.I).strip(' "“”\'')
    term=re.sub(r'^(?:the|a|an)\s+','',term,flags=re.I)
    if not term:return None
    # Bare "what is" becomes a definition only after a full title/identifier or
    # explicit glossary heading is found. Never consume a numerical school query.
    return {'term':term,'explicit':explicit,'comparison':bool(re.match(r'(?:what is|explain) the difference between\b',q,re.I))}


def _norm6(text):
    # Treat "6-year"/"6 year" and "six-year" as the same phrase.
    return re.sub(r'\b6 year\b','six year',normalized(text))


def _measure_core(label):
    """Split a reviewed label into (subgroup, core). "All: six-year bachelor
    graduation rate" -> ("all","six-year bachelor graduation rate")."""
    m=re.match(r'\s*(.+?):\s*(.+)$',label)
    return (m[1].strip().casefold(),m[2].strip()) if m else (None,label.strip())


def _alias_forms(core):
    """Acceptable normalized phrasings of a measure core: with or without the word
    'bachelor'. The 'six-year' qualifier is NOT dropped: bare 'graduation rate' stays
    generic (IPEDS has 4-/6-/8-year rates) and must not claim the six-year definition."""
    base=_norm6(core)
    forms={base,base.replace("bachelor's ",'').replace('bachelor ','')}
    return {re.sub(r'\s+',' ',f).strip() for f in forms if f}


def reviewed(term):
    """Map a natural term to a reviewed measure. Exact label/id first, then a
    subgroup-aware core match (unqualified -> the 'All' measure). Ambiguous
    unqualified matches fall through to the codebook search."""
    from .analytics import measures
    ms=list(measures().values())
    direct=next((m for m in ms if normalized(term)==normalized(m['label']) or term.strip().casefold()==m['id']),None)
    if direct:return direct
    t=_norm6(term)
    subgroup=('non-pell students' if re.search(r'\bnon[\s-]?pell\b',term,re.I) else 'pell recipients' if re.search(r'\bpell\b',term,re.I)
              else 'men' if re.search(r'\b(?:men|male)\b',term,re.I) else 'women' if re.search(r'\b(?:women|female)\b',term,re.I)
              else 'u.s. nonresident' if re.search(r'\b(?:nonresident|non[\s-]?resident|international)\b',term,re.I) else None)
    t_core=re.sub(r'\s+',' ',re.sub(r'\b(?:non[\s-]?pell|pell|men|male|women|female|u s nonresident|nonresident|non resident|international|students?|recipients?|s)\b','',t,flags=re.I)).strip()
    best=[]
    for m in ms:
        pref,core=_measure_core(m['label'])
        if t_core and t_core in _alias_forms(core):
            if subgroup is None and pref in (None,'all'):best.append(m)
            elif subgroup is not None and pref==subgroup:best.append(m)
    if len(best)==1:return best[0]
    return best[0] if best and subgroup else None


def scope(term):
    years=list(dict.fromkeys(int(y) for y in re.findall(r'(?<!\d)((?:19|20)\d{2})(?!\d)',term)))
    # An explicit annual table identifier also selects its source release.
    if not years:years=list(dict.fromkeys(int(y) for y in re.findall(r'[A-Z_]+((?:19|20)\d{2})',term)))
    cleaned=re.sub(r'\b(?:in|for|from|release|fall|academic year)\s+(?:19|20)\d{2}(?:[-–]\d{2})?',' ',term,flags=re.I).strip()
    return cleaned,years or [2024]


def heading_excerpt(text,term):
    # A glossary entry is stronger evidence than incidental use in a measure.
    phrase=r'[\s-]+'.join(map(re.escape,words(term)))
    if not phrase:return None
    matches=list(re.finditer(r'\b(?i:'+phrase+r')\b(?:\s*[-–—:]\s+(?=[A-Z])|\s+(?=(?:is|are|means|refers|Persons|A |An |The |As defined)\b))',text))
    matches=[m for m in matches if text[m.start()].isupper()]
    if not matches:return None
    start=matches[-1].start();tail=text[start:]
    next_heading=re.search(r'\s+(?:(?:[A-Z]{2,}|[A-Z][a-z]+)(?:[ ][A-Za-z]+){0,3}\s*[-–—:]\s+(?=[A-Z])|[A-Z][a-z]+-(?=[A-Z][a-z]+\s+(?:of|is|the|as)\b))',tail[len(term)+3:])
    if next_heading:tail=tail[:len(term)+3+next_heading.start()]
    return tail.strip() if 20<=len(tail)<=1800 else None


def candidates(term,years,limit=20):
    parts=term.split('.')
    table=parts[0] if len(parts)==2 and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',parts[0]) else None
    target=parts[-1] if table else term
    key=normalized(target);required=tokens(target)
    if not required:return []
    # AND terms retain the requested concept; no OR-only topic overview.
    def variants(w):
        return ['enrollment','enrolled','enrollments'] if stem(w)=='enroll' else list(dict.fromkeys([w,stem(w),stem(w)+'s']))
    fts=' AND '.join('('+' OR '.join('"'+v+'"' for v in variants(w))+')' for w in required[:12])
    releases=[f'IPEDS_{y}-' for y in years]
    with readonly(DATA/'metadata_catalog.sqlite') as db:
        release_ids=[r[0] for r in db.execute('SELECT release_id FROM releases') if any(r[0].startswith(p) for p in releases)]
        if not release_ids:return []
        rows=db.execute('''SELECT r.record_id,r.release_id,r.kind,r.table_name,r.variable_name,r.title,
            coalesce(nullif(v.long_description,''),nullif(t.description,''),r.body) AS definition,
            f.path AS source_file,s.sheet_name,r.source_row
            FROM search_index JOIN records r ON r.record_id=search_index.record_id
            LEFT JOIN variable_docs v USING(record_id) LEFT JOIN table_docs t USING(record_id)
            JOIN source_files f ON f.source_id=r.source_id LEFT JOIN sheets s ON s.sheet_id=r.sheet_id
            WHERE search_index MATCH ? AND r.release_id IN ('''+','.join('?' for _ in release_ids)+''')
            AND r.kind IN ('variable_definition','table_definition')
            ORDER BY bm25(search_index),r.record_id LIMIT 120''',[fts,*release_ids]).fetchall()
        found=[]
        for row in rows:
            r=dict(row)
            if table and r['table_name'].casefold()!=table.casefold():continue
            text=re.sub(r'\s+',' ',r['definition']).strip();title=normalized(r['title'])
            exact=bool(key in {title,normalized(r['variable_name'] or '')})
            heading=heading_excerpt(text,target)
            identifier_use=bool(re.fullmatch(r'[A-Z][A-Z0-9_]{2,}',target) and r['kind']=='table_definition' and re.search(r'\(\s*'+re.escape(target)+r'\s*\)',text,re.I))
            prefix=bool(len(required)>=2 and title.startswith(key+' ') and len(words(text))>len(words(r['title']))+5)
            # Metadata table names/survey labels alone do not define a term.
            if not exact and not all(stem(w) in {stem(t) for t in words(text+' '+r['title'])} for w in required):continue
            identifier_excerpt=None
            if identifier_use:
                identifier_excerpt=next((m.group().strip() for m in re.finditer(r'[^.!?]+[.!?]?',text) if re.search(r'\b'+re.escape(target)+r'\b',m.group(),re.I)),None)
            r['excerpt']=heading or identifier_excerpt or text[:1800]
            r['glossary_excerpt']=heading if not exact else None
            r['direct_match']=exact or bool(heading) or prefix or identifier_use
            r['score']=(1000 if exact else 700 if heading else 650 if identifier_use else 500 if prefix else 0)+sum(w in title.split() for w in required)*20-(len(text)/10000)
            r['score']-=3*max(0,len(title.split())-len(required))
            if not set(required)&{'men','women','male','female'} and set(title.split())&{'men','women','male','female'}:r['score']-=100
            if 'total' in title.split() and 'total' not in required:r['score']+=20
            if identifier_use and 'one record per institution' in text.casefold():r['score']+=80
            r['physical_column_present']=bool(db.execute('SELECT 1 FROM physical_columns WHERE release_id=? AND table_name=? AND column_name=?',(r['release_id'],r['table_name'],r['variable_name'])).fetchone()) if r['variable_name'] else None
            r['issues']=[dict(x) for x in db.execute('SELECT issue_type,description,status FROM issues WHERE source_record_id=?',(r['record_id'],))]
            r['definition']=text
            found.append(r)
    return sorted(found,key=lambda r:(-r['score'],r['record_id']))[:limit]


def can_answer(question):
    parsed=request(question)
    if not parsed:return False
    if parsed['comparison']:
        terms=re.split(r'\s+and\s+',parsed['term'],maxsplit=1,flags=re.I)
        return len(terms)==2 and all(reviewed(scope(t)[0]) or any(r['direct_match'] for r in candidates(*scope(t),limit=8)) for t in terms)
    if parsed['explicit']:return True
    term,years=scope(parsed['term'])
    if re.search(r'\d{4}',parsed['term']) and not re.fullmatch(r'[A-Z][A-Z0-9_.]*(?:\s+in\s+\d{4})?',parsed['term']):return False
    if reviewed(term):return True
    return any(r['direct_match'] for r in candidates(term,years,8))


def extract_with_model(term,records,model,trusted_ids=()):
    from .discovery import request as model_request,obj,array,STRING
    from .agent import usage_cost
    schema=obj({'passages':array(obj({'record_id':{'type':'integer'},'excerpt':STRING}))})
    system='''Answer a definition lookup using ONLY the supplied codebook records. Return select_definition with up to three passages, each an EXACT contiguous excerpt of a supplied definition (whitespace normalization is allowed). Prefer ONE sufficient definition. Do not repeat the same meaning from multiple fields or add unrelated salary/count methodology. Do not paraphrase, compute, invent expansions or use external knowledge. When a record has glossary_entry=true, select its ENTIRE provided definition unchanged, including exclusions and qualifications. Prefer that explicit glossary entry over a measure that merely mentions the term. Do not equate faculty status with instructional occupation. If there are genuinely different measure-specific meanings, select distinct applicable definitions rather than merging them. For an identifier whose own definition is absent, a table passage explaining its use is acceptable, but do not substitute a parent-ID variable. Use an empty passages list if these records do not establish the requested meaning. Each excerpt must be 20–1800 characters; no invented explanations or counts.'''
    package=[];budget=32000
    for r in records[:12]:
        text=(r.get('glossary_excerpt') or r['definition'])[:min(6000,budget)]
        if len(text)<100:break
        package.append({**{k:r[k] for k in ['record_id','title','variable_name','table_name']},'definition':text,'glossary_entry':bool(r.get('glossary_excerpt'))})
        budget-=len(text)
    response=model_request(model,schema,system,{'term':term,'records':package},max_tokens=2200,tool_name='select_definition')
    u={k:getattr(response.usage,k,0) or 0 for k in ['input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens']}
    usage={'model':model,'calls':1,'latency_seconds':0,**u,'estimated_api_usd':usage_cost(model,u),'stage':'definition passage selection'}
    blocks=[b for b in response.content if b.type=='tool_use' and b.name=='select_definition']
    try:
        import jsonschema
        if len(blocks)!=1 or response.stop_reason=='max_tokens':raise ValueError('No complete definition selection.')
        payload=blocks[0].input;jsonschema.validate(payload,schema)
        if len(payload['passages'])>3:raise ValueError('Too many definition passages.')
        selected=[];lookup={r['record_id']:r for r in records};sent={r['record_id']:r for r in package};seen=set()
        for p in payload['passages']:
            excerpt=re.sub(r'\s+',' ',p['excerpt']).strip();r=lookup.get(p['record_id'])
            if not r or p['record_id'] not in sent or not 20<=len(excerpt)<=1800 or excerpt not in sent[p['record_id']]['definition']:raise ValueError('Definition excerpt must match an inspected source verbatim.')
            if sent[p['record_id']]['glossary_entry'] and excerpt!=sent[p['record_id']]['definition']:raise ValueError('Retain the complete glossary definition and its qualifications.')
            if r['kind']=='variable_definition' and not sent[p['record_id']]['glossary_entry']:
                first=re.split(r'(?<=[.!?])\s+',sent[p['record_id']]['definition'],maxsplit=1)[0]
                if len(first)<=600 and first not in excerpt:raise ValueError('Retain the opening source definition and population scope.')
            identifier=normalized(term.split('.')[-1])==normalized(r['variable_name'] or '')
            if not identifier and p['record_id'] not in trusted_ids and not all(stem(w) in {stem(t) for t in words(r['title']+' '+excerpt)} for w in tokens(term.split('.')[-1])):raise ValueError('Definition excerpt does not retain the requested term.')
            if normalized(excerpt) not in seen:selected.append({**r,'excerpt':excerpt})
            seen.add(normalized(excerpt))
        return selected,usage,'accepted'
    except (ValueError,jsonschema.ValidationError) as exc:return None,usage,str(exc)


def answer(question,use_model=False,model=None,conversation=None):
    from .agent import DEFAULT_MODEL,api_key
    started=time.perf_counter();parsed=request(question)
    if not parsed:raise ValueError('Not a standalone definition question.')
    if parsed['comparison']:
        terms=re.split(r'\s+and\s+',parsed['term'],maxsplit=1,flags=re.I)
        if len(terms)!=2:return {'intent':'clarify','mode':'source definition','message':'Name the two terms you would like compared.'}
        parts=[answer('Define '+term,use_model,model,conversation) for term in terms]
        output={'intent':'definition','mode':'source definition','message':'The terms have separate source definitions:\n\n'+'\n\n'.join(p['message'] for p in parts),
                'evidence':list({r['record_id']:r for p in parts for r in p.get('evidence',[])}.values()),
                'definition_lookup':{'term':parsed['term'],'terms':terms,'comparison':True,'parts':[p.get('definition_lookup',{}) for p in parts]},
                'latency':{'answer_ready_seconds':time.perf_counter()-started,'live_model_calls':sum(p.get('latency',{}).get('live_model_calls',0) for p in parts)}}
        usages=[p['model_usage'] for p in parts if p.get('model_usage')]
        if usages:
            output['model_usage']={'model':model or DEFAULT_MODEL,'calls':sum(u['calls'] for u in usages),'latency_seconds':sum(u['latency_seconds'] for u in usages),
                                   'estimated_api_usd':sum(u['estimated_api_usd'] for u in usages) if all(u.get('estimated_api_usd') is not None for u in usages) else None,'stages':usages}
        return output
    term=parsed['term']
    if normalized(term) in {'that','this','it'}:
        previous=(conversation or [{}])[-1].get('answer',{})
        if previous.get('definition_lookup',{}).get('comparison'):
            return {'intent':'clarify','mode':'source definition','message':'Which of the compared terms would you like explained further?'}
        old=previous.get('definition_lookup',{}).get('term')
        if old:term=old
        else:
            metrics=previous.get('result',{}).get('plan',{}).get('metrics',[])
            labels=[r['measure'] for r in previous.get('result',{}).get('rows',[])]
            if len(metrics)==1 and labels:term=labels[0]
            else:return {'intent':'clarify','mode':'source definition','message':'Which term or variable would you like defined? Name it so I can use the relevant supplied codebook.'}
    explicit_years=bool(re.search(r'(?:19|20)\d{2}',term))
    term,years=scope(term)
    if any(y not in range(2015,2025) for y in years):
        return {'intent':'clarify','mode':'source definition','message':'The supplied codebooks cover source releases 2015–2024. I cannot verify that definition for the requested release; no other year has been substituted.'}
    if len(years)>1:
        return {'intent':'clarify','mode':'source definition','message':'This definition lookup explains one source release at a time. You requested '+', '.join(map(str,years))+'. Which release should I use? I will not assume definitions are unchanged across years.'}
    report('Looking up the term in the supplied codebooks…')
    records=candidates(term,years);selected=[];usage=None;selection='deterministic'
    mapping=reviewed(term)
    mapping_definition=None;ids=[]
    if mapping:
        ids=[rid for y in years for rid in mapping.get('annual',{}).get(str(y),{}).get('definition_record_ids',[])]
        from .catalog import definition_detail
        for rid in ids:
            if any(r['record_id']==rid for r in records):continue
            r=definition_detail(rid)
            r['definition']=re.sub(r'\s+',' ',r['definition']).strip()
            r.update(excerpt=r['definition'][:1800],direct_match=True,score=1000,issues=[],physical_column_present=None)
            records.insert(0,r)
        mapping_definition=mapping['definition']
        selected=[r for r in records if r['record_id'] in ids][:3]
        selection='reviewed mapping with source definitions'
    if use_model and records and api_key() and not mapping:
        try:
            mark=time.perf_counter();selected,usage,selection=extract_with_model(term,records,model or DEFAULT_MODEL,ids)
            if usage:usage['latency_seconds']=time.perf_counter()-mark
        except Exception as exc:
            selected=None;selection='Selection unavailable: '+type(exc).__name__
            usage={'model':model or DEFAULT_MODEL,'calls':1,'latency_seconds':time.perf_counter()-mark,
                   'estimated_api_usd':None,'usage_complete':False,'stage':'definition passage selection'}
    elif not mapping:selected=None
    if selected is None:
        seen=set();selected=[]
        for r in records:
            if not r['direct_match'] or normalized(r['excerpt']) in seen:continue
            seen.add(normalized(r['excerpt']));selected.append(r)
            if len(selected)==1:break
    if selected:
        text='Supporting source definitions:\n\n' if mapping else 'For **'+term+'**, the supplied codebook gives these source passages:\n\n'
        text+='\n\n'.join('**'+r['title']+'** ('+r['release_id'].removeprefix('IPEDS_').replace('_',' · ')+' · '+r['table_name']+' · '+(r['variable_name'] or 'table documentation')+')\n\n> '+r['excerpt'] for r in selected)
        text+='\n\nThese excerpts retain their source-specific scope. Full definitions and source locations are under Definitions & sources.'
    else:
        text='I could not establish a direct definition of **'+term+'** from this bounded search of the supplied codebooks. This does not prove the term is absent. Try its exact variable name, source table, or a more specific term.'
    if mapping_definition:
        names={r.get('variable_name'):r['title'] for r in records if r.get('variable_name')}
        formula=mapping.get('expression','')
        match=re.fullmatch(r'100(?:\.0)?\*([A-Z0-9_]+)/NULLIF\(([A-Z0-9_]+),0\)',formula)
        calculation=(names.get(match[1],match[1])+' ÷ '+names.get(match[2],match[2])+' × 100.') if match else ''
        text='**'+mapping['label']+' — reviewed app definition:** '+mapping_definition+('\n\nCalculation: '+calculation if calculation else '')+'\n\n'+text
    evidence=selected or records[:5]
    result={'intent':'definition','mode':'source definition','message':text,'evidence':evidence,
            'definition_lookup':{'term':term,'source_years':years,'default_latest_release':not explicit_years,
                'status':'defined' if selected else 'not_established','selection':selection,'reviewed_measure':mapping['id'] if mapping else None,'candidate_record_ids':[r['record_id'] for r in records],
                'passages':[{'record_id':r['record_id'],'excerpt':r['excerpt']} for r in selected],
                'source_policy':'Owner-supplied metadata only; no statistical values queried'},
            'latency':{'answer_ready_seconds':time.perf_counter()-started,'live_model_calls':1 if usage else 0}}
    if usage:result['model_usage']=usage
    return result


# ===== merged from category_documentation.py (consolidation) =====
"""Bounded source-code label explanations, including blocked-query follow-ups."""
import re
from .catalog import readonly, DATA, definition_detail


def category_answer(question, conversation=None):
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


# ===== merged from documentation.py (consolidation) =====
"""Route documentation questions before identity/statistical planning.

Conversation supplies references, never new source evidence. No model call is
needed to classify these common intents or resolve an unambiguous reference.
"""
import re


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
    parsed=request(question)
    if parsed and can_answer(question):
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
    categorical=category_answer(question,conversation)
    if categorical is not None:return categorical
    parsed=classify(question)
    if not parsed and conversation:
        last=conversation[-1].get('answer',{})
        pending=last.get('documentation_context',{})
        if last.get('intent')=='clarify' and pending.get('kind'):
            match=next((t for t in pending.get('terms',[]) if normalized(t)==normalized(question)),None)
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
        result=answer(effective,use_model,model,conversation)
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
