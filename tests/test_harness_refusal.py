"""A harness that would not run the session, told from a session that ran and failed.

On the recap voyage the harness answered twice with one `result` line — `You've hit your session limit ·
resets 9:40pm (Europe/London)`, `is_error` true — and the captain read the exit code, which is 1 either way.
It ran each slice twice more in under a second, spent `attempts`, and parked eight slices on a wait that had
a time on it nothing read. This holds the reading: the words, the time, and the two guesses where there is
no time to read.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

import checkout_packages  # noqa: F401
from test_harness import loaded

RECAP = ('{"type":"result","subtype":"success","is_error":true,"duration_ms":540,"num_turns":1,'
         '"result":"You\'ve hit your session limit · resets 9:40pm (Europe/London)","session_id":"x"}')
#: 17:40 London on 2026-10-21 is 16:40Z: British Summer Time until the 25th.
AT = datetime(2026, 10, 21, 16, 40, tzinfo=UTC)


class RefusalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = loaded(Path(tempfile.mkdtemp()))

    def test_the_recap_line_is_a_limit_lifting_at_the_named_time_in_the_named_zone(self) -> None:
        found = self.harness.refusal(json.loads(RECAP)["result"], AT)
        self.assertEqual(found.cause, "limit")
        self.assertEqual(found.until, "2026-10-21T20:40:00Z")
        self.assertIn("resets 9:40pm", found.said)

    def test_a_time_already_passed_today_is_tomorrow_s(self) -> None:
        found = self.harness.refusal("You've hit your session limit · resets 4:40pm (Europe/London)", AT)
        self.assertEqual(found.until, "2026-10-22T15:40:00Z")

    def test_the_forms_the_time_may_take(self) -> None:
        for text, until in (("session limit · resets at 9pm (Europe/London)", "2026-10-21T20:00:00Z"),
                            ("usage limit reached, resets 09:40 PM (UTC)", "2026-10-21T21:40:00Z"),
                            ("session limit · resets 12:05am (UTC)", "2026-10-22T00:05:00Z")):
            with self.subTest(text=text):
                self.assertEqual(self.harness.refusal(text, AT).until, until)

    def test_a_zone_it_cannot_read_falls_back_to_the_machine_s_and_still_answers(self) -> None:
        found = self.harness.refusal("session limit · resets 9:40pm (Mars/Olympus)", AT)
        self.assertEqual(found.cause, "limit")
        self.assertRegex(found.until, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00Z$")

    def test_a_rate_limit_names_no_time_and_is_paused_fifteen_minutes(self) -> None:
        found = self.harness.refusal("API Error: 429 rate limit exceeded", AT)
        self.assertEqual(found.until, "2026-10-21T16:55:00Z")
        self.assertIn("paused 15 minutes", found.said)

    def test_a_session_limit_with_no_readable_time_is_paused_an_hour_and_says_it_guessed(self) -> None:
        found = self.harness.refusal("You've hit your session limit.", AT)
        self.assertEqual(found.until, "2026-10-21T17:40:00Z")
        self.assertIn("no reset time given, so paused 60 minutes", found.said)

    def test_a_session_that_ran_and_failed_is_not_a_refusal(self) -> None:
        for text in ("", "The tests are red and I could not fix them", "exited 1"):
            with self.subTest(text=text):
                self.assertIsNone(self.harness.refusal(text, AT))


class EndingTest(unittest.TestCase):
    def test_the_ending_keeps_what_the_last_result_said(self) -> None:
        harness = loaded(Path(tempfile.mkdtemp()))
        ending = harness.Ending()
        ending.read('{"type":"system","subtype":"init"}')
        ending.read(RECAP.encode("utf-8"))
        self.assertTrue(ending.erred)
        self.assertIn("session limit", ending.said)
        self.assertEqual(harness.refusal(ending.said, AT).until, "2026-10-21T20:40:00Z")

    def test_a_success_says_nothing_to_read_as_a_refusal(self) -> None:
        harness = loaded(Path(tempfile.mkdtemp()))
        ending = harness.Ending()
        ending.read('{"type":"result","subtype":"success","is_error":false,"result":"LB3 is through its gate"}')
        self.assertFalse(ending.erred)
        self.assertIsNone(harness.refusal(ending.said, AT))


if __name__ == "__main__":
    unittest.main()
