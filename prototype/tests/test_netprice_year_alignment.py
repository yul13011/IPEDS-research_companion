"""Regression: net-price columns (NPIST0/1/2) encode a rolling 3-year window that shifts
by release, so a single-year request must bind to the column whose title carries THAT year.
The planner sometimes selected NPIST2 ('2023-24') for a '2022-23' request; the deterministic
_align_field_years swap fixes it to NPIST1 ('2022-23'). See COVERAGE_SWEEP_2026-10-27.md
(net-price reclassification)."""
from pathlib import Path
import sys, sqlite3, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / ".packages"), str(ROOT)]
from prototype.catalog import DATA
from prototype.catalog_planner import _align_field_years


def rid(span):
    db = sqlite3.connect(DATA / "metadata_catalog.sqlite")
    r = db.execute("SELECT record_id FROM records WHERE table_name='COST2_2024_netprice' "
                   "AND variable_name=? ", (span,)).fetchone()
    db.close()
    return r[0] if r else None


class NetPriceYearAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.npist1 = rid("NPIST1")   # title '...2022-23'
        self.npist2 = rid("NPIST2")   # title '...2023-24'
        self.assertTrue(self.npist1 and self.npist2)

    def _plan(self, record_id):
        return {"version": 1, "institutions": ["Alabama A & M University"], "source_years": [2024],
                "selections": [{"record_id": record_id, "role": "measure"}], "filters": [],
                "group_by_record_ids": [], "calculations": [], "joins": [], "output": "answer",
                "assumptions": [], "clarification_questions": []}

    def test_wrong_year_column_is_realigned(self):
        q = "net price for Alabama A & M University in 2022-23"
        out = _align_field_years(self._plan(self.npist2), q)
        self.assertEqual(out["selections"][0]["record_id"], self.npist1)

    def test_correct_column_is_left_alone(self):
        q = "net price for Alabama A & M University in 2022-23"
        out = _align_field_years(self._plan(self.npist1), q)
        self.assertEqual(out["selections"][0]["record_id"], self.npist1)

    def test_multi_year_request_untouched(self):
        q = "net price from 2021-22 to 2023-24"
        out = _align_field_years(self._plan(self.npist2), q)
        self.assertEqual(out["selections"][0]["record_id"], self.npist2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
