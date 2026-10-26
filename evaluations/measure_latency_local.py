"""Controlled local comparisons: old eager-work emulation vs optimized paths."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import json,statistics,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.analytics import Plan,execute
from prototype.responses import finalize_answer
from prototype.chart_format import series_names
from prototype.charts import series_names_for_context
from prototype.discovery import overview
from prototype.discovery_narrative import evidence_package,compact_package

def timed(fn,n=5):
    samples=[]
    for _ in range(n):
        start=time.perf_counter();fn();samples.append(time.perf_counter()-start)
    return {'median_seconds':statistics.median(samples),'samples':samples}

def main():
    from streamlit.testing.v1 import AppTest
    import streamlit as st
    r=execute(Plan(['graduation_rate'],['Ivy League'],list(range(2015,2025))))
    a=finalize_answer({'result':r})
    series_names(r,a['presentation']);series_names_for_context(r,a['presentation'])
    report={'scope':'Same-process controlled local comparison. Eager mode materializes the exact new download producers during redraw to emulate prior eager-export work; other code is held constant. No API calls, no browser paint/network measurements.',
        'series_old':timed(lambda:series_names(r,a['presentation'])),
        'series_new':timed(lambda:series_names_for_context(r,a['presentation']))}
    p,_=evidence_package(overview('What data do you have on faculty?'),'What data do you have on faculty?');c,_=compact_package(p)
    report['discovery']={'full_chars':len(json.dumps(p,ensure_ascii=False)),
                         'compact_chars':len(json.dumps(c,ensure_ascii=False)),
                         'passages_before':sum(len(r['passages']) for r in p['source_records']),
                         'distinct_passages_after':len(c['source_passages'])}
    app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=90).run()
    app.session_state['use_ai']=False;app.session_state['main_page']='Ask & Analyze'
    original_download=st.download_button;redraws=[]
    for count in [1,5]:
        app.session_state['history']=[{'question':'Graduation trend','answer':deepcopy(a)} for _ in range(count)]
        app.run()
        measurements={'deferred':[],'eager_emulation':[]};counts={}
        for cycle in range(3):
            for mode in (['deferred','eager_emulation'] if cycle%2==0 else ['eager_emulation','deferred']):
                generated=[]
                def download(label,data,**kwargs):
                    if mode=='eager_emulation' and callable(data):data=data();generated.append(label)
                    return original_download(label,data,**kwargs)
                with patch('streamlit.download_button',side_effect=download):
                    start=time.perf_counter();app.run();elapsed=time.perf_counter()-start
                if app.exception:raise RuntimeError(str(app.exception))
                measurements[mode].append(elapsed);counts[mode]=len(generated)
        item={'history_answers':count,**{mode:{'median_seconds':statistics.median(times),'samples':times,'exports_generated_per_redraw':counts[mode]} for mode,times in measurements.items()}}
        redraws.append(item);print(json.dumps(item),flush=True)
    report['redraws']=redraws
    (ROOT/'evaluations/latency_local_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='redraws'}),flush=True)

if __name__=='__main__':main()
