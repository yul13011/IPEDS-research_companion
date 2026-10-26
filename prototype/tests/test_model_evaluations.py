"""Benchmark outages must stop spend and remain separate from model accuracy."""
from pathlib import Path
from threading import Event
from unittest.mock import Mock,patch
import json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT),str(ROOT/'evaluations')]
import compare_models_current as bench

class EvaluationTests(unittest.TestCase):
    def test_account_limit_stops_after_first_provider_request(self):
        client=Mock();client.messages.create.side_effect=RuntimeError('You have reached your specified API usage limits.')
        def interpret(*args):return client.messages.create(model='claude-sonnet-5-5')
        with tempfile.TemporaryDirectory() as temporary,patch.multiple(bench,
            STOP=Event(),STOP_REASON='',CALLS=[],RECORDS=[],BLOCKED_ATTEMPTS=[],TARGET=Path(temporary)/'result.json'):
            with patch.object(bench,'fixtures',return_value=({},{})),patch.object(bench,'get_client',return_value=client),patch('prototype.intent_router.interpret',side_effect=interpret),patch.object(sys,'argv',['benchmark','--live']):
                self.assertEqual(bench.main(),2)
            report=json.loads(bench.TARGET.read_text())
            self.assertEqual(len(report['calls']),1)
            self.assertIn('account usage limit',report['stop_reason'])
            self.assertEqual(report['cases'],[])

    def test_unavailable_requests_do_not_lower_model_accuracy(self):
        model='claude-sonnet-5-5'
        records=[dict(model=model,passed=True,usage_complete=True,wall_seconds=5,estimated_api_usd=.01,group='numerical'),
            dict(model=model,passed=False,usage_complete=False,wall_seconds=.1,estimated_api_usd=0,group='numerical')]
        with tempfile.TemporaryDirectory() as temporary,patch.multiple(bench,
            TARGET=Path(temporary)/'result.json',RECORDS=records,CALLS=[],BLOCKED_ATTEMPTS=[]):
            bench.save();summary=json.loads(bench.TARGET.read_text())['models'][0]
        self.assertEqual((summary['passed'],summary['total'],summary['unavailable']),(1,1,1))
        self.assertEqual(summary['median_seconds'],5)

    def test_latency_uses_only_matched_successes(self):
        from summarize_model_reliability import comparison
        records=[]
        for model in ['a','b']:
            for case,passed,seconds in [('same',True,6),('different',model=='a',20 if model=='a' else .1)]:
                records.append(dict(model=model,round=1,case=case,passed=passed,wall_seconds=seconds,
                    usage_complete=True,estimated_api_usd=.01))
        summary=comparison({'cases':records,'expected_tasks_per_model':2})
        self.assertTrue(summary['complete']);self.assertEqual(summary['matched_successful_pairs'],1)
        self.assertEqual([m['matched_success_median_seconds'] for m in summary['models']],[6,6])
        self.assertEqual([m['passed'] for m in summary['models']],[2,1])

    def test_writer_resume_keeps_completed_outcomes(self):
        import compare_narrative_settings as writer
        done={'topic':'faculty','round':1,'configuration':'sonnet_current','model':'claude-sonnet-5-5',
            'status':'accepted','evidence_sha256':'kept','usage':{'usage_complete':True,'estimated_api_usd':0}}
        unavailable={**done,'configuration':'haiku_current','status':'fallback',
            'usage':{'usage_complete':False,'estimated_api_usd':None}}
        response={'discovery_narrative':{'status':'accepted','evidence_sha256':'new'},
            'model_usage':{'usage_complete':True,'estimated_api_usd':0}}
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'evaluations').mkdir()
            target=root/'evaluations/narrative_settings_comparison.json'
            target.write_text(json.dumps({'records':[done,unavailable]}),encoding='utf-8')
            with patch.object(writer,'ROOT',root),patch.object(writer,'overview',return_value={}),patch.object(writer,'write',return_value=response) as write,patch.object(sys,'argv',['writer','--live','--resume']),patch('builtins.print'):
                writer.main()
            result=json.loads(target.read_text(encoding='utf-8'))
        self.assertEqual(write.call_count,23)
        self.assertEqual(len(result['records']),24)
        self.assertEqual(result['records'][0],done)
        self.assertEqual(len(result['previous_unavailable_attempts']),1)

    def test_exact_css_hex_equivalents_are_not_chart_failures(self):
        from summarize_model_reliability import comparison
        self.assertTrue(bench.color_is('#FF0000','red'))
        self.assertTrue(bench.color_is('#0000ff','blue'))
        self.assertFalse(bench.color_is('#0000ff','red'))
        c=dict(model='a',round=1,case='compound_style__variation',usage_complete=True,
            passed=False,checks={'color':False,'title':True},wall_seconds=1,estimated_api_usd=.01,
            presentation={'series_colors':{'Harvard University':'#ff0000'}})
        summary=comparison({'cases':[c],'expected_tasks_per_model':1})
        self.assertEqual(summary['models'][0]['passed'],1)
        self.assertFalse(c['passed'])  # Original audit remains unchanged.
        self.assertEqual(len(summary['grading_corrections']),1)

    def test_yield_allows_only_verified_explanatory_denominator(self):
        expected={'admissions':[100,20,20],'yield_followup':[10,50]}
        rows=[{'metric':'matriculants','value':10,'status':'ok'},
            {'metric':'yield_rate','value':50,'status':'ok'},
            {'metric':'admits','value':20,'status':'ok'}]
        self.assertTrue(bench.yield_values_match(rows,expected))
        rows[-1]['value']=21
        self.assertFalse(bench.yield_values_match(rows,expected))
        rows[-1].update(metric='applicants',value=20)
        self.assertFalse(bench.yield_values_match(rows,expected))

if __name__=='__main__':unittest.main()
