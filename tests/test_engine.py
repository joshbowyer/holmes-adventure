"""Engine unit tests against a tiny made-up fixture (no real story content)."""

import os
import tempfile
import unittest

os.environ.setdefault("HOLMES_SAVE_DIR", tempfile.mkdtemp(prefix="holmes-test-"))

from holmes.engine import codec
from holmes.engine.conditions import check
from holmes.engine.game import Game
from holmes.engine.hints import current_hint
from holmes.engine.parser import build_verb_map, parse
from holmes.engine.state import GameState
from holmes.engine.story import Story
from holmes.engine.text import ScriptedConsole, wrap
from holmes.validate import validate

FIXTURE = {
    "case": {"id": "fixture", "title": "Fixture", "start": "a", "intro": "Intro."},
    "verbs": {"pull": ["pull", "tug"]},
    "rooms": {
        "a": {"name": "Room A", "description": "A.", "exits": {"north": "b", "down": {"to": "c"}}},
        "b": {"name": "Room B", "description": "B.", "exits": {"south": "a"}},
        "c": {"name": "Cellar", "description": "C.", "dark_when": "!has:lamp",
              "exits": {"up": "a"}},
    },
    "items": {
        "lamp": {"name": "brass lamp", "aliases": ["lamp"], "location": "a", "description": "L."},
        "box": {"name": "box", "location": "a", "description": "Bx.", "container": True,
                "openable": True, "scenery": True},
        "key": {"name": "key", "location": "box", "description": "K.", "clue": "found_key"},
        "coin1": {"name": "penny", "location": "b", "description": "P.", "coin": True},
        "rope": {"name": "rope", "location": "c", "description": "R.", "scenery": True},
    },
    "characters": {
        "bob": {"name": "Bob", "location": "b", "description": "Bob.",
                "topics": {"key": [{"text": "Bob on key.", "effects": ["set:asked"]}]}},
    },
    "clues": {"found_key": {"text": "A key."}, "rope_pulled": {"text": "Pulled."}},
    "actions": [
        {"verb": "pull", "target": "rope", "text": "Pulled.", "effects": ["clue:rope_pulled"]},
    ],
    "hints": [
        {"id": "h1", "done": "clue:found_key", "texts": ["one", "two"]},
        {"id": "h2", "when": "clue:found_key", "done": "flag:asked", "texts": ["three"]},
    ],
    "final": {
        "type": "accuse", "when": "clue:found_key",
        "questions": [{"id": "who", "prompt": "Who?",
                       "options": [{"id": "bob", "label": "Bob"}, {"id": "nob", "label": "Nob"}]}],
        "solution": {"who": "bob"}, "good": "win", "default_wrong": "lose",
    },
    "endings": {"win": {"text": "Won."}, "lose": {"text": "Lost."}},
}


def new_game(inputs=()):
    import copy
    story = Story(copy.deepcopy(FIXTURE))
    con = ScriptedConsole(inputs)
    return Game(story, con, autosave=False), con


class ParserTests(unittest.TestCase):
    vm = build_verb_map({"pull": ["tug"]})

    def p(self, line):
        c = parse(line, self.vm)
        return (c.verb, c.obj, c.prep, c.obj2)

    def test_directions(self):
        self.assertEqual(self.p("n"), ("go", "north", "", ""))
        self.assertEqual(self.p("go down"), ("go", "down", "", ""))
        self.assertEqual(self.p("look north"), ("go", "north", "", ""))

    def test_phrases_and_articles(self):
        self.assertEqual(self.p("pick up the brass lamp"), ("take", "brass lamp", "", ""))
        self.assertEqual(self.p("look at the box"), ("examine", "box", "", ""))
        self.assertEqual(self.p("x box"), ("examine", "box", "", ""))
        self.assertEqual(self.p("talk to bob"), ("talk", "bob", "", ""))
        self.assertEqual(self.p("consult holmes"), ("hint", "", "", ""))

    def test_prepositions(self):
        self.assertEqual(self.p("ask mrs hudson about the cake"),
                         ("ask", "mrs hudson", "about", "cake"))
        self.assertEqual(self.p("show the key to bob"), ("show", "key", "to", "bob"))
        self.assertEqual(self.p("use key on box"), ("use", "key", "on", "box"))
        self.assertEqual(self.p("look under the sofa"), ("examine", "sofa", "", ""))

    def test_story_verbs_and_unknown(self):
        self.assertEqual(self.p("tug rope"), ("pull", "rope", "", ""))
        self.assertIsNone(parse("frobnicate it", self.vm).verb)
        self.assertIsNone(parse("   ", self.vm))


class TextTests(unittest.TestCase):
    def test_wrap_ignores_ansi_and_keeps_verbatim(self):
        out = wrap("\x1b[1mword\x1b[0m " * 30, 40)
        self.assertTrue(all(len(l.replace("\x1b[1m", "").replace("\x1b[0m", "")) <= 40
                            for l in out.split("\n")))
        self.assertEqual(wrap("| a   b\n| c", 40), "a   b\nc")


class CodecTests(unittest.TestCase):
    def test_roundtrip_and_unreadable(self):
        obj = {"secret": "the butler", "n": [1, 2]}
        enc = codec.encode(obj)
        self.assertNotIn("butler", enc)
        self.assertEqual(codec.decode(enc), obj)

    def test_state_roundtrip(self):
        g, _ = new_game()
        g.state.flags.add("x")
        d = codec.decode(codec.encode(g.state.to_dict()))
        self.assertEqual(GameState.from_dict(d), g.state)


class GameTests(unittest.TestCase):
    def test_fixture_is_valid(self):
        self.assertEqual(validate(FIXTURE), [])

    def test_validator_catches_typos(self):
        import copy
        bad = copy.deepcopy(FIXTURE)
        bad["rooms"]["a"]["exits"]["east"] = "nowhere_room"
        bad["hints"][0]["done"] = "flag:never_set"
        errs = validate(bad)
        self.assertTrue(any("unknown room" in e for e in errs))
        self.assertTrue(any("never set" in e for e in errs))

    def test_movement_and_blocked(self):
        g, con = new_game()
        g.handle("n")
        self.assertEqual(g.state.room, "b")
        g.handle("east")
        self.assertEqual(g.state.room, "b")
        g.handle("go room a")
        self.assertEqual(g.state.room, "a")

    def test_container_take_and_clue(self):
        g, _ = new_game()
        g.handle("take key")
        self.assertNotEqual(g.state.loc("key"), "player")   # box is shut
        g.handle("open box")
        g.handle("take key")
        self.assertEqual(g.state.loc("key"), "player")
        g.handle("examine key")
        self.assertEqual(g.state.clues, ["found_key"])

    def test_dark_room(self):
        g, _ = new_game()
        g.handle("down")
        g.handle("pull rope")
        self.assertNotIn("rope_pulled", g.state.clues)       # cannot see it
        g.handle("up")
        g.handle("take lamp")
        g.handle("down")
        g.handle("tug rope")
        self.assertIn("rope_pulled", g.state.clues)

    def test_coins_and_state_aware_hints(self):
        g, con = new_game(["y", "y"])
        self.assertEqual(current_hint(g)["id"], "h1")
        g.handle("hint")
        self.assertEqual(g.state.coins, 0)                   # broke: nothing bought
        g.handle("n")
        g.handle("take penny")
        self.assertEqual((g.state.coins, g.state.coins_found), (1, 1))
        g.state.clues.append("found_key")                     # h1 now done: skip it
        self.assertEqual(current_hint(g)["id"], "h2")
        g.handle("hint")
        self.assertEqual((g.state.coins, g.state.hint_levels), (0, {"h2": 1}))
        g.handle("ask bob about key")
        self.assertIsNone(current_hint(g))

    def test_cheat_word_grants_a_free_coin(self):
        g, _ = new_game()
        g.handle("Persian Slipper")
        g.handle("persianslipper")
        self.assertEqual((g.state.coins, g.state.coins_found, g.state.turns), (2, 0, 0))

    def test_counters_ticks_wait_and_status(self):
        import copy
        data = copy.deepcopy(FIXTURE)
        data["case"].update({
            "counters": {"oil": 3, "tide": 0},
            "every_turn": [
                {"when": "has:lamp", "effects": ["add:oil:-1"]},
                {"effects": ["add:tide:1"]},
                {"when": "eq:oil:0", "text": "The lamp dies.", "effects": ["setn:oil:-1"]},
            ],
            "status": [{"when": "has:lamp", "text": "[Oil: {oil}]"}],
            "wait_turns": 5,
        })
        self.assertEqual(validate(data), [])
        g = Game(Story(data), ScriptedConsole([]), autosave=False)
        g.handle("notebook")                                  # untimed
        self.assertEqual(g.state.counters["tide"], 0)
        for failed in ("examine unicorn", "east", "take", "pull box", "ask bob about cheese"):
            g.handle(failed)                                  # came to nothing: free
        self.assertEqual((g.state.counters["tide"], g.state.turns), (0, 1))
        g.handle("take lamp")
        self.assertEqual(g.state.counters, {"oil": 2, "tide": 1})
        self.assertEqual(g.status_text(), "[Oil: 2]")
        g.handle("wait")                                      # stops when the lamp dies
        self.assertEqual(g.state.counters, {"oil": -1, "tide": 3})
        self.assertTrue(check(g.state, ["lt:oil:0", "ge:tide:3", "!eq:tide:4"]))
        bad = copy.deepcopy(data)
        bad["case"]["every_turn"][0]["effects"] = ["add:fuel:-1"]
        self.assertTrue(any("unknown counter" in e for e in validate(bad)))

    def test_timeline_board_and_final(self):
        import copy
        data = copy.deepcopy(FIXTURE)
        data["final"].update({"type": "timeline", "when": ["clue:found_key", "clue:rope_pulled"],
                              "timeline": {"cards": {"rope_pulled": "Rope.", "found_key": "Key."},
                                           "order": ["rope_pulled", "found_key"],
                                           "wrong_ending": "lose"}})
        self.assertEqual(validate(data), [])
        g = Game(Story(data), ScriptedConsole([]), autosave=False)
        g.state.clues += ["found_key", "rope_pulled"]          # dealt as A (key), B (rope)
        g.handle("arrange c")
        self.assertEqual((g.state.arrangement, g.state.turns), ([], 0))   # no such card: free
        g.handle("arrange a b")
        self.assertEqual(g.state.arrangement, ["found_key", "rope_pulled"])
        g.io.inputs += ["", "1", "y", ""]                       # stand by A B: wrong order
        g.handle("accuse")
        self.assertEqual((g.state.wrong, g.state.solved), (1, False))
        g.io.inputs += ["ba", "", "1", "y"]                     # re-order at the accusation
        g.handle("accuse")
        self.assertTrue(g.state.solved)

    def test_incomplete_timeline_and_met_options(self):
        import copy
        from holmes.engine.conditions import check
        data = copy.deepcopy(FIXTURE)
        del data["final"]["when"]
        data["final"]["questions"][0]["options"][0]["when"] = "met:bob"
        data["final"].update({"type": "timeline",
                              "timeline": {"cards": {"rope_pulled": "Rope.",
                                                     "k": {"event": "Key", "says": {"found_key": "now"}}},
                                           "order": ["rope_pulled", "k"],
                                           "wrong_ending": "lose", "incomplete_ending": "gaps"}})
        data["endings"]["gaps"] = {"text": "Gaps."}
        self.assertEqual(validate(data), [])
        g = Game(Story(data), ScriptedConsole([]), autosave=False)
        self.assertFalse(check(g.state, "met:bob"))
        g.io.inputs += ["", "1", "y", ""]                 # nothing found: may still accuse
        g.handle("accuse")
        self.assertEqual(g.state.wrong, 1)               # only Nob was offered
        g.handle("n")
        g.handle("ask bob about key")
        self.assertTrue(check(g.state, "met:bob"))
        g.state.clues.append("found_key")                 # one card of two, in order
        mark = len(g.io.output)
        g.io.inputs += ["a", "", "bob", "y", ""]
        g.handle("accuse")
        self.assertIn("Gaps.", "".join(g.io.output[mark:]))
        self.assertEqual((g.state.wrong, g.state.solved), (2, False))

    def test_seating_plan_and_final(self):
        import copy
        data = copy.deepcopy(FIXTURE)
        del data["final"]["when"]
        data["final"].update({"type": "seating", "seating": {
            "places": [{"id": "1", "label": "Top."}, {"id": "2", "label": "Left."},
                       {"id": "3", "label": "Right."}],
            "people": {"host": {"name": "Host", "fixed": "1"},
                       "bob": {"name": "Bob", "when": "met:bob"},
                       "ann": {"name": "Ann Lee", "aliases": ["lee"]}},
            "answer": {"1": "host", "2": "ann", "3": "bob"},
            "wrong_ending": "lose", "incomplete_ending": "gaps"}})
        data["endings"]["gaps"] = {"text": "Gaps."}
        self.assertEqual(validate(data), [])
        g = Game(Story(data), ScriptedConsole([]), autosave=False)
        g.handle("seat bob at 3")                          # not known yet: refused, free
        self.assertEqual((g.state.seating, g.state.turns), ({}, 0))
        g.handle("seat host at 2")                         # fixed: refused
        g.handle("seat lee at 3")
        g.handle("seat ann lee 2")                         # moves her
        self.assertEqual(g.state.seating, {"2": "ann"})
        mark = len(g.io.output)
        g.io.inputs += ["", "bob", "y", ""]               # Bob unknown: incomplete
        g.handle("accuse")
        self.assertIn("Gaps.", "".join(g.io.output[mark:]))
        g.state.met.add("bob")
        g.io.inputs += ["seat bob 2", "seat ann 3", "", "bob", "y", ""]   # wrong plan
        g.handle("accuse")
        self.assertEqual((g.state.wrong, g.state.solved), (2, False))
        g.io.inputs += ["seat ann 2", "seat bob 3", "", "bob", "y"]
        g.handle("accuse")
        self.assertTrue(g.state.solved)

    def test_morse_tapes_and_final(self):
        import copy
        from holmes.puzzles.morse import literal, render
        split = {"dot": 1, "dash": 3, "gap": 1, "letter": 3, "word": 7, "split": ["C"]}
        self.assertEqual(literal("CAT", split), "NNAT")
        self.assertEqual("".join(render("ET", {"dot": 1, "dash": 4, "gap": 1, "letter": 2,
                                               "word": 5})), "=  ====")
        data = copy.deepcopy(FIXTURE)
        del data["final"]["when"]
        data["final"].update({"type": "morse", "morse": {
            "codebook_when": "clue:found_key",
            "fists": {"plain": {"dot": 1, "dash": 3, "gap": 1, "letter": 3, "word": 7},
                      "odd": split},
            "passages": {
                "p1": {"deal": "found_key", "label": "First.", "text": "SOS", "fist": "plain",
                       "sender": "bob"},
                "p2": {"deal": "found_key", "label": "Second.", "text": "CAT", "fist": "odd",
                       "clue": "rope_pulled"},
            },
            "senders": {"bob": {"name": "Bob"}, "ann": {"name": "Ann Lee", "when": "met:bob"}},
            "answer": {"p2": "ann"},
            "wrong_ending": "lose", "incomplete_ending": "gaps"}})
        data["endings"]["gaps"] = {"text": "Gaps."}
        data["actions"] = []
        self.assertEqual(validate(data), [])
        g = Game(Story(data), ScriptedConsole([]), autosave=False)
        g.handle("codebook")                                 # no alphabet yet: refused
        self.assertTrue(g.failed)
        g.state.clues.append("found_key")
        g.handle("tape b")
        self.assertIn("=== =   === =", "".join(g.io.output))   # the split C
        g.handle("decode b as dog")
        self.assertEqual(g.state.decoded, [])
        g.handle("decode b as nnat")                         # the literal reading will do
        self.assertEqual((g.state.decoded, g.state.clues[-1]), (["p2"], "rope_pulled"))
        g.handle("attribute a to ann")                       # known sender: refused
        g.handle("attribute b to ann")                       # Ann not known yet
        self.assertEqual(g.state.attribution, {})
        g.handle("attribute b to bob")
        g.io.inputs += ["", "bob", "y", ""]                 # wrong sender
        g.handle("accuse")
        self.assertEqual(g.state.wrong, 1)
        g.state.met.add("bob")
        g.io.inputs += ["attribute b to lee", "", "bob", "y"]
        g.handle("accuse")
        self.assertTrue(g.state.solved)

    def test_wrong_then_right_accusation(self):
        g, _ = new_game(["2", "y", "", "1", "y"])
        g.handle("accuse")
        self.assertEqual(g.state.wrong, 0)                   # locked: no key clue yet
        g.state.clues.append("found_key")
        g.handle("accuse")
        self.assertEqual((g.state.wrong, g.state.solved), (1, False))
        g.handle("accuse")
        self.assertEqual((g.state.wrong, g.state.solved), (1, True))
        self.assertTrue(g.finished)


if __name__ == "__main__":
    unittest.main()
