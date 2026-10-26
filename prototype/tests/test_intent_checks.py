"""Independent intent, execution and display checks, including conversation chains."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
from contextlib import contextmanager
import json,sys,time,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.intent_checks import CURRENT,contract,check_plan,check_result,IntentMismatch,stamp
from prototype.analytics import Plan,execute
from prototype.responses import finalize_answer
from prototype.agent import ask
from prototype.memory import context

@contextmanager
def request(q,history=None,resolved=None):
    token=CURRENT.set(contract(q,resolved,context(history or [])))
    try:yield
    finally:CURRENT.reset(token)

def cached_view(result):
    from prototype.components import render_result
    render_result(result,'cached',compact=True)

class IntentCheckTests(unittest.TestCase):
    def test_confirmed_executor_aliases_survive_scope_validation(self):
        from prototype.intent_checks import _ids
        from prototype.institution_confirmation import AUTHORIZED
        token=AUTHORIZED.set({217156,190150})
        try:self.assertEqual(_ids(['Brown','Columbia']),[190150,217156])
        finally:AUTHORIZED.reset(token)
        token=AUTHORIZED.set(set())
        try:self.assertEqual(_ids(['Brown','Columbia']),[])
        finally:AUTHORIZED.reset(token)


    @classmethod
    def setUpClass(cls):
        cls.plan=Plan(['total_enrollment'],['166939'],list(range(2015,2025)),output='chart')
        cls.result=execute(cls.plan)

    def test_original_interval_survives_bad_context_rewrite(self):
        old={'question':'Total enrollment for 166939 in 2024','answer':{'plan':{**self.result['plan'],'years':[2024]}}}
        c=contract('Show a 10-year trend.','Total enrollment for 166939 in 2024',context([old]))
        self.assertEqual(c['expected_years'],list(range(2015,2025)))
        with request('Show a 10-year trend.',[old]):
            with self.assertRaises(IntentMismatch):check_plan({**self.result['plan'],'years':[2024]})
            self.assertIsNotNone(check_plan(self.result['plan']))
        with patch('prototype.intent_checks.trend_years',return_value=list(range(2016,2025))):
            c=contract('Show a 10-year trend for 166939')
        token=CURRENT.set(c)
        try:
            with self.assertRaisesRegex(IntentMismatch,'number'):check_plan({**self.result['plan'],'years':list(range(2016,2025))})
        finally:CURRENT.reset(token)

    def test_pre_execution_rejects_missing_institutions_measures_and_percentages(self):
        from prototype.catalog import IVY
        self.assertEqual(contract('Compare Ivy League enrollment in 2024')['unitids'],sorted(IVY))
        self.assertEqual(contract('Compare Ivy League except 130794 in 2024')['unitids'],sorted(set(IVY)-{130794}))
        from prototype.institution_confirmation import AUTHORIZED
        token=AUTHORIZED.set({130794})
        try:self.assertEqual(contract('Awards for 130794 in CIP program 513801 in 2024')['unitids'],[130794])
        finally:AUTHORIZED.reset(token)
        for q,plan in [
            ('Compare total enrollment for 166939 and 167835 in 2024',Plan(['total_enrollment'],['166939'],[2024])),
            ('Total enrollment for 166939 in 2024',Plan(['total_enrollment'],['166939','167835'],[2024])),
            ('Undergraduate enrollment for 166939 in 2024',Plan(['graduate_enrollment'],['166939'],[2024])),
            ('Show percentages for undergraduate enrollment at 166939 in 2024',Plan(['undergraduate_enrollment'],['166939'],[2024])),
            ('Show undergraduate enrollment by gender for 166939 in 2024',Plan(['undergraduate_enrollment'],['166939'],[2024]))]:
            with request(q),patch('prototype.analytics.compile_query',side_effect=AssertionError('Must stop before fact SQL')):
                with self.assertRaises(IntentMismatch,msg=q):execute(plan)

    def test_catalog_breakdown_uses_real_source_titles_not_labels(self):
        from prototype.catalog_planner import enrollment_gender_plan
        from prototype.catalog_execution import execute_catalog,prepare_catalog_proposal
        q='Show Yale undergraduate enrollment by gender in fall 2024'
        a=enrollment_gender_plan(q);p=deepcopy(a['catalog_plan'])
        # Remove the actual women field; adding the word women to assumptions cannot satisfy the check.
        defs={d['record_id']:d for d in a['catalog_proposal']['definition_evidence']}
        p['selections']=[s for s in p['selections'] if defs[s['record_id']]['variable_name']!='EFTOTLW']
        p['assumptions'].append('Women and men are included')
        with request(q),patch('prototype.catalog_execution.quoted',side_effect=AssertionError('Must stop before fact SQL')):
            with self.assertRaises(IntentMismatch):execute_catalog({**a,'catalog_plan':p},q)
        from prototype.tests.test_query_engine import source
        first,_=source('EF2024A',fields=['EFTOTLM','EFTOTLW','EFTOTLT'],filters={'EFALEVEL':'4'})
        p=deepcopy(a['catalog_plan']);p['filters']=first['filters']
        evidence=prepare_catalog_proposal(p,q)
        with request(q),patch('prototype.catalog_execution.quoted',side_effect=AssertionError('Must stop before fact SQL')):
            with self.assertRaisesRegex(IntentMismatch,'first-time'):check_plan(p,q,evidence)
            self.assertNotIn('result',execute_catalog({**a,'catalog_plan':p},q))

    def test_result_checks_real_periods_and_retains_missing_observations(self):
        c=contract('Show a 10-year trend of total enrollment for 166939')
        r=deepcopy(self.result);r['rows']=r['rows'][-1:]
        with self.assertRaisesRegex(IntentMismatch,'Only one'):check_result(r,c)
        r=deepcopy(self.result);r['rows']=r['rows'][1:]
        with self.assertRaisesRegex(IntentMismatch,'interval|number'):check_result(r,c)
        r=deepcopy(self.result)
        for row in r['rows'][:-1]:row.update(value=None,status='missing')
        before=deepcopy(r);warnings=check_result(r,c)
        self.assertEqual(r,before);self.assertIn('cannot be assessed',warnings[0])
        both=execute(Plan(['total_enrollment'],['166939','167835'],list(range(2015,2025)),output='chart'))
        both['rows']=[r for r in both['rows'] if not (r['unitid']==166939 and r['observation_year']==2015)]
        with self.assertRaisesRegex(IntentMismatch,'institution is missing'):check_result(both,contract('10-year trend for 166939 and 167835'))

    def test_saved_result_guard_stops_chart_table_and_downloads(self):
        from streamlit.testing.v1 import AppTest
        r=deepcopy(self.result)
        stamp(r,{'contract':contract('Show a 10-year trend of total enrollment for 166939'),'plan_checks':['test']})
        r['rows']=r['rows'][-1:]
        app=AppTest.from_function(cached_view,args=(r,),default_timeout=60).run()
        self.assertFalse(app.exception);self.assertTrue(app.warning)
        self.assertFalse(app.get('vega_lite_chart'));self.assertFalse(app.dataframe);self.assertFalse(app.get('download_button'))

    def test_semantic_failure_clarifies_and_context_does_not_leak(self):
        old={'question':'Total enrollment for 166939 in 2024','answer':{'plan':{**self.result['plan'],'years':[2024]}}}
        rewritten={'kind':'followup','question':'Total enrollment for 166939 in 2024','referenced_turns':[1]}
        with patch('prototype.memory.resolve',return_value=(rewritten,{'calls':1,'latency_seconds':.01})),patch('prototype.agent.model_plan',return_value={'intent':'analyze','plan':old['answer']['plan']}),patch('prototype.analytics.compile_query',side_effect=AssertionError('No fact SQL')):
            a=ask('Show a 10-year trend.',use_model=True,conversation=[old])
        self.assertEqual(a['intent'],'clarify');self.assertNotIn('result',a);self.assertEqual(a['mode'],'intent validation')
        self.assertIsNone(CURRENT.get())

    def test_period_and_cohort_semantics_and_percentile_are_preserved(self):
        for q,p in [
            ('Grants in 2014–2015',Plan(['undergraduate_grant_percent'],['Yale'],[2015])),
            ('Grants in 2014–15 through 2023–24',Plan(['undergraduate_grant_percent'],['Yale'],list(range(2015,2025)))),
            ('Yale class of 2028 entering fall 2024 applicants',Plan(['applicants'],['Yale'],[2024])),
            ('Yale students who started in 2009 six-year graduation rate',Plan(['graduation_rate'],['Yale'],[2009],time_basis='entry_cohort')),
            ('Yale SAT 25th percentile in 2024',Plan(['satvr25','satmt25'],['Yale'],[2024]))]:
            with request(q):
                r=execute(p);self.assertEqual(r['intent_validation']['status'],'passed',q)

    def test_conversation_counts_trend_percentages_and_new_topic(self):
        h=[];latencies=[]
        queries=[('Show Yale undergraduate enrollment by gender in fall 2024',None),
                 ('Show a 10-year trend.','Show Yale undergraduate enrollment by gender from fall 2015 through fall 2024'),
                 ('Show percentages','Show Yale undergraduate enrollment by gender as percentages from fall 2015 through fall 2024')]
        for q,standalone in queries:
            start=time.perf_counter()
            with patch('prototype.memory.resolve',return_value=({'kind':'followup','question':standalone,'referenced_turns':[len(h)]},{'calls':1,'latency_seconds':.01})):
                a=ask(q,previous=h[-1]['answer'].get('catalog_plan') if h else None,use_model=True,conversation=h)
            self.assertIn('result',a,a.get('message'));self.assertEqual(a['result']['intent_validation']['status'],'passed')
            h.append({'question':q,'answer':a});latencies.append(time.perf_counter()-start)
        rows=h[-1]['answer']['result']['rows'];self.assertEqual(len({r['observation_year'] for r in rows}),10)
        self.assertEqual({r['unit'] for r in rows},{'percent'})
        # Formatting turns must not become the active analytical topic.
        h.append({'question':'Set chart title to "Gender"','answer':{**h[-1]['answer'],'mode':'presentation adjustment'}})
        self.assertEqual(context(h)['active_analysis']['question'],'Show percentages')
        c=contract('Total enrollment for 167835 in 2024',bundle=context(h))
        self.assertFalse(c['dimensions']);self.assertFalse(c['percentage']);self.assertEqual(c['unitids'],[167835])
        (ROOT/'evaluations/intent_conversation_latency.json').write_text(json.dumps({'scope':'Real local annual data; mocked context-model transport. Not live unfamiliar-question latency.','questions':[q for q,_ in queries],'answer_seconds':latencies},indent=2),encoding='utf-8')

    def test_relational_comparison_and_combined_institutions_remain_valid(self):
        from prototype.tests.test_query_engine import source,plan,expr,join
        from prototype.query_engine import execute as run,field_ref,aggregate_ref
        a,da=source('ADM2015',year=2015,sid='a',fields=['APPLCN'])
        b,db=source('ADM2024',sid='b',fields=['APPLCN'])
        p=plan([a,b],[('xgrowth','Applicant growth')],joins=[join('a','b',period='explicit_comparison')],expressions=[expr('growth','percent_change',[field_ref(db['APPLCN'],'b'),field_ref(da['APPLCN'],'a')])],time_basis='explicit_comparison')
        with request('Percent change in applicants for 130794 from fall 2015 to fall 2024'):
            r=run(p,'Percent change in Yale applicants from fall 2015 to fall 2024')
        self.assertEqual(r['intent_validation']['status'],'passed');self.assertEqual(len(r['rows']),1)
        # Reduction across named institutions legitimately has no per-institution output row.
        s,d=source('ADM2024',fields=['APPLCN'])
        p=plan([s],[('xsum','Applicants combined')],expressions=[expr('sum','sum',[field_ref(d['APPLCN'],'s')])],institutions=['166939','167835'])
        with request('Sum applicants across 166939 and 167835 in 2024'):
            r=run(p,'Sum applicants across Mount Holyoke and Smith in 2024')
        self.assertEqual(r['intent_validation']['status'],'passed');self.assertIsNone(r['rows'][0]['unitid'])
        s,d=source('C2024_A',fields=['CTOTALT'],filters={'CIPCODE':'99','MAJORNUM':'1'},groups=['AWLEVEL'])
        p=plan([s],[(field_ref(d['CTOTALT'],'s'),'Awards')])
        with request('Awards by degree level for 130794 in 2024'):r=run(p,'Yale awards by degree level in 2024')
        self.assertEqual(r['intent_validation']['status'],'passed')

    def test_result_incomplete_summary_is_hidden_before_text(self):
        from streamlit.testing.v1 import AppTest
        def view(answer):
            from prototype.ui import render_answer
            render_answer(answer,'guard')
        r=deepcopy(self.result);stamp(r,{'contract':contract('10-year trend for 166939'),'plan_checks':[]});r['rows']=r['rows'][-1:]
        app=AppTest.from_function(view,args=({'result':r,'message':'Incorrect numerical summary SHOULD_NOT_APPEAR'},),default_timeout=60).run()
        self.assertTrue(app.warning);self.assertFalse(app.exception)
        self.assertFalse(any('SHOULD_NOT_APPEAR' in m.value for m in app.markdown))

    def test_no_guard_context_leak_after_failed_execution(self):
        with request('Show a 10-year trend for 166939'):
            with self.assertRaises(IntentMismatch):execute(Plan(['total_enrollment'],['166939'],[2024]))
        self.assertIsNone(CURRENT.get())
        self.assertEqual(len(execute(Plan(['total_enrollment'],['166939'],[2024]))['rows']),1)

if __name__=='__main__':unittest.main()
