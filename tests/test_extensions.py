"""Extensions arrive through `./init --extension <key>`, same as an agent integration through `./init
--integration <agent>` — see docs/extensions.md for the contract `init.py` owes."""
from __future__ import annotations

import json
import os
import pty
import subprocess
import tempfile
import time
from pathlib import Path

from support import FactoryTestCase

from slipwai.catalog import CATALOG
from slipwai.extensions import known_extensions, validate_extensions

FAKE_SPECIFY = "#!/bin/sh\nexit 0\n"
# `j` once per row moves the cursor from the first extension to the Confirm row below the last.
TO_CONFIRM = b"j" * len(known_extensions(CATALOG))
# The server as `scripts/extensions/codegraph/init.py` names it, in the JSON shape most harnesses read and Codex's TOML.
SERVER = {"type": "stdio", "command": "npx", "args": ["-y", "@colbymchenry/codegraph@1.6.0", "serve", "--mcp"]}
CODEX_TABLE = ('[mcp_servers.codegraph]\ncommand = "npx"\n'
               'args = ["-y", "@colbymchenry/codegraph@1.6.0", "serve", "--mcp"]\n')


def run_init_at_a_terminal(repo: Path, args: list[str], keys: bytes, environment: dict) -> str:
    """Run `./init` attached to a real pty, the way an interactive user would — `/dev/tty` only resolves
    to something when a controlling terminal exists, which a plain `subprocess.run` never gives it. Sends
    `keys` once the checkbox menu has produced its first render, then reads to EOF. `keys` is raw bytes —
    e.g. `b"\\rj\\r"` to check the first row, move to the Confirm row and finish, or `b"j\\r"` to finish
    with nothing checked."""
    pid, master_fd = pty.fork()
    if pid == 0:
        os.chdir(repo)
        os.execvpe("./init", ["./init", *args], environment)
    output = b""
    sent = False
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            chunk = os.read(master_fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        output += chunk
        if not sent:
            time.sleep(0.2)  # let the menu finish its first render before keys arrive
            os.write(master_fd, keys)
            sent = True
    os.waitpid(pid, 0)
    return output.decode(errors="replace")


class ExtensionsTest(FactoryTestCase):
    def test_a_terminal_is_prompted_and_a_checked_extension_is_adopted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "codegraph-prompted")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            (fake_bin / "specify").write_text(FAKE_SPECIFY)
            (fake_bin / "specify").chmod(0o755)
            (fake_bin / "codegraph").write_text("#!/bin/sh\nexit 0\n")
            (fake_bin / "codegraph").chmod(0o755)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}

            output = run_init_at_a_terminal(repo, ["--integration", "codex"], b"\r" + TO_CONFIRM + b"\r", environment)

            self.assertIn("CodeGraph", output)
            self.assertIn("Extensions: codegraph", output)
            self.assertIn("<!-- extension:codegraph:begin -->", (repo / "AGENTS.md").read_text())
            self.assertTrue((repo / ".agents/skills/testing/SKILL.md").is_file())

    def test_a_terminal_confirming_with_nothing_checked_adopts_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "codegraph-declined")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            (fake_bin / "specify").write_text(FAKE_SPECIFY)
            (fake_bin / "specify").chmod(0o755)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}

            output = run_init_at_a_terminal(repo, ["--integration", "codex"], TO_CONFIRM + b"\r", environment)

            self.assertIn("Extensions: none", output)
            self.assertNotIn("<!-- extension:codegraph:begin -->", (repo / "AGENTS.md").read_text())
            self.assertTrue((repo / ".agents/skills/testing/SKILL.md").is_file())

    def test_init_extension_installs_and_indexes_codegraph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "codegraph-product")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            (fake_bin / "specify").write_text(FAKE_SPECIFY)
            (fake_bin / "specify").chmod(0o755)
            log = Path(directory) / "codegraph-args"
            fake_codegraph = fake_bin / "codegraph"
            fake_codegraph.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > {log}\n")
            fake_codegraph.chmod(0o755)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}

            subprocess.run(
                ["./init", "--integration", "codex", "--extension", "codegraph"],
                cwd=repo,
                check=True,
                env=environment,
            )

            self.assertEqual(log.read_text().split(), ["install", "--yes", "--init"])
            agents = (repo / "AGENTS.md").read_text()
            self.assertIn("<!-- extension:codegraph:begin -->", agents)
            self.assertIn("codegraph_explore", agents)
            self.assertEqual(
                json.loads((repo / ".slipwai/extensions.json").read_text()),
                {"schemaVersion": 1, "extensions": ["codegraph"]},
            )
            self.assertIn(".codegraph/", (repo / ".gitignore").read_text())
            # The connection travels with the checkout: the harness this run installs — recorded by Spec Kit in the
            # same run, so learnt from `SLIPWAI_INTEGRATION` — gets the server in the project file it reads, Codex's
            # TOML here, started through `npx` so a checkout with Node reaches the index without the CLI. The file
            # is committed: only the projected `.codex/agents/` is ignored, never the directory.
            self.assertEqual((repo / ".codex/config.toml").read_text(), CODEX_TABLE)
            self.assertFalse((repo / ".mcp.json").exists(), "Claude Code is not installed here")
            self.assertNotIn(".codex/\n", (repo / ".gitignore").read_text())
            self.assertNotIn("config.toml", (repo / ".gitignore").read_text())
            self.assertIn(".slipwai/catch-up.md", (repo / ".gitignore").read_text())
            self.assertNotIn(".slipwai/\n", (repo / ".gitignore").read_text())
            # Agent projection still ran alongside the extension.
            self.assertTrue((repo / ".agents/skills/testing/SKILL.md").is_file())

    def test_extension_guidance_is_replaceable_without_duplicating_its_markers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "codegraph-twice")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            (fake_bin / "specify").write_text(FAKE_SPECIFY)
            (fake_bin / "specify").chmod(0o755)
            fake_codegraph = fake_bin / "codegraph"
            fake_codegraph.write_text("#!/bin/sh\nexit 0\n")
            fake_codegraph.chmod(0o755)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}

            subprocess.run(
                ["./init", "--integration", "codex", "--extension", "codegraph"],
                cwd=repo,
                check=True,
                env=environment,
            )
            init = repo / "scripts/extensions/codegraph/init.py"
            init.write_text(init.read_text().replace(
                "This project is indexed by CodeGraph", "This project has the replacement CodeGraph guidance"
            ))
            subprocess.run(["python3", "scripts/extensions/project.py"], cwd=repo, check=True)

            agents = (repo / "AGENTS.md").read_text()
            self.assertEqual(agents.count("<!-- extension:codegraph:begin -->"), 1)
            self.assertEqual(agents.count("<!-- extension:codegraph:end -->"), 1)
            self.assertIn("This project has the replacement CodeGraph guidance", agents)
            self.assertNotIn("This project is indexed by CodeGraph", agents)

    def test_check_extensions_reports_and_make_agents_repairs_guidance_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "codegraph-guidance-drift")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            for tool, body in (("specify", FAKE_SPECIFY), ("codegraph", "#!/bin/sh\nexit 0\n")):
                (fake_bin / tool).write_text(body)
                (fake_bin / tool).chmod(0o755)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}
            (repo / ".specify").mkdir(exist_ok=True)
            (repo / ".specify/integration.json").write_text(
                json.dumps({"installed_integrations": ["codex"], "default_integration": "codex"})
            )
            subprocess.run(
                ["./init", "--integration", "codex", "--extension", "codegraph"],
                cwd=repo, check=True, env=environment,
            )
            agents = repo / "AGENTS.md"
            agents.write_text(agents.read_text().replace("This project is indexed", "This stale project was indexed"))

            stale = subprocess.run(
                ["make", "check-extensions"], cwd=repo, text=True, capture_output=True,
            )
            self.assertEqual(stale.returncode, 2)
            self.assertIn("codegraph extension block has drifted", stale.stderr)
            subprocess.run(["make", "agents"], cwd=repo, check=True, capture_output=True)
            current = subprocess.run(
                ["make", "check-extensions"], cwd=repo, text=True, capture_output=True,
            )
            self.assertEqual(current.returncode, 0, current.stderr)
            self.assertEqual(agents.read_text().count("<!-- extension:codegraph:begin -->"), 1)

    def test_init_extension_missing_cli_is_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "codegraph-missing")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            (fake_bin / "specify").write_text(FAKE_SPECIFY)
            (fake_bin / "specify").chmod(0o755)
            # No `codegraph` binary on this PATH at all — which has to be arranged, not assumed: the
            # machine running the suite may well have the real CLI installed, and prepending a fake-bin
            # without a stub would still find it further down.
            without_codegraph = os.pathsep.join(
                entry
                for entry in os.environ["PATH"].split(os.pathsep)
                if not os.access(Path(entry) / "codegraph", os.X_OK)
            )
            environment = os.environ | {"PATH": f"{fake_bin}:{without_codegraph}"}

            result = subprocess.run(
                ["./init", "--integration", "codex", "--extension", "codegraph"],
                cwd=repo,
                env=environment,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("CodeGraph CLI not found", result.stderr)
            self.assertIn("./init --extension codegraph", result.stderr)
            self.assertNotIn("<!-- extension:codegraph:begin -->", (repo / "AGENTS.md").read_text())
            self.assertTrue((repo / ".agents/skills/testing/SKILL.md").is_file())

    def test_a_failing_codegraph_install_is_non_fatal_and_says_how_to_retry(self) -> None:
        """`codegraph install` exiting non-zero must not fail `./init`, and must not leave a half-adopted
        project silently: no pointer is written, and the message names the command that finishes the job."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "codegraph-install-fails")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            (fake_bin / "specify").write_text(FAKE_SPECIFY)
            (fake_bin / "specify").chmod(0o755)
            (fake_bin / "codegraph").write_text("#!/bin/sh\nexit 3\n")
            (fake_bin / "codegraph").chmod(0o755)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}

            result = subprocess.run(
                ["./init", "--integration", "codex", "--extension", "codegraph"],
                cwd=repo,
                env=environment,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("exited 3", result.stderr)
            self.assertIn("./init --extension codegraph", result.stderr)
            self.assertNotIn("<!-- extension:codegraph:begin -->", (repo / "AGENTS.md").read_text())

    def test_init_rejects_an_unknown_extension_key_without_failing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "unknown-extension")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            (fake_bin / "specify").write_text(FAKE_SPECIFY)
            (fake_bin / "specify").chmod(0o755)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}

            result = subprocess.run(
                ["./init", "--integration", "codex", "--extension", "not-a-real-extension"],
                cwd=repo,
                env=environment,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn('Unknown extension "not-a-real-extension"', result.stderr)
            self.assertTrue((repo / ".agents/skills/testing/SKILL.md").is_file())


class ExtensionsCatalogTest(FactoryTestCase):
    def test_the_shipped_extensions_are_valid(self) -> None:
        validate_extensions(CATALOG)
        self.assertEqual(sorted(known_extensions(CATALOG)), ["codegraph", "uipro", "ux-gates"])

    def test_every_extension_exposes_replaceable_side_effect_free_guidance(self) -> None:
        for key in known_extensions(CATALOG):
            source = (
                Path(__file__).parents[1] / f"assets/toolkit/scripts/extensions/{key}/init.py"
            ).read_text()
            self.assertIn("def project_guidance()", source, key)
            self.assertIn("project_guidance()\n", source, key)
            self.assertIn(f'replace_block("{key}", GUIDANCE)', source, key)

    def test_an_extension_must_declare_a_name_and_a_description(self) -> None:
        for field in ("name", "description"):
            broken = json.loads(json.dumps(CATALOG))
            del broken["extensions"]["codegraph"][field]
            with self.assertRaisesRegex(ValueError, f"must declare a non-empty {field}"):
                validate_extensions(broken)

    def test_an_extension_s_ignore_field_must_be_a_string_when_present(self) -> None:
        broken = json.loads(json.dumps(CATALOG))
        broken["extensions"]["codegraph"]["ignore"] = ["not", "a", "string"]
        with self.assertRaisesRegex(ValueError, "ignore must be a string"):
            validate_extensions(broken)

    def test_an_extension_refuses_an_unknown_field(self) -> None:
        broken = json.loads(json.dumps(CATALOG))
        broken["extensions"]["codegraph"]["cli"] = "codegraph"
        with self.assertRaisesRegex(ValueError, "unknown field"):
            validate_extensions(broken)
