"""Regression for F-A: a finance question for fiscal year "YYYY-YY" must bind the
finance table whose fiscal year ends that year (F2223 for 2022-23), not the
collection-year folder's prior-year table (F2122). See
DIAGNOSIS_AND_FIX_PLAN_2026-10-26.md (F-A)."""
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / '.packages'), str(ROOT)]
from prototype.query_engine import check_fiscal_year

Q = "What was Yale's total revenue from tuition and fees in 2022-23?"


class FinanceFiscalYearTests(unittest.TestCase):
    def test_wrong_fiscal_table_is_rejected(self):
        # F2122 = FY2021-22; request is FY2022-23 -> must raise.
        with self.assertRaises(ValueError) as ctx:
            check_fiscal_year([{'table': 'F2122_F2'}], Q)
        self.assertIn('2023', str(ctx.exception))
        self.assertIn('F2223', str(ctx.exception))

    def test_correct_fiscal_table_passes(self):
        # F2223 = FY2022-23 -> no error.
        check_fiscal_year([{'table': 'F2223_F2'}], Q)
        check_fiscal_year([{'table': 'F2223_F1A'}], Q)

    def test_non_finance_tables_are_untouched(self):
        # Enrollment/admissions tables for a "2022-23" academic phrasing must not trip it.
        check_fiscal_year([{'table': 'EF2022A'}, {'table': 'ADM2022'}], Q)

    def test_no_fiscal_span_no_check(self):
        check_fiscal_year([{'table': 'F2122_F2'}], "Yale tuition revenue in fiscal year 2022")

    def test_earlier_year_binds_its_own_table(self):
        # "2017-18" -> F1718 correct; F1617 wrong.
        q = "Yale total expenses in 2017-18?"
        check_fiscal_year([{'table': 'F1718_F2'}], q)
        with self.assertRaises(ValueError):
            check_fiscal_year([{'table': 'F1617_F2'}], q)


if __name__ == '__main__':
    unittest.main(verbosity=2)
