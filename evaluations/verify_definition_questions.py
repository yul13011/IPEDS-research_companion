"""Independent final saved-answer/source checks; no provider requests."""
from pathlib import Path
import json,re,sqlite3,statistics
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluations'
refined=json.loads((OUT/'definition_questions_live_refined.json').read_text())['cases']
rate=json.loads((OUT/'definition_questions_reviewed_rate_recheck.json').read_text())['cases'][0]
graduation=json.loads((OUT/'definition_questions_graduation_recheck.json').read_text())['cases'][0]
cases=[graduation if c['question']=='Define graduation rate' else rate if c['question']=='What is admission rate?' else c for c in refined]
normal=lambda s:re.sub(r'\s+',' ',s).strip()
checks={};source_cells=0
db=sqlite3.connect((ROOT/'data/metadata_catalog.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
for case in cases:
    a=case['answer'];q=case['question'];d=a['definition_lookup']
    checks[q+' / definition route']=a['mode']=='source definition' and 'result' not in a
    checks[q+' / supported status']=d['status']==('not_established' if 'quantum' in q else 'defined')
    for p in d['passages']:
        text=db.execute("SELECT coalesce(nullif(v.long_description,''),nullif(t.description,''),r.body) FROM records r LEFT JOIN variable_docs v USING(record_id) LEFT JOIN table_docs t USING(record_id) WHERE r.record_id=?",(p['record_id'],)).fetchone()
        checks[q+' / source '+str(p['record_id'])]=bool(text and p['excerpt'] in normal(text[0]));source_cells+=1
by_question={c['question']:c['answer'] for c in cases}
staff=by_question['What is the definition of instructional staff?']['message']
faculty=by_question['What is faculty?']['message']
grad=by_question['Define graduation rate']
checks['Instructional functions retained']='Instruction combined with research and/or public service' in staff
checks['No unrelated salary-outlay passage']='Annual salary outlays' not in staff
checks['Faculty designation distinct']='separate from the activities' in faculty and 'not included in this category' in faculty
checks['Graduation cohort population retained']='first-time' in grad['message'] and 'full-time' in grad['message']
checks['Generic graduation not bound to reviewed six-year default']=grad['definition_lookup']['reviewed_measure'] is None
checks['Reviewed rate coherent']='could not establish' not in rate['answer']['message'] and 'Admissions total ÷ Applicants total × 100' in rate['answer']['message']
checks['Explicit salary release retained']=by_question['What does SAL2023_IS.SAOUTLT mean?']['definition_lookup']['source_years']==[2023]
db.close()
timings=[c['wall_seconds'] for c in cases if c['answer']['definition_lookup']['status']=='defined']
report={'passed':all(checks.values()),'checks':checks,'questions':len(cases),'source_passages_verified':source_cells,
        'final_case_origins':['definition_questions_live_refined.json','definition_questions_graduation_recheck.json','definition_questions_reviewed_rate_recheck.json'],
        'median_supported_seconds':statistics.median(timings),'supported_range_seconds':[min(timings),max(timings)],
        'estimated_final_case_api_usd':sum(c['answer'].get('model_usage',{}).get('estimated_api_usd',0) or 0 for c in cases),
        'scope':'Final accepted cases combine the refined suite with explicitly preserved targeted rechecks. Timing/cost exclude earlier attempts and browser rendering.'}
(OUT/'definition_questions_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report));raise SystemExit(not report['passed'])
