"""Repeatable source-backed routing probes; --live uses the configured provider."""
import json,time,sys
from pathlib import Path
from prototype.institution_confirmation import ask
from prototype.progress import reporting

out=Path('evaluations/flexible_routing_probes');out.mkdir(exist_ok=True)
live='--live' in sys.argv
cases=[('greeting','Hi'),('help','What can you do?'),('polite_definition','Can you explain Pell?'),
       ('numerical','Yale applicants fall 2024'),
       ('mixed','Define admission rate and show Yale admission rate fall 2024')]
if '--analysis-only' in sys.argv:cases=[case for case in cases if case[0] in {'numerical','mixed'}]
records=[]
for label,question in cases:
    events=[];started=time.perf_counter()
    try:
        with reporting(events.append):answer=ask(question,use_model=live)
        record={'case':label,'question':question,'wall_seconds':round(time.perf_counter()-started,3),
                'live':live,'intent':answer.get('intent'),'model_usage':answer.get('model_usage',{}),
                'has_result':bool(answer.get('result')),'has_documentation':bool(answer.get('documentation_sections')),
                'source_evidence_count':len(answer.get('evidence',[])),'stages':events}
        (out/(label+('_live' if live else '_local')+'.json')).write_text(json.dumps(answer,indent=2,ensure_ascii=False),encoding='utf-8')
    except Exception as exc:record={'case':label,'error':str(exc),'wall_seconds':round(time.perf_counter()-started,3),'live':live}
    records.append(record);print(json.dumps(record),flush=True)
(out/(('live_analysis_summary.json' if '--analysis-only' in sys.argv else 'live_summary.json') if live else 'local_summary.json')).write_text(json.dumps(records,indent=2),encoding='utf-8')
