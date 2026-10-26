"""Independent source-SQL and actual app interaction checks for live artifacts."""
from pathlib import Path
import json,sys,re,time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.catalog import readonly,annual_path
from analysis_catalog.catalog import connection
OUT=ROOT/'evaluations/clarification_workflow'
first=json.loads((OUT/'turn_1.json').read_text(encoding='utf-8'))
second=json.loads((OUT/'turn_2.json').read_text(encoding='utf-8'))
checks=[]
with connection() as catalog,readonly(annual_path(2024)) as db:
    fields={r['record_id']:r['variable_name'] for r in catalog.execute("SELECT record_id,variable_name FROM source.variable_docs WHERE release_id='IPEDS_2024-25_Provisional'")}
    staff={r['FACSTAT']:dict(r) for r in db.execute('SELECT * FROM S2024_SIS WHERE UNITID=130493 AND FACSTAT IN (20,30)')}
    salaries={r['ARANK']:dict(r) for r in db.execute('SELECT * FROM SAL2024_IS WHERE UNITID=130493')}
    labels={r['value_label']:r['code_value'] for r in catalog.execute("SELECT value_label,code_value FROM source.code_values WHERE release_id='IPEDS_2024-25_Provisional' AND table_name='SAL2024_IS' AND variable_name='ARANK'")}
    for row in second['result']['rows']:
        field=fields[int(re.search(r'_(\d+)$',row['metric'])[1])]
        status=30 if 'on tenure track' in ' '.join(row['groups']) else 20
        expected=float(staff[status][field]);assert expected==row['value'],(field,status,expected,row['value'])
        checks.append({'field':field,'tenure_status':status,'value':expected,'pass':True})
    for row in second['related_analyses'][0]['result']['rows']:
        field=fields[int(re.search(r'_(\d+)$',row['metric'])[1])]
        label=row['groups'][0].split(': ',1)[1];rank=int(labels[label])
        expected=float(salaries[rank][field]);assert expected==row['value'],(field,rank,expected,row['value'])
        checks.append({'field':field,'rank':rank,'value':expected,'pass':True})
    expected_professors=float(db.execute('SELECT SUM(SISPROF) FROM S2024_SIS WHERE UNITID=130493 AND FACSTAT IN (20,30)').fetchone()[0])
    expected_salary=float(db.execute('SELECT SAEQ9AT FROM SAL2024_IS WHERE UNITID=130493 AND ARANK=1').fetchone()[0])
    third_path=OUT/'turn_3.json'
    if third_path.exists():
        third=json.loads(third_path.read_text(encoding='utf-8'))
        assert third.get('result'),third.get('message')
        values=[r['value'] for a in [third]+third.get('related_analyses',[]) for r in a.get('result',{}).get('rows',[])]
        assert expected_professors in values and expected_salary in values,(values,expected_professors,expected_salary)
        checks.append({'modified_followup':True,'professors':expected_professors,'salary':expected_salary,'pass':True})

from streamlit.testing.v1 import AppTest
started=time.perf_counter()
app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60)
app.session_state['main_page']='Ask & Analyze'
app.session_state['history']=[{'question':'How many ladder faculty does Southern Connecticut State University have, and what are their average salaries by academic rank?','answer':first}]
app.run();assert not app.exception,app.exception
app.button(key='answer_0_discovery_choice_A').click().run()
assert not app.exception,app.exception
history=app.session_state['history'];answer=history[-1]['answer']
assert answer['analysis_brief']['status']=='completed'
assert len(answer['related_analyses'])==1
assert answer['model_usage']['calls']==0
assert not any(b.label.startswith('Use ') for b in app.button)
app.button(key='clear_chat').click().run()
assert not app.exception,app.exception
assert not app.session_state['history']
checks.append({'actual_app_button_and_two_panels':True,'clear_conversation':True,'seconds':time.perf_counter()-started,'pass':True})
(OUT/'verification.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(f'{len(checks)} independent source/UI checks passed.',flush=True)
