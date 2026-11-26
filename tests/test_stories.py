"""Checks every real case from its private source. Asserts structure only and never
prints story text: failures name a step number, a command, or an id."""

import os
import tempfile
import unittest

os.environ.setdefault("HOLMES_SAVE_DIR", tempfile.mkdtemp(prefix="holmes-test-"))

from holmes import build
from holmes.engine import codec
from holmes.engine.game import Game
from holmes.engine.story import Story
from holmes.engine.text import ScriptedConsole
from holmes.validate import validate

# Engine responses that mean a walkthrough command misfired.
MISFIRES = ("I do not quite follow", "I see no ", "You cannot go that way", "Which do you mean",
            "I see no way to", "too dark to make anything out", "has nothing to say on that head")


def play(data, commands):
    shipped = {k: v for k, v in data.items() if k != "test"}
    console = ScriptedConsole(commands)
    game = Game(Story(shipped), console, autosave=False)
    game.enter(game.state.room)
    steps = 0
    while console.inputs and not game.finished:
        line = console.inputs.pop(0)
        mark = len(console.output)
        game.handle(line)
        reply = "".join(console.output[mark:])
        for m in MISFIRES:
            if m in reply:
                raise AssertionError(f"step {steps}: {line!r} misfired ({m.strip()!r})")
        steps += 1
    return game


class StoryTests(unittest.TestCase):
    def test_sources_exist(self):
        self.assertTrue(build.source_dirs(), "no story sources found")

    def test_each_case(self):
        for d in build.source_dirs():
            data = build.load_source(d)
            cid = data["case"]["id"]
            with self.subTest(case=cid):
                self.assertEqual(validate(data), [], "validation errors (run python -m holmes.build)")

                shipped = build.DATA_DIR / f"{cid}.case"
                self.assertTrue(shipped.exists(), "not built")
                expected = {k: v for k, v in data.items() if k != "test"}
                self.assertEqual(codec.decode(shipped.read_text(encoding="utf-8")), expected,
                                 "shipped data is stale (run python -m holmes.build)")

                tests = data.get("test", {})
                self.assertIn("walkthrough", tests, "no walkthrough")
                g = play(data, tests["walkthrough"])
                self.assertTrue(g.state.solved, "walkthrough does not solve the case")
                self.assertEqual(g.state.wrong, 0)
                missing = sorted(set(data["clues"]) - set(g.state.clues))
                self.assertEqual(missing, [], "walkthrough leaves clues unfound")

                if "wrong_path" in tests:
                    g = play(data, tests["wrong_path"])
                    self.assertFalse(g.state.solved)
                    self.assertEqual(g.state.wrong, 1, "wrong path did not reach a bad ending")


if __name__ == "__main__":
    unittest.main()
