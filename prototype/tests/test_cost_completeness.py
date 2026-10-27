"""Regression: a current-year cost/tuition/price plan must deterministically return the complete,
correct DRVCOST2024 column set (tuition & fees + total price on campus, in-state AND out-of-state),
so public schools always get out-of-state too and a populated field is always used. See the cost
field-selection fix (bug B)."""
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / ".packages"), str(ROOT)]
from prototype.catalog_planner import _complete_cost_selection, _drvcost_ids


def plan(selection_vars_ids=(999999,)):
    return {"version": 1, "institutions": ["Test College"], "source_years": [2024],
            "requested_time": {"basis": "academic", "description": "2024-25"},
            "selections": [{"record_id": r, "role": "measure"} for r in selection_vars_ids],
            "filters": [], "group_by_record_ids": [], "calculations": [], "joins": [],
            "output": "table", "assumptions": [], "clarification_questions": []}


class CostCompletenessTests(unittest.TestCase):
    def setUp(self):
        self.full = _drvcost_ids(["TUFEYR3", "CINSON", "COTSON"])
        self.tuition = _drvcost_ids(["TUFEYR3"])
        self.assertTrue(self.full and self.tuition)

    def _ids(self, out):
        return [s["record_id"] for s in out["selections"]]

    def test_general_cost_gets_full_residency_set(self):
        out = _complete_cost_selection(plan(), "how much does University of Connecticut cost?")
        self.assertEqual(self._ids(out), self.full)

    def test_explicit_tuition_only(self):
        out = _complete_cost_selection(plan(), "published tuition and required fees for 2024-25")
        self.assertEqual(self._ids(out), self.tuition)

    def test_non_cost_question_untouched(self):
        p = plan()
        out = _complete_cost_selection(p, "how many bachelor's degrees did it award in 2024?")
        self.assertEqual(self._ids(out), [999999])

    def test_net_price_left_to_planner(self):
        p = plan()
        out = _complete_cost_selection(p, "what is the net price at University of Connecticut?")
        self.assertEqual(self._ids(out), [999999])

    def test_residency_specific_tuition_left_to_planner(self):
        p = plan()
        out = _complete_cost_selection(p, "what is the out-of-state tuition at University of Connecticut?")
        self.assertEqual(self._ids(out), [999999])

    def test_historical_year_left_to_planner(self):
        p = plan(); p["source_years"] = [2020]
        out = _complete_cost_selection(p, "how much did it cost in 2020?")
        self.assertEqual(self._ids(out), [999999])


if __name__ == "__main__":
    unittest.main(verbosity=2)
