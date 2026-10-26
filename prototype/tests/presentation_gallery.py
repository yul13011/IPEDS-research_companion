"""Local visual QA of actual chat, formatting panel and export; no model call."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
import streamlit as st
from prototype.analytics import execute,Plan
from prototype.responses import finalize_answer
from prototype.ui import main
if 'gallery_seeded' not in st.session_state:
    r=execute(Plan(['total_enrollment'],['166939','167835'],list(range(2015,2025))))
    a=finalize_answer({'result':r});a['presentation']['title']='Fall enrollment at Mount Holyoke and Smith'
    st.session_state.update(main_page='Ask & Analyze',ideas_open=False,tools_open=False,history=[{'question':'Compare Mount Holyoke’s total enrollment with Smith College.','answer':a}],gallery_seeded=True)
main()
