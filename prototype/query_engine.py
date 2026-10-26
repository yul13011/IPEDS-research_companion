"""General bounded relational executor: source binding, grain, joins, DAG math.

Version 1 stays supported. Version 2 builds source relations independently,
checks row domains before aggregation and validates joins before deriving output.
Every identifier originates in the catalog; all predicates use bound parameters.
"""
from collections import defaultdict
from datetime import datetime,timezone
from hashlib import sha256
import json
import math
import re
import time

import pandas as pd

from analysis_catalog.catalog import connection,table_context
from .catalog import annual_path,readonly,institutions
from .catalog_planner import validate_proposal
from .query_schema import QUERY_SCHEMA
from .semantics import describe_field,subset,words
from .responses import finalize_answer
from .progress import report

ROW_LIMIT=20000
OUTPUT_LIMIT=5000
IDENTIFIER=re.compile(r'[a-zA-Z][a-zA-Z0-9_]{0,30}\Z')


def quote(name):return '"'+name.replace('"','""')+'"'
def field_ref(rid,source):return 'f'+source+'_'+str(rid)
def aggregate_ref(source,agg):return 'a'+source+'_'+agg
def key_ref(source,column):return source+'__'+column.upper()


def signed_allowed(d):
    text=d['title']+' '+d['long_description']
    return bool(re.search(r'\b(net|loss|losses|deficit|surplus|unrestricted|change in|excess of)\b',text,re.I)
                and re.search(r'assets?|liabilit|position|income|revenue|expense|investment|balance|cash|financial',text,re.I))


def number(value,d,missing_codes=()):
    if value is None or str(value).strip()=='' or str(value) in missing_codes:return None
    try:value=float(value)
    except (ValueError,TypeError):return None
    if not math.isfinite(value):return None
    if value<0 and not signed_allowed(d):return None
    return int(value) if value.is_integer() else value


def parse_period(text):
    """Source labels to comparable period anchors; raw wording always retained."""
    low=text.casefold();years=[int(y) for y in re.findall(r'\b(?:19|20)\d{2}\b',low)]
    if not years:return {'kind':'unknown','start':None,'end':None,'raw':text}
    start=min(years);end=max(years)
    short=re.search(r'\b((?:19|20)\d{2})[-–/](\d{2})\b',low)
    if short:end=int(short[1])//100*100+int(short[2])
    kind='fall' if 'fall' in low else 'november' if 'november' in low else 'fiscal' if 'fiscal' in low or re.search(r'\bfy\b',low) else 'july_june' if 'july' in low and 'june' in low else 'academic' if 'academic' in low else 'reporting'
    return {'kind':kind,'start':start,'end':end,'raw':text}


def period_set(t):
    periods=[parse_period(str(e['year_coverage'])) for e in t['period_evidence'] if e.get('year_coverage')]
    # Some codebooks put only "2024-25" in Year Coverage but explicitly say
    # "Academic year 2024-25" in the same table's title. Use that exact evidence
    # to type the period, retaining the original coverage text for provenance.
    titles=[p.get('title','') for p in t.get('population_evidence',[])]
    for p in periods:
        if p['kind']!='reporting':continue
        matches=[parse_period(title) for title in titles if re.search(r'\b(?:academic|fiscal) year\b',title,re.I)]
        matches=[m for m in matches if (m['start'],m['end'])==(p['start'],p['end'])]
        kinds={m['kind'] for m in matches}
        if len(kinds)==1:p['kind']=next(iter(kinds))
    return periods


def cohort_years(bound,sources):
    years={int(y) for s in sources for f in s['filters'] for c in bound['codes'][f['record_id']]
        if c['code_value'] in f['values'] and re.search(r'cohort',bound['definitions'][f['record_id']]['title']+' '+c['value_label'],re.I)
        for y in re.findall(r'\b(?:19|20)\d{2}\b',c['value_label'])}
    if years:return years
    for s in sources:
        if not re.fullmatch(r'GR\d{4}(?:_L2)?',s['table'],re.I):continue
        labels=' '.join(c['value_label'] for f in s['filters'] for c in bound['codes'][f['record_id']] if c['code_value'] in f['values'])
        texts=' '.join(e['title'] for e in source_context(bound,s)['population_evidence'])
        if s['table'].upper().endswith('_L2'):
            hits=re.findall(r'cohort year\s+((?:19|20)\d{2})',texts,re.I)
        else:
            kind='4' if re.search(r'4[ -](?:year|yr)',labels,re.I) else '2' if re.search(r'2[ -](?:year|yr)',labels,re.I) else None
            hits=re.findall(r'cohort year\s+((?:19|20)\d{2})\s*\('+kind+r'[ -]year',texts,re.I) if kind else []
        years.update(map(int,hits))
    return years


def leaf_domain(field,code_rows):
    """Reject totals, hierarchical ancestors and mixed population slices."""
    labels=[r['value_label'] for r in code_rows]
    if len(labels)<2:return True
    # Full-/part-time are a source-defined disjoint dimension even where each
    # category's label contains a total over other dimensions.
    normalized=[re.sub(r'\b(full|part)[ -]time\b','ATTENDANCE',s,flags=re.I) for s in labels]
    if len(set(normalized))==1 and all(re.search(r'\b(full|part)[ -]time\b',s,re.I) for s in labels):return True
    if any(re.search(r'\b(total|all)\b',s,re.I) for s in labels):return False
    if any(',' in s for s in labels):
        paths=[tuple(words(p) for p in s.split(',')) for s in labels]
        if any(len(a)<len(b) and b[:len(a)]==a for a in paths for b in paths):return False
    codes=[r['code_value'] for r in code_rows]
    if any('.' in c for c in codes):
        if any(a!=b and b.startswith(a.rstrip('0').rstrip('.')+'.') for a in codes for b in codes):return False
    # Coded dimensions must describe a classification, not arbitrary numeric bins.
    return bool(re.search(r'rank|classif|categor|level|status|program|gender|sex|race|occupation|assigned',field['title']+' '+field['long_description'],re.I))


def check_fiscal_year(sources,question):
    """Guard the IPEDS finance off-by-one. A hyphenated "YYYY-YY" span (e.g. "2022-23")
    names a fiscal year by its END year (2023). Finance tables are named F{aa}{bb} for
    fiscal year 20aa-20bb and are published in the NEXT collection release, so binding the
    collection-year folder (table F2122 in the 2022-23 release) instead of FY2022-23
    (table F2223) is a silent off-by-one. Reject a selected finance table whose own fiscal
    year end does not match the requested one."""
    for start,two in re.findall(r'\b((?:19|20)\d{2})[-–/](\d{2})\b',question):
        end_year=int(start)//100*100+int(two)
        for s in sources:
            m=re.match(r'f(\d{2})(\d{2})(?:_|$)',str(s.get('table','')),re.I)
            if m and 2000+int(m[2])!=end_year:
                raise ValueError('Requested fiscal year '+start+'-'+two+' needs the finance table whose fiscal year ends '+str(end_year)+' (e.g. F'+start[2:]+two+'); the selected '+str(s['table']).upper()+' covers a different fiscal year. No release-year substitution.')


def bind(plan,question):
    import jsonschema
    jsonschema.validate(plan,QUERY_SCHEMA)
    if plan['version']!=2:raise ValueError('Use query-plan version 2.')
    if plan.get('population'):
        if plan['institutions']:raise ValueError('A population query cannot also contain named institutions.')
        from .populations import select,validate_request
        validate_request(plan['population'],question,max(plan['source_years']))
        populations={y:select(plan['population'],y) for y in plan['source_years']}
    else:populations={}
    if not (0 if populations else 1)<=len(plan['institutions'])<=30 or not 1<=len(plan['sources'])<=20:raise ValueError('Use named institutions or an explicit directory population and 1–20 source relations.')
    if len(plan['joins'])>19 or len(plan['expressions'])>24 or not 1<=len(plan['outputs'])<=40:raise ValueError('Query-plan bounds exceeded.')
    if len(set(plan['source_years']))!=len(plan['source_years']) or set(plan['source_years'])!={s['year'] for s in plan['sources']}:raise ValueError('Every selected source year must be represented exactly; no date substitution.')
    if plan['clarification_questions']:raise ValueError(' '.join(plan['clarification_questions']))
    source_ids=[s['id'] for s in plan['sources']]
    if len(set(source_ids))!=len(source_ids) or any(not IDENTIFIER.fullmatch(s) for s in source_ids):raise ValueError('Source identifiers must be unique simple identifiers.')
    references=[];filters=[]
    for s in plan['sources']:
        if len({a['id'] for a in s['aggregates']})!=len(s['aggregates']):raise ValueError('Aggregate IDs must be unique within a source.')
        if not 2015<=s['year']<=2024 or len(s['field_record_ids'])>40 or not (s['field_record_ids'] or s['group_by_record_ids'] or s['filters']) or len(s['filters'])>20 or len(s['aggregates'])>20:raise ValueError('Source relation bounds exceeded.')
        references.extend(s['field_record_ids']);references.extend(s['group_by_record_ids']);filters.extend(s['filters'])
        for a in s['aggregates']:
            if not IDENTIFIER.fullmatch(a['id']):raise ValueError('Aggregate identifiers must be simple identifiers.')
            references.extend(r for r in [a['record_id'],a['weight_record_id']] if r is not None)
    references.extend(f['record_id'] for f in filters)
    references=list(dict.fromkeys(references))
    if len(references)>100:raise ValueError('A plan may reference at most 100 exact source fields.')
    # Reuse exact schema/physical/code ownership and institution binding. No v1
    # semantic gate is applied: v2 validates relational grain below instead.
    packets=[]
    for s in plan['sources']:
        own=set(s['field_record_ids'])|set(s['group_by_record_ids'])|{f['record_id'] for f in s['filters']}
        own|={rid for a in s['aggregates'] for rid in [a['record_id'],a['weight_record_id']] if rid is not None}
        if len(own)>40:raise ValueError('A source relation may bind at most 40 fields.')
        adapter={'version':1,'institutions':plan['institutions'],'source_years':[s['year']],
            'requested_time':{'basis':'reporting_period','description':'Source-bound relational query'},
            'selections':[{'record_id':rid,'role':'measure'} for rid in own],'filters':s['filters'],
            'group_by_record_ids':[],'calculations':[],'joins':[],'output':'table','assumptions':plan['assumptions'],'clarification_questions':[]}
        packet=validate_proposal(adapter,question,population=plan.get('population'))
        if packet['validation']['blocks']:raise ValueError(packet['validation']['blocks'][0])
        packets.append(packet)
    evidence={'definition_evidence':list({d['record_id']:d for p in packets for d in p['definition_evidence']}.values()),
        'category_evidence':list({c['record_id']:c for p in packets for c in p['category_evidence']}.values()),
        'catalog_identity':packets[0]['catalog_identity'],'table_evidence':[t for p in packets for t in p['table_evidence']]}
    defs={d['record_id']:d for d in evidence['definition_evidence']};contexts={};descriptors={};codes={}
    with connection() as db:
        for rid,d in defs.items():
            t=contexts.setdefault((d['release_id'],d['table_name'].casefold()),table_context(d['release_id'],d['table_name']))
            descriptors[rid]=describe_field(d,t)
            # Financial balances retain genuine signed values; exact documented
            # missing codes take precedence over sign interpretation.
            codes[rid]=[dict(r) for r in db.execute('SELECT record_id,code_value,value_label FROM source.code_values WHERE release_id=? AND table_name=? COLLATE NOCASE AND variable_name=? COLLATE NOCASE',(d['release_id'],d['table_name'],d['variable_name']))]
        for s in plan['sources']:
            own=set(s['field_record_ids'])|set(s['group_by_record_ids'])|{f['record_id'] for f in s['filters']}
            own|={rid for a in s['aggregates'] for rid in [a['record_id'],a['weight_record_id']] if rid is not None}
            if any(int(defs[r]['release_id'][6:10])!=s['year'] or defs[r]['table_name'].casefold()!=s['table'].casefold() for r in own):raise ValueError('A source relation contains a field from a different physical table/release.')
            s_key=(next(defs[r]['release_id'] for r in own),s['table'].casefold())
            t=contexts[s_key];key=t['profile'].get('candidate_key') or []
            if 'UNITID' not in [k.upper() for k in key]:raise ValueError('The source lacks a usable institution grain.')
            if not period_set(t):raise ValueError('The source reporting period is unresolved.')
            if re.fullmatch(r'EF\d{4}A',s['table'],re.I) and re.search(r'undergrad',question,re.I):
                first=bool(re.search(r'first[ -]*(year|time)',question,re.I))
                ordinary=bool(re.search(r'race|ethnic|gender|sex|population|full.time|part.time',question,re.I)) and not re.search(r'transfer|continuing|non.degree|other degree|degree.seek',question,re.I)
                if first or ordinary:
                    levels=[rid for rid in own if defs[rid]['variable_name'].upper()=='EFALEVEL']
                    predicates=[f for f in s['filters'] if f['record_id'] in levels and f['operator'] in {'eq','in'}]
                    allowed_attendance=['All students']
                    full=bool(re.search(r'full[ -]*time',question,re.I));part=bool(re.search(r'part[ -]*time',question,re.I))
                    if full or part:allowed_attendance=(['Full-time students'] if full else [])+(['Part-time students'] if part else [])
                    suffix=', Undergraduate, Degree/certificate-seeking, First-time' if first else ', Undergraduate total'
                    expected={a+suffix for a in allowed_attendance}
                    labels={c['value_label'] for f in predicates for c in codes[f['record_id']] if c['code_value'] in f['values']}
                    if not labels or not labels<=expected:raise ValueError('The source enrollment population does not match the requested undergraduate/first-time/attendance scope.')
            if plan['time_basis']=='cohort':
                qyears=set(re.findall(r'(?:cohorts?|entered|entering)\s+(?:of\s+)?((?:19|20)\d{2})',question,re.I))
                selected_cohorts=cohort_years({'codes':codes,'definitions':defs,'contexts':contexts},[s])
                if not selected_cohorts:raise ValueError('Cohort timing needs source-coded cohort evidence; release year is not a cohort year.')
            for f in s['filters']:
                d=defs[f['record_id']]
                if f['operator'] not in {'eq','in'}:
                    if d['format']!='Cont' or d['data_type']!='N':raise ValueError('Range filters require a continuous numeric source field.')
                    if any(not math.isfinite(float(v)) for v in f['values']):raise ValueError('Range bounds must be finite numbers.')
            # Aggregates must not combine an unresolved key or overlapping domain.
            grouped=set(s['group_by_record_ids'])
            for col in key:
                if col.upper()=='UNITID':continue
                matching=[rid for rid in own if defs[rid]['variable_name'].upper()==col.upper()]
                if not matching:raise ValueError('Select or filter every source key dimension: '+col)
                rid=matching[0];domain=[f for f in s['filters'] if f['record_id']==rid and f['operator'] in {'eq','in'}]
                if rid in grouped:continue
                if not domain:raise ValueError('An aggregated or hidden key needs an explicit source category domain: '+col)
                values=set(domain[0]['values'])
                for f in domain[1:]:values&=set(f['values'])
                if not values:raise ValueError('Conflicting source category filters.')
                if len(values)>1 and (not s['aggregates'] or not leaf_domain(defs[rid],[c for c in codes[rid] if c['code_value'] in values])):
                    raise ValueError('The selected source domain may combine totals, ancestors or overlapping subgroups: '+col)
            for a in s['aggregates']:
                if a['operator']!='count' and a['record_id'] is None:raise ValueError('This aggregate needs a numerical field or distinct identifier.')
                if a['record_id'] is not None:
                    d=defs[a['record_id']];desc=descriptors[a['record_id']]
                    if a['operator']!='count_distinct' and (d['format']!='Cont' or d['data_type']!='N'):raise ValueError('Aggregate input is not a continuous numeric observation.')
                    if a['operator']=='sum' and not desc['additive'] and not signed_allowed(d):raise ValueError('Summing this field would add averages/rates or unresolved units.')
                if a['operator']=='weighted_mean':
                    rid=a['record_id'];weight=a['weight_record_id']
                    if weight is None or descriptors[weight]['unit'] not in {'students','employees','awards','items','FTE'}:raise ValueError('A weighted mean needs explicit compatible nonnegative count/exposure weights.')
                    if descriptors[rid]['unit']=='unknown':raise ValueError('Weighted-mean value units are unresolved.')
                    validate_salary_weights(defs,descriptors,rid,weight,question)
                    if descriptors[rid]['dimensions']!=descriptors[weight]['dimensions']:raise ValueError('Value and weight refer to different source subgroups.')
                    # Source counts paired with a supplied mean must describe the
                    # same contract/population; mismatched contract lengths fail.
                    def contract(d):return tuple(re.findall(r'\b(?:9|10|11|12)(?=[ -]month)|less.?than.?9',d['title'],re.I))
                    if contract(defs[rid]) and contract(defs[weight]) and contract(defs[rid])!=contract(defs[weight]):raise ValueError('Salary/value and weight contract periods differ.')
    periods=[p for t in contexts.values() for p in period_set(t)]
    if plan['time_basis']=='cohort':
        requested={int(y) for y in re.findall(r'(?:cohorts?|entered|entering)\s+(?:of\s+)?((?:19|20)\d{2})',question,re.I)}
        span=re.search(r'cohorts?\s+((?:19|20)\d{2})\s+(?:through|to|[-–])\s*((?:19|20)\d{2})',question,re.I)
        if span:requested.update(range(int(span[1]),int(span[2])+1))
        observed=cohort_years({'codes':codes,'definitions':defs,'contexts':contexts},plan['sources'])
        if requested and requested!=observed:raise ValueError('Cohort timing does not cover exactly the requested entering cohorts; release years cannot substitute for cohorts.')
    for kind,year in re.findall(r'\b(fall|fiscal(?: year)?|academic(?: year)?)\s+((?:19|20)\d{2})',question,re.I):
        expected_kind='fall' if kind.lower()=='fall' else 'fiscal' if kind.lower().startswith('fiscal') else 'academic'
        if not any(p['kind']==expected_kind and int(year)==(p['end'] if expected_kind=='fiscal' else p['start']) for p in periods):
            raise ValueError('Requested '+kind+' '+year+' is not supported by the selected source observation periods; no date substitution.')
    check_fiscal_year(plan['sources'],question)
    return {'plan':plan,'definitions':defs,'descriptors':descriptors,'contexts':contexts,'codes':codes,'evidence':evidence,'populations':populations}


def source_context(bound,s):
    return next(t for (release,table),t in bound['contexts'].items() if int(release[6:10])==s['year'] and table==s['table'].casefold())


def row_containment(b,left,right):
    if left['year']!=right['year'] or left['table'].casefold()!=right['table'].casefold():return False
    lf={f['record_id']:set(f['values']) for f in left['filters'] if f['operator'] in {'eq','in'}}
    rf={f['record_id']:set(f['values']) for f in right['filters'] if f['operator'] in {'eq','in'}}
    if lf==rf:return True
    if set(lf)!=set(rf):return False
    differences=[rid for rid in lf if lf[rid]!=rf[rid]]
    if len(differences)!=1:return False
    rid=differences[0]
    if len(lf[rid])!=1 or len(rf[rid])!=1:return False
    n=next(c for c in b['codes'][rid] if c['code_value'] in lf[rid]);d=next(c for c in b['codes'][rid] if c['code_value'] in rf[rid])
    definition=b['definitions'][rid];table=source_context(b,left)
    nd=describe_field({**definition,'title':n['value_label'],'format':'Cont','data_type':'N'},table)
    dd=describe_field({**definition,'title':d['value_label'],'format':'Cont','data_type':'N'},table)
    if subset(nd,dd,{**definition,'title':n['value_label']},{**definition,'title':d['value_label']})[0]:return True
    # Source-defined completers are members of the same adjusted cohort, not
    # arbitrary differently filtered rows. Require the same subcohort prefix.
    doc=definition['long_description'].casefold()
    np=re.split(r'\bcompleters?\b',n['value_label'],flags=re.I)[0]
    dp=re.split(r'\badjusted cohort\b',d['value_label'],flags=re.I)[0]
    return (bool(re.search(r'\bcompleters?\b',n['value_label'],re.I)) and 'adjusted cohort' in d['value_label'].casefold()
        and words(np)==words(dp) and 'within a cohort' in doc and 'exclusions' in doc)


def documented_count_share(b,left,right,numerator,denominator):
    """Annual source count relationships, never precomputed statistical answers."""
    if left['year']!=right['year'] or left['table'].casefold()!=right['table'].casefold():return False
    n,d=b['definitions'][numerator],b['definitions'][denominator]
    pair=(n['variable_name'].upper(),d['variable_name'].upper());table=left['table'].upper()
    if any(b['descriptors'][rid]['unit']!='students' for rid in [numerator,denominator]):return False
    if re.fullmatch(r'EF\d{4}D',table) and pair in {('RET_NMF','RRFTCTA'),('RET_NMP','RRPTCTA')}:
        return 'cohort' in n['long_description'].lower() and 'cohort' in d['long_description'].lower()
    if re.fullmatch(r'SFA\d{4}(?:_P1)?',table) and pair in {('ANYAIDN','SCUGFFN'),('UPGRNTN','SCUGRAD'),('UFLOANN','SCUGRAD')}:
        return 'undergrad' in n['long_description'].lower() and 'undergrad' in d['long_description'].lower()
    if re.fullmatch(r'ADM\d{4}',table) and pair in {('ADMSSN','APPLCN'),('ENRLT','ADMSSN')}:return True
    if re.fullmatch(r'GR\d{4}_L2',table) and pair==('LINE_11','LINE_50'):return True
    if re.fullmatch(r'OM\d{4}',table) and pair==('OMAWDN8','OMACHRT'):
        # OM explicitly defines this award count as a subset of the adjusted
        # entering cohort, measured eight years later. Verify annual evidence
        # rather than treating different cohort/outcome dates as unrelated.
        year=left['year'];cohort=f'{year-8}-{str(year-7)[-2:]}'
        return (cohort in d['title'] and 'adjusted' in d['title'].lower()
            and f'August 31, {year}' in n['title'] and '8 years' in n['title']
            and 'adjusted cohort' in n['long_description'].lower()
            and 'reporting institution' in n['long_description'].lower())
    return False


def validate_salary_weights(definitions,descriptors,value,weight,question):
    """A salary mean and its exposure count must describe the same staff."""
    a=definitions[value];w=definitions[weight]
    if not re.search(r'\bsalar(?:y|ies)\b',a['title'],re.I):return
    if descriptors[weight]['unit']!='employees':raise ValueError('Salary weights require staff counts, not another salary or unrelated exposure unit.')
    if (a['release_id'],a['table_name'].casefold())!=(w['release_id'],w['table_name'].casefold()):
        raise ValueError('Salary value and weight require the same inspected source population/table and release.')
    if descriptors[value]['dimensions']!=descriptors[weight]['dimensions']:
        raise ValueError('Salary value and weight populations differ (including gender); explicit weighting wording cannot authorize incompatible staff counts.')
    if bool(re.search(r'\bequated\b',a['title'],re.I))!=bool(re.search(r'\bequated\b',w['title'],re.I)):
        raise ValueError('Equated and actual-contract salary/weight populations differ; do not substitute actual nine-month counts for equated staff exposure.')
    def contract(d):return tuple(re.findall(r'\b(?:9|10|11|12)(?=[ -]month)|less.?than.?9',d['title'],re.I))
    if contract(a)!=contract(w):raise ValueError('Salary/value and weight contract periods differ.')
    gender=descriptors[value]['dimensions'].get('gender')
    if gender not in {None,'all'} and not re.search(r'\b(men|women|males?|females?|gender|sex)\b',question,re.I):
        raise ValueError('The requested salary population is not gender-restricted; do not substitute a gender-specific salary and weight.')


def inspect(plan,question):
    from copy import deepcopy
    plan=deepcopy(plan)
    # Repair only a uniquely bound alias-prefix typo, never a field selection.
    # Source s1 requires fs1_<record>, a common representation slip is f1_<record>.
    valid={field_ref(r,s['id']) for s in plan['sources'] for r in s['field_record_ids']+s['group_by_record_ids']}
    changed=[]
    def canonical(ref):
        if ref in valid:return ref
        m=re.fullmatch(r'f(\d+)_(\d+)',ref)
        candidate='fs'+m[1]+'_'+m[2] if m else ''
        if candidate in valid:changed.append((ref,candidate));return candidate
        return ref
    for e in plan['expressions']:
        e['inputs']=[canonical(r) for r in e['inputs']];e['group_by_references']=[canonical(r) for r in e['group_by_references']]
    for o in plan['outputs']:o['reference']=canonical(o['reference'])
    if changed:plan['assumptions'].append('Normalized unambiguous source-alias references: '+str(list(dict.fromkeys(changed))))
    if plan.get('population') and plan['missing_policy']=='complete_cases':
        normalized=False
        for j in plan['joins']:
            if j['how']=='inner' and j['missing_keys']=='retain':j['how']='left';normalized=True
        if normalized:plan['assumptions'].append('Retained unmatched source rows to audit complete-case exclusions instead of dropping them in an inner join.')
    if plan['joins'] and len(plan['joins'])==len(plan['sources'])-1:
        order=[plan['joins'][0]['left_source']]
        for j in plan['joins']:
            if j['left_source'] not in order or j['right_source'] in order:break
            order.append(j['right_source'])
        if len(order)==len(plan['sources']) and set(order)=={s['id'] for s in plan['sources']}:
            plan['sources']=sorted(plan['sources'],key=lambda s:order.index(s['id']))
    if plan.get('annual_years'):
        from .populations import annual_plans
        annual_question=re.sub(r'\b(?:19|20)\d{2}\b','',question)
        checked=[inspect(p,annual_question) for p in annual_plans(plan)]
        return checked[0]
    """Metadata preflight. Cardinalities and row-domain checks repeat at runtime."""
    report('Validating source selections, relationships and calculations…')
    b=bind(plan,question);available={'institution':{'unit':'identifier','sources':set(),'field':None,'aggregation':None}};source_by={s['id']:s for s in plan['sources']}
    if any(s['group_by_record_ids'] for s in plan['sources']) and not re.search(r'how many|\bcounts?\b|\bnumber\b|distribution|frequency|percentage|percent|share',question,re.I):
        if all(o['reference'].startswith('a') for o in plan['outputs']) and all(a['operator'] in {'count','count_distinct'} for s in plan['sources'] for a in s['aggregates']):
            raise ValueError('A dummy record count does not answer a categorical lookup. Use submit_observation_plan for direct source responses.')
    for s in plan['sources']:
        for rid in (s['group_by_record_ids'] if s['aggregates'] else s['field_record_ids']+s['group_by_record_ids']):
            available[field_ref(rid,s['id'])]={'unit':b['descriptors'][rid]['unit'],'sources':{s['id']},'field':rid,'aggregation':None}
        for a in s['aggregates']:
            available[aggregate_ref(s['id'],a['id'])]={'unit':'records' if a['operator'] in {'count','count_distinct'} else b['descriptors'][a['record_id']]['unit'],'sources':{s['id']},'field':a['record_id'],'aggregation':a['operator']}
    seen={plan['sources'][0]['id']}
    for j in plan['joins']:
        if j['left_source'] not in seen or j['right_source'] in seen or j['right_source'] not in source_by:raise ValueError('Joins must form an ordered connected source tree.')
        if not 1<=len(j['left_columns'])<=4 or len(j['left_columns'])!=len(j['right_columns']):raise ValueError('Join keys must be paired.')
        left=source_by[j['left_source']];right=source_by[j['right_source']]
        for s,cols in [(left,j['left_columns']),(right,j['right_columns'])]:
            with connection() as db:
                for col in cols:
                    if not db.execute('SELECT 1 FROM fields WHERE release_id=? AND table_name=? COLLATE NOCASE AND column_name=? COLLATE NOCASE',(source_context(b,s)['release_id'],s['table'],col)).fetchone():raise ValueError('A join key is absent from its source relation.')
        if [c.upper() for c in j['left_columns']].count('UNITID')!=1 or [c.upper() for c in j['right_columns']].count('UNITID')!=1:raise ValueError('Institution fact joins must include UNITID; institution Cartesian products are forbidden.')
        for lc,rc in zip(j['left_columns'],j['right_columns']):
            if lc.upper()=='UNITID' or rc.upper()=='UNITID':
                if lc.upper()!=rc.upper():raise ValueError('An institution identifier cannot join to a category or measure.')
                continue
            ldefs=[d for d in b['definitions'].values() if int(d['release_id'][6:10])==left['year'] and d['table_name'].casefold()==left['table'].casefold() and d['variable_name'].casefold()==lc.casefold()]
            rdefs=[d for d in b['definitions'].values() if int(d['release_id'][6:10])==right['year'] and d['table_name'].casefold()==right['table'].casefold() and d['variable_name'].casefold()==rc.casefold()]
            if len(ldefs)!=1 or len(rdefs)!=1 or words(ldefs[0]['title'])!=words(rdefs[0]['title']):raise ValueError('Non-institution join keys need matching documented meanings.')
            lcodes={c['code_value']:words(c['value_label']) for c in b['codes'][ldefs[0]['record_id']]};rcodes={c['code_value']:words(c['value_label']) for c in b['codes'][rdefs[0]['record_id']]}
            if any(lcodes[c]!=rcodes[c] for c in set(lcodes)&set(rcodes)):raise ValueError('Join category definitions changed; an explicit reviewed crosswalk is required.')
        lp=period_set(source_context(b,left));rp=period_set(source_context(b,right))
        directory_decoration=(source_context(b,left)['family'].upper().startswith('HD') or source_context(b,right)['family'].upper().startswith('HD')) and left['year']==right['year']
        if j['period_alignment']=='same_period' and not directory_decoration and [(p['kind'],p['start'],p['end']) for p in lp]!=[(p['kind'],p['start'],p['end']) for p in rp]:raise ValueError('Same-period join sources have different observation periods.')
        if j['period_alignment']=='successive_periods':
            if lp[0]['kind']!=rp[0]['kind'] or rp[0]['end']-lp[0]['end']!=1:raise ValueError('Successive-period sources are not the same period type in adjacent years.')
        if j['period_alignment']=='explicit_comparison' and plan['time_basis']!='explicit_comparison':raise ValueError('Different periods require an explicit comparison interpretation.')
        seen.add(j['right_source'])
    if len(seen)!=len(source_by):raise ValueError('Every source must be connected by a validated join; no implicit joins.')
    for e in plan['expressions']:
        if not IDENTIFIER.fullmatch(e['id']) or 'x'+e['id'] in available:raise ValueError('Expression IDs must be unique simple identifiers.')
        if any(ref not in available for ref in e['inputs']):raise ValueError('Unknown or forward expression reference; calculation cycles are forbidden. Available references: '+', '.join(sorted(available)[:15]))
        if e['operator'] in {'sum','mean','weighted_mean','count','min','max'}:
            if len(e['inputs'])!=(2 if e['operator']=='weighted_mean' else 1):raise ValueError('This reducer has the wrong number of inputs.')
            if any(ref not in available for ref in e['group_by_references']):raise ValueError('A reducer group references an absent field.')
            a=available[e['inputs'][0]]
            if a['unit'] in {'unknown','identifier'} and e['operator']!='count':raise ValueError('Reducer input units are unresolved.')
            if e['operator']=='sum' and a['field'] is not None and a['unit']!='FTE' and not b['descriptors'][a['field']]['additive'] and not signed_allowed(b['definitions'][a['field']]):raise ValueError('Cannot sum nonadditive values.')
            if e['operator']=='sum' and a['unit'] in {'percent','ratio','percentage points'}:raise ValueError('Cannot sum rates or ratios; use a pooled calculation from source counts.')
            if e['operator'] in {'sum','mean','weighted_mean','count'}:
                for sid in a['sources']:
                    src=source_by[sid]
                    for rid in src['group_by_record_ids']:
                        if field_ref(rid,sid) in e['group_by_references']:continue
                        domain=[f for f in src['filters'] if f['record_id']==rid and f['operator'] in {'eq','in'}]
                        selected=[c for c in b['codes'][rid] if domain and c['code_value'] in domain[0]['values']]
                        if not selected or not leaf_domain(b['definitions'][rid],selected):raise ValueError('Reducing grouped source rows needs an explicit disjoint category domain; totals and subgroups cannot be combined.')
            if e['operator']=='weighted_mean':
                weight=available[e['inputs'][1]]
                if weight['unit'] not in {'students','employees','awards','items','FTE','monetary amount'}:raise ValueError('Weights need explicit count/exposure units.')
                if a['field'] is not None and weight['field'] is not None:
                    validate_salary_weights(b['definitions'],b['descriptors'],a['field'],weight['field'],question)
                    if b['descriptors'][a['field']]['dimensions']!=b['descriptors'][weight['field']]['dimensions'] and not re.search(r'weighted by|using .*weights?',question,re.I):raise ValueError('Value and weight subgroups differ; the weighting interpretation must be explicit.')
            if e['operator']=='mean' and a['unit']=='percent' and not re.search(r'unweighted|simple mean|mean of .*rates',question,re.I):raise ValueError('Specify an unweighted mean of institutional rates or a pooled rate from counts; these are different methods.')
            available['x'+e['id']]={'unit':'records' if e['operator']=='count' else a['unit'],'sources':set().union(*(available[ref]['sources'] for ref in e['inputs'])),'field':a['field'] if e['operator']=='sum' else None,'aggregation':e['operator']}
            if e['operator']=='sum' and a.get('share_total') is not None:available['x'+e['id']]['share_total']=a['share_total']
            continue
        if len(e['inputs'])!=2 or e['group_by_references']:raise ValueError('Binary arithmetic has exactly two inputs and no reducer grouping.')
        a,c=[available[r] for r in e['inputs']];op=e['operator']
        if op=='multiply' and a['field'] is not None and c['field'] is not None:
            for value,weight in ((a,c),(c,a)):
                if weight['unit']=='employees':validate_salary_weights(b['definitions'],b['descriptors'],value['field'],weight['field'],question)
        if a['field'] is not None and c['field'] is not None:
            known_pair=documented_count_share(b,source_by[next(iter(a['sources']))],source_by[next(iter(c['sources']))],a['field'],c['field'])
            if b['descriptors'][a['field']]['field_time_qualifiers']!=b['descriptors'][c['field']]['field_time_qualifiers'] and plan['time_basis']!='explicit_comparison' and not known_pair:raise ValueError('Field-specific observation periods differ; declare an explicit period comparison.')
        if op in {'add','subtract','percent_change'} and (a['unit']=='unknown' or a['unit']!=c['unit']):raise ValueError('This operation requires compatible known units.')
        if op=='percent_change':
            dates=re.search(r'from\s+(?:(?:fall|fiscal|academic)(?: year)?\s+)?((?:19|20)\d{2})\s+to\s+(?:(?:fall|fiscal|academic)(?: year)?\s+)?((?:19|20)\d{2})',question,re.I)
            if dates:
                ayears={p['start'] for sid in a['sources'] for p in period_set(source_context(b,source_by[sid]))}
                cyears={p['start'] for sid in c['sources'] for p in period_set(source_context(b,source_by[sid]))}
                if ayears!={int(dates[2])} or cyears!={int(dates[1])}:raise ValueError('percent_change inputs must be [NEW value, OLD baseline], matching the requested from/to periods.')
            if a['field'] is not None and c['field'] is not None and words(b['definitions'][a['field']]['title'])!=words(b['definitions'][c['field']]['title']):raise ValueError('Percent change needs the same documented measure in both periods.')
        if op=='percent':
            partition_share=(a.get('share_total') is not None and a['share_total']==c['field'] and a['sources']==c['sources'])
            if not partition_share and (a['field'] is None or c['field'] is None):raise ValueError('A percent share needs a source-proven numerator/denominator relationship; use divide for an explicit general ratio.')
            if a['aggregation']!=c['aggregation']:raise ValueError('Numerator and denominator aggregate methods differ.')
            left_source=source_by[next(iter(a['sources']))];right_source=source_by[next(iter(c['sources']))]
            row_ok=row_containment(b,left_source,right_source)
            if partition_share:ok,reason=True,'Verified distance-education partition.'
            else:
                ok,reason,_=subset(b['descriptors'][a['field']],b['descriptors'][c['field']],b['definitions'][a['field']],b['definitions'][c['field']])
                ok=ok or documented_count_share(b,left_source,right_source,a['field'],c['field'])
            if not row_ok or not (ok or a['field']==c['field']):raise ValueError(reason if not ok else 'Numerator and denominator row populations do not establish containment.')
        if 'unknown' in {a['unit'],c['unit']}:raise ValueError('Arithmetic units are unresolved; direct retrieval remains available.')
        unit='percent' if op in {'percent','percent_change'} else 'percentage points' if op=='subtract' and a['unit']=='percent' else a['unit'] if op in {'add','subtract'} else 'ratio' if op=='divide' and a['unit']==c['unit'] else a['unit']+' / '+c['unit'] if op=='divide' else a['unit']+' × '+c['unit']
        available['x'+e['id']]={'unit':unit,'sources':a['sources']|c['sources'],'field':None,'aggregation':None}
        if op=='add' and a['field'] is not None and c['field'] is not None and a['sources']==c['sources'] and len(a['sources'])==1 and a['aggregation'] is None and c['aggregation'] is None:
            src=source_by[next(iter(a['sources']))]
            if src.get('reconcile_distance_partition') and re.fullmatch(r'EF\d{4}A_DIST',src['table'],re.I) and {b['definitions'][r]['variable_name'] for r in [a['field'],c['field']]}=={'EFDEEXC','EFDESOM'}:
                total=next((rid for rid in src['field_record_ids'] if b['definitions'][rid]['variable_name']=='EFDETOT'),None)
                if total is not None:available['x'+e['id']]['share_total']=total
    if any(o['reference'] not in available for o in plan['outputs']):raise ValueError('An output refers to an absent or hidden source value.')
    for out in plan['outputs']:
        meta=available[out['reference']]
        if meta['field'] is not None and meta['aggregation'] is None and b['definitions'][meta['field']]['format']!='Cont':raise ValueError('Categorical codes must be group labels, not numerical measure outputs. Include the field in group_by_record_ids and remove it from outputs.')
    if len({o['reference'] for o in plan['outputs']})!=len(plan['outputs']):raise ValueError('Output references must be unique.')
    if plan.get('population'):
        reduced=set()
        for e in plan['expressions']:
            ref='x'+e['id']
            if e['operator'] in {'sum','mean','weighted_mean','count','min','max'} and 'institution' not in e['group_by_references']:reduced.add(ref)
            elif all(r in reduced for r in e['inputs']):reduced.add(ref)
        if any(o['reference'] not in reduced for o in plan['outputs']):raise ValueError('Population outputs must be aggregates; individual institution rows cannot stand in for a national result.')
        if re.search(r'by sector|by state|by control',question,re.I):
            expected='SECTOR' if re.search('by sector',question,re.I) else 'FIPS' if re.search('by state',question,re.I) else 'CONTROL'
            refs={field_ref(rid,s['id']) for s in plan['sources'] for rid in s['group_by_record_ids'] if b['definitions'][rid]['variable_name'].upper()==expected}
            if not refs or any(not refs.intersection(e['group_by_references']) for e in plan['expressions'] if e['operator'] in {'sum','mean','weighted_mean','count','min','max'}):raise ValueError('The aggregate plan dropped the requested directory grouping.')
    if plan.get('population'):
        from .populations import check
        check(plan)
    b['available']=available
    return b


def reconcile_distance_counts(values,raw):
    """A closed, nonnegative count partition can prove blank components zero."""
    parts=['EFDEEXC','EFDESOM','EFDENON'];total=values['EFDETOT']
    known=[v for v in values.values() if v is not None]
    if any(v<0 or not float(v).is_integer() for v in known):raise ValueError('Distance-education partition requires nonnegative whole student counts.')
    if total is None:return []
    observed=sum(values[c] for c in parts if values[c] is not None)
    if observed>total or (all(values[c] is not None for c in parts) and observed!=total):raise ValueError('Distance-education source categories do not reconcile to total enrollment.')
    missing=[c for c in parts if values[c] is None]
    if observed!=total or any(raw[c] is not None and str(raw[c]).strip()!='' for c in missing):return []
    for c in missing:values[c]=0.0
    return missing


def execute_source(b,s,question):
    report(f"Reading source data for {s['year']}…")
    defs=b['definitions'];t=source_context(b,s);sid=s['id']
    ids=set(s['field_record_ids'])|set(s['group_by_record_ids'])|{f['record_id'] for f in s['filters']}
    ids|={rid for a in s['aggregates'] for rid in [a['record_id'],a['weight_record_id']] if rid is not None}
    keys=t['profile']['candidate_key'];columns=list(dict.fromkeys(keys+[defs[r]['variable_name'] for r in ids]))
    unitids=b['populations'][s['year']]['unitids'] if b['populations'] else institutions(b['plan']['institutions'],s['year'])
    if b['populations']:
        population=b['populations'][s['year']]
        params=list(population['parameters']);where=['"UNITID" IN ('+population['directory_sql'].replace('SELECT UNITID,INSTNM','SELECT UNITID')+')']
    else:params=list(unitids);where=['"UNITID" IN ('+','.join('?' for _ in unitids)+')']
    missing_codes={rid:{r['code_value'] for r in b['codes'][rid] if re.search(r'not applicable|not reported|missing|suppressed|not available',r['value_label'],re.I)} for rid in ids}
    for f in s['filters']:
        col=quote(defs[f['record_id']]['variable_name']);op=f['operator']
        if op in {'eq','in'}:
            where.append(col+' IN ('+','.join('?' for _ in f['values'])+')');params.extend(f['values'])
        else:
            # A Python SQLite function validates full numeric strings before
            # comparison, avoiding SQLite TEXT affinity/invalid-text-to-zero bugs.
            col='number_'+str(f['record_id'])+'('+col+')'
            where.append(col+' BETWEEN ? AND ?' if op=='between' else col+' '+{'gt':'>','gte':'>=','lt':'<','lte':'<='}[op]+' ?')
            params.extend(float(v) for v in f['values'])
    sql='SELECT '+','.join(quote(c)+' AS '+quote(c) for c in columns)+' FROM '+quote(s['table'])+' WHERE '+' AND '.join(where)+' LIMIT '+str(ROW_LIMIT+1)
    path=annual_path(s['year'])
    with readonly(path,deadline_seconds=60 if b['populations'] else 20) as db:
        for rid in ids:db.create_function('number_'+str(rid),1,lambda v,rid=rid:number(v,defs[rid],missing_codes[rid]),deterministic=True)
        raw=[dict(r) for r in db.execute(sql,params).fetchmany(ROW_LIMIT+1)]
        names={} if b['populations'] else {r[0]:r[1] for r in db.execute('SELECT UNITID,INSTNM FROM '+quote('HD'+str(s['year']))+' WHERE UNITID IN ('+','.join('?' for _ in unitids)+')',unitids)}
    if len(raw)>ROW_LIMIT:raise ValueError('Source row limit reached; narrow the population or category domain before aggregation.')
    # Row-key uniqueness is checked after selection, independently of profiling.
    tuples=[tuple(r[k] for k in keys) for r in raw]
    if len(tuples)!=len(set(tuples)):raise ValueError('Selected source keys are not unique; no result was published.')
    partition_ids={defs[r]['variable_name']:r for r in ids}
    partition_columns=['EFDEEXC','EFDESOM','EFDENON','EFDETOT']
    reconcile=s.get('reconcile_distance_partition',False)
    if reconcile:
        expected={'EFDEEXC':'Students enrolled exclusively in distance education courses','EFDESOM':'Students enrolled in some but not all distance education courses','EFDENON':'Student not enrolled in any distance education courses','EFDETOT':'All students enrolled'}
        if not re.fullmatch(r'EF\d{4}A_DIST',s['table'],re.I) or any(c not in partition_ids or defs[partition_ids[c]]['title'].strip().casefold()!=title.casefold() for c,title in expected.items()):
            raise ValueError('Distance partition reconciliation requires the exact documented exclusive/some/none/total source fields.')
    data=[];inferred=[]
    for r in raw:
        item={key_ref(sid,col):r[col] for col in keys}
        item['__unitid']=r['UNITID']
        for rid in ids:
            d=defs[rid];v=r[d['variable_name']]
            item[field_ref(rid,sid)]=number(v,d,missing_codes[rid]) if d['format']=='Cont' and d['data_type']=='N' else v
            item[key_ref(sid,d['variable_name'])]=v
        if reconcile:
            values={c:item[field_ref(partition_ids[c],sid)] for c in partition_columns}
            filled=reconcile_distance_counts(values,r)
            if filled:
                inferred.append({'unitid':r['UNITID'],'source_key':{k:r[k] for k in keys},'fields':filled})
                for c in filled:item[field_ref(partition_ids[c],sid)]=values[c]
        data.append(item)
    frame=pd.DataFrame(data,columns=list(dict.fromkeys(['__unitid']+[key_ref(sid,c) for c in columns]+[field_ref(r,sid) for r in ids])))
    metadata={field_ref(r,sid):{'record_ids':[r],'unit':b['descriptors'][r]['unit'],'sources':{sid},'grain':[key_ref(sid,k) for k in keys],'periods':period_set(t)} for r in ids}
    audit={'source_id':sid,'database':str(path),'sql':sql,'parameters':params,'selected_rows':len(frame),'raw_keys':keys,'row_limit':ROW_LIMIT,
        'requested_unitids':unitids,'missing_unitids':sorted(set(unitids)-{r['UNITID'] for r in raw}),'missing_codes':{str(k):sorted(v) for k,v in missing_codes.items()}}
    if reconcile:audit['partition_reconciliation']={'method':'Exclusive + some + no distance education = total; infer blank zeros only when nonnegative reported components already equal total. Original source cells are unchanged.','derived_zero_cells':sum(len(r['fields']) for r in inferred),'rows':inferred}
    if s['aggregates']:
        groups=['__unitid']+[field_ref(r,sid) for r in s['group_by_record_ids']]
        expected_rows=1
        for col in keys:
            rid=next((rid for rid in ids if defs[rid]['variable_name'].upper()==col.upper()),None)
            if col.upper()=='UNITID' or rid in s['group_by_record_ids']:continue
            domains=[set(f['values']) for f in s['filters'] if f['record_id']==rid and f['operator'] in {'eq','in'}]
            if domains:expected_rows*=len(set.intersection(*domains))
        output=[]
        for group,part in frame.groupby(groups,dropna=False,sort=False):
            group=group if isinstance(group,tuple) else (group,);row=dict(zip(groups,group))
            for a in s['aggregates']:
                ref=aggregate_ref(sid,a['id']);rid=a['record_id'];op=a['operator'];values=part[field_ref(rid,sid)] if rid is not None else None
                valid=values.notna() if values is not None else pd.Series(True,index=part.index)
                weights=part[field_ref(a['weight_record_id'],sid)] if a['weight_record_id'] is not None else None
                if weights is not None:
                    if (weights.dropna()<0).any():raise ValueError('Weights must be nonnegative.')
                    valid=(valid|(weights==0))&weights.notna()
                if b['plan']['missing_policy']=='propagate' and (not valid.all() or len(part)<expected_rows):value=None
                elif op=='count':value=len(part)
                elif op=='count_distinct':value=values[valid].nunique()
                elif not valid.any():value=None
                elif op=='weighted_mean':
                    denominator=float(weights[valid].sum());value=float((values[valid].fillna(0)*weights[valid]).sum()/denominator) if denominator>0 else None
                else:value=getattr(values[valid],op)()
                row[ref]=float(value) if value is not None and pd.notna(value) else None
                row[ref+'__available']=int(valid.sum());row[ref+'__requested']=max(len(part),expected_rows)
                metadata[ref]={'record_ids':[r for r in [rid,a['weight_record_id']] if r is not None],'unit':b['available'][ref]['unit'],'sources':{sid},'grain':groups,'periods':period_set(t)}
            row[key_ref(sid,'UNITID')]=row['__unitid']
            for rid in s['group_by_record_ids']:row[key_ref(sid,defs[rid]['variable_name'])]=row[field_ref(rid,sid)]
            output.append(row)
        frame=pd.DataFrame(output,columns=list(dict.fromkeys(groups+[key_ref(sid,'UNITID')]+[key_ref(sid,defs[r]['variable_name']) for r in s['group_by_record_ids']]+[c for a in s['aggregates'] for c in [aggregate_ref(sid,a['id']),aggregate_ref(sid,a['id'])+'__available',aggregate_ref(sid,a['id'])+'__requested']])))
        # Hidden raw fields cannot be used after aggregation.
        metadata={ref:v for ref,v in metadata.items() if ref in frame.columns}
    return frame,metadata,audit,names


def execute(plan,question):
    if plan.get('annual_years'):
        from .populations import execute_annual
        return execute_annual(plan,question)
    started=time.perf_counter();b=inspect(plan,question);plan=b['plan'];validated=time.perf_counter()
    from .intent_checks import check_plan,stamp
    intent_check=check_plan(plan,question,{**b['evidence'],'field_semantics':{str(k):v for k,v in b['descriptors'].items()},'output_units':[b['available'][o['reference']]['unit'] for o in plan['outputs']]})
    frames={};metadata={};audits=[];names={};join_audits=[]
    for s in plan['sources']:
        frame,meta,audit,source_names=execute_source(b,s,question)
        frames[s['id']]=frame;metadata.update(meta);audits.append(audit);names.update(source_names)
    current=frames[plan['sources'][0]['id']]
    for j in plan['joins']:
        report('Combining sources and checking matching records…')
        right=frames[j['right_source']].drop(columns=['__unitid'],errors='ignore')
        lk=[key_ref(j['left_source'],c) for c in j['left_columns']];rk=[key_ref(j['right_source'],c) for c in j['right_columns']]
        if any(k not in current for k in lk) or any(k not in right for k in rk):raise ValueError('A join key was removed by source aggregation; include it in source grouping.')
        if current[lk].isna().any().any() or right[rk].isna().any().any():raise ValueError('Null join keys require a source-specific matching policy.')
        if right.duplicated(rk).any() or j['cardinality']=='one_to_one' and current.duplicated(lk).any():raise ValueError('Join cardinality disagrees with the selected source grains; aggregate first or use complete keys.')
        for l,r in zip(lk,rk):
            # Physical UNITID storage can differ (INTEGER/REAL/TEXT); preserve
            # exact identifier values, never turn an invalid ID into zero.
            if l.endswith('__UNITID') and r.endswith('__UNITID'):
                current[l]=current[l].map(lambda v:str(int(v)))
                right[r]=right[r].map(lambda v:str(int(v)))
        joined=current.merge(right,left_on=lk,right_on=rk,how='left',validate=j['cardinality'],indicator=True)
        unmatched=int((joined['_merge']=='left_only').sum())
        if unmatched and (j['missing_keys']=='error' or j['how']=='inner'):raise ValueError('Join would drop unmatched source observations; use an explicit retained-missing policy.')
        if len(joined)!=len(current):raise ValueError('Join multiplied the source row count; no result was published.')
        current=joined.drop(columns='_merge');join_audits.append({**j,'left_rows':len(current),'unmatched_left_rows':unmatched,'result_rows':len(joined),'cardinality_verified':True})
    current['institution']=current['__unitid']
    metadata['institution']={'record_ids':[],'unit':'identifier','sources':set(frames),'grain':['__unitid'],'periods':[]}
    expression_nodes={'x'+e['id']:e for e in plan['expressions']}
    pooled_inputs={}
    for node in plan['expressions']:
        if node['operator'] not in {'percent','divide'}:continue
        children=[expression_nodes.get(ref) for ref in node['inputs']]
        if all(c and c['operator']=='sum' and len(c['inputs'])==1 for c in children):
            if children[0]['group_by_references']!=children[1]['group_by_references']:raise ValueError('Pooled numerator and denominator groups must agree.')
            for ref in node['inputs']:pooled_inputs[ref]=[c['inputs'][0] for c in children]
    for e in plan['expressions']:
        report('Calculating results from the validated data…')
        op=e['operator'];ref='x'+e['id']
        if op in {'sum','mean','weighted_mean','count','min','max'}:
            grouping=['__unitid' if r=='institution' else r for r in e['group_by_references']]
            for inp in e['inputs']:
                grain=metadata[inp]['grain']
                if op not in {'min','max'} and grain and current.loc[current[inp].notna()].duplicated(grain).any():raise ValueError('A join or earlier reducer replicated this input grain; re-aggregate before joining rather than double-count it.')
            current[ref]=None
            current[ref+'__available']=None;current[ref+'__requested']=None
            contributors={}
            parts=current.groupby(grouping,dropna=False,sort=False).groups.values() if grouping else [current.index]
            for indices in parts:
                part=current.loc[indices];values=part[e['inputs'][0]];valid=values.notna()
                if b['populations'] and ref in pooled_inputs:
                    for pair_input in pooled_inputs[ref]:
                        if pair_input not in part:raise ValueError('Pooled pair inputs must be evaluated before their reducers.')
                        valid &= part[pair_input].notna()
                weights=part[e['inputs'][1]] if op=='weighted_mean' else None
                if weights is not None:
                    if (weights.dropna()<0).any():raise ValueError('Weights must be nonnegative.')
                    valid=(valid|(weights==0))&weights.notna()
                missing_institutions=set().union(*(set(a['missing_unitids']) for a in audits if a['source_id'] in b['available'][ref]['sources'])) if '__unitid' not in grouping and not b['populations'] else set()
                if plan['missing_policy']=='propagate' and (not valid.all() or missing_institutions):value=None
                elif op=='count':value=int(valid.sum())
                elif not valid.any():value=None
                elif op=='weighted_mean':value=float((values[valid].fillna(0)*weights[valid]).sum()/weights[valid].sum()) if weights[valid].sum()>0 else None
                else:value=float(getattr(values[valid],op)())
                current.loc[indices,ref]=value
                current.loc[indices,ref+'__available']=int(valid.sum())
                current.loc[indices,ref+'__requested']=len(part)+len(missing_institutions)
                key=tuple(str(part.iloc[0][g]) for g in grouping)
                contributors[key]=sorted(set(int(v) for v in part.loc[valid,'__unitid']))
            metadata[ref]={'record_ids':list(dict.fromkeys(r for inp in e['inputs'] for r in metadata[inp]['record_ids'])),'unit':b['available'][ref]['unit'],
                'sources':set().union(*(metadata[inp]['sources'] for inp in e['inputs'])),'grain':grouping,'periods':[p for inp in e['inputs'] for p in metadata[inp]['periods']],'contributors':contributors}
            continue
        a,c=[current[r] for r in e['inputs']]
        if b['populations'] and op in {'divide','percent'}:
            am,cm=[metadata[r] for r in e['inputs']]
            if am.get('contributors') is not None and cm.get('contributors') is not None and am['contributors']!=cm['contributors']:
                raise ValueError('Pooled numerator and denominator must use the same complete reporting-unit population. Inspect missing pairs before publishing this rate.')
        valid=a.notna()&c.notna()
        if op in {'divide','percent','percent_change'}:valid &= c!=0
        if op=='percent_change' and (c[valid]<0).any():raise ValueError('Percentage change from a negative baseline needs an explicit alternative method; ordinary growth is undefined here.')
        if op=='percent' and ((a[valid]<0)|(c[valid]<0)|(a[valid]>c[valid])).any():raise ValueError('A source category is outside its total; no percentage was published.')
        values=a+c if op=='add' else a-c if op=='subtract' else a*c if op=='multiply' else (a-c)/c*100 if op=='percent_change' else a/c*(100 if op=='percent' else 1)
        current[ref]=values.where(valid,None)
        if any(not math.isfinite(float(v)) for v in current[ref].dropna()):raise ValueError('Derived output is nonfinite.')
        metadata[ref]={'record_ids':list(dict.fromkeys(r for inp in e['inputs'] for r in metadata[inp]['record_ids'])),'unit':b['available'][ref]['unit'],'sources':set().union(*(metadata[inp]['sources'] for inp in e['inputs'])),'grain':list(dict.fromkeys(g for inp in e['inputs'] for g in metadata[inp]['grain'])),'periods':[p for inp in e['inputs'] for p in metadata[inp]['periods']]}
    rows=[];specs={};definitions={};sources=[];warnings=[]
    technical_notes=list(plan['assumptions'])+['Source row domains, missingness policy, join cardinality and typed calculations are retained in the audit. Missing values are not zeros.']
    if any(a.get('partition_reconciliation',{}).get('derived_zero_cells',0)>0 for a in audits):
        technical_notes.append('Distance-education blank categories were derived as zero only where the reported nonnegative partition already equals total enrollment; each derived cell is audited. Unresolved and suppressed cells remain missing.')
        warnings.append('Some blank distance-education categories are derived as zero where reported counts prove the category is empty; unresolved blanks remain missing.')
    if plan['missing_policy']=='complete_cases':warnings.append('Complete-case calculations exclude missing value/weight pairs; available/requested counts are retained.')
    if any(a['missing_unitids'] for a in audits):warnings.append('Some requested institution/source scopes have no matching rows. Missing source institutions are listed in the query audit; returned rows are not a complete institution-by-category grid.')
    if any(j['period_alignment']!='same_period' for j in plan['joins']):warnings.append('Different source periods are explicitly compared. This does not assert that changed definitions have been harmonized.')
    if b['populations']:
        warnings.append('Aggregates use the selected source reporting units and available observations. Counts are sums of institutional reports, not deduplicated people across institutions. Coverage and exclusions are in Definitions & sources and downloads.')
        if plan['population']['administrative_offices']:warnings.append('The selected reporting scope includes administrative offices where they report separate source observations.')
        technical_notes.append('Directory filters and exact source category evidence are retained in population_evidence; source reporting units need not equal every directory entry.')
    all_groups=[(s['id'],rid) for s in plan['sources'] for rid in s['group_by_record_ids']]
    emitted=set()
    for _,r in current.iterrows():
        uid=int(r['__unitid']);group_labels={}
        for sid,rid in all_groups:
            ref=field_ref(rid,sid)
            if ref in current:
                value=r[ref];text=str(int(value)) if isinstance(value,(int,float)) and float(value).is_integer() else str(value)
                label=next((c['value_label'] for c in b['codes'][rid] if c['code_value']==text),text)
                group_labels[(sid,rid)]=b['definitions'][rid]['title']+': '+label
        for out in plan['outputs']:
            ref=out['reference'];meta=metadata[ref];raw=r[ref]
            signature=(ref,tuple(str(r[g]) for g in meta['grain']))
            if signature in emitted:continue
            emitted.add(signature)
            val=None if pd.isna(raw) else float(raw) if isinstance(raw,(int,float)) or pd.api.types.is_number(raw) else raw
            if isinstance(val,str):raise ValueError('Numerical outputs cannot be categorical fields; use them as group labels.')
            selected_sources=[s for s in plan['sources'] if s['id'] in meta['sources']]
            year=max(s['year'] for s in selected_sources);period='; '.join(dict.fromkeys(p['raw'] for p in meta['periods']))
            selected_labels=[label for (sid,rid),label in group_labels.items() if field_ref(rid,sid) in meta['grain'] or key_ref(sid,b['definitions'][rid]['variable_name']) in meta['grain']]
            metric=ref;measure=out['label']+(' · '+'; '.join(selected_labels) if selected_labels else '')
            specs[metric]={'label':out['label'],'family':'query','unit':meta['unit']}
            combined=not any(g=='__unitid' or g.endswith('__UNITID') for g in meta['grain'])
            cohorts=cohort_years(b,selected_sources) if plan['time_basis']=='cohort' else set()
            rows.append({'institution':b['populations'][year]['label'] if combined and b['populations'] else 'Selected institutions combined' if combined else names.get(uid,str(uid)),'unitid':None if combined else uid,'observation_year':year,'entry_cohort_year':next(iter(cohorts)) if len(cohorts)==1 else None,'reporting_period':period,
                'metric':metric,'measure':measure,'unit':meta['unit'],'value':val,'release':'; '.join(source_context(b,s)['release_id'] for s in selected_sources),
                'provisional':any('Provisional' in source_context(b,s)['release_id'] for s in selected_sources),'status':'ok' if val is not None else 'missing',
                'numerator':None,'denominator':None,'series_segment':json.dumps(selected_labels),'groups':selected_labels,
                'available_rows':int(r[ref+'__available']) if ref+'__available' in current and pd.notna(r[ref+'__available']) else None,'requested_rows':int(r[ref+'__requested']) if ref+'__requested' in current and pd.notna(r[ref+'__requested']) else None})
            expression=next((e for e in plan['expressions'] if 'x'+e['id']==ref and e['operator'] in {'percent','divide'}),None)
            if expression:
                rows[-1]['numerator']=float(r[expression['inputs'][0]]) if pd.notna(r[expression['inputs'][0]]) else None
                rows[-1]['denominator']=float(r[expression['inputs'][1]]) if pd.notna(r[expression['inputs'][1]]) else None
            rows[-1]['unit_metadata']={'version':1,'unit':meta['unit'],'status':'unresolved' if meta['unit']=='unknown' else 'verified',
                'basis':'Validated query expression' if ref.startswith('x') else 'Source field',
                'inputs':[b['descriptors'][rid]['unit_metadata'] for rid in meta['record_ids']]}
            if re.fullmatch(r'f[A-Za-z0-9]+_\d+',ref) and len(meta['record_ids'])==1:
                rows[-1]['unit_metadata']=b['descriptors'][next(iter(meta['record_ids']))]['unit_metadata']
            if len(rows)>OUTPUT_LIMIT:raise ValueError('Output limit reached; narrow the requested groups or measures.')
            docs=[]
            for rid in meta['record_ids']:
                d=b['definitions'][rid];ev=d['evidence'];docs.append({**ev,'long_description':d['long_description'],'documented_table':d['table_name'],'physical_table':d['table_name'],'location_override':False,'issues':[]})
            definitions[metric]='\n\n'.join(d['title']+': '+d['long_description'] for d in docs)
            for s in selected_sources:
                audit=next(a for a in audits if a['source_id']==s['id']);path=annual_path(s['year']);stat=path.stat()
                sources.append({'metric':metric,'year':s['year'],'unitid':None if combined else uid,'database':str(path),'database_size':stat.st_size,'database_mtime_ns':stat.st_mtime_ns,'table':s['table'],
                    'columns':[b['definitions'][rid]['variable_name'] for rid in meta['record_ids'] if b['definitions'][rid]['table_name'].casefold()==s['table'].casefold()],
                    'filters':s['filters'],'formula':{'aggregates':s['aggregates'],'expressions':plan['expressions']},'sql':audit['sql'],'parameters':audit['parameters'],'codebook_evidence':docs,'code_filters':b['evidence']['category_evidence']})
    finished=time.perf_counter()
    output='chart' if re.search(r'chart|plot|graph|trend',question,re.I) else 'export' if re.search(r'csv|excel|download|export',question,re.I) else 'table'
    result={'plan':{'metrics':list(specs),'institutions':plan['institutions'],'years':plan['source_years'],'time_basis':plan['time_basis'],'output':output},'catalog_plan':plan,
        'metric_specs':specs,'rows':rows,'observation_years':sorted({r['observation_year'] for r in rows}),'sources':sources,'definitions':definitions,'warnings':warnings,'technical_notes':technical_notes,
        'created_at':datetime.now(timezone.utc).isoformat(),'registry_sha256':b['evidence']['catalog_identity'],'review_status':'Source-bound relational plan with observed grain, bounded domains, cardinality and typed-operation validation.',
        'coverage':{'requested_cells':len(rows),'available_cells':sum(r['status']=='ok' for r in rows)},'query_audit':audits,'join_validation':join_audits,
        'semantic_validation':{'execution_approved':True,'version':2,'missing_policy':plan['missing_policy'],'time_basis':plan['time_basis']},
        'catalog_evidence':b['evidence'],'population_evidence':b['populations'],'field_semantics':{str(k):v for k,v in b['descriptors'].items()},
        'latency':{'validation_seconds':validated-started,'query_seconds':finished-validated}}
    result['result_id']=sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()[:16]
    return stamp(result,intent_check)


def proposal_answer(plan,question,usage=None,error=None,checked=None):
    from .catalog_planner import _save
    if error is None and checked is None:checked=inspect(plan,question)
    if checked is not None and not plan.get('annual_years'):plan=checked['plan']
    proposal={'catalog_plan':plan,'question':question,'definition_evidence':list(checked['definitions'].values()) if checked else [],
        'category_evidence':checked['evidence']['category_evidence'] if checked else [],
        'validation':{'execution_approved':False,'preflight_eligible':not bool(error),'semantic_status':'blocked' if error else 'runtime_cardinality_pending','blocks':[error] if error else []},
        'created_at':datetime.now(timezone.utc).isoformat()}
    _save(proposal)
    answer={'intent':'catalog_plan','catalog_plan':plan,'catalog_proposal':proposal,
        'message':'The query could not be validated: '+error if error else 'Prepared a source-bound relational query. Runtime grain and join checks precede publication.',
        'mode':'catalog relational planner'}
    if usage:answer['model_usage']=usage
    return answer


def execute_answer(answer,question):
    if answer['catalog_proposal']['validation']['blocks']:return {**answer,'latency':{'validation_seconds':0.0,'query_seconds':0.0}}
    started=time.perf_counter()
    import sqlite3
    try:result=execute(answer['catalog_plan'],question)
    except (ValueError,sqlite3.OperationalError) as exc:
        if isinstance(exc,sqlite3.OperationalError) and 'interrupted' in str(exc).lower():exc=ValueError('The source query reached its time limit. No partial result was published; try a narrower source domain or fewer periods.')
        proposal=answer['catalog_proposal'];proposal['validation'].update(execution_approved=False,semantic_status='blocked',blocks=[str(exc)])
        return {**answer,'message':'This query did not pass validation; no numerical result was published. '+str(exc),'latency':{'validation_and_query_seconds':time.perf_counter()-started}}
    result['planning_validation']={'repair_attempts':answer.get('validation_attempts',[])}
    return finalize_answer({**answer,'intent':'analyze','result':result,'latency':result['latency']},question)
