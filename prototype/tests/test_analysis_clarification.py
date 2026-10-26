from copy import deepcopy
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch,MagicMock
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.tests.test_query_engine import source,plan,field_ref
from prototype.tests.test_catalog_planner import block,response
from prototype.conversation import prepare,select
from prototype.agent import ask
from prototype.conversation import context
from prototype.catalog import readonly,annual_path


class ClarificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        s,d=source('EF2024',fields=['EFTOTAL','EFWOM'],filters={'EFLEVEL':'20'})
        cls.payload={'question':'Which enrollment population do you mean?','goal':'Understand undergraduate enrollment at Yale.',
            'options':[{'id':i,'label':label,'interpretation':'Show '+label+' at Yale in Fall 2024.',
                'qualifications':['Fall headcount; these are enrollment counts.'],
                'plan':plan([s],[(field_ref(d[f],'s'),label)])}
                for i,f,label in [('A','EFTOTAL','All undergraduates'),('B','EFWOM','Women undergraduates')]]}
        cls.tmp=tempfile.TemporaryDirectory()
        cls.storage=patch('prototype.catalog_planner.PLAN_DIR',Path(cls.tmp.name));cls.storage.start()
    @classmethod
    def tearDownClass(cls):cls.storage.stop();cls.tmp.cleanup()

    def history(self):
        return [{'question':'How many students at Yale?', 'answer':prepare(deepcopy(self.payload),'How many students at Yale?')}]

    def test_offering_options_never_queries_statistical_values(self):
        with patch('prototype.query_engine.execute',side_effect=AssertionError('No values before selection')):
            a=self.history()[0]['answer']
        self.assertEqual(a['analysis_brief']['status'],'pending')
        self.assertTrue(a['analysis_brief']['options'][0]['evidence']['definitions'])

    def test_invalid_option_is_not_offered(self):
        payload=deepcopy(self.payload);payload['options'][1]['plan']['outputs'][0]['reference']='invented'
        with self.assertRaises(ValueError):prepare(payload,'Yale enrollment')

    def test_choices_cannot_change_institution_scope(self):
        payload=deepcopy(self.payload);payload['options'][1]['plan']['institutions']=['Harvard']
        with self.assertRaisesRegex(ValueError,'scopes identical'):prepare(payload,'Enrollment')

    def test_exact_letters_ordinals_and_labels(self):
        h=self.history()
        for text,expected in [('A','A'),('(a)','A'),('option B','B'),('2','B'),('the second one','B'),('use A','A')]:
            self.assertEqual(select(text,h)[1]['id'],expected)
        self.assertIsNone(select('A, but only first-year students',h))
        self.assertIsNone(select('Show Harvard tuition',h))

    def test_selected_plan_runs_without_llm_or_replanning(self):
        with patch('prototype.conversation.resolve',side_effect=AssertionError('No resolver')),patch('prototype.agent._answer',side_effect=AssertionError('No replanning')):
            a=ask('A',conversation=self.history(),use_model=True)
        with readonly(annual_path(2024)) as db:expected=db.execute('SELECT EFTOTAL FROM EF2024 WHERE UNITID=130794 AND EFLEVEL=20').fetchone()[0]
        self.assertEqual(a['intent'],'analyze');self.assertEqual(a['result']['rows'][0]['value'],float(expected))
        self.assertEqual(a['analysis_brief']['status'],'completed')
        self.assertEqual(a['model_usage']['calls'],0)
        self.assertIn('Fall headcount',a['message'])

    def test_outer_identity_guard_skips_model_for_selection(self):
        from prototype.institution_confirmation import ask as outer
        h=self.history();h[0]['answer']['institution_identity']={'unitids':[130794],'confirmed_choices':{},'labels':['Yale University']}
        with patch('prototype.institution_confirmation.mentions',side_effect=AssertionError('No mention call')):
            a=outer('A',conversation=h,use_model=True)
        self.assertEqual(a['institution_identity']['unitids'],[130794]);self.assertIn('result',a)

    def test_failed_execution_keeps_choice_for_retry(self):
        h=self.history()
        with patch('prototype.query_engine.execute_answer',return_value={'intent':'clarify','message':'Runtime grain failed.'}):a=ask('B',conversation=h)
        h.append({'question':'B','answer':a})
        self.assertEqual(a['analysis_brief']['selected_option'],'B');self.assertEqual(a['analysis_brief']['status'],'failed')
        retry=ask('try again',conversation=h)
        with readonly(annual_path(2024)) as db:expected=db.execute('SELECT EFWOM FROM EF2024 WHERE UNITID=130794 AND EFLEVEL=20').fetchone()[0]
        self.assertEqual(retry['analysis_brief']['status'],'completed');self.assertEqual(retry['result']['rows'][0]['value'],float(expected))

    def test_separate_populations_are_executed_as_separate_panels(self):
        payload=deepcopy(self.payload)
        payload['options'][0]['additional_analyses']=[{k:v for k,v in payload['options'][1].items() if k!='id'}]
        a=ask('A',conversation=[{'question':'Enrollment','answer':prepare(payload,'Enrollment')}])
        self.assertEqual(len(a['related_analyses']),1)
        self.assertIn('Women',a['related_analyses'][0]['result']['rows'][0]['measure'])
        self.assertNotIn('plan',context([{'question':'A','answer':a}])['analysis_brief']['options'][0])

    def test_no_partial_publication_if_one_panel_fails(self):
        payload=deepcopy(self.payload)
        payload['options'][0]['additional_analyses']=[{k:v for k,v in payload['options'][1].items() if k!='id'}]
        h=[{'question':'Enrollment','answer':prepare(payload,'Enrollment')}]
        with patch('prototype.query_engine.execute_answer',side_effect=[{'result':{'rows':[]}}, {'intent':'clarify','message':'Second panel failed.'}]):a=ask('A',conversation=h)
        self.assertNotIn('result',a);self.assertEqual(a['analysis_brief']['status'],'failed')

    def test_confirmed_bundle_finishes_without_reasking_or_double_query(self):
        from prototype.conversation import prepare_bundle
        from prototype.agent import _answer
        s,d=source('S2024_SIS',fields=['SISPROF'],filters={'FACSTAT':['20','30']},aggregates=[('count','sum','SISPROF',None)])
        p=plan([s],[('as_count','Ladder professors')],institutions=['130493'])
        sal,sd=source('SAL2024_IS',sid='salary',fields=['SAEQ9AT'],filters={'ARANK':'1'})
        ps=plan([sal],[(field_ref(sd['SAEQ9AT'],'salary'),'All instructional professor salary')],institutions=['130493'])
        analyses=[{'label':'Ladder professors','interpretation':'Southern Connecticut State University ladder professors Fall 2024','qualifications':[],'plan':p},
            {'label':'Contextual salary','interpretation':'Southern Connecticut State University professor salary academic year 2024-25','qualifications':['This salary covers all full-time nonmedical professors.'],'plan':ps}]
        question='Southern Connecticut State University ladder professors Fall 2024 and contextual salary academic year 2024-25'
        prepared=prepare_bundle({'goal':'Counts and contextual salaries','analyses':analyses},question)
        from prototype.query_engine import execute
        with patch('prototype.agent._ask',return_value=prepared),patch('prototype.query_engine.execute',wraps=execute) as executor:
            a=_answer(question)
        self.assertEqual(executor.call_count,2)
        self.assertEqual(a['analysis_brief']['status'],'completed');self.assertEqual(len(a['related_analyses']),1)
        self.assertEqual(a['result']['rows'][0]['value'],192)
        self.assertEqual(a['related_analyses'][0]['result']['rows'][0]['value'],115453)

    def test_bare_coverage_period_uses_matching_source_title_only(self):
        from prototype.query_engine import period_set
        table={'period_evidence':[{'year_coverage':'2024-25'}], 'population_evidence':[{'title':'Salary: Academic year 2024-25'}]}
        self.assertEqual(period_set(table)[0]['kind'],'academic')
        table['population_evidence'][0]['title']='Salary: Academic year 2023-24'
        self.assertEqual(period_set(table)[0]['kind'],'reporting')

    def test_wide_staff_rank_count_units_and_disjoint_sum(self):
        from prototype.query_engine import execute,aggregate_ref
        s,d=source('S2024_SIS',fields=['SISPROF'],filters={'FACSTAT':['20','30']},aggregates=[('count','sum','SISPROF',None)])
        p=plan([s],[(aggregate_ref('s','count'),'Tenured plus tenure-track professors')],institutions=['130493'])
        result=execute(p,'Southern Connecticut State University tenured plus tenure-track professors Fall 2024')
        self.assertEqual(result['rows'][0]['unit'],'employees')
        self.assertEqual(result['rows'][0]['value'],192)
        from prototype.semantics import describe_field
        fake={'record_id':1,'release_id':'x','table_name':'x','variable_name':'x','title':'Professors','long_description':'Academic rank','format':'Cont','data_type':'N'}
        self.assertEqual(describe_field(fake,{'population_evidence':[{'record_id':2,'description':'Salaries of instructional staff by rank'}]})['unit'],'unknown')

    def test_invalid_choice_preserves_pending(self):
        a=ask('C',conversation=self.history(),use_model=True)
        self.assertEqual(a['intent'],'clarify');self.assertEqual(a['analysis_brief']['status'],'pending')

    def test_modified_reply_uses_brief_and_invalidates_old_plan(self):
        h=self.history()
        resolved={'kind':'followup','question':'Show Yale women first-year undergraduates in Fall 2024.','referenced_turns':[1]}
        with patch('prototype.conversation.resolve',return_value=(resolved,{'calls':1,'latency_seconds':.1})),patch('prototype.agent._answer',return_value={'intent':'clarify','message':'Planning limit'}) as planner:
            a=ask('B, but only first-year students',conversation=h,use_model=True)
        self.assertEqual(planner.call_args.args[0],resolved['question'])
        self.assertEqual(a['analysis_brief']['status'],'revising')
        self.assertIsNone(select('retry',[{'question':'modified','answer':a}]))
        b=context(h)['analysis_brief'];self.assertEqual(len(b['options']),2);self.assertNotIn('plan',b['options'][0])

    def test_new_topic_discards_pending(self):
        with patch('prototype.conversation.resolve',return_value=({'kind':'new','question':'Harvard tuition 2024','referenced_turns':[]},{'calls':1,'latency_seconds':.1})),patch('prototype.agent._answer',return_value={'intent':'clarify','message':'New task'}):
            a=ask('Harvard tuition 2024',conversation=self.history(),use_model=True)
        self.assertEqual(a['analysis_brief']['original_question'],'Harvard tuition 2024')
        self.assertEqual(a['analysis_brief']['options'],[])

    def test_model_tool_options_are_preflighted(self):
        from prototype.catalog_planner import model_catalog_plan
        with patch('anthropic.Anthropic') as cls:
            client=MagicMock();cls.return_value=client
            client.messages.create.return_value=response(block('offer_analysis_options',deepcopy(self.payload),'choices'))
            a=model_catalog_plan('Yale enrollment Fall 2024')
        self.assertEqual(a['analysis_brief']['status'],'pending')
        self.assertEqual(a['model_usage']['calls'],1)

    def test_ui_buttons_submit_saved_choice_and_clear_removes_brief(self):
        from streamlit.testing.v1 import AppTest
        def app():
            import streamlit as st
            from prototype.ui import render_answer,clear_conversation
            st.session_state.setdefault('ideas_epoch',0);st.session_state.setdefault('transcript_revision',0)
            if st.session_state.history:render_answer(st.session_state.history[-1]['answer'],'pending')
            st.button('Clear',key='clear',on_click=clear_conversation)
        app=AppTest.from_function(app,default_timeout=30)
        app.session_state['history']=self.history()
        app.run();self.assertFalse(app.exception)
        app.button(key='pending_choice_A').click().run()
        self.assertEqual(app.session_state['pending_action']['question'],'A')
        app.button(key='clear').click().run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state['history'],[])


if __name__=='__main__':unittest.main()
