"""The watch seat and the feed: what the session that typed `/cruise` sees of the run it started, and what a run
is allowed to do without asking. The runner renders a harness's event stream — Claude Code's `stream-json`,
Codex's `--json`, from recorded fixtures — into one line per thing an iteration did; `watch` reads that back to
the next boundary; the kick-off typed after `/cruise` reaches the first iteration only; and the allowlist every
project ships covers every command the command file and the hooks issue, whatever the language, because a
headless iteration cannot ask.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_cruise_runner import cruise, enable, fake_harness, logged

from slipwai.project.cruise_record import RUNNER_STREAM

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class CruiseWatchTest(FactoryTestCase):
    def test_the_feed_renders_a_harness_stream_one_line_per_thing_done_and_reads_the_last_line_from_it(self) -> None:
        """A harness with an event stream — Claude Code's `stream-json`, Codex's `--json` — is not echoed raw: the
        runner renders one line per command, file, and delegate out and back, keeps the raw stream beside the
        log, and reads the iteration's last line from the stream's final message. A refused command is in the
        feed the moment it happens, with the denial the session ended on."""
        fixtures = FIXTURES / "cruise"
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "feed", "standard", "python")
            enable(repo)
            env = fake_harness(Path(directory), f"""mkdir -p specs && touch "specs/progress-$n"
if [ "$n" -lt 2 ]; then cat {fixtures}/claude-stream.jsonl
else sed 's/cruise: continue/cruise: done/' {fixtures}/claude-stream.jsonl; fi""")
            run = cruise(repo, "run", env={**env, "CRUISE_HARNESS_STREAM": "claude"})
            self.assertEqual(run.returncode, 0, run.stderr)
            feed = [re.sub(r"^\d\d:\d\d:\d\d  ", "", line) for line in run.stdout.splitlines()]
            for line in (
                "  $ python3 scripts/agents/cruise.py loop",
                "  read  /work/product/specs/001-ledger/spec.md",
                "  · Iteration 1: S03 is the ready slice. Delegating its plan.",
                '  agent drive-plan  "S03 plan: the posting adapter"  ▶',
                "      $ make verify",
                "        failed  make: *** [verify] Error 2",
                "      write  /work/product/specs/001-ledger/slices/S03/plan.md",
                "      report  · S03 plan written; one test red as expected.",
                "  agent drive-plan  ■ back  0s",
                "cruise: iteration 1 ended — cruise: continue (0s)",
                "cruise: iteration 2 ended — cruise: done (0s)",
            ):
                self.assertIn(line, feed, line)
            self.assertNotIn("Second paragraph the feed does not show.", run.stdout)
            self.assertNotIn('"type": "assistant"', run.stdout, "the raw stream is not echoed")
            self.assertEqual([entry["last_line"] for entry in logged(repo)], ["cruise: continue", "cruise: done"])
            raw = (repo / RUNNER_STREAM).read_text()
            self.assertIn("# iteration 1 ", raw)
            self.assertIn('"type": "result"', raw)
            self.assertIn(RUNNER_STREAM, (repo / ".gitignore").read_text())
            # Codex's stream, through the same seat.
            (Path(directory) / "calls").unlink()
            env = fake_harness(Path(directory), f"cat {fixtures}/codex-stream.jsonl")
            run = cruise(repo, "run", "--no-park", env={**env, "CRUISE_HARNESS_STREAM": "codex",
                                                         "CRUISE_POLL_SECONDS": "0.1"})
            feed = [re.sub(r"^\d\d:\d\d:\d\d  ", "", line) for line in run.stdout.splitlines()]
            for line in (
                "  $ make verify",
                "    failed  exit 2  FAIL: test_posting_rejects_an_empty_id",
                "  add  specs/001-ledger/slices/S03/plan.md",
                "  update  apps/ledger/src/posting.ts",
                '  agent spawn_agent  "Demo S03 as the actor"  ▶',
                "  agent spawn_agent  ■ back  completed",
                "  · S03 demoed and accepted.",
                "cruise: iteration 3 ended — cruise: continue (0s)",
            ):
                self.assertIn(line, feed, line)
            # A first command refused: the feed says so where it happened, and the run parks on the session's word.
            (Path(directory) / "calls").unlink()
            env = fake_harness(Path(directory), f"cat {fixtures}/claude-stream-refused.jsonl")
            run = cruise(repo, "run", "--no-park", env={**env, "CRUISE_HARNESS_STREAM": "claude"})
            self.assertEqual(run.returncode, 3, run.stdout)
            self.assertIn("failed  Permission to use Bash with command python3 scripts/agents/cruise.py loop",
                          run.stdout)
            self.assertIn("denied  Bash  python3 scripts/agents/cruise.py loop", run.stdout)
            self.assertIn("cruise: parked — no command can be run from this session (python3 needs approval)",
                          run.stdout)
            # What the run was refused is measured from the stream, not guessed: the list to read before widening.
            refused = cruise(repo, "denials")
            self.assertEqual(refused.stdout.splitlines(), [
                "cruise: 1 refusal(s), 1 distinct — each is a tool the harness's row does not allow, or a settings "
                "rule denies; a deny rule that fired is doing its job",
                "    1×  Bash  python3 scripts/agents/cruise.py loop  (iteration 6)",
            ])
            self.assertIn("cruise: 1 permission refusal(s) in the stream; `python3 scripts/agents/cruise.py denials` "
                          "lists them", cruise(repo, "status").stdout)

    def test_the_watch_seat_returns_at_each_boundary_and_the_kick_off_reaches_the_first_iteration_only(self) -> None:
        """A typed `/cruise` starts the runner and then watches it from the same session: `watch` prints the feed
        from where the last one left off and returns at the iteration's end, a park, the run's end or no runner,
        saying which. What was typed after `/cruise` is the kick-off: the first iteration's argument, and no
        later one's, because everything after derives from disk."""
        fixtures = FIXTURES / "cruise"
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "watch", "standard", "python")
            enable(repo)
            env = {**fake_harness(Path(directory), f"""mkdir -p specs && touch "specs/progress-$n"
sleep 0.3
if [ "$n" -lt 2 ]; then cat {fixtures}/claude-stream.jsonl
else sed 's/cruise: continue/cruise: done/' {fixtures}/claude-stream.jsonl; fi"""),
                   "CRUISE_HARNESS_STREAM": "claude", "CRUISE_WATCH_TICK": "0.05"}
            nobody = cruise(repo, "watch", env=env)
            self.assertEqual(nobody.stdout.strip().splitlines()[-1],
                             "cruise: watch: no runner is running; nothing to watch (`python3 scripts/agents/cruise.py "
                             "status` says what the log shows)")
            try:
                started = cruise(repo, "start", "use", "the", "PRD", "in", "docs/prd.md", env=env)
                self.assertEqual(started.returncode, 0, started.stderr)
                self.assertIn("cruise: runner started as pid", started.stdout)
                self.assertIn("cruise: the first iteration runs `/cruise use the PRD in docs/prd.md`, the kick-off; "
                              "every later one runs `/cruise`, and derives from disk", started.stdout)
                self.assertIn("cruise: watch it from here with `python3 scripts/agents/cruise.py watch`: it prints "
                              "what the iteration does as it happens and returns at the iteration's end, a park, the "
                              "run's end, once the feed has been quiet for 20 seconds, or after 1.5 minutes with "
                              "nothing new", started.stdout)
                first = cruise(repo, "watch", env=env)
                self.assertEqual(first.returncode, 0, first.stderr)
                lines = first.stdout.splitlines()
                self.assertIn("cruise: runner started ", lines[0])
                self.assertIn("cruise: iteration 1 started ", first.stdout)
                self.assertIn("running `/cruise use the PRD in docs/prd.md`", first.stdout)
                self.assertIn('agent drive-plan  "S03 plan: the posting adapter"  ▶', first.stdout)
                self.assertIn("agent drive-plan  ■ back", first.stdout)
                self.assertIn("cruise: iteration 1 ended — cruise: continue (0s)", first.stdout)
                self.assertEqual(lines[-1], "cruise: watch: the run continues — watch again with `python3 "
                                            "scripts/agents/cruise.py watch`; the runner needs nothing from this "
                                            "session")
                self.assertNotIn("iteration 2 ended", first.stdout, "a watch returns at the first boundary")
                second = cruise(repo, "watch", env=env)
                self.assertNotIn("iteration 1 ended", second.stdout, "the cursor moved: nothing is shown twice")
                self.assertIn("cruise: iteration 2 started ", second.stdout)
                self.assertIn("running `/cruise`", second.stdout)
                self.assertIn("cruise: iteration 2 ended — cruise: done (0s)", second.stdout)
                self.assertEqual(second.stdout.strip().splitlines()[-1],
                                 "cruise: watch: the run ended — cruise: done — every specification is satisfied; "
                                 "nothing to watch")
                self.assertEqual((Path(directory) / "prompts").read_text().splitlines(),
                                 ["/cruise use the PRD in docs/prd.md", "/cruise"])
                log = logged(repo)
                self.assertEqual([entry.get("attempt") for entry in log], ["kick-off", None])
                # A run parked before the seat looked: said at once, not after the watch's whole budget.
                (Path(directory) / "calls").unlink()
                env = {**env, **fake_harness(Path(directory), f"cat {fixtures}/claude-stream-refused.jsonl"),
                       "CRUISE_POLL_SECONDS": "30"}
                started = cruise(repo, "start", env=env)
                self.assertEqual(started.returncode, 0, started.stderr)
                self.assertNotIn("kick-off", started.stdout)
                parked = cruise(repo, "watch", env=env)
                self.assertIn("denied  Bash  python3 scripts/agents/cruise.py loop", parked.stdout)
                self.assertEqual(parked.stdout.strip().splitlines()[-1],
                                 "cruise: watch: parked — no command can be run from this session (python3 needs "
                                 "approval). The runner waits: a change under specs/ or a commit resumes it, `touch "
                                 ".specify/cruise.stop` ends it; nothing to watch until then")
                again = subprocess.run(["python3", "scripts/agents/cruise.py", "watch", "--minutes", "1"], cwd=repo,
                                       text=True, capture_output=True, env={**os.environ, **env}, timeout=20)
                self.assertTrue(again.stdout.startswith("cruise: watch: parked — "), again.stdout)
            finally:
                cruise(repo, "stop", "--now")
            # An iteration that keeps working: the seat returns with what it has once the feed goes quiet, so a
            # harness that shows a command's output only when it returns still shows the feed as it happens.
            (repo / ".specify/cruise.stop").unlink()
            (Path(directory) / "calls").unlink()
            env = {**env, **fake_harness(Path(directory), f"""head -3 {fixtures}/claude-stream.jsonl
sleep 4
tail -n +4 {fixtures}/claude-stream.jsonl | sed 's/cruise: continue/cruise: done/'"""), "CRUISE_POLL_SECONDS": "0.1"}
            try:
                started = cruise(repo, "start", env=env)
                self.assertEqual(started.returncode, 0, started.stderr)
                quiet = cruise(repo, "watch", "--quiet", "0.5", env=env)
                self.assertIn("$ python3 scripts/agents/cruise.py loop", quiet.stdout)
                self.assertNotIn("agent drive-plan", quiet.stdout, "returned on quiet, before the rest of the stream")
                self.assertEqual(quiet.stdout.strip().splitlines()[-1],
                                 "cruise: watch: the iteration is in flight and the feed went quiet — watch again with "
                                 "`python3 scripts/agents/cruise.py watch` to keep watching")
                rest = cruise(repo, "watch", "--quiet", "0.5", env=env)
                self.assertIn("agent drive-plan", rest.stdout)
                self.assertIn("cruise: watch: the run ended — cruise: done", rest.stdout)
            finally:
                cruise(repo, "stop", "--now")

    def test_the_allowlist_covers_every_command_the_command_and_the_hooks_issue_whatever_the_language(self) -> None:
        """A session that cannot ask is refused every command its rules do not name — which is what parked a
        TypeScript project's first iteration on `python3 scripts/agents/cruise.py loop`, its allowlist having no
        `python3` rule. The headless iteration is now given the shell wholesale by the registry row, and the
        allowlist is what keeps a person's own session — `/drive`, a typed `/cruise` — from prompting at every
        hook and gate; the deny rules are what hold in both. So the toolkit's own scripts and the Git a slice
        is made of are allowed in every project, and this holds the list to what the command file and the
        hooks actually run."""
        def matches(rules: list[str], command: str) -> bool:
            for rule in rules:
                pattern = rule.removeprefix("Bash(").removesuffix(")")
                if pattern.endswith("*") and command.startswith(pattern[:-1]) or command == pattern:
                    return True
            return False

        def allows(permissions: dict, command: str) -> bool:
            # Claude Code's rule: a deny rule wins over every allow rule.
            return matches(permissions["allow"], command) and not matches(permissions.get("deny", []), command)

        with tempfile.TemporaryDirectory() as directory:
            for language in ("typescript", "go", "python"):
                repo = self.generate(directory, language, "standard", language)
                settings = json.loads((repo / ".claude/settings.json").read_text())
                rules = settings["permissions"]
                command = (repo / "commands/cruise.md").read_text()
                issued = set(re.findall(r"python3 scripts/[a-z_/-]+\.py(?: [a-z-]+)?", command))
                issued |= {hook["command"] for event in settings["hooks"].values() for entry in event
                           for hook in entry["hooks"]}
                self.assertIn("python3 scripts/agents/cruise.py loop", issued)
                self.assertIn("python3 scripts/agents/cruise.py start", issued)
                self.assertIn("python3 scripts/agents/cruise.py watch", issued)
                self.assertIn("python3 scripts/agents/cruise.py stopping", issued)
                for each in sorted(issued) + [
                    "git status --porcelain", "git rev-parse HEAD", "git fetch origin", "git log --oneline main..HEAD",
                    "git diff --stat", "git checkout -b slice/S01", "git switch main", "git add -A",
                    "git commit -m 'S01: the posting adapter'", "git merge --no-ff slice/S01", "git push origin main",
                    "git push --force-with-lease=refs/heads/slice/S01: origin HEAD:refs/heads/slice/S01",
                ]:
                    self.assertTrue(allows(rules, each), f"{language}: {each} is not allowed by {rules}")
                # A rule is a prefix, so a `--force` written after the remote is not caught; the flag first is.
                for never in ("git push --force origin main", "git push -f origin main", "git reset --hard HEAD~1",
                              "git clean -fdx", "rm -rf apps"):
                    self.assertFalse(allows(rules, never), f"{language}: {never} is allowed")
                self.assertEqual("Bash(python3 *)" in rules["allow"], language == "python")

    def test_status_and_stop_are_commands_beside_the_seat_and_every_seat_command_repeats_its_output(self) -> None:
        """A person beside a run types `/cruise-status` and `/cruise-stop` rather than remembering the script's
        verbs, and each — the watch seat included — tells the session to put what the command printed into its
        reply unchanged, because a harness folds a command's output and the words have to reach the person."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "seat", "standard", "python")
            verbatim = ("Put every line it printed in your reply, unchanged, in a fenced block, before anything else: "
                        "the harness folds a command's output, so what it said reaches a person only through your "
                        "reply.")
            status = (repo / "commands/cruise-status.md").read_text()
            self.assertIn("description: Say whether a /cruise runner is running, how the last iteration ended, whether "
                          "it is parked and why, and show the tail of its feed", status)
            self.assertIn("python3 scripts/agents/cruise.py status\ntail -n ${ARGUMENTS:-40} .specify/cruise-run.log",
                          status)
            self.assertIn(verbatim, status)
            self.assertIn("`python3 scripts/agents/cruise.py denials` lists those", status)
            stop = (repo / "commands/cruise-stop.md").read_text()
            self.assertIn("description: End a /cruise run after the iteration in flight, or at once with `now`", stop)
            self.assertIn('python3 scripts/agents/cruise.py stop $(test "$ARGUMENTS" = now && echo --now)', stop)
            self.assertIn(verbatim, stop)
            self.assertIn("`rm .specify/cruise.stop` when they want one", stop)
            self.assertIn("`make cruise-stop` is the same\nfrom a terminal, `CRUISE_FLAGS=--now` for the immediate "
                          "form", stop)
            cruise = (repo / "commands/cruise.md").read_text()
            self.assertIn("**Put every line it printed in your reply, unchanged, in a\nfenced block, before anything "
                          "else** — the harness folds a command's output, so the feed reaches a person only\nthrough "
                          "your reply", cruise)
            page = (repo / "docs/skills-and-commands.md").read_text()
            self.assertIn("- `/cruise-settings` — `commands/cruise-settings.md`\n- `/cruise-status` — "
                          "`commands/cruise-status.md`\n- `/cruise-stop` — `commands/cruise-stop.md`", page)
