---
description: Cast off — start a captain per stream to run /sail as driver and product owner until every specification is satisfied — and watch
argument-hint: [--boilers <n>] | unblock: <what a captain saw>
---

# Cruise

`/sail` takes one slice from wherever it stands to an actor-visible demo and stops for a product decision, an
unavailable input, an exhausted split and the demo. This command runs **that ladder — `commands/sail.md`,
every rule as written** — with nobody at the wheel: it decides what the ladder would have asked a person,
runs each demo as the actor, and re-enters the ladder until the specification under `specs/<feature>/` is
satisfied. Nothing about what a stage produces changes; what changes is who answers.

**Typed, this casts off and watches.** `python3 {{fleet}} start` starts the harbourmaster and one captain per
stream the chart names, under the telegraph's `boilers`, and exits — nothing is left holding the state of the
run. Each captain claims a slice, makes its berth, dispatches `/sail` for it, and reads the deck log to know
how it went. **Dispatched, this file is the rules**: a `/sail` session a captain started reads everything
below *The watch seat* and answers at the ladder's stops by it.

<!-- section: adopted -->
This repository adopted the method around code that was already there, and two of its stops are a person's word — the rows at the foot of the table. A run here proceeds on stated assumptions and `Proposed` records rather than parking, and a person confirms or overturns them afterwards.

<!-- end section -->
## Before anything: refuse, or cast off

Read `{{config}}`. `enabled: false` is a refusal in one line that says so. No `specs/<feature>/spec.md` is a
refusal too: a specification is the one thing a person brings, and the chart is drawn from it.

Then: **in a session a person typed this in**, run `python3 {{fleet}} start`, pass `--boilers <n>` through where
they gave one, and repeat what it printed — which streams were lit, which are waiting for a berth, and which
were already going. A refusal is the whole answer: the telegraph at `stop` lights nothing and says so, and a
chart with no streams is a chart nobody has split yet. Then take the watch seat (below), and **run no stage of
the ladder in this session**: the captains are doing that, each in its own berth, and a stage run here would
be a second writer in a tree one of them holds.

**In a session a captain dispatched**, this is a stage of the ladder. The captain says which in the
environment — the stream, the slice and the instant the session opened — so read the owner brief
(`{{owner-brief}}`), every standing entry in `{{decisions}}`, and that stream's own last lines
(`python3 {{inbox}} <stream>`), and say the slice, the branch and its distance from trunk. Where this
project has adopted a code index, a caller or blast-radius question is one call to it, by a route its block in
`AGENTS.md` names, rather than a search. Open a `skipper`, `hand` or `bosun` benchmark entry
around each delegation the way every stage is bracketed, and pass `driver=cruise` to every `end` this
session closes.

**A person's word arrives as a `told` line in the stream's own deck log**, written by `/cruise-tell` or from
the bridge. Read the inbox at every stage boundary (`python3 {{inbox}} <stream>`) and act on what is
there before the next stage: a steer takes precedence over what the artifacts alone would make this stage do,
a fact the run lacked is the answer to a block, and a scope or a preference is written down — into the owner
brief (`{{owner-brief}}`) or a decision entry with `Decided by: human` — so it outlives this session. Answer
each with a `read` line carrying that `told`'s own timestamp: the receipt is what makes it evidence somebody
was told rather than an assertion that somebody looked. A message never changes a setting; say so and point
at `/cruise-settings` where one asks for that.

## The watch seat

After casting off — and only in the session that did, never in one a captain dispatched —
{{watch-seat}}
## Run the ladder, and answer at its stops

Run `commands/sail.md` from *Enter at the first incomplete stage* to its end, exactly as written — the entry
stage from artifacts, the branch check, *Who runs each stage*, the benchmark bracket, the ready-set rules and
the concurrent fan-out. Wherever that command would stop for a person, this table says what to do instead;
where the table is silent, the ladder's own rule stands.

{{stop-table}}

## Deciding: the skipper protocol

A product question is decided, never deferred, and every decision is written twice — into the artifact the
stage owns, and as the next entry of `{{decisions}}`, which is the only place a person can read every decision
this run took. Read the standing entries before any decision, so a hundred answers stay consistent with each
other — and read **what this project already does**, which is an authority the other three are not: a
generated project ten slices in, and an adopted repository on its first day, both hold conventions no
document of this method names. How this codebase already publishes, already links one handler to the next,
already names a migration. A decision taken without them is how a codebase ends up with two ways of doing
one thing, each defensible on its own. `docs/architecture.md` and the code itself are where they are
written in a generated project; `structure.md` and the survey in an adopted one. **Why** says which of the
four answered, or that none did. Under `decide: recommended-first`, decide here when the stage itself
recommends an answer (the release-constraint stage says *recommend the answer with its reason rather than
asking an open question*), when a standing entry already covers the question, when this project's own
convention settles it, or when the specification or the constitution answers it outright. Anything else is an **open question**: delegate it to one fresh `{{skipper}}` delegate with the
question, the stage, the options and the recommendation in its brief — the spec, the constitution, the owner
brief and the log are the standing part of its own brief — and **the number its entry will carry**. `D<n>` is
allocated here, before dispatch: the next after the last entry in `{{decisions}}`, one per delegate in dispatch
order where several go out at once. The delegate returns the whole entry under that number and writes
nothing; this session appends it, in number order, and writes the decision into the artifact the stage owns.
Under `decide: skipper-always`, every question goes to the delegate. Several open questions in one turn are
several concurrent delegates, each with its own number; a slice delegate that handed one back does not wait
on the others. Every other identifier a decision adds to a shared artifact — a requirement, a criterion, an
example, a state — is allocated the same way: by this session, after the delegates return, in dispatch order.
A delegate cannot see what its siblings are adding, so it numbers nothing they share; two entries that came
back as the same `D3`, with requirement ranges that overlapped, were exactly the reconciliation by hand this
protocol exists to end.

The entry's shape, which `{{make}} check-decisions` holds:

```markdown
{{decision-entry}}
```

A decision that would break a constitution MUST is not available; the skipper says so and the question parks.
A fact nobody here has — a credential, a third party's behaviour, an approval — is `unavailable`, and the
skipper's brief says which those are: it is never decided, whatever `decide` says. A person overrides a
decision by editing its `Status` and writing the answer they want into the artifact; the next dispatch
re-derives the entry stage from that artifact, the way demo feedback re-enters the ladder.

{{adr-rule}}

{{hand}}
## When the ready set is empty: the completion audit

An exhausted split is where `/sail` stops and where this command does its last stage. Delegate `/gaps` over
the whole of `specs/<feature>/spec.md` against what shipped — one `sail-gaps-lookout` delegate per feature area,
concurrently, as the post-implementation pass is per seam — and put every finding to the skipper protocol:
a criterion nothing built becomes a slice, appended to the split with `/story-splitting`, and the ladder is
re-entered for it; a finding the owner rules out of scope is a decision entry saying so. Write
`{{report}}`: what the specification asked, what shipped, every out-of-scope decision, and every entry a person
has not yet reviewed. An audit with nothing left to build writes the stream's last lines and the capability's `accepted`; the captain reads those and claims nothing more.

## The stage contract

Spend this session on one unit of work, write the lines that say what it did, and end. **Before the split
exists**, the unit is the upstream stages together — {{upstream}} — through to the split's first ready set: each
reads the one before it and none is a slice, so the session does not end inside them; it ends when the split
is written, or at a park. **From the split on**, the unit is the one slice the captain dispatched this session
for, through Phase 4 and its done marker. `commands/sail.md` says *do not wait to be invoked again*; here the
captain is what dispatches again, with a fresh context, which is the rule every delegate already lives by.

**A stage that wrote no line made no progress, whatever it says it did.** That is the one rule this contract
has, and it is the whole of it. The captain reads the deck log — every mark the chart's `sets` names for this
slice, and the demo's verdict, written during this session — and nothing else: not a summary, not a closing
sentence, not a report that says the work is done. Write each line as the stage produces it, through
`python3 scripts/agents/telegraph.py` and the ladder's own writers, rather than keeping them to the end: a
session that dies halfway has then said what it got through, and one that kept them has said nothing.

Where a harness lets a hook refuse the end of a turn, the project uses it for exactly this: a turn that tries
to end having written no line is held once and told so, up to three times, and then let go — `before-stop`, in
`scripts/agents/session.py`. The hold is a courtesy and not the control. The control is the captain's gate,
which runs after the session has gone, parks the slice, and says which mark is missing.

Where nothing can move — the ready set blocked and the bosun could not move one, or a blocker is on the
catastrophic list — write the park line with the exact thing a person must provide or decide, and end. The
captain reads it, the board shows the stream as waiting on somebody, and `/cruise-tell` with the answer is
what resumes it. A park is a line, not an exit: nothing is lost and nothing is retried blindly.

## A compacted context

A harness can summarise this context at any point — Claude Code compacts, Gemini CLI compresses — and what a
summary loses is the state nothing on disk carries: which delegates are out and with what manifest, a question
half-answered, which slice's demo comes next. There is no checkpoint file to keep current any more, because
there is something better and it is written anyway: **the deck log**. It is what the captain reads, so it is
never stale, and it costs this session nothing extra to keep.

Where the harness can run a command after compaction, the project does it for you: `after-compact` prints
this stream's last lines straight back into the resumed context, and `before-compact` fires whatever the
elected extensions attached there (`scripts/agents/session.py`; `.claude/settings.json`, `.cursor/hooks.json`
and `.gemini/settings.json` carry the rows, and `scripts/agents/registry.json` says which harness has what).
Where it cannot, read them yourself at the start of every stage and whenever this context looks summarised:
`python3 {{inbox}} <stream>` says what is owed, and `slipwai fleet <stream>` says the whole of it.

A line an earlier session left is a lead, never a result: its delegates ended with it, so verify what they
left in the tree before continuing.

{{unblock}}
## What holds throughout

- **Parallelism is inherited and widened.** Everything *Running ready slices concurrently* allows runs the
  same way here — the two bands, the states `clearance.py` prints, the refill at every boundary and the
  reason owed for any eligible slice left waiting. What no longer serialises the fan-out are the two stops
  that were a person's: a delegate's `question` line is answered by the skipper's `decision` while its
  siblings keep running, and a slice's demo runs in the hand while the next slice's delegate is still
  converging. Phase 4 stays one slice at a time on `main`. The worktrees
  beside the checkout are writable on Claude Code because the captain starts every `/sail` with `--add-dir`
  for the directory the checkout sits in (`scripts/agents/registry.json`, `headless.worktreeFlags`); on a
  harness whose row has no such flag, make the worktree inside the tree where the harness offers one, or run
  the ready slices one at a time here and say so, as the ladder does where the harness cannot delegate.
- **Flags stay off.** Under `release: flagged` nothing this run merges is visible to a real actor until a
  person flips a key. Turning a flag on is never a decision the log can contain.
- **The constitution's MUSTs are the floor.** No decision waives one; a question whose every option breaks
  one goes to the bosun for the reading that keeps them all, and parks only if there is none.
- **The hand edits no code.** A defect it finds is a task; a fix there would make the verdict evidence for
  itself.
- **Stuck is detected, and it is the captain that detects it.** A stage that writes no line for longer than
  the telegraph's `wait_bound` is ended and the slice re-dispatched, up to `attempts` times, and then parked
  by name. A session that ends on an open `question` is parked with the question in the line, and the
  answer a person gives through `/cruise-tell` is written by the captain as the `decision` carrying that
  question's `id` before the slice is re-dispatched. The same open question raised twice in one session goes
  to the bosun once and parks after that. A
  run that loops is not a run, and the thing that notices is outside the session, which is the point: the
  first attempt had the loop judging itself and it judged itself to be working for a fortnight.
- **The record says who drove.** `driver=cruise` on every benchmark entry, `skipper`, `hand` and `bosun` as stages
  of their own, so a decision's cost and a demo's cost are numbers `{{make}} benchmark` can read.
- **Settings change only through `/cruise-settings`**, never inside an iteration, and `{{config}}` is
  committed: a run's rules are a diff.
