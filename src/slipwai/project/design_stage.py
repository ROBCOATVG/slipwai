"""The two design rungs of `commands/drive.md`: the screen decided before it is built, and reviewed rendered
before the demo.

Its own module for the reason `converge_stage.py` is: the text exists because of evidence. Three new screens —
an editor, a list and a printable sheet — reached their demo with every `check-ux-gates` gate green, and still
showed default-blue links, labels crammed against their fields, a raw UUID and a diagram drawn as a bare
rectangle. The design skills were installed and `AGENTS.md` named them; no rung asked for them to run, so a
delegate briefed from the plan styled from the tokens, ran the gates, and read the silence conservatively. So
the review is a rung, with a record in `tasks.md` like the convergence verdict, which is what makes it
impossible to skip silently and unnecessary to repeat.

The rungs name only what every project with a browser app carries: `skills/frontend-design` and
`skills/web-interface-guidelines`. An extension that brings more to a rung — `uipro`'s search before the
build, `ux-gates`' gates and checklists before the demo — says so in its own `AGENTS.md` block, written when
it is adopted, so a project that never adopted one never reads about it. Absent where there is no browser app:
a rung nothing can fail teaches the reader to skim the rest.
"""
from __future__ import annotations

# What the *Plan and tasks* rung adds where there is a browser app: styling is one of the slice's tasks.
PLAN_STYLING = """ Where the slice puts anything on a screen, its styling is one of the tasks written here rather
   than a follow-on: name the screens it adds or changes and where each takes its styles from."""


def screen_design_stage(baseline: str) -> str:
    """The `**Screen design**` rung, between the plan and the implementation: what each screen is to look like."""
    return f"""**Screen design** — `tasks.md` has a `## Design review` heading with a `Designed:` line for
   every screen the slice adds or changes, or the one line `No screen in this slice`. Otherwise decide each
   screen before any code for it is written. Read `docs/design.md` first, and write into it any decision this
   screen needs that it does not hold — a pattern, a layout, a component — doing what an extension block in
   `AGENTS.md` adds to this rung as well. Then take the plan's screens through `skills/frontend-design`'s
   second pass — the review against the brief for the defaults that would appear whatever the product — and
   write what it changed into the plan. The line names the screen, where its styles come from
   (`docs/design.md`, the constitution's design notes, or the baseline in {baseline} extended) and what the
   second pass changed, or that it changed nothing and why. A screen with no decision is built on the
   browser's, and the implementer reads the silence as permission."""


def design_review_stage(baseline: str) -> str:
    """The `**Design review**` rung, after implementation and before convergence: the screens looked at."""
    return f"""**Design review** — the `## Design review` section has a `Reviewed:` line for every screen the
   slice adds or changes, or says `No screen in this slice`. Otherwise review what the actor will see, not the
   source: render each screen in {baseline} — the running app, reached the way `skills/run-the-app` records —
   take a screenshot of each state it can be in, and read the screenshots against
   `skills/web-interface-guidelines`, doing what an extension block in `AGENTS.md` adds to this rung as well.
   A passing gate is evidence for this stage, never the stage: screens with every automated check green have
   still shipped default-blue links, labels crammed against their fields, a raw identifier shown to the actor
   and a diagram drawn as a bare rectangle. So look for what a check cannot see — browser defaults anywhere,
   the space between a label and its field, a value the actor was never meant to read (an identifier, an
   enum's spelling, a raw timestamp), a figure with no labels, an empty state with nothing in it, one thing
   styled two ways. Fix each finding in this slice, or record it with a reason on the screen's line; a finding
   with neither is a demo that shows it. The line names the screen, the screenshots under
   `specs/<feature>/slices/<id>/design/`, what the review read, and what was fixed or recorded. A later task
   that changes a reviewed screen adds a line for it rather than leaving the old one to speak for it."""


def tasks_brief() -> str:
    """What the tasks delegate writes into `tasks.md` for a slice with a screen, inside its styling task."""
    return """The styling task names the design steps inside it, so a brief built from it
carries them: `skills/frontend-design`'s second pass over the plan before any code, and the review of the
rendered screens against `skills/web-interface-guidelines` before the demo — each with whatever an extension
block in `AGENTS.md` adds to `/drive`'s *Screen design* or *Design review* rung. Leave a `## Design review`
heading for the `Designed:` and `Reviewed:` lines those rungs write, or `No screen in this slice` under it
where the slice has none."""


def with_design_rungs(stages: list[str], baseline: str) -> list[str]:
    """The ladder with *Screen design* before *Implementation* and *Design review* after it — around the
    implementation rather than after convergence, because the review's fixes are code converge should see, and
    the screen is decided before a delegate builds it on the browser's defaults."""
    at = next(index for index, stage in enumerate(stages) if stage.startswith("**Implementation**"))
    return [*stages[:at], screen_design_stage(baseline), stages[at], design_review_stage(baseline), *stages[at + 1:]]
