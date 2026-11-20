"""A child run to a time limit, and ended with everything it started when the limit comes.

`subprocess.run(..., capture_output=True, timeout=n)` ends the child at the limit and then reads its pipes to
the end. A captain starts sessions of its own, and those inherit the pipes: with the captain gone and a
session still alive, that read never returns. The `gate (macos-latest, 3)` job sat in one such read for two
hours, twice in a day, with trunk's next run queued behind it, and the runner's own clean-up listed the four
orphaned Python processes that had held it.

So the child is given a process group of its own, and at the limit the whole group is ended before anything
is read. What comes back is the failure the limit was for, with what the child had said.
"""
from __future__ import annotations

import contextlib
import os
import signal
import subprocess
from pathlib import Path


def run(argv: list[str], timeout: float, cwd: Path | None = None,
        env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """`subprocess.run(argv, capture_output=True, text=True)`, bounded for the child and its descendants.

    Raises `AssertionError` at the limit, with the output so far, rather than `TimeoutExpired` after a read
    that may never end. On Windows there is no process group to signal this way, and the plain call is made.
    """
    if os.name == "nt":  # pragma: no cover - the other platform's branch
        return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, check=False)
    with subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          start_new_session=True) as child:
        try:
            out, err = child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(child.pid, signal.SIGKILL)
            try:
                out, err = child.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                out, err = "", "(its output could not be read: something outside its process group held the pipe)"
            raise AssertionError(f"{' '.join(argv[:4])} was still running after {timeout:g}s and was ended, with "
                                 f"everything it started.\n{out}\n{err}") from None
    return subprocess.CompletedProcess(argv, child.returncode, out, err)
