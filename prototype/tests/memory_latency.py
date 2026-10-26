"""Real conversational continuations, cross-route context, source checks and latency."""
from pathlib import Path
import datetime,json,math,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.agent import ask
from prototype.catalog import readonly,annual_path

def main():
 if '--live' not in sys.argv:raise SystemExit('Pass --live for provider calls.')
 history=[];records=[]
 questions=["Show Yale's undergraduate population by race and ethnicity in fall 2024",'now Harvard','show percentages',"How many applicants did Yale have in fall 2024?","Back to Harvard's undergraduate race breakdown: show counts again."]
 for i,q in enumerate(questions):
  started=time.perf_counter();a=ask(q,use_model=i>0,conversation=history);rows=a.get('result',{}).get('rows',[])
  if i==3:
   with readonly(annual_path(2024)) as db:expected=db.execute('SELECT APPLCN FROM ADM2024 WHERE UNITID=130794').fetchone()[0]
   passed=len(rows)==1 and rows[0]['unitid']==130794 and rows[0]['value']==expected
  else:
   uid=130794 if i==0 else 166027
   with readonly(annual_path(2024)) as db:
    row=db.execute('SELECT EFTOTLT,EFHISPT, EFAIANT,EFASIAT,EFBKAAT,EFNHPIT,EFWHITT,EF2MORT,EFUNKNT,EFNRALT FROM EF2024A WHERE UNITID=? AND EFALEVEL=2',(uid,)).fetchone()
   expected=sorted(100*v/row[0] if i==2 else v for v in row[1:])
   actual=sorted(r['value'] for r in rows if r['status']=='ok' and (i!=2 or r['unit']=='percent'))
   # Count answers may include an explicit total, separately verified.
   if i!=2 and len(actual)==10:expected=sorted(expected+[row[0]])
   passed=len(actual)==len(expected) and all(math.isclose(x,y,rel_tol=1e-9) for x,y in zip(actual,expected)) and all(r['unitid']==uid for r in rows)
  r={'question':q,'resolved_question':a.get('resolved_question'),'resolution':a.get('conversation_resolution'),'intent':a['intent'],'message':a.get('message'),'passed':passed,'latency':a.get('latency'),'model_calls':a.get('model_usage',{}).get('calls',0),'wall_seconds':time.perf_counter()-started}
  records.append(r);history.append({'question':q,'answer':a})
  report={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':sum(r['passed'] for r in records),'total':len(records),'cases':records,'scope':'Sequential live conversation, with deterministic source-SQL verification. Initial context setup is local; subsequent turns use the actual model resolver/planners. Answer-ready excludes browser paint.'}
  (ROOT/'evaluations/memory_latency.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
  print(json.dumps(r),flush=True)
 return 0 if all(r['passed'] for r in records) else 1

if __name__=='__main__':sys.exit(main())
