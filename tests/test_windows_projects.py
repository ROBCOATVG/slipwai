"""A generated project started on Windows: through Git's bash, with Spec Kit's sh scripts and long paths.

What is proved, with Windows pretended where it must be: a `./script` the board starts goes through `bash`,
and every program is looked up on the child's own `PATH` (`CreateProcess` searches the parent's); `./init`
asks Spec Kit for its sh scripts only under Git's bash, which `uname -s` names; and a repository the keel
makes on Windows allows long paths; and a generated project, cloned with `core.autocrlf=true` as Git for
Windows clones, checks `init` out with LF. The windows-latest job runs a generated project for real.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import init_run, scaffold
from slipwai.project import init_script


class StartTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tools = Path(tempfile.mkdtemp())
        self.suffix = ".exe" if os.name == "nt" else ""
        for name in ("bash", "make"):
            program = self.tools / f"{name}{self.suffix}"
            program.write_text("#!/bin/sh\n", encoding="utf-8")
            program.chmod(0o755)

    def test_a_script_goes_through_bash_found_on_the_childs_path(self) -> None:
        argv = init_run.windows_argv(["./init", "--integration", "codex"], str(self.tools))
        self.assertEqual([argv[0].lower(), *argv[1:]],
                         [str(self.tools / f"bash{self.suffix}").lower(), "./init", "--integration", "codex"])

    def test_a_program_is_found_on_the_childs_path(self) -> None:
        argv = init_run.windows_argv(["make", "draft"], str(self.tools))
        self.assertEqual([argv[0].lower(), *argv[1:]], [str(self.tools / f"make{self.suffix}").lower(), "draft"])
        self.assertEqual(init_run.windows_argv(["absent"], str(self.tools)), ["absent"])


@unittest.skipIf(os.name == "nt", "pretends a uname with a shell script")
class SpecKitScriptTest(unittest.TestCase):
    """The `case` line `./init` carries, run under sh with a `uname` that answers as each platform does."""

    def arguments(self, system: str) -> str:
        # The line is read out of the template, not restated here.
        source = Path(init_script.__file__).read_text(encoding="utf-8")
        line = next(one.strip() for one in source.splitlines() if "MINGW*|MSYS*|CYGWIN*" in one)
        fake = Path(tempfile.mkdtemp())
        (fake / "uname").write_text(f"#!/bin/sh\necho {system}\n", encoding="utf-8")
        (fake / "uname").chmod(0o755)
        done = subprocess.run(["sh", "-c", f'{line}\necho "$@"', "init", "--integration", "codex"],
                              capture_output=True, text=True, env={**os.environ, "PATH": f"{fake}:/usr/bin:/bin"})
        return done.stdout.strip()

    def test_only_gits_bash_on_windows_asks_for_sh_scripts(self) -> None:
        self.assertEqual(self.arguments("MINGW64_NT-10.0-26100"), "--script sh --integration codex")
        self.assertEqual(self.arguments("Darwin"), "--integration codex")
        self.assertEqual(self.arguments("Linux"), "--integration codex")


class LongPathsTest(unittest.TestCase):
    def config(self, system: str) -> str:
        repository = Path(tempfile.mkdtemp())
        (repository / "README.md").write_text("x\n", encoding="utf-8")
        with mock.patch.object(sys, "platform", system), mock.patch.object(scaffold.githooks, "install"):
            scaffold.commit_all(repository, "first")
        done = subprocess.run(["git", "config", "--get", "core.longpaths"], cwd=repository, capture_output=True,
                              text=True)
        return done.stdout.strip()

    def test_long_paths_on_windows_and_nothing_new_elsewhere(self) -> None:
        self.assertEqual(self.config("win32"), "true")
        self.assertEqual(self.config("darwin"), "")



class LineEndingTest(unittest.TestCase):
    def test_a_clone_with_autocrlf_keeps_the_scripts_at_lf(self) -> None:
        source = Path(tempfile.mkdtemp())
        (source / ".gitattributes").write_text(scaffold.GITATTRIBUTES, encoding="utf-8")
        for path in ("init", "scripts/verify", "scripts/agents/run.py", "apps/service/scripts/verify",
                     ".githooks/pre-push", "Makefile", "README.md"):
            (source / path).parent.mkdir(parents=True, exist_ok=True)
            (source / path).write_bytes(b"#!/bin/sh\nset -eu\n")
        # A binary under scripts/ with CR LF in it, as a committed `.pyc` is: left byte for byte as it was.
        binary = b"\x00\xa7\r\n\r\n\x01binary\r\n"
        (source / "scripts/agents/__pycache__").mkdir(parents=True)
        (source / "scripts/agents/__pycache__/run.cpython-311.pyc").write_bytes(binary)
        with mock.patch.object(scaffold.githooks, "install"):
            scaffold.commit_all(source, "first")
        self.assertEqual(subprocess.run(["git", "status", "--porcelain"], cwd=source, capture_output=True,
                                        text=True).stdout, "", "nothing reads as modified after the commit")
        clone = Path(tempfile.mkdtemp()) / "clone"
        subprocess.run(["git", "-c", "core.autocrlf=true", "clone", "-q", str(source), str(clone)], check=True)
        for path in ("init", "scripts/verify", "scripts/agents/run.py", "apps/service/scripts/verify",
                     ".githooks/pre-push", "Makefile"):
            self.assertNotIn(b"\r", (clone / path).read_bytes(), path)
        self.assertIn(b"\r\n", (clone / "README.md").read_bytes(), "the control: an unnamed file does get CRLF")
        self.assertEqual((clone / "scripts/agents/__pycache__/run.cpython-311.pyc").read_bytes(), binary)


if __name__ == "__main__":
    unittest.main()
