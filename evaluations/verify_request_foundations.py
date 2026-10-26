"""Live conversational acceptance: typed tasks, truthful coverage and stable scope."""
from pathlib import Path
from unittest.mock import patch
from copy import deepcopy
import json,math,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.intent_router import handle
from prototype.institution_confirmation import ask
from prototype.model_policy import AUTOMATIC
from prototype.working_analysis import results,recent_result
from prototype.analytics import Plan,execute
from prototype.responses import finalize_answer
from prototype.api_client import get_client
from prototype.agent import usage_cost
from prototype.catalog import readonly,annual_path
from prototype.tests.test_query_engine import source,plan,field_ref
from prototype.query_engine import execute as execute_query

FIELDS=['EFAIANT','EFASIAT','EFBKAAT','EFHISPT','EFNHPIT','EFWHITT','EF2MORT','EFUNKNT','EFNRALT']

def main():
    if '--live' not in sys.argv:raise SystemExit('Pass --live; capped at $1 estimated provider spend.')
    client=get_client();original=client.messages.create;calls=[];records=[]
    from prototype import agent
    original_plan=agent.model_plan;reviewed_plans=[]
    def model_plan(*args,**kwargs):
        action=original_plan(*args,**kwargs);reviewed_plans.append(deepcopy(action));return action
    target=ROOT/'evaluations/request_foundations_live.json'
    def create(**kwargs):
        if sum(c['estimated_api_usd'] for c in calls)>=1:raise RuntimeError('Live acceptance budget reached.')
        start=time.perf_counter();response=original(**kwargs)
        usage={k:getattr(response.usage,k,0) or 0 for k in ['input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens']}
        calls.append({'model':kwargs['model'],**usage,'estimated_api_usd':usage_cost(kwargs['model'],usage),'seconds':time.perf_counter()-start})
        return response
    def run(label,q,history,check):
        start=time.perf_counter();before=deepcopy(history);answer={};plan_start=len(reviewed_plans)
        try:
            answer=handle(q,recent_result(history),AUTOMATIC,history,ask)
            checks=check(answer);checks['history_unchanged']=history==before
            record={'case':label,'question':q,'passed':all(checks.values()),'checks':checks,'message':answer.get('message'),
                'reviewed_plans':reviewed_plans[plan_start:],'request_plan':answer.get('request_plan'),'task_tracking':answer.get('task_tracking'),
                'task_messages':[t['answer'].get('message') for t in answer.get('task_results',[])],
                'coverage':answer.get('coverage'),'working_analysis':answer.get('working_analysis'),
                'result_rows':[{k:r.get(k) for k in ['metric','unitid','observation_year','value','unit']} for x in results(answer) for r in x['result']['rows']],
                'usage':answer.get('model_usage'),'policy':answer.get('model_policy')}
        except Exception as exc:record={'case':label,'passed':False,'error_type':type(exc).__name__,'error':str(exc)}
        record['seconds']=time.perf_counter()-start;records.append(record)
        target.write_text(json.dumps({'records':records,'calls':calls,'estimated_api_usd':sum(c['estimated_api_usd'] for c in calls)},indent=2),encoding='utf-8')
        print(json.dumps({'case':label,'passed':record['passed'],'seconds':record['seconds'],'error':record.get('error'),'message':record.get('message'),'tasks':record.get('task_tracking')}),flush=True)
        if answer:history.append({'question':q,'answer':answer})
        return answer
    with patch.object(client.messages,'create',side_effect=create),patch.object(agent,'model_plan',side_effect=model_plan):
        intro=[]
        run('general_data_guide','What data do you have?',intro,
            lambda a:{'guide':a.get('coverage',{}).get('operation')=='overview','broad_topics':len(a.get('guide',{}).get('section_ids',[]))>=10})
        run('general_release_years','What years do you have?',intro,
            lambda a:{'release_inventory':a.get('coverage',{}).get('available_periods')==list(range(2015,2025)),
                'source_not_observation':a.get('coverage',{}).get('time_basis')=='source_release'})
        run('plain_language_topic','What information do you have about people working at colleges?',[],
            lambda a:{'staffing_guide':'staff' in a.get('guide',{}).get('section_ids',[])})
        history=[]
        first=run('ivy_compare','Compare Ivy League admission rates in fall 2024.',history,
            lambda a:{'eight_rates':sum(r.get('metric')=='admission_rate' for x in results(a) for r in x['result']['rows'])==8})
        rid=(first.get('working_analysis',{}).get('artifact') or {}).get('result_id')
        run('unavailable_followup','Do we have admission rates for Fall 2025?',history,
            lambda a:{'coverage':a.get('coverage',{}).get('requested_status')=='not_loaded',
                'available_periods':a.get('coverage',{}).get('available_periods')==list(range(2015,2025)),
                'retained_eight_institutions':len(a.get('coverage',{}).get('scope',{}).get('institutions',[]))==8,
                'same_artifact':(a.get('working_analysis',{}).get('artifact') or {}).get('result_id')==rid})
        run('available_years','Which years do we have?',history,
            lambda a:{'straight_answer':a.get('coverage',{}).get('available_periods')==list(range(2015,2025)),
                'same_measure':a.get('coverage',{}).get('scope',{}).get('measure_ids')==['admission_rate']})
        run('multiple_questions','Do we have admission rates for Fall 2025? Which years are available? Compare Ivy League admission rates for the latest available year.',history,
            lambda a:{'all_parts':len(a.get('task_tracking',{}).get('tasks',[]))>=3,
                'unavailable_and_answered':{t['status'] for t in a.get('task_tracking',{}).get('tasks',[])}=={'unavailable','answered'},
                'correct_latest':any(sum(r.get('metric')=='admission_rate' for r in x['result']['rows'])==8 and all(r['observation_year']==2024 for r in x['result']['rows']) for x in results(a))})
        s,d=source('EF2024A',fields=FIELDS,filters={'EFALEVEL':'2'})
        ug_plan=plan([s],[(field_ref(d[f],'s'),f) for f in FIELDS])
        ug=finalize_answer({'catalog_plan':ug_plan,'result':execute_query(ug_plan,'Yale undergraduate enrollment by race in fall 2024')})
        grad_history=[{'question':'Yale undergraduate enrollment by race and ethnicity in fall 2024.','answer':ug}]
        run('graduate_scope',"Yale's graduate enrollment by race and ethnicity in fall 2024.",grad_history,
            lambda a:{'result':bool(list(results(a))),'graduate_scope':all('12' in f['values'] for x in results(a) for src in (x.get('catalog_plan') or {}).get('sources',[]) for f in src['filters'])})
        grad_counts_history=deepcopy(grad_history)
        with readonly(annual_path(2024)) as db:
            raw=db.execute('SELECT '+','.join(FIELDS)+',EFTOTLT FROM EF2024A WHERE UNITID=130794 AND EFALEVEL=12').fetchone()
        expected=sorted(100*float(v)/raw[-1] for v in raw[:-1])
        def percent_check(a):
            values=[float(r['value']) for x in results(a) for r in x['result']['rows'] if r.get('unit')=='percent' and r.get('value') is not None]
            return {'nine_shares':len(values)==9,'exact_graduate_shares':len(values)==9 and all(math.isclose(x,y,rel_tol=1e-8) for x,y in zip(sorted(values),expected))}
        run('percentages_preserve_graduate','Convert these student enrollment numbers into percentages.',grad_history,percent_check)
        before=deepcopy(grad_history[-1]['answer'].get('working_analysis',{}).get('artifact'))
        run('unsupported_chart_preserves_scope','Show me a 100% stacked bar chart.',grad_history,
            lambda a:{'unsupported':any(t['status']=='unsupported' for t in a.get('task_tracking',{}).get('tasks',[])),
                'same_graduate_artifact':a.get('working_analysis',{}).get('artifact')==before,
                'no_unnecessary_population_question':'undergraduate' not in a.get('message','').casefold()})
        run('supported_work_with_unsupported_chart','Convert these student enrollment numbers into percentages and show a 100% stacked bar chart.',grad_counts_history,
            lambda a:{**percent_check(a),'both_parts_accounted_for':{t['status'] for t in a.get('task_tracking',{}).get('tasks',[])}=={'answered','unsupported'}})
    print('Saved',target,flush=True)

if __name__=='__main__':main()

