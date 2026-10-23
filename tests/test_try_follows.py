"""Try it follows trunk, and the seed door is a Make target — slices 20.5 and 20.8 of the feedback-points plan.

After a granted merge the harbourmaster moves a running Try it to the trunk it made; a stopped one is a
person's to start. The keel writes `seed-<service>` where a language's tooling answers `seed`, and the Try
it script runs it before a story's first step — or says *no seed door yet* where the Makefile has none.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401
from harbourmaster_fixture import MergeFixture

from slipwai.assets import TOOLKIT_ROOT
from slipwai.project import makefile

FAKE_TRY_IT = """import sys, pathlib
pathlib.Path(".slipwai/try-it/ran.txt").open("a").write(" ".join(sys.argv[1:]) + "\\n")
"""


class FollowsTrunkTest(MergeFixture):
    def try_state(self, state: str) -> None:
        home = self.root / ".slipwai/try-it"
        home.mkdir(parents=True, exist_ok=True)
        (home / "state.json").write_text(json.dumps({"state": state, "url": "http://localhost:4173"}), encoding="utf-8")
        (self.root / "scripts/agents/try_it.py").write_text(FAKE_TRY_IT, encoding="utf-8")

    def ran(self) -> list[str]:
        path = self.root / ".slipwai/try-it/ran.txt"
        return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []

    def merge(self) -> None:
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        done = self.run_once()
        self.assertEqual(self.answer().kind, "granted", done.stdout + done.stderr)

    def test_a_running_try_it_is_refreshed_once_after_a_granted_merge(self) -> None:
        self.try_state("ready")
        self.merge()
        import time
        for _ in range(50):
            if self.ran():
                break
            time.sleep(0.1)
        self.assertEqual(self.ran(), ["refresh"])
        self.assertIn("refresh after ORD-01 merged", (self.root / ".slipwai/try-it/harbourmaster.log").read_text())

    def test_a_stopped_try_it_is_left_stopped(self) -> None:
        self.try_state("stopped")
        self.merge()
        self.assertEqual(self.ran(), [])


class SeedDoorTargetTest(unittest.TestCase):
    def test_the_seed_target_is_written_where_the_tooling_answers_seed_and_not_otherwise(self) -> None:
        service: Any = mock.Mock()
        service.name = "recap-api"
        service.selection.migrating_feature = "postgres"
        tooling = {"install": "npm ci", "seed": "npm run seed -- $(FILE)"}
        with mock.patch.object(makefile, "app_tooling", return_value=tooling), \
             mock.patch.object(makefile, "install_step", return_value=(" node_modules/.package-lock.json", "")):
            text = makefile.seed_targets([service], [service])
        self.assertIn("seed-recap-api: node_modules/.package-lock.json ## Append the events a slice's try-it.json "
                      "gives", text)
        self.assertIn("\tnpm run seed -- $(FILE)", text)
        self.assertIn("# backing-service:postgres:begin", text)
        with mock.patch.object(makefile, "app_tooling", return_value={"install": "npm ci"}):
            self.assertEqual(makefile.seed_targets([service], [service]), "")


class SeedDoorRunTest(unittest.TestCase):
    """Try it runs the door before a story's first step, with every story's givens in one file."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()) / "shop"
        (self.root / "scripts/agents").mkdir(parents=True)
        (self.root / "scripts/agents/try_it.py").write_text((TOOLKIT_ROOT / "scripts/agents/try_it.py").read_text(),
                                                            encoding="utf-8")
        (self.root / "project.json").write_text(json.dumps({"name": "shop", "deployables": {
            "service": {"kind": "service", "path": "apps/service", "port": 3000, "selection": {"http": "fastify"}}}}),
            encoding="utf-8")
        spec = importlib.util.spec_from_file_location("try_it_door", self.root / "scripts/agents/try_it.py")
        assert spec and spec.loader
        module: Any = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.module = module
        self.module.request = lambda method, address, body=None, token="", headers=None: {"id": "r-1"}
        self.module.token_for = lambda who, env, where: "t"
        place = self.root / "specs/001-shop/slices/CU5"
        place.mkdir(parents=True)
        (place / "try-it.json").write_text(json.dumps({
            "as": "ada", "open": [{"label": "The recap", "path": "/books/cs-1"}],
            "given": [{"stream": "book-cs-1", "event": "BookImported", "data": {"bookId": "cs-1"}}],
            "steps": [{"method": "GET", "path": "/api/books/cs-1"}]}), encoding="utf-8")

    def test_no_door_in_the_makefile_fails_the_giving_story_saying_so(self) -> None:
        (self.root / "Makefile").write_text("dev:\n\t@true\n", encoding="utf-8")
        state: dict = {}
        self.module.seed(self.root, {}, state, only_new=False)
        self.assertEqual(state["seeded"], [])
        self.assertEqual(state["seed_failed"][0]["step"], "given")
        self.assertIn("no seed door yet: the Makefile has no seed-service target", state["seed_failed"][0]["said"])

    def test_the_door_is_run_once_with_the_givens_and_a_green_story_s_links_say_given(self) -> None:
        # The door says which file it was handed, and the test reads the givens from that file. `echo` rather
        # than `cat`: `make` runs a recipe in `cmd.exe` on Windows, which has the one and not the other.
        (self.root / "Makefile").write_text("seed-service:\n\t@echo $(FILE)> seeded-from.txt\n", encoding="utf-8")
        state: dict = {}
        self.module.seed(self.root, {}, state, only_new=False)
        self.assertEqual(state["seeded"], ["001-shop/CU5"], state.get("seed_failed"))
        handed = Path((self.root / "seeded-from.txt").read_text(encoding="utf-8").strip())
        given = json.loads(handed.read_text(encoding="utf-8"))
        self.assertEqual(given, [{"stream": "book-cs-1", "event": "BookImported", "data": {"bookId": "cs-1"},
                                  "slice": "001-shop/CU5"}])
        self.assertEqual(state["given"], {"001-shop/CU5": 1})
        self.assertTrue(state["links"][0]["given"])

    def test_a_door_that_refuses_fails_the_story(self) -> None:
        (self.root / "Makefile").write_text("seed-service:\n\t@echo 'DATABASE_URL is unset' >&2; exit 2\n",
                                            encoding="utf-8")
        state: dict = {}
        self.module.seed(self.root, {}, state, only_new=False)
        self.assertEqual(state["seeded"], [])
        self.assertIn("the seed door refused", state["seed_failed"][0]["said"])


if __name__ == "__main__":
    unittest.main()
