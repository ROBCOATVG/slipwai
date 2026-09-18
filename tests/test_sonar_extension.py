"""The Sonar extension's local adoption and scanner routes."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

FAKE_SPECIFY = "#!/bin/sh\nexit 0\n"
TOKEN = "never-put-this-in-an-argument"


def fake_tools(directory: str, scanner: str = "#!/bin/sh\nexit 0\n") -> Path:
    fake_bin = Path(directory) / "fake-bin"
    fake_bin.mkdir()
    for name, body in (("specify", FAKE_SPECIFY), ("sonar-scanner", scanner)):
        (fake_bin / name).write_text(body)
        (fake_bin / name).chmod(0o755)
    return fake_bin


def sonar_environment(fake_bin: Path) -> dict[str, str]:
    return os.environ | {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "SONAR_HOST_URL": "https://sonar.example.test",
        "SONAR_TOKEN": TOKEN,
    }


class SonarExtensionTest(FactoryTestCase):
    def test_adoption_writes_configuration_and_runs_the_standalone_scanner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "sonar-product", profile="standard")
            log = Path(directory) / "sonar-args"
            fake_bin = fake_tools(directory, f"#!/bin/sh\nprintf '%s\\n' \"$@\" > {log}\n")
            environment = sonar_environment(fake_bin)

            subprocess.run(
                ["./init", "--integration", "codex", "--extension", "sonar"],
                cwd=repo,
                check=True,
                env=environment,
            )
            coverage = repo / "apps/service/coverage/lcov.info"
            coverage.parent.mkdir(parents=True)
            coverage.write_text("TN:\n")
            subprocess.run(["make", "sonar"], cwd=repo, check=True, env=environment)

            properties = (repo / "sonar-project.properties").read_text()
            self.assertIn("sonar.projectKey=sonar-product", properties)
            self.assertNotIn(TOKEN, properties)
            arguments = log.read_text()
            self.assertIn("-Dsonar.javascript.lcov.reportPaths=apps/service/coverage/lcov.info", arguments)
            self.assertNotIn(TOKEN, arguments)
            agents = (repo / "AGENTS.md").read_text()
            self.assertIn("<!-- extension:sonar:begin -->", agents)
            self.assertIn("make sonar", agents)
            self.assertEqual(
                json.loads((repo / ".slipwai/extensions.json").read_text()),
                {"schemaVersion": 1, "extensions": ["sonar"]},
            )
            self.assertIn(".scannerwork/", (repo / ".gitignore").read_text())

    def test_missing_scanner_is_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "sonar-missing", profile="standard")
            fake_bin = fake_tools(directory)
            (fake_bin / "sonar-scanner").unlink()
            without_scanner = os.pathsep.join(
                entry
                for entry in os.environ["PATH"].split(os.pathsep)
                if not os.access(Path(entry) / "sonar-scanner", os.X_OK)
            )
            environment = os.environ | {"PATH": f"{fake_bin}:{without_scanner}"}

            result = subprocess.run(
                ["./init", "--integration", "codex", "--extension", "sonar"],
                cwd=repo,
                env=environment,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("Sonar Scanner CLI not found", result.stderr)
            self.assertIn("./init --extension sonar", result.stderr)
            self.assertFalse((repo / "sonar-project.properties").exists())
            self.assertNotIn("<!-- extension:sonar:begin -->", (repo / "AGENTS.md").read_text())

    def test_make_sonar_names_missing_credentials_without_running_the_scanner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "sonar-credentials", profile="standard")
            log = Path(directory) / "sonar-ran"
            fake_bin = fake_tools(directory, f"#!/bin/sh\ntouch {log}\n")
            environment = {
                key: value
                for key, value in os.environ.items()
                if key not in ("SONAR_HOST_URL", "SONAR_TOKEN")
            } | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}
            subprocess.run(
                ["./init", "--integration", "codex", "--extension", "sonar"],
                cwd=repo,
                check=True,
                env=environment,
            )

            result = subprocess.run(
                ["make", "sonar"],
                cwd=repo,
                env=environment,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("SONAR_HOST_URL, SONAR_TOKEN", result.stderr)
            self.assertFalse(log.exists())

    def test_java_uses_maven_without_putting_the_token_on_its_command_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "sonar-java", profile="standard", language="java-spring")
            fake_bin = fake_tools(directory)
            log = Path(directory) / "maven-args"
            wrapper = repo / "apps/service/mvnw"
            wrapper.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > {log}\n")
            wrapper.chmod(0o755)
            environment = sonar_environment(fake_bin)

            subprocess.run(
                ["./init", "--integration", "codex", "--extension", "sonar"],
                cwd=repo,
                check=True,
                env=environment,
            )
            subprocess.run(["make", "sonar"], cwd=repo, check=True, env=environment)

            arguments = log.read_text()
            self.assertIn("sonar:sonar", arguments)
            self.assertIn("-Dsonar.projectKey=sonar-java", arguments)
            self.assertNotIn(TOKEN, arguments)
