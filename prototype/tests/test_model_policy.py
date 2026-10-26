"""Automatic routing preserves validation, user ambiguity, isolation and spend."""
from pathlib import Path
from unittest.mock import Mock,patch
from copy import deepcopy
import sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.model_policy import ACTIVE,AUTOMATIC,HAIKU,source_model
from prototype.agent import DEFAULT_MODEL
from prototype.intent_router import handle,InterpretationError
from prototype.tests.test_intent_router import decision,USAGE

class ModelPolicyTests(unittest.TestCase):
    def test_automatic_uses_haiku_and_keeps_legitimate_clarification(self):
        d=decision('clarify','',message='Which financial-aid population do you mean?')
        with patch('prototype.intent_router.interpret',return_value=(d,deepcopy(USAGE),{})) as interpret:
            answer=handle('Financial aid?',None,AUTOMATIC,[],Mock())
        self.assertEqual(interpret.call_count,1)
        self.assertEqual(interpret.call_args.args[2],HAIKU)
        self.assertEqual(answer['intent'],'clarify')
        self.assertEqual(answer['model_usage']['calls'],1)
        self.assertFalse(ACTIVE.get())

    def test_source_work_escalates_by_stage_without_changing_manual_models(self):
        d=decision('numerical','Show Yale enrollment in 2024')
        def execute(*args,**kwargs):
            self.assertEqual(args[3],HAIKU)
            self.assertEqual(source_model(args[3]),DEFAULT_MODEL)
            return {'intent':'clarify','message':'Source-backed user choice needed'}
        with patch('prototype.intent_router.interpret',return_value=(d,deepcopy(USAGE),{})):
            answer=handle(d['question'],None,AUTOMATIC,[],execute)
        self.assertEqual(answer['model_policy']['catalog_planner_model'],DEFAULT_MODEL)
        self.assertEqual(source_model(HAIKU),HAIKU)

    def test_one_rejected_interpretation_retry_counts_failed_cost(self):
        d=decision('conversation','Hello',message='Hello!')
        with patch('prototype.intent_router.interpret',side_effect=[InterpretationError('Incomplete structured output',deepcopy(USAGE)),(d,deepcopy(USAGE),{})]) as interpret:
            answer=handle('Hello',None,AUTOMATIC,[],Mock())
        self.assertEqual([call.args[2] for call in interpret.call_args_list],[HAIKU,DEFAULT_MODEL])
        self.assertEqual(answer['model_usage']['calls'],2)
        self.assertAlmostEqual(answer['model_usage']['estimated_api_usd'],.002)
        self.assertEqual(len(answer['model_policy']['interpretation_retries']),1)
        self.assertFalse(ACTIVE.get())

    def test_second_rejection_stops_and_clears_policy(self):
        with patch('prototype.intent_router.interpret',side_effect=InterpretationError('Rejected',deepcopy(USAGE))) as interpret:
            with self.assertRaises(InterpretationError):handle('Hello',None,AUTOMATIC,[],Mock())
        self.assertEqual(interpret.call_count,2);self.assertFalse(ACTIVE.get())

    def test_unavailable_service_does_not_trigger_same_provider_retry(self):
        with patch('prototype.intent_router.interpret',side_effect=RuntimeError('Unavailable')) as interpret:
            with self.assertRaises(RuntimeError):handle('Hello',None,AUTOMATIC,[],Mock())
        self.assertEqual(interpret.call_count,1);self.assertFalse(ACTIVE.get())

    def test_automatic_option_works_through_streamlit(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        self.assertEqual(app.session_state['model_choice'],AUTOMATIC)
        app.session_state['use_ai']=True
        app.session_state['model_choice']=AUTOMATIC
        app.session_state['main_page']='Ask & Analyze'
        app.run()
        d=decision('conversation','Hello',message='Hello! Ask an IPEDS question.')
        with patch('prototype.intent_router.interpret',return_value=(d,deepcopy(USAGE),{})) as interpret:
            app.chat_input(key='initial_question').set_value('Hello').run()
        self.assertFalse(app.exception);self.assertFalse(app.session_state.get('request_error'))
        self.assertEqual(interpret.call_args.args[2],HAIKU)
        answer=app.session_state['history'][-1]['answer']
        self.assertEqual(answer['model_policy']['strategy'],'conservative automatic')
        self.assertEqual(answer['model_usage']['model'],AUTOMATIC)

    def test_rejected_reviewed_plan_retains_its_charged_usage(self):
        from prototype.institution_confirmation import ask
        d=decision('numerical','Compare Yale and Harvard admission rates in 2024')
        d['institution_mentions']=['Yale','Harvard']
        planner_usage={**USAGE,'estimated_api_usd':.02}
        action={'intent':'analyze','plan':{'metrics':['admission_rate'],'institutions':['Yale'],
            'years':[2024],'time_basis':'observation','output':'chart'},'model_usage':planner_usage}
        with patch('prototype.intent_router.interpret',return_value=(d,deepcopy(USAGE),{})),patch('prototype.agent.model_plan',return_value=action):
            answer=handle(d['question'],None,DEFAULT_MODEL,[],ask)
        self.assertNotIn('result',answer)
        self.assertEqual(answer['intent'],'clarify')
        self.assertEqual(answer['model_usage']['calls'],2)
        self.assertAlmostEqual(answer['model_usage']['estimated_api_usd'],.021)

    def test_existing_manual_selection_is_preserved_on_rerun(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['model_choice']=DEFAULT_MODEL
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['model_choice'],DEFAULT_MODEL)

if __name__=='__main__':unittest.main()
