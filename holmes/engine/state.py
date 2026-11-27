"""Everything that changes during play. Serialises to a plain dict for saving."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GameState:
    case_id: str
    room: str
    locations: dict = field(default_factory=dict)   # thing id -> room/item/'player'/'nowhere'
    flags: set = field(default_factory=set)
    clues: list = field(default_factory=list)        # in the order found
    visited: set = field(default_factory=set)
    met: set = field(default_factory=set)           # people spoken to
    opened: set = field(default_factory=set)
    searched: set = field(default_factory=set)       # containers examined (contents found)
    fired: set = field(default_factory=set)          # ids of one-shot events already run
    coins: int = 0
    coins_found: int = 0
    hint_levels: dict = field(default_factory=dict)  # hint id -> texts bought
    hints_bought: int = 0
    wrong: int = 0
    turns: int = 0
    solved: bool = False
    counters: dict = field(default_factory=dict)     # name -> int (tide, lamp oil...)
    arrangement: list = field(default_factory=list)  # timeline card ids, player's order
    seating: dict = field(default_factory=dict)      # place id -> sitter, player's plan
    decoded: list = field(default_factory=list)      # tape passages read correctly
    attribution: dict = field(default_factory=dict)  # tape passage -> sender, player's view

    @classmethod
    def new(cls, story) -> "GameState":
        s = cls(case_id=story.id, room=story.case["start"])
        s.counters = dict(story.case.get("counters", {}))
        for tid, t in list(story.items.items()) + list(story.characters.items()):
            s.locations[tid] = t.get("location", "nowhere")
        s.opened = {tid for tid, it in story.items.items() if it.get("open")}
        return s

    def loc(self, thing: str) -> str:
        return self.locations.get(thing, "nowhere")

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        for k in ("flags", "visited", "met", "opened", "searched", "fired"):
            d[k] = sorted(d[k])
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "GameState":
        d = dict(d)
        for k in ("flags", "visited", "met", "opened", "searched", "fired"):
            d[k] = set(d.get(k, []))
        known = cls.__dataclass_fields__
        return cls(**{k: v for k, v in d.items() if k in known})
