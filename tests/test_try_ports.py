"""Try it frees its own ports and refuses anybody else's, so `ready` is never said over another process.

A stop signalled the process groups it had recorded, and recap's service and web server from a morning's run
outlived every stop after it: each new start could not bind, and the old processes answered the health checks,
so Try it reported `ready` over old code all day.
"""
from __future__ import annotations

import importlib.util
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

SCRIPT = TOOLKIT_ROOT / "scripts/agents/try_it.py"


def load() -> Any:
    spec = importlib.util.spec_from_file_location("try_it_ports", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@unittest.skipUnless(shutil.which("lsof") and sys.platform != "win32", "lsof says who holds a port")
class PortsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load()
        self.workspace = Path(tempfile.mkdtemp())
        self.elsewhere = Path(tempfile.mkdtemp())
        self.children: list[subprocess.Popen] = []

    def tearDown(self) -> None:
        for child in self.children:
            child.kill()
            child.wait()

    def listener(self, where: Path) -> tuple[int, subprocess.Popen]:
        port = free_port()
        child = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=where,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.children.append(child)
        deadline = time.monotonic() + 10
        while not self.module.taken(port) and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertTrue(self.module.taken(port), "the test's own listener never answered")
        return port, child

    def seen(self, port: int) -> None:
        # GitHub's macOS runner has an `lsof` that cannot see the test's own child listening; there is nothing to
        # stop by pid there, and the unnamed holder is the other test's to prove.
        if not self.module.listening(port):
            self.skipTest("lsof here cannot see a listener this test started")

    def test_a_process_of_its_own_left_on_its_port_is_stopped(self) -> None:
        port, child = self.listener(self.workspace)
        self.seen(port)
        self.module.ports_of = lambda where: [port]
        self.assertEqual(self.module.free_ports(self.workspace), [])
        self.assertIsNotNone(child.wait(timeout=10))
        self.assertEqual(self.module.listening(port), [])

    def test_somebody_else_s_process_on_its_port_is_named_and_left_alone(self) -> None:
        port, child = self.listener(self.elsewhere)
        self.module.ports_of = lambda where: [port]
        said = self.module.free_ports(self.workspace)
        named = f"port {port} is held by pid {child.pid}, which Try it did not start"
        unnamed = f"port {port} is held by a process lsof could not name"
        self.assertIn(said, ([named], [unnamed]))
        self.assertIsNone(child.poll())

    def test_a_port_that_answers_with_nobody_named_on_it_is_held(self) -> None:
        port, child = self.listener(self.elsewhere)
        self.module.ports_of = lambda where: [port]
        self.module.listening = lambda port: []
        said = self.module.free_ports(self.workspace)
        self.assertEqual(said, [f"port {port} is held by a process lsof could not name"])
        self.assertIsNone(child.poll())

    def test_a_port_nothing_answers_on_is_free(self) -> None:
        port = free_port()
        self.module.ports_of = lambda where: [port]
        self.assertEqual(self.module.free_ports(self.workspace), [])


if __name__ == "__main__":
    unittest.main()
