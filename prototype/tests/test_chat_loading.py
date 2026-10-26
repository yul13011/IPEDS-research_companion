"""Loading stays in the conversation after the surrounding workspace redraws."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
import streamlit as st
from streamlit.testing.v1 import AppTest
from prototype import ui
from prototype.progress import report,reporting


class ChatLoadingTests(unittest.TestCase):
    def test_panel_reruns_retain_interrupted_request(self):
        for panel in ('ideas','tools'):
            with self.subTest(panel=panel):
                app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
                app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
                app.button(key='nav_ask').click().run()
                # Streamlit interruption exceptions bypass ordinary Exception
                # handlers, just as a widget-triggered rerun does mid-query.
                with patch.object(ui,'ask',side_effect=lambda *a,**k:st.stop()):
                    app.chat_input(key='initial_question').set_value('Keep this question').run()
                self.assertEqual(app.session_state['pending_action']['question'],'Keep this question')
                self.assertEqual(app.session_state['history'],[])
                with patch.object(ui,'ask',return_value={'intent':'clarify','message':'Retained answer'}) as query:
                    app.button(key='collapse_'+panel).click().run()
                self.assertFalse(app.exception)
                self.assertFalse(app.session_state[panel+'_open'])
                self.assertIsNone(app.session_state['pending_action'])
                self.assertEqual(len(app.session_state['history']),1)
                self.assertEqual(app.session_state['history'][0]['question'],'Keep this question')
                self.assertEqual(app.session_state['history'][0]['answer']['message'],'Retained answer')
                query.assert_called_once()
                app.run()
                self.assertEqual(len(app.session_state['history']),1)

    def test_stage_reporters_are_scoped_and_reset_on_failure(self):
        outer=[];inner=[]
        with reporting(outer.append):
            report('outer')
            with self.assertRaises(ValueError):
                with reporting(inner.append):
                    report('inner');raise ValueError('failed request')
            report('resumed outer')
        report('no active request')
        self.assertEqual(outer,['outer','resumed outer'])
        self.assertEqual(inner,['inner'])

    def test_real_offline_request_reports_its_actual_stages(self):
        events=[]
        with reporting(events.append):answer=ui.ask('Yale applicants fall 2024',use_model=False)
        self.assertEqual(answer['intent'],'analyze')
        self.assertIn('Identifying the institution in your question…',events)
        self.assertIn('Validating selections and source definitions…',events)
        self.assertIn('Reading source data for 2024…',events)
        self.assertEqual(events[-1],'Preparing your answer and display…')
        self.assertLess(events.index('Validating selections and source definitions…'),events.index('Reading source data for 2024…'))
        self.assertFalse(any('step' in text for text in events))

    def test_loading_context_and_workspace_order(self):
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
        app.button(key='nav_ask').click().run()
        order=[];contexts=[];updates=[];update_contexts=[]
        original_pending=ui.run_pending;original_tools=ui.render_tools
        original_status=ui.show_work_status

        def status(slot,message):
            updates.append(message)
            update_contexts.append(st._main._active_dg._block_type)
            original_status(slot,message)

        def answer(*args,**kwargs):
            report('Reading source data for 2024…')
            report('Preparing your answer and display…')
            return {'intent':'clarify','message':'Test reply'}

        def tools():
            original_tools();order.append('tools rendered')

        def pending():
            order.append('query started')
            dg=st._main._active_dg;chain=[]
            while dg is not None:
                chain.append(dg._block_type);dg=dg._parent
            contexts.append(chain)
            original_pending()

        with patch.object(ui,'render_tools',side_effect=tools),patch.object(ui,'run_pending',side_effect=pending),patch.object(ui,'ask',side_effect=answer),patch.object(ui,'show_work_status',side_effect=status):
            app.chat_input(key='initial_question').set_value('A test question').run()
        self.assertFalse(app.exception)
        self.assertEqual(order[:2],['tools rendered','query started'])
        self.assertEqual(contexts[0][0],'chat_message')
        self.assertIn('column',contexts[0])
        self.assertEqual(len(app.chat_message),2)
        self.assertEqual(app.session_state['history'][-1]['question'],'A test question')
        self.assertEqual(app.session_state['history'][-1]['answer']['message'],'Test reply')
        self.assertFalse(app.chat_input(key='followup_question').disabled)
        self.assertIn('Reading source data for 2024…',updates)
        self.assertIn('Preparing your answer and display…',updates)
        self.assertTrue(all(kind=='chat_message' for kind in update_contexts))
        self.assertFalse(any(item.value in updates for item in app.caption))


if __name__=='__main__':unittest.main()
