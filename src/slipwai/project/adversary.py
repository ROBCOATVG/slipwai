"""`commands/adversary.md`: select and attack only the seams a slice widened.

The page is the asset's own words now (`assets/toolkit/commands/adversary.md`); what is left here is which
of its sections this project gets. The trigger table is the whole of the page's selection rule, so what is
*in* it has to be reachable on the services this project actually has. A row naming a stream identity on a
project whose services keep current state is a row every slice marks `not present`, which teaches the reader
to skim a table they are supposed to be answering honestly — so the rows follow each service's rung
(plan 15.3).

Three places on the page say the same thing about one rung — the surface list, the trigger table and the
scope of the pass — so a rung is three sections rather than one: a section is named once per page, and these
are three spans with standing text between them rather than one span that happens to be interrupted.
"""
from __future__ import annotations

from ..assets import TOOLKIT_ROOT
from ..services import App
from .prose import page
from .write_model_prose import sourced_services, state_services

# Where the page lives: beside the commands a project has always received verbatim.
COMMANDS = TOOLKIT_ROOT / "commands"
#: Where each rung speaks on the page, in the order the page carries them.
PLACES = ("surface", "trigger", "pass")


def adversary_command(event: bool, apps: list[App]) -> str:
    logged, stored = (sourced_services(apps), state_services(apps)) if event else ([], [])
    wanted = tuple(
        f"{rung}-{place}"
        for rung, present in (("logged", logged), ("stored", stored))
        if present
        for place in PLACES
    )
    return page(COMMANDS, "adversary.md", {}, wanted)
