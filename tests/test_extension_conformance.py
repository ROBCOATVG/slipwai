"""The six obligations, run against packages written to break exactly one of them each.

A suite that only ever sees a passing package proves nothing about what it would refuse, so every check here
has a package that fails it and a package that does not — and the passing one is the scaffold, because what
`slipwai package new` writes has to meet the list the same command prints.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import package_new
from slipwai.conformance import extension
from slipwai.conformance.extension import check

CORE = "9.0"
FENCE = ('BEGIN = "<!-- extension:{key}:begin -->"\nEND = "<!-- extension:{key}:end -->"\n')


def package(root: Path, key: str, body: str, ignore: str | None = None) -> Path:
    place = root / key
    place.mkdir(parents=True)
    manifest = {"key": key, "name": key.title(), "description": "A fake", "kind": "extension",
                "core": ">=9.0,<10", "hooks": {"init": "init.py"}}
    if ignore:
        manifest["ignore"] = ignore
    (place / "extension.json").write_text(json.dumps(manifest), encoding="utf-8")
    (place / "init.py").write_text(body, encoding="utf-8")
    return place


PROJECTS = FENCE + '''
import pathlib
agents = pathlib.Path("AGENTS.md")
text = agents.read_text(encoding="utf-8")
block = BEGIN.format(key="{key}") + "\\n\\nguidance\\n\\n" + END.format(key="{key}")
if BEGIN.format(key="{key}") in text:
    head, rest = text.split(BEGIN.format(key="{key}"), 1)
    text = head + block + rest.split(END.format(key="{key}"), 1)[1]
else:
    text = text.rstrip() + "\\n\\n" + block + "\\n"
agents.write_text(text, encoding="utf-8")
'''


class SaidTest(unittest.TestCase):
    """How the suite reads what an entry point printed, and why both readings were wrong.

    `recovers` asks that every failure path names the command that fixes it. It read line by line, and
    every real message is written the other way — the trouble, then `Install it:`, then the command,
    indented — so the first line of every one of them failed and the command two lines below was never
    seen. All three published extensions were written that way.

    `projects` asks that the AGENTS.md block is marker-fenced. It excused an entry point that stopped
    because its own tool was missing, recognised by words like `not found`; but the scratch project is
    deliberately bare, so an extension that acts on a browser app correctly does nothing there and says
    `this project has no browser app for it to design` — no such words, and it was failed for doing the
    right thing.
    """

    TROUBLED = ("CodeGraph CLI not found: nothing was indexed and AGENTS.md is unchanged.\n"
                "Install it:\n"
                "  curl -fsSL https://example.invalid/install.sh | sh\n"
                "Then adopt it here:\n"
                "  ./init --extension codegraph\n")
    NOTHING_TO_DO = ("UI/UX Pro Max designs screens, and this project has no browser app for it to design: "
                     "nothing was installed and AGENTS.md is unchanged.\n"
                     "Add one first, then adopt it here:\n"
                     "  slipwai add-frontend web\n"
                     "  ./init --extension uipro\n")

    def test_a_remedy_on_the_next_line_counts(self) -> None:
        self.assertEqual(extension.unsaid(self.TROUBLED), [])

    def test_a_problem_with_nothing_after_it_still_fails(self) -> None:
        said = extension.unsaid("codegraph was not found and nothing was indexed.\n")
        self.assertEqual(len(said), 1)
        self.assertIn("named no command to fix it", said[0])

    def test_a_second_problem_does_not_borrow_the_first_one_s_remedy(self) -> None:
        """Grouped per message: the remedy under one has nothing to do with the next."""
        said = extension.unsaid(self.TROUBLED + "the index could not be read.\n")
        self.assertEqual(len(said), 1)
        self.assertIn("could not be read", said[0])

    def test_a_stop_that_names_the_way_on_is_a_stop_whatever_words_it_used(self) -> None:
        """What makes a stop legitimate is that it names the way on — not that it used one of a list of
        words for trouble."""
        self.assertTrue(extension.REMEDY.search(self.NOTHING_TO_DO))
        self.assertEqual(extension.unsaid(self.NOTHING_TO_DO), [])

    def test_saying_nothing_at_all_is_not_a_stop(self) -> None:
        self.assertIsNone(extension.REMEDY.search(""))

    def test_an_indented_init_is_a_remedy(self) -> None:
        """A word boundary needs a word character on one side, and the character before `.` in
        `  ./init --extension uipro` is a space — so `\\b\\./init` could never match, and the one remedy
        every extension names was the one this could not see."""
        self.assertTrue(extension.REMEDY.search("  ./init --extension uipro"))
        self.assertTrue(extension.REMEDY.search("  slipwai add-frontend web"))
        self.assertIsNone(extension.REMEDY.search("  ./init"))


class SuiteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())

    def test_the_scaffold_passes_all_six(self) -> None:
        """`package new` writes the publisher's first package. One that fails the list is a broken lesson."""
        package_new.write("extension", "thing", self.area, CORE)
        report = check(self.area / "thing")
        self.assertTrue(report.passed, report.findings)

    def test_an_entry_point_that_appends_every_run_fails_idempotent(self) -> None:
        body = PROJECTS.format(key="loud").replace("if BEGIN.format(key=\"loud\") in text:",
                                                   "if False:")
        package(self.area, "loud", body)
        report = check(self.area / "loud")
        self.assertTrue(report.findings["idempotent"])

    def test_an_entry_point_that_exits_non_zero_with_no_tools_fails_non_fatal(self) -> None:
        body = PROJECTS.format(key="brittle") + '\nimport shutil, sys\nsys.exit(0 if shutil.which("git") else 1)\n'
        package(self.area, "brittle", body)
        report = check(self.area / "brittle")
        self.assertTrue(report.findings["non-fatal"])
        self.assertIn("PATH", report.findings["non-fatal"][0])

    def test_an_unfenced_block_fails_projects(self) -> None:
        package(self.area, "bare", 'import pathlib\n'
                'pathlib.Path("AGENTS.md").write_text("# A project\\n\\nguidance\\n", encoding="utf-8")\n')
        report = check(self.area / "bare")
        self.assertTrue(report.findings["projects"])

    def test_overwriting_what_a_person_wrote_fails_merges(self) -> None:
        package(self.area, "rude", 'import pathlib\n'
                'pathlib.Path("AGENTS.md").write_text("mine now\\n", encoding="utf-8")\n')
        report = check(self.area / "rude")
        self.assertTrue(report.findings["merges"])

    def test_leaving_state_with_no_gate_fails_gated(self) -> None:
        package(self.area, "stateful", PROJECTS.format(key="stateful"), ignore=".stateful/\n")
        report = check(self.area / "stateful")
        self.assertTrue(report.findings["gated"])

    def test_declaring_a_check_hook_satisfies_gated(self) -> None:
        place = package(self.area, "checked", PROJECTS.format(key="checked"), ignore=".checked/\n")
        manifest = json.loads((place / "extension.json").read_text(encoding="utf-8"))
        manifest["hooks"]["check"] = "hooks/check.py"
        (place / "extension.json").write_text(json.dumps(manifest), encoding="utf-8")
        (place / "hooks").mkdir()
        (place / "hooks/check.py").write_text("", encoding="utf-8")
        self.assertEqual(check(place).findings["gated"], [])

    def test_a_problem_reported_with_no_command_fails_recovers(self) -> None:
        body = PROJECTS.format(key="terse") + '\nprint("the tool could not be installed")\n'
        package(self.area, "terse", body)
        report = check(self.area / "terse")
        self.assertTrue(report.findings["recovers"])

    def test_the_same_problem_with_the_command_passes_recovers(self) -> None:
        body = PROJECTS.format(key="kind") + '\nprint("the tool could not be installed; run `brew install it`")\n'
        package(self.area, "kind", body)
        self.assertEqual(check(self.area / "kind").findings["recovers"], [])

    def test_an_entry_point_the_package_does_not_ship_fails_and_the_six_are_said_not_to_have_run(self) -> None:
        """Until #117 this passed: nothing was checked, so nothing failed, and a package with no entry point
        at all could be published. The six still cannot be run; what fails is that the package is not whole."""
        place = package(self.area, "absent", "")
        (place / "init.py").unlink()
        report = check(place)
        self.assertEqual(list(report.findings), ["ships"])
        self.assertEqual(len(report.findings["ships"]), 2, "`init`, and `project` which defaults to it")
        self.assertEqual(len(report.not_run), 6)
        self.assertIn("init.py", report.not_run["idempotent"])
        self.assertFalse(report.passed)

if __name__ == "__main__":
    unittest.main()
