"""`commands/characterise.md` and `commands/survey.md`: the Pin stage of adopting the method around code that existed before it.

Only an adopted repository (brownfield adoption; experimental as `AGENTS.md` defines the word) gets these
two. `/characterise` scopes the shipped `characterisation-tests` and `finding-seams` skills to the one
behaviour a slice is about to change, at the seam where it can be observed, and refuses "full coverage first"
— which is where these programmes die. `/survey` runs the factory's `adopt --refresh` the way `/add-service`
runs `add-service`, and reconciles what a fresh survey finds with what `project.json` recorded: a fact recorded
as detected is refreshed, a fact a person confirmed or overrode is never changed behind their back. Both write
to `survey/`, beside the survey `adopt` left: `pinned.md` is the ledger of what has been pinned, and
`survey.md` is the survey as it stands.
"""
from __future__ import annotations

from ..layout import Layout
from ..services import App, wrapped_of
from .add_commands import FACTORY

PINNED_LEDGER = """# Pinned behaviour

What `/characterise` has pinned, one row per behaviour: the current behaviour of code that existed before
the delivery method did, recorded at the seam where it can be observed, so that a change to it can be told
apart from a regression. A slice reads this before it changes code that is here; `/strangle` reads it when a
behaviour moves. Rows are appended, never rewritten — a behaviour that stopped being pinned says so in a new row.

| Date | Behaviour | Seam | Tests | Runs with |
|---|---|---|---|---|
"""


def test_commands(apps: list[App]) -> str:
    """How each application's recorded `test` command runs its tests — the command the characterisation tests
    have to be reachable from — or the fact that none is recorded."""
    lines = []
    for app in wrapped_of(apps):
        command = (app.commands or {}).get("test")
        lines.append(
            f"- `{app.name}` (`{app.path}`, {app.language}): "
            + (f"`{command}`" if command else "no `test` command recorded — the first characterisation test is also "
               "the moment to record one, in `project.json`, or nothing runs it")
        )
    return "\n".join(lines) or "- no application that existed before the method is recorded here"


def characterise_command(apps: list[App], layout: Layout) -> str:
    ledger = layout.under("survey/pinned.md")
    return f"""---
description: Pin the current behaviour of the code a slice is about to change, at the seam where it can be observed, before changing it
argument-hint: <the behaviour about to change, and where it is observed>
---

# Characterise

Read `skills/characterisation-tests/SKILL.md` and `skills/finding-seams/SKILL.md`. This command scopes them
to one behaviour: the one a slice is about to change. It is the Pin step of adopting the method around code
that existed before it (`docs/adoption.md`) — tests that record what the code does now, including what is
ugly, so that a change can be told apart from a regression.

## Refuse "full coverage first"

If `$ARGUMENTS` is empty, or names the whole system — "everything", "the service", "all of it" — stop and
ask: which behaviour is about to change, and for whom? Characterising a whole legacy system before touching
it is where these programmes die. A behaviour is pinned because a slice needs it pinned, and the slice names
it; the answer is the argument to run this command again with.

## Find the seam

Observe; do not restructure. The seam is the boundary where the current behaviour can be recorded without
changing the code: the HTTP boundary (request in, response out), the database (the rows a use case writes),
the messages it emits, the files it writes, the reports it produces. Prefer the widest seam that stays
deterministic. Where nothing is deterministic — time, generated ids, ordering — `finding-seams` says how to
introduce the smallest seam that makes it so, and that seam is itself a change to record in the ledger.

## Doubles are fakes you write, not a framework you add

What stands in for the outside world at the seam is never a mocking framework. A collaborator that has to be
replaced — a clock, a repository, a gateway to another system — is replaced by a **fake**: a small
implementation of its real interface, written in the test tree, that holds state and answers from it
(`skills/hexagonal-architecture/resources/testing-hex-arch.md`, "Fakes, Not Mocks"). A test that asserts
which methods were called, in what order, with what arguments, records the code's shape and not its
behaviour, and breaks on exactly the refactoring it exists to make safe. So this command never adds
Mockito, Moq, gomock, `unittest.mock`, `jest.mock` or `vi.mock` to a repository and never recommends one:
the skills it reads show their last-resort module seam in Vitest, and that seam's counterpart in another
language is the same last resort, not the first move. A repository that already has such a framework keeps
the tests it has; the pinned tests are written without it. A repository with no tests at all gets its
ecosystem's own runner — JUnit 5, pytest, `go test`, `dotnet test`, `node --test` — and no second
dependency: that is the `tests-exist` rung, and it is one row in the ledger.

## Pin it

Write the characterisation tests in the application's own test tool, where its tests already are, so that the
recorded `test` command reaches them:

{test_commands(apps)}

Approval-style where the output is large. Record actual behaviour, never desired: a test that fails because
the code is wrong is written to pass, with a comment saying the behaviour is wrong and a question for the
person through `/gaps`. Run them, then `make verify`.

## Record it

Append one row to `{ledger}`: today's date, the behaviour, the seam, the test files, and the command that
runs them. Never rewrite an earlier row; a behaviour that is no longer pinned gets a new row saying so.

## Then

The pinned behaviour is what the slice may now change. `/drive` continues with the plan, and the
characterisation tests are the ones that keep passing until the plan says which of them change, and why.
"""


def survey_command(apps: list[App], layout: Layout, event: bool) -> str:
    page = layout.under("survey/survey.md")
    view = layout.under("survey/structure.md")
    model = """
## The event model

This project keeps a global event model in `docs/event-model/model.yaml`. The code that existed before the
method is an **external system** in it — never a set of invented events. Read `skills/event-modeling/SKILL.md`
first. Where a slice needs what the legacy system does, model it as the translation pattern that skill
describes: an event marked `external: true` for what the legacy system emits or exposes, the process that
reads it, and the command and event that are this project's own. Nothing in the legacy system's tables or
tables' history becomes an event by being renamed; `docs/adoption.md` says why that honesty matters here.
""" if event else ""
    return f"""---
description: Re-survey this repository with the factory and reconcile what it finds with what project.json records
---

# Survey

This repository adopted the delivery method: `project.json` records what the factory's survey detected about
the code that was here and what the person confirmed or overrode, each fact with its provenance. Code
changes; the survey is re-run, and the record is reconciled with it — refreshed where it was only detected,
questioned where a person decided. Run this when a build tool, a language, a schema tool or a deployment
description appears, moves or goes.

{FACTORY.format(verb="adopt --refresh", stop="A wrong guess at its location is a stop, not a reason to edit `project.json` by hand from memory.")}

## Run it

1. `git status --porcelain` prints nothing. The command refuses an unclean tree so that `git checkout . &&
   git clean -fd` undoes exactly what it wrote and nothing else.
2. `slipwai adopt --refresh`, from this directory.
3. Read its report, which has three kinds of line.

## Read the report

- **Refreshed.** A fact recorded as `detected` that the tree now says differently was updated in place —
  a command the build gained, a toolchain pin that moved — and the files that read it were regenerated.
  Nothing to decide; `git diff` shows what changed.
- **Disagrees.** A fact a person `confirmed` or `overrode` that a fresh detection contradicts. It was **not**
  changed. Put the two side by side for the user — what was recorded, what the tree says, and the evidence —
  and record the answer: edit `project.json`, keeping the provenance honest (`confirmed` if the recorded
  value stands, `overridden` if they chose the new one), then run this command again so the files follow.
- **Not wrapped.** A directory that builds and has no record. Adding it is a decision, not a refresh: ask
  whether it is part of this system, and if so add its record to `project.json`'s `deployables` as
  `"generated": false` with the commands the report shows, then run this command again.

`{page}` was rewritten as the survey now stands, with the evidence for every line, and `{view}` — the
architecture view: where anything starts, what depends on what, where change happens — from the tree, the Git
history and CodeGraph's index where `.codegraph/` holds one.
{model}
## Then

- `make verify` — the gate still holds after the record moved.
- Commit the result as one change, saying what the survey found and what was decided.
"""


def pin_command_files(apps: list[App], layout: Layout, event: bool) -> dict[str, str]:
    """The two commands an adopted repository has that a generated one does not."""
    return {
        "commands/characterise.md": characterise_command(apps, layout),
        "commands/survey.md": survey_command(apps, layout, event),
    }
