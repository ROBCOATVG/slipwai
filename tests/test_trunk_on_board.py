"""Trunk on the board: a red trunk, what the trunk mender did about it, and what that holds.

The owner's first real fleet run went red at its first commit; the mender tried twice, committed nothing —
the only fix was one its brief forbids — and parked for a person. The board said nothing at all. Each case
here writes the harbour log as that run did, in each of its states — red, mending, mended, spent and parked,
green again — beside a `mender.out` cut down from the real stream, and reads the board through its routes.
"""
from __future__ import annotations

import json
import os
import re
import time
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import logs, trunk_story
from slipwai.slice_card import slice_html
from slipwai.trunk_card import document

RED = "889f96c7d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6"
FIXED = "4b1d2c3e5f60718293a4b5c6d7e8f9a0b1c2d3e4"
JOBS = ".github/workflows/deploy.yml, .github/workflows/rollback.yml"
ANSWER = ("## Why I committed nothing\n\nBoth workflows fail at parse time: `deploy.yml` names a job `needs: "
          "build` that does not exist.\n\n- **What a person changes:** remove the `needs:` line in "
          "`.github/workflows/deploy.yml`\n- The brief forbids me any change to a workflow but a `uses:` ref.")
HOSTILE = ("<script>alert('mender')</script> and [a link](javascript:alert(1)) and "
           '<img src=x onerror="alert(2)"> and [the run](https://github.com/o/n/actions/runs/7)')


def at(minutes: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def line(kind: str, minutes: float, **fields: object) -> str:
    return json.dumps({"v": 1, "t": at(minutes), "kind": kind, **fields}) + "\n"


def stream(*results: str, after: tuple[str, ...] = ()) -> str:
    """A `mender.out` in the shape a print-mode session writes: an init, the agent's turns, a result per
    attempt — and, for the attempt in flight, its lines after the last result."""
    out = json.dumps({"type": "system", "subtype": "init", "session_id": "s1", "tools": ["Bash", "Read"]}) + "\n"
    for said in results:
        out += json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Reading the failed run."},
            {"type": "tool_use", "name": "Bash", "input": {"command": "gh run view 7 --log-failed",
                                                           "description": "Read the failed run's log"}}]}}) + "\n"
        out += json.dumps({"type": "user",
                           "message": {"content": [{"type": "tool_result", "content": "x" * 400}]}}) + "\n"
        out += json.dumps({"type": "result", "subtype": "success", "result": said,
                           "usage": {"output_tokens": 812}}) + "\n"
    for doing in after:
        out += json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": doing}}]}}) + "\n"
    return out


class TrunkBoardTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.harbour = logs.harbour_path(self.root, "m1")
        self.harbour.parent.mkdir(parents=True, exist_ok=True)
        self.running = logs.run_dir(self.root) / "running"
        self.running.mkdir(parents=True, exist_ok=True)
        trunk_story.KEPT.clear()

    def write(self, *lines: str) -> None:
        with self.harbour.open("a", encoding="utf-8") as handle:
            handle.write("".join(lines))

    def red(self) -> None:
        self.write(line("trunk-red", 40, commit=RED, job=JOBS, why=f"trunk is red at {RED[:8]}"))

    def attempt(self, n: int, minutes: float, failed: str = "") -> None:
        self.write(line("mend", minutes, job="trunk", commit=RED, attempt=n, branch=f"mend/trunk-{RED[:8]}-{n}"))
        if failed:
            self.write(line("mend-failed", minutes - 5, job="trunk", why=failed, commit=RED, attempt=n))

    def park(self) -> None:
        self.write(line("park", 10, fairway="", mend=True,
                        why=f"trunk is red at {RED[:8]} ({JOBS}) and the trunk mender's 2 attempt(s) did not clear "
                            "it; the last: the mender ended without committing anything on its branch. A person "
                            "decides what happens; no merge is granted until trunk is green"))

    def live(self) -> dict:
        return json.loads(self.get("/live.json")[1])

    def bands(self) -> tuple[str, str]:
        found = self.live()["bands"]
        return found["trunk"]["html"], found["fleet"]["html"]


class RedTrunkTest(TrunkBoardTest):
    def test_a_red_trunk_is_a_band_above_the_tabs_saying_where_since_when_and_that_merges_are_held(self) -> None:
        self.red()
        band, _ = self.bands()
        self.assertIn(f"Trunk is red at {RED[:8]}", band)
        self.assertIn(JOBS, band)
        self.assertIn("No merge is granted until trunk is green", band)
        self.assertIn("has not started yet", band)
        page = self.get("/voyage")[1]
        self.assertLess(page.index('data-band="trunk"'), page.index('<nav class="tabs" role="tablist"'),
                        "above the tabs, not in one")
        self.assertIn(f"Trunk is red at {RED[:8]}", page)

    def test_a_green_trunk_is_quiet_and_turning_red_is_swapped_in_by_the_poll_not_a_reload(self) -> None:
        self.write(line("trunk-green", 50, commit=RED))
        before = self.live()
        self.assertEqual(before["bands"]["trunk"]["html"], "")
        self.assertIn('data-band="trunk"', self.get("/voyage")[1], "the holder is there while it is empty")
        self.red()
        after = self.live()
        self.assertIn("Trunk is red", after["bands"]["trunk"]["html"])
        self.assertNotEqual(after["bands"]["trunk"]["said"], before["bands"]["trunk"]["said"])
        self.assertEqual(after["passage"]["shape"], before["passage"]["shape"], "a reload would be a shape change")

    def test_the_attempt_in_flight_is_said_with_its_number_its_time_and_what_it_is_doing(self) -> None:
        self.red()
        self.attempt(1, 35, failed="the mender ended without committing anything on its branch")
        self.attempt(2, 4)
        (self.running / "mender.json").write_text(json.dumps(
            {"job": "trunk", "attempt": 2, "pid": os.getpid(), "branch": f"mend/trunk-{RED[:8]}-2",
             "started": time.time() - 240, "url": "https://github.com/o/n/actions/runs/7", "commit": RED}))
        (self.running / "mender.out").write_text(stream(ANSWER, after=("/w/.github/workflows/deploy.yml",)))
        band, fleet = self.bands()
        self.assertIn("The trunk mender is on attempt 2 of 2", band)
        self.assertIn("4m in", band)
        self.assertIn('id="trunk-mend"', fleet)
        self.assertIn("What attempt 2 is doing", fleet)
        self.assertIn("deploy.yml", fleet[fleet.index("What attempt 2"):])
        self.assertIn("did not clear it", fleet, "attempt 1's outcome")
        self.assertIn('href="https://github.com/o/n/actions/runs/7"', fleet, "the CI run the attempt was sent")
        self.assertEqual(self.live()["waiting"]["count"], 0, "nothing is a person's while the mender works")


class SpentTest(TrunkBoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.red()
        self.attempt(1, 35, failed="the mender ended without committing anything on its branch")
        self.attempt(2, 20, failed="the mender ended without committing anything on its branch")
        self.park()

    def test_the_harbour_park_is_waiting_on_you_with_its_reason_linking_to_the_band(self) -> None:
        listed = self.live()["waiting"]
        self.assertEqual(listed["count"], 1)
        first = listed["holding"][0]
        self.assertEqual(first["href"], "#trunk")
        self.assertIn("the trunk mender's 2 attempt(s) did not clear it", first["text"])
        band, _ = self.bands()
        self.assertIn("could not clear it: 2 attempts spent", band)
        self.assertIn("Nothing on the board clears it but trunk going green", band, "no button that does nothing")
        self.assertNotIn("<button", band)

    def test_the_mender_s_last_answer_is_read_as_a_document(self) -> None:
        (self.running / "mender.out").write_text(stream("an earlier answer", ANSWER))
        _, fleet = self.bands()
        self.assertIn("<h2>Why I committed nothing</h2>", fleet)
        self.assertIn("<b>What a person changes:</b> remove the <code>needs:</code> line", fleet)
        self.assertNotIn("an earlier answer", fleet)
        self.assertEqual(fleet.count('class="mend-row"'), 2)

    def test_a_hostile_answer_is_drawn_as_text(self) -> None:
        (self.running / "mender.out").write_text(stream(HOSTILE))
        page = self.get("/voyage")[1]
        _, fleet = self.bands()
        for drawn in (fleet, page):
            self.assertNotIn("<script>alert", drawn)
            self.assertNotIn("<img src=x", drawn)
            self.assertNotIn('href="javascript', drawn)
            self.assertIn("&lt;script&gt;alert(&#x27;mender&#x27;)&lt;/script&gt;", drawn)
        self.assertIn('<a href="https://github.com/o/n/actions/runs/7" rel="noopener">the run</a>', fleet)

    def test_trunk_going_green_takes_it_off_the_list(self) -> None:
        self.write(line("trunk-green", 1, commit=FIXED))
        self.assertEqual(self.live()["waiting"]["count"], 0)
        band, fleet = self.bands()
        self.assertEqual(band, "", "green with no mend is quiet")
        self.assertIn("Green since", fleet, "the card keeps the last red's attempts")


class MendedTest(TrunkBoardTest):
    def test_a_landed_fix_waits_on_ci_and_then_says_green_again_for_a_while(self) -> None:
        self.red()
        self.attempt(1, 30)
        self.write(line("mended", 20, job="trunk", commit=FIXED, red=RED, attempt=1))
        band, _ = self.bands()
        self.assertIn(f"fix landed as {FIXED[:8]}", band)
        self.write(line("trunk-green", 2, commit=FIXED))
        band, fleet = self.bands()
        self.assertIn("Trunk is green again", band)
        self.assertIn(f"Mended at <code>{FIXED[:8]}</code>", band)
        self.assertIn("mended", fleet)
        with mock.patch("slipwai.trunk_card.BRIEFLY", 60):
            self.assertEqual(self.bands()[0], "", "and quiet once a while has passed")


class SliceHeldTest(unittest.TestCase):
    def test_a_slice_whose_merge_a_red_trunk_holds_says_so_rather_than_looking_stuck(self) -> None:
        row = {"slice": "GN3", "title": "", "state": "working", "fairway": "game-nights", "feature": "001-demo",
               "why": "", "stage": "Held · trunk red", "chip": "Held · trunk red", "tasks": ""}
        self.assertIn("Waiting for trunk to be green", slice_html(row))
        self.assertNotIn("Waiting for trunk", slice_html({**row, "stage": "Merge requested"}))


class TailTest(unittest.TestCase):
    """`mender.out` is tens of megabytes on a long attempt: its tail is read, once per change."""

    def setUp(self) -> None:
        import tempfile
        self.root = Path(tempfile.mkdtemp())
        self.out = logs.run_dir(self.root) / "running/mender.out"
        self.out.parent.mkdir(parents=True)
        self.out.write_text(("x" * 1000 + "\n") * 3000 + stream(ANSWER))
        trunk_story.KEPT.clear()

    def test_only_the_tail_is_read_and_an_unchanged_file_is_not_read_again(self) -> None:
        asked: list[tuple] = []
        real = trunk_story.read_bytes

        def counted(path: Path, limit: int, start: int = 0) -> tuple[bytes, int] | None:
            asked.append((limit, start))
            return real(path, limit, start)
        with mock.patch.object(trunk_story, "read_bytes", counted):
            first = trunk_story.said(self.root)
            again = trunk_story.said(self.root)
            self.assertIn("Why I committed nothing", first["result"])
            self.assertEqual(again, first)
            self.assertEqual(asked, [(trunk_story.TAIL, -trunk_story.TAIL)])
            with self.out.open("a") as handle:
                handle.write(stream("a newer answer"))
            self.assertEqual(trunk_story.said(self.root)["result"], "a newer answer")
            self.assertEqual(len(asked), 2)

    def test_a_link_or_a_pipe_in_its_place_is_not_read(self) -> None:
        self.out.unlink()
        self.out.symlink_to(self.root / "elsewhere")
        (self.root / "elsewhere").write_text(stream("not the mender's"))
        self.assertEqual(trunk_story.said(self.root)["result"], "")

    def test_only_web_links_survive_in_the_document(self) -> None:
        drawn = document("[x](javascript:alert(1)) [y](https://example.com/a)")
        self.assertNotIn("javascript", re.findall(r'href="([^"]*)"', drawn)[0] if 'href="' in drawn else "")
        self.assertEqual(re.findall(r'href="([^"]*)"', drawn), ["https://example.com/a"])


if __name__ == "__main__":
    unittest.main()
