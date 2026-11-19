"""Who agreed to which guard, kept: agreeing to one more keeps the rest, and taking one away is its own verb.

`guards.py --elect <key>` wrote the registry from the keys it was given and nothing else, so agreeing to a
second extension's guard withdrew the first one's without a word (#121). An agreement is a person's answer
to *may this refuse what I asked for*, and the answer to a different question does not take it back. So
`--elect` adds, `--remove` is how an answer is withdrawn, and `./init` naming one more extension asks about
that one and leaves the rest as they were.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401
from guard_project import Project

REFUSES = "import sys\nprint('no')\nsys.exit(2)\n"
ONE = {"before-search": {"run": "g.py", "budget": "5s"}}


class AddsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project()
        self.addCleanup(self.project.close)
        self.project.extension("cg", ONE, **{"g.py": REFUSES})
        self.project.extension("lint", {"before-write": {"run": "w.py", "budget": "5s"},
                                        "before-search": {"run": "s.py", "budget": "5s"}})

    def test_agreeing_to_a_second_keeps_the_first(self) -> None:
        self.project.guards("--elect", "cg")
        done = self.project.guards("--elect", "lint")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.project.agreed(), {"before-search": ["cg", "lint"], "before-write": ["lint"]})

    def test_agreeing_twice_writes_the_same_file(self) -> None:
        self.project.guards("--elect", "cg", "lint")
        first = self.project.registry.read_bytes()
        self.project.guards("--elect", "cg")
        self.assertEqual(self.project.registry.read_bytes(), first)

    def test_a_registry_written_before_this_is_read_and_kept_as_it_was(self) -> None:
        """What `--elect` wrote yesterday, down to a field this code has never heard of. The extension it
        names is not even offered here any more: its agreement is still a person's, and is still there."""
        self.project.registry.parent.mkdir(exist_ok=True)
        yesterday = {"extension": "old", "run": "guards/old.py", "budget": "3s", "stages": ["implement"],
                     "note": "kept"}
        self.project.registry.write_text(json.dumps({"v": 1, "guards": {"before-search": [yesterday]}},
                                                    indent=2) + "\n", encoding="utf-8")
        self.project.guards("--elect", "cg")
        written = json.loads(self.project.registry.read_text(encoding="utf-8"))
        self.assertEqual(written["v"], 1)
        self.assertEqual(written["guards"]["before-search"],
                         [{"extension": "cg", **ONE["before-search"]}, yesterday])

    def test_naming_one_more_extension_at_init_keeps_what_was_agreed(self) -> None:
        """`./init --extension lint`, months after `cg` was agreed to, with nobody at a terminal: `lint` is
        not agreed to, because silence is no — and `cg` is not withdrawn, because nobody was asked that."""
        self.project.guards("--elect", "cg")
        self.project.guards("--offer", "lint")
        self.assertEqual(self.project.agreed(), {"before-search": ["cg"]})

    def test_an_election_that_offers_nothing_withdraws_nothing(self) -> None:
        self.project.guards("--elect", "cg")
        self.project.guards("--offer", "no-guards-here")
        self.assertEqual(self.project.agreed(), {"before-search": ["cg"]})

    def test_the_guard_agreed_to_first_still_refuses(self) -> None:
        self.project.guards("--elect", "cg")
        self.project.guards("--elect", "lint")
        done = self.project.guards("before-search", "--query", "x")
        self.assertEqual(done.returncode, 2)
        self.assertIn("no", done.stderr)


class RemovesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project()
        self.addCleanup(self.project.close)
        self.project.extension("cg", ONE, **{"g.py": REFUSES})
        self.project.extension("lint", {"before-write": {"run": "w.py", "budget": "5s"}})
        self.project.guards("--elect", "cg", "lint")

    def test_removing_one_keeps_the_other_and_it_stops_refusing(self) -> None:
        done = self.project.guards("--remove", "cg")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.project.agreed(), {"before-write": ["lint"]})
        self.assertEqual(self.project.guards("before-search", "--query", "x").returncode, 0)

    def test_removing_what_was_never_agreed_to_says_so_and_changes_nothing(self) -> None:
        before = self.project.registry.read_bytes()
        done = self.project.guards("--remove", "nobody")
        self.assertEqual(done.returncode, 0)
        self.assertIn("nobody", done.stdout + done.stderr)
        self.assertEqual(self.project.registry.read_bytes(), before)

    def test_removing_nothing_is_refused_with_the_command(self) -> None:
        done = self.project.guards("--remove")
        self.assertEqual(done.returncode, 1)
        self.assertIn("guards.py --remove <key>", done.stderr)

    def test_what_was_removed_can_be_agreed_to_again(self) -> None:
        self.project.guards("--remove", "cg")
        self.project.guards("--elect", "cg")
        self.assertEqual(self.project.agreed(), {"before-search": ["cg"], "before-write": ["lint"]})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
