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


# ===== merged from chart_format.py (consolidation) =====
"""Shared presentation settings, local prompt edits and complete figure exports."""
from copy import deepcopy
import json,re,textwrap

DEFAULTS=dict(subtitle=None,footnote='',font='Arial',font_size=13,title_size=24,label_size=12,
    legend='top',value_labels='auto',markers=True,line_width=2.5,marker_size=32,
    bar_size=18,gridlines=True,background='#ffffff',series_colors={},
    label_angle='auto',decimals=None,number_format='auto',tick_count=5,
    separate_panels=False,reference_value=None,reference_label='Reference',
    layout='Full slide · 16:9')

def effective(result,presentation):
    import streamlit as st
    return {**DEFAULTS,**presentation,**st.session_state.get('chart_formats',{}).get(result['result_id'],{})}

def commit(result,presentation):
    import streamlit as st
    rid=result['result_id'];s=st.session_state
    old=s.get('chart_formats',{}).get(rid)
    if old!=presentation:
        undo=dict(s.get('chart_undo',{}));undo[rid]=(undo.get(rid,[])+[deepcopy(old)])[-20:];s.chart_undo=undo
        s.chart_formats={**s.get('chart_formats',{}),rid:deepcopy(presentation)}

def color_series(result,presentation=None):
    """Use the actual rendered color domains, including overrides and constants."""
    from .responses import presentation_for
    p={**DEFAULTS,**(presentation or presentation_for(result))};out={}
    def collect(node,spec):
        if not isinstance(node,dict):return
        mark=node.get('mark',{});kind=mark.get('type') if isinstance(mark,dict) else mark
        if kind in {'line','bar'}:
            color=node.get('encoding',{}).get('color',{})
            scale=color.get('scale',{});domain=scale.get('domain',[]);palette=scale.get('range',[])
            if domain and palette:out.update({n:palette[i%len(palette)] for i,n in enumerate(domain)})
            elif 'value' in color:
                field='series_label' if kind=='line' else 'institution'
                for data in spec.get('datasets',{}).values():
                    for row in data:
                        if field in row:out[row[field]]=color['value']
        for layer in node.get('layer',[]):collect(layer,spec)
    for panel in panels(result,p):
        spec=styled(panel,p);collect(spec,spec)
    return out


def series_names(result,presentation=None):
    return list(color_series(result,presentation))

def normalize_edit_question(q):
    """Normalize request politeness, never the quoted text or data selection."""
    q=q.strip().rstrip('.!?').strip()
    return re.sub(r'^(?:(?:can|could|would) you\s+)?(?:please\s+)?','',q,flags=re.I)


def edit_text(value):
    value=value.strip()
    if len(value)>=2 and (value[0],value[-1]) in {('"','"'),("'","'"),('“','”'),('‘','’')}:return value[1:-1].strip()
    return value


def edit_clauses(q):
    """Split commands outside quotes; apostrophes in names are not quotes."""
    parts=[];start=0;quote=None;i=0
    closes={'"':'"',"'":"'",'“':'”','‘':'’'}
    verbs=r'(?:make|set|change|show|hide|label|use|remove|highlight|move|rename|reset|sort|order|switch|rotate)'
    while i<len(q):
        ch=q[i]
        if quote:
            if ch==quote and not (ch in {"'",'’'} and i>0 and i+1<len(q) and q[i-1].isalnum() and q[i+1].isalnum()):quote=None
        elif ch in closes and (i==0 or q[i-1].isspace() or q[i-1] in '(:='):
            quote=closes[ch]
        elif ch in ',;' and not (ch==',' and i>0 and i+1<len(q) and q[i-1].isdigit() and q[i+1].isdigit()):
            parts.append(q[start:i].strip());start=i+1
        elif ch.isspace() and (m:=re.match(r'\s+and\s+(?='+verbs+r'\b)',q[i:],re.I)):
            parts.append(q[start:i].strip());i+=m.end();start=i;continue
        i+=1
    parts.append(q[start:].strip())
    return [re.sub(r'^and\s+','',p,flags=re.I) for p in parts if p]

def extra_edits(question,previous):
    """Return settings or None; a compound edit succeeds atomically."""
    if not previous or 'result' not in previous:return None
    q=normalize_edit_question(question)
    changes={}
    # Commas within quoted titles/numbers are preserved. Split explicit conjunctions.
    clauses=edit_clauses(q)
    colors=r'(blue|red|green|gray|grey|orange|purple|black|navy|#[0-9a-f]{6})'
    for clause in clauses:
        c=clause.strip();low=c.lower();m=None
        if (m:=re.fullmatch(r'(?:(?:make|set|change|highlight) )?(.+?)(?: color)?(?: to| in)? '+colors,c,re.I)):
            target=m[1].strip(' "“”')
            target=re.sub(r'^the color of\s+','',target,flags=re.I)
            target=re.sub(r"(?:['’]s)?\s+(?:line|bar|series)$",'',target,flags=re.I)
            names=series_names(previous['result'],previous.get('presentation'))
            matches=[n for n in names if target.casefold() in n.casefold()]
            if len(matches)!=1:return None
            changes.setdefault('series_colors',{}).update({matches[0]:m[2].lower()})
            changes['color']=None
        elif (m:=re.fullmatch(r'(?:set|change)(?: the)? (font size|title size|label size|line width|marker size|bar width|tick count|decimals|font)(?: to)? (.+)',c,re.I)):
            key={'font':'font','font size':'font_size','title size':'title_size','label size':'label_size','line width':'line_width','marker size':'marker_size','bar width':'bar_size','tick count':'tick_count','decimals':'decimals'}[m[1].lower()]
            v=m[2].strip(' "“”');bounds={'font_size':(10,32),'title_size':(14,48),'label_size':(10,28),'line_width':(1,8),'marker_size':(10,200),'bar_size':(8,40),'tick_count':(2,12),'decimals':(0,4)}
            if key=='font':
                if v.lower() not in {'arial','calibri','georgia','times new roman','verdana'}:return None
                changes[key]=v.title()
            else:
                try:value=float(re.sub(r'\s*(?:px|pt|pixels|points)$','',v))
                except ValueError:return None
                if not bounds[key][0]<=value<=bounds[key][1] or key not in {'line_width'} and value!=int(value):return None
                changes[key]=value if key=='line_width' else int(value)
        elif (m:=re.fullmatch(r'(?:set|change)(?: the)? subtitle to (.+)',c,re.I)):changes['subtitle']=edit_text(m[1])
        elif low in {'hide subtitle','remove subtitle'}:changes['subtitle']=''
        elif (m:=re.fullmatch(r'(?:add|set|change)(?: the| a)? footnote(?: to)? (.+)',c,re.I)):changes['footnote']=edit_text(m[1])
        elif low in {'hide footnote','remove footnote'}:changes['footnote']=''
        elif re.fullmatch(r'(?:show|hide) (?:the )?(?:point )?markers',low):changes['markers']=low.startswith('show')
        elif re.fullmatch(r'(?:show|hide|remove) (?:the )?gridlines',low):changes['gridlines']=low.startswith('show')
        elif re.fullmatch(r'(?:hide|remove) (?:the )?legend',low):changes['legend']='none'
        elif low in {'use direct labels','show direct labels'}:changes['legend']='direct'
        elif (m:=re.fullmatch(r'(?:move|set|change|show)(?: the)? legend(?: position)?(?: to| at)?(?: the)? (top|bottom|left|right)',low)):changes['legend']=m[1]
        elif (m:=re.fullmatch(r'(?:label|show labels for)(?: only)? (?:the )?(latest(?: year| values?)?|endpoints|all(?: values| points)?|no points)',low)):
            changes['value_labels']='latest' if m[1].startswith('latest') else 'endpoints' if m[1]=='endpoints' else 'none' if m[1]=='no points' else 'all'
        elif low in {'hide value labels','remove value labels'}:changes['value_labels']='none'
        elif low in {'use separate panels','show separate panels','separate the panels'}:changes['separate_panels']=True
        elif low in {'combine panels','use combined panels'}:changes['separate_panels']=False
        elif low in {'use presentation preset','use presentation style'}:changes.update(font_size=18,title_size=28,label_size=16,value_labels='latest',legend='direct')
        elif low in {'use full slide layout','use full-slide layout'}:changes['layout']='Full slide · 16:9'
        elif low in {'use half slide layout','use half-slide layout'}:changes['layout']='Half slide · 4:3'
        elif (m:=re.fullmatch(r'(?:use|set)(?: the)? (?:number format to )?(compact|standard) number(?:s| formatting)?',low)):changes['number_format']='compact' if m[1]=='compact' else 'auto'
        elif (m:=re.fullmatch(r'(?:add|set)(?: a| the)? reference line(?: at| to)? ([+-]?[\d,.]+)(?: labeled ["“]?(.+?)["”]?)?',c,re.I)):
            changes.update(reference_value=float(m[1].replace(',','')),reference_label=m[2] or 'Reference')
        elif low in {'remove reference line','hide reference line'}:changes['reference_value']=None
        elif (m:=re.fullmatch(r'(?:make|set|change)(?: the)? background(?: to)? (white|transparent|#[0-9a-f]{6})',low)):changes['background']=m[1]
        else:return None
    if not changes:return None
    if 'series_colors' in changes:changes['series_colors']={**previous.get('presentation',{}).get('series_colors',{}),**changes['series_colors']}
    return changes

def number_pattern(unit,p):
    if p.get('number_format')=='compact':return '.3~s'
    decimals=p.get('decimals')
    return (',' if unit!='ratio' else '')+'.'+str(decimals if decimals is not None else 1 if unit in {'percent','FTE','percentage points'} else 4 if unit=='ratio' else 0)+'f'

def styled(panel,p):
    """Style a copied Vega-Lite specification; source rows remain untouched."""
    from .units import is_currency
    spec=deepcopy(panel['chart'].to_dict());temporal=p['chart_type']=='line'
    legend=p.get('legend','top');labels=p.get('value_labels','auto');unit=panel['unit']
    def walk(node):
        if not isinstance(node,dict):return
        enc=node.get('encoding',{})
        for channel in ['x','y']:
            axis=enc.get(channel,{}).get('axis')
            if axis is not None:
                if 'labelLineHeight' in axis:axis['labelLineHeight']=p.get('font_size',13)+3
                if enc[channel].get('type')=='quantitative':
                    axis['format']=number_pattern(unit,p);axis['tickCount']=p.get('tick_count',5)
                    axis['grid']=p.get('gridlines',True)
        for channel in ['color','strokeDash']:
            e=enc.get(channel)
            if e and 'field' in e:
                e['legend']=None if legend in {'none','direct'} else dict(orient=legend,title=None,labelLimit=320)
                if channel=='strokeDash' and 'value' not in enc.get('color',{}):e['legend']=None
                if channel=='color' and 'scale' in e:
                    existing=e['scale'].get('range',PALETTE)
                    e['scale']['range']=[p.get('series_colors',{}).get(n,p.get('color') or existing[i%len(existing)]) for i,n in enumerate(e['scale']['domain'])]
        mark=node.get('mark')
        if isinstance(mark,dict):
            if mark['type']=='line':mark.update(strokeWidth=p.get('line_width',2.5),point={'size':p.get('marker_size',32)} if p.get('markers',True) else False)
            elif mark['type']=='bar':mark['size']=p.get('bar_size',18)
            elif mark['type']=='text':mark['fontSize']=p.get('label_size',12)
        if isinstance(mark,dict) and mark['type']=='text' and enc.get('text',{}).get('field')=='display_value' and (p.get('decimals') is not None or p.get('number_format')=='compact'):
            expression=("'$' + " if is_currency(unit) else '')+f"format(datum.plot_value, '{number_pattern(unit,p)}')"+(" + '%'" if unit=='percent' else '')
            node.setdefault('transform',[]).append({'calculate':expression,'as':'formatted_label'})
            enc['text']={'field':'formatted_label','type':'nominal'}
        for layer in node.get('layer',[]):walk(layer)
    walk(spec)
    # Make raw values visible outside interactive tooltips.
    if temporal and (labels not in {'auto','none'} or legend=='direct'):
        source=spec if 'layer' not in spec else spec['layer'][0]
        enc=deepcopy(source['encoding']);enc.pop('strokeDash',None);enc.pop('detail',None)
        transforms=[{'filter':'isValid(datum.plot_value)'},{'joinaggregate':[{'op':'max','field':'observation_year','as':'last_year'},{'op':'min','field':'observation_year','as':'first_year'}],'groupby':['series_label']}]
        pattern=number_pattern(unit,p)
        suffix='%' if unit=='percent' else ''
        label_expr=("'$' + " if is_currency(unit) else '')+f"format(datum.plot_value, '{pattern}') + '{suffix}'"
        if legend=='direct':label_expr='datum.series_label' if labels=='none' else f"datum.series_label + ' · ' + {label_expr}"
        if labels!='all' or legend=='direct':transforms.append({'filter':'datum.observation_year == datum.last_year'+(' || datum.observation_year == datum.first_year' if labels=='endpoints' and legend!='direct' else '')})
        transforms.append({'calculate':label_expr,'as':'format_label'})
        enc['text']={'field':'format_label','type':'nominal'}
        layer=dict(mark=dict(type='text',align='left' if legend=='direct' else 'center',dx=10 if legend=='direct' else 0,dy=0 if legend=='direct' else -14,fontSize=p.get('label_size',12)),encoding=enc,transform=transforms)
        spec['layer']=[{k:spec.pop(k) for k in ['mark','encoding'] if k in spec},layer]
        if legend=='direct':spec['padding']['right']=240
    elif not temporal and labels=='none':
        spec['layer']=[layer for layer in spec.get('layer',[]) if layer.get('mark',{}).get('type')!='text']
    if p.get('reference_value') is not None:
        axis='y' if temporal else 'x';value=p['reference_value']
        if 'layer' not in spec:spec['layer']=[{k:spec.pop(k) for k in ['mark','encoding'] if k in spec}]
        spec['layer'].append({'data':{'values':[{'reference':value,'caption':p.get('reference_label','Reference')}]},'mark':{'type':'rule','strokeDash':[5,4],'color':'#52616D'},'encoding':{axis:{'field':'reference','type':'quantitative'}}})
        spec['layer'].append({'data':{'values':[{'reference':value,'caption':p.get('reference_label','Reference')}]},'mark':{'type':'text','align':'left','dx':8,'dy':-9,'color':'#52616D'},'encoding':{axis:{'field':'reference','type':'quantitative'},'text':{'field':'caption'}}})
    config=spec.setdefault('config',{});config['font']=p.get('font','Arial')
    config.setdefault('axis',{}).update(labelFontSize=p.get('font_size',13),titleFontSize=p.get('font_size',13))
    config.setdefault('legend',{})['labelFontSize']=p.get('font_size',13)
    config.setdefault('text',{})['font']=p.get('font','Arial')
    spec['background']=p.get('background','#ffffff')
    return spec

def figure_spec(panel,p,result,width=1200,height=675):
    """A complete fixed-size figure; title/source/caveats travel with the plot."""
    from .responses import evidence_summary,visible_warnings
    spec=styled(panel,p);spec.pop('autosize',None)
    spec['width']=max(200,width-330 if p.get('legend')=='direct' else width-140)
    spec['height']=max(180,height-260,spec.get('height',0) if p['chart_type']=='bar' else 0)
    subtitle=p.get('subtitle') if p.get('subtitle') is not None else panel['subtitle']
    sources=evidence_summary(result)['sources']
    source_lines=['Source: IPEDS · '+ ' · '.join(str(row.get(k,'')) for k in ['IPEDS release','Survey','Year coverage','Table']) for row in sources]
    # Summarize annual sources without misrepresenting reporting periods.
    families={(r.get('Survey'),re.sub(r'20\d{2}|19\d{2}','{year}',str(r.get('Table','')))) for r in sources}
    if len(source_lines)>3 and len(families)==1:
        surveys=list(dict.fromkeys(str(r.get('Survey','')) for r in sources));tables=[str(r.get('Table','')) for r in sources]
        source_lines=['Source: IPEDS · '+'; '.join(surveys)+' · '+tables[0]+' through '+tables[-1], 'Source releases: '+str(sources[0].get('IPEDS release',''))+' through '+str(sources[-1].get('IPEDS release',''))]
    notes=source_lines+([p['footnote'].strip()] if p.get('footnote','').strip() else [])+[panel['note']]+visible_warnings(result)+evidence_summary(result).get('source_notes',[])
    footer=[line for note in notes for line in textwrap.wrap(note,max(65,int(width/8)))]
    title={'text':textwrap.wrap(panel['title'],max(35,int(width/18))),'subtitle':textwrap.wrap(subtitle,max(50,int(width/11))) if subtitle else [],'anchor':'start','fontSize':p.get('title_size',24),'subtitleFontSize':p.get('font_size',13),'offset':24,'color':'#203747'}
    # vconcat keeps provenance inside the exported image, with no page controls.
    config=spec.pop('config',{});background=spec.pop('background','white');spec.pop('$schema',None)
    datasets=spec.pop('datasets',{})
    foot={'data':{'values':[{'note':n,'row':i} for i,n in enumerate(footer)]},'mark':{'type':'text','align':'left','baseline':'top','fontSize':11,'color':'#52616D'},'encoding':{'x':{'value':0},'y':{'field':'row','type':'ordinal','axis':None},'text':{'field':'note'}},'width':width-80,'height':max(25,len(footer)*16)}
    return {'$schema':'https://vega.github.io/schema/vega-lite/v6.json','title':title,'vconcat':[spec,foot],'datasets':datasets,'spacing':24,'padding':30,'config':config,'background':background,'usermeta':{'canvas_width':width,'canvas_height':height}}

def export_figure(spec,kind='png',scale=2):
    import vl_convert as vlc
    import xml.etree.ElementTree as ET
    svg=vlc.vegalite_to_svg(spec);root=ET.fromstring(svg)
    width=spec['usermeta']['canvas_width'];height=spec['usermeta']['canvas_height']
    natural_w=float(root.attrib['width']);natural_h=float(root.attrib['height']);factor=min(width/natural_w,height/natural_h)
    root.set('x',str((width-natural_w*factor)/2));root.set('y',str((height-natural_h*factor)/2))
    root.set('width',str(natural_w*factor));root.set('height',str(natural_h*factor))
    background=spec.get('background','white')
    outer=f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="{background}"/>'+ET.tostring(root,encoding='unicode')+'</svg>'
    if kind=='svg':return outer.encode('utf-8')
    return vlc.svg_to_png(outer,scale=scale)
