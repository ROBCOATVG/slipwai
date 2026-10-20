"""A headless session that has said it is finished is ended, and one that exits by itself is left alone.

The session this was written for printed its `result` line with all thirty-two background tasks reported
back, then sat for seven minutes with its MCP servers attached until a person killed it — and `make surfaces`
read the 143 as a failed drawing. The fakes below are that session in miniature: a script that writes
stream-json and then sleeps, with a child of its own standing in for the servers.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401
from test_harness import loaded

from slipwai.process_alive import alive

STREAMED = ["--output-format", "stream-json"]


def line(**event: Any) -> str:
    return json.dumps(event)


class SessionEndTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        self.harness = loaded(self.root)
        self.harness.END_GRACE, self.harness.STOP_GRACE = 0.5, 1.0

    def fake(self, events: list[str], then: str) -> list[str]:
        """A session that prints `events`, starts a sleeping child as its server would, then runs `then`."""
        script = self.root / "fake.py"
        script.write_text(
            "import subprocess, sys, time\n"
            f"server = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
            f"open({str(self.root / 'server.pid')!r}, 'w').write(str(server.pid))\n"
            f"for event in {events!r}:\n"
            "    print(event, flush=True)\n"
            f"{then}\n", encoding="utf-8")
        return [sys.executable, str(script)]

    def run_session(self, argv: list[str]) -> tuple[int, str, float]:
        started = time.monotonic()
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            code = self.harness.run_session(argv, self.root, dict(os.environ))
        return code, out.getvalue(), time.monotonic() - started

    def server_gone(self) -> bool:
        pid = int((self.root / "server.pid").read_text(encoding="utf-8"))
        # Asked through `alive`, because `os.kill(pid, 0)` is not a question on Windows.
        for _ in range(30):
            if not alive(pid):
                return True
            time.sleep(0.1)
        with contextlib.suppress(OSError):
            os.kill(pid, 9)
        return False

    def test_a_finished_session_that_hangs_is_ended_with_what_it_said(self) -> None:
        events = [line(type="system", subtype="task_started", task_id="b1"),
                  line(type="system", subtype="task_notification", task_id="b1", status="completed"),
                  line(type="system", subtype="background_tasks_changed", tasks=[]),
                  line(type="result", subtype="success", is_error=False, result="drawn")]
        code, out, took = self.run_session([*self.fake(events, "time.sleep(60)"), *STREAMED])
        self.assertEqual(code, 0)
        self.assertLess(took, 15)
        self.assertIn('"result": "drawn"', out, "the stream is passed through unchanged")
        self.assertTrue(self.server_gone(), "the server it started goes with it")

    def test_a_failed_result_is_not_turned_into_success(self) -> None:
        events = [line(type="result", subtype="error_during_execution", is_error=True)]
        code, _, _ = self.run_session([*self.fake(events, "time.sleep(60)"), *STREAMED])
        self.assertNotEqual(code, 0)
        self.assertTrue(self.server_gone())

    def test_a_task_still_out_keeps_the_session_waited_on(self) -> None:
        """A delegate not yet reported back is the session still working, whatever `result` said."""
        events = [line(type="system", subtype="task_started", task_id="a1"),
                  line(type="result", subtype="success", is_error=False)]
        code, _, _ = self.run_session([*self.fake(events, "time.sleep(2); server.kill(); sys.exit(7)"),
                                       *STREAMED])
        self.assertEqual(code, 7, "it exited by itself, so its own status stands")

    def test_a_session_that_exits_by_itself_is_untouched(self) -> None:
        events = [line(type="result", subtype="success", is_error=False)]
        code, _, _ = self.run_session([*self.fake(events, "server.kill(); sys.exit(3)"), *STREAMED])
        self.assertEqual(code, 3)
        code, _, _ = self.run_session(self.fake(["plain words"], "server.kill(); sys.exit(5)"))
        self.assertEqual(code, 5, "a harness that does not stream events runs as it always did")

    def test_a_turn_after_a_result_is_not_the_end(self) -> None:
        ending = self.harness.Ending()
        ending.read(line(type="result", subtype="success", is_error=False))
        self.assertTrue(ending.ended)
        ending.read(line(type="system", subtype="init"))
        self.assertFalse(ending.ended)
        ending.read("not json at all")
        ending.read(line(type="system", subtype="background_tasks_changed", tasks=[{"task_id": "a2"}]))
        ending.read(line(type="result", subtype="success", is_error=False))
        self.assertFalse(ending.ended)
        ending.read(line(type="system", subtype="task_updated", task_id="a2", patch={"status": "completed"}))
        self.assertTrue(ending.ended)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
