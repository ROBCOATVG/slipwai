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

## Three roles and two loops

```text
outer loop — make cruise (scripts/agents/cruise.py run)
  a fresh harness session per iteration · the stop file · a stuck detector · parks when blocked · a log
  │
  └─ one iteration — /cruise
       driver: runs commands/drive.md as written, stage by stage, delegating as it does
         ├─ a product question ──▶ skipper: the host, or drive-skipper when the question is open
         │                          answer → the artifact, and specs/<feature>/decisions.md
         └─ the demo stop ────────▶ hand: drive-hand, with a browser where the slice has a screen
                                    verdict → demo-log.md, the benchmark outcome, back into the ladder
       ends with one line: cruise: continue | done | parked: <why> | stopped: human
```

**The driver** is the session that runs `/cruise`. It runs `commands/drive.md` itself, not a copy of it, so
every rule of the ladder holds: fresh-context delegation, claims, the shared-surface rule, merges in split
order, the benchmark bracket. `/cruise` adds only the stop table, the two protocols below, the completion
audit and the iteration contract.

**The skipper** answers product questions. The driver answers on the host when the stage itself recommends
an answer, when a standing decision already covers the question, or when the specification or the
constitution answers it. Any other question is open. An open question goes to a fresh `drive-skipper`
delegate. That delegate reads the specification, the constitution, the owner brief and the decision log,
and then decides. It states its confidence and the one condition that would reverse the decision. It does
not defer. `skipper` is a role of its own in `.specify/models.json`, so a project can run a bigger model on
deciding than on driving: `/model-delegation-settings claude.skipper=opus`.

**The hand** runs the demo. A fresh `drive-hand` delegate takes exactly what the demo stop hands a person:
the board, the command or URL to run, the seed data, the expected result. It also takes the acceptance
script: the slice's `examples.md`, or its acceptance criteria in `spec.md`. It walks every example as the
actor would. It gives its verdict in the three words the benchmark already knows: `accepted`, `behaviour`
or `implementation`. The driver then re-enters the ladder at the stage that owns the change, exactly as
`commands/drive.md` says demo feedback does.

**The inner loop** is one `/cruise` invocation. It spends its context on one unit of work: one slice through
its hardening, or one concurrent fan-out through its merges. Then it ends with one machine-readable line.
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
| 4 | Which service or bounded context owns a slice | Decide against each service's recorded `purpose`. Where none covers it, write the purpose the spec implies, then decide. | the model or plan, `project.json`, a decision entry |
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
| `specs/<feature>/decisions.md` | The decision log: one numbered entry per product answer, with the question, the options, the decision, the reason, who decided (the host, `drive-skipper` with its model, or a human), the confidence, the condition that would reverse it, the artifacts it was written into, and its status. Append-only. | the driver and the skipper; a person overrides an entry by editing its status |
| `.specify/product-owner.md` | The owner brief: who the actor is, what the product is for, priorities, tie-breakers, taste, what is out of scope. The skipper reads it before every decision. Edit it to steer a run without stopping it. | a person |
| `specs/<feature>/slices/<id>/demo-log.md` and `demo/` | One section per demo: what was started and how, each example walked and what happened, the verdict, the feedback, and the screenshots and responses under `demo/`. | `drive-hand` |
| `specs/cruise-log.jsonl` and `specs/<feature>/cruise-report.md` | The outer loop's record, one line per iteration, and the completion audit's report. | the runner and the driver |

The benchmark record gains `driver=cruise` on every stage a run bracketed, and `skipper`, `hand` and `bosun` are
stages of their own, so `make benchmark` can say what a decision cost and what a demo cost.

## Start a run, watch it, stop it

A project ships with `/cruise` disabled. To start:

```sh
/cruise-settings enabled=true     # in an agent session; commits .specify/cruise.json
make cruise                       # the outer loop: python3 scripts/agents/cruise.py run
```

`make cruise` runs the installed harness headless, one fresh session per iteration, until the last line says
`done`. A parked run waits, and re-checks every `poll_minutes` for a reason to resume: the stop file, or an
artifact a person changed. `make cruise-status` prints the log's tail.

To watch a run inside a Claude Code session instead, type `/loop /cruise`. The session's own timer re-runs
the command. The context is summarised rather than fresh, so this is the way to watch, not the way to run
unattended.

To stop a run, do one of three things. Each is safe in the middle of a slice, because the slice's commits
are on its branch and the next iteration re-derives its stage from the artifacts.

- Run `touch .specify/cruise.stop`. The runner checks between iterations. The command checks between stages,
  finishes the stage's own writes, commits what is green, and ends.
- Press Ctrl-C on the runner. The harness session dies with it.
- Type into an interactive session.

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
- **Unattended permissions need a sandbox.** The headless call runs with `acceptEdits` by default. Bypassing
  permissions is allowed only with the runner's `--sandbox` flag, and the runner says why. Run an unattended
  loop inside a container or sandbox.
- **A run that loops is detected.** `stuck_after` iterations with the same artifact fingerprint give the
  bosun one iteration, then park the loop; the same open question raised twice in one iteration goes the
  same way.

The ladder `/cruise` runs, its stages, the models table and the benchmark are all described in
[The delivery loop](delivery-loop.md).
