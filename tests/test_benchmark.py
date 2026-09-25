"""Every stage of `/drive` records what it cost and how it did, read from the harness's transcript where there
is one and said to be unknown where there is not."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from support import FactoryTestCase
from test_adopt import repository, slipwai

from slipwai.assets import TOOLKIT_ROOT
from slipwai.project.benchmark import SIGNALS

REGISTRY = TOOLKIT_ROOT / "scripts/agents/registry.json"
SESSION = "sess-1"
CLAUDE_FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def clean(**extra: str) -> dict[str, str]:
    """The environment with the running harness's own session removed, so a test names the one it means."""
    env = {key: value for key, value in os.environ.items() if not key.startswith(("CLAUDE", "CODEX"))}
    env.update(extra)
    return env


def bench(repo: Path, *arguments: str, env: dict[str, str], delivery: str = ".") -> subprocess.CompletedProcess:
    return subprocess.run(["python3", str(repo / delivery / "scripts/agents/benchmark.py"), *arguments],
                          cwd=repo, env=env, text=True, capture_output=True)


def assistant(request: str, model: str, tokens: tuple[int, int, int, int], blocks: int = 2) -> str:
    """What Claude Code writes for one response: one line per content block, the same usage on each."""
    usage = dict(zip(CLAUDE_FIELDS, tokens, strict=True))
    line = json.dumps({"type": "assistant", "requestId": request, "message": {"model": model, "usage": usage}})
    return (line + "\n") * blocks


def rollout_line(kind: str, payload: dict) -> str:
    """One line of a Codex rollout: a timestamp, the item's `type`, and its payload."""
    return json.dumps({"timestamp": "t", "type": kind, "payload": payload}) + "\n"


def token_count(total: dict) -> str:
    info = {"total_token_usage": total, "last_token_usage": total, "model_context_window": None}
    return rollout_line("event_msg", {"type": "token_count", "info": info})


def installed(repo: Path, *keys: str) -> None:
    (repo / ".specify/integration.json").write_text(json.dumps({"installed_integrations": list(keys)}))


def record(repo: Path, directory: str) -> dict:
    return json.loads((repo / directory / "benchmark.json").read_text())


def commit(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", message],
                   cwd=repo, check=True, capture_output=True)


class BenchmarkTest(FactoryTestCase):
    def test_the_ladder_records_every_stage_and_the_project_ships_the_script_target_and_command(self) -> None:
        """The section sits after *Who runs each stage* and before the slice loop; it asks each stage for one
        signal and reads everything else. The record is beside the slice's artifacts, the aggregate is a Makefile
        target, the overview is a command, and the registry says per harness where the tokens are."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "shape", "event-modelling", "typescript")
            drive = (repo / "commands/drive.md").read_text()
            self.assertLess(drive.index("## Who runs each stage"), drive.index("## What each stage costs"))
            self.assertLess(drive.index("## What each stage costs"), drive.index("## Once inside the slice"))
            section = drive.split("## What each stage costs")[1].split("## Once inside the slice")[0]
            self.assertIn("python3 scripts/agents/benchmark.py start specs/<feature>/slices/<id> implement", section)
            self.assertIn("python3 scripts/agents/benchmark.py end specs/<feature>/slices/<id> implement "
                          "verify_failures=1", section)
            self.assertIn("python3 scripts/agents/benchmark.py close specs/<feature>/slices/<id>", section)
            for stage, takes in SIGNALS:
                self.assertIn(f"| `{stage}` | {takes} |", section)
            self.assertIn("go to `specs/<feature>/benchmark.json`", section)
            self.assertIn("A delegated stage is started and ended here, by the host", section)
            self.assertIn("never fill one\nin", section)
            self.assertIn("Nothing on either goes on the\ndemo board", section)
            self.assertIn("`make\nbenchmark` prints the same aggregate", section)

            makefile = (repo / "Makefile").read_text()
            self.assertIn("verify: check-python lint typecheck check-imports check-migrations check-slice-scope "
                          "check-extensions check-agents "
                          "check-speckit check-codegraph check-ux-gates check-constitution check-benchmark "
                          "check-decisions test check-model",
                          makefile)
            self.assertIn(
                "check-benchmark: ## Fail when the benchmark script's own behaviour regresses; warn of an entry "
                "left open or a done slice with no record", makefile,
            )
            self.assertTrue((repo / "scripts/test_benchmark.py").is_file())
            checked = subprocess.run(["make", "check-benchmark"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertIn("benchmark: ## Show what each slice cost and how each stage of /drive did", makefile)
            self.assertIn("\tpython3 scripts/agents/benchmark.py\n", makefile)
            gates = (repo / "docs/gates.md").read_text()
            self.assertIn("mutation, model, benchmark and dependency-audit targets", gates)

            command = (repo / "commands/benchmark.md").read_text()
            self.assertIn("python3 scripts/agents/benchmark.py overview $ARGUMENTS", command)
            self.assertIn("`specs/<feature>/benchmark.md`", command)
            for heading in ("Where the cost sits", "What moved", "Whether the split paid", "What is unknown"):
                self.assertIn(f"**{heading}**", command)
            self.assertIn("An unknown is never estimated", command)
            listed = (repo / "docs/skills-and-commands.md").read_text()
            self.assertIn("- `/model-delegation-settings` — `commands/model-delegation-settings.md`\n"
                          "- `/drive-settings` — `commands/drive-settings.md`\n"
                          "- `/benchmark` — `commands/benchmark.md`", listed)
            self.assertIn("Under `usage`, the registry also says", (repo / "docs/agent-harnesses.md").read_text())

            registry = json.loads(REGISTRY.read_text())
            verified = {}
            for harness in registry["harnesses"]:
                self.assertIn("usage", harness, harness["key"])
                if harness["usage"] is not None:
                    verified[harness["key"]] = harness["usage"]
                    for field in ("where", "what", "env", "source"):
                        self.assertTrue(harness["usage"].get(field), f"{harness['key']}: {field}")
                    self.assertRegex(harness["usage"]["source"], r"read \d{4}-\d{2}-\d{2}$")
            self.assertEqual({"claude": "CLAUDE_CODE_SESSION_ID", "codex": "CODEX_THREAD_ID"},
                             {key: usage["env"] for key, usage in verified.items()})
            self.assertIn("`usage` is the factory's too", registry["_generated"])

    def test_a_stage_is_costed_from_the_transcript_and_the_record_derives_the_rest(self) -> None:
        """Tokens by model from the session the harness named, counted once per request although the transcript
        writes one line per content block; a sub-agent's transcript makes the stage delegated. Converge's
        appended tasks, the gaps before and after converge, a stage re-entered after implementation and the shape
        are derived, never asked. What the stage alone knows is passed in words and checked."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "cost", "standard", "python")
            home = Path(directory) / "home"
            transcript = home / ".claude/projects/-x-cost" / f"{SESSION}.jsonl"
            transcript.parent.mkdir(parents=True)
            subagents = transcript.parent / SESSION / "subagents"
            subagents.mkdir(parents=True)
            env = clean(HOME=str(home), CLAUDE_CODE_SESSION_ID=SESSION)
            installed(repo, "claude")
            slice_ = "specs/shop/slices/S1"
            (repo / "specs/shop/slices/S1").mkdir(parents=True)
            # Under the record from the day it is planned (the canonical slot is a link, and ignored).
            (repo / "specs/shop/slices/S1/tasks.md").write_text("# Tasks\n- [ ] T1\n- [ ] T2\n- [x] T0\n")
            commit(repo, "the slice begins")

            transcript.write_text(assistant("r0", "claude-fable-5-1", (5, 5, 0, 0)))  # before the stage: not counted
            started = bench(repo, "start", slice_, "implement", env=env)
            self.assertEqual(started.returncode, 0, started.stderr)
            self.assertIn("implement started (specs/shop/slices/S1/benchmark.json; usage from claude)", started.stdout)
            time.sleep(1.05)
            with transcript.open("a") as handle:
                handle.write(assistant("r1", "claude-fable-5-1", (10, 100, 1000, 200)))
                handle.write(assistant("r2", "claude-fable-5-1", (20, 200, 0, 0), blocks=3))
                handle.write(json.dumps({"type": "user", "message": {"content": "x"}}) + "\n")
            (subagents / "agent-a1.jsonl").write_text(assistant("r3", "claude-sonnet-4-5", (7, 70, 300, 0)))
            ended = bench(repo, "end", slice_, "implement", "verify_failures=1", env=env)
            self.assertEqual(ended.returncode, 0, ended.stderr)
            # Wall time is real: a slow runner ticks a second between start and end, so its shape is what is held.
            self.assertRegex(ended.stdout, r"implement: \d+s · in 1\.5k · out 370 · claude-fable-5-1, "
                                           r"claude-sonnet-4-5, delegated")
            entry = record(repo, slice_)["stages"][0]
            self.assertEqual(entry["usage"]["host"], {"claude-fable-5-1": {
                "input": 30, "output": 300, "cache_read": 1000, "cache_creation": 200}})
            self.assertEqual(entry["usage"]["subagents"], {"claude-sonnet-4-5": {
                "input": 7, "output": 70, "cache_read": 300, "cache_creation": 0}})
            self.assertTrue(entry["delegated"])
            self.assertTrue(entry["planned"].startswith("implement: fast → sonnet"))
            self.assertEqual(entry["signals"], {"verify_failures": 1})
            self.assertNotIn("cursor", entry)

            bench(repo, "start", slice_, "converge", env=env)
            (repo / "specs/shop/slices/S1/tasks.md").write_text(
                "# Tasks\n- [x] T1\n- [x] T2\n- [x] T0\n- [ ] T3\n- [ ] T4\n"
            )
            self.assertEqual(bench(repo, "end", slice_, "converge", env=env).returncode, 0)
            for stage, signal in (("gaps", "gaps=2"), ("demo", "outcome=accepted"), ("example-map", "note=feedback"),
                                  ("mutation", "mutation_score=87%")):
                bench(repo, "start", slice_, stage, env=env)
                self.assertEqual(bench(repo, "end", slice_, stage, signal, env=env).returncode, 0, stage)
            for arguments, refusal in (
                (("end", slice_, "mutation", "bogus=1"), "`bogus` is not a signal; known: gaps, findings"),
                (("end", slice_, "demo", "outcome=maybe"), "outcome is one of accepted, behaviour, implementation"),
                (("end", slice_, "plan"), "no open `plan` entry"),
                (("start", slice_, "plan", "gaps=1"), "start takes no signals"),
                (("end", slice_, "gaps", "gaps=two"), "gaps takes a count"),
            ):
                refused = bench(repo, *arguments, env=env)
                self.assertEqual(refused.returncode, 1, arguments)
                self.assertIn(refusal, refused.stderr, arguments)

            (repo / "new.py").write_text("x = 1\ny = 2\n")
            closed = bench(repo, "close", slice_, env=env)
            self.assertEqual(closed.returncode, 0, closed.stderr)
            # Two lines of tasks.md flipped and two appended, one file nobody has added yet: all of it is the shape.
            self.assertIn("S1 closed — 5 tasks, 2 files, +6/-2", closed.stdout)
            self.assertIn("specs/shop/benchmark.md redrawn", closed.stdout)
            self.assertIn("S1: re-entered example-map after implementation", closed.stdout)
            shape = record(repo, slice_)["shape"]
            self.assertEqual((shape["tasks"], shape["files"], shape["added"], shape["removed"]), (5, 2, 6, 2))

            aggregate = bench(repo, env=env)
            self.assertEqual(aggregate.returncode, 0, aggregate.stderr)
            row = next(line for line in aggregate.stdout.splitlines() if line.strip().startswith("S1 "))
            self.assertRegex(row, r"^\s+S1\s+—\s+\d+s\+\s+1\.5k \(\+5 unread\)\s+370\s+")
            self.assertRegex(row, r"\s+1\s+2\s+0/2\s+87%\s+0\s+accepted\s+1\s+1\s+5\s+2\s+\+6/-2\s*$")
            self.assertIn("tokens are not prices", aggregate.stdout)
            summary = json.loads(bench(repo, "--json", env=env).stdout)[0]
            derived = (summary["converge_passes"], summary["tasks_appended"], summary["gaps"], summary["rework"])
            self.assertEqual(derived, (1, 2, {"before": 0, "after": 2}, ["example-map"]))
            page = (repo / "specs/shop/benchmark.md").read_text()
            self.assertIn("# Benchmark — shop", page)
            rest = (
                " | 1.5k (+5 unread) | 370 | claude-fable-5-1, claude-sonnet-4-5 | 1 | 1 | 2 | 0/2 | 87% | "
                "0 | accepted | 1 | 1 | 5 | 2 | +6/-2 |"
            )
            self.assertRegex(page, re.escape("| S1 | — | ") + r"\d+s\+" + re.escape(rest))
            self.assertIn("| implement | ", page)
            self.assertIn("| yes | verify_failures=1 |", page)
            self.assertIn("| demo | ", page)
            self.assertIn("| unbracketed | unknown | unknown |", page)
            self.assertIn("not bracketed around its work", page)
            self.assertIn("- S1: re-entered example-map after implementation", page)
            self.assertIn("## Reading these numbers", page)
            made = subprocess.run(["make", "benchmark"], cwd=repo, env=env, text=True, capture_output=True)
            self.assertEqual(made.returncode, 0, made.stderr)
            self.assertIn("shop — 1 slice(s) recorded", made.stdout)
            missing = bench(repo, "overview", "nope", env=env)
            self.assertEqual(missing.returncode, 1)
            self.assertIn("no record under specs/nope/; known: shop", missing.stderr)

    def test_usage_is_unknown_with_the_reason_wherever_no_transcript_can_be_read(self) -> None:
        """Four roads to null, each a different sentence: no harness at all, a harness the registry records no
        transcript for, a harness that can be read but did not name this session, and a session that changed
        between start and end. Codex is read from its rollout — per response where the rollout records one, as
        the difference between two totals otherwise."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "unknown", "standard", "go")
            home = Path(directory) / "home"
            (repo / "specs/f").mkdir(parents=True)

            def costed(stage: str, env: dict[str, str]) -> dict:
                bench(repo, "start", "specs/f", stage, env=env)
                ended = bench(repo, "end", "specs/f", stage, env=env)
                self.assertEqual(ended.returncode, 0, ended.stderr)
                return next(entry for entry in reversed(record(repo, "specs/f")["stages"]) if entry["stage"] == stage)

            self.assertIn("no harness installed", costed("split", clean(HOME=str(home)))["usage"]["reason"])
            installed(repo, "amp")
            self.assertEqual(costed("plan", clean(HOME=str(home)))["usage"],
                             {"source": None, "reason": "the registry records no transcript to read for Amp"})
            installed(repo, "claude")
            self.assertIn("Claude Code is installed but did not name this session in the environment",
                          costed("tasks", clean(HOME=str(home)))["usage"]["reason"])
            ghost = clean(HOME=str(home), CLAUDE_CODE_SESSION_ID="ghost")
            self.assertIn("has no transcript under ~/.claude/projects", costed("gaps", ghost)["usage"]["reason"])
            transcript = home / ".claude/projects/-x" / f"{SESSION}.jsonl"
            transcript.parent.mkdir(parents=True)
            transcript.write_text("")
            bench(repo, "start", "specs/f", "demo", env=clean(HOME=str(home), CLAUDE_CODE_SESSION_ID=SESSION))
            other = clean(HOME=str(home), CLAUDE_CODE_SESSION_ID="other")
            bench(repo, "end", "specs/f", "demo", "model=opus", env=other)
            demo = record(repo, "specs/f")["stages"][-1]
            self.assertEqual(demo["usage"]["reason"], f"the session changed since the stage started ({SESSION})")
            self.assertEqual(demo["ran"], ["opus"])

            codex_home = Path(directory) / "codex"
            rollout = codex_home / "sessions/2026/09/09/rollout-2026-09-09T10-00-00-thread-1.jsonl"
            rollout.parent.mkdir(parents=True)
            usage = {"input_tokens": 100, "cached_input_tokens": 50, "cache_write_input_tokens": 0, "output_tokens": 10,
                     "reasoning_output_tokens": 3, "total_tokens": 160}
            rollout.write_text(token_count(usage))
            installed(repo, "codex")
            env = clean(HOME=str(home), CODEX_HOME=str(codex_home), CODEX_THREAD_ID="thread-1")
            bench(repo, "start", "specs/f", "implement", env=env)
            time.sleep(1.05)
            with rollout.open("a") as handle:
                handle.write(token_count(dict(usage, input_tokens=400, cached_input_tokens=250, output_tokens=60)))
            bench(repo, "end", "specs/f", "implement", env=env)
            implement = record(repo, "specs/f")["stages"][-1]
            self.assertEqual(implement["usage"]["read"], "the difference between token_count totals")
            self.assertEqual(implement["usage"]["host"], {"unknown": {
                "input": 300, "output": 50, "cache_read": 200, "cache_creation": 0}})
            bench(repo, "start", "specs/f", "converge", env=env)
            time.sleep(1.05)
            with rollout.open("a") as handle:
                handle.write(rollout_line("turn_context", {"model": "gpt-5-codex"}))
                for response in ("a", "a", "b"):
                    handle.write(rollout_line("token_usage_record", {"response_id": response, "usage": usage,
                                                                     "turn_token_usage": usage,
                                                                     "thread_token_usage": usage}))
            bench(repo, "end", "specs/f", "converge", env=env)
            converge = record(repo, "specs/f")["stages"][-1]
            self.assertEqual(converge["usage"]["read"], "token_usage_record lines, one per response")
            self.assertEqual(converge["usage"]["host"], {"gpt-5-codex": {
                "input": 200, "output": 20, "cache_read": 100, "cache_creation": 0}})
            self.assertEqual(converge["ran"], ["gpt-5-codex"])
            aggregate = bench(repo, env=env).stdout
            self.assertIn("(feature)", aggregate)
            # Five stages never got a transcript (split/plan/tasks/gaps/demo). implement and converge
            # did — they are not unread once bracketed, and must not be counted just because start/end
            # sometimes share a clock second.
            self.assertIn("(+5 unread)", aggregate)
            self.assertIn("(feature) split: tokens unknown — no harness installed", aggregate)

    def test_the_gate_says_one_line_about_a_project_with_no_slice_recorded(self) -> None:
        """`check-benchmark` runs inside `make verify`, where a passing gate is silent about its work.

        It used to print `benchmark: demo: unbracketed · tokens unknown — stage was not bracketed around
        its work · model unknown` — the summary line for a record in the test's own temporary directory,
        leaking through a suite that captured stderr and not stdout. In a fresh project, whose first
        `make verify` is the first thing anyone runs, that reads as a finding about the project.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "quiet-gate", "event-modelling", "typescript")
            result = subprocess.run(
                ["make", "check-benchmark"], cwd=repo, text=True, capture_output=True, env=clean()
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            said = [line for line in result.stdout.splitlines() if line.startswith("benchmark:")]
            self.assertEqual([], said, f"the gate printed a benchmark line:\n{result.stdout}")
            self.assertIn("check-benchmark: 2 boundary and rendering checks pass", result.stdout)

    def test_a_moved_layout_records_from_the_delivery_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": '{"name": "shop", "private": true, "scripts": {"test": "node --test"}}\n',
                "package-lock.json": '{"name": "shop", "lockfileVersion": 3}\n',
                "test/a.test.js": "test('a', () => {});\n",
            })
            result = slipwai(repo, "adopt", "--yes")
            self.assertEqual(result.returncode, 0, result.stderr)
            drive = (repo / "delivery/commands/drive.md").read_text()
            self.assertIn("python3 delivery/scripts/agents/benchmark.py start specs/<feature>/slices/<id> implement",
                          drive)
            self.assertIn("`make -f delivery/Makefile\nbenchmark` prints", drive)
            env = clean(HOME=directory)
            started = bench(repo, "start", "specs/f/slices/S1", "plan", env=env, delivery="delivery")
            self.assertEqual(started.returncode, 0, started.stderr)
            self.assertTrue((repo / "specs/f/slices/S1/benchmark.json").is_file())
            ended = bench(repo, "end", "specs/f/slices/S1", "plan", env=env, delivery="delivery")
            self.assertEqual(ended.returncode, 0, ended.stderr)
            self.assertEqual(record(repo, "specs/f/slices/S1")["slice"], "S1")
