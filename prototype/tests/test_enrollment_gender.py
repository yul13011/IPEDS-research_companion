"""First-time undergraduate gender interpretation, retrieval and percentages."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from analysis_catalog.catalog import connection
from prototype.agent import ask
from prototype.catalog import annual_path, readonly
from prototype.catalog_planner import enrollment_gender_plan
from prototype.catalog_execution import execute_catalog

QUESTION="show me the gender break down of Yale College's first year undergrads"


class EnrollmentGenderTests(unittest.TestCase):
    def test_exact_ten_year_prompt_and_shares_match_all_annual_sources(self):
        from prototype.institution_confirmation import ask as chat_ask
        question='Yale undergraduates by gender in the past 10 years'
        with patch('prototype.catalog_planner.model_catalog_plan',side_effect=AssertionError('This source-defined breakdown does not need model catalog search')):
            counts=chat_ask(question,use_model=False)
            shares=ask(question+' as percentages',use_model=True)
        self.assertEqual(counts['intent'],'analyze')
        self.assertEqual(shares['intent'],'analyze')
        self.assertFalse(counts['catalog_plan']['calculations'])
        self.assertEqual(len(shares['catalog_plan']['calculations']),20)
        self.assertEqual(len(counts['result']['rows']),30)
        self.assertEqual(len(shares['result']['rows']),20)
        for year in range(2015,2025):
            with readonly(annual_path(year)) as db:
                source=db.execute(f'SELECT EFTOTLM,EFTOTLW,EFTOTLT FROM EF{year}A WHERE UNITID=130794 AND EFALEVEL=2').fetchone()
            actual={r['measure']:r['value'] for r in counts['result']['rows'] if r['observation_year']==year}
            self.assertEqual(actual,{'Grand total men':source[0],'Grand total women':source[1],'Grand total':source[2]})
            actual={r['measure']:r for r in shares['result']['rows'] if r['observation_year']==year}
            for label,value in [('Men',source[0]),('Women',source[1])]:
                row=actual[label+' as percent of undergraduates']
                self.assertEqual(row['denominator'],source[2])
                self.assertAlmostEqual(row['value'],100*value/source[2])
        self.assertEqual(shares['latency']['live_model_calls'],0)

    def test_all_undergraduate_gender_cannot_silently_use_first_time_population(self):
        q='Yale undergraduates by gender in 2024'
        answer=enrollment_gender_plan(q)
        with connection() as db:
            code=db.execute("SELECT record_id FROM source.code_values WHERE table_name='EF2024A' AND variable_name='EFALEVEL' AND code_value='4'").fetchone()[0]
        answer['catalog_plan']['filters'][0].update(values=['4'],code_record_ids=[code])
        self.assertNotIn('result',execute_catalog(answer,q))
        self.assertIsNone(enrollment_gender_plan(q+' by income'))

    def test_percentage_followup_preserves_population_without_general_search(self):
        from prototype.institution_confirmation import ask as chat_ask
        q='Yale undergraduates by gender in the past 10 years'
        counts=chat_ask(q,use_model=False)
        history=[{'question':q,'answer':counts}]
        resolved='For Yale University undergraduates (total undergraduate, all attendance statuses), show fall enrollment by gender (men and women) for fall 2015 through fall 2024 as percentages of total undergraduate enrollment.'
        with patch('prototype.catalog_planner.model_catalog_plan',side_effect=AssertionError('Equivalent gender scopes must retain the source-bound path')):
            explicit=ask(resolved,use_model=True)
            continuation=chat_ask('show percentages',use_model=False,conversation=history)
        self.assertEqual(explicit['intent'],'analyze')
        self.assertEqual(continuation['intent'],'analyze')
        expected=[r['value'] for r in explicit['result']['rows']]
        self.assertEqual(expected,[r['value'] for r in continuation['result']['rows']])

    def test_exact_user_question_returns_counts_without_model(self):
        with patch('prototype.agent.model_plan',side_effect=AssertionError('Do not reduce the requested gender population')):
            with patch('prototype.catalog_planner.model_catalog_plan',side_effect=AssertionError('Source-bound starter covers this question')):
                answer=ask(QUESTION,use_model=True)
        self.assertEqual(answer['intent'],'analyze')
        self.assertFalse(answer['catalog_plan']['calculations'])
        self.assertEqual(answer['catalog_plan']['filters'][0]['values'],['4'])
        rows={r['measure']:r['value'] for r in answer['result']['rows']}
        with readonly(annual_path(2024)) as db:
            source=db.execute('SELECT EFTOTLM,EFTOTLW,EFTOTLT FROM EF2024A WHERE UNITID=130794 AND EFALEVEL=4').fetchone()
        self.assertEqual(rows,{'Grand total men':source[0],'Grand total women':source[1],'Grand total':source[2]})
        self.assertEqual(source[2],1554)
        self.assertTrue(any('not a separately reported Yale College' in w for w in answer['result']['warnings']))
        self.assertTrue(any('no residual or zero is inferred' in w for w in answer['result']['warnings']))
        self.assertEqual(answer['latency']['live_model_calls'],0)

    def test_percentages_have_one_numerator_each_and_same_population_total(self):
        answer=ask('Show Yale first-time undergraduate enrollment by gender as percentages for 2024')
        self.assertEqual(len(answer['catalog_plan']['calculations']),2)
        self.assertTrue(all(len(c['input_record_ids'])==1 for c in answer['catalog_plan']['calculations']))
        rows=answer['result']['rows'];self.assertEqual(len(rows),2)
        self.assertAlmostEqual(sum(r['value'] for r in rows),100)
        for r in rows:
            self.assertEqual(r['denominator'],1554)
            self.assertAlmostEqual(r['value'],r['numerator']/1554*100)

    def test_wrong_population_and_multi_numerator_formula_rejected(self):
        original=enrollment_gender_plan(QUESTION)
        bad=deepcopy(original)
        with connection() as db:
            code=db.execute("SELECT record_id FROM source.code_values WHERE release_id='IPEDS_2024-25_Provisional' AND table_name='EF2024A' AND variable_name='EFALEVEL' AND code_value='2'").fetchone()[0]
        bad['catalog_plan']['filters'][0].update(values=['2'],code_record_ids=[code])
        self.assertNotIn('result',execute_catalog(bad,QUESTION))
        bad=enrollment_gender_plan(QUESTION+' as percentages')
        bad['catalog_plan']['calculations'][0]['input_record_ids'].append(bad['catalog_plan']['calculations'][1]['input_record_ids'][0])
        repaired=execute_catalog(bad,QUESTION+' as percentages')
        self.assertIn('result',repaired)
        self.assertEqual(len(repaired['result']['rows']),2)
        self.assertTrue(repaired['catalog_proposal']['normalization'])

    def test_attendance_years_and_unrecognized_scope(self):
        for qualifier,code in [('full-time','24'),('part-time','44')]:
            answer=ask(f'Show Yale {qualifier} first-year undergrads by gender in 2024')
            self.assertEqual(answer['catalog_plan']['filters'][0]['values'],[code])
            if qualifier=='part-time':self.assertTrue(all(r['status']=='missing' for r in answer['result']['rows']))
        for extra in ['by income','by race','excluding transfers','including transfer students','only women','nonbinary students']:
            self.assertIsNone(enrollment_gender_plan(QUESTION+' '+extra),extra)
        unavailable=ask(QUESTION+' in 2025')
        self.assertEqual(unavailable['intent'],'clarify')
        corrected=ask('2024 instead',unavailable['catalog_context'])
        self.assertEqual(corrected['intent'],'analyze')
        self.assertEqual(corrected['catalog_plan']['source_years'],[2024])


if __name__=='__main__':unittest.main()
