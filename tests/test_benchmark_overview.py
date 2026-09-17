"""What `make benchmark` says about a record beyond tabulating it.

The table has carried a converge-pass count without anyone reading it: converge is append-only and
safe to repeat, so six passes look like diligence rather than like a slice that kept finding the next
sibling of the fix before. A number nothing interprets is a number nobody looks at, which is why the
overview's notes are their own suite — they are the part of the output that is an opinion.
"""
from __future__ import annotations

import json
import tempfile

from support import FactoryTestCase
from test_benchmark import bench, clean


class BenchmarkOverviewTest(FactoryTestCase):
    def test_the_overview_says_when_a_slice_kept_going_back_to_converge(self) -> None:
        """S11 took six converge passes and nineteen appended tasks; S10 took six and thirteen. The number
        was already in the table and nothing read it out, so nobody looked: converge is append-only and
        safe to repeat, which makes a high count easy to mistake for diligence. It is the cheapest signal
        there is that the slice was too large, or that each pass closed the instance it found and left the
        siblings for the next one."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "repeating", "event-modelling", "python")
            env = clean()

            def passes(slice_: str, count: int, appended: int) -> None:
                stages = [{"stage": "implement", "ended": "now", "seconds": 60, "signals": {}}]
                for index in range(count):
                    stages.append({
                        "stage": "converge", "ended": "now", "seconds": 60, "signals": {},
                        "tasks": {"start": {"unchecked": index}, "end": {"unchecked": index + appended // count}},
                    })
                path = repo / "specs/f/slices" / slice_
                path.mkdir(parents=True)
                (path / "benchmark.json").write_text(json.dumps(
                    {"feature": "f", "slice": slice_, "stages": stages}))

            passes("S10", 2, 2)
            passes("S11", 6, 18)
            aggregate = bench(repo, env=env).stdout

            self.assertIn("S11: converge ran 6 times, appending 18 task(s)", aggregate)
            self.assertIn("a slice too large, or fixes too narrow to close the class of what they found",
                          aggregate)
            # Two passes is what a slice that converged looks like: find the work, confirm it closed.
            self.assertNotIn("S10: converge ran", aggregate)
