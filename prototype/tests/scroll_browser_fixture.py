"""Isolated UI-only scroll check. Never calls a model or changes source data."""
from pathlib import Path
import sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
import streamlit as st
from prototype import ui

if 'history' not in st.session_state:
    st.session_state.main_page='Ask & Analyze'
    st.session_state.history=[{'question':f'Older question {i}', 'answer':{'intent':'clarify',
        'message':f'Older answer {i}. '+('A longer source-backed explanation for scrolling verification. '*12)}} for i in range(1,9)]

def answer(question,*args,**kwargs):
    # Deliberate wait makes pending state/manual scrolling observable.
    time.sleep(6)
    return {'intent':'clarify','message':'Latest answer: '+question+'. '+('More answer details. '*30)}

ui.ask=answer
ui.main()
