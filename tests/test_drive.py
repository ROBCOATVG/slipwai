"""A captain's drive over the Agent Client Protocol, where `SLIPWAI_ACP` says so, over the stand-in agent.

What is proved: a drive has a process's face and the captain's watch gets a slice through on it, believing
the deck log as it always did; a write outside the berth is refused and a question declined, with a line
saying so, because nobody is in the berth; an agent that dies is a failed drive with no refusal in it; the
model `cruise.json` names is set where the agent offers it; and with the variable unset nothing is taken.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401
from captain_fixture import Fixture

from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"
AGENT = Path(__file__).resolve().parent / "fixtures" / "acp_agent.py"
STAND_IN = f"{sys.executable} {AGENT}"


def loaded(root: Path) -> Any:
    """`drive.py` as it runs inside a project, with the harness beside it pointed at that project."""
    spec = importlib.util.spec_from_file_location(f"drive_{root.name}", AGENTS / "drive.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    module.harness.ROOT = root
    module.harness.INTEGRATION = root / ".specify/integration.json"
    return module


def run(**held: Any) -> Any:
    return subprocess.run(**held, check=False)


class DriveTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.drive = loaded(self.root)
        self.was = os.environ.pop("SLIPWAI_ACP", None)
        self.addCleanup(self.restore)

    def restore(self) -> None:
        """The variable as it was, and never left set: a captain test after this one would take the protocol."""
        os.environ.pop("SLIPWAI_ACP", None)
        if self.was is not None:
            os.environ["SLIPWAI_ACP"] = self.was

    def started(self, prompt: str, model: str | None = None) -> Any:
        return self.drive.Drive([sys.executable, str(AGENT)], self.root, dict(os.environ), prompt, model=model,
                                kept=self.root / ".slipwai" / "acp" / "x")

    def test_with_the_variable_unset_nothing_is_taken_and_a_named_command_is_the_launch(self) -> None:
        self.assertIsNone(self.drive.protocol())
        os.environ["SLIPWAI_ACP"] = STAND_IN
        argv, row, said = self.drive.protocol()
        self.assertEqual((argv, row), ([sys.executable, str(AGENT)], None))
        self.assertIn("over the Agent Client Protocol", said)
        os.environ["SLIPWAI_ACP"] = "1"
        with self.assertRaises(self.drive.harness.NoHarness) as refused:  # nothing initialised here
            self.drive.protocol()
        self.assertIn("no initialised harness has a launch row", str(refused.exception))

    def test_a_launch_row_is_what_this_machine_can_make(self) -> None:
        self.assertEqual(self.drive.acp_launch({"acp": {"binary": {"cmd": "no-such-agent-here", "args": ["acp"]}}}), [])
        self.assertEqual(self.drive.acp_launch({"acp": None}), [])
        found = self.drive.acp_launch({"acp": {"binary": {"cmd": "python3", "args": ["acp"]}}})
        self.assertEqual(found[1:], ["acp"])
        self.assertEqual(self.drive.acp_environment({"acp": {"npx": {"package": "p", "env": {"A": 1}}}}), {"A": "1"})

    def test_a_drive_has_a_process_s_face_and_ends_as_the_agent_said(self) -> None:
        drive = self.started("outside ask")
        self.assertIsNone(drive.poll())
        self.assertEqual(drive.wait(20), 0)
        self.assertEqual(drive.returncode, 0)
        self.assertIsNone(drive.refusal)
        self.assertTrue((self.root / "prototype" / "index.html").is_file(), "a write inside the berth was allowed")
        self.assertFalse(Path("/etc/hosts.written").exists())
        drive.end()  # harmless once ended

    def test_a_drive_whose_agent_died_is_a_failed_run_and_no_refusal(self) -> None:
        drive = self.started("die")
        self.assertEqual(drive.wait(20), 1)
        self.assertIsNone(drive.refusal)

    def test_the_model_is_set_where_the_agent_offers_it(self) -> None:
        drive = self.started("hello", model="b")
        drive.wait(20)
        self.assertEqual(drive.session.agent.config_options[0]["currentValue"], "b")
        drive = self.started("hello", model="zz")
        drive.wait(20)
        self.assertEqual(drive.session.agent.config_options[0]["currentValue"], "a", "the agent's own default")


class CaptainTest(Fixture):
    def over(self, fairway: str) -> subprocess.CompletedProcess:
        env = {key: value for key, value in os.environ.items() if key != "SLIPWAI_SAIL"}
        return subprocess.run([sys.executable, str(self.script), fairway, "--once"], capture_output=True, text=True,
                              cwd=self.root, timeout=90, env={**env, "SLIPWAI_ACP": STAND_IN})

    def test_the_captain_gets_a_slice_through_on_a_drive_over_the_protocol(self) -> None:
        self.grant("ORD-01")
        done = self.over("ORD")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("SLIPWAI_ACP", done.stdout)
        self.assertIn("Drawn: Run the /drive command", done.stdout)
        self.assertIn("the agent ended its turn: end_turn", done.stdout)
        kinds = [e.kind for e in self.read("ORD")]
        self.assertIn("claimed", kinds)
        self.assertIn("mark-set", kinds)
        self.assertIn("request", kinds, "the merge is asked of the harbourmaster, as it always was")
        self.assertNotIn("parked", kinds, done.stdout)


if __name__ == "__main__":
    unittest.main()
