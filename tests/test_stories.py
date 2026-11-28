"""Checks every real case from its private source. Asserts structure only and never
prints story text: failures name a step number, a command, or an id."""

import os
import re
import tempfile
import unittest

os.environ.setdefault("HOLMES_SAVE_DIR", tempfile.mkdtemp(prefix="holmes-test-"))

from holmes import build
from holmes.engine import codec
from holmes.engine.conditions import check
from holmes.engine.state import GameState
from holmes.engine.game import Game
from holmes.engine.parser import parse
from holmes.engine.story import Story
from holmes.engine.text import ScriptedConsole
from holmes.puzzles.timeline import card_clues
from holmes.validate import validate

# Engine responses that mean a walkthrough command misfired.
MISFIRES = ("I do not quite follow", "I see no ", "You cannot go that way", "Which do you mean",
            "I see no way to", "too dark to make anything out", "has nothing to say on that head")


def play(data, commands):
    shipped = {k: v for k, v in data.items() if k != "test"}
    console = ScriptedConsole(commands)
    story = Story(shipped)
    game = Game(story, console, autosave=False)
    # Each character's own "I don't know about that" replies also count as misfires.
    misfires = list(MISFIRES) + ["Nothing comes of"]
    for ch in story.characters.values():
        misfires += [ch[k] for k in ("unknown_topic", "unknown_show") if ch.get(k)]
    game.enter(game.state.room)
    steps = 0
    while console.inputs and not game.finished:
        line = console.inputs.pop(0)
        mark = len(console.output)
        game.handle(line)
        reply = "".join(console.output[mark:])
        flat = " ".join(reply.split())
        for i, m in enumerate(misfires):
            if " ".join(m.split()) in flat:
                kind = m.strip() if i < len(MISFIRES) + 1 else "a character's unknown-topic reply"
                raise AssertionError(f"step {steps}: {line!r} misfired ({kind})")
        steps += 1
    return game


SIGNPOSTED_VERBS = {"examine", "take", "open", "close", "use", "show", "talk", "search"}


def _norm(text):
    return " ".join(text.lower().replace("’", "'").replace("-", " ").split())


def _mentioned(phrase, text):
    """Does the text name this thing, as a player would type it?"""
    phrase = _norm(phrase)
    for art in ("the ", "a ", "an ", "some ", "his ", "her "):
        if phrase.startswith(art):
            phrase = phrase[len(art):]
    if not phrase:
        return True
    return re.search(r"(?<![\w'])" + re.escape(phrase) + r"(s|es)?(?![\w])", _norm(text)) is not None


def signpost_problems(data, commands):
    """Play the walkthrough and report every command that relies on a word the player
    has not been shown: things to examine or take must be named in the text of the
    room they are in, and ASK topics must come up in what that person has said (or be
    a thing the player has seen). Problems name a step and a command, never prose."""
    shipped = {k: v for k, v in data.items() if k != "test"}
    console = ScriptedConsole(commands)
    story = Story(shipped)
    game = Game(story, console, autosave=False)
    people = list(story.characters)
    said = {c: " ".join([story.characters[c].get("description", ""),
                         story.characters[c].get("presence", "")]) for c in people}
    mark = len(console.output)
    game.enter(game.state.room)
    room_text = "".join(console.output[mark:])
    all_text = room_text
    problems, step = [], 0
    while console.inputs and not game.finished:
        line = console.inputs.pop(0)
        cmd = parse(line, game.verb_map)
        room_before = game.state.room
        carried = " ".join(story.article_name(t) for t in game.gather("player"))
        here = room_text + " " + carried
        who = None
        if cmd and cmd.verb in ("ask", "talk", "show"):
            name = cmd.obj2 if cmd.verb == "show" else cmd.obj
            found = game.match(name or "", people)
            who = found[0] if len(found) == 1 else None
        if cmd and cmd.verb == "ask" and cmd.obj2:
            topic = cmd.obj2
            known = who and _mentioned(topic, said[who])
            thing = game.match(topic, list(story.items) + people) and _mentioned(topic, all_text)
            if not (known or thing):
                problems.append(f"step {step}: {line!r} (topic never raised)")
        elif cmd and (cmd.verb in SIGNPOSTED_VERBS or cmd.verb in story.verbs):
            for phrase in (cmd.obj, cmd.obj2):
                if phrase and not _mentioned(phrase, here):
                    problems.append(f"step {step}: {line!r} ({phrase!r} not named in the room)")
        mark = len(console.output)
        game.handle(line)
        reply = "".join(console.output[mark:])
        all_text += " " + reply
        if who:
            said[who] += " " + reply
        room_text = reply if game.state.room != room_before else room_text + " " + reply
        step += 1
    return problems


def unnamed_scenery(data):
    """Scenery is never listed, so the room (or something in it) must name it."""
    rooms, items, people = data["rooms"], data["items"], data.get("characters", {})

    def text_of(o):
        return " ".join([o.get("description", ""), o.get("presence", "")]
                        + [d["text"] for d in o.get("details", [])])
    out = []
    for iid, it in items.items():
        loc = it.get("location")
        if loc not in rooms or not it.get("scenery"):
            continue
        text = " ".join([text_of(rooms[loc])]
                        + [text_of(o) for k, o in items.items() if o.get("location") == loc and k != iid]
                        + [text_of(c) for c in people.values() if c.get("location") == loc])
        if not any(_mentioned(n, text) for n in [it["name"]] + it.get("aliases", [])):
            out.append(f"{loc}: {iid}")
    return out


_N = r"(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|twenty-five|\d{1,2})"
CLOCK_READING = re.compile(r"\d{1,2}:\d{2}|o'clock|\bo'c\b|\b(quarter|half|minutes?|" + _N + r")\s+"
                           r"(past|to|after|before)\s+" + _N + r"\b|\bstr(uck|ikes|iking)\b", re.I)


def undealt_times(data):
    """In a timeline case, every text that gives a clock time must deal a card
    (user, 2026-11-26), unless [test] untimed lists its path as a timetable,
    an appointment or the like. Returns the offending paths, never prose."""
    final = data.get("final", {})
    if final.get("type") != "timeline":
        return []
    dealers = card_clues(final)
    allowed = set(data.get("test", {}).get("untimed", []))
    out = []

    def walk(node, path):
        if isinstance(node, dict):
            clues = {v[5:] for vals in node.values() if isinstance(vals, list)
                     for v in vals if isinstance(v, str) and v.startswith("clue:")}
            for k in ("text", "description"):
                if (isinstance(node.get(k), str) and CLOCK_READING.search(node[k])
                        and not clues & set(dealers) and path not in allowed):
                    out.append(path)
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}.{i}")
    for part in ("rooms", "items", "characters", "events"):
        walk(data.get(part, {}), part)
    return out


class StoryTests(unittest.TestCase):
    def test_unexplored_case_cannot_be_solved(self):
        """The player may accuse at any time (user, 2026-11-27), but the answers they
        have not yet found are not offered, so the right answer needs the evidence."""
        for d in build.source_dirs():
            data = build.load_source(d)
            with self.subTest(case=data["case"]["id"]):
                final = data["final"]
                self.assertFalse(final.get("when"), "accusation is gated")
                state = GameState.new(Story({k: v for k, v in data.items() if k != "test"}))
                offered = {q["id"]: {o["id"] for o in q["options"] if check(state, o.get("when"))}
                           for q in final["questions"]}
                self.assertFalse(all(v in offered[k] for k, v in final["solution"].items()))

    def test_timed_statements_deal_cards(self):
        for d in build.source_dirs():
            data = build.load_source(d)
            with self.subTest(case=data["case"]["id"]):
                self.assertEqual(undealt_times(data), [])

    def test_cylinder_parts_are_verbatim(self):
        """Every part of a questioned cylinder says exactly words found on the cylinder
        it was copied from (user, 2026-11-27: a part began with a 'to' no source had).
        Failures name the part id only."""
        def norm(t):
            return " ".join(re.sub(r"[^\w\s']", " ", t.lower()).split())
        for d in build.source_dirs():
            data = build.load_source(d)
            spec = data["final"].get("cylinder")
            if data["final"].get("type") != "cylinder":
                continue
            with self.subTest(case=data["case"]["id"]):
                parts = {p["id"]: p for c in spec["cylinders"].values() for p in c["parts"]}
                bad = []
                for pid, cid in spec["answer"].items():
                    words = norm(parts[pid].get("words", ""))
                    source = norm(" ".join(p.get("words", "")
                                           for p in spec["cylinders"][cid]["parts"]))
                    if words and words not in source:
                        bad.append(pid)
                self.assertEqual(bad, [])

    def test_clock_times_use_colons(self):
        """Times are written 9:05, never the period-style 9.5 or 9.05 (user's request)."""
        def strings(v):
            if isinstance(v, str):
                yield v
            elif isinstance(v, dict):
                for x in v.values():
                    yield from strings(x)
            elif isinstance(v, list):
                for x in v:
                    yield from strings(x)
        dotted = re.compile(r"(?<![\d.£])\b\d{1,2}\.\d{1,2}\b(?!\d)")
        for d in build.source_dirs():
            data = build.load_source(d)
            shipped = {k: v for k, v in data.items() if k != "test"}
            with self.subTest(case=data["case"]["id"]):
                self.assertEqual(sum(bool(dotted.search(s)) for s in strings(shipped)), 0)

    def test_scenery_is_named(self):
        for d in build.source_dirs():
            data = build.load_source(d)
            with self.subTest(case=data["case"]["id"]):
                self.assertEqual(unnamed_scenery(data), [])

    def test_walkthrough_words_are_signposted(self):
        for d in build.source_dirs():
            data = build.load_source(d)
            with self.subTest(case=data["case"]["id"]):
                walk = data.get("test", {}).get("walkthrough", [])
                self.assertEqual(signpost_problems(data, walk), [])

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
