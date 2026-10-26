"""Annual evidence retrieval and short clarification regression checks."""
from pathlib import Path
from copy import deepcopy
import sys, unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from analysis_catalog.catalog import connection
from prototype.catalog_planner import read_source_series,expand_annual_plan,proposal_answer
from prototype.memory import context, resolve_option
from prototype.agent import ask


class SourceSeriesTests(unittest.TestCase):
    def test_ten_year_faculty_template_executes_and_matches_independent_sources(self):
        from prototype.catalog_execution import execute_catalog
        from prototype.catalog import readonly,annual_path
        with connection() as db:
            ids={r['variable_name']:r['record_id'] for r in db.execute("SELECT variable_name,record_id FROM definitions WHERE table_name='EAP2024'")}
            codes={(r['variable_name'],r['code_value']):r['record_id'] for r in db.execute("SELECT variable_name,code_value,record_id FROM source.code_values WHERE table_name='EAP2024'")}
        p={'version':1,'institutions':['Yale University'],'source_years':[2024],
           'requested_time':{'basis':'fall','description':'Fall 2015 through 2024'},
           'selections':[{'record_id':ids['EAPTOT'],'role':'measure'}],
           'filters':[{'record_id':ids[k],'operator':'eq','values':[v],'code_record_ids':[codes[k,v]]} for k,v in [('OCCUPCAT','210'),('FACSTAT','10'),('EAPCAT','21010')]],
           'group_by_record_ids':[],'calculations':[],'joins':[],'output':'chart','assumptions':[],'clarification_questions':[]}
        expanded=expand_annual_plan(p,list(range(2015,2025)))
        self.assertEqual(len(expanded['filters']),30)
        q='Yale University instructional staff with faculty status, full- plus part-time, Fall 2015 through 2024'
        answer=execute_catalog(proposal_answer(expanded,q),q)
        self.assertTrue('result' in answer,answer['message'])
        self.assertEqual(len(answer['result']['rows']),10)
        self.assertIn('instructional staff',answer['message'].lower())
        self.assertIn('faculty status',answer['message'].lower())
        for row in answer['result']['rows']:
            year=row['observation_year']
            with readonly(annual_path(year)) as db:
                # Independent population predicate, using the full/part-time sum
                # to cross-check the selected source-reported total.
                raw=db.execute(f'SELECT EAPFT,EAPPT FROM EAP{year} WHERE UNITID=130794 AND OCCUPCAT=210 AND FACSTAT=10').fetchall()
            self.assertEqual(len(raw),1)
            self.assertEqual(row['value'],float(raw[0][0])+float(raw[0][1]))
        with patch('prototype.catalog_planner.read_source_series',return_value={'fields':[]}):
            with self.assertRaises(ValueError):expand_annual_plan(p,[2023])
        altered=read_source_series([2023],[{'record_id':s['record_id'],'code_values':next((f['values'] for f in p['filters'] if f['record_id']==s['record_id']),[])} for s in p['selections']+p['filters']])
        next(d for d in altered['fields'] if d['variable']=='FACSTAT')['codes'][0]['matches'][0]['value_label']='Changed category meaning'
        with patch('prototype.catalog_planner.read_source_series',return_value=altered):
            with self.assertRaisesRegex(ValueError,'category label changed'):expand_annual_plan(p,[2023])

        # The compact tool follows the same repair path as an ordinary proposal.
        from prototype.catalog_planner import model_catalog_plan
        from prototype.tests.test_catalog_planner import block,response
        bad=deepcopy(p);bad['filters']=[f for f in bad['filters'] if f['record_id']!=ids['FACSTAT']]
        with patch('anthropic.Anthropic') as client:
            client.return_value.messages.create.side_effect=[response(block('submit_annual_plan',{'template':bad,'years':list(range(2015,2025))})),response(block('submit_annual_plan',{'template':p,'years':list(range(2015,2025))}))]
            planned=model_catalog_plan(q)
        self.assertTrue(planned['preflight_validation']['execution_eligible'])
        self.assertEqual(len(planned['validation_attempts']),1)

    def test_each_annual_definition_and_category_comes_from_its_own_release(self):
        with connection() as db:
            seed=db.execute("SELECT record_id FROM definitions WHERE table_name='EAP2024' AND variable_name='OCCUPCAT'").fetchone()[0]
        result=read_source_series(list(range(2015,2025)),[{'record_id':seed,'code_values':['210','nonexistent']}])
        self.assertEqual(len(result['fields']),10)
        with connection() as db:
            for item in result['fields']:
                row=db.execute('SELECT release_id,table_name,variable_name FROM definitions WHERE record_id=?',(item['record_id'],)).fetchone()
                self.assertIn(str(item['year']),row['release_id'])
                self.assertEqual(row['table_name'],'EAP'+str(item['year']))
                category=item['codes'][0]['matches'][0]
                source=db.execute('SELECT release_id,code_value,value_label FROM source.code_values WHERE record_id=?',(category['record_id'],)).fetchone()
                self.assertEqual(source['release_id'],row['release_id'])
                self.assertEqual(source['code_value'],'210')
                self.assertEqual(category['value_label'],source['value_label'])
                self.assertEqual(item['codes'][1]['matches'],[])
        with self.assertRaises(ValueError):read_source_series([2014],[{'record_id':seed,'code_values':[]}])
        with self.assertRaises(ValueError):read_source_series(list(range(2015,2025)),[{'record_id':seed,'code_values':[]}]*5)

    def test_letter_choice_preserves_scope_without_second_model_interpretation(self):
        q='number of faculty of Yale University in the past 10 years'
        h=[{'question':q,'answer':{'intent':'clarify','message':'Which count, Fall 2015-2024? Options: (a) instructional staff with faculty status (full- plus part-time, EAP table), (b) full-time only, or (c) all faculty? If you have no preference, I will use (a).','catalog_context':{'kind':'catalog_clarification','question':q}}}]
        b=context(h)
        choice=resolve_option('(a)',b)
        self.assertIn('full- plus part-time',choice['question'])
        self.assertIn('Fall 2015-2024',choice['question'])
        self.assertNotIn('(b)',choice['question'])
        self.assertIsNone(resolve_option('new question',b))
        self.assertIsNone(resolve_option('(d)',b))
        with patch('prototype.memory.resolve',side_effect=AssertionError('No extra model call')),patch('prototype.agent._answer',return_value={'intent':'clarify','message':'test'}) as execute:
            answer=ask('(a)',use_model=True,conversation=h)
        self.assertEqual(answer['resolved_question'],choice['question'])
        self.assertEqual(execute.call_args.args[0],choice['question'])
        h[0]['answer'].pop('catalog_context')
        self.assertIsNone(resolve_option('(a)',context(h)))


if __name__=='__main__':unittest.main()
