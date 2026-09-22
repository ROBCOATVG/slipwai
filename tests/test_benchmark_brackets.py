"""Three holes a real run's records showed in the benchmark: two brackets open at once both counted the same delegate
lines; entries opened by an iteration that was then stopped stayed open for good; and a slice was delivered with no
record through a gate that ran only the script's self-test. Each is held here against fabricated transcripts, a fake
harness, and a register.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from support import FactoryTestCase
from test_benchmark import CLAUDE_FIELDS, SESSION, bench, clean, commit, installed, record
from test_cruise_runner import cruise, enable, fake_harness

from slipwai.project.cruise_record import RUNNER_LOG, RUNNER_PID


def turn(request: str, model: str, tokens: tuple[int, int, int, int], agent: str | None = None) -> str:
    """One response as Claude Code writes it, attributed to a delegate type where a sub-agent wrote it."""
    usage = dict(zip(CLAUDE_FIELDS, tokens, strict=True))
    line = {"type": "assistant", "requestId": request, "message": {"model": model, "usage": usage}}
    if agent is not None:
        line["attributionAgent"] = agent
    return json.dumps(line) + "\n"


def tokens(entry: dict, part: str) -> dict[str, dict[str, int]]:
    return {model: {key: value for key, value in usage.items() if value}
            for model, usage in entry["usage"][part].items()}


class BenchmarkBracketsTest(FactoryTestCase):
    def test_two_brackets_open_at_once_each_count_only_their_own_lines(self) -> None:
        """A skipper round opened in the feature record while a slice's implementers run: the skipper's entry
        counts its own host turns and its own delegate, not the implementers' lines written meanwhile; the
        implement entry, closed later, keeps its delegates' lines (its type owns them, whatever bracket was open)
        and leaves the skipper round's host turn and delegate to the skipper. Every record in the project is
        consulted, because the two brackets live in different files."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "overlap", "standard", "python")
            home = Path(directory) / "home"
            transcript = home / ".claude/projects/-x-overlap" / f"{SESSION}.jsonl"
            transcript.parent.mkdir(parents=True)
            subagents = transcript.parent / SESSION / "subagents"
            subagents.mkdir(parents=True)
            env = clean(HOME=str(home), CLAUDE_CODE_SESSION_ID=SESSION)
            installed(repo, "claude")
            slice_, feature = "specs/shop/slices/A1", "specs/shop"
            (repo / slice_).mkdir(parents=True)
            commit(repo, "the slice begins")
            transcript.write_text("")
            self.assertEqual(bench(repo, "start", slice_, "implement", env=env).returncode, 0)
            with transcript.open("a") as handle:
                handle.write(turn("r1", "claude-fable-5-1", (10, 100, 0, 0)))
            (subagents / "agent-impl.jsonl").write_text(turn("r2", "claude-sonnet-5", (2, 20, 0, 0), "drive-implement"))
            time.sleep(1.05)
            started = bench(repo, "start", feature, "skipper", env=env)
            self.assertEqual(started.returncode, 0, started.stderr)
            with transcript.open("a") as handle:
                handle.write(turn("r3", "claude-fable-5-1", (30, 300, 0, 0)))
            (subagents / "agent-skip.jsonl").write_text(turn("r4", "claude-fable-5-1", (4, 40, 0, 0), "drive-skipper"))
            with (subagents / "agent-impl.jsonl").open("a") as handle:
                handle.write(turn("r5", "claude-sonnet-5", (5, 50, 0, 0), "drive-implement"))
            ended = bench(repo, "end", feature, "skipper", env=env)
            self.assertEqual(ended.returncode, 0, ended.stderr)
            skipper = record(repo, feature)["stages"][0]
            self.assertEqual(tokens(skipper, "host"), {"claude-fable-5-1": {"input": 30, "output": 300}})
            self.assertEqual(tokens(skipper, "subagents"), {"claude-fable-5-1": {"input": 4, "output": 40}})
            self.assertEqual(skipper["agents"], ["drive-skipper"])
            self.assertIn("1 request(s) left to a bracket open at the same time", skipper["usage"]["read"])
            self.assertEqual(set(skipper["span"]), {"from", "to"})
            with transcript.open("a") as handle:
                handle.write(turn("r6", "claude-fable-5-1", (60, 600, 0, 0)))
            ended = bench(repo, "end", slice_, "implement", env=env)
            self.assertEqual(ended.returncode, 0, ended.stderr)
            implement = record(repo, slice_)["stages"][0]
            self.assertEqual(tokens(implement, "host"), {"claude-fable-5-1": {"input": 70, "output": 700}})
            self.assertEqual(tokens(implement, "subagents"), {"claude-sonnet-5": {"input": 7, "output": 70}})
            self.assertEqual(implement["agents"], ["drive-implement"])
            self.assertIn("2 request(s) left to a bracket open at the same time", implement["usage"]["read"])

    def test_the_runner_cuts_off_what_an_iteration_left_open_and_says_so(self) -> None:
        """An iteration that opens a bracket and ends without closing it — or is ended by `stop --now` — leaves
        nothing open: the runner closes the entry with the reason, no tokens and no signals, its wall real, and
        the overview's notes and the gate both read it as cut off rather than as a stage still running."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "cutoff", "standard", "python")
            enable(repo)
            (repo / "specs/f/slices/S1").mkdir(parents=True)
            opened = "python3 scripts/agents/benchmark.py start specs/f/slices/S1 implement"
            env = fake_harness(Path(directory), f'{opened}\necho "cruise: done"')
            run = cruise(repo, "run", env=env)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("benchmark: S1 implement: cut off — iteration 1 ended with the entry open", run.stdout)
            entry = record(repo, "specs/f/slices/S1")["stages"][0]
            self.assertEqual(entry["cut_off"], "iteration 1 ended with the entry open")
            self.assertEqual(entry["usage"],
                             {"source": None, "reason": "cut off — iteration 1 ended with the entry open"})
            self.assertEqual((entry["ran"], entry["agents"], entry["delegated"], entry["signals"]),
                             (None, None, False, {}))
            self.assertIn("S1 implement: cut off — iteration 1 ended with the entry open",
                          bench(repo, env=clean()).stdout)
            self.assertEqual(bench(repo, "check", env=clean()).returncode, 0)
            # Ended by a person: the runner's SIGTERM ends the session and cuts the bracket off with that reason.
            # The session starts a background process of its own, as a dev server would be; ending the iteration
            # ends that too, because the runner ends the session's whole process group and not only its shell.
            child = Path(directory) / "child-pid"
            env = fake_harness(Path(directory), 'python3 scripts/agents/benchmark.py start specs/f/slices/S1 demo\n'
                                                f'sleep 30 & echo $! > {child}\nwait\necho "cruise: continue"')
            started = cruise(repo, "start", env=env)
            self.assertEqual(started.returncode, 0, started.stderr)
            for _ in range(100):
                if "demo started" in (repo / RUNNER_LOG).read_text():
                    break
                time.sleep(0.1)
            stopped = cruise(repo, "stop", "--now", env=env)
            self.assertEqual(stopped.returncode, 0, stopped.stderr)
            for _ in range(100):
                if not (repo / RUNNER_PID).is_file():
                    break
                time.sleep(0.1)
            self.assertIn("benchmark: S1 demo: cut off — the iteration was ended by `stop --now`",
                          (repo / RUNNER_LOG).read_text())
            demo = record(repo, "specs/f/slices/S1")["stages"][1]
            self.assertEqual(demo["cut_off"], "the iteration was ended by `stop --now`")
            time.sleep(0.2)
            with self.assertRaises(ProcessLookupError, msg="the session's background process outlived the iteration"):
                os.kill(int(child.read_text()), 0)

    def test_the_gate_fails_on_an_open_entry_a_done_slice_without_a_record_and_a_feature_without_one(self) -> None:
        """`check-benchmark` used to run the script's self-test and nothing about the project, so a slice was
        delivered with no record at all. Now it reads what the ladder calls done — a register row, or
        `status: implemented` in the event model — and holds each done slice to a closed record, every record
        to nothing open, and the feature to a record above the slice loop."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "gate", "standard", "python")
            env = clean(HOME=directory)

            def findings() -> list[str]:
                result = bench(repo, "check", env=env)
                return [line.removeprefix("check-benchmark: ") for line in result.stderr.splitlines()]

            quiet = bench(repo, "check", env=env)
            self.assertEqual((quiet.returncode, quiet.stdout.strip()),
                             (0, "check-benchmark: no record and no done slice yet — nothing to hold"))
            (repo / "specs/shop/slices/S1").mkdir(parents=True)
            (repo / "specs/shop/slices/README.md").write_text("| Slice | Accepted |\n|---|---|\n| S1 | 2026-09-22 |\n")
            self.assertEqual(findings(), [
                "specs/shop/slices/S1 is done but has no benchmark.json: no stage of it was bracketed "
                "(commands/drive.md, *What each stage costs*)",
                "specs/shop/benchmark.json is missing while 1 slice(s) are done: the stages above the slice loop "
                "were not bracketed"])
            bench(repo, "start", "specs/shop/slices/S1", "implement", env=env)
            self.assertIn("specs/shop/slices/S1/benchmark.json: `implement` has been open since", findings()[0])
            bench(repo, "end", "specs/shop/slices/S1", "implement", env=env)
            self.assertEqual(findings()[0], "specs/shop/slices/S1 is done but its record was never closed — "
                                            "`python3 scripts/agents/benchmark.py close specs/shop/slices/S1`")
            bench(repo, "close", "specs/shop/slices/S1", env=env)
            self.assertEqual(findings(), ["specs/shop/benchmark.json is missing while 1 slice(s) are done: the stages "
                                          "above the slice loop were not bracketed"])
            bench(repo, "start", "specs/shop", "split", env=env)
            bench(repo, "end", "specs/shop", "split", env=env)
            held = bench(repo, "check", env=env)
            self.assertEqual((held.returncode, held.stdout.strip()),
                             (0, "check-benchmark: 2 record(s), nothing open, every done slice recorded and closed"))
            # The event profile marks a slice done in the model instead; a slice merely planned is not held.
            (repo / "docs/event-model").mkdir(parents=True)
            (repo / "docs/event-model/model.yaml").write_text(
                "version: 1\nslices:\n  - id: S2\n    name: Two\n    status: implemented\n"
                "  - id: S3\n    name: Three\n    status: planned\n")
            self.assertEqual(findings(), ["specs/shop/slices/S2 is done but has no benchmark.json: no stage of it was "
                                          "bracketed (commands/drive.md, *What each stage costs*)"])
            made = subprocess.run(["make", "check-benchmark"], cwd=repo, env=env, text=True, capture_output=True)
            self.assertEqual(made.returncode, 2)
            self.assertIn("specs/shop/slices/S2 is done but has no benchmark.json", made.stderr)
