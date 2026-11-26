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

    conds: list[tuple[str, object]] = []
    effects: list[tuple[str, object]] = []

    def events(where: str, evs) -> None:
        for i, e in enumerate(_events(evs)):
            conds.append((f"{where}[{i}].when", e.get("when")))
            effects.append((f"{where}[{i}].effects", e.get("effects")))

    # rooms
    for rid, r in rooms.items():
        for k in ("name", "description"):
            if k not in r:
                errs.append(f"room {rid}: missing {k}")
        for d, ex in r.get("exits", {}).items():
            ex = {"to": ex} if isinstance(ex, str) else ex
            if d not in DIRECTIONS.values():
                errs.append(f"room {rid}: exit {d!r} is not a direction")
            if ex.get("to") not in rooms:
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
    elif final.get("type", "accuse") == "accuse":
        conds.append(("final.when", final.get("when")))
        qopts = {}
        for q in final.get("questions", []):
            ids = [o.get("id") for o in q.get("options", [])]
            if len(set(ids)) != len(ids):
                errs.append(f"final question {q.get('id')}: duplicate option ids")
            qopts[q.get("id")] = set(ids)
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
                elif kind == "clue" and a not in clues:
                    errs.append(f"{where}: unknown clue {a!r}")
                elif kind == "loc" and (a not in things or args[1] not in places):
                    errs.append(f"{where}: bad loc reference {term!r}")

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
