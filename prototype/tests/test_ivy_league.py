"""Regression for the named institution-group registry (catalog.GROUPS): "Ivy League",
"Ivy Plus"/"Ivy+", and "Seven Sisters" — including the loose phrasings the model copies
literally — expand to their member IDs across the institution resolver and the intent-check
helper; a bare "ivy" that is not one of these (e.g. Ivy Tech) must not. See the group registry."""
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / ".packages"), str(ROOT)]
from prototype.catalog import IVY, SEVEN_SISTERS, IVY_PLUS, GROUPS, institutions, group_label
from prototype.intent_checks import _ids


class GroupRegistryTests(unittest.TestCase):
    def _resolves_to(self, names, ids):
        for name in names:
            self.assertEqual(sorted(institutions([name], 2024)), sorted(ids), name)

    def test_ivy_league(self):
        self._resolves_to(["Ivy League", "ivy league universities", "the Ivy League",
                           "Ivy League institutions", "ivy league schools", "IVIES"], IVY)

    def test_ivy_plus(self):
        self.assertEqual(len(IVY_PLUS), 12)
        self._resolves_to(["Ivy Plus", "ivy plus", "Ivy+", "ivy +", "ivy-plus", "Ivy Plus schools"], IVY_PLUS)

    def test_seven_sisters(self):
        self.assertEqual(len(SEVEN_SISTERS), 6)
        self._resolves_to(["Seven Sisters", "the seven sisters", "seven sister colleges"], SEVEN_SISTERS)

    def test_groups_do_not_collide(self):
        self.assertEqual(group_label("ivy plus"), "Ivy Plus")
        self.assertEqual(group_label("ivy league"), "Ivy League")
        self.assertEqual(group_label("seven sisters"), "Seven Sisters")

    def test_ids_helper_expands_phrasings(self):
        self.assertEqual(_ids(["Ivy League institutions"]), sorted(IVY))
        self.assertEqual(_ids(["ivy plus universities"]), sorted(IVY_PLUS))

    def test_bare_ivy_is_not_a_group(self):
        # "ivy" without a group word must not expand (e.g. Ivy Tech is not the Ivy League).
        self.assertIsNone(group_label("Ivy Tech Community College"))
        with self.assertRaises(ValueError):
            institutions(["Poison Ivy College"], 2024)


if __name__ == "__main__":
    unittest.main(verbosity=2)
