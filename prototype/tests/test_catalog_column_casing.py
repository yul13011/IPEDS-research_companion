"""Regression: the catalog executor must read a value whose codebook variable_name casing
differs from the physical column (IC/COST tables use 'chg2ay3' while the column is
'CHG2AY3'). Before the fix this returned 'not reported'. No live model calls.
See COVERAGE_SWEEP_2026-10-27.md (fix class #1)."""
from pathlib import Path
import sys, sqlite3, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / ".packages"), str(ROOT)]
from prototype.catalog import DATA, annual_path, readonly
from prototype.catalog_execution import execute_catalog

SMITH = 167835


def rid(table, var):
    db = sqlite3.connect(DATA / "metadata_catalog.sqlite")
    r = db.execute("SELECT record_id FROM records WHERE release_id LIKE 'IPEDS_2023%' "
                   "AND table_name=? AND variable_name=?", (table, var)).fetchone()
    db.close()
    return r[0] if r else None


class ColumnCasingTests(unittest.TestCase):
    def test_lowercase_codebook_field_reads_uppercase_physical_value(self):
        r1, r2 = rid("IC2023_AY", "chg2ay3"), rid("IC2023_AY", "chg3ay3")
        self.assertIsNotNone(r1); self.assertIsNotNone(r2)
        plan = {"version": 1, "institutions": ["Smith College"], "source_years": [2023],
                "requested_time": {"basis": "academic", "description": "Academic year 2023-24"},
                "selections": [{"record_id": r1, "role": "measure"},
                               {"record_id": r2, "role": "measure"}],
                "filters": [], "group_by_record_ids": [], "calculations": [], "joins": [],
                "output": "answer", "assumptions": [], "clarification_questions": []}
        ans = execute_catalog({"catalog_plan": plan},
                              "What was the published tuition and fees at Smith College for 2023-24?")
        self.assertIn("result", ans, "executor did not run: " + str(ans.get("message")))
        rows = ans["result"]["rows"]
        self.assertTrue(rows, "no rows published")
        with readonly(annual_path(2023)) as db:
            expected = db.execute("SELECT CHG2AY3 FROM IC2023_AY WHERE UNITID=?", (SMITH,)).fetchone()[0]
        values = [r["value"] for r in rows]
        self.assertIn(expected, values, f"real value {expected} missing from {values}")
        self.assertNotIn(None, values, "a field read as missing (casing regression)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
