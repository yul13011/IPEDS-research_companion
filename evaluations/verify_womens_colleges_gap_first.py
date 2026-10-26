"""Inspect the saved live response without any provider call."""
from pathlib import Path
import json
root=Path(__file__).resolve().parent
record=json.loads((root/'womens_colleges_gap_first_trace.json').read_text(encoding='utf-8'))
answer=record['answer']
checks={
    'coverage_response':answer['mode']=='source coverage limitation',
    'no_statistical_result':'result' not in answer,
    'gap_first':answer['message'].startswith('I can'),
    'local_inspection_evidence':bool(answer['coverage_gap']['source_inspections']),
    'no_forced_proxy_options':not answer['analysis_brief']['options'],
    'no_external_suggestion':not any(term in answer['message'].lower() for term in ['scorecard','http://','https://']),
    'scope_disclosed':'2024' in answer['message'] and 'other release years' in answer['message'],
}
out={'checks':checks,'passed':all(checks.values()),'inspection_count':len(answer['coverage_gap']['source_inspections'])}
(root/'womens_colleges_gap_first_verification.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out));raise SystemExit(not out['passed'])
