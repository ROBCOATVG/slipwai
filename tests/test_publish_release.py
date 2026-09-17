"""`scripts/publish-release.py`: what it attaches, what it replaces, and the tag it refuses to invent.

The release this exists because of failed with the archives already built — `gh: command not found` on a
forge that has no `gh` and would not answer it — so the gate is not "it uploads" but the three refusals and
the rerun. The forge is a local HTTP server recording every request, answering the releases API the way
Gitea does: a `404` for a tag with no release, a release with the assets it already holds, and an `id` to
post attachments to. No network, and nothing published anywhere.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from slipwai.assets import ROOT

SCRIPT = ROOT / "scripts/publish-release.py"
REPOSITORY = "OWNER/slipwai"
TAG = "v1.2.3"
CHANGELOG = "# Changelog\n\n## 1.2.3 — MINOR\n\nWhat this one gave a user.\n\n## 1.2.2 — PATCH\n\nBefore it.\n"


class Forge(BaseHTTPRequestHandler):
    """Gitea's releases API, as much of it as this script touches.

    `state` is the fixture: which tags exist, whether the tag already has a release, and what that release
    already holds. The rest is the assertion surface — `seen` is every request in order, so a test can prove
    that a tag was looked up *before* a release was created and that a replaced asset was deleted first.
    """

    state: dict[str, object] = {}
    seen: list[tuple[str, str]] = []
    headers_seen: dict[str, str] = {}
    uploaded: list[tuple[str, int]] = []
    created: dict[str, object] | None = None
    last_upload: tuple[str, bytes] = ("", b"")

    def record(self) -> None:
        Forge.seen.append((self.command, self.path))
        Forge.headers_seen = dict(self.headers)

    def reply(self, code: int, payload: object = None) -> None:
        body = json.dumps(payload).encode() if payload is not None else b""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def release(self) -> dict[str, object]:
        return {"id": 7, "html_url": f"https://forge.example/{REPOSITORY}/releases/tag/{TAG}",
                "assets": Forge.state.get("assets", [])}

    def do_GET(self) -> None:  # noqa: N802 — the name is http.server's
        self.record()
        if "/releases/tags/" in self.path:
            self.reply(200, self.release()) if Forge.state.get("released") else self.reply(404, {})
            return
        if re.search(r"/tags/[^/]+$", self.path):
            self.reply(200, {"name": TAG}) if Forge.state.get("tagged") else self.reply(404, {})
            return
        self.reply(404, {})

    def do_POST(self) -> None:  # noqa: N802 — the name is http.server's
        self.record()
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path.endswith("/releases"):
            Forge.created = json.loads(body)
            self.reply(201, self.release())
            return
        Forge.uploaded.append((self.path, len(body)))
        Forge.last_upload = (self.headers.get("Content-Type", ""), body)
        self.reply(201, {"id": 1})

    def do_DELETE(self) -> None:  # noqa: N802 — the name is http.server's
        self.record()
        self.reply(204)

    def log_message(self, *_arguments: object) -> None:
        """Silence: the suite's output is the report, and a request log in it is noise."""


class PublishReleaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.server = HTTPServer(("127.0.0.1", 0), Forge)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        Forge.state = {"tagged": True, "released": False, "assets": []}
        Forge.seen = []
        Forge.headers_seen = {}
        Forge.uploaded = []
        Forge.created = None
        Forge.last_upload = ("", b"")
        self.api = f"http://127.0.0.1:{self.server.server_port}/api/v1"

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "CHANGELOG.md").write_text(CHANGELOG)
        self.archive = self.root / "slipwai-linux-x86_64.tar.gz"
        self.archive.write_bytes(b"not really a tarball, but a real number of bytes")
        self.checksum = self.root / "slipwai-linux-x86_64.tar.gz.sha256"
        self.checksum.write_text("0000  slipwai-linux-x86_64.tar.gz\n")

    def publish(self, *files: Path, tag: str = TAG, token: str = "a-token") -> subprocess.CompletedProcess[str]:
        environment = {**os.environ, "GITEA_TOKEN": token} if token else {
            key: value for key, value in os.environ.items() if key != "GITEA_TOKEN"
        }
        return subprocess.run(
            ["python3", str(SCRIPT), "--api", self.api, "--repository", REPOSITORY, "--tag", tag,
             "--changelog-from", str(self.root), *(str(file) for file in (files or (self.archive,)))],
            text=True, capture_output=True, env=environment,
        )

    def test_it_will_not_invent_a_tag_the_forge_has_not_got(self) -> None:
        """The refusal that matters most. Gitea's `POST /releases` creates a missing `tag_name` pointing at
        the default branch, so a typo would leave a real tag naming a commit nobody released — and this
        repository's whole release discipline rests on a tag never moving."""
        Forge.state["tagged"] = False
        result = self.publish()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("has no tag", result.stderr)
        self.assertNotIn("POST", [method for method, _ in Forge.seen])

    def test_it_looks_the_tag_up_before_it_creates_anything(self) -> None:
        """Order, not just outcome: the release is created only after the tag is known to exist."""
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        methods = [method for method, _ in Forge.seen]
        self.assertEqual(methods[:2], ["GET", "GET"])
        self.assertEqual(methods[2], "POST")

    def test_the_notes_are_the_changelog_entry_for_that_version(self) -> None:
        """Read rather than composed, from the same file `tag-release.py` reads the tag's message from, and
        cut at the next heading so one version's entry never carries the one before it."""
        self.assertEqual(self.publish().returncode, 0)
        self.assertIsNotNone(Forge.created)
        assert Forge.created is not None
        self.assertEqual(Forge.created["tag_name"], TAG)
        self.assertEqual(Forge.created["body"], "What this one gave a user.")

    def test_a_missing_entry_does_not_stop_a_release_that_is_already_tagged(self) -> None:
        """By the time this runs the tag is pushed and the archives are built. Refusing over a changelog
        heading would leave a release nobody can download to protect a file somebody can still edit."""
        (self.root / "CHANGELOG.md").write_text("# Changelog\n\n## 9.9.9 — PATCH\n\nSomething else.\n")
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        assert Forge.created is not None
        self.assertEqual(Forge.created["body"], "")

    def test_every_file_is_attached_under_its_own_name(self) -> None:
        result = self.publish(self.checksum, self.archive)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            [path.rpartition("name=")[2] for path, _ in Forge.uploaded],
            ["slipwai-linux-x86_64.tar.gz", "slipwai-linux-x86_64.tar.gz.sha256"],
        )
        self.assertIn("/releases/7/assets?name=", Forge.uploaded[0][0])

    def test_the_upload_is_multipart_and_carries_the_file_whole(self) -> None:
        """The one thing a hand-rolled body can get wrong: the attachments endpoint takes `multipart/
        form-data` under the field name `attachment`, and the bytes have to arrive intact."""
        self.assertEqual(self.publish().returncode, 0)
        content_type, body = Forge.last_upload
        self.assertIn("multipart/form-data; boundary=", content_type)
        self.assertIn(b'name="attachment"; filename="slipwai-linux-x86_64.tar.gz"', body)
        self.assertIn(self.archive.read_bytes(), body)

    def test_a_rerun_replaces_an_asset_rather_than_attaching_it_twice(self) -> None:
        """Gitea allows two attachments with one name, so a release retried without this would hold the
        archive twice and no reader could tell which one the `.sha256` beside it describes."""
        Forge.state["released"] = True
        Forge.state["assets"] = [{"id": 42, "name": "slipwai-linux-x86_64.tar.gz"}]
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(("DELETE", "/api/v1/repos/OWNER/slipwai/releases/7/assets/42"), Forge.seen)
        self.assertIn("replacing: slipwai-linux-x86_64.tar.gz", result.stdout)
        methods = [method for method, _ in Forge.seen]
        self.assertLess(methods.index("DELETE"), methods.index("POST"))

    def test_a_release_the_forge_already_has_is_not_created_again(self) -> None:
        """A rerun finishes an upload; it does not rewrite the description of a release somebody may have
        edited by hand."""
        Forge.state["released"] = True
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("release exists", result.stdout)
        self.assertIsNone(Forge.created)

    def test_it_refuses_a_file_that_is_not_there(self) -> None:
        """Before anything is created, so a release is never made for archives that failed to download."""
        result = self.publish(self.root / "never-built.tar.gz")
        self.assertEqual(result.returncode, 1)
        self.assertIn("nothing to attach at", result.stderr)
        self.assertEqual(Forge.seen, [])

    def snapshot(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), "--api", self.api, "--repository", REPOSITORY, *arguments, str(self.archive)],
            text=True, capture_output=True, env={**os.environ, "GITEA_TOKEN": "a-token"},
        )

    def test_the_snapshot_is_the_one_release_remade_at_a_new_commit(self) -> None:
        """`--snapshot`: the previous `snapshot` release and its tag deleted, both made again at the commit
        the archives were built from, marked a pre-release — and then the archives attached as for any
        release. The tag moves because it is not a version and nothing is built from it."""
        Forge.state.update(released=True, tagged=True)
        result = self.snapshot("--snapshot", "1.13.0.dev7", "--commit", "abc123def456")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        methods = [(method, path.rsplit("/", 2)[-2:]) for method, path in Forge.seen]
        self.assertEqual(methods[0], ("GET", ["tags", "snapshot"]))
        self.assertEqual(methods[1], ("DELETE", ["releases", "7"]))
        self.assertEqual(methods[2], ("GET", ["tags", "snapshot"]))
        self.assertEqual(methods[3], ("DELETE", ["tags", "snapshot"]))
        self.assertEqual(methods[4][0], "POST")
        assert Forge.created is not None
        self.assertEqual(Forge.created["tag_name"], "snapshot")
        self.assertEqual(Forge.created["target_commitish"], "abc123def456")
        self.assertTrue(Forge.created["prerelease"])
        self.assertIn("1.13.0.dev7", str(Forge.created["name"]))
        self.assertIn("--pre", str(Forge.created["body"]))
        self.assertEqual([path.rsplit("name=", 1)[-1] for path, _size in Forge.uploaded], [self.archive.name])
        self.assertIn("1.13.0.dev7", result.stdout)

    def test_a_forge_with_no_snapshot_yet_gets_one_without_deleting_anything(self) -> None:
        Forge.state.update(released=False, tagged=False)
        result = self.snapshot("--snapshot", "1.13.0.dev1", "--commit", "abc123def456")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("DELETE", [method for method, _ in Forge.seen])
        assert Forge.created is not None
        self.assertEqual(Forge.created["tag_name"], "snapshot")

    def test_a_snapshot_needs_the_commit_it_was_built_from(self) -> None:
        """Without it Gitea would put the tag on the default branch's tip — which is not necessarily what
        was built, and exactly the tag-invented-by-CI this script exists to refuse."""
        result = self.snapshot("--snapshot", "1.13.0.dev7")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--snapshot needs --commit", result.stderr)
        self.assertEqual(Forge.seen, [])

    def test_the_token_comes_from_the_environment_and_is_required(self) -> None:
        """Never an argument: a command line is in the process table and in the runner's own logs."""
        result = self.publish(token="")
        self.assertEqual(result.returncode, 1)
        self.assertIn("GITEA_TOKEN", result.stderr)
        self.assertEqual(Forge.seen, [])

    def test_the_token_is_sent_the_way_gitea_reads_it(self) -> None:
        """`Authorization: token <t>`, not `Bearer`: the same spelling `publish-to-gitea.py` uses, and the
        one Gitea's API accepts for a personal access token or an Actions job token."""
        self.assertEqual(self.publish().returncode, 0)
        self.assertEqual(Forge.headers_seen.get("Authorization"), "token a-token")
        self.assertEqual(Forge.headers_seen.get("User-Agent"), "slipwai-publish")


class WorkflowTest(unittest.TestCase):
    """The workflow that calls it, held to the two mistakes that produced a failed release.

    Read as text rather than parsed: this is a gate on what the file says, and the `gh` that was here is
    exactly the string that must not come back.
    """

    def setUp(self) -> None:
        self.workflow = (ROOT / ".github/workflows/package.yml").read_text()

    def test_it_does_not_reach_for_the_github_cli(self) -> None:
        """`gh` is not on this forge's runner image, and Gitea does not serve GitHub's API to it."""
        self.assertNotIn("gh release", self.workflow)
        self.assertNotIn("GH_TOKEN", self.workflow)

    def test_it_publishes_through_the_script_this_suite_gates(self) -> None:
        self.assertIn("scripts/publish-release.py", self.workflow)
        self.assertIn("GITEA_TOKEN: ${{ github.token }}", self.workflow)

    def test_a_dispatched_tag_can_finish_a_release_whose_upload_failed(self) -> None:
        """The retry a spent version needs: the tag cannot be pushed again, so the tag is an input, the
        build takes that tag's source and the release job runs this workflow's own publishing code."""
        self.assertIn("ref: ${{ github.event.inputs.tag || github.ref }}", self.workflow)
        self.assertIn("--tag \"${{ github.event.inputs.tag || github.ref_name }}\"", self.workflow)
        self.assertIn("github.event.inputs.tag != ''", self.workflow)

    def test_it_is_the_retry_and_not_the_release_path(self) -> None:
        """A tag push must not start this, because the same atomic push starts the gate.

        `make release` pushes `main` and `v1.2.3` together, so a workflow on `v*` ran beside `verify.yml`
        and — being the shorter of the two — finished first: the executables were attached while the gate
        was still running, and would have been attached over a red one. A version is spent the moment it is
        uploaded. What is left here is the failure a gate cannot help with, which is the test above.
        """
        wheel = (ROOT / ".github/workflows/publish-package.yml").read_text()
        for workflow in (self.workflow, wheel):
            self.assertNotIn("tags:", workflow, "a tag push publishes beside the gate again")
            self.assertIn("workflow_dispatch:", workflow)


class ReleaseGateTest(unittest.TestCase):
    """The release publishes from the tag's own `verify` run, behind the same `needs:` the snapshot is.

    `needs:` is the only thing standing between a failed gate and a published version, because the registry
    accepts a name and version once and a fetched tag must never move. The tag is also verify's own trigger:
    after a release `main`'s head is the `Open` commit, so a branch run proves the *child* of what ships.
    """

    def setUp(self) -> None:
        self.workflow = (ROOT / ".github/workflows/verify.yml").read_text()
        self.jobs = re.findall(r"(?m)^  ([a-z0-9-]+):$", self.workflow[self.workflow.index("\njobs:"):])

    def test_a_tag_runs_the_whole_gate_and_is_never_cancelled(self) -> None:
        self.assertIn("tags:\n      - 'v*'", self.workflow, "a tag no longer runs the gate")
        # Never cancelled, for the reason `main` is not: a half-published release cannot be reasoned about.
        self.assertIn("!startsWith(github.ref, 'refs/tags/')", self.workflow)

    def test_the_release_job_waits_for_every_gate_job(self) -> None:
        self.assertIn("release", self.jobs)
        release = self.workflow[self.workflow.index("\n  release:"):]
        needs = re.search(r"needs: \[([^\]]*)\]", release)
        assert needs is not None, "the release job needs nothing, so it would publish over a red gate"
        self.assertEqual(sorted(n.strip() for n in needs.group(1).split(",")),
                          sorted(j for j in self.jobs if j not in ("snapshot", "release")))
        self.assertIn("if: startsWith(github.ref, 'refs/tags/v')", release)
        self.assertIn('if [ "${{ github.server_url }}" = "https://git.treyco.dev" ]', release)
        self.assertEqual(release.count("if: steps.instance.outputs.canonical == 'true'"),
                          release.count("      - ") - 1, "a step is ungated on the instance check")
        self.assertIn("fetch-depth: 0", release)
        for step in ("make package-executable", "make publish-wheel", "scripts/publish-release.py",
                     '--tag "${{ github.ref_name }}"'):
            self.assertIn(step, release, f"the release job no longer runs {step}")
        # `--snapshot` is what makes the other job a snapshot; a release is attached to its tag instead.
        self.assertNotIn("--snapshot", release)

    def test_the_gate_jobs_the_tag_runs_tolerate_a_released_VERSION(self) -> None:
        """Gate jobs used to assume `main`; the tagged commit carries a released VERSION, so they failed and
        `release` never started."""
        changelog = (ROOT / "tests/test_changelog.py").read_text()
        self.assertIn("is_release(VERSION)", changelog)
        self.assertIn("v{VERSION}", changelog)
        migration = (ROOT / "scripts/test-migration.py").read_text()
        self.assertIn("def source_revision", migration)
        self.assertIn("the tagged Release commit itself", migration)


if __name__ == "__main__":
    unittest.main()
