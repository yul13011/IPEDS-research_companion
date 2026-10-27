"""Regression: a finance 'YYYY-YY' question must auto-resolve to the fiscal year named by its
END year instead of the collection release. '2022-23' = fiscal year 2023 = table F2223_F2 (in
the 2023-24 release), NOT F2122_F2 (in the 2022-23 release). Covers both halves of the fix:
the deterministic _align_finance_years swap in the planner, and semantic_check accepting the
span's end year so the aligned plan executes instead of being blocked / sent to clarify.
See COVERAGE_SWEEP_2026-10-27.md (finance YYYY-YY -> fiscal-year auto-resolution)."""
from pathlib import Path
import sys, sqlite3, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / ".packages"), str(ROOT)]
from prototype.catalog import DATA, annual_path, readonly
from prototype.catalog_planner import _align_finance_years
from prototype.catalog_execution import execute_catalog
from prototype.intent_checks import CURRENT, contract

YALE = 130794
Q = "What was Yale's total revenue from tuition and fees in 2022-23?"


def rid(table):
    db = sqlite3.connect(DATA / "metadata_catalog.sqlite")
    r = db.execute("SELECT record_id FROM records WHERE table_name=? AND variable_name='F2D01'",
                   (table,)).fetchone()
    db.close()
    return r[0] if r else None


class FinanceYearAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.f2122 = rid("F2122_F2")   # fiscal year 2022 (2022-23 release)
        self.f2223 = rid("F2223_F2")   # fiscal year 2023 (2023-24 release)
        self.assertTrue(self.f2122 and self.f2223)

    def _plan(self, record_id, source_year):
        return {"version": 1, "institutions": ["Yale University"], "source_years": [source_year],
                "requested_time": {"basis": "fiscal", "description": f"FY{source_year}"},
                "selections": [{"record_id": record_id, "role": "measure"}], "filters": [],
                "group_by_record_ids": [], "calculations": [], "joins": [], "output": "answer",
                "assumptions": ["The period is fiscal year 2022, as labelled in the 2022-23 release."],
                "clarification_questions": []}

    def test_wrong_fiscal_year_is_realigned(self):
        out = _align_finance_years(self._plan(self.f2122, 2022), Q)
        self.assertEqual(out["selections"][0]["record_id"], self.f2223)
        self.assertEqual(out["source_years"], [2023])
        # the stale 'fiscal year 2022' note is replaced by an accurate disclosure
        self.assertTrue(any("ending 2023" in a for a in out["assumptions"]))
        self.assertFalse(any("fiscal year 2022" in a.lower() for a in out["assumptions"]))

    def test_already_correct_is_left_alone(self):
        out = _align_finance_years(self._plan(self.f2223, 2023), Q)
        self.assertEqual(out["selections"][0]["record_id"], self.f2223)

    def test_multi_year_trend_untouched(self):
        out = _align_finance_years(self._plan(self.f2122, 2022),
                                   "tuition revenue from 2015-16 to 2022-23")
        self.assertEqual(out["selections"][0]["record_id"], self.f2122)

    def test_aligned_plan_executes_to_fy2023_value(self):
        plan = self._plan(self.f2223, 2023)
        token = CURRENT.set(contract(Q))
        try:
            ans = execute_catalog({"catalog_plan": plan}, Q)
        finally:
            CURRENT.reset(token)
        self.assertIn("result", ans, "blocked: " + str(ans.get("message")))
        rows = ans["result"]["rows"]
        self.assertTrue(rows, "no rows published")
        with readonly(annual_path(2023)) as db:
            expected = db.execute("SELECT F2D01 FROM F2223_F2 WHERE UNITID=?", (YALE,)).fetchone()[0]
        self.assertEqual(rows[0]["value"], expected)
        self.assertIn("2023", str(rows[0]["reporting_period"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
