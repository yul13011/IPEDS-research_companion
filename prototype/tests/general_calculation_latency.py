"""Live unfamiliar calculation evaluation with independent SQL and latency."""
from pathlib import Path
import datetime
import json
import math
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.agent import ask, DEFAULT_MODEL
from prototype.catalog import readonly, annual_path
from prototype.exports import csv_bytes, excel_bytes, audit_bytes

CASES=[
    ('admissions women share',"What percentage of Yale's fall 2024 applicants were women?",'SELECT APPLCNW,APPLCN FROM ADM2024 WHERE UNITID=130794'),
    ('bachelor awards women share',"What percentage of Yale's bachelor's degrees awarded from July 1, 2023 through June 30, 2024 went to women? Use first majors across all fields of study.","SELECT CTOTALW,CTOTALT FROM C2024_A WHERE UNITID=130794 AND AWLEVEL=5 AND CIPCODE='99' AND MAJORNUM=1"),
    ('physical library collection share',"For fiscal year 2024, what percentage of Yale's total physical and electronic library collection units were physical collection units? Include all collection types, not just books.",'SELECT LPCLLCT,LTCLLCT FROM AL2024 WHERE UNITID=130794'),
]


def main():
    if '--live' not in sys.argv:raise SystemExit('Pass --live to run actual provider requests.')
    records=[]
    for label,question,sql in CASES:
        start=time.perf_counter();r={'label':label,'question':question,'independent_sql':sql}
        with readonly(annual_path(2024)) as db:n,d=db.execute(sql).fetchone()
        r['expected_numerator']=n;r['expected_denominator']=d;r['expected_percent']=100*n/d
        try:
            a=ask(question,use_model=True)
            r.update(outcome=a['intent'],message=a.get('message'),latency=a.get('latency'),model_usage=a.get('model_usage'),repair_history=a.get('validation_attempts',[]))
            result=a.get('result');percent_rows=[row for row in (result or {}).get('rows',[]) if row['unit']=='percent']
            r['passed']=any(row['status']=='ok' and row['numerator']==n and row['denominator']==d and math.isclose(row['value'],100*n/d,rel_tol=1e-10) for row in percent_rows)
            if result:
                r['rows']=result['rows'];r['export_seconds']={}
                for kind,fn in [('csv',csv_bytes),('excel',excel_bytes),('audit_json',audit_bytes)]:
                    mark=time.perf_counter();fn(result);r['export_seconds'][kind]=time.perf_counter()-mark
                (ROOT/'evaluations/results'/('general-'+label.replace(' ','-')+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
        except Exception as exc:
            r.update(outcome='error',passed=False,error_type=type(exc).__name__)
        r['test_wall_seconds']=time.perf_counter()-start;records.append(r)
        times=[x['latency']['answer_ready_seconds'] for x in records if x.get('latency')]
        report={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model':DEFAULT_MODEL,'cases':records,
            'passed':sum(x['passed'] for x in records),'total':len(records),
            'latency_summary':{'n':len(times),'median_seconds':statistics.median(times),'min_seconds':min(times),'max_seconds':max(times)} if times else None,
            'scope':'Live model, no previous plan, generic catalog route with no case-specific numerical shortcuts. Independent source SQL verifies the requested percent. Small serial sample; caches can warm; browser paint excluded; exports separately measured. Failed requests retain elapsed time.'}
        (ROOT/'evaluations/general_calculation_latency.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in r.items() if k not in {'rows','repair_history'}},ensure_ascii=False),flush=True)
    return 0 if all(x['passed'] for x in records) else 1


if __name__=='__main__':sys.exit(main())
