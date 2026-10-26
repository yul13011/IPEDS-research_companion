"""Regression for F-C: a concrete per-institution quantity question ("how many
books ...") must not be routed to catalog discovery. See
DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md (F-C)."""
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / '.packages'), str(ROOT)]
from prototype.intent_router import normalize_decision


def dec(route, question, relationship='new', referenced_turns=None):
    return {'route': route, 'question': question, 'relationship': relationship,
            'referenced_turns': referenced_turns or [], 'chart_edits': [],
            'documentation': {'kind': 'none', 'terms': [], 'years': []},
            'institution_mentions': [], 'target_result_id': None, 'message': ''}


class CountRoutingTests(unittest.TestCase):
    def test_count_question_reclassified_from_discovery(self):
        q = "How many books were in Harvard's library collection in 2023?"
        # Discovery rewrites the question; the original intent must be restored.
        d = normalize_decision(dec('discovery', 'What data do you have on library collections?'), q)
        self.assertEqual(d['route'], 'analysis')
        self.assertEqual(d['question'], q)

    def test_amount_question_reclassified(self):
        q = "How much revenue did Yale report from tuition in 2022?"
        d = normalize_decision(dec('discovery', 'What data do you have on finance?'), q)
        self.assertEqual(d['route'], 'analysis')

    def test_metadata_browse_stays_discovery(self):
        for q in ["How many variables describe financial aid?",
                  "What data do you have on faculty?",
                  "Which tables cover admissions?"]:
            d = normalize_decision(dec('discovery', q), q)
            self.assertEqual(d['route'], 'discovery', q)

    def test_followup_not_reclassified(self):
        q = "How many books in 2023?"
        d = normalize_decision(dec('discovery', q, relationship='followup', referenced_turns=[1]), q)
        self.assertEqual(d['route'], 'discovery')

    def test_other_routes_untouched(self):
        q = "How many books were in Harvard's library collection in 2023?"
        self.assertEqual(normalize_decision(dec('numerical', q), q)['route'], 'numerical')
        self.assertEqual(normalize_decision(dec('definition', q), q)['route'], 'definition')


if __name__ == '__main__':
    unittest.main(verbosity=2)
