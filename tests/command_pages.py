"""The matrix every `commands/*.md` is rendered across, and the digests of what came out.

Not a test module — `unittest discover` collects `test_*.py` only. This is the reading `test_command_pages.py`
compares against `tests/fixtures/command-pages.sha256`, and it is a file rather than a one-liner because the
pages the commands slice moves branch on five things at once: the profile, whether a service keeps its events,
whether the project has a browser app or any application at all, whether its destination is managed, where the
delivery material sits, and whether the repository adopted the method around code that was already here.

Run it to take the reading:

    PYTHONPATH=src:tests python3 tests/command_pages.py

Every case is named, and the name is what the record's middle column carries, so a row that fails says which
project the page belonged to rather than only which file.
"""
from __future__ import annotations

import hashlib

import checkout_packages  # noqa: F401

from slipwai.layout import Layout
from slipwai.origin import Adoption
from slipwai.project.commands import command_files
from slipwai.project.ground_command import ground_command_files
from slipwai.project.pin_commands import pin_command_files
from slipwai.selection import Selection
from slipwai.services import APPLICATIONS, App, service_app

# The one backend a checkout pins. Which language a service speaks changes none of these pages: what they
# read off a service is its rung, its purpose and its contexts, and `mutation.md` — which this slice does not
# move — is the only one that asks what it is written in.
BACKEND = "toy-plain"


def service(rung: str = "state", name: str = "service", first: bool = True) -> App:
    """A generated service on the rung named: `events` is what `sourced_services` reads."""
    return service_app(name, BACKEND, 8000, Selection({"write-model": rung}), first=first,
                       purpose="the shop's orders", contexts=("orders",))


def browser(name: str = "web", api: str = "service") -> App:
    """A browser app, built here rather than through `web_app`, which asks for a browser language this
    checkout does not pin. Every page that names one reads its name, path, port and `api` and nothing else."""
    return App(name, f"{APPLICATIONS}/{name}", "web", "typescript", "react-vite", 5173, api=api, first=True)


def wrapped(name: str = "shop", command: str | None = "npm test", version: str | None = "20") -> App:
    """An application that was here before the method was: what `/characterise`, `/survey` and `/ground`
    are written about."""
    return App(name, ".", "service", "javascript", None, 0, generated=False,
               commands={"test": command, "smoke": None},
               toolchain={"kind": "node", "version": version} if version else {},
               provenance={"kind": "confirmed", "commands": "detected"})


CANDIDATES = [
    {"name": "shop", "path": ".", "language": "javascript", "kind": "service", "commands": {},
     "toolchain": {}, "evidence": "package.json", "roleEvidence": "a server entry point",
     "writeModel": "events", "writeModelEvidence": "@eventstore/db-client in package.json"},
    {"name": "assets", "path": "assets", "language": "javascript", "commands": {}, "toolchain": {},
     "evidence": "package.json"},
]
MAP = [
    {"axis": "integration", "rung": "long-lived", "provenance": "unrecorded", "evidence": None},
    {"axis": "safety-net", "rung": "tests-exist", "provenance": "confirmed", "evidence": "they said so"},
]

#: One entry per project the pages are rendered for: the profile, the applications, the destination, where
#: the delivery material sits, and the adoption record where there is one. Between them they reach every
#: branch the five modules make — a service with a log and one without, a project with a browser app, one
#: without and one with no application at all, a managed destination and none, both layouts, and an adopted
#: repository with candidates outstanding and one with none.
CASES: dict[str, dict] = {
    "standard": dict(event=False, apps=[service(), browser()], target="none", delivery=".", adoption=None),
    "event": dict(event=True, apps=[service("events"), browser()], target="none", delivery=".", adoption=None),
    "event-state": dict(event=True, apps=[service()], target="none", delivery=".", adoption=None),
    "event-two-services": dict(event=True, apps=[service("events"), service("state", "billing", False),
                                                 browser(), browser("admin", "billing")],
                               target="aws", delivery="delivery", adoption=None),
    "standard-managed": dict(event=False, apps=[service()], target="azure", delivery=".", adoption=None),
    "no-applications": dict(event=False, apps=[], target="none", delivery=".", adoption=None),
    "adopted": dict(event=True, apps=[wrapped()], target="existing", delivery="delivery",
                    adoption=Adoption(why="the runtime is out of support", candidates=CANDIDATES,
                                      convergence=MAP)),
    "adopted-settled": dict(event=False, apps=[wrapped("legacy", None, None)], target="none", delivery=".",
                            adoption=Adoption(candidates=[], convergence=MAP)),
}


def pages(case: str) -> dict[str, str]:
    """Every command page that project receives from the five modules this slice moves."""
    given = CASES[case]
    layout = Layout(given["delivery"])
    apps, event, adoption = given["apps"], given["event"], given["adoption"]
    rendered = dict(command_files(event, apps, given["target"], layout, adoption))
    rendered.update(pin_command_files(apps, layout, event))
    if adoption is not None:
        rendered.update(ground_command_files(apps, layout, adoption))
    return rendered


def record() -> str:
    """The reading, one line per page: digest, case, path."""
    return "\n".join(
        f"{hashlib.sha256(text.encode('utf-8')).hexdigest()}  {case}  {path}"
        for case in CASES
        for path, text in sorted(pages(case).items())
    )


if __name__ == "__main__":  # pragma: no cover
    print(record())
