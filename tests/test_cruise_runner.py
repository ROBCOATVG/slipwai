"""`/cruise`'s settings and its outer loop: `.specify/cruise.json`, `scripts/agents/cruise.py`, and the registry's
`headless` column the loop runs a harness through.

The command says it stops for a human and for nothing else; the loop is what makes that true across sessions,
so it is run here for real against a fake harness — one that makes progress and finishes, one that parks, one
that touches the stop file, one that spins without changing anything — and read back through the log it keeps.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from support import FactoryTestCase

from slipwai.assets import TOOLKIT_ROOT
from slipwai.project.cruise import CONFIG, LOG, SETTINGS, STOP_FILE, cruise_config

REGISTRY = json.loads((TOOLKIT_ROOT / "scripts/agents/registry.json").read_text())["harnesses"]
# A harness the loop can stand in for: one shell script, its behaviour chosen by the first word of its script.
FAKE = """#!/bin/sh
count_file="$(dirname "$0")/calls"
n=$(cat "$count_file" 2>/dev/null || echo 0); n=$((n + 1)); echo "$n" > "$count_file"
echo "$*" >> "$(dirname "$0")/prompts"
echo "iteration $n of the fake harness"
{behaviour}
"""


def cruise(repo: Path, *arguments: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["python3", "scripts/agents/cruise.py", *arguments], cwd=repo, text=True,
                          capture_output=True, env={**os.environ, **(env or {})})


def enable(repo: Path, harness: str = "claude", **settings: str) -> None:
    (repo / ".specify/integration.json").write_text(json.dumps({"installed_integrations": [harness]}))
    result = cruise(repo, "--set", "enabled=true", *(f"{k}={v}" for k, v in settings.items()))
    assert result.returncode == 0, result.stderr


def fake_harness(directory: Path, behaviour: str) -> dict[str, str]:
    """A fake harness whose command the loop runs instead of the registry's, and a fast poll."""
    script = directory / "harness.sh"
    script.write_text(FAKE.replace("{behaviour}", behaviour))
    return {"CRUISE_HARNESS_COMMAND": f"sh {script} {{prompt}}", "CRUISE_POLL_SECONDS": "0.1"}


def logged(repo: Path) -> list[dict]:
    return [json.loads(line) for line in (repo / LOG).read_text().splitlines()]


class CruiseRunnerTest(FactoryTestCase):
    def test_the_settings_file_the_script_and_the_command_agree_and_a_change_is_checked(self) -> None:
        """One list of settings, written into the file by the factory and read back by the script: the same
        keys, the same defaults, the same words for what each controls — and a hand edit or a `--set` outside
        it is refused with the reason, writing nothing."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "settings", "standard", "python")
            self.assertEqual((repo / CONFIG).read_text(), cruise_config())
            self.assertEqual({k for k, *_ in SETTINGS}, set(json.loads((repo / CONFIG).read_text())) - {"_comment"})
            shown = cruise(repo)
            self.assertEqual(shown.returncode, 0, shown.stderr)
            for key, _, default, controls in SETTINGS:
                self.assertIn(f"{key}: {json.dumps(default)} — {controls}", shown.stdout)
            check = cruise(repo, "--check")
            self.assertIn(f"check-cruise: {CONFIG} is well-formed; /cruise is not enabled", check.stdout)
            written = cruise(repo, "--set", "enabled=true", "stuck_after=2", "max_hours=null", "hand=http")
            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertIn("enabled = true\nstuck_after = 2\nmax_hours = null\nhand = \"http\"", written.stdout)
            self.assertIn("Commit it", written.stdout)
            table = json.loads((repo / CONFIG).read_text())
            self.assertEqual((table["enabled"], table["stuck_after"], table["max_hours"], table["hand"]),
                             (True, 2, None, "http"))
            for arguments, reason in (
                (("decide=nope",), "`decide` must be one of recommended-first, skipper-always, not 'nope'"),
                (("stuck_after=zero",), "`stuck_after` takes a whole number, not 'zero'"),
                (("stuck_after=0",), "`stuck_after` must be a whole number of at least 1, not 0"),
                (("poll_minutes=null",), "`poll_minutes` must be a whole number of at least 1, not None"),
                (("cycle=rule",), "--set takes key=value with a key from enabled, decide"),
                (("enabled=yes",), "`enabled` is true or false, not 'yes'"),
            ):
                refused = cruise(repo, "--set", *arguments)
                self.assertEqual(refused.returncode, 1, arguments)
                self.assertIn(reason, refused.stderr, arguments)
            self.assertEqual(json.loads((repo / CONFIG).read_text()), table, "a refusal wrote the file")
            (repo / CONFIG).write_text(json.dumps({**table, "release": "ask", "max_iterations": True}))
            broken = cruise(repo, "--check")
            self.assertEqual(broken.returncode, 1)
            self.assertIn("`release` must be one of flagged, park, not 'ask'", broken.stderr)
            self.assertIn("`max_iterations` must be a whole number of at least 1, or null, not True", broken.stderr)
            self.assertIn("python3 scripts/agents/cruise.py --check", (repo / "Makefile").read_text())

    def test_the_loop_runs_a_fresh_session_per_iteration_until_the_last_line_says_done(self) -> None:
        """Each iteration is one headless harness run, and the loop reads one line of it. `continue` runs
        another; `done` ends the run; every iteration is a line in the log with its fingerprint."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "done", "standard", "python")
            refused = cruise(repo, "run")
            self.assertEqual(refused.returncode, 1)
            self.assertIn("not enabled", refused.stderr)
            enable(repo)
            env = fake_harness(Path(directory), """mkdir -p specs && touch "specs/progress-$n"
if [ "$n" -lt 3 ]; then echo "cruise: continue"; else echo "cruise: done"; fi""")
            run = cruise(repo, "run", "--feature", "001-campaign", env=env)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("harness: CRUISE_HARNESS_COMMAND, as given", run.stdout)
            self.assertIn("each iteration runs `/cruise 001-campaign` in a fresh session", run.stdout)
            self.assertIn("cruise: done — every specification is satisfied", run.stdout)
            self.assertEqual((Path(directory) / "prompts").read_text(), "/cruise 001-campaign\n" * 3)
            log = logged(repo)
            self.assertEqual([entry["iteration"] for entry in log], [1, 2, 3])
            self.assertEqual([entry["last_line"] for entry in log],
                             ["cruise: continue", "cruise: continue", "cruise: done"])
            self.assertEqual({entry["harness"] for entry in log}, {"claude"})
            self.assertEqual(len({entry["fingerprint"] for entry in log}), 3, "progress changed the fingerprint")
            status = cruise(repo, "status")
            self.assertIn("3 iteration(s) logged; the last ended", status.stdout)
            self.assertIn("`cruise: done`", status.stdout)
            # A fourth run continues the numbering: the log is the run's memory, not the process.
            again = cruise(repo, "run", env={**env, "CRUISE_HARNESS_COMMAND": "echo 'cruise: done'"})
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertEqual(logged(repo)[-1]["iteration"], 4)

    def test_parked_waits_for_a_person_and_resumes_when_something_changes(self) -> None:
        """A parked iteration is the run saying what a person must provide. The loop waits — it does not exit,
        because exiting is how a run goes idle with nobody knowing — and resumes when an artifact changes;
        `--no-park` is the CI shape, which exits 3 instead."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "parked", "standard", "python")
            enable(repo)
            env = fake_harness(Path(directory), """mkdir -p specs
if [ "$n" -eq 1 ]; then echo "cruise: parked: a database credential nobody here has"; else echo "cruise: done"; fi""")
            no_park = cruise(repo, "run", "--no-park", env=env)
            self.assertEqual(no_park.returncode, 3, no_park.stdout)
            self.assertIn("cruise: parked — a database credential nobody here has", no_park.stdout)
            self.assertEqual(logged(repo)[-1]["last_line"], "cruise: parked: a database credential nobody here has")
            status = cruise(repo, "status")
            self.assertIn("cruise: parked — a database credential nobody here has", status.stdout)
            # Reset the fake and let the run wait; a person "answers" by writing under specs/.
            (Path(directory) / "calls").unlink()
            timer = threading.Timer(0.6, lambda: (repo / "specs/answer.md").write_text("here you are\n"))
            timer.start()
            waited = cruise(repo, "run", env=env)
            timer.join()
            self.assertEqual(waited.returncode, 0, waited.stderr)
            self.assertIn("cruise: waiting; `touch .specify/cruise.stop` ends the run", waited.stdout)
            self.assertIn("cruise: something changed; resuming", waited.stdout)
            self.assertIn("cruise: done", waited.stdout)

    def test_a_person_stops_a_run_with_the_stop_file_and_a_spinning_run_parks_itself(self) -> None:
        """The stop file ends the run between iterations, and inside a parked wait. And a run whose iterations
        change nothing is not a run: after `stuck_after` identical fingerprints it parks, saying since when."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "stop", "standard", "python")
            enable(repo, stuck_after="2")
            env = fake_harness(Path(directory), f"""mkdir -p specs && touch "specs/progress-$n"
if [ "$n" -eq 2 ]; then touch {STOP_FILE}; fi
echo "cruise: continue\"""")
            stopped = cruise(repo, "run", env=env)
            self.assertEqual(stopped.returncode, 0, stopped.stderr)
            self.assertIn("cruise: stopped by human", stopped.stdout)
            self.assertEqual(len(logged(repo)), 2)
            self.assertIn(f"{STOP_FILE} is present; remove it before the next run", cruise(repo, "status").stdout)
            (repo / STOP_FILE).unlink()
            (Path(directory) / "calls").unlink()
            spinning = fake_harness(Path(directory), 'echo "cruise: continue"')
            stuck = cruise(repo, "run", "--no-park", env=spinning)
            self.assertEqual(stuck.returncode, 3, stuck.stdout)
            self.assertIn("cruise: parked — no progress since iteration 3", stuck.stdout)
            self.assertEqual([entry["last_line"] for entry in logged(repo)[2:]], ["cruise: continue"] * 2)
            # A budget is the other honest end: it says so and exits 0.
            (Path(directory) / "calls").unlink()
            cruise(repo, "--set", "max_iterations=1")
            ticking = fake_harness(Path(directory), 'mkdir -p specs; date +%N > specs/t; echo "cruise: continue"')
            budget = cruise(repo, "run", env=ticking)
            self.assertEqual(budget.returncode, 0, budget.stderr)
            self.assertIn("cruise: budget spent — 1 iteration(s)", budget.stdout)

    def test_the_registry_says_how_each_harness_runs_headless_or_that_nobody_checked(self) -> None:
        """The loop guesses no flag: a harness runs headless the way its own documentation says, on the date
        the row names, and a harness with `null` is told to use its own loop over `/cruise` in a session."""
        for entry in REGISTRY:
            self.assertIn("headless", entry, entry["key"])
            row = entry["headless"]
            if row is None:
                continue
            self.assertIn("{prompt}", row["command"], entry["key"])
            for field in ("how", "command", "permissions", "sandboxPermissions", "source"):
                self.assertIn(field, row, f"{entry['key']}: {field}")
            self.assertRegex(row["source"], r"read \d{4}-\d{2}-\d{2}", entry["key"])
        claude = next(entry for entry in REGISTRY if entry["key"] == "claude")["headless"]
        self.assertEqual(claude["command"], "claude -p {prompt} --output-format text {permissions}")
        self.assertEqual(claude["permissions"], "--permission-mode acceptEdits")
        self.assertEqual(claude["sandboxPermissions"], "--dangerously-skip-permissions")
        # A print session ends its background delegates after 600s unless told to wait: a real run lost its
        # story delegate mid-slice to exactly that.
        self.assertEqual(claude["env"], {"CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS": "0"})
        self.assertTrue(next(entry for entry in REGISTRY if entry["key"] == "codex")["headless"])
        self.assertIsNone(next(entry for entry in REGISTRY if entry["key"] == "gemini")["headless"])
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "headless", "standard", "python")
            enable(repo, harness="gemini")
            unknown = cruise(repo, "run")
            self.assertEqual(unknown.returncode, 1)
            self.assertIn("the registry records no way to run Gemini CLI headless", unknown.stderr)
            self.assertIn("set CRUISE_HARNESS_COMMAND", unknown.stderr)
            # The registry's own template is what runs when nothing overrides it, with the permission flag the
            # row names — said once, at the start — and `--sandbox` is the only way to bypass them all.
            enable(repo, harness="claude")
            fake_claude = Path(directory) / "bin"
            fake_claude.mkdir()
            (fake_claude / "claude").write_text(
                '#!/bin/sh\necho "$* wait=$CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS'
                f' session=${{CLAUDE_CODE_SESSION_ID:-none}}" >> {Path(directory) / "claude-args"}\n'
                'echo "cruise: done"\n')
            (fake_claude / "claude").chmod(0o755)
            # A loop started from inside a Claude Code session inherits that session's id; the child must not.
            env = {"PATH": f"{fake_claude}:{os.environ['PATH']}", "CRUISE_POLL_SECONDS": "0",
                   "CLAUDE_CODE_SESSION_ID": "the-parent-session"}
            plain = cruise(repo, "run", env=env)
            self.assertEqual(plain.returncode, 0, plain.stderr)
            self.assertIn("cruise: harness: Claude Code; edits are accepted and every other permission is the "
                          "harness's own to grant or refuse", plain.stdout)
            sandboxed = cruise(repo, "run", "--sandbox", "--feature", "S1", env=env)
            self.assertEqual(sandboxed.returncode, 0, sandboxed.stderr)
            self.assertIn("--sandbox: every permission check is bypassed", sandboxed.stdout)
            self.assertEqual((Path(directory) / "claude-args").read_text(),
                             "-p /cruise --output-format text --permission-mode acceptEdits wait=0 session=none\n"
                             "-p /cruise S1 --output-format text --dangerously-skip-permissions wait=0 session=none\n")
            self.assertNotIn("session", logged(repo)[-1])
            # An iteration whose output carries no last line is logged as such and treated as `continue`.
            (fake_claude / "claude").write_text("#!/bin/sh\necho nothing to see\n")
            cruise(repo, "--set", "max_iterations=1")
            silent = cruise(repo, "run", env=env)
            self.assertEqual(silent.returncode, 0, silent.stderr)
            self.assertEqual(logged(repo)[-1]["last_line"], "no last line")

    def test_the_makefile_carries_the_loop_and_the_gate_holds_the_logs(self) -> None:
        """`make cruise` is the loop, `make cruise-status` the log, and `check-decisions` sits on `verify`
        because the decision log is the file a person edits to overrule the machine."""
        with tempfile.TemporaryDirectory() as directory:
            for profile in ("event-modelling", "standard"):
                repo = self.generate(directory, profile, profile, "typescript")
                makefile = (repo / "Makefile").read_text()
                self.assertIn("cruise: ## Run /drive with nobody at the wheel", makefile)
                self.assertIn("\tpython3 scripts/agents/cruise.py run $(if $(FEATURE),--feature $(FEATURE),) "
                              "$(CRUISE_FLAGS)", makefile)
                self.assertIn("cruise-status: ## Say what the /cruise log shows", makefile)
                self.assertIn("check-decisions: ## Fail when a decision log or demo log /cruise wrote has lost its "
                              "shape", makefile)
                verify = re.search(r"^verify: (.*)$", makefile, re.MULTILINE)
                assert verify is not None
                self.assertIn("check-decisions", verify.group(1).split())
                self.assertIn("check-benchmark check-decisions test", verify.group(1))
                self.assertTrue((repo / "scripts/agents/cruise.py").is_file())
                self.assertLess(time.time() - (repo / "scripts/agents/cruise.py").stat().st_mtime, 3600)
