"""Summarize paired results and apply a documented source-reference correction."""
from pathlib import Path
from copy import deepcopy
import json,statistics,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.catalog import readonly,annual_path

def main():
    raw=json.loads((ROOT/'evaluations/model_comparison_current.json').read_text(encoding='utf-8'))
    cases=deepcopy(raw['cases'])
    with readonly(annual_path(2024)) as db:
        expected={r[0] for r in db.execute("SELECT h.UNITID FROM HD2024 h JOIN IC2024 i USING(UNITID) WHERE h.STABBR='MA' AND h.DEGGRANT=1 AND i.DISTCRS=1")}
    for c in cases:
        c['raw_passed']=c['passed']
        if c['case']=='ma_distance' and c.get('checks'):
            c['checks']['exact_institution_set']={r['unitid'] for r in c.get('rows',[])}==expected
            c['passed']=all(c['checks'].values())
    models=[m['model'] for m in raw['models']]
    matched=[(r,label) for r,label in sorted({(c['round'],c['case']) for c in cases})
             if all(any(c['model']==m and c['round']==r and c['case']==label and c['passed'] for c in cases) for m in models)]
    summary={'scope':raw['scope'],'expected_tasks_per_model':raw['expected_tasks_per_model'],
        'reference_correction':{'case':'ma_distance','reason':'The broad question asks whether distance-education courses are offered. The initial fixture mistakenly used the narrower undergraduate opportunity field DSTNCED1 (83 schools). DISTCRS is the direct institutional course-offering response (95 schools). Only grading was corrected; prompts and model answers were not changed.',
                                'expected_count':len(expected),'source_variable_record_id':136131,'sql':"SELECT h.UNITID FROM HD2024 h JOIN IC2024 i USING(UNITID) WHERE h.STABBR='MA' AND h.DEGGRANT=1 AND i.DISTCRS=1"},
        'matched_successful_pairs':len(matched),'models':[],'cases':cases,
        'estimated_total_including_warmup':raw['estimated_spend_including_warmup']}
    for model in models:
        selected=[c for c in cases if c['model']==model];success=[c for c in selected if c['passed']]
        same=[c for c in selected if (c['round'],c['case']) in matched]
        discovery=[c for c in selected if c['case']=='discovery']
        calls=[c for c in raw['calls'] if c['model']==model and not c['case_id'].startswith('warmup:')]
        entry={'model':model,'passed':len(success),'total':len(selected),
            'median_all_attempts_seconds':statistics.median(c['wall_seconds'] for c in selected),
            'median_successful_seconds':statistics.median(c['wall_seconds'] for c in success),
            'median_matched_successful_seconds':statistics.median(c['wall_seconds'] for c in same),
            'estimated_task_usd':sum(c['estimated_api_usd'] for c in selected),
            'provider_calls':len(calls),'usage_complete':all(c['usage_complete'] for c in selected),
            'narrative_accepted':sum(c['narrative_status']=='accepted' for c in discovery),'narrative_total':len(discovery),
            'max_prompt_tokens':max(sum(c.get(k,0) for k in ['input_tokens','cache_read_input_tokens','cache_creation_input_tokens']) for c in calls),
            'by_case':[],'failures':[]}
        for label in dict.fromkeys(c['case'] for c in selected):
            group=[c for c in selected if c['case']==label]
            entry['by_case'].append({'case':label,'passed':sum(c['passed'] for c in group),'total':len(group),
                                    'median_seconds':statistics.median(c['wall_seconds'] for c in group),'estimated_usd':sum(c['estimated_api_usd'] for c in group)})
        for c in selected:
            if not c['passed']:entry['failures'].append({k:c.get(k) for k in ['round','case','checks','intent','mode','message','error','interpretation']})
        summary['models'].append(entry)
    (ROOT/'evaluations/model_comparison_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in {'cases','models'}},indent=2))
    for m in summary['models']:print(json.dumps(m,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
