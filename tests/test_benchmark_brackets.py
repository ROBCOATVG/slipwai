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


def dead(pid: int, within: float = 5.0) -> bool:
    """Whether a process has ended — gone, or a zombie nobody has reaped yet, which is what a killed child becomes
    in a container whose pid 1 reaps nothing (the CI job's), and which still answers a signal-0 probe."""
    deadline = time.monotonic() + within
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        try:
            state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
        except OSError:
            return True
        if state == "Z":
            return True
        if time.monotonic() > deadline:
            return False
        time.sleep(0.05)


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

    def test_a_left_open_entry_is_cut_off_by_the_next_start_with_its_tokens_read_from_the_transcript(self) -> None:
        """A run was stopped mid-implement; the next iteration's `start implement` stacked a second entry on the
        first and only said "left open", `end` closed the newer one, and an hour and twenty minutes of work stayed
        open for good. Now `start` cuts off what its record still has open — and the cut-off reads the dead
        session's transcript from the files the cursor named, so those tokens still count."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "leftopen", "standard", "python")
            home = Path(directory) / "home"
            transcript = home / ".claude/projects/-x-leftopen" / f"{SESSION}.jsonl"
            transcript.parent.mkdir(parents=True)
            subagents = transcript.parent / SESSION / "subagents"
            subagents.mkdir(parents=True)
            transcript.write_text("")
            installed(repo, "claude")
            slice_ = "specs/shop/slices/A1"
            (repo / slice_).mkdir(parents=True)
            commit(repo, "the slice begins")
            first = clean(HOME=str(home), CLAUDE_CODE_SESSION_ID=SESSION)
            self.assertEqual(bench(repo, "start", slice_, "implement", env=first).returncode, 0)
            with transcript.open("a") as handle:
                handle.write(turn("r1", "claude-fable-5-1", (10, 100, 0, 0)))
            (subagents / "agent-impl.jsonl").write_text(turn("r2", "claude-sonnet-5", (2, 20, 0, 0), "drive-implement"))
            time.sleep(1.05)
            # The session is gone; the next one has no transcript of its own yet and starts the next stage.
            later = clean(HOME=str(home), CLAUDE_CODE_SESSION_ID="next-session")
            started = bench(repo, "start", slice_, "converge", env=later)
            self.assertEqual(started.returncode, 0, started.stderr)
            self.assertIn("benchmark: A1 implement: cut off — a new `converge` entry started while it was open",
                          started.stdout)
            self.assertNotIn("left open", started.stdout)
            implement, converge = record(repo, slice_)["stages"]
            self.assertEqual(implement["cut_off"], "a new `converge` entry started while it was open")
            self.assertGreaterEqual(implement["seconds"], 1)
            self.assertEqual(tokens(implement, "host"), {"claude-fable-5-1": {"input": 10, "output": 100}})
            self.assertEqual(tokens(implement, "subagents"), {"claude-sonnet-5": {"input": 2, "output": 20}})
            self.assertEqual((implement["agents"], implement["delegated"], implement["signals"]),
                             (["drive-implement"], True, {}))
            self.assertIn("read after the session that opened the entry had ended", implement["usage"]["read"])
            self.assertNotIn("ended", converge)
            self.assertEqual(bench(repo, "end", slice_, "converge", env=later).returncode, 0)
            self.assertEqual(bench(repo, "check", env=later).returncode, 0)
            self.assertIn("A1 implement: cut off — a new `converge` entry started while it was open; its wall is real, "
                          "its signals were never reported", bench(repo, env=later).stdout)
            note = bench(repo, env=later).stdout.split("A1 implement: cut off")[1].split("\n")[0]
            self.assertNotIn("tokens unknown", note)

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
            self.assertTrue(dead(int(child.read_text())), "the session's background process outlived the iteration")

    def test_the_gate_warns_of_an_open_entry_a_done_slice_without_a_record_and_a_feature_without_one(self) -> None:
        """`check-benchmark` used to run the script's self-test and nothing about the project, so a slice was
        delivered with no record at all. Now it reads what the ladder calls done — a register row, or
        `status: implemented` in the event model — and says of each done slice without a closed record, every
        record with an entry open, and a feature with no record above the slice loop. It says so as a warning and
        never fails `verify`: a bracket can only be taken at the time, so a slice finished without one — every
        slice of a project that migrated across this check — could never be made to pass honestly."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "gate", "standard", "python")
            env = clean(HOME=directory)

            def findings() -> list[str]:
                result = bench(repo, "check", env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                return [line.removeprefix("check-benchmark: warning: ") for line in result.stderr.splitlines()]

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
            # The model is the whole project's: a slice counts for the feature its `spec`/`gwt` names, or the one
            # holding its folder, and one no feature holds is said once rather than charged to every feature.
            (repo / "specs/other/slices").mkdir(parents=True)
            (repo / "docs/event-model/model.yaml").write_text(
                "version: 1\nslices:\n  - id: S2\n    name: Two\n    status: implemented\n"
                "    spec: specs/shop/spec.md\n"
                "  - id: S3\n    name: Three\n    status: planned\n"
                "  - id: S12Q\n    name: Nowhere\n    status: implemented\n")
            self.assertEqual(findings(), [
                "docs/event-model/model.yaml: S12Q is implemented but names no feature (`spec`/`gwt` under "
                "specs/<feature>/) and has no specs/*/slices/ folder, so no feature's record is asked for it",
                "specs/shop/slices/S2 is done but has no benchmark.json: no stage of it was "
                "bracketed (commands/drive.md, *What each stage costs*)"])
            made = subprocess.run(["make", "check-benchmark"], cwd=repo, env=env, text=True, capture_output=True)
            self.assertEqual(made.returncode, 0, made.stderr)
            self.assertIn("check-benchmark: warning: specs/shop/slices/S2 is done but has no benchmark.json",
                          made.stderr)
            self.assertIn("check-benchmark: 2 warning(s) above — what was not measured stays unmeasured; not failing "
                          "verify", made.stdout)
