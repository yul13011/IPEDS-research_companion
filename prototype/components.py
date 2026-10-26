"""Reusable result and definition presentation; no query planning here."""
import json
from functools import partial
import streamlit as st
import pandas as pd
import altair as alt
from .catalog import definition_detail
from .analytics import measures
from .exports import dataframe, csv_bytes, excel_bytes, audit_bytes
from .responses import presentation_for,value_text
from .semantics import display_result,is_currency,UNVERIFIED

specs=measures()


def render_catalog_proposal(proposal,key):
    """Source availability/proposal only; never render invented statistical values."""
    plan=proposal['catalog_plan']
    count=len(plan['outputs']) if plan.get('version')==2 else sum(s['role']=='measure' for s in plan['selections'])
    st.caption(f"Source-backed proposed analysis · {count} selected field(s) · no numerical query executed")
    with st.popover('Definitions & sources'):
        st.write('Institutions: '+', '.join(plan['institutions']))
        st.write('Requested time: '+(plan['time_basis'] if plan.get('version')==2 else plan['requested_time']['description']))
        for note in plan['assumptions']:st.caption(note)
        seen=set()
        for definition in proposal['definition_evidence']:
            evidence=definition['evidence'];rid=evidence['record_id']
            if rid in seen:continue
            seen.add(rid)
            st.markdown('**'+definition['title']+'**')
            st.caption(f"{definition['release_id']} · {definition['table_name']} · {definition['variable_name']}")
            st.write(definition['long_description'])
            st.caption(f"{evidence['sheet_name']} · row {evidence['source_row']} · record {rid}")
        for code in proposal['category_evidence']:
            st.write(code['title']);st.caption(code['body'])
        for warning in proposal['validation']['blocks']:st.warning(warning)


def render_evidence(records,key,select_one=False):
    if not records:st.info('No matching source records. Try a shorter topic or an exact variable name.');return
    st.caption('Ranked source excerpts, not an exhaustive inventory. A documented field may have a physical-location issue. Check the details before using it.')
    frame=pd.DataFrame(records)
    display=frame[['release_id','kind','table_name','variable_name','title','physical_column_present']].rename(columns={
        'release_id':'Source release','kind':'Record type','table_name':'Table','variable_name':'Variable',
        'title':'Description','physical_column_present':'Column at documented location'})
    st.dataframe(display,hide_index=True,width='stretch')
    if select_one:
        st.caption(f'Showing {len(records)} ranked records. Choose one to read its full definition and any coded categories.')
        options={r['record_id']:r for r in records}
        chosen=st.selectbox('Read a definition',list(options),
            format_func=lambda n:f"{options[n]['variable_name'] or options[n]['table_name'] or options[n]['kind']} — {options[n]['title']} ({options[n]['release_id']})",
            key=key+'_selected_record')
        summary=options[chosen];detail=definition_detail(chosen)
        st.markdown(f"**{detail['title']}**")
        st.write(detail['definition'])
        if summary['physical_column_present'] is True:st.caption('This column exists at the documented table location in the annual dataset.')
        elif summary['physical_column_present'] is False:st.warning('This column was not found at its documented location. Check the documentation issues before using it.')
        for issue in summary['issues']:st.warning(issue['description'])
        if detail['codes']:
            st.write('**Coded categories**')
            st.dataframe(pd.DataFrame(detail['codes']).rename(columns={'code_value':'Code','value_label':'Meaning'}),hide_index=True,width='stretch')
        with st.expander('Original source reference'):
            st.write(f"Table: {detail['table_name'] or '—'} · Variable: {detail['variable_name'] or '—'}")
            st.write(f"{detail['sheet_name'] or 'Release notes'} · row {detail['source_row']} · catalog record {detail['record_id']}")
            st.caption(detail['source_file'])
        return
    for i,r in enumerate(records):
        with st.expander(f"{r['release_id']} · {r['table_name'] or r['kind']} · {r['variable_name'] or r['title']}"):
            st.write(r['definition']);st.caption(f"Record {r['record_id']} · {r['source_file']} · {r['sheet_name']} · row {r['source_row']}")
            for issue in r['issues']:st.warning(issue['description'])


def render_result(result,key,show_chart=None,presentation=None,compact=False):
    if result.get('result_schema_version')==2:
        from .observations import render
        return render(result,key)
    from .intent_checks import check_result,IntentMismatch
    try:check_result(result)
    except IntentMismatch as exc:
        st.warning(str(exc));return
    result=display_result(result)
    specs={**measures(),**result.get('metric_specs',{})}
    frame=dataframe(result)
    good=frame[frame.status=='ok']
    coverage=result['coverage']
    presentation={**presentation_for(result),**(presentation or {})}
    from .charts import effective,styled
    presentation=effective(result,presentation)
    chart_type=presentation['chart_type']
    if show_chart is False:chart_type='none'
    elif show_chart and chart_type=='none':chart_type='line' if len(result['observation_years'])>1 else 'bar'
    if any(r['unit'] in {'unknown','source units','identifier','coded'} for r in result['rows']):
        chart_type='none'
        st.caption('A measurement unit is unresolved or the field is an identifier/category. A chart cannot use these values as a verified measurement axis; saved calculations may need to be rerun.')
    if chart_type=='none' and presentation.get('table_reason'):st.caption(presentation['table_reason'])
    from .responses import visible_warnings
    for warning in visible_warnings(result):st.warning(warning)
    display=frame[['institution','reporting_period','measure']].rename(columns={'institution':'Institution','reporting_period':'Period','measure':'Measure'}).copy()
    display['Value']=[value_text(r)+(' '+r['unit'] if r['status']=='ok' and r['unit'] not in {'percent','score','monetary amount','unknown','source units','identifier','coded',UNVERIFIED} and not is_currency(r['unit']) else '') for r in result['rows']]
    if chart_type=='none' and len(good)==1 and len(frame)==1:
        st.metric(label=str(good.iloc[0]['measure']),value=value_text(result['rows'][0]))
    table_visible=presentation['show_table'] or chart_type=='none' or good.empty
    if compact:
        table_visible=st.toggle('Display table',value=table_visible,key=key+'_table')
    if table_visible:
        st.dataframe(display,hide_index=True,width='stretch',column_config={
            'Institution':st.column_config.TextColumn(width='medium'),
            'Period':st.column_config.TextColumn(width='small'),
            'Measure':st.column_config.TextColumn(width='medium'),
            'Value':st.column_config.TextColumn(width='small')})
        if compact:
            if st.checkbox('Show underlying counts and data status',key=key+'_counts'):
                st.dataframe(frame[['institution','observation_year','entry_cohort_year','measure','value','numerator','denominator','status','provisional']],hide_index=True,width='stretch')
    if chart_type!='none' and not good.empty:
        from .charts import panels
        opened=st.session_state.get(key+'_format_open',False)
        plot_area,edit_area=st.columns([2.2,1]) if opened else (st.container(),None)
        if edit_area:
            with edit_area,st.container(height=480,border=True,key=key+'_format_panel'):editor(result,presentation,key)
        with plot_area:
          for panel in panels(result,{**presentation,'chart_type':chart_type}):
            if panel['total'] and panel['rows']==1 and panel.get('single_row') is not None:
                from .charts import formatted
                row=panel['single_row']
                st.metric(panel['title'],formatted(row['value'],row['unit']))
                st.caption(panel['subtitle'])
                continue
            if presentation.get('title_size',24)!=24:
                from html import escape
                st.markdown('<div style="font-size:'+str(presentation['title_size'])+'px;font-family:'+escape(presentation['font'])+';font-weight:600">'+escape(panel['title'])+'</div>',unsafe_allow_html=True)
            else:st.markdown('**'+panel['title']+'**')
            subtitle=presentation['subtitle'] if presentation.get('subtitle') is not None else panel['subtitle']
            if subtitle:st.caption(subtitle)
            st.vega_lite_chart(styled(panel,{**presentation,'chart_type':chart_type}),width='stretch',theme=None)
            if presentation.get('footnote','').strip():st.caption(presentation['footnote'].strip())
            st.caption(panel['note'])
        with st.container(horizontal=True):
            if st.button('Close formatting' if opened else 'Format chart',key=key+'_format_button'):
                st.session_state[key+'_format_open']=not opened;st.rerun()
            if st.button('Preview & download chart',key=key+'_preview_button'):preview(result,{**presentation,'chart_type':chart_type},key)
        hint='Use Format chart or ask for changes to colors, fonts, labels, legend, markers or axes. Missing values remain missing.'
        if any(specs[m]['family']=='sat' for m in result['plan']['metrics']):hint+=' SAT trend lines break at the 2017 reporting-protocol change.'
        st.caption(hint)
    with st.container(horizontal=True):
        with st.popover('Definitions & sources'):
            for info in result.get('display_units',[]):
                st.caption('Currency unit: '+info['unit']+'. Values retain their source scale; no conversion or inflation adjustment was applied.')
            from .responses import evidence_summary,definition_summary,calculation_summary,metric_label
            details=evidence_summary(result)
            if details['institutions']:st.write(('Scope: ' if result.get('population_evidence') else 'Institution: ')+', '.join(details['institutions']))
            if details['population']:st.write('Population / selection: '+'; '.join(details['population']))
            if details['periods']:st.write('Reporting period: '+'; '.join(details['periods']))
            if result.get('population_evidence'):
                st.markdown('**Aggregate scope and coverage**')
                st.dataframe(pd.DataFrame([{'Source release':p['year'],'Population':p['label'],'Directory reporting units':p['directory_count'],
                    'Administrative offices':'Included' if p['filters']['administrative_offices'] else 'Excluded'} for p in result['population_evidence'].values()]),hide_index=True)
                st.caption('Directory entries and source reporters differ. The audit lists source reporting units, missing inputs and exclusions. National rates pool matching counts; they are not averages of institutional rates.')
            for metric in result['plan']['metrics']:
                st.markdown('**'+metric_label(result,metric,specs[metric]['label'])+'**')
                for definition in definition_summary(result,metric):st.write(definition)
                calculation=calculation_summary(result,metric)
                if calculation:st.write('Calculation: '+calculation)
            if details['sources']:
                st.markdown('**Sources**')
                for index,group in enumerate(details['source_groups']):
                    st.caption(group['title'])
                    st.dataframe(pd.DataFrame(group['rows']),hide_index=True,width='stretch',height='content',key=key+'source_tables_'+str(index))
                for note in details['source_notes']:st.warning(note)
            st.caption('Downloads include full original definitions, variable codes, formulas, query details and validation notes.')
        with st.popover('Download Data'):
            st.download_button('Excel + sources',partial(excel_bytes,result),file_name=f"ipeds-{result['result_id']}.xlsx",mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key=key+'xlsx',on_click='ignore')
            st.download_button('CSV',partial(csv_bytes,result),file_name=f"ipeds-{result['result_id']}.csv",mime='text/csv',key=key+'csv',on_click='ignore')
            st.download_button('Technical audit file (JSON)',partial(audit_bytes,result),file_name=f"ipeds-{result['result_id']}-sources.json",mime='application/json',key=key+'json',on_click='ignore')


# ===== merged from chart_controls.py (consolidation) =====
"""Discoverable chart editor and export preview, sharing settings with chat."""
from copy import deepcopy
import streamlit as st
from .charts import DEFAULTS,effective,commit,color_series,figure_spec,export_figure

@st.cache_data(show_spinner=False,max_entries=32)
def image_bytes(spec,kind,scale):return export_figure(spec,kind,scale)

def undo(result):
    rid=result['result_id'];stack=st.session_state.get('chart_undo',{}).get(rid,[])
    if stack:
        old=stack.pop();formats=dict(st.session_state.get('chart_formats',{}))
        if old is None:formats.pop(rid,None)
        else:formats[rid]=old
        st.session_state.chart_formats=formats

def editor(result,p,key):
    heading,close=st.columns([5,1],vertical_alignment='center')
    heading.markdown('**Format chart**')
    if close.button('×',key=key+'_format_close',help='Close chart formatting',type='tertiary'):
        st.session_state[key+'_format_open']=False
        st.rerun()
    tabs=st.tabs(['Layout','Text','Style','Axes'])
    def control(kind,label,field,**args):
        widget_key=key+'_format_'+field
        val=p.get(field,DEFAULTS.get(field))
        if kind=='selectbox':
            options=args['options'];val=val if val in options else options[0]
        st.session_state[widget_key]=val
        def update():
            change=deepcopy(p);change[field]=st.session_state[widget_key];commit(result,change)
        return getattr(st,kind)(label,key=widget_key,on_change=update,**args)
    with tabs[0]:
        control('selectbox','Chart type','chart_type',options=['line','bar'])
        control('selectbox','Bar order','sort',options=['auto','ascending','descending','alphabetical'])
        control('selectbox','Export layout','layout',options=['Full slide · 16:9','Half slide · 4:3'])
        control('checkbox','Separate series into panels','separate_panels')
        if st.button('Use presentation preset',key=key+'_preset'):
            commit(result,{**p,'font_size':18,'title_size':28,'label_size':16,'legend':'direct','value_labels':'latest'});st.rerun()
        if st.button('Presentation preview',key=key+'_layout_preview'):preview(result,p,key)
        st.caption('Export includes the title, source and material notes. Each panel can be downloaded separately.')
    with tabs[1]:
        # None means use the automatic title/subtitle. Empty subtitle hides it.
        for field in ['title','subtitle','x_label','y_label']:
            widget_key=key+'_format_'+field;st.session_state[widget_key]=p.get(field) or ''
            def update_text(f=field,k=widget_key):
                change=deepcopy(p);change[f]=st.session_state[k] if f=='subtitle' else st.session_state[k] or None;commit(result,change)
            st.text_input({'title':'Chart title','subtitle':'Subtitle','x_label':'X-axis title','y_label':'Y-axis title'}[field],key=widget_key,on_change=update_text,placeholder='Automatic' if field!='subtitle' else 'Automatic until edited')
        footnote_key=key+'_format_footnote'
        st.session_state[footnote_key]=p.get('footnote','')
        def update_footnote():commit(result,{**p,'footnote':st.session_state[footnote_key]})
        st.text_area('Footnote',key=footnote_key,on_change=update_footnote,help='Add your own note below the chart. Sources and required data notes remain visible.')
        control('selectbox','Font','font',options=['Arial','Calibri','Georgia','Times New Roman','Verdana'])
        control('number_input','Axis and legend font size','font_size',min_value=10,max_value=32,step=1)
        control('number_input','Title font size','title_size',min_value=14,max_value=48,step=1)
        control('number_input','Value-label font size','label_size',min_value=10,max_value=28,step=1)
    with tabs[2]:
        from .charts import PALETTE
        rendered_colors=color_series(result,p)
        for i,(name,rendered_color) in enumerate(rendered_colors.items()):
            widget_key=key+'_series_'+str(i);st.session_state[widget_key]=rendered_color
            def recolor(n=name,k=widget_key):
                change=deepcopy(p);change['color']=None;change['series_colors']={**rendered_colors,n:st.session_state[k]};commit(result,change)
            # Chat accepts named colors; picker requires hexadecimal.
            value=st.session_state[widget_key]
            if not value.startswith('#'):
                named={'blue':'#0000ff','red':'#ff0000','green':'#008000','gray':'#808080','grey':'#808080','orange':'#ffa500','purple':'#800080','black':'#000000','navy':'#000080'}
                st.session_state[widget_key]=named.get(value,PALETTE[i%4])
            st.color_picker(name,key=widget_key,on_change=recolor)
        control('selectbox','Value labels','value_labels',options=['auto','none','latest','endpoints','all'])
        control('selectbox','Legend','legend',options=['top','bottom','left','right','none','direct'])
        control('checkbox','Show point markers','markers')
        control('checkbox','Show numeric gridlines','gridlines')
        control('slider','Line width','line_width',min_value=1.0,max_value=8.0,step=.5)
        control('slider','Marker size','marker_size',min_value=10,max_value=200,step=2)
        control('slider','Bar width','bar_size',min_value=8,max_value=40,step=1)
        control('selectbox','Background','background',options=list(dict.fromkeys(['#ffffff','transparent',p.get('background','#ffffff')])))
        bg_key=key+'_background_color';st.session_state[bg_key]=p.get('background') if str(p.get('background')).startswith('#') else '#ffffff'
        def recolor_background():commit(result,{**p,'background':st.session_state[bg_key]})
        st.color_picker('Background color',key=bg_key,on_change=recolor_background)
    with tabs[3]:
        if p['chart_type']=='line':
            st.caption('Every reporting period stays visible. Numeric limits apply to the Y-axis.')
        else:
            st.caption('Numeric limits apply to the horizontal value (X) axis.')
        control('selectbox','Number format','number_format',options=['auto','compact'])
        control('selectbox','Decimal places','decimals',options=[None,0,1,2,3,4],format_func=lambda x:'Automatic' if x is None else str(x))
        control('number_input','Suggested numeric tick count','tick_count',min_value=2,max_value=12,step=1)
        # Validate both bounds atomically; partial/invalid inputs never reach chart scales.
        with st.form(key+'_bounds'):
            lo=st.number_input('Numeric minimum',value=float(p['y_min']) if p.get('y_min') is not None else 0.0)
            hi=st.number_input('Numeric maximum',value=float(p['y_max']) if p.get('y_max') is not None else 100.0)
            if st.form_submit_button('Apply numeric limits'):
                percentage=all(r['unit']=='percent' for r in result['rows'])
                if lo>=hi or percentage and not 0<=lo<hi<=100:st.error('Choose increasing bounds, within 0–100 for percentages.')
                else:commit(result,{**p,'y_min':lo,'y_max':hi});st.rerun()
        if st.button('Reset numeric limits',key=key+'_reset_limits'):commit(result,{**p,'y_min':None,'y_max':None});st.rerun()
        with st.form(key+'_reference'):
            ref=st.number_input('Reference line value',value=float(p.get('reference_value') or 0))
            caption=st.text_input('Reference line label',value=p.get('reference_label','Reference'))
            if st.form_submit_button('Add / update reference line'):commit(result,{**p,'reference_value':ref,'reference_label':caption});st.rerun()
        if st.button('Remove reference line',key=key+'_remove_reference'):commit(result,{**p,'reference_value':None});st.rerun()
    a,b=st.columns(2)
    if a.button('Undo',key=key+'_undo',disabled=not st.session_state.get('chart_undo',{}).get(result['result_id'])):undo(result);st.rerun()
    if b.button('Reset formatting',key=key+'_reset'):
        from .responses import presentation_for
        commit(result,{**DEFAULTS,**presentation_for(result)});st.rerun()
    st.caption('Changes apply immediately. Your data and calculations stay the same.')

@st.dialog('Presentation preview',width='large')
def preview(result,p,key):
    from .intent_checks import check_result,IntentMismatch
    try:check_result(result)
    except IntentMismatch as exc:
        st.warning(str(exc));return
    from .charts import panels
    st.caption('Preview and download the complete figure, including its source and important notes.')
    st.html('<style>[role="dialog"] [data-testid="stImage"] img {max-height: max(220px, calc(100dvh - 330px)); width: auto !important; max-width:100%; object-fit:contain; margin:0 auto;}</style>')
    layout_col,type_col,resolution_col,download_col=st.columns([2,1,1.6,1.4],vertical_alignment='bottom')
    with layout_col:layout=st.selectbox('Slide layout',['Full slide · 16:9','Half slide · 4:3'],index=0 if p.get('layout','').startswith('Full') else 1,key=key+'_preview_layout')
    with type_col:kind=st.selectbox('File type',['PNG','SVG'],key=key+'_preview_kind')
    with resolution_col:resolution=st.selectbox('Resolution',['Standard','High resolution'],index=1,key=key+'_preview_resolution')
    p={**p,'layout':layout};available=panels(result,p)
    index=st.selectbox('Chart panel',range(len(available)),format_func=lambda i:f"{i+1}. {available[i]['title']} — {available[i]['subtitle']}",key=key+'_preview_panel') if len(available)>1 else 0
    width,height=(1200,675) if layout.startswith('Full') else (800,600)
    scale=2 if resolution=='High resolution' else 1
    try:
        spec=figure_spec(available[index],p,result,width,height)
        png=image_bytes(spec,'png',scale)
        payload=png if kind=='PNG' else image_bytes(spec,'svg',scale)
        with download_col:st.download_button('Download chart',payload,file_name=f"ipeds-{result['result_id']}-panel-{index+1}.{kind.lower()}",mime='image/png' if kind=='PNG' else 'image/svg+xml',key=key+'_download_image',on_click='ignore')
        st.image(png,width='stretch')
        st.caption(f'{width*scale} × {height*scale} pixels' if kind=='PNG' else 'Vector SVG · scales without losing sharpness')
    except Exception as exc:
        st.error('The chart image could not be rendered. Your data and chart settings have been retained.')
        st.caption(str(exc))


# ===== merged from transcript_scroll.py (consolidation) =====
"""Browser scroll policy; only application-owned JavaScript and numeric state."""
from pathlib import Path
import json
import streamlit as st

SCRIPT=(Path(__file__).parent/'transcript_scroll.js').read_text(encoding='utf-8')


def render(request,editing=False):
    config=json.dumps({'request':int(request),'editing':bool(editing)})
    with st.container(key='transcript_scroll_driver'):
        st.html('<script>'+SCRIPT+'\nwindow.ipedsTranscriptScroll.update('+config+');</script>',unsafe_allow_javascript=True)
