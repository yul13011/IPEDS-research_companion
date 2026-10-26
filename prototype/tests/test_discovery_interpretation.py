"""Model search proposals are optional; catalog evidence and original scope govern."""
from pathlib import Path
from types import SimpleNamespace as NS
from copy import deepcopy
import sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.discovery_interpretation import interpret,catalog_matches,validate_proposal,merge_hits,combine_usage
from prototype.discovery import overview
from prototype.discovery_narrative import evidence_package


def proposal(concept='Net price',terms=None,ambiguous=False):
    return {'interpretations':[{'concept':concept,'search_terms':terms or ['average net price'],'uncertainty':''}],'ambiguous':ambiguous}


def reply(payload,name='interpret_discovery'):
    return NS(content=[NS(type='tool_use',name=name,input=payload)],stop_reason='tool_use',
        usage=NS(input_tokens=1000,output_tokens=200,cache_creation_input_tokens=0,cache_read_input_tokens=0))


class InterpretationTests(unittest.TestCase):
    def test_catalog_verification_requires_concept_and_phrase_in_same_physical_record(self):
        matches=catalog_matches('Net price','average net price',years=[2024])
        self.assertTrue(matches)
        self.assertTrue(all('2024' in r['release_id'] for r in matches))
        self.assertTrue(all(r['physical_column_present'] is not False for r in matches))
        self.assertFalse(catalog_matches('Xylophonic zebras','enrollment'))
        self.assertFalse(catalog_matches('Net price',years=[2035]))
        salary=catalog_matches('Instructional staff salaries')
        self.assertTrue(any(r['table_name'].upper().startswith('SAL') for r in salary))
        self.assertTrue(any(r['kind']=='table_definition' for r in salary))
        self.assertTrue(any(r['kind']=='variable_definition' for r in salary))

    def test_proposed_concepts_are_checked_and_made_up_concepts_rejected(self):
        draft=proposal();draft['interpretations'].append({'concept':'Xylophonic zebras','search_terms':['enrollment'],'uncertainty':''})
        with patch('prototype.agent.api_key',return_value='test-only'),patch('prototype.discovery_narrative.request',return_value=reply(draft)):
            audit,streams,usage=interpret('What information do you have on what families actually pay?','families actually pay')
        self.assertEqual([i['concept'] for i in audit['verified']],['Net price'])
        self.assertEqual(len(audit['rejected']),1)
        self.assertTrue(streams[0]);self.assertEqual(usage['calls'],1)
        self.assertAlmostEqual(usage['estimated_api_usd'],.004)
        self.assertEqual(audit['original_keywords'],'families actually pay')

    def test_invalid_proposals_cannot_add_dates_operators_or_exceed_budget(self):
        for draft in [proposal(terms=['tuition 2035']),proposal(terms=['DROP TABLE records;']),{'interpretations':[proposal()['interpretations'][0]]*6,'ambiguous':False}]:
            with self.assertRaises(Exception):validate_proposal(draft)
        extra=proposal();extra['interpretations']+=[{'concept':label,'search_terms':[label],'uncertainty':''} for label in ['Cost of attendance','Tuition and fees','Student financial aid']]
        validate_proposal(extra)

    def test_fallback_retains_original_search_and_records_unknown_cost(self):
        with patch('prototype.agent.api_key',return_value='test-only'),patch('prototype.discovery_narrative.request',side_effect=TimeoutError('timeout')):
            audit,streams,usage=interpret('What data do we have on faculty?','faculty')
        self.assertEqual(audit['status'],'fallback');self.assertFalse(streams)
        self.assertFalse(usage['usage_complete']);self.assertIsNone(usage['estimated_api_usd'])
        self.assertEqual(audit['original_keywords'],'faculty')
        with patch('prototype.agent.api_key',return_value=None),patch('prototype.discovery_narrative.request',side_effect=AssertionError('No call')):
            audit,streams,usage=interpret('What data do we have on faculty?','faculty')
        self.assertEqual(audit['calls'],0);self.assertIsNone(usage)

    def test_original_hits_survive_and_new_concept_matches_enter_overview(self):
        question='What data do we have on what families actually pay?'
        original=overview(question)
        with patch('prototype.agent.api_key',return_value='test-only'),patch('prototype.discovery_narrative.request',return_value=reply(proposal())),patch('prototype.discovery_narrative.write',side_effect=lambda a,q,m:a):
            answer=overview(question,use_model=True)
        audit=answer['discovery']['interpretation']
        self.assertEqual(answer['query'],original['query'])
        self.assertTrue(set(audit['original_hit_record_ids'])<=set(audit['merged_hit_record_ids']))
        self.assertTrue(any('net price' in i['title'].casefold() for i in answer['discovery']['topics']))
        self.assertEqual(answer['latency']['live_model_calls'],1)

    def test_failed_interpretation_preserves_baseline_topics(self):
        original=overview('What data do we have on faculty?')
        with patch('prototype.agent.api_key',return_value='test-only'),patch('prototype.discovery_narrative.request',return_value=reply({'interpretations':[],'ambiguous':False})),patch('prototype.discovery_narrative.write',side_effect=lambda a,q,m:a):
            answer=overview('What data do we have on faculty?',use_model=True)
        self.assertEqual(answer['discovery']['topics'],original['discovery']['topics'])
        self.assertEqual(answer['discovery']['interpretation']['status'],'no_verified_expansion')

    def test_everyday_salary_and_overseas_queries_find_relevant_data_areas(self):
        cases=[("What information do you have on teachers' pay?",proposal('Instructional staff salaries',['salary outlays']),lambda title:'salary outlays' in title.casefold()),
            ('What information do you have on students from overseas?',proposal('U.S. nonresident enrollment',['nonresident enrollment']),lambda title:'enrollment' in title.casefold() or 'race/ethnicity' in title.casefold())]
        for question,draft,relevant in cases:
            with patch('prototype.agent.api_key',return_value='test-only'),patch('prototype.discovery_narrative.request',return_value=reply(draft)),patch('prototype.discovery_narrative.write',side_effect=lambda a,q,m:a):
                answer=overview(question,use_model=True)
            self.assertTrue(any(relevant(i['title']) for i in answer['discovery']['topics']))
            audit=answer['discovery']['interpretation']
            self.assertTrue(set(audit['original_hit_record_ids'])<=set(audit['merged_hit_record_ids']))

    def test_ambiguity_and_year_scope_are_preserved_in_evidence_package(self):
        draft=proposal(ambiguous=True);draft['interpretations'][0]['uncertainty']='Published charges and net price differ.'
        with patch('prototype.agent.api_key',return_value='test-only'),patch('prototype.discovery_narrative.request',return_value=reply(draft)),patch('prototype.discovery_narrative.write',side_effect=lambda a,q,m:a):
            answer=overview('What information do we have on what families pay in 2024?',use_model=True)
        self.assertEqual(answer['discovery']['requested_release_years'],[2024])
        self.assertTrue(all('2024' in row['release_id'] for t in answer['discovery']['interpretation']['verified'] for row in t['source_matches']))
        package,_=evidence_package(answer,'what families pay')
        self.assertTrue(package['verified_search_concepts'])
        self.assertTrue(any('not treated as equivalent' in s for s in package['required_qualifications']))

    def test_round_robin_keeps_original_and_expanded_records(self):
        originals=[{'record_id':i} for i in range(4)]
        expanded=[{'record_id':i} for i in range(3,7)]
        merged=merge_hits(originals,[],[expanded])
        self.assertEqual({r['record_id'] for r in merged},set(range(7)))
        self.assertEqual(len(merged),7)
        self.assertEqual(merged[:2],[originals[0],expanded[0]])

    def test_stage_usage_combines_and_unknown_cost_is_never_zero(self):
        a={'model':'x','calls':1,'input_tokens':100,'output_tokens':10,'estimated_api_usd':.01,'usage_complete':True}
        b={**a,'estimated_api_usd':.02}
        merged=combine_usage(a,b)
        self.assertEqual(merged['calls'],2);self.assertAlmostEqual(merged['estimated_api_usd'],.03)
        self.assertEqual(len(merged['stages']),2)
        b['estimated_api_usd']=None;b['usage_complete']=False
        self.assertIsNone(combine_usage(a,b)['estimated_api_usd'])
        self.assertFalse(combine_usage(a,b)['usage_complete'])

    def test_two_stage_chat_flow_preserves_audit_and_combines_usage(self):
        from prototype.agent import DEFAULT_MODEL
        from prototype.tests.test_intent_router import decision,USAGE
        from streamlit.testing.v1 import AppTest
        from prototype.tests.test_discovery_narrative import valid_draft,response
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=True
        app.session_state['model_choice']=DEFAULT_MODEL  # This fixture checks Sonnet pricing.
        app.button(key='nav_ask').click().run()
        def model_reply(model,schema,system,payload,**kwargs):
            if kwargs.get('tool_name')=='interpret_discovery':return reply(proposal())
            draft=valid_draft(payload)
            return response(draft)
        with patch('prototype.intent_router.interpret',return_value=(decision('discovery','What data do we have on college tuition?'),USAGE,{})),patch('prototype.agent.api_key',return_value='test-only'),patch('prototype.discovery_narrative.request',side_effect=model_reply) as client:
            app.chat_input(key='initial_question').set_value('What data do we have on college tuition?').run()
        self.assertFalse(app.exception)
        answer=app.session_state['history'][-1]['answer']
        self.assertEqual(answer['discovery']['interpretation']['status'],'verified')
        self.assertEqual(answer['discovery_narrative']['status'],'accepted')
        self.assertEqual(answer['latency']['live_model_calls'],3)
        self.assertEqual(answer['model_usage']['calls'],3)
        self.assertEqual(len(answer['model_usage']['stages']),2)
        self.assertAlmostEqual(answer['model_usage']['estimated_api_usd'],.023)
        self.assertEqual(client.call_count,2)


if __name__=='__main__':unittest.main()
