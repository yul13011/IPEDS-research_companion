"""Definition intent uses source metadata without institution or value queries."""
from pathlib import Path
from copy import deepcopy
import sys,json,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.definitions import answer,request,can_answer,candidates
from prototype.institution_confirmation import ask
from prototype.tests.test_catalog_planner import block,response
from prototype.catalog import readonly,DATA


class DefinitionTests(unittest.TestCase):
    def test_explicit_definition_routes_before_identity_and_statistical_planning(self):
        questions=['What is the definition of instructional staff?','What does UNITID mean?',
                   'Define graduation rate','How is full-time undergraduate enrollment defined?',
                   'What is faculty?','What is SAOUTLT?','What is admission rate?']
        with (patch('prototype.institution_confirmation.mentions',side_effect=AssertionError('No institution lookup')),
              patch('prototype.agent._answer',side_effect=AssertionError('No analysis planner')),
              patch('prototype.query_engine.execute',side_effect=AssertionError('No statistical query')),
              patch('prototype.catalog.annual_path',side_effect=AssertionError('No annual fact database'))):
            for q in questions:
                a=ask(q,use_model=False)
                self.assertEqual(a['intent'],'definition',q);self.assertNotIn('result',a)

    def test_definitions_are_exact_supplied_source_excerpts(self):
        for q in ['Define instructional staff','What does UNITID mean?','Define faculty',
                  'Define graduation rate','Define full-time undergraduate enrollment','Define admission rate']:
            a=ask(q,use_model=False)
            self.assertEqual(a['mode'],'source definition',q)
            self.assertEqual(a['definition_lookup']['status'],'defined',q)
            self.assertNotIn('result',a)
            lookup={r['record_id']:r for r in a['evidence']}
            for p in a['definition_lookup']['passages']:
                self.assertIn(p['excerpt'],lookup[p['record_id']]['definition'])
            self.assertTrue(all(r.get('source_file') and r.get('source_row') for r in a['evidence']))

    def test_instructional_staff_retains_combined_functions_and_faculty_separation(self):
        staff=ask('Define instructional staff')
        self.assertIn('Instruction combined with research and/or public service',staff['message'])
        self.assertNotIn('equated to month contract',staff['message'])
        faculty=ask('What is faculty?')
        self.assertIn('separate from the activities',faculty['message'])
        self.assertIn('not included in this category',faculty['message'])
        self.assertNotIn('faculty-supervised',faculty['message'])

    def test_variable_table_year_scope_and_unavailable_year(self):
        a=ask('What does SAL2023_IS.SAOUTLT mean?')
        self.assertEqual(a['definition_lookup']['source_years'],[2023])
        self.assertFalse(a['definition_lookup']['default_latest_release'])
        self.assertTrue(all(r['table_name']=='SAL2023_IS' for r in a['evidence']))
        self.assertIn('base salaries only',a['message'])
        missing=ask('Define instructional staff in 2030')
        self.assertIn('no other year has been substituted',missing['message'])
        self.assertNotIn('result',missing)
        multiple=ask('Define faculty in 2019 and 2024')
        self.assertIn('one source release at a time',multiple['message'])
        self.assertNotIn('result',multiple)

    def test_generic_graduation_rate_does_not_claim_universal_six_year_definition(self):
        a=ask('Define graduation rate')
        self.assertIn('source-specific scope',a['message'])
        self.assertIsNone(a['definition_lookup']['reviewed_measure'])
        self.assertNotIn('six-year bachelor graduation rate — reviewed app definition',a['message'])
        self.assertIn('first-time',a['message']);self.assertIn('full-time',a['message'])
        self.assertTrue(any('cohort' in r['definition'].lower() for r in a['evidence']))

    def test_reviewed_rate_uses_its_actual_formula_and_supporting_definitions(self):
        with patch('prototype.discovery_narrative.request',side_effect=AssertionError('Reviewed definition needs no model')):
            a=ask('What is admission rate?',use_model=True)
        self.assertEqual(a['definition_lookup']['status'],'defined')
        self.assertIn('Admissions total ÷ Applicants total × 100',a['message'])
        self.assertIn('Supporting source definitions',a['message'])
        self.assertNotIn('could not establish',a['message'])
        self.assertEqual(a['latency']['live_model_calls'],0)

    def test_unknown_term_and_mixed_questions_do_not_invent_or_drop_scope(self):
        a=ask('Define quantum banana index')
        self.assertEqual(a['definition_lookup']['status'],'not_established')
        self.assertIn('does not prove the term is absent',a['message'])
        for q in ['Define faculty and show Yale faculty counts','What is Yale admission rate in fall 2024?',
                  'What is the tuition for Harvard?','How many students does Yale have?','What is tuition in 2024?',
                  'What is the difference between Yale and Harvard admission rates in 2024?']:
            self.assertFalse(can_answer(q),q)

    def test_model_can_select_only_verbatim_inspected_passages(self):
        records=candidates('instructional staff',[2024]);r=next(r for r in records if r['direct_match'])
        good=response(block('select_definition',{'passages':[{'record_id':r['record_id'],'excerpt':r['excerpt']}]}))
        with patch('prototype.agent.api_key',return_value='test'),patch('prototype.discovery_narrative.request',return_value=good):
            a=answer('Define instructional staff',use_model=True)
        self.assertEqual(a['definition_lookup']['selection'],'accepted')
        self.assertEqual(a['model_usage']['calls'],1)
        bad=response(block('select_definition',{'passages':[{'record_id':r['record_id'],'excerpt':'Invented unsupported definition of staff, not in a supplied source.'}]}))
        with patch('prototype.agent.api_key',return_value='test'),patch('prototype.discovery_narrative.request',return_value=bad):
            a=answer('Define instructional staff',use_model=True)
        self.assertNotIn('Invented unsupported',a['message'])
        self.assertEqual(a['model_usage']['calls'],1)
        self.assertIn('Instruction combined with research',a['message'])

    def test_transport_failure_preserves_unknown_cost_and_safe_fallback(self):
        with patch('prototype.agent.api_key',return_value='test'),patch('prototype.discovery_narrative.request',side_effect=TimeoutError('test')):
            a=answer('Define instructional staff',use_model=True)
        self.assertIsNone(a['model_usage']['estimated_api_usd'])
        self.assertEqual(a['model_usage']['calls'],1)
        self.assertIn('Instruction combined with research',a['message'])

    def test_complete_glossary_entry_cannot_be_shortened_to_drop_qualifications(self):
        records=candidates('faculty',[2024]);r=next(r for r in records if r.get('glossary_excerpt'))
        excerpt=r['glossary_excerpt'].split('. ')[0]+'.'
        short=response(block('select_definition',{'passages':[{'record_id':r['record_id'],'excerpt':excerpt}]}))
        with patch('prototype.agent.api_key',return_value='test'),patch('prototype.discovery_narrative.request',return_value=short):
            a=answer('Define faculty',use_model=True)
        self.assertIn('separate from the activities',a['message'])
        self.assertIn('complete glossary',a['definition_lookup']['selection'])

    def test_comparison_and_followup_use_metadata_without_mutating_history(self):
        a=ask('What is the difference between faculty and instructional staff?')
        self.assertTrue(a['definition_lookup']['comparison'])
        self.assertIn('separate from the activities',a['message'])
        h=[{'question':'Define instructional staff','answer':ask('Define instructional staff')}]
        before=deepcopy(h);follow=ask('What does that mean?',conversation=h)
        self.assertEqual(follow['definition_lookup']['term'],'instructional staff')
        self.assertEqual(h,before)

    def test_ui_keeps_full_source_evidence_under_popover(self):
        from streamlit.testing.v1 import AppTest
        a=ask('Define instructional staff')
        def app():
            import streamlit as st
            from prototype.ui import render_answer
            render_answer(st.session_state['definition_answer'],'definition')
        app=AppTest.from_function(app,default_timeout=60)
        app.session_state['definition_answer']=a;app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('popover')),1)
        self.assertTrue(any('Definitions & sources' in str(p.proto) for p in app.get('popover')))

    def test_noncompact_usage_handles_unknown_tokens_and_cost(self):
        from streamlit.testing.v1 import AppTest
        with patch('prototype.agent.api_key',return_value='test'),patch('prototype.discovery_narrative.request',side_effect=TimeoutError('test')):
            a=answer('Define instructional staff',use_model=True)
        def app():
            import streamlit as st
            from prototype.ui import render_answer
            render_answer(st.session_state['definition_answer'],'definition',compact=False)
        app=AppTest.from_function(app,default_timeout=60)
        app.session_state['definition_answer']=a;app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any('unavailable' in str(c.value) for c in app.caption))


if __name__=='__main__':unittest.main()
