"""Regression: the national-aggregate SQL fast path (_combined_pushdown) returns results
identical to the row path (_relational_reduce), and only triggers for an eligible combined
single-field sum over a population. A ratio or a count stays on the row path. See the
national-aggregate pushdown (query_engine)."""
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / ".packages"), str(ROOT)]
from prototype.populations import EVALUATING
from prototype.query_engine import inspect, execute, _combined_pushdown, _relational_reduce
from evaluations.run_population_engine_benchmarks import build


class PushdownTests(unittest.TestCase):
    def setUp(self):
        EVALUATING.set(True)

    def test_national_sum_matches_row_path(self):
        plan, _ = build(24, 2018)  # national degrees/certificates awarded, 2017-18
        b = inspect(plan, "national completions")
        ref = plan["outputs"][0]["reference"]
        pushed = _combined_pushdown(b, plan, "x")
        self.assertIsNotNone(pushed, "eligible national sum should take the fast path")
        cur_p, meta_p, aud_p = pushed
        cur_r, meta_r, *_ = _relational_reduce(b, plan, "x")
        self.assertEqual(cur_p[ref].iloc[0], cur_r[ref].iloc[0])
        self.assertEqual(int(cur_p[ref + "__available"].iloc[0]), int(cur_r[ref + "__available"].iloc[0]))
        self.assertEqual(int(cur_p[ref + "__requested"].iloc[0]), int(cur_r[ref + "__requested"].iloc[0]))
        self.assertEqual(meta_p[ref]["grain"], [])
        self.assertTrue(aud_p[0].get("pushdown"))

    def test_execute_national_sum_value(self):
        plan, _ = build(24, 2018)
        row = execute(plan, "national completions")["rows"][0]
        self.assertEqual(row["value"], 5020910.0)
        self.assertEqual(row["available_rows"], 6131)
        self.assertEqual(row["requested_rows"], 6131)
        self.assertIsNone(row["unitid"])  # combined national result

    def test_count_not_pushed_down(self):
        plan, _ = build(1, 2018)  # national institution count (non-numeric field, count op)
        b = inspect(plan, "how many institutions")
        self.assertIsNone(_combined_pushdown(b, plan, "x"))

    def test_rate_not_pushed_down(self):
        plan, _ = build(20, 2016)  # national graduation rate: a pooled ratio, not a sum
        b = inspect(plan, "national graduation rate")
        self.assertIsNone(_combined_pushdown(b, plan, "x"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
