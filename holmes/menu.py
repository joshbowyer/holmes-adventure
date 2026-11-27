"""Entry point: the story-select menu.

  python -m holmes             menu
  python -m holmes --plain     no colour
  python -m holmes --case ID   jump straight into a case
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from holmes.engine import codec, saves
from holmes.engine.game import Game
from holmes.engine.state import GameState
from holmes.engine.story import Story
from holmes.engine.text import Console

DATA_DIR = Path(__file__).parent / "data"

BANNER = """\
|   ____________________________________________________
|
|        FROM THE NOTEBOOKS OF JOHN H. WATSON, M.D.
|           Being Certain Cases of Mr Sherlock Holmes
|   ____________________________________________________"""


def load_stories(data_dir: Path = DATA_DIR) -> list[Story]:
    stories = []
    for p in sorted(data_dir.glob("*.case")):
        stories.append(Story(codec.decode(p.read_text(encoding="utf-8"))))
    stories.sort(key=lambda s: (s.case.get("order", 99), s.case.get("year", 0)))
    return stories


def _yes(answer: str | None) -> bool:
    return (answer or "").strip().lower() in {"y", "yes"}


def play_case(story: Story, console: Console, profile: dict) -> None:
    saved = saves.load_game(story.id)
    solved = profile["cases"].get(story.id, {}).get("solved")
    state = None
    if saved:
        what = "a replay of this case" if solved else "this case"
        console.say(f"You have {what} in progress.")
        console.raw("  1. Continue where you left off")
        console.raw("  2. Start afresh")
        console.raw("  3. Put it away (your progress is thrown away)")
        console.raw("  Enter: back to the casebook")
        choice = (console.read("Your choice: ") or "").strip().lower()
        if choice == "1":
            state = GameState.from_dict(saved)
        elif choice == "2":
            if not _yes(console.read("Your progress in this case will be lost. Are you sure? (y/n) ")):
                return
            saves.delete_game(story.id)
        elif choice == "3":
            if _yes(console.read("Throw away your progress in this case? (y/n) ")):
                saves.delete_game(story.id)
                console.say("Put away." + (" The case stays solved in your casebook." if solved else ""))
            return
        else:
            return
    elif solved:
        if not _yes(console.read("You have solved this case already. Play it again from the "
                                 "start? (y/n) ")):
            return
    console.write("\n")
    st = Game(story, console, state).run()
    if st.solved:
        rec = profile["cases"].setdefault(story.id, {})
        rec["solved"] = True
        rec["best_wrong"] = min(rec.get("best_wrong", st.wrong), st.wrong)
        rec["best_hints"] = min(rec.get("best_hints", st.hints_bought), st.hints_bought)
        saves.save_profile(profile)
        console.read("Press Enter to return to the casebook. ")


def menu(stories: list[Story], console: Console, profile: dict) -> None:
    while True:
        console.write("\n")
        console.say(BANNER, "heading")
        for i, s in enumerate(stories, 1):
            line = f"  {i}. {s.title} ({s.case.get('year', '?')})"
            if s.case.get("subtitle"):
                line += f": {s.case['subtitle']}"
            solved = profile["cases"].get(s.id, {}).get("solved")
            playing = saves.save_path(s.id).exists()
            if solved and playing:
                status = "  [solved; replay in progress]"
            elif solved:
                status = "  [solved]"
            elif playing:
                status = "  [in progress]"
            else:
                status = ""
            console.raw(line + console.style(status, "note"))
        console.raw("")
        console.raw(f"  c. Colour: {'on' if console.color else 'off'}")
        console.raw("  q. Quit")
        console.raw("")
        choice = console.read("Choose a case: ")
        if choice is None:
            return
        choice = choice.strip().lower()
        if choice in ("q", "quit", "exit"):
            console.say("Good day to you.")
            return
        if choice == "c":
            console.color = not console.color
            profile["color"] = console.color
            saves.save_profile(profile)
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(stories):
            play_case(stories[int(choice) - 1], console, profile)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="holmes")
    ap.add_argument("--plain", action="store_true", help="no colour")
    ap.add_argument("--case", help="start this case directly (by id)")
    args = ap.parse_args(argv)

    if os.name == "nt":
        os.system("")  # enables ANSI escape handling in the Windows console
    for stream in (sys.stdout, sys.stdin):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    profile = saves.load_profile()
    color = False if args.plain else profile.get("color")
    console = Console(color=color)
    stories = load_stories()
    if not stories:
        console.say("No cases found. Run `python -m holmes.build` first.")
        return 1
    try:
        if args.case:
            match = [s for s in stories if s.id == args.case]
            if not match:
                console.say(f"No case called {args.case!r}.")
                return 1
            play_case(match[0], console, profile)
        else:
            menu(stories, console, profile)
    except KeyboardInterrupt:
        console.write("\n")
    return 0
