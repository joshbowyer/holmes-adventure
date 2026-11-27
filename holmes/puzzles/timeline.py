"""Timeline building: put the events of the case in their true order, then answer.

spec: everything an `accuse` spec has, plus
  timeline = {
    intro         shown before the board, when the player accuses
    cards = {card id: "short label"}   an event card, dealt when the clue of the same
                                        id is noted; the label gives the time as stated
          or {card id: {event = "what happened",
                        says = {clue id: "the time as this witness gave it", ...}}}
                                        an event several witnesses timed: dealt by
                                        whichever of those clues is noted first, and
                                        labelled with the event and every statement
                                        of it noted so far
    order = [card id, ...]             the true order (every card)
    wrong_ending  ending id when the order is wrong
  }

During play, TIMELINE shows the cards found so far, each lettered in the order it was
found (so a letter never changes), and ARRANGE <letters> puts them in an order. The
arrangement is kept in the save. At the accusation the player stands by it or types a
new one; a wrong order plays `wrong_ending` before any question is judged.
"""

from __future__ import annotations

from holmes.puzzles.accuse import AccusePuzzle

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def has_timeline(game) -> bool:
    return game.story.final.get("type") == "timeline"


def card_clues(spec: dict) -> dict[str, list[str]]:
    """{clue id: [card ids it deals]} for a final spec's timeline."""
    out: dict[str, list[str]] = {}
    for cid, card in spec.get("timeline", {}).get("cards", {}).items():
        for clue in (card.get("says", {}) if isinstance(card, dict) else [cid]):
            out.setdefault(clue, []).append(cid)
    return out


def dealt(game) -> list[str]:
    """The card ids found so far, in the order found."""
    by_clue = card_clues(game.story.final)
    out: list[str] = []
    for clue in game.state.clues:
        out += [c for c in by_clue.get(clue, []) if c not in out]
    return out


def label(game, cid: str) -> str:
    card = game.story.final["timeline"]["cards"][cid]
    if not isinstance(card, dict):
        return card
    said = [t for clue, t in card.get("says", {}).items() if clue in game.state.clues]
    return f"{card['event']}: {'; '.join(said)}."


def letter_of(game) -> dict[str, str]:
    return {cid: LETTERS[i] for i, cid in enumerate(dealt(game))}


def placed(game) -> tuple[list[str], list[str]]:
    """(arranged card ids in order, found cards not yet placed)."""
    found = dealt(game)
    arranged = [c for c in game.state.arrangement if c in found]
    return arranged, [c for c in found if c not in arranged]


def show_board(game) -> None:
    letters = letter_of(game)
    arranged, loose = placed(game)
    game.say("TIMELINE", "heading")
    if not letters:
        game.say("I have not yet a single event I can fix to a time.")
        return
    lines = []
    if arranged:
        lines += ["| In the order you have put them, earliest first:"]
        lines += [f"|   {letters[c]}  {label(game, c)}" for c in arranged]
    if loose:
        lines += ["| Not yet placed:" if arranged else "| Events noted, not yet placed:"]
        lines += [f"|   {letters[c]}  {label(game, c)}" for c in loose]
    game.say("\n".join(lines))
    game.say("(ARRANGE followed by letters, earliest first, sets the order: e.g. "
             f"ARRANGE {''.join(sorted(letters.values())[:3])}. You may place only some.)",
             "system")


def parse_letters(game, text: str) -> list[str] | str:
    """Card ids for typed letters, or a reason they will not do."""
    by_letter = {v: k for k, v in letter_of(game).items()}
    picked = [ch for ch in text.upper() if ch.isalpha()]
    if not picked:
        return "Give the letters of the events, earliest first."
    bad = [ch for ch in picked if ch not in by_letter]
    if bad:
        return f"There is no event {bad[0]} on the board."
    if len(set(picked)) != len(picked):
        return "Each event can stand in only one place."
    return [by_letter[ch] for ch in picked]


def arrange(game, text: str) -> bool:
    got = parse_letters(game, text)
    if isinstance(got, str):
        game.fail(got)
        return False
    game.state.arrangement = got
    show_board(game)
    return True


class TimelinePuzzle(AccusePuzzle):
    def run(self) -> None:
        if not self.gate():
            return
        tl = self.spec["timeline"]
        if tl.get("intro"):
            self.game.say(tl["intro"])
        if not self.settle_order():
            return self.stop()
        answers = self.ask()
        if answers is None or not self.confirm():
            return self.stop()
        if not self.order_right():
            return self.judge(tl["wrong_ending"], False)
        self.judge(*self.ending_for(answers))

    def settle_order(self) -> bool:
        g = self.game
        while True:
            show_board(g)
            arranged, loose = placed(g)
            if loose:
                prompt = "Set the events in order, as letters (or Enter to stop): "
            else:
                prompt = "Enter to stand by this order, or type a new one: "
            line = g.io.read(prompt)
            if line is None:
                return False
            if not line.strip():
                if loose:
                    return False
                return True
            got = parse_letters(g, line)
            if isinstance(got, str):
                g.say(got, "system")
                continue
            if len(got) < len(dealt(g)):
                g.say("Every event must have its place.", "system")
                continue
            g.state.arrangement = got

    def order_right(self) -> bool:
        order = self.spec["timeline"]["order"]
        mine = [c for c in self.game.state.arrangement if c in order]
        return mine == order
