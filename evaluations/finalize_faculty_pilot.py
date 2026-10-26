"""Apply a safe writing fallback to the recorded second pass; no new API calls."""
from pathlib import Path
import sys,json,statistics
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
import evaluations.faculty_answer_pilot as p
original=json.loads((p.OUT/'results.json').read_text(encoding='utf-8'))
refined=json.loads((p.OUT/'writing_refinement.json').read_text(encoding='utf-8'))
calls=json.loads((p.OUT/'writing_refinement_calls.json').read_text(encoding='utf-8'))
out=[]
for row in refined:
    entry=next(e for e in original if e['id']==row['id'])
    pkg=json.loads((p.OUT/(row['id']+'_evidence.json')).read_text(encoding='utf-8'))
    if 'error' in row:
        rejected=next(c for c in calls if c['case']==row['id'])
        writing={'lead_scope_id':entry['rows'][0]['id'],
            'explanation':'The rows describe the source populations named in the table. Matching counts do not make different definitions interchangeable.',
            'evidence_ids':[pkg['table']['record_id']]}
        row={**row,'status':'fallback','rejected_writing':rejected['tool_inputs'],
            'usage':rejected['usage'],'answer':p.render(pkg,entry['review'],entry['rows'],writing,refined=True)}
    else:row={**row,'status':'accepted'}
    repair_path=p.OUT/'semantic_repair.json'
    if row['id']=='instructional_faculty' and repair_path.exists():
        repair=json.loads(repair_path.read_text(encoding='utf-8'))
        row={**row,'status':'accepted_after_source_definition_repair',
            'initial_semantic_failure':row['writing'],'writing':repair['writing'],
            'answer':repair['answer'],'semantic_repair_usage':repair['usage'],
            'additional_source_evidence':repair['additional_source_evidence']}
    out.append(row)
(p.OUT/'final_writing_results.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
md='# Tested faculty-answer examples\n\nEvaluation only; live app unchanged.\n\n'
for row in out:
    entry=next(e for e in original if e['id']==row['id'])
    md+='## '+row['id']+'\n\n**Question:** '+entry['question']+'\n\n'+row['answer']+'\n\n'
for entry in original:
    if entry.get('review',{}).get('action')=='clarify':md+='## '+entry['id']+'\n\n**Question:** '+entry['question']+'\n\n'+entry['answer']+'\n\n'
(p.OUT/'final_answers.md').write_text(md,encoding='utf-8')
count_cases=[e for e in original if e.get('rows')]
summary={'tested_questions':len(original),'count_answers':len(count_cases),'clarifications':len(original)-len(count_cases),
    'routing_matches':sum(e.get('checks',{}).get('decision',False) for e in original),
    'exact_scope_profiles':sum(e.get('checks',{}).get('scopes',False) for e in count_cases),
    'source_values_checked':sum(len(r['values']) for e in count_cases for r in e['rows']),
    'initial_count_answer_median_seconds':statistics.median(e['seconds'] for e in count_cases),
    'initial_count_answer_min_seconds':min(e['seconds'] for e in count_cases),
    'initial_count_answer_max_seconds':max(e['seconds'] for e in count_cases),
    'initial_count_answer_median_usd':statistics.median(e['estimated_api_usd'] for e in count_cases),
    'initial_completed_suite_api_usd':sum(e.get('estimated_api_usd',0) for e in original),
    'refined_writing_accepted':sum(r['status']=='accepted' for r in out),'refined_writing_fallbacks':sum(r['status']=='fallback' for r in out),
    'semantic_repairs':sum(r['status']=='accepted_after_source_definition_repair' for r in out),
    'refined_writing_api_usd':sum(r['usage']['estimated_api_usd'] for r in out),
    'refined_answer_word_median':statistics.median(len(r['answer'].split()) for r in out),
    'initial_answer_word_median':statistics.median(len(e['answer'].split()) for e in count_cases)}
(p.OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
