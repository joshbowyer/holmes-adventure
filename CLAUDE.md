# Holmes Adventure — project brief

A personal hobby project: a single-player Sherlock Holmes text adventure / puzzle game,
played entirely in a terminal on Linux (and later over telnet/ssh).

This has nothing to do with the user's day job. Never reference their employer, work repos,
work GitHub org, or work tooling. This repo has no remote; if one is ever added it will be a
personal account the user names.

## The player is also the audience — spoiler rules

The user wants to *play* these mysteries, so Claude designs every solution and the user
must never learn it outside the game.

- Never state culprits, twists, solutions, or the meaning of clues in chat. Talk about
  stories in terms of structure ("case 3's third clue chain is done"), not content.
- Keep the private story bible (culprit, motive, true timeline, clue graph) in `spoilers/`.
  The user agrees not to open that folder or the story data files.
- Story data that ships with the game should be lightly obfuscated on disk (e.g. a simple
  encoding decoded at load time) so a stray `cat` or `grep` can't spoil anything.
- When asking the user design questions, ask about tone, difficulty, mechanics and UX —
  never "should the butler have done it?"
- Ask before any step that would show the user story text they haven't reached in play
  (e.g. test output). Prefer tests that assert structure, not printed prose.

## Writing style

- Imitate Arthur Conan Doyle's prose: Watson's first-person narration, period vocabulary,
  Holmes's dry deductive dialogue, Victorian London texture. No modern idiom.
- Mysteries must be clever but realistic: fair-play (every clue needed is findable),
  period-accurate technology and procedure, no supernatural solutions, no deus ex machina.
- Entirely original stories. The user has read all the canon and played the Frogwares
  games, so avoid retreading them. Known near-misses already rejected:
  - a fake arrangement hiding a crime (too close to *The Red-Headed League*)
  - a Kew Gardens botanical case (Frogwares, *Crimes & Punishments* — "The Kew Gardens Drama")
  - church change-ringing alibis (Dorothy Sayers, *The Nine Tailors*)
  - typewriter identification (canon, *A Case of Identity*); the Underground (*Bruce-Partington*)
- Canon characters (Holmes, Watson, Mrs Hudson, Lestrade, Mycroft, Wiggins…) are fine to use.

## Game structure

- Main menu with **story select**. Each story is self-contained.
- Five main cases plus one unlockable, each built around a *different* puzzle style:

| # | Story | Year | Puzzle style |
|---|---|---|---|
| 1 | The Wax Cylinder Will | 1894 | Sound deduction |
| 2 | The Two Clocks of Hatherleigh | 1881 | Timeline building |
| 3 | The Medium's Last Sitting | 1892 | Seating / hand-chain logic |
| 4 | The Operator's Fist | 1887 | Morse decoding & timing |
| 5 | Census Night | 1891 | Record cross-checking; collection finale |
| Unlock | Letters from Sussex | 1905 | Delayed-telegram strategy |

The unlock condition is undecided (probably: solve all five).

### Premises (agreed hooks only — solutions are Claude's to invent)

1. **The Wax Cylinder Will.** An inventor records his will on a phonograph cylinder and dies
   within the week; the family calls the recording a forgery. The player "listens" through
   text: play at different speeds, isolate background sounds (bells, train whistle, rain, a
   cough) to work out where and when it was really recorded.
2. **The Two Clocks of Hatherleigh.** A stubborn West Country village whose church clock keeps
   local solar time while the railway station keeps London time (~16 minutes apart). Every
   suspect has an airtight alibi by one clock or the other. The player assembles statements
   into a timeline that the game validates. (A rejected idea — rival editions of Bradshaw's
   railway timetable — could be folded in here as a sub-clue if it fits.)
3. **The Medium's Last Sitting.** A fashionable medium dies mid-séance in a pitch-dark room;
   all sitters swear the hand-held circle never broke. Built on the real *hand substitution*
   trick. The player deduces from testimony whose hand was actually free. (Nice irony: Doyle
   himself became a committed spiritualist.)
4. **The Operator's Fist.** A telegraph operator at a remote relay station is found dead; his
   station sent its last message two hours after his death. Every operator's sending rhythm
   ("fist") is distinctive. The player decodes real Morse with an in-game codebook and
   compares timing to prove who sent it.
5. **Census Night.** On census night, 5 April 1891, a household schedule lists a visitor who
   could not have been there; next morning the visitor is found dead forty miles away. Census
   schedules render as terminal tables to cross-check (names, ages, birthplaces,
   occupations). This is Holmes's last case before Reichenbach (May 1891) — a bittersweet
   finale for the collection.
6. **Letters from Sussex (unlockable).** Holmes has retired to keep bees. The player is
   **Wiggins**, the grown-up former Baker Street Irregular, doing London legwork; Holmes
   helps only by telegram, and replies arrive turns later, so what to ask becomes strategy.

## Technical direction (not yet decided — confirm with the user)

- Must run in a plain Linux terminal; later servable over telnet/ssh. Keep I/O to stdin/stdout
  so a wrapper can serve it.
- Language candidates: Python (fast to write) or Go (single static binary, easy to host).
  Recommend one, but let the user choose.
- Data-driven: engine code separate from story content so new cases are data, not code.
- Puzzle mechanics needed by the lineup: room/inventory/examine parser, notebook of clues,
  "listen at speed" for cylinders, timeline builder, logic-grid/seating input, Morse
  input/codebook, tabular record viewer, delayed-message queue, save/load per story.

## Working with the user

- They pay per token on other plans; this plan has no usage cost, so thoroughness is fine.
- Next step from here: pick the language/engine shape with the user, then build the engine
  and one story end to end (suggest starting with whichever case best exercises the engine)
  before writing the rest.
