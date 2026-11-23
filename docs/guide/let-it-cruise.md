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

There is one captain for each fairway. A captain is two things: **the captain program**, which always runs,
and, where the harness allows it, **the captain agent** on top of it. The agent chooses; the program checks
and does.

### The captain program

On each turn, the program does these things:

1. It fetches trunk and both logs.
2. It works out its own state from its own `claimed` and `merged` lines.
3. It picks the next slice that clearance allows, or, where there is a captain agent and a choice to make,
   starts the cleared slice the agent ordered.
4. It writes `claimed`.
5. It runs `/sail` in that slice's berth, through the slice's driver: one session held open over the Agent
   Client Protocol where the `sessions` setting and the harness allow it, the harness's print mode elsewhere.
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

**No slice runs without limit.** The program writes a `dispatched` line for each run of `/sail` it starts for
a slice. Between two things a person says to that slice, it runs at most `2 × attempts + 1` runs that cost an
attempt — five at the default two — whoever asks for them, across restarts and cleared parks. Then the slice
parks for a person. A run you asked for, by a message or an interrupt, costs no attempt.

### The captain agent

The agent is one coding-agent session for the stream, held open over the Agent Client Protocol. The program
wakes it with an **event** when there is a choice to make, and nothing else wakes it. The agent's choices are:

- which cleared slice starts next, when more could start than there are free slots;
- after a slice misses its gate, whether it runs again and with what note, or parks and why;
- what to do about a stuck slice — taking long, going in circles, or gone quiet: send it a message, interrupt
  it, pause or stop it, park it, or tell you;
- where something said to the whole stream goes: to which slice, or answered itself;
- whether a slice's session may touch something outside its berth. It may allow a read inside the project,
  and nothing else.

It acts only by giving orders through the project's own `scripts/agents/orders.py`. The program checks each
order against the rules as they are when it carries the order out — clearance, the free slots, the attempts
left, a person's hold, the merge — does it or refuses it, and writes why. Clearance, the session slots, the
stage budgets, the retry ceiling, the gate, merge requests, the ceiling on unreviewed decisions and the deck
log stay the program's. The agent writes no line and edits no file.

**The program never waits on it.** Where the agent says nothing within its bound (60 seconds by default),
orders something it may not, or cannot be run, the program makes that one choice by the fixed rule it has
always used, says so, and asks the agent again at the next event. If the agent's own machinery fails, the
stream runs on the program alone until the captain is next started, and the deck log gets one `noted` line
saying so. Nothing waits on a `noted` line: it is news for you, not a question.

**It does not answer product questions.** A question a slice's session asks mid-turn is declined, as it was
before there was an agent, and goes down the deck log's `question` path: to the skipper under `/cruise`, to
you otherwise, as the **Who answers** settings say. The skipper is unchanged. A project can let the captain
answer by setting `answers` to `true`; then every answer it gives is written as a `decision` by the captain for
you to review. The program cannot tell an operational question from a product one by its words, and under
`/cruise` nothing else bounds what it answers. That is why it is off.

**Only over the Agent Client Protocol.** Over the protocol the agent's session is confined to reading and
running `orders.py`. A captain run headless, with a shell of its own, could not be confined, so there is no
such captain. Where the project's harness has no launch over the protocol that the registry marks proven, or
this machine cannot make it, the stream runs on the program alone, exactly as before, and says so once on the
captain's output: *no captain agent: this harness has no proven protocol launch*.

**What it costs.** Each event is one turn of the project's harness. `per_hour` (30 by default) is the most
times a stream's captain is woken in an hour; past it, the stream runs on its rules alone until the hour has
passed.

### Turning the captain agent on

A newly generated project has it on: its `harbour.json` carries

```json
"captain": {"agent": true, "bound": 60, "answers": false}
```

An existing project is not switched by `slipwai migrate`. To turn the agent on there, migrate first, so the
project has the new `scripts/agents/`, then add that `captain` block to `harbour.json` and cast the fleet off
again. It runs only where the project's harness has a proven launch over the Agent Client Protocol. Set
`SLIPWAI_CAPTAIN=off` in the fleet's environment to turn it off whatever the file says, or
`SLIPWAI_CAPTAIN=1` to turn it on through the project's own harness.

The slices' own sessions are a separate setting: `sessions` in `.specify/cruise.json`, on the board's **Who
answers** tab as *A captain's session*. A new project is written with `auto`: over the protocol where the
harness's launch is proven, print mode elsewhere. An existing project stays in print mode until you choose
`auto` there, or run `python3 scripts/agents/cruise.py --set sessions=auto`.

## The harbourmaster

There is one harbourmaster for each **machine**. It writes its own harbour log,
`.slipwai/run/logs/harbour/<machine>.jsonl`. It reads the harbour logs of every machine, and combines them into
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

There are two places to say something: to one slice, or to a stream's captain.

**To one slice.** Open the slice's window from its card (**Open its window**), or use the one-line box on the
opened card. Choose for each message:

- **Send** waits for the turn under way to end, and the message is the next prompt. This is the default.
- **Interrupt** cancels the turn and delivers the message at once. A turn cancelled for your message costs the
  slice no attempt. A slice in print mode has no Interrupt; its messages go in with its next run.

Each message shows its receipt: *queued* (you can still withdraw it), *held* while the slice is at its merge,
*delivered* at the time the slice's driver records, *answered* with the reply under it, *delivered, not
addressed* where the turn ended without a word about it, or *not delivered* with why and **Send again**.

**Pause**, **Resume** and **Stop** are in the same window. Pause lets the turn finish, keeps the session and
gives the slot back. Stop ends the session now and puts the slice back in the queue; its commits stay on its
branch and its uncommitted edits stay in its berth. A pause or stop you make holds the slice until you resume
it, whatever anyone else does meanwhile. A slice you paused is listed under *When you have time*.

**To a stream.** The captains strip above the tabs has a button for each stream's captain, which opens its
window and its conversation. **Tell every captain** puts one message in every captain's inbox; each captain
works out which of its slices it is for, sends it on, and reports back. Where a stream's captain is the
program alone, it reads what you said at its next turn and writes it into the stream's log; it routes nothing.

**Ask about this project**, beside them, opens a console that reads the run's logs and answers questions. It
never acts. Something you want done, say to a captain or a slice.

From the agent:

```text
/cruise-tell booking the hold should expire after 15 minutes, not 45
```

The first word is the stream, and the rest is the message. `/cruise-tell` refuses a message with no stream,
and lists the streams that there are. `--everyone` as the first word sends the message to every stream.
`/cruise-tell` writes the message as a `told` line in the fairway's deck log. When the captain has read it, it
writes a `read` line with the timestamp of the message that it answers. This makes the `read` line a receipt,
not just a claim that somebody looked.

**A message to a parked fairway clears the park.** The park is cleared by a `told` line in the fairway's deck
log after it. `/cruise-tell` writes that line itself. The board places your answer in the parked slice's
inbox instead, and its captain writes the `told` line when it next runs; the row on the board says whether that
has happened. On its next pass, the harbourmaster writes a `cleared` receipt in the harbour log for each open
park that the message came after. It keeps the message as the answer. On the pass after that, it starts the
captain again.

**The harbourmaster does not start a captain for a parked fairway.** That captain would read the park and
exit at once. The fairway waits until a person clears the park. The one exception is a message waiting for
the captain: the harbourmaster lights the captain so that it can read it.

## A board older than the log

The deck log gained two kinds with the captain agent: `dispatched` and `noted`. A reader that meets a kind it
does not have refuses the line rather than skip it, because a board folded from a log with holes in it is
wrong and looks certain. So a board from before this release, opened on a project whose fleet has run since,
says it cannot read that stream's log, names the line it stopped at, and shows nothing more of that stream. Nothing is
lost: the lines are all there for a newer board. Update the app.

An app that checks its release against the project's says so before that: if the project was written by a
newer slipwai, every page says the app is older, and the app changes nothing until you update it.

## What still stops for a person

1. **Mock-up approval.** Before the work is given types, every surface state is approved, parked with the
   question that it waits on, or marked `n/a` with a reason. A surface that nobody has seen becomes a read
   model, a route and a set of tests. All three cost more to change than a drawing.
2. **The demo, if you ask for it.** Acceptance is recorded against a **capability**, not a slice. By
   default the hand's verdict is the acceptance, and its film is on the board for you to comment on. Set
   `demos` to `person` in `.specify/cruise.json`, and a person accepts each capability instead.
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
  careen. A finding below the fairway's severity bar is also stowed, and the slice merges. The bar is
  `MEDIUM` unless a person sets it with `slipwai telegraph --set bar=…`; ringing a speed never moves it. A
  finding that leaves a feature unusable or untrustworthy for its actor is never stowed, whatever the bar:
  a CRITICAL, a validation bypass on a state-changing route, a forgery in a generated document, personal
  data that survives an erasure, or wrong arithmetic in a money figure.
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
