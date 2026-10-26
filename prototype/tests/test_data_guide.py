"""Beginner orientation stays grounded in loaded source documentation."""
import unittest
from prototype import discovery as data_guide,coverage,conversation as working_analysis
from prototype.tests.test_request_tasks import query


class DataGuideTests(unittest.TestCase):
    def test_all_topics_have_actual_source_documentation(self):
        guide=data_guide.get()
        self.assertEqual(len(guide['sections']),12)
        for section in guide['sections']:
            self.assertTrue(section['source_refs'])
            self.assertTrue(all(r['description'] and r['table_name'] for r in section['source_refs']))
        self.assertIn('not individual student records',guide['markdown'])

    def test_broad_orientation_and_topic_search(self):
        self.assertEqual(len(data_guide.guide_answer()['guide']['section_ids']),12)
        self.assertIn('staff',data_guide.guide_answer('faculty employees salary')['guide']['section_ids'])
        self.assertIn('does not prove',data_guide.guide_answer('qzxabc')['message'])

    def test_overview_followed_by_years_is_a_release_inventory(self):
        answer=coverage.answer(query('overview',scope_mode='dataset'))
        state=working_analysis.update({},answer,turn=1)
        years=coverage.answer(query('periods',inherit_working=True,time_basis='working'),state)
        self.assertEqual(years['coverage']['available_periods'],list(range(2015,2025)))
        self.assertEqual(years['coverage']['time_basis'],'source_release')
        self.assertIn('Observation periods depend',years['message'])

    def test_topic_guide_years_do_not_claim_all_variable_coverage(self):
        answer=data_guide.guide_answer('admissions')
        state=working_analysis.update({},answer,turn=1)
        years=coverage.answer(query('periods',inherit_working=True,time_basis='working'),state)
        self.assertEqual(years['coverage']['time_basis'],'source_release')
        self.assertIn('vary by field',years['message'])

    def test_cached_document_cannot_be_mutated_by_a_caller(self):
        guide=data_guide.get();guide['sections'].clear()
        self.assertEqual(len(data_guide.get()['sections']),12)

    def test_years_after_legacy_discovery_do_not_repeat_a_topic_search(self):
        for topic in ['faculty','qzxabcxzz']:
            state=working_analysis.from_history([{'question':'What information is available?',
                'answer':{'mode':'data discovery','query':topic}}])
            from unittest.mock import patch
            with patch('prototype.catalog.search',side_effect=AssertionError('Year enumeration must not run topic search')):
                years=coverage.answer(query('periods',inherit_working=True,time_basis='working'),state)
            self.assertEqual(years['coverage']['available_periods'],list(range(2015,2025)))
            self.assertEqual(years['coverage']['time_basis'],'source_release')
            self.assertNotIn('bounded topic search',years['message'])
            self.assertTrue('vary by field' in years['message'] or 'does not establish' in years['message'])



if __name__=='__main__':unittest.main()

