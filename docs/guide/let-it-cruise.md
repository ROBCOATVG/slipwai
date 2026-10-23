# Let it cruise

Until now, you have been present for every slice. This page is about a run that continues without you. For
example, the run keeps going while you are at lunch. It stops for you only when it really needs you, not at
every rung.

First, the honest summary: **cruising does not take you out of the loop. It takes you out of the middle of
the loop.** Three things still stop for a person, by design. They are the three things where a wrong
decision is expensive.

---

## Cast off

Type `/cruise` in your coding agent. It runs `make cruise`, repeats what that printed, and then takes the
watch seat in your session and prints each stream's lines as they arrive:

```console
> /cruise
harbourmaster started, pid 48021
booking: captain started, pid 48023
availability: captain started, pid 48024
`slipwai fleet` shows what they are doing; `slipwai bridge` is the page you answer from
```

`make cruise` starts the harbourmaster and one captain for each fairway, and then exits. You can close the
terminal or end the session. Nothing that `make cruise` started holds the state of the run.

This matters because of the first attempt. In the first attempt, the runner *was* the state of the run. It
stopped at iteration two. The seventeen iterations after it ran from interactive sessions and wrote
nothing, so the checkpoint still said "iteration 2" while twenty slices merged. In version 2, no process
holds the state. If you stop every process, `/cruise-status` still tells you exactly where the run got to,
because it reads the logs.

## The captain

There is one captain for each fairway. On each turn, a captain does these things:

1. It fetches trunk and both logs.
2. It works out its own state from its own `claimed` and `merged` lines.
3. It picks the next slice that clearance allows.
4. It writes `claimed`.
5. It runs `/sail` in that fairway's berth.
6. It watches the log while `/sail` runs.

**The captain believes the log, not the agent.** If a stage shows no progress for the stage bound, the
captain ends the stage and parks it with a reason. The stage bound is the longest stage budget in
`harbour.json`. Two things count as progress:

- a new line in the fairway's deck log
- a new commit on the slice's branch, `slice/<id>`

Both are evidence on disk. Neither is the agent's own report about itself, and a stuck agent cannot report
that it is stuck. This is why you can leave a captain alone safely.

The commit counts because the implement rung commits one example at a time, and writes no deck line until
its mark. Before this rule, a captain ended a slice that had committed fourteen times in ninety minutes.

When the agent parks its own stage, the captain keeps that park and its reason. The captain does not add a
second park on top.

A captain holds no credential and never merges. It asks for the merge:

```
2026-10-08T09:14:50Z  asked to merge: merge slice/BOK-01 into trunk after the full gate
```

## The harbourmaster

There is one harbourmaster for each **machine**. It writes its own harbour log,
`.slipwai/logs/harbour/<machine>.jsonl`. It reads the harbour logs of every machine, and combines them into
one history by the time on each line. It combines the deck logs in the same way.

Each file has one writer. Everything here depends on that rule. If the harbourmasters of three people wrote
one file, the rule would break. To choose one of them to write would need an election, and the chosen one
still could not see the berths on the other machines.

The harbourmaster does three jobs:

- **It carries marks.** A `mark-set` line in one fairway's deck log becomes a line in the harbour log, and
  every other fairway reads that line. This is how a sibling slice starts when nothing has merged.
- **It answers requests.** A captain asks, and the harbourmaster writes `granted` or `refused`, with the
  reason. If a request were refused without a line, a captain would wait for ever, and nobody could explain
  why afterwards.
- **It allocates berths.** It allocates up to the number of boilers that are lit, from its own machine's
  allocations. Ports are local to a machine, so two machines that allocate separately cannot collide. A
  berth's database name includes the machine, in case you point both machines at one database server.

**The merge is the one thing that still needs one decider.** A ref puts merges in order, not a process. A
harbourmaster takes `refs/slipwai/merge` before it rebases, and gives it back afterwards. This is the same
compare-and-swap that a captain uses to claim a fairway. The machine that loses the race waits. If it is
still waiting when `wait_bound` runs out, it says which machine has the ref and since when.

## The telegraph: one lever for the whole run

```console
$ slipwai telegraph
telegraph: half-ahead
  boilers           3         slice sessions running at once, across every fairway
  fanout            2         delegates one captain may have running
  bunker_per_slice  1000      thousands of work tokens (uncached input + output) one slice may spend
  bunker_per_day    10000     thousands of work tokens (uncached input + output) the harbour may spend in a day
  stage_scale       1.0       what every stage budget in `stages` is multiplied by
  bar               MEDIUM    the severity at or above which an adversary finding must close before a merge
  decision_ceiling  10        decisions that may stand unread before a fairway parks
  wait_bound        60        minutes a wait may go with the harbour log silent before it is a parked line
  abreast           unset     slices one fairway may run at once, within `boilers` — 1 is one slice at a time
```

There are five positions. The fastest is first:

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

**Note: the bar gets *stricter* as the run slows.** This is a judgement, not arithmetic. If somebody slows a
run down, they are probably already unhappy with it. So the run defers less work, not more. `stop` is the
brake: running captains finish the stage that they are in, and then park.

## Saying something to a run that is going

```text
/cruise-tell booking the hold should expire after 15 minutes, not 45
```

The first word is the stream, and the rest is the message. `/cruise-tell` refuses a message with no stream,
and lists the streams that there are. `--everyone` as the first word sends the message to every stream. The
board's answer box writes the same line.

The message goes into that fairway's inbox. The captain reads the inbox **at every boundary**, not only at
the start of a slice. When the captain has read the message, it writes a `read` line with the timestamp of
the message that it answers. This makes the `read` line a receipt, not just a claim that somebody looked.

**A message to a parked fairway clears the park.** The message is a `told` line in the fairway's deck log.
The board's answer box writes the same line. On its next pass, the harbourmaster writes a `cleared` receipt
in the harbour log for each open park that the message came after. It keeps the message as the answer. On
the pass after that, it starts the captain again.

**The harbourmaster does not start a captain for a parked fairway.** That captain would read the park and
exit at once. The fairway waits until a person clears the park.

## What still stops for a person

1. **Mock-up approval.** Before the work is given types, every surface state is approved, parked with the
   question that it waits on, or marked `n/a` with a reason. A surface that nobody has seen becomes a read
   model, a route and a set of tests. All three cost more to change than a drawing.
2. **The demo.** This is a run of the slice that an actor can see, in front of somebody. Acceptance is
   recorded against a **capability**, not a slice, because a person accepts a piece of working product, not
   a branch.
3. **Anything that the ceiling catches.** When `decision_ceiling` decisions have been taken without a person
   reading them, the fairway parks itself. This is not a warning: the fairway stops. A run that takes a
   hundred unread decisions has quietly become somebody else's product.

Everything else is enforced, not asked about: the stage order, the budgets, which slice is next, the scope
and the gates.

By default, the steps above the chart also stop for a person. These steps are the specification, the
storyboard and the event model. The `upstream` setting makes them advance on their own instead.
[The workflow](the-workflow.md#the-upstream-setting) describes it.

## Careen and stow

These two words name where unfinished work goes. Work is never dropped.

- **Stow** is what a stage does with open work when it runs out of budget. It moves the work into the
  careen. A finding below the fairway's severity bar is also stowed, and the slice merges. A CRITICAL
  finding is never stowed.
- **The careen** is one hardening slice for each fairway. It holds the stowed work. It runs when the
  fairway's planned slices are done, and before the fairway's flag is hoisted. It runs the ladder like any
  other slice. Its demo is: the findings are closed. `/careen`, in the agent, runs it.

The careen may not stow. A stage inside the careen that runs out of budget parks for a person instead.

## What this looks like when it is working

![The bridge: what is waiting on a person, the streams, the speed](../captures/bridge.png)

This shows two streams, one question that waits, the lever at half-ahead, and the run reporting on itself
one line at a time. You answer the top block and leave the rest alone.

## Next

→ **[Bring an existing codebase](adopt.md)**: use this page if the product that you want to work on
already exists.

Other pages: [start here](start-here.md) · [your first feature](first-feature.md) ·
[a second person joins](a-second-person.md) · [the workflow](the-workflow.md) · [the board](the-board.md) ·
[the vocabulary](../../GLOSSARY.md)
