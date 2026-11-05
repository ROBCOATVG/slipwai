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
        while not self.module.listening(port) and time.monotonic() < deadline:
            time.sleep(0.1)
        return port, child

    def test_a_process_of_its_own_left_on_its_port_is_stopped(self) -> None:
        port, child = self.listener(self.workspace)
        self.module.ports_of = lambda where: [port]
        self.assertEqual(self.module.free_ports(self.workspace), [])
        self.assertIsNotNone(child.wait(timeout=10))
        self.assertEqual(self.module.listening(port), [])

    def test_somebody_else_s_process_on_its_port_is_named_and_left_alone(self) -> None:
        port, child = self.listener(self.elsewhere)
        self.module.ports_of = lambda where: [port]
        said = self.module.free_ports(self.workspace)
        self.assertEqual(said, [f"port {port} is held by pid {child.pid}, which Try it did not start"])
        self.assertIsNone(child.poll())


if __name__ == "__main__":
    unittest.main()
