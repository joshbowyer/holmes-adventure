# From the Notebooks of John H. Watson, M.D.

Sherlock Holmes mysteries to play in a terminal. Explore with typed commands
(`go north`, `examine the window`, `ask mrs hudson about the cake`), collect clues in
your notebook, and name the truth when you are ready.

## Playing

Needs Python 3.10 or newer and nothing else.

```bash
python3 -m holmes
```

`--plain` turns colour off, and `--case tutorial` skips the menu. Type `HELP` in a case
for the commands. Progress saves itself after every command.

Saves are kept in `~/.local/share/holmes-adventure/` (on Windows, `%APPDATA%\holmes-adventure`),
or in `$HOLMES_SAVE_DIR` if you set it.

## No peeking

`spoilers/` holds the story sources and solutions, and `holmes/data/*.case` is the same
content scrambled. Don't open either if you want to play the cases.

## Development

```bash
python -m holmes.build      # compile spoilers/stories/* into holmes/data/*.case (Python 3.11+)
python -m unittest -v       # engine tests + a scripted play-through of every case
```

Engine code is in `holmes/engine/`, final-puzzle types in `holmes/puzzles/`. Cases are
data only; the data format is documented at the top of `holmes/engine/story.py` and
`holmes/engine/conditions.py`.
