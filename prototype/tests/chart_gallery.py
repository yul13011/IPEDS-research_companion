"""Local-only visual QA for shared chart specifications; no model calls."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
import streamlit as st
from prototype.agent import ask
from prototype.analytics import Plan,execute
from prototype.responses import presentation_for
import importlib
from prototype import charts
panels=importlib.reload(charts).panels
st.set_page_config(page_title='IPEDS chart verification',layout='wide')
st.title('IPEDS chart verification')
case=st.selectbox('Case',['Race percentages','Race counts','Ivy League trends','Entering cohorts','Institution comparison'])
width=st.radio('Chart width',['Normal','Narrow'],horizontal=True)
if case.startswith('Race'):
    r=ask('Show Yale undergrad population by race and ethnicity in 2024'+(' as percentages' if case=='Race percentages' else ''))['result']
elif case=='Ivy League trends':r=execute(Plan(['admission_rate'],['Ivy League'],list(range(2015,2025))))
elif case=='Entering cohorts':r=execute(Plan(['graduation_rate'],['Yale'],list(range(2009,2019)),time_basis='entry_cohort'))
else:r=execute(Plan(['applicants'],['Ivy League'],[2024]))
p=presentation_for(r)
if case.startswith('Race'):p['chart_type']='bar'
with st.container(width=900 if width=='Normal' else 360):
    for panel in panels(r,p):
        st.markdown('**'+panel['title']+'**');st.caption(panel['subtitle'])
        st.altair_chart(panel['chart'],width='stretch',theme=None);st.caption(panel['note'])
