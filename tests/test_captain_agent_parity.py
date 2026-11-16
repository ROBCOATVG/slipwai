"""Layer 2: a stand-in captain agent that gives the orders today's rules would changes nothing.

The captain suites are run twice, side by side, unchanged: once on the program alone, once with a stand-in
captain agent (`fixtures/captain_stand_in.py`, named in `SLIPWAI_CAPTAIN`) that reads each event and gives,
through `orders.py`, exactly the order the event says the fixed rule would. `captain_fixture` records each
case's deck lines. The two runs must leave, in every case, the same order of `claimed` lines in each stream —
which slice the captain started when — and the same count of every kind of line for each slice, so a retry
that was one and became two, or a start that came in another order, is seen. (The order of two siblings'
lines beside each other is not compared: slices running abreast are threads, and which writes first is the
scheduler's, agent or not.) And the stand-in must have been asked, every event closed by its own orders, or
the comparison would prove nothing.

The whole of it runs the six captain suites twice over, about eight minutes, so it is `make parity`, which
`make verify` runs. The default suite keeps one fast case: the choosing and the ordering cases alone.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import checkout_packages  # noqa: F401

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SUITES = ("test_captain", "test_captain_abreast", "test_captain_gate", "test_captain_log", "test_captain_stop",
          "test_captain_watch")
FAST = ("test_captain.ChoosingTest", "test_captain_abreast.OrderTest", "test_captain_gate.GateTest")
STAND_IN = HERE / "fixtures" / "captain_stand_in.py"


def suites(record: Path, names: tuple[str, ...], **env: str) -> subprocess.Popen:
    clean = {key: value for key, value in os.environ.items()
             if key not in ("SLIPWAI_CAPTAIN", "SLIPWAI_SAIL", "SLIPWAI_ACP", "STAND_IN_CAPTAIN")}
    path = os.pathsep.join([str(ROOT / "src"), str(ROOT / ".python-tools"), str(HERE)])
    return subprocess.Popen([sys.executable, "-m", "unittest", *names], cwd=ROOT, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            env={**clean, "PYTHONPATH": path, "SLIPWAI_TEST_RECORD": str(record), **env})


def read(record: Path) -> dict[str, dict]:
    return {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in sorted(record.glob("*.json"))}


def shape(decks: dict[str, list[list[str]]]) -> dict[str, object]:
    """What is compared of one case's decks: each stream's `claimed` lines in order, and each slice's count of
    every kind of line."""
    held: dict[str, object] = {}
    for deck, lines in decks.items():
        held[f"{deck} claimed"] = [slice_id for kind, slice_id in lines if kind == "claimed"]
        held[f"{deck} counts"] = sorted(Counter((slice_id, kind) for kind, slice_id in lines).items())
    return held


class ParityTest(unittest.TestCase):
    def both_ways(self, names: tuple[str, ...]) -> None:
        folder = Path(tempfile.mkdtemp())
        alone, agent = folder / "alone", folder / "agent"
        runs = [suites(alone, names), suites(agent, names, SLIPWAI_CAPTAIN=f"{sys.executable} {STAND_IN}",
                                             STAND_IN_CAPTAIN="today")]
        said = [run.communicate(timeout=1800)[0] for run in runs]
        for run, out in zip(runs, said, strict=True):
            self.assertEqual(run.returncode, 0, out[-4000:])
        plain, standing_in = read(alone), read(agent)
        self.assertEqual(sorted(plain), sorted(standing_in), "the same cases ran both ways")
        differ = [case for case in plain if shape(plain[case]["decks"]) != shape(standing_in[case]["decks"])]
        self.assertEqual(differ, [], "\n".join(f"{case}:\n  alone {shape(plain[case]['decks'])}\n  agent "
                                               f"{shape(standing_in[case]['decks'])}" for case in differ))
        closed = [by for case in standing_in.values() for by in case["closed"]]
        self.assertTrue(closed, "the stand-in was never woken, so nothing was compared")
        self.assertEqual(set(closed), {"captain"}, "every event the stand-in was woken for, closed by its orders")
        self.assertEqual([by for case in plain.values() for by in case["closed"]], [], "alone, nothing is asked")

    def test_a_stand_in_making_today_s_choices_chooses_and_orders_as_the_program_did(self) -> None:
        self.both_ways(FAST)

    @unittest.skipUnless(os.environ.get("SLIPWAI_PARITY"), "the whole comparison is `make parity`, which verify runs")
    def test_a_stand_in_that_makes_today_s_choices_leaves_the_same_deck_lines(self) -> None:
        self.both_ways(SUITES)


if __name__ == "__main__":
    unittest.main()
