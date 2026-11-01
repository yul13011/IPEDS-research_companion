"""Regression: "Ivy League" — and phrasings like "ivy league universities / schools /
institutions" that the model copies literally — expand to the eight member IDs across the
institution resolver and the intent-check helper; a bare "ivy" that is not "ivy league"
(e.g. Ivy Tech) must not. See the Ivy League phrase-expansion fix."""
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / ".packages"), str(ROOT)]
from prototype.catalog import IVY, institutions
from prototype.intent_checks import _ids


class IvyLeagueTests(unittest.TestCase):
    def test_resolver_expands_phrasings(self):
        for name in ["Ivy League", "ivy league universities", "the Ivy League",
                     "Ivy League institutions", "ivy league schools", "IVIES"]:
            self.assertEqual(sorted(institutions([name], 2024)), sorted(IVY), name)

    def test_ids_helper_expands_phrasings(self):
        self.assertEqual(_ids(["Ivy League institutions"]), sorted(IVY))
        self.assertEqual(_ids(["ivy league universities"]), sorted(IVY))

    def test_bare_ivy_is_not_ivy_league(self):
        # "ivy" without "league" must not expand to the Ivy League.
        with self.assertRaises(ValueError):
            institutions(["Poison Ivy College"], 2024)


if __name__ == "__main__":
    unittest.main(verbosity=2)
