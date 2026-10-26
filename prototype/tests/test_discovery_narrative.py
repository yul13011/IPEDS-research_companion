"""Writing quality contracts, adversarial drafts, fallbacks and usage accounting."""
from pathlib import Path
from copy import deepcopy
from types import SimpleNamespace as NS
import sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.discovery import overview
from prototype.discovery import evidence_package,validate,render,write,QUALIFICATIONS,normalize_editorial


def valid_draft(package):
    blocks={};sources={r['record_id']:r for r in package.get('source_records',[])}
    for t in package['topics']:
        rid=t['record_ids'][0]
        quote=(sources[rid]['passages'][0]['quote_id'] if sources else next(p['quote_id'] for p in package['source_passages'] if t['topic_id'] in p['topic_ids']))
        text='Explore the documented '+('nonmedical ' if 'nonmedical' in t['description'].casefold() else '')+'measures and available breakdowns.'
        blocks.setdefault(t['survey'],[]).append({'title':'Available measures','text':text,
            'topic_ids':[t['topic_id']],'citations':[{'topic_id':t['topic_id'],'quote_id':quote}]})
    return {'blocks':[{'survey':survey,'points':points} for survey,points in blocks.items()]}


def response(draft):
    return NS(content=[NS(type='tool_use',name='write_discovery',input=draft)],stop_reason='tool_use',usage=NS(input_tokens=5000,output_tokens=800,cache_creation_input_tokens=0,cache_read_input_tokens=0))


class NarrativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.question='What data do we have on graduation rates?'
        cls.answer=overview(cls.question)
        cls.package,cls.digest=evidence_package(cls.answer,cls.question)

    def test_package_has_full_source_definitions_and_required_qualifications(self):
        self.assertEqual(len(self.digest),64)
        self.assertEqual(len(self.package['topics']),len(self.answer['discovery']['topics']))
        sources={r['record_id']:r for r in self.package['source_records']}
        for topic in self.package['topics']:
            self.assertTrue(set(topic['record_ids'])<=set(sources))
            self.assertTrue(topic['annual_coverage'])
        self.assertTrue(any(sum(len(p['text']) for p in r['passages'])>2000 for r in sources.values()))
        self.assertTrue(any('Loan-program labels differ' in q for q in self.package['required_qualifications']))
        self.assertTrue(any('provisional release' in q for q in self.package['required_qualifications']))

    def test_validated_rewrite_preserves_qualifications_evidence_and_cost(self):
        draft=valid_draft(self.package)
        before=deepcopy(self.answer)
        with patch('prototype.agent.api_key',return_value='test-only'),patch('anthropic.Anthropic') as client:
            client.return_value.messages.create.return_value=response(draft)
            answer=write(self.answer,self.question)
        self.assertEqual(answer['discovery_narrative']['status'],'accepted')
        self.assertEqual(answer['evidence'],before['evidence'])
        self.assertEqual(answer['discovery']['topics'],before['discovery']['topics'])
        self.assertEqual(self.answer,before)
        for qualification in self.package['required_qualifications']:self.assertIn(qualification,answer['message'])
        self.assertEqual(answer['discovery']['template_message'],before['message'])
        self.assertAlmostEqual(answer['model_usage']['estimated_api_usd'],.018)
        self.assertEqual(answer['latency']['live_model_calls'],1)
        args=client.return_value.messages.create.call_args.kwargs
        self.assertTrue(args['tools'][0]['strict'])
        self.assertEqual(args['tool_choice']['type'],'auto')
        self.assertNotIn('sql',args['tools'][0]['input_schema']['properties'])

    def test_reject_bad_references_quotes_numbers_scope_and_unreadable_drafts(self):
        good=valid_draft(self.package)
        mutations=[lambda p:p['blocks'][0]['points'][0]['citations'][0].update(quote_id='R999999P0'),
            lambda p:p['blocks'][0]['points'][0]['citations'][0].update(quote_id='Invented field without evidence'),
            lambda p:p['blocks'][0]['points'][0].update(text='Explore 999 percent completion.'),
            lambda p:p['blocks'][0]['points'][0].update(text='All institutions have comparable measures.'),
            lambda p:p['blocks'][0]['points'][0].update(text='Available from 1900 through 2099.'),
            lambda p:p['blocks'][0]['points'][0].update(text='Explore on-time graduation rates.'),
            lambda p:p['blocks'][0]['points'].pop(),
            lambda p:p['blocks'][0]['points'][0].update(text='Word '*60),
            lambda p:p['blocks'][0].update(survey='Invented survey')]
        for mutation in mutations:
            draft=deepcopy(good);mutation(draft)
            with self.assertRaises(Exception):validate(draft,self.package)

    def test_material_scope_and_different_concepts_cannot_be_dropped_or_merged(self):
        faculty=overview('What data do we have on faculty?');package,_=evidence_package(faculty,'faculty')
        draft=valid_draft(package)
        for block in draft['blocks']:
            for point in block['points']:
                topic=next(t for t in package['topics'] if t['topic_id']==point['topic_ids'][0])
                if 'nonmedical' in topic['description'].casefold():point['text']='Explore nonmedical staff measures.'
        validate(draft,package)
        for block in draft['blocks']:
            for point in block['points']:
                if 'nonmedical' in point['text']:
                    point['text']='Explore staff measures.'
                    with self.assertRaises(ValueError):validate(draft,package)
                    point['text']='Explore nonmedical staff measures.'
        merged=deepcopy(draft);points=merged['blocks'][0]['points']
        points[0]['topic_ids']+=points[1]['topic_ids'];points[0]['citations']+=points[1]['citations'];points.pop(1)
        with self.assertRaises(ValueError):validate(merged,package)
        # Established units and ordinary words are not equivalence/identifier claims.
        draft['blocks'][0]['points'][0]['text']='Explore full-time-equivalent measures and institution sector.'
        validate(draft,package)

    def test_release_year_qualification_is_preserved(self):
        answer=overview('What data do we have on graduation rates from 2020 through 2022?')
        package,_=evidence_package(answer,'graduation rates 2020 through 2022')
        self.assertFalse(any('provisional release' in q for q in package['required_qualifications']))
        draft=valid_draft(package)
        validate(draft,package)
        self.assertIn('Year filters select source releases, not necessarily the observation years.',render(draft,answer,package))

    def test_small_editorial_overrun_does_not_discard_verified_answer(self):
        from prototype.discovery import words
        package=deepcopy(self.package);draft=valid_draft(package)
        total=sum(len(words(p['title']+' '+p['text'])) for b in draft['blocks'] for p in b['points'])
        package['max_prose_words']=total-1
        checks=validate(draft,package)
        self.assertEqual(checks['prose_words'],total)
        package['max_prose_words']=total//2
        with self.assertRaises(ValueError):validate(draft,package)
        package['max_prose_words']=total-1
        draft['blocks'][0]['points'][0]['citations'][0]['quote_id']='Invented passage'
        with self.assertRaises(ValueError):validate(draft,package)

    def test_verified_title_dates_move_to_details_but_unknown_years_are_rejected(self):
        draft=valid_draft(self.package)
        draft['blocks'][0]['points'][0]['title']='Available measures, 2022 aid year'
        corrected,changes=normalize_editorial(draft,self.package)
        validate(corrected,self.package)
        self.assertEqual(corrected['blocks'][0]['points'][0]['title'],'Available measures')
        self.assertEqual(len(changes),1)
        self.assertEqual(draft['blocks'][0]['points'][0]['title'],'Available measures, 2022 aid year')
        annual=deepcopy(self.package)
        annual['topics'][0]['reporting_periods']=['Academic year 2022-23']
        draft['blocks'][0]['points'][0]['title']='Available measures, 2022-23 aid year'
        corrected,changes=normalize_editorial(draft,annual)
        self.assertEqual(corrected['blocks'][0]['points'][0]['title'],'Available measures')
        self.assertEqual(len(changes),1)
        draft['blocks'][0]['points'][0]['title']='Available measures, 2099 aid year'
        corrected,changes=normalize_editorial(draft,self.package)
        self.assertFalse(changes)
        with self.assertRaises(ValueError):validate(corrected,self.package)

    def test_invalid_or_unavailable_writer_falls_back_and_preserves_billed_usage(self):
        bad=valid_draft(self.package);bad['blocks'][0]['points'][0]['citations'][0]['quote_id']='unsupported made-up quote'
        with patch('prototype.agent.api_key',return_value='test-only'),patch('anthropic.Anthropic') as client:
            client.return_value.messages.create.return_value=response(bad)
            answer=write(self.answer,self.question)
            self.assertEqual(answer['message'],self.answer['message'])
            self.assertEqual(answer['discovery_narrative']['status'],'fallback')
            self.assertAlmostEqual(answer['model_usage']['estimated_api_usd'],.018)
            client.return_value.messages.create.side_effect=TimeoutError('provider timeout')
            answer=write(self.answer,self.question)
            self.assertEqual(answer['message'],self.answer['message'])
            self.assertFalse(answer['model_usage']['usage_complete'])
            self.assertIsNone(answer['model_usage']['estimated_api_usd'])

    def test_offline_no_match_and_missing_key_make_no_api_calls(self):
        with patch('anthropic.Anthropic',side_effect=AssertionError('No call expected')):
            self.assertNotIn('discovery_narrative',overview(self.question))
            self.assertNotIn('discovery_narrative',overview('What data do we have on xylophoniczebras?',use_model=True))
            with patch('prototype.agent.api_key',return_value=None):
                answer=write(self.answer,self.question)
                self.assertEqual(answer['latency']['live_model_calls'],0)
                self.assertEqual(answer['discovery_narrative']['status'],'fallback')

    def test_all_routes_forward_writer_settings_and_skip_analytical_planning(self):
        from prototype.agent import ask
        from prototype.institution_confirmation import ask as wrapped
        with patch('prototype.discovery.interpret',return_value=({'status':'no_verified_expansion','calls':0,'elapsed_seconds':0,'ambiguous':False,'verified':[]},[],None)),patch('prototype.discovery.write',side_effect=lambda a,q,m:{**a,'writer_model':m}) as writer,patch('prototype.agent.model_plan',side_effect=AssertionError('No analytical planning')),patch('prototype.memory.resolve',side_effect=AssertionError('No topic rewriting')),patch('prototype.institution_confirmation.mentions',side_effect=AssertionError('No institution resolution')):
            for route in [ask,wrapped]:
                answer=route(self.question,use_model=True,model='claude-haiku-5-5')
                self.assertEqual(answer['writer_model'],'claude-haiku-5-5')
            self.assertEqual(writer.call_count,2)

    def test_chat_displays_rewrite_with_detailed_coverage_and_audit(self):
        from prototype.tests.test_intent_router import decision,USAGE
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=True
        app.button(key='nav_ask').click().run()
        with patch('prototype.intent_router.interpret',return_value=(decision('discovery',self.question),USAGE,{})),patch('prototype.discovery.interpret',return_value=({'status':'no_verified_expansion','calls':0,'elapsed_seconds':0,'ambiguous':False,'verified':[]},[],None)),patch('prototype.agent.api_key',return_value='test-only'),patch('anthropic.Anthropic') as client:
            client.return_value.messages.create.return_value=response(valid_draft(self.package))
            app.chat_input(key='initial_question').set_value(self.question).run()
        self.assertFalse(app.exception)
        answer=app.session_state['history'][-1]['answer']
        self.assertEqual(answer['discovery_narrative']['status'],'accepted')
        self.assertTrue(any(e.label=='Detailed catalog coverage' for e in app.expander))
        self.assertTrue(any(e.label=='Answer construction and source checks' for e in app.expander))


if __name__=='__main__':unittest.main()
