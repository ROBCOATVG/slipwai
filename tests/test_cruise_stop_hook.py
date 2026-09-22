"""`/cruise`'s Stop hook: the end of a turn checked where the harness lets a hook refuse it.

`commands/cruise.md` said "do not wait to be invoked again" and was not enough twice in one session — once
ending after the upstream stages, once on a report that said "continuing now" — so the contract is enforced by
`scripts/agents/cruise.py stopping`, run from `.claude/settings.json` on Claude Code's `Stop` event, and the
runner marks the sessions it starts so a typed `/cruise` can be told from a driven one. Both are run here for
real, against a fake transcript and a checkpoint.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_cruise_runner import enable

from slipwai.project.cruise import STOP_FILE, UNREAD
from slipwai.project.cruise_record import CHECKPOINT


class CruiseStopHookTest(FactoryTestCase):
    def test_the_stop_hook_holds_a_turn_that_is_not_an_end_and_a_typed_session_never_ends_on_continue(self) -> None:
        """Prose in a command file is not a control: one session ended an iteration after the upstream stages,
        and later on a report that said "continuing now". Claude Code's Stop hook can refuse the end of a turn,
        so `stopping` does — while a checkpoint is in flight and no stop file exists — unless the last assistant
        message ends on one of the four lines, and, with no runner reading it, unless that line is not
        `continue`. It stamps every hold, lets go after HOLD_LIMIT holds nothing rewrote, takes the checkpoint
        with a `done`, and says nothing at all outside an iteration."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "stopping", "standard", "python")
            settings = json.loads((repo / ".claude/settings.json").read_text())
            self.assertEqual(settings["hooks"]["Stop"],
                             [{"hooks": [{"type": "command", "command": "python3 scripts/agents/cruise.py stopping"}]}])
            enable(repo)
            checkpoint = repo / CHECKPOINT
            transcript = Path(directory) / "transcript.jsonl"
            unset = {k: v for k, v in os.environ.items() if k not in ("CRUISE_RUNNER", "CRUISE_ITERATION")}

            def said(*texts: str) -> None:
                lines = [json.dumps({"type": "user", "message": {"role": "user", "content": "/cruise"}})]
                for text in texts:
                    lines.append(json.dumps({"type": "assistant", "message": {
                        "role": "assistant", "content": [{"type": "text", "text": text}]}}))
                    lines.append(json.dumps({"type": "assistant", "message": {
                        "role": "assistant", "content": [{"type": "tool_use", "name": "Bash", "input": {}}]}}))
                transcript.write_text("\n".join(lines) + "\n")

            def stop(**env: str) -> subprocess.CompletedProcess:
                return subprocess.run(["python3", "scripts/agents/cruise.py", "stopping"], cwd=repo, text=True,
                                      capture_output=True, env={**unset, **env},
                                      input=json.dumps({"hook_event_name": "Stop", "stop_hook_active": False,
                                                        "transcript_path": str(transcript)}))

            # What `loop` says on each side.
            typed = subprocess.run(["python3", "scripts/agents/cruise.py", "loop"], cwd=repo, text=True,
                                   capture_output=True, env=unset)
            self.assertEqual(typed.stdout.strip(), f"cruise: {UNREAD}")
            driven = subprocess.run(["python3", "scripts/agents/cruise.py", "loop"], cwd=repo, text=True,
                                    capture_output=True, env={**unset, "CRUISE_RUNNER": "1", "CRUISE_ITERATION": "4"})
            self.assertIn("started this session as iteration 4 and reads its last line", driven.stdout)
            # No iteration in flight: the hook is silent whatever the transcript says.
            said("Stage done. Continuing into S1's plan and tasks now.")
            quiet = stop()
            self.assertEqual((quiet.returncode, quiet.stdout, quiet.stderr), (0, "", ""))
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_text("# Cruise checkpoint — iteration 2\n- **Stage:** plan\n"
                                  "- **Next:** run /speckit-plan for S1\n")
            held = stop()
            self.assertEqual(held.returncode, 0, held.stderr)
            decision = json.loads(held.stdout)
            self.assertEqual(decision["decision"], "block")
            self.assertIn("did not end on one of its\nfour last lines".replace("\n", " "), decision["reason"])
            self.assertIn("a message that says what it is about to do next is a stop", decision["reason"])
            self.assertIn("Continue from the checkpoint: - **Next:** run /speckit-plan for S1.", decision["reason"])
            self.assertIn(f"`touch {STOP_FILE}`", decision["reason"])
            self.assertEqual(checkpoint.read_text().count("- **Held:**"), 1)
            # `continue` with no runner reading it is not an end either; with the runner, it is.
            said("The split is written and S1 is ready.\n\ncruise: continue")
            typed_continue = json.loads(stop().stdout)
            self.assertIn("`cruise: continue` reaches nobody: no runner started this session", typed_continue["reason"])
            self.assertEqual(checkpoint.read_text().count("- **Held:**"), 2)
            runner_continue = stop(CRUISE_RUNNER="1", CRUISE_ITERATION="2")
            self.assertEqual((runner_continue.returncode, runner_continue.stdout), (0, ""))
            # `parked` ends a turn on either side; the stop file ends the hook's interest; a rewrite resets the holds.
            said("cruise: parked: the payment provider's sandbox credentials")
            self.assertEqual(stop().stdout, "")
            said("Continuing now.")
            self.assertEqual(json.loads(stop().stdout)["decision"], "block")
            self.assertEqual(checkpoint.read_text().count("- **Held:**"), 3)
            let_go = stop()
            self.assertEqual(let_go.stdout, "")
            self.assertIn("held 3 times against a checkpoint nothing rewrote; letting the turn end", let_go.stderr)
            checkpoint.write_text("# Cruise checkpoint — iteration 2\n- **Stage:** tasks\n- **Next:** T001\n")
            self.assertEqual(json.loads(stop().stdout)["decision"], "block")
            (repo / STOP_FILE).touch()
            self.assertEqual(stop().stdout, "")
            (repo / STOP_FILE).unlink()
            # The event's own copy of the message wins over a transcript that has not caught up.
            said("Still going.")
            carried = subprocess.run(["python3", "scripts/agents/cruise.py", "stopping"], cwd=repo, text=True,
                                     capture_output=True, env=unset,
                                     input=json.dumps({"hook_event_name": "Stop", "transcript_path": str(transcript),
                                                       "last_assistant_message": "Parked.\n\ncruise: parked: a key"}))
            self.assertEqual((carried.returncode, carried.stdout), (0, ""))
            # `done` ends the turn and takes the checkpoint with it, as the runner would have.
            said("Every criterion shipped.\n\ncruise: done")
            self.assertEqual(stop().stdout, "")
            self.assertFalse(checkpoint.exists())
