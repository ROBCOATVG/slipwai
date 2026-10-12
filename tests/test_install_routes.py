"""One supported route and two conveniences, written down and then made true rather than advisory.

A project that can be installed three ways and is supported in one has two ways to be wrong about. The
page is the decision; this is what keeps the decision and the code from parting company. Both directions
are held, because either alone rots: a page naming a route the keel has not got sends somebody looking for
a verb that is not there, and a route the keel has that the page does not name is a route nobody decided
about and everybody will eventually use.
"""
from __future__ import annotations

import contextlib
import io
import re
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import native, plugin
from slipwai.assets import ROOT
from slipwai.cli import VERBS as CLI_VERBS
from slipwai.cli_package import ROUTES as ROUTES_PAGE
from slipwai.cli_package import package_main
from slipwai.layout import AT_ROOT
from slipwai.package_new import VERBS as PACKAGE_VERBS
from slipwai.project.agents import agent_files
from slipwai.project.commands import command_files

PAGE = ROOT / "docs/reference/install-routes.md"
#: The three ways the keel's material reaches a person, keyed as the page heads each one.
ROUTES = ("init", "plugin", "harness")
#: What a route's section says of itself, and exactly one route may say the first.
SUPPORTED = "**Supported.**"
CONVENIENCE = "**A convenience.**"


def page() -> str:
    return PAGE.read_text(encoding="utf-8")


def sections() -> dict[str, str]:
    """Each route's part of the page, keyed by the `<!-- route: <key> -->` marker that opens it."""
    found = {}
    parts = re.split(r"<!-- route: ([a-z-]+) -->", page())
    for key, body in zip(parts[1::2], parts[2::2], strict=True):
        found[key] = body
    return found


class PageTest(unittest.TestCase):
    """The decision is written where the done-when puts it, in the five sections this repository uses."""

    def test_the_page_is_there(self) -> None:
        self.assertTrue(PAGE.is_file(), f"{PAGE} is the decision 12.4 is")

    def test_it_is_written_in_the_five_sections_a_decision_takes_here(self) -> None:
        """Nygard's, which is what `docs/adr/0001` installs into every generated project — so a reader who
        has seen one decision in a slipwai project has seen this one's shape too."""
        for heading in ("## Status", "## Context", "## Decision", "## Consequences"):
            self.assertIn(heading, page(), heading)

    def test_it_names_every_route_the_keel_has_and_no_other(self) -> None:
        self.assertEqual(sorted(sections()), sorted(ROUTES))

    def test_exactly_one_route_is_the_supported_one(self) -> None:
        """The whole decision. Two supported routes is the state the slice exists to end."""
        supported = [key for key, body in sections().items() if SUPPORTED in body]
        self.assertEqual(supported, ["init"])

    def test_every_other_route_says_it_is_not(self) -> None:
        """Said in each one's own section, not once at the top: a reader arrives at the route they are
        about to use, and a caveat two screens up is a caveat they did not read."""
        for key, body in sections().items():
            if key != "init":
                with self.subTest(route=key):
                    self.assertIn(CONVENIENCE, body)
                    self.assertIn("not held by a gate", body)

    def test_the_supported_route_names_the_gates_that_hold_it(self) -> None:
        for gate in ("make verify", "make test-docs"):
            self.assertIn(gate, sections()["init"], gate)

    def test_every_verb_the_page_names_is_one_the_command_line_has(self) -> None:
        said = set(re.findall(r"`slipwai (?:package )?([a-z-]+)", page()))
        known = set(CLI_VERBS) | set(PACKAGE_VERBS) | {"generate", "adopt"}
        self.assertEqual(said - known, set())


class MadeTrueTest(unittest.TestCase):
    """What stops the decision being advice: each convenience is rendered from the supported route."""

    def test_the_plugins_commands_and_agent_types_are_the_generators_own(self) -> None:
        rendered = plugin.files("standard")
        for path, text in command_files(False, [], "none", AT_ROOT, None).items():
            self.assertEqual(rendered.get(path), text, path)
        for path, text in agent_files(AT_ROOT).items():
            self.assertEqual(rendered.get(path), text, path)

    def test_the_harness_material_is_the_plugins_own_material_moved(self) -> None:
        """Byte for byte for a harness whose row changes nothing — which is what makes the relocation a
        relocation rather than a third rendering."""
        rendered = native.files("claude")
        for path, text in plugin.files("standard").items():
            if path.startswith("skills/"):
                self.assertEqual(rendered.get(f".claude/skills/{path.removeprefix('skills/')}"), text, path)

    def test_each_convenience_tells_the_person_using_it_that_it_is_one(self) -> None:
        """A decision on a page nobody opens is a decision nobody has, so both verbs print where it is."""
        self.assertEqual(ROOT / ROUTES_PAGE, PAGE)
        for argv in (["plugin", str(Path(tempfile.mkdtemp()) / "p")],
                     ["harness", str(Path(tempfile.mkdtemp()) / "h"), "--harness", "codex"]):
            said = io.StringIO()
            with contextlib.redirect_stdout(said):
                package_main(argv)
            with self.subTest(verb=argv[0]):
                self.assertIn(ROUTES_PAGE, said.getvalue())
                self.assertIn("not the supported route", said.getvalue())

    def test_the_two_conveniences_are_verbs_of_the_publishers_verb(self) -> None:
        """Not top-level verbs. A person looking for how to install something looks in one place."""
        self.assertIn("plugin", PACKAGE_VERBS)
        self.assertIn("harness", PACKAGE_VERBS)
        self.assertNotIn("plugin", CLI_VERBS)
        self.assertNotIn("harness", CLI_VERBS)


if __name__ == "__main__":
    unittest.main()
