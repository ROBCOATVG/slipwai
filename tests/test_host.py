"""Which machine this is, what installs a missing tool on it, and `./init` run as the last step of `generate`.

The recipes are read against hosts built by hand — a macOS with Homebrew, a Debian with apt, a Windows with
winget — because the machine running the suite is one of them at most. What runs `./init` is driven for real,
against a stand-in script in a scratch directory and a PATH the test chooses.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.assets import ROOT
from slipwai.cli_init import bootstrap, launcher
from slipwai.host import PACKAGES, Host, detect, install_command, install_hint
from slipwai.targets import TOOLS

MAC = Host("macos", ("brew",))
DEBIAN = Host("linux", ("apt-get",))
WINDOWS = Host("windows", ("winget", "scoop"))
BARE_WINDOWS = Host("windows", ())


class HostTest(FactoryTestCase):
    def test_the_running_machine_is_named(self) -> None:
        self.assertIn(detect().system, ("macos", "linux", "wsl", "windows", "other"))

    def test_each_machine_gets_its_own_manager_s_command(self) -> None:
        self.assertEqual(install_command("tofu", MAC), "brew install opentofu")
        self.assertEqual(install_command("tofu", WINDOWS), "winget install --exact --id OpenTofu.Tofu")
        self.assertEqual(install_command("gh", DEBIAN), "sudo apt-get install -y gh")
        self.assertEqual(install_command("python3", DEBIAN), "sudo apt-get install -y python3 python3-venv")

    def test_a_package_no_default_index_carries_falls_back_to_the_link(self) -> None:
        """OpenTofu is not in Debian's own archive: the answer is the page, not a repository added for you."""
        self.assertIsNone(install_command("tofu", DEBIAN))
        self.assertEqual(install_hint("tofu", "https://opentofu.org/", DEBIAN), "https://opentofu.org/")
        self.assertIn("`brew install opentofu`", install_hint("tofu", "https://opentofu.org/", MAC))

    def test_uv_has_its_own_installer_where_no_manager_carries_it(self) -> None:
        self.assertEqual(install_command("uv", DEBIAN), "curl -LsSf https://astral.sh/uv/install.sh | sh")
        self.assertIn("install.ps1", install_command("uv", BARE_WINDOWS) or "")

    def test_every_tool_a_target_needs_has_a_recipe_somewhere(self) -> None:
        for rows in TOOLS.values():
            for tool, _why, _where in rows:
                self.assertIn(tool, PACKAGES, f"{tool} has no install recipe in host.PACKAGES")

    def test_a_posix_machine_runs_init_as_it_is(self) -> None:
        if shutil.which("python3") is None:
            self.skipTest("the python3 check comes first, and this machine has none")
        self.assertEqual(launcher(Host("linux", ())), [])

    def test_windows_with_no_sh_is_told_where_to_run_init_instead(self) -> None:
        """A PATH with python3 and nothing else: no `sh`, and no Git whose `sh.exe` could stand in."""
        python = shutil.which("python3")
        if python is None:
            self.skipTest("the python3 check comes first, and this machine has none")
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "python3").symlink_to(python)
            result = subprocess.run(
                [python, "-c",
                 "from slipwai.cli_init import launcher; from slipwai.host import Host; "
                 "print(launcher(Host('windows', ('winget',))))"],
                env={**os.environ, "PATH": directory, "PYTHONPATH": str(ROOT / "src")},
                text=True, capture_output=True, check=True,
            )
        self.assertIn("inside WSL", result.stdout)
        self.assertIn("winget install --exact --id Git.Git", result.stdout)


class BootstrapTest(FactoryTestCase):
    def script(self, root: Path, body: str) -> Path:
        init = root / "init"
        init.write_text(f"#!/bin/sh\n{body}\n")
        init.chmod(0o755)
        return Path("init")

    def test_the_script_runs_from_the_project_with_the_agent_named(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = self.script(root, 'printf "%s" "$*" > ran')
            self.assertTrue(bootstrap(root, script, "claude"))
            self.assertEqual((root / "ran").read_text(), "--integration claude")

    def test_a_failing_script_is_reported_and_not_raised(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertFalse(bootstrap(root, self.script(root, "exit 3"), None))

    def test_no_python3_means_init_is_not_started(self) -> None:
        """Without python3, `./init` would fetch Spec Kit and then stop; it is said before anything runs."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = self.script(root, "touch ran")
            empty = root / "empty-path"
            empty.mkdir()
            result = subprocess.run(
                [shutil.which("python3") or "python3", "-c",
                 "import sys; from pathlib import Path; from slipwai.cli_init import bootstrap; "
                 f"sys.exit(0 if bootstrap(Path({str(root)!r}), Path({str(script)!r}), None) else 1)"],
                env={**os.environ, "PATH": str(empty), "PYTHONPATH": str(ROOT / "src")},
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("./init needs python3", result.stdout)
            self.assertFalse((root / "ran").exists())


class GenerateInitTest(FactoryTestCase):
    def test_the_flag_form_leaves_init_as_the_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [str(ROOT / "slipwai"), "generate", "quiet", "--output", directory],
                text=True, capture_output=True, check=True,
            )
            self.assertIn("created:", result.stdout)
            self.assertNotIn("Running ./init", result.stdout)

    def test_an_agent_the_registry_does_not_know_is_refused_before_anything_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [str(ROOT / "slipwai"), "generate", "named", "--integration", "nobody", "--output", directory],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--integration names `nobody`", result.stderr)
            self.assertFalse((Path(directory) / "named").exists())

    def test_init_and_no_init_cannot_both_be_asked_for(self) -> None:
        result = subprocess.run(
            [str(ROOT / "slipwai"), "generate", "both", "--init", "--no-init"], text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("not allowed with argument", result.stderr)
