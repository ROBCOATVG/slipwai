"""The section of `commands/drive.md` that records what each stage cost and how it did.

Every slice runs the same ladder and, until this, nothing recorded what a slice cost or how well each stage did
its job — so whether a change to a stage prompt, a skill or a generated project's layout made slices cheaper or
better was a matter of impression, and "a lesser model for implementation" a claim nobody could check. The
record is a file per slice beside the slice's other artifacts, written by `scripts/agents/benchmark.py` at each
stage boundary; this module is the ladder's instruction to write it. What the script can read it reads — the
harness's transcript, `tasks.md`, git, the record itself — and the section asks the stage only for what nothing on
disk can say, one signal per stage, in the table below. The demo board is deliberately not touched: cost is the
team's, the board is the actor's.
"""
from __future__ import annotations

from ..layout import AT_ROOT, Layout

# What each stage passes to `end`, and nothing else. One place, so the ladder and the tests cannot disagree.
SIGNALS: tuple[tuple[str, str], ...] = (
    ("gaps", "`gaps=N` — criteria or states added before the plan; findings traced after converge"),
    ("implement", "`verify_failures=N` — red `make verify` runs during the stage"),
    ("implement", "`delegate=…` and `cycle=…` — how the stage was delegated and driven (*How implementation is "
                  "delegated*)"),
    ("implement", "`split=N` — groups the delegate fanned out into; `0` where it did not"),
    ("adversary", "`findings=N` — findings the pass recorded in the log; a recorded skip is `0`"),
    ("adversary", "`seams=N` — delegates spawned; a recorded skip is `0`"),
    ("mutation", "`mutation_score=…` — copied from the tool's own line, in its own units"),
    ("demo", "`outcome=accepted`, `outcome=behaviour` or `outcome=implementation` — what the feedback changed"),
    ("any", "`model=…` only when the record shows no transcript was read and the stage said which model ran it"),
    ("any", "`agent=…` the same way: only when the transcript attributed the delegate to no type and the stage "
            "delegated to one"),
)


def what_each_stage_costs(layout: Layout = AT_ROOT) -> str:
    """The `## What each stage costs` section: start before a stage, end after it, close at the archive."""
    rows = "\n".join(f"| `{stage}` | {takes} |" for stage, takes in SIGNALS)
    return f"""## What each stage costs

Every stage is recorded, so a change to a prompt, a skill or the layout can be compared on what it did to cost
and quality rather than on impressions. `scripts/agents/benchmark.py` keeps one record per slice,
`specs/<feature>/slices/<id>/benchmark.json`, beside the slice's other artifacts; the stages above the slice loop
go to `specs/<feature>/benchmark.json`, since they are the feature's cost and not the next slice's. Before a
stage, open its entry:

```sh
python3 scripts/agents/benchmark.py start specs/<feature>/slices/<id> implement
```

After it, close the entry with the signals that stage owes, and nothing else:

```sh
python3 scripts/agents/benchmark.py end specs/<feature>/slices/<id> implement verify_failures=1
```

| Stage | `end` takes |
|---|---|
{rows}

Everything else is read, not asked: wall time; tokens by model from the harness's own transcript between the two
moments — Claude Code's and Codex's today; anywhere else the record says `null` and why — whether the stage was
delegated, and to which agent type where the transcript names one (Claude Code attributes every sub-agent line
to the type that ran it, so an adversary pass on this slice is comparable with the same type on another); the tasks a converge pass appended; how many converge passes there were; a stage re-entered after
implementation. A delegated stage is started and ended here, by the host: the sub-agent's transcript is found from
this session's. A number the script could not read is `null` with its reason and stays that way — never fill one
in, and never pass `model=` when the record already names one. Start and end must bracket the work itself. Two
brackets open at once are told apart: a line goes to the innermost bracket covering it, and a delegate's lines to
the bracket whose stage owns the type that ran them, so a skipper round during implementation costs the skipper
and not the implementers. An entry a session leaves open is cut off — by the `/cruise` runner when the iteration
ends, and by the next `start` in the same record — with the reason, its tokens read from the transcript it left,
and no signals: nothing will close it truthfully afterwards. `{layout.make}
check-benchmark`, in `{layout.make} verify`, warns of an entry still open, a slice the ladder calls done with no
record or an unclosed one, and a feature with done slices and no record above the slice loop — warns, never fails,
because a bracket missed cannot be taken afterwards. Close
`adversary` after its findings are triaged and before any fix, passing `findings=N` and `seams=N`; each
failing test and fix belongs to a new
`implement` entry. Bracket `demo` around the actor's session, not the note afterwards, and `mutation` around the
run. A same-moment start and end is reported as `unbracketed`, not `0s`, and makes the slice wall a floor.

When the slice is archived, close its record:

```sh
python3 scripts/agents/benchmark.py close specs/<feature>/slices/<id>   # adds tasks, files and lines, prints the aggregate
```

Closing also redraws `specs/<feature>/benchmark.md`, the overview `/benchmark` writes on demand; `{layout.make}
benchmark` prints the same aggregate at any time — one row per slice: cost, converge passes, gaps, mutation score,
findings, demo outcome, rework, shape. Commit the record and the page with the slice. Nothing on either goes on the
demo board: cost is the team's, and the board is the actor's.
"""


def benchmark_command(layout: Layout = AT_ROOT) -> str:
    """`/benchmark`: the overview page, redrawn from the records and read back with the reading only a person or an
    agent can add — which stage the cost sits in, what moved between slices, whether the cheaper role paid for
    itself. The numbers come from the script; the words never add one the script did not write."""
    return f"""---
description: Draw the benchmark overview — what each slice cost and how each stage did — as a page beside the records
argument-hint: [feature]
---

# Benchmark

Every stage `/drive` runs is recorded in `specs/<feature>/slices/<id>/benchmark.json` (the stages above the slice
loop in `specs/<feature>/benchmark.json`). This command turns the records into the page a person reads, and reads
it back to them.

## Draw the page

```sh
python3 scripts/agents/benchmark.py overview $ARGUMENTS
```

With a feature named, that feature's page; with none, one page per feature that has a record. Each is
`specs/<feature>/benchmark.md`: the slices side by side — wall, tokens in and out, the models that ran, converge
passes, tasks appended, gaps before and after converge, mutation score, adversary findings, demo outcome, verify
failures, rework, sessions, tasks, files, lines — then every stage of every slice with the type and model that
ran it and what it reported, the notes (entries
still open, a stage re-entered after implementation, tokens the script could not read and why), and how to read
the numbers. The page is regenerated whole; never edit it, and never edit a record to change what it says. No
record yet is the script's own line, and the answer: nothing has been driven since the records began.

## Read it back

Show the slices table as the page has it, then say what it shows, in this order and only where the page
supports it:

- **Where the cost sits** — the stage or two that took most of the tokens and time, per slice, and whether that
  is the same stage every time.
- **What moved** — between one slice and the next, and across any change to a prompt, a skill, the layout or
  `.specify/models.json` the history records: cheaper or dearer, more or fewer converge passes, gaps found after
  converge, the mutation score. Host context grows through a session, so do not compare host tokens directly
  between slices spanning different numbers or lengths of sessions.
- **Whether the split paid** — where a stage ran on the `fast` role (`/model-delegation-settings` shows which), what it cost against
  the converge passes, verify failures and mutation score of the slices it ran in. A conclusion needs more than
  one slice; with one, say so.
- **What is unknown** — every `unknown` on the page, with the reason the record gives, and the harness or setting
  that would make it known. An unknown is never estimated.

Tokens are not prices, and the page compares this project on this harness with itself — say neither more nor
less. Then commit the page: `git add specs/<feature>/benchmark.md`, on its own or with the slice it follows.
`{layout.make} benchmark` prints the same table in the terminal without writing anything.
"""
