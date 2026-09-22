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
from .cruise_agents import BROWSER, DECISIONS, DEMO_LOG, EVIDENCE, HAND, OWNER_BRIEF, SKIPPER

CONFIG = ".specify/cruise.json"
SCRIPT = "scripts/agents/cruise.py"
STOP_FILE = ".specify/cruise.stop"
LOG = "specs/cruise-log.jsonl"
REPORT = "specs/<feature>/cruise-report.md"
# The last line of every iteration: the one thing the outer loop reads.
LAST_LINES = ("cruise: continue", "cruise: done", "cruise: parked: <what a person must provide>",
              "cruise: stopped: human")
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
DECISION_ENTRY = f"""## D<n> — <the question, in one line>
- **Stage:** <stage> · **Slice:** <id> · **When:** <ISO instant> · **Iteration:** <n>
- **Question:** <as the stage raised it>
- **Options:** <each, marking the one the stage recommended>
- **Decision:** <one>
- **Why:** <in the actor's terms>
- **Decided by:** host (stage recommendation) | host (standing decision D<m>) | {SKIPPER} (<model>) | human
- **Confidence:** high | medium | low · **Would reverse if:** <the one condition>
- **Written to:** <the artifact paths the answer went into>
- **Status:** standing | overridden by D<m> | overridden by human <date>"""
DEMO_ENTRY = f"""## <ISO instant> — <accepted | behaviour | implementation> · iteration <n> · {HAND} (<model>)
- **Started with:** <the literal command or URL> · **Seeded:** <what, or none>
- **Driven through:** {BROWSER} | <harness browser tool> | HTTP | CLI — <why, where not the first>
- **Examples:** <one line each — R1 e1: passed · R2 e1: failed, expected X, saw Y · R3 e2: unreachable, why>
- **Evidence:** <paths under demo/>
- **Feedback:** <what re-entered the ladder and at which stage, or the note for the next slice>"""


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


def stop_table(event: bool, target: str, adoption: Adoption | None) -> str:
    """Every stop `/drive` makes, what `/cruise` does there instead, and where the answer is recorded."""
    criteria = "`examples.md`" if event else "the criteria in `spec.md`"
    rows = [
        ("The checkout is behind trunk, or the fetch failed",
         "Fetch and fast-forward where the tree is clean; rebase a `slice/<id>` branch that has local commits. "
         "A conflict parks; a fetch that cannot run parks and says so. Never derive from a stale tree",
         f"`{LOG}`"),
        ("Principles: the constitution is unratified",
         "`constitution: ratify` — the skipper drafts it with `/speckit-constitution` from the spec and the "
         "owner brief, answers `/constitution-coverage`, and ratifies it with the line `ratified by cruise "
         "(skipper) — pending human review`. `park` stops here instead",
         "`constitution.md`, a decision entry"),
        ("Product specification missing",
         "Refuse to start. A spec is the one thing a person brings; `/cruise` writes no product from nothing",
         "—"),
        ("Which service or bounded context owns a slice",
         "Decide against each service's recorded `purpose`; where none covers it, write the purpose the spec "
         "implies and decide. Contexts by the language test, recorded on the service",
         "the model or plan, `project.json`, a decision entry"),
        (f"Slice gaps: a question at a time over {criteria}",
         "The conversational loop runs with the owner as the other party: each gap is answered — host or "
         "skipper by `decide` — and written back as the criterion or state. `gaps=N` still counts",
         f"{criteria}, a decision entry per question"),
        ("A delegate hands back a product question in `plan.md`",
         "Answer it, un-block the slice, re-dispatch with the entry as a pointer, never as a conclusion",
         "`plan.md`, a decision entry"),
        ("Converge appended Phase 4 tasks; the after-converge `/gaps` says stop",
         "Already bounded by the ladder: continue to the demo as `commands/drive.md` says", "—"),
        ("The demo stop",
         f"Delegate to `{HAND}` with exactly what the stop hands a person, plus the acceptance script; take its "
         "verdict as the actor's and re-enter the ladder where demo feedback re-enters. Acceptance says "
         f"`accepted-by: {HAND}` on the register row or status flip",
         f"`{DEMO_LOG}`, `benchmark.json` `outcome=`, the register"),
        ("The ready set is empty",
         "Not a stop: the completion audit below. Only an audit with nothing left is `done`",
         f"`{REPORT}`, decision entries"),
        ("An input that is genuinely unavailable — a credential, an external system, a person's approval",
         "Never decided. Record it as blocked with what is needed, take the next ready slice, and park only "
         "when nothing can move",
         "a `parked` line in the log, ⛔ on the board"),
    ]
    if target != "none":
        rows.insert(5, (
            "Release constraint",
            "Take the stage's own recommendation. `release: flagged` — every slice continues or opens a flag "
            "seeded `off`, so every merge is dark and a person flips keys. `park` stops at the push instead",
            "`plan.md`, the flag file, a decision entry"))
        rows.insert(6, (
            "\"A release they want now\" — no flag, or a flag already on, before the push",
            "Never answered by the machine. Under `flagged` it does not arise; where it does, park with the "
            "exact question", "a `parked` line in the log"))
    if adoption is not None:
        rows += [
            ("Ground: a convergence row still `unrecorded` on an axis the slice touches",
             "A fact about the world is not a decision. The row stays `unrecorded`; slices touching that axis "
             "are blocked; product slices that do not proceed", "nothing — a `parked` line where nothing can move"),
            ("The change-strategy ADR at `Accepted`", "The word is a person's. Park", "—"),
            ("Quick wins and method slices offered from the programme",
             "Take the programme top-first, as the stage recommends", "`project.json` `planned`, a decision entry"),
        ]
    body = "\n".join(f"| {index} | {stop} | {does} | {recorded} |" for index, (stop, does, recorded)
                     in enumerate(rows, start=1))
    return f"| # | Where `/drive` stops | What `/cruise` does there | Recorded in |\n|---|---|---|---|\n{body}"


def cruise_command(
    event: bool, apps: list[App], target: str = "none", layout: Layout = AT_ROOT, adoption: Adoption | None = None,
) -> str:
    del apps  # the ladder's own text already carries the profile's services; nothing here is per service
    adopted = (
        "\n\nThis repository adopted the method around code that was already there, and two of its stops "
        "stay a person's under `/cruise` — the rows at the foot of the table. A run here is degraded by design: "
        "it parks where a person's word is the artifact."
        if adoption is not None else ""
    )
    return f"""---
description: Run /drive as driver and product owner, iteration after iteration, until every specification is satisfied — stopping only for a human
argument-hint: [feature]
---

# Cruise

`/drive` takes one slice from wherever it stands to an actor-visible demo and stops for a product decision, an
unavailable input, an exhausted split and the demo. This command runs **that ladder — `commands/drive.md`,
every rule as written** — with nobody at the wheel: it decides what the ladder would have asked a person,
runs each demo as the actor, and re-enters the ladder until the specification under `specs/<feature>/` is
satisfied. Nothing about what a stage produces changes; what changes is who answers. It stops for a human and
for nothing else. An iteration is one invocation of this command; the outer loop that re-invokes it with a
fresh context is `python3 {SCRIPT} run` (`{layout.make} cruise`), and a person watching a run in this session
can use the harness's own loop over `/cruise` instead.{adopted}

## Before anything: refuse, or start

Read `{CONFIG}`. `enabled: false`, or `{STOP_FILE}` present, is a refusal in one line that says which. No
`specs/<feature>/spec.md` is a refusal too: a specification is the one thing a person brings. Then read the
owner brief (`{OWNER_BRIEF}`) and every standing entry in `{DECISIONS}`, and say the iteration number from
`{LOG}`, the branch and its distance from trunk, and that a person stops this run with `touch {STOP_FILE}` or
by interrupting the session. Open a `skipper` or `hand` benchmark entry around each delegation the way every
stage is bracketed, and pass `driver=cruise` to every `end` this iteration closes.

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
brief and the log are the standing part of its own brief — and take the entry it appends. Under
`decide: skipper-always`, every question goes to the delegate. Several open questions in one turn are several
concurrent delegates; a slice delegate that handed one back does not wait on the others.

The entry's shape, which `{layout.make} check-decisions` holds:

```markdown
{DECISION_ENTRY}
```

A decision that would break a constitution MUST is not available; the skipper says so and the question parks.
A fact nobody here has — a credential, a third party's behaviour, an approval — is `unavailable`, and the
skipper's brief says which those are: it is never decided, whatever `decide` says. A person overrides a
decision by editing its `Status` and writing the answer they want into the artifact; the next iteration
re-derives the entry stage from that artifact, the way demo feedback re-enters the ladder.

## Demonstrating: the hand protocol

At the demo stop, compose everything `commands/drive.md` says the stop must contain — the board, the literal
command or URL, the seed data, the expected result, the running process — and hand it, with the slice's
acceptance script, to one fresh `{HAND}` delegate instead of a person. `hand: {SETTINGS[4][2]}` is the top of
its ladder: `{BROWSER}` where the slice has a screen, then a browser tool the harness exposes, then HTTP, then
the CLI, each falling through where it cannot run and saying so. Its verdict is the actor's: `accepted`
continues to *After acceptance*, `behaviour` re-enters the ladder at the stage that owns the change with the
example that shows it, `implementation` is a task. Record `outcome=` on the demo entry from the verdict, and
write `accepted-by: {HAND}` beside the register row or status flip, so a person can tell which demos a person
has seen. The hand's writes are `{DEMO_LOG}` — one section per demo — and its evidence under `{EVIDENCE}`:

```markdown
{DEMO_ENTRY}
```

## When the ready set is empty: the completion audit

An exhausted split is where `/drive` stops and where this command does its last stage. Delegate `/gaps` over
the whole of `specs/<feature>/spec.md` against what shipped — one `drive-gaps` delegate per feature area,
concurrently, as the post-implementation pass is per seam — and put every finding to the skipper protocol:
a criterion nothing built becomes a slice, appended to the split with `/story-splitting`, and the ladder is
re-entered for it; a finding the owner rules out of scope is a decision entry saying so. Write
`{REPORT}`: what the specification asked, what shipped, every out-of-scope decision, and every entry a person
has not yet reviewed. Only an audit with nothing left to build ends with `cruise: done`.

## The iteration contract

Spend this context on one unit of work — one slice through Phase 4 and its done marker, or one concurrent
fan-out through its merges in split order — and then end the iteration rather than starting the next slice in
a context that has already carried one. `commands/drive.md` says *do not wait to be invoked again*; here the
outer loop is what re-invokes, with a fresh context, which is the rule every delegate already lives by.
Between stages, look for `{STOP_FILE}`: present, finish the stage's own writes, commit what is green, and end.
Where nothing can move — every ready slice blocked on an input nobody here has — end with `parked` and the
exact thing a person must provide; the loop waits, it does not exit. The last line of every iteration is one
of these, and the outer loop reads nothing else:

- `{LAST_LINES[0]}`
- `{LAST_LINES[1]}`
- `{LAST_LINES[2]}`
- `{LAST_LINES[3]}`

## What holds throughout

- **Parallelism is inherited and widened.** Everything *Running ready slices concurrently* allows runs the
  same way here. What no longer serialises the fan-out are the two stops that were a person's: a delegate's
  product question is answered while its siblings keep running, and a slice's demo runs in the hand while
  the next slice's delegate is still converging. Phase 4 stays one slice at a time on `main`.
- **Flags stay off.** Under `release: flagged` nothing this run merges is visible to a real actor until a
  person flips a key. Turning a flag on is never a decision the log can contain.
- **The constitution's MUSTs are the floor.** No decision waives one; a question whose every option breaks
  one parks.
- **The hand edits no code.** A defect it finds is a task; a fix there would make the verdict evidence for
  itself.
- **Stuck is detected.** `stuck_after` iterations with the same artifact fingerprint park the loop, and the
  same open question raised twice in one iteration parks with it. A run that loops is not a run.
- **The record says who drove.** `driver=cruise` on every benchmark entry, `skipper` and `hand` as stages
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
every key at the value the table shows. Stopping a run that is going is not a setting: it is `touch
{STOP_FILE}`, or interrupting the session, and `commands/cruise.md` says how the run ends cleanly from either.
"""
