"""The parts that wire a generated project together: its composition root, its pins, its permissions.

These write the files a project is held together by rather than the pages it is read through. The
experiment proved them by generating and reading back, so those suites return in 3.3z; what is here is
what each has to be true of before any project exists.

The pins get the most attention. A pin is the difference between a repository that builds the same way
on two machines and one that does not, and a range dressed as a pin is the shape that hides it.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai.project import agent_settings, composition, openapi, pins, renovate


class CompositionTest(unittest.TestCase):
    """The composition root is written from marked placeholders, so one language's wiring is data."""

    def test_every_placeholder_is_distinct(self) -> None:
        marks = (composition.STORE_IMPORT, composition.APP_IMPORTS,
                 composition.STORE_OPEN, composition.STORE_ARGUMENT)
        self.assertEqual(len(set(marks)), len(marks))

    def test_a_placeholder_could_not_occur_in_real_code_by_accident(self) -> None:
        for mark in (composition.STORE_IMPORT, composition.APP_IMPORTS,
                     composition.STORE_OPEN, composition.STORE_ARGUMENT):
            with self.subTest(mark=mark):
                self.assertTrue(mark.startswith("__") and mark.endswith("__"))
                self.assertEqual(mark, mark.upper())


class PinsTest(unittest.TestCase):
    """What a generated project is pinned to, and the shape a pin has to have."""

    def test_spec_kit_is_pinned_to_a_tag_and_not_to_a_branch(self) -> None:
        """A branch moves under a project that was generated months ago."""
        self.assertRegex(pins.SPECKIT_TAG, r"^v\d+\.\d+\.\d+$")
        self.assertIn(pins.SPECKIT_TAG, pins.SPECKIT_SOURCE)

    def test_the_source_names_the_tag_it_claims_to_pin(self) -> None:
        self.assertTrue(pins.SPECKIT_SOURCE.endswith(pins.SPECKIT_TAG))

    def test_a_project_with_no_application_still_gets_the_files_every_repository_needs(self) -> None:
        written = pins.pin_files([])
        self.assertIn(".editorconfig", written)


class RenovateTest(unittest.TestCase):
    def test_a_project_with_no_application_has_no_family_rules_rather_than_a_crash(self) -> None:
        self.assertEqual(renovate.family_rules([]), [])

    def test_the_workflow_pattern_is_anchored_at_both_ends(self) -> None:
        """An unanchored pattern matches a path that merely contains one, and updates the wrong file."""
        self.assertTrue(renovate.WORKFLOWS.startswith("/^"))
        self.assertTrue(renovate.WORKFLOWS.endswith("$/"))


class OpenApiTest(unittest.TestCase):
    def test_the_client_package_lives_under_the_workspace_packages(self) -> None:
        self.assertTrue(openapi.API_CLIENT.endswith("/api-client"))
        self.assertTrue(openapi.API_CLIENT_NAME.startswith("@"))

    def test_make_openapi_writes_by_an_absolute_path(self) -> None:
        """`npm --workspace` runs the script inside the service, where a path from the root names nothing:
        every berth in hr-test-2 wrote its document nowhere."""
        service = SimpleNamespace(transport="fastify", path="apps/service")
        with mock.patch.object(openapi, "exporting", return_value=[service]), \
                mock.patch.object(openapi, "DOCUMENTS", {"fastify": "openapi.json"}), \
                mock.patch.object(openapi, "export_command", return_value="npm --workspace apps/service run"):
            recipe = openapi.openapi_targets("shop", [])
        self.assertIn("@out=$(CURDIR)/apps/service/openapi.json; npm --workspace apps/service", recipe)


class PermissionsTest(unittest.TestCase):
    """What an agent in a generated project may and may not do."""

    def test_something_is_denied(self) -> None:
        """A permission list that denies nothing is a permission list nobody wrote."""
        self.assertTrue(agent_settings.DENIED_PERMISSIONS)

    def test_nothing_is_both_allowed_and_denied(self) -> None:
        """A rule in both lists resolves by whichever the harness reads last, which is not a decision."""
        allowed = {str(rule) for rule in agent_settings.TOOLKIT_PERMISSIONS}
        denied = {str(rule) for rule in agent_settings.DENIED_PERMISSIONS}
        self.assertEqual(allowed & denied, set())

    def test_the_keel_names_no_extension_in_a_projects_settings(self) -> None:
        """Slice 6.1c's line. Which extensions a project has is decided at `./init`, inside the project,
        after this file was written — so a keel that named one wrote a permission, an MCP server and two
        hook rows for a tool every project carried whether or not it had elected anything. An extension
        that installs a server writes its own entry now."""
        written = agent_settings.claude_settings([])
        self.assertNotIn("codegraph", written)
        self.assertNotIn("mcp__", written)
        self.assertNotIn("enabledMcpjsonServers", written)
        for rule in agent_settings.TOOLKIT_PERMISSIONS:
            self.assertFalse(str(rule).startswith("scripts/"), rule)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
