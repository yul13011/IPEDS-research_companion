"""Output-layer ranking: order per-institution rows by one measure, keep top N."""
import os, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / '.packages')]

from prototype.catalog_execution import apply_ranking, ranking_metric
from prototype.catalog_planner import _validate_shape, NEUTRAL_RANKING


def _rows():
    m = 'ADM{YEAR}::RATE'
    return [
        {'institution': 'Yale', 'unitid': 1, 'metric': m, 'value': 4.0, 'status': 'ok', 'observation_year': 2024},
        {'institution': 'Wesleyan', 'unitid': 2, 'metric': m, 'value': 16.0, 'status': 'ok', 'observation_year': 2024},
        {'institution': 'Trinity', 'unitid': 3, 'metric': m, 'value': 29.0, 'status': 'ok', 'observation_year': 2024},
        {'institution': 'Nodata', 'unitid': 4, 'metric': m, 'value': None, 'status': 'missing', 'observation_year': 2024},
    ]


SPECS = {'ADM{YEAR}::RATE': {'label': 'Percent admitted - total', 'unit': 'percent'}}


class RankingTests(unittest.TestCase):
    def test_ascending_limit_one_picks_minimum(self):
        notes = []
        out = apply_ranking(_rows(), {'by': '', 'direction': 'ascending', 'limit': 1}, SPECS, notes)
        self.assertEqual([r['institution'] for r in out], ['Yale'])
        self.assertTrue(notes and 'lowest first' in notes[0])

    def test_descending_limit_two_picks_top_two_in_order(self):
        out = apply_ranking(_rows(), {'by': 'Percent admitted', 'direction': 'descending', 'limit': 2}, SPECS, [])
        self.assertEqual([r['institution'] for r in out], ['Trinity', 'Wesleyan'])

    def test_missing_values_excluded_from_ranking(self):
        out = apply_ranking(_rows(), {'by': '', 'direction': 'ascending', 'limit': 10}, SPECS, [])
        self.assertNotIn('Nodata', [r['institution'] for r in out])
        self.assertEqual(len(out), 3)

    def test_neutral_ranking_is_a_no_op(self):
        rows = _rows()
        self.assertEqual(apply_ranking(rows, dict(NEUTRAL_RANKING), SPECS, []), rows)
        self.assertEqual(apply_ranking(rows, None, SPECS, []), rows)

    def test_ranking_metric_prefers_named_then_sole(self):
        self.assertEqual(ranking_metric('percent admitted', _rows(), SPECS), 'ADM{YEAR}::RATE')
        self.assertEqual(ranking_metric('', _rows(), SPECS), 'ADM{YEAR}::RATE')

    def test_schema_defaults_and_bounds(self):
        plan = {'version': 1, 'institutions': ['Yale'], 'source_years': [2024],
                'requested_time': {'basis': 'fall', 'description': 'x'}, 'selections': [{'record_id': 1, 'role': 'measure'}],
                'filters': [], 'group_by_record_ids': [], 'calculations': [], 'joins': [], 'output': 'answer',
                'assumptions': [], 'clarification_questions': []}
        _validate_shape(dict(plan))  # no ranking -> defaulted, validates
        bad = {**plan, 'ranking': {'by': '', 'direction': 'ascending', 'limit': 0}}
        with self.assertRaises(ValueError):
            _validate_shape(bad)  # active direction needs a positive limit


if __name__ == '__main__':
    unittest.main(verbosity=2)
