"""The adoption phases of `/sail`: what the ladder gains in a repository the method was installed around.

Brownfield adoption is a phase of the delivery loop rather than a step before it. A generated project starts at the top
of every ladder on the convergence map; an adopted one starts wherever it is, and the loop's job is to climb, one rung
per slice, until the two are the same thing. So `/sail` in an adopted repository has three more things to do, and they
are stages so that the "enter at the first incomplete stage" rule reaches them: **Ground** before Principles — no map,
no principles, and an unrecorded row on an axis the slice touches is a question before anything else; **Pin** before
Implementation — code that was here is changed only once `/characterise` has recorded what it does at the seam; and
Convergence re-checks the map after the slice, flips the row a rung was reached on, and offers the next unplanned row as
a method slice. The hooks in `.specify/extensions.yml` say the same three things to whoever typed a `/speckit-*` command
without ever typing `/sail`.

The words are `assets/adoption/sail/`: `stages.md`, one section per stage or addendum, and `hooks.yml`, the
three hooks appended to the file Spec Kit reads. An asset of the adoption rather than of the toolkit for the
reason `ground_command.py` gives — everything under `assets/toolkit/` is copied into every project, and only
an adopted one is written over here, so a page kept there would reach a generated repository raw. `stages.md`
is a page of parts rather than a page: none of it lands anywhere on its own; each section is spliced into
`commands/sail.md` beside the stages the ladder already had.

What is left here is the placing. Which stage each addendum joins is found by the stage's own title rather
than by position, so the ladder's order holds whatever a profile adds between them, and that is code about
behaviour and not a paragraph anybody edits.
"""
from __future__ import annotations

from ..assets import ADOPTION_ROOT
from ..layout import AT_ROOT, Layout
from ..services import App, wrapped_of
from .observe_command import observation_stage
from .prose import page, part

MAP = "docs/convergence.md"
#: Where the adoption's own words for the ladder live: the stages as parts, the hooks as the file they join.
SAIL = ADOPTION_ROOT / "sail"
STAGES = "stages.md"


def wrapped_paths(apps: list[App]) -> str:
    return ", ".join(f"`{app.path}/`" if app.path != "." else "the repository root" for app in wrapped_of(apps))


def values(apps: list[App] | None = None, layout: Layout = AT_ROOT) -> dict[str, str]:
    """Every value a part or hook under `assets/adoption/sail/` may name, and the whole of what one may.

    Two spellings of the wrapped paths, not one: a stage that names a single application and one that names
    them all each fall back to their own words where nothing was wrapped, which is a sentence agreeing with a
    count and so stays here rather than in the asset.
    """
    apps = [] if apps is None else apps
    paths = wrapped_paths(apps)
    return {
        "map": MAP,
        "convergence": layout.under(MAP),
        "drive": layout.under("commands/sail.md"),
        "pinned": layout.under("survey/pinned.md"),
        "running": layout.under("survey/running.md"),
        "retirement": layout.under("retirement.md"),
        "programme": layout.under("docs/change-strategy.md"),
        "wrapped-or-one": paths or "a wrapped application",
        "wrapped-or-many": paths or "the wrapped applications",
    }


def stage(name: str, apps: list[App], layout: Layout) -> str:
    """One section of `stages.md`, rendered for this repository."""
    return part(SAIL, STAGES, name, values(apps, layout))


def adoption_ladder(stages: list[str], apps: list[App], layout: Layout) -> list[str]:
    """The `/sail` ladder with the adoption phases in it: Ground first, the Plan stage holding the slice's home to
    the decided strategy, Pin before Implementation, the Implementation stage saying how new code beside what was
    here is tested, and the Convergence stage re-checking the map. The stages are found by their titles, so the
    ladder's own order holds whatever a profile adds between them."""
    ladder = [stage("ground", apps, layout), *stages]
    for index, found in enumerate(ladder):
        if found.startswith("**Event model**"):
            ladder[index] = found.rstrip() + observation_stage(layout)
    plan = next(index for index, found in enumerate(ladder) if found.startswith("**Plan and tasks**"))
    # Under an accepted `strangler-fig` the slice's home is a new one, and the Plan stage says so. The first
    # strangler adoption accepted the ADR by the person's word and then built five product slices in the WAR
    # it was meant to strangle: `split.md` called the home "a working assumption to confirm at plan time",
    # and the plan confirmed it alone.
    ladder[plan] = ladder[plan].rstrip() + stage("plan", apps, layout)
    implementation = next(index for index, found in enumerate(ladder) if found.startswith("**Implementation**"))
    # New code beside what was here is tested with fakes and the ecosystem's current runner. The second real
    # adoption asked "what should I add?" over a JUnit 3 tree at exactly this stage, and the answer it reached
    # for was JUnit 4 with Mockito: the rule against a mocking framework lived in `/characterise`, which new
    # code never reads, and nothing said *current*.
    ladder[implementation] = ladder[implementation].rstrip() + stage("implementation", apps, layout)
    ladder.insert(implementation, stage("pin", apps, layout))
    convergence = next(index for index, found in enumerate(ladder) if found.startswith("**Convergence**"))
    ladder[convergence] = ladder[convergence].rstrip() + stage("map", apps, layout)
    return ladder


def adoption_hooks(extensions: str, apps: list[App], layout: Layout) -> str:
    """`.specify/extensions.yml` with the adoption's hooks appended: the map before a specification is written,
    the pin before a plan is, and the map again after converge. All three print rather than run — each says what
    `/sail` already does, for the session that entered the loop through a `/speckit-*` command instead."""
    last = extensions.rfind("\n  after_")
    assert last != -1 and extensions[last:].startswith("\n  after_converge:"), "after_converge is no longer last"
    return extensions.rstrip("\n") + page(SAIL, "hooks.yml", values(apps, layout))
