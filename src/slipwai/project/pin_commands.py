"""`commands/characterise.md` and `commands/survey.md`: the Pin stage of adopting the method around code that existed before it.

Only an adopted repository (brownfield adoption) gets these commands. `/characterise` scopes the shipped
`characterisation-tests` and `finding-seams` skills to the one behaviour a slice is about to change, at the seam where
it can be observed, and refuses "full coverage first" — which is where these programmes die. `/survey` runs the
factory's `adopt --refresh` the way `/add-service` runs `add-service`, and reconciles what a fresh survey finds with
what `project.json` recorded: a fact recorded as detected is refreshed, a fact a person confirmed or overrode is never
changed behind their back. Both write to `survey/`, beside the survey `adopt` left: `pinned.md` is the ledger of what
has been pinned, and `survey.md` is the survey as it stands. On the event profile `/observe` reads one pinned
capability into the model, with its source evidence, before a requirement changes it.

Both pages are assets — `assets/adoption/commands/` — and what is left here is which value each may name
and which of its sections this repository gets. The ledger `adopt` writes is not one: it lands at
`survey/pinned.md` rather than under `commands/`, and the page a project receives there is written once,
by the command that adopts, rather than regenerated.
"""
from __future__ import annotations

from ..assets import ADOPTION_ROOT
from ..layout import AT_ROOT, Layout
from ..services import App, wrapped_of
from .observe_command import observe_command
from .prose import page

# Where the pages live. An asset of the adoption rather than of the toolkit, for the reason
# `strangle_command.py` gives: everything under `assets/toolkit/` is copied into every project and
# only an adopted one is written over here, so a page kept there would reach a generated repository
# raw, with its `{{make}}` still in it — and a greenfield project has nothing that was here to ask
# about anyway.
COMMANDS = ADOPTION_ROOT / "commands"

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


def values(apps: list[App] | None = None, layout: Layout = AT_ROOT) -> dict[str, str]:
    """Every value the two pages here may name, and the whole of what one may name: how each application
    runs its tests, read off `project.json`, and the three paths that move when a project keeps its
    delivery material in a subdirectory."""
    apps = [] if apps is None else apps
    return {
        "test-commands": test_commands(apps),
        "ledger": layout.under("survey/pinned.md"),
        "survey-page": layout.under("survey/survey.md"),
        "structure-page": layout.under("survey/structure.md"),
    }


def characterise_command(apps: list[App], layout: Layout) -> str:
    return page(COMMANDS, "characterise.md", values(apps, layout))


def survey_command(apps: list[App], layout: Layout, event: bool) -> str:
    """The reading of what was here is a whole section: on the event profile the code that existed before
    the method is an external system or a state-stored service of this project, and on the standard one
    there is no model for it to be either in."""
    return page(COMMANDS, "survey.md", values(apps, layout), ("event-model",) if event else ())


def pin_command_files(apps: list[App], layout: Layout, event: bool) -> dict[str, str]:
    """Adoption's two survey/pin commands, plus capability observation on the event profile."""
    files = {
        "commands/characterise.md": characterise_command(apps, layout),
        "commands/survey.md": survey_command(apps, layout, event),
    }
    if event:
        files["commands/observe.md"] = observe_command(apps, layout)
    return files
