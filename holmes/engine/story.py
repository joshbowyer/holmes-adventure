"""A loaded case: thin accessors over the story data, with defaults filled in.

Story data shape (authored as TOML, shipped encoded as JSON):

  case        id, title, year, start, intro, order, coin_name, coin_plural, hint texts,
              counters{name: start value}, every_turn[] (events run after each timed
              command), status[] ({when, text} shown after rooms and by STATUS; text may
              use {counter}), wait_turns, wait_text
  rooms.ID    name, description, aliases, details[], exits{dir: room | {to, when, blocked,
              visible_when, aliases, text}}, dark_when, dark_text, on_enter[]
              (an exit with `blocked` and no `to` is a way that is always barred)
  items.ID    name, aliases, location, description, details[], scenery, portable, listed,
              container, openable, open, coin, visible_when, clue, on_examine[], take_text,
              cant_take, open_text, on_take
  characters.ID  name, aliases, location, description, details[], presence, clue,
              on_examine[], greeting[], topics{key: [variant]}, shows{item: [variant]},
              unknown_topic, unknown_show
  clues.ID    text (the notebook entry)
  verbs       extra verb words: {verb: [synonyms]}
  actions[]   verb, target, with, when, text, effects, once, id
  hints[]     id, when, done, texts[]
  final       the final puzzle: {type, ...}
  endings.ID  title, text

A "variant" / event is {when, text, effects, once}.
"""

from __future__ import annotations


def as_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


class Story:
    def __init__(self, data: dict):
        self.data = data
        self.case = data["case"]
        self.id: str = self.case["id"]
        self.title: str = self.case["title"]
        self.rooms: dict = data.get("rooms", {})
        self.items: dict = data.get("items", {})
        self.characters: dict = data.get("characters", {})
        self.clues: dict = data.get("clues", {})
        self.actions: list = data.get("actions", [])
        self.hints: list = data.get("hints", [])
        self.endings: dict = data.get("endings", {})
        self.final: dict = data.get("final", {})
        self.verbs: dict = data.get("verbs", {})
        for ch in self.characters.values():
            ch["topics"] = {k: as_list(v) for k, v in ch.get("topics", {}).items()}
            ch["shows"] = {k: as_list(v) for k, v in ch.get("shows", {}).items()}
            ch["greeting"] = as_list(ch.get("greeting"))
        for i, a in enumerate(self.actions):
            a.setdefault("id", f"action{i}")

    # --- lookups ---------------------------------------------------------------

    def thing(self, tid: str) -> dict:
        return self.items.get(tid) or self.characters[tid]

    def is_item(self, tid: str) -> bool:
        return tid in self.items

    def is_character(self, tid: str) -> bool:
        return tid in self.characters

    def name(self, tid: str) -> str:
        if tid in self.rooms:
            return self.rooms[tid]["name"]
        return self.thing(tid)["name"]

    def article_name(self, tid: str) -> str:
        """'a candle', 'some caraway seeds', 'Mrs Hudson'."""
        t = self.thing(tid)
        art = t.get("article")
        if art is None:
            if tid in self.characters:
                return t["name"]
            art = "an" if t["name"][:1].lower() in "aeiou" else "a"
        return f"{art} {t['name']}" if art else t["name"]

    def scenery(self, tid: str) -> bool:
        return bool(self.items.get(tid, {}).get("scenery", False))

    def portable(self, tid: str) -> bool:
        it = self.items.get(tid)
        if it is None:
            return False
        return bool(it.get("portable", not it.get("scenery", False)))

    def listed(self, tid: str) -> bool:
        it = self.items.get(tid)
        if it is None:
            return False
        return bool(it.get("listed", not it.get("scenery", False)))

    def names_for(self, tid: str) -> list[str]:
        t = self.rooms.get(tid) or self.thing(tid)
        return [t["name"].lower()] + [a.lower() for a in t.get("aliases", [])]

    # --- case settings -----------------------------------------------------------

    def coin_name(self, n: int = 1) -> str:
        if n == 1:
            return self.case.get("coin_name", "coin")
        return self.case.get("coin_plural", self.coin_name(1) + "s")

    def coin_total(self) -> int:
        return sum(1 for it in self.items.values() if it.get("coin"))
