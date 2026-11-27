"""Casebook menu: starting, resuming and replaying cases (no story text printed)."""

import copy
import os
import tempfile
import unittest

os.environ.setdefault("HOLMES_SAVE_DIR", tempfile.mkdtemp(prefix="holmes-test-"))

from holmes import menu
from holmes.engine import saves
from holmes.engine.story import Story
from holmes.engine.text import ScriptedConsole
from tests.test_engine import FIXTURE


def story():
    data = copy.deepcopy(FIXTURE)
    data["case"]["id"] = "menufixture"
    return Story(data)


class MenuTests(unittest.TestCase):
    def setUp(self):
        saves.delete_game("menufixture")

    def test_solved_case_asks_before_replaying(self):
        """Opening a solved case by mistake (user, 2026-11-27) must not start it."""
        profile = {"cases": {"menufixture": {"solved": True}}}
        menu.play_case(story(), ScriptedConsole(["n"]), profile)
        self.assertFalse(saves.save_path("menufixture").exists())
        menu.play_case(story(), ScriptedConsole(["y", "quit"]), profile)
        self.assertTrue(saves.save_path("menufixture").exists())    # a replay under way

    def test_case_in_progress_can_be_put_away(self):
        profile = {"cases": {"menufixture": {"solved": True}}}
        menu.play_case(story(), ScriptedConsole(["y", "quit"]), profile)
        menu.play_case(story(), ScriptedConsole([""]), profile)          # back out
        self.assertTrue(saves.save_path("menufixture").exists())
        menu.play_case(story(), ScriptedConsole(["3", "y"]), profile)    # put it away
        self.assertFalse(saves.save_path("menufixture").exists())
        self.assertTrue(profile["cases"]["menufixture"]["solved"])

    def test_casebook_status(self):
        profile = {"cases": {"menufixture": {"solved": True}}}
        con = ScriptedConsole(["q"])
        menu.play_case(story(), ScriptedConsole(["y", "quit"]), profile)
        menu.menu([story()], con, profile)
        self.assertIn("[solved; replay in progress]", con.text())


if __name__ == "__main__":
    unittest.main()
