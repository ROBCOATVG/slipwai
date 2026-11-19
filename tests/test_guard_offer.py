"""A guard a project gained on an upgrade is said, with the command that agrees to it — and never agreed for.

A guard was agreed to at `./init`, on a terminal, and nowhere else. A project that elected an extension
before the extension had a guard was therefore never asked: `migrate` brought the guard's files and the
declaration, `make agents` projected around it, and nothing said that a refusal was sitting there waiting
for a person's yes (#121). The extension could not write the registry itself, and must not: that is the
agreement, and software that writes it has agreed with itself.

So both say it. `make agents` says it every time it runs and asks where somebody is at a terminal;
`migrate` says it in its report and on the catch-up page. Neither writes `.slipwai/guards.json` unless a
person answered yes, and the cases here hold the file to its bytes.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock

import checkout_packages  # noqa: F401
from guard_project import Project

from slipwai import catch_up, guards_offered, toolkit
from slipwai.extension_directory import Extension

SEARCH = {"before-search": {"run": "g.py", "budget": "5s"}}
AGREE = "python3 scripts/extensions/guards.py --elect cg"


class Upgraded(unittest.TestCase):
    """A project that agreed to `lint`'s guard long ago, and elected `cg` before `cg` had one."""

    def setUp(self) -> None:
        self.project = Project()
        self.addCleanup(self.project.close)
        self.project.extension("lint", {"before-write": {"run": "w.py", "budget": "5s"}})
        self.project.guards("--elect", "lint")
        self.project.extension("cg", SEARCH)
        self.project.extension("never-elected", SEARCH)
        self.project.elected("cg", "lint")
        self.before = self.project.registry.read_bytes()

    def make_agents(self) -> subprocess.CompletedProcess:
        """The first command of `make agents`, with nobody at a terminal."""
        return subprocess.run([sys.executable, str(self.project.extensions / "project.py")],
                              capture_output=True, text=True, cwd=self.project.root, timeout=120,
                              stdin=subprocess.DEVNULL)

    def offer(self) -> ModuleType:
        """This project's own `guard_offer.py`, loaded so a case can stand in for the person at the terminal."""
        path = self.project.extensions / "guard_offer.py"
        spec = importlib.util.spec_from_file_location(f"guard_offer_{id(self)}", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(module)
        return module


class MakeAgentsTest(Upgraded):
    def test_it_says_which_extension_what_it_would_stop_and_the_command_that_agrees(self) -> None:
        done = self.make_agents()
        self.assertEqual(done.returncode, 0, done.stderr)
        said = [line for line in done.stdout.splitlines() if line.startswith("guards:")]
        self.assertEqual(said, [
            "guards: cg can refuse a tool call here, and nobody has agreed to it: it would stop a search of "
            "the tree and tell the agent what to ask instead. It refuses nothing until a person agrees: "
            f"{AGREE}"])

    def test_with_nobody_at_a_terminal_the_registry_is_the_bytes_it_was(self) -> None:
        self.make_agents()
        self.make_agents()
        self.assertEqual(self.project.registry.read_bytes(), self.before)

    def test_a_project_with_no_registry_at_all_is_not_given_one(self) -> None:
        self.project.registry.unlink()
        self.assertEqual(self.make_agents().returncode, 0)
        self.assertFalse(self.project.registry.exists())

    def test_the_command_it_names_is_the_agreement_and_then_it_says_no_more(self) -> None:
        self.assertEqual(self.project.guards(*AGREE.split()[2:]).returncode, 0)
        self.assertEqual(self.project.agreed(), {"before-search": ["cg"], "before-write": ["lint"]})
        self.assertNotIn("guards:", self.make_agents().stdout)

    def test_an_extension_nobody_elected_is_not_offered(self) -> None:
        self.assertNotIn("never-elected", self.make_agents().stdout)

    def test_a_guard_that_changed_since_it_was_agreed_to_is_said_and_the_old_one_stays(self) -> None:
        """An extension that gave its agreed guard something new to see has changed what was agreed to.
        The registry holds the guard as it was when a person said yes, and goes on holding it."""
        self.project.guards("--elect", "cg")
        agreed = self.project.registry.read_bytes()
        self.project.extension("cg", {"before-search": {"run": "g.py", "budget": "5s", "stages": ["implement"]}})
        said = self.make_agents().stdout
        self.assertIn("guards: cg's before-search guard has changed since somebody agreed to it, and the one "
                      f"agreed to is the one that fires. To agree to it as it is now: {AGREE}", said)
        self.assertEqual(self.project.registry.read_bytes(), agreed)

    def test_a_project_laid_out_under_another_directory_is_given_the_path_it_has(self) -> None:
        self.assertEqual(self.offer().COMMAND, "python3 scripts/extensions/guards.py")


class AtATerminalTest(Upgraded):
    """Where somebody is there, `make agents` asks as `./init` does. The person is a callable here: a test
    that needed a real terminal would be a test that runs on one platform and hangs on the rest."""

    def test_yes_agrees_to_what_was_asked_about_and_keeps_the_rest(self) -> None:
        shown: list[str] = []

        def yes(text: str) -> str:
            shown.append(text)
            return "y"

        self.assertEqual(self.offer().announce(terminal=True, ask=yes, say=shown.append), 0)
        self.assertEqual(self.project.agreed(), {"before-search": ["cg"], "before-write": ["lint"]})
        self.assertIn("cg: stop a search of the tree", "\n".join(shown))
        self.assertTrue(shown[-2].endswith("[y/N]: "), shown)

    def test_anything_else_is_no_and_says_how_to_agree_later(self) -> None:
        for answer in ("", "n", "maybe"):
            with self.subTest(answer=answer):
                shown: list[str] = []
                self.offer().announce(terminal=True, ask=lambda text, said=answer: said, say=shown.append)
                self.assertEqual(self.project.registry.read_bytes(), self.before)
                self.assertIn(AGREE, "\n".join(shown))

    def test_a_terminal_that_goes_away_mid_question_has_said_no(self) -> None:
        def gone(text: str) -> str:
            raise EOFError

        self.assertEqual(self.offer().announce(terminal=True, ask=gone, say=lambda line: None), 0)
        self.assertEqual(self.project.registry.read_bytes(), self.before)

    def test_a_changed_guard_is_never_asked_about_in_passing(self) -> None:
        """Asked about by name, with its command, and not folded into a yes about something else."""
        self.project.guards("--elect", "cg")
        self.project.extension("cg", {"before-search": {"run": "other.py", "budget": "5s"}})
        agreed = self.project.registry.read_bytes()

        def never(text: str) -> str:
            raise AssertionError("asked")

        self.offer().announce(terminal=True, ask=never, say=lambda line: None)
        self.assertEqual(self.project.registry.read_bytes(), agreed)


class MigrateTest(Upgraded):
    """The keel's half: what `migrate` prints, and the section it writes on the catch-up page."""

    def test_migrate_says_it_and_writes_nothing(self) -> None:
        said = guards_offered.said(self.project.root, {"name": "pir"})
        self.assertEqual(len(said), 1)
        self.assertTrue(said[0].startswith("guards: cg can refuse a tool call here, and nobody has agreed"))
        self.assertTrue(said[0].endswith(AGREE))
        self.assertEqual(self.project.registry.read_bytes(), self.before)

    def test_the_catch_up_page_carries_it_under_its_own_heading(self) -> None:
        section = guards_offered.section(self.project.root, {"name": "pir"})
        page = catch_up.notes("pir", "2.0.0", extensions=section)
        self.assertIn("## Guards nobody has agreed to", page)
        self.assertIn(f"`{AGREE}`", page)
        self.assertLess(page.index("## Guards nobody has agreed to"), page.index("## Then"))

    def test_a_project_owed_nothing_gets_no_section_and_no_line(self) -> None:
        self.project.guards("--elect", "cg")
        self.assertEqual(guards_offered.said(self.project.root, {"name": "pir"}), [])
        self.assertEqual(guards_offered.section(self.project.root, {"name": "pir"}), [])

    def test_a_project_from_before_the_script_existed_is_a_page_short_a_section_and_never_a_traceback(self) -> None:
        (self.project.extensions / "guard_offer.py").unlink()
        self.assertEqual(guards_offered.section(self.project.root, {"name": "pir"}), [])

    def test_what_migrate_replays_is_what_the_installed_package_declares_now(self) -> None:
        """`available-guards.json` is the keel's file: every replay writes it from the packages installed
        on that machine, so a guard an extension gained reaches the project with the files that run it."""
        gained = Extension("cg", Path("nowhere"), {"key": "cg", "guards": SEARCH})
        with mock.patch.object(toolkit, "EXTENSIONS", (gained,)), \
                mock.patch.object(toolkit, "package_files", return_value=[]):
            written = json.loads(toolkit.extension_files()[toolkit.EXTENSION_GUARDS])
        self.assertEqual(written, {"cg": SEARCH})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
