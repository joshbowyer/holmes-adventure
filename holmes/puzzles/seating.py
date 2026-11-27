"""Seating: work out who sat where at a round table, then answer.

spec: everything an `accuse` spec has, plus
  seating = {
    intro              shown before the plan, when the player accuses
    places = [{id, label}, ...]   the places round the table, in order round to each
                       sitter's left (clockwise seen from above), the first at the top
    people = {key: {name, aliases?, when?, fixed?}}
                       the sitters; `when` says when the player knows they sat there
                       (unset: known from the start); `fixed` = a place id they are
                       always shown in, and need not be seated by the player
    answer = {place id: person key}   who truly sat where (every place)
    wrong_ending       ending id when anyone is in the wrong place
    incomplete_ending  optional: ending id when everyone placed is right but some
                       sitters were never found (else wrong_ending)
  }

During play, SEATING shows the plan, SEAT <name> AT <number> puts a known sitter in a
place, and UNSEAT <name> takes them out. The plan is kept in the save. At the
accusation the player may still change it; anyone in a wrong place plays
`wrong_ending` before any question is judged.
"""

from __future__ import annotations

import math

from holmes.engine.conditions import check
from holmes.puzzles.accuse import AccusePuzzle

FILLER = {"at", "in", "on", "to", "into", "place", "chair", "seat", "number", "no", "the"}


def has_seating(game) -> bool:
    return game.story.final.get("type") == "seating"


def _spec(game) -> dict:
    return game.story.final["seating"]


def known(game) -> list[str]:
    """Sitters the player knows were at the table, in the spec's order."""
    return [k for k, p in _spec(game)["people"].items() if check(game.state, p.get("when"))]


def plan(game) -> dict[str, str]:
    """{place id: person key}, fixed sitters included."""
    spec, out = _spec(game), {}
    for k, p in spec["people"].items():
        if p.get("fixed"):
            out[p["fixed"]] = k
    ok = set(known(game))
    for place, k in game.state.seating.items():
        if k in ok and place not in out:
            out[place] = k
    return out


def unseated(game) -> list[str]:
    seated = set(plan(game).values())
    return [k for k in known(game) if k not in seated]


def _name(game, key: str) -> str:
    return _spec(game)["people"][key]["name"]


def show_plan(game) -> None:
    spec = _spec(game)
    places, seats = spec["places"], plan(game)
    n = len(places)
    width, height = 62, 13
    rx, ry, cx, cy = 22, 5, width // 2, height // 2
    grid = [[" "] * width for _ in range(height)]

    def put(row, col, text):
        col = max(0, min(width - len(text), col))
        for i, ch in enumerate(text):
            grid[row][col + i] = ch

    for i, place in enumerate(places):
        a = 2 * math.pi * i / n
        x, y = cx + rx * math.sin(a), cy - ry * math.cos(a)
        who = _name(game, seats[place["id"]]) if place["id"] in seats else "......"
        text = f"{place['id']} {who}"
        put(round(y), round(x - len(text) / 2), text)
    put(cy, cx - 3, "TABLE")
    game.say("THE SITTING", "heading")
    lines = ["| " + "".join(r).rstrip() for r in grid]
    lines += ["|"] + [f"|   {p['id']}  {p['label']}" for p in places]
    game.say("\n".join(lines))
    loose = unseated(game)
    if loose:
        game.say("Known to have sat, not yet placed: "
                 + ", ".join(_name(game, k) for k in loose) + ".")
    note = spec.get("note", "Places are numbered round the table to each sitter's left.")
    game.say(f"({note} SEAT <name> AT <number> places a sitter; UNSEAT <name> "
             "takes them out.)", "system")


def _find_person(game, words: list[str]) -> list[str]:
    spec, hits = _spec(game), []
    phrase = " ".join(words)
    for k in known(game):
        p = spec["people"][k]
        names = [p["name"].lower()] + [a.lower() for a in p.get("aliases", [])] + [k]
        vocab = {w for n in names for w in n.replace("-", " ").split()}
        if phrase in names or all(w in vocab for w in words):
            hits.append(k)
    return hits


def _person_from(game, words: list[str]) -> str | None:
    words = [w for w in words if w not in FILLER]
    if not words:
        game.fail("Whom do you mean?", "system")
        return None
    hits = _find_person(game, words)
    if len(hits) != 1:
        game.fail("I know of no sitter by that name." if not hits
                  else "Which do you mean: " + ", ".join(_name(game, k) for k in hits) + "?",
                  "system")
        return None
    return hits[0]


def seat(game, text: str) -> bool:
    spec = _spec(game)
    words = text.lower().replace(".", " ").split()
    ids = [p["id"].lower() for p in spec["places"]]
    place_words = [w for w in words if w in ids]
    if not place_words:
        game.fail("Seat whom, and where? (For example: SEAT SMITH AT 3.)", "system")
        return False
    place = spec["places"][ids.index(place_words[-1])]["id"]
    rest = [w for w in words if w != place_words[-1]]
    who = _person_from(game, rest)
    if who is None:
        return False
    if spec["people"][who].get("fixed"):
        game.fail(f"{_name(game, who)}'s place is not in doubt.", "system")
        return False
    taken = plan(game).get(place)
    if taken and spec["people"][taken].get("fixed"):
        game.fail(f"That was {_name(game, taken)}'s place.", "system")
        return False
    st = game.state.seating
    for p, k in list(st.items()):
        if k == who or p == place:
            del st[p]
    st[place] = who
    show_plan(game)
    return True


def unseat(game, text: str) -> bool:
    spec = _spec(game)
    words = text.lower().split()
    ids = [p["id"].lower() for p in spec["places"]]
    if len(words) == 1 and words[0] in ids:
        place = spec["places"][ids.index(words[0])]["id"]
        if place not in game.state.seating:
            game.fail("Nobody is placed there.", "system")
            return False
        del game.state.seating[place]
        show_plan(game)
        return True
    who = _person_from(game, words)
    if who is None:
        return False
    for p, k in list(game.state.seating.items()):
        if k == who:
            del game.state.seating[p]
            show_plan(game)
            return True
    game.fail(f"{_name(game, who)} has no place on the plan yet.", "system")
    return False


class SeatingPuzzle(AccusePuzzle):
    def run(self) -> None:
        if not self.gate():
            return
        sp = self.spec["seating"]
        if sp.get("intro"):
            self.game.say(sp["intro"])
        if not self.settle_plan():
            return self.stop()
        answers = self.ask()
        if answers is None or not self.confirm():
            return self.stop()
        verdict = self.plan_verdict()
        if verdict != "right":
            return self.judge(sp.get("incomplete_ending", sp["wrong_ending"])
                              if verdict == "incomplete" else sp["wrong_ending"], False)
        self.judge(*self.ending_for(answers))

    def settle_plan(self) -> bool:
        g = self.game
        while True:
            show_plan(g)
            loose = unseated(g)
            prompt = ("Place the sitters (SEAT name AT number), or Enter to stop: " if loose
                      else "Enter to stand by this plan, or SEAT / UNSEAT to change it: ")
            line = g.io.read(prompt)
            if line is None:
                return False
            line = line.strip()
            if not line:
                return not loose
            verb, _, rest = line.partition(" ")
            if verb.lower() == "seat":
                seat(g, rest)
            elif verb.lower() == "unseat":
                unseat(g, rest)
            else:
                g.say("Use SEAT name AT number, or UNSEAT name.", "system")

    def plan_verdict(self) -> str:
        answer, seats = self.spec["seating"]["answer"], plan(self.game)
        if any(answer.get(p) != k for p, k in seats.items()):
            return "wrong"
        return "right" if len(seats) == len(answer) else "incomplete"
