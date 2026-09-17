"""The image CI runs every job in: what pins its toolchains, and what holds it to them.

No CI job installs a toolchain. Every job needs all of them — the suite generates a project of any backend
and runs its native gate — so they are baked into the image built from `.github/runner/`, and
`.github/actions/toolchains` only checks that the image provides what this repository expects. These are
the properties that arrangement depends on: one place the versions are written, and a check that reads them
back from the checkout rather than from the image.
"""
from __future__ import annotations

import re

from support import FactoryTestCase

from slipwai.assets import ROOT

RUNNER = ROOT / ".github/runner"
TOOLCHAINS = ("PYTHON", "NODE", "GO", "JAVA", "TOFU", "KO", "PACK")


class CiImageTest(FactoryTestCase):
    def versions(self) -> dict[str, str]:
        return dict(
            line.split("=", 1)
            for line in (RUNNER / "versions.env").read_text().splitlines()
            if "=" in line and not line.startswith("#")
        )

    def test_every_toolchain_is_pinned_by_version_and_digest(self) -> None:
        """A version without a digest is a tag someone else can move under us."""
        versions = self.versions()
        for tool in TOOLCHAINS:
            self.assertTrue(versions.get(f"{tool}_VERSION", "").strip(), f"{tool}_VERSION is not pinned")
            self.assertRegex(
                versions.get(f"{tool}_SHA256", ""),
                r"^[0-9a-f]{64}$",
                f"{tool}_SHA256 is not a sha256, so a substituted archive would build cleanly",
            )

    def test_the_dockerfile_takes_every_version_from_that_one_file(self) -> None:
        """`versions.env` is the only place a toolchain version is written.

        The Dockerfile declares each as an ARG and `build.sh` supplies them all. An ARG with a default
        would be the second place a version can come from — and the one nobody remembers to update.
        """
        declared = re.findall(r"(?m)^ARG (\w+)(=?)", (RUNNER / "Dockerfile").read_text())
        self.assertEqual(sorted(name for name, _ in declared), sorted(self.versions()))
        self.assertEqual(
            [name for name, default in declared if default],
            [],
            "an ARG with a default can build an image versions.env never agreed to",
        )

    def test_the_check_reads_the_pins_from_the_checkout(self) -> None:
        """Every pin is asserted, and asserted against the repository rather than against the image.

        An image that checked itself would always agree with itself, so the script the action runs is the
        one in the checkout, reading the checkout's pins. That is what makes a rebuild that never happened
        fail the first job of the run instead of going unnoticed.
        """
        check = (RUNNER / "check-toolchains.sh").read_text()
        self.assertIn('. "$here/versions.env"', check)
        for tool in TOOLCHAINS:
            self.assertIn(f"${tool}_VERSION", check, f"{tool}_VERSION is pinned but never checked")
        action = (ROOT / ".github/actions/toolchains/action.yml").read_text()
        self.assertIn(".github/runner/check-toolchains.sh", action)

    def test_no_job_installs_a_toolchain(self) -> None:
        """The defect this replaced: a `setup-*` step re-downloads its toolchain into a container that is
        thrown away when the job ends, and asks api.github.com which version to fetch — unauthenticated, so
        60 requests an hour for the whole runner host, which one run spent."""
        action = (ROOT / ".github/actions/toolchains/action.yml").read_text()
        for installer in ("actions/setup-python", "actions/setup-node", "actions/setup-go",
                          "actions/setup-java", "setup-opentofu", "setup-ko", "setup-pack"):
            self.assertNotIn(installer, action, f"{installer} is back in the toolchains action")
        # The npm tarball cache is not a toolchain, and rides in the same action deliberately.
        self.assertIn("actions/cache@v4", action)
