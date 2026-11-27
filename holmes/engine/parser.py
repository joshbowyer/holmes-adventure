"""Turns a typed line into a Command: verb, object phrase, preposition, second phrase.

Resolving phrases to things in the world is the game's job, not the parser's.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DIRECTIONS = {
    "n": "north", "north": "north", "s": "south", "south": "south",
    "e": "east", "east": "east", "w": "west", "west": "west",
    "ne": "northeast", "northeast": "northeast", "nw": "northwest", "northwest": "northwest",
    "se": "southeast", "southeast": "southeast", "sw": "southwest", "southwest": "southwest",
    "u": "up", "up": "up", "upstairs": "up", "d": "down", "down": "down", "downstairs": "down",
    "in": "in", "inside": "in", "out": "out", "outside": "out",
}

BUILTIN_VERBS = {
    "look": ["look", "l"],
    "examine": ["examine", "x", "inspect", "read", "study", "search", "check", "observe"],
    "take": ["take", "get", "grab", "pocket", "collect"],
    "drop": ["drop", "discard", "leave"],
    "open": ["open"],
    "close": ["close", "shut"],
    "inventory": ["inventory", "inv", "i"],
    "go": ["go", "walk", "run", "enter", "head", "move"],
    "ask": ["ask", "question", "query"],
    "talk": ["talk", "speak", "greet", "chat"],
    "show": ["show", "give", "offer", "hand", "present"],
    "use": ["use", "apply"],
    "notebook": ["notebook", "notes", "clues", "journal", "nb"],
    "hint": ["hint", "hints", "consult"],
    "accuse": ["accuse", "solve", "conclude", "deduce"],
    "help": ["help", "?", "h", "commands"],
    "save": ["save"],
    "quit": ["quit", "q", "menu"],
    "exits": ["exits", "ways"],
    "wait": ["wait", "z"],
    "status": ["status", "time"],
    "timeline": ["timeline", "board", "events"],
    "arrange": ["arrange", "order", "reorder", "sort"],
    "seating": ["seating", "seats", "plan", "places"],
    "seat": ["seat"],
    "unseat": ["unseat"],
    "again": ["again", "g"],
}

# Multi-word verbs, matched before single words.
PHRASES = [
    ("penny for your thoughts", "hint"),
    ("consult holmes", "hint"),
    ("ask holmes for help", "hint"),
    ("pick up", "take"),
    ("put down", "drop"),
    ("look at", "examine"),
    ("look in", "examine"),
    ("look inside", "examine"),
    ("look into", "examine"),
    ("look under", "examine"),
    ("look behind", "examine"),
    ("look through", "examine"),
    ("talk to", "talk"),
    ("talk with", "talk"),
    ("speak to", "talk"),
    ("speak with", "talk"),
    ("go to", "go"),
    ("walk to", "go"),
    ("go into", "go"),
    ("go through", "go"),
]

ARTICLES = {"the", "a", "an", "some", "my", "his", "her", "its", "this", "that", "their"}
PREPOSITIONS = ["about", "to", "with", "on", "onto", "at", "in", "into", "from",
                "under", "behind", "using", "for"]

# Verbs whose object is a place or direction: never split on prepositions.
NO_SPLIT = {"go"}


@dataclass
class Command:
    verb: str | None          # canonical verb, or None if unrecognised
    obj: str = ""             # first noun phrase
    prep: str = ""            # preposition joining the two phrases
    obj2: str = ""            # second noun phrase
    word: str = ""            # the verb word as typed
    raw: str = ""


def build_verb_map(extra: dict | None = None) -> dict[str, str]:
    vm = {}
    for verb, words in BUILTIN_VERBS.items():
        for w in words:
            vm[w] = verb
    for verb, words in (extra or {}).items():
        vm[verb] = verb
        for w in words:
            vm[w] = verb
    return vm


_PHRASES = sorted(((p.split(), v) for p, v in PHRASES), key=lambda pv: -len(pv[0]))


def tokenize(line: str) -> list[str]:
    return re.sub(r"[^\w\s'?-]", " ", line.lower()).split()


def parse(line: str, verb_map: dict[str, str]) -> Command | None:
    tokens = tokenize(line)
    if not tokens:
        return None
    raw = line.strip()

    if len(tokens) == 1 and tokens[0] in DIRECTIONS:
        return Command("go", DIRECTIONS[tokens[0]], word=tokens[0], raw=raw)

    verb, rest, word = None, tokens[1:], tokens[0]
    for words, v in _PHRASES:
        if tokens[:len(words)] == words:
            verb, rest, word = v, tokens[len(words):], " ".join(words)
            break
    else:
        verb = verb_map.get(tokens[0])

    if verb is None:
        return Command(None, " ".join(tokens[1:]), word=tokens[0], raw=raw)

    rest = [t for t in rest if t not in ARTICLES]

    if verb == "look" and rest:
        # "look north" moves you; "look cushion" examines it.
        if len(rest) == 1 and rest[0] in DIRECTIONS:
            return Command("go", DIRECTIONS[rest[0]], word=word, raw=raw)
        verb = "examine"

    if verb in NO_SPLIT:
        obj = " ".join(rest)
        if obj in DIRECTIONS:
            obj = DIRECTIONS[obj]
        return Command(verb, obj, word=word, raw=raw)

    # A leading preposition left over ("examine under the sofa") carries no meaning.
    while rest and rest[0] in PREPOSITIONS:
        rest = rest[1:]
    for i, t in enumerate(rest):
        if t in PREPOSITIONS and i > 0:
            return Command(verb, " ".join(rest[:i]), t, " ".join(rest[i + 1:]), word=word, raw=raw)
    return Command(verb, " ".join(rest), word=word, raw=raw)
