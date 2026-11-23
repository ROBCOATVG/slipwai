# The telegraph

The telegraph is one lever that a person rings. It sets a group of numbers together. A run has about a dozen
numbers that all mean the same thing in different units. Examples are how many berths are lit, how many
delegates each captain can have, what a slice can spend, and how long a stage can take. To change from "go
faster" to "go slower" by hand, a person must make eight edits. A person in a hurry gets some of them
wrong.

```
slipwai telegraph                      # where it is, and every number under it
slipwai telegraph half-ahead           # ring a position: every number together
slipwai telegraph --set boilers=2      # change one and leave the rest
```

The numbers are in `harbour.json`, in the project. They are versioned with the project and visible in a
diff. A number in a prompt is a number that nobody can find later. A number in somebody's head is not a
number.

---

## The five positions

The table shows the fastest position first. Banking the fires steps down through the positions in the same
order.

| Position | `boilers` | `fanout` | `bunker_per_slice` | `bunker_per_day` | `stage_scale` | `decision_ceiling` | `wait_bound` | `attempts` | `browsers` |
|---|---|---|---|---|---|---|---|---|---|
| `full-ahead` | 5 | 3 | 1500 | 20000 | 1.0 | 12 | 90 | 3 | 2 |
| `half-ahead` | 3 | 2 | 1000 | 10000 | 1.0 | 10 | 60 | 2 | 1 |
| `slow-ahead` | 2 | 1 | 700 | 5000 | 0.75 | 5 | 30 | 2 | 1 |
| `dead-slow` | 1 | 1 | 400 | 2000 | 0.5 | 3 | 20 | 1 | 1 |
| `stop` | 0 | 0 | 0 | 0 | 0.0 | 0 | 0 | 0 | 0 |

| Number | What it is |
|---|---|
| `boilers` | Slice sessions running at once, across every fairway |
| `fanout` | Delegates one captain may have running |
| `bunker_per_slice` | Thousands of input tokens one slice may spend |
| `bunker_per_day` | Thousands of input tokens the harbour may spend in a day |
| `stage_scale` | What every stage budget in `stages` is multiplied by |
| `decision_ceiling` | Decisions that may stand unread before a fairway parks |
| `wait_bound` | Minutes a wait may go with the harbour log silent before it is a `parked` line |
| `attempts` | Times one slice may be re-dispatched before the fairway parks |
| `browsers` | Browser-driven test runs at once on this machine |

**`boilers` counts slice sessions, not captains.** A captain runs every ready slice of its fairway that
the slice graph lets run together, so a number that counted captains would let three fairways run nine
slices on a machine somebody set to three. One budget, shared by the harbourmaster — see
[how the boilers are shared](fairways-and-captains.md#how-the-boilers-are-shared).

**`abreast` is a number no position rings.** It is how many of one fairway's slices may run at once,
`3` where `harbour.json` does not say, and never more than `boilers`:

```
slipwai telegraph --set abreast=1      # one slice at a time in every fairway: the fleet as it was
slipwai telegraph --set abreast=5      # wider, still within boilers
```

It is a shape and not a pace. `boilers` is the pace and already bounds it, so ringing `slow-ahead` narrows
every fairway without a second lever, and a `harbour.json` written before the number existed does not read
as `adjusted`. Zero is refused: a fairway that may run nothing is `stop`, said in the wrong place.

**`bar` is not on the lever either.** It is the severity at or above which a finding must close before a
merge rather than be stowed into the careen, and it is `MEDIUM` until a person changes it:

```
slipwai telegraph --set bar=HIGH       # what may merge unfixed: a person's decision, never a position's
```

What may merge unfixed is a quality decision, and the positions are a throughput decision. While the bar was
one of the positions' numbers, ringing `full-ahead` for throughput quietly raised it to `HIGH`, and a real
run then stowed forty-six MEDIUM findings — a coerced request body that countersigned an agreement, a
control character that forged a line in a signed PDF, a rounding that fed a valuation. So no ring and no
banking of the fires moves it, `slipwai telegraph` and the board show it beside the position, and a
`harbour.json` with no `bar` reads as `MEDIUM`.

Whatever the bar says, some findings are never stowed. **A finding that leaves a feature unusable or
untrustworthy for its actor is never deferred**: a CRITICAL, and a finding of any of these kinds, whatever its
severity. Each parks or is fixed like a finding above the bar, and carries `kind: <tag>`:

- `validation-bypass` — input coercion or a validation bypass on a state-changing route
- `document-forgery` — forgery or injection into a generated document — a PDF, an email
- `erasure-leak` — personal data that survives, or leaks, after deletion or erasure
- `money-arithmetic` — wrong arithmetic in a money or financial figure

**A new harbour starts at `half-ahead`.** It does not start at `full-ahead`. Nobody has watched a first run
yet, so the position that spends the most is a strange place to start. The `half-ahead` row is exactly the
defaults of the generated `harbour.json`. So a new project reads `half-ahead`, not `half-ahead, adjusted`,
on the day it is made.

The rows are not a formula. `decision_ceiling` gets stricter as the run slows. A slower run is a run that
somebody is already unhappy about. That is a judgement, not arithmetic.

---

## Adjusted

`--set` changes one number and leaves the others. The board then says `half-ahead, adjusted`. It says
adjusted, not a new position, because a board that reports a position that the numbers do not match is
giving false information.

Ringing a position again resets every number to that position's group. This makes a hurried `--set` safe,
because one action puts everything back. Ringing also rescales every stage budget in `stages`. Each budget
stays at one minute and one token or more. A budget of zero is a budget that no stage can meet. It would
read as "every stage failed", not as `stop`.

A name that is nearly correct is still refused. `slipwai telegraph half` lists the five positions. It does
not guess. A closed set of positions exists to stop the wrong lever being rung because a name was guessed.

---

## What the telegraph does not set

**Model roles.** `.specify/models.json` holds a role for each stage. For each harness, it also holds what
each role maps to. A position does not change this file, and the telegraph cannot set it:

```
make models                                          # the table, and why each stage resolves as it does
python3 scripts/agents/models.py --set implement-shipwright=strong
```

**How wide a cycle is.** `delegate` and `cycle` belong to `/sail`, and they are in `.specify/sail.json`.
The telegraph *mirrors* them, so a person sets every width in one place. `--set` writes them back to
`.specify/sail.json`. But no position rings them, because the harbour does not decide them. Both are words,
not numbers:

- `delegate` is `story`, `rule` or `task`.
- `cycle` is `rule` or `example`.

---

## Banking the fires

Banking the fires is the same lever, but the clock pulls it, not a person. When the day's bunker is spent,
the harbourmaster steps the position down **one notch at a time**. It writes `fires-banked` into the
[harbour log](the-logs.md), with the step and the reason.

It steps one notch, not straight to `stop`. A run that stops dead at the end of the day loses the work that
was in progress. A run that slows down continues to finish what it started. To stoke the fires back up, a
person rings the telegraph again.

`stop` is not a crash. Every captain parks at its *next boundary*. A captain was built to have this: a place
where stopping costs nothing, and where the log says exactly how far the work got.

---

Next: [fairways, captains and the harbourmaster](fairways-and-captains.md) ·
[the deck log and the harbour log](the-logs.md) · [let it cruise](../guide/let-it-cruise.md)
