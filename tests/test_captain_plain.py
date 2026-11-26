"""Every park and need the captain writes carries a plain line, held to the one rule (`logs.unplain`).

#174 gave a need and a question raised through `fleet.py tell` a `plain` line, and left the captain's own
parks without one: *has had 7 runs since a person last said anything to it*, a gate's attempts spent, a park
its captain agent ordered with `--needs`. Each rendered with the note that its wording was the agent's own.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from typing import Any

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"


def captain() -> Any:
    if str(AGENTS) not in sys.path:
        sys.path.insert(0, str(AGENTS))
    found = importlib.util.spec_from_file_location("toolkit_captain_plain", AGENTS / "captain.py")
    assert found is not None and found.loader is not None
    made = importlib.util.module_from_spec(found)
    sys.dont_write_bytecode = True
    found.loader.exec_module(made)
    return made


class PlainTest(unittest.TestCase):
    module: Any = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = captain()

    def written(self, **carried: object) -> logs.Entry:
        lines: list[logs.Entry] = []
        self.module.entries = lambda _feature, _fairway: []
        self.module.write = lambda _feature, _fairway, line: lines.append(line)
        self.module.finished("001-orders", "ORD", "ORD-01", False, "the demo was not run", 0, True,
                             carried=carried)
        [line] = lines
        return line

    def test_every_cause_has_a_plain_line_and_every_line_is_plain(self) -> None:
        self.assertEqual(set(self.module.PARK_PLAIN), set(logs.CAUSES))
        said = [*self.module.PARK_PLAIN.values(), self.module.SPENT_PLAIN, self.module.STRANDED_PLAIN,
                self.module.NEED_PLAIN, *(need["plain"] for need in self.module.seed_need("ORD-01", "001-orders"))]
        for one in said:
            self.assertEqual(logs.unplain(one), "", one)
            self.assertLessEqual(len([bit for bit in one.split(". ") if bit]), 2, one)

    def test_a_park_leads_with_its_cause_s_plain_line(self) -> None:
        line = self.written(cause="gate")
        self.assertEqual(line.fields["plain"], self.module.PARK_PLAIN["gate"])
        self.assertEqual(line.fields["why"], "ORD-01: the demo was not run", "the captain's words stay its why")
        self.assertEqual(self.written().fields["plain"], self.module.PARK_PLAIN["other"])

    def test_a_slice_out_of_runs_says_what_lets_it_run_again(self) -> None:
        self.assertEqual(self.written(cause="gate", plain=self.module.SPENT_PLAIN).fields["plain"],
                         self.module.SPENT_PLAIN)

    def test_a_need_the_captain_carries_has_a_plain_line(self) -> None:
        need = self.module.person_need("a person reads the demo log and says what to change")
        self.assertEqual(need, {"what": "a person reads the demo log and says what to change", "by": "person",
                                "plain": "a person reads the demo log and says what to change"})
        for unplain in ("fix specs/001-orders/slices/ORD-01/try-it.json first", "decide FR-012 for ORD-01",
                        "Read it. Then read it again. Then say."):
            self.assertEqual(self.module.person_need(unplain)["plain"], self.module.NEED_PLAIN, unplain)
        line = self.written(cause="other", needs=[need])
        self.assertTrue(all(one.get("plain") for one in line.fields["needs"]))


if __name__ == "__main__":
    unittest.main()
