"""`/cruise`: `/drive` with nobody at the wheel — the agent as driver and product owner, until the specs are satisfied.

`/drive` stops for four things: a product decision, an input that is genuinely unavailable, a split with no
ready slice left, and the next slice's demo. Three of those belong to a person and are why the command stops.
`/cruise` runs the same ladder — not a copy of it — and at each of those stops does what the owner or the actor
would have done: decides, on the host where the stage recommends an answer or a standing decision covers it
and through `drive-skipper` where the question is open; runs the demo through `drive-hand`; and, where the
split is exhausted, audits the specification against what shipped rather than declaring the product done.
Every answer is written where `/drive` would have written a person's, and once more in `decisions.md`, so
a person can read every decision the machine took in one place and overturn any of them. It stops for a human
and for nothing else; the outer loop that re-invokes it with a fresh context is `scripts/agents/cruise.py run`.
"""
from __future__ import annotations

import json

from ..layout import AT_ROOT, Layout
from ..origin import Adoption
from ..services import App
from .cruise_agents import DECISIONS, OWNER_BRIEF, SKIPPER
from .cruise_hand import hand_section
from .cruise_record import CHECKPOINT, CHECKPOINT_ENTRY, DECISION_ENTRY, STOP_FILE
from .cruise_stops import LOG, REPORT, stop_table
from .cruise_unblock import unblock_section

CONFIG = ".specify/cruise.json"
SCRIPT = "scripts/agents/cruise.py"
# The last line of every iteration: the one thing the outer loop reads.
LAST_LINES = ("cruise: continue", "cruise: done", "cruise: parked: <what a person must provide>",
              "cruise: stopped: human")
# What a session is told when nothing is reading its last line — a person typed `/cruise`, and an iteration run
# here would end with nobody to re-invoke it. `scripts/agents/cruise.py loop` prints the same words, so the
# command and the script cannot disagree: the runner is the one thing that continues a run, on every harness.
UNREAD = ("no outer loop is reading this: a `/cruise` typed in a session starts the runner — `python3 "
          "scripts/agents/cruise.py start` — and then watches it with `python3 scripts/agents/cruise.py watch`; the "
          "runner drives the ladder from here, a fresh session per iteration, and this session runs no stage of it")
# Every setting, its values, its default and what it controls — the one list the config, the command, the
# settings command and `scripts/agents/cruise.py` are all written from.
SETTINGS: tuple[tuple[str, tuple[str, ...] | str, object, str], ...] = (
    ("enabled", ("true", "false"), False, "whether `/cruise` runs at all; `false` is a refusal that says so"),
    ("decide", ("recommended-first", "skipper-always"), "recommended-first",
     "who answers a product question: the host where the stage recommends an answer or a standing decision "
     "covers it and `drive-skipper` otherwise, or `drive-skipper` for every question"),
    ("release", ("flagged", "park"), "flagged",
     "the release-constraint stage: every slice continues or opens a flag seeded off, so every merge is dark; "
     "or park at the push and let a person say it is a release they want"),
    ("constitution", ("ratify", "park"), "ratify",
     "an unratified constitution: the skipper drafts and ratifies it, marked pending human review; or park"),
    ("hand", ("browser", "http", "cli"), "browser",
     "the top of the hand's ladder for a demo; each falls through to the next where it cannot run"),
    ("unblock", ("bosun", "park"), "bosun",
     "what a block becomes: work for `drive-bosun` first — a stub, a narrower reading, a repair — parking only "
     "at the catastrophic or when it fails; or a park at once"),
    ("stuck_after", "a whole number", 3, "iterations with no artifact change before the loop parks"),
    ("max_iterations", "a whole number or null", None, "a budget on iterations; null is unbounded"),
    ("max_hours", "a whole number or null", None, "a budget on wall time; null is unbounded"),
    ("poll_minutes", "a whole number", 10, "how often a parked loop looks for a reason to resume"),
)
COMMENT = (
    "How /cruise runs /drive with nobody at the wheel. Change it with /cruise-settings (python3 "
    f"{SCRIPT} --set key=value), checked; `make check-agents` holds the shape. commands/cruise.md says what "
    "each value means. `enabled: false` is the default: a project has to ask for this."
)


def cruise_config() -> str:
    """`.specify/cruise.json` as generated: every setting at its default, and where it is explained."""
    table: dict[str, object] = {"_comment": COMMENT, **{key: default for key, _, default, _ in SETTINGS}}
    return json.dumps(table, indent=2, ensure_ascii=False) + "\n"


def settings_table() -> str:
    def spelled(values: tuple[str, ...] | str) -> str:
        return " \\| ".join(f"`{value}`" for value in values) if isinstance(values, tuple) else values

    rows = "\n".join(
        f"| `{key}` | {spelled(values)} | `{json.dumps(default)}` | {controls} |"
        for key, values, default, controls in SETTINGS
    )
    return f"| Setting | Values | Default | Controls |\n|---|---|---|---|\n{rows}"


def cruise_command(
    event: bool, apps: list[App], target: str = "none", layout: Layout = AT_ROOT, adoption: Adoption | None = None,
) -> str:
    del apps  # the ladder's own text already carries the profile's services; nothing here is per service
    upstream = ("principles, the specification, the event model and the split" if event
                else "principles, the specification and the split")
    adopted = (
        "\n\nThis repository adopted the method around code that was already there, and two of its stops "
        "are a person's word — the rows at the foot of the table. A run here proceeds on stated assumptions "
        "and `Proposed` records rather than parking, and a person confirms or overturns them afterwards."
        if adoption is not None else ""
    )
    return f"""---
description: Run /drive as driver and product owner, iteration after iteration, until every specification is satisfied — stopping only for a human
argument-hint: [--feature <name>] [kick-off: what this run is for, where the brief or PRD is] | unblock: <what the outer loop saw>
---

# Cruise

`/drive` takes one slice from wherever it stands to an actor-visible demo and stops for a product decision, an
unavailable input, an exhausted split and the demo. This command runs **that ladder — `commands/drive.md`,
every rule as written** — with nobody at the wheel: it decides what the ladder would have asked a person,
runs each demo as the actor, and re-enters the ladder until the specification under `specs/<feature>/` is
satisfied. Nothing about what a stage produces changes; what changes is who answers. It stops for a human and
for nothing else. An iteration is one invocation of this command; the outer loop that re-invokes it with a
fresh context is `python3 {SCRIPT} run` (`{layout.make} cruise`), on every harness. Typed in a session, nothing
re-invokes it, so the command starts that loop instead of running the ladder here (*Before anything*, below):
the runner is the one thing that continues a run, whatever the harness.{adopted}

## Before anything: refuse, or start

Read `{CONFIG}`. `enabled: false`, or `{STOP_FILE}` present, is a refusal in one line that says which. No
`specs/<feature>/spec.md` is a refusal too: a specification is the one thing a person brings. In an iteration a
refusal still ends on a last line, because the runner reads nothing else and would spend its stuck budget on a
plain one: `enabled: false` or the stop file ends on `{LAST_LINES[3]}` — a person turned it off — and a missing
specification on `cruise: parked: a specification under specs/<feature>/spec.md`; typed in a session, the
refusal is plain, since nothing reads it. Then run
`python3 {SCRIPT} loop`: it says what is reading this session's last line. **Where it says nobody is** — this
command was typed in a session, and no runner set `CRUISE_RUNNER` and `CRUISE_ITERATION` — run
`python3 {SCRIPT} start` with everything typed after `/cruise` as its arguments, verbatim, and repeat what it
printed: the runner it started drives the ladder from here, one fresh session per iteration, and this session
runs no stage of it. A refusal is the whole answer — a runner already running, the stop file present, no
harness on PATH it can run an iteration through. Then take the watch seat (*The watch seat*, below). **Where
it says the outer loop started this session**, this is an iteration: read the owner brief (`{OWNER_BRIEF}`)
and every standing entry in `{DECISIONS}`, and say the iteration number from `{LOG}`, the branch and its
distance from trunk, and that a person stops this run with `touch {STOP_FILE}`. Where `.codegraph/` is in the
tree, load `codegraph_explore` by name through this harness's tool-search step now, before the first stage: a
caller or blast-radius question later is then one call and not a text search, and `python3 {SCRIPT} status`
counts the iterations that asked. Open a `skipper`, `hand` or `bosun`
benchmark entry around each delegation the way every stage is bracketed, and
pass `driver=cruise` to every `end` this iteration closes.

**The argument is the kick-off.** What a person typed after `/cruise` — what this run is for, where the brief
or the PRD is, which feature — reaches the first iteration of the run and no other: every later iteration
runs bare and derives its stage from disk. So the first iteration writes down whatever the kick-off says that
must outlive it — a PRD it names becomes the specification through the ladder's own stages, a preference it
states goes into the owner brief (`{OWNER_BRIEF}`), a scope it sets is a decision entry — before it does
anything else. Two things the runner passes itself recur: a feature named with `--feature` on `run` or `start`
(`{layout.make} cruise FEATURE=<name>`) is the first word of every iteration's argument and scopes the run to that
feature's specification — the ladder is entered for it and no other — and `unblock: <reason>` is what the runner
says when a run makes no progress (*Blocked: the bosun protocol*, below).

## The watch seat

After `start` — or where `start` said a runner is already running — run `python3 {SCRIPT} watch`. It prints
what the iteration does as it happens, one line per command, file, and delegate out and back, and returns at
the iteration's end, a park, the run's end, once the feed has gone quiet for a moment, or after a minute and a
half with nothing new; its last line says which. **Put every line it printed in your reply, unchanged, in a
fenced block, before anything else** — the harness folds a command's output, so the feed reaches a person only
through your reply — **and where it says the run continues, or the iteration is in flight, run `watch` again
at once**; where it says parked, ended, or no runner, repeat what it said and end the turn. A watch the
harness cut short — a tool timeout, with no last line from `watch` — is watched again, not asked about. Where
the harness can run a command in the background and re-invoke this session with its output when it returns,
run `watch` that way, so the turn ends between watches and a person can type in the gap. Watching is only ever
reading — the runner needs nothing from this session, and a turn that ends here ends nothing else — so it is
never a reason to run a stage of the ladder in this session.

**A person typing here is talking to you, not stopping the run.** Answer them — what the feed shows, what
`{CONFIG}` says (`python3 {SCRIPT}` prints every setting and what it controls), what `python3 {SCRIPT} status`
says, what `{DECISIONS}` records — and change a setting through `/cruise-settings` where they ask; it takes
effect at the next iteration. Then watch again. Only `touch {STOP_FILE}`, `python3 {SCRIPT} stop`, or
`{layout.make} cruise-stop` ends the run, and only when they ask for that.

## Run the ladder, and answer at its stops

Run `commands/drive.md` from *Enter at the first incomplete stage* to its end, exactly as written — the entry
stage from artifacts, the branch check, *Who runs each stage*, the benchmark bracket, the ready-set rules and
the concurrent fan-out. Wherever that command would stop for a person, this table says what to do instead;
where the table is silent, the ladder's own rule stands.

{stop_table(event, target, adoption)}

## Deciding: the skipper protocol

A product question is decided, never deferred, and every decision is written twice — into the artifact the
stage owns, and as the next entry of `{DECISIONS}`, which is the only place a person can read every decision
this run took. Read the standing entries before any decision, so a hundred answers stay consistent with each
other. Under `decide: recommended-first`, decide here when the stage itself recommends an answer (the
release-constraint stage says *recommend the answer with its reason rather than asking an open question*),
when a standing entry already covers the question, or when the specification or the constitution answers it
outright. Anything else is an **open question**: delegate it to one fresh `{SKIPPER}` delegate with the
question, the stage, the options and the recommendation in its brief — the spec, the constitution, the owner
brief and the log are the standing part of its own brief — and **the number its entry will carry**. `D<n>` is
allocated here, before dispatch: the next after the last entry in `{DECISIONS}`, one per delegate in dispatch
order where several go out at once. The delegate returns the whole entry under that number and writes
nothing; this session appends it, in number order, and writes the decision into the artifact the stage owns.
Under `decide: skipper-always`, every question goes to the delegate. Several open questions in one turn are
several concurrent delegates, each with its own number; a slice delegate that handed one back does not wait
on the others. Every other identifier a decision adds to a shared artifact — a requirement, a criterion, an
example, a state — is allocated the same way: by this session, after the delegates return, in dispatch order.
A delegate cannot see what its siblings are adding, so it numbers nothing they share; two entries that came
back as the same `D3`, with requirement ranges that overlapped, were exactly the reconciliation by hand this
protocol exists to end.

The entry's shape, which `{layout.make} check-decisions` holds:

```markdown
{DECISION_ENTRY}
```

A decision that would break a constitution MUST is not available; the skipper says so and the question parks.
A fact nobody here has — a credential, a third party's behaviour, an approval — is `unavailable`, and the
skipper's brief says which those are: it is never decided, whatever `decide` says. A person overrides a
decision by editing its `Status` and writing the answer they want into the artifact; the next iteration
re-derives the entry stage from that artifact, the way demo feedback re-enters the ladder.

{hand_section(layout.make)}
## When the ready set is empty: the completion audit

An exhausted split is where `/drive` stops and where this command does its last stage. Delegate `/gaps` over
the whole of `specs/<feature>/spec.md` against what shipped — one `drive-gaps` delegate per feature area,
concurrently, as the post-implementation pass is per seam — and put every finding to the skipper protocol:
a criterion nothing built becomes a slice, appended to the split with `/story-splitting`, and the ladder is
re-entered for it; a finding the owner rules out of scope is a decision entry saying so. Write
`{REPORT}`: what the specification asked, what shipped, every out-of-scope decision, and every entry a person
has not yet reviewed. Only an audit with nothing left to build ends with `cruise: done`.

## The iteration contract

Spend this context on one unit of work, and then end the iteration rather than starting the next unit in a
context that has already carried one. **Before the split exists**, the unit is the upstream stages together —
{upstream} — through to the split's first ready set: each reads the one before it and none is a slice, so the
iteration does not end inside them; it ends when the split is written, or at a park. **From the split on**,
the unit is one slice through Phase 4 and its done marker, or one concurrent fan-out through its merges in
split order. `commands/drive.md` says *do not wait to be invoked again*; here the
outer loop is what re-invokes, with a fresh context, which is the rule every delegate already lives by.
Between stages, look for `{STOP_FILE}`: present, finish the stage's own writes, commit what is green, and end
on `{LAST_LINES[3]}`.
At every stage boundary and every delegation, rewrite the checkpoint (*Checkpoint*, below).
Where nothing can move — every ready slice blocked and the bosun could not move one, or a blocker is on the
catastrophic list — end with `parked` and the exact thing a person must provide or decide; the loop waits,
it does not exit. The last line of every iteration is one
of these, and the outer loop reads nothing else:

- `{LAST_LINES[0]}`
- `{LAST_LINES[1]}`
- `{LAST_LINES[2]}`
- `{LAST_LINES[3]}`

**An iteration ends only on one of those four lines.** Any other message that ends a turn is a stop, whatever
it says it is about to do: in Claude Code a message with no tool call *is* the end of the turn, so "continuing
into the plan now" is a stop that called itself progress. And an iteration is only ever a session the runner
started: where `python3 {SCRIPT} loop` said nobody is reading, this command started the runner and watched it
(*{UNREAD}*). Neither rule is left to this text. The runner reads the last line and re-invokes, on every
harness, and a session that ended without one is no progress to it. Where a harness lets a hook refuse the
end of a turn, the project's hook file runs `python3 {SCRIPT} stopping` there — `.claude/settings.json` runs
it as Claude Code's `Stop` hook, `.cursor/hooks.json` as Cursor's `stop`, `.gemini/settings.json` as Gemini
CLI's `AfterAgent`; `scripts/agents/registry.json`, `hooks`, says what each harness has — and while a runner
started the session, `{CHECKPOINT}` says an iteration is in flight and `{STOP_FILE}` is absent, it refuses a
turn that ends on anything but a last line and hands back the checkpoint's `Next:` line as the reason. It
lets go after three holds against a checkpoint nothing rewrote, so a session that cannot move is not held
forever; rewriting the checkpoint at every stage boundary is what keeps it moving.

## Checkpoint: what survives a compacted context

A harness can summarise this context at any point — Claude Code compacts, Gemini CLI compresses — and what a
summary loses is the state nothing on disk carries: which delegates are out and with what manifest, a
question half-answered, which slice's demo comes next. So keep `{CHECKPOINT}` current: rewrite it at every
stage boundary and every delegation, in this shape:

```markdown
{CHECKPOINT_ENTRY}
```

At the start of every stage, and whenever this context looks summarised — the iteration number is not in
memory, or a summary opens the context — read the checkpoint before acting; `python3 {SCRIPT} resume` prints
it with the rules beside it, and prints nothing where no iteration is in flight. Where the harness can run a
command after compaction, the project's settings do that for you: `.claude/settings.json` runs `resume` on
Claude Code's `SessionStart` with the `compact` matcher and stamps the checkpoint on `PreCompact`, and
`scripts/agents/registry.json`, `compaction`, says what each harness can. A checkpoint left by an earlier
iteration is a lead, never a result: its delegates ended with that session, so verify what they left in the
tree before continuing. The runner deletes the checkpoint when an iteration ends `done` or `stopped`, and so
does the stop hook; one that ends `continue` or `parked` leaves it for the next.

{unblock_section(SCRIPT)}
## What holds throughout

- **Parallelism is inherited and widened.** Everything *Running ready slices concurrently* allows runs the
  same way here. What no longer serialises the fan-out are the two stops that were a person's: a delegate's
  product question is answered while its siblings keep running, and a slice's demo runs in the hand while
  the next slice's delegate is still converging. Phase 4 stays one slice at a time on `main`. The worktrees
  beside the checkout are writable on Claude Code because the runner starts every iteration with `--add-dir`
  for the directory the checkout sits in (`scripts/agents/registry.json`, `headless.worktreeFlags`); on a
  harness whose row has no such flag, make the worktree inside the tree where the harness offers one, or run
  the ready slices one at a time here and say so, as the ladder does where the harness cannot delegate.
- **Flags stay off.** Under `release: flagged` nothing this run merges is visible to a real actor until a
  person flips a key. Turning a flag on is never a decision the log can contain.
- **The constitution's MUSTs are the floor.** No decision waives one; a question whose every option breaks
  one goes to the bosun for the reading that keeps them all, and parks only if there is none.
- **The hand edits no code.** A defect it finds is a task; a fix there would make the verdict evidence for
  itself.
- **Stuck is detected.** `stuck_after` iterations with the same artifact fingerprint give the bosun one
  iteration to move it, then park the loop; the same open question raised twice in one iteration goes the
  same way. A run that loops is not a run.
- **The record says who drove.** `driver=cruise` on every benchmark entry, `skipper`, `hand` and `bosun` as stages
  of their own, so a decision's cost and a demo's cost are numbers `{layout.make} benchmark` can read.
- **Settings change only through `/cruise-settings`**, never inside an iteration, and `{CONFIG}` is
  committed: a run's rules are a diff.
"""


def cruise_settings_command(layout: Layout = AT_ROOT) -> str:
    """`/cruise-settings`: the settings shown, or changed through the checked `--set`."""
    return f"""---
description: Show or change how /cruise runs /drive on its own — who decides, how it releases, what it demos with, when it parks
argument-hint: [key=value ...]
---

# Cruise settings

`{CONFIG}` holds how `/cruise` runs `commands/drive.md` with nobody at the wheel. `commands/cruise.md` says what
each value does at the stops it governs. This command is how the settings are read and how they change:
checked, at any time, and never by quietly running an iteration under different rules.

{settings_table()}

## No argument — show the settings

```sh
python3 {SCRIPT}
```

Report every line as printed — the value and what it controls — and whether a run is enabled at all.

## Arguments — change them

```sh
python3 {SCRIPT} --set $ARGUMENTS
```

Each argument is `key=value` from the table, and several may be given at once. The script refuses a key it
does not know, a value outside the ones listed, and a number that is not one, and writes nothing then. Report
a refusal in its words; do not work around it by editing the file. Then commit `{CONFIG}` on its own, with a
message naming the change: it takes effect at the next iteration, and nothing already running is interrupted.
`{layout.make} check-agents` holds the file's shape whether it was edited by hand or through this command.

## When the request is in words

"Turn it on" is `enabled=true`; "stop after tonight" is `max_hours=<n>`; "ask me before every release" is
`release=park`; "let the skipper decide everything" is `decide=skipper-always`; "back to the defaults" is
every key at the value the table shows. Stopping a run that is going is not a setting: it is `python3 {SCRIPT}
stop` — `touch {STOP_FILE}`, which ends the run after the iteration in flight; `--now` ends that iteration too
— and `commands/cruise.md` says how the run ends cleanly from either.
"""
