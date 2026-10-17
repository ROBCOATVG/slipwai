# A second person joins

If one person drives one slice at a time, that person does not need this page. Two people do need it. One
person who runs two agents also needs it. The problem is the same in both cases: **two workers in one
repository, and nobody waits for anybody's branch.**

---

## The fairway, not the branch

A **fairway** is the slices of one bounded context. A fairway owns a set of paths, and one worker holds it
at a time. Everything on this page is about the fairway:

- the board has one row for each fairway
- the logs have one file for each fairway
- the scope gate checks each fairway separately

The chart says what each fairway owns:

```yaml
fairways:
  booking:
    owns: ["apps/bookings/**/booking/**"]
  availability:
    owns: ["apps/bookings/**/availability/**"]
```

```console
$ make check-slice-scope
check-slice-scope: slice/BOK-01 touches only what one slice may
```

If a branch writes outside its fairway, the gate refuses it. The refusal names the path and the fairway
that owns that path. This is a gate, not a convention. The first attempt relied on a convention, and two
agents rewrote each other's adapter within an hour.

## Why neither of you is waiting

Read this part slowly. It is the thing that version 2 changed.

`BOK-01` is in the `booking` fairway and sets `BookingHeld`. `AVA-01` is in `availability` and steers by
`BookingHeld`.

- The old rule: `AVA-01` waits for `BOK-01` to merge.
- The new rule: **`AVA-01` is cleared as soon as the mark is set.** `BOK-01` sets the mark at its first
  stage, in its own worktree, before anything has merged anywhere:

```console
$ slipwai fleet booking
booking: the last 6 line(s) its captain wrote
  2026-10-08T09:14:48Z  claimed BOK-01
  2026-10-08T09:14:48Z  set BookingHeld — BOK-01
  2026-10-08T09:14:49Z  still going, 42k spent
  2026-10-08T09:14:49Z  demo of BOK-01: accepted
  2026-10-08T09:14:50Z  asked to merge: merge slice/BOK-01 into trunk after the full gate
  2026-10-08T09:14:58Z  merged BOK-01 as a1b2c3d4

$ python3 scripts/agents/clearance.py
clearance: 2 of 3 slices start now in booking (slots: 3)
  start  BOK-02  implement  — cleared and sets nothing, so there is nothing to settle
  start  AVA-01  prepare  — cleared; may prepare now — example map, the contract it sets, gaps — and implementation waits on its own mark-set for TableTaken
  done   BOK-01  — merged at a1b2c3d4
```

**Read the second line, and then the last line.** The mark was set one second after the slice was claimed.
Nothing reached trunk until ten seconds later. `AVA-01` was cleared by line two. That was eight seconds and
four rungs before `BookingHeld` existed anywhere except in one worktree.

This is safe because of the rule that the chart enforces: **each mark has one setter**. `BookingHeld` has
exactly one owner and one typed definition. So a second fairway that builds against it cannot build against
a different definition. If two slices both claimed to set it, `make check-chart` would have refused the
chart before either slice started.

## Berths: how a worker is given a place to work

A **berth** is a worktree with a branch and a name. The second person does not clone anything and does not
negotiate anything:

```console
$ slipwai fleet
berths: 2
  fairway       feature  slice   state    waiting  last line  tokens  merged  marks
  ------------  -------  ------  -------  -------  ---------  ------  ------  -----
  availability  booking  AVA-01  working  0        31s ago    42      0       0
  booking       booking  BOK-02  working  0        12s ago    84      1       1
```

Each berth is a separate working directory on the same repository. So two gates can run at the same time,
and they do not compete for one `node_modules` or one database file.

## Taking a fairway

Neither of you picks a slice. `/sail` with no arguments already takes every ready slice of every fairway
that nobody holds. So two people who both run it take different work, and they do not need to agree
anything. The claim is the `slice/<id>` branch. When somebody has claimed a slice, the other person leaves
it.

If you do want to divide the fairways between you, name one:

```
/sail fairway=booking
```

This limits the ready set to `booking`. `/sail` names the ready slices of the other fairways as another
fairway's, and leaves them. To make the division last, take the fairway:

```sh
python3 scripts/agents/claims.py --take booking    # and --release when you are done with it
```

This pushes `refs/slipwai/claims/booking`. A second person cannot win that push. So the second machine that
tries is told who holds the fairway and since when. Without this, both of you would append to one deck log.

- A captain does exactly this before it claims a slice.
- The split's `held_by` column is **rendered** from those refs. You never type a name into it, and
  `make check-rendered` refuses a split where somebody has.
- The claim is still **routing, not a lock**. The claim on the work itself is the `slice/<id>` branch. So
  two sessions on one fairway make two claims, and the second session finds the first.
- A harbour with no `origin` shows `—` in the column, and says that the claim is local to that machine. A
  claim that nobody else can see does not route anybody.

## The board

```sh
slipwai fleet          # once
slipwai fleet watch    # redrawn every few seconds
```

```
waiting on you: 2
  billing    told    should a refund be its own capability?
  billing    told    are you doing anything

berths: 2, 2 stalled
  fairway   feature  slice   state    last line  tokens  merged  marks
  --------  -------  ------  -------  ---------  ------  ------  -----
  billing   model    BIL-01  stalled  989m ago   42      0       1
  ordering  model    ORD-02  stalled  990m ago   84      0       1

telegraph: half-ahead  boilers 3  fanout 2  bunker 126/10000k today

last lines
  2026-10-07T16:11:51Z  billing    mark-set
  2026-10-07T16:11:53Z  ordering   claimed
  2026-10-07T16:11:53Z  ordering   demo
  2026-10-07T16:11:55Z  harbour    granted
  2026-10-07T16:11:55Z  harbour    mark-set
```

**Read the first block first.** "Waiting on you" is the only part of the board that is about you.
Everything below it is the run reporting on itself.

**The board keeps no state.** The board calculates every column from the logs each time it draws them.
Nothing writes a status field anywhere. This is deliberate. It corrects two specific failures:

- In the first attempt, a runner was the only source of status. It stopped at iteration two, and twenty
  slices continued to merge.
- A model file said `planned` for eight slices that had shipped. The field was written at plan time and
  never corrected.

**A stage that wrote no log line and made no commit made no progress.** This rule is the whole design. It
is only true if the board reads nothing except the logs and git.

`stalled` above is the rule at work. Those two captains had written nothing for sixteen hours, so the board
says so. It does not guess.

## One stream's log

The board always makes people ask the same question: *what is `billing` actually doing?* The board cannot
answer it, because the answer is forty lines of one file. So use this:

```console
$ slipwai fleet ordering
ordering: the last 9 line(s) its captain wrote
  2026-10-07T16:11:48Z  claimed ORD-01
  2026-10-07T16:11:48Z  set OrderPlaced — ORD-01
  2026-10-07T16:11:49Z  still going, 42k spent
  2026-10-07T16:11:49Z  demo of ORD-01: accepted
  2026-10-07T16:11:50Z  asked to merge: merge slice/ORD-01 into trunk after the full gate
  2026-10-07T16:11:53Z  claimed ORD-02
  2026-10-07T16:11:53Z  still going, 42k spent
  2026-10-07T16:11:53Z  demo of ORD-02: accepted
  2026-10-07T16:11:55Z  asked to merge: merge slice/ORD-02 into trunk after the full gate
```

This is the fairway's own log, told one line at a time, in English. Each fairway writes only its own file,
and nothing else writes that file. This is why two workers never conflict on a log, and why the board can
combine all the logs without a lock.

## Answering from one seat

While a run is going, you do not want two terminals and a board that you must run again:

```console
$ slipwai bridge
bridge: http://127.0.0.1:8099  — ctrl-c to stop
```

![The bridge: what is waiting on a person, the streams, the speed](../captures/bridge.png)

The items that wait for a person are at the top. When you type an answer there, the answer becomes a line
in that stream's own log. It is the same line that the agent would get in a terminal.

The page binds only to the loopback address. The page changes what a run does, so it must not be on a
shared network by default.

## Next

→ **[Let it cruise](let-it-cruise.md)**: captains, the telegraph, and the decisions that a person still
makes.

Other pages: [start here](start-here.md) · [your first feature](first-feature.md) ·
[bring an existing codebase](adopt.md) · [the vocabulary](../../GLOSSARY.md)
