"""The plainest final puzzle: answer a series of multiple-choice questions.

spec:
  type = "accuse"
  when           condition before an accusation is allowed
  locked_text    shown when `when` does not hold
  intro          shown before the questions
  questions = [{id, prompt, options = [{id, label, when?}]}]
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
        g, spec, st = self.game, self.spec, self.game.state
        if st.solved:
            g.say("The case is closed.")
            return
        if not check(st, spec.get("when")):
            g.say(spec.get("locked_text",
                           "You turn the matter over, but you have not yet facts enough to "
                           "build upon. Better to look further."))
            return
        if spec.get("intro"):
            g.say(spec["intro"])
        answers = {}
        for q in spec["questions"]:
            opts = [o for o in q["options"] if check(st, o.get("when"))]
            choice = self.choose(q["prompt"], opts)
            if choice is None:
                g.say("You decide to gather more facts before committing yourself.")
                return
            answers[q["id"]] = choice
        confirm = g.io.read("Is that your final word? (y/n) ")
        if (confirm or "").strip().lower() not in YES:
            g.say("You decide to gather more facts before committing yourself.")
            return
        if all(answers.get(k) == v for k, v in spec["solution"].items()):
            g.show_ending(spec["good"])
            g.case_closed()
            return
        ending = spec["default_wrong"]
        for w in spec.get("wrong", []):
            if all(answers.get(k) == v for k, v in w["answers"].items()):
                ending = w["ending"]
                break
        g.show_ending(ending)
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
