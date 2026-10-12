"""The method's own pages, byte for byte, before and after the standing text in them moved to assets.

Slice 16.5 moves the prose out of `event_model.py`, `model_to_code.py`, `adversary.py` and
`parallel_slices.py`, and `docs/generated-prose.md` says the one thing a move like that owes: the new path
reproduces the old bytes exactly. "Generate before and after" cannot be run across one commit, so
`tests/fixtures/method-pages.sha256` is what these modules rendered at a6a0aed, the commit this slice was
written on top of, and the tests below are the only reason that file exists.

**The matrix, and what it honestly covers.** Thirty-two combinations of four application sets, both
profiles, two destinations and both delivery layouts. The application sets are the branches these four
modules actually have: one service whose log is its truth, one that keeps current state, one of each — the
project phase 15 exists to make generatable, and the only set that reaches both halves of every rung
branch — and no service at all, which `sail.md` still has to be written for. The destinations are there
because `sail.md` grows a release-constraint section on a target the keel deploys to, and the layouts
because every `make` in the concurrency section is `make -f delivery/Makefile` in a repository the method
was installed beside.

`docs/first-slice.md` and the mapping document are written only on the event profile and only where the
keel made a service, so eight of the thirty-two combinations carry five files and the rest carry two.

The page address in `model.yaml` is read from the environment (`GITEA_OWNER`, `GITEA_PAGES_URL`), so both
are pinned while the matrix renders: a record that moved with whoever took the reading would be a record of
their machine.
"""
from __future__ import annotations

import hashlib
import os
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages

from slipwai.layout import Layout
from slipwai.project.adversary import adversary_command
from slipwai.project.commands import sail_command
from slipwai.project.event_model import event_documentation
from slipwai.selection import Selection
from slipwai.services import App, service_app, services_of

RECORD = Path(__file__).resolve().parent / "fixtures/method-pages.sha256"
PROJECT = "harbour-shop"
TOY = "toy-plain"
#: What the reading is taken with, so the page address in `model.yaml` is this record's and not a machine's.
FORGE = {"GITEA_OWNER": "harbour", "GITEA_PAGES_URL": "http://localhost:3301"}
EVENTS = Selection({"write-model": "events", "persistence": "postgres", "http": "toy-serve"})
STATE = Selection({"write-model": "state", "persistence": "postgres", "http": "toy-serve"})


def sourced() -> list[App]:
    return [service_app("orders", TOY, 3000, EVENTS, first=True)]


def stored() -> list[App]:
    return [service_app("billing", TOY, 3000, STATE, first=True)]


def mixed() -> list[App]:
    """One service on each rung: every rung branch in these pages answered both ways at once."""
    return [service_app("orders", TOY, 3000, EVENTS, first=True),
            service_app("billing", TOY, 3001, STATE)]


def bare() -> list[App]:
    """No service at all, which `sail.md` and `adversary.md` are still written for."""
    return []


SETS = (("sourced", sourced), ("stored", stored), ("mixed", mixed), ("bare", bare))
PROFILES = ("standard", "event-modelling")
#: Nowhere, and a cloud the keel deploys to — which is what `sail.md`'s release constraint turns on.
TARGETS = ("none", "aws")
DELIVERIES = (".", "delivery")


def combinations() -> list[tuple[str, str, str, str]]:
    return [(name, profile, target, delivery)
            for name, _build in SETS
            for profile in PROFILES
            for target in TARGETS
            for delivery in DELIVERIES]


def pages(apps: list[App], profile: str, target: str, delivery: str) -> dict[str, str]:
    """Every file these four modules write for one combination."""
    event = profile == "event-modelling"
    files = {
        "commands/sail.md": sail_command(event, apps, target, Layout(delivery)),
        "commands/adversary.md": adversary_command(event, apps),
    }
    if event and services_of(apps):
        files.update(event_documentation(PROJECT, services_of(apps)))
    return files


def rendered() -> dict[tuple[str, str], str]:
    """The whole matrix, as `(combination, path) -> text`, with the forge pinned."""
    built: dict[tuple[str, str], str] = {}
    sets = dict(SETS)
    with mock.patch.dict(os.environ, FORGE):
        for name, profile, target, delivery in combinations():
            key = f"{name}/{profile}/{target}/{delivery}"
            for path, text in pages(sets[name](), profile, target, delivery).items():
                built[(key, path)] = text
    return built


def recorded() -> dict[tuple[str, str], str]:
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
    """What the method's own pages were before the prose left the modules."""

    def test_the_record_covers_every_combination_and_every_file_of_it(self) -> None:
        self.assertEqual(sorted(recorded()), sorted(rendered()))

    def test_every_file_is_what_it_was_before_the_prose_left_the_modules(self) -> None:
        record = recorded()
        for (combination, path), text in sorted(rendered().items()):
            with self.subTest(combination=combination, file=path):
                self.assertEqual(
                    hashlib.sha256(text.encode("utf-8")).hexdigest(), record.get((combination, path)),
                    f"{path} is no longer the text recorded in {RECORD.name} for {combination}",
                )

    def test_the_matrix_separates_the_application_sets_it_claims_to(self) -> None:
        """A matrix whose rows render the same bytes is a matrix proving one thing several times.

        Asked of the event profile alone, and deliberately. The rung is a question only a modelled project
        is asked, so on the standard profile a service that keeps its events and one that keeps current
        state are the same service to every page here — claiming otherwise would be claiming coverage the
        reading does not have.
        """
        for target in TARGETS:
            seen: dict[str, str] = {}
            for name, build in SETS:
                text = "".join(sorted(pages(build(), "event-modelling", target, ".").values()))
                with self.subTest(target=target, apps=name):
                    self.assertNotIn(text, seen, f"{name} renders what {seen.get(text)} does")
                seen[text] = name

    def test_the_delivery_layout_reaches_these_pages(self) -> None:
        """Every `make` in the concurrency section is `make -f delivery/Makefile` where the method was
        installed beside a repository, so the second half of the record is not a copy of the first."""
        at_root = pages(mixed(), "event-modelling", "none", ".")
        beside = pages(mixed(), "event-modelling", "none", "delivery")
        self.assertNotEqual(at_root["commands/sail.md"], beside["commands/sail.md"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
