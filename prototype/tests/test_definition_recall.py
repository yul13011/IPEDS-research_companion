"""Regression for F-E: natural phrasings of reviewed measures resolve to their
reviewed definition instead of 'could not establish a definition'. See
DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md (F-E)."""
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / '.packages'), str(ROOT)]
from prototype.definitions import reviewed, answer


class ReviewedTermMappingTests(unittest.TestCase):
    def test_six_year_grad_rate_maps_to_all(self):
        for t in ['six-year graduation rate', '6-year graduation rate',
                  'six-year bachelor graduation rate']:
            self.assertEqual(reviewed(t)['id'], 'graduation_rate', t)

    def test_bare_graduation_rate_stays_generic(self):
        # IPEDS has 4-/6-/8-year rates; a bare term must not claim the six-year measure.
        self.assertIsNone(reviewed('graduation rate'))
        self.assertIsNone(reviewed('women graduation rate'))

    def test_subgroups_with_six_year_map_to_their_measure(self):
        self.assertEqual(reviewed("men's six-year graduation rate")['id'], 'men_graduation_rate')
        self.assertEqual(reviewed('women six-year graduation rate')['id'], 'women_graduation_rate')
        self.assertEqual(reviewed('Pell six-year graduation rate')['id'], 'pell_graduation_rate')
        self.assertEqual(reviewed('non-Pell six-year graduation rate')['id'], 'nonpell_graduation_rate')
        self.assertEqual(reviewed('nonresident six-year graduation rate')['id'], 'nonresident_graduation_rate')

    def test_cohort_and_completers_distinguished(self):
        self.assertEqual(reviewed('adjusted bachelor cohort')['id'], 'graduation_cohort')
        self.assertEqual(reviewed('six-year bachelor completers')['id'], 'graduation_completers')

    def test_non_measure_terms_do_not_misfire(self):
        for t in ['faculty salary', 'library books', 'tuition revenue',
                  'distance education', 'retention rate']:
            self.assertIsNone(reviewed(t), t)


class DefinitionAnswerTests(unittest.TestCase):
    def test_six_year_graduation_rate_is_defined(self):
        a = answer('Define six-year graduation rate')
        self.assertEqual(a['definition_lookup']['status'], 'defined')
        self.assertEqual(a['definition_lookup']['reviewed_measure'], 'graduation_rate')
        self.assertIn('reviewed app definition', a['message'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
