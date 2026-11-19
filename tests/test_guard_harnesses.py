"""Which harness holds which guard, said once and held to what is actually written.

Only Claude Code got `before-search`, and nothing said so: an extension that declared a guard was installed
and agreed to on Cursor or Gemini CLI and silently refused nothing there, and its guidance told the agent
about a guard that was not holding (#121). A harness holds a guard point where its registry row records a
hook that can refuse at that moment *and* a projection whose shape somebody read. For Cursor and Gemini CLI
that is the stop hook and nothing before a tool call, so nothing is projected for them — a row written from
a guess would be a guard that looks installed.

What is done instead is that the fact is stated: a table on the contract page, and `SLIPWAI_GUARDS_HELD`
handed to an extension at `init` and `project`, so its guidance can say truthfully whether a guard holds
here. The cases below hold the table and the variable to the rows the keel and the projector really write.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from guard_project import TOOLKIT, Project

from slipwai import guards
from slipwai.layout import AT_ROOT
from slipwai.project.agent_settings import harness_hooks

DOCS = Path(__file__).resolve().parents[1] / "docs/extensions.md"
REGISTRY = TOOLKIT / "scripts/agents/registry.json"
#: Every moment a guard's script can be run at: the seven it may refuse at, and the one it is only told at.
MOMENTS = (*guards.NAMES, "tool-use")
PRINTS = ("import os, sys\nfrom pathlib import Path\n"
          "(Path(__file__).parent / (os.environ['SLIPWAI_POINT'] + '.held')).write_text("
          "os.environ.get('SLIPWAI_GUARDS_HELD', 'not handed'), encoding='utf-8')\n")


def rows() -> dict[str, dict]:
    return {row["key"]: row for row in json.loads(REGISTRY.read_text(encoding="utf-8"))["harnesses"]}


def recorded(row: dict) -> list[str]:
    """What the registry says this harness holds, read the way a project reads it."""
    hooks = row.get("hooks") or {}
    projection = hooks.get("projection") or {}
    named = hooks.get("guards", list(projection.get("events", {})))
    return [moment for moment in MOMENTS if moment in named]


class RecordedTest(unittest.TestCase):
    def test_claude_code_is_recorded_as_holding_exactly_what_the_keel_writes_for_it(self) -> None:
        """Its rows are the keel's own (`agent_settings.harness_hooks`), so the registry's claim is held to
        them — and `tool-use` to the row `guard_harness.py` writes from an agreement."""
        written = set()
        for event in harness_hooks(AT_ROOT).values():
            for row in event:
                hooked = row["hooks"]
                assert isinstance(hooked, list)
                written |= {str(hook["command"]).rsplit(" ", 1)[-1] for hook in hooked}
        self.assertEqual(recorded(rows()["claude"]), [m for m in MOMENTS if m in written or m == "tool-use"])
        self.assertEqual(set(guards.NAMES) - written, set(), "a guard point the keel writes no row for")

    def test_cursor_and_gemini_hold_the_stop_and_nothing_before_a_tool_call(self) -> None:
        """What their rows record is a stop hook. Neither row records a pre-tool event whose shape was read,
        so `before-search` is not projected for them, and is not claimed."""
        for key in ("cursor-agent", "gemini"):
            with self.subTest(harness=key):
                self.assertEqual(recorded(rows()[key]), ["before-stop"])
                self.assertNotIn("before-search", json.dumps(rows()[key]["hooks"]["projection"]))

    def test_no_other_harness_is_recorded_as_holding_anything(self) -> None:
        holding = {key for key, row in rows().items() if recorded(row)}
        self.assertEqual(holding, {"claude", "cursor-agent", "gemini"})

    def test_a_row_claims_only_moments_there_are(self) -> None:
        for key, row in rows().items():
            for named in (row.get("hooks") or {}).get("guards", []):
                with self.subTest(harness=key, named=named):
                    self.assertIn(named, MOMENTS)


class PageTest(unittest.TestCase):
    def table(self) -> dict[str, list[str]]:
        section = DOCS.read_text(encoding="utf-8").split("## Which harness holds which guard", 1)[1]
        section = section.split("\n## ", 1)[0]
        header = [cell.strip(" `") for cell in re.search(r"^\| Harness \|(.*)\|$", section, re.M).group(1).split("|")]  # type: ignore[union-attr]
        found = {}
        for key, cells in re.findall(r"^\| [^|]*\(`([a-z-]+)`\) \|(.*)\|$", section, re.M):
            marks = [cell.strip() for cell in cells.split("|")]
            found[key] = [moment for moment, mark in zip(header, marks, strict=True) if mark == "yes"]
        self.assertEqual(header, list(MOMENTS))
        return found

    def test_the_page_says_what_the_registry_records_and_no_more(self) -> None:
        self.assertEqual(self.table(), {key: recorded(row) for key, row in rows().items() if recorded(row)})


class HandedTest(unittest.TestCase):
    """An extension is told at `init` and at `project`, for the harnesses installed in this project."""

    def setUp(self) -> None:
        self.project = Project()
        self.addCleanup(self.project.close)
        (self.project.root / "scripts/agents/registry.json").write_text(
            REGISTRY.read_text(encoding="utf-8"), encoding="utf-8")
        self.home = self.project.extension("cg", {}, **{"init.py": PRINTS})
        (self.project.extensions / "available.json").write_text(
            json.dumps({"cg": {"init": {"run": "init.py"}, "project": {"run": "init.py"}}}), encoding="utf-8")
        self.project.run("hooks.py", "--elect", "cg")

    def installed(self, *keys: str) -> None:
        (self.project.root / ".specify").mkdir(exist_ok=True)
        (self.project.root / ".specify/integration.json").write_text(
            json.dumps({"installed_integrations": list(keys)}), encoding="utf-8")

    def held_at(self, point: str, **named: str) -> dict:
        self.project.run("hooks.py", point, **named)
        return json.loads((self.home / f"{point}.held").read_text(encoding="utf-8"))

    def test_it_is_handed_each_installed_harness_and_what_holds_there(self) -> None:
        self.installed("claude", "gemini", "opencode")
        held = self.held_at("project")
        self.assertEqual(held, {"claude": list(MOMENTS), "gemini": ["before-stop"], "opencode": []})

    def test_the_harness_this_init_is_installing_is_there_before_its_record_is(self) -> None:
        self.assertEqual(self.held_at("init", SLIPWAI_INTEGRATION="cursor-agent"), {"cursor-agent": ["before-stop"]})

    def test_the_same_answer_is_one_command_away(self) -> None:
        self.installed("claude")
        done = self.project.run("guard_harness.py", "--held")
        self.assertEqual(json.loads(done.stdout), {"claude": list(MOMENTS)})

    def test_a_project_with_no_registry_is_told_nothing_rather_than_a_guess(self) -> None:
        (self.project.root / "scripts/agents/registry.json").unlink()
        self.installed("claude")
        self.assertEqual(self.held_at("project"), {})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
