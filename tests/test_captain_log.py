"""One captain's window: its deck log and the harbour's answers as one timeline, and its own output.

The Streams drawer shows the last sixty lines of one deck log, and stops at *asked to merge*: what happened to
the request, and how long it took, is in the harbour log. These hold the window that reads both — the fold
that puts a request beside its answer, the tail of the captain's output read from a byte, and the two routes.
"""
from __future__ import annotations

import json
import urllib.error

import checkout_packages  # noqa: F401
from board_fixture import BoardTest, Fixture

from slipwai import logs
from slipwai.bridge_page import read_only
from slipwai.cli_fleet import config
from slipwai.deck import TAIL, output, timeline
from slipwai.fleet import board


class CaptainFixture(Fixture):
    def harbour(self, *entries: logs.Entry) -> None:
        path = self.root / logs.harbour_path("m1")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())

    def printed(self, fairway: str, text: str) -> None:
        path = self.root / ".slipwai/running" / f"captain-{fairway}.out"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)

    def a_merge(self) -> None:
        """ORD asks for a merge and the harbour grants it, with the time it took. Both are stamped now, after
        the fixture's own claim: a pinned instant would fall behind that claim once the date passed it."""
        self.deck("ORD", logs.entry("request", fairway="ORD", id="merge-ORD-01", what="merge",
                                    slice="ORD-01", detail="merge slice/ORD-01"))
        self.harbour(logs.entry("granted", harbour=True, fairway="ORD", request="merge-ORD-01",
                                what="merge", slice="ORD-01", commit="4f2a91c0", waited_s=4, lock_s=0,
                                gate_s=161, attempt=1))


class TimelineTest(CaptainFixture):
    def test_a_request_sits_beside_the_harbour_s_answer_and_what_it_took(self) -> None:
        self.a_merge()
        lines, fault = timeline(self.root, "ORD")
        self.assertEqual(fault, "")
        kinds = [(one["who"], one["kind"]) for one in lines]
        self.assertEqual(kinds[-2:], [("captain", "request"), ("harbour", "granted")])
        self.assertIn("merge-ORD-01 granted at 4f2a91c0", lines[-1]["what"])
        self.assertEqual(lines[-1]["timing"], {"waited_s": 4, "lock_s": 0, "gate_s": 161, "attempt": 1})

    def test_another_fairway_s_harbour_lines_are_not_this_captain_s(self) -> None:
        self.harbour(logs.entry("berth-allocated", harbour=True, fairway="BIL", berth="bil-1"))
        self.assertNotIn("berth-allocated", [one["kind"] for one in timeline(self.root, "ORD")[0]])

    def test_a_line_without_a_slice_belongs_to_the_slice_last_claimed(self) -> None:
        self.deck("ORD", logs.entry("heartbeat", fairway="ORD", tokens=12))
        self.assertEqual(timeline(self.root, "ORD")[0][-1]["slice"], "ORD-01")

    def test_a_person_s_message_is_marked_as_theirs(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="go again"))
        self.assertEqual(timeline(self.root, "ORD")[0][-1]["who"], "person")


class OutputTest(CaptainFixture):
    def test_the_window_opens_on_the_tail_from_a_whole_line(self) -> None:
        self.printed("ORD", "x" * TAIL + "\nthe line after the cut\n")
        said, at = output(self.root, "ORD")
        self.assertEqual(said, "the line after the cut\n")
        self.assertEqual(at, TAIL + len("\nthe line after the cut\n"))

    def test_the_poll_gets_only_what_was_printed_since(self) -> None:
        self.printed("ORD", "captain: claimed\n")
        _, at = output(self.root, "ORD")
        self.printed("ORD", "captain: dispatched\n")
        self.assertEqual(output(self.root, "ORD", at), ("captain: dispatched\n", at + 20))

    def test_a_file_started_again_is_read_again_rather_than_waited_on(self) -> None:
        self.printed("ORD", "a fresh start\n")
        self.assertEqual(output(self.root, "ORD", 10_000)[0], "a fresh start\n")

    def test_a_name_with_no_deck_log_reads_nothing(self) -> None:
        """Which also keeps the name a fairway's: it is never a path somebody typed."""
        self.assertEqual(output(self.root, "../../etc/passwd"), ("", 0))


class RouteTest(CaptainFixture, BoardTest):
    def test_the_window_carries_both_logs(self) -> None:
        self.a_merge()
        self.printed("ORD", "captain: ORD claimed ORD-01\n")
        code, said = self.get("/captain?fairway=ORD")
        self.assertEqual(code, 200)
        self.assertIn("merge-ORD-01 granted", said)
        self.assertIn("captain: ORD claimed ORD-01", said)

    def test_the_poll_returns_what_is_new_and_where_it_ends(self) -> None:
        count = len(timeline(self.root, "ORD")[0])
        self.printed("ORD", "first\n")
        self.a_merge()
        code, said = self.get(f"/captain.json?fairway=ORD&lines={count}&out=0")
        self.assertEqual(code, 200)
        found = json.loads(said)
        self.assertEqual([one["kind"] for one in found["lines"]], ["request", "granted"])
        self.assertEqual((found["out"], found["at"]), ("first\n", 6))

    def test_a_captain_it_has_not_got_is_a_404_naming_the_ones_it_has(self) -> None:
        code, said = self.get_status("/captain?fairway=NOPE")
        self.assertEqual(code, 404)
        self.assertIn("ORD", said)

    def test_a_line_that_says_script_cannot_end_the_block_it_rides_in(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="</script><script>alert(1)</script>"))
        self.assertNotIn("</script><script>alert(1)", self.get("/captain?fairway=ORD")[1])

    def test_each_stream_links_to_its_window_and_the_published_copy_does_not(self) -> None:
        self.assertIn('href="/captain?fairway=ORD"', self.get("/voyage")[1])
        self.assertNotIn("/captain?", read_only(board(self.root, config(self.root)), config(self.root)))

    def get_status(self, path: str) -> tuple[int, str]:
        try:
            return self.get(path)
        except urllib.error.HTTPError as refused:
            with refused:
                return refused.code, refused.read().decode("utf-8")
