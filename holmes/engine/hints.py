"""Hints bought with coins found by exploring.

Story `hints` are an ordered list of steps: {id, when, done, texts[]}. The hint offered
is the first step whose `when` holds and whose `done` does not, so a coin is never
spent on something the player has already found or solved. Each purchase on the same
step reveals the next, plainer text; once all are bought, the last is repeated free.

A step may also have `parts`: [{done, text}]. They make its plainest tier, after
`texts`, and only the parts not yet done are given, so the plain instructions never
repeat what the player has already found.
"""

from __future__ import annotations

from holmes.engine.conditions import check
from holmes.engine.story import as_list

YES = {"y", "yes", "aye", "yea", "ok", "very well"}


def current_hint(game) -> dict | None:
    st = game.state
    for h in game.story.hints:
        if check(st, h.get("when")) and not (h.get("done") and check(st, h["done"])):
            return h
    return None


def tiers(game, h: dict) -> list[str]:
    texts = list(as_list(h.get("texts", [])))
    parts = h.get("parts")
    if parts:
        todo = [p["text"] for p in parts if not check(game.state, p.get("done"))]
        texts.append('"' + " ".join(todo or [p["text"] for p in parts]) + '"')
    return texts


def give_hint(game) -> None:
    story, st = game.story, game.state
    case = story.case
    h = current_hint(game)
    if h is None:
        game.say(case.get("hint_none",
                          "There is nothing more to be had from hints. You have the facts; "
                          "put them together."))
        return
    texts = tiers(game, h)
    bought = st.hint_levels.get(h["id"], 0)
    if bought >= len(texts):
        game.note("[You have already bought every hint for this step. Repeating the last:]")
        game.say(texts[-1])
        return
    coin = story.coin_name()
    if st.coins < 1:
        game.say(case.get("hint_broke", f"You have no {story.coin_name(2)} to spend. "
                                        "Explore further; they turn up in odd places."))
        return
    answer = game.io.read(f"Spend a {coin} on a hint? You have {st.coins}. (y/n) ")
    if (answer or "").strip().lower() not in YES:
        game.say(f"You keep your {coin}.")
        return
    st.coins -= 1
    st.hints_bought += 1
    st.hint_levels[h["id"]] = bought + 1
    if case.get("hint_intro"):
        game.say(case["hint_intro"])
    game.say(texts[bought])
    if bought + 1 < len(texts):
        game.note("[If that is not enough, another hint on this will be plainer.]")
