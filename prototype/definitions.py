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


def reviewed(term):
    from .analytics import measures
    return next((m for m in measures().values() if normalized(term)==normalized(m['label']) or term.strip().casefold()==m['id']),None)


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
    from .discovery_narrative import request as model_request,obj,array,STRING
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
