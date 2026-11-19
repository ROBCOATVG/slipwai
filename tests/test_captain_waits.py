"""Parks that wait on nobody: a limit met at a merge, a red trunk, and an answer that was yesterday's.

Split from `test_captain_gate.py` at its budget. lean-coffee-club, 2026-11-19: the fleet said twelve things
were waiting on a person, and one was.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401
from captain_fixture import WORKS, Fixture

from slipwai import logs


class WaitsOnNobodyTest(Fixture):
    def test_a_limit_met_while_resolving_a_refused_merge_is_a_pause_too(self) -> None:
        """lean-coffee-club's SI2 was back in its berth resolving a conflict when the usage limit came. That
        run was read as one that failed, and the stream parked on "`/sail` exited 1" for a person for ten
        hours while the two streams beside it paused and started again at the reset."""
        self.refuse("ORD-01", "slice/ORD-01 conflicts with origin/main in decisions.md", resolve=True)
        runs = self.root / "runs.txt"
        # The stream-json flag comes before the slice and the fairway, so the fake reads them from the end.
        body = WORKS.replace("sys.argv[1], sys.argv[2]", "sys.argv[-2], sys.argv[-1]") + f"""
runs = pathlib.Path({str(runs)!r})
runs.write_text(runs.read_text() + "x" if runs.exists() else "x")
if runs.read_text() != "x":
    print('{{"type":"system","subtype":"init","session_id":"s"}}', flush=True)
    print('{{"type":"result","subtype":"success","is_error":true,"num_turns":1,'
          '"result":"You\\'ve hit your session limit · resets 9:40pm (Europe/London)"}}', flush=True)
    sys.exit(1)
"""
        done = self.captain("ORD", self.sail(body) + " --output-format stream-json")
        parked = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parked), 1, done.stdout + done.stderr)
        self.assertEqual(parked[0].fields.get("cause"), "limit", done.stdout + done.stderr)
        self.assertIn("no attempt spent", str(parked[0].fields["why"]))
        self.assertNotIn("exited 1", str(parked[0].fields["why"]))

    def test_a_merge_refused_on_a_red_trunk_parks_saying_it_waits_on_trunk(self) -> None:
        """So that every reader can tell it from a wait on a person: the harbourmaster clears it itself."""
        self.harbour(logs.entry("refused", harbour=True, fairway="ORD", request="merge-ORD-01",
                                why="trunk is red, and nothing merges onto a red trunk", resolve=False,
                                waiting="green-trunk"))
        done = self.captain("ORD", self.sail(WORKS))
        parked = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parked), 1, done.stdout + done.stderr)
        self.assertEqual((parked[0].fields.get("waiting"), parked[0].fields.get("cause")),
                         ("green-trunk", "trunk"), done.stdout)
        self.assertEqual(logs.paused(parked), parked)

    def test_yesterday_s_refusal_does_not_answer_today_s_request_of_the_same_id(self) -> None:
        """Merge requests are numbered from nought at every run, so the id repeats; the answer must not."""
        old, ahead = "2026-01-01T10:00:00Z", "2099-01-01T00:00:00Z"
        self.deck("ORD", logs.entry("request", fairway="ORD", id="merge-ORD-01", what="merge", slice="ORD-01",
                                    detail="merge slice/ORD-01 into trunk after the full gate", t=old))
        self.harbour(logs.entry("refused", harbour=True, fairway="ORD", request="merge-ORD-01", t=old,
                                why="trunk is red, and nothing merges onto a red trunk", resolve=False,
                                waiting="green-trunk"),
                     logs.entry("granted", harbour=True, fairway="ORD", request="merge-ORD-01", what="merge",
                                slice="ORD-01", commit="a1b2c3d", t=ahead))
        done = self.captain("ORD", self.sail(WORKS))
        self.assertEqual([e for e in self.read("ORD") if e.kind == "parked"], [], done.stdout + done.stderr)
        landed = [e for e in self.read("ORD") if e.kind == "merged"]
        self.assertEqual([str(e.fields["commit"]) for e in landed], ["a1b2c3d"], done.stdout + done.stderr)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
