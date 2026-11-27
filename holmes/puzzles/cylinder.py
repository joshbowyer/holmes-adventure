"""Phonograph cylinders: play them at different speeds, hear what is on them, and say where
each part of a questioned cylinder came from.

Nothing is ever played aloud. PLAY describes what Watson hears and what Holmes measures
at the speed chosen, worked out from the data, so the text never states a true speed.

spec: everything an `accuse` spec has, plus
  cylinder = {
    intro            shown before the board, when the player accuses
    play_when        condition under which PLAY works (e.g. at the machine)
    play_refused     what is said when it does not
    min_speed, max_speed   the machine's range, in turns a minute (default 60 to 240)
    sounds = {key: {name, freq?, rate?, voice?}}
                     every sound on any cylinder. `freq` is its true pitch in vibrations
                     a second, `rate` its true beats to the minute; at a speed other than
                     the true one both are scaled by speed / true speed. A sound with
                     `voice` set is a speaker: his words are given only while they can be
                     made out, with how his voice sounds at that speed.
    cylinders = {cid: {deal, label, parts = [{id, voice?, words?, true_speed,
                       sounds? [keys], clue?}], background? = [{sound, true_speed, clue?}]}}
                     a cylinder is dealt when the clue `deal` is noted (it is lettered in
                     the order found). Its parts play one after another, each sounding
                     natural at its own `true_speed`; between parts the hiss changes.
                     `background` runs under the whole cylinder. A `clue` is noted the
                     first time that part or sound is heard at its true speed.
    answer = {part id: cid}   for each part of a questioned cylinder, the cylinder it was
                     copied from. These parts are numbered 1, 2, 3 ... for SOURCE.
    wrong_ending     ending id when any part is given the wrong source
    incomplete_ending  optional: everything given is right but parts are unsettled
  }

During play, CYLINDERS lists what has been found, PLAY <letter> AT <speed> plays one, and
SOURCE <number> FROM <letter> says where a part of the questioned cylinder came from.
The player's sources are kept in `state.attribution`.
"""

from __future__ import annotations

import textwrap

from holmes.engine.conditions import check
from holmes.puzzles.accuse import AccusePuzzle

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
TRUE_WITHIN = 0.02          # within 2% of the true speed, a sound is heard truly
NOBODY = {"nobody", "none", "nothing", "unknown", "clear"}


def has_cylinder(game) -> bool:
    return game.story.final.get("type") == "cylinder"


def _spec(game) -> dict:
    return game.story.final["cylinder"]


def is_true(speed: float, true_speed: float) -> bool:
    return abs(speed / true_speed - 1) <= TRUE_WITHIN


# --- what the player has found ---------------------------------------------------------

def dealt(game) -> list[str]:
    by_clue: dict[str, list[str]] = {}
    for cid, c in _spec(game)["cylinders"].items():
        by_clue.setdefault(c["deal"], []).append(cid)
    out: list[str] = []
    for clue in game.state.clues:
        out += [c for c in by_clue.get(clue, []) if c not in out]
    return out


def letter_of(game) -> dict[str, str]:
    return {cid: LETTERS[i] for i, cid in enumerate(dealt(game))}


def numbered_parts(game) -> dict[str, int]:
    """Parts of questioned cylinders found so far, numbered for SOURCE."""
    answer = _spec(game)["answer"]
    out, n = {}, 0
    for cid in dealt(game):
        for part in _spec(game)["cylinders"][cid]["parts"]:
            if part["id"] in answer:
                n += 1
                out[part["id"]] = n
    return out


def source_of(game, pid: str) -> str | None:
    cid = game.state.attribution.get(pid)
    return cid if cid in dealt(game) else None


def unsettled(game) -> list[str]:
    return [p for p in numbered_parts(game) if source_of(game, p) is None]


def _cylinder_from(game, word: str) -> str | None:
    by_letter = {v: k for k, v in letter_of(game).items()}
    return by_letter.get(word.strip().upper()) if len(word.strip()) == 1 else None


# --- hearing -----------------------------------------------------------------------------

def _voice_quality(r: float) -> tuple[str, bool]:
    """How a voice sounds at this ratio of speeds, and whether its words can be made out."""
    if r < 0.6:
        return "a slow, booming drone", False
    if r < 0.85:
        return "deep and dragging", True
    if r < 1 - TRUE_WITHIN:
        return "a little low and slow", True
    if r <= 1 + TRUE_WITHIN:
        return "natural", True
    if r <= 1.15:
        return "a little high and quick", True
    if r <= 1.6:
        return "high and gabbling", True
    return "a shrill twittering", False


def _measure(sound: dict, r: float) -> str:
    if "freq" in sound:
        return f"{sound['name']}, about {round(sound['freq'] * r)} vibrations a second"
    if "rate" in sound:
        return f"{sound['name']}, {round(sound['rate'] * r)} to the minute"
    return sound["name"]


def play(game, text: str) -> bool:
    spec = _spec(game)
    if not dealt(game):
        game.fail("I have no cylinders to play.")
        return False
    if not check(game.state, spec.get("play_when")):
        game.fail(spec.get("play_refused", "There is no phonograph here to play it on."))
        return False
    words = [w for w in text.lower().replace(",", " ").split()
             if w not in ("cylinder", "the", "at", "on", "speed", "turns", "rpm", "revolutions",
                          "minute", "per")]
    letter = next((w for w in words if w.isalpha() and len(w) == 1), None)
    number = next((w for w in words if w.isdigit()), None)
    if letter is None or number is None:
        game.fail("Play which cylinder, at what speed? (For example: PLAY A AT 120.)", "system")
        return False
    cid = _cylinder_from(game, letter)
    if cid is None:
        game.fail(f"There is no cylinder {letter.upper()} among those I have.", "system")
        return False
    speed = int(number)
    lo, hi = int(spec.get("min_speed", 60)), int(spec.get("max_speed", 240))
    if not lo <= speed <= hi:
        game.fail(f"The governor of the machine will run from {lo} to {hi} turns a minute, "
                  "and no further.", "system")
        return False
    _hear(game, cid, speed)
    return True


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def _wrap(lines: list[str], text: str, first: str, rest: str, width: int = 76) -> None:
    for i, line in enumerate(textwrap.wrap(text, width - len(first)) or [""]):
        lines.append("|" + (first if i == 0 else rest) + line)


def _hear(game, cid: str, speed: int) -> None:
    spec = _spec(game)
    sounds, c = spec["sounds"], spec["cylinders"][cid]
    numbers = numbered_parts(game)
    letter = letter_of(game)[cid]
    lines = [f"| Cylinder {letter}, {c['label']}, at {speed} turns a minute:", "|"]
    new_clues: list[str] = []
    for i, part in enumerate(c["parts"]):
        if i:
            lines += ["|    ... a faint click, and the hiss beneath changes ...", "|"]
        r = speed / part["true_speed"]
        tag = f"{numbers[part['id']]}." if part["id"] in numbers else "-"
        heard = []
        if part.get("voice"):
            v = sounds[part["voice"]]
            quality, plain = _voice_quality(r)
            said = f': "{part["words"]}"' if plain and part.get("words") else \
                ", but not a word can be made out" if part.get("words") else ""
            heard.append(f"{v['name']}, sounding {quality} (about {round(v['freq'] * r)} "
                         f"vibrations a second){said}")
        heard += [_measure(sounds[s], r) for s in part.get("sounds", [])]
        _wrap(lines, _cap(heard[0]) + ("" if heard[0].endswith('"') else "."),
              f" {tag:>3} ", "      ")
        for h in heard[1:]:
            _wrap(lines, f"With it: {h}.", "      ", "        ")
        if part.get("clue") and is_true(speed, part["true_speed"]):
            new_clues.append(part["clue"])
    bg = c.get("background", [])
    if bg:
        lines += ["|", "|    Behind it all, from first to last:"]
        for b in bg:
            _wrap(lines, _cap(_measure(sounds[b["sound"]], speed / b["true_speed"])) + ".",
                  "      ", "        ")
            if b.get("clue") and is_true(speed, b["true_speed"]):
                new_clues.append(b["clue"])
    game.say("\n".join(lines))
    game.say("(Holmes took each figure from his siren as the cylinder turned. PLAY "
             f"{letter} AT another speed to hear it again.)", "system")
    for clue in new_clues:
        game.add_clue(clue)


# --- the board ---------------------------------------------------------------------------

def show_board(game) -> None:
    spec, letters = _spec(game), letter_of(game)
    game.say("CYLINDERS", "heading")
    if not letters:
        game.say("I have not yet a single cylinder.")
        return
    lines = [f"| {letters[cid]}  {spec['cylinders'][cid]['label']}" for cid in letters]
    numbers = numbered_parts(game)
    if numbers:
        lines += ["|", "| Parts of the questioned cylinder, and where each came from:"]
        for pid, n in numbers.items():
            src = source_of(game, pid)
            where = f"from cylinder {letters[src]}?" if src else "not yet settled"
            lines.append(f"|   {n}.  {where}")
    game.say("\n".join(lines))
    game.say("(PLAY <letter> AT <speed> plays a cylinder, at the machine. SOURCE <number> "
             "FROM <letter> says which cylinder a part was taken from; SOURCE <number> FROM "
             "NONE clears it.)", "system")


def source(game, text: str) -> bool:
    words = [w for w in text.lower().replace(",", " ").split()
             if w not in ("from", "to", "is", "was", "cylinder", "part", "the", "taken", "copied")]
    numbers = numbered_parts(game)
    if not numbers:
        game.fail("I have no questioned cylinder whose parts need settling.", "system")
        return False
    nums = [w for w in words if w.isdigit()]
    rest = [w for w in words if not w.isdigit()]
    if not nums or not rest:
        game.fail("Say which part, and which cylinder it came from. (For example: SOURCE 2 "
                  "FROM C.)", "system")
        return False
    by_number = {n: pid for pid, n in numbers.items()}
    pids = []
    for w in nums:
        if int(w) not in by_number:
            game.fail(f"There is no part {w} on the questioned cylinder.", "system")
            return False
        pids.append(by_number[int(w)])
    if all(w in NOBODY for w in rest):
        for pid in pids:
            game.state.attribution.pop(pid, None)
        show_board(game)
        return True
    if len(rest) != 1:
        game.fail("Name the cylinder by its letter.", "system")
        return False
    cid = _cylinder_from(game, rest[0])
    if cid is None:
        game.fail(f"There is no cylinder {rest[0].upper()} among those I have.", "system")
        return False
    if any(spec_part in pids for spec_part in
           [p["id"] for p in _spec(game)["cylinders"][cid]["parts"]]):
        game.fail("A cylinder cannot be copied from itself.", "system")
        return False
    for pid in pids:
        game.state.attribution[pid] = cid
    show_board(game)
    return True


def cylinders_dealt_by(game, clue: str | None) -> list[str]:
    if not clue or not has_cylinder(game):
        return []
    return [cid for cid, c in _spec(game)["cylinders"].items() if c["deal"] == clue]


def note_item_cylinder(game, clue: str | None) -> None:
    """Examining a cylinder says which letter it has."""
    cids = [c for c in cylinders_dealt_by(game, clue) if c in dealt(game)]
    if not cids:
        return
    letters = letter_of(game)
    for cid in cids:
        game.say(f"(This is cylinder {letters[cid]}. CYLINDERS lists all you have; PLAY "
                 f"{letters[cid]} AT <speed> plays it, at the machine.)", "system")


class CylinderPuzzle(AccusePuzzle):
    def run(self) -> None:
        if not self.gate():
            return
        sp = self.spec["cylinder"]
        if sp.get("intro"):
            self.game.say(sp["intro"])
        if not self.settle():
            return self.stop()
        answers = self.ask()
        if answers is None or not self.confirm():
            return self.stop()
        verdict = self.verdict()
        if verdict != "right":
            return self.judge(sp.get("incomplete_ending", sp["wrong_ending"])
                              if verdict == "incomplete" else sp["wrong_ending"], False)
        self.judge(*self.ending_for(answers))

    def settle(self) -> bool:
        g = self.game
        while True:
            show_board(g)
            loose = unsettled(g)
            prompt = ("Say where each part came from (SOURCE number FROM letter), or Enter "
                      "to stop: " if loose else
                      "Enter to stand by these, or SOURCE number FROM letter to change one: ")
            line = g.io.read(prompt)
            if line is None:
                return False
            line = line.strip()
            if not line:
                return not loose
            verb, _, rest = line.partition(" ")
            if verb.lower() == "source":
                source(g, rest)
            else:
                g.say("Use SOURCE number FROM letter.", "system")

    def verdict(self) -> str:
        answer = self.spec["cylinder"]["answer"]
        mine = {pid: source_of(self.game, pid) for pid in numbered_parts(self.game)}
        if any(c is not None and answer[pid] != c for pid, c in mine.items()):
            return "wrong"
        if len(mine) == len(answer) and all(mine.values()):
            return "right"
        return "incomplete"
