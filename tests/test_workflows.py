"""What CI runs, and — the part that matters — what it does not.

Theme A's division is enforced here because nothing else can enforce it: the keel's gate proves the
conformance suite works against one toy package in-tree, each package proves itself against a pinned
keel in its own repository, and the keel's release proves the published packages once. A keel whose
gate ran every package's variants would be a keel nobody could change without them, and that is a
property of a YAML file rather than of any Python, so a test reads the YAML.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github/workflows"


def read(name: str) -> str:
    """The workflow as written. Read as text and not as parsed YAML, deliberately: the keel ships with
    no dependency at all and this would be the first one past ruff and mypy, bought to check four
    assertions about a file whose shape is as visible in its text as in its tree."""
    return (WORKFLOWS / name).read_text(encoding="utf-8")


class GateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.gate = read("verify.yml")

    def test_the_gate_runs_on_every_platform_the_command_is_run_from(self) -> None:
        named = set(re.findall(r"(ubuntu|macos|windows)-latest", self.gate))
        self.assertEqual(named, {"ubuntu", "macos", "windows"})

    def test_the_gate_fetches_the_whole_history(self) -> None:
        """`scripts/progress.py --check` reads the `Slice-done:` trailers, and a shallow clone has none."""
        self.assertRegex(self.gate, r"actions/checkout@v\d+\s*\n\s*with:\s*\n\s*fetch-depth: 0")

    def test_the_gate_reads_no_package_but_the_toy(self) -> None:
        """The line theme A draws. A keel whose gate checks seven packages cannot be changed without
        them, which is the coupling the packages were split out to remove.

        The checkout does take the submodules: the two target pointers are public and anonymous, and the
        structure gate refuses an empty package directory. What the gate may not do is name a language
        package, or run a package's own suite — those run in the package's own repository."""
        for package in ("slipwai-language-go", "slipwai-language-java", "packages/go", "packages/typescript"):
            with self.subTest(absent=package):
                self.assertNotIn(package, self.gate)
        self.assertIn("submodules: true", self.gate)

    def test_the_gate_runs_the_fast_half_and_never_the_matrix(self) -> None:
        self.assertIn("make verify", self.gate)
        self.assertNotIn("slipwai.matrix", self.gate)


class PublisherFlagTest(unittest.TestCase):
    """`--accept-publisher` is `slipwai extension install`'s and nothing else's.

    `trust.admitted` is called from `extension_install` alone, so the language path never asks about a
    publisher — and a workflow that passed the flag to it got an argument error rather than a no-op. It was
    in both workflows, and neither had ever reached that line.
    """

    def test_no_workflow_passes_it_to_a_language_install(self) -> None:
        for name in ("package.yml", "backstop.yml"):
            with self.subTest(workflow=name):
                for line in read(name).splitlines():
                    said = line.strip()
                    if said.startswith("slipwai install") or "slipwai install \"" in said:
                        self.assertNotIn("--accept-publisher", said)


class PackageWorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = read("package.yml")

    def test_it_is_called_by_a_package_and_never_triggered_here(self) -> None:
        """It is reused, not copied: a package repository calls it, so a fix reaches every package."""
        self.assertIn("workflow_call:", self.workflow)
        for trigger in ("push:", "pull_request:", "schedule:"):
            with self.subTest(trigger=trigger):
                self.assertNotIn(f"\n  {trigger}", self.workflow)

    def test_a_package_names_itself_and_the_keel_it_is_built_for(self) -> None:
        self.assertRegex(self.workflow, r"package:\s*\n(\s+.*\n)*?\s+required: true")
        self.assertIn("keel:", self.workflow)

    def test_a_package_is_proved_with_what_it_is_proved_through_beside_it(self) -> None:
        """The checkout is one directory and conformance reads the directory above it, so without this step
        a framework meets its own family missing and a family meets no framework to be checked through.
        Three of the six published languages were red on exactly that, each saying so in as many words."""
        self.assertIn("Install what this package is proved beside", self.workflow)
        beside = self.workflow[self.workflow.index("Install what this package is proved beside"):
                               self.workflow.index("- name: Conformance")]
        # Installed into the keel's own directory and copied across, because `slipwai install` loads the
        # directory it installs into: installing *into* `$PWD` loads the checkout, and the checkout is the
        # thing whose family is missing — the install refuses with the message it was run to fix.
        self.assertIn('cp -R "$HOME/.slipwai/packages/$sibling" "$PWD/$sibling"', beside)
        # Only the siblings are copied. `$PWD` keeps the checkout as the copy under test.
        self.assertNotIn('cp -R "$HOME/.slipwai/packages/${{ inputs.package }}"', beside)
        # `--accept-publisher` belongs to `slipwai extension install` and to nothing else. The language
        # path does not ask about a publisher, so passing it there is an argument error, not a no-op.
        self.assertNotIn("slipwai install \"$sibling\" --accept-publisher", beside)
        # A framework's family is read from its own manifest; a family's framework is the `beside` input.
        self.assertIn("requires", beside)
        self.assertIn("${{ inputs.beside }}", beside)
        self.assertIn("beside:", self.workflow)

    def test_installing_a_sibling_runs_before_conformance_and_not_after(self) -> None:
        self.assertLess(self.workflow.index("Install what this package is proved beside"),
                        self.workflow.index("python -m slipwai.conformance"))

    def test_only_a_language_is_proved_beside_a_sibling(self) -> None:
        """An extension and a target each have no family and no framework; the step would have nothing to
        read and no manifest to read it from. Named for what *is* proved beside something rather than for
        what is not: the condition was `!= 'extension'`, and the third kind silently took the language's
        path the day it arrived."""
        beside = self.workflow[self.workflow.index("Install what this package is proved beside"):
                               self.workflow.index("- name: Conformance")]
        self.assertIn("if: inputs.kind == 'language'", beside)

    def test_each_kind_is_proved_by_the_suite_that_is_its_own(self) -> None:
        conformance = self.workflow[self.workflow.index("- name: Conformance"):
                                    self.workflow.index("inputs.toolchains")]
        self.assertIn("--extension", conformance)
        self.assertIn("--target", conformance)

    def test_the_matrix_runs_on_a_runner_that_can_build_a_generated_project(self) -> None:
        """The matrix generates a project per row and runs *that project's* own `make verify`, so the runner
        needs the language's own toolchain. It had none, and all four of the first matrix runs said so in
        four different ways: no `uv`, no `covdata`, a JDK too old for release 25, and a Maven wrapper that
        could not fetch Maven."""
        for toolchain in ("go", "node", "java", "uv", "pack"):
            with self.subTest(toolchain=toolchain):
                self.assertIn(f"contains(inputs.toolchains, '{toolchain}')", self.workflow)
        # Only for the matrix: conformance asks the package questions and needs none of this.
        for line in self.workflow.splitlines():
            if "inputs.toolchains" in line:
                self.assertIn("inputs.matrix", line)

    def test_a_toolchain_step_runs_before_the_matrix_and_after_conformance(self) -> None:
        """Conformance is the fast half and should not wait on four installs it does not use."""
        self.assertLess(self.workflow.index("python -m slipwai.conformance"),
                        self.workflow.index("inputs.toolchains"))
        self.assertLess(self.workflow.index("inputs.toolchains"),
                        self.workflow.index("python -m slipwai.matrix"))

    def test_the_matrix_is_opt_in(self) -> None:
        """It builds images and starts containers; a package that has not got that far says so."""
        self.assertRegex(self.workflow, r"matrix:\s*\n(\s+.*\n)*?\s+default: false")

    def test_it_runs_the_conformance_suite_and_the_matrix_only_when_asked(self) -> None:
        conformance = self.workflow.index("python -m slipwai.conformance")
        matrix = self.workflow.index("python -m slipwai.matrix")
        self.assertNotIn("if:", self.workflow[self.workflow.rindex("- name:", 0, conformance):conformance])
        self.assertIn("if:", self.workflow[self.workflow.rindex("- name:", 0, matrix):matrix])

    def test_it_reads_nothing_of_this_repository_but_the_published_keel(self) -> None:
        """A package proves itself against a keel it installs, so a package's CI does not need a
        checkout of the keel and must not quietly depend on one."""
        self.assertIn("pip install", self.workflow)
        self.assertNotIn("slipwai_v2_Fork", self.workflow)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
