"""Regression: a single-year academic/fiscal request must not be rejected when the data
year is encoded in the COLUMN (e.g. IC 'Published tuition and fees 2022-23' = chg2ay2),
not the table period. Before the fix catalog_execution blocked these with 'the source
reporting period does not cover the requested year'. See COVERAGE_SWEEP_2026-10-27.md
(fix class #2)."""
from pathlib import Path
import sys, sqlite3, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / ".packages"), str(ROOT)]
from prototype.catalog import DATA, annual_path, readonly
from prototype.catalog_execution import execute_catalog
from prototype.intent_checks import CURRENT, contract

SMITH = 167835


def rid(table, var):
    db = sqlite3.connect(DATA / "metadata_catalog.sqlite")
    r = db.execute("SELECT record_id FROM records WHERE release_id LIKE 'IPEDS_2023%' "
                   "AND table_name=? AND variable_name=?", (table, var)).fetchone()
    db.close()
    return r[0] if r else None


class PeriodBindingTests(unittest.TestCase):
    def test_prior_year_tuition_not_blocked_by_table_period(self):
        q = "What was the published tuition and fees at Smith College for 2022-23?"
        plan = {"version": 1, "institutions": ["Smith College"], "source_years": [2023],
                "requested_time": {"basis": "academic", "description": "Academic year 2022-23"},
                "selections": [{"record_id": rid("IC2023_AY", "chg2ay2"), "role": "measure"}],
                "filters": [], "group_by_record_ids": [], "calculations": [], "joins": [],
                "output": "answer", "assumptions": [], "clarification_questions": []}
        token = CURRENT.set(contract(q))
        try:
            ans = execute_catalog({"catalog_plan": plan}, q)
        finally:
            CURRENT.reset(token)
        self.assertIn("result", ans, "blocked: " + str(ans.get("message")))
        rows = ans["result"]["rows"]
        self.assertTrue(rows, "no rows published")
        with readonly(annual_path(2023)) as db:
            expected = db.execute("SELECT CHG2AY2 FROM IC2023_AY WHERE UNITID=?", (SMITH,)).fetchone()[0]
        self.assertEqual(rows[0]["value"], expected)
        # period reflects the field's data year, not the table's collection span
        self.assertIn("2022", str(rows[0]["reporting_period"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
