"""The model, triage and launch over the Agent Client Protocol from the board, over the stand-in agent.

What is proved: the model's prompt is the project's own script's, less the sentence written for a session
with nobody to ask; a stage that ended without what it was for is a failed step that says what is missing;
triage is given the numbers nobody has routed; a launch is the chart and the split over the protocol and
then the two processes that cast off; and each falls back to the script it always was where the board has
no agent to launch.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import board_settings, stage_session
from slipwai.adoption_run import agent_steps
from slipwai.board_settings import Launch
from slipwai.feedback import capture
from slipwai.init_run import CRUISE, LAUNCH, MODEL, TRIAGE, Fitting, Step, outside_session
from slipwai.layout import Layout
from slipwai.next_steps import Step as Next
from slipwai.passage import split
from slipwai.stage_session import StageSession
from slipwai.stage_steps import NOBODY, begin_model, launch, launch_steps, model_prompt, model_step, triage_step

ROOT = Path(__file__).resolve().parent.parent
AGENT = Path(__file__).resolve().parent / "fixtures" / "acp_agent.py"
STAND_IN = Launch("stand-in", "Stand-in", (sys.executable, str(AGENT)), "a script")
SCRIPT = ("import sys\nif sys.argv[1:] == ['--prompt']:\n    print('Model it.')\n"
          f"    print({NOBODY!r})\n")


def finished(fitting: Fitting, seconds: float = 20) -> dict:
    for _ in range(int(seconds / 0.05)):
        said = fitting.said()
        if said["done"]:
            return said
        time.sleep(0.05)
    raise AssertionError("the stage never ended")


class StageStepsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "scripts" / "agents").mkdir(parents=True)
        (self.root / "scripts" / "agents" / "model.py").write_text(SCRIPT, encoding="utf-8")
        for patched in (mock.patch.object(board_settings, "SETTINGS", self.root / "board.json"),
                        mock.patch.object(stage_session, "launchable", return_value=STAND_IN)):
            patched.start()
            self.addCleanup(patched.stop)

    def test_the_model_s_prompt_is_the_project_s_script_s_less_the_sentence_for_nobody(self) -> None:
        self.assertEqual(model_prompt(self.root), "Model it.")
        (self.root / "scripts" / "agents" / "model.py").write_text("import sys\nsys.exit(2)\n", encoding="utf-8")
        self.assertEqual(model_prompt(self.root), "", "a script without the flag leaves the stage to the child")
        self.assertEqual((model_step(self.root).argv, model_step(self.root).session), (MODEL, None))

    def test_the_model_runs_over_the_protocol_and_is_short_without_a_slice(self) -> None:
        said = finished(begin_model(self.root, ["approved"]))
        self.assertEqual(said["code"], 1)
        self.assertEqual(said["lines"][0], "approved")
        self.assertTrue(any(line.startswith("Drawn: Model it.\n") for line in said["lines"]), "the rule rides under")
        self.assertEqual(said["lines"][-1], "The model stopped short; its lines above say where. Model again tries "
                                            "once more.")
        self.assertTrue(any(line.startswith("! The session ended without a slice") for line in said["lines"]))
        self.assertFalse((self.root / ".slipwai" / "model-next.pid").exists(), "the marker is taken away after")
        (self.root / "docs" / "event-model").mkdir(parents=True)
        (self.root / "docs" / "event-model" / "model.yaml").write_text("slices:\n  - a\n", encoding="utf-8")
        said = finished(begin_model(self.root))
        self.assertEqual(said["code"], 0)
        self.assertIn("The model is under docs/event-model/", said["lines"][-1])

    def test_a_running_stage_is_seen_from_another_window_by_its_marker(self) -> None:
        stage = StageSession(self.root, "model", launch=STAND_IN, prompt="slow", pid="model-next.pid")
        fitting = Fitting(self.root, [Step([], "Modelling.", lambda code: f"ended {code}", "model", session=stage.run)])
        fitting.thread.start()
        for _ in range(400):
            if any(t["kind"] == "permission" for t in stage.said()["turns"]):
                break
            time.sleep(0.05)
        seen = outside_session(self.root)
        assert seen is not None
        self.assertEqual(seen["step"], "model")
        stage.cancel()
        self.assertEqual(finished(fitting)["code"], 1)
        self.assertIsNone(outside_session(self.root))

    def test_triage_is_given_the_numbers_nobody_has_routed_and_is_short_until_each_is_proposed(self) -> None:
        self.assertEqual((triage_step(self.root).argv, triage_step(self.root).session), (TRIAGE, None))
        capture(self.root, "the button is wrong")
        capture(self.root, "and the colour")
        step = triage_step(self.root)
        self.assertEqual(step.argv, [])
        fitting = Fitting(self.root, [step])
        fitting.thread.start()
        said = finished(fitting)
        self.assertEqual(said["code"], 1)
        self.assertTrue(any("with `0001,0002` as its argument" in line for line in said["lines"]), said["lines"])
        self.assertIn("! The session ended with 0001, 0002 not proposed; Triage on the Feedback card tries again.",
                      said["lines"])

    def test_a_launch_is_the_chart_and_split_over_the_protocol_then_the_two_processes_that_cast_off(self) -> None:
        steps = launch_steps(self.root)
        self.assertEqual([one.argv for one in steps],
                         [[], ["python3", "scripts/agents/cruise.py", "--set", "enabled=true"], CRUISE])
        self.assertIsNotNone(steps[0].session)
        (self.root / "specs" / "001-x").mkdir(parents=True)
        (self.root / "specs" / "001-x" / "chart.yaml").write_text("slices: []\n", encoding="utf-8")
        self.assertFalse(split(self.root))
        (self.root / "specs" / "001-x" / "chart.yaml").write_text("slices:\n  - id: a\n", encoding="utf-8")
        self.assertTrue(split(self.root))
        self.assertEqual(len(launch_steps(self.root)), 2, "charted and split already: enable and cast off")
        (self.root / "scripts" / "agents" / "cruise.py").write_text("print('enabled')\n", encoding="utf-8")
        (self.root / "Makefile").write_text("cruise:\n\t@echo 'cast'\n", encoding="utf-8")
        said = finished(launch(self.root, ["drafted"]))
        self.assertEqual(said["code"], 0, said["lines"])
        self.assertIn("cast", said["lines"])
        self.assertTrue(said["lines"][-1].startswith("The build is continued: the fleet is cast off."))
        with mock.patch.object(stage_session, "launchable", return_value=None):
            self.assertEqual([one.argv for one in launch_steps(self.root)], [LAUNCH])

    def test_a_launch_whose_session_left_no_split_casts_nothing_off(self) -> None:
        said = finished(launch(self.root))
        self.assertEqual(said["code"], 1)
        self.assertTrue(any(line.startswith("! The session ended without a split") for line in said["lines"]))
        self.assertNotIn("Enabling /cruise.", said["lines"])

    def test_an_adoption_step_is_the_step_script_s_prompt_over_the_protocol(self) -> None:
        layout = Layout("adopt")
        script = self.root / layout.under("scripts/agents/step.py")
        script.parent.mkdir(parents=True)
        script.write_text("import sys\nif sys.argv[1] == '--prompt':\n    print('Take ' + sys.argv[2] + ' because ' + "
                          "sys.argv[3])\n", encoding="utf-8")
        now = Next("the build floor, in the agent", "it runs", False)
        steps = agent_steps(layout, now, self.root)
        self.assertEqual(steps[0].argv, [])
        self.assertIn("over the Agent Client Protocol", steps[0].announced)
        fitting = Fitting(self.root, steps)
        fitting.thread.start()
        said = finished(fitting)
        self.assertEqual(said["code"], 0, said["lines"])
        self.assertTrue(any(line.startswith("Drawn: Take the build floor because it runs\n") for line in said["lines"]))
        with mock.patch.object(stage_session, "launchable", return_value=None):
            self.assertEqual(agent_steps(layout, now, self.root)[0].argv,
                             [sys.executable, "adopt/scripts/agents/step.py", "the build floor", "it runs"])

    def test_the_adoption_step_script_says_its_prompt_when_asked(self) -> None:
        agents = self.root / "scripts" / "agents"
        for name in ("harness.py", "registry.json"):
            shutil.copy(ROOT / "assets/toolkit/scripts/agents" / name, agents / name)
        shutil.copy(ROOT / "assets/adoption/scripts/agents/step.py", agents / "step.py")
        said = subprocess.run([sys.executable, str(agents / "step.py"), "--prompt", "the build floor", "it runs"],
                              cwd=self.root, capture_output=True, text=True, check=False)
        self.assertEqual(said.returncode, 0, said.stderr)
        self.assertTrue(said.stdout.startswith("Take one step of this repository's adoption, and only that step: "
                                               "the build floor — it runs."), said.stdout)

    def test_the_toolkit_s_model_script_says_its_prompt_when_asked(self) -> None:
        said = subprocess.run([sys.executable, str(ROOT / "assets/toolkit/scripts/agents/model.py"), "--prompt"],
                              capture_output=True, text=True, check=False)
        self.assertEqual(said.returncode, 0, said.stderr)
        self.assertTrue(said.stdout.startswith("The storyboard is approved."))
        self.assertIn(NOBODY, said.stdout)


if __name__ == "__main__":
    unittest.main()
