"""Versioned direct categorical/mixed projections. No arithmetic on source codes.

Uses the existing physical/code/institution binding; only single-institution-grain
tables may be projected. Population lists intersect validated source predicates by
UNITID, never join arbitrary fact rows or synthesize a numerical count.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
import re
import time

from .query_schema import obj, array, STRING, INTEGER, FILTER, QUERY_SCHEMA

SCHEMA = obj({'version': {'const': 1}, 'institutions': array(STRING),
    'population': {'anyOf': [QUERY_SCHEMA['properties']['population'], {'type': 'null'}]},
    'sources': array(obj({'year': INTEGER, 'table': STRING,
        'field_record_ids': array(INTEGER), 'filters': array(FILTER)})),
    'result_kind': {'enum': ['lookup', 'institution_list']}})
SCHEMA['properties']['source_years']=array(INTEGER)


def enabled():
    return os.environ.get('IPEDS_TYPED_OBSERVATIONS', '1') != '0'


def code_text(raw):
    if raw is None or str(raw).strip() == '':
        return None
    text = str(raw).strip()
    return str(int(float(text))) if re.fullmatch(r'-?\d+\.0+', text) else text


def decode(raw, codes):
    code = code_text(raw)
    if code is None:
        return {'raw_code': raw, 'response_label': 'Missing observation',
                'response_status': 'missing', 'category_record_ids': []}
    matches = [c for c in codes if c['code_value'] == str(raw).strip()]
    if not matches:matches = [c for c in codes if c['code_value'] == code]
    if len({c['value_label'] for c in matches}) > 1:
        raise ValueError('Conflicting source labels for the same category code.')
    label = matches[0]['value_label'] if matches else 'Unmapped code: ' + code
    status = {'not reported': 'not_reported', 'not applicable': 'not_applicable',
              'implied no': 'implied_no', 'no': 'no', 'yes': 'yes'}.get(label.casefold(), 'reported' if matches else 'unmapped')
    return {'raw_code': raw, 'response_label': label, 'response_status': status,
            'category_record_ids': [c['record_id'] for c in matches]}


def requested_releases(question):
    """Academic release labels identify their start, not the observation date."""
    pairs = re.findall(r'\b((?:19|20)\d{2})[-–/]\d{2}\b', question)
    return set(map(int, pairs))


def verify_request(plan, question):
    years = {s['year'] for s in plan['sources']}
    wanted = requested_releases(question)
    if wanted and years != wanted:
        raise ValueError('The categorical plan must retain every requested release; no year substitution.')
    # Preserve simple explicit multi-year requests as well as academic labels.
    if not wanted:
        explicit = set(map(int, re.findall(r'\b(?:19|20)\d{2}\b', question)))
        if explicit and not re.search(r'cohort|observation|enrolled in|Fall \d{4}', question, re.I) and years != explicit:
            raise ValueError('The observation plan omits or substitutes a requested source year.')
    if re.search(r'\baverage\b|\bsum\b|percentage share|percent(?:age)? change', question, re.I):
        raise ValueError('Use the existing numerical query path for calculations and institution counts.')
    if re.search(r'\bbetter\b|\bbest\b|\bquality\b', question, re.I):
        raise ValueError('Availability projections do not establish service quality; explain the source coverage gap.')


def bind(plan, question):
    import jsonschema
    from analysis_catalog.catalog import connection, table_context
    from .catalog_planner import validate_proposal
    from .field_semantics import describe_field
    from .institution_confirmation import AUTHORIZED
    jsonschema.validate(plan, SCHEMA)
    if not enabled():
        raise ValueError('Typed categorical observations are disabled.')
    plan = deepcopy(plan)
    if not 1 <= len(plan['sources']) <= 20 or not 0 <= len(plan['institutions']) <= 30:
        raise ValueError('Observation bounds exceeded.')
    if bool(plan['institutions']) == bool(plan['population']):
        raise ValueError('Select named institutions or one explicit directory population.')
    if plan['result_kind'] == 'institution_list' and not plan['population']:
        raise ValueError('Institution lists require an explicit directory population.')
    if plan['population'] and re.search(r'\bwhich\b|list (?:their |the )?names',question,re.I) and plan['result_kind']!='institution_list':
        raise ValueError('A matching-school question requires institution_list output, not missing rows for the entire directory.')
    verify_request(plan, question)
    plan['source_years']=sorted({s['year'] for s in plan['sources']})
    populations = {}
    if plan['population']:
        from .populations import select, validate_request
        for year in {s['year'] for s in plan['sources']}:
            validate_request(plan['population'], question, year)
            populations[year] = select(plan['population'], year)
    authorized = AUTHORIZED.get()
    from .catalog import institutions
    resolved = {}
    fields = {}; codes = {}; contexts = {}; descriptors = {}
    seen = set()
    with connection() as db:
        for source in plan['sources']:
            key = (source['year'], source['table'].casefold())
            if key in seen:
                raise ValueError('Use one source projection per table and release.')
            seen.add(key)
            if not 1 <= len(source['field_record_ids']) <= 40 or len(source['filters']) > 20:
                raise ValueError('Select 1–40 exact fields and at most 20 filters per source.')
            if any(f['operator'] not in {'eq', 'in'} for f in source['filters']):
                raise ValueError('Observation filters require exact source-code equality or membership.')
            ids = set(source['field_record_ids']) | {f['record_id'] for f in source['filters']}
            adapter = {'version': 1, 'institutions': plan['institutions'], 'source_years': [source['year']],
                'requested_time': {'basis': 'reporting_period', 'description': 'Direct typed source observation'},
                'selections': [{'record_id': rid, 'role': 'measure'} for rid in ids],
                'filters': source['filters'], 'group_by_record_ids': [], 'calculations': [],
                'joins': [], 'output': 'table', 'assumptions': [], 'clarification_questions': []}
            packet = validate_proposal(adapter, question, population=plan['population'])
            if packet['validation']['blocks']:
                raise ValueError(packet['validation']['blocks'][0])
            docs = {d['record_id']: d for d in packet['definition_evidence']}
            if any(int(d['release_id'][6:10]) != source['year'] or d['table_name'].casefold() != source['table'].casefold() for d in docs.values()):
                raise ValueError('Observation fields must belong to the exact source table and release.')
            release = next(iter(docs.values()))['release_id']
            context = table_context(release, source['table'])
            keys=[k.upper() for k in context['profile']['candidate_key']]
            fixed={docs[f['record_id']]['variable_name'].upper() for f in source['filters'] if f['operator']=='eq' and len(f['values'])==1}
            if 'UNITID' not in keys or any(k!='UNITID' and k not in fixed for k in keys):
                raise ValueError('Direct observations require a verified institution grain: fix every additional source key to one documented category before projection.')
            contexts[key] = context
            # Source-backed conditional rule, all schools/releases. Requires the
            # actual definition, never an inferred link from a similar label.
            for rid in list(source['field_record_ids']):
                d = docs[rid]
                if d['variable_name'].upper() == 'DISABPCT' and re.search(r'more than 3 percent', d['long_description'], re.I):
                    companion = db.execute('SELECT record_id FROM definitions WHERE release_id=? AND table_name=? COLLATE NOCASE AND variable_name=\'DISAB\'', (release, source['table'])).fetchone()
                    if not companion:
                        raise ValueError('The source percentage requires its reporting-status companion.')
                    cd=db.execute('SELECT d.*,v.title,v.long_description,v.data_type,v.format FROM definitions d JOIN source.variable_docs v USING(record_id) WHERE d.record_id=?',(companion[0],)).fetchone()
                    if cd is None or cd['physical_status']!='documented_location_present':
                        raise ValueError('The source percentage selector is not verified at its documented location.')
                    from analysis_catalog.catalog import source_record
                    docs[companion[0]] = {**dict(cd),'evidence':source_record(db,companion[0])}
                    source.setdefault('companion_ids', {})[str(rid)] = companion[0]
            for rid, d in docs.items():
                fields[rid] = d
                codes[rid] = [dict(r) for r in db.execute('SELECT record_id,code_value,value_label FROM source.code_values WHERE release_id=? AND table_name=? COLLATE NOCASE AND variable_name=? COLLATE NOCASE', (release, source['table'], d['variable_name']))]
                descriptors[rid] = describe_field(d, context)
                if len({c['code_value'] for c in codes[rid]}) != len(codes[rid]):
                    for c in codes[rid]:
                        decode(c['code_value'], codes[rid])
            if re.fullmatch(r'EF\d{4}A',source['table'],re.I) and re.search(r'undergrad',question,re.I):
                selected_labels=[c['value_label'] for f in source['filters'] if docs[f['record_id']]['variable_name'].upper()=='EFALEVEL' for c in codes[f['record_id']] if c['code_value'] in f['values']]
                if not selected_labels or any('undergraduate' not in label.casefold() for label in selected_labels):
                    raise ValueError('The direct enrollment observation does not establish the requested undergraduate source population.')
            if not populations:
                resolved[source['year']] = institutions(plan['institutions'], source['year'])
                if authorized is not None and not set(resolved[source['year']]) <= authorized:
                    raise ValueError('Observation institutions differ from confirmed identities.')
                from .intent_checks import CURRENT
                request=CURRENT.get()
                if request and request.get('unitids') and set(resolved[source['year']])!=set(request['unitids']):
                    raise ValueError('The observation plan must retain exactly the requested institutions.')
    if not any(fields[rid]['format']!='Cont' or descriptors[rid]['unit']=='identifier' for s in plan['sources'] for rid in s['field_record_ids']) and not any(s.get('companion_ids') for s in plan['sources']):
        raise ValueError('Pure quantitative observations retain the existing numerical query path.')
    if sum(len(s['field_record_ids']) for s in plan['sources']) > 100:
        raise ValueError('Observation field limit exceeded.')
    if re.search(r'how many|how much',question,re.I) and not any(fields[rid]['format']=='Cont' for s in plan['sources'] for rid in s['field_record_ids']):
        raise ValueError('Use the existing numerical query path to count institutions matching categorical conditions.')
    required=[]
    # These are source concept anchors, not answer values or institution rules.
    anchors=[(r'calendar system','CALSYS'),(r'religious affili','RELAFFIL'),(r'open admission','OPENADMP'),
        (r'counsel(?:ing|ling)','STUSRV2'),(r'student employment|employment services','STUSRV3'),
        (r'career placement|placement services','STUSRV4'),(r'childcare|day care','STUSRV8'),
        (r'study abroad','SLO6'),(r'\bAP\s+credits|advanced placement','CREDITS3'),
        (r'bachelor.{0,8}degree','LEVEL5'),(r'master.{0,8}degree','LEVEL7')]
    if re.search(r'bachelor.{0,8}and master',question,re.I):required+=['LEVEL5','LEVEL7']
    if re.search(r'distance education courses',question,re.I):required.append('DSTNUGC')
    if re.search(r'distance education programs',question,re.I):required.append('DSTNUGP')
    required+=[var for pattern,var in anchors if re.search(pattern,question,re.I)]
    selected={fields[rid]['variable_name'].upper() for s in plan['sources'] for rid in s['field_record_ids']}|{fields[f['record_id']]['variable_name'].upper() for s in plan['sources'] for f in s['filters']}
    # Only enforce anchors documented in this source family; do not force IC codes
    # onto unrelated surveys containing similarly worded numerical measures.
    if all(re.fullmatch(r'IC\d{4}',s['table'],re.I) for s in plan['sources']):
        for year in plan['source_years']:
            selected={fields[rid]['variable_name'].upper() for s in plan['sources'] if s['year']==year for rid in s['field_record_ids']}|{fields[f['record_id']]['variable_name'].upper() for s in plan['sources'] if s['year']==year for f in s['filters']}
            if set(required)-selected:raise ValueError('The observation plan omits requested source concepts in '+str(year)+': '+', '.join(sorted(set(required)-selected)))
    return dict(plan=plan, fields=fields, codes=codes, contexts=contexts,
                descriptors=descriptors, populations=populations, resolved=resolved)


def execute(plan, question):
    from .catalog import readonly, annual_path
    from .query_engine import quote, number
    started = time.perf_counter(); b = bind(plan, question); plan = b['plan']
    sources = []; extracted = []; names = {}; missing_sources = []
    for source in plan['sources']:
        year = source['year']; path = annual_path(year)
        population = b['populations'].get(year)
        if population:
            where = 'UNITID IN (' + population['directory_sql'].replace('SELECT UNITID,INSTNM', 'SELECT UNITID') + ')'
            params = list(population['parameters'])
        else:
            ids = b['resolved'][year]; where = 'UNITID IN (' + ','.join('?' for _ in ids) + ')'; params = list(ids)
        field_ids = list(dict.fromkeys(source['field_record_ids'] + list(source.get('companion_ids', {}).values())))
        columns = ['UNITID'] + list(dict.fromkeys(b['fields'][rid]['variable_name'] for rid in field_ids))
        for f in source['filters']:
            where += ' AND ' + quote(b['fields'][f['record_id']]['variable_name']) + ' IN (' + ','.join('?' for _ in f['values']) + ')'
            params.extend(f['values'])
        sql = 'SELECT ' + ','.join(quote(c) for c in columns) + ' FROM ' + quote(source['table']) + ' WHERE ' + where + ' LIMIT 20001'
        with readonly(path) as db:
            raw = [dict(r) for r in db.execute(sql, params)]
            if len(raw) > 20000 or len({r['UNITID'] for r in raw}) != len(raw):
                raise ValueError('Source exceeds the bounded unique-institution projection.')
            names[year] = dict(db.execute('SELECT UNITID,INSTNM FROM ' + quote('HD' + str(year))))
        byid = {r['UNITID']: r for r in raw}
        missing_sources.append({'year': year, 'table': source['table'], 'selected_rows': len(raw)})
        extracted.append((source, byid, sql, params, path))
    eligible = {}
    for year in {s['year'] for s in plan['sources']}:
        sets = [set(rows) for s, rows, *_ in extracted if s['year'] == year]
        eligible[year] = set.intersection(*sets) if plan['result_kind'] == 'institution_list' else (set(b['populations'][year]['unitids']) if year in b['populations'] else set(b['resolved'][year]))
    rows = []; specs = {}; definitions = {}; allcells = []
    for source, byid, sql, params, path in extracted:
        year = source['year']; context = b['contexts'][(year, source['table'].casefold())]
        table_periods = [e['year_coverage'] for e in context['period_evidence'] if e.get('year_coverage')]
        for rid in source['field_record_ids']:
            d = b['fields'][rid]; desc = b['descriptors'][rid]; metric = re.sub(r'\d{4}', '{YEAR}', source['table']) + '::' + d['variable_name']
            specs[metric] = {'label': d['title'], 'family': 'observation', 'unit': desc['unit']}
            definitions[metric] = d['long_description']
            ev = d['evidence']; doc = {**ev, 'long_description': d['long_description'], 'documented_table': source['table'], 'physical_table': source['table'], 'issues': []}
            ids = list(dict.fromkeys([rid] + ([source['companion_ids'][str(rid)]] if str(rid) in source.get('companion_ids', {}) else []) + [f['record_id'] for f in source['filters']]))
            docs = [doc] + [{**b['fields'][i]['evidence'], 'long_description': b['fields'][i]['long_description'], 'documented_table': source['table'], 'physical_table': source['table'], 'issues': []} for i in ids[1:]]
            sources.append({'metric': metric, 'year': year, 'unitid': None, 'database': str(path), 'database_size': path.stat().st_size, 'database_mtime_ns': path.stat().st_mtime_ns, 'table': source['table'], 'columns': [b['fields'][i]['variable_name'] for i in ids], 'filters': source['filters'], 'formula': 'direct source observation', 'sql': sql, 'parameters': params, 'codebook_evidence': docs, 'code_filters': [c for i in ids for c in b['codes'][i]]})
            period = '; '.join(table_periods)
            if d['variable_name'].upper() in {'DISAB','DISABPCT'}:
                dates = re.findall(r'undergraduates enrolled in (Fall \d{4})', d['long_description'], re.I)
                if not dates and str(rid) in source.get('companion_ids', {}):
                    dates = re.findall(r'undergraduates enrolled in (Fall \d{4})', b['fields'][source['companion_ids'][str(rid)]]['long_description'], re.I)
                if dates: period = dates[0]
                asked=re.findall(r'\bFall\s+((?:19|20)\d{2})',question,re.I)
                if dates and asked and not re.search(r'release|codebook|collection',question,re.I) and any(y not in period for y in asked):
                    raise ValueError('The requested student observation year is not established by this source field, which describes '+period+'. No year substitution was published.')
            for uid in sorted(eligible[year],key=lambda uid:names[year].get(uid,str(uid)).casefold()):
                raw = byid.get(uid, {}).get(d['variable_name']); kind = 'identifier' if desc['unit'] == 'identifier' else 'quantitative' if d['format'] == 'Cont' else 'categorical' if b['codes'][rid] or d['data_type']=='N' else 'text'
                cell = {'institution': names[year].get(uid, str(uid)), 'unitid': uid, 'observation_year': year, 'entry_cohort_year': None, 'reporting_period': period, 'source_reporting_period': '; '.join(table_periods), 'metric': metric, 'measure': d['title'], 'unit': 'coded' if kind in {'categorical','text'} else desc['unit'], 'value': None, 'release': d['release_id'], 'provisional': 'Provisional' in d['release_id'], 'status': 'ok', 'numerator': None, 'denominator': None, 'series_segment': '', 'groups': [], 'result_type': kind, 'record_id': rid, 'raw_code': raw, 'response_label': None, 'response_status': 'reported', 'category_record_ids': [], 'unit_metadata': desc['unit_metadata']}
                if kind == 'categorical': cell.update(decode(raw, b['codes'][rid]))
                elif kind in {'text','identifier'}:
                    cell.update(response_label=str(raw) if raw is not None else 'Missing observation', response_status='reported' if raw is not None else 'missing')
                else:
                    cell['value'] = number(raw, d, [c['code_value'] for c in b['codes'][rid]])
                    if cell['value'] is None:
                        cell['status'] = 'missing'
                        if code_text(raw) is not None:
                            response=decode(raw,b['codes'][rid])
                            cell.update(response_status=response['response_status'],response_label=response['response_label'],category_record_ids=response['category_record_ids'])
                if str(rid) in source.get('companion_ids', {}):
                    cid = source['companion_ids'][str(rid)]; selector = decode(byid.get(uid, {}).get(b['fields'][cid]['variable_name']), b['codes'][cid])
                    cell['conditional_evidence'] = {'record_id': cid, **selector}
                    label = selector['response_label']
                    if re.fullmatch(r'\d+(?:\.\d+)? percent or less', label, re.I):
                        cell.update(result_type='bounded', value=None, status='bounded', response_label=label, response_status='bounded', bound={'upper': float(label.split()[0]), 'upper_inclusive': True, 'unit': 'percent'})
                    elif re.fullmatch(r'More than \d+(?:\.\d+)? percent',label,re.I) and cell['value'] is None:
                        cell.update(result_type='bounded',status='bounded',response_label=label,response_status='bounded',bound={'lower':float(label.split()[2]),'lower_inclusive':False,'unit':'percent'})
                    elif not re.fullmatch(r'More than \d+(?:\.\d+)? percent', label, re.I):
                        cell.update(value=None, status='missing', response_label=label, response_status=selector['response_status'])
                if uid not in byid: cell.update(status='missing', response_status='missing', response_label='Missing source row')
                rows.append(cell); allcells.append((uid, year, rid))
    if len(rows) > 5000:
        raise ValueError('Observation output limit reached; narrow the population. No partial list was published.')
    public_plan={**plan,'sources':[{k:v for k,v in s.items() if k!='companion_ids'} for s in plan['sources']]}
    result = {'result_schema_version': 2, 'result_kind': plan['result_kind'], 'observation_plan': public_plan,
        'plan': {'metrics': list(specs), 'institutions': plan['institutions'], 'years': sorted(eligible), 'time_basis': 'source_release', 'output': 'table'},
        'metric_specs': specs, 'rows': rows, 'observation_years': sorted(eligible), 'sources': sources, 'definitions': definitions,
        'warnings': ['Implied no is a source response distinct from Not reported and Not applicable.'] if any(r['response_status'] == 'implied_no' for r in rows) else [],
        'technical_notes': ['Codes are categorical responses, never numerical quantities. Lists include only reporting units satisfying every selected source predicate.'],
        'created_at': datetime.now(timezone.utc).isoformat(), 'registry_sha256': sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(),
        'review_status': 'Source-bound typed direct observations; no arithmetic on categorical codes.',
        'coverage': {'requested_cells': len(rows), 'available_cells': sum(r['response_status'] not in {'missing','unmapped','not_reported'} for r in rows), 'matching_institutions': {str(y): len(ids) for y, ids in eligible.items()}, 'source_rows': missing_sources},
        'population_evidence': b['populations'], 'observation_validation': {'cells': allcells, 'source_years': sorted(eligible), 'institutions': sorted({r['unitid'] for r in rows})},
        'latency': {'validation_and_query_seconds': time.perf_counter()-started}}
    result['result_id'] = sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()[:16]
    result['observation_validation']['rows_sha256']=sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
    verify_result(result)
    return result


def verify_result(result):
    expected = result['observation_validation']
    if sha256(json.dumps(result['rows'],sort_keys=True).encode()).hexdigest()!=expected['rows_sha256']:
        raise ValueError('Typed responses no longer match the validated source cells.')
    actual = [(r['unitid'], r['observation_year'], r['record_id']) for r in result['rows']]
    if len(set(actual)) != len(actual) or set(actual) != {tuple(c) for c in expected['cells']}:
        raise ValueError('Typed observation cells no longer match the validated source projection.')
    for row in result['rows']:
        if row['result_type'] in {'categorical','identifier','text','bounded'} and row['value'] is not None:
            raise ValueError('Categorical and bounded responses cannot be numerical values.')
    return []


def answer(plan, question, usage=None):
    from .responses import finalize_answer
    result=execute(plan,question)
    return finalize_answer({'intent': 'analyze', 'mode': 'typed source observations', 'observation_plan': result['observation_plan'],
        'result': result, 'model_usage': usage or {'calls': 0, 'estimated_api_usd': 0}}, question)


def from_legacy(plan):
    """Lossless projection adapter only; never convert aggregates or calculations."""
    if not enabled():return None
    from analysis_catalog.catalog import connection
    if plan.get('version')==1:
        if plan.get('calculations') or plan.get('joins') or plan.get('clarification_questions'):return None
        ids=[s['record_id'] for s in plan.get('selections',[]) if s['role']!='identifier']
        filters=plan.get('filters',[])
        sources=[]
        with connection() as db:
            docs=[dict(db.execute('SELECT r.record_id,r.table_name,r.release_id,v.format,v.variable_name FROM source.records r JOIN source.variable_docs v USING(record_id) WHERE r.record_id=?',(rid,)).fetchone() or {}) for rid in ids]
        if not docs or any(not d for d in docs):return None
        if not any(d['format']!='Cont' or d['variable_name'].upper()=='DISABPCT' for d in docs):return None
        roles={s['record_id']:s['role'] for s in plan.get('selections',[])}
        if any(d['format']=='Cont' for d in docs) and not any(d['variable_name'].upper()=='DISABPCT' or (d['format']!='Cont' and roles[d['record_id']]=='measure') for d in docs):
            # Coded grouping/selector dimensions do not turn a valid numerical
            # lookup into a categorical projection or suppress its existing chart.
            return None
        for year,table in dict.fromkeys((int(d['release_id'][6:10]),d['table_name']) for d in docs):
            own=[d['record_id'] for d in docs if int(d['release_id'][6:10])==year and d['table_name']==table]
            if any(f['record_id'] not in ids for f in filters):return None
            sources.append({'year':year,'table':table,'field_record_ids':own,'filters':[f for f in filters if f['record_id'] in own]})
        return {'version':1,'institutions':plan['institutions'],'population':None,'sources':sources,'result_kind':'lookup'}
    if plan.get('version')==2:
        if plan.get('expressions') or plan.get('joins') or any(s['aggregates'] for s in plan['sources']):return None
        valid={'f'+s['id']+'_'+str(rid) for s in plan['sources'] for rid in s['field_record_ids']}
        if any(o['reference'] not in valid for o in plan['outputs']):return None
        selected={o['reference'] for o in plan['outputs']}
        sources=[{'year':s['year'],'table':s['table'],'field_record_ids':[rid for rid in s['field_record_ids'] if 'f'+s['id']+'_'+str(rid) in selected],'filters':s['filters']} for s in plan['sources']]
        if any(not s['field_record_ids'] for s in sources):return None
        with connection() as db:
            docs=[dict(db.execute('SELECT format,variable_name FROM source.variable_docs WHERE record_id=?',(rid,)).fetchone() or {}) for s in sources for rid in s['field_record_ids']]
        if not any(d and (d['format']!='Cont' or d['variable_name'].upper()=='DISABPCT') for d in docs):return None
        return {'version':1,'institutions':plan['institutions'],'population':plan.get('population'),'sources':sources,'result_kind':'institution_list' if plan.get('population') else 'lookup'}
    return None
