"""Paired live model comparison through the current Claude-first app pipeline."""
from pathlib import Path
from copy import deepcopy
from contextvars import ContextVar
from concurrent.futures import ThreadPoolExecutor
from threading import RLock,Event
from unittest.mock import patch
import datetime,json,math,statistics,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.agent import MODEL_LABELS,usage_cost
from prototype.api_client import get_client
from prototype.intent_router import handle,charts_context
from prototype.institution_confirmation import ask
from prototype.analytics import Plan,execute
from prototype.responses import finalize_answer
from prototype.catalog import annual_path,readonly

MODELS=list(MODEL_LABELS);CASE=ContextVar('model_comparison_case',default='unassigned')
LOCK=RLock();CALLS=[];RECORDS=[];START=time.perf_counter();MAX_USD=5
STOP=Event();STOP_REASON='';BLOCKED_ATTEMPTS=[]
TARGET=ROOT/'evaluations/model_comparison_current.json'
CASES=[
 ('greeting','conversation','Hello!','none'),
 ('definition','definition','What does admission rate mean in the 2024-25 release?','none'),
 ('discovery','discovery','What information do you have on faculty?','none'),
 ('admissions','numerical',"Show Yale University's applicants, admits, and admission rate in fall 2024.",'none'),
 ('yield_followup','followup','How many matriculated that fall, and what was the yield rate?','admissions'),
 ('cohort_trend','numerical',"Plot Yale University's six-year bachelor's graduation rate for entering cohorts 2009 through 2018.",'none'),
 ('services','categorical','In the 2024-25 release, does Smith College offer academic/career counseling, employment services for current students, and on-campus childcare? Report each source response.','none'),
 ('ma_distance','categorical','Which degree-granting institutions in Massachusetts offer distance education in 2024-25? Use the institutional yes/no response, not enrollment counts.','none'),
 ('axis_reset','chart_edit','reset x-axis range to 0-10','chart'),
 ('compound_style','chart_edit',"Make Harvard red, move the legend to the bottom, set the font size to 18, and set the title to 'Admissions, and show table'.",'chart'),
 ('ambiguous_aid','clarification','What percentage of Yale College students were on financial aid in 2024?','none'),
 ('weighted_salary','calculation',"For Yale University, calculate the weighted average nine-month salary of full-time nonmedical instructional staff across professor, associate professor and assistant professor ranks in the 2024-25 release. Weight each rank's nine-month average salary by its nine-month staff count. Exclude all other ranks and the all-ranks total.",'none'),
 ('mixed','mixed','Compare Yale University and Harvard University admission rates in fall 2024 and make the bars blue.','none')]

def sql(year,query):
    with readonly(annual_path(year)) as db:return [tuple(r) for r in db.execute(query)]

def fixtures():
    admissions=finalize_answer({'intent':'analyze','result':execute(Plan(['applicants','admits','admission_rate'],['Yale'],[2024]))})
    chart=finalize_answer({'intent':'analyze','result':execute(Plan(['admission_rate'],['Ivy League'],[2024]))})
    seeds={'none':[],'admissions':[{'question':CASES[3][2],'answer':admissions}],
           'chart':[{'question':'Compare Ivy League admission rates in fall 2024.','answer':chart}]}
    charts_context(seeds['chart'])
    applicants,admits,enrolled=sql(2024,'SELECT APPLCN,ADMSSN,ENRLT FROM ADM2024 WHERE UNITID=130794')[0]
    expected={'admissions':[applicants,admits,100*admits/applicants],
              'yield_followup':[enrolled,100*enrolled/admits],
              'cohort_trend':{year:sql(year,f'SELECT 100.0*n.GRTOTLT/d.GRTOTLT FROM GR{year} n JOIN GR{year} d USING(UNITID) WHERE n.UNITID=130794 AND n.GRTYPE=12 AND d.GRTYPE=8')[0][0] for year in range(2015,2025)},
              'services':dict(zip(['STUSRV2','STUSRV3','STUSRV8'],sql(2024,'SELECT STUSRV2,STUSRV3,STUSRV8 FROM IC2024 WHERE UNITID=167835')[0])),
              'ma_distance':{r[0] for r in sql(2024,"SELECT h.UNITID FROM HD2024 h JOIN IC2024 i USING(UNITID) WHERE h.STABBR='MA' AND h.DEGGRANT=1 AND i.DISTCRS=1")},
              'weighted_salary':sql(2024,'SELECT SUM(1.0*SA09MAT*SA09MCT)/SUM(SA09MCT) FROM SAL2024_IS WHERE UNITID=130794 AND ARANK IN (1,2,3)')[0][0],
              'mixed':{r[0]:100*r[2]/r[1] for r in sql(2024,'SELECT UNITID,APPLCN,ADMSSN FROM ADM2024 WHERE UNITID IN (130794,166027)')}}
    return seeds,expected

def numbers(rows):return sorted(float(r['value']) for r in rows if r.get('value') is not None and r.get('status')=='ok')

def color_is(value,name):
    return isinstance(value,str) and value.casefold() in {name,{'red':'#ff0000','blue':'#0000ff'}[name]}

def yield_values_match(rows,expected):
    # The prompt does not forbid showing the verified admitted denominator.
    required=[r for r in rows if r.get('metric') in {'matriculants','yield_rate'}] if len(rows)==3 else rows
    extra=[r for r in rows if r not in required]
    return (len(required)==2 and close_values(numbers(required),expected['yield_followup'])
        and len(extra)<=1 and all(r.get('metric')=='admits' and r.get('status')=='ok'
            and r.get('value') is not None and math.isclose(r['value'],expected['admissions'][1],rel_tol=1e-8) for r in extra))
def close_values(a,b):
    a=sorted(a);b=sorted(b)
    return len(a)==len(b) and all(math.isclose(x,y,rel_tol=1e-8,abs_tol=1e-8) for x,y in zip(a,b))

def check(label,answer,history,expected):
    result=answer.get('result',{});rows=result.get('rows',[]);p=answer.get('presentation',{})
    checks={}
    if label=='greeting':checks={'conversation':answer.get('intent')=='conversation','no_statistics':not result}
    elif label=='definition':
        lookup=answer.get('definition_lookup',{})
        checks={'definition':answer.get('intent')=='definition','source_passages':bool(answer.get('evidence')),
                'correct_measure':lookup.get('reviewed_measure')=='admission_rate','release':lookup.get('source_years')==[2024]}
    elif label=='discovery':checks={'discovery':answer.get('mode')=='data discovery','topics':bool(answer.get('discovery',{}).get('topics')),'evidence':bool(answer.get('evidence'))}
    elif label in {'admissions','yield_followup'}:
        checks={'exact_values':close_values(numbers(rows),expected[label]),'complete_rows':len(rows)==len(expected[label]),
                'scope':bool(rows) and all(r['unitid']==130794 and r['observation_year']==2024 for r in rows)}
        if label=='yield_followup' and len(rows)==3 and yield_values_match(rows,expected):
            checks.update(exact_values=True,complete_rows=True)
    elif label=='cohort_trend':
        checks={'ten_rates':len(rows)==10,'scope':bool(rows) and all(r['unitid']==130794 and r['observation_year'] in expected[label] for r in rows),
                'values':len(rows)==10 and all(r.get('value') is not None and math.isclose(r['value'],expected[label].get(r['observation_year'],-1),rel_tol=1e-8) for r in rows)}
    elif label=='services':
        codes={r['metric'].split('::')[-1]:r.get('raw_code') for r in rows}
        checks={'typed':result.get('result_schema_version')==2,'three_responses':len(rows)==3,
                'exact_codes':set(codes)==set(expected[label]) and all(str(codes[k])==str(v) for k,v in expected[label].items()),
                'scope':bool(rows) and all(r['unitid']==167835 and r['observation_year']==2024 and r['value'] is None for r in rows)}
    elif label=='ma_distance':checks={'typed':result.get('result_schema_version')==2,'exact_institution_set':{r['unitid'] for r in rows}==expected[label],
                                    'release':bool(rows) and all(r['observation_year']==2024 for r in rows)}
    elif label in {'axis_reset','compound_style'}:
        previous=history[-1]['answer']['result']
        checks={'presentation_only':answer.get('mode')=='presentation adjustment','same_result':result is previous}
        if label=='axis_reset':checks['range']=[p.get('y_min'),p.get('y_max')]==[0,10]
        else:checks.update(color=color_is(p.get('series_colors',{}).get('Harvard University'),'red'),legend=p.get('legend')=='bottom',
                           font=p.get('font_size')==18,title=p.get('title')=='Admissions, and show table',table_unchanged=p.get('show_table')==history[-1]['answer']['presentation']['show_table'])
    elif label=='ambiguous_aid':
        message=answer.get('message','').lower()
        checks={'safe_clarification':answer.get('intent') in {'clarify','institution_confirmation'} and not result,
                'relevant_ambiguity':any(w in message for w in ['aid','grant','loan','college','reporting']) and not any(w in message for w in ['response limit','invalid schema','network','could not finish'])}
    elif label=='weighted_salary':checks={'one_value':len(rows)==1,'exact_weighted_mean':close_values(numbers(rows),[expected[label]]),'release':bool(rows) and rows[0]['observation_year']==2024}
    elif label=='mixed':checks={'two_institutions':{r['unitid'] for r in rows}==set(expected[label]),'values':len(rows)==2 and all(r['observation_year']==2024 and math.isclose(r['value'],expected[label].get(r['unitid'],-1),rel_tol=1e-8) for r in rows),'blue':color_is(p.get('color'),'blue')}
    return checks

def save():
    with LOCK:
        total=sum(c.get('estimated_api_usd',0) or 0 for c in CALLS)
        report={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':f'Two paired passes of {len(CASES)} predeclared tasks per model through current handle/executors. Standardized independent seed histories. Direct SQLite correctness checks. Warmup excluded from task latency but included in spend. Models use existing app settings, not equalized reasoning effort. No app defaults changed.',
                'expected_tasks_per_model':2*len(CASES),'estimated_spend_including_warmup':total,'elapsed_seconds':time.perf_counter()-START,'cases':RECORDS,'calls':CALLS,'models':[],
                'stop_reason':STOP_REASON,'previous_unavailable_attempts':BLOCKED_ATTEMPTS}
        for model in MODELS:
            attempted=[c for c in RECORDS if c['model']==model]
            cases=[c for c in attempted if c.get('usage_complete')]
            times=[c['wall_seconds'] for c in cases]
            costs=[c['estimated_api_usd'] or 0 for c in cases]
            report['models'].append({'model':model,'passed':sum(c['passed'] for c in cases),'total':len(cases),'attempted':len(attempted),'unavailable':len(attempted)-len(cases),
                'median_seconds':statistics.median(times) if times else None,'total_task_seconds':sum(times),'estimated_task_usd':sum(costs),
                'by_group':{group:{'passed':sum(c['passed'] for c in cases if c['group']==group),'total':sum(c['group']==group for c in cases),
                                  'median_seconds':statistics.median([c['wall_seconds'] for c in cases if c['group']==group])} for group in sorted({c['group'] for c in cases})}})
        TARGET.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')

def main():
    global STOP_REASON
    if '--live' not in sys.argv:raise SystemExit('Pass --live for the paired provider benchmark.')
    if '--resume' in sys.argv and TARGET.exists():
        prior=json.loads(TARGET.read_text(encoding='utf-8'))
        BLOCKED_ATTEMPTS.extend(prior.get('previous_unavailable_attempts',[]))
        for record in prior['cases']:
            (RECORDS if record.get('usage_complete',True) else BLOCKED_ATTEMPTS).append(record)
        completed={r['case_id'] for r in RECORDS}
        CALLS.extend(c for c in prior['calls'] if c['case_id'] in completed or c['case_id'].startswith('warmup:'))
    print('Preparing standardized seed results and independent SQLite expectations.',flush=True)
    seeds,expected=fixtures();client=get_client();original=client.messages.create
    def metered(*args,**kwargs):
        global STOP_REASON
        started=time.perf_counter();model=kwargs.get('model');entry={'case_id':CASE.get(),'model':model}
        try:
            if STOP.is_set():raise RuntimeError('Live benchmark stopped: '+STOP_REASON)
            response=original(*args,**kwargs)
            usage={k:getattr(response.usage,k,0) or 0 for k in ['input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens']}
            entry.update(usage,estimated_api_usd=usage_cost(model,usage),status='ok')
            return response
        except Exception as exc:
            if 'specified API usage limits' in str(exc):
                STOP_REASON='Anthropic account usage limit reached; remaining tasks are unavailable, not model failures.';STOP.set()
            entry.update(status='error',error_type=type(exc).__name__,estimated_api_usd=None);raise
        finally:
            entry['seconds']=time.perf_counter()-started
            with LOCK:CALLS.append(entry)
    def run(model,round_number,case):
        label,group,question,seed=case;case_id=f'{round_number}:{label}:{model}'
        if any(r['case_id']==case_id for r in RECORDS):return
        history=deepcopy(seeds[seed]);before=deepcopy(history);previous=history[-1]['answer'] if history else None
        token=CASE.set(case_id);started=time.perf_counter();record={'model':model,'round':round_number,'case':label,'group':group,'question':question,'case_id':case_id}
        try:
            a=handle(question,previous,model,history,ask)
            if a.get('result') and a.get('mode')!='presentation adjustment':a=finalize_answer(a,question)
            checks=check(label,a,history,expected);checks['seed_unchanged']=history==before
            result=a.get('result',{})
            record.update(passed=all(checks.values()),checks=checks,intent=a.get('intent'),mode=a.get('mode'),message=a.get('message','')[:2500],
                interpretation=a.get('intent_interpretation'),presentation=a.get('presentation'),
                model_policy=a.get('model_policy'),reported_usage=a.get('model_usage'),
                rows=[{k:r.get(k) for k in ['unitid','observation_year','entry_cohort_year','metric','value','raw_code','response_label','status']} for r in result.get('rows',[])],
                narrative_status=a.get('discovery_narrative',{}).get('status'),latency=a.get('latency'),
                narrative_reason=a.get('discovery_narrative',{}).get('reason'),plan=a.get('catalog_plan') or a.get('observation_plan') or a.get('plan'))
        except Exception as exc:record.update(passed=False,error_type=type(exc).__name__,error=str(exc)[:500])
        finally:CASE.reset(token)
        record['wall_seconds']=round(time.perf_counter()-started,3)
        with LOCK:
            calls=[c for c in CALLS if c['case_id']==case_id]
            record['model_calls']=len(calls);record['estimated_api_usd']=sum(c.get('estimated_api_usd',0) or 0 for c in calls)
            record['usage_complete']=all(c['status']=='ok' for c in calls);RECORDS.append(record);save()
        print(json.dumps({k:record[k] for k in ['model','round','case','passed','wall_seconds','model_calls','estimated_api_usd']}),flush=True)
    with patch.object(client.messages,'create',side_effect=metered):
        from prototype.intent_router import interpret
        for model in MODELS:
            if STOP.is_set():break
            token=CASE.set('warmup:'+model)
            try:interpret('Hello',[],'claude-haiku-5-5' if model=='automatic' else model);print('Warmed '+model,flush=True)
            except Exception:
                if not STOP.is_set():raise
            finally:CASE.reset(token)
        with ThreadPoolExecutor(max_workers=2) as pool:
            for round_number in [1,2]:
                for index,case in enumerate(CASES):
                    if STOP.is_set():save();return 2
                    if sum(c.get('estimated_api_usd',0) or 0 for c in CALLS)>=MAX_USD:
                        save();raise SystemExit('Stopped at the estimated provider-spend cap; results are incomplete.')
                    order=MODELS if (round_number+index)%2 else MODELS[::-1]
                    list(pool.map(lambda model:run(model,round_number,case),order))
    save();return 0

if __name__=='__main__':raise SystemExit(main())
