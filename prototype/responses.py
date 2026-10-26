"""Source-bound summaries and presentation rules; never retrieves or changes data."""
import re
from copy import deepcopy
from .semantics import display_result,is_currency,currency_text,UNVERIFIED

MAX_DEFAULT_CHART_CATEGORIES=12


def comparison_categories(rows):
    """Count category labels, not cells or years; different units plot separately."""
    units={r['unit'] for r in rows}
    return max((max(len({r['measure'] for r in rows if r['unit']==unit}),
                    len({r['institution'] for r in rows if r['unit']==unit})) for unit in units),default=0)


def uses_context(question):
    from .time_scope import is_trend_followup
    if is_trend_followup(question):return True
    q=question.lower().strip()
    if re.search(r'\b(same|that year|those|these|instead|previous|above|them|it)\b|^(what about|how about|and |add |also )',q):return True
    if re.search(r'\b(applicants?|applications?|admission|admits?|matriculated|yield|enrollment|graduation|financial aid|grants?|scholarships?|sat|bachelor)',q):return False
    return bool(re.search(r'^(show |plot |chart |export |download |make |change |hide )',q) or re.fullmatch(r'(?:in |for )?(?:19|20)\d{2}[?.]?',q))


def value_text(row):
    if row.get('result_type') in {'categorical','text','identifier','bounded'} or row.get('response_label'):
        return row.get('response_label') or 'Missing observation'
    if row['status']=='not_collected':return 'not collected'
    if row['status']!='ok' or row['value'] is None:return 'not reported'
    value=row['value'];unit=row['unit']
    if is_currency(unit):return currency_text(value,unit)
    if unit in {'monetary amount',UNVERIFIED}:return f'{value:,.2f}'.rstrip('0').rstrip('.')+' (currency/scale unverified)'
    if unit=='percent':return f'{value:,.2f}%'
    if unit=='ratio':return f'{value:,.4f}'.rstrip('0').rstrip('.')
    if unit in {'source units','FTE','dollars','monetary amount','percentage points'}:return f'{value:,.2f}'.rstrip('0').rstrip('.')
    return f'{value:,.0f}'+(' points' if unit=='score' else '')


def summarize(result):
    result=display_result(result)
    if result.get('result_schema_version')==2:
        rows=result['rows']
        if not rows:return 'No reporting institutions matched the selected source responses. The selected scope and source predicates are retained in Definitions & sources.'
        names=list(dict.fromkeys(r['institution'] for r in rows))
        if result.get('result_kind')=='institution_list':
            population=result['observation_plan'].get('population') or {}
            qualifier=('Title IV ' if population.get('title_iv') else '')+('degree-granting ' if population.get('degree_granting') is True else 'nondegree ' if population.get('degree_granting') is False else '')
            counts=result['coverage']['matching_institutions']
            units={r['unitid']:r['institution'] for r in rows}
            scope=', '.join(str(n)+' in release '+str(y) for y,n in sorted(counts.items())) if len(counts)>1 else str(next(iter(counts.values())))
            text=f"{scope} {qualifier}reporting institution(s) match the selected source responses: "+'; '.join(list(units.values())[:8])+'.'
            return text+(' The table and download contain the complete list.' if len(units)>8 else '')
        if len(names)>1:
            groups={}
            for r in rows:
                groups.setdefault((r['measure'],r['reporting_period'],value_text(r)),[]).append(r['institution'])
            facts=[f"{measure}: {value} at {', '.join(institutions)} ({period})" for (measure,period,value),institutions in list(groups.items())[:8]]
            return '; '.join(facts)+'.'+(' The table and download contain the remaining responses.' if len(groups)>8 else '')
        facts=[f"{r['institution']} — {r['measure']}: {value_text(r)} ({r['reporting_period']})" for r in rows[:8]]
        return '; '.join(facts)+'.'+(' The table and download contain the remaining responses.' if len(rows)>8 else '')
    rows=result['rows'];good=[r for r in rows if r['status']=='ok'];sentences=[]
    if not rows:return 'No matching data was found. Try another institution, measure, or year.'
    if not good:
        reason='not collected in the requested years' if all(r['status']=='not_collected' for r in rows) else 'not reported in the available source records'
        return f'The requested values are {reason}. Missing values have not been treated as zero.'
    metrics=list(dict.fromkeys(r['metric'] for r in rows));names=list(dict.fromkeys(r['institution'] for r in rows));years=sorted({r['observation_year'] for r in rows})
    if len(names)==1 and len(years)==1:
        facts='; '.join(f"{r['measure']}: {value_text(r)}" for r in good[:4])
        sentences.append(f"For {names[0]} ({good[0]['reporting_period']}), {facts}.")
        if len(good)>4:sentences.append('The table or download includes the remaining requested measures.')
    elif len(metrics)==1 and len(years)>1:
        for name in names[:3]:
            series=sorted([r for r in rows if r['institution']==name],key=lambda r:r['observation_year'])
            first,last=series[0],series[-1]
            if first['status']=='ok' and last['status']=='ok':
                sentences.append(f"{name}’s {first['measure'].lower()} was {value_text(first)} in {first['observation_year']} and {value_text(last)} in {last['observation_year']}.")
            else:sentences.append(f"{name} has {sum(r['status']=='ok' for r in series)} reported {series[0]['measure'].lower()} observations across {years[0]}–{years[-1]}; an endpoint is unavailable.")
        if len(names)>3:sentences.append(f'The chart or download includes all {len(names)} institutions.')
    elif len(metrics)==1 and len(years)==1:
        facts='; '.join(f"{r['institution']} — {r['measure']}: {value_text(r)}" for r in good[:4])
        sentences.append(f"{facts} ({good[0]['reporting_period']}).")
        if len(good)>4:sentences.append(f'The chart or download includes all {len(names)} requested institutions.')
    else:
        r=good[0]
        sentences.append(f"The results cover {len(names)} institution(s), {len(metrics)} measure(s), and {len(years)} observation year(s).")
        sentences.append(f"For example, {r['institution']}’s {r['measure'].lower()} was {value_text(r)} ({r['reporting_period']}).")
    if any(r['status']!='ok' for r in rows):
        missing=sum(r['status']=='missing' for r in rows);uncollected=sum(r['status']=='not_collected' for r in rows)
        sentences.append(f'{missing} value(s) were not reported and {uncollected} were not collected; neither is treated as zero.')
    if any(r.get('entry_cohort_year') is not None for r in rows):
        sentences.append('Outcome/reporting years and entering cohort years are identified separately in the results.')
    elif len(sentences)==1:sentences.append('The reporting period and source definitions are available below.')
    return ' '.join(sentences[:5])


def presentation_for(result,question=''):
    if result.get('result_schema_version')==2:
        return {'chart_type':'none','show_table':True,'table_reason':'Source responses are shown in a table; category codes are not quantities.','title':None,'x_label':None,'y_label':None,'y_min':None,'y_max':None,'sort':'auto','color':None}
    result=display_result(result)
    q=question.lower();plan=result['plan'];rows=result['rows']
    export=plan['output']=='export' or bool(re.search(r'\b(csv|excel|export|spreadsheet|download)\b',q))
    table=export or bool(re.search(r'\b(table|raw data|rows)\b',q))
    years={r['observation_year'] for r in rows};names={r['institution'] for r in rows}
    same_unit=len({r['unit'] for r in rows})==1
    kind='line' if len(years)>1 else 'bar' if len(names)>1 or (same_unit and (len(plan['metrics'])>1 or len(rows)>1 and any(r.get('groups') for r in rows))) else 'none'
    if plan['output']=='chart' and kind=='none':kind='bar'
    if table and not re.search(r'\b(chart|plot|graph)\b',q):kind='none'
    if plan['output']=='answer' and not re.search(r'\b(chart|plot|graph)\b',q):kind='none'
    crowded=len(years)<=1 and comparison_categories(rows)>MAX_DEFAULT_CHART_CATEGORIES
    reason=None
    if crowded and not re.search(r'\b(chart|plot|graph)\b',q):
        kind='none';table=True
        reason=f'Showing a table because this comparison has more than {MAX_DEFAULT_CHART_CATEGORIES} categories. You can ask for a chart.'
    if any(r['unit'] in {'unknown','source units','identifier','coded'} for r in rows):
        kind='none';table=True;reason='Showing a table because a measurement unit is unresolved or the field is an identifier/category.'
    return {'chart_type':kind,'show_table':table or kind=='none','table_reason':reason,'title':None,'x_label':None,'y_label':None,'y_min':None,'y_max':None,'sort':'auto','color':None}


def finalize_answer(answer,question=''):
    if 'result' not in answer:return answer
    from .progress import report
    result=answer['result']
    from .intent_checks import check_result
    warnings=check_result(result)
    if warnings:result['warnings']=list(dict.fromkeys(result.get('warnings',[])+warnings))
    report('Preparing your answer and display…')
    return {**answer,'message':summarize(result),'presentation':answer.get('presentation') or presentation_for(result,question)}


def adjust_presentation(question,previous_answer):
    """Recognize display-only requests locally; reuse the exact result and provenance."""
    from .charts import normalize_edit_question
    q=normalize_edit_question(question);low=q.lower();change={}
    if re.fullmatch(r'(?:please )?(?:set|change|rotate|make)(?: the)? (?:(?:[xy][- ]axis|axis|year|reporting[- ]period) )?(?:tick(?:mark)? )?labels?(?: angle)?(?: to)? (?:horizontal|vertical|flat|[−-]?\d+)(?:\s*(?:°|degrees?))?',low):
        return {'intent':'clarify','message':'Axis tick-label rotation is currently unavailable. Label angles are set automatically; the data has not changed.'}
    from .charts import extra_edits,edit_clauses
    clauses=edit_clauses(q)
    if len(clauses)>1:
        first=adjust_presentation(clauses[0],previous_answer)
        if first is None:return None
        current=first
        for clause in clauses[1:]:
            edited=adjust_presentation(clause,current)
            if not edited or edited.get('mode')!='presentation adjustment':return {'intent':'clarify','message':'I could not apply every part of that chart edit. No settings were changed. Try the edits individually or use Format chart.'}
            current=edited
        return current
    extra=extra_edits(q,previous_answer)
    if extra:change=extra
    elif re.fullmatch(r'(?:please )?(?:show|display)(?: me)? (?:the )?(?:table|raw data|rows)',low):change={'show_table':True}
    elif re.fullmatch(r'(?:please )?hide (?:the )?(?:table|raw data|rows)',low):change={'show_table':False}
    elif re.fullmatch(r'(?:please )?(?:show|make|use|switch(?: it| this)? to|change to|change (?:the )?chart(?: type)? to)(?: me)?(?: it| this| the| a| as| to)* (line|bar)(?: chart| graph)?',low):change={'chart_type':'line' if 'line' in low else 'bar'}
    elif re.fullmatch(r'(?:please )?(?:show|plot|visualize)(?: me)? (?:it|this|these results|the data)(?: as a chart)?',low):change={'chart_type':'auto'}
    elif (match:=re.fullmatch(r'(?:reset|clear) (?:the )?([xy])[- ]axis(?: range)?',low)):
        if match[1]=='x' and previous_answer and 'result' in previous_answer and (previous_answer.get('presentation') or presentation_for(previous_answer['result'])).get('chart_type')!='bar':
            return {'intent':'clarify','message':'This chart has reporting periods on its X-axis. Changing the displayed years requires a new data request; its numeric range is on the Y-axis. No settings were changed.'}
        change={'y_min':None,'y_max':None}
    elif (match:=re.fullmatch(r'(?:set|reset|change|make) (?:the )?([xy])[- ]?axis(?: range)?(?: to| from)? ([+-]?(?:\d[\d,]*(?:\.\d+)?|\.\d+))\s*(?:-|–|to)\s*([+-]?(?:\d[\d,]*(?:\.\d+)?|\.\d+))(?:%)?',low)):
        if match[1]=='x' and previous_answer and 'result' in previous_answer and (previous_answer.get('presentation') or presentation_for(previous_answer['result'])).get('chart_type')!='bar':
            return {'intent':'clarify','message':'This chart has reporting periods on its X-axis. Changing the displayed years requires a new data request; its numeric range is on the Y-axis. No settings were changed.'}
        change={'y_min':float(match[2].replace(',','')),'y_max':float(match[3].replace(',',''))}
        if change['y_min']>=change['y_max']:return {'intent':'clarify','message':'Choose a y-axis minimum below its maximum. The data has not changed.'}
    elif (match:=re.fullmatch(r'(?:please )?(?:set|change|rename) (?:the )?(chart title|title|[xy][- ]?axis(?: label| title)?) to\s+(.+)',q,re.I)):
        field='x_label' if match[1].lower().startswith('x') else 'y_label' if match[1].lower().startswith('y') else 'title'
        value=match[2].strip();quoted=len(value)>=2 and (value[0],value[-1]) in {('"','"'),("'","'"),('“','”'),('‘','’')}
        if quoted:value=value[1:-1].strip()
        if not value:return {'intent':'clarify','message':'Provide a nonempty chart title or axis label. The data has not changed.'}
        if field!='title' and not re.search(r'label|title',match[1],re.I) and not quoted and re.fullmatch(r'[+\-\d.,%\s–]+|[+\-\d.,%\s]+to[+\-\d.,%\s]+',value,re.I):
            return {'intent':'clarify','message':'To rename the axis, provide a label such as “Year”. Numeric range edits use “Set y-axis range to 0–100”; changing the displayed years requires a new data request. The data has not changed.'}
        change={field:value}
    elif (match:=re.fullmatch(r'(?:make|set|change) (?:the )?(?:chart|lines?|bars?)(?: color)?(?: to)? (blue|red|green|gray|grey|orange|purple|black|navy|#[0-9a-f]{6})',low)):change={'color':match[1],'series_colors':{}}
    elif (match:=re.fullmatch(r'(?:sort|order) (?:the )?bars(?: by value)?(?: in)? (ascending|descending|alphabetical|alphabetically)(?: order)?',low)):change={'sort':'alphabetical' if match[1]=='alphabetically' else match[1]}
    elif (re.search(r'^(make|change|adjust|set|remove|add|reset|increase|decrease|rotate|rename)\b',low) and re.search(r'\b(chart|axis|gridlines|legend|font|background|markers|title|labels|blue|red|green|gray|grey|dashed|dotted|colors?)\b',low)
          or re.search(r'^(?:show|hide|move) (?:the )?(?:legend|[xy][- ]?axis|point markers|gridlines|value labels)\b',low)):
        return {'intent':'clarify','message':'Use Format chart for the available controls, or ask for a title, axis label, numeric range, series color, font size, legend position, value labels, markers, gridlines or reference line. I could not apply this wording; the data has not changed.'}
    else:return None
    if not previous_answer or 'result' not in previous_answer:return {'intent':'clarify','message':'Ask a data question first, then I can change its chart or table.'}
    if previous_answer['result'].get('result_schema_version')==2 and any(k not in {'show_table','chart_type'} or (k=='chart_type' and v!='none') or (k=='show_table' and not v) for k,v in change.items()):
        result=previous_answer['result']
        return {'intent':'analyze','result':result,'presentation':presentation_for(result),'mode':'presentation adjustment',
                'message':'These source responses are displayed as a table. Category codes and source-defined bounds are not numerical chart values. You can ask for counts of institutions by response to create a frequency chart; no new calculation has run.'}
    result=previous_answer['result'];presentation=deepcopy(previous_answer.get('presentation') or presentation_for(result))
    if change.get('chart_type')=='auto':change['chart_type']='line' if len(result['observation_years'])>1 else 'bar'
    if change.get('y_max') is not None and all(r['unit']=='percent' for r in result['rows']) and not 0<=change['y_min']<change['y_max']<=100:
        return {'intent':'clarify','message':'Percentage axes use a 0–100 scale. Choose bounds within that range; the data has not changed.'}
    presentation.update(change)
    if presentation['chart_type']=='none' and not presentation['show_table']:return {'intent':'clarify','message':'This result is currently a table only. Ask for a line or bar chart before hiding the table.'}
    return {'intent':'analyze','plan':result['plan'],'catalog_plan':result.get('catalog_plan'),'result':result,'presentation':presentation,'message':'Here is the updated display. It uses the same data and source references; no new query ran.','mode':'presentation adjustment'}


# ===== merged from result_text.py (consolidation) =====
"""Reader-facing evidence and substantive caveats; full originals stay in audit."""
from pathlib import Path
import re
from .catalog import DATA,readonly

TECHNICAL_PREFIXES=('Source release labels are shown separately from source reporting periods.',
    'Source row domains, missingness policy, join cardinality and typed calculations are retained in the audit.')

def visible_warnings(result):
    assumptions=set(result.get('catalog_plan',{}).get('assumptions',[]))
    output=[]
    for warning in result.get('warnings',[]):
        if ('technical_notes' not in result and warning in assumptions) or warning.startswith(TECHNICAL_PREFIXES):continue
        if warning.startswith('Results use the confirmed reporting institution.'):
            names=list(dict.fromkeys(r['institution'] for r in result['rows']))
            identity=result.get('institution_identity',{})
            mentions=identity.get('original_mentions',[])
            if mentions:
                from .institution_confirmation import needs_reporting_scope_warning,normalized,resolve
                unitids=identity.get('unitids') or list(dict.fromkeys(r.get('unitid') for r in result['rows'] if r.get('unitid')))
                scoped=identity.get('scope_mentions')
                if scoped is None:
                    scoped=[]
                    for text in mentions:
                        selected=identity.get('confirmed_choices',{}).get(normalized(text))
                        if selected in unitids:
                            if needs_reporting_scope_warning(text,selected):scoped.append(text)
                        elif resolve(text,{}) not in unitids and any(needs_reporting_scope_warning(text,uid) for uid in unitids):scoped.append(text)
                if unitids and not scoped:continue
                mentions=scoped or mentions
            if len(names)==1 and len(mentions)==1:warning='Figures are reported by '+names[0]+'; these results do not establish separate figures for '+mentions[0]+'.'
        elif warning.startswith('Complete-case calculations exclude'):warning='This calculation excludes observations with missing values or weights.'
        elif warning.startswith('A source denominator is zero;'):warning='A percentage or ratio could not be calculated because its denominator is zero.'
        if warning not in output:output.append(warning)
    if any(r.get('provisional') for r in result['rows']) and not any('provisional' in w.lower() for w in output):
        output.append('The latest-release figures are provisional and may be revised.')
    if any(r['status']!='ok' for r in result['rows']) and not any(re.search(r'missing|not.reported|not.collected',w,re.I) for w in output):
        output.append('Some requested values are unavailable. Missing values have not been treated as zero.')
    if any(d.get('location_override') for s in result.get('sources',[]) for d in s.get('codebook_evidence',[])):
        output.append('This analysis uses an implementation-reviewed correction to a documented source location. Details are included in the download.')
    return output

def concise(text,limit=300):
    text=re.sub(r'\s+',' ',text).strip()
    text=re.split(r'\b(?:CREDIT\s*[-:]|NOTE[S]?\s*:)',text,maxsplit=1)[0].strip()
    text=text.replace('U.S.','U§S§')
    text=re.split(r'(?<=[.!?])\s+(?=[A-Z])',text,maxsplit=1)[0].replace('U§S§','U.S.')
    if len(text)>limit:text=text[:limit].rsplit(' ',1)[0]+'…'
    return text

def definition_summary(result,metric):
    text=result.get('definitions',{}).get(metric,'')
    parts=[p.strip() for p in re.split(r'\n\s*\n',text) if p.strip() and not p.startswith('Calculation:')]
    return list(dict.fromkeys(concise(p) for p in parts if concise(p)))

def metric_label(result,metric,fallback):
    friendly=fallback
    for source in result.get('sources',[]):
        if source['metric']!=metric:continue
        for doc in source.get('codebook_evidence',[]):
            friendly=re.sub(r'\b'+re.escape(doc['variable_name'])+r'\b',lambda _:doc['title'],friendly)
    if friendly!=fallback:return friendly
    if re.match(r'^[A-Z][A-Z0-9_]{3,}\b',fallback):
        definitions=definition_summary(result,metric)
        if definitions:return definitions[0].split(': ',1)[0]+(' (%)' if next((r['unit'] for r in result['rows'] if r['metric']==metric),'')=='percent' else '')
    return fallback

def documents(result):
    return {d['record_id']:d for s in result.get('sources',[]) for d in s.get('codebook_evidence',[])}

def calculation_summary(result,metric):
    docs=documents(result)
    def name(rid):return docs.get(rid,{}).get('title','selected source value')
    for source in result.get('sources',[]):
        if source['metric']!=metric:continue
        f=source.get('formula')
        if isinstance(f,dict) and f.get('typed_calculation'):
            c=f['typed_calculation'];inputs=[name(rid) for rid in c['input_record_ids']];op=c['operator']
            if op in {'percent','ratio'}:return inputs[0]+' ÷ '+name(c['denominator_record_id'])+(' × 100' if op=='percent' else '')+'.'
            return (' + ' if op=='sum' else ' − ').join(inputs)+'.'
        if isinstance(f,str):
            match=re.fullmatch(r'100(?:\.0)?\*([A-Za-z]\w*)/NULLIF\(([A-Za-z]\w*),0\)',f)
            if match:
                names={d['variable_name']:d['title'] for d in source.get('codebook_evidence',[])}
                if all(v in names for v in match.groups()):return names[match[1]]+' ÷ '+names[match[2]]+' × 100.'
    p=result.get('catalog_plan',{})
    if p.get('version')==2:
        expressions={'x'+e['id']:e for e in p['expressions']}
        aggregates={'a'+s['id']+'_'+a['id']:a for s in p['sources'] for a in s['aggregates']}
        def ref(r,depth=0):
            if depth>4:return 'an intermediate calculation (full formula in download)'
            if re.fullmatch(r'f[a-zA-Z][a-zA-Z0-9_]*_\d+',r):return name(int(r.rsplit('_',1)[1]))
            if r in aggregates:
                a=aggregates[r];op=a['operator'].replace('_',' ')
                return op+' of '+name(a['record_id'])+(' using '+name(a['weight_record_id'])+' as weights' if a.get('weight_record_id') else '')
            if r not in expressions:return 'selected source value'
            e=expressions[r];values=[ref(i,depth+1) for i in e['inputs']];op=e['operator']
            if op in {'add','subtract','multiply','divide','percent','percent_change'}:
                a,b=values
                if op=='percent_change':return '('+a+' − '+b+') ÷ '+b+' × 100'
                return '('+a+{'add':' + ','subtract':' − ','multiply':' × ','divide':' ÷ ','percent':' ÷ '}[op]+b+')'+(' × 100' if op=='percent' else '')
            return op.replace('_',' ')+' of '+values[0]+(' using '+values[1]+' as weights' if op=='weighted_mean' else '')
        if metric in expressions or metric in aggregates:return ref(metric)+'.'
    # Reviewed calculations retain their source documentation without exposing SQL.
    rows=[r for r in result['rows'] if r['metric']==metric]
    if rows and any(r.get('numerator') is not None and r.get('denominator') is not None for r in rows):
        return 'Numerator ÷ denominator'+(' × 100.' if rows[0]['unit']=='percent' else '.')
    return None

def _table_metadata(keys):
    """Read table-level codebook rows for exact executed release/table pairs."""
    with readonly(DATA/'metadata_catalog.sqlite') as db:
        return {key:[dict(r) for r in db.execute('''SELECT table_name,survey,year_coverage,title FROM table_docs
            WHERE release_id=? AND table_name=? COLLATE NOCASE ORDER BY record_id''',key)] for key in keys}


def source_summary(result):
    executed={}
    for source in result.get('sources',[]):
        release=Path(source['database']).parent.name
        table=source['table']
        executed.setdefault((release,table.casefold()),table)
    keys=sorted(executed)
    metadata=_table_metadata(keys) if keys else {}
    rows=[];groups={};notes=[]
    for key in keys:
        release,_=key;table=executed[key];docs=metadata.get(key,[])
        documented_names=list(dict.fromkeys(d['table_name'] for d in docs if d.get('table_name')))
        if len(documented_names)==1:table=documented_names[0]
        release_label=release.removeprefix('IPEDS_').replace('_',' · ')
        release_label=re.sub(r'(?<=\d)-(?=\d)','–',release_label)
        fields={}
        for field in ['survey','year_coverage','title']:
            values=list(dict.fromkeys(str(d.get(field) or '').strip() for d in docs if str(d.get(field) or '').strip()))
            if len(values)==1:fields[field]=values[0]
            elif len(values)>1:
                fields[field]='Conflicting metadata'
                notes.append(release_label+' · '+table+': conflicting '+{'survey':'survey names','year_coverage':'year coverage','title':'table titles'}[field]+' — '+'; '.join(values)+'.')
            else:fields[field]='Not documented'
        if not docs:notes.append(release_label+' · '+table+': table-level source metadata is unavailable.')
        elif any(v=='Not documented' for v in fields.values()):notes.append(release_label+' · '+table+': some table-level source metadata is not documented.')
        title=fields['title']
        if title=='Not documented':title='Table description not documented'
        elif title=='Conflicting metadata':title='Conflicting source table descriptions'
        elif fields['year_coverage'] not in {'Not documented','Conflicting metadata'}:
            # Strip only the exact documented period suffix, shown separately
            # in its own column. Do not invent a shared title or reporting year.
            title=re.sub(r'\s*[:;—–-]?\s*'+re.escape(fields['year_coverage'])+r'\s*$', '',title,flags=re.I).strip(' :;,—–-') or fields['title']
        row={'IPEDS release':release_label,'Survey':fields['survey'],'Year coverage':fields['year_coverage'],'Table':table}
        rows.append(row)
        groups.setdefault(title,[]).append(row)
    return {'sources':rows,'source_groups':[{'title':title,'rows':items} for title,items in groups.items()],
            'source_notes':list(dict.fromkeys(notes))}


def evidence_summary(result):
    institutions=list(dict.fromkeys(r['institution'] for r in result['rows']))
    periods=list(dict.fromkeys(r['reporting_period'] for r in result['rows']))
    population=[]
    for s in result.get('sources',[]):
        for c in s.get('code_filters',[]):
            label=c.get('title') or c.get('value_label')
            if label and label not in population:population.append(label)
    return {'institutions':institutions,'periods':periods,'population':population,**source_summary(result)}
