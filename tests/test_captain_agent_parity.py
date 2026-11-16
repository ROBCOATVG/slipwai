"""Layer 2: a stand-in captain agent that gives the orders today's rules would changes nothing.

The six captain suites are run twice, side by side, unchanged: once on the program alone, once with a stand-in
captain agent (`fixtures/captain_stand_in.py`, named in `SLIPWAI_CAPTAIN`) that reads each event and gives,
through `orders.py`, exactly the order the event says the fixed rule would. `captain_fixture` records each
case's deck lines as kinds and slices in order. The two runs must leave the same lines in every case, each
slice's in the same order (siblings running abreast are threads, and which writes first is the scheduler's,
with an agent or without) — and
the stand-in must actually have been asked, every event it was woken for closed by its own orders and none
by the rule, or the comparison would prove nothing.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SUITES = ("test_captain", "test_captain_abreast", "test_captain_gate", "test_captain_log", "test_captain_stop",
          "test_captain_watch")
STAND_IN = HERE / "fixtures" / "captain_stand_in.py"


def suites(record: Path, **env: str) -> subprocess.Popen:
    clean = {key: value for key, value in os.environ.items()
             if key not in ("SLIPWAI_CAPTAIN", "SLIPWAI_SAIL", "SLIPWAI_ACP", "STAND_IN_CAPTAIN")}
    path = os.pathsep.join([str(ROOT / "src"), str(ROOT / ".python-tools"), str(HERE)])
    return subprocess.Popen([sys.executable, "-m", "unittest", *SUITES], cwd=ROOT, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            env={**clean, "PYTHONPATH": path, "SLIPWAI_TEST_RECORD": str(record), **env})


def read(record: Path) -> dict[str, dict]:
    return {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in sorted(record.glob("*.json"))}


def per_slice(decks: dict[str, list[list[str]]]) -> dict[str, dict[str, list[str]]]:
    """Each deck's lines as each slice's kinds in order. Slices running abreast are threads, and which of two
    siblings writes its `claimed` or its `demo` first is the scheduler's, run to run, with an agent or
    without: the order that is the captain's is the order of each slice's own lines, and which slices have
    them at all."""
    held: dict[str, dict[str, list[str]]] = {}
    for deck, lines in decks.items():
        for kind, slice_id in lines:
            held.setdefault(deck, {}).setdefault(slice_id, []).append(kind)
    return held


class ParityTest(unittest.TestCase):
    def test_a_stand_in_that_makes_today_s_choices_leaves_the_same_deck_lines(self) -> None:
        folder = Path(tempfile.mkdtemp())
        alone, agent = folder / "alone", folder / "agent"
        runs = [suites(alone), suites(agent, SLIPWAI_CAPTAIN=f"{sys.executable} {STAND_IN}",
                                      STAND_IN_CAPTAIN="today")]
        said = [run.communicate(timeout=1800)[0] for run in runs]
        for run, out in zip(runs, said, strict=True):
            self.assertEqual(run.returncode, 0, out[-4000:])
        plain, standing_in = read(alone), read(agent)
        self.assertEqual(sorted(plain), sorted(standing_in), "the same cases ran both ways")
        differ = [case for case in plain if per_slice(plain[case]["decks"]) != per_slice(standing_in[case]["decks"])]
        self.assertEqual(differ, [], "\n".join(f"{case}:\n  alone {plain[case]['decks']}\n  agent "
                                               f"{standing_in[case]['decks']}" for case in differ))
        closed = [by for case in standing_in.values() for by in case["closed"]]
        self.assertTrue(closed, "the stand-in was never woken, so nothing was compared")
        self.assertEqual(set(closed), {"captain"}, "every event the stand-in was woken for, closed by its orders")
        self.assertEqual([by for case in plain.values() for by in case["closed"]], [], "alone, nothing is asked")


if __name__ == "__main__":
    unittest.main()
