"""The second closed set: the three moments an extension may refuse a tool call, and what refusing does.

`hooks.py`'s second rule is that a hook is never fatal to the rung, and that rule left one thing
unbuildable: an extension that wants to say *don't grep for that, ask the index* is answering a tool call
that has not happened yet, not reporting after the fact. Widening `hooks` would have made every hook able to
fail a rung. So a guard is its own kind, and these are the differences that make it safe to have.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai import guards, hooks
from slipwai.assets import TOOLKIT_ROOT

RUNNER = TOOLKIT_ROOT / "scripts/extensions/guards.py"


class SetTest(unittest.TestCase):
    def test_the_seven_are_the_set_and_an_eighth_is_refused(self) -> None:
        self.assertEqual(guards.NAMES, ("session", "before-search", "before-write", "before-command",
                                        "before-fetch", "after-delegate", "before-stop"))
        with self.assertRaises(KeyError) as refused:
            guards.guard("before-merge")
        self.assertIn("is not a guard the keel fires", str(refused.exception))

    def test_every_shape_a_tool_call_comes_in_has_a_point(self) -> None:
        """The four added on 2026-10-08 are shapes, not guesses: a path, a command, a URL and the end of a
        session. A guard that wanted one of these before had to be a `before-search` pretending, or a
        harness's own hook — which is how version 1's control-file refusal came to work on one harness.

        What a guard is handed is the test of whether a shape is really its own. A path is not a query and a
        host is not a path, so the three cannot be folded into one point without the point handing over a
        bag of maybes.
        """
        given = {one.name: set(one.given) for one in guards.GUARDS}
        self.assertIn("path", given["before-write"])
        self.assertIn("command", given["before-command"])
        self.assertIn("url", given["before-fetch"])
        self.assertNotIn("tool", given["before-stop"])

    def test_a_hook_point_is_not_a_guard_and_a_guard_is_not_a_hook_point(self) -> None:
        """Two sets, not one widened. A name in both would be a point whose fatality depended on which
        file somebody read."""
        self.assertEqual(set(guards.NAMES) & set(hooks.NAMES), set())

    def test_every_guard_says_what_refusing_it_does(self) -> None:
        """A person is asked once whether an extension may refuse their tool calls. They cannot answer that
        without being told what a refusal costs."""
        for one in guards.GUARDS:
            with self.subTest(guard=one.name):
                self.assertTrue(one.refusing)
                self.assertTrue(one.when)
                self.assertTrue(one.given)

    def test_a_guard_declared_on_a_name_the_keel_has_not_got_is_refused(self) -> None:
        with self.assertRaises(KeyError):
            guards.declared({"guards": {"before-merge": "g.py"}})

    def test_the_short_and_the_long_form_read_the_same(self) -> None:
        short = guards.declared({"guards": {"before-search": "g/search.py"}})
        long = guards.declared({"guards": {"before-search": {"run": "g/search.py"}}})
        self.assertEqual(short, long)
        self.assertEqual(short["before-search"]["budget"], guards.DEFAULT_BUDGET)

    def test_a_guard_s_budget_is_shorter_than_a_hook_s(self) -> None:
        """A hook runs around a rung; a guard is in front of a tool call somebody is waiting on."""
        self.assertLess(float(guards.DEFAULT_BUDGET.rstrip("s")), float(hooks.DEFAULT_BUDGET.rstrip("s")))


class AgreementTest(unittest.TestCase):
    """Electing an extension runs its hooks. A guard is agreed to as well, because it refuses things a
    person asked for — so the registry is written from the agreement and never from the manifest."""

    MANIFESTS = {"cg": {"hooks": {"check": "h.py"}, "guards": {"before-search": "g.py"}}}

    def test_an_extension_nobody_agreed_to_fires_no_guard(self) -> None:
        self.assertEqual(guards.registry(self.MANIFESTS)["guards"], {})

    def test_an_extension_agreed_to_fires_its_guards(self) -> None:
        written = guards.registry(self.MANIFESTS, agreed={"cg"})
        self.assertEqual(written["guards"]["before-search"][0]["extension"], "cg")

    def test_electing_the_hook_does_not_agree_to_the_guard(self) -> None:
        """The two registries are written from two different answers, which is the whole of the design."""
        self.assertIn("check", hooks.registry(self.MANIFESTS)["points"])
        self.assertEqual(guards.registry(self.MANIFESTS)["guards"], {})


class RunnerTest(unittest.TestCase):
    """The runner as a project runs it: a script, in a directory laid out like one."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        place = self.root / "scripts/extensions"
        place.mkdir(parents=True)
        self.script = place / "guards.py"
        self.script.write_text(RUNNER.read_text(encoding="utf-8"), encoding="utf-8")
        (place / "cg").mkdir()

    def guard_script(self, body: str, name: str = "g.py") -> None:
        (self.root / "scripts/extensions/cg" / name).write_text(body, encoding="utf-8")

    def registry(self, **bodies: dict) -> None:
        (self.root / ".slipwai").mkdir(exist_ok=True)
        (self.root / ".slipwai/guards.json").write_text(
            json.dumps({"v": 1, "guards": {name: [{"extension": "cg", **body}]
                                           for name, body in bodies.items()}}), encoding="utf-8")

    def fire(self, name: str, *given: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), name, *given],
                              capture_output=True, text=True, cwd=self.root, timeout=60)

    def test_exit_two_refuses_the_call_and_the_reason_reaches_the_agent(self) -> None:
        self.guard_script("import sys\nprint('ask the index: codegraph explore \"place_order\"')\nsys.exit(2)\n")
        self.registry(**{"before-search": {"run": "g.py"}})
        done = self.fire("before-search", "--query", "place_order")
        self.assertEqual(done.returncode, 2)
        self.assertIn("ask the index", done.stderr)

    def test_everything_other_than_two_lets_the_call_through(self) -> None:
        """A guard that crashed has said nothing, and a tool call stopped by silence is a delegate blocked
        by a bug in something it was never told about."""
        for body in ("import sys\nsys.exit(1)\n", "raise SystemExit(3)\n", "import x_not_a_module\n"):
            with self.subTest(body=body.strip()):
                self.guard_script(body)
                self.registry(**{"before-search": {"run": "g.py"}})
                self.assertEqual(self.fire("before-search").returncode, 0)

    def test_a_guard_over_its_budget_is_ended_and_the_call_goes_ahead(self) -> None:
        self.guard_script("import time\ntime.sleep(30)\n")
        self.registry(**{"before-search": {"run": "g.py", "budget": "1s"}})
        done = self.fire("before-search")
        self.assertEqual(done.returncode, 0)
        self.assertIn("budget", done.stderr)

    def test_a_guard_whose_script_is_not_there_lets_the_call_through(self) -> None:
        self.registry(**{"before-search": {"run": "missing.py"}})
        done = self.fire("before-search")
        self.assertEqual(done.returncode, 0)
        self.assertIn("is not in this project", done.stderr)

    def test_what_the_rung_is_about_reaches_the_guard(self) -> None:
        self.guard_script("import os, sys\n"
                          "print(os.environ.get('SLIPWAI_QUERY', 'nothing'))\nsys.exit(2)\n")
        self.registry(**{"before-search": {"run": "g.py"}})
        done = self.fire("before-search", "--query", "place_order")
        self.assertIn("place_order", done.stderr)

    def test_a_guard_that_names_stages_is_not_fired_on_another(self) -> None:
        self.guard_script("import sys\nsys.exit(2)\n")
        self.registry(**{"before-search": {"run": "g.py", "stages": ["implement"]}})
        self.assertEqual(self.fire("before-search", "--stage", "demo").returncode, 0)
        self.assertEqual(self.fire("before-search", "--stage", "implement").returncode, 2)

    def test_with_no_registry_nothing_is_refused(self) -> None:
        self.assertEqual(self.fire("before-search").returncode, 0)

    def test_offering_with_no_terminal_agrees_to_nothing(self) -> None:
        """Silence is no. A question about whether software may refuse what a person told it to do has one
        safe answer when nobody is there to answer it."""
        (self.root / "scripts/extensions/available-guards.json").write_text(
            json.dumps({"cg": {"before-search": {"run": "g.py"}}}), encoding="utf-8")
        done = subprocess.run([sys.executable, str(self.script), "--offer", "cg"],
                              capture_output=True, text=True, cwd=self.root, stdin=subprocess.DEVNULL,
                              timeout=60)
        self.assertEqual(done.returncode, 0)
        written = json.loads((self.root / ".slipwai/guards.json").read_text(encoding="utf-8"))
        self.assertEqual(written["guards"], {})


class AskedOncePerQuickstartTest(unittest.TestCase):
    """13.4: a person who said yes when they wrote the quickstart has said yes.

    The guard question is the one question in `./init` that is about *refusing what somebody asked for*,
    and asking it again in every project generated from one quickstart is how a person learns to answer it
    without reading it. So the agreement travels with the quickstart — and only as far as it goes: an
    extension that has *gained* a guard since is asked about again, naming the new one and nothing else.
    """

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        place = self.root / "scripts/extensions"
        place.mkdir(parents=True)
        self.script = place / "guards.py"
        self.script.write_text(RUNNER.read_text(encoding="utf-8"), encoding="utf-8")

    def available(self, declared: dict) -> None:
        (self.root / "scripts/extensions/available-guards.json").write_text(
            json.dumps(declared), encoding="utf-8")

    def record(self, agreed: dict) -> None:
        (self.root / ".slipwai").mkdir(exist_ok=True)
        (self.root / ".slipwai/quickstart.json").write_text(
            json.dumps({"v": 1, "name": "ours", "extensions": sorted(agreed), "guards": agreed}),
            encoding="utf-8")

    def offer(self, *keys: str) -> subprocess.CompletedProcess:
        """`--offer` with nobody at a terminal, which is how a question that is asked would be refused."""
        return subprocess.run([sys.executable, str(self.script), "--offer", *keys],
                              capture_output=True, text=True, cwd=self.root,
                              stdin=subprocess.DEVNULL, timeout=60)

    def written(self) -> dict:
        return json.loads((self.root / ".slipwai/guards.json").read_text(encoding="utf-8"))["guards"]

    def test_a_guard_agreed_when_the_quickstart_was_written_fires_without_being_asked_about(self) -> None:
        self.available({"cg": {"before-search": {"run": "g.py"}}})
        self.record({"cg": ["before-search"]})
        done = self.offer("cg")
        self.assertEqual(done.returncode, 0)
        self.assertEqual(self.written()["before-search"][0]["extension"], "cg")
        self.assertIn("quickstart", done.stdout)

    def test_a_guard_the_extension_gained_since_is_the_only_one_asked_about(self) -> None:
        """And with nobody there to answer, silence is still no — for the new one alone. The agreement
        already given is not withdrawn by a question nobody was present for."""
        self.available({"cg": {"before-search": {"run": "g.py"}, "before-write": {"run": "w.py"}}})
        self.record({"cg": ["before-search"]})
        self.offer("cg")
        self.assertIn("before-search", self.written())
        self.assertNotIn("before-write", self.written())

    def test_an_extension_the_quickstart_did_not_agree_to_is_asked_about_as_it_always_was(self) -> None:
        self.available({"cg": {"before-search": {"run": "g.py"}}})
        self.record({"other": ["before-search"]})
        self.offer("cg")
        self.assertEqual(self.written(), {})


class CarriedTest(unittest.TestCase):
    """The runner's own copy of what each guard can stop, held to the keel's."""

    runner: Any

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location("guards_runner", RUNNER)
        assert spec is not None and spec.loader is not None
        self.runner = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(self.runner)

    def test_the_runner_knows_every_guard_the_keel_has(self) -> None:
        """A project has no slipwai to import, so the words a person is asked with are a second copy. A
        guard missing from it is one offered as its own bare name, which answers nothing."""
        self.assertEqual(set(self.runner.REFUSING), set(guards.NAMES))

    def test_both_sides_refuse_on_the_same_exit_code(self) -> None:
        self.assertEqual(self.runner.REFUSE, guards.REFUSE)

    def test_only_what_nobody_has_agreed_to_is_what_a_person_is_asked(self) -> None:
        """The arithmetic 13.4 rests on, where a terminal is not needed to read it: what is asked is the
        declared guards minus the agreed ones, per extension, and an extension with nothing new drops out
        of the question entirely rather than appearing with an empty list."""
        offered: dict[str, dict] = {"cg": {"before-search": {}, "before-write": {}},
                                    "ux": {"before-stop": {}}}
        asked = self.runner.newly(offered, {"cg": ["before-search"], "ux": ["before-stop"]})
        self.assertEqual(asked, {"cg": {"before-write": {}}})

    def test_both_sides_default_to_the_same_budget(self) -> None:
        self.assertEqual(self.runner.DEFAULT_BUDGET, guards.DEFAULT_BUDGET)


if __name__ == "__main__":
    unittest.main()
