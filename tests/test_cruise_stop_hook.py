"""`/cruise`'s stop hook: the end of a runner's iteration checked where a harness lets a hook refuse it.

`commands/cruise.md` said "do not wait to be invoked again" and was not enough twice in one session — once
ending after the upstream stages, once on a report that said "continuing now" — so the contract is enforced by
`scripts/agents/cruise.py stopping`, run from the hook file each harness reads: `.claude/settings.json` on
Claude Code's `Stop`, `.cursor/hooks.json` on Cursor's `stop`, `.gemini/settings.json` on Gemini CLI's
`AfterAgent`. Only in a session the runner started, which it marks: a typed `/cruise` runs no iteration, it starts
the runner, so there the hook is silent. All of it is run here for real, against fake events, a transcript and a
checkpoint.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_cruise_runner import REGISTRY, enable

from slipwai.project.cruise import STOP_FILE, UNREAD
from slipwai.project.cruise_record import CHECKPOINT, LAST_RESPONSE

RUNNER = {"CRUISE_RUNNER": "1", "CRUISE_ITERATION": "2"}


def hook(repo: Path, verb: str, event: dict, env: dict[str, str]) -> subprocess.CompletedProcess:
    unset = {k: v for k, v in os.environ.items() if k not in ("CRUISE_RUNNER", "CRUISE_ITERATION")}
    return subprocess.run(["python3", "scripts/agents/cruise.py", verb], cwd=repo, text=True, capture_output=True,
                          env={**unset, **env}, input=json.dumps(event))


class CruiseStopHookTest(FactoryTestCase):
    def test_the_stop_hook_holds_a_runners_iteration_that_is_not_at_an_end_and_never_a_typed_session(self) -> None:
        """Prose in a command file is not a control: one session ended an iteration after the upstream stages,
        and later on a report that said "continuing now". Claude Code's Stop hook can refuse the end of a turn,
        so `stopping` does — in a session the runner started, while a checkpoint is in flight and no stop file
        exists — unless the last assistant message ends on one of the four lines. It stamps every hold, lets go
        after HOLD_LIMIT holds nothing rewrote, takes the checkpoint with a `done`, and says nothing at all in a
        session no runner started: a typed `/cruise` starts the runner and ends, so there is nothing to hold."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "stopping", "standard", "python")
            settings = json.loads((repo / ".claude/settings.json").read_text())
            self.assertEqual(settings["hooks"]["Stop"],
                             [{"hooks": [{"type": "command", "command": "python3 scripts/agents/cruise.py stopping"}]}])
            enable(repo)
            checkpoint = repo / CHECKPOINT
            transcript = Path(directory) / "transcript.jsonl"

            def said(*texts: str) -> None:
                lines = [json.dumps({"type": "user", "message": {"role": "user", "content": "/cruise"}})]
                for text in texts:
                    lines.append(json.dumps({"type": "assistant", "message": {
                        "role": "assistant", "content": [{"type": "text", "text": text}]}}))
                    lines.append(json.dumps({"type": "assistant", "message": {
                        "role": "assistant", "content": [{"type": "tool_use", "name": "Bash", "input": {}}]}}))
                transcript.write_text("\n".join(lines) + "\n")

            def stop(env: dict[str, str] = RUNNER, **event: object) -> subprocess.CompletedProcess:
                return hook(repo, "stopping", {"hook_event_name": "Stop", "stop_hook_active": False,
                                               "transcript_path": str(transcript), **event}, env)

            # What `loop` says on each side.
            typed = hook(repo, "loop", {}, {})
            self.assertEqual(typed.stdout.strip(), f"cruise: {UNREAD}")
            self.assertIn("scripts/agents/cruise.py start", typed.stdout)
            driven = hook(repo, "loop", {}, {"CRUISE_RUNNER": "1", "CRUISE_ITERATION": "4"})
            self.assertIn("started this session as iteration 4 and reads its last line", driven.stdout)
            # No iteration in flight: the hook is silent whatever the transcript says.
            said("Stage done. Continuing into S1's plan and tasks now.")
            quiet = stop()
            self.assertEqual((quiet.returncode, quiet.stdout, quiet.stderr), (0, "", ""))
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_text("# Cruise checkpoint — iteration 2\n- **Stage:** plan\n"
                                  "- **Next:** run /speckit-plan for S1\n")
            # A checkpoint in flight, but no runner started this session: a typed /cruise, which is never held.
            unheld = stop(env={})
            self.assertEqual((unheld.returncode, unheld.stdout, unheld.stderr), (0, "", ""))
            self.assertNotIn("- **Held:**", checkpoint.read_text())
            held = stop()
            self.assertEqual(held.returncode, 0, held.stderr)
            decision = json.loads(held.stdout)
            self.assertEqual(decision["decision"], "block")
            self.assertIn("did not end on one of its four last lines", decision["reason"])
            self.assertIn("a message that says what it is about to do next is a stop", decision["reason"])
            self.assertIn("Continue from the checkpoint: - **Next:** run /speckit-plan for S1.", decision["reason"])
            self.assertIn(f"`touch {STOP_FILE}`", decision["reason"])
            self.assertEqual(checkpoint.read_text().count("- **Held:**"), 1)
            # `continue` is an end for the runner, which reads it; so is `parked`.
            said("The split is written and S1 is ready.\n\ncruise: continue")
            self.assertEqual((stop().returncode, stop().stdout), (0, ""))
            said("cruise: parked: the payment provider's sandbox credentials")
            self.assertEqual(stop().stdout, "")
            # Every hold is stamped; after three against one checkpoint the hook lets go, and a rewrite resets it.
            said("Continuing now.")
            self.assertEqual(json.loads(stop().stdout)["decision"], "block")
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
            carried = stop(last_assistant_message="Parked.\n\ncruise: parked: a key")
            self.assertEqual((carried.returncode, carried.stdout), (0, ""))
            # No message anywhere is no evidence, and no hold: a hook cannot judge what it cannot see.
            blind = stop(transcript_path=str(Path(directory) / "nowhere.jsonl"))
            self.assertEqual((blind.returncode, blind.stdout), (0, ""))
            self.assertIn("carries no last message and no hook kept one; not holding", blind.stderr)
            # `done` ends the turn and takes the checkpoint with it, as the runner would have.
            said("Every criterion shipped.\n\ncruise: done")
            self.assertEqual(stop().stdout, "")
            self.assertFalse(checkpoint.exists())

    def test_the_hold_is_spelled_the_way_each_harness_reads_it_and_projected_where_its_shape_is_known(self) -> None:
        """Cursor's `stop` takes `followup_message` and carries no text, so `afterAgentResponse` keeps the last
        message for it; Gemini CLI's `AfterAgent` carries it as `prompt_response` and takes the same block
        decision Claude Code does; Grok Build spells the message `lastAssistantMessage`. The registry says which
        harness has such a hook and, where the file's shape was read, `scripts/agents/project.py` writes it —
        merged into a file a person may also keep keys in, and held to by `check-agents`."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "shapes", "standard", "python")
            enable(repo)
            checkpoint = repo / CHECKPOINT
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_text("# Cruise checkpoint — iteration 3\n- **Stage:** implement\n- **Next:** T004\n")
            # Cursor: the after-response hook keeps the text, in a runner's session only; the stop hook reads it.
            kept = hook(repo, "responded", {"hook_event_name": "afterAgentResponse", "text": "Going on.\n"}, {})
            self.assertEqual((kept.returncode, kept.stdout), (0, ""))
            self.assertFalse((repo / LAST_RESPONSE).exists(), "a typed session's messages are nobody's business")
            hook(repo, "responded", {"hook_event_name": "afterAgentResponse", "text": "Going on to T004 now."}, RUNNER)
            self.assertEqual((repo / LAST_RESPONSE).read_text(), "Going on to T004 now.")
            cursor = hook(repo, "stopping", {"hook_event_name": "stop", "status": "completed", "loop_count": 0}, RUNNER)
            self.assertEqual(cursor.returncode, 0, cursor.stderr)
            followup = json.loads(cursor.stdout)
            self.assertEqual(list(followup), ["followup_message"])
            self.assertIn("Continue from the checkpoint: - **Next:** T004.", followup["followup_message"])
            hook(repo, "responded", {"hook_event_name": "afterAgentResponse", "text": "Done.\n\ncruise: continue"},
                 RUNNER)
            ended = hook(repo, "stopping", {"hook_event_name": "stop", "status": "completed", "loop_count": 1}, RUNNER)
            self.assertEqual(ended.stdout, "")
            # Gemini CLI: the text rides in the event, and `block` is the alias its `deny` accepts.
            gemini = hook(repo, "stopping", {"prompt": "/cruise", "prompt_response": "Next: the plan.",
                                             "stop_hook_active": False}, RUNNER)
            self.assertEqual(json.loads(gemini.stdout)["decision"], "block")
            self.assertEqual(hook(repo, "stopping", {"prompt_response": "cruise: continue"}, RUNNER).stdout, "")
            # Grok Build: Claude Code's shape with its own spelling of the message.
            grok = hook(repo, "stopping", {"hook_event_name": "Stop", "lastAssistantMessage": "cruise: parked: a key"},
                        RUNNER)
            self.assertEqual(grok.stdout, "")
            self.assertEqual(checkpoint.read_text().count("- **Held:**"), 2)
            # The registry: every harness says whether it can hold a turn, and what this factory writes for it.
            projected = {}
            for entry in REGISTRY:
                self.assertIn("hooks", entry, entry["key"])
                row = entry["hooks"]
                if row is None:
                    continue
                self.assertIn("holds", row, entry["key"])
                self.assertTrue(row["how"], entry["key"])
                if row["projection"] is None:
                    self.assertTrue(row["why"], entry["key"])
                else:
                    projected[entry["key"]] = row["projection"]
            self.assertEqual(set(projected), {"cursor-agent", "gemini"})
            self.assertEqual(projected["cursor-agent"]["where"], ".cursor/hooks.json")
            self.assertEqual(projected["gemini"]["where"], ".gemini/settings.json")
            self.assertTrue(next(e for e in REGISTRY if e["key"] == "claude")["hooks"]["holds"])
            # The projection: written by `project.py`, merged into what a person already keeps there.
            (repo / ".gemini").mkdir()
            (repo / ".gemini/settings.json").write_text(json.dumps(
                {"theme": "Dracula", "hooks": {"BeforeTool": [{"type": "command", "command": "./mine.sh"}]}}))
            (repo / ".specify/integration.json").write_text(
                json.dumps({"installed_integrations": ["cursor-agent", "gemini"]}))
            written = subprocess.run(["python3", "scripts/agents/project.py", "cursor-agent", "gemini"], cwd=repo,
                                     text=True, capture_output=True)
            self.assertEqual(written.returncode, 0, written.stderr)
            cursor_hooks = json.loads((repo / ".cursor/hooks.json").read_text())
            self.assertEqual(cursor_hooks, {"version": 1, "hooks": {
                "stop": [{"command": "python3 scripts/agents/cruise.py stopping", "loop_limit": None}],
                "afterAgentResponse": [{"command": "python3 scripts/agents/cruise.py responded"}],
                "preCompact": [{"command": "python3 scripts/agents/cruise.py compacting"}]}})
            gemini_settings = json.loads((repo / ".gemini/settings.json").read_text())
            self.assertEqual(gemini_settings["theme"], "Dracula")
            self.assertEqual(gemini_settings["hooks"]["BeforeTool"], [{"type": "command", "command": "./mine.sh"}])
            self.assertEqual(gemini_settings["hooks"]["AfterAgent"],
                             [{"type": "command", "command": "python3 scripts/agents/cruise.py stopping",
                               "name": "cruise"}])
            check = subprocess.run(["python3", "scripts/agents/project.py", "--check"], cwd=repo, text=True,
                                   capture_output=True)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            # A person's formatting is not drift; a missing stop hook is.
            (repo / ".cursor/hooks.json").write_text(json.dumps(cursor_hooks, indent=4))
            self.assertEqual(subprocess.run(["python3", "scripts/agents/project.py", "--check"], cwd=repo, text=True,
                                            capture_output=True).returncode, 0)
            del cursor_hooks["hooks"]["stop"]
            (repo / ".cursor/hooks.json").write_text(json.dumps(cursor_hooks))
            drifted = subprocess.run(["python3", "scripts/agents/project.py", "--check"], cwd=repo, text=True,
                                     capture_output=True)
            self.assertEqual(drifted.returncode, 1)
            self.assertIn(".cursor/hooks.json: differs from its canonical source", drifted.stderr)
