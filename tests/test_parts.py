"""The parts that wait on nothing, each held to the one thing it is for.

These ten modules came back together because none of them imports anything that was not already here.
Their own suites in the experiment do not: `test_services.py` and `test_layout.py` both reach for
`scaffold`, which is forty modules away in the last wave but four, and `test_npm_workspace.py` reaches
for `project.shared_packages`. Those suites come back with the scaffold, in slice 3.3b.

What is here instead is what each module can be asked on its own — the pure functions and the refusals.
It is narrower than the suites that are coming, and it is the difference between a module that has been
read and a module that has only been copied.
"""
from __future__ import annotations

import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import backends, ecosystems, layout, naming, origin, probes, services
from slipwai.catalog import CATALOG
from slipwai.errors import GenerationError
from slipwai.npm_workspace import NoBrowserLanguage, npm, workspaces
from slipwai.selection import Selection


class NamingTest(unittest.TestCase):
    """A project name becomes a namespace in each ecosystem, and each has its own idea of a legal one."""

    def test_a_java_package_segment_is_lower_case_and_loses_its_separators(self) -> None:
        self.assertEqual(naming.java_package_segment("my-project"), "myproject")

    def test_a_python_package_name_keeps_words_apart_with_underscores(self) -> None:
        self.assertEqual(naming.python_package_name("my-project"), "my_project")

    def test_a_name_that_is_already_legal_is_left_alone(self) -> None:
        self.assertEqual(naming.python_package_name("demo"), "demo")
        self.assertEqual(naming.java_package_segment("demo"), "demo")


class ProbesTest(unittest.TestCase):
    """Where a service says it is alive. The keel asks the registry, and answers for nothing itself."""

    def test_the_liveness_path_is_the_keels_to_fix_and_not_a_languages(self) -> None:
        self.assertEqual(probes.HEALTH_PATH, "/health")

    def test_a_backend_no_package_answers_for_refuses_rather_than_guessing(self) -> None:
        for ask in (probes.ready_path, probes.health_body):
            with self.subTest(ask=ask.__name__), self.assertRaises(KeyError):
                ask("a-backend-no-package-declares")


class BackendsTest(unittest.TestCase):
    """The pins and placeholders every generated project shares, whatever language it is in."""

    def test_the_placeholders_are_distinctive_enough_not_to_occur_by_accident(self) -> None:
        for placeholder in (backends.APP, backends.VERIFY):
            self.assertTrue(placeholder.startswith("__") and placeholder.endswith("__"), placeholder)

    def test_the_pinned_toolchains_are_exact_versions_not_ranges(self) -> None:
        """A range here is a generated project that builds differently on two machines."""
        for pin in (backends.PYTHON_VERSION, backends.UV_VERSION):
            self.assertRegex(pin, r"^\d+(\.\d+)*$")
        self.assertIsInstance(backends.NODE_MAJOR, int)


class EcosystemsTest(unittest.TestCase):
    """What a build ecosystem's files say, for a repository the keel did not make."""

    def test_every_target_an_adopted_repository_is_asked_for_is_named_once(self) -> None:
        self.assertEqual(len(ecosystems.TARGETS), len(set(ecosystems.TARGETS)))
        self.assertIn("test", ecosystems.TARGETS)

    def test_a_command_is_placed_in_the_directory_it_belongs_to(self) -> None:
        self.assertIn("thing", ecosystems.in_dir("thing", "make test"))

    def test_reading_a_file_that_is_not_there_is_empty_rather_than_a_crash(self) -> None:
        """Adoption reads a repository nobody promised anything about."""
        self.assertEqual(ecosystems.read(Path("/nonexistent/pom.xml")), "")
        self.assertEqual(ecosystems.first_line(Path("/nonexistent/pom.xml")), "")


class NpmWorkspaceTest(unittest.TestCase):
    """The browser app needs a language that answers the npm workspace, and the keel answers for none."""

    def test_with_no_package_loaded_there_is_no_workspace(self) -> None:
        self.assertEqual(workspaces(), {})

    def test_no_language_answers_it_in_an_empty_keel(self) -> None:
        self.assertFalse(npm("typescript"))

    def test_asking_for_the_browser_language_refuses_with_what_is_missing(self) -> None:
        from slipwai.npm_workspace import browser_language

        with self.assertRaises(NoBrowserLanguage) as raised:
            browser_language()
        self.assertIn("ships a browser app", str(raised.exception))
        self.assertIsInstance(raised.exception, GenerationError)


class OriginTest(unittest.TestCase):
    """What a repository the keel did not generate records about itself."""

    def test_a_project_is_generated_or_adopted_and_nothing_else(self) -> None:
        self.assertEqual(set(origin.ORIGINS), {"generated", "adopted"})

    def test_the_renamed_strategy_is_still_answerable_by_its_old_name(self) -> None:
        """A repository adopted before the rename records the old word, and must still read back."""
        for old, new in origin.OLD_STRATEGIES.items():
            with self.subTest(old=old):
                self.assertIn(new, origin.STRATEGIES)
                self.assertNotIn(old, origin.STRATEGIES)


class LayoutTest(unittest.TestCase):
    """Which paths of a generated project belong to the delivery method rather than to the product."""

    def test_the_delivery_roots_are_the_ones_a_pointer_may_name(self) -> None:
        for root in ("scripts", "skills", "commands", "agents", "docs"):
            self.assertIn(root, layout.DELIVERY_ROOTS)

    def test_a_delivery_path_is_told_from_a_product_one(self) -> None:
        self.assertTrue(layout.is_delivery("scripts/verify"))
        self.assertFalse(layout.is_delivery("apps/service/src/main.py"))


class ServicesTest(unittest.TestCase):
    """What a project's applications are called, and what the keel refuses to call one."""

    def test_the_first_service_and_the_first_browser_app_have_names_the_interview_offers(self) -> None:
        self.assertEqual((services.FIRST_SERVICE, services.FIRST_WEB), ("service", "web"))

    def test_a_service_name_is_lower_case_and_hyphenated(self) -> None:
        for good in ("billing", "order-entry", "a"):
            self.assertRegex(good, naming.SERVICE_NAME)

    def test_a_name_the_pattern_refuses_is_refused_whole_and_not_in_part(self) -> None:
        """`fullmatch`, not `match`: `Billing!` must not pass because `illing` would."""
        for bad in ("Billing", "order_entry", "-billing", "billing-", ""):
            with self.subTest(name=bad):
                self.assertIsNone(naming.SERVICE_NAME.fullmatch(bad))

    def test_a_context_is_named_like_a_service(self) -> None:
        self.assertIs(naming.CONTEXT_NAME, naming.SERVICE_NAME)


class SelectionTest(unittest.TestCase):
    """One option per axis. Everything downstream reads this rather than a flat list of names, because a
    flat list cannot answer "which event store did they choose?" without guessing from membership."""

    def test_an_axis_that_was_asked_reads_back_the_answer(self) -> None:
        self.assertEqual(Selection({"persistence": "postgres"}).option("persistence"), "postgres")

    def test_an_axis_that_was_never_asked_reads_as_its_no_infrastructure_answer(self) -> None:
        """Not a KeyError and not None: an unasked axis has an answer, and it is "nothing there"."""
        self.assertEqual(Selection({}).option("persistence"), CATALOG["axes"]["persistence"]["absent"])

    def test_two_selections_of_the_same_answers_are_the_same_selection(self) -> None:
        self.assertEqual(Selection({"http": "none"}), Selection({"http": "none"}))

    def test_the_choices_it_is_given_are_copied_rather_than_held(self) -> None:
        """A caller that keeps editing its dict must not be editing the selection too."""
        given = {"http": "none"}
        selection = Selection(given)
        given["http"] = "fastapi"
        self.assertEqual(selection.option("http"), "none")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
