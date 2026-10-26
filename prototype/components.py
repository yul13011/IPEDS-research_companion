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
from .units import display_result,is_currency,UNVERIFIED

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
        from .observation_ui import render
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
    from .chart_format import effective,styled
    presentation=effective(result,presentation)
    chart_type=presentation['chart_type']
    if show_chart is False:chart_type='none'
    elif show_chart and chart_type=='none':chart_type='line' if len(result['observation_years'])>1 else 'bar'
    if any(r['unit'] in {'unknown','source units','identifier','coded'} for r in result['rows']):
        chart_type='none'
        st.caption('A measurement unit is unresolved or the field is an identifier/category. A chart cannot use these values as a verified measurement axis; saved calculations may need to be rerun.')
    if chart_type=='none' and presentation.get('table_reason'):st.caption(presentation['table_reason'])
    from .result_text import visible_warnings
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
        from .chart_controls import editor,preview
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
            from .result_text import evidence_summary,definition_summary,calculation_summary,metric_label
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
