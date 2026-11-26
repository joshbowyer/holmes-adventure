"""Final puzzles: what the player does with the evidence to close a case.

Each case's `final` table names a puzzle type. New types (timeline, seating chart,
Morse tape, record tables, telegram queue, cylinder) are added here as classes with
the same interface: Puzzle(game, spec).run().
"""

from __future__ import annotations

from holmes.puzzles.accuse import AccusePuzzle

PUZZLES = {
    "accuse": AccusePuzzle,
}


def run_final(game) -> None:
    spec = game.story.final
    PUZZLES[spec.get("type", "accuse")](game, spec).run()
