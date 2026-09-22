# Cruise: `/drive` with nobody at the wheel

`/drive` takes one slice from wherever it stands to a demo, and stops when it needs a person: for a product
decision, for an input nobody has given it, when the split has no ready slice left, and at every demo.
`/cruise` runs the same ladder, and answers the first and last of those stops itself: it decides as the
product owner, and it runs each demo as the actor. It keeps going, iteration after iteration, until the
specification is satisfied, and it stops only for a human.

Nothing about what a stage produces changes. What changes is who answers.

- [What it guarantees](#what-it-guarantees)
- [Three roles and two loops](#three-roles-and-two-loops)
- [What it does at each stop](#what-it-does-at-each-stop)
- [Where it keeps its answers](#where-it-keeps-its-answers)
- [Start a run, watch it, stop it](#start-a-run-watch-it-stop-it)
- [The settings](#the-settings)
- [What a person reviews afterwards](#what-a-person-reviews-afterwards)
- [The browser](#the-browser)
- [When it is blocked](#when-it-is-blocked)
- [How an iteration is held to its end](#how-an-iteration-is-held-to-its-end)
- [The limits](#the-limits)

## What it guarantees

1. **It stops only for a human.** A stop file, Ctrl-C, or a person typing into the session ends a run. A
   finished slice, a demo, a product question, a stale checkout or a full context does not.
2. **It writes every answer down twice.** Each answer goes where `/drive` would have written a person's
   answer, and again into one log per feature. A person can read every decision the machine took in one
   place, and can overturn any of them.
3. **It never invents an input, and it does not stop for one either.** A product *decision* is the owner's
   to make, and the machine makes it. A *fact* it does not have, such as a credential or a third party's
   behaviour, is never invented: the slice is marked blocked, the run takes the next ready slice, and a
   strong delegate, the bosun, works around the block. It puts a fake behind the port, recorded as a fake,
   or takes the narrower reading that keeps every rule, and writes down what it did. The run parks only for
   something catastrophic, or when the bosun could not move it.
4. **Done means the specification is satisfied.** When the split runs out, the last stage audits the
   specification against what shipped. Each finding becomes a new slice, or a recorded decision that it is
   out of scope. Only an audit with nothing left ends the run.
5. **The board is honest.** A slice the machine accepted says so. A person can see at a glance which demos
   a person has seen.
6. **An iteration ends only on one of its four last lines.** A message that says what it is about to do
   next is a stop, whatever it says, and where the harness has a hook that can refuse it, the project's hook
   file does. An iteration is only ever a session the runner started: typed in a session, `/cruise` starts
   the runner and ends, on every harness, so nothing depends on what a session does with its last line.

## Three roles and two loops

```text
outer loop — scripts/agents/cruise.py run: make cruise from a terminal, or what a typed /cruise starts (detached)
  a fresh harness session per iteration, through any CLI harness on PATH · the stop file · a stuck detector
  · parks when blocked · a log
  │
  └─ one iteration — /cruise
       driver: runs commands/drive.md as written, stage by stage, delegating as it does
         ├─ a product question ──▶ skipper: the host, or drive-skipper when the question is open
         │                          answer → the artifact, and specs/<feature>/decisions.md
         └─ the demo stop ────────▶ hand: drive-hand, with a browser where the slice has a screen
                                    verdict → demo-log.md, the benchmark outcome, back into the ladder
       ends with one line: cruise: continue | done | parked: <why> | stopped: human
       (held to that, where the harness has a stop hook: python3 scripts/agents/cruise.py stopping)
```

**The driver** is the session that runs `/cruise`. It runs `commands/drive.md` itself, not a copy of it, so
every rule of the ladder holds: fresh-context delegation, claims, the shared-surface rule, merges in split
order, the benchmark bracket. `/cruise` adds only the stop table, the two protocols below, the completion
audit and the iteration contract.

**The skipper** answers product questions. The driver answers on the host when the stage itself recommends
an answer, when a standing decision already covers the question, or when the specification or the
constitution answers it. Any other question is open. An open question goes to a fresh `drive-skipper`
delegate, with the number its entry will carry: the driver allocates `D<n>` before dispatch, one per
delegate in dispatch order, so several deciding at once never come back with the same one. That delegate
reads the specification, the constitution, the owner brief and the decision log, and then decides. It
states its confidence and the one condition that would reverse the decision. It does not defer, and it
writes nothing: it returns the whole entry, the driver appends it in number order and writes the decision
into the artifact. Every other identifier a decision adds — a requirement, a criterion, an example — is the
driver's to number after the delegates return, for the same reason. `skipper` is a role of its own in `.specify/models.json`, so a project can run a bigger model on
deciding than on driving: `/model-delegation-settings claude.skipper=opus`.

**The hand** runs the demo. A fresh `drive-hand` delegate takes exactly what the demo stop hands a person:
the board, the command or URL to run, the seed data, the expected result. It also takes the acceptance
script: the slice's `examples.md`, or its acceptance criteria in `spec.md`. It walks every example as the
actor would. It gives its verdict in the three words the benchmark already knows: `accepted`, `behaviour`
or `implementation`. The driver then re-enters the ladder at the stage that owns the change, exactly as
`commands/drive.md` says demo feedback does.

**The inner loop** is one `/cruise` invocation. It spends its context on one unit of work. Before the split
exists, the unit is the upstream stages together: principles, the specification, the event model where there
is one, and the split, through to the first ready set. From the split on, it is one slice through its
hardening, or one concurrent fan-out through its merges. Then it ends with one machine-readable line.
**The outer loop** is a script. It runs the harness headless with a fresh context, reads that last line, and
runs again until the line says `done` or a human stops it. Both loops are needed. `/drive` derives every
stage from artifacts on disk, which is what lets a fresh session resume correctly, and no single context
lasts a whole product.

## What it does at each stop

The table below is the one a generated project carries in `commands/cruise.md`, for the event profile with a
production target. A `standard` project reads its criteria from `spec.md` instead of `examples.md`. A project
with no production target has no release rows. An adopted repository has three more rows; see
[The limits](#the-limits).

| # | Where `/drive` stops | What `/cruise` does there | Recorded in |
|---|---|---|---|
| 1 | The checkout is behind trunk, or the fetch failed | Fetch and fast-forward where the tree is clean. Rebase a `slice/<id>` branch that has local commits. A conflict parks. A fetch that cannot run parks and says so. | `specs/cruise-log.jsonl` |
| 2 | The constitution is not ratified | With `constitution: ratify`, the skipper drafts it with `/speckit-constitution` from the spec and the owner brief, answers `/constitution-coverage`, and ratifies it with the line `ratified by cruise (skipper) — pending human review`. With `park`, the run stops here. | `constitution.md`, a decision entry |
| 3 | There is no product specification | Refuse to start. A specification is the one thing a person brings. | — |
| 4 | Which service or bounded context owns a slice | Decide against each service's recorded `purpose`. Where none covers it, record the purpose the spec implies with `slipwai describe-service <name> --purpose`, then decide. Contexts are recorded the same way, with `--context`. | the model or plan, `project.json`, a decision entry |
| 5 | Slice gaps: one question at a time | The gaps loop runs with the owner as the other party. Each gap is answered, by the host or the skipper, and written back as the criterion or state. | `examples.md`, a decision entry per question |
| 6 | The release constraint | Take the stage's own recommendation. With `release: flagged`, every slice continues or opens a flag seeded `off`, so every merge is dark and a person flips the keys. With `park`, the run stops at the push. | `plan.md`, the flag file, a decision entry |
| 7 | "A release they want now": no flag, or a flag already on, before the push | Never answered by the machine. Under `flagged` it does not arise. Where it does, park with the exact question. | a `parked` line in the log |
| 8 | A delegate hands back a product question in `plan.md` | Answer it, un-block the slice, and re-dispatch the delegate with the entry as a pointer, never as a conclusion. | `plan.md`, a decision entry |
| 9 | Converge appended tasks and the `/gaps` pass says stop | Already bounded by the ladder. Continue to the demo. | — |
| 10 | The demo stop | Delegate to `drive-hand` with what the stop hands a person, plus the acceptance script. Take its verdict as the actor's. Acceptance is marked `accepted-by: drive-hand`. | `demo-log.md`, the benchmark `outcome=`, the register |
| 11 | The ready set is empty | Not a stop. Run the completion audit. Only an audit with nothing left is `done`. | `specs/<feature>/cruise-report.md`, decision entries |
| 12 | An input nobody has: a credential, an external system, a person's approval | Never decided. Record it as blocked with what is needed. Take the next ready slice. Park only when nothing can move. | a `parked` line in the log, ⛔ on the board |

**The completion audit** runs where `/drive` would say the split is exhausted. `/gaps` runs over the whole of
`spec.md` against what shipped, one `drive-gaps` delegate per feature area. Each finding goes to the skipper:
a criterion nothing built becomes a slice, appended to the split with `/story-splitting`; a finding the
owner rules out of scope becomes a decision entry that says so. The report lists what the specification
asked, what shipped, every out-of-scope decision, and every decision a person has not yet reviewed.

## Where it keeps its answers

`/drive` reads artifacts, not memory, and `/cruise` keeps that rule. Nothing a run needs to resume lives
only in a context window. Four things are added to a project.

| File | Holds | Who writes it |
|---|---|---|
| `specs/<feature>/decisions.md` | The decision log: one numbered entry per product answer, with the question, the options, the decision, the reason, who decided (the host, `drive-skipper` with its model, or a human), the confidence, the condition that would reverse it, the artifacts it was written into, and its status. Append-only, numbered by the driver before a delegate decides. | the driver; the skipper returns its entry and the driver appends it; a person overrides an entry by editing its status |
| `.specify/product-owner.md` | The owner brief: who the actor is, what the product is for, priorities, tie-breakers, taste, what is out of scope. The skipper reads it before every decision. Edit it to steer a run without stopping it. | a person |
| `specs/<feature>/slices/<id>/demo-log.md` and `demo/` | One section per demo: what was started and how, each example walked and what happened, the verdict, the feedback, and the screenshots and responses under `demo/`. | `drive-hand` |
| `specs/cruise-log.jsonl` and `specs/<feature>/cruise-report.md` | The outer loop's record, one line per iteration, and the completion audit's report. | the runner and the driver |

The benchmark record gains `driver=cruise` on every stage a run bracketed, and `skipper`, `hand` and `bosun` are
stages of their own, so `make benchmark` can say what a decision cost and what a demo cost.

## Start a run, watch it, stop it

A project ships with `/cruise` disabled. To start, in any harness's session:

```sh
/cruise-settings enabled=true     # commits .specify/cruise.json
/cruise                           # starts the runner, detached from this session, and reports
```

or from a terminal, `make cruise`, which runs the same loop in the foreground. Either way the runner is the
one thing that continues a run: `python3 scripts/agents/cruise.py run` starts one fresh headless session per
iteration, reads its last line, and runs again until the line says `done`. A parked run waits, and re-checks
every `poll_minutes` for a reason to resume: the stop file, or an artifact a person changed.

A `/cruise` typed into a session never runs the ladder itself. The command asks `python3
scripts/agents/cruise.py loop` who is reading its last line; where nobody is, it runs `python3
scripts/agents/cruise.py start`, repeats what that printed, and ends the turn. `start` checks everything that
can refuse before it detaches — the settings, the stop file, a runner already running, no harness on the PATH
it can run an iteration through — so the refusal is what you read. The runner then writes to
`.specify/cruise-run.log`, keeps its pid in `.specify/cruise.pid`, and `make cruise-status` says whether it
is running and what the log shows. This is the same on every harness, because it needs nothing of the
session beyond a shell.

Which harness the runner drives is `scripts/agents/registry.json`'s business, under `headless`: for each
harness, how it runs one prompt non-interactively and exits, read from its own documentation on the date the
row names — 27 of the 36 have a row; the nine that do not say why, editor-only or unreachable docs. The runner
takes the first installed harness with a row whose binary is on the PATH, and otherwise any harness in the
registry whose binary is, so a `/cruise` typed into Zed or Antigravity runs through whichever CLI harness the
machine has, and the log names which. Only Claude Code's print mode is known to resolve `/cruise` itself;
every other harness is asked, in the same words, to read `commands/cruise.md` and follow it.
`CRUISE_HARNESS_COMMAND`, a shell template with `{prompt}`, overrides the choice.

To stop a run, do one of these. Each is safe in the middle of a slice, because the slice's commits are on
its branch and the next iteration re-derives its stage from the artifacts.

- Run `make cruise-stop`, or `touch .specify/cruise.stop`. The runner ends after the iteration in flight, and
  the command checks between stages, finishes the stage's own writes, commits what is green, and ends.
  `make cruise-stop CRUISE_FLAGS=--now` ends the iteration in flight too.
- Press Ctrl-C on a foreground runner. The harness session dies with it.

## The settings

`.specify/cruise.json` holds them. `/cruise-settings key=value` changes them, checked, and a change takes
effect at the next iteration. `make check-agents` holds the file's shape.

| Setting | Values | Default | Controls |
|---|---|---|---|
| `enabled` | `true`, `false` | `false` | whether `/cruise` runs at all |
| `decide` | `recommended-first`, `skipper-always` | `recommended-first` | who answers a product question: the host where the stage recommends an answer or a standing decision covers it, and `drive-skipper` otherwise; or `drive-skipper` for every question |
| `release` | `flagged`, `park` | `flagged` | the release-constraint stage: every slice behind a flag seeded off, so every merge is dark; or park at the push and let a person decide |
| `constitution` | `ratify`, `park` | `ratify` | an unratified constitution: the skipper drafts and ratifies it, marked pending human review; or park |
| `hand` | `browser`, `http`, `cli` | `browser` | the top of the hand's ladder for a demo; each falls through to the next where it cannot run |
| `unblock` | `bosun`, `park` | `bosun` | what a block becomes: work for the bosun first, a park only at the catastrophic or when it fails; or a park at once |
| `stuck_after` | a whole number | `3` | iterations with no artifact change before the loop parks |
| `max_iterations` | a whole number or `null` | `null` | a budget on iterations; `null` is unbounded |
| `max_hours` | a whole number or `null` | `null` | a budget on wall time; `null` is unbounded |
| `poll_minutes` | a whole number | `10` | how often a parked loop looks for a reason to resume |

## What a person reviews afterwards

Read these, in this order.

1. `specs/<feature>/cruise-report.md`: what shipped, what was ruled out of scope, and every decision not yet
   reviewed.
2. `specs/<feature>/decisions.md`: every decision, with its reason. To overturn one, change its `Status` and
   write the answer you want into the artifact it names. The next iteration re-enters the ladder from that
   artifact.
3. Each slice's `demo-log.md` and `demo/`: the evidence behind every `accepted-by: drive-hand`.
4. The constitution, if the run ratified it: the line `pending human review` is yours to remove.
5. The flags: nothing the run merged is visible to a real actor until you turn a key on.

## The browser

Where a slice has a screen, the hand drives it through a browser. It uses Vercel Labs'
[`agent-browser`](https://github.com/vercel-labs/agent-browser) first. This is a command-line tool, so it
runs from the shell on every harness, and every snapshot and screenshot it takes is a file that goes under
`demo/`. The hand installs it on demand, the way the run skill installs Playwright:

```sh
npm install -g agent-browser && agent-browser install
```

It finds an installed Playwright or Chrome before it downloads one. `agent-browser snapshot` returns an
accessibility tree with references, and the hand clicks and fills by reference. `--allowed-domains` fences
it to the addresses the run skill names. Where the tool cannot be installed, the hand uses a browser tool the
harness exposes. Where there is none, it drives the API over HTTP and records that the screen was judged
from its API alone. `agent-browser` is never a dependency of the project.

## When the context is compacted

A harness can shorten a long context at any point. Claude Code calls this compaction; Gemini CLI calls it
compression. A summary loses the state that no file carries: which delegates are out and with what
manifest, a question that is half answered, which slice's demo comes next.

`/cruise` keeps that state in one small file, `specs/cruise-checkpoint.md`. It rewrites the file at every
stage boundary and at every delegation. At the start of every stage, and whenever its context looks
summarised, it reads the file before it acts. `python3 scripts/agents/cruise.py resume` prints the
checkpoint with the rules beside it, and prints nothing when no iteration is in flight. The file is run
state, not a record: it is ignored by git, and the runner deletes it when an iteration ends with `done` or
`stopped`.

Where a harness can run a command after compaction, the project's settings replay the checkpoint for you.
On Claude Code, `.claude/settings.json` runs `resume` on the `SessionStart` hook with the `compact` matcher,
and stamps the checkpoint on `PreCompact`. Both commands print nothing unless an iteration is in flight, so a
plain `/drive` session never sees them. `scripts/agents/registry.json` records under `compaction` what each
harness can do, read from its documentation on a named date: Gemini CLI has a `PreCompress` event but nothing
that adds context afterwards, and the rest are `null` until someone checks. On those harnesses the checkpoint
still works; only the automatic replay is missing, and the command's rule to re-read the file covers it.

## How an iteration is held to its end

Prose in a command file is not a control. One session ended an iteration after the upstream stages, because
the contract named no unit before the split; the same session later ended a turn on a report that said
"continuing into the plan now", which in Claude Code is the end of the turn whatever the sentence says.
`make verify` was green both times, and the checkpoint correctly said an iteration was in flight, and nothing
read it. So the end of a turn is checked where the harness lets a hook refuse it.

The control is the runner. It marks every session it starts (`CRUISE_RUNNER`, `CRUISE_ITERATION`), reads
the last line, and treats an iteration that ended without one as no progress, which the stuck detector then
counts. A typed `/cruise` starts the runner rather than running an iteration, so there is no session whose
last line matters and nobody is reading.

The hook is the seatbelt inside a runner's iteration, where a harness has one. `python3
scripts/agents/cruise.py stopping` runs from the project's hook file: `.claude/settings.json` on Claude
Code's `Stop`, `.cursor/hooks.json` on Cursor's `stop`, `.gemini/settings.json` on Gemini CLI's `AfterAgent`.
In a session the runner started, while `specs/cruise-checkpoint.md` says an iteration is in flight and
`.specify/cruise.stop` is absent, it refuses a turn whose last message does not end on one of the four last
lines, spelled the way that harness reads a refusal — a block decision, or Cursor's follow-up message — with
the checkpoint's own `Next:` line as the reason. Every hold is stamped on the checkpoint, and the hook lets go
after three holds against a checkpoint nothing rewrote, so a session that cannot move is not held forever:
rewriting the checkpoint at every stage boundary, which the command already requires, is what keeps a turn
holdable. A turn that ends on `done` or `stopped` takes the checkpoint with it. Cursor's stop event carries no
text, so its `afterAgentResponse` hook keeps the last message for it (`cruise.py responded`); an event that
carries no message and no kept one is no evidence, and the hook does not hold on none. Outside a runner's
iteration the hook does nothing, so a plain `/drive` session, and a typed `/cruise`, never meet it.

`scripts/agents/registry.json` records under `hooks`, for every harness, whether it has a hook that fires
when a turn ends and can refuse the end, how, and the projection `scripts/agents/project.py` writes — merged
into a file a person may keep other keys in, and held to by `make check-agents`. Where the file's shape was
not read, or a harness's hook cannot continue the agent, the row says so and the runner's own reading of the
last line is what holds.

## When it is blocked

A block is work before it is a stop. When the run meets an input nobody has, a question whose every option
seems to break a constitution rule, a checkout that will not rebase, or an iteration that made no progress,
it marks the slice blocked, takes the next ready slice, and hands the block to a third delegate,
`drive-bosun`, on the skipper's model role. The bosun takes the least surprising way round, in this order:

1. **Stub the world.** The code is a hexagon, so a fake adapter goes behind the port the missing thing sits
   behind, chosen by configuration and seeded with what the examples need. The plan records it as a
   deliberate stub, so the progress board shows it under *Not working yet*. A stub is always recorded as a
   stub, never as a fact about the real system.
2. **Narrow the reading.** Where every option seems to break a rule, it takes the reading that keeps every
   rule and defers the rest behind the slice's flag. The amendment a person may want becomes an ADR at
   `Proposed`, never ratified by the machine. In an adopted repository a fact the tree cannot say stays
   `unrecorded` or `detected`: the bosun works on the survey's value as a stated assumption and never marks
   it `confirmed`.
3. **Repair the run.** Rebase and resolve, finish or revert what a dead delegate left, find why a gate
   loops.

Every move is an entry in `decisions.md` with `Decided by: drive-bosun`, the condition under which a person
should undo it, and a task in the next slice to remove the stub when the real thing arrives. Nothing done to
get moving is done silently. When the outer loop sees no progress for `stuck_after` iterations, it gives the
bosun one iteration before it parks, and the log marks that iteration `attempt: unblock`.

**What always parks.** The bosun refuses, and the run parks, at anything on this list: destroying data or
history; releasing what a person has not asked for, such as turning a flag on or deploying to production;
spending money or exposing a secret; weakening security; discarding a person's commits to make a checkout
consistent. It also parks when the bosun could not move the block. `unblock: park` switches the bosun off
and parks at once.

## The limits

- **Adopted repositories run on stated assumptions.** The Ground stage asks facts about the world, such
  as the release path of code the factory did not write. A fact is not a decision, so a row stays
  `unrecorded` and the bosun works on the survey's value as an assumption it names. The change-strategy ADR
  proceeds at `Proposed`; only a person writes `Accepted`. A person confirms or overturns both afterwards.
- **Facts are never invented.** See guarantee 3.
- **Flags stay off.** Under `release: flagged`, turning a flag on is never a decision the log can contain.
- **The constitution's MUSTs are the floor.** No decision waives one. A question whose every option breaks
  one goes to the bosun for the reading that keeps them all, and parks only if there is none.
- **The hand edits no code.** A defect it finds is a task. A fix there would make the verdict evidence for
  itself.
- **Unattended permissions need a sandbox.** The headless call runs with the permissions the registry row
  names for a normal run — edits accepted, the rest the harness's own to grant or refuse. Bypassing them all
  is allowed only with the runner's `--sandbox` flag, and the runner says why. Run an unattended loop inside
  a container or sandbox.
- **A run that loops is detected.** `stuck_after` iterations with the same artifact fingerprint give the
  bosun one iteration, then park the loop; the same open question raised twice in one iteration goes the
  same way.

The ladder `/cruise` runs, its stages, the models table and the benchmark are all described in
[The delivery loop](delivery-loop.md).
