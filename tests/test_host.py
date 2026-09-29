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

    def test_a_package_no_default_index_carries_uses_the_publisher_s_installer(self) -> None:
        """OpenTofu is not in Debian's own archive: its own standalone installer is the route, not a repository
        added for you; a tool with neither is still answered with the page."""
        self.assertIn("get.opentofu.org", install_command("tofu", DEBIAN) or "")
        self.assertIn("`brew install opentofu`", install_hint("tofu", "https://opentofu.org/", MAC))
        self.assertIsNone(install_command("az", DEBIAN))
        self.assertEqual(install_hint("az", "https://aka.ms/azcli", DEBIAN), "https://aka.ms/azcli")

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


class PreflightShellTest(FactoryTestCase):
    def test_a_windows_refusal_spells_the_variable_for_powershell(self) -> None:
        """`export` is not a PowerShell command; the line a Windows user is handed has to be one that runs."""
        from slipwai.preflight import REGION, for_shell

        why = REGION["aws"][2][1]
        self.assertIn('`$env:AWS_REGION = "eu-west-2"`', for_shell(why, WINDOWS))
        self.assertNotIn("export", for_shell(why, WINDOWS))
        self.assertEqual(for_shell(why, MAC), why)
        self.assertEqual(for_shell(why, DEBIAN), why)


class PortableRecipesTest(FactoryTestCase):
    def test_no_generated_recipe_runs_an_npm_shim_a_windows_make_cannot(self) -> None:
        """`node_modules/.bin/<tool>` is a POSIX shell script on every OS, and native Windows `make` fails on it;
        `make verify` on Windows stopped at exactly one recipe, `check-drawio`, for that reason."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "portable", "event-modelling", "typescript")
            makefile = (repo / "Makefile").read_text(encoding="utf-8")
            self.assertNotIn("node_modules/.bin/", makefile)
            self.assertIn("node scripts/event-model/node_modules/tsx/dist/cli.mjs", makefile)


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


# A tool no machine has, registered with the installer for the test alone. A real one — `tofu`, `gh` — may well be
# on the machine running the suite (CI's image has OpenTofu in /usr/local/bin), and `ensure` rightly widens PATH with
# the standard install directories before it looks, so it would find the real one and install nothing.
TOOL = "zz-slipwai-test-tool"
SYNTHETIC = (
    "from slipwai.host import ensure, Host, TOOLS; "
    f"TOOL = '{TOOL}'; TOOLS.PACKAGES[TOOL] = {{'brew': 'zz-formula', 'apt-get': 'zz-package'}}; "
)
ON_BREW = SYNTHETIC + "print(ensure([TOOL], Host('macos', ('brew',))))"
ON_APT = SYNTHETIC + "print(ensure([TOOL], Host('linux', ('apt-get',))))"


def run_python(
    code: str, path: str, *, no_install: bool = False, stdin: str | None = None, home: str | None = None
) -> subprocess.CompletedProcess[str]:
    """`code` in a fresh interpreter with `PATH` set to `path`, installs on unless asked otherwise."""
    environment = {key: value for key, value in os.environ.items() if key != "SLIPWAI_NO_INSTALL"}
    environment |= {"PATH": path, "PYTHONPATH": str(ROOT / "src")} | ({"HOME": home} if home else {})
    if no_install:
        environment["SLIPWAI_NO_INSTALL"] = "1"
    return subprocess.run(
        [shutil.which("python3") or "python3", "-c", code], env=environment, input=stdin, text=True,
        capture_output=True,
    )


class InstallTest(FactoryTestCase):
    """What was chosen is installed, not handed back as a line to run — driven through stub package managers on a
    private PATH, so the real install path runs and nothing reaches the network or this machine's packages."""

    def stubs(self, directory: str, **scripts: str) -> Path:
        bin_dir = Path(directory) / "bin"
        bin_dir.mkdir(exist_ok=True)
        for name, body in scripts.items():
            (bin_dir / name).write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
            (bin_dir / name).chmod(0o755)
        for tool in ("sh", "python3", "chmod"):  # what the stubs themselves call; nothing else is on this PATH
            real = shutil.which(tool)
            if real and not (bin_dir / tool).exists():
                (bin_dir / tool).symlink_to(real)
        return bin_dir

    def test_a_missing_tool_is_installed_with_the_package_manager_the_machine_has(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "brew.log"
            bin_dir = self.stubs(directory, brew=(
                f'echo "$@" >> {log}\n'
                f'printf "#!/bin/sh\\n" > "{directory}/bin/{TOOL}"; chmod 755 "{directory}/bin/{TOOL}"'
            ))
            done = run_python(ON_BREW, str(bin_dir), home=directory)
            self.assertEqual(done.stdout.strip().splitlines()[-1], "[]", done.stderr)
            self.assertEqual(log.read_text(encoding="utf-8").strip(), "install zz-formula")

    def test_nothing_is_installed_where_installs_are_turned_off(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "brew.log"
            bin_dir = self.stubs(directory, brew=f'echo "$@" >> {log}')
            done = run_python(
                ON_BREW, str(bin_dir), no_install=True, home=directory,
            )
            self.assertEqual(done.stdout.strip().splitlines()[-1], f"['{TOOL}']", done.stderr)
            self.assertFalse(log.exists(), "SLIPWAI_NO_INSTALL was set, and brew still ran")

    def test_a_system_manager_goes_through_sudo_and_never_waits_for_a_password_without_a_terminal(self) -> None:
        """apt needs root: `sudo`, refreshed once first, and `-n` where there is no terminal to type a password into
        — a failure then, never a hang. As root, there is no `sudo` at all."""
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "calls.log"
            bin_dir = self.stubs(
                directory,
                sudo=f'echo "sudo $@" >> {log}\nwhile [ "${{1#-}}" != "$1" ]; do shift; done\nexec "$@"',
                **{"apt-get": f'echo "apt-get $@" >> {log}\ncase "$*" in *install*) printf "#!/bin/sh\\n" > '
                              f'"{directory}/bin/{TOOL}"; chmod 755 "{directory}/bin/{TOOL}" ;; esac'},
            )
            done = run_python(ON_APT, str(bin_dir), home=directory)
            self.assertEqual(done.stdout.strip().splitlines()[-1], "[]", done.stderr)
            calls = log.read_text(encoding="utf-8").splitlines()
            self.assertIn("apt-get update -qq", calls)
            self.assertIn("apt-get install -y zz-package", calls)
            if os.geteuid() != 0:
                self.assertIn("sudo -n apt-get install -y zz-package", calls)

    def test_the_agent_question_has_no_answer_until_one_is_chosen(self) -> None:
        """Nothing preselected: Enter alone is not an answer — the list Spec Kit shows highlights Copilot, and
        Enter there chose it for people who meant Claude Code."""
        done = run_python(
            "from slipwai.cli_init import prompt_agent; print('chose', prompt_agent())",
            os.environ["PATH"], stdin="\nclaude\n",
        )
        self.assertIn("chose claude", done.stdout, done.stderr)
        self.assertIn("Coding agent (", done.stdout)
        self.assertNotIn("[copilot]", done.stdout)
        self.assertIn("Invalid coding agent", done.stderr)

    def test_installing_is_on_at_a_terminal_off_in_scripts_and_off_under_the_opt_out(self) -> None:
        code = ("from slipwai.cli_init import installing; "
                "print(installing(None, True), installing(None, False), installing(True, False), "
                "installing(False, True))")
        self.assertEqual(run_python(code, os.environ["PATH"]).stdout.split(), ["True", "False", "True", "False"])
        self.assertEqual(run_python(code, os.environ["PATH"], no_install=True).stdout.split(), ["False"] * 4)


class StatusTest(FactoryTestCase):
    def test_slipwai_status_and_next_are_adopt_next(self) -> None:
        """The ways people asked "where am I?" in a real adoption — `slipwai --next`, `slipwai --status` — answer
        it, rather than printing usage."""
        with tempfile.TemporaryDirectory() as directory:
            reference = subprocess.run(
                [str(ROOT / "slipwai"), "adopt", "--next"], cwd=directory, text=True, capture_output=True
            )
            for spelling in (["status"], ["--next"], ["--status"], ["next"]):
                asked = subprocess.run(
                    [str(ROOT / "slipwai"), *spelling], cwd=directory, text=True, capture_output=True
                )
                self.assertEqual(asked.returncode, reference.returncode, spelling)
                self.assertEqual(asked.stderr.splitlines()[-1:], reference.stderr.splitlines()[-1:], spelling)


class FrozenExecutableTest(FactoryTestCase):
    def test_the_executable_is_told_about_every_module_the_installer_imports(self) -> None:
        """`host.py` loads `install-tools.py` from the bundled assets at run time, so PyInstaller never sees its
        imports; the 1.5.0 executable died on `import platform` in its release smoke test. Every module the
        installer imports has to be named in `slipwai.spec`'s `hiddenimports`."""
        import ast
        import re

        source = ast.parse((ROOT / "assets/toolkit/scripts/install-tools.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(source):
            if isinstance(node, ast.Import):
                imported |= {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and node.module != "__future__":
                imported.add(node.module)
        spec = (ROOT / "slipwai.spec").read_text(encoding="utf-8")
        listed = set(re.findall(r'"([a-z_.]+)"', spec.split("hiddenimports=", 1)[1].split("hookspath", 1)[0]))
        always_bundled = {"os", "sys", "pathlib"}  # the frozen app's own imports pull these in regardless
        self.assertEqual(sorted(imported - listed - always_bundled), [])
