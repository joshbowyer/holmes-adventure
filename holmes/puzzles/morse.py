"""Morse tapes: read inked telegraph tape, decode it, and say who sent each passage.

spec: everything an `accuse` spec has, plus
  morse = {
    intro            shown before the board, when the player accuses
    note             optional reminder shown under the board
    codebook_when    condition under which CODEBOOK shows the alphabet (e.g. a clue)
    fists = {key: {dot, dash, gap, letter, word, split?, slip?, wobble?}}
                     how a sender's hand lays marks on the tape, in units: a dot's and
                     a dash's length, the gap inside a letter, between letters and
                     between words. `split` = letters the sender breaks in two (a split
                     C reads as two N's); `slip` = every Nth dash falls one unit short;
                     `wobble` = an unsteady hand (dash and gap lengths vary by one)
    passages = {pid: {deal, label, text, fist, sender?, clue?}}
                     a passage of tape, dealt when the clue `deal` is noted; `text` is
                     what was sent (letters, figures and spaces); `sender` marks a
                     passage whose sender is already known (a sample to compare);
                     `clue` is noted when the player decodes it
    senders = {key: {name, aliases?, when?}}   who might have sent a passage
    answer = {pid: sender key}   who truly sent every passage that has no `sender`
    wrong_ending     ending id when any passage is put to the wrong sender
    incomplete_ending  optional: when everything attributed is right but some
                     passages were never found or attributed (else wrong_ending)
  }

During play, TAPES lists the passages found (lettered in the order found), TAPE <letters>
shows their marks, DECODE <letter> AS <words> checks a reading, ATTRIBUTE <letter> TO
<name> says who sent it, and CODEBOOK shows the alphabet. All of it is kept in the save.
"""

from __future__ import annotations

from holmes.engine.conditions import check
from holmes.puzzles.accuse import AccusePuzzle

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.",
    "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.",
    "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-", "U": "..-",
    "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..",
    "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....",
    "6": "-....", "7": "--...", "8": "---..", "9": "----.", "0": "-----",
}
LETTER_OF = {v: k for k, v in MORSE.items()}
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
MARK = "="
TAPE_WIDTH = 66
NOBODY = {"nobody", "none", "no", "one", "clear", "unknown"}
FILLER = {"to", "as", "is", "by", "was", "sent", "the", "from", "passage", "tape", "mr",
          "mrs", "miss"}


def has_morse(game) -> bool:
    return game.story.final.get("type") == "morse"


def _spec(game) -> dict:
    return game.story.final["morse"]


# --- the tape itself -------------------------------------------------------------------

def symbols(text: str, fist: dict) -> list[list[str]]:
    """The passage as words of letters of dot/dash codes, with split letters broken."""
    split = {s.upper() for s in fist.get("split", [])}
    words = []
    for w in text.upper().split():
        letters = []
        for ch in w:
            code = MORSE[ch]
            if ch in split and len(code) > 1:
                half = len(code) // 2
                letters += [code[:half], code[half:]]
            else:
                letters.append(code)
        words.append(letters)
    return words


def literal(text: str, fist: dict) -> str:
    """What the tape reads as, letter by letter (a split C reads NN)."""
    return " ".join("".join(LETTER_OF.get(c, "?") for c in w) for w in symbols(text, fist))


def render(text: str, fist: dict) -> list[str]:
    """The tape as marks ('=') and gaps (' '), one string per mark-and-gap token."""
    dot, dash = int(fist.get("dot", 1)), int(fist.get("dash", 3))
    gap, lgap, wgap = int(fist.get("gap", 1)), int(fist.get("letter", 3)), int(fist.get("word", 7))
    slip, wobble = int(fist.get("slip", 0)), int(fist.get("wobble", 0))
    n = 0                                  # dashes and gaps so far, for slips and wobbles
    tokens: list[str] = []

    def vary(x: int) -> int:
        nonlocal n
        n += 1
        if wobble and n % 3 == 0:
            return max(1, x + (1 if n % 2 else -1) * wobble)
        return x

    dashes = 0
    words = symbols(text, fist)
    for wi, letters in enumerate(words):
        for li, code in enumerate(letters):
            for ei, el in enumerate(code):
                if el == "-":
                    dashes += 1
                    length = dash - 1 if slip and dashes % slip == 0 else dash
                    mark = MARK * vary(length)
                else:
                    mark = MARK * dot
                last = ei == len(code) - 1
                if not last:
                    space = gap
                elif li < len(letters) - 1:
                    space = vary(lgap)
                elif wi < len(words) - 1:
                    space = vary(wgap)
                else:
                    space = 0
                tokens.append(mark + " " * space)
    return tokens


def tape_lines(text: str, fist: dict, width: int = TAPE_WIDTH) -> list[str]:
    lines, cur = [], ""
    for tok in render(text, fist):
        if cur and len(cur) + len(tok.rstrip()) > width:
            lines.append(cur.rstrip())
            cur = ""
        cur += tok
    if cur.strip():
        lines.append(cur.rstrip())
    return lines


def _letters_only(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalnum())


# --- what the player has found ---------------------------------------------------------

def dealt(game) -> list[str]:
    """Passage ids found so far, in the order found."""
    by_clue: dict[str, list[str]] = {}
    for pid, p in _spec(game)["passages"].items():
        by_clue.setdefault(p["deal"], []).append(pid)
    out: list[str] = []
    for clue in game.state.clues:
        out += [p for p in by_clue.get(clue, []) if p not in out]
    return out


def letter_of(game) -> dict[str, str]:
    return {pid: LETTERS[i] for i, pid in enumerate(dealt(game))}


def known_senders(game) -> list[str]:
    return [k for k, s in _spec(game)["senders"].items() if check(game.state, s.get("when"))]


def sender_of(game, pid: str) -> str | None:
    p = _spec(game)["passages"][pid]
    if p.get("sender"):
        return p["sender"]
    k = game.state.attribution.get(pid)
    return k if k in known_senders(game) else None


def _name(game, key: str) -> str:
    return _spec(game)["senders"][key]["name"]


def unattributed(game) -> list[str]:
    return [p for p in dealt(game) if sender_of(game, p) is None]


def _passages_from(game, text: str) -> list[str] | str:
    by_letter = {v: k for k, v in letter_of(game).items()}
    picked = [ch for ch in text.upper() if ch.isalpha()]
    if not picked:
        return "Which passage? Give its letter."
    bad = [ch for ch in picked if ch not in by_letter]
    if bad:
        return f"There is no passage {bad[0]} among your tapes."
    return [by_letter[ch] for ch in dict.fromkeys(picked)]


# --- commands ---------------------------------------------------------------------------

def show_board(game) -> None:
    spec, letters = _spec(game), letter_of(game)
    game.say("TAPES", "heading")
    if not letters:
        game.say("I have not yet a single inch of tape to my name.")
        return
    lines = []
    for pid, ch in letters.items():
        p = spec["passages"][pid]
        who = sender_of(game, pid)
        if p.get("sender"):
            sent = f"sent by {_name(game, who)} (known)"
        else:
            sent = f"sent by {_name(game, who)}?" if who else "sender not yet settled"
        read = (f'reads: "{p["text"].upper()}"' if pid in game.state.decoded
                else "not yet read")
        lines += [f"| {ch}  {p['label']}", f"|      {read}; {sent}."]
    game.say("\n".join(lines))
    game.say("(TAPE <letters> shows the marks: e.g. TAPE A, or TAPE alone for all. "
             "DECODE <letter> AS <words> tries a reading; ATTRIBUTE <letter> TO <name> "
             "says who sent it; CODEBOOK shows the alphabet.)", "system")


def show_tapes(game, text: str) -> bool:
    spec = _spec(game)
    if not dealt(game):
        game.fail("I have not yet a single inch of tape to my name.")
        return False
    if text.strip().lower() in ("", "all", "s", "es"):
        pids = dealt(game)
    else:
        got = _passages_from(game, text)
        if isinstance(got, str):
            game.fail(got, "system")
            return False
        pids = got
    letters = letter_of(game)
    for pid in pids:
        p = spec["passages"][pid]
        fist = spec["fists"][p["fist"]]
        body = [f"| {letters[pid]}  {p['label']}", "|"]
        body += [f"|    {line}" for line in tape_lines(p["text"], fist)]
        game.say("\n".join(body))
    game.say("(A short mark is a dot, a long one a dash. Gaps part the letters, and "
             "longer gaps the words.)", "system")
    return True


def passages_dealt_by(game, clue: str | None) -> list[str]:
    if not clue or not has_morse(game):
        return []
    return [pid for pid, p in _spec(game)["passages"].items() if p["deal"] == clue]


def show_item_tape(game, clue: str | None) -> None:
    """Examining a piece of tape shows its marks, with the letters TAPES uses."""
    pids = [p for p in passages_dealt_by(game, clue) if p in dealt(game)]
    if not pids:
        return
    letters = letter_of(game)
    show_tapes(game, "".join(letters[p] for p in pids))
    game.say("(Each passage keeps its letter. TAPES lists every passage you hold; DECODE "
             "<letter> AS <words> tries a reading, ATTRIBUTE <letter> TO <name> says who "
             "sent it, and CODEBOOK shows the alphabet once you have it.)", "system")


def show_codebook(game) -> bool:
    spec = _spec(game)
    if not check(game.state, spec.get("codebook_when")):
        game.fail("I have no Morse alphabet to hand, and I do not know it by heart.")
        return False
    keys = list(MORSE)
    cols, rows = 4, -(-len(keys) // 4)
    lines = []
    for r in range(rows):
        cells = []
        for c in range(cols):
            i = c * rows + r
            if i < len(keys):
                k = keys[i]
                cells.append(f"{k}  {MORSE[k].ljust(6)}")
        lines.append("|  " + "    ".join(cells))
    game.say("THE MORSE ALPHABET", "heading")
    game.say("\n".join(lines))
    game.say("(A dot is a short mark on the tape, a dash a long one. Figures are written "
             "out in full, five marks apiece.)", "system")
    return True


def decode(game, text: str) -> bool:
    spec = _spec(game)
    words = text.split()
    if not words:
        game.fail("Decode which passage, and how? (For example: DECODE A AS THE WORDS "
                  "YOU READ.)", "system")
        return False
    got = _passages_from(game, words[0])
    if isinstance(got, str) or len(got) != 1 or len(words[0]) != 1:
        game.fail(got if isinstance(got, str) else "Decode one passage at a time.", "system")
        return False
    pid = got[0]
    rest = words[1:]
    if rest and rest[0].lower() in ("as", "to", "reads", "is"):
        rest = rest[1:]
    if not rest:
        game.fail("Give the words you read, after the letter.", "system")
        return False
    p = spec["passages"][pid]
    mine = _letters_only(" ".join(rest))
    right = {_letters_only(p["text"]), _letters_only(literal(p["text"], spec["fists"][p["fist"]]))}
    if mine in right:
        first = pid not in game.state.decoded
        if first:
            game.state.decoded.append(pid)
        game.say(f'I wrote it out fair beneath the tape: "{p["text"].upper()}"')
        if _letters_only(literal(p["text"], spec["fists"][p["fist"]])) != _letters_only(p["text"]) \
                and mine != _letters_only(p["text"]):
            game.say("(Read mark by mark it gives a word that is no word; I set down what "
                     "was plainly meant.)", "system")
        if first and p.get("clue"):
            game.add_clue(p["clue"])
        return True
    target = _letters_only(p["text"])
    good = 0
    for a, b in zip(mine, target):
        if a != b:
            break
        good += 1
    if good == 0:
        game.fail("That does not fit the tape from the very first letter.", "system")
    elif good >= len(target):
        game.fail(f"The first {len(target)} letters fit, but you have read more than "
                  "the tape holds.", "system")
    else:
        game.fail(f"The first {good} letter{'s' if good != 1 else ''} fit the tape; "
                  "after that, your reading goes astray.", "system")
    return False


def _sender_from(game, words: list[str]) -> str | None | bool:
    """A sender key, None for 'nobody', or False after saying why not."""
    words = [w for w in words if w not in FILLER]
    if not words:
        game.fail("Attribute it to whom?", "system")
        return False
    if all(w in NOBODY for w in words):
        return None
    spec, hits = _spec(game), []
    phrase = " ".join(words)
    for k in known_senders(game):
        s = spec["senders"][k]
        names = [s["name"].lower()] + [a.lower() for a in s.get("aliases", [])] + [k]
        vocab = {w for n in names for w in n.replace("-", " ").split()}
        if phrase in names or all(w in vocab for w in words):
            hits.append(k)
    if len(hits) != 1:
        game.fail("I know of no such sender." if not hits else
                  "Which do you mean: " + ", ".join(_name(game, k) for k in hits) + "?",
                  "system")
        return False
    return hits[0]


def attribute(game, text: str) -> bool:
    spec = _spec(game)
    words = text.lower().replace(".", " ").split()
    if not words:
        game.fail("Attribute which passage, to whom? (For example: ATTRIBUTE A TO "
                  "SMITH.)", "system")
        return False
    words = [w for w in words if w not in ("passage", "passages", "tape", "tapes")]
    if not words or not words[0].isalpha() or len(words[0]) > 26:
        game.fail("Which passage? Give its letter first.", "system")
        return False
    got = _passages_from(game, words[0])
    if isinstance(got, str):
        game.fail(got, "system")
        return False
    who = _sender_from(game, words[1:])
    if who is False:
        return False
    for pid in got:
        if spec["passages"][pid].get("sender"):
            game.fail("Who sent that passage is not in doubt.", "system")
            return False
    for pid in got:
        if who is None:
            game.state.attribution.pop(pid, None)
        else:
            game.state.attribution[pid] = who
    show_board(game)
    return True


class MorsePuzzle(AccusePuzzle):
    def run(self) -> None:
        if not self.gate():
            return
        sp = self.spec["morse"]
        if sp.get("intro"):
            self.game.say(sp["intro"])
        if not self.settle():
            return self.stop()
        answers = self.ask()
        if answers is None or not self.confirm():
            return self.stop()
        verdict = self.verdict()
        if verdict != "right":
            return self.judge(sp.get("incomplete_ending", sp["wrong_ending"])
                              if verdict == "incomplete" else sp["wrong_ending"], False)
        self.judge(*self.ending_for(answers))

    def settle(self) -> bool:
        g = self.game
        while True:
            show_board(g)
            loose = unattributed(g)
            prompt = ("Say who sent each passage (ATTRIBUTE letter TO name), or Enter to "
                      "stop: " if loose else
                      "Enter to stand by these, or ATTRIBUTE letter TO name to change one: ")
            line = g.io.read(prompt)
            if line is None:
                return False
            line = line.strip()
            if not line:
                return not loose
            verb, _, rest = line.partition(" ")
            if verb.lower() in ("attribute", "ascribe", "assign", "credit"):
                attribute(g, rest)
            elif verb.lower() in ("tape", "tapes"):
                show_tapes(g, rest)
            else:
                g.say("Use ATTRIBUTE letter TO name, or TAPE letter to look again.", "system")

    def verdict(self) -> str:
        answer = self.spec["morse"]["answer"]
        mine = {pid: sender_of(self.game, pid) for pid in dealt(self.game) if pid in answer}
        if any(k is not None and answer[pid] != k for pid, k in mine.items()):
            return "wrong"
        if len(mine) == len(answer) and all(mine.values()):
            return "right"
        return "incomplete"
