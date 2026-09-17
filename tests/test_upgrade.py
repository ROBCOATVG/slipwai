"""`slipwai upgrade`: which install it decides it is, what it asks the registry, and what it says back.

The behaviour worth gating is the one the verb was written for: a private registry that answers `401` must
be reported as a refusal, never as an up-to-date install. `uv tool upgrade` gets that wrong — it prints
`Nothing to upgrade` and exits 0 — so a test that only proved "we shell out to uv" would prove the bug. The
registry here is a local HTTP server answering the four things a real one answers: a page of files, a page
whose newest file is the version this checkout carries, a `404` for a package it does not hold, and a `401`
for a caller it does not know.
"""
from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from slipwai.assets import ROOT, VERSION
from slipwai.errors import GenerationError
from slipwai.upgrade import (
    RECEIPT,
    credentials,
    environment_variable,
    following_snapshots,
    how_installed,
    index_of,
    published,
    upgrade_command,
    versions_in,
)
from slipwai.versions import key

# A version this factory cannot have reached, so the "there is a newer one" page stays newer than whatever
# `VERSION` says today — a fixture that has to be edited on a bump is a fixture that fails on a bump.
NEWER = f"{int(VERSION.split('.')[0]) + 1}.0.0"
# And the snapshot of main past that, which the registry also holds and which nobody is upgraded to unasked.
SNAPSHOT = f"{int(VERSION.split('.')[0]) + 2}.0.0.dev3"
# Two files per version, the way a registry that has taken a wheel and an sdist lists them, with the
# absolute URLs and `data-` attributes PyPI writes and a Gitea registry need not.
PAGE = f"""<!DOCTYPE html><html><body><h1>Links for slipwai</h1>
<a href="https://forge.example/files/slipwai-1.5.10.tar.gz#sha256=abc">slipwai-1.5.10.tar.gz</a><br />
<a href="../../files/slipwai-1.5.10-py3-none-any.whl" data-requires-python="&gt;=3.11">wheel</a><br />
<a href="https://forge.example/files/slipwai-{NEWER}-py3-none-any.whl#sha256=def">slipwai-{NEWER}.whl</a>
</body></html>"""
# The same registry once main's snapshot has been published to it as well.
WITH_SNAPSHOT = PAGE.replace(
    "</body>", f'<a href="https://forge.example/files/slipwai-{SNAPSHOT}-py3-none-any.whl#sha256=eee">s</a></body>'
)


class Registry(BaseHTTPRequestHandler):
    """A PEP 503 index of four moods, chosen by the path asked for."""

    seen: dict[str, str] = {}

    def do_GET(self) -> None:
        Registry.seen = dict(self.headers)
        if self.path.startswith("/private") and not self.headers.get("Authorization"):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="forge"')
            self.end_headers()
            self.wfile.write(b"unauthorized")
            return
        if self.path.startswith("/empty"):
            self.send_error(404)
            return
        page = (
            PAGE.replace("1.5.10", VERSION).replace(NEWER, VERSION)
            if self.path.startswith("/current")
            else PAGE
        )
        if self.path.startswith("/snapshots"):
            page = WITH_SNAPSHOT
        body = page.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_arguments: object) -> None:
        """Silence: the suite's output is the report, and a request log in it is noise."""


class UpgradeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.server = HTTPServer(("127.0.0.1", 0), Registry)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        Registry.seen = {}
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        for variable in ("UV_INDEX_SLIPWAI_USERNAME", "UV_INDEX_SLIPWAI_PASSWORD", "SLIPWAI_INDEX"):
            self.addCleanup(os.environ.pop, variable, None)
            os.environ.pop(variable, None)

    def run_upgrade(self, *arguments: str, **environment: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(ROOT / "slipwai"), "upgrade", *arguments],
            text=True,
            capture_output=True,
            env={**os.environ, **environment},
        )

    def test_a_refusal_is_reported_as_a_refusal_and_never_as_being_up_to_date(self) -> None:
        """The whole reason this verb asks the registry itself. `uv tool upgrade` answers a 401 index with
        `Nothing to upgrade` and exit 0, so a copy that cannot see the registry is told it is current. Here
        the status is quoted, the two variables to export are named, and the exit is not a success."""
        result = self.run_upgrade(SLIPWAI_INDEX=f"{self.base}/private")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("answered 401", result.stderr)
        self.assertIn("UV_INDEX_SLIPWAI_USERNAME", result.stderr)
        self.assertIn("UV_INDEX_SLIPWAI_PASSWORD", result.stderr)
        self.assertNotIn("newest published", result.stdout)

    def test_credentials_from_the_environment_reach_the_registry(self) -> None:
        """The same two variables `uv` reads, so a machine that can upgrade can also be told whether to."""
        result = self.run_upgrade(
            "--check",
            SLIPWAI_INDEX=f"{self.base}/private",
            UV_INDEX_SLIPWAI_USERNAME="someone",
            UV_INDEX_SLIPWAI_PASSWORD="a-token",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"newest published: {NEWER}", result.stdout)

    def test_a_registry_holding_none_of_this_package_says_so(self) -> None:
        """A 404 is an absence and is reported as one — the distinction the 401 case exists to keep."""
        result = self.run_upgrade(SLIPWAI_INDEX=f"{self.base}/empty")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("has no slipwai published", result.stdout)

    def test_a_checkout_is_told_to_pull_rather_than_pulled(self) -> None:
        """The newest version is reported for every shape, but a working tree is nobody else's to move: it
        may hold local commits, uncommitted changes, or a branch that is not main."""
        result = self.run_upgrade(SLIPWAI_INDEX=self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("installed as: checkout", result.stdout)
        self.assertIn(f"newest published: {NEWER}", result.stdout)
        self.assertIn(f"git -C {ROOT} pull", result.stdout)

    def test_the_version_this_checkout_carries_is_compared_rather_than_assumed(self) -> None:
        """An index whose newest file is this version says so, instead of upgrading this copy to itself."""
        result = self.run_upgrade(SLIPWAI_INDEX=f"{self.base}/current")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already the newest published version", result.stdout)
        self.assertNotIn("git -C", result.stdout)

    def test_the_page_is_read_by_filename_whatever_shape_the_links_are(self) -> None:
        found = versions_in(PAGE)
        self.assertEqual(sorted(set(found)), sorted({"1.5.10", NEWER}))
        self.assertEqual(max(found, key=key), NEWER)
        self.assertEqual(max(versions_in(WITH_SNAPSHOT), key=key), SNAPSHOT)
        # Ordered by number rather than by string, or 1.5.10 sorts below 1.5.9 and nobody is ever upgraded.
        self.assertGreater(key("1.5.10"), key("1.5.9"))
        self.assertEqual(versions_in('<a href="https://forge.example/files/other-9.9.9.whl">x</a>'), [])

    def test_a_snapshot_is_passed_over_unless_asked_for(self) -> None:
        """The registry holds the snapshot of main beside the releases. `pip` and `uv` pass a `.dev` version
        over, and so does this — a copy that never asked for one must never be told it is behind it."""
        self.assertEqual(published("slipwai", f"{self.base}/snapshots"), NEWER)
        self.assertEqual(published("slipwai", f"{self.base}/snapshots", prerelease=True), SNAPSHOT)
        self.assertTrue(following_snapshots(asked=True))
        # This checkout is a snapshot itself (`VERSION` is `<release>.dev0` on main), and a snapshot follows
        # the snapshots unasked: whoever installed one was asking for main.
        self.assertEqual(following_snapshots(), "dev" in VERSION)

        result = self.run_upgrade("--check", "--pre", SLIPWAI_INDEX=f"{self.base}/snapshots")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"newest published: {SNAPSHOT} (snapshots counted)", result.stdout)
        result = self.run_upgrade("--check", SLIPWAI_INDEX=f"{self.base}/snapshots")
        self.assertEqual(result.returncode, 0, result.stderr)
        newest = SNAPSHOT if "dev" in VERSION else NEWER
        self.assertIn(f"newest published: {newest}", result.stdout)

    def test_a_package_the_registry_does_not_hold_is_none_rather_than_a_refusal(self) -> None:
        self.assertIsNone(published("slipwai", f"{self.base}/empty"))
        with self.assertRaises(GenerationError) as refused:
            published("slipwai", f"{self.base}/private")
        self.assertIn("answered 401", str(refused.exception))

    def test_credentials_go_in_a_header_whether_they_came_from_the_environment_or_the_url(self) -> None:
        """A `pip --index-url https://user:token@forge/...` install can answer its own question too, and
        either way the token goes where a token goes: an Authorization header, never the request line."""
        expected = f"Basic {base64.b64encode(b'someone:a-token').decode()}"
        authority = self.base.replace("http://", "http://someone:a-token@")
        self.assertEqual(credentials("slipwai", authority), ("someone", "a-token"))
        self.assertEqual(published("slipwai", f"{authority}/private"), NEWER)
        self.assertEqual(Registry.seen.get("Authorization"), expected)

        os.environ["UV_INDEX_SLIPWAI_USERNAME"] = "someone"
        os.environ["UV_INDEX_SLIPWAI_PASSWORD"] = "a-token"
        Registry.seen = {}
        self.assertEqual(published("slipwai", f"{self.base}/private"), NEWER)
        self.assertEqual(Registry.seen.get("Authorization"), expected)

    def test_which_install_this_copy_is(self) -> None:
        """Four shapes, and the two `assets` cannot tell apart told apart by uv's receipt."""
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)
            self.assertEqual(how_installed(frozen=True, installed=True, prefix=prefix), "executable")
            self.assertEqual(how_installed(frozen=False, installed=False, prefix=prefix), "checkout")
            self.assertEqual(how_installed(frozen=False, installed=True, prefix=prefix), "environment")
            (prefix / RECEIPT).write_text("[tool]\nrequirements = []\n")
            self.assertEqual(how_installed(frozen=False, installed=True, prefix=prefix), "uv-tool")

    def test_the_index_a_uv_tool_installs_from_is_read_off_its_receipt(self) -> None:
        """Where a copy came from is where it is upgraded from — a mirror is not overridden by this
        factory's own default — and the index's name is what the credential variables are derived from."""
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / RECEIPT
            receipt.write_text(
                '[tool]\nrequirements = [{ name = "slipwai" }]\n\n[tool.options]\n'
                'index = [{ name = "our-forge", url = "https://mirror.example/pypi/simple", default = true }]\n'
            )
            self.assertEqual(index_of(receipt), ("our-forge", "https://mirror.example/pypi/simple"))
            # No receipt and no override: the public package index.
            name, url = index_of(Path(directory) / "absent.toml")
        self.assertEqual(name, "slipwai")
        self.assertEqual(url, "https://pypi.org/simple")
        self.assertEqual(environment_variable("our-forge"), "UV_INDEX_OUR_FORGE")

    def test_the_command_each_installed_shape_is_upgraded_with(self) -> None:
        """And that the two that cannot be upgraded from inside themselves refuse to name one."""
        if shutil.which("uv") is None:
            # No uv, no command to name — and saying so is the behaviour, not a gap in the test.
            with self.assertRaises(GenerationError):
                upgrade_command("uv-tool")
        else:
            self.assertEqual(upgrade_command("uv-tool")[1:], ["tool", "upgrade", "slipwai"])
            self.assertEqual(
                upgrade_command("uv-tool", prerelease=True)[1:], ["tool", "upgrade", "--prerelease", "allow", "slipwai"]
            )
        self.assertEqual(upgrade_command("environment")[1:], ["-m", "pip", "install", "--upgrade", "slipwai"])
        self.assertEqual(
            upgrade_command("environment", prerelease=True)[1:],
            ["-m", "pip", "install", "--upgrade", "--pre", "slipwai"],
        )
        for kind in ("executable", "checkout"):
            with self.assertRaises(GenerationError):
                upgrade_command(kind)
