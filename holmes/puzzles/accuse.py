"""The plainest final puzzle: answer a series of multiple-choice questions.

spec:
  type = "accuse"
  when           optional condition before an accusation is allowed (user, 2026-11-27:
                 don't use it; let the player rush to a wrong answer instead)
  locked_text    shown when `when` does not hold
  intro          shown before the questions
  questions = [{id, prompt, options = [{id, label, when?}]}]
                 an option with `when` is offered only once the player has found
                 what it names, so an unexplored case cannot be answered rightly
  solution = {question id: option id}
  good           ending id for the right answer
  wrong = [{answers = {question id: option id}, ending}]   first match wins
  default_wrong  ending id when no `wrong` entry matches

A wrong answer plays its bad ending in full, is counted, and returns the player to
the investigation.
"""

from __future__ import annotations

from holmes.engine.conditions import check
from holmes.engine.hints import YES


class AccusePuzzle:
    def __init__(self, game, spec: dict):
        self.game = game
        self.spec = spec

    def run(self) -> None:
        if not self.gate():
            return
        answers = self.ask()
        if answers is None or not self.confirm():
            return self.stop()
        self.judge(*self.ending_for(answers))

    # --- the steps, shared with puzzles built on this one ------------------------------

    def gate(self) -> bool:
        g, spec, st = self.game, self.spec, self.game.state
        if st.solved:
            g.say("The case is closed.")
            return False
        if not check(st, spec.get("when")):
            g.say(spec.get("locked_text",
                           "You turn the matter over, but you have not yet facts enough to "
                           "build upon. Better to look further."))
            return False
        if spec.get("intro"):
            g.say(spec["intro"])
        return True

    def stop(self) -> None:
        self.game.say("You decide to gather more facts before committing yourself.")

    def ask(self) -> dict | None:
        st, answers = self.game.state, {}
        for q in self.spec["questions"]:
            opts = [o for o in q["options"] if check(st, o.get("when"))]
            choice = self.choose(q["prompt"], opts)
            if choice is None:
                return None
            answers[q["id"]] = choice
        return answers

    def confirm(self) -> bool:
        confirm = self.game.io.read("Is that your final word? (y/n) ")
        return (confirm or "").strip().lower() in YES

    def ending_for(self, answers: dict) -> tuple[str, bool]:
        spec = self.spec
        if all(answers.get(k) == v for k, v in spec["solution"].items()):
            return spec["good"], True
        for w in spec.get("wrong", []):
            if all(answers.get(k) == v for k, v in w["answers"].items()):
                return w["ending"], False
        return spec["default_wrong"], False

    def judge(self, ending: str, good: bool) -> None:
        g, st = self.game, self.game.state
        g.show_ending(ending)
        if good:
            g.case_closed()
            return
        st.wrong += 1
        g.note(f"[That was not the truth of the matter. Wrong conclusions so far: {st.wrong}. "
               "The case is still open.]")
        g.io.read("Press Enter to return to the investigation. ")
        g.describe_room()

    def choose(self, prompt: str, opts: list[dict]) -> str | None:
        g = self.game
        g.say(prompt, "heading")
        g.io.raw("\n".join(f"  {i}. {o['label']}" for i, o in enumerate(opts, 1)) + "\n")
        while True:
            line = g.io.read("Your answer (a number, or Enter to stop): ")
            if line is None or not line.strip():
                return None
            line = line.strip().lower()
            if line.isdigit() and 1 <= int(line) <= len(opts):
                return opts[int(line) - 1]["id"]
            words = line.split()
            hits = [o for o in opts if all(w in o["label"].lower() for w in words)]
            if len(hits) == 1:
                return hits[0]["id"]
            g.say("Choose one of the numbers above.", "system")
