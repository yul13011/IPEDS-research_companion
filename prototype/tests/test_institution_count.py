"""Regression for F-D: a bare institution headcount is answered from the directory
population (Title IV default), while measure/feature/named-geography questions fall
through. See DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md (F-D)."""
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / '.packages'), str(ROOT)]
from prototype.populations import institution_count_question, institution_count


class InstitutionCountTriggerTests(unittest.TestCase):
    def test_triggers_on_bare_counts(self):
        for q in ["How many degree-granting institutions reported to IPEDS in 2023?",
                  "How many public four-year institutions are there in 2023?",
                  "Number of private nonprofit colleges in 2022"]:
            self.assertTrue(institution_count_question(q), q)

    def test_skips_measures_features_and_named_units(self):
        for q in ["How many undergraduates enrolled at Yale in 2023?",
                  "How many institutions offer distance education in Massachusetts?",
                  "How many students graduated nationally in 2023?",
                  "What is institution 130794 enrollment?"]:
            self.assertFalse(institution_count_question(q), q)


class InstitutionCountAnswerTests(unittest.TestCase):
    def test_degree_granting_title_iv_default(self):
        a = institution_count("How many degree-granting institutions reported to IPEDS in 2023?")
        self.assertIsNotNone(a)
        self.assertEqual(a['institution_count']['count'], 3841)
        self.assertIn('Title IV', a['institution_count']['scope'])
        self.assertIn('degree-granting', a['institution_count']['scope'])
        self.assertIn('3,841', a['message'])

    def test_named_state_falls_through(self):
        # Geography the population guard rejects must return None (no national count).
        self.assertIsNone(institution_count("How many colleges are in California in 2023?"))

    def test_sector_level_scope(self):
        a = institution_count("How many public four-year institutions are there in 2023?")
        self.assertIsNotNone(a)
        self.assertIn('public', a['institution_count']['scope'])
        self.assertIn('four-year', a['institution_count']['scope'])
        self.assertGreater(a['institution_count']['count'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
