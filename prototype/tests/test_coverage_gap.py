from copy import deepcopy
from pathlib import Path
import sys,unittest
from unittest.mock import patch,MagicMock
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.coverage_gap import prepare_gap
from prototype.analysis_clarification import prepare,select
from prototype.tests.test_query_engine import source,plan,field_ref
from prototype.tests.test_catalog_planner import block,response
from prototype.agent import ask


class CoverageGapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        s,d=source('EF2024',fields=['EFWOM'],filters={'EFLEVEL':'20'})
        cls.option={'id':'A','label':'Women undergraduate enrollment',
            'interpretation':'Show Yale women undergraduate enrollment in Fall 2024.',
            'qualifications':['Enrollment is not an institution classification.'],
            'plan':plan([s],[(field_ref(d['EFWOM'],'s'),'Women undergraduates')])}
        cls.payload={'missing_information':'Requested institutional classification',
            'explanation':'The inspected supplied files do not establish this classification; enrollment composition does not determine it.',
            'status':'coverage_gap','options':[]}
        cls.inspections=[{'tool':'search_catalog','input':{'query':'institution classification','year':2024,'limit':5},'returned_items':0}]

    def test_gap_is_a_complete_response_without_forced_choices(self):
        with patch('prototype.query_engine.execute',side_effect=AssertionError('No values')):
            a=prepare_gap(self.payload,'Count this institution class',inspections=self.inspections)
        self.assertTrue(a['message'].startswith('I can’t answer the original question'))
        self.assertFalse(a['analysis_brief']['options']);self.assertFalse(a['analysis_brief']['open_questions'])
        self.assertIsNone(select('continue',[{'answer':a}]))
        self.assertNotIn('result',a)

    def test_one_optional_proxy_preserves_gap_and_runs_only_after_selection(self):
        p=deepcopy(self.payload);p['options']=[deepcopy(self.option)]
        with patch('prototype.query_engine.execute',side_effect=AssertionError('No values before selection')):
            a=prepare_gap(p,'Classify Yale',inspections=self.inspections)
        self.assertLess(a['message'].index('can’t answer'),a['message'].index('Optional alternatives'))
        self.assertFalse(a['analysis_brief']['open_questions'])
        history=[{'question':'Classify Yale','answer':a}]
        self.assertIsNone(select('continue',history))
        with patch('prototype.memory.resolve',side_effect=AssertionError('No guessed proxy choice')):
            self.assertNotIn('result',ask('continue',conversation=history,use_model=True))
        self.assertIsNotNone(select('try optional proxy A',history))
        with patch('prototype.agent._answer',side_effect=AssertionError('No model planning')):
            selected=ask('A',conversation=history,use_model=True)
        self.assertIn('result',selected);self.assertEqual(selected['model_usage']['calls'],0)
        self.assertIn('does not answer the original question',selected['message'])
        self.assertIn('coverage_gap',selected['analysis_brief'])

    def test_source_inspection_required_and_incomplete_search_not_absence(self):
        with self.assertRaisesRegex(ValueError,'Inspect'):prepare_gap(self.payload,'Count')
        p=deepcopy(self.payload);p['status']='incomplete_search'
        a=prepare_gap(p,'Count',inspections=self.inspections)
        self.assertIn('can’t determine whether',a['message'])
        p['options']=[self.option]
        with self.assertRaisesRegex(ValueError,'Incomplete retrieval'):prepare_gap(p,'Count',inspections=self.inspections)

    def test_proxy_cannot_masquerade_as_ordinary_definition_choice(self):
        option=deepcopy(self.option);option['interpretation']='Proxy based on undergraduate women at Yale.'
        other=deepcopy(option);other['id']='B'
        with self.assertRaisesRegex(ValueError,'report_coverage_gap'):
            prepare({'question':'Choose a definition','goal':'Classify','options':[option,other]},'Classify')

    def test_invalid_optional_plan_is_never_offered(self):
        p=deepcopy(self.payload);p['options']=[deepcopy(self.option)]
        p['options'][0]['plan']['outputs'][0]['reference']='invented'
        with self.assertRaises(ValueError):prepare_gap(p,'Count',inspections=self.inspections)

    def test_production_planner_dispatch_preserves_local_source_evidence(self):
        from prototype.catalog_planner import model_catalog_plan
        messages=[response(block('search_catalog',{'query':'women college classification','year':2024,'limit':5})),
                  response(block('report_coverage_gap',self.payload))]
        with patch('anthropic.Anthropic') as client:
            client.return_value.messages.create.side_effect=messages
            with patch('prototype.query_engine.execute',side_effect=AssertionError('No statistical values')):
                a=model_catalog_plan("how many women's colleges in the US")
            sent=client.return_value.messages.create.call_args.kwargs
        self.assertEqual(a['mode'],'source coverage limitation')
        self.assertEqual(a['coverage_gap']['source_inspections'][0]['input']['query'],'women college classification')
        self.assertIn('sources supplied by the owner',sent['system'][0]['text'])
        self.assertFalse(any(t['name'] in {'web_search','browse'} for t in sent['tools']))

    def test_actual_ui_labels_proxy_as_optional_and_keeps_gap_first(self):
        from streamlit.testing.v1 import AppTest
        p=deepcopy(self.payload);p['options']=[deepcopy(self.option)]
        a=prepare_gap(p,'Classify Yale',inspections=self.inspections)
        def app():
            import streamlit as st
            from prototype.ui import render_answer
            render_answer(st.session_state['history'][-1]['answer'],'gap')
        app=AppTest.from_function(app,default_timeout=60)
        app.session_state['history']=[{'question':'Classify Yale','answer':a}]
        app.run();self.assertFalse(app.exception)
        self.assertEqual(app.button(key='gap_choice_A').label,'Try optional proxy A')
        self.assertTrue(any('Optional: try a proxy' in c.value for c in app.caption))

    def test_unrequested_proxy_submission_gets_repair_feedback_not_execution(self):
        from prototype.catalog_planner import model_catalog_plan
        proxy=deepcopy(self.option['plan']);proxy['assumptions']=['Proxy for the requested classification']
        with patch('anthropic.Anthropic') as client:
            client.return_value.messages.create.side_effect=[
                response(block('search_catalog',{'query':'classification','year':2024,'limit':5})),
                response(block('submit_query_plan',proxy)),
                response(block('report_coverage_gap',self.payload))]
            with patch('prototype.query_engine.execute',side_effect=AssertionError('No proxy execution')):
                a=model_catalog_plan('Classify Yale')
            self.assertEqual(client.return_value.messages.create.call_count,3)
        self.assertEqual(a['mode'],'source coverage limitation');self.assertNotIn('result',a)


if __name__=='__main__':unittest.main()
