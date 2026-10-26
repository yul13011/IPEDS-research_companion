"""Live preflight/confirmation followed by independent source checks."""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.institution_confirmation import ask
from prototype.catalog import readonly,annual_path

if '--live' not in sys.argv:raise SystemExit('Pass --live for provider calls.')
q="Show University of Michigan's undergraduate population by race and ethnicity in fall 2024"
started=time.perf_counter();a=ask(q,use_model=True)
assert a['intent']=='institution_confirmation' and 'result' not in a,a.get('message')
b=ask(q,use_model=True,institution_choices={'university of michigan':170976})
assert b['intent']=='analyze',b.get('message')
assert all(r['unitid']==170976 for r in b['result']['rows'])
with readonly(annual_path(2024)) as db:
    expected=list(db.execute('SELECT EFAIANT,EFASIAT,EFBKAAT,EFHISPT,EFNHPIT,EFWHITT,EF2MORT,EFUNKNT,EFNRALT,EFTOTLT FROM EF2024A WHERE UNITID=170976 AND EFALEVEL=2').fetchone())
assert sorted(r['value'] for r in b['result']['rows'])==sorted(expected)
report={'pending':a,'confirmed_institution':b['institution_identity'],'latency':b['latency'],'independent_values':expected,'passed':True,'wall_seconds':time.perf_counter()-started,'scope':'Live extraction and continuation after explicit UNITID selection; all nine category counts and total checked against independent source SQL. Human selection time excluded.'}
(ROOT/'evaluations/institution_confirmation_live.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'latency':b['latency'],'source_total':expected[-1]}))
