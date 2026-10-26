"""Source-bound summaries and presentation rules; never retrieves or changes data."""
import re
from copy import deepcopy
from .units import display_result,is_currency,currency_text,UNVERIFIED

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
    from .chart_format import normalize_edit_question
    q=normalize_edit_question(question);low=q.lower();change={}
    if re.fullmatch(r'(?:please )?(?:set|change|rotate|make)(?: the)? (?:(?:[xy][- ]axis|axis|year|reporting[- ]period) )?(?:tick(?:mark)? )?labels?(?: angle)?(?: to)? (?:horizontal|vertical|flat|[−-]?\d+)(?:\s*(?:°|degrees?))?',low):
        return {'intent':'clarify','message':'Axis tick-label rotation is currently unavailable. Label angles are set automatically; the data has not changed.'}
    from .chart_format import extra_edits,edit_clauses
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
