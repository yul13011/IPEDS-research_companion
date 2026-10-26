"""Bounded live checks for year questions across fresh and inherited topics."""
from pathlib import Path
from unittest.mock import patch,Mock
import json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype import intent_router,working_analysis,data_guide
from prototype.api_client import get_client
from prototype.model_policy import AUTOMATIC,HAIKU
from prototype.agent import usage_cost,DEFAULT_MODEL
from prototype.analytics import Plan,execute
from prototype.responses import finalize_answer


def main():
    if '--live' not in sys.argv:raise SystemExit('Pass --live; capped at $0.40 estimated provider spend.')
    client=get_client();original=client.messages.create;calls=[];records=[]
    target=ROOT/'evaluations/year_routing_live.json'
    def create(**kwargs):
        if sum(c['estimated_api_usd'] for c in calls)>=.4:raise RuntimeError('Live acceptance budget reached.')
        response=original(**kwargs)
        usage={k:getattr(response.usage,k,0) or 0 for k in ['input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens']}
        calls.append({'model':kwargs['model'],**usage,'estimated_api_usd':usage_cost(kwargs['model'],usage)})
        return response
    def save():
        target.write_text(json.dumps({'records':records,'calls':calls,'estimated_api_usd':sum(c['estimated_api_usd'] for c in calls)},indent=2),encoding='utf-8')
    def run(label,history,expected,model=AUTOMATIC,question='Which years do you have?'):
        started=time.perf_counter()
        try:
            executor=Mock(side_effect=AssertionError('Availability must not run statistical planning'))
            answer=intent_router.handle(question,working_analysis.recent_result(history),model,history,executor)
            checks={'coverage_route':all(t['route']=='coverage' for t in answer.get('request_plan',{}).get('tasks',[])),
                'coverage_answer':answer.get('coverage',{}).get('available_periods')==expected,
                'no_discovery_dump':not answer.get('discovery'),'no_statistical_planner':not executor.called}
            record={'case':label,'passed':all(checks.values()),'checks':checks,'message':answer.get('message'),
                'request_plan':answer.get('request_plan'),'coverage':answer.get('coverage')}
        except Exception as exc:record={'case':label,'passed':False,'error':str(exc),'error_type':type(exc).__name__}
        record['seconds']=time.perf_counter()-started;records.append(record);save()
        print(json.dumps({k:record.get(k) for k in ['case','passed','checks','message','error','seconds']},ensure_ascii=True),flush=True)
    with patch.object(client.messages,'create',side_effect=create):
        years=list(range(2015,2025))
        run('fresh_automatic',[],years)
        run('after_general_guide',[{'question':'What data do you have?','answer':data_guide.answer()}],years)
        run('after_faculty_guide',[{'question':'What data do you have about faculty?','answer':data_guide.answer('faculty')}],years)
        run('after_legacy_faculty_discovery',[{'question':'What data do you have about faculty?',
            'answer':{'mode':'data discovery','query':'faculty','message':'Human resources source tables and variables.'}}],years)
        run('after_legacy_year_word_search',[{'question':'Which years do you have?',
            'answer':{'mode':'data discovery','query':'years','message':'Unrelated human resources, enrollment and finance tables.'}}],years)
        sat=finalize_answer({'result':execute(Plan(['satvr50'],['Yale'],[2024]))})
        run('bound_sat_median_measure',[{'question':'Yale median SAT reading score in fall 2024','answer':sat}],[2022,2023,2024])
        run('explicit_whole_database_switch',[{'question':'Yale median SAT reading score in fall 2024','answer':sat}],years,
            question='Which years does the whole database cover, regardless of my previous SAT question?')
        run('fresh_sonnet',[],years,DEFAULT_MODEL)
        for label,question,expected in [('detailed_variables','Which source variables describe staff occupational categories?','discovery'),
                ('definition','What does the variable SAOUTLT mean?','definition')]:
            try:
                plan,usage,_=intent_router.interpret(question,[],HAIKU)
                routes=[t['route'] for t in plan['tasks']]
                record={'case':label,'passed':routes==[expected],'routes':routes,'expected':expected,'request_plan':plan}
            except Exception as exc:record={'case':label,'passed':False,'error':str(exc)}
            records.append(record);save();print(json.dumps({k:record.get(k) for k in ['case','passed','routes','expected','error']},ensure_ascii=True),flush=True)
    print(json.dumps({'passed':sum(r['passed'] for r in records),'cases':len(records),'estimated_api_usd':sum(c['estimated_api_usd'] for c in calls)}),flush=True)


if __name__=='__main__':main()
