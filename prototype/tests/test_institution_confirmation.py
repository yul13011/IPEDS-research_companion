from pathlib import Path
import sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.institution_confirmation import ask,resolve,candidates,AUTHORIZED,mentions,complete_mentions
from prototype.catalog import institutions

class InstitutionConfirmationTests(unittest.TestCase):
    def test_name_id_annotations_require_verified_full_name(self):
        for name in ['Yale University (130794)','Yale University (UNITID 130794)','yale university (unitid 130794)']:
            self.assertEqual(resolve(name,{}),130794)
            self.assertEqual(institutions([name],2024),[130794])
        for name in ['Yale University (166027)','Yale College (130794)','Invented Campus (130794)']:
            self.assertIsNone(resolve(name,{}))

    def test_reviewed_literal_aliases_survive_model_omission(self):
        from prototype.intent_router import INTERPRETED
        token=INTERPRETED.set({'institution_mentions':[]})
        try:
            with patch('anthropic.Anthropic',side_effect=AssertionError('Do not spend another extraction call')):
                names,_=mentions('Compare Yale and Harvard admissions',True,'claude-haiku-5-5')
                geography,_=mentions('Which Massachusetts schools offer distance courses?',True,'claude-haiku-5-5')
            self.assertEqual(set(names),{'Yale','Harvard'})
            self.assertEqual(geography,[])
        finally:INTERPRETED.reset(token)

    def test_complete_official_names_and_formatting_do_not_need_confirmation(self):
        for name in ['Mount Holyoke College','mount holyoke college','Mount  Holyoke College','Mount\u00a0Holyoke College','Mount Holyoke College.']:
            self.assertEqual(resolve(name,{}),166939,name)
        # A unique fuzzy/shorthand option still requires an explicit choice.
        self.assertIsNone(resolve('Mount Holyoke',{}))
        with patch('prototype.institution_confirmation.mentions',return_value=(['Mount Holyoke'],None)),patch('prototype.agent.ask') as execute:
            pending=ask('Mount Holyoke enrollment')
        self.assertEqual(pending['institution_confirmation']['unresolved'][0]['candidates'],[166939])
        execute.assert_not_called()
        # Formatting normalization cannot silently choose between collisions.
        with patch('prototype.workflows.institution_index',return_value={1:{'names':['Example College']},2:{'names':['Example-College']}}):
            self.assertIsNone(resolve('Example  College',{}))
            self.assertEqual(resolve('Example College',{}),1)

    def test_literal_directory_name_recovers_partial_model_extraction(self):
        q='how many students does Mount Holyoke College have? Show 10-year trend.'
        for extracted in [[],['Mount Holyoke'],['Holyoke College']]:
            self.assertEqual(complete_mentions(q,extracted),['Mount Holyoke College'])
        with patch('prototype.institution_confirmation.mentions',return_value=(complete_mentions(q,['Holyoke College']),None)),patch('prototype.agent.ask',return_value={'intent':'clarify','message':'Population choice, not institution choice'}) as execute:
            answer=ask(q,use_model=True)
        self.assertEqual(answer['institution_identity']['unitids'],[166939])
        self.assertNotEqual(answer['intent'],'institution_confirmation')
        self.assertIn('166939',execute.call_args.args[0])

    def test_college_in_official_name_is_not_a_separate_reporting_unit(self):
        from prototype.responses import visible_warnings
        q='Show Mount Holyoke College undergraduate population by race and ethnicity in fall 2024'
        answer=ask(q)
        self.assertEqual(answer['intent'],'analyze')
        self.assertEqual(answer['institution_identity']['unitids'],[166939])
        self.assertFalse(answer['institution_identity']['scope_mentions'])
        self.assertFalse(any('separate' in w.lower() for w in visible_warnings(answer['result'])))
        # Old saved answers must also stop claiming the official college is absent.
        answer['result']['warnings'].append('Results use the confirmed reporting institution. A separate record for the originally named college/school/campus was not identified; do not interpret these as separately reported college-level figures.')
        answer['result']['institution_identity'].pop('scope_mentions')
        self.assertFalse(any('separate' in w.lower() for w in visible_warnings(answer['result'])))
        for name,uid,expect_scope in [('Mount Holoyke College',166939,False),('Yale College',130794,True)]:
            with patch('prototype.institution_confirmation.mentions',return_value=([name],None)):
                confirmed=ask('Show '+name+' undergraduate population by race and ethnicity in fall 2024',institution_choices={name.lower():uid})
            self.assertEqual(confirmed['intent'],'analyze')
            shown=visible_warnings(confirmed['result'])
            self.assertEqual(any('separate figures' in w for w in shown),expect_scope)
            self.assertFalse(any('record was not identified' in w for w in shown))

    def test_exact_alias_and_nonexact_single_candidate(self):
        self.assertEqual(resolve('Yale University',{}),130794)
        self.assertEqual(resolve('MIT',{}),166683)
        self.assertIsNone(resolve('University of Michigan',{}))
        self.assertIsNone(resolve('Columbia',{}))
        self.assertIn(170976,candidates('University of Michigan'))
        self.assertIn(130794,candidates('Ylae University'))

    def test_pending_never_runs_analysis(self):
        with patch('prototype.agent.ask') as execute,patch('prototype.institution_confirmation.mentions',return_value=(['University of Michigan'],None)):
            a=ask('Show University of Michigan graduation rates')
        self.assertEqual(a['intent'],'institution_confirmation');execute.assert_not_called()
        self.assertGreater(len(a['institution_confirmation']['unresolved'][0]['candidates']),1)

    def test_yale_college_preserves_full_original_name(self):
        from prototype.institution_confirmation import complete_mentions
        q="what is Yale College's undergraduate population in the last 10 years."
        self.assertEqual(complete_mentions(q,['Yale']),['Yale College'])
        self.assertEqual(complete_mentions(q,[]),['Yale College'])
        with patch('prototype.agent.ask') as execute:
            a=ask(q)
        execute.assert_not_called()
        self.assertEqual(a['intent'],'institution_confirmation')
        pending=a['institution_confirmation']['unresolved'][0]
        self.assertEqual(pending['text'],'Yale College')
        self.assertIn(130794,pending['candidates'])

    def test_candidates_require_distinctive_name_evidence(self):
        from prototype.workflows import institution_index
        names=[institution_index()[uid]['name'] for uid in candidates('Yale College')]
        self.assertIn('Yale University',names)
        self.assertNotIn('Salem College',names)
        self.assertTrue(all('Yale' in name for name in names),names)
        self.assertEqual(candidates('College'),[])
        self.assertIn(130794,candidates('Ylae University'))

    def test_confirmed_convention_is_reused_across_topics(self):
        h=[{'question':'Yale College gender','answer':{'institution_identity':{'unitids':[130794],'confirmed_choices':{'yale college':130794}}}}]
        with patch('prototype.agent.ask',return_value={'intent':'clarify','message':'Test'}) as execute:
            a=ask("Show Yale College's race/ethnicity distribution in Fall 2024",conversation=h)
        self.assertNotEqual(a['intent'],'institution_confirmation')
        self.assertIn('130794',execute.call_args.args[0])
        self.assertEqual(a['institution_identity']['confirmed_choices']['yale college'],130794)

    def test_confirmed_id_is_used_and_other_campuses_are_blocked(self):
        with patch('prototype.institution_confirmation.mentions',return_value=(['University of Michigan'],None)),patch('prototype.agent.ask') as execute:
            def run(q,*args,**kwargs):
                self.assertIn('170976',q)
                self.assertEqual(institutions(['170976'],2024),[170976])
                with self.assertRaisesRegex(ValueError,'model-selected campus'):institutions(['170639'],2024)
                return {'intent':'clarify','message':'Test'}
            execute.side_effect=run
            a=ask('Show University of Michigan graduation rates',institution_choices={'university of michigan':170976})
        self.assertEqual(a['institution_identity']['unitids'],[170976]);self.assertIsNone(AUTHORIZED.get())

    def test_exact_institution_actual_query(self):
        a=ask("Show Yale University's undergraduate population by race and ethnicity in fall 2024")
        self.assertEqual(a['intent'],'analyze')
        self.assertTrue(all(r['unitid']==130794 for r in a['result']['rows']))

    def test_unknown_can_be_refined_and_no_match_is_not_guessed(self):
        with patch('prototype.institution_confirmation.mentions',return_value=(['zzzzuniversityzzzz'],None)),patch('prototype.agent.ask') as execute:
            a=ask('Show zzzzuniversityzzzz enrollment')
        execute.assert_not_called();self.assertFalse(a['institution_confirmation']['unresolved'][0]['candidates'])
        self.assertIn(130794,candidates('130794'))

    def test_ui_requires_choice_and_cancel_executes_nothing(self):
        from streamlit.testing.v1 import AppTest
        from prototype import ui
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
        app.button(key='nav_ask').click().run()
        pending={'question':'Michigan enrollment','choices':{},'unresolved':[{'text':'Michigan','key':'michigan','candidates':[170976,170639]}]}
        with patch.object(ui,'ask',return_value={'intent':'institution_confirmation','message':'Which institution?','institution_confirmation':pending}) as query:
            app.chat_input(key='initial_question').set_value('Michigan enrollment').run()
            self.assertFalse(app.exception)
            box=next(x for x in app.selectbox if x.label=='Which institution did you mean?')
            self.assertIsNone(box.value)
            controls=[getattr(node,'label',None) for node in app.main]
            self.assertLess(controls.index('Which institution did you mean?'),controls.index('None of these? Refine by name, city/state or UNITID'))
            app.button(key='institution_continue').click().run()
            self.assertEqual(query.call_count,1)
            app.button(key='institution_cancel').click().run()
            self.assertEqual(query.call_count,1);self.assertFalse(app.session_state.get('institution_pending'))
            app.chat_input(key='followup_question').set_value('Michigan enrollment').run()
            next(x for x in app.selectbox if x.label=='Which institution did you mean?').set_value(170976).run()
            query.return_value={'intent':'clarify','message':'Confirmed test request'}
            app.button(key='institution_continue').click().run()
            self.assertEqual(query.call_args.kwargs['institution_choices']['michigan'],170976)
            self.assertFalse(app.session_state.get('institution_pending'))
            self.assertEqual(app.session_state['confirmed_institutions']['michigan'],170976)
            app.chat_input(key='followup_question').set_value('Another topic for Michigan').run()
            self.assertEqual(query.call_args.kwargs['institution_choices']['michigan'],170976)
            app.button(key='clear_chat').click().run()
            self.assertFalse(app.session_state.get('confirmed_institutions'))
        self.assertFalse(app.exception)

if __name__=='__main__':unittest.main()
