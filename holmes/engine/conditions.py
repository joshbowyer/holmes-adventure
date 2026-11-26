"""The tiny condition language used by story data.

A condition (`when`, `done`, `visible_when`, ...) is a string or a list of strings.
All list entries must hold (AND). Within one string, '|' separates alternatives (OR).
A leading '!' negates a term.

  flag:NAME          a story flag is set
  has:ITEM           the player is carrying ITEM
  at:ROOM            the player is in ROOM
  visited:ROOM       the player has been in ROOM
  clue:ID            the clue is in the notebook
  loc:THING:PLACE    THING is at PLACE (room, container item, 'player', 'nowhere')
  open:ITEM          ITEM is open
  lt:COUNTER:N       a counter (declared in case.counters) is below N
  ge:COUNTER:N       ... is N or more
  eq:COUNTER:N       ... is exactly N

Effects are strings too:

  set:FLAG  unset:FLAG  clue:ID  move:THING:PLACE  give:ITEM  remove:THING
  open:ITEM  close:ITEM  goto:ROOM  look
  add:COUNTER:N      add N (may be negative) to a counter
  setn:COUNTER:N     set a counter to N
"""

from __future__ import annotations

from holmes.engine.story import as_list

COUNTER_TESTS = {"lt", "ge", "eq"}
COND_ARITY = {"flag": 1, "has": 1, "at": 1, "visited": 1, "clue": 1, "loc": 2, "open": 1,
              "lt": 2, "ge": 2, "eq": 2}
EFFECT_ARITY = {
    "set": 1, "unset": 1, "clue": 1, "move": 2, "give": 1, "remove": 1,
    "open": 1, "close": 1, "goto": 1, "look": 0, "add": 2, "setn": 2,
}


def split_term(term: str) -> tuple[bool, str, list[str]]:
    term = term.strip()
    neg = term.startswith("!")
    if neg:
        term = term[1:]
    kind, _, rest = term.partition(":")
    return neg, kind, rest.split(":") if rest else []


def alternatives(cond) -> list[list[str]]:
    """Normalise a condition to [[alt, alt], [alt]] (AND of ORs)."""
    return [[a.strip() for a in s.split("|")] for s in as_list(cond)]


def check(state, cond) -> bool:
    return all(any(_term(state, alt) for alt in ors) for ors in alternatives(cond))


def _term(state, term: str) -> bool:
    neg, kind, args = split_term(term)
    if kind == "flag":
        r = args[0] in state.flags
    elif kind == "has":
        r = state.loc(args[0]) == "player"
    elif kind == "at":
        r = state.room == args[0]
    elif kind == "visited":
        r = args[0] in state.visited
    elif kind == "clue":
        r = args[0] in state.clues
    elif kind == "loc":
        r = state.loc(args[0]) == args[1]
    elif kind == "open":
        r = args[0] in state.opened
    elif kind in COUNTER_TESTS:
        v, n = state.counters.get(args[0], 0), int(args[1])
        r = v < n if kind == "lt" else v >= n if kind == "ge" else v == n
    else:
        raise ValueError(f"unknown condition {term!r}")
    return r != neg
