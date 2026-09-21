"""The Sonar extension's local adoption and scanner routes."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest import mock

from support import FactoryTestCase

FAKE_SPECIFY = "#!/bin/sh\nexit 0\n"
TOKEN = "never-put-this-in-an-argument"


def scanner_module() -> Any:
    path = Path(__file__).parents[1] / "assets/toolkit/scripts/extensions/sonar/scan.py"
    specification = importlib.util.spec_from_file_location("sonar_scan", path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        specification.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


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
    def test_python_and_go_coverage_commands_stay_on_the_sonar_path(self) -> None:
        scanner = scanner_module()
        with tempfile.TemporaryDirectory() as directory:
            scanner.ROOT = Path(directory)
            scanner.SCRIPTS = Path(directory) / "scripts"
            commands: list[list[str]] = []

            def record(command: list[str], cwd: Path, environment: dict[str, str] | None = None) -> int:
                del cwd
                del environment
                commands.append(command)
                return 0

            scanner.run = record
            applications = [
                {"path": "apps/python", "language": "python"},
                {"path": "apps/go", "language": "go"},
            ]
            with (
                mock.patch.object(scanner.shutil, "which", return_value="/bin/tool"),
                mock.patch.object(scanner.subprocess, "run"),
            ):
                self.assertEqual(scanner.generate_coverage(applications), 0)

            rendered = [" ".join(command) for command in commands]
            self.assertTrue(any("coverage==7.16.1 coverage run --source=src -m pytest" in line for line in rendered))
            self.assertTrue(any("coverage==7.16.1 coverage xml -o coverage.xml" in line for line in rendered))
            self.assertIn("go test -coverpkg=./... -coverprofile=coverage.out ./...", rendered)
            self.assertTrue(any("--sonar-output sonar-coverage.out" in line for line in rendered))

    def test_adoption_writes_configuration_and_runs_the_standalone_scanner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "sonar-product", profile="standard")
            log = Path(directory) / "sonar-args"
            coverage_log = Path(directory) / "coverage-args"
            fake_bin = fake_tools(directory, f"#!/bin/sh\nprintf '%s\\n' \"$@\" > {log}\n")
            (fake_bin / "npm").write_text(
                f"#!/bin/sh\nprintf '%s ' \"$@\" >> {coverage_log}; printf '\\n' >> {coverage_log}\n"
                "if [ \"$1\" = '--workspace' ]; then\n"
                "  mkdir -p \"$2/coverage\"\n"
                "  printf 'TN:\\n' > \"$2/coverage/lcov.info\"\n"
                "fi\n"
            )
            (fake_bin / "npm").chmod(0o755)
            environment = sonar_environment(fake_bin)

            subprocess.run(
                ["./init", "--integration", "codex", "--extension", "sonar"],
                cwd=repo,
                check=True,
                env=environment,
            )
            subprocess.run(["make", "sonar"], cwd=repo, check=True, env=environment)

            properties = (repo / "sonar-project.properties").read_text()
            self.assertIn("sonar.projectKey=sonar-product", properties)
            self.assertNotIn(TOKEN, properties)
            arguments = log.read_text()
            self.assertIn("-Dsonar.javascript.lcov.reportPaths=apps/service/coverage/lcov.info", arguments)
            self.assertNotIn(TOKEN, arguments)
            coverage_arguments = coverage_log.read_text()
            self.assertIn("@vitest/coverage-v8@4.1.11", coverage_arguments)
            self.assertIn("--coverage.reporter=lcov", coverage_arguments)
            agents = (repo / "AGENTS.md").read_text()
            self.assertIn("<!-- extension:sonar:begin -->", agents)
            self.assertIn("make sonar", agents)
            self.assertEqual(
                json.loads((repo / ".slipwai/extensions.json").read_text()),
                {"schemaVersion": 1, "extensions": ["sonar"]},
            )
            ignored = (repo / ".gitignore").read_text()
            self.assertIn(".scannerwork/", ignored)
            self.assertIn("sonar-coverage.out", ignored)
            workflow = (repo / ".github/workflows/sonar.yml").read_text()
            self.assertIn("SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}", workflow)
            self.assertIn("hashFiles('sonar-project.properties') != ''", workflow)
            self.assertIn("SonarSource/sonarqube-scan-action@v8.2.2", workflow)
            self.assertIn("scripts/extensions/sonar/scan.py --coverage-only", workflow)
            self.assertIn("-Dsonar.javascript.lcov.reportPaths=apps/service/coverage/lcov.info", workflow)
            self.assertNotIn("sonar", (repo / ".github/workflows/verify.yml").read_text())

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
            wrapper.write_text(
                f"#!/bin/sh\nprintf '%s\\n' \"$@\" >> {log}\n"
                "if [ \"$2\" = 'test' ]; then\n"
                "  mkdir -p target/site/jacoco\n"
                "  printf '<report/>\\n' > target/site/jacoco/jacoco.xml\n"
                "fi\n"
            )
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
            self.assertIn("test", arguments)
            self.assertIn("sonar:sonar", arguments)
            self.assertIn("-Dsonar.projectKey=sonar-java", arguments)
            self.assertIn("-Dsonar.coverage.jacoco.xmlReportPaths=", arguments)
            self.assertNotIn(TOKEN, arguments)
            workflow = (repo / ".github/workflows/sonar.yml").read_text()
            self.assertIn("scripts/extensions/sonar/scan.py --java-only", workflow)
            self.assertNotIn("SonarSource/sonarqube-scan-action", workflow)
            self.assertNotIn("--coverage-only", workflow)

    def test_a_rerun_merges_the_properties_file_rather_than_rewriting_it(self) -> None:
        """SonarCloud requires `sonar.organization` and `project.json` holds no organisation, so the generated
        file is incomplete by construction and the user finishes it by hand. Written unconditionally, the hook
        deleted that edit on every rerun — silently, only where the scanner was installed, and surfacing later
        as an analysis filed against nothing. It is a merge target now, and this is what holds it to that."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "sonar-merged", profile="standard")
            fake_bin = fake_tools(directory)
            environment = sonar_environment(fake_bin)
            init = ["./init", "--integration", "codex", "--extension", "sonar"]
            subprocess.run(init, cwd=repo, check=True, env=environment)

            properties = repo / "sonar-project.properties"
            hand_edited = properties.read_text() + (
                "sonar.organization=the-old-warbook\n"
                "# our exclusions, added by hand\n"
                "sonar.exclusions=**/generated/**\n"
            )
            properties.write_text(hand_edited)

            subprocess.run(init, cwd=repo, check=True, env=environment)

            after = properties.read_text()
            # Every line the extension does not own survives, comment and all.
            self.assertIn("sonar.organization=the-old-warbook", after)
            self.assertIn("# our exclusions, added by hand", after)
            self.assertIn("sonar.exclusions=**/generated/**", after)
            # The keys it does own are written once, from the manifest, not duplicated by the rerun.
            self.assertEqual(after.count("sonar.projectKey=sonar-merged"), 1)
            self.assertEqual(after.count("sonar.projectName="), 1)
            self.assertEqual(after.count("sonar.sourceEncoding=UTF-8"), 1)
            self.assertEqual(after.count("# Generated by ./init --extension sonar"), 1)
            # And a third run is a no-op: the merge is idempotent, not merely non-destructive.
            subprocess.run(init, cwd=repo, check=True, env=environment)
            self.assertEqual(properties.read_text(), after)
