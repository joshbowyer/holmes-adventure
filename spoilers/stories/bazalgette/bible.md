# Below Bazalgette — story bible (PRIVATE)

Wednesday 10 November 1886. Play opens about eight in the morning at the Metropolitan
Board of Works flushers' depot in Water Lane, Blackfriars.

## The truth

**Victim:** Edwin Hurrell, 34, assistant engineer, Main Drainage department of the
Metropolitan Board of Works. He had been sent to examine Gaskin & Pell's contract for
relining the invert and haunches of the Fleet sewer above the Blackfriars penstock
(paid by measure) before the final payment certificate was signed.

**Murderer:** Joseph Ruddock, works foreman to Gaskin & Pell. He did the work and
measured it. Over chains 9–14 his gang never relined at all: they rendered a skin of
cement over the old, rotten brick and he certified it as new lining. Abel Coaker, the
Board's flushers' foreman, countersigned the measurements for a consideration from
Gaskin. Exposure meant prison for Ruddock (fraud on a public body); Coaker would lose
his place; Gaskin his name and the Board's custom. Only Ruddock killed.

**Motive:** to stop Hurrell reporting that the relining was a sham.

### Timeline (true)

| Time | Event |
|---|---|
| Tue 3 Aug | A second penstock handle lent to Gaskin & Pell for the works (key book). It hangs in Ruddock's hut; he alone keeps the hut key. |
| Tue 9 Nov, day | Hurrell, suspicious, tells Ruddock he will go down and see for himself. Ruddock proposes they meet at the penstock at midnight "when the works are quiet and the flow low" and he will show him the lining is sound. |
| 10.00 pm | Dunn's gang shut the Fleet penstock to gather a head for the scheduled 2 a.m. flush (routine). The pond fills ~2 ft an hour in dry weather. |
| 11.20 pm | Hurrell signs out the Farringdon Street side-entrance key from Coaker and draws lamp No. 7, filled, from Sparrow (oil book). A full lamp burns about four hours. |
| 11.30 pm – 1.30 am | Coaker and Sparrow play cribbage in the lamp-room. The depot handle hangs on its rack in the office in view of the lamp-room door the whole time. |
| ~11.40 pm | Hurrell, above the pond on the side benching, scrapes the render at chain 11 with his knife: old rotten brick beneath. Render under his nails. Writes last notebook entry. |
| ~11.55 pm | Ruddock comes down the contractors' works shaft from the yard with his dark lantern and the contractors' penstock handle. |
| ~12.05 am | On the penstock walkway Ruddock strikes Hurrell on the back of the head with the square socket end of the handle (depressed square fracture ~1 in). Hurrell falls senseless. Ruddock rolls him into the pond above the gate (4 ft head by now). He screws down the wick of lamp No. 7 so no light shows along the tunnel, meaning to throw it after the body, and in the dark with his own lantern shuttered he cannot find it again on the ledge. |
| ~12.15 am | Ruddock winds up the penstock: no whistle. The flush carries Hurrell down the Fleet, over the storm weir (only a flood tops it; dry-weather flow turns into the low-level sewer) and into the outfall chamber. His watch, hanging loose, snags on the weir's iron edge; the chain's last link is torn open. |
| ~12.15 am | Ruddock timed it for low water (depot board and his own works tide card: low water 12.15–12.20), when the tidal flaps stand open and a flush would sweep a body out into the river to be found days later downstream as a common drowned man. But an easterly gale had held the tide up: at 12.15 the river stood near full and the flaps were shut fast. The body stayed in the outfall chamber. |
| ~12.20 am | Ruddock shuts the gate again so all looks as left, and the pond begins to refill. |
| ~12.30 am | Ruddock climbs out the works shaft (smearing the upper rungs with sewer mud), wet to the thighs. Fitch, the contractors' night watchman, sees him; Ruddock tells him to hold his tongue. Ruddock goes home, hangs his wet trousers behind the hut stove first, scrubs the handle in the yard trough. |
| ~12.15 am | Saul Mott, an old tosher working the Fleet below the shaft foot (he gets in by an old cellar shaft in Fleet Lane), hears a flush come down with no whistle, climbs onto the benching, sees something heavy go past. Afterwards finds a gold watch snagged at the weir and pockets it. |
| 1.30 am | Dunn draws the depot handle (key book). |
| 2.00 am | Dunn's gang blow the whistle and flush. Gauge only 3 ft 4 in (should be ~8 ft by 2 — full crest is 7 ft, so "full"); logged as "head low". Dunn sees an unlit lamp on the ledge and takes it for contractors' gear. 3 ft 4 in at 2 ft/hr ⇒ pond emptied ~12.20. Gate shut again 2.20. Mott hears the 2 a.m. whistle and goes home. |
| ~2.30 am | Wind drops; river falls fast. True low water near four. |
| 4.15 am | Dick Pellow, waterman, rowing past the outfall at low water, sees a man's arm hanging out under a flap. Fetches the Thames Police; flushers bring the body up through the sewer at low water. |
| 8.00 am | Play begins. Gregson's view: misadventure (fell into the channel in the dark and was carried down), with a hope of hanging it on the tosher, who was seen hawking a gold watch at 6 a.m. |

### Why the body stayed

The flaps open only when the river is lower than the water in the sewer behind them.
Held up by the gale, the tide never fell at the predicted hour; at 12.15 the flaps were
shut and the flush simply filled the outfall chamber. (Pellow, the flap mechanism, the
tide board.) At 2 the flaps were still shut. When the river fell after 2.30 the chamber
drained slowly through the half-open flaps and the body lodged against one.

## Red herrings / wrong answers

- **Coaker** — complicit in the fraud (countersigned the measure), evasive, named
  "the foreman" ambiguously in Hurrell's notebook. Alibi: cribbage with Sparrow
  11.30–1.30 in the lamp-room; never left.
- **Gaskin** — motive. Alibi: Masonic dinner at the Cannon Street Hotel until 1.15
  (Gregson has checked it), and no key to the hut.
- **Mott** — had the watch (Gregson's suspect). Cleared: the chain was torn by force, not
  unhooked; a thief would have taken the chain and the money too; he has no handle.
- **Dunn** — flushed at 2, with the whistle; the body went down near midnight
  (lamp oil) and the head at 2 was low because someone had already flushed.
- **Accident** — the wound is a blow, square, from behind, and there is little sign of
  drowning; a lamp put out by screwing down the wick.

## Mechanics

- Tide cycles (counter `tide` 0 low, 1 flood, 2 high, 3 ebb; `tide_left` turns). The
  foreshore and the outfall chamber can be reached only at low water.
- Lantern oil (counter `oil`, 40 when full): burns only below ground. Runs out ⇒ Watson
  gropes back to the shaft foot. Refill in the lamp-room.
- The pond stands full in the morning, drowning the relined length. Watson must take the
  depot handle and the whistle, blow it at the penstock, then let the pond off.

## Solution

who = ruddock; how = an unwarned flush about 12.15; why it stayed = wind-held tide kept
the flaps shut; why = to hide the sham relining.
