"""Regression for the deterministic aid/affordability route (catalog_planner.aid_plan and
model_policy._deterministic_aid_answer). Current-year financial-aid, grant, scholarship and
student-loan questions for one cleanly resolved institution answer with zero model calls and
the full-time first-year panel by default; "all undergraduates" switches to the thin
total-grant/Pell/federal-loan set; loan/borrow questions reach the aid route (not the cost
route); and cost/tuition, percentage-only, trend, comparison, historical and unresolved-name
questions fall through (None). See the aid route."""
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / ".packages"), str(ROOT)]
from prototype.catalog_planner import aid_plan, cost_plan, scorecard_deflection
from prototype.model_policy import (_deterministic_aid_answer, _deterministic_cost_answer,
                                     _deterministic_debt_deflection)


def route(q):
    """Which deterministic route (if any) claims the question, in handle() precedence order:
    the debt/default scope note first, then cost, then aid."""
    if scorecard_deflection(q):return "deflect"
    if cost_plan(q):return "cost"
    if aid_plan(q):return "aid"
    return None


def panel(answer):
    """Map each row's IPEDS variable (the part after '::') to its value."""
    return {r["metric"].split("::")[-1]: r["value"] for r in answer["result"]["rows"]}


class AidRouteTests(unittest.TestCase):
    def test_aid_questions_take_aid_route(self):
        for q in ["how much financial aid does Harvard College receive on average?",
                  "how much in grants does Harvard College give?",
                  "what scholarships does Harvard College award on average?"]:
            self.assertEqual(route(q), "aid", q)

    def test_loan_and_borrow_take_aid_route_not_cost(self):
        # The cost route also matches "how much"; loan/borrow must still reach the aid route.
        for q in ["how much do students borrow at Harvard College?",
                  "how much do first-year students borrow at Harvard College?",
                  "how much in loans does Harvard College give?"]:
            self.assertEqual(route(q), "aid", q)

    def test_cost_questions_stay_on_cost_route(self):
        for q in ["what is the cost of attending Harvard College?",
                  "how much is tuition at Harvard College?",
                  "what is the total price of attendance at Harvard College?"]:
            self.assertEqual(route(q), "cost", q)

    def test_falls_through_for_non_current_and_relational(self):
        for q in ["how much financial aid did Harvard College give in 2016?",
                  "what percent of undergraduates got grants at Harvard College?",
                  "show Harvard College grant aid from 2015 through 2024",
                  "compare financial aid at Harvard College and Yale University",
                  "how much financial aid does the University of Michigan give?"]:
            self.assertIsNone(aid_plan(q), q)

    def test_ftft_panel_values(self):
        a = _deterministic_aid_answer("how much financial aid does Harvard College receive on average?", None, [])
        self.assertIsNotNone(a)
        self.assertEqual(a["model_usage"]["calls"], 0)
        vals = panel(a)
        self.assertEqual(vals["AGRNT_A"], 68015.0)   # total grant aid, FTFT
        self.assertEqual(vals["IGRNT_A"], 65260.0)   # institutional grant aid, FTFT
        self.assertEqual(vals["LOAN_A"], 12445.0)    # student loans, FTFT

    def test_all_undergraduate_panel_is_thin_set(self):
        a = _deterministic_aid_answer("how much financial aid do all undergraduates at Harvard College receive?", None, [])
        self.assertIsNotNone(a)
        vals = panel(a)
        self.assertEqual(vals["UAGRNTA"], 59539.0)   # all-undergrad total grant aid
        self.assertIn("UPGRNTA", vals)               # Pell
        self.assertNotIn("IGRNT_A", vals)            # no FTFT-only institutional grant
        self.assertNotIn("NPT42", vals)              # no net price for all undergraduates

    def test_loan_only_panel_is_loans(self):
        a = _deterministic_aid_answer("how much do first-year students borrow at Harvard College?", None, [])
        self.assertIsNotNone(a)
        metrics = set(panel(a))
        self.assertIn("LOAN_A", metrics)
        self.assertFalse(metrics & {"AGRNT_A", "IGRNT_A"})  # grants excluded for a loan-only ask

    def test_cost_route_unaffected_by_aid_route(self):
        c = _deterministic_cost_answer("what is the cost of attending Harvard College?", None, [])
        self.assertIsNotNone(c)
        self.assertEqual(c["model_usage"]["calls"], 0)

    def test_debt_and_default_deflect_to_scorecard(self):
        # Cumulative debt, debt at graduation and loan default are not IPEDS; they must get the
        # honest scope note, never tuition (cost route) or awarded-loan figures (aid route).
        for q in ["how much debt do students graduate with at Harvard College?",
                  "what is the student loan default rate at Harvard College?",
                  "how much total debt do Harvard College graduates have?",
                  "how much do Harvard College students owe in student loans?"]:
            self.assertEqual(route(q), "deflect", q)
            d = _deterministic_debt_deflection(q, None, [])
            self.assertIsNotNone(d)
            self.assertEqual(d["model_usage"]["calls"], 0)
            self.assertIs(d["capability"]["supported"], False)
            self.assertIn("College Scorecard", d["message"])

    def test_awarded_loans_not_deflected(self):
        # A borrowing question about aid awarded this year is answerable; it must not deflect.
        for q in ["how much do students borrow per year at Harvard College?",
                  "how much do first-year students borrow at Harvard College?"]:
            self.assertIsNone(scorecard_deflection(q), q)
            self.assertEqual(route(q), "aid", q)

    def test_institutional_debt_not_deflected(self):
        # Institutional long-term debt (a finance question) has no student context; leave it to the planner.
        self.assertIsNone(scorecard_deflection("how much long-term debt does Harvard University carry?"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
