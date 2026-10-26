"""Live, serial answer-ready timings. No mocked transport or synthetic values.

Run with --live to incur the configured provider's normal API usage. Each case
is a fresh question (no previous plan); process/catalog/provider caches may warm.
"""
from pathlib import Path
import argparse
import datetime
import json
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.agent import ask, DEFAULT_MODEL
from prototype.exports import excel_bytes, csv_bytes, audit_bytes


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
    cases=[('enrollment shortcut',"Show Yale's undergrad population by race and ethnicity",False),
           ('unfamiliar library',"How many physical books did Yale's library report for fiscal year 2024?",True),
           ('unfamiliar tuition',"Show Yale's out-of-state undergraduate tuition for academic year 2024-25, excluding fees and room and board.",True),
           ('unfamiliar library repeat',"How many physical books did Yale's library report for fiscal year 2024?",True)]
    records=[]
    for label,question,live in cases:
        if live and not args.live:continue
        start=time.perf_counter();record={'label':label,'question':question,'live_model_requested':live}
        try:
            answer=ask(question,use_model=live)
            record.update(outcome=answer['intent'],message=answer.get('message'),latency=answer.get('latency'),
                          model_usage=answer.get('model_usage'),rows=len(answer.get('result',{}).get('rows',[])))
            if answer.get('result'):
                result=answer['result'];record['observations']=[{k:r[k] for k in ['measure','value','reporting_period','status']} for r in result['rows']]
                record['export_seconds']={}
                for name,fn in [('csv',csv_bytes),('excel',excel_bytes),('audit_json',audit_bytes)]:
                    mark=time.perf_counter();payload=fn(result)
                    record['export_seconds'][name]=time.perf_counter()-mark
                    record.setdefault('export_bytes',{})[name]=len(payload)
                (ROOT/'evaluations/results').mkdir(exist_ok=True)
                (ROOT/'evaluations/results'/('latency-'+label.replace(' ','-')+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
        except Exception as exc:
            record.update(outcome='error',error_type=type(exc).__name__)
        record['test_wall_seconds']=time.perf_counter()-start
        records.append(record)
        report={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model':DEFAULT_MODEL,'cases':records,
                'measurement':'Serial fresh questions in one Python process; answer-ready includes planning, catalog binding, validation, query, and summary. Exports separate. Browser/network paint excluded. Repeated questions can benefit from caches. Small descriptive sample, not a service-level guarantee.'}
        live_values=[r['latency']['answer_ready_seconds'] for r in records if r.get('model_usage',{} ) and r.get('latency')]
        if live_values:report['live_answer_ready_summary']={'n':len(live_values),'min_seconds':min(live_values),'median_seconds':statistics.median(live_values),'max_seconds':max(live_values)}
        (ROOT/'evaluations/catalog_latency.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(record,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
