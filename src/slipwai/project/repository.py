"""`LICENSE`, `SECURITY.md` and the pull-request template: what a repository owes whoever arrives at it.

Three files that every repository is expected to have and that a scaffolder can only half-write, because
each of them states a decision that belongs to the people who own the code. What is written here is the
honest half — the shape, the project's own name, and what the project actually asks of a change — with the
half that is not the factory's marked as the owner's to take.

**The licence is the sharpest case.** A generated project is the customer's, and a permissive licence written
in by a generator would be a grant nobody made — irrevocable, and made by a tool. There is no licence axis
and this file does not invent one: the default is `All rights reserved`, which is the position a repository
with no licence file is already in, stated clearly instead of by omission, and the file says how to replace
it and where to record the decision when it is taken. The year and the project's name are filled in because
those the factory does know.

**The pull-request template names what this project actually asks**, which is not a list of good intentions.
`make verify` is the gate; the event model, the expand/contract rule and the ADR test are gates or documented
rules this project has; and the record of a change is the slice's own artifacts under `specs/`. It says
plainly that the project keeps no `CHANGELOG.md` of its own, because the alternative — a checklist item
pointing at a file that does not exist — is how a template becomes something people tick without reading.
"""
from __future__ import annotations

import datetime

from ..catalog import CATALOG
from ..services import App, needs_environment, services_of
from ..targets import managed

# What a repository with no licence decision is, said rather than left to be inferred from a missing file.
# Not a licence: a licence grants, and nothing here grants anything.
DEFAULT_LICENCE = "All rights reserved"


def licence(project_name: str, today: datetime.date | None = None) -> str:
    """`LICENSE`: the default until the owner decides, with this project's name and this year in it."""
    year = (today or datetime.date.today()).year
    return f"""Copyright (c) {year} the maintainers of {project_name}

{DEFAULT_LICENCE}.

No licence is granted by this file, and that is deliberate rather than an omission. A licence
is the decision of whoever owns this code — is it proprietary, is it delivered to a customer
under a contract that says what they may do with it, is it to be open source — and a tool that
scaffolded the repository is not in a position to take it. A permissive licence written in by a
generator would be a grant nobody made, and a grant is hard to take back.

"{DEFAULT_LICENCE}" is where a repository with no licence file already stands, stated clearly
instead of by silence. It is the safe default and it is not the answer; replace this file when
the decision is taken.

When it is: take the licence text from its own source (https://spdx.org/licenses/) rather than
from a copy, put the owner's name in it rather than the project's, and record the decision in
`docs/adr/` with the rest of this project's decisions — a licence is exactly the kind of choice
that is expensive to reverse once code has been shared under it.
"""


def security_policy(project_name: str) -> str:
    """`SECURITY.md`: how a vulnerability reaches the people who can fix it, without becoming public first."""
    return f"""# Security policy

How to report a vulnerability in {project_name}.

## Reporting

**Do not open an issue or a pull request for a security problem.** An issue is public the moment it is
filed, and a pull request describes the fix and therefore the flaw. Either one tells everybody with
access to this repository about the vulnerability before there is a fix to deploy.

Report it privately instead:

> **Contact:** *replace this line with the address or channel this project actually uses — a security
> mailbox, a private issue tracker, or the maintainers' team channel.* Leaving a placeholder here is the
> same as having no policy: somebody who found a flaw will do the visible thing instead.

Include what you did, what happened, and what you expected — enough to reproduce it. If you have a
suggested fix, describe it rather than opening a branch.

## What to expect

- An acknowledgement that the report was received, so you know it did not vanish.
- An assessment of whether it is exploitable here and how far it reaches.
- A fix, and a deployment of that fix, before the details are made public.

Set the times this project commits to beside each of those; a policy with no timescale is a policy
nobody can tell has been missed.

## Scope

Everything in this repository: the services under `apps/`, the shared code under `packages/`, the
infrastructure and the delivery pipeline. A vulnerability in a dependency is in scope as far as this
project's use of it goes — `make audit` runs the ecosystem's own advisory check, and `renovate.json`
says how updates reach this repository.
"""


def pull_request_template(profile: str, apps: list[App], target: str) -> str:
    """`.github/PULL_REQUEST_TEMPLATE.md`: what this project asks of a change, and nothing it does not.

    Read by GitHub and by Gitea from the same path, which is where the workflows already are. Every line
    is a gate this project runs or a rule one of its own pages states, so that the list stays something
    worth reading rather than a set of good intentions.
    """
    checks = [
        "`make verify` passes here — the same gate CI runs, so a green local run is the whole of it",
    ]
    if profile == "event-modelling":
        checks.append(
            "the event model carries whatever this slice added or changed, `make check-model` agrees, and the "
            "committed canvas was regenerated with it — `make model-drawio`, which `make check-drawio` holds to "
            "(`docs/event-model/`)"
        )
    if any(service.selection.migrating_feature for service in services_of(apps)):
        checks.append(
            "a migration that contracts the schema names the earlier expand it completes — `make "
            "check-migrations` fails without it, and an expand and a contract do not belong in one release"
        )
    if managed(CATALOG, target):
        checks.append(
            "anything not ready to be on in production is behind a flag that is seeded off, and both paths "
            "are tested (`make check-flags`)"
        )
    # Of the trait rather than of any option's name: what earns this line is that the project has answers
    # configured through the environment at all — a database address, a tenant credential, an issuer.
    if needs_environment(apps):
        checks.append(
            "no credential, token or connection string is in the diff — everything an answer needs is read "
            "from the environment, and `.env.example` is the list of what to set, never of what it is set to"
        )
    checks += [
        "a decision here that would cost a migration rather than a refactor to reverse is recorded in "
        "`docs/adr/` (`skills/architecture-decisions/`)",
        "the pages that describe what changed were changed with it — `AGENTS.md`, `docs/architecture.md` "
        "and the slice's own artifacts under `specs/` are the record of this change",
    ]
    ticks = "\n".join(f"- [ ] {check}" for check in checks)
    return f"""## What this changes

<!-- The behaviour, not the diff: what somebody using this can now do, or no longer has to. Name the
     slice under `specs/` this belongs to, if it has one. -->

## Why

<!-- The decision behind it, or a link to where that decision is written down. -->

## Before merging

{ticks}

<!-- This project keeps no CHANGELOG.md of its own, and that is on purpose: the record of a change is the
     slice's artifacts under `specs/` plus, where it was a decision, an ADR under `docs/adr/`. The one
     changelog this repository reads is the factory's, which `slipwai migrate` and `/catch-up` bring in
     when a newer version of it has something for this project (`docs/evolving-the-project.md`). If this
     project starts publishing releases to somebody outside it, that is when it earns a changelog of its
     own — add the line here in the same change. -->
"""


def repository_files(project_name: str, profile: str, apps: list[App], target: str) -> dict[str, str]:
    """The three files, keyed by path."""
    return {
        "LICENSE": licence(project_name),
        "SECURITY.md": security_policy(project_name),
        ".github/PULL_REQUEST_TEMPLATE.md": pull_request_template(profile, apps, target),
    }
