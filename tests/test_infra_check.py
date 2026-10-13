"""The reading of a project's stacks that a crossing does last, and that nothing else can do at all.

A generated project's own gate runs with no provider plugins and no cloud credential, by design, so the
first thing that reads these files for real is the deploy — on a runner, after a merge to trunk. The fault
this exists for travelled exactly that far: a factory landed a second implementation of one block, two
files declared the same name, and the stack would not parse. One command said so, four hours later.

So the structural half needs nothing installed and always runs. The `tofu` half is the real answer and
only ever adds to what the first one found.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.infra_check import check, declared_in, duplicates, locals_of, stacks, validated

ONE = """
locals {
  wanted = true
  web_environment = {
    NAME = "a value with = in it"
  }
}

resource "cloud_pool" "players" {
  name = "players"
}

variable "callback_urls" {
  type = list(string)
}
"""


class ReadingTest(unittest.TestCase):
    def test_every_local_a_file_declares_is_found_and_nothing_inside_one_is(self) -> None:
        """A local's own value may be an object full of assignments; those are not locals."""
        self.assertEqual(locals_of(ONE), ["wanted", "web_environment"])

    def test_the_addressable_names_are_read_whatever_product_they_name(self) -> None:
        self.assertEqual(declared_in(ONE),
                         ['resource "cloud_pool" "players"', 'variable "callback_urls"'])


class DuplicateTest(unittest.TestCase):
    """One module, one namespace: a name two files of one directory both declare refuses the stack."""

    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.stack = Path(scratch.name) / "infra/service"
        self.stack.mkdir(parents=True)

    def write(self, name: str, text: str) -> None:
        (self.stack / name).write_text(text, encoding="utf-8")

    def test_one_block_implemented_twice_is_named_with_both_files(self) -> None:
        """Which is what a factory that wrote into somebody's infrastructure leaves behind."""
        self.write("theirs.tf", "locals {\n  web_environment = {}\n}\n")
        self.write("ours.tf", "locals {\n  web_environment = {}\n}\n")
        said = duplicates(self.stack)
        self.assertEqual(len(said), 1, said)
        self.assertIn("local web_environment", said[0])
        self.assertIn("ours.tf", said[0])
        self.assertIn("theirs.tf", said[0])

    def test_a_resource_address_declared_twice_is_the_same_fault(self) -> None:
        self.write("a.tf", 'resource "cloud_pool" "players" {}\n')
        self.write("b.tf", 'resource "cloud_pool" "players" {}\n')
        self.assertIn('resource "cloud_pool" "players"', duplicates(self.stack)[0])

    def test_one_file_declaring_a_name_once_is_nothing(self) -> None:
        self.write("a.tf", ONE)
        self.assertEqual(duplicates(self.stack), [])

    def test_the_same_name_in_two_stacks_is_two_modules_and_not_a_duplicate(self) -> None:
        other = self.stack.parent / "bootstrap"
        other.mkdir()
        self.write("a.tf", "locals {\n  wanted = true\n}\n")
        (other / "a.tf").write_text("locals {\n  wanted = true\n}\n", encoding="utf-8")
        root = self.stack.parent.parent
        self.assertEqual(stacks(root), [other, self.stack])
        self.assertEqual(check(root, run=accepts), [])

    def test_a_project_with_no_infra_is_not_a_project_this_has_anything_to_say_about(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(stacks(Path(empty)), [])
            self.assertEqual(check(Path(empty), run=unreachable), [])


def unreachable(*_: object, **__: object) -> subprocess.CompletedProcess:
    raise AssertionError("nothing may be run for a project with no stack to read")


def accepts(*_: object, **__: object) -> subprocess.CompletedProcess:
    """A tool that is installed and says the stack is fine, so only the structural reading can speak."""
    return subprocess.CompletedProcess(["tofu"], 0, "", "")


class ValidateTest(unittest.TestCase):
    """The half that needs a tool, which is allowed to be absent and allowed to be uninitialised."""

    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.stack = Path(scratch.name)
        (self.stack / "main.tf").write_text("locals {\n  a = 1\n}\n", encoding="utf-8")

    def answer(self, code: int, said: str) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(["tofu"], code, "", said)

    def test_a_refusal_is_reported_with_what_it_said(self) -> None:
        found = validated(self.stack, lambda *a, **k: self.answer(1, "Error: Duplicate local value"))
        self.assertIsNotNone(found)
        self.assertIn("Duplicate local value", str(found))

    def test_asking_to_be_initialised_is_not_a_verdict_on_the_files(self) -> None:
        """Running `init` reaches a network and writes plugins into somebody's tree, which a crossing may
        not do on its own — so not initialised means this did not check, not that something is wrong."""
        said = "Error: Missing required providers. Please run tofu init."
        self.assertIsNone(validated(self.stack, lambda *a, **k: self.answer(1, said)))

    def test_a_stack_it_accepts_says_nothing(self) -> None:
        self.assertIsNone(validated(self.stack, lambda *a, **k: self.answer(0, "")))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
