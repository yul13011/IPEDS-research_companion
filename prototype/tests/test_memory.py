from pathlib import Path
import sys,json,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.agent import ask
from prototype.memory import context,PLANNING_CONTEXT,local_resolve

def history():
    return [{'question':"Show Yale's undergraduate population by race and ethnicity in fall 2024",'answer':{'intent':'analyze','catalog_plan':{'version':1,'institutions':['Yale'],'source_years':[2024]},'message':'Source counts'}}]

class MemoryTests(unittest.TestCase):
    def test_context_is_bounded_and_never_includes_source_sql(self):
        h=history()*20
        h[0]['answer']['result']={'sources':[{'sql':'DO NOT SEND'}],'rows':[{'value':123}]}
        b=context(h)
        self.assertEqual(len(b['recent_turns']),12)
        self.assertEqual(b['recent_turns'][-1]['turn'],20)
        self.assertNotIn('DO NOT SEND',json.dumps(b));self.assertNotIn('rows',json.dumps(b))

    def test_local_name_and_percentage_continuations(self):
        b=context(history())
        self.assertIn('Harvard',local_resolve('now Harvard',b))
        self.assertNotIn('Yale',local_resolve('now Harvard',b))
        self.assertIn('percentages',local_resolve('show percentages',b))
        self.assertEqual(local_resolve('New question about tuition',b),'New question about tuition')

    def test_semantic_resolution_is_used_before_routing_and_isolated(self):
        resolved={'kind':'followup','question':'Show Harvard undergraduate enrollment by race in fall 2024','referenced_turns':[1]}
        usage={'calls':1,'latency_seconds':.1,'estimated_api_usd':.01}
        seen=[]
        def answer(question,*args):
            seen.append((question,PLANNING_CONTEXT.get()))
            return {'intent':'clarify','message':'Test','model_usage':{'calls':2,'estimated_api_usd':.02}}
        with patch('prototype.memory.resolve',return_value=(resolved,usage)),patch('prototype.agent._answer',side_effect=answer):
            a=ask('now Harvard',use_model=True,conversation=history())
        self.assertEqual(seen[0][0],resolved['question']);self.assertTrue(seen[0][1]['recent_turns'])
        self.assertEqual(a['model_usage']['calls'],3);self.assertAlmostEqual(a['model_usage']['estimated_api_usd'],.03)
        self.assertIsNone(PLANNING_CONTEXT.get())

    def test_ambiguous_reference_clarifies_without_execution(self):
        resolved={'kind':'clarify','question':'Do you mean the race breakdown or the awards breakdown?','referenced_turns':[1]}
        with patch('prototype.memory.resolve',return_value=(resolved,{'calls':1,'latency_seconds':.1})),patch('prototype.agent._answer') as execute:
            a=ask('Change that breakdown',use_model=True,conversation=history())
        self.assertEqual(a['intent'],'clarify');execute.assert_not_called()

    def test_clear_context_and_exception_do_not_leak(self):
        with patch('prototype.memory.resolve') as resolver,patch('prototype.agent._answer',return_value={'intent':'clarify','message':'Test'}):
            ask('A new conversation',use_model=True,conversation=[]);resolver.assert_not_called()
        with patch('prototype.memory.resolve',side_effect=ValueError('Test')):
            with self.assertRaises(ValueError):ask('followup',use_model=True,conversation=history())
        self.assertIsNone(PLANNING_CONTEXT.get())

    def test_resolver_transport_and_explicit_period_protection(self):
        from prototype.memory import resolve
        from prototype.tests.test_catalog_planner import block,response
        from unittest.mock import MagicMock
        b=context(history())
        with patch('anthropic.Anthropic') as cls:
            client=MagicMock();cls.return_value=client
            client.messages.create.return_value=response(block('resolve_context',{'kind':'followup','question':'Show Harvard race breakdown in fall 2025','referenced_turns':[1]}))
            result,usage=resolve('now Harvard in fall 2025',b,'claude-sonnet-5-5')
            self.assertIn('2025',result['question']);self.assertEqual(usage['calls'],1)
            args=client.messages.create.call_args.kwargs
            self.assertEqual(args['tool_choice'],{'type':'auto'})
            self.assertIn('recent_turns',args['messages'][0]['content'])
            client.messages.create.return_value=response(block('resolve_context',{'kind':'followup','question':'Show Harvard race breakdown in fall 2024','referenced_turns':[1]}))
            with self.assertRaisesRegex(ValueError,'explicitly requested year'):resolve('now Harvard in fall 2025',b,'claude-sonnet-5-5')
            client.messages.create.return_value=response(block('resolve_context',{'kind':'followup','question':'Show Harvard race breakdown','referenced_turns':[99]}))
            with self.assertRaisesRegex(ValueError,'reference could not be resolved'):resolve('now Harvard',b,'claude-sonnet-5-5')

    def test_actual_local_continuation_changes_institution_and_preserves_scope(self):
        a=ask('now Harvard',conversation=history())
        self.assertEqual(a['intent'],'analyze')
        self.assertEqual([x.lower() for x in a['catalog_plan']['institutions']],['harvard'])
        self.assertTrue(all(r['unitid']==166027 for r in a['result']['rows']))
        self.assertEqual(a['catalog_plan']['filters'][0]['values'],['2'])

    def test_clear_button_recovers_from_first_question_planner_error(self):
        from streamlit.testing.v1 import AppTest
        from prototype import ui
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
        app.button(key='nav_ask').click().run()
        with patch.object(ui,'ask',side_effect=ValueError('Too many planning tool requests in one call.')):
            app.chat_input(key='initial_question').set_value('A complex question').run()
        self.assertTrue(app.error);self.assertFalse(app.session_state['history'])
        app.session_state['confirmed_institutions']={'yale college':130794}
        app.button(key='clear_chat').click().run()
        self.assertFalse(app.exception);self.assertFalse(app.error)
        self.assertFalse(app.session_state['history']);self.assertFalse(app.session_state.get('confirmed_institutions'))
        self.assertIsNone(app.session_state['pending_action']);self.assertIsNone(app.session_state['last_plan'])
        self.assertFalse(app.chat_input(key='initial_question').disabled)

    def test_ui_passes_history_and_new_conversation_clears_it(self):
        from streamlit.testing.v1 import AppTest
        from prototype import ui
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
        app.button(key='nav_ask').click().run()
        with patch.object(ui,'ask',return_value={'intent':'clarify','message':'Test answer'}) as mocked:
            app.chat_input(key='initial_question').set_value('First question').run()
            app.chat_input(key='followup_question').set_value('And another question').run()
        self.assertFalse(app.exception)
        sent=mocked.call_args.kwargs['conversation']
        self.assertEqual(sent[0]['question'],'First question')
        app.button(key='clear_chat').click().run()
        self.assertFalse(app.session_state['history'])
        self.assertIsNone(app.session_state['last_plan'])

if __name__=='__main__':unittest.main()

