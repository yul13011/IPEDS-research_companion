"""Live unfamiliar relational questions, independent SQL, and end-to-end latency."""
from pathlib import Path
import datetime,json,math,statistics,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.agent import ask,DEFAULT_MODEL
from prototype.catalog import readonly,annual_path
from prototype.exports import csv_bytes,excel_bytes,audit_bytes

CASES=[
 ('grouped_awards',"Show Yale's total awards by award level for July 1, 2023 through June 30, 2024. Use all fields of study and first majors. Return counts, not percentages.","SELECT CTOTALT FROM C2024_A WHERE UNITID=130794 AND CIPCODE='99' AND MAJORNUM=1",2024),
 ('weighted_salary',"For Yale, calculate the weighted average nine-month salary of full-time nonmedical instructional staff across professor, associate professor and assistant professor ranks in the 2024–25 release. Weight each rank's nine-month average salary by its nine-month staff count. Exclude all other ranks and the all-ranks total.","SELECT SUM(1.0*SA09MAT*SA09MCT)/SUM(SA09MCT) FROM SAL2024_IS WHERE UNITID=130794 AND ARANK IN (1,2,3)",2024),
 ('cross_period_change',"Calculate the percentage change in Yale's total applicants from fall 2023 to fall 2024, using fall 2023 as the baseline.",'SELECT APPLCN FROM ADM2024 WHERE UNITID=130794',2024),
 ('joined_weighted_tuition',"Calculate one combined weighted mean of Yale and Harvard's out-of-state undergraduate tuition for academic year 2024–25, weighted by each institution's fall 2024 total undergraduate headcount. Use the tuition amount and enrollment headcount from their respective source tables; explicitly compare these different reporting periods.",'SELECT SUM(1.0*t.TUITION3*e.EFTOTLT)/SUM(e.EFTOTLT) FROM Cost1_2024 t JOIN EF2024A e USING(UNITID) WHERE t.UNITID IN (130794,166027) AND e.EFALEVEL=2',2024),
]

def main():
 if '--live' not in sys.argv:raise SystemExit('Pass --live for provider requests.')
 target=ROOT/'evaluations/query_engine_latency.json'
 records=json.loads(target.read_text(encoding='utf-8'))['cases'] if len(sys.argv)>2 and target.exists() else []
 for label,q,sql,year in CASES:
  if len(sys.argv)>2 and label not in sys.argv[2:]:continue
  started=time.perf_counter();r={'label':label,'question':q,'independent_sql':sql}
  with readonly(annual_path(year)) as db:expected=[float(x[0]) for x in db.execute(sql)]
  if label=='cross_period_change':
   with readonly(annual_path(2023)) as db:old=db.execute('SELECT APPLCN FROM ADM2023 WHERE UNITID=130794').fetchone()[0]
   expected=[(expected[0]-old)/old*100]
  r['expected_values']=sorted(expected)
  try:
   answer=ask(q,use_model=True);result=answer.get('result')
   r.update(intent=answer['intent'],message=answer.get('message'),latency=answer.get('latency'),model_usage=answer.get('model_usage'),repairs=answer.get('validation_attempts',[]))
   actual=sorted(float(row['value']) for row in (result or {}).get('rows',[]) if row['status']=='ok')
   r['actual_values']=actual;r['passed']=len(actual)==len(expected) and all(math.isclose(a,b,rel_tol=1e-9) for a,b in zip(actual,sorted(expected)))
   if result:
    r['plan_version']=result.get('catalog_plan',{}).get('version');r['export_seconds']={}
    for name,fn in [('csv',csv_bytes),('excel',excel_bytes),('audit_json',audit_bytes)]:
     mark=time.perf_counter();fn(result);r['export_seconds'][name]=time.perf_counter()-mark
    (ROOT/'evaluations/results'/('relational-'+label+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
  except Exception as exc:r.update(passed=False,error_type=type(exc).__name__,error=str(exc))
  r['test_wall_seconds']=time.perf_counter()-started;records=[x for x in records if x['label']!=label]+[r]
  times=[x['latency']['answer_ready_seconds'] for x in records if x.get('latency')]
  report={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model':DEFAULT_MODEL,'cases':records,'passed':sum(x['passed'] for x in records),'total':len(records),'median_seconds':statistics.median(times) if times else None,'scope':'Live unfamiliar questions with no conversation history; independent raw-source SQL; server answer-ready latency excludes browser paint. Exports separately timed. Small serial sample.'}
  (ROOT/'evaluations/query_engine_latency.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
  print(json.dumps(r),flush=True)
 return 0 if all(x['passed'] for x in records) else 1

if __name__=='__main__':sys.exit(main())
