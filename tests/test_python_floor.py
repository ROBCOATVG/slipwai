"""One Python floor: the one the package declares, the board installs to, and every project check asks for."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import prerequisites

ROOT = Path(__file__).resolve().parents[1]


class FloorTest(unittest.TestCase):
    def test_every_python_floor_a_project_checks_is_the_one_the_board_installs_to(self) -> None:
        """`make check-python` and the fleet's preflight said 3.10 while the toolkit imports 3.11's
        `datetime.UTC` and `tomllib`: a 3.10 passed both checks and then failed in the first gate script."""
        floor = ", ".join(str(part) for part in prerequisites.PYTHON_FLOOR)
        for path in ("src/slipwai/project/agent_targets.py", "assets/toolkit/scripts/agents/preflight.py"):
            held = (ROOT / path).read_text(encoding="utf-8")
            self.assertEqual(re.findall(r"sys\.version_info >= \(([\d, ]+)\)", held), [floor], path)
        self.assertIn(f'requires-python = ">={floor.replace(", ", ".")}"',
                      (ROOT / "pyproject.toml").read_text(encoding="utf-8"))
