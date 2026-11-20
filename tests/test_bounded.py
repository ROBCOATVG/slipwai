"""The bounded run ends a child with everything it started, and says so, where the plain one waits for ever."""
from __future__ import annotations

import os
import sys
import time
import unittest

import bounded

#: A child that starts a grandchild holding its pipes and then sleeps: a captain with a session still alive.
BROOD = ("import subprocess, sys, time\n"
         "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
         "print('started', flush=True)\ntime.sleep(120)\n")


@unittest.skipIf(os.name == "nt", "a process group is ended by signal")
class BoundedTest(unittest.TestCase):
    def test_a_child_that_ends_in_time_is_what_run_would_have_returned(self) -> None:
        done = bounded.run([sys.executable, "-c", "print('hello')"], timeout=30)
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "hello"))

    def test_at_the_limit_the_child_and_what_it_started_are_ended_and_the_failure_says_what_it_had_said(self) -> None:
        began = time.monotonic()
        with self.assertRaises(AssertionError) as raised:
            bounded.run([sys.executable, "-c", BROOD], timeout=2)
        self.assertLess(time.monotonic() - began, 30, "the read after the limit waited on the grandchild")
        self.assertIn("was still running after 2s", str(raised.exception))
        self.assertIn("started", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
