"""Table/evidence/export presentation for typed source observations."""
import pandas as pd
from functools import partial
import streamlit as st
from .responses import value_text
from .exports import csv_bytes, excel_bytes, audit_bytes
from .observations import verify_result


def render(result, key):
    verify_result(result)
    names={}
    for row in result['rows']:names.setdefault(row['institution'],set()).add(row['unitid'])
    data = [{'Institution': r['institution']+(f" (UNITID {r['unitid']})" if len(names[r['institution']])>1 else ''), 'Period': r['reporting_period'],
             'Measure': r['measure'], 'Response': value_text(r)} for r in result['rows']]
    frame = pd.DataFrame(data, columns=['Institution','Period','Measure','Response'])
    if not data:
        st.info('No reporting institutions matched the selected source responses.')
    elif result['result_kind'] != 'institution_list' and frame.Institution.nunique() > 1:
        st.dataframe(frame.pivot(index=['Measure','Period'], columns='Institution', values='Response').reset_index(), hide_index=True, width='stretch')
    else:
        st.dataframe(frame, hide_index=True, width='stretch')
    for warning in result['warnings']: st.caption(warning)
    with st.popover('Definitions & sources'):
        st.caption('Source responses are not numerical quantities. Original codes, response status and source references are retained in downloads.')
        for source in result['sources']:
            for d in source['codebook_evidence']:
                st.markdown('**'+d['title']+'**')
                st.caption(f"{d['release_id']} · {d['table_name']} · {d['variable_name']} · {d['sheet_name']} row {d['source_row']}")
                st.write(d['long_description'])
            if source['code_filters']:
                st.dataframe(pd.DataFrame(source['code_filters']), hide_index=True)
        for p in result.get('population_evidence', {}).values():
            st.caption('Selected scope: '+p['label'])
        st.json(result['coverage'])
    with st.popover('Download Data'):
        for name, producer, extension, mime in [('Excel + sources',excel_bytes,'xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),('CSV',csv_bytes,'csv','text/csv'),('Technical audit file (JSON)',audit_bytes,'json','application/json')]:
            st.download_button(name,partial(producer,result),file_name='ipeds-'+result['result_id']+'.'+extension,mime=mime,key=key+extension,on_click='ignore')
