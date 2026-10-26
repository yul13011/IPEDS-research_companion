"""Browser scroll policy; only application-owned JavaScript and numeric state."""
from pathlib import Path
import json
import streamlit as st

SCRIPT=Path(__file__).with_suffix('.js').read_text(encoding='utf-8')


def render(request,editing=False):
    config=json.dumps({'request':int(request),'editing':bool(editing)})
    with st.container(key='transcript_scroll_driver'):
        st.html('<script>'+SCRIPT+'\nwindow.ipedsTranscriptScroll.update('+config+');</script>',unsafe_allow_javascript=True)
