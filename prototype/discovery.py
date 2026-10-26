"""Source-backed topic overviews; metadata discovery never retrieves statistics."""
import re
import time
from collections import defaultdict
from .catalog import DATA,readonly,search
from .progress import report


def clean(text):return str(text or '').strip().rstrip(' .;:')


def cohort_pairs(title):
    pairs=re.findall(r'cohort year\s+((?:19|20)\d{2})\s*\(([^)]+)\)',title,re.I)
    if not pairs:
        pairs=[(year,'') for year in re.findall(r'\b((?:19|20)\d{2}(?:-\d{2})?) cohort\b',title,re.I)]
    if not pairs:
        pairs=[(year,'') for year in re.findall(r'cohorts? from ((?:19|20)\d{2}(?:-\d{2})?)\b',title,re.I)]
    return pairs


def stable_title(row):
    title=clean(row['title'])
    # Cohort years are coverage, not the name of the data area. Retain the
    # source population labels separately in both the grouping key and output.
    pairs=cohort_pairs(title)
    if pairs:
        title=re.split(r'\s*[-–]\s*cohort year\b',title,flags=re.I)[0]
        title=re.sub(r',?\s*\b(?:19|20)\d{2}(?:-\d{2})? cohort\b','',title,flags=re.I)
        title=re.sub(r'(cohorts?) from (?:19|20)\d{2}(?:-\d{2})?',r'\1',title,flags=re.I)
        populations=list(dict.fromkeys(p.removesuffix(' institutions') for _,p in pairs if p))
        if populations:title+=' ('+', '.join(populations)+' institutions)'
    period=clean(row.get('year_coverage'))
    if period:
        title=re.sub(r'\s*[:,–-]\s*(?:Academic year\s+)?'+re.escape(period)+r'\s*$','',title,flags=re.I)
    # Annual labels can disagree between title and year_coverage (e.g. AL2016).
    # Remove dates from navigation headings, retain both originals in evidence;
    # never rewrite one source label to agree with the other.
    date=re.search(r'\s*[:,–-]\s*(?:(?:Academic year|Fiscal year|Fall(?: enrollment)?|Spring|Summer|Winter)\s+)?((?:19|20)\d{2})(?:[-–](?:\d{2}|\d{4}))?$',title,re.I)
    if date:title=title[:date.start()]
    return clean(title)


def concept_key(row):
    title=stable_title(row).casefold().replace('varables','variables')
    populations=tuple(p.casefold() for _,p in cohort_pairs(row['title']))
    return (row['survey'],title,populations)


def group_tables(docs,schemas):
    """Group annual source descriptions only with supporting schema overlap.

    No numerical comparability is inferred. Changed populations, completion
    percentages or distinct same-release tables remain separate.
    """
    groups=defaultdict(list)
    for row in docs:
        key=concept_key(row);columns=schemas.get((row['release_id'],row['table_name']),set())
        for group in groups[key]:
            previous=group[-1];old=schemas.get((previous['release_id'],previous['table_name']),set())
            overlap=len(columns&old)/max(1,min(len(columns),len(old)))
            same_release=any(r['release_id']==row['release_id'] for r in group)
            if not same_release and overlap>=.6 and len(columns&old)>=2:
                group.append(row);break
        else:groups[key].append([row])
    return [group for candidates in groups.values() for group in candidates]


def topic(question):
    text=re.sub(r'\b(?:19|20)\d{2}\b',' ',question)
    text=re.sub(r'[^\w\s]',' ',text)
    stop=set('what which data information do does we you have has know available availability on about in the a an of for can show me tell variables tables ipeds is are our local files contain contains'.split())
    words=[w for w in text.split() if w.lower() not in stop]
    context={'college','colleges','university','universities'}
    if any(w.casefold() not in context for w in words):
        words=[w for w in words if w.casefold() not in context]
    return ' '.join(words)


def period_text(periods):
    """Compress only contiguous annual periods with identical source formatting."""
    periods=list(dict.fromkeys(clean(p) for p in periods))
    if periods and all(re.fullmatch(r'Status of student as of August 31, \d{4}',p) for p in periods):
        years=[p[-4:] for p in periods]
        return 'August 31: '+period_text(years)
    parsed=[re.fullmatch(r'(.*?)(\d{4})(-\d{2})?',p) for p in periods]
    if len(periods)>2 and all(parsed):
        shapes={(m[1],bool(m[3])) for m in parsed}
        starts=[int(m[2]) for m in parsed]
        valid_ends=all(not m[3] or int(m[3][1:])==(int(m[2])+1)%100 for m in parsed)
        if len(shapes)==1 and valid_ends and starts==sorted(set(starts)):
            runs=[];start=0
            for i in range(1,len(starts)+1):
                if i==len(starts) or starts[i]!=starts[i-1]+1:
                    runs.append(periods[start]+' through '+periods[i-1] if i-start>2 else '; '.join(periods[start:i]))
                    start=i
            return '; '.join(runs)
    return '; '.join(periods) or 'Not documented'


def coverage_label(periods):
    return 'Outcome dates' if periods and all(p.startswith('Status of student as of ') for p in periods) else 'Reporting periods'


def cohort_text(rows):
    groups=defaultdict(set)
    for row in rows:
        for year,population in cohort_pairs(row['title']):groups[population].add(year)
    return '; '.join((population.removesuffix(' institutions')+' institutions: ' if population else '')+period_text(sorted(years)) for population,years in groups.items())


def example_fields(db,rows,query):
    """Retrieve examples within each selected concept, not a global hit budget."""
    words=set(query.casefold().split());examples=[];records=[]
    for row in reversed(rows):
        fields=[dict(r) for r in db.execute('''SELECT v.record_id,v.variable_name,v.title FROM variable_docs v
            WHERE v.release_id=? AND v.table_name=? COLLATE NOCASE AND EXISTS
            (SELECT 1 FROM physical_columns p WHERE p.release_id=v.release_id
             AND p.table_name=v.table_name COLLATE NOCASE AND p.column_name=v.variable_name COLLATE NOCASE)
            ORDER BY v.record_id''',(row['release_id'],row['table_name']))]
        fields=[r for r in fields if r['title'] and r['variable_name'].upper()!='UNITID' and not r['variable_name'].upper().startswith('X')]
        fields.sort(key=lambda r:-len(words&set(re.findall(r'\w+',r['title'].casefold()))))
        for field in fields:
            if clean(field['title']) not in examples:
                examples.append(clean(field['title']));records.append(field['record_id'])
            if len(examples)==4:return examples,records
    return examples,records


def evidence_records(db,ids):
    records=[]
    for record_id in dict.fromkeys(ids):
        row=db.execute('''SELECT r.record_id,r.release_id,r.kind,r.table_name,r.variable_name,r.title,
            substr(r.body,1,2000) AS definition,f.path AS source_file,s.sheet_name,r.source_row
            FROM records r JOIN source_files f ON f.source_id=r.source_id
            LEFT JOIN sheets s ON s.sheet_id=r.sheet_id WHERE r.record_id=?''',(record_id,)).fetchone()
        item=dict(row);item['physical_column_present']=True if item['variable_name'] else None
        item['issues']=[dict(r) for r in db.execute('SELECT issue_type,description,status FROM issues WHERE source_record_id=?',(record_id,))]
        records.append(item)
    return records


def validate_topics(items,evidence):
    """Check overview coverage against its retained source records before display."""
    sources={r['record_id']:r for r in evidence};ids=set(sources);seen=set()
    for item in items:
        annual=item['annual_coverage'];records=set(item['record_ids'])
        if seen&records:raise ValueError('Discovery repeated an annual source record. Please narrow the topic.')
        seen.update(records)
        if records!={r['record_id'] for r in annual} or not records<=ids:
            raise ValueError('Discovery source coverage could not be verified.')
        periods={r['reporting_period'] for r in annual if r['reporting_period']}
        if periods!=set(item['periods']) or cohort_pairs(item['title']) or item['cohorts']!=cohort_text(annual):
            raise ValueError('Discovery labels and annual coverage disagree.')
        if not set(item['field_record_ids'])<=ids:raise ValueError('Discovery example fields lack source evidence.')
        if item['fields']!=[clean(sources[r]['title']) for r in item['field_record_ids']]:
            raise ValueError('Discovery example labels disagree with source definitions.')


def survey_blocks(items):
    groups=defaultdict(list)
    for item in items:groups[item['survey']].append(item)
    blocks=[]
    for survey,features in groups.items():
        coverages=[tuple(clean(p) for p in i['periods']) for i in features]
        common=max(coverages,key=coverages.count)
        different=any(c!=common for c in coverages)
        lines=['**Survey: '+(survey or 'Not documented')+'**',
            coverage_label(list(common))+(' (unless noted)' if different else '')+': '+period_text(list(common))+'.']
        bullets=[]
        for item in features:
            title=item['title']
            if item['periods']:
                title=re.sub(r':\s*(?:Academic year\s+)?'+re.escape(item['periods'][-1])+r'\s*$','',title,flags=re.I)
            text='**'+title.rstrip(' .;:')+'**'
            if tuple(clean(p) for p in item['periods'])!=common:text+=' — '+coverage_label(item['periods'])+': '+period_text(item['periods'])
            text+='.'
            if item.get('grouping_note'):text+='  \n  '+item['grouping_note']
            if item.get('cohorts'):text+='  \n  Entering cohorts: '+item['cohorts']+'.'
            if item['fields']:text+='  \n  Example fields: '+'; '.join(s.rstrip(' .;') for s in item['fields'])+'.'
            else:text+='  \n  Example fields could not be verified for this data area.'
            bullets.append('- '+text)
        lines.append('\n'.join(bullets))
        blocks.append('\n\n'.join(lines))
    return blocks


def overview(question,use_model=False,model=None):
    if not isinstance(question,str) or not 1<=len(question)<=4000:
        raise ValueError('Enter a question of at most 4,000 characters.')
    started=time.perf_counter();query=topic(question)
    years=sorted(set(int(y) for y in re.findall(r'\b(?:19|20)\d{2}\b',question)))
    if len(years)==2 and re.search(r'\b(?:through|to)\b|\d{4}\s*[–-]\s*\d{4}',question) and years[1]-years[0]<=30:
        years=list(range(years[0],years[1]+1))
    if not query:
        from .data_guide import answer
        return answer()
    interpretation=None;expansions=[];interpretation_usage=None
    if use_model:
        from .discovery_interpretation import interpret
        interpretation,expansions,interpretation_usage=interpret(question,query,years,model)
    report('Searching original keywords and verified catalog alternatives…' if expansions else 'Searching source tables and codebook definitions…')
    # Exclude conversational filler before FTS. Separate searches prevent annual
    # copies of a single variable from crowding all table definitions out.
    tables=search(query,limit=100,kinds=['table_definition'])
    fields=[r for r in search(query,limit=100,kinds=['variable_definition']) if r['physical_column_present']]
    records=tables+fields
    if interpretation is not None:
        from .discovery_interpretation import merge_hits
        interpretation['original_hit_record_ids']=list(dict.fromkeys(r['record_id'] for r in records))
        if expansions:records=merge_hits(tables,fields,expansions)
        interpretation['merged_hit_record_ids']=[r['record_id'] for r in records]
    hits={(r['release_id'],r['table_name'].upper()):i for i,r in reversed(list(enumerate(records))) if r.get('table_name')}
    verified_pairs={(r['release_id'],r['table_name'].upper()) for stream in expansions for r in stream}
    direct_pairs=set()
    if expansions:
        from .discovery_interpretation import tokens
        generic={'student','students','institution','institutions','college','colleges','university','universities','actually','people','who','how','many','much','what'}
        keywords=set(tokens(query))-generic
        direct_pairs={(r['release_id'],r['table_name'].upper()) for r in tables+fields if keywords&set(tokens(r['title']))}
        interpretation['ranking_policy']='Prioritize catalog-verified interpretations; also retain original-keyword matches directly in source titles. All original hits remain in the search audit and are the fallback if no expansion verifies.'
    with readonly(DATA/'metadata_catalog.sqlite') as db:
        docs=[dict(r) for r in db.execute('''SELECT t.* FROM table_docs t WHERE EXISTS
            (SELECT 1 FROM physical_tables p WHERE p.release_id=t.release_id
             AND p.table_name=t.table_name COLLATE NOCASE) ORDER BY t.release_id,t.table_name''')]
        schemas=defaultdict(set)
        for r in db.execute('SELECT release_id,table_name,column_name FROM physical_columns'):
            schemas[(r['release_id'],r['table_name'])].add(r['column_name'].upper())
        # Build all concepts first, then rank and cap them. Annual repeats can
        # no longer consume the eight display slots.
        groups=group_tables(docs,schemas)
        selected=[]
        for rows in groups:
            ranks=[hits[(r['release_id'],r['table_name'].upper())] for r in rows if (r['release_id'],r['table_name'].upper()) in hits]
            pairs={(r['release_id'],r['table_name'].upper()) for r in rows}
            available=[r for r in rows if not years or int(r['release_id'][6:10]) in years]
            if expansions and not pairs&(verified_pairs|direct_pairs):continue
            if ranks and available:
                priority=0 if pairs&verified_pairs else 1
                selected.append(((priority,min(ranks)),available))
        selected.sort(key=lambda x:x[0]);selected=selected[:8]
        items=[];source_ids=[]
        for _,rows in selected:
            latest=rows[-1];examples,field_ids=example_fields(db,rows,query)
            items.append({'title':stable_title(latest),'survey':latest['survey'],
                'periods':list(dict.fromkeys(r['year_coverage'] for r in rows if r['year_coverage'])),
                'tables':list(dict.fromkeys(r['table_name'] for r in rows)),
                'releases':list(dict.fromkeys(r['release_id'] for r in rows)),
                'fields':examples,'field_record_ids':field_ids,'cohorts':cohort_text(rows),
                'grouping_note':('Listed separately because source definitions or table structures differ.' if sum(concept_key(other[0])==concept_key(rows[0]) for _,other in selected)>1 else ''),
                'record_ids':[r['record_id'] for r in rows],
                'annual_coverage':[{'release_id':r['release_id'],'table_name':r['table_name'],'title':r['title'],'reporting_period':r['year_coverage'],'record_id':r['record_id']} for r in rows]})
            source_ids.extend(r['record_id'] for r in rows);source_ids.extend(field_ids)
        evidence=evidence_records(db,source_ids)
    report('Checking discovery coverage and source references…')
    validate_topics(items,evidence)
    lines=[]
    if items:
        lines.append('Here are relevant data areas I found in the local IPEDS files:')
        lines.extend(survey_blocks(items))
        lines.append('These are codebook and physical-table matches, not confirmation that every institution has reported values. Definitions, populations and available breakdowns can differ by year. This is a bounded topic search, not an exhaustive inventory.')
        if years:lines.append('The year filter selects source releases; reporting periods are listed separately above.')
        lines.append('To continue, tell me the institution, data area and years you want to analyze.')
    else:
        lines.append('I did not find a matching documented physical table in this bounded search'+(' for the requested release years' if years else '')+'. This does not establish that the data are absent. Try a related term or an exact IPEDS table or variable name.')
    answer={'intent':'discover','mode':'data discovery','query':query,'message':'\n\n'.join(lines),
        'discovery':{'topics':items,'requested_release_years':years,'bounded':True,
            'grouping_policy':'Exact survey and stable description/population; at most one table per release; at least two shared columns and 60% overlap relative to the smaller schema. Navigation grouping does not certify numerical comparability.'},'evidence':evidence,
        'latency':{'answer_ready_seconds':time.perf_counter()-started,'live_model_calls':interpretation.get('calls',0) if interpretation else 0,
            'discovery_interpretation_seconds':interpretation.get('elapsed_seconds',0) if interpretation else 0}}
    if interpretation is not None:answer['discovery']['interpretation']=interpretation
    if interpretation_usage:answer['model_usage']=interpretation_usage
    if interpretation and interpretation['ambiguous'] and items:
        answer['message']='Your wording can have more than one meaning; the available options below are not treated as equivalent.\n\n'+answer['message']
    if use_model and items:
        from .discovery_narrative import write
        return write(answer,question,model)
    return answer
