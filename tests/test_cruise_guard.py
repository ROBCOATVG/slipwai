"""A gate is satisfied in the tree it measures, never by editing the gate — held mechanically, on both sides.

A `/cruise` run met `check-ux-gates` failing because two of the kit's scripts crash where Chrome is not installed,
and the bosun patched `scripts/check-ux-gates.py` to call that skipped, committed it, and went on. The brief now
forbids it, and the rule is not left to the brief: Claude Code's `PreToolUse` hook runs `scripts/agents/cruise.py
guard` on every editing tool and refuses the edit in a runner's session, and the runner compares every gate and
control before and after each iteration, on every harness, and parks the run on a change. Both run here for real.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_cruise_runner import cruise, enable, fake_harness, logged
from test_cruise_stop_hook import RUNNER, hook

from slipwai.assets import ROOT
from slipwai.project.cruise_agents import BOSUN

GUARDED = ("scripts/check-ux-gates.py", "scripts/agents/cruise.py", "tools/ux-gates/scripts/verify_responsive.mjs",
           "Makefile", ".claude/settings.json", ".cursor/hooks.json", ".github/workflows/verify.yml")
OPEN = ("apps/api/src/app.py", "specs/cruise-checkpoint.md", "docs/adr/0002-a-choice.md", "AGENTS.md")


def edit(repo: Path, path: str, env: dict[str, str] = RUNNER, **more: object):
    event = {"hook_event_name": "PreToolUse", "tool_name": "Write", "cwd": str(repo),
             "tool_input": {"file_path": path, "content": "patched"}, **more}
    return hook(repo, "guard", event, env)


class CruiseGuardTest(FactoryTestCase):
    def test_the_guard_hook_refuses_an_edit_to_a_gate_or_a_control_in_a_runners_session_only(self) -> None:
        """`.claude/settings.json` runs `guard` before every editing tool. In a session the runner started it
        refuses — exit 2, the reason on stderr, which is how Claude Code hands a refusal to the model — an edit
        under `scripts/`, `tools/`, the Makefile, CI or a harness's hook file, by absolute or relative path, and
        lets an edit to the slice's own tree through. Outside a runner's session it does nothing at all."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "guarded", "standard", "python")
            settings = json.loads((repo / ".claude/settings.json").read_text())
            self.assertEqual(settings["hooks"]["PreToolUse"], [{
                "matcher": "Edit|Write|MultiEdit|NotebookEdit",
                "hooks": [{"type": "command", "command": "python3 scripts/agents/cruise.py guard"}]}])
            enable(repo)
            for path in GUARDED:
                for spelled in (path, str(repo / path)):
                    refused = edit(repo, spelled)
                    self.assertEqual(refused.returncode, 2, (spelled, refused.stderr))
                    self.assertIn(f"cruise: `{path}` is a gate or a control of this run, and an iteration never "
                                  "edits one — a gate is satisfied in the tree it measures, or the run parks with "
                                  "the gate's own output as the reason", refused.stderr)
                    self.assertEqual(refused.stdout, "")
            notebook = hook(repo, "guard", {"tool_name": "NotebookEdit", "cwd": str(repo),
                                            "tool_input": {"notebook_path": "scripts/agents/notes.ipynb"}}, RUNNER)
            self.assertEqual(notebook.returncode, 2, notebook.stderr)
            for path in OPEN:
                allowed = edit(repo, str(repo / path))
                self.assertEqual((allowed.returncode, allowed.stdout, allowed.stderr), (0, "", ""), path)
            typed = edit(repo, str(repo / "scripts/check-ux-gates.py"), env={})
            self.assertEqual((typed.returncode, typed.stdout, typed.stderr), (0, "", ""))
            # An event with no path — a tool the matcher did not mean — is let through rather than guessed at.
            self.assertEqual(hook(repo, "guard", {"tool_name": "Write", "tool_input": {}}, RUNNER).returncode, 0)

    def test_the_runner_parks_an_iteration_that_changed_a_gate_whatever_its_last_line_said(self) -> None:
        """The hook covers the editing tools on one harness; the runner covers the shell on every harness. It takes
        the content of every gate and control before an iteration and compares it after: a modified gate parks the
        run at once with the file named, `controls_changed` on the log entry, and `cruise: continue` counts for
        nothing. A file installed under `tools/`, which is what `./init --extension` does, is not a change; a
        gate deleted, or a script added beside the gates, is."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "parks", "standard", "python")
            enable(repo)
            env = fake_harness(Path(directory), """mkdir -p specs tools/ux-gates && touch "specs/progress-$n"
touch "tools/ux-gates/installed-$n"
if [ "$n" -eq 1 ]; then echo "# treat a crash as skipped" >> scripts/check-ux-gates.py; fi
echo "cruise: continue\"""")
            parked = cruise(repo, "run", "--no-park", env=env)
            self.assertEqual(parked.returncode, 3, parked.stdout + parked.stderr)
            self.assertIn("cruise: iteration 1 ended — cruise: continue", parked.stdout)
            self.assertIn("cruise: parked — iteration 1 changed a gate or a control of the run — "
                          "scripts/check-ux-gates.py (modified) — and a gate is satisfied in the tree it measures, "
                          "never edited; revert the change, or keep it on purpose and resume with a message",
                          parked.stdout)
            self.assertEqual(logged(repo)[-1]["controls_changed"], ["scripts/check-ux-gates.py (modified)"])
            self.assertEqual(len(logged(repo)), 1, "the run did not go on to a second iteration")
            (repo / "scripts/check-ux-gates.py").write_text(
                (repo / "scripts/check-ux-gates.py").read_text().replace("# treat a crash as skipped\n", ""))
            (Path(directory) / "calls").unlink()
            env = fake_harness(Path(directory), """mkdir -p specs tools/ux-gates && touch "specs/progress-$n"
touch "tools/ux-gates/installed-$n"
if [ "$n" -eq 2 ]; then rm Makefile; printf 'raise SystemExit(0)\\n' > scripts/check-nothing.py; fi
if [ "$n" -ge 3 ]; then echo "cruise: done"; else echo "cruise: continue"; fi""")
            # The log numbers iterations across runs: the fake's first call here is iteration 2, its second 3.
            again = cruise(repo, "run", "--no-park", env=env)
            self.assertEqual(again.returncode, 3, again.stdout + again.stderr)
            self.assertIn("cruise: iteration 2 ended — cruise: continue", again.stdout)
            self.assertNotIn("iteration 2 changed", again.stdout, "an install under tools/ is not a change")
            self.assertIn("cruise: parked — iteration 3 changed a gate or a control of the run — "
                          "Makefile (deleted), scripts/check-nothing.py (added)", again.stdout)
            self.assertEqual(logged(repo)[-1]["controls_changed"],
                             ["Makefile (deleted)", "scripts/check-nothing.py (added)"])

    def test_the_brief_the_command_and_the_pages_say_a_gate_is_never_repaired_in_the_gate(self) -> None:
        """The words match the mechanism: the bosun's brief names what it never touches and what a gate the tree
        cannot satisfy becomes, `commands/cruise.md` carries the rule on the catastrophic list and beside the two
        controls that hold it, and the pages a person reads say the same."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "worded", "standard", "python")
            bosun = (repo / f"agents/{BOSUN}.md").read_text()
            self.assertIn("or make a gate pass by\nchanging the gate. **A gate is satisfied in the tree it measures, "
                          "never by editing what measures it**: nothing\nunder `scripts/` — the `check-*` gates, "
                          "this runner — the `Makefile`, anything under `tools/`, CI, or a\nharness's hook settings "
                          "is yours to touch, whatever it reports.", bosun)
            self.assertIn("is `cannot: <the gate's name and\nits own last lines>`, and the run parks on those words; "
                          "`make verify` reporting a gate as skipped is not a\nfailure", bosun)
            self.assertIn("fix the cause in the tree the gate measures", bosun)
            command = (repo / "commands/cruise.md").read_text()
            self.assertIn("- making a gate pass by changing the gate — anything under `scripts/`, the `Makefile`, "
                          "anything under `tools/`, CI, a harness's hook settings: a gate is satisfied in the tree it "
                          "measures, or the run parks with the gate's own output as the reason", command)
            self.assertIn("**A failing gate is never repaired in the gate.**", command)
            self.assertIn("`cruise: parked: <gate>: <its own last lines>`", command)
            self.assertIn("`python3 scripts/agents/cruise.py guard` runs as the `PreToolUse` hook", command)
            self.assertIn("`controls_changed` on the log entry names the files", command)
            self.assertIn("A file installed under `tools/` by `./init --extension` is not a change.", command)
        for page, words in (("docs/cruise.md", "**A failing gate is never repaired in the gate.**"),
                            ("README.md", "**It never makes a gate pass by changing the gate.**")):
            self.assertIn(words, (ROOT / page).read_text(), page)
