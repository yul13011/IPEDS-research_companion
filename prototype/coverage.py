"""Read-only, source-backed coverage. An empty search never proves absence."""
from copy import deepcopy
from functools import lru_cache
import math,re
from .catalog import DATA,annual_path,readonly,IVY

class CoverageQuestion(ValueError):pass


def inventory():
    from .analytics import REGISTRY
    paths=[DATA/'metadata_catalog.sqlite',REGISTRY]+sorted((DATA/'annual').glob('IPEDS_*/*.sqlite'))
    signature=tuple((str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in paths if p.exists())
    return deepcopy(_inventory(signature))


@lru_cache(maxsize=4)
def _inventory(signature):
    from .analytics import measures
    files={}
    for path,_,_ in signature:
        m=re.search(r'IPEDS_((?:19|20)\d{2})-',path)
        if m:files[int(m[1])]=path
    with readonly(DATA/'metadata_catalog.sqlite') as db:
        releases=[r[0] for r in db.execute('SELECT DISTINCT release_id FROM physical_tables ORDER BY release_id') if int(r[0][6:10]) in files]
    return {'releases':releases,'release_years':[int(r[6:10]) for r in releases],
        'file_years':sorted(files),'measures':[{'id':m['id'],'label':m['label'],'family':m['family'],
            'mapped_release_years':sorted(map(int,m['annual']))} for m in measures().values()],
        'basis':'Local annual files, physical catalog inventory and reviewed measure registry; not global IPEDS availability.'}


def _years_text(years):
    years=sorted(set(years))
    if not years:return 'none verified'
    if len(years)>2 and years==list(range(years[0],years[-1]+1)):return str(years[0])+'–'+str(years[-1])
    return ', '.join(map(str,years))


def _unitids(names):
    from .institution_confirmation import resolve
    ids=[]
    for name in names:
        if str(name).casefold() in {'ivy','ivy league','ivies'}:ids.extend(IVY);continue
        uid=resolve(str(name),{})
        if uid is None:raise CoverageQuestion('Please confirm the institution name or UNITID before checking its reported values: '+str(name))
        ids.append(uid)
    if len(set(ids))>30:raise CoverageQuestion('Coverage checks support up to 30 named institutions.')
    return sorted(set(ids))


def _has_fields(year,table,columns):
    from .analytics import _identifier
    with readonly(annual_path(year)) as db:
        actual={r['name'].casefold() for r in db.execute('PRAGMA table_info('+_identifier(table)+')')}
    return bool(actual) and {c.casefold() for c in columns}<=actual


def _cell(db,spec,mapping,uid):
    from .analytics import compile_query
    sql,params=compile_query(spec,mapping,uid)
    rows=db.execute(sql,params).fetchmany(2)
    if len(rows)>1:return 'inconclusive_duplicate_rows'
    if not rows or rows[0]['value'] is None:return 'missing_values'
    row=dict(rows[0]);value=row['value']
    valid=isinstance(value,(int,float)) and math.isfinite(value) and value>=0
    if spec['unit']=='percent':valid=valid and value<=100
    if spec['unit']=='score':valid=valid and 200<=value<=800
    if row.get('denominator') is not None:
        valid=valid and row['denominator']>0 and row.get('numerator') is not None and 0<=row['numerator']<=row['denominator']
    return 'reported' if valid else 'inconclusive_invalid_value'


def _reviewed(metric,scope,basis,inv):
    from .analytics import measures
    from .catalog import evidence
    spec=measures()[metric]
    if basis=='entry_cohort' and spec['family'] not in {'graduation','pell'}:raise CoverageQuestion('This measure does not support entering-cohort coverage. Please specify the intended reporting-period basis.')
    if basis=='class' and spec['family'] not in {'admissions','sat'}:raise CoverageQuestion('This measure does not support nominal class-of coverage. Please specify the intended reporting-period basis.')
    ids=_unitids(scope['institutions']);periods=[];refs=[]
    with readonly(DATA/'metadata_catalog.sqlite') as cat:
        for year in inv['release_years']:
            mapping=spec['annual'].get(str(year))
            if not mapping:
                periods.append({'release_year':year,'period':year-6 if basis=='entry_cohort' else year+4 if basis=='class' else year,
                    'status':'not_mapped','reporting_status':'not_checked'})
                continue
            if not _has_fields(year,mapping['table'],spec['columns']+list(spec['filters'])):
                periods.append({'release_year':year,'period':year-6 if basis=='entry_cohort' else year+4 if basis=='class' else year,
                    'status':'field_not_present','reporting_status':'not_checked'})
                continue
            docs=evidence(cat,mapping['release'],mapping['table'],spec['columns'])
            refs.extend({'record_id':d['record_id'],'release_id':mapping['release'],'table':mapping['table'],'title':d['title']} for d in docs)
            checks={}
            if ids:
                with readonly(annual_path(year)) as db:checks={str(uid):_cell(db,spec,mapping,uid) for uid in ids}
            reporting='reported' if checks and all(v=='reported' for v in checks.values()) else 'partial_or_missing' if checks else 'not_checked'
            periods.append({'release_year':year,'period':year-6 if basis=='entry_cohort' else year+4 if basis=='class' else year,
                'status':'documented_in_loaded_source','reporting_status':reporting,'institutions':checks})
    return {'measure_id':metric,'label':spec['label'],'periods':periods,'source_refs':refs,
        'period_label':'entering cohort' if basis=='entry_cohort' else 'nominal class-of' if basis=='class' else 'source release' if basis=='source_release' else 'fall' if spec['family'] in {'admissions','sat','enrollment'} else 'observation year'}


def _catalog(fields,scope,basis,inv):
    """Exact physical-field history; retain source periods instead of guessing dates."""
    from analysis_catalog.catalog import connection,table_context
    with connection() as db:
        definitions=[dict(db.execute('SELECT d.*,v.title FROM definitions d JOIN source.variable_docs v USING(record_id) WHERE record_id=?',(rid,)).fetchone() or {}) for rid in fields]
        if any(not d for d in definitions):raise ValueError('A requested coverage field has no source definition.')
        output=[]
        for d in definitions:
            table=d['table_name'];seed=int(d['release_id'][6:10]);template=table.replace(str(seed),'{year}')
            periods=[];refs=[]
            for year in inv['release_years']:
                candidate=template.format(year=year)
                row=db.execute('SELECT * FROM definitions WHERE release_id LIKE ? AND table_name=? COLLATE NOCASE AND variable_name=? COLLATE NOCASE',
                    (f'IPEDS_{year}-%',candidate,d['variable_name'])).fetchone()
                if not row or row['physical_status']!='documented_location_present':continue
                if not _has_fields(year,row['table_name'],[row['variable_name']]):continue
                ctx=table_context(row['release_id'],row['table_name'])
                labels=list(dict.fromkeys(p['year_coverage'] for p in ctx['period_evidence'] if p.get('year_coverage')))
                fall=[int(m[1]) for label in labels if (m:=re.fullmatch(r'Fall ((?:19|20)\d{2})',label,re.I))]
                period=year if basis=='source_release' else fall[0] if len(set(fall))==1 and len(labels)==1 and basis=='observation' else None
                periods.append({'release_year':year,'period':period,'source_period_labels':labels,
                    'status':'documented_in_loaded_source','reporting_status':'not_checked'})
                refs.append({'record_id':row['record_id'],'release_id':row['release_id'],'table':row['table_name'],'title':d['title']})
            output.append({'field_record_id':d['record_id'],'label':d['title'],'periods':periods,'source_refs':refs,
                'period_label':'source release' if basis=='source_release' else 'source-documented reporting period'})
    return output


def answer(query,working=None):
    """Answer typed coverage requests from inventory/evidence, without an LLM."""
    if query.get('operation')=='overview':
        from .discovery import guide_answer
        return guide_answer(query.get('topic',''))
    inv=inventory();working=working or {};current=working.get('subject') or {}
    matches=(bool(query.get('measure_ids')) and set(query['measure_ids'])<=set(current.get('measure_ids',[]))) or (
        bool(query.get('field_record_ids')) and set(query['field_record_ids'])<=set(current.get('field_record_ids',[])))
    use_context=query.get('scope_mode','context')=='context' and (query.get('inherit_working') or matches)
    base=deepcopy(current) if use_context else {}
    explicit=bool(query.get('measure_ids') or query.get('field_record_ids'))
    scope={**base,'measure_ids':query.get('measure_ids',[]) if explicit else base.get('measure_ids',[]),
        'field_record_ids':query.get('field_record_ids',[]) if explicit else base.get('field_record_ids',[]),
        'institutions':query.get('institutions') or base.get('institutions',[]),'topic':query.get('topic') or base.get('topic','')}
    if explicit and (set(scope['measure_ids'])!=set(base.get('measure_ids',[])) or set(scope['field_record_ids'])!=set(base.get('field_record_ids',[]))):
        scope.update(plan={},periods=[])
    if query.get('institutions') and set(query['institutions'])!=set(base.get('institutions',[])):scope['plan']={}
    if scope['institutions']:scope['institutions']=list(map(str,_unitids(scope['institutions'])))
    if len(scope['field_record_ids'])>40:raise CoverageQuestion('This analysis contains more than 40 source fields. Please identify the measure or field whose periods you want checked.')
    basis=query.get('time_basis','observation')
    if basis=='working':basis=scope.get('time_basis','observation')
    if basis not in {'observation','entry_cohort','class','source_release'}:basis='observation'
    scope['time_basis']=basis
    op=query['operation'];requested=query.get('requested_years',[])
    if op=='releases' and (scope['measure_ids'] or scope['field_record_ids'] or scope['topic']):
        basis='source_release';scope['time_basis']=basis
    coverage={'operation':op,'scope':scope,'time_basis':basis,'requested_periods':requested,
        'loaded_release_years':inv['release_years'],'status':'answered','available_periods':[],
        'limits':['This describes the supplied local files, not whether IPEDS has published other data.']}
    if not scope['measure_ids'] and not scope['field_record_ids'] and op in {'periods','releases'} and scope['topic'] and not scope.get('guide_section_ids'):
        from .discovery import search as guide_search
        scope['guide_section_ids']=[s['id'] for s in guide_search(scope['topic'])]
    if not scope['measure_ids'] and not scope['field_record_ids'] and scope.get('guide_section_ids') and op in {'periods','releases'}:
        from .discovery import get
        sections=[s for s in get()['sections'] if s['id'] in scope['guide_section_ids']]
        coverage.update(time_basis='source_release',available_periods=sorted({y for s in sections for y in s['release_years']}))
        scope['time_basis']='source_release'
        coverage['limits'].append('Component release coverage does not establish observation-period coverage for every field.')
        return {'intent':'coverage','mode':'source coverage','coverage':coverage,
            'message':'\n\n'.join(s['title']+': documented in source releases '+_years_text(s['release_years'])+'.' for s in sections)+' These are source-release years; observation periods and reporting availability vary by field. Name a measure for its exact periods.'}
    if not scope['measure_ids'] and not scope['field_record_ids'] and (not scope['topic'] or op in {'periods','releases'}):
        coverage['available_periods']=inv['release_years'];coverage['time_basis']='source_release'
        message='Loaded source releases: '+', '.join(r.removeprefix('IPEDS_').replace('_',' ') for r in inv['releases'])+'. Observation periods depend on the measure.'
        if scope['topic']:
            message+=' No exact measure is bound to the previous topic; this release inventory does not establish that topic\'s coverage. Name a measure for its exact observation periods.'
            coverage['limits'].append('Unbound topic coverage is not established by the global release inventory.')
        if op=='check':
            if basis!='source_release':
                coverage['status']='inconclusive'
                return {'intent':'clarify','mode':'source coverage','message':message+' Which measure should I check for the requested observation periods?','coverage':coverage}
            missing=sorted(set(requested)-set(inv['release_years']))
            coverage.update(unavailable_periods=missing,requested_status='not_loaded' if missing else 'available')
            message=('The requested source releases '+_years_text(missing)+' are not loaded. ' if missing else 'Yes, the requested source releases are loaded. ')+message
        return {'intent':'coverage','mode':'source coverage','message':message,'coverage':coverage}
    from .analytics import measures
    if any(m not in measures() for m in scope['measure_ids']):raise ValueError('Coverage measure IDs must exist in the supplied registry.')
    entries=[_reviewed(m,scope,basis,inv) for m in scope['measure_ids']]
    if scope['field_record_ids']:
        entries+=_catalog(scope['field_record_ids'],scope,basis,inv)
        coverage['limits'].append('Exact field presence is verified. Institution-level values, row selectors and cross-year comparability have not been certified by this metadata check.')
    if not scope['measure_ids'] and not scope['field_record_ids']:
        from .catalog import search
        hits=search(scope['topic'],limit=8,kinds=['variable_definition','table_definition'])
        coverage.update(status='inconclusive',candidates=[{'record_id':r['record_id'],'title':r['title'],'release_id':r['release_id']} for r in hits])
        return {'intent':'clarify','mode':'source coverage','message':'I need an exact measure or source field to establish its periods. The bounded topic search '+('found possible matches; it does not establish complete coverage.' if hits else 'was inconclusive; it does not prove the data are absent.'),'coverage':coverage}
    coverage['entries']=entries
    available_sets=[{p['period'] for p in e['periods'] if p['period'] is not None and p['status']=='documented_in_loaded_source' and p['reporting_status'] in {'reported','not_checked'}} for e in entries]
    available=sorted(set.intersection(*available_sets)) if available_sets else []
    coverage['available_periods']=available
    label=entries[0]['period_label'] if len({e['period_label'] for e in entries})==1 else 'measure-specific period'
    text=[]
    for e in entries:
        supported=sorted({p['period'] for p in e['periods'] if p['period'] is not None and p['status']=='documented_in_loaded_source'})
        reported=sorted({p['period'] for p in e['periods'] if p['reporting_status']=='reported'})
        text.append(e['label']+': '+e['period_label']+' coverage '+_years_text(supported)+'.'+
            (' Reported values for every requested institution are verified for '+_years_text(reported)+'.' if scope['institutions'] and scope['measure_ids'] else ' Institution-level reporting has not been checked.'))
        if not supported:
            labels=sorted({label for p in e['periods'] for label in p.get('source_period_labels',[])})
            text.append('Documented source periods: '+('; '.join(labels) or 'no exact annual field match verified')+'. No unsupported conversion to '+basis+' years was inferred.')
    if op=='check':
        unavailable=[y for y in requested if y not in available]
        coverage['unavailable_periods']=unavailable
        if unavailable:
            file_years={y+6 if basis=='entry_cohort' else y-4 if basis=='class' else y for y in unavailable}
            not_loaded=file_years-set(inv['file_years'])
            coverage['requested_status']='not_loaded' if not_loaded==file_years else 'not_available_or_not_verified'
            text.insert(0,('The requested '+label+' '+_years_text(unavailable)+' data are not loaded in this app.' if not_loaded==file_years else 'The requested '+label+' '+_years_text(unavailable)+' values are not available or not verified for the selected scope.'))
        else:
            coverage['requested_status']='available';text.insert(0,'Yes. The requested '+label+' '+_years_text(requested)+' coverage is verified in the local sources.')
    return {'intent':'coverage','mode':'source coverage','message':'\n\n'.join(text),'coverage':coverage}


# ===== merged from coverage_gap.py (consolidation) =====
"""Explain source limitations before optional, independently validated proxies."""
from copy import deepcopy
from .query_schema import obj,array,STRING
from .conversation import OPTION_SCHEMA,prepare,draft

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


# ===== merged from source_policy.py (consolidation) =====
"""Owner's source boundary, shared by model-facing analytical routes."""
SOURCE_POLICY='''Use only sources supplied by the owner and exposed through this application's local tools. Do not browse, consult, recommend or import unprovided external sources (including College Scorecard, outside lists or websites) to fill a gap. Model background knowledge is not data evidence. Answer directly when the supplied data support the requested meaning, including valid derived calculations. If the original concept cannot be established from inspected supplied sources, explain that coverage limitation first. Scope absence claims to the inspected supplied releases; an unsuccessful search or a tool failure alone does not prove data do not exist. Distinguish an established coverage gap from incomplete retrieval or unresolved definitions. Do not redefine an institution classification as enrollment composition. Proxies are optional alternatives, never equivalent answers or mandatory user choices, and must not run until explicitly selected. Do not replace the original question with a proxy by default.'''
