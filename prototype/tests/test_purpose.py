import unittest
from unittest.mock import patch
from prototype import purpose,institution_confirmation,agent
from prototype.progress import reporting


class PurposeTests(unittest.TestCase):
    def test_conversation_bypasses_provider_identity_and_progress(self):
        for entry in [institution_confirmation.ask,agent.ask]:
            for question in ['Hi','Hi there!','Hello!','Thanks for clarifying.','What can you do?','Hi, what can you do?']:
                with self.subTest(entry=entry.__module__,question=question),patch('prototype.institution_confirmation.mentions',side_effect=AssertionError('identity ran')),patch('prototype.definitions.handle',side_effect=AssertionError('documentation ran')):
                    stages=[]
                    with reporting(stages.append):answer=entry(question,use_model=True,conversation=[{'question':'old','answer':{}}])
                    self.assertEqual(answer['model_usage']['calls'],0)
                    self.assertEqual(answer['intent'],'conversation')
                    self.assertEqual(stages,[])

    def test_substantive_questions_survive(self):
        for question in ['Hi, compare Smith and Wellesley enrollment','Thanks, show Smith enrollment','A','What about Wellesley?','Which Massachusetts colleges offer childcare?','What is Smith enrollment?']:
            self.assertIsNone(purpose.direct(purpose.prepare(question)))
        self.assertEqual(purpose.prepare('Hello! What does Pell mean?'),'What does Pell mean?')
        with patch('prototype.institution_confirmation._ask',return_value={'intent':'analyze'}) as route:
            institution_confirmation.ask('Hi, show Smith enrollment')
            self.assertEqual(route.call_args.args[0],'show Smith enrollment')

    def test_mixed_retains_both_outputs_and_usage(self):
        docs={'intent':'definition','message':'Source definition','evidence':[{'record_id':42}],'model_usage':{'calls':1,'estimated_api_usd':.01}}
        analysis={'intent':'analyze','message':'Validated result','result':{'result_id':'r'},'model_usage':{'calls':2,'estimated_api_usd':.02}}
        with patch('prototype.definitions.handle',return_value=docs),patch('prototype.institution_confirmation._ask',return_value=analysis) as route:
            answer=institution_confirmation.ask('Define Pell and show Pell enrollment at Smith College',use_model=True)
        self.assertEqual(route.call_args.args[0],'show Pell enrollment at Smith College')
        self.assertEqual(answer['documentation_sections'][0]['evidence'][0]['record_id'],42)
        self.assertEqual(answer['model_usage']['calls'],3)
        self.assertAlmostEqual(answer['model_usage']['estimated_api_usd'],.03)
        self.assertEqual(answer['result']['result_id'],'r')

    def test_ambiguous_documentation_does_not_compute(self):
        with patch('prototype.definitions.handle',return_value={'intent':'clarify','message':'Which measure?'}),patch('prototype.institution_confirmation._ask') as analysis:
            answer=institution_confirmation.ask('Define this and compare Smith and Wellesley')
        analysis.assert_not_called()
        self.assertIn('analysis_question',answer['pending_mixed_request'])

    def test_compounds_do_not_split_definition_comparisons_or_numeric_requests(self):
        self.assertIsNone(purpose.mixed('Explain the difference between Pell and other grants'))
        self.assertIsNone(purpose.mixed('Show tuition and compare enrollment'))
        self.assertEqual(purpose.mixed('How is enrollment calculated then show Smith enrollment')[0],'How is enrollment calculated')

    def test_documentation_tool_reads_real_supplied_evidence(self):
        from prototype.catalog_planner import run_catalog_tool
        answer=run_catalog_tool('lookup_documentation',{'question':'What does Pell mean in IPEDS?'})
        self.assertTrue(answer.get('evidence'))
        self.assertNotIn('result',answer)
        self.assertIn('Pell',answer['message'])
        with self.assertRaises(ValueError):run_catalog_tool('lookup_documentation',{'question':'x'*501})

    def test_invalid_input(self):
        for q in ['',None,'x'*4001]:
            with self.assertRaises(ValueError):institution_confirmation.ask(q)

    def test_social_turn_does_not_erase_documentation_antecedent(self):
        first=institution_confirmation.ask('Define admission rate')
        history=[{'question':'Define admission rate','answer':first},
                 {'question':'Thanks','answer':institution_confirmation.ask('Thanks')}]
        answer=institution_confirmation.ask('How is it calculated?',conversation=history)
        self.assertIn('Admissions total ÷ Applicants total × 100',answer['message'])

    def test_mixed_pronoun_uses_current_definition(self):
        docs={'intent':'definition','message':'Definition','documentation_context':{'terms':['admission rate']}}
        with patch('prototype.definitions.handle',return_value=docs),patch('prototype.institution_confirmation._ask',return_value={'intent':'analyze'}) as analysis:
            institution_confirmation.ask('Define admission rate and show it at Smith College')
        self.assertEqual(analysis.call_args.args[0],'show admission rate at Smith College')

    def test_greeting_in_real_chat_bypasses_display_and_analysis(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        from prototype import ui
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
        app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
        app.button(key='nav_ask').click().run()
        with patch.object(ui,'ask',side_effect=AssertionError('analytical entry called')),patch.object(ui,'adjust_presentation',side_effect=AssertionError('display route called')):
            app.chat_input(key='initial_question').set_value('Hi').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['history'][-1]['answer']['purpose']['kind'],'greeting')

    def test_planner_can_investigate_documentation_within_tool_loop(self):
        from unittest.mock import MagicMock
        from prototype.tests.test_catalog_planner import response,block
        from prototype.catalog_planner import model_catalog_plan
        with patch('anthropic.Anthropic') as cls:
            client=MagicMock();cls.return_value=client
            client.messages.create.side_effect=[
                response(block('lookup_documentation',{'question':'Define Pell in 2024'},'doc')),
                response(block('ask_clarification',{'questions':['Which Pell measure and institution should I use?']},'finish'))]
            answer=model_catalog_plan('Explain Pell and compare the relevant measure')
        self.assertEqual(answer['model_usage']['calls'],2)
        second=client.messages.create.call_args.kwargs
        results=second['messages'][2]['content']
        self.assertEqual(results[0]['tool_use_id'],'doc')
        self.assertIn('evidence',results[0]['content'])
        self.assertEqual(answer['intent'],'clarify')

    def test_polite_definition_variants(self):
        for question in ['Can you explain Pell?','How should I interpret admission rate?','Tell me what Pell means']:
            with self.subTest(question=question),patch('prototype.institution_confirmation.mentions',side_effect=AssertionError('identity ran')):
                answer=institution_confirmation.ask(question)
                self.assertTrue(answer.get('evidence'))
                self.assertNotIn('result',answer)

    def test_canonical_identity_annotation_validates_without_weakening_conflicts(self):
        from prototype.intent_checks import _ids
        self.assertEqual(_ids(['Yale University (UNITID 130794)']),[130794])
        self.assertIsNone(institution_confirmation.resolve('Harvard University (UNITID 130794)',{}))
        self.assertIsNone(institution_confirmation.resolve('Yale (UNITID 130794)',{}))

    def test_model_canonical_identity_executes_reviewed_numerical_lookup(self):
        from unittest.mock import MagicMock
        from prototype.tests.test_catalog_planner import response,block
        from prototype.intent_checks import CURRENT,contract
        payload={'intent':'analyze','message':'Applicants','query':'','metrics':['applicants'],
                 'institutions':['Yale University (UNITID 130794)'],'years':[2024],
                 'time_basis':'observation','output':'answer'}
        token=CURRENT.set(contract('Yale University (UNITID 130794) applicants fall 2024'))
        try:
            with patch('anthropic.Anthropic') as cls:
                client=MagicMock();cls.return_value=client
                client.messages.create.return_value=response(block('choose_plan',payload,'plan'))
                planned=agent.model_plan('Yale University (UNITID 130794) applicants fall 2024')
            self.assertEqual(planned['plan']['institutions'],['130794'])
            from prototype.analytics import execute,Plan
            result=execute(Plan(**planned['plan']))
            self.assertEqual(result['rows'][0]['unitid'],130794)
            self.assertGreater(result['rows'][0]['value'],0)
        finally:CURRENT.reset(token)


if __name__=='__main__':unittest.main()
