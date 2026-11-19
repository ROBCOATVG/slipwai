"""Agreeing to a guard, or taking the agreement back, leaves the project's gate green with nothing else run.

An extension's block in `AGENTS.md` may say whether its guard holds here *and has been agreed to* — that is
what `SLIPWAI_GUARDS_HELD` is handed to its `project` hook for. `guards.py --elect` and `--remove` changed
the agreement and fired no `project` point, so the block was one step behind the moment a person did what
they had been told to do, and `make check-extensions` was red until somebody thought to run `make agents`.
The same person typing *yes* at `make agents`' own question was left in the same place, by the same cause.

An action a person is told to take does not leave the gate red. So the command that changes an agreement
brings what is derived from it up to date before it returns — the harness's row, the extension's guidance,
the copy of that guidance a harness reads — says what it did, and is never failed by a hook: the agreement
is the registry, and a hook that crashed is said, by name, with the command that runs it again.

The extension here is a stand-in shaped like the real one: `GUIDANCE` worked out from the agreement and what
it was handed, a `project` hook that writes it, a `check` hook that fails when it is stale.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from types import ModuleType

import checkout_packages  # noqa: F401
from guard_project import TOOLKIT, Project

from slipwai.layout import AT_ROOT
from slipwai.project.agent_settings import harness_hooks

DECLARED = {"before-search": {"run": "g.py", "budget": "5s", "sees": ["mcp__cg__.*"]}}
#: `GUIDANCE` as the real extension works it out: from the registry, and from what the keel says holds here.
INIT = '''\
import json, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
def held():
    if "SLIPWAI_GUARDS_HELD" in os.environ:
        return json.loads(os.environ["SLIPWAI_GUARDS_HELD"])
    import guard_harness
    return guard_harness.held()
def agreed():
    try:
        found = json.loads((ROOT / ".slipwai/guards.json").read_text(encoding="utf-8"))["guards"]
    except (OSError, ValueError, KeyError):
        return False
    return any(body.get("extension") == "cg" for body in found.get("before-search", []))
holding = sorted(key for key, moments in held().items() if "before-search" in moments)
state = "not held" if not holding else ("held and agreed" if agreed() else "available, not agreed")
GUIDANCE = f"<!-- extension:cg:begin -->\\nIts guard: {state} ({', '.join(holding)}).\\n<!-- extension:cg:end -->"
'''
PROJECT = '''\
import os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]
if (HERE / "crash").is_file():
    raise RuntimeError("the floor gave way")
if (HERE / "hang").is_file():
    import time
    time.sleep(600)
assert os.environ["SLIPWAI_POINT"] == "project" and "SLIPWAI_GUARDS_HELD" in os.environ
from guidance import replace_block
from init import GUIDANCE
replace_block("cg", GUIDANCE)
print("cg: wrote its block")
'''
CHECK = '''\
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]
from guidance import installed_block
from init import GUIDANCE
if installed_block("cg") != GUIDANCE:
    print("check-cg: the block is stale", file=sys.stderr)
    sys.exit(1)
'''
HOOKS = {"project": {"run": "project.py", "budget": "30s"}, "check": {"run": "check.py"}}


class Agreeable(unittest.TestCase):
    """A project on Claude Code that elected `cg`, projected it, and has agreed to nothing."""

    hooks = HOOKS

    def setUp(self) -> None:
        self.project = Project()
        self.addCleanup(self.project.close)
        root = self.project.root
        (root / "scripts/agents/registry.json").write_text(
            (TOOLKIT / "scripts/agents/registry.json").read_text(encoding="utf-8"), encoding="utf-8")
        (root / ".specify").mkdir()
        (root / ".specify/integration.json").write_text(
            json.dumps({"installed_integrations": ["claude"]}), encoding="utf-8")
        self.settings = root / ".claude/settings.json"
        self.settings.parent.mkdir()
        self.settings.write_text(json.dumps({"hooks": harness_hooks(AT_ROOT)}, indent=2) + "\n", encoding="utf-8")
        self.agents = root / "AGENTS.md"
        self.agents.write_text("# Guidance\n\nWritten by a person.\n", encoding="utf-8")
        self.home = self.project.extension("cg", DECLARED, **{"init.py": INIT, "project.py": PROJECT,
                                                              "check.py": CHECK, "g.py": ""})
        (self.project.extensions / "available.json").write_text(json.dumps({"cg": self.hooks}), encoding="utf-8")
        self.project.elected("cg")
        self.project.run("hooks.py", "--elect", "cg")
        self.assertEqual(self.make_agents().returncode, 0)
        self.assertIn("Its guard: available, not agreed (claude).", self.agents.read_text(encoding="utf-8"))
        self.assertEqual(self.check(), "")

    def make_agents(self) -> subprocess.CompletedProcess:
        """The first command of `make agents`, with nobody at a terminal."""
        return self.project.run("project.py")

    def check(self) -> str:
        """`make check-extensions`: both of its commands. What they said where the gate is red, else nothing."""
        said = ""
        for script, arguments in (("project.py", ["--check"]), ("hooks.py", ["check", "--fatal"])):
            done = self.project.run(script, *arguments)
            said += done.stderr if done.returncode else ""
        return said

    def tells(self) -> list[str]:
        """The tools the harness tells an agreed guard about."""
        rows = json.loads(self.settings.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
        return [row["matcher"] for row in rows if row["hooks"][0]["command"].endswith(" tool-use")]


class ElectTest(Agreeable):
    def test_the_gate_is_green_the_moment_it_returns(self) -> None:
        done = self.project.guards("--elect", "cg")
        self.assertEqual(done.returncode, 0, done.stderr)
        written = self.agents.read_text(encoding="utf-8")
        self.assertTrue(written.startswith("# Guidance\n\nWritten by a person.\n"), written)
        self.assertIn("Its guard: held and agreed (claude).", written)
        self.assertEqual(self.check(), "")

    def test_it_says_what_it_brought_up_to_date_in_the_order_it_did_it(self) -> None:
        done = self.project.guards("--elect", "cg")
        self.assertEqual(done.stdout.splitlines(), [
            "guards: 1 extension(s) may refuse at before-search",
            "guards: .claude/settings.json now tells an agreed guard about mcp__cg__.*",
            "cg: wrote its block",
            "guards: cg's guidance is up to date with this agreement: its `project` hook ran",
        ])
        self.assertEqual(done.stderr, "")
        self.assertEqual(self.tells(), ["mcp__cg__.*"])

    def test_agreeing_again_changes_no_file(self) -> None:
        self.project.guards("--elect", "cg")
        before = [path.read_bytes() for path in (self.agents, self.settings, self.project.registry)]
        self.assertEqual(self.project.guards("--elect", "cg").returncode, 0)
        self.assertEqual([path.read_bytes() for path in (self.agents, self.settings, self.project.registry)], before)

    def test_only_the_extension_whose_agreement_changed_is_projected_again(self) -> None:
        other = self.project.extension("lint", {"before-write": {"run": "w.py"}}, **{
            "project.py": "from pathlib import Path\n(Path(__file__).parent / 'fired').write_text('', 'utf-8')\n"})
        (self.project.extensions / "available.json").write_text(
            json.dumps({"cg": self.hooks, "lint": {"project": {"run": "project.py"}}}), encoding="utf-8")
        self.project.run("hooks.py", "--elect", "cg", "lint")
        self.project.guards("--elect", "cg")
        self.assertFalse((other / "fired").exists())

    def test_an_extension_that_is_not_elected_here_is_agreed_to_and_said_to_have_no_guidance(self) -> None:
        self.project.extension("stray", {"before-write": {"run": "w.py"}})
        done = self.project.guards("--elect", "stray")
        self.assertEqual((done.returncode, self.project.agreed()["before-write"]), (0, ["stray"]))
        self.assertIn("guards: stray is not elected here, so it has no guidance to bring up to date", done.stdout)


class RemoveTest(Agreeable):
    def test_the_gate_is_green_the_moment_it_returns(self) -> None:
        self.project.guards("--elect", "cg")
        done = self.project.guards("--remove", "cg")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.splitlines(), [
            "guards: 0 extension(s) may refuse at no guard",
            "guards: .claude/settings.json now tells an agreed guard about nothing",
            "cg: wrote its block",
            "guards: cg's guidance is up to date with this agreement: its `project` hook ran",
        ])
        self.assertIn("Its guard: available, not agreed (claude).", self.agents.read_text(encoding="utf-8"))
        self.assertEqual(self.tells(), [])
        self.assertEqual(self.check(), "")

    def test_removing_what_was_never_agreed_to_projects_nothing(self) -> None:
        before = self.agents.read_bytes()
        done = self.project.guards("--remove", "cg")
        self.assertEqual(done.stdout.splitlines(), ["guards: cg has no guard agreed to here, so nothing was removed"])
        self.assertEqual(self.agents.read_bytes(), before)


class MakeAgentsTest(Agreeable):
    """`make agents` asks last, after it has projected. A yes there is the person's own `--elect`."""

    def offer(self) -> ModuleType:
        path = self.project.extensions / "guard_offer.py"
        spec = importlib.util.spec_from_file_location(f"guard_offer_current_{id(self)}", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(module)
        return module

    def test_a_yes_at_its_question_is_in_the_guidance_when_that_run_ends(self) -> None:
        self.make_agents()
        shown: list[str] = []
        self.offer().announce(terminal=True, ask=lambda text: "y", say=shown.append)
        self.assertEqual(self.project.agreed(), {"before-search": ["cg"]})
        self.assertIn("Its guard: held and agreed (claude).", self.agents.read_text(encoding="utf-8"))
        self.assertEqual(self.check(), "")
        self.assertIn("guards: cg's guidance is up to date with this agreement: its `project` hook ran",
                      "\n".join(shown))

    def test_a_no_leaves_every_file_as_the_projection_left_it(self) -> None:
        self.make_agents()
        before = self.agents.read_bytes()
        self.offer().announce(terminal=True, ask=lambda text: "n", say=lambda line: None)
        self.assertFalse(self.project.registry.exists())
        self.assertEqual(self.agents.read_bytes(), before)
        self.assertEqual(self.check(), "")

    def test_with_nobody_at_a_terminal_it_asks_nothing_and_writes_no_agreement(self) -> None:
        done = self.make_agents()
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("[y/N]", done.stdout)
        self.assertIn("It refuses nothing until a person agrees", done.stdout)
        self.assertFalse(self.project.registry.exists())
        self.assertEqual(self.check(), "")

    def test_what_a_failed_hook_said_reaches_the_person_who_answered_yes(self) -> None:
        (self.home / "crash").write_text("", encoding="utf-8")
        shown: list[str] = []
        self.offer().announce(terminal=True, ask=lambda text: "y", say=shown.append)
        self.assertEqual(self.project.agreed(), {"before-search": ["cg"]})
        self.assertIn("hook cg project: exited 1; RuntimeError: the floor gave way", "\n".join(shown))


class TheHookFailsTest(Agreeable):
    """The agreement is the registry. A hook that crashed is said by name, and is never why `--elect` failed."""

    def test_a_crash_is_said_by_name_and_the_agreement_stands(self) -> None:
        (self.home / "crash").write_text("", encoding="utf-8")
        done = self.project.guards("--elect", "cg")
        self.assertEqual(done.returncode, 0)
        self.assertEqual(self.project.agreed(), {"before-search": ["cg"]})
        self.assertEqual(self.tells(), ["mcp__cg__.*"])
        self.assertEqual(done.stderr.splitlines(), [
            "hook cg project: exited 1; RuntimeError: the floor gave way",
            "guards: cg's `project` hook did not finish (the `hook cg project` line above). The agreement is "
            "recorded and stands, and cg's AGENTS.md block was written from its GUIDANCE, so it is current; "
            "`make agents` runs the hook again for anything else it does.",
        ])
        self.assertEqual(self.check(), "")

    def test_a_hook_over_its_budget_is_ended_and_said_the_same_way(self) -> None:
        (self.home / "hang").write_text("", encoding="utf-8")
        (self.project.extensions / "available.json").write_text(
            json.dumps({"cg": {**self.hooks, "project": {"run": "project.py", "budget": "1s"}}}), encoding="utf-8")
        self.project.run("hooks.py", "--elect", "cg")
        done = self.project.guards("--elect", "cg")
        self.assertEqual(done.returncode, 0)
        self.assertEqual(self.project.agreed(), {"before-search": ["cg"]})
        self.assertIn("hook cg project: over its 1s budget, ended", done.stderr)
        self.assertIn("`make agents` runs the hook again", done.stderr)

    def test_where_nothing_else_can_write_the_block_it_says_it_is_behind_and_what_retries(self) -> None:
        """No `GUIDANCE` to write the block from: the hook was the only writer, and it crashed."""
        (self.home / "crash").write_text("", encoding="utf-8")
        (self.home / "init.py").write_text("raise RuntimeError('no guidance to read')\n", encoding="utf-8")
        before = self.agents.read_bytes()
        done = self.project.guards("--elect", "cg")
        self.assertEqual(done.returncode, 0)
        self.assertEqual(self.project.agreed(), {"before-search": ["cg"]})
        self.assertEqual(self.agents.read_bytes(), before)
        self.assertEqual(done.stderr.splitlines()[-1],
                         "guards: cg's `project` hook did not finish (the `hook cg project` line above), so what "
                         "cg says in AGENTS.md may be as it was before this agreement changed. The agreement is "
                         "recorded and stands; `make agents` runs the hook again.")
        (self.home / "crash").unlink()  # and `make agents` is the retry it names
        (self.home / "init.py").write_text(INIT, encoding="utf-8")
        self.assertIn("cg: wrote its block", self.make_agents().stdout)

    def test_a_project_from_before_the_projector_could_do_this_is_told_the_one_command(self) -> None:
        (self.project.extensions / "project.py").unlink()
        done = self.project.guards("--elect", "cg")
        self.assertEqual(done.returncode, 0)
        self.assertEqual(self.project.agreed(), {"before-search": ["cg"]})
        self.assertIn("guards: what cg says in AGENTS.md could not be brought up to date from here "
                      "(scripts/extensions/project.py is not in this project). The agreement is recorded and "
                      "stands; `make agents` brings it up to date.", done.stderr)


class CopiedTest(Agreeable):
    """A harness that reads a copy of `AGENTS.md`'s extension guidance — Gemini CLI's `GEMINI.md` — is given
    the new one, or `make check-agents` is the gate left red instead."""

    def setUp(self) -> None:
        super().setUp()
        root = self.project.root
        for source in sorted((TOOLKIT / "scripts/agents").glob("*.py"), key=lambda path: path.name):
            (root / "scripts/agents" / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        (root / ".specify/integration.json").write_text(
            json.dumps({"installed_integrations": ["claude", "gemini"]}), encoding="utf-8")
        self.copy = root / "GEMINI.md"
        self.copy.write_text("# Gemini\n", encoding="utf-8")
        self.assertEqual(self.project.run("../agents/project.py", "--context").returncode, 0)
        self.assertIn("Its guard: available, not agreed (claude).", self.copy.read_text(encoding="utf-8"))

    def test_the_copy_follows_the_agreement_both_ways(self) -> None:
        done = self.project.guards("--elect", "cg")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("Its guard: held and agreed (claude).", self.copy.read_text(encoding="utf-8"))
        self.assertEqual(done.stdout.splitlines()[-1], "Extension pointers projected for Gemini CLI (gemini).")
        self.assertNotIn("Extension pointers", self.project.guards("--elect", "cg").stdout)  # nothing moved
        self.project.guards("--remove", "cg")
        self.assertIn("Its guard: available, not agreed (claude).", self.copy.read_text(encoding="utf-8"))

    def test_a_copy_that_could_not_be_written_is_said_with_the_command_and_the_agreement_stands(self) -> None:
        (self.project.root / "scripts/agents/project.py").write_text("raise SystemExit(1)\n", encoding="utf-8")
        done = self.project.guards("--elect", "cg")
        self.assertEqual(done.returncode, 0)
        self.assertEqual(self.project.agreed(), {"before-search": ["cg"]})
        self.assertEqual(done.stderr.splitlines(), [
            "guards: AGENTS.md says what is agreed to now, but the copy of its extension guidance a harness "
            "reads could not be written (project.py --context: 1). The agreement is recorded and stands; "
            "`make agents` writes the copy."])


class NoHookTest(Agreeable):
    """An extension that attaches nothing to `project`: its block is written from its `GUIDANCE`, as
    `make agents` writes it."""

    hooks = {"check": {"run": "check.py"}}

    def test_its_block_is_written_from_its_guidance(self) -> None:
        done = self.project.guards("--elect", "cg")
        self.assertEqual(done.stdout.splitlines()[-1],
                         "guards: cg's guidance is up to date with this agreement: its AGENTS.md block was "
                         "written from its GUIDANCE")
        self.assertEqual(self.check(), "")
        self.assertEqual(self.project.guards("--remove", "cg").returncode, 0)
        self.assertEqual(self.check(), "")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
