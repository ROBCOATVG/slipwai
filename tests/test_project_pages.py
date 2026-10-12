"""The README, `project.json`, the pages under `docs/` and the run-the-app skill, byte for byte.

Slice 16.4 moves standing text out of `docs.py`, `readme.py` and `run_skill.py` and into `assets/`, and
`docs/generated-prose.md` says the one thing a move like that owes: the new path reproduces the old bytes
exactly. "Generate before and after" cannot be run across one commit, so `tests/fixtures/project-pages.sha256`
is what these modules rendered at 074aa35, the commit this slice was written on top of, and the tests below
are the only reason that file exists.

**The matrix, and what it honestly covers.** Fifty-six combinations of six application sets, two profiles,
four target-and-shape answers and — for the set with no generated service, the only one whose pages read it —
two delivery layouts. The application sets are the branches these three modules actually have: a repository
the method was installed around and whose services the keel did not make; one service alone; a service with a
browser app; two services on different rungs with two browser apps; a service with no inbound transport,
which `run_skill` has a whole separate page for; and that same service with a browser app beside it, which is
the only combination that reaches the run skill's *there is no HTTP transport* section — a browser app alone
keeps the full page, and a transportless service alone is handed the separate one.

Two limits are worth stating rather than implying. The browser apps here are built as `App` directly instead
of through `services.web_app`, because that function asks for the browser language's package and this
checkout pins only the toy language and the two targets — the pages read the framework and the paths, which
are the same either way, so the bytes are the keel's own and not a fake's. And `toy-serve` is offered on the
`none` target alone, so a service that is both transported and bound for a cloud is a combination the
interview would not reach today; it is recorded anyway, because these are pure functions and the page a
second transport would make real is cheaper to hold now than to re-record later.
"""
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import checkout_packages

from slipwai.layout import Layout
from slipwai.project.docs import documentation_files
from slipwai.project.metadata import metadata
from slipwai.project.readme import readme
from slipwai.project.run_skill import RUNNING, run_skill, running_ledger
from slipwai.selection import Selection
from slipwai.services import App, service_app

RECORD = Path(__file__).resolve().parent / "fixtures/project-pages.sha256"
PROJECT = "harbour-shop"
TOY = "toy-plain"
#: The two rungs, each with a transport, and the third answer: a service with no inbound HTTP at all.
EVENTS = Selection({"write-model": "events", "persistence": "postgres", "http": "toy-serve"})
STATE = Selection({"write-model": "state", "persistence": "postgres", "http": "toy-serve"})
QUIET = Selection({"write-model": "state", "persistence": "postgres"})


def browser(name: str, port: int, api: str, first: bool = False) -> App:
    """A browser app as `project.json` records one, without asking for the language package this checkout
    has not got: `services.web_app` reads the browser language from a loaded package, and these pages read
    the framework, the path and the port, which are the same whichever package named the language."""
    return App(name, f"apps/{name}", "web", "typescript", "react-vite", port, api=api, first=first)


def adopted() -> list[App]:
    """A repository the method was installed around: nothing here was made by the keel."""
    return [
        App("legacy", "services/legacy", "service", "python", None, 0, generated=False,
            commands={"test": "pytest", "lint": None}),
    ]


def solo() -> list[App]:
    return [service_app("service", TOY, 3000, EVENTS, first=True)]


def with_browser() -> list[App]:
    return [service_app("service", TOY, 3000, STATE, first=True), browser("web", 5173, "service", first=True)]


def pair() -> list[App]:
    """Two services on different rungs, two browser apps: every plural in these pages at once."""
    return [
        service_app("orders", TOY, 3000, EVENTS, first=True),
        service_app("billing", TOY, 3001, STATE),
        browser("web", 5173, "orders", first=True),
        browser("admin", 5174, "billing"),
    ]


def quiet() -> list[App]:
    """A service with no inbound transport: the page `run_skill` writes when there is nothing to start."""
    return [service_app("service", TOY, 3000, QUIET, first=True)]


def quiet_browser() -> list[App]:
    """A browser app with nothing to proxy to: the one set where the run skill is the full page and still
    has no transport to describe, and the README offers a way to run it that starts no service."""
    return [service_app("service", TOY, 3000, QUIET, first=True),
            browser("web", 5173, "service", first=True)]


#: One row per application set, in the order the record carries them.
SETS = (("adopted", adopted), ("solo", solo), ("browser", with_browser), ("pair", pair),
        ("quiet", quiet), ("quiet-browser", quiet_browser))
PROFILES = ("standard", "event-modelling")
#: Where this project goes, and in what shape: nowhere, a repository that already deploys, a cloud in each
#: of the two shapes. Two clouds because the README is written round nouns each target answers for itself.
DESTINATIONS = (("none", "liner"), ("existing", "liner"), ("aws", "liner"), ("azure", "skiff"))


def combinations() -> list[tuple[str, str, str, str, str]]:
    """Every combination the record holds, as `(apps, profile, target, shape, delivery)`."""
    rows = [
        (name, profile, target, shape, ".")
        for name, _build in SETS
        for profile in PROFILES
        for target, shape in DESTINATIONS
    ]
    # The delivery layout reaches these pages only where no service was generated: `run_skill` then points at
    # the repository's own running ledger, and the path it prints is the one the layout moved.
    rows += [(name, profile, target, shape, "delivery")
             for name, _build in SETS[:1]
             for profile in PROFILES
             for target, shape in DESTINATIONS]
    return rows


def pages(apps: list[App], profile: str, target: str, shape: str, delivery: str) -> dict[str, str]:
    """Every file these three modules write for one combination, plus the manifest they are read beside."""
    layout = Layout(delivery)
    files = {
        "README.md": readme(PROJECT, profile, apps, target, shape),
        "project.json": metadata(PROJECT, profile, target, apps, layout),
        "skills/run-the-app/SKILL.md": run_skill(PROJECT, apps, layout),
        **documentation_files(PROJECT, profile, apps, target),
    }
    if wrapped := [app for app in apps if not app.generated]:
        files[RUNNING] = running_ledger(PROJECT, wrapped)
    return files


def rendered() -> dict[tuple[str, str], str]:
    """The whole matrix, as `(combination, path) -> text`."""
    built: dict[tuple[str, str], str] = {}
    sets = dict(SETS)
    for name, profile, target, shape, delivery in combinations():
        key = f"{name}/{profile}/{target}-{shape}/{delivery}"
        for path, text in pages(sets[name](), profile, target, shape, delivery).items():
            built[(key, path)] = text
    return built


def recorded() -> dict[tuple[str, str], str]:
    """The record, as `(combination, path) -> digest`, with its header read as the comment it is."""
    rows = {}
    for line in RECORD.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        digest, combination, path = line.split()
        rows[(combination, path)] = digest
    return rows


def lines() -> str:
    """The record as this checkout would write it — what the header's command prints."""
    return "".join(
        f"{hashlib.sha256(text.encode('utf-8')).hexdigest()}  {combination}  {path}\n"
        for (combination, path), text in sorted(rendered().items())
    )


@unittest.skipUnless(checkout_packages.installed("toy"), "needs the toy package: slice 3.8")
class ByteForByteTest(unittest.TestCase):
    """What the README, the manifest, `docs/` and the run skill were before the prose left the modules."""

    def test_the_record_covers_every_combination_and_every_file_of_it(self) -> None:
        """A record that lost a row would pass by not asking about the file that changed."""
        self.assertEqual(sorted(recorded()), sorted(rendered()))

    def test_every_file_is_what_it_was_before_the_prose_left_the_modules(self) -> None:
        for (combination, path), text in sorted(rendered().items()):
            with self.subTest(combination=combination, file=path):
                self.assertEqual(
                    hashlib.sha256(text.encode("utf-8")).hexdigest(), recorded().get((combination, path)),
                    f"{path} is no longer the text recorded in {RECORD.name} for {combination}",
                )

    def test_the_matrix_separates_the_combinations_it_claims_to(self) -> None:
        """A matrix whose rows render the same bytes is a matrix proving one thing several times.

        Every application set must make at least one page differ from every other set, under the same
        profile and destination — otherwise a branch nobody is exercising is being recorded as covered.
        """
        for profile in PROFILES:
            for target, shape in DESTINATIONS:
                seen: dict[str, str] = {}
                for name, build in SETS:
                    text = "".join(sorted(pages(build(), profile, target, shape, ".").values()))
                    with self.subTest(profile=profile, target=target, apps=name):
                        self.assertNotIn(text, seen, f"{name} renders what {seen.get(text)} does")
                    seen[text] = name


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
