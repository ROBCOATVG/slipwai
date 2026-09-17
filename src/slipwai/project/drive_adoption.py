"""The adoption phases of `/drive`: what the ladder gains in a repository the method was installed around.

Brownfield adoption (experimental as `AGENTS.md` defines the word) is a phase of the delivery loop rather
than a step before it. A generated project starts at the top of every ladder on the convergence map; an
adopted one starts wherever it is, and the loop's job is to climb, one rung per slice, until the two are the
same thing. So `/drive` in an adopted repository has three more things to do, and they are stages so that the
"enter at the first incomplete stage" rule reaches them: **Ground** before Principles — no map, no principles,
and an unrecorded row on an axis the slice touches is a question before anything else; **Pin** before
Implementation — code that was here is changed only once `/characterise` has recorded what it does at the
seam; and Convergence re-checks the map after the slice, flips the row a rung was reached on, and offers the
next unplanned row as a method slice. The hooks in `.specify/extensions.yml` say the same three things to
whoever typed a `/speckit-*` command without ever typing `/drive`.
"""
from __future__ import annotations

from ..layout import Layout
from ..services import App, wrapped_of

MAP = "docs/convergence.md"


def wrapped_paths(apps: list[App]) -> str:
    return ", ".join(f"`{app.path}/`" if app.path != "." else "the repository root" for app in wrapped_of(apps))


def ground_stage(apps: list[App], layout: Layout) -> str:
    return f"""**Ground** — this repository adopted the method around code that was already here, so before any
   principle is ratified the map says where it stands: `{MAP}` exists and `make check-convergence` is
   green (`adopt` wrote both; `/survey` redraws the page from `project.json`). No map, no Principles. Read
   the rows and name the ones this slice touches — a slice through {wrapped_paths(apps) or 'a wrapped application'}
   touches at least *Safety net*, *Structure* and *Strategy* — adding to or changing what was here is
   what a strategy is about, and a strategy the map only *recommends* is a question, never a default; a slice
   that changes how a change reaches production touches *Path to production*. A row whose provenance is
   `unrecorded` — or `detected`, the tree's reading and nobody's answer — on an axis the slice touches is a
   question for the person **before anything else**: the release path first of all, since a slice with no
   known path to production cannot be called releasable. **Asking is this stage's work, not a stop:** run
   `/ground` here, inside `/drive`, for the axes the slice touches — or with no argument, the first time, for
   every row a person has not placed — one row at a time, the evidence and the rungs shown first, each answer
   written where the record keeps it (`release`, `ci`, a deployable's `kind`, `why`, or the `convergence` row
   itself, provenance `confirmed`), then `/survey` so the record is followed. The stage is done when the rows
   the slice touches are `confirmed` or `overridden`, or the person has said they cannot place them; a row
   nobody can answer today stays as it is and is said so in the slice's specification — never filled in from context
   — and an ADR's `Accepted` is the person's word, never yours. Then continue down the ladder in the same run."""


def pin_stage(apps: list[App], layout: Layout) -> str:
    ledger = layout.under("survey/pinned.md")
    running = layout.under("survey/running.md")
    return f"""**Pin** — the slice changes code that existed before the method did (under
   {wrapped_paths(apps) or 'the wrapped applications'}) only once the current behaviour at the seam it changes is
   recorded: `{ledger}` carries a row for each behaviour `plan.md` says this slice changes, with the tests
   that pin it and the command that runs them. Otherwise run `/characterise <behaviour>` for each, one at a
   time — it refuses "everything", and so does this stage. Code the factory generated needs no pin: its
   tests are the pin. A slice that touches no code that was here passes this stage by saying so, and a slice
   that reaches a seam nothing can observe deterministically records the smallest seam it introduced in the
   same ledger. What stands in at the seam is a fake written in the test tree, never a mocking framework this
   stage would have to add — `/characterise` says why. This is the *pinned* rung of the safety-net axis,
   held per slice rather than claimed once. **And before any pin, the application has to start.** Where
   `{running}` still reads *Not yet proven* for the application the slice changes, or its record in
   `project.json` has no `smoke` command, this stage refuses the slice and says so: proving the run path and
   recording `smoke` is the programme's step right after the build, and it goes first — the one exception is
   the slice that proves it. A suite that never builds the context cannot see a constructor the container
   cannot call, and slices have shipped that way, converged and green, with an application that no longer
   started."""


def plan_addendum(apps: list[App], layout: Layout) -> str:
    """What the Plan stage adds in an adopted repository: under an accepted `strangler-fig`, the slice's home is a
    new one. The first strangler adoption accepted the ADR by the person's word and then built five product slices
    in the WAR it was meant to strangle — `split.md` called the home "a working assumption to confirm at plan time",
    and the plan confirmed it alone."""
    ledger = layout.under("retirement.md")
    return f""" In this repository the decided strategy governs the home too. Under an accepted `strangler-fig`,
   a product slice's *Structure Decision* names a deployable that is **not** one that was here (under
   {wrapped_paths(apps) or 'the wrapped applications'}) — a service `add-service` made beside them, current from day one,
   whose first capability moves through `/strangle` and writes `{ledger}` — or it quotes the owner's written
   exception for this slice, in their words. "Confirmed at plan time" by the plan alone is not a decision:
   a strangler that lands every slice in the old home is the old home with a new label, and
   `check-convergence` says so while the ledger stays empty."""


def map_addendum(layout: Layout) -> str:
    return f""" A slice that touched how an application starts — constructors, dependency injection,
   configuration, module registration, the build — has converged only once that application has started with
   the change in place: `make smoke` where a `smoke` command is recorded, the command `{layout.under('survey/running.md')}`
   holds otherwise, and a converged verdict that rests on the suite alone is not one. A runtime or a
   framework that moved a major version moves on the Platform row, as a slice of its own and never inside
   another — `/survey` reports a version that moved without the row planning it as a disagreement, and the
   slice that moved it is not converged until the row, or an ADR, owns the move. Then, because this repository is converging on what a generated one has, hold
   the map to what the slice did: run `make check-convergence` and read `{MAP}` against the diff. A rung this
   slice reached — a quarantined suite now green, a role now recorded, a release script now run by CI on
   every commit — flips its row: edit that row in `project.json`'s `convergence` (`rung`, `evidence` naming
   what established it, `provenance` `confirmed`, `planned` cleared), run `/survey` so the page follows, and
   `make ratchet-tighten` where fewer findings remain than the baseline records. A rung the slice did not
   reach stays where it is; the map is never moved to match a hope, and `make verify` fails a row the tree
   contradicts. Then offer the next slice. **An open `CRITICAL` in `specs/<feature>/adversary-log.md` comes
   first**, ahead of every product and method slice, until it is fixed or a person has deferred it in that row
   with their name and reason: one adoption pinned a defect that leaked one customer's account to another as a
   failing-if-fixed test and then spent a slice on an icon. Then the next method slice,
   from the programme `{layout.under('docs/change-strategy.md')}` carries (*The programme*), top first: a quick win — a secret in the tree the same day — then a build below the
   floor (Ant with its jars committed, to Maven or Gradle: first whatever the strategy), then an application
   nobody has proved starts (its run path written and `smoke` recorded: before any slice changes code that was
   here), then a product out of
   support, then a rung of the ladder or a tool the ecosystem has and nothing here runs, each paced as the
   decided strategy says; and, with the programme empty, the lowest map row still below its target with nothing
   `planned`. What is offered is written into the row's `planned` (or the step's evidence named in the slice) and
   handed to `/story-splitting` as a method slice for the split to place among the product slices — never ahead
   of all of them by default, a secret and an open `CRITICAL` excepted. A step that needs a decision nobody has
   made (a release path,
   a change strategy — the programme says *decide it first*) is offered as the question, not as work;
   `/survey` derives the programme again, so a step done is gone rather than ticked. Demo feedback that is
   neither a thing an actor does nor a rung of the map — an icon, a colour, a label — is a task in the next
   slice, never a slice with acceptance criteria of its own."""


def implementation_addendum(apps: list[App]) -> str:
    """What the Implementation stage adds in an adopted repository: new code beside what was here is tested with
    fakes and the ecosystem's current runner. The second real adoption asked "what should I add?" over a JUnit 3
    tree at exactly this stage, and the answer it reached for was JUnit 4 with Mockito: the rule against a mocking
    framework lived in `/characterise`, which new code never reads, and nothing said *current*."""
    return f""" In this repository new code beside what was here (under
   {wrapped_paths(apps) or 'the wrapped applications'}) is tested the way `AGENTS.md`, *Delivery method*, says: what
   stands in at a seam is a fake written in the test tree, never a mocking framework added for the purpose —
   Mockito, Moq, gomock, `unittest.mock` are the same last resort in every language, and "what should I add?"
   is never answered with one. The runner is the one the application records; where that is out of support
   (JUnit 3 or 4, nose, a runner nobody maintains) new tests use the ecosystem's *current* framework and keep
   the old tests running beside them — JUnit 5 through its vintage engine, pytest running `unittest` as it is
   — as a slice on the map's Platform row, never the next-oldest version chosen because the tree's vintage
   makes it usual."""


def adoption_ladder(stages: list[str], apps: list[App], layout: Layout) -> list[str]:
    """The `/drive` ladder with the adoption phases in it: Ground first, the Plan stage holding the slice's home to
    the decided strategy, Pin before Implementation, the Implementation stage saying how new code beside what was
    here is tested, and the Convergence stage re-checking the map. The stages are found by their titles, so the
    ladder's own order holds whatever a profile adds between them."""
    ladder = [ground_stage(apps, layout), *stages]
    plan = next(index for index, stage in enumerate(ladder) if stage.startswith("**Plan and tasks**"))
    ladder[plan] = ladder[plan].rstrip() + plan_addendum(apps, layout)
    implementation = next(index for index, stage in enumerate(ladder) if stage.startswith("**Implementation**"))
    ladder[implementation] = ladder[implementation].rstrip() + implementation_addendum(apps)
    ladder.insert(implementation, pin_stage(apps, layout))
    convergence = next(index for index, stage in enumerate(ladder) if stage.startswith("**Convergence**"))
    ladder[convergence] = ladder[convergence].rstrip() + map_addendum(layout)
    return ladder


def adoption_hooks(extensions: str, apps: list[App], layout: Layout) -> str:
    """`.specify/extensions.yml` with the adoption's hooks appended: the map before a specification is written,
    the pin before a plan is, and the map again after converge. All three print rather than run — each says what
    `/drive` already does, for the session that entered the loop through a `/speckit-*` command instead."""
    last = extensions.rfind("\n  after_")
    assert last != -1 and extensions[last:].startswith("\n  after_converge:"), "after_converge is no longer last"
    ledger, page, drive = layout.under("survey/pinned.md"), layout.under(MAP), layout.under("commands/drive.md")
    where = wrapped_paths(apps) or "the wrapped applications"
    return extensions.rstrip("\n") + f"""
    - extension: "convergence-map"
      command: "drive"
      description: "Hold the convergence map to what this slice did, and offer the next row"
      optional: true
      enabled: true
      prompt: >-
        This repository adopted the delivery method around code that was already here, and `{page}` is
        where it stands on each ladder a generated project sits at the top of. Now that the slice has
        converged, run `make check-convergence` and read the map against the diff. A rung this slice reached
        flips its row in `project.json`'s `convergence` (`rung`, `evidence`, `provenance` `confirmed`,
        `planned` cleared), then `/survey` redraws the page. A rung it did not reach stays: the map is never
        moved to match a hope. Then name the lowest row still below its target with nothing planned — that is
        the next method slice, offered to the split. `{drive}`, the Convergence stage, has the rule.

  before_specify:
    - extension: "convergence-map"
      command: "drive"
      description: "Read the convergence map before specifying: which rows does this slice touch or move?"
      optional: true
      enabled: true
      prompt: >-
        Read `{page}` before writing a word of the specification. A slice through {where}
        touches at least the Safety net, Structure and Strategy rows; a method slice moves exactly one row
        one rung, and says which in the row's `planned`. A row whose provenance is `unrecorded` or `detected` on
        an axis this slice touches is a question for the person before the specification is written, never a
        default — the release path first of all, and a change strategy the map only recommends;
        `/ground` asks it, one row at a time, and records the answer. `{drive}`, the Ground stage, has the
        rule; `/drive` enters there.

  before_plan:
    - extension: "pin"
      command: "characterise"
      description: "Wrapped code the plan will change is pinned at its seam before the plan is written"
      optional: true
      enabled: true
      prompt: >-
        The plan is about to say which code changes. Where that code existed before the method did (under
        {where}), its current behaviour at the seam is recorded first: `{ledger}` carries a row
        for each behaviour this slice changes, or `/characterise <behaviour>` writes one — one behaviour at a
        time, never "everything". Code the factory generated needs no pin. `{drive}`, the Pin
        stage, has the rule; a slice that touches no code that was here says so and moves on.
"""
