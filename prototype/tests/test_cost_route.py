"""Regression: the deterministic cost route resolves institution names from the directory and
answers current-year cost/tuition/price questions without any model call, so cost always returns
the complete, correct columns instead of randomly clarifying or taking a different planner path.
See the cost consistency fix (bug C)."""
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / ".packages"), str(ROOT)]
from prototype.catalog_planner import cost_plan, _cost_institution_names
from prototype.model_policy import _deterministic_cost_answer


class CostRouteTests(unittest.TestCase):
    def test_directory_name_resolution(self):
        self.assertIn("129020", _cost_institution_names("how much does University of Connecticut cost?")[0])
        self.assertIn("168218", _cost_institution_names("how much does Wellesley college cost?")[0])
        self.assertIn("167835", _cost_institution_names("how much does Smith College cost?")[0])

    def test_cost_plan_fires_for_cost_question(self):
        self.assertEqual(cost_plan("how much does University of Connecticut cost?")["intent"], "catalog_plan")

    def test_cost_plan_skips_unrelated(self):
        self.assertIsNone(cost_plan("how many degrees did Smith College award in 2023?"))
        self.assertIsNone(cost_plan("what is the net price at University of Connecticut?"))
        self.assertIsNone(cost_plan("how much did Smith College cost in 2019?"))
        self.assertIsNone(cost_plan("how much does cost?"))  # no resolvable institution

    def test_deterministic_answer_is_complete_and_modelfree(self):
        a = _deterministic_cost_answer("how much does University of Connecticut cost?", None, [])
        self.assertIsNotNone(a)
        self.assertEqual(a["intent"], "analyze")
        self.assertEqual(a.get("model_usage", {}).get("calls"), 0)  # no API call
        values = {r.get("value") for r in a["result"]["rows"]}
        self.assertIn(40744, values)   # in-state total price
        self.assertIn(63412, values)   # out-of-state total price (public school completeness)

    def test_non_cost_question_not_intercepted(self):
        self.assertIsNone(_deterministic_cost_answer("how many degrees did Smith College award in 2023?", None, []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
