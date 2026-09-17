#!/usr/bin/env python3
"""Regression checks for benchmark stage boundaries and rendering.

Everything here drives the real script over a real record in a temporary directory. The one collaborator a
test cannot let be itself is the clock — a stage that started and ended in the same moment is exactly what
is under test — so `end` takes it as a parameter and the test passes a two-line stand-in. No mocking
framework: this repository writes its own fakes at a seam, and `scripts/agents/benchmark.py` carries the
seam so that this file does not have to replace the module to use it.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("agents") / "benchmark.py"
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("benchmark", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


class BenchmarkRenderingTest(unittest.TestCase):
    def entry(self, seconds: int) -> dict:
        return {
            "stage": "demo",
            "started": "2026-09-11T12:00:00Z",
            "ended": "2026-09-11T12:00:00Z",
            "seconds": seconds,
            "usage": {"source": "test", "session": "one", "host": {}, "subagents": {}},
            "ran": ["test-model"],
            "delegated": False,
            "tasks": {"start": None, "end": None},
            "signals": {},
        }

    def test_zero_second_stage_is_unbracketed_and_makes_total_a_floor(self) -> None:
        record = {"feature": "shop", "slice": "S1", "stages": [self.entry(0)]}
        summary = benchmark.summarise(record)

        self.assertEqual(benchmark.stage_wall(record["stages"][0]), "unbracketed")
        self.assertEqual(benchmark.summary_wall(summary), "0s+")
        self.assertEqual(benchmark.stage_rows(record)[0][2:5], ["unbracketed", "unknown", "unknown"])
        self.assertIn(
            "S1 demo: not bracketed around its work — start and end were called in the same moment, "
            "so this stage's wall and tokens are missing, not zero.",
            benchmark.notes([summary], [record]),
        )

    def test_end_warns_when_start_and_end_are_the_same_moment(self) -> None:
        moment = "2026-09-11T12:00:00Z"
        open_entry = {
            "stage": "demo",
            "started": moment,
            "planned": "demo: strong → host",
            "tasks": {"start": None},
            # No harness named this session, so `usage_since` reports the reason and reads no transcript.
            "cursor": {"source": None, "reason": "test"},
        }
        with tempfile.TemporaryDirectory() as directory:
            slice_ = Path(directory)
            benchmark.save(slice_, {"feature": "shop", "slice": "S1", "stages": [open_entry]})
            stderr, stdout = io.StringIO(), io.StringIO()

            # Both streams, and stdout especially: this runs inside `make verify` as `check-benchmark`,
            # and `end` prints the stage's summary line for whoever ran it from `/drive`. Left uncaptured,
            # a gate that passed printed `benchmark: demo: unbracketed · tokens unknown …` about a record
            # in a temporary directory, which reads in a fresh project like a finding about the project.
            # A gate is silent on success; what the line says is asserted here instead of leaked.
            with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
                benchmark.end(slice_, "demo", [], clock=lambda: moment)

            closed = benchmark.load(slice_)["stages"][0]
            self.assertIn("warning: demo was not bracketed around its work", stderr.getvalue())
            self.assertEqual(
                "benchmark: demo: unbracketed · tokens unknown — stage was not bracketed around its "
                "work · model unknown\n",
                stdout.getvalue(),
            )
            self.assertTrue(benchmark.is_unbracketed(closed))
            self.assertEqual(closed["usage"], {"source": None, "reason": "test"})


def main() -> int:
    """`make check-benchmark`, in the shape every other gate script here has: one line on success, the
    runner's whole report on failure. A gate that passes is silent about what it looked at."""
    report = io.StringIO()
    result = unittest.TextTestRunner(stream=report, verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromName("__main__")
    )
    if not result.wasSuccessful():
        print(report.getvalue(), file=sys.stderr)
        return 1
    print(f"check-benchmark: {result.testsRun} boundary and rendering checks pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
