"""`AGENTS.md` and `docs/architecture.md`, byte for byte, across the matrix a project can be generated in.

Slice 16.3 moves the standing text of `project/guidance.py` and `project/rules.py` out of Python string
literals and into `assets/guidance/`. `AGENTS.md` is the largest single page a project receives and the one
most often edited for wording, so the move is only worth doing if it changed nothing anybody receives — and
"generate before and after" cannot be run across one commit. The record beside this file is the before, taken
on the commit the move was written on top of, and these tests are the only reason it exists.

**What is recorded.** Both pages, over every combination of what makes them differ: the two profiles, the four
targets, the two deployment shapes, and twelve projects chosen so that every conditional block either page
has appears in at least one of them — none, one and two browser apps; one service and two; each store on each
rung; a transport; an identity realm and a users realm; and the mixed project where one service is
event-sourced and the next is state-stored. `docs/architecture.md` takes neither target nor shape, so it is
recorded once per profile and project rather than sixteen times over.

**What the matrix cannot reach on this machine, said rather than implied.** `packages/` here holds the toy
language fixture and the two targets, so every service in every row is `toy-plain`: the pages have one
backend's shape, not three. Two consequences follow, and both are left uncovered rather than faked. The
toy's transport publishes no API document, so `rules.api_contracts` is only ever exercised down its empty
branch and `rules.frontend_contract` only down the half that says there is no `packages/api-client`. And no
loaded family answers the npm workspace, so `services.web_app` refuses to build a browser app at all — the
browser rows below build one directly, in the language a browser app is written in, and `architecture`'s
shared-code paragraph is read through a stand-in for that family's registry answer. The stand-in changes one
paragraph of `docs/architecture.md` in every row that has a browser app, identically before and after, which
is what a before-and-after record needs of it; it does not touch the browser section itself.
"""
from __future__ import annotations

import hashlib
import unittest
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai.project import guidance
from slipwai.registry import SHARED_CODE, Family, registry
from slipwai.selection import Selection
from slipwai.services import App, service_app

RECORD = Path(__file__).resolve().parent / "fixtures/guidance-pages.sha256"

# The one backend `packages/` pins here. Every service in the matrix is written on it.
TOY = "toy-plain"
# What a browser app is written in. Named here because no loaded family answers the npm workspace, so
# `services.web_app` cannot be asked and the app is built directly.
BROWSER_FAMILY = "typescript"
# The paragraph that family's registry answer would supply. Fixed, so a row that has a browser app is
# compared against itself before and after rather than against whichever package happened to be installed.
BROWSER_SHARED_CODE = "A shared package of its own, which the browser app and nothing else consumes"


def browser(name: str, port: int, api: str, first: bool = False) -> App:
    return App(name, f"apps/{name}", "web", BROWSER_FAMILY, "react-vite", port, api=api, first=first)


def service(name: str, port: int, choices: dict[str, str], first: bool = False,
            purpose: str | None = None, contexts: tuple[str, ...] = ()) -> App:
    return service_app(name, TOY, port, Selection(choices), first=first, purpose=purpose, contexts=contexts)


#: One entry per shape of project either page branches on, built fresh per row because an `App` carries
#: what the pages read off it. A block of prose that no row here reaches is a block the record does not
#: hold, which is why these are chosen against the conditionals rather than against plausibility.
PROJECTS: dict[str, Callable[[], list[App]]] = {
    "bare": lambda: [service("service", 3000, {}, first=True)],
    "one-browser-app": lambda: [service("service", 3000, {}, first=True),
                                browser("web", 5173, "service", first=True)],
    "two-browser-apps": lambda: [service("service", 3000, {}, first=True),
                                 browser("web", 5173, "service", first=True),
                                 browser("admin", 5174, "service")],
    "transport": lambda: [service("service", 3000, {"http": "toy-serve"}, first=True)],
    "memory-events": lambda: [service("service", 3000,
                                      {"write-model": "events", "persistence": "memory"}, first=True)],
    "sqlite-events": lambda: [service("service", 3000,
                                      {"write-model": "events", "persistence": "sqlite"}, first=True)],
    "postgres-events": lambda: [service("service", 3000,
                                        {"write-model": "events", "persistence": "postgres"}, first=True)],
    "sqlite-state": lambda: [service("service", 3000,
                                     {"write-model": "state", "persistence": "sqlite"}, first=True)],
    "postgres-state": lambda: [service("service", 3000,
                                       {"write-model": "state", "persistence": "postgres"}, first=True)],
    "identity": lambda: [service("service", 3000, {"auth": "keycloak", "users": "keycloak"}, first=True)],
    "mixed-rungs": lambda: [
        service("orders", 3000, {"write-model": "events", "persistence": "postgres"}, first=True,
                purpose="takes the order", contexts=("ordering", "pricing")),
        service("billing", 3001, {"write-model": "state", "persistence": "sqlite"}),
    ],
    "everything": lambda: [
        service("orders", 3000,
                {"http": "toy-serve", "write-model": "events", "persistence": "postgres",
                 "auth": "keycloak", "users": "keycloak"},
                first=True, purpose="takes the order", contexts=("ordering",)),
        service("billing", 3001, {"http": "toy-serve", "write-model": "state", "persistence": "sqlite"},
                purpose="bills for what was ordered"),
        browser("web", 5173, "orders", first=True),
        browser("admin", 5174, "billing"),
    ],
}
PROFILES = ("standard", "event-modelling")
TARGETS = ("none", "existing", "aws", "azure")
SHAPES = ("liner", "skiff")


@contextmanager
def stood_in_for() -> Iterator[None]:
    """The registry `architecture` reads, with the browser family's shared-code answer stood in for.

    No language package checked out here answers the npm workspace, so the family a browser app is written
    in has no row in the registry and the paragraph naming it cannot be rendered. The answer is fixed above
    rather than taken from whatever is installed, so a row with a browser app is compared against itself.
    """
    held = registry()
    families = {**held.families, BROWSER_FAMILY: Family(BROWSER_FAMILY, {SHARED_CODE: BROWSER_SHARED_CODE})}
    with mock.patch.object(guidance, "registry", new=lambda: replace(held, families=families)):
        yield


def pages() -> dict[tuple[str, str], str]:
    """Every row of the matrix, as `(row, path in the generated project) -> the text a project receives`."""
    rendered: dict[tuple[str, str], str] = {}
    with stood_in_for():
        for name, build in PROJECTS.items():
            for profile in PROFILES:
                rendered[(f"{profile}/{name}", "docs/architecture.md")] = guidance.architecture(
                    profile, build())
                for target in TARGETS:
                    for shape in SHAPES:
                        rendered[(f"{profile}/{name}/{target}/{shape}", "AGENTS.md")] = (
                            guidance.agent_guidance(profile, build(), target, shape))
    return rendered


def recorded() -> dict[tuple[str, str], str]:
    """The record, as `(row, path) -> digest`, with its header read as the comment it is."""
    rows = {}
    for line in RECORD.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        digest, row, path = line.split()
        rows[(row, path)] = digest
    return rows


def record() -> str:
    """The record as it is written, so that re-taking it is one command rather than a transcription."""
    return "".join(
        f"{hashlib.sha256(text.encode('utf-8')).hexdigest()}  {row}  {path}\n"
        for (row, path), text in sorted(pages().items())
    )


class ByteForByteTest(unittest.TestCase):
    """What the generator rendered before the prose left the modules, and what it renders now."""

    def test_every_row_the_record_holds_is_still_rendered_the_same(self) -> None:
        rendered = pages()
        for (row, path), digest in sorted(recorded().items()):
            with self.subTest(row=row, file=path):
                self.assertIn((row, path), rendered,
                              f"{path} is recorded for {row} and no longer rendered")
                self.assertEqual(
                    hashlib.sha256(rendered[(row, path)].encode("utf-8")).hexdigest(), digest,
                    f"{path} is no longer the text recorded in {RECORD.name} for {row}")

    def test_the_record_covers_every_row_the_matrix_has(self) -> None:
        """A record that lost a row would pass by not asking about the page that changed."""
        self.assertEqual(sorted(recorded()), sorted(pages()))

    def test_the_matrix_spans_what_the_slice_claims_it_does(self) -> None:
        """The count, said out loud: both profiles, four targets, two shapes and twelve projects, with
        `docs/architecture.md` taken once per profile and project because it is given neither of the
        other two."""
        rows = recorded()
        self.assertEqual(len([key for key in rows if key[1] == "AGENTS.md"]),
                         len(PROJECTS) * len(PROFILES) * len(TARGETS) * len(SHAPES))
        self.assertEqual(len([key for key in rows if key[1] == "docs/architecture.md"]),
                         len(PROJECTS) * len(PROFILES))


class CoverageTest(unittest.TestCase):
    """That every conditional block either page has is in at least one row of the record.

    A digest gate proves only that what it covers did not move. This is the half that says what it covers:
    a block nobody's project in the matrix reaches could be rewritten during the move and these digests
    would all still match. Each line below is a sentence out of one branch, chosen to be unmistakable.
    """

    #: A phrase from each conditional block, and nothing from the standing text around them.
    BLOCKS = (
        "## Browser frontend",                           # the section both pages grow for a browser app
        "`project.json` lists the services",             # the second service's bullet
        "docs/design.md",                                # the frontend contract
        "there is no `packages/api-client`",             # the half of it this matrix can reach
        "A green gate is not a demonstration",           # a composed project
        "holds the app's own services behind an `app`",  # a project with containers
        "SQLite adapter carries its own schema",         # the event-sourced rung's store rules
        "`(stream_id, version)` unique constraint",
        "SQLite repository adapter carries",             # and the state-stored rung's
        "the no-lost-update guarantee is proved",
        "The HTTP adapter parses untrusted input",       # a transport
        "The OIDC flow in the auth adapter",             # an identity realm
        "External users sign in from the browser app",   # a users realm
        "A feature flag is what makes merging",          # a managed target
        "VITE_FLAG_<KEY>",                               # and its browser half
        "This skiff deploys one production environment",  # the skiff shape
        "## Per-slice continuation contract",            # both profiles' contracts
        "Use `/sail` to resume from the first missing",
        "The loop starts when any per-slice command",
        "make check-model` makes every slice",           # the model gate clause
    )

    def test_every_conditional_block_is_in_some_row_of_the_record(self) -> None:
        whole = "".join(pages().values())
        for block in self.BLOCKS:
            with self.subTest(block=block):
                self.assertIn(block, whole)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
