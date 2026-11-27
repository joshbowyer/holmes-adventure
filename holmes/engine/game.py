"""The exploration layer: the command loop and every built-in verb.

Story-defined `actions` are always tried before a built-in verb's default behaviour,
so a case can override anything (a locked drawer, a dark cellar, a special verb).
"""

from __future__ import annotations

from holmes.engine import saves
from holmes.engine.conditions import check, split_term
from holmes.engine.hints import give_hint
from holmes.engine.parser import DIRECTIONS, Command, build_verb_map, parse

PRONOUNS = {"him", "her", "them", "he", "she"}
from holmes.engine.state import GameState
from holmes.engine.story import Story, as_list
from holmes.puzzles import cylinder, morse
from holmes.puzzles.seating import has_seating, seat, show_plan, unseat
from holmes.puzzles.timeline import arrange, has_timeline, show_board

HELP = """\
| Moving about:   NORTH (N), SOUTH, EAST, WEST, UP, DOWN, IN, OUT,
|                 or GO <place>.  EXITS lists the ways on.
| Looking:        LOOK (L), EXAMINE (X) <thing or person>
| Handling:       TAKE, DROP, OPEN, CLOSE, USE <thing> [ON <thing>],
|                 INVENTORY (I), WAIT (Z), STATUS (time, light...)
| People:         TALK TO <person>, ASK <person> ABOUT <subject>,
|                 SHOW <thing> TO <person>
| Thinking:       NOTEBOOK (your clues), HINT (costs a {coin}),
|                 ACCUSE (when you are ready to name the truth)
| Other:          SAVE, QUIT (back to the menu; progress is kept),
|                 AGAIN (G) repeats your last command"""


# Verbs that take no time in the world: the tide does not turn while you read your notes.
# (WAIT runs its own turns.)
UNTIMED = {"notebook", "hint", "help", "save", "quit", "inventory", "exits", "accuse",
           "status", "look", "wait", "timeline", "arrange",
           "seating", "seat", "unseat",
           "tapes", "tape", "decode", "attribute", "codebook",
           "cylinders", "play", "source"}

# Typed alone (spaces and case ignored), grants one hint coin. Not listed in HELP.
CHEAT_WORD = "persianslipper"


def join_list(parts: list[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " and " + parts[-1]


class Game:
    def __init__(self, story: Story, console, state: GameState | None = None,
                 autosave: bool = True):
        self.story = story
        self.io = console
        self.state = state or GameState.new(story)
        if state is not None and not state.met:
            # saves from before `met` existed: count everyone in a room already visited
            state.met = {c for c in story.characters if state.loc(c) in state.visited}
        self.autosave = autosave
        self.verb_map = build_verb_map(story.verbs)
        self.last: Command | None = None
        self.finished = False
        self.failed = False

    # --- main loop -------------------------------------------------------------------

    def run(self) -> GameState:
        st = self.state
        if not st.visited:
            self.say(self.story.title.upper(), "heading")
            self.say(self.story.case.get("intro", ""))
            if self.story.case.get("intro_note"):
                self.say(self.story.case["intro_note"], "system")
            self.enter(st.room)
        else:
            self.say("You take up the threads of the case once more.", "system")
            self.describe_room()
        while not self.finished:
            line = self.io.read("> ")
            if line is None:
                break
            self.handle(line)
            if not self.finished:
                self.save()
        if not st.solved:
            self.save()
        return st

    def handle(self, line: str) -> None:
        if "".join(ch for ch in line.lower() if ch.isalpha()) == CHEAT_WORD:
            self.cheat_coin()
            return
        cmd = parse(line, self.verb_map)
        if cmd is None:
            return
        if cmd.verb == "again":
            if self.last is None:
                self.say("Again? We have done nothing yet.")
                return
            cmd = self.last
        else:
            self.last = cmd
        if cmd.verb is None:
            self.say(f"I do not quite follow you. (Type HELP for a list of commands.)", "system")
            return
        self.failed = False
        handler = getattr(self, "do_" + cmd.verb, None)
        (handler or self.do_custom)(cmd)
        if self.failed:
            return              # nothing happened, so no time passes
        self.state.turns += 1
        if cmd.verb not in UNTIMED and not self.finished:
            self.tick()

    def cheat_coin(self) -> None:
        """The secret word: one hint coin, free of time, in this case's own coinage."""
        st, coin = self.state, self.story.coin_name()
        st.coins += 1
        self.say(f"From the toe of a Persian slipper, among the shag tobacco, "
                 f"there drops a {coin}.")
        self.note(f"[{st.coins} {self.story.coin_name(st.coins)} in your purse.]")

    def tick(self) -> bool:
        """One turn of the world passing: the case's `every_turn` events (tides, a
        burning lamp...). Returns True if anything was said."""
        said = False
        for i, ev in enumerate(as_list(self.story.case.get("every_turn"))):
            if self.run_event(ev, f"turn:{i}") and ev.get("text"):
                said = True
        return said

    def status_text(self) -> str:
        parts = []
        for s in self.story.case.get("status", []):
            if check(self.state, s.get("when")):
                parts.append(s["text"].format_map(self.state.counters))
        return " ".join(parts)

    def save(self) -> None:
        if self.autosave and not self.state.solved:
            saves.save_game(self.state.to_dict())

    # --- output helpers --------------------------------------------------------------

    def say(self, text: str, kind: str | None = None) -> None:
        self.io.say(text, kind)

    def fail(self, text: str, kind: str | None = None) -> None:
        """Say why a command came to nothing. A failed command costs no turn."""
        self.failed = True
        self.say(text, kind)

    def note(self, text: str) -> None:
        self.io.say(text, "note")

    def styled_name(self, tid: str) -> str:
        kind = "person" if self.story.is_character(tid) else "item"
        return self.io.style(self.story.article_name(tid), kind)

    # --- world queries ---------------------------------------------------------------

    def is_dark(self) -> bool:
        room = self.story.rooms[self.state.room]
        return "dark_when" in room and check(self.state, room["dark_when"])

    def visible(self, tid: str) -> bool:
        t = self.story.items.get(tid) or self.story.characters.get(tid)
        return t is not None and check(self.state, t.get("visible_when"))

    def contents(self, place: str) -> list[str]:
        return [t for t, loc in self.state.locations.items() if loc == place and self.visible(t)]

    def accessible(self, tid: str) -> bool:
        """Can the player reach into this container? Only once it is open, or, for one
        that does not open, once it has been examined: what is in a jug or under a
        cushion is not in reach until the player has looked there."""
        it = self.story.items.get(tid, {})
        if not it.get("container"):
            return False
        if it.get("openable"):
            return tid in self.state.opened
        return tid in self.state.searched

    def takeable_contents(self, place: str) -> list[str]:
        """What the game lists as 'you see': only things the player can pick up."""
        return [t for t in self.contents(place) if self.story.listed(t) and self.story.portable(t)]

    def gather(self, place: str) -> list[str]:
        out = []
        for tid in self.contents(place):
            out.append(tid)
            if self.accessible(tid):
                out += self.gather(tid)
        return out

    def scope(self) -> list[str]:
        held = self.gather("player")
        if self.is_dark():
            return held
        return self.gather(self.state.room) + held

    def match(self, phrase: str, candidates: list[str]) -> list[str]:
        phrase = phrase.strip().lower()
        words = phrase.replace("-", " ").split()
        exact, partial = [], []
        for tid in candidates:
            names = self.story.names_for(tid)
            if phrase in names:
                exact.append(tid)
                continue
            vocab = set()
            for n in names:
                vocab.update(n.replace("-", " ").split())
            if words and all(w in vocab for w in words):
                partial.append(tid)
        if len(exact) > 1:
            # "telegram" means the thing called a telegram, not one with it as an alias
            named = [t for t in exact if self.story.names_for(t)[0] == phrase]
            if len(named) == 1:
                return named
        return exact or partial

    def resolve(self, phrase: str, candidates: list[str] | None = None) -> str | None:
        found = self.match(phrase, self.scope() if candidates is None else candidates)
        if len(found) == 1:
            return found[0]
        if not found:
            if self.is_dark():
                self.fail("It is too dark to make anything out.")
            else:
                self.fail(f"I see no {phrase} here.")
            return None
        names = [self.story.article_name(t) for t in found]
        self.fail(f"Which do you mean: {join_list(names).replace(' and ', ' or ')}?")
        return None

    # --- events and effects ----------------------------------------------------------

    def run_event(self, ev: dict, key: str) -> bool:
        if ev.get("once") and key in self.state.fired:
            return False
        if not check(self.state, ev.get("when")):
            return False
        if ev.get("once"):
            self.state.fired.add(key)
        if ev.get("text"):
            self.say(ev["text"])
        self.apply(ev.get("effects"))
        return True

    def run_all(self, events, key: str) -> bool:
        ran = False
        for i, ev in enumerate(as_list(events)):
            ran = self.run_event(ev, f"{key}:{i}") or ran
        return ran

    def run_first(self, events, key: str) -> bool:
        return any(self.run_event(ev, f"{key}:{i}") for i, ev in enumerate(as_list(events)))

    def apply(self, effects) -> None:
        st = self.state
        for eff in as_list(effects):
            _, kind, args = split_term(eff)
            if kind == "set":
                st.flags.add(args[0])
            elif kind == "unset":
                st.flags.discard(args[0])
            elif kind == "clue":
                self.add_clue(args[0])
            elif kind == "move":
                st.locations[args[0]] = args[1]
            elif kind == "give":
                st.locations[args[0]] = "player"
            elif kind == "remove":
                st.locations[args[0]] = "nowhere"
            elif kind == "open":
                st.opened.add(args[0])
            elif kind == "close":
                st.opened.discard(args[0])
            elif kind == "goto":
                self.enter(args[0])
            elif kind == "look":
                self.describe_room()
            elif kind == "add":
                st.counters[args[0]] = st.counters.get(args[0], 0) + int(args[1])
            elif kind == "setn":
                st.counters[args[0]] = int(args[1])
            else:
                raise ValueError(f"unknown effect {eff!r}")

    def add_clue(self, cid: str) -> None:
        if cid not in self.state.clues:
            self.state.clues.append(cid)
            self.note("[Noted in your notebook.]")

    def try_actions(self, verb: str, target: str | None, with_: str | None = None) -> bool:
        for a in self.story.actions:
            if verb not in as_list(a["verb"]):
                continue
            targets = as_list(a.get("target"))
            if targets and target not in targets:
                continue
            if not targets and target is not None:
                continue
            withs = as_list(a.get("with"))
            if withs and with_ not in withs:
                continue
            if self.run_event(a, a["id"]):
                return True
        return False

    # --- rooms -------------------------------------------------------------------------

    def enter(self, room_id: str) -> None:
        self.state.room = room_id
        self.describe_room()
        room = self.story.rooms[room_id]
        self.run_all(room.get("on_enter"), f"enter:{room_id}")

    def describe_room(self) -> None:
        st, story = self.state, self.story
        room = story.rooms[st.room]
        st.visited.add(st.room)
        self.say(room["name"], "title")
        if self.is_dark():
            self.say(room.get("dark_text", "It is too dark to see anything at all."))
            self.show_exits()
            self.show_status()
            return
        text = room["description"].rstrip()
        extras = [d["text"].strip() for d in room.get("details", []) if check(st, d.get("when"))]
        if extras:
            text += " " + " ".join(extras)
        self.say(text)
        here = self.contents(st.room)
        items = self.takeable_contents(st.room)
        if items:
            self.say("You notice " + join_list([self.styled_name(t) for t in items]) + ".")
        for c in here:
            if story.is_character(c):
                ch = story.characters[c]
                self.say(ch.get("presence") or f"{ch['name']} is here.", "person")
        self.show_exits()
        self.show_status()

    def show_status(self) -> None:
        text = self.status_text()
        if text:
            self.say(text, "note")

    def exits(self) -> dict[str, dict]:
        out = {}
        for d, ex in self.story.rooms[self.state.room].get("exits", {}).items():
            ex = {"to": ex} if isinstance(ex, str) else ex
            if check(self.state, ex.get("visible_when")):
                out[d] = ex
        return out

    def show_exits(self) -> None:
        parts = []
        for d, ex in self.exits().items():
            label = d
            if ex.get("to") in self.state.visited:
                label += f" ({self.story.rooms[ex['to']]['name']})"
            parts.append(label)
        if parts:
            self.say("Ways on: " + ", ".join(parts) + ".", "exit")
        else:
            self.say("There is no obvious way on.", "exit")

    # --- built-in verbs ----------------------------------------------------------------

    def do_go(self, cmd: Command) -> None:
        if not cmd.obj:
            self.fail("Which way?")
            return
        exits = self.exits()
        key = cmd.obj if cmd.obj in exits else None
        if key is None:
            words = cmd.obj.replace("-", " ").split()
            for d, ex in exits.items():
                names = [a.lower() for a in ex.get("aliases", [])]
                if ex.get("to"):
                    names += self.story.names_for(ex["to"])
                vocab = {w for n in names for w in n.replace("-", " ").split()}
                if cmd.obj in names or (words and all(w in vocab for w in words)):
                    key = d
                    break
        if key is None:
            if cmd.obj in DIRECTIONS.values():
                self.fail("You cannot go that way.")
            else:
                self.fail(f"I see no way to {cmd.obj} from here.")
            return
        ex = exits[key]
        if not ex.get("to") or not check(self.state, ex.get("when")):
            self.fail(ex.get("blocked", "The way is barred."))
            return
        if ex.get("text"):
            self.say(ex["text"])
        self.enter(ex["to"])

    def do_look(self, cmd: Command) -> None:
        self.describe_room()

    def do_exits(self, cmd: Command) -> None:
        self.show_exits()

    def do_examine(self, cmd: Command) -> None:
        if not cmd.obj:
            self.fail("Examine what?")
            return
        if cmd.obj in ("room", "around", "here", "about"):
            self.describe_room()
            return
        tid = self.resolve(cmd.obj)
        if tid is not None and self.story.items.get(tid, {}).get("container"):
            self.state.searched.add(tid)     # even when a story action does the describing
        if tid is None or self.try_actions("examine", tid):
            return
        self.examine(tid)

    def examine(self, tid: str) -> None:
        story, st = self.story, self.state
        t = story.thing(tid)
        text = t.get("description", "You see nothing remarkable.").rstrip()
        extras = [d["text"].strip() for d in t.get("details", []) if check(st, d.get("when"))]
        if extras:
            text += " " + " ".join(extras)
        self.say(text)
        if t.get("container"):
            st.searched.add(tid)
        if self.accessible(tid):
            inside = self.takeable_contents(tid)
            if inside:
                self.say(f"In the {t['name']} you see " +
                         join_list([self.styled_name(i) for i in inside]) + ".")
            elif t.get("openable"):
                self.say("It is empty.")
        elif t.get("container") and t.get("openable"):
            self.say(f"The {t['name']} is shut.")
        if t.get("clue"):
            self.add_clue(t["clue"])
            morse.show_item_tape(self, t["clue"])
            cylinder.note_item_cylinder(self, t["clue"])
        self.run_all(t.get("on_examine"), f"examine:{tid}")

    def do_take(self, cmd: Command) -> None:
        story, st = self.story, self.state
        if not cmd.obj:
            self.fail("Take what?")
            return
        if cmd.obj in ("all", "everything"):
            self.fail("One thing at a time, as Holmes would say.")
            return
        tid = self.resolve(cmd.obj)
        if tid is None or self.try_actions("take", tid):
            return
        if story.is_character(tid):
            self.fail(f"You can hardly carry off {story.name(tid)}.")
            return
        if st.loc(tid) == "player":
            self.fail("You have it already.")
            return
        it = story.items[tid]
        if not story.portable(tid):
            self.fail(it.get("cant_take", "That is not something you can carry off."))
            return
        if it.get("coin"):
            st.locations[tid] = "spent"
            st.coins += 1
            st.coins_found += 1
            self.say(it.get("take_text", f"You pocket the {story.coin_name()}."))
            self.note(f"[{st.coins} {story.coin_name(st.coins)} in your purse. "
                      f"HINT spends one.]")
            return
        st.locations[tid] = "player"
        self.say(it.get("take_text", "Taken."))
        self.apply(it.get("on_take"))

    def do_drop(self, cmd: Command) -> None:
        if not cmd.obj:
            self.fail("Drop what?")
            return
        tid = self.resolve(cmd.obj, self.gather("player"))
        if tid is None or self.try_actions("drop", tid):
            return
        if self.state.loc(tid) != "player":
            self.fail("You are not carrying that.")
            return
        self.state.locations[tid] = self.state.room
        self.say("Dropped.")

    def do_open(self, cmd: Command) -> None:
        self._open_close(cmd, True)

    def do_close(self, cmd: Command) -> None:
        self._open_close(cmd, False)

    def _open_close(self, cmd: Command, opening: bool) -> None:
        verb = "open" if opening else "close"
        if not cmd.obj:
            self.fail(f"{verb.capitalize()} what?")
            return
        tid = self.resolve(cmd.obj)
        if tid is None or self.try_actions(verb, tid):
            return
        it = self.story.items.get(tid, {})
        if not it.get("openable"):
            self.fail(f"That is not something you can {verb}.")
            return
        is_open = tid in self.state.opened
        if is_open == opening:
            self.fail(f"It is already {'open' if opening else 'closed'}.")
            return
        if opening:
            self.state.opened.add(tid)
            self.say(it.get("open_text", f"You open the {it['name']}."))
            if self.accessible(tid):
                inside = self.takeable_contents(tid)
                self.say((f"Inside you see " + join_list([self.styled_name(i) for i in inside]) + ".")
                         if inside else "It is empty.")
        else:
            self.state.opened.discard(tid)
            self.say(it.get("close_text", f"You close the {it['name']}."))

    def do_inventory(self, cmd: Command) -> None:
        held = self.contents("player")
        if held:
            self.say("You are carrying " + join_list([self.styled_name(t) for t in held]) + ".")
        else:
            self.say("You are carrying nothing of note.")
        n = self.state.coins
        self.note(f"[{n} {self.story.coin_name(n)} in your purse.]")

    def _people_here(self) -> list[str]:
        return [c for c in self.contents(self.state.room) if self.story.is_character(c)]

    def _person(self, phrase: str, verb: str) -> str | None:
        people = self._people_here()
        if phrase in PRONOUNS:
            # "ask him about…": the one person here, or the last one spoken to here.
            last = getattr(self, "last_person", None)
            if len(people) == 1:
                phrase = ""
            elif last in people:
                return last
            else:
                self.fail(f"{verb.capitalize()} whom? Name them.")
                return None
        if not phrase:
            if len(people) == 1:
                self.state.met.add(people[0])
                self.last_person = people[0]
                return people[0]
            self.fail(f"{verb.capitalize()} whom?")
            return None
        tid = self.resolve(phrase)
        if tid is None:
            return None
        if not self.story.is_character(tid):
            self.fail("You receive no answer.")
            return None
        self.state.met.add(tid)
        self.last_person = tid
        return tid

    def do_talk(self, cmd: Command) -> None:
        tid = self._person(cmd.obj, "talk to")
        if tid is None or self.try_actions("talk", tid):
            return
        ch = self.story.characters[tid]
        if not self.run_first(ch["greeting"], f"greet:{tid}"):
            self.say(f"{ch['name']} regards you expectantly.")
        self.say(f"(Try ASK {ch['name'].upper()} ABOUT something.)", "system")

    def do_ask(self, cmd: Command) -> None:
        if cmd.prep == "about":
            who, topic = cmd.obj, cmd.obj2
        elif cmd.prep == "for" and not cmd.obj2:
            who, topic = cmd.obj, ""
        else:
            # "ask about the cake" parses as obj="", or "ask cake" with nobody named
            who, topic = "", cmd.obj2 or cmd.obj
        if not topic:
            self.fail("Ask about what? (For example: ASK MRS HUDSON ABOUT THE CAKE.)", "system")
            return
        tid = self._person(who, "ask")
        if tid is None:
            return
        ch = self.story.characters[tid]
        key = self._topic_key(ch, topic)
        if key is None or not self.run_first(ch["topics"][key], f"topic:{tid}:{key}"):
            self.fail(ch.get("unknown_topic") or f"{ch['name']} has nothing to say on that head.")

    def _topic_key(self, ch: dict, topic: str) -> str | None:
        topic = topic.strip().lower()
        words = topic.replace("-", " ").split()
        partial = None
        for key, variants in ch["topics"].items():
            names = [key.replace("_", " ")]
            for v in variants:
                names += [a.lower() for a in v.get("aliases", [])]
            if topic in names:
                return key
            vocab = {w for n in names for w in n.replace("-", " ").split()}
            if partial is None and words and all(w in vocab for w in words):
                partial = key
        if partial:
            return partial
        # "ask hudson about the seeds" -> a topic keyed by the thing's id
        everything = list(self.story.items) + list(self.story.characters)
        for tid in self.match(topic, everything):
            if tid in ch["topics"]:
                return tid
        return None

    def do_show(self, cmd: Command) -> None:
        if not cmd.obj or not cmd.obj2:
            self.fail("Show what to whom? (For example: SHOW THE LETTER TO HOLMES.)", "system")
            return
        item = self.resolve(cmd.obj, self.gather("player"))
        if item is None:
            return
        tid = self._person(cmd.obj2, "show it to")
        if tid is None or self.try_actions("show", item, tid):
            return
        ch = self.story.characters[tid]
        if not self.run_first(ch["shows"].get(item), f"show:{tid}:{item}"):
            self.fail(ch.get("unknown_show") or f"{ch['name']} glances at it without interest.")

    def do_use(self, cmd: Command) -> None:
        if not cmd.obj:
            self.fail("Use what?")
            return
        tid = self.resolve(cmd.obj)
        if tid is None:
            return
        tid2 = None
        if cmd.obj2:
            tid2 = self.resolve(cmd.obj2)
            if tid2 is None:
                return
        if self.try_actions("use", tid, tid2):
            return
        if tid2 and self.try_actions("use", tid2, tid):
            return
        self.fail("Nothing comes of that.")

    def do_custom(self, cmd: Command) -> None:
        """A verb the story defines (light, pull, climb...): only actions give it meaning."""
        tid = tid2 = None
        if cmd.obj:
            tid = self.resolve(cmd.obj)
            if tid is None:
                return
        if cmd.obj2:
            tid2 = self.resolve(cmd.obj2)
            if tid2 is None:
                return
        if self.try_actions(cmd.verb, tid, tid2):
            return
        fail = self.story.case.get("verb_fail", {}).get(cmd.verb)
        self.fail(fail or "Nothing comes of it.")

    def do_wait(self, cmd: Command) -> None:
        """Lets several turns pass (case.wait_turns), stopping early if anything happens."""
        case = self.story.case
        self.say(case.get("wait_text", "Time passes."))
        for i in range(max(1, int(case.get("wait_turns", 1)))):
            if i:
                self.state.turns += 1   # handle() counts the first
            if self.tick() or self.finished:
                break

    def do_status(self, cmd: Command) -> None:
        self.say(self.status_text() or "Nothing presses upon you but the case itself.", "note")

    def do_notebook(self, cmd: Command) -> None:
        st, story = self.state, self.story
        self.say(f"NOTEBOOK: {story.title}", "heading")
        if not st.clues:
            self.say("My notebook is as yet a blank page.")
        for i, cid in enumerate(st.clues, 1):
            self.say(f"{i}. {story.clues[cid]['text'].strip()}")
        n = st.coins
        self.note(f"[{n} {story.coin_name(n)} in your purse.]")

    def do_hint(self, cmd: Command) -> None:
        give_hint(self)

    def do_accuse(self, cmd: Command) -> None:
        from holmes.puzzles import run_final
        run_final(self)

    def do_help(self, cmd: Command) -> None:
        text = HELP.format(coin=self.story.coin_name())
        if has_timeline(self):
            text += ("\n| Timeline:       TIMELINE shows the events you can fix to a time;"
                     "\n|                 ARRANGE <letters> puts them in order")
        if has_seating(self):
            text += ("\n| Seating:        SEATING shows who sat where; SEAT <name> AT <number>"
                     "\n|                 places a sitter, UNSEAT <name> takes them out")
        if morse.has_morse(self):
            text += ("\n| Tapes:          TAPES lists the passages of tape you hold;"
                     "\n|                 TAPE <letter> shows its marks; CODEBOOK the alphabet"
                     "\n|                 DECODE <letter> AS <words> tries a reading"
                     "\n|                 ATTRIBUTE <letter> TO <name> says who sent it")
        if cylinder.has_cylinder(self):
            text += ("\n| Cylinders:      CYLINDERS lists the cylinders you hold;"
                     "\n|                 PLAY <letter> AT <speed> plays one at the machine"
                     "\n|                 SOURCE <number> FROM <letter> says where a part of"
                     "\n|                 the questioned cylinder was copied from")
        self.say(text, "system")

    def _no_tapes(self) -> bool:
        if morse.has_morse(self):
            return False
        self.fail("There are no telegraph tapes to be read in this case.")
        return True

    def do_tapes(self, cmd: Command) -> None:
        if not self._no_tapes():
            morse.show_board(self)

    def do_tape(self, cmd: Command) -> None:
        if not self._no_tapes():
            morse.show_tapes(self, self._rest(cmd))

    def do_decode(self, cmd: Command) -> None:
        if not self._no_tapes():
            morse.decode(self, self._rest(cmd))

    def do_attribute(self, cmd: Command) -> None:
        if not self._no_tapes():
            morse.attribute(self, self._rest(cmd))

    def do_codebook(self, cmd: Command) -> None:
        if not self._no_tapes():
            morse.show_codebook(self)

    def _no_cylinders(self) -> bool:
        if cylinder.has_cylinder(self):
            return False
        self.fail("There are no phonograph cylinders to be played in this case.")
        return True

    def do_cylinders(self, cmd: Command) -> None:
        if not self._no_cylinders():
            cylinder.show_board(self)

    def do_play(self, cmd: Command) -> None:
        if not self._no_cylinders():
            cylinder.play(self, self._rest(cmd))

    def do_source(self, cmd: Command) -> None:
        if not self._no_cylinders():
            cylinder.source(self, self._rest(cmd))

    def do_timeline(self, cmd: Command) -> None:
        if not has_timeline(self):
            self.fail("There is no timeline to be built in this case.")
            return
        show_board(self)

    def do_arrange(self, cmd: Command) -> None:
        if not has_timeline(self):
            self.fail("There is no timeline to be built in this case.")
            return
        text = cmd.raw.split(None, 1)[1] if len(cmd.raw.split(None, 1)) > 1 else ""
        arrange(self, text)

    def _rest(self, cmd: Command) -> str:
        parts = cmd.raw.split(None, 1)
        return parts[1] if len(parts) > 1 else ""

    def do_seating(self, cmd: Command) -> None:
        if not has_seating(self):
            self.fail("There is no seating plan to be made in this case.")
            return
        show_plan(self)

    def do_seat(self, cmd: Command) -> None:
        if not has_seating(self):
            self.fail("There is no seating plan to be made in this case.")
            return
        seat(self, self._rest(cmd))

    def do_unseat(self, cmd: Command) -> None:
        if not has_seating(self):
            self.fail("There is no seating plan to be made in this case.")
            return
        unseat(self, self._rest(cmd))

    def do_save(self, cmd: Command) -> None:
        self.save()
        self.say("[Your progress is saved.]", "system")

    def do_quit(self, cmd: Command) -> None:
        self.save()
        self.say("You set the case aside for now. Your progress is kept.", "system")
        self.finished = True

    # --- endings -------------------------------------------------------------------------

    def show_ending(self, eid: str) -> None:
        e = self.story.endings[eid]
        if e.get("title"):
            self.say(e["title"], "title")
        self.say(e["text"])

    def case_closed(self) -> None:
        st, story = self.state, self.story
        st.solved = True
        self.say("CASE CLOSED", "heading")
        total = story.coin_total()
        self.say("\n".join([
            f"| Wrong conclusions: {st.wrong}",
            f"| {story.coin_name(2).capitalize()} found:  {st.coins_found} of {total}",
            f"| Hints bought:      {st.hints_bought}",
            f"| Turns taken:       {st.turns}",
        ]), "note")
        if self.autosave:
            saves.delete_game(story.id)
        self.finished = True
