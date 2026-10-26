"""Catalog planning tests: real metadata, mocked model transport, no live API charges."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import json
import sys
import tempfile
import unittest

BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'.packages'))

from prototype.agent import ask, model_plan, DEFAULT_MODEL
from prototype.catalog_planner import (PLAN_SCHEMA, enrollment_race_plan, validate_proposal,
    proposal_answer, model_catalog_plan, run_catalog_tool, inspect_table, catalogue_scope)
from analysis_catalog.catalog import connection

QUESTION="Show Yale's undergrad population by race and ethnicity"


def block(name,payload,identity='test-tool'):
    value=SimpleNamespace(type='tool_use',name=name,input=payload,id=identity)
    value.model_dump=lambda:{'type':'tool_use','name':name,'input':payload,'id':identity}
    return value


def response(*blocks):
    usage=SimpleNamespace(input_tokens=100,output_tokens=50,cache_creation_input_tokens=0,cache_read_input_tokens=0)
    return SimpleNamespace(content=list(blocks),usage=usage,stop_reason='tool_use')


class CatalogPlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.store=patch('prototype.catalog_planner.PLAN_DIR',Path(cls.tmp.name))
        cls.store.start()
        cls.answer=enrollment_race_plan(QUESTION)
        cls.plan=cls.answer['catalog_plan']
        with connection() as db:
            # A different survey family proves that proposals are not limited to
            # the enrollment acceptance path or the old 36-measure registry.
            row=db.execute('''SELECT d.record_id FROM definitions d JOIN source.variable_docs v USING(record_id)
              WHERE d.release_id='IPEDS_2024-25_Provisional' AND d.table_name='AL2024'
              AND d.physical_status='documented_location_present' AND v.format='Cont' LIMIT 1''').fetchone()
            cls.library_id=row[0]
        cls.library_plan={'version':1,'institutions':['Yale'],'source_years':[2024],
            'requested_time':{'basis':'fiscal','description':'Fiscal year 2024; validate the selected library field definition.'},
            'selections':[{'record_id':cls.library_id,'role':'measure'}],
            'filters':[],'group_by_record_ids':[],'calculations':[],'joins':[],
            'output':'table','assumptions':[],'clarification_questions':[]}

    @classmethod
    def tearDownClass(cls):
        cls.store.stop();cls.tmp.cleanup()

    def test_original_question_uses_catalog_executor(self):
        with patch('prototype.agent.execute',side_effect=AssertionError('Unfamiliar proposals must not execute reviewed SQL')):
            answer=ask(QUESTION)
        self.assertEqual(answer['intent'],'analyze')
        self.assertIn('result',answer)
        proposal=answer['catalog_proposal']
        self.assertTrue(proposal['validation']['execution_approved'])
        names={d['variable_name'] for d in proposal['definition_evidence']}
        self.assertTrue({'EFALEVEL','EFUNKNT','EFNRALT','EFTOTLT','EFASIAT'}<=names)
        self.assertEqual(answer['catalog_plan']['filters'][0]['values'],['2'])
        self.assertEqual(answer['catalog_plan']['source_years'],[2024])
        self.assertTrue(list(Path(self.tmp.name).glob('*.json')))

    def test_reviewed_questions_keep_numerical_route(self):
        with patch('prototype.catalog_planner.plan_catalog_question',side_effect=AssertionError('Keep reviewed route')):
            answer=ask('Yale applicants fall 2024')
        self.assertEqual(answer['result']['rows'][0]['value'],57517)

    def test_known_new_dimensions_route_before_legacy_model(self):
        for q in [QUESTION,'Show Yale tuition in 2024','Show Yale faculty salaries in 2024',
                  'Yale undergraduate full-time enrollment by gender in 2024','Yale four-year graduation rate']:
            self.assertTrue(catalogue_scope(q))
            with patch('prototype.agent.model_plan',side_effect=AssertionError('Do not reduce new scope to old measures')):
                with patch('prototype.catalog_planner.plan_catalog_question',return_value={'intent':'catalog_plan','message':'proposal'}) as planner:
                    ask(q,use_model=True)
            self.assertEqual(planner.call_args.args[0],q)

    def test_unknown_new_question_can_leave_registry_router(self):
        action={'intent':'catalog','message':'Need source evidence','query':'class size'}
        with patch('prototype.agent.model_plan',return_value=action):
            with patch('prototype.catalog_planner.plan_catalog_question',return_value={'intent':'catalog_discovery','message':'source evidence'}) as planner:
                answer=ask('Show Yale average class size for 2024',use_model=True)
        self.assertEqual(answer['intent'],'catalog_discovery');self.assertEqual(planner.call_count,1)

    def test_percentage_has_explicit_denominators_and_no_regrouping(self):
        answer=enrollment_race_plan(QUESTION+' as percentages in 2023')
        plan=answer['catalog_plan']
        self.assertEqual(plan['source_years'],[2023])
        self.assertEqual(len(plan['calculations']),9)
        self.assertTrue(all(c['operator']=='percent' and c['denominator_record_id'] for c in plan['calculations']))
        self.assertFalse(answer['catalog_proposal']['validation']['execution_approved'])

    def test_starter_does_not_silently_drop_extra_scope(self):
        for suffix in [' excluding unknown race',' for full-time students',' for women only',
                       ' for entering cohort 2018',' and tuition',' in academic year 2023–24',
                       ' by household income',' among students with disabilities']:
            self.assertIsNone(enrollment_race_plan(QUESTION+suffix),suffix)
        self.assertEqual(enrollment_race_plan(QUESTION+' in 2025')['intent'],'clarify')
        self.assertEqual(enrollment_race_plan('Show undergrad population by race')['intent'],'clarify')

    def test_all_requested_years_require_source_evidence(self):
        plan=deepcopy(self.plan);plan['source_years']=[2023,2024]
        with self.assertRaisesRegex(ValueError,'silently omitted'):validate_proposal(plan,QUESTION)
        proper=enrollment_race_plan(QUESTION+' from 2023 through 2024')
        self.assertEqual(len(proper['catalog_plan']['selections']),20)

    def test_filter_codes_must_belong_to_exact_definition(self):
        plan=deepcopy(self.plan);plan['filters'][0]['values']=['99']
        with self.assertRaisesRegex(ValueError,'disagree'):validate_proposal(plan,QUESTION)
        plan=deepcopy(self.plan);plan['filters'][0]['code_record_ids']=[self.library_id]
        with self.assertRaisesRegex(ValueError,'exact field'):validate_proposal(plan,QUESTION)

    def test_arbitrary_sql_and_unknown_ids_are_rejected(self):
        import jsonschema
        plan=deepcopy(self.plan);plan['sql']='SELECT * FROM HD2024'
        with self.assertRaises(jsonschema.ValidationError):validate_proposal(plan,QUESTION)
        plan=deepcopy(self.plan);plan['selections'][0]['record_id']=999999999
        with self.assertRaisesRegex(ValueError,'Unknown variable'):validate_proposal(plan,QUESTION)
        with self.assertRaises(ValueError):run_catalog_tool('execute_sql',{'sql':'SELECT 1'})
        with self.assertRaises(ValueError):inspect_table(2024,'EF2024A; DROP TABLE fields')

    def test_join_columns_bind_to_physical_inventory_not_guessed_definitions(self):
        plan=deepcopy(self.plan)
        plan['joins']=[{'year':2024,'left_table':'EF2024A','right_table':'HD2024',
                        'left_columns':['UNITID'],'right_columns':['UNITID'],'purpose':'Institution attributes'}]
        result=validate_proposal(plan,QUESTION)
        self.assertEqual(len(result['join_key_evidence']),2)
        self.assertFalse(result['validation']['blocks'])
        self.assertFalse(result['validation']['execution_approved'])
        plan['joins'][0]['left_columns']=['UNITID; DROP TABLE fields']
        with self.assertRaisesRegex(ValueError,'physical table'):validate_proposal(plan,QUESTION)

    def test_fact_join_is_only_a_review_proposal(self):
        plan=deepcopy(self.plan)
        plan['joins']=[{'year':2024,'left_table':'EF2024A','right_table':'ADM2024',
                        'left_columns':['UNITID'],'right_columns':['UNITID'],'purpose':'Candidate enrollment/admissions alignment'}]
        result=validate_proposal(plan,QUESTION)
        self.assertTrue(result['validation']['blocks'])
        self.assertIn('review',result['validation']['blocks'][0])

    def test_conflicting_source_locations_remain_blocked(self):
        with connection() as db:
            rid=db.execute("SELECT record_id FROM definitions WHERE release_id='IPEDS_2024-25_Provisional' AND physical_status!='documented_location_present' LIMIT 1").fetchone()
            if rid is None:
                rid=db.execute("SELECT record_id,release_id FROM definitions WHERE physical_status!='documented_location_present' LIMIT 1").fetchone()
                year=int(rid[1][6:10])
            else:year=2024
        plan=deepcopy(self.library_plan);plan['source_years']=[year]
        plan['selections']=[{'record_id':rid[0],'role':'measure'}]
        result=validate_proposal(plan,'Source location review')
        self.assertTrue(result['validation']['blocks']);self.assertFalse(result['validation']['execution_approved'])

    def test_bounded_model_tools_can_propose_nonregistry_library_field(self):
        with patch('anthropic.Anthropic') as cls:
            client=MagicMock();cls.return_value=client
            client.messages.create.side_effect=[
                response(block('inspect_table',{'year':2024,'table':'AL2024','offset':0,'limit':5,'keyword':''},'inspect')),
                response(block('read_definition',{'record_id':self.library_id,'offset':0,'limit':6000},'read')),
                response(block('submit_catalog_plan',self.library_plan,'finish'))]
            answer=model_catalog_plan('Show Yale academic library information for fiscal 2024')
        self.assertEqual(answer['intent'],'catalog_plan')
        self.assertEqual(answer['catalog_plan']['selections'][0]['record_id'],self.library_id)
        self.assertEqual(answer['model_usage']['calls'],3)
        self.assertEqual(answer['catalog_proposal']['validation']['schema_and_catalog_binding'],'passed')
        self.assertFalse(answer['catalog_proposal']['validation']['execution_approved'])
        args=client.messages.create.call_args.kwargs
        self.assertNotIn('enum',PLAN_SCHEMA['properties']['selections']['items']['properties']['record_id'])
        self.assertTrue(all(t['strict'] for t in args['tools'] if t['name'] not in {'submit_catalog_plan','submit_query_plan','submit_annual_plan','offer_analysis_options','submit_analysis_bundle','report_coverage_gap','submit_observation_plan'}))
        self.assertFalse(next(t['strict'] for t in args['tools'] if t['name']=='submit_catalog_plan'))
        self.assertFalse(any('execute' in t['name'] for t in args['tools']))

    def test_cache_prefix_is_stable_and_tool_history_is_append_only(self):
        requests=[]
        def create(**kwargs):
            requests.append(deepcopy(kwargs))
            if len(requests)==1:
                result=response(block('inspect_table',{'year':2024,'table':'AL2024','offset':0,'limit':5,'keyword':''},'inspect'))
            else:
                result=response(block('ask_clarification',{'questions':['Which library measure would you like?']}))
            result.usage.cache_creation_input_tokens=200
            result.usage.cache_read_input_tokens=800
            return result
        from prototype.memory import PLANNING_CONTEXT
        with patch('prototype.api_client.get_client') as get_client:
            get_client.return_value.messages.create.side_effect=create
            token=PLANNING_CONTEXT.set({'test_context':'Yale conversation'})
            try:first=model_catalog_plan('Yale library fiscal 2024')
            finally:PLANNING_CONTEXT.reset(token)
            model_catalog_plan('Harvard library fiscal 2024')
            model_catalog_plan('Harvard library fiscal 2023')
        first_request,second_request,other_question,other_year=requests
        for request in requests:
            self.assertEqual(request['cache_control'],{'type':'ephemeral'})
            self.assertEqual(request['system'][0]['cache_control'],{'type':'ephemeral'})
        stable,dynamic=first_request['messages'][0]['content']
        self.assertEqual(stable['cache_control'],{'type':'ephemeral'})
        self.assertNotIn('cache_control',dynamic)
        self.assertEqual(json.loads(dynamic['text'])['conversation_context'],{'test_context':'Yale conversation'})
        self.assertEqual(stable,other_question['messages'][0]['content'][0])
        self.assertNotEqual(dynamic,other_question['messages'][0]['content'][1])
        self.assertNotEqual(stable,other_year['messages'][0]['content'][0])
        self.assertEqual(second_request['messages'][:len(first_request['messages'])],first_request['messages'])
        self.assertEqual(second_request['messages'][-1]['content'][0]['tool_use_id'],'inspect')
        self.assertEqual(first['model_usage']['cache_creation_input_tokens'],400)
        self.assertEqual(first['model_usage']['cache_read_input_tokens'],1600)

    def test_model_invalid_plan_is_returned_for_repair_not_executed(self):
        bad=deepcopy(self.library_plan);bad['selections'][0]['record_id']=999999999
        with patch('anthropic.Anthropic') as cls:
            client=MagicMock();cls.return_value=client
            client.messages.create.side_effect=[response(block('submit_catalog_plan',bad,'bad')),
                                                 response(block('submit_catalog_plan',self.library_plan,'fixed'))]
            answer=model_catalog_plan('Yale library fiscal 2024')
            messages=deepcopy(client.messages.create.call_args.kwargs['messages'])
        self.assertEqual(answer['intent'],'catalog_plan')
        self.assertTrue(any(r.get('is_error') for m in messages if isinstance(m['content'],list) for r in m['content']))

    def test_missing_methodology_still_requests_clarification(self):
        self.assertEqual(ask('Yale URM graduation rate')['intent'],'clarify')
        self.assertNotEqual(ask('national enrollment by race')['intent'],'clarify')
        with patch('anthropic.Anthropic') as cls:
            cls.return_value.messages.create.return_value=response(block('ask_clarification',{'questions':['Do you mean fall headcount or 12-month enrollment?']}))
            answer=model_catalog_plan('Yale student population')
        self.assertEqual(answer['intent'],'clarify');self.assertIn('12-month',answer['message'])

    def test_catalog_followup_and_new_question_context_are_separate(self):
        with patch('prototype.catalog_planner.plan_catalog_question',return_value={'intent':'catalog_discovery','message':'followup'}) as planner:
            ask('What about Harvard?',self.plan)
        self.assertEqual(planner.call_args.args[1],self.plan)
        answer=ask('Yale applicants fall 2024',self.plan)
        self.assertIn('result',answer)

    def test_pending_catalog_clarification_accepts_short_reply(self):
        first=ask('Show undergrad population by race and ethnicity')
        self.assertEqual(first['intent'],'clarify')
        self.assertEqual(first['catalog_context']['kind'],'catalog_clarification')
        follow=ask('Yale',first['catalog_context'])
        self.assertEqual(follow['intent'],'analyze')
        fresh=ask('Yale applicants fall 2024',first['catalog_context'])
        self.assertIn('result',fresh)
        unavailable=ask(QUESTION+' in 2025')
        corrected=ask('2024 instead',unavailable['catalog_context'])
        self.assertEqual(corrected['catalog_plan']['source_years'],[2024])

    def test_streamlit_proposal_does_not_reuse_old_result_or_break_builder(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(BASE/'prototype/app.py'),default_timeout=60).run()
        app.button(key='topic_admissions').click().run();app.button(key='home_admissions-point').click().run()
        app.session_state['use_ai']=False
        app.chat_input(key='followup_question').set_value(QUESTION).run()
        self.assertFalse(app.exception)
        latest=app.session_state['history'][-1]['answer']
        self.assertEqual(latest['intent'],'analyze');self.assertIn('result',latest)
        self.assertEqual(app.session_state['last_plan']['version'],1)
        app.chat_input(key='followup_question').set_value('Show me the table').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['history'][-1]['answer']['mode'],'presentation adjustment')
        app.session_state['development_mode']=True;app.run()
        app.button(key='open_builder').click().run()
        self.assertFalse(app.exception)


if __name__=='__main__':
    unittest.main()

