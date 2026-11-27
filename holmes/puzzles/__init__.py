"""Final puzzles: what the player does with the evidence to close a case.

Each case's `final` table names a puzzle type. New types (seating chart, Morse tape,
record tables, telegram queue, cylinder) are added here as classes with the same
interface: Puzzle(game, spec).run().
"""

from __future__ import annotations

from holmes.puzzles.accuse import AccusePuzzle
from holmes.puzzles.cylinder import CylinderPuzzle
from holmes.puzzles.morse import MorsePuzzle
from holmes.puzzles.seating import SeatingPuzzle
from holmes.puzzles.timeline import TimelinePuzzle

PUZZLES = {
    "accuse": AccusePuzzle,
    "timeline": TimelinePuzzle,
    "seating": SeatingPuzzle,
    "morse": MorsePuzzle,
    "cylinder": CylinderPuzzle,
}


def run_final(game) -> None:
    spec = game.story.final
    PUZZLES[spec.get("type", "accuse")](game, spec).run()
