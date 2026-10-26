from pathlib import Path
import sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]


class TranscriptScrollTests(unittest.TestCase):
    def test_submission_completion_and_controls_keep_one_container_and_request(self):
        import streamlit as st
        from streamlit.testing.v1 import AppTest
        from prototype import ui
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60)
        app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
        app.session_state['main_page']='Ask & Analyze'
        app.session_state['history']=[{'question':f'Old question {i}','answer':{'intent':'clarify','message':'Old answer. '*30}} for i in range(8)]
        app.run();self.assertFalse(app.exception)
        with patch.object(st,'container',wraps=st.container) as containers,patch.object(st,'html',wraps=st.html) as html,patch.object(ui,'ask',return_value={'intent':'clarify','message':'New answer'}):
            app.chat_input(key='followup_question').set_value('UNTRUSTED_MESSAGE_123').run()
        self.assertFalse(app.exception)
        transcript=[c.kwargs for c in containers.call_args_list if c.kwargs.get('key','').startswith('conversation_messages')]
        self.assertGreaterEqual(len(transcript),2) # Pending and completed renders.
        self.assertEqual({c['key'] for c in transcript},{'conversation_messages'})
        self.assertTrue(all(c['autoscroll'] is False for c in transcript))
        self.assertTrue(html.call_args_list)
        self.assertTrue(all('UNTRUSTED_MESSAGE_123' not in str(c.args[0]) for c in html.call_args_list))
        serial=app.session_state['scroll_request_serial'];self.assertEqual(serial,1)
        self.assertEqual(len(app.session_state['history']),9)
        for button in ['hide_app_banner','collapse_ideas','collapse_tools']:
            app.button(key=button).click().run()
            self.assertEqual(app.session_state['scroll_request_serial'],serial)
            self.assertEqual(len(app.session_state['history']),9)
        with patch.object(ui,'ask',return_value={'intent':'clarify','message':'Another answer'}):
            app.chat_input(key='followup_question').set_value('Next question').run()
        self.assertEqual(app.session_state['scroll_request_serial'],2)
        self.assertEqual(len(app.session_state['history']),10)
        app.button(key='clear_chat').click().run()
        self.assertEqual(app.session_state['history'],[]);self.assertFalse(app.exception)


if __name__=='__main__':unittest.main()
