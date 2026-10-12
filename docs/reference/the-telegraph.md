# The telegraph

One lever a person rings, and the numbers it sets as a group. A run has a dozen numbers that all mean the
same thing in different units — how many berths are lit, how many delegates each captain may have, what a
slice may spend, how long a stage may take. Changing "go slower" from one to another is eight edits, and
anybody doing it in a hurry gets some of them.

```
slipwai telegraph                      # where it is, and every number under it
slipwai telegraph half-ahead           # ring a position: every number together
slipwai telegraph --set boilers=2      # change one and leave the rest
```

The numbers live in `harbour.json`, in the project, versioned with it and visible in a diff — because a
number in a prompt is a number nobody can find afterwards, and a number in somebody's head is not a number.

---

## The five positions

Fastest first; this is also the order the fires are banked in.

| Position | `boilers` | `fanout` | `bunker_per_slice` | `bunker_per_day` | `stage_scale` | `bar` | `decision_ceiling` | `wait_bound` | `attempts` |
|---|---|---|---|---|---|---|---|---|---|
| `full-ahead` | 5 | 3 | 1500 | 20000 | 1.0 | HIGH | 12 | 90 | 3 |
| `half-ahead` | 3 | 2 | 1000 | 10000 | 1.0 | MEDIUM | 10 | 60 | 2 |
| `slow-ahead` | 2 | 1 | 700 | 5000 | 0.75 | MEDIUM | 5 | 30 | 2 |
| `dead-slow` | 1 | 1 | 400 | 2000 | 0.5 | LOW | 3 | 20 | 1 |
| `stop` | 0 | 0 | 0 | 0 | 0.0 | LOW | 0 | 0 | 0 |

| Number | What it is |
|---|---|
| `boilers` | Berths lit at once |
| `fanout` | Delegates one captain may have running |
| `bunker_per_slice` | Thousands of input tokens one slice may spend |
| `bunker_per_day` | Thousands of input tokens the harbour may spend in a day |
| `stage_scale` | What every stage budget in `stages` is multiplied by |
| `bar` | The severity at or above which an adversary finding must close before a merge |
| `decision_ceiling` | Decisions that may stand unread before a fairway parks |
| `wait_bound` | Minutes a wait may go with the harbour log silent before it is a `parked` line |
| `attempts` | Times one slice may be re-dispatched before the fairway parks |

**`half-ahead` is where a fresh harbour starts.** Not `full-ahead`: a first run is the one nobody has
watched yet, and the position that spends most is a strange place to begin. The `half-ahead` row is exactly
the generated `harbour.json`'s defaults, so a new project reads `half-ahead` and not `half-ahead, adjusted`
on the day it is made.

The rows are not a formula. `bar` and `decision_ceiling` tighten as the run slows, because a slower run is
one somebody is already unhappy about, and that is a judgement rather than an arithmetic. A *lower* bar is
stricter, so slowing lowers it: a run somebody has slowed down is one where less gets deferred, not more.

---

## Adjusted

`--set` changes one number and leaves the others, and the board then says `half-ahead, adjusted` —
adjusted, not a new position, because a board reporting a position the numbers do not match is a board that
is lying.

Ringing a position again resets every number to that position's group, which is what makes a hurried `--set`
safe to make: there is one action that puts everything back. Ringing also rescales every stage budget in
`stages`, each kept to a minute and a token at least — zero would be a budget no stage can meet, which reads
as "every stage failed" rather than as `stop`.

A near miss is still a refusal. `slipwai telegraph half` lists the five rather than guessing, because ringing
the wrong lever because a name was guessed at is exactly what a closed set exists to stop.

---

## What the telegraph does not set

**Model roles.** `.specify/models.json` holds a role per stage and, per harness, what each role maps to. A
position does not touch it, and the telegraph cannot set it:

```
make models                                          # the table, and why each stage resolves as it does
python3 scripts/agents/models.py --set implement-shipwright=strong
```

**How wide a cycle is.** `delegate` and `cycle` belong to `/sail` and live in `.specify/sail.json`. They are
*mirrored* here so a person sets every width in one place, and `--set` writes them back where they came
from — but no position rings them, because they are not the harbour's to decide. Both are words rather than
numbers: `delegate` is `story`, `rule` or `task`; `cycle` is `rule` or `example`.

---

## Banking the fires

Banking the fires is this same lever, pulled by the clock instead of by a person. When the day's bunker is
spent, the harbourmaster steps the position down **one notch at a time** and writes `fires-banked` into the
[harbour log](the-logs.md) with the step and the reason. One notch, and not straight to `stop`: a run that
stops dead at the end of the day loses whatever was in flight, and a run that slows keeps finishing what it
started. A person stokes the fires back up by ringing the telegraph again.

`stop` is not a crash. Every captain parks at its *next boundary*, which is the thing a captain was built to
have: a place where ending costs nothing and the log says exactly where it got to.

---

Next: [fairways, captains and the harbourmaster](fairways-and-captains.md) ·
[the deck log and the harbour log](the-logs.md) · [let it cruise](../guide/let-it-cruise.md)
