"""The app and the project it opens are the same release, or each side says so.

2.1 moved a run's own state under `.slipwai/run/`. A 2.0 app opened on a migrated project shows an empty board
and writes a person's answers where no captain reads them, so the app now holds itself to the release that
last wrote the project (`generator.updatedWith`), and tells the project's own scripts which release it is so
they can hold it to the same thing from the other side.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import app_version
from slipwai.assets import TOOLKIT_ROOT, VERSION


def stamp(root: Path, version: str) -> None:
    path = root / "project.json"
    document = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    document["generator"] = {"name": "slipwai", "generatedWith": "2.0.0", "updatedWith": version}
    path.write_text(json.dumps(document), encoding="utf-8")


class StandingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_a_project_ahead_of_the_app_is_refused_with_both_versions_and_what_to_do(self) -> None:
        stamp(self.root, "2.2.0")
        said = app_version.refusal(self.root, "2.1.0")
        self.assertIn("2.2.0", said)
        self.assertIn("2.1.0", said)
        self.assertIn("update the app", said)

    def test_a_project_behind_the_app_is_told_to_migrate_and_not_refused(self) -> None:
        stamp(self.root, "2.0.1")
        self.assertEqual(app_version.refusal(self.root, "2.1.0"), "")
        self.assertIn("slipwai migrate", app_version.notice(self.root, "2.1.0"))

    def test_the_same_release_and_a_folder_with_no_record_say_nothing(self) -> None:
        self.assertEqual(app_version.notice(self.root, "2.1.0"), "", "no project.json")
        stamp(self.root, "2.1.0")
        self.assertEqual(app_version.notice(self.root, "2.1.0"), "")

    def test_a_snapshot_is_behind_its_release(self) -> None:
        stamp(self.root, "2.1.0")
        self.assertEqual(app_version.standing(self.root, "2.1.0.dev3"), "newer")

    def test_the_notice_is_the_first_thing_in_the_body(self) -> None:
        stamp(self.root, "9.0.0")
        page = app_version.with_notice("<html><body class='x'><h1>Board</h1></body></html>", self.root, "2.1.0")
        self.assertLess(page.index("app-version"), page.index("<h1>"))
        self.assertGreater(page.index("app-version"), page.index("<body"))


class BoardRefusesTest(BoardTest):
    """A board older than its project changes nothing, and says why on the page and in the refusal."""

    def test_every_change_is_refused_and_every_page_says_why(self) -> None:
        stamp(self.root, "99.0.0")
        code, said = self.post("/tell", {"fairway": "ORD", "message": "lost if it were written"})
        self.assertEqual(code, 409, said)
        self.assertIn("update the app", said)
        self.assertEqual([e for e in self.read("ORD") if e.kind == "told"], [])
        code, page = self.get("/")
        self.assertEqual(code, 200)
        self.assertIn("app-version refused", page)

    def test_a_project_at_this_release_is_left_alone(self) -> None:
        stamp(self.root, VERSION)
        code, _ = self.post("/tell", {"fairway": "ORD", "message": "kept"})
        self.assertEqual(code, 200)
        self.assertNotIn("app-version", self.get("/")[1])


class FleetRefusesTest(unittest.TestCase):
    """The project's own `fleet.py` refuses an older app that names itself, and never a person at a terminal."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "scripts/agents").mkdir(parents=True)
        for name in ("fleet.py", "clearance.py", "logs.py", "berths.py", "abreast.py", "telegraph.py",
                     "inbox.py", "ids.py"):
            shutil.copy(TOOLKIT_ROOT / "scripts/agents" / name, self.root / "scripts/agents" / name)
        stamp(self.root, "2.2.0")

    def tell(self, app: str | None) -> subprocess.CompletedProcess:
        environment = {k: v for k, v in os.environ.items() if k != "SLIPWAI_APP_VERSION"}
        if app is not None:
            environment["SLIPWAI_APP_VERSION"] = app
        return subprocess.run([sys.executable, "scripts/agents/fleet.py", "tell", "ORD", "hello"],
                              cwd=self.root, capture_output=True, text=True, env=environment, timeout=60)

    def test_an_older_app_is_refused_and_nothing_is_written(self) -> None:
        done = self.tell("2.1.0")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn("Update the app to 2.2.0", done.stderr)

    def test_a_person_at_the_terminal_is_never_refused_here(self) -> None:
        self.assertNotIn("Update the app", self.tell(None).stderr)

    def test_an_app_at_the_project_s_release_is_not_refused(self) -> None:
        self.assertNotIn("Update the app", self.tell("2.2.0").stderr)


if __name__ == "__main__":
    unittest.main()
