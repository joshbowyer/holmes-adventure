"""Terminal output: word-wrapping, sparing ANSI colour, and line input.

All game I/O goes through a Console so the game can be driven by stdin/stdout
(and later an ssh/telnet wrapper) or by a scripted console in tests.
"""

from __future__ import annotations

import os
import re
import shutil
import sys

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

STYLES = {
    "title": "1;33",    # room names
    "item": "36",       # things you can see
    "person": "32",     # characters
    "exit": "2",        # ways out
    "note": "35",       # notebook / pennies
    "system": "2",      # engine chrome
    "heading": "1",
    "warn": "31",
}


def visible_len(s: str) -> int:
    return len(ANSI_RE.sub("", s))


def wrap(text: str, width: int) -> str:
    """Wrap prose to width, keeping blank-line paragraph breaks.

    A paragraph whose lines all start with '|' is kept verbatim (minus the '| '),
    for letters, notices and tables.
    """
    out = []
    for para in re.split(r"\n[ \t]*\n", text.strip("\n")):
        lines = para.split("\n")
        if all(l.lstrip().startswith("|") for l in lines if l.strip()):
            out.append("\n".join(re.sub(r"^\s*\| ?", "", l) for l in lines))
            continue
        words = para.split()
        result, cur, cur_len = [], [], 0
        for w in words:
            wl = visible_len(w)
            if cur and cur_len + 1 + wl > width:
                result.append(" ".join(cur))
                cur, cur_len = [w], wl
            else:
                cur_len = wl if not cur else cur_len + 1 + wl
                cur.append(w)
        if cur:
            result.append(" ".join(cur))
        out.append("\n".join(result))
    return "\n\n".join(out)


class Console:
    def __init__(self, color: bool | None = None, stdin=None, stdout=None):
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        if color is None:
            color = self._default_color()
        self.color = color

    def _default_color(self) -> bool:
        if os.environ.get("NO_COLOR"):
            return False
        try:
            return self.stdout.isatty()
        except Exception:
            return False

    def width(self) -> int:
        cols = shutil.get_terminal_size((80, 24)).columns
        return max(40, min(cols, 80) - 1)

    def style(self, text: str, kind: str | None) -> str:
        if not kind or not self.color or kind not in STYLES:
            return text
        return f"\x1b[{STYLES[kind]}m{text}\x1b[0m"

    def write(self, text: str) -> None:
        self.stdout.write(text)
        self.stdout.flush()

    def say(self, text: str = "", kind: str | None = None) -> None:
        """Print wrapped prose, followed by a blank line."""
        if not text:
            self.write("\n")
            return
        wrapped = wrap(text, self.width())
        if kind:
            wrapped = "\n".join(self.style(l, kind) if l else l for l in wrapped.split("\n"))
        self.write(wrapped + "\n\n")

    def raw(self, text: str) -> None:
        self.write(text + "\n")

    def read(self, prompt: str = "> ") -> str | None:
        self.write(self.style(prompt, "heading"))
        line = self.stdin.readline()
        if line == "":
            return None
        return line.rstrip("\r\n")


class ScriptedConsole(Console):
    """Feeds canned input and captures output, for tests. Never prints."""

    def __init__(self, inputs):
        self.inputs = list(inputs)
        self.output: list[str] = []
        self.color = False
        self.stdin = self.stdout = None

    def width(self) -> int:
        return 79

    def write(self, text: str) -> None:
        self.output.append(text)

    def read(self, prompt: str = "> ") -> str | None:
        if not self.inputs:
            return None
        return self.inputs.pop(0)

    def text(self) -> str:
        return "".join(self.output)
