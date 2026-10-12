"""The parts that write how a project is run: `/cruise`'s own settings, its CI, and `./init`.

These are the files a generated repository is operated through rather than read through, and the places
where a wrong string is silent: a shell argument that is not quoted is a project name that can run a
command.

Their suites generate a project and come back in 3.3z. Held here is what has to be true before one
exists.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401

from slipwai.project import (
    ci_workflows,
    cruise,
    existing,
    init_extensions,
    init_script,
    integration,
)


class CruiseTest(unittest.TestCase):
    """What `/cruise` is after 7.7d: the settings a run gives at the ladder's stops, and nothing that holds
    a run. The two tests that stood here held the runner's contract — the four last lines it parsed, and the
    sentence a session printed when nothing was reading them — and both went with it. What replaced the
    contract is the deck log, which `tests/test_captain.py` holds."""

    def test_the_config_it_writes_is_json_and_says_where_it_is_explained(self) -> None:
        written = json.loads(cruise.cruise_config())
        self.assertIn("_comment", written)

    def test_it_declares_no_setting_that_bounds_a_loop(self) -> None:
        """A budget on iterations, wall time or polling is a budget on something that no longer exists. A
        setting nothing reads is worse than one that was never there: it is answered, committed, and
        silently ignored."""
        declared = {key for key, _, _, _ in cruise.SETTINGS}
        self.assertEqual(declared & {"stuck_after", "max_iterations", "max_hours", "poll_minutes"}, set())

    def test_the_settings_the_stops_need_are_all_still_here(self) -> None:
        declared = {key for key, _, _, _ in cruise.SETTINGS}
        self.assertEqual(declared, {"enabled", "decide", "release", "constitution", "hand", "unblock", "model"})

    def test_the_command_names_no_part_of_the_runner(self) -> None:
        """Prose is where a deletion rots: a command file that still tells somebody to run `cruise.py watch`
        is a command file that works until they read it."""
        written = cruise.cruise_command(True, [])
        for gone in ("cruise.py run", "cruise.py start", "cruise.py watch", "cruise.py tell",
                     "cruise.py told", "cruise.py loop", "cruise.py stopping", "cruise.py status",
                     "cruise: continue", "cruise: done", "cruise-checkpoint", "cruise.stop"):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, written)

    def test_it_says_what_casts_off_and_what_a_dispatched_session_reads(self) -> None:
        written = cruise.cruise_command(True, [])
        self.assertIn("fleet.py start", written)
        self.assertIn("a stage that wrote no line made no progress", written.lower())


class InitScriptTest(unittest.TestCase):
    """`./init` is shell, written by Python, run on a stranger's machine."""

    def test_a_value_with_a_quote_in_it_cannot_close_the_quote_around_it(self) -> None:
        """The whole of what stops a project name being a command."""
        quoted = init_extensions._sh_single_quote("it's; rm -rf /")
        self.assertTrue(quoted.startswith("'") and quoted.endswith("'"))
        self.assertNotIn("'it's", quoted)

    def test_an_ordinary_value_is_still_quoted(self) -> None:
        self.assertEqual(init_extensions._sh_single_quote("demo"), "'demo'")

    def test_the_argument_scan_names_every_axis_it_is_given(self) -> None:
        written = init_script.argument_scan(["persistence", "http"], ["codegraph"])
        for axis in ("persistence", "http"):
            with self.subTest(axis=axis):
                self.assertIn(f"--{axis}", written)

    def test_an_extension_is_taken_by_flag_and_not_by_a_name_the_script_knows(self) -> None:
        """`--extension <key>` is generic on purpose: the keys come from the catalogue, so a package
        adding one needs no edit to the shell `./init` is written as."""
        written = init_script.argument_scan(["http"], ["codegraph"])
        self.assertIn("--extension", written)
        self.assertNotIn("codegraph", written)

    def test_the_extension_menu_offers_what_the_catalogue_declares_and_not_a_fixed_list(self) -> None:
        offered = init_script.prompt_extensions({"toy": {"name": "Toy", "description": "a toy"}})
        self.assertIn("toy", offered)
        self.assertNotIn("codegraph", offered)

    def test_a_quickstart_s_election_is_read_before_the_menu_is_shown(self) -> None:
        """A person who chose a quickstart has already answered the menu's question. Both are gated on
        `selected_extensions` being empty, so whichever runs first wins — and the record runs first."""
        written = init_extensions.ELECTED_FROM_QUICKSTART + init_extensions.prompt_extensions(
            {"toy": {"name": "Toy", "description": "a toy"}})
        self.assertLess(written.index("elected.py"), written.index("menu.py"))
        self.assertEqual(written.count('[ -z "$selected_extensions" ]'), 2)


class CiWorkflowsTest(unittest.TestCase):
    """`toolchain_setup` asks the first service's backend for its family's answer, so it needs a loaded
    package and is proven in each package's own CI rather than here."""

    def test_the_paths_a_workflow_watches_are_listed_one_per_line(self) -> None:
        written = ci_workflows.dependency_paths(["apps/service/**", "package.json"])
        self.assertIn("apps/service/**", written)
        self.assertIn("package.json", written)


class IntegrationTest(unittest.TestCase):
    def test_a_project_with_no_service_has_no_integration_variables(self) -> None:
        self.assertEqual(integration.integration_variables([], [], []).strip(), "")


class ExistingTargetTest(unittest.TestCase):
    """The target the keel does not manage: it offers what `none` offers and provisions nothing."""

    def test_the_release_constraint_says_the_keel_does_not_manage_the_infrastructure(self) -> None:
        self.assertIn("the keel does not manage", existing.EXISTING_STAGE)

    def test_the_pages_it_adds_are_all_written(self) -> None:
        for page in (existing.EXISTING_GUIDANCE, existing.EXISTING_README):
            self.assertTrue(page.strip())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
