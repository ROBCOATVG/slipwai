# Let it cruise

So far you have been in the room for every slice. This page is about not being — a run that keeps going
while you are at lunch, and stops for you when it genuinely needs you rather than at every rung.

The honest summary first: **this does not take you out of the loop, it takes you out of the loop's
middle.** Three things still stop for a person, by design, and they are the three where being wrong is
expensive.

---

## Cast off

```console
$ make cruise
cruise: harbourmaster up (pid 48021), captains: booking (48023), availability (48024)
cruise: nothing here is holding the state of the run — close this terminal if you like
```

That last line is not a pleasantry. The first attempt's runner *was* the state of the run; it died at
iteration two, and the seventeen iterations after it ran from interactive sessions and wrote nothing, so
the checkpoint still said "iteration 2" while twenty slices merged. Nothing here holds anything. Kill
every process and `slipwai fleet` still tells you exactly where the run got to, because it reads the logs.

## The captain

One captain per fairway. Each turn it fetches trunk and both logs, works out its own state from its own
`claimed` and `merged` lines, picks the next slice that clearance allows, writes `claimed`, dispatches
`/sail` in that fairway's berth, and watches the log while it runs.

**It believes the log, not the agent.** A captain ends a stage that shows no progress for the stage bound,
and parks it with a reason. The stage bound is the longest stage budget in `harbour.json`. Two things count
as progress: a new line in the fairway's deck log, and a new commit on the slice's branch, `slice/<id>`.
Both are evidence on disk. Neither is the agent's own account of itself, and a stuck agent cannot say that
it is stuck. This is the reason a captain is safe to leave alone.

The commit counts because the implement rung commits one example at a time and writes no deck line until
its mark. Before this rule, a captain ended a slice that had committed fourteen times in ninety minutes.

When the agent parks its own stage, the captain keeps that park and its reason. It does not add a second
park on top.

A captain holds no credential and never merges. It asks:

```
2026-10-08T09:14:50Z  asked to merge: merge slice/BOK-01 into trunk after the full gate
```

## The harbourmaster

One per **machine**. It writes its own harbour log, `.slipwai/logs/harbour/<machine>.jsonl`, and reads
every machine's — folded into one history by the instant each line records, exactly the way the deck logs
are. One writer per file is the rule everything here rests on, and three people's harbourmasters writing
one file would break it; electing one of them would need an election, and the elected one could not see
the other machines' berths anyway. It does three jobs:

- **Carries marks.** A `mark-set` line in one fairway's deck log becomes a harbour-log line every other
  fairway reads. That is the mechanism behind "nothing merged and the sibling started".
- **Answers requests.** A captain asks; it writes `granted` or `refused`, with the reason. A request that
  was refused and left no line is one a captain waits on for ever and nobody can explain afterwards.
- **Allocates berths.** Up to the number of boilers lit, out of its own machine's allocations — ports are
  local to a machine, so two machines allocating independently cannot collide, and a berth's database name
  carries the machine for the case where you point both at one database server.

**The merge is the one thing that still needs a decider**, and it is serialised by a ref rather than by a
process: a harbourmaster takes `refs/slipwai/merge` before it rebases and gives it back afterwards, the
same compare-and-swap a captain uses to claim a fairway. The machine that loses the race waits; the one
that is still waiting when `wait_bound` runs out says which machine has it and since when.

## The telegraph: one lever for the whole run

```console
$ slipwai telegraph
telegraph: half-ahead
  boilers           3         berths lit at once
  fanout            2         delegates one captain may have running
  bunker_per_slice  1000      thousands of work tokens (uncached input + output) one slice may spend
  bunker_per_day    10000     thousands of work tokens (uncached input + output) the harbour may spend in a day
  stage_scale       1.0       what every stage budget in `stages` is multiplied by
  bar               MEDIUM    the severity at or above which an adversary finding must close before a merge
  decision_ceiling  10        decisions that may stand unread before a fairway parks
  wait_bound        60        minutes a wait may go with the harbour log silent before it is a parked line
```

Five positions, fastest first:

| Position | boilers | fanout | per slice | per day | bar | decisions | wait |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `full-ahead` | 5 | 3 | 1500k | 20000k | HIGH | 12 | 90m |
| `half-ahead` | 3 | 2 | 1000k | 10000k | MEDIUM | 10 | 60m |
| `slow-ahead` | 2 | 1 | 700k | 5000k | MEDIUM | 5 | 30m |
| `dead-slow` | 1 | 1 | 400k | 2000k | LOW | 3 | 20m |
| `stop` | 0 | 0 | 0 | 0 | LOW | 0 | 0 |

```sh
slipwai telegraph slow-ahead          # every number together
slipwai telegraph --set boilers=4     # one number; the board then says "slow-ahead, adjusted"
```

**Notice that the bar gets *stricter* as the run slows.** That is not arithmetic, it is a judgement: a run
somebody has reached over and slowed down is a run they are already unhappy with, so less gets deferred,
not more. `stop` is the brake — running captains finish the stage they are in and park.

## Saying something to a run that is going

```sh
make cruise-tell MSG="the hold should expire after 15 minutes, not 45"
```

It goes into that fairway's inbox, and the captain reads the inbox **at every boundary** — not just at the
start of a slice. Having read it, it writes a `read` line carrying the timestamp of what it answers, which
is what makes it a receipt rather than an assertion that somebody looked.

`--now` ends the iteration in flight so the message goes immediately, at the cost of the stage's work.

**A message to a parked fairway clears the park.** The message is a `told` line in the fairway's deck log.
The board's answer box writes the same line. On its next pass, the harbourmaster writes a `cleared` receipt
in the harbour log for each open park that the message came after, and keeps the message as the answer. On
the pass after that, it lights the captain again.

**The harbourmaster does not light a captain for a parked fairway.** That captain would read the park and
exit at once. The fairway waits until a person clears the park.

## What still stops for a person

1. **Mock-up approval.** Before the work is typed, every surface state is approved, parked with the question
   it waits on, or marked `n/a` with a reason. A surface nobody has seen becomes a read model, a route and a
   set of tests, and all three cost more to move than a drawing.
2. **The demo.** An actor-visible run of the slice, in front of somebody, and acceptance is recorded against
   a **capability** rather than a slice — because what a person accepts is a chunk of working product, not a
   branch.
3. **Anything the ceiling catches.** When `decision_ceiling` decisions have been taken without a person
   reading them, the fairway parks itself. Not a warning: it stops. A run that takes a hundred unread
   decisions is a run that has quietly become somebody else's product.

Everything else — stage order, budgets, which slice is next, scope, the gates — is enforced rather than
asked about.

The steps above the chart — the specification, the storyboard and the event model — also stop for a person
by default. The `upstream` setting makes them advance on their own instead. [The workflow](the-workflow.md#the-upstream-setting)
describes it.

## Careen and stow

```sh
make careen     # stop taking new slices, finish what is in flight, and clean up
```

A long run accretes: stale berths, branches whose slices merged, logs worth rotating. `careen` is the
haul-out. **Stow** is the smaller one — a captain stowing its working state at a boundary so the next turn,
possibly in a different process, picks it up from disk rather than from memory it no longer has.

## What this looks like when it is working

![The bridge: what is waiting on a person, the streams, the speed](../captures/bridge.png)

Two streams, one question waiting, the lever at half-ahead, and the run reporting on itself a line at a
time. You answer the top block and leave the rest alone.

## Next

→ **[Bring an existing codebase](adopt.md)** — if what you want to do this to already exists.

Other pages: [start here](start-here.md) · [your first feature](first-feature.md) ·
[a second person joins](a-second-person.md) · [the workflow](the-workflow.md) · [the board](the-board.md) ·
[the vocabulary](../../GLOSSARY.md)
