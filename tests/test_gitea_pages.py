"""`scripts/gitea-pages.py` and its installer: the daemon behind a forge's pages address.

Three things about it were only true of a daemon run by hand on a Mac, and each is pinned here so it stays
true of one installed on a host that fronts it with a public name: the bind address can be moved, the owner
and repository match without regard to case, and a response that is not a success leaves a log line. The
installer's part is that the documented overrides reach an installed daemon at all.
"""
from __future__ import annotations

import importlib.util
import os
import plistlib
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from unittest import mock

from slipwai.assets import ROOT

SCRIPT = ROOT / "scripts/gitea-pages.py"
INSTALLER = ROOT / "scripts/install-gitea-pages"


def load_daemon() -> ModuleType:
    specification = importlib.util.spec_from_file_location("gitea_pages", SCRIPT)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class SiteCaseTest(unittest.TestCase):
    """Gitea lowercases owner and repository directories on disk; a project's link carries the owner as
    typed. On a case-sensitive filesystem only the daemon can make those two meet."""

    def setUp(self) -> None:
        self.module = load_daemon()
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "robcoatvg/slipwai/Slices").mkdir(parents=True)
        (self.root / "robcoatvg/slipwai/index.html").write_text("<h1>model</h1>\n")
        (self.root / "robcoatvg/slipwai/Slices/index.html").write_text("<h1>slices</h1>\n")

    def fold(self, path: str) -> str:
        return self.module.fold_site_case(path, self.root)

    def test_owner_and_repository_fold_to_their_on_disk_spelling(self) -> None:
        self.assertEqual(self.fold("/ROBCOATVG/slipwai/"), "/robcoatvg/slipwai/")
        self.assertEqual(self.fold("/ROBCOATVG/Slipwai/index.html"), "/robcoatvg/slipwai/index.html")

    def test_only_the_first_two_segments_fold(self) -> None:
        # Below owner and repository is site content, which stays exactly as the page linked it.
        self.assertEqual(self.fold("/ROBCOATVG/slipwai/slices/"), "/robcoatvg/slipwai/slices/")
        self.assertEqual(self.fold("/ROBCOATVG/slipwai/Slices/"), "/robcoatvg/slipwai/Slices/")

    def test_a_query_string_survives_and_an_unknown_name_is_left_for_the_404(self) -> None:
        self.assertEqual(self.fold("/ROBCOATVG/slipwai/?v=2"), "/robcoatvg/slipwai/?v=2")
        self.assertEqual(self.fold("/Nobody/slipwai/"), "/Nobody/slipwai/")
        self.assertEqual(self.fold("/"), "/")
        self.assertEqual(self.fold("/index.html"), "/index.html")

    def test_the_bind_address_is_an_override_with_loopback_as_its_default(self) -> None:
        self.assertEqual(self.module.HOST, "127.0.0.1")
        with mock.patch.dict(os.environ, {"GITEA_PAGES_HOST": "0.0.0.0"}):
            self.assertEqual(load_daemon().HOST, "0.0.0.0")


class ServingTest(unittest.TestCase):
    """The handler over a real socket: what it serves, and what it writes down."""

    def setUp(self) -> None:
        self.module = load_daemon()
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "robcoatvg/slipwai").mkdir(parents=True)
        (self.root / "robcoatvg/slipwai/index.html").write_text("<h1>model</h1>\n")
        self.logged: list[str] = []
        # The module reads its root at import and writes through `log`; a test swaps both.
        setattr(self.module, "ROOT", self.root)  # noqa: B010
        setattr(self.module, "log", self.logged.append)  # noqa: B010
        handler = partial(self.module.Handler, directory=str(self.root))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_address[1]
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def get(self, path: str) -> tuple[int, bytes]:
        connection = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_the_owner_as_typed_reaches_the_lowercase_site_and_a_success_is_not_logged(self) -> None:
        status, body = self.get("/ROBCOATVG/slipwai/")
        self.assertEqual((status, body), (200, b"<h1>model</h1>\n"))
        self.assertEqual(self.logged, [])

    def test_a_missing_site_is_a_404_with_a_line_in_the_log(self) -> None:
        status, _ = self.get("/nobody/slipwai/")
        self.assertEqual(status, 404)
        self.assertTrue(any("404 'GET /nobody/slipwai/ HTTP/1.1'" in line for line in self.logged), self.logged)

    def test_a_tls_handshake_reaching_the_cleartext_port_is_a_400_that_names_its_request_line(self) -> None:
        # A public https:// name with nothing terminating TLS in front of the daemon. The ClientHello is not
        # a request line, and the log says so rather than nothing.
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as raw:
            raw.sendall(b"\x16\x03\x01 \x00\xa5 \x01\x00\n")
            raw.shutdown(socket.SHUT_WR)
            answer = b""
            while chunk := raw.recv(4096):
                answer += chunk
        # No status line: a request whose version cannot be read is answered as HTTP/0.9, body only, which is
        # also what a browser behind the missing proxy would have been shown.
        self.assertIn(b"Error code: 400", answer)
        self.assertIn(b"Bad request version", answer)
        self.assertTrue(any(line.startswith("127.0.0.1 - 400 '\\x16\\x03\\x01") for line in self.logged), self.logged)


class InstallerTest(unittest.TestCase):
    """`scripts/install-gitea-pages` writes the launchd agent; launchd gives an agent nothing from the shell,
    so every override present at install time has to be written into the plist to hold."""

    def install(self, environment: dict[str, str]) -> dict[str, object]:
        home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        prefix = home / "brew"
        (prefix / "bin").mkdir(parents=True)
        stub = home / "stub-bin"
        stub.mkdir()
        (stub / "launchctl").write_text("#!/bin/sh\nexit 0\n")
        (stub / "launchctl").chmod(0o755)
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GITEA_") and key not in {"HOME", "HOMEBREW_PREFIX"}
        }
        env.update({"HOME": str(home), "HOMEBREW_PREFIX": str(prefix), "PATH": f"{stub}:{env['PATH']}"})
        env.update(environment)
        result = subprocess.run(["sh", str(INSTALLER)], env=env, capture_output=True, text=True, check=True)
        self.home = home
        self.assertTrue((prefix / "bin/gitea-pages").exists())
        plist = plistlib.loads((home / "Library/LaunchAgents/dev.gitea.pages.plist").read_bytes())
        self.assertEqual(plist["ProgramArguments"], [f"{prefix}/bin/gitea-pages"])
        self.stdout = result.stdout
        return plist

    def test_every_override_set_at_install_time_reaches_the_agent_verbatim(self) -> None:
        overrides = {
            "GITEA_PAGES_HOST": "0.0.0.0",
            "GITEA_PAGES_PORT": "8081",
            "GITEA_REPOS_DIR": "/srv/gitea/repos & <more>",  # an XML-hostile value must arrive intact
            "GITEA_PAGES_ROOT": "%HOME%/served pages",
            "GITEA_PAGES_BRANCH": "site",
            "GITEA_PAGES_POLL_SECONDS": "5",
        }
        home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        overrides["GITEA_PAGES_ROOT"] = str(home / "served pages")
        plist = self.install(overrides)
        self.assertEqual(plist["EnvironmentVariables"], overrides)
        self.assertIn("http://0.0.0.0:8081/", self.stdout)
        # The site root it will serve from is made at the override, not at the Homebrew default.
        self.assertTrue((home / "served pages").is_dir())
        self.assertFalse((self.home / "brew/var/gitea-pages").exists())

    def test_with_nothing_set_the_agent_gets_the_defaults_and_an_empty_environment(self) -> None:
        plist = self.install({})
        self.assertEqual(plist["EnvironmentVariables"], {})
        self.assertIn("http://127.0.0.1:3301/", self.stdout)
        self.assertTrue((self.home / "brew/var/gitea-pages").is_dir())


if __name__ == "__main__":
    unittest.main()
