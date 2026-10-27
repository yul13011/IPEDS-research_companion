"""Bounded, read-only execution of catalog-bound direct observations.

SQL identifiers come exclusively from revalidated catalog evidence. Model text
never becomes SQL. Repeated rows need documented keys and explicit selectors;
arbitrary aggregates, fact joins and unverified denominators remain blocked.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import re
import time

from .catalog import annual_path, readonly
from .catalog_planner import validate_proposal
from .responses import finalize_answer
from .progress import report
from .semantics import describe_field, validate_calculation, normalize_plan, formula_text


def quoted(name):
    return '"'+name.replace('"','""')+'"'


def numeric(value):
    if value is None or str(value).strip()=='':return None
    try:number=float(value)
    except (ValueError,TypeError):return None
    # IPEDS negative sentinels must never become observations or zeros.
    if not math.isfinite(number) or number<0:return None
    return int(number) if number.is_integer() else number


def source_unit(d):
    from .semantics import resolve
    return resolve(d)['unit']


def semantic_check(proposal):
    p=proposal['catalog_plan'];blocks=list(proposal['validation']['blocks'])
    defs={d['record_id']:d for d in proposal['definition_evidence']}
    question=proposal['question']
    if p['requested_time']['basis']=='fall':
        from .catalog_planner import _source_years
        if re.search(r'\b(?:19|20)\d{2}\b',question) and set(_source_years(question))!=set(p['source_years']):
            blocks.append('The proposed fall years do not cover the requested years; no substitute release may be used.')
    selected=[defs[s['record_id']] for s in p['selections'] if s['role']=='measure']
    if p['clarification_questions']:blocks.extend(p['clarification_questions'])
    if not selected:blocks.append('No numerical measure was selected.')
    if p['joins']:blocks.append('Joined catalog analyses need a separate cardinality and population review; use a single source table for now.')
    if p['group_by_record_ids'] or any(s['role']=='dimension' for s in p['selections']):
        blocks.append('Grouped extracts need an explicit row-output and subtotal policy; this executor currently returns explicitly selected institution observations.')
    if any(f['operator'] not in {'eq','in'} for f in p['filters']):
        blocks.append('Range filters need field-specific numeric storage and missing-value validation before execution.')
    choices_by_field={}
    for f in p['filters']:
        if f['operator'] in {'eq','in'}:
            rid=f['record_id'];values=set(f['values'])
            choices_by_field[rid]=choices_by_field.get(rid,values)&values
    if any(not values for values in choices_by_field.values()):blocks.append('The plan contains conflicting population selectors for the same source field.')
    for d in selected:
        if d['format']!='Cont' or d['data_type']!='N':blocks.append(f"{d['variable_name']} is not a documented continuous numerical measure.")
    groups={}
    for d in defs.values():groups.setdefault((d['release_id'],d['table_name']),[]).append(d)
    measure_tables={(d['release_id'],d['table_name'].lower()) for d in selected}
    if any((defs[f['record_id']]['release_id'],defs[f['record_id']]['table_name'].lower()) not in measure_tables for f in p['filters']):
        blocks.append('A filter refers to a different table from the selected observations; it cannot be silently omitted.')
    calc_inputs=[rid for c in p['calculations'] for rid in c['input_record_ids']]
    if any(rid not in {d['record_id'] for d in selected} for rid in calc_inputs):
        blocks.append('Every calculation input must be a selected numerical observation.')
    # No cross-table arithmetic; no implicit row reductions, even when a key is
    # empirically unique. The source description must also document its grain.
    for t in proposal['table_evidence']:
        if (re.fullmatch(r'EF\d{4}A',t['table_name'],re.I) and re.search(r'undergrad',question,re.I)
            and re.search(r'race|ethnic|\b(gender|sex)\b',question,re.I)
            and not re.search(r'full.time|part.time|first[\s-]*(time|year)|degree.seek|continuing|transfer|only|exclud|except',question,re.I)):
            from analysis_catalog.catalog import connection
            with connection() as catalog_db:
                total_codes=[r['code_value'] for r in catalog_db.execute(
                    "SELECT code_value,value_label FROM source.code_values WHERE release_id=? AND table_name=? COLLATE NOCASE AND variable_name='EFALEVEL'",
                    (t['release_id'],t['table_name'])) if r['value_label'].strip().casefold()=='all students, undergraduate total']
            level_ids={d['record_id'] for d in defs.values() if d['release_id']==t['release_id'] and d['table_name'].lower()==t['table_name'].lower() and d['variable_name'].upper()=='EFALEVEL'}
            if len(total_codes)!=1 or not any(f['record_id'] in level_ids and f['operator']=='eq' and f['values']==total_codes for f in p['filters']):
                blocks.append('The selected population does not represent all undergraduates; a subgroup cannot answer the requested total undergraduate breakdown.')
        if (re.fullmatch(r'EF\d{4}A',t['table_name'],re.I) and re.search(r'undergrad',question,re.I)
            and re.search(r'first[\s-]*(time|year)',question,re.I) and re.search(r'\b(gender|sex)\b',question,re.I)):
            from analysis_catalog.catalog import connection
            attendance='Full-time students' if re.search(r'full[\s-]*time',question,re.I) else 'Part-time students' if re.search(r'part[\s-]*time',question,re.I) else 'All students'
            expected=attendance+', Undergraduate, Degree/certificate-seeking, First-time'
            with connection() as catalog_db:
                codes=[r['code_value'] for r in catalog_db.execute(
                    "SELECT code_value,value_label FROM source.code_values WHERE release_id=? AND table_name=? COLLATE NOCASE AND variable_name='EFALEVEL'",
                    (t['release_id'],t['table_name'])) if r['value_label'].strip().casefold()==expected.casefold()]
            level_ids={d['record_id'] for d in defs.values() if d['release_id']==t['release_id'] and d['table_name'].lower()==t['table_name'].lower() and d['variable_name'].upper()=='EFALEVEL'}
            if len(codes)!=1 or not any(f['record_id'] in level_ids and f['operator']=='eq' and f['values']==codes for f in p['filters']):
                blocks.append('The selected population does not match the requested first-time undergraduate attendance scope.')
        key=t['profile'].get('candidate_key') or []
        description=' '.join(s.get('description','') for s in t['population_evidence']).upper()
        if not key or 'UNITID' not in [c.upper() for c in key]:
            blocks.append(f"{t['table_name']}: no validated institution key candidate.");continue
        for column in key:
            if column.upper()=='UNITID':continue
            choices=[d for d in defs.values() if d['release_id']==t['release_id'] and d['table_name'].lower()==t['table_name'].lower() and d['variable_name'].upper()==column.upper()]
            selectors=[f for f in p['filters'] if any(d['record_id']==f['record_id'] for d in choices)]
            # Exact variable definitions and validated category evidence also
            # document a population key; table prose need not repeat its code name.
            documented=column.upper() in description or any(d.get('title') and d.get('category_count',0)>0 for d in choices)
            if not documented or not selectors or any(f['operator']!='eq' for f in selectors):
                blocks.append(f"{t['table_name']}: select one source-documented {column} population row before execution.")
        periods=[str(e.get('year_coverage') or '') for e in t['period_evidence']]
        if not any(periods):blocks.append(f"{t['table_name']}: source reporting-period evidence is missing.")
        basis=p['requested_time']['basis']
        period=' '.join(periods).lower()
        if basis=='cohort':blocks.append('Cohort-to-release alignment needs a source-specific mapping; no release-year substitution was made.')
        if basis=='fall' and 'fall' not in period:blocks.append(f"{t['table_name']}: requested fall period does not match the source period.")
        if basis=='fiscal' and not re.search(r'fiscal|fy\b',period):blocks.append(f"{t['table_name']}: fiscal-year alignment needs review.")
        if basis=='academic' and not re.search(r'academic|\d{4}.\d{2,4}|july 1.*june 30',period):blocks.append(f"{t['table_name']}: academic-year alignment needs review.")
        if basis in {'fiscal','academic'} and len(p['source_years'])==1:
            explicit=re.findall(r'\b(?:19|20)\d{2}\b',question)
            # Price/cost tables encode the data year in the column, not the table period
            # (e.g. IC 'published tuition and fees 2022-23'; net price NPIST2 '...2022-23').
            # Accept the requested year when a selected field's own title covers it.
            field_text=' '.join(str(d.get('title','')) for d in selected if d['table_name'].lower()==t['table_name'].lower()).lower()
            if explicit and explicit[0] not in period and explicit[0] not in field_text:
                blocks.append(f"{t['table_name']}: the source reporting period does not cover the requested year.")
    descriptors={}
    for d in defs.values():
        t=next((t for t in proposal['table_evidence'] if t['release_id']==d['release_id'] and t['table_name'].casefold()==d['table_name'].casefold()),{})
        descriptors[d['record_id']]=describe_field(d,t)
    proposal['field_semantics']={str(rid):value for rid,value in descriptors.items()}
    proofs=[validate_calculation(c,defs,descriptors) for c in p['calculations']]
    proposal['calculation_validation']=proofs
    intent_patterns={'percent':r'%|percent|share|proportion|fraction|\brate\b',
        'ratio':r'\bratio\b|\bper\b|fraction|proportion',
        'sum':r'\b(total|sum|combined|together|add)\b',
        'difference':r'\b(difference|subtract|minus|gap|more|fewer)\b'}
    for proof in proofs:
        if proof['operator'] in intent_patterns and not re.search(intent_patterns[proof['operator']],question,re.I):
            blocks.append(proof['label']+': the request does not ask for this derived calculation; return counts or preserve the explicitly requested operation.')
        if not proof['approved']:blocks.append(proof['label']+': '+proof['reason'])
    # Prevent one release from supplying a similarly named field for another.
    for s in p['selections']:
        d=defs[s['record_id']]
        if s['role']=='measure' and len(p['source_years'])>1:
            peers=[x for x in selected if x['variable_name']==d['variable_name']]
            if len({x['release_id'] for x in peers})!=len(p['source_years']):
                blocks.append(f"{d['variable_name']}: each requested release needs its own field definition.")
    return list(dict.fromkeys(blocks))


def prepare_catalog_proposal(plan,question):
    report('Validating source selections and calculation rules…')
    proposal=validate_proposal(plan,question)
    definitions={d['record_id']:d for d in proposal['definition_evidence']}
    normalized,notes=normalize_plan(plan,question,definitions)
    if normalized!=plan:proposal=validate_proposal(normalized,question)
    proposal['normalization']=notes
    blocks=semantic_check(proposal)
    proposal['validation'].update(blocks=blocks,semantic_status='blocked' if blocks else 'passed',execution_approved=not blocks)
    return proposal


def execute_catalog(answer, question):
    """Revalidate an untrusted proposal, then either execute or retain its blockers."""
    start=time.perf_counter()
    proposal=prepare_catalog_proposal(answer['catalog_plan'],question)
    blocks=proposal['validation']['blocks']
    answer={**answer,'catalog_plan':proposal['catalog_plan']}
    validation_seconds=time.perf_counter()-start
    proposal['validation'].update(blocks=blocks,semantic_status='blocked' if blocks else 'passed',execution_approved=not blocks,
        execution_scope='Source observations and evidence-backed arithmetic on the same selected population row; no implicit row aggregation, joins or inferred year equivalence.')
    if not blocks:
        proposal['validation']['completed_checks']=['exact physical fields and source codes','documented and observed row key','explicit row selectors',
            'source reporting period','bounded read-only compilation','numeric missingness policy','calculation relationship where applicable']
        proposal['validation']['required_next_checks']=[]
    if blocks:
        return {**answer,'catalog_proposal':proposal,'message':'I found relevant source fields, but this analysis has not run. '+blocks[0],
                'latency':{'validation_seconds':validation_seconds,'query_seconds':0.0}}
    p=proposal['catalog_plan'];defs={d['record_id']:d for d in proposal['definition_evidence']}
    from .intent_checks import check_plan,stamp
    intent_check=check_plan(p,question,proposal)
    proof_by_calc={json.dumps(c,sort_keys=True):proof for c,proof in zip(p['calculations'],proposal['calculation_validation'])}
    rows=[];sources=[];specs={};definitions={};warnings=list(answer.get('source_caveats',[]))
    technical_notes=list(p['assumptions'])+['Source release labels are shown separately from source reporting periods. Missing, suppressed and nonnumeric values remain empty. These answers do not infer reported versus imputed status.']
    if len(p['source_years'])>1:technical_notes.append('Each release uses its own source definition. Matching variable names do not establish comparability; no change or growth rate was calculated.')
    query_start=time.perf_counter()
    for year in p['source_years']:
        report(f'Reading source data for {year}…')
        selected=[defs[s['record_id']] for s in p['selections'] if s['role']=='measure' and int(defs[s['record_id']]['release_id'][6:10])==year]
        tables=list(dict.fromkeys(d['table_name'] for d in selected))
        path=annual_path(year);stat=path.stat()
        with readonly(path) as db:
            for table in tables:
                fields=[d for d in defs.values() if d['table_name']==table and int(d['release_id'][6:10])==year]
                columns=list(dict.fromkeys(d['variable_name'] for d in fields))
                filters=[f for f in p['filters'] if defs[f['record_id']] in fields]
                where=['"UNITID"=?'];tail=[]
                for f in filters:
                    col=quoted(defs[f['record_id']]['variable_name']);op=f['operator'];values=f['values']
                    if op=='in':where.append(f'{col} IN ({",".join("?" for _ in values)})')
                    elif op=='between':where.append(f'{col} BETWEEN ? AND ?')
                    else:where.append(f'{col} '+{'eq':'=','gt':'>','gte':'>=','lt':'<','lte':'<='}[op]+' ?')
                    tail.extend(values)
                sql='SELECT '+', '.join(quoted(c) for c in columns)+' FROM '+quoted(table)+' WHERE '+' AND '.join(where)+' LIMIT 2'
                t=next(t for t in proposal['table_evidence'] if t['table_name'].lower()==table.lower() and int(t['release_id'][6:10])==year)
                period='; '.join(dict.fromkeys(str(e['year_coverage']) for e in t['period_evidence'] if e.get('year_coverage')))
                for unitid in proposal['resolved_institutions'][str(year)]:
                    name=db.execute(f'SELECT INSTNM FROM "HD{year}" WHERE UNITID=?',(unitid,)).fetchone()[0]
                    values=db.execute(sql,[unitid]+tail).fetchmany(2)
                    if len(values)>1:raise ValueError('Population selectors returned multiple records; no catalog result was published.')
                    # Index the row by UPPER-cased physical column name: codebook
                    # variable_name casing (e.g. IC/COST 'chg2ay3') can differ from the
                    # physical column ('CHG2AY3'), which otherwise reads values as missing.
                    record={str(k).upper():v for k,v in dict(values[0]).items()} if values else {}
                    partition=['EFAIANT','EFASIAT','EFBKAAT','EFHISPT','EFNHPIT','EFWHITT','EF2MORT','EFUNKNT','EFNRALT']
                    if re.fullmatch(r'EF\d{4}A',table,re.I) and set(partition+['EFTOTLT'])<=set(columns):
                        counts=[numeric(record.get(c)) for c in partition];total=numeric(record.get('EFTOTLT'))
                        if total is not None and all(v is not None for v in counts) and sum(counts)!=total:
                            if p['calculations']:raise ValueError('The source race/ethnicity counts do not reconcile to their total; no percentages were published.')
                            warnings.append('The source race/ethnicity categories do not reconcile to the supplied total. Values are shown as recorded; no correction was applied.')
                    if re.fullmatch(r'EF\d{4}A',table,re.I) and {'EFTOTLM','EFTOTLW','EFTOTLT'}<=set(columns):
                        gender_counts=[numeric(record.get(c)) for c in ['EFTOTLM','EFTOTLW']];gender_total=numeric(record.get('EFTOTLT'))
                        if gender_total is not None and all(v is not None for v in gender_counts) and sum(gender_counts)!=gender_total:
                            if p['calculations']:raise ValueError('Source men/women counts do not reconcile to the selected population total; no percentages were published.')
                            warnings.append('Source men/women counts do not reconcile to the supplied total. Values are shown as recorded; no residual gender category was inferred.')
                    if any(record.get(c.upper()) is not None and numeric(record[c.upper()]) is None and str(record[c.upper()]).strip().startswith('-') for c in columns):
                        warnings.append('Negative source values were withheld pending a field-specific sentinel/sign interpretation; they were not treated as zero. Raw values are retained in the audit rows.')
                    calculations=[c for c in p['calculations'] if defs[c['input_record_ids'][0]] in fields]
                    consumed={rid for c in calculations for rid in c['input_record_ids']}
                    outputs=[(d,None,0) for d in selected if d['table_name']==table and d['record_id'] not in consumed]
                    outputs += [(defs[c['input_record_ids'][0]],c,index) for index,c in enumerate(calculations)]
                    for d,calc,index in outputs:
                        metric=re.sub(r'\d{4}','{YEAR}',table)+'::'+d['variable_name']+('::'+calc['operator']+'::'+str(index) if calc else '')
                        label=calc['label'] if calc else d['title']
                        if not calc and label.strip().casefold() in {'total employees','full-time employees','part-time employees'}:
                            chosen_codes={rid for f in filters for rid in f['code_record_ids']}
                            population_labels=[e['title'] for e in proposal['category_evidence'] if e['record_id'] in chosen_codes and e.get('title')]
                            if population_labels:label=max(population_labels,key=len)+' ('+label.lower()+')'
                        descriptor=proposal['field_semantics'][str(d['record_id'])]
                        unit=proof_by_calc[json.dumps(calc,sort_keys=True)]['unit'] if calc else descriptor['unit']
                        val=numeric(record.get(d['variable_name'].upper()));num=den=None;input_values=None
                        if calc:
                            input_values=[numeric(record.get(defs[rid]['variable_name'].upper())) for rid in calc['input_record_ids']]
                            op=calc['operator'];val=None
                            if op in {'percent','ratio'}:
                                num=input_values[0];den=numeric(record.get(defs[calc['denominator_record_id']]['variable_name'].upper()))
                                proof=proof_by_calc[json.dumps(calc,sort_keys=True)]
                                if den==0:warnings.append('A source denominator is zero; its calculated percentage/ratio remains missing.')
                                if proof['bounded_share'] and num is not None and den is not None and den>0 and num>den:raise ValueError('Category count exceeds its denominator; no catalog result was published.')
                                if num is not None and den is not None and den>0:val=(100 if op=='percent' else 1)*num/den
                            elif all(v is not None for v in input_values):
                                val=sum(input_values) if op=='sum' else input_values[0]-input_values[1]
                                if op=='difference' and proof_by_calc[json.dumps(calc,sort_keys=True)]['proof']['kind']=='total_minus_component' and val<0:
                                    raise ValueError('A component exceeds its source total; no difference was published.')
                        if val is not None and not math.isfinite(val):raise ValueError('A calculation produced a nonfinite result; no catalog result was published.')
                        specs[metric]={'label':label,'family':'catalog','unit':unit}
                        if calc:
                            involved=list(dict.fromkeys(calc['input_record_ids']+([calc['denominator_record_id']] if calc['denominator_record_id'] else [])))
                            definitions[metric]='\n\n'.join(defs[rid]['title']+': '+defs[rid]['long_description'] for rid in involved)+'\n\nCalculation: '+formula_text(calc,defs)
                        else:definitions[metric]=d['long_description']
                        # Column-encoded-year tables (net price NPIST2, prior-year tuition)
                        # are table-labeled by collection year; use the field's own academic
                        # year from its title so the period reflects the actual data year.
                        field_period=period
                        if not calc:
                            _ym=re.search(r'\b(?:19|20)\d{2}[-–/]\d{2,4}\b',str(d.get('title','')))
                            if _ym:field_period=_ym.group(0)
                        rows.append(dict(institution=name,unitid=unitid,observation_year=year,entry_cohort_year=None,reporting_period=field_period,
                            metric=metric,measure=label,unit=unit,value=val,release=d['release_id'],provisional='Provisional' in d['release_id'],
                            status='ok' if val is not None else 'missing',numerator=num,denominator=den,series_segment='source observations'))
                        rows[-1]['source_value']=record.get(d['variable_name'].upper())
                        rows[-1]['unit_metadata']=({'version':1,'status':'verified','basis':'Validated typed calculation','unit':unit,
                            'inputs':[proposal['field_semantics'][str(rid)]['unit_metadata'] for rid in calc['input_record_ids']]} if calc else descriptor['unit_metadata'])
                        if calc:
                            rows[-1]['input_values']=input_values
                            rows[-1]['calculation_evidence']=proof_by_calc[json.dumps(calc,sort_keys=True)]
                        docs=[]
                        for f in fields:
                            e=f['evidence'];docs.append({**e,'long_description':f['long_description'],'documented_table':table,'physical_table':table,'location_override':False,'issues':[]})
                        sources.append(dict(metric=metric,year=year,unitid=unitid,database=str(path),database_size=stat.st_size,database_mtime_ns=stat.st_mtime_ns,
                            table=table,columns=columns,filters=filters,formula={'typed_calculation':calc,'canonical_expression':formula_text(calc,defs)} if calc else 'direct source observation',sql=sql,parameters=[unitid]+tail,
                            codebook_evidence=docs,code_filters=proposal['category_evidence']))
    query_seconds=time.perf_counter()-query_start
    result=dict(plan=dict(metrics=list(specs),institutions=p['institutions'],years=p['source_years'],time_basis='source_release',output=p['output']),
                catalog_plan=p,metric_specs=specs,observation_years=p['source_years'],rows=rows,sources=sources,warnings=warnings,technical_notes=technical_notes,definitions=definitions,
                created_at=datetime.now(timezone.utc).isoformat(),registry_sha256=proposal['catalog_identity'],
                review_status='Catalog-bound observations and source-proven same-row calculations; row keys, selectors, periods, units, relationships and numeric missingness validated. No implicit row aggregation or fact joins.',
                semantic_validation=proposal['validation'],catalog_evidence=proposal,
                field_semantics=proposal['field_semantics'],calculation_validation=proposal['calculation_validation'],
                planning_validation={'preflight':answer.get('preflight_validation'),'repair_attempts':answer.get('validation_attempts',[])},
                coverage={'requested_cells':len(rows),'available_cells':sum(r['status']=='ok' for r in rows)})
    result['result_id']=sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()[:16]
    stamp(result,intent_check)
    return finalize_answer({**answer,'intent':'analyze','result':result,'catalog_proposal':proposal,
                            'latency':{'validation_seconds':validation_seconds,'query_seconds':query_seconds}},question)
