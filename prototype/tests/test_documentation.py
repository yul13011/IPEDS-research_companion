"""Documentation intents and cross-route follow-ups never retrieve statistics."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from prototype.institution_confirmation import ask
from prototype.definitions import classify


class DocumentationTests(unittest.TestCase):
    def test_initial_types_route_without_institution_or_statistics(self):
        with patch('prototype.institution_confirmation.mentions',side_effect=AssertionError('Identity lookup')):
            for q,kind in [('What does the label SAOUTLT mean?','label'),
                           ('How is admission rate calculated?','calculation'),
                           ('What is the formula for admission rate?','calculation'),
                           ('Define faculty','definition')]:
                a=ask(q)
                self.assertEqual(a['documentation_context']['kind'],kind)
                self.assertNotIn('result',a)
            with patch('prototype.discovery.overview',return_value={'intent':'discover','mode':'data discovery'}) as overview:
                a=ask('What information do you have on Pell?')
                self.assertEqual(a['documentation_context']['kind'],'discovery')
                self.assertIn('Pell',overview.call_args.args[0])

    def test_definition_to_calculation_and_discovery(self):
        history=[{'question':'Define admission rate','answer':ask('Define admission rate')}]
        before=deepcopy(history)
        a=ask('How is it calculated?',conversation=history)
        self.assertIn('Admissions total ÷ Applicants total × 100',a['message'])
        self.assertTrue(a['documentation_context']['context_resolved'])
        self.assertEqual(a['latency']['live_model_calls'],0)
        with patch('prototype.discovery.overview',return_value={'intent':'discover','mode':'data discovery'}) as overview:
            ask('What other data do you have on that?',conversation=history)
            self.assertIn('admission rate',overview.call_args.args[0])
        self.assertEqual(history,before)

    def test_analysis_followup_preserves_label_and_release(self):
        h=[{'question':'statistics','answer':{'result':{'plan':{'metrics':['admission_rate'],'years':[2023]},
                'rows':[{'measure':'Admission rate','value':20},{'measure':'Admission rate','value':30}]}}}]
        a=ask('What does this label mean?',conversation=h)
        self.assertEqual(a['definition_lookup']['source_years'],[2023])
        self.assertEqual(a['definition_lookup']['reviewed_measure'],'admission_rate')

    def test_ambiguous_followup_then_named_selection(self):
        h=[{'question':'discovery','answer':{'mode':'data discovery','query':'financial aid','evidence':[
            {'variable_name':'UPGRNTN','title':'Number of undergraduate students awarded Federal Pell grants'},
            {'variable_name':'PGRNT_P','title':'Percent of full-time first-time undergraduates awarded Pell grants'}]}}]
        a=ask('What does that label mean?',conversation=h)
        self.assertEqual(a['intent'],'clarify')
        self.assertIn('Number of undergraduate',a['message'])
        h.append({'question':'What does that label mean?','answer':a})
        b=ask('Number of undergraduate students awarded Federal Pell grants',conversation=h)
        self.assertEqual(b['intent'],'definition')
        self.assertIn('demonstrated financial need',b['message'])

    def test_missing_context_and_unknown_formula_do_not_invent(self):
        self.assertEqual(ask('How is it calculated?')['intent'],'clarify')
        a=ask('How is quantum banana index calculated?')
        self.assertIn('not established an app calculation formula',a['message'])
        self.assertEqual(a['definition_lookup']['status'],'not_established')
        self.assertNotIn('result',a)

    def test_multiyear_followup_asks_release_and_accepts_year(self):
        h=[{'question':'trend','answer':{'result':{'plan':{'metrics':['admission_rate'],'years':[2022,2023]},
            'rows':[{'measure':'Admission rate'}]}}}]
        a=ask('How is it calculated?',conversation=h)
        self.assertEqual(a['intent'],'clarify')
        self.assertIn('Which release',a['message'])
        h.append({'question':'How is it calculated?','answer':a})
        b=ask('2023',conversation=h)
        self.assertEqual(b['definition_lookup']['source_years'],[2023])

    def test_explicit_topic_overrides_history_and_mixed_request_not_captured(self):
        h=[{'question':'Define faculty','answer':ask('Define faculty')}]
        a=ask('How is admission rate calculated?',conversation=h)
        self.assertEqual(a['documentation_context']['terms'],['admission rate'])
        for q in ['Define faculty and show Yale faculty counts','How many students does Yale have?',
                  'How is admission rate calculated and show Yale admission rates?']:
            self.assertIsNone(classify(q),q)


if __name__=='__main__':unittest.main()
