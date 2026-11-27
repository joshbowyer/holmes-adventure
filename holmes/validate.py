"""Structural checks on story data. Reports ids only, never story prose.

Catches typos and dead ends: references to things that do not exist, flags that are
tested but never set, clues that can never be found, rooms nobody can reach, and a
final puzzle whose answer or endings are missing.
"""

from __future__ import annotations

from holmes.engine.conditions import COND_ARITY, EFFECT_ARITY, alternatives, split_term
from holmes.engine.parser import BUILTIN_VERBS, DIRECTIONS
from holmes.engine.story import as_list


def _events(v) -> list[dict]:
    return [e for e in as_list(v) if isinstance(e, dict)]


def validate(data: dict) -> list[str]:
    errs: list[str] = []
    case = data.get("case", {})
    rooms = data.get("rooms", {})
    items = data.get("items", {})
    chars = data.get("characters", {})
    clues = data.get("clues", {})
    endings = data.get("endings", {})
    verbs = set(BUILTIN_VERBS) | set(data.get("verbs", {}))
    things = set(items) | set(chars)
    places = set(rooms) | set(items) | {"player", "nowhere"}

    for k in ("id", "title", "start", "intro"):
        if k not in case:
            errs.append(f"case: missing {k}")
    if case.get("start") not in rooms:
        errs.append(f"case: start room {case.get('start')!r} does not exist")
    dupes = (set(rooms) & things) | (set(items) & set(chars))
    for d in sorted(dupes):
        errs.append(f"id {d!r} is used by more than one room/item/character")

    clue_from_decoding: set[str] = set()
    conds: list[tuple[str, object]] = []
    effects: list[tuple[str, object]] = []
    counters = case.get("counters", {})
    for k, v in counters.items():
        if not isinstance(v, int):
            errs.append(f"case: counter {k!r} must start at a whole number")

    def events(where: str, evs) -> None:
        for i, e in enumerate(_events(evs)):
            conds.append((f"{where}[{i}].when", e.get("when")))
            effects.append((f"{where}[{i}].effects", e.get("effects")))

    def counter_ref(where: str, term: str, args: list[str]) -> None:
        if args[0] not in counters:
            errs.append(f"{where}: unknown counter in {term!r} (declare it in case.counters)")
        try:
            int(args[1])
        except ValueError:
            errs.append(f"{where}: {term!r} needs a whole number")

    events("case.every_turn", case.get("every_turn"))
    for i, s in enumerate(case.get("status", [])):
        conds.append((f"case.status[{i}]", s.get("when")))
        try:
            s.get("text", "").format_map(counters)
        except (KeyError, ValueError, IndexError):
            errs.append(f"case.status[{i}]: text names an unknown counter")

    # rooms
    for rid, r in rooms.items():
        for k in ("name", "description"):
            if k not in r:
                errs.append(f"room {rid}: missing {k}")
        for d, ex in r.get("exits", {}).items():
            ex = {"to": ex} if isinstance(ex, str) else ex
            if d not in DIRECTIONS.values():
                errs.append(f"room {rid}: exit {d!r} is not a direction")
            if "to" not in ex and "blocked" not in ex:
                errs.append(f"room {rid}: exit {d} needs 'to' (or 'blocked' for a barred way)")
            elif "to" in ex and ex["to"] not in rooms:
                errs.append(f"room {rid}: exit {d} leads to unknown room {ex.get('to')!r}")
            conds.append((f"room {rid} exit {d}.when", ex.get("when")))
            conds.append((f"room {rid} exit {d}.visible_when", ex.get("visible_when")))
        for i, det in enumerate(r.get("details", [])):
            conds.append((f"room {rid} details[{i}]", det.get("when")))
        conds.append((f"room {rid}.dark_when", r.get("dark_when")))
        events(f"room {rid}.on_enter", r.get("on_enter"))

    # items
    for iid, it in items.items():
        for k in ("name", "description"):
            if k not in it:
                errs.append(f"item {iid}: missing {k}")
        loc = it.get("location", "nowhere")
        if loc not in places:
            errs.append(f"item {iid}: unknown location {loc!r}")
        conds.append((f"item {iid}.visible_when", it.get("visible_when")))
        for i, det in enumerate(it.get("details", [])):
            conds.append((f"item {iid} details[{i}]", det.get("when")))
        events(f"item {iid}.on_examine", it.get("on_examine"))
        effects.append((f"item {iid}.on_take", it.get("on_take")))
        if "clue" in it and it["clue"] not in clues:
            errs.append(f"item {iid}: unknown clue {it['clue']!r}")

    # characters
    for cid, ch in chars.items():
        for k in ("name", "description"):
            if k not in ch:
                errs.append(f"character {cid}: missing {k}")
        if ch.get("location", "nowhere") not in set(rooms) | {"nowhere"}:
            errs.append(f"character {cid}: unknown location {ch.get('location')!r}")
        conds.append((f"character {cid}.visible_when", ch.get("visible_when")))
        for i, det in enumerate(ch.get("details", [])):
            conds.append((f"character {cid} details[{i}]", det.get("when")))
        events(f"character {cid}.on_examine", ch.get("on_examine"))
        events(f"character {cid}.greeting", ch.get("greeting"))
        for key, vs in ch.get("topics", {}).items():
            events(f"character {cid} topic {key}", vs)
        for key, vs in ch.get("shows", {}).items():
            if key not in items:
                errs.append(f"character {cid}: show for unknown item {key!r}")
            events(f"character {cid} show {key}", vs)
        if "clue" in ch and ch["clue"] not in clues:
            errs.append(f"character {cid}: unknown clue {ch['clue']!r}")

    # actions
    for i, a in enumerate(data.get("actions", [])):
        where = f"action {a.get('id', i)}"
        for v in as_list(a.get("verb")):
            if v not in verbs:
                errs.append(f"{where}: unknown verb {v!r} (add it under [verbs])")
        if not as_list(a.get("verb")):
            errs.append(f"{where}: missing verb")
        for t in as_list(a.get("target")) + as_list(a.get("with")):
            if t not in things:
                errs.append(f"{where}: unknown thing {t!r}")
        events(where, [a])

    # hints
    seen = set()
    for i, h in enumerate(data.get("hints", [])):
        hid = h.get("id")
        if not hid or hid in seen:
            errs.append(f"hint {i}: missing or duplicate id {hid!r}")
        seen.add(hid)
        if not as_list(h.get("texts")):
            errs.append(f"hint {hid}: no texts")
        conds.append((f"hint {hid}.when", h.get("when")))
        conds.append((f"hint {hid}.done", h.get("done")))

    # final puzzle
    final = data.get("final")
    if not final:
        errs.append("final: missing")
    elif final.get("type", "accuse") in ("accuse", "timeline", "seating", "morse"):
        if final.get("type") == "morse":
            from holmes.puzzles.morse import MORSE
            ms = final.get("morse", {})
            fists, senders = ms.get("fists", {}), ms.get("senders", {})
            passages, answer = ms.get("passages", {}), ms.get("answer", {})
            conds.append(("final morse.codebook_when", ms.get("codebook_when")))
            for k, f in fists.items():
                for n in ("dot", "dash", "gap", "letter", "word"):
                    if not isinstance(f.get(n), int) or f[n] < 1:
                        errs.append(f"final morse: fist {k!r} needs a whole-number {n}")
            for k, s in senders.items():
                if not s.get("name"):
                    errs.append(f"final morse: sender {k!r} has no name")
                conds.append((f"final morse sender {k}.when", s.get("when")))
            if len(passages) > 26:
                errs.append("final morse: more than 26 passages")
            for pid, p in passages.items():
                if p.get("deal") not in clues:
                    errs.append(f"final morse: passage {pid!r} is dealt by unknown clue {p.get('deal')!r}")
                if p.get("fist") not in fists:
                    errs.append(f"final morse: passage {pid!r} has unknown fist {p.get('fist')!r}")
                if not p.get("label"):
                    errs.append(f"final morse: passage {pid!r} has no label")
                bad = {ch for ch in p.get("text", "").upper() if ch != " " and ch not in MORSE}
                if not p.get("text", "").strip() or bad:
                    errs.append(f"final morse: passage {pid!r} text must be letters, figures and spaces")
                if p.get("clue"):
                    if p["clue"] not in clues:
                        errs.append(f"final morse: passage {pid!r} gives unknown clue {p['clue']!r}")
                    clue_from_decoding.add(p["clue"])
                if p.get("sender"):
                    if p["sender"] not in senders:
                        errs.append(f"final morse: passage {pid!r} has unknown sender {p['sender']!r}")
                    if pid in answer:
                        errs.append(f"final morse: passage {pid!r} has a known sender and an answer")
                elif answer.get(pid) not in senders:
                    errs.append(f"final morse: passage {pid!r} needs an answer naming a sender")
            for pid in answer:
                if pid not in passages:
                    errs.append(f"final morse: answer for unknown passage {pid!r}")
            for key in ("wrong_ending", "incomplete_ending"):
                if (key in ms or key == "wrong_ending") and ms.get(key) not in endings:
                    errs.append(f"final morse: {key} {ms.get(key)!r} does not exist")
        if final.get("type") == "seating":
            sp = final.get("seating", {})
            seat_ids = [pl.get("id") for pl in sp.get("places", [])]
            people, answer = sp.get("people", {}), sp.get("answer", {})
            if len(seat_ids) < 3 or len(set(seat_ids)) != len(seat_ids):
                errs.append("final seating: needs three or more places with distinct ids")
            if set(answer) != set(seat_ids):
                errs.append("final seating: answer must seat every place")
            if sorted(answer.values()) != sorted(people):
                errs.append("final seating: answer must place every sitter exactly once")
            for k, pp in people.items():
                if not pp.get("name"):
                    errs.append(f"final seating: sitter {k!r} has no name")
                if pp.get("fixed") and answer.get(pp["fixed"]) != k:
                    errs.append(f"final seating: sitter {k!r} is fixed at the wrong place")
                conds.append((f"final seating sitter {k}.when", pp.get("when")))
            for key in ("wrong_ending", "incomplete_ending"):
                if (key in sp or key == "wrong_ending") and sp.get(key) not in endings:
                    errs.append(f"final seating: {key} {sp.get(key)!r} does not exist")
        if final.get("type") == "timeline":
            tl = final.get("timeline", {})
            cards, order = tl.get("cards", {}), tl.get("order", [])
            for cid, card in cards.items():
                if isinstance(card, dict):
                    if not isinstance(card.get("event"), str) or not card.get("says"):
                        errs.append(f"final timeline: card {cid!r} needs an event and says")
                    for clue in card.get("says", {}):
                        if clue not in clues:
                            errs.append(f"final timeline: card {cid!r} says {clue!r}, not a clue")
                elif cid not in clues:
                    errs.append(f"final timeline: card {cid!r} is not a clue")
            if sorted(order) != sorted(cards) or len(set(order)) != len(order):
                errs.append("final timeline: order must list every card exactly once")
            if len(cards) > 26:
                errs.append("final timeline: more than 26 cards")
            if tl.get("incomplete_ending", tl.get("wrong_ending")) not in endings:
                errs.append(f"final timeline: incomplete_ending {tl.get('incomplete_ending')!r} does not exist")
            if tl.get("wrong_ending") not in endings:
                errs.append(f"final timeline: wrong_ending {tl.get('wrong_ending')!r} does not exist")
        conds.append(("final.when", final.get("when")))
        qopts = {}
        for q in final.get("questions", []):
            ids = [o.get("id") for o in q.get("options", [])]
            if len(set(ids)) != len(ids):
                errs.append(f"final question {q.get('id')}: duplicate option ids")
            qopts[q.get("id")] = set(ids)
            if all(o.get("when") for o in q.get("options", [])):
                errs.append(f"final question {q.get('id')}: needs an option offered from the start")
            for o in q.get("options", []):
                conds.append((f"final option {o.get('id')}.when", o.get("when")))
        sol = final.get("solution", {})
        if set(sol) != set(qopts):
            errs.append("final: solution must answer every question")
        for k, v in sol.items():
            if v not in qopts.get(k, set()):
                errs.append(f"final: solution {k}={v!r} is not an option")
        for k in ("good", "default_wrong"):
            if final.get(k) not in endings:
                errs.append(f"final: {k} ending {final.get(k)!r} does not exist")
        for w in final.get("wrong", []):
            if w.get("ending") not in endings:
                errs.append(f"final: wrong ending {w.get('ending')!r} does not exist")
            for k, v in w.get("answers", {}).items():
                if v not in qopts.get(k, set()):
                    errs.append(f"final: wrong answer {k}={v!r} is not an option")
    else:
        errs.append(f"final: unknown type {final.get('type')!r}")

    # effects: syntax, references, and what they make possible
    flags_set: set[str] = set()
    clues_given = {it["clue"] for it in items.values() if "clue" in it}
    clues_given |= {ch["clue"] for ch in chars.values() if "clue" in ch}
    clues_given |= clue_from_decoding
    gotos: list[str] = []
    for where, effs in effects:
        for e in as_list(effs):
            neg, kind, args = split_term(e)
            if neg or kind not in EFFECT_ARITY or len(args) != EFFECT_ARITY[kind]:
                errs.append(f"{where}: bad effect {e!r}")
                continue
            if kind in ("set", "unset"):
                flags_set.add(args[0])
            elif kind == "clue":
                clues_given.add(args[0])
                if args[0] not in clues:
                    errs.append(f"{where}: unknown clue {args[0]!r}")
            elif kind == "move":
                if args[0] not in things:
                    errs.append(f"{where}: unknown thing {args[0]!r}")
                if args[1] not in places:
                    errs.append(f"{where}: unknown place {args[1]!r}")
            elif kind in ("give", "open", "close") and args[0] not in items:
                errs.append(f"{where}: unknown item {args[0]!r}")
            elif kind == "remove" and args[0] not in things:
                errs.append(f"{where}: unknown thing {args[0]!r}")
            elif kind == "goto":
                gotos.append(args[0])
                if args[0] not in rooms:
                    errs.append(f"{where}: unknown room {args[0]!r}")
            elif kind in ("add", "setn"):
                counter_ref(where, e, args)

    # conditions: syntax and references
    for where, cond in conds:
        for ors in alternatives(cond):
            for term in ors:
                _, kind, args = split_term(term)
                if kind not in COND_ARITY or len(args) != COND_ARITY[kind]:
                    errs.append(f"{where}: bad condition {term!r}")
                    continue
                a = args[0]
                if kind == "flag" and a not in flags_set:
                    errs.append(f"{where}: flag {a!r} is tested but never set")
                elif kind in ("has", "open") and a not in items:
                    errs.append(f"{where}: unknown item {a!r}")
                elif kind in ("at", "visited") and a not in rooms:
                    errs.append(f"{where}: unknown room {a!r}")
                elif kind == "met" and a not in chars:
                    errs.append(f"{where}: unknown person {a!r}")
                elif kind == "clue" and a not in clues:
                    errs.append(f"{where}: unknown clue {a!r}")
                elif kind == "loc" and (a not in things or args[1] not in places):
                    errs.append(f"{where}: bad loc reference {term!r}")
                elif kind in ("lt", "ge", "eq"):
                    counter_ref(where, term, args)

    for cid in clues:
        if "text" not in clues[cid]:
            errs.append(f"clue {cid}: missing text")
        if cid not in clues_given:
            errs.append(f"clue {cid}: can never be found")

    # every room reachable from the start (ignoring conditions)
    start = case.get("start")
    if start in rooms:
        reach, todo = {start}, [start]
        while todo:
            r = todo.pop()
            for ex in rooms[r].get("exits", {}).values():
                to = ex if isinstance(ex, str) else ex.get("to")
                if to in rooms and to not in reach:
                    reach.add(to)
                    todo.append(to)
            if not todo:
                for g in gotos:
                    if g in rooms and g not in reach:
                        reach.add(g)
                        todo.append(g)
        for r in sorted(set(rooms) - reach):
            errs.append(f"room {r}: unreachable")

    if not any(it.get("coin") for it in items.values()):
        errs.append("case: no hint coins anywhere")
    return errs
