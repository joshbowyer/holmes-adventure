# Holmes Adventure — project brief

A personal hobby project: a single-player Sherlock Holmes text adventure / puzzle game,
played entirely in a terminal on Linux (and later over telnet/ssh).

This has nothing to do with the user's day job. Never reference their employer, work repos,
work GitHub org, or work tooling.

**Remote (added 2026-11-26):** `origin` = `git@github-holmes:joshbowyer/holmes-adventure.git`
(private, the user's personal account). Pushes go over SSH with a repo-only deploy key
(`~/.ssh/holmes_deploy`, host alias `github-holmes` in `~/.ssh/config`). Never use `gh` or
HTTPS for this repo: on this machine `gh` and the credential manager are signed in to the
user's work account (via `GH_TOKEN`). Commits use the repo-local personal email; keep it.

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
- **Obvious culprit, hard proof** is the house style so far, and the user likes it
  ("these are absolutely perfect", 2026-11-27; they expect dozens of cases).
- **Misdirection cases, interspersed** (user, 2026-11-27): some cases should let the
  clues, narrative and descriptions point at someone innocent, with the real culprit
  someone "obviously innocent" in context and circumstance, turned by one lynchpin clue
  that comes later or is harder to find than the rest. Still fair-play. Rules:
  - **Not the case after Two Clocks** (the next one built).
  - **Never tell the user which cases have the twist**, not even that a given case
    doesn't. Not in chat, commits, CLAUDE.md, case titles, menu blurbs or the lineup
    tables. Decide privately when writing each bible and record it only in `spoilers/`
    (the bible and `spoilers/twists.md`). Mix them in irregularly so there's no pattern.
- Entirely original stories. The user has read all the canon and played the Frogwares
  games, so avoid retreading them. Known near-misses already rejected:
  - a fake arrangement hiding a crime (too close to *The Red-Headed League*)
  - a Kew Gardens botanical case (Frogwares, *Crimes & Punishments* — "The Kew Gardens Drama")
  - church change-ringing alibis (Dorothy Sayers, *The Nine Tailors*)
  - typewriter identification (canon, *A Case of Identity*); the Underground (*Bruce-Partington*)
- Canon characters (Holmes, Watson, Mrs Hudson, Lestrade, Mycroft, Wiggins…) are fine to use.
- **Never reuse a name across cases** (user, 2026-11-27: the Wax Cylinder Will reused Vane,
  Orme, Clara, Edmund from the Bell-Board and Dunn from Bazalgette; renamed). Check every
  new character's first and last names against all other cases' sources before writing.
- The Irregulars are **street urchins**. Don't call them "street Arabs" (the user's request,
  2026-11-26, even though the canon uses the phrase).
- **Prose must match the game state** (user feedback on the practice case, 2026-11-26):
  - When text reveals things found (in a pocket, under a cushion), name only things the
    player can actually take. No incidental clutter ("a pencil-stub, a cab-ticket") that
    can't be picked up.
  - Nothing can be taken before it is found (user, 2026-11-27: TAKE FARTHING worked
    blind). The engine keeps a container's contents out of reach until the container
    has been examined (`state.searched`) or, if it opens, opened.
  - A description must not keep hinting at something once it has been taken (user,
    2026-11-27: a grate still promised "something that had not burnt so well" after the
    find was taken). Any hint of a takeable thing goes in a `details` entry gated on
    `loc:ITEM:CONTAINER`, never in the base description.
  - **No grasping at straws** (user feedback on Below Bazalgette, 2026-11-26): every word
    the player needs must appear in text they have seen. Scenery is named in its room's
    text (or in something else there); parts worth examining are named in the parent's
    description; every ASK topic is raised in that person's greeting (e.g. "last night"),
    and topics get generous aliases (asking about the lamp should reach the account of the
    night in which the lamp figures). Tests enforce this: `test_scenery_is_named`, and
    `test_walkthrough_words_are_signposted`, which needs walkthroughs to TALK TO before
    ASK and to use the words the screen shows.
  - **Write clock times as 9:05** (user, 2026-11-26), never the period-style "9.5" or
    "9.05", which read as decimals. Words ("five past nine") are fine. A test enforces it.
    Aliases for typed times use spaces ("9 05"), since the parser turns ":" into a space.
  - Never narrate an action the player hasn't performed. If the text says Watson pockets
    something, an effect must really do it; otherwise just describe where it lies and let
    the player TAKE it.

## Game structure

- Main menu with **story select**. Each story is self-contained.
- **Every case is MUD-style exploration first** (`[verb] [object|place]`: go, examine, take,
  open, follow…). The player walks the scenes and gathers evidence, and each case's final
  puzzle is something done *with* what they found (confirmed by the user, 2026-11-26).
- **No real audio** (user, 2026-11-26): the game never plays sound. Sounds described in text
  are fine, so the Wax Cylinder case stays. Visual tables are fine.
- **Morse is read, not heard:** in The Operator's Fist the player decodes dots and dashes from
  a telegraph inker's printed paper tape; an operator's "fist" shows as spacing on the tape.
- **Hints are paid for with coins found by exploring** (user, 2026-11-26). Coins are hidden
  around each case's scenes; spending one buys a hint from Holmes. Hints must be
  state-aware: chosen from the player's current inventory, notebook and progress so a coin
  is never wasted on something already found or solved. Repeated hints on the same step get
  firmer. A step that covers several finds gives its plainest tier as `parts`
  [{done, text}], and only the parts not yet done are told (user, 2026-11-27: hints
  repeated things already done, and a step stuck on one missed piece). Hint commands
  must really work as typed; ASK HIM / ASK HER reach the one person present or the
  last one spoken to. Secret cheat word `persianslipper` (typed alone, spaces/case ignored) grants one
  coin of the current case's coinage, free of time; not listed in HELP (user, 2026-11-26).
- **Wrong final answer:** the player sees that answer's bad ending in full, then may resume
  the case and try again. Wrong attempts are counted and shown on the case-closed screen.
- **Accusing is never blocked** (user, 2026-11-27): ACCUSE works from the first turn, so a
  player who thinks they have it may rush to a wrong answer. Don't set `final.when`.
  Instead, each answer choice that names something found in play (a person, a route, a
  means, a motive) has `when` and is offered only once it is found: `met:PERSON` (spoken
  to) or `clue:` alternatives. Gate wrong choices as well as right ones, so a new choice
  appearing is no tell. Every question keeps at least one choice offered from the start.
  A timeline case accused with cards missing plays `incomplete_ending` if the cards found
  are in the right order. Tests: `test_unexplored_case_cannot_be_solved`; the validator
  needs an ungated choice per question.
- **Colour:** ANSI colour and bold used sparingly (room names, items, exits), with a plain
  mode that turns it off.
- Deduction cases, each built around a *different* final-puzzle style:

| # | Story | Year | Puzzle style |
|---|---|---|---|
| 1 | The Wax Cylinder Will | 1894 | Sound deduction (sounds described in text) |
| 2 | The Two Clocks of Hatherleigh | 1881 | Timeline building |
| 3 | The Medium's Last Sitting | 1890 | Seating / hand-chain logic |
| 4 | The Operator's Fist | 1887 | Morse decoding & timing |
| 5 | Census Night | 1891 | Record cross-checking; collection finale |
| Unlock | Letters from Sussex | 1905 | Delayed-telegram strategy |

- Exploration-heavy cases (added 2026-11-26; all five approved by the user), where walking
  the scene is the main event rather than a lead-in:

| # | Story | Year | Setting to explore |
|---|---|---|---|
| E1 | The Bell-Board at Pelham Square | 1888 | Mayfair townhouse, family rooms + servants' passages |
| E2 | Below Bazalgette | 1886 | London sewers, tides, flood gates, lantern oil |
| E3 | The Crystal Palace by Night | 1895 | Sydenham palace courts after closing, watchman's rounds |
| E4 | The Ice Wells of Battlebridge Basin | 1883 | Ice wells, canal basin, barges, carters' yard |
| E5 | The *Margaret Ainsley* in Dry Dock | 1897 | Merchant ship in a Rotherhithe dry dock, deck by deck |

Numbering and running order are not final. The unlock condition is undecided (was "solve all
five"; needs revisiting now there are more cases).

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
3. **The Medium's Last Sitting** (moved from 1892 to 1890: Holmes is "dead" from May
   1891 to 1894; mind the Great Hiatus when dating cases). A fashionable medium dies mid-séance in a pitch-dark room;
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

Exploration premises:

- **E1 The Bell-Board at Pelham Square.** A guest dies during a Mayfair dinner party. The
  house has two worlds: the family's rooms and the servants' back stairs, dumb-waiter,
  speaking tubes and servants'-hall bell-board. Some rooms are reachable from only one side.
- **E2 Below Bazalgette.** A body is found at a sewer outfall nobody should have been able to
  reach. The player goes down with a tosher and a sewer-company foreman; tides, flood gates
  and lantern oil limit where and how long they can go.
- **E3 The Crystal Palace by Night.** A night-watchman is found dead in the Crystal Palace at
  Sydenham. The themed courts (Egyptian, Alhambra, Pompeian, the dinosaur grounds) must be
  searched by lamplight after closing, timed around a second watchman's rounds.
- **E4 The Ice Wells of Battlebridge Basin.** A man is found dead in an ice merchant's deep
  brick ice wells by the Regent's Canal at King's Cross. Explore wells, warehouses, barges
  and the ice-carters' yard; the setting itself is part of the mystery.
- **E5 The *Margaret Ainsley* in Dry Dock.** A ship's officer dies aboard a merchant ship in a
  Rotherhithe dry dock, crew paid off. A vertical maze: holds, cabins, chain locker, and the
  dock floor beneath the hull.

## Technical direction

- Must run in a plain Linux terminal; later servable over telnet/ssh. Keep I/O to stdin/stdout
  so a wrapper can serve it.
- **Language: Python 3 (decided 2026-11-26), standard library only** — no pip installs, so it
  runs anywhere Python already is. Go was considered (single binary, easy ssh hosting) and
  passed over; ssh serving can be done with `sshd` `ForceCommand` or a small wrapper.
- Data-driven: engine code separate from story content so new cases are data, not code.
- **Engine built (2026-11-26).** Runtime targets Python 3.10+; the build step needs 3.11+
  (tomllib). On this Windows dev machine Python is reached as `py` (3.15).
  - `holmes/engine/`: game loop and verbs (`game.py`), parser, conditions/effects language,
    state, hints (coins), saves, text/colour. `holmes/puzzles/`: final-puzzle types: `accuse`
    (multiple choice) and `timeline` (accuse plus an ordering step: `final.timeline` has
    `cards` {clue id: label giving the time as stated}, `order`, `wrong_ending`; during
    play TIMELINE shows found cards lettered in the order found, ARRANGE <letters> orders
    them, saved in `state.arrangement`; a wrong order plays `wrong_ending`). **Any statement
    that fixes an event to a clock time must deal a card** (user, 2026-11-26: Pook gave
    the shot's time and TIMELINE stayed empty; 2026-11-27: Vodden's own account gave
    times and dealt nothing). A card can be any clue id, so the clue a witness's answer
    gives can itself be the card. When several witnesses time the same event, the card is
    `{event, says = {clue: statement}}`: whichever is heard first deals it, and the label
    lists every statement heard. `test_timed_statements_deal_cards` scans timeline cases
    for clock readings in texts that deal no card; timetables and appointments go in
    `[test] untimed` by path. `seating` (accuse plus a seating plan: `final.seating` has
    `places` [{id, label}] in order round to each sitter's left, the first at the top;
    `people` {key: {name, aliases, when, fixed}}; `answer` {place: person};
    `wrong_ending`, `incomplete_ending`. SEATING draws the round table, SEAT <name> AT <n>
    and UNSEAT <name> edit `state.seating`; sitters appear once their `when` holds).
    `morse` (accuse plus attributing tape passages to senders: `final.morse` has `fists`
    {key: {dot, dash, gap, letter, word, split?, slip?, wobble?}} in mark units,
    `passages` {pid: {deal (clue), label, text, fist, sender? (known sample), clue?
    (noted when decoded)}}, `senders`, `answer` {pid: sender} for passages without a
    known sender, `codebook_when`, `wrong_ending`, `incomplete_ending`. Tape is drawn
    from the text and fist at runtime as `=` marks and spaces, so the prose never
    states it. Commands: TAPES, TAPE <letters>, DECODE <letter> AS <words> (accepts the
    literal reading of split letters; on a miss it says how many letters fit),
    ATTRIBUTE <letters> TO <name>, CODEBOOK; state in `state.decoded`/`attribution`).
    `cylinder` (accuse plus tracing a questioned cylinder's parts to their sources:
    `final.cylinder` has `sounds` {key: {name, freq? | rate?, voice?}} at true pitch,
    `cylinders` {cid: {deal, label, parts [{id, voice?, words?, true_speed, sounds?,
    clue?}], background? [{sound, true_speed, clue?}]}}, `answer` {part: source cid},
    `play_when`, `min_speed`/`max_speed`, `wrong_ending`, `incomplete_ending`. PLAY
    <letter> AT <speed> describes every sound with pitch/rate scaled by speed /
    true_speed and says how voices sound (words lost when far off); a `clue` is noted
    on first hearing that part or sound within 2% of its true speed. Parts of the
    questioned cylinder are numbered; SOURCE <n> FROM <letter>; CYLINDERS lists.
    Sources kept in `state.attribution`).
    `holmes/menu.py`: story select. `holmes/validate.py`: structural checks.
  - Story sources: `spoilers/stories/<id>/*.toml` (all files in a folder are merged).
    `python -m holmes.build` validates and writes scrambled `holmes/data/<id>.case`.
  - Each source has a private `[test]` section: `walkthrough` (must solve the case, find
    every clue, and hit no misfire replies) and optional `wrong_path` (must reach a bad
    ending). Run `python -m unittest`. Tests never print story text.
  - Shipped so far: `tutorial` (practice case, played and approved by the user),
    `bellboard` (E1, 19 rooms, 12 people; played and approved, "perfect") and
    `bazalgette` (E2, 16 rooms, 10 people, 31 clues; played, finished: "a little clunkier
    than the previous one" because the syntax had grown and the text hadn't caught up,
    since fixed by the signposting rule) and `clocks` (deduction case 2, The Two Clocks of
    Hatherleigh, 21 rooms, 14 people, 39 clues, 9 timeline cards, 8 halfpence; first
    `timeline` case; set "a little harder" than E2 at the user's request; played and
    finished: "very good case") and `medium` (deduction case 3, The Medium's Last
    Sitting, 14 rooms, 12 people, 34 clues, 8 threepenny bits; first `seating` case;
    difficulty "about the same" as Two Clocks; played and finished: "very good", but
    the seating was "too easy": testimony placed every sitter outright) and `fist`
    (deduction case 4, The Operator's Fist, 1887, Lizard coast, 15 rooms, 11 people,
    47 clues, 8 farthings; first `morse` case; a step harder than the Medium, with
    passages whose sender must be inferred; played and finished 2026-11-27. Tape
    reading and DECODE/ATTRIBUTE worked; the snag was noise: a minor fault in one
    fist (an occasional short dash) looked like another fist's wobble, and the player
    chased every discrepancy. Removed. **Every visible quirk in a puzzle should mean
    something; don't add texture that resembles a real tell.** Verdict on difficulty
    (user, 2026-11-27): "wasn't actually that hard". Lots of times and facts turned out
    superfluous; only a few mattered. Next case harder by **depth, not volume**: some
    noise is fine, but the solution should need more pieces logically linked, with
    chains where one inference unlocks the next (fact A + fact B gives C, which only
    matters beside D), rather than single clues that each settle a point.
    And `palace` (E3, The Crystal Palace by Night, 1895, 21 rooms, 10 people, 46 clues,
    8 sixpences; `accuse` with six questions; built for depth per the note above;
    played and finished 2026-11-27: "that was good"; one bug, Pike's keys named a
    screen door they could not open, fixed). Its timed mechanic: the second watchman walks a round (counter
    `round`, `move:` effects, `loc:crouch:ROOM` conditions), stands still while Watson
    is in his room, and a gallery stair opens only while he is there; STATUS shows
    where he is.
    And `cylinder` (deduction case 1, The Wax Cylinder Will, 1894, 15 rooms, 10 people,
    54 clues, 8 shillings; first `cylinder` case; a step above the Palace: the
    questioned cylinder has parts true at two speeds, and several parts' words fit
    two sources; played and finished 2026-11-27: "that was tricky", but it "got easy
    once I realized" the source cylinders fell into two speed groups; after that the
    SOURCE step was just matching phrases. Lesson: **a final puzzle should not collapse
    to bookkeeping after one insight**; build in a second, independent insight (or a
    group that splits again) so the last stretch still needs thought).
  - **Difficulty trajectory** (user, 2026-11-27): make each new case a little harder than
    the last, unless the user says the latest one was a little too hard. Don't ask about
    difficulty each time; just step it up.
  - **Final puzzles must leave gaps to infer** (user, 2026-11-27, on the Medium's seating):
    testimony should not hand over the whole answer piece by piece. Leave a gap or two
    (a seat, a card, a field) that no one states and the player must work out from
    constraints: elimination, "two places from", "had the fire at her back", a detail
    in a room. Validate privately that the gaps have exactly one consistent answer.
    Bibles live in
    `spoilers/stories/<id>/bible.md`.
  - Timed cases (added for E2): `case.counters` (named ints), conditions `lt:/ge:/eq:NAME:N`,
    effects `add:NAME:N` / `setn:NAME:N`, `case.every_turn` events run after each timed
    command (meta verbs like NOTEBOOK, HINT, LOOK, STATUS are free, and so is any command
    that came to nothing: engine refusals go through `Game.fail()`, user's request
    2026-11-26), `case.status` lines
    shown after each room and by STATUS, and WAIT running `case.wait_turns` turns (stops
    early when something happens). E2 uses these for a tide cycle and lantern oil.
  - A scripted walkthrough must respect the clock: plan the order so tide-gated places are
    visited in a low-water window. Trace a walkthrough's room/counters/clues without prose
    before committing it.
  - The walkthrough test also fails on any character's own "unknown topic/show" reply, so
    every ASK and SHOW in a walkthrough must hit a written answer.
- Puzzle mechanics needed by the lineup: room/inventory/examine parser, notebook of clues,
  "listen at speed" for cylinders, timeline builder, logic-grid/seating input, Morse
  input/codebook, tabular record viewer, delayed-message queue, save/load per story.

## Working with the user

- They pay per token on other plans; this plan has no usage cost, so thoroughness is fine.
- Next step from here: build the next case (user asked to proceed, 2026-11-27).
  Remaining: E4 Ice Wells, E5 Margaret Ainsley, Census Night (finale, needs record tables)
  and Letters from Sussex (needs the telegram queue).
