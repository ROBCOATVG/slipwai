"""The build wrapper `slipwai adopt` writes where a Maven or Gradle repository has none.

The first real adoption was a Maven repository that built from the IDE, on a laptop with no `mvn` on PATH, and
its first `verify` said `command not found`. The ecosystem's own answer is the committed wrapper, so what is
gated here is the contract: the survey records the wrapper form, `adopt` writes the wrapper beside the build file
where it is missing — byte for byte the files the factory carries, executable where it must be, committed as the
repository's own rather than the factory's — leaves one that is there alone, writes none for commands a person
pointed at plain `mvn`, and `adopt --refresh` writes it too. Running the wrapper is not gated: it fetches its
build tool from the network, which a unit test does not get to do.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import repository, slipwai
from test_replay import git

from slipwai.wrappers import GRADLE_SOURCE, MAVEN_SOURCE

POM = (
    "<project><modelVersion>4.0.0</modelVersion><groupId>x</groupId><artifactId>x</artifactId>"
    "<version>1</version></project>"
)


class WrapperTest(FactoryTestCase):
    def test_a_maven_repository_without_mvnw_gets_the_wrapper_as_its_own(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {"pom.xml": POM, "src/main/java/A.java": "class A {}\n"})
            result = slipwai(repo, "adopt", "--yes")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                "Wrote the Maven Wrapper for shop (mvnw, mvnw.cmd, .mvn/wrapper/maven-wrapper.properties), since it "
                "had none: its commands run ./mvnw, which fetches Maven 3.9.16 itself",
                result.stdout,
            )
            self.assertNotIn("is not on PATH here", result.stdout, "./mvnw is not a tool to install")
            self.assertEqual((repo / "mvnw").read_bytes(), (MAVEN_SOURCE / "mvnw").read_bytes())
            self.assertEqual((repo / "mvnw.cmd").read_bytes(), (MAVEN_SOURCE / "mvnw.cmd").read_bytes())
            self.assertIn(b"\r\n", (repo / "mvnw.cmd").read_bytes(), "the batch script keeps its CRLF")
            self.assertTrue((repo / "mvnw").stat().st_mode & 0o111, "mvnw is executable")
            self.assertIn("3.9.16", (repo / ".mvn/wrapper/maven-wrapper.properties").read_text())
            shop = json.loads((repo / "project.json").read_text())["deployables"]["shop"]
            self.assertEqual(shop["commands"]["test"], "./mvnw -B -q test")
            self.assertEqual(shop["commands"]["typecheck"], "./mvnw -B -q -DskipTests test-compile")
            # Theirs, not the factory's: committed with the adoption, and not in `.written` for `migrate` to replace.
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")
            self.assertEqual(git(repo, "ls-files", "--stage", "mvnw").stdout.split()[0], "100755")
            written = (repo / "delivery/.written").read_text().splitlines()
            self.assertFalse({"mvnw", "mvnw.cmd", ".mvn/wrapper/maven-wrapper.properties"} & set(written))
            self.assertIn("./mvnw -B -q test", (repo / "delivery/Makefile").read_text())

            refreshed = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            self.assertNotIn("Wrote the Maven Wrapper", refreshed.stdout, "a wrapper that is there is left alone")
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")

    def test_a_gradle_build_below_the_root_gets_the_wrapper_beside_its_build_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "services/api/build.gradle": "plugins { id 'java' }\n",
                "services/api/settings.gradle": "rootProject.name = 'api'\n",
                "README.md": "# Shop\n",
            })
            result = slipwai(repo, "adopt", "--yes")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Wrote the Gradle Wrapper for api (services/api/gradlew, services/api/gradlew.bat, "
                          "services/api/gradle/wrapper/gradle-wrapper.jar, "
                          "services/api/gradle/wrapper/gradle-wrapper.properties)", result.stdout)
            self.assertIn("fetches Gradle 9.7.1 itself", result.stdout)
            api = repo / "services/api"
            jar = (api / "gradle/wrapper/gradle-wrapper.jar").read_bytes()
            self.assertEqual(jar[:4], b"PK\x03\x04", "the jar is a real zip, decoded from the text asset")
            self.assertGreater(len(jar), 40000)
            self.assertEqual((api / "gradlew").read_bytes(), (GRADLE_SOURCE / "gradlew").read_bytes())
            self.assertIn(b"\r\n", (api / "gradlew.bat").read_bytes())
            self.assertTrue((api / "gradlew").stat().st_mode & 0o111)
            self.assertIn("gradle-9.7.1-bin.zip", (api / "gradle/wrapper/gradle-wrapper.properties").read_text())
            commands = json.loads((repo / "project.json").read_text())["deployables"]["api"]["commands"]
            self.assertEqual(commands["test"], "cd services/api && ./gradlew -q test")
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")

    def test_a_wrapper_that_is_there_or_a_command_that_does_not_run_one_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            present = repository(Path(directory), "present", {"pom.xml": POM, "mvnw": "#!/bin/sh\necho theirs\n"})
            result = slipwai(present, "adopt", "--yes")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Wrapper", result.stdout)
            self.assertEqual((present / "mvnw").read_text(), "#!/bin/sh\necho theirs\n", "theirs is untouched")
            self.assertFalse((present / "mvnw.cmd").exists())

            plain = repository(Path(directory), "plain", {"pom.xml": POM})
            result = slipwai(
                plain, "adopt", "--yes", "--command", "plain:install=-", "--command", "plain:typecheck=-",
                "--command", "plain:test=mvn -B -q test",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Wrapper", result.stdout, "a person who chose plain mvn is not handed a wrapper")
            self.assertFalse((plain / "mvnw").exists())
            self.assertIn("`mvn` is not on PATH here", result.stdout) if not _on_path("mvn") else None


def _on_path(tool: str) -> bool:
    import shutil

    return shutil.which(tool) is not None


class AntTest(FactoryTestCase):
    def test_an_ant_build_has_no_wrapper_so_the_runner_installs_ant_until_the_build_moves(self) -> None:
        from slipwai.project.adopted_ci import setup_steps
        from slipwai.services import App
        java = {"kind": "java", "version": "8", "ecosystem": "ant"}
        ant = App("hospital", ".", "application", "java", None, 0, generated=False,
                  commands={"typecheck": "ant -q compile"}, toolchain=java)
        steps = setup_steps([ant])
        self.assertIn("actions/setup-java@v5", steps)
        self.assertIn("command -v ant >/dev/null || sudo apt-get install -y -q ant", steps)
        self.assertIn("Maven or Gradle is the programme's first step", steps)
        maven = App("shop", ".", "application", "java", None, 0, generated=False,
                    commands={"test": "./mvnw -B -q test"}, toolchain={**java, "version": "17", "ecosystem": "maven"})
        self.assertNotIn("apt-get", setup_steps([maven]))
