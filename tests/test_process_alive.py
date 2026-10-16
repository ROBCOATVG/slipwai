"""Whether a pid file's process is running, asked without signalling it — on Windows above all, where the
old `os.kill(pid, 0)` was a Ctrl-C to the whole console and ended the suite that asked."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest

import checkout_packages  # noqa: F401

from slipwai.process_alive import alive


class AliveTest(unittest.TestCase):
    def test_this_process_is_running_and_is_still_running_after_being_asked(self) -> None:
        self.assertTrue(alive(os.getpid()))
        self.assertTrue(alive(os.getpid()), "asking twice: the first ask did not end it")

    def test_a_process_that_has_exited_is_not(self) -> None:
        done = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"],
                              capture_output=True, text=True, check=True)
        self.assertFalse(alive(int(done.stdout.strip())))

    def test_no_pid_is_not_a_process(self) -> None:
        """Zero is the caller's own process group on POSIX, so a pid file holding it must not read as alive."""
        self.assertFalse(alive(0))
        self.assertFalse(alive(-1))


if __name__ == "__main__":
    unittest.main()
