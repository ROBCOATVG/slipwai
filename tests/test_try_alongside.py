"""What runs beside the apps for the stories: the processes a project declares, and nothing it did not.

recap's stories connect to an Audiobookshelf server, and the project's stub for one was started by hand from a
quickstart or nowhere, so six stories answered `serverUnreachable` on every Try it.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

SCRIPT = TOOLKIT_ROOT / "scripts/agents/try_it.py"


def load() -> Any:
    spec = importlib.util.spec_from_file_location("try_it_alongside", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AlongsideTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.module = load()

    def declare(self, body: object) -> None:
        path = self.root / self.module.ALONGSIDE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body), encoding="utf-8")

    def test_a_project_that_declares_nothing_runs_nothing_beside_its_apps(self) -> None:
        self.assertEqual(self.module.alongside(self.root), [])

    def test_each_declared_process_is_kept_with_its_command_and_where_it_answers(self) -> None:
        stub = {"name": "audiobookshelf-stub", "run": ["npx", "tsx", "stub.ts", "--port", "13378"],
                "answers": "http://127.0.0.1:13378/status"}
        self.declare([stub])
        self.assertEqual(self.module.alongside(self.root), [stub])

    def test_an_entry_with_no_name_or_no_command_is_left_out_rather_than_run(self) -> None:
        self.declare([{"run": ["true"]}, {"name": "x", "run": "a string, not an argv"}, {"name": "y", "run": []}])
        self.assertEqual(self.module.alongside(self.root), [])

    def test_a_file_that_is_not_a_list_runs_nothing(self) -> None:
        self.declare({"name": "x", "run": ["true"]})
        self.assertEqual(self.module.alongside(self.root), [])


if __name__ == "__main__":
    unittest.main()
