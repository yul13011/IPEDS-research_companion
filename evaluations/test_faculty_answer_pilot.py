"""Guard checks for the evaluation harness, not new production app behavior."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from evaluations.faculty_answer_pilot import package,CASES,bound_plans,execute_and_verify,render

class PilotGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg=package(CASES[0])
        cls.review={'action':'answer','source_year':2024,'employment':'both','medical_scope':'include',
            'reason':'','clarification_question':'','interpretations':[]}
        for sid,occupation,label in [('all','100','All staff with faculty status'),('instructional','210','Instructional staff with faculty status')]:
            evidence=[c['record_id'] for c in cls.pkg['categories'] if c['variable_name']=='OCCUPCAT' and c['code_value']==occupation or c['variable_name']=='FACSTAT' and c['code_value']=='10']
            cls.review['interpretations'].append({'id':sid,'label':label,'occupation_code':occupation,'faculty_status_codes':['10'],'evidence_ids':evidence})
    def test_two_scopes_match_independent_sql(self):
        rows,_=execute_and_verify(self.review,self.pkg)
        self.assertEqual(rows[0]['values'],{'EAPFT':4688,'EAPPT':1047,'EAPTOT':5735})
        self.assertEqual(rows[1]['values'],{'EAPFT':2995,'EAPPT':805,'EAPTOT':3800})
    def test_invalid_evidence_and_wrong_year_are_blocked_before_execution(self):
        for bad in ['reference','category','year']:
            review=deepcopy(self.review)
            if bad=='reference':review['interpretations'][0]['evidence_ids'].append(999999999)
            if bad=='category':review['interpretations'][0]['faculty_status_codes']=['999']
            if bad=='year':review['source_year']=2030
            with patch('evaluations.faculty_answer_pilot.execute',side_effect=AssertionError('No query')):
                with self.assertRaises(ValueError):execute_and_verify(review,self.pkg)
    def test_unconfirmed_institution_cannot_be_queried(self):
        pkg=deepcopy(self.pkg);pkg['confirmed_institution']=None
        with self.assertRaises(ValueError):bound_plans(self.review,pkg)
    def test_writer_cannot_insert_numbers_or_invent_citations(self):
        rows,_=execute_and_verify(self.review,self.pkg)
        writing={'lead_scope_id':'all','explanation':'The instructional population is a subset of staff with faculty status.','evidence_ids':[self.pkg['table']['record_id']]}
        text=render(self.pkg,self.review,rows,writing)
        for required in ['5,735','3,800','medical-school','not a separately identified','November 1','provisional','must not be added']:self.assertIn(required,text)
        for key,value in [('explanation','There are 9000 faculty.'),('evidence_ids',[99999999]),('lead_scope_id','invented')]:
            bad={**writing,key:value}
            with self.assertRaises(ValueError):render(self.pkg,self.review,rows,bad)

if __name__=='__main__':unittest.main()
