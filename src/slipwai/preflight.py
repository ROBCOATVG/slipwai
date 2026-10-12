"""What a production target needs on this machine, checked before a project is written.

Everything here is asked of the target, because a second cloud needs a different CLI and a different way of
saying where it deploys, and nothing else about the check changes. A target that answers neither needs
nothing beyond what any project needs, which is what `none` is.

A project going to a managed target is not finished until `./init` has pushed it and bootstrapped the
account, and that needs tools scaffolding itself does not: whatever applies the stacks, the cloud's own CLI,
and a way to configure the repository on the forge. Finding that out at the end of `./init`, with Spec Kit
installed and a repository half made, is the wrong moment; the right one is the moment the target
is chosen. So `generate` asks this module then — right
after the target question interactively, before anything is written from flags — and refuses with what is
missing and where to get it. `--skip-checks` is for the case where another machine will run `./init`.

Presence on the PATH is all that is checked. Whether `gh` is signed in or a token has the right scope is the
forge's to say, and `make bootstrap` says it plainly when the time comes.
"""
from __future__ import annotations

import os
import shutil
import subprocess

from .catalog import CATALOG
from .errors import GenerationError
from .loaded_targets import answer
from .target_protocol import REGION, TOOLS
from .targets import managed

FORGE = (
    "gh or GITEA_TOKEN",
    "a way to configure the repository the project is pushed to: `gh` on the PATH and signed in for GitHub, "
    "or GITEA_TOKEN set to a token with write access for Gitea",
    "https://cli.github.com/ · Gitea: Settings → Applications → Generate token",
)


def answers(probe: tuple[str, ...]) -> bool:
    """Whether the target's own CLI already knows the setting, from its configuration or a profile."""
    if shutil.which(probe[0]) is None:
        return False
    result = subprocess.run(list(probe), text=True, capture_output=True)
    return bool(result.stdout.strip())


def missing_for(target: str) -> list[tuple[str, str, str]]:
    """Every requirement this machine does not meet for the target, as (what, why, where).

    Nothing at all for a target that provisions nothing: `none` goes nowhere and `existing` goes somewhere
    the keel does not own, so neither has a CLI to sign in with, a region to be told, or a pipeline to
    configure on the forge. Asked before the target is known to be managed, this would refuse a local-only
    project for want of a tool nothing was ever going to run.
    """
    if not managed(CATALOG, target):
        return []
    found = [(tool, why, where) for tool, why, where in answer(target, TOOLS, default=()) or ()
             if shutil.which(tool) is None]
    region = answer(target, REGION)
    if region is not None:
        variable, probe, requirement = region
        if not os.environ.get(variable) and not answers(probe):
            found.append(requirement)
    if shutil.which("gh") is None and not os.environ.get("GITEA_TOKEN"):
        found.append(FORGE)
    return found


def check(target: str, skip: bool = False) -> None:
    """Refuse a target this machine cannot take a project to, naming each gap and the way past it."""
    if skip:
        return
    missing = missing_for(target)
    if not missing:
        return
    width = max(len(what) for what, _, _ in missing)
    rows = "\n".join(f"  {what.ljust(width)}  {why} — {where}" for what, why, where in missing)
    raise GenerationError(
        f"--target {target} needs more than this machine has:\n{rows}\n"
        f"Install what is missing and run again, or generate with --skip-checks if another machine will run "
        f"./init — which is where these are used (docs/requirements.md has the full table)."
    )
