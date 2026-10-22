"""`scripts/agents/session.py`: the harness's own moments, and the two closed sets fired from one place.

The bug this file is written over is older than the script. Version 1 reached three harness moments by
having the keel write `scripts/agents/cruise.py <verb>` straight into `.claude/settings.json`, so the
control-file refusal and the compaction protocol were behaviours of *one harness*: on Claude Code they
worked, and on the other thirty-five they were absent with nothing saying so. Both closed sets exist to end
that, and `session.py` is where they are fired from.

So the tests that matter most here are the two that hold the wiring rather than the behaviour: every verb
the script answers is a point of one of the two sets, and every verb the keel writes into a harness's
settings is a verb the script answers. A row naming a verb that is not there fails exactly the way the old
shape failed — silently, for ever.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import guards, hooks
from slipwai.assets import TOOLKIT_ROOT
from slipwai.layout import AT_ROOT
from slipwai.project.agent_settings import harness_hooks

AGENTS = TOOLKIT_ROOT / "scripts/agents"
SCRIPT = AGENTS / "session.py"


#: The activity log's verbs, which are plumbing too: the board's Now strip reads what they write, they refuse
#: nothing, and an extension has nothing to attach to a sentence the session says about itself.
ACTIVITY_VERBS = {"before-delegate", "agent-started", "agent-stopped", "after-failure", "say", "waiting"}


class VerbTest(unittest.TestCase):
    """Every verb is a point of a set, and every row the keel writes names a verb."""

    def verbs(self) -> set[str]:
        source = SCRIPT.read_text(encoding="utf-8")
        block = source.split("VERBS = {", 1)[1].split("}", 1)[0]
        return {line.split('"')[1] for line in block.splitlines() if '"' in line}

    def test_every_verb_is_a_point_of_one_of_the_two_sets(self) -> None:
        """`responded` is the one that is neither, and it is plumbing: a harness whose stop event carries no
        text needs its last message kept a moment earlier. An extension has nothing to attach there, and a
        point nothing could use would be a promise with no caller."""
        self.assertEqual(self.verbs() - set(guards.NAMES) - set(hooks.NAMES), {"responded"} | ACTIVITY_VERBS)

    def test_every_guard_is_answered(self) -> None:
        """All seven, with no exception — including `after-delegate`, which fires on a harness's post-tool
        event rather than its pre-tool one. A guard the script does not answer is a guard an extension can
        declare, be elected for, and never once be run at: installed, valid, and silent for ever."""
        self.assertEqual(set(guards.NAMES) - self.verbs(), set())

    def test_the_compaction_pair_are_answered_and_the_rung_points_are_not(self) -> None:
        """A rung point is the captain's to fire, because a rung is the captain's. Only the moments a
        *harness* owns arrive here."""
        self.assertEqual(set(hooks.NAMES) & self.verbs(), {"before-compact", "after-compact"})

    def test_every_command_the_keel_writes_into_a_harness_names_a_verb_this_script_has(self) -> None:
        """The whole class of failure this script exists to end: a settings row naming a verb that is not
        there does nothing, says nothing, and goes on not doing it for ever."""
        verbs = self.verbs()
        for event, rows in harness_hooks(AT_ROOT).items():
            for row in rows:
                hooked = row["hooks"]
                assert isinstance(hooked, list)
                for hook in hooked:
                    command = str(hook["command"])
                    if "session.py" not in command:
                        continue
                    with self.subTest(event=event, command=command):
                        self.assertIn(command.rsplit(" ", 1)[-1], verbs)

    def test_the_other_harnesses_rows_name_one_too(self) -> None:
        """`registry.json`'s `hooks.projection` is the same wiring in each harness's own format, and it
        drifted from the settings file once already — which is how `stopping` outlived the verb."""
        registry = json.loads((AGENTS / "registry.json").read_text(encoding="utf-8"))
        verbs, found = self.verbs(), 0
        for row in registry["harnesses"]:
            projection = (row.get("hooks") or {}).get("projection")
            if not isinstance(projection, dict):
                continue
            for verb in projection["events"]:
                found += 1
                with self.subTest(harness=row.get("key"), verb=verb):
                    self.assertIn(verb, verbs)
        self.assertGreater(found, 0, "no harness projects a hook file; the check proved nothing")


class FiredTest(unittest.TestCase):
    """Every point of both closed sets has something that fires it.

    This is the rule the sets are written against, turned into a gate. A point nobody fires is the worst
    kind of broken thing here: an extension declares it, passes conformance, is elected, and then never runs
    — installed, valid, and silent for ever. The keel refuses a point an extension *invents* for exactly
    that reason, and a point the keel declares and never calls is the same failure with the keel's name on
    it.

    It cost two of them to find out. `after-merge` was added with 7.7b and was fired by nothing until the
    harbourmaster called it; `after-delegate` was declared in 6.1d and had no caller at all until
    `session.py` answered it on the post-tool event.
    """

    def callers(self) -> str:
        """Everything that could fire one, read as text. The calls are one-line `fire(...)`, verb tables,
        Makefile targets and the shell `./init` is written from, so what is held is that the name reaches
        something that runs.

        `./init` is in here because the `init` point is fired from it and from nowhere else — it is the
        election, and there is no rung and no `make` target around it.
        """
        scripts = sorted(AGENTS.glob("*.py")) + sorted((AGENTS.parent / "extensions").glob("*.py"))
        from slipwai.project.agent_targets import agent_targets  # noqa: PLC0415
        from slipwai.project.init_extensions import RUN_EXTENSIONS  # noqa: PLC0415
        return "\n".join(path.read_text(encoding="utf-8") for path in scripts) + agent_targets() + RUN_EXTENSIONS

    def test_every_hook_point_is_fired_by_something(self) -> None:
        text = self.callers()
        for name in sorted(hooks.NAMES):
            with self.subTest(point=name):
                self.assertIn(name, text,
                              f"`{name}` is a point the keel promises and nothing in the toolkit fires")

    def test_every_guard_is_fired_by_something(self) -> None:
        text = self.callers()
        for name in guards.NAMES:
            with self.subTest(guard=name):
                self.assertIn(f'"{name}"', text,
                              f"`{name}` is a guard the keel promises and nothing in the toolkit fires")

    def test_nothing_is_run_by_convention_any_more(self) -> None:
        """6.1e's own line. `init` and `project` used to be run by name — a file called `init.py`, a
        function called `project_guidance()` — so an extension that declared another script at either was
        ignored. They are default declarations now, which means the registry is the only firing path and
        there is no exemption list for a later point to join quietly."""
        self.assertEqual(set(hooks.DEFAULTS), {"init", "project"})
        self.assertTrue(set(hooks.DEFAULTS).issubset(hooks.NAMES))
        fired = (AGENTS.parent / "extensions/project.py").read_text(encoding="utf-8")
        self.assertIn('"project"', fired, "the project point is not fired through hooks.py")
        self.assertNotIn("module.project_guidance", fired, "the projection still calls a function by name")


class RunTest(unittest.TestCase):
    """The script in a project, run the way a harness runs it: an event on stdin, a code back."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        for name in ("session.py", "logs.py"):
            (place / name).write_text((AGENTS / name).read_text(encoding="utf-8"), encoding="utf-8")
        (self.root / "Makefile").write_text("verify:\n\t@true\n", encoding="utf-8")
        self.script = place / "session.py"

    def fire(self, verb: str, event: dict, **named: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), verb], input=json.dumps(event),
                              capture_output=True, text=True, cwd=self.root, timeout=60,
                              env={**os.environ, **named})

    def line(self, fairway: str, kind: str = "heartbeat", **fields: str) -> None:
        """One deck-log line, written by the toolkit's own `logs.py` rather than by a hand-rolled dict:
        a fixture that spelled a line its own way would pass while the real writer's output did not."""
        spec = importlib.util.spec_from_file_location("deck_logs", AGENTS / "logs.py")
        assert spec is not None and spec.loader is not None
        written = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        # In `sys.modules` before it runs: `logs.py` declares dataclasses, and a dataclass resolves its own
        # module while the decorator runs, which fails with a bare `AttributeError` if nothing registered it.
        sys.modules[spec.name] = written
        spec.loader.exec_module(written)
        where = self.root / f".slipwai/logs/feature/{fairway}.jsonl"
        where.parent.mkdir(parents=True, exist_ok=True)
        with where.open("a", encoding="utf-8") as handle:
            handle.write(written.entry(kind, fairway=fairway, **fields).line())

    def test_a_dispatched_session_may_not_edit_a_gate(self) -> None:
        done = self.fire("before-write", {"tool_input": {"file_path": "Makefile"}, "cwd": str(self.root)},
                         SLIPWAI_FAIRWAY="ORD")
        self.assertEqual(done.returncode, 2)
        self.assertIn("gate or a control", done.stderr)

    def test_a_persons_own_session_may(self) -> None:
        """A tool that refused a person their own Makefile is a tool they turn off. The captain's rule is
        the captain's, and `SLIPWAI_FAIRWAY` is what says a captain is there."""
        done = self.fire("before-write", {"tool_input": {"file_path": "Makefile"}, "cwd": str(self.root)})
        self.assertEqual(done.returncode, 0)

    def test_an_ordinary_file_is_written(self) -> None:
        done = self.fire("before-write", {"tool_input": {"file_path": "apps/x.py"}, "cwd": str(self.root)},
                         SLIPWAI_FAIRWAY="ORD")
        self.assertEqual(done.returncode, 0)

    def test_the_shell_is_judged_by_the_same_list(self) -> None:
        """The door `before-write` cannot see through: `make verify` rewritten by a `sed` is rewritten all
        the same. Crude on purpose — the captain's controlled-files diff is the real control, and a clever
        parse of shell would buy false refusals rather than safety."""
        wrote = self.fire("before-command", {"tool_input": {"command": "sed -i s/a/b/ scripts/check.py"}},
                          SLIPWAI_FAIRWAY="ORD")
        self.assertEqual(wrote.returncode, 2)
        read = self.fire("before-command", {"tool_input": {"command": "cat scripts/check.py"}},
                         SLIPWAI_FAIRWAY="ORD")
        self.assertEqual(read.returncode, 0)

    def test_a_turn_that_wrote_no_line_is_held(self) -> None:
        """*A stage that wrote no line made no progress* is the loop's whole rule, and this is the cheap
        half of enforcing it. The first attempt proved prose is not a control by ending iterations on a
        report that said "continuing now"."""
        done = self.fire("before-stop", {"last_assistant_message": "Continuing now."},
                         SLIPWAI_FAIRWAY="ORD", SLIPWAI_STAGE="implement")
        self.assertEqual(json.loads(done.stdout)["decision"], "block")

    def test_a_turn_that_wrote_one_is_not(self) -> None:
        self.line("ORD")
        done = self.fire("before-stop", {"last_assistant_message": "Continuing now."},
                         SLIPWAI_FAIRWAY="ORD", SLIPWAI_STAGE="implement",
                         SLIPWAI_SINCE="2000-01-01T00:00:00Z")
        self.assertEqual(done.stdout.strip(), "")

    def test_a_line_older_than_the_session_does_not_count(self) -> None:
        """"No line" has to mean none *since this session opened*: a fairway with a hundred lines behind it
        would otherwise satisfy the test for ever, which is the hold never firing again."""
        self.line("ORD")
        done = self.fire("before-stop", {"last_assistant_message": "Continuing now."},
                         SLIPWAI_FAIRWAY="ORD", SLIPWAI_STAGE="implement",
                         SLIPWAI_SINCE="2099-01-01T00:00:00Z")
        self.assertEqual(json.loads(done.stdout)["decision"], "block")

    def test_it_lets_go_after_three_holds(self) -> None:
        """A turn held for ever is the same silence the hold was there to break — and below every harness's
        own cap, so it is this script that decides when to let go and says so."""
        for _ in range(3):
            self.fire("before-stop", {"last_assistant_message": "x"}, SLIPWAI_FAIRWAY="ORD")
        done = self.fire("before-stop", {"last_assistant_message": "x"}, SLIPWAI_FAIRWAY="ORD")
        self.assertEqual(done.stdout.strip(), "")
        self.assertIn("letting the turn end", done.stderr)

    def test_a_cursors_stop_is_spelled_its_own_way(self) -> None:
        done = self.fire("before-stop", {"text": "x", "loop_count": 0}, SLIPWAI_FAIRWAY="ORD")
        self.assertIn("followup_message", json.loads(done.stdout))

    def test_a_stop_event_carrying_no_message_holds_nothing(self) -> None:
        """A hold on no evidence is a hold on every turn."""
        done = self.fire("before-stop", {}, SLIPWAI_FAIRWAY="ORD")
        self.assertEqual(done.stdout.strip(), "")

    def test_a_persons_turn_is_never_held(self) -> None:
        done = self.fire("before-stop", {"last_assistant_message": "Done."})
        self.assertEqual(done.stdout.strip(), "")

    def returned(self, kind: str, text: str) -> subprocess.CompletedProcess:
        return self.fire("after-delegate", {"tool_name": "Agent", "tool_input": {"subagent_type": kind, "prompt": "T3"},
                                            "tool_response": text})

    def test_a_shipwright_that_names_no_commit_is_sent_back_for_the_hash(self) -> None:
        """What the session integrates is a commit, never files copied out of a working tree — which is how
        a host once took a sibling's files while its next rule was still RED."""
        done = self.returned("sail-implement-shipwright", "Done: R3 green, two tests added, make unit passed.")
        self.assertEqual(done.returncode, 2)
        self.assertIn("without naming a commit", done.stderr)

    def test_a_return_naming_its_commit_goes_through(self) -> None:
        done = self.returned("sail-implement-shipwright", "commit 1a2b3c4d — R3 green; boundary: rule; cycle: rule")
        self.assertEqual(done.returncode, 0)

    def test_the_honest_empty_return_is_not_refused(self) -> None:
        done = self.returned("sail-implement-shipwright",
                             "No commit: every example was already green, nothing written.")
        self.assertEqual(done.returncode, 0)

    def test_a_type_that_does_not_commit_is_not_asked_for_a_hash(self) -> None:
        done = self.returned("sail-review-mate", "Three findings, ranked. No edits.")
        self.assertEqual(done.returncode, 0)

    def test_a_structured_response_is_read_the_same_way(self) -> None:
        done = self.fire("after-delegate", {
            "tool_name": "Task", "tool_input": {"subagent_type": "sail-implement-shipwright"},
            "tool_response": [{"type": "text", "text": "Committed as commit 9f8e7d6c5b."}]})
        self.assertEqual(done.returncode, 0)

    def test_a_resumed_context_is_given_the_log_and_not_a_retelling(self) -> None:
        self.line("ORD", "claimed", slice="1.1")
        done = self.fire("after-compact", {}, SLIPWAI_FAIRWAY="ORD", SLIPWAI_SLICE="1.1")
        self.assertIn("context was compacted", done.stdout)
        self.assertIn('"kind": "claimed"', done.stdout)

    def test_a_verb_that_throws_never_stops_a_stage(self) -> None:
        """The captain depends on none of this: delete the file and the loop still runs. So every failure
        here is said and shrugged off — a stage stopped by a broken hook is the control plane both closed
        sets are written to prevent."""
        (self.root / ".slipwai").mkdir(exist_ok=True)
        (self.root / ".slipwai/holds.json").write_text("{", encoding="utf-8")
        done = self.fire("before-stop", {"last_assistant_message": "x"}, SLIPWAI_FAIRWAY="ORD")
        self.assertEqual(done.returncode, 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
