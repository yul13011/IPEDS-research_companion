"""Regression for F-B: "N-year <sector noun>" (e.g. "four-year institutions") must
not be read as an N-year reporting window. See DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md."""
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / '.packages'), str(ROOT)]
from prototype.time_scope import trend_years
from prototype.intent_checks import contract


class SectorNotDurationTests(unittest.TestCase):
    def test_four_year_institutions_is_not_a_window(self):
        q = ("What was the overall six-year graduation rate for four-year "
             "institutions in the United States for the 2016 entering cohort?")
        self.assertIsNone(trend_years(q, default_end=2018))
        c = contract(q)
        self.assertFalse(c['temporal'], 'sector phrase must not flag a longitudinal trend')
        self.assertIsNone(c['period_count'], '"four-year" must not become a 4-period count')
        self.assertEqual(c['expected_years'], [2016])

    def test_two_year_colleges_is_not_a_window(self):
        q = "How many two-year colleges are in California in 2023?"
        self.assertIsNone(trend_years(q))
        c = contract(q)
        self.assertFalse(c['temporal'])
        self.assertIsNone(c['period_count'])
        self.assertEqual(c['expected_years'], [2023])

    def test_genuine_durations_still_bind(self):
        self.assertEqual(trend_years('Plot Yale total enrollment over the past 10 years'),
                         list(range(2015, 2025)))
        self.assertEqual(trend_years('Show Smith enrollment for the last five years'),
                         list(range(2020, 2025)))
        c = contract('Plot Yale total enrollment over the past 10 years')
        self.assertTrue(c['temporal'])
        self.assertEqual(c['period_count'], 10)

    def test_n_year_trend_phrase_still_binds(self):
        self.assertEqual(trend_years('Show a 10-year trend of Yale enrollment'),
                         list(range(2015, 2025)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
