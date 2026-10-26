"""Read-only grading summary: provider-unavailable tasks are not model failures."""
from pathlib import Path
from copy import deepcopy
import json,statistics
ROOT=Path(__file__).resolve().parents[1]

def median(values):return statistics.median(values) if values else None

def comparison(raw):
    from compare_models_current import color_is,yield_values_match,sql
    available=[deepcopy(c) for c in raw['cases'] if c.get('usage_complete')]
    corrections=[]
    for c in available:
        checks=c.get('checks') or {};presentation=c.get('presentation') or {}
        base=c['case'].split('__')[0]
        if base=='yield_followup' and len(c.get('rows') or [])==3:
            applicants,admits,enrolled=sql(2024,'SELECT APPLCN,ADMSSN,ENRLT FROM ADM2024 WHERE UNITID=130794')[0]
            expected={'admissions':[applicants,admits,100*admits/applicants],'yield_followup':[enrolled,100*enrolled/admits]}
            if yield_values_match(c['rows'],expected) and (not checks.get('exact_values') or not checks.get('complete_rows')):
                corrections.append({'model':c['model'],'round':c['round'],'case':c['case'],
                    'reason':'Requested yield/count are correct; the only extra row is the independently verified admitted denominator.'})
                checks.update(exact_values=True,complete_rows=True);c['passed']=all(checks.values())
        key='color' if base=='compound_style' else 'blue' if base=='mixed' else None
        if key and key in checks:
            value=presentation.get('series_colors',{}).get('Harvard University') if key=='color' else presentation.get('color')
            corrected=color_is(value,'red' if key=='color' else 'blue')
            if corrected!=checks[key]:
                corrections.append({'model':c['model'],'round':c['round'],'case':c['case'],'check':key,'value':value,'reason':'CSS color name and its exact six-digit hexadecimal equivalent are identical.'})
                checks[key]=corrected;c['passed']=all(checks.values())
    models=sorted({c['model'] for c in raw['cases']}|{m['model'] for m in raw.get('models',[])})
    result={'expected_per_model':raw['expected_tasks_per_model'],'models':[],'failures':[],'grading_corrections':corrections}
    paired={}
    for c in available:paired.setdefault((c['round'],c['case']),{})[c['model']]=c
    matched=[p for p in paired.values() if set(p)==set(models) and all(c['passed'] for c in p.values())]
    result['matched_successful_pairs']=len(matched)
    result['complete']=bool(models) and all(sum(c['model']==m for c in available)==raw['expected_tasks_per_model'] for m in models)
    for model in models:
        records=[c for c in available if c['model']==model]
        result['models'].append({'model':model,'completed':len(records),'passed':sum(c['passed'] for c in records),
            'unavailable':sum(c['model']==model and not c.get('usage_complete') for c in raw['cases']),
            'median_seconds':median([c['wall_seconds'] for c in records]),
            'matched_success_median_seconds':median([p[model]['wall_seconds'] for p in matched]),
            'estimated_completed_task_usd':sum(c['estimated_api_usd'] for c in records),
            'narratives_accepted':sum(c.get('narrative_status')=='accepted' for c in records),
            'narratives_attempted':sum(c.get('narrative_status') is not None for c in records),
            'interpretation_retries':sum(len((c.get('model_policy') or {}).get('interpretation_retries',[])) for c in records),
            'completed_cases':[{'case':c['case'],'round':c['round'],'passed':c['passed']} for c in records]})
        result['failures'].extend({k:c.get(k) for k in ['case','round','model','checks','message','error','rows']} for c in records if not c['passed'])
    return result


def main():
    raw=json.loads((ROOT/'evaluations/model_reliability_comparison.json').read_text(encoding='utf-8'))
    result={'scope':'Partial live comparison; Anthropic account usage limit prevented completion.',
        'expected_per_model':raw['expected_tasks_per_model'],'models':[],
        'narrative_settings':[],'limitations':['No automatic-policy live qualification was completed.',
            'Unavailable provider requests are excluded from model accuracy and latency.',
            'Narratives use identical deterministic evidence per topic; this differs from live model-expanded discovery.']}
    result.update(comparison(raw))
    result['scope']='Completed live comparison.' if result['complete'] else 'Partial live comparison; exclude provider-unavailable tasks.'
    result['limitations']=[s for s in result['limitations'] if not s.startswith('No automatic-policy')]
    policy=ROOT/'evaluations/model_policy_comparison.json'
    if policy.exists():result['automatic_comparison']=comparison(json.loads(policy.read_text(encoding='utf-8')))
    else:result['limitations'].append('Automatic-policy live qualification not yet completed.')
    for name in ['model_policy_followup','model_policy_annotation_fix']:
        path=ROOT/('evaluations/'+name+'.json')
        if path.exists():result[name]=comparison(json.loads(path.read_text(encoding='utf-8')))
    result['limitations'].extend([
        'Main-run scope failures preceded a verified-name/ID annotation repair; post-fix targeted results are separate, not substituted into the original scores.',
        'One paired SQLite timeout coincided with concurrent offline regressions; isolated follow-ups must be read separately from the main results.',
        'A small repeated workload does not establish general model superiority or production reliability.'])
    narrative=json.loads((ROOT/'evaluations/narrative_settings_comparison.json').read_text(encoding='utf-8'))['records']
    for config in sorted({c['configuration'] for c in narrative}):
        all_records=[c for c in narrative if c['configuration']==config]
        records=[c for c in all_records if c['usage'].get('usage_complete')]
        result['narrative_settings'].append({'configuration':config,'completed':len(records),
            'accepted':sum(c['status']=='accepted' for c in records),'unavailable':len(all_records)-len(records),
            'median_seconds':median([c['wall_seconds'] for c in records]),
            'estimated_usd':sum(c['usage']['estimated_api_usd'] for c in records),
            'rejections':[{'topic':c['topic'],'reason':c['reason']} for c in records if c['status']!='accepted']})
    target=ROOT/'evaluations/model_reliability_summary.json'
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
