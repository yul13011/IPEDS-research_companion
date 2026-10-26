"""Readable chart specifications from validated rows; never changes source results."""
import re,textwrap
import altair as alt
import pandas as pd
from .units import display_result,is_currency,currency_text,unit_title as currency_unit_title,UNVERIFIED

PALETTE=['#24658A','#C47A28','#78649B','#398278']

def label(text):
    text=re.sub(r'\s+',' ',str(text)).strip()
    text=re.sub(r'\s*(?:% of undergraduates|percent of undergraduates)$','',text,flags=re.I)
    text=re.sub(r'\s+total$','',text,flags=re.I) if not re.fullmatch(r'(grand |overall )?total',text,re.I) else text
    return text

def formatted(value,unit):
    if pd.isna(value):return 'Not reported'
    if unit=='percent':return f'{value:,.1f}%'
    if is_currency(unit):return currency_text(value,unit,0)
    if unit=='ratio':return f'{value:,.4f}'.rstrip('0').rstrip('.')
    if unit in {'FTE','percentage points'}:return f'{value:,.1f}'+(' pp' if unit=='percentage points' else '')
    return f'{value:,.0f}' if float(value).is_integer() else f'{value:,.1f}'

def period(row,cohort=False):
    if cohort and pd.notna(row.get('entry_cohort_year')):return str(int(row['entry_cohort_year']))
    text=str(row.get('reporting_period',''));years=re.findall(r'\b(?:19|20)\d{2}\b',text)
    short=re.search(r'((?:19|20)\d{2})[-–/](\d{2})\b',text)
    if short:return short[1]+'–'+short[2]
    if len(set(years))>1:return min(years)+'–'+max(years)[-2:]
    if years:return ('FY ' if 'fiscal' in text.lower() else 'Fall ' if 'fall' in text.lower() else '')+years[-1]
    return str(int(row['observation_year']))

def prepare(result):
    result=display_result(result)
    frame=pd.DataFrame(result['rows']).copy(deep=True)
    # Older catalog results used a different line group for every release.
    # Release provenance is not a protocol break; normalize only those legacy
    # generated markers, leaving explicit scope/protocol segments intact.
    legacy=frame['series_segment'].fillna('').str.fullmatch(r'source release \d{4}')
    frame.loc[legacy,'series_segment']='source observations'
    def readable(row):
        text=row['measure']
        if re.match(r'^[A-Z][A-Z0-9_]{3,}\b',text):
            definition=result.get('definitions',{}).get(row['metric'],'')
            if ': ' in definition:text=definition.split(': ',1)[0]
        if row.get('groups'):
            group='; '.join(g.split(': ',1)[-1] for g in row['groups'])
            text=group if len(result['plan']['metrics'])==1 else text.split(' · ')[0]+' · '+group
        return label(text)
    frame['display_measure']=[readable(r) for r in result['rows']]
    # Keep labels distinct if shortening would collapse two different measures.
    for display,part in frame.groupby('display_measure'):
        if part['measure'].nunique()>1:frame.loc[part.index,'display_measure']=part['measure']
    frame['display_value']=[formatted(r['value'],r['unit']) for r in result['rows']]
    frame['plot_value']=frame['value'].where(frame['status']=='ok',None)
    cohort=result['plan'].get('time_basis') in {'entry_cohort','cohort'} and frame['entry_cohort_year'].notna().all()
    frame['period_label']=[period(r,cohort) for r in result['rows']]
    frame['total_panel']=frame['measure'].str.fullmatch(r'(?i)(?:grand total|total undergraduates|total undergraduate enrollment|all ranks)')
    return frame,cohort

def comparison_title(data,total):
    if total:return 'Total reported population'
    names=' '.join(data['display_measure']).lower()
    if sum(w in names for w in ['hispanic','asian','black','white','alaska native','nonresident'])>=3:
        population={'students':'Enrollment','awards':'Awards','employees':'Employees'}.get(data['unit'].iloc[0],'Population')
        return population+' by race and ethnicity'
    if re.search(r'\b(men|male)\b',names) and re.search(r'\b(women|female)\b',names):return 'Population by gender'
    if re.search(r"bachelor|master|certificate|doctor",names):return 'Awards by degree level'
    return data['display_measure'].iloc[0] if data['display_measure'].nunique()==1 else 'Category comparison'

def population_scope(result):
    labels=[]
    for source in result.get('sources',[]):
        for code in source.get('code_filters',[]):
            if code.get('variable_name') in {'EFALEVEL','EFFYLEV'} and code.get('title') not in labels:labels.append(code['title'])
    return '; '.join(labels)

def unit_title(unit):
    if is_currency(unit) or unit in {'monetary amount',UNVERIFIED}:return currency_unit_title(unit)
    return {'percent':'Percent (%)','students':'Students','employees':'Employees','awards':'Awards','items':'Items','percentage points':'Percentage points'}.get(unit,unit.capitalize())

def domain(values,unit,temporal,presentation):
    valid=values.dropna()
    if presentation.get('y_min') is not None:return [presentation['y_min'],presentation['y_max']]
    if not len(valid):return [0,100] if unit=='percent' else [0,1]
    low,high=float(valid.min()),float(valid.max())
    if unit=='percent' and not temporal:return [0,100]
    if temporal:
        pad=max((high-low)*.12,1 if unit=='percent' else abs(high)*.03 or 1)
        return [max(0,low-pad) if low>=0 else low-pad,min(100,high+pad) if unit=='percent' else high+pad]
    return [min(0,low)*1.15,max(0,high)*1.15 or 1]

def series_names_for_context(result,presentation):
    """The same series domains as panels, without constructing Altair charts."""
    frame,_=prepare(result)
    if frame['unit'].isin(['unknown','source units','identifier','coded']).any():return []
    names=[]
    for _,part in frame.groupby(['unit','total_panel'],sort=False):
        if presentation['chart_type']=='line' and part['display_measure'].nunique()>1:
            labels=(part['institution']+' · '+part['display_measure']) if part['institution'].nunique()>1 else part['display_measure']
        else:labels=part['institution']
        names.extend(labels)
    return list(dict.fromkeys(names))


def panels(result,presentation):
    if result.get('result_schema_version')==2:return []
    """Return all chart panels, titles and notes; no truncation or aggregation."""
    frame,cohort=prepare(result);temporal=presentation['chart_type']=='line'
    if frame['unit'].isin(['unknown','source units','identifier','coded']).any():return []
    names=list(dict.fromkeys(frame['institution']));palette=alt.Scale(domain=names,range=[PALETTE[i%4] for i in range(len(names))])
    output=[]
    for (unit,total),unit_frame in frame.groupby(['unit','total_panel'],sort=False):
        # Comparisons sharing units receive the same numerical scale, including
        # line batches and repeated panels. Totals have their own explicit panel.
        limits=domain(unit_frame['plot_value'],unit,temporal,presentation)
        unit_frame=unit_frame.copy()
        multiple_measures=unit_frame['display_measure'].nunique()>1
        unit_frame['series_label']=unit_frame['institution']+' · '+unit_frame['display_measure'] if multiple_measures and unit_frame['institution'].nunique()>1 else unit_frame['display_measure'] if multiple_measures else unit_frame['institution']
        all_series=list(dict.fromkeys(unit_frame['series_label']))
        series_palette=alt.Scale(domain=all_series,range=[PALETTE[i%4] for i in range(len(all_series))])
        groups=[(None,unit_frame)]
        for measure,data in groups:
            # Multiple unrelated measures at a single time are separate when
            # units differ; same-unit category bars share one comparison panel.
            institutions=list(dict.fromkeys(data['series_label' if temporal else 'institution']))
            batch_size=1 if presentation.get('separate_panels') else 4
            batches=[institutions[i:i+batch_size] for i in range(0,len(institutions),batch_size)] if temporal or data['display_measure'].nunique()>1 else [institutions]
            for batch in batches:
                part=data[data['series_label' if temporal else 'institution'].isin(batch)].copy()
                shown_names=list(dict.fromkeys(part['institution']))
                subtitle=' · '.join(shown_names) if len(shown_names)<=4 else str(len(shown_names))+' institutions'
                dates=list(dict.fromkeys(part.sort_values('observation_year')['period_label']))
                time_text=('Entering cohort ' if cohort else '')+(dates[0] if len(dates)==1 else dates[0]+' to '+dates[-1])
                title=presentation.get('title') or (measure if measure else comparison_title(part,total))
                scope=population_scope(result)
                if not presentation.get('title') and re.search(r'\bundergraduate total\b',scope,re.I):
                    title=re.sub(r'^(Population|Enrollment) by','Undergraduates by',title)
                tooltip=[alt.Tooltip('institution:N',title='Institution'),alt.Tooltip('reporting_period:N',title='Source period'),alt.Tooltip('entry_cohort_year:Q',title='Entering cohort',format='d'),alt.Tooltip('measure:N',title='Measure'),alt.Tooltip('display_value:N',title='Value'),alt.Tooltip('status:N',title='Data status'),alt.Tooltip('provisional:N',title='Provisional')]
                scale=alt.Scale(domain=limits,zero=not temporal and presentation.get('y_min') is None,nice=False)
                base=alt.Chart(part).encode(tooltip=tooltip)
                panel_palette=alt.Scale(domain=shown_names,range=[PALETTE[names.index(name)%4] for name in shown_names])
                color=alt.value(presentation['color']) if presentation.get('color') else alt.Color('institution:N',scale=panel_palette,legend=alt.Legend(orient='top',title=None,labelLimit=220,columns=1,direction='vertical') if len(batch)>1 else None)
                if temporal:
                    series_palette=alt.Scale(domain=batch,range=[PALETTE[(names.index(s) if s in names else all_series.index(s))%4] for s in batch])
                    color=alt.value(presentation['color']) if presentation.get('color') else alt.Color('series_label:N',scale=series_palette,legend=alt.Legend(orient='top',title=None,labelLimit=220,columns=1,direction='vertical') if len(batch)>1 else None)
                    part['axis_period']=part['period_label'].str.replace(r'^Fall ','',regex=True)
                    base=alt.Chart(part).encode(tooltip=tooltip)
                    order=list(dict.fromkeys(part.sort_values('observation_year')['axis_period']))
                    ticks=order
                    chart=base.mark_line(point=alt.OverlayMarkDef(size=32),strokeWidth=2.5,invalid='break-paths-show-domains').encode(
                        x=alt.X('axis_period:O',sort=order,title=presentation.get('x_label') or ('Entering cohort year' if cohort else 'Reporting period'),axis=alt.Axis(labelAngle=-45 if len(order)>6 else 0,values=ticks,labelOverlap=False)),
                        y=alt.Y('plot_value:Q',title=presentation.get('y_label') or unit_title(unit),scale=scale,axis=alt.Axis(format=',.0f' if unit not in {'percent','ratio'} else '.1f')),
                        color=color,strokeDash=alt.StrokeDash('series_label:N',legend=alt.Legend(orient='top',title=None,labelLimit=220,columns=1,direction='vertical') if presentation.get('color') and len(batch)>1 else None),detail=['series_label:N','series_segment:N']).properties(height=320)
                    note='Gaps indicate unavailable observations.'
                    if unit=='percent' and limits!=[0,100]:note+=' Percentage trend uses a focused, labeled scale.'
                else:
                    multi=part['display_measure'].nunique()>1
                    many_periods=part['period_label'].nunique()>1
                    if many_periods:part['category']=part['period_label']+' · '+part['display_measure'] if multi else part['period_label']
                    else:part['category']=part['display_measure'] if multi else part['institution']
                    part['wrapped_category']=part['category'].map(lambda s:'\n'.join(textwrap.wrap(s,22,break_long_words=False)))
                    base=alt.Chart(part).encode(tooltip=tooltip)
                    semantic=many_periods or multi and bool(re.search(r'award level|degree level|degree:|certificate', ' '.join(part['measure']),re.I))
                    categories=list(dict.fromkeys(part['wrapped_category']))
                    sorting=presentation.get('sort','auto')
                    if sorting=='alphabetical':order=sorted(categories)
                    elif semantic and sorting=='auto':order=categories
                    else:
                        ascending=sorting=='ascending'
                        order=list(part.sort_values('plot_value',ascending=ascending,na_position='last')['wrapped_category'].drop_duplicates())
                    numeric_axis=alt.Axis(format=',.0f' if unit not in {'percent','ratio','percentage points','FTE'} else '.1f')
                    if unit=='percent':
                        numeric_axis=(alt.Axis(format='.0f',tickCount=5,labelOverlap=False) if presentation.get('y_min') is not None
                                      else alt.Axis(format='.0f',values=[v for v in [0,25,50,75,100] if limits[0]<=v<=limits[1]],labelOverlap=False))
                    category_line_height=presentation.get('font_size',13)+3
                    encoding={'x':alt.X('plot_value:Q',title=presentation.get('x_label') or unit_title(unit),scale=scale,axis=numeric_axis),
                        'y':alt.Y('wrapped_category:N',sort=order,title=presentation.get('y_label'),axis=alt.Axis(labelAngle=0,labelLimit=0,labelLineHeight=category_line_height,labelExpr="split(datum.label, '\\n')"))}
                    grouped=(multi or many_periods) and len(shown_names)>1
                    bar_size=presentation.get('bar_size',18)
                    label_size=presentation.get('label_size',12)
                    offset=alt.YOffset('institution:N',sort=shown_names,scale=alt.Scale(domain=shown_names,paddingInner=.25,paddingOuter=.1))
                    if grouped:encoding['y']=encoding['y'].scale(paddingInner=.18,paddingOuter=.12)
                    bar_color=color if (multi or many_periods) and len(batch)>1 else alt.value(presentation.get('color') or PALETTE[0])
                    if presentation.get('series_colors'):
                        bar_color=alt.Color('institution:N',scale=alt.Scale(domain=shown_names,range=[presentation['series_colors'].get(n,PALETTE[names.index(n)%4]) for n in shown_names]),legend=None)
                    bars=base.mark_bar(size=bar_size).encode(**encoding,color=bar_color)
                    if grouped:bars=bars.encode(yOffset=offset)
                    labels=base.mark_text(align='left',dx=6,fontSize=12,color='#263746').encode(**encoding,text='display_value:N')
                    if grouped:labels=labels.encode(yOffset=offset)
                    positive=labels.transform_filter('isValid(datum.plot_value) && datum.plot_value >= 0')
                    negative=base.mark_text(align='right',dx=-6,fontSize=12,color='#263746').encode(**encoding,text='display_value:N').transform_filter('isValid(datum.plot_value) && datum.plot_value < 0')
                    if grouped:negative=negative.encode(yOffset=offset)
                    zero=alt.Chart(pd.DataFrame({'baseline':[0]})).mark_rule(color='#8D989E',strokeWidth=1).encode(x=alt.datum(0))
                    line_height=max((c.count('\n')+1)*category_line_height+12 for c in categories)
                    slot=max(bar_size,label_size)+10
                    group_height=len(shown_names)*slot+20 if grouped else slot
                    height=max(180,len(categories)*max(36,line_height,group_height))
                    chart=(bars+positive+negative+zero).properties(height=height)
                    note='Values are labeled; missing observations are not zero.'
                if presentation.get('y_min') is not None:note+=' User-selected numeric axis range: '+str(limits[0])+' to '+str(limits[1])+'.'
                chart=chart.properties(width='container',padding={'left':8,'right':64,'top':12,'bottom':8}).configure_axis(labelFontSize=13,titleFontSize=13,labelColor='#263746',titleColor='#263746',gridColor='#E7EBED',domainColor='#AAB4B9').configure_legend(labelFontSize=12).configure_view(stroke=None)
                output.append({'chart':chart,'title':title,'subtitle':subtitle+' · '+time_text+(' · '+scope if scope else ''),'note':note,'rows':len(part),'unit':unit,'total':bool(total),
                    'single_row':part.iloc[0].to_dict() if len(part)==1 else None})
    return output
