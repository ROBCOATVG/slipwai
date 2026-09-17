"""The note the Makefile carries above `make mutation`, and the files it names.

The note is the one per-backend answer no gate reports on (docs/backend-obligations.md section 3), and the
target it explains is run by no gate at either level. What it can be held to is that it names the project's
own files — the Go service's `.gremlins.yaml`, the Spring service's `pom.xml` — for every service of that
backend, and never the template's word for them.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from slipwai.assets import LANGUAGE_ROOT
from slipwai.project.languages.go import GO_COVERAGE_SCRIPT, GO_GREMLINS_TOKEN
from slipwai.project.mutation import GO_GREMLINS, GO_MUTATION_SCRIPT, mutation_notes
from slipwai.services import App


def script(relative: str) -> Any:
    """One of the Go gate scripts, imported from its asset so its functions can be held to their docstrings."""
    path = LANGUAGE_ROOT / "go" / relative
    specification = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def service(name: str, language: str, framework: str | None = None) -> App:
    return App(name, f"apps/{name}", "service", language, framework, 3000)


class MutationNoteTest(unittest.TestCase):
    def test_go_note_names_every_go_services_gate_file(self) -> None:
        note = mutation_notes([service("orders", "go"), service("billing", "go")])

        self.assertIn("`apps/orders/.gremlins.yaml` and `apps/billing/.gremlins.yaml`", note)
        self.assertNotIn("__APP__", note)
        # One note for the backend, however many services are written on it.
        self.assertEqual(note.count("Wired up: Gremlins"), 1)

    def test_each_backend_names_its_own_files(self) -> None:
        note = mutation_notes([service("orders", "go"), service("ledger", "java", "spring-boot")])

        self.assertIn("`apps/orders/.gremlins.yaml`", note)
        self.assertIn("`apps/ledger/pom.xml`", note)
        self.assertNotIn("`apps/orders/pom.xml`", note)
        self.assertNotIn("`apps/ledger/.gremlins.yaml`", note)
        self.assertNotIn("__APP__", note)

    def test_gremlins_is_pinned_to_a_release(self) -> None:
        # `@latest` is the floating version the constitution forbids anywhere the pipeline reads; a release
        # tag is the same tool on every machine and every run.
        self.assertRegex(GO_GREMLINS, r"^github\.com/go-gremlins/gremlins/cmd/gremlins@v\d+\.\d+\.\d+$")

    def test_the_go_note_names_the_wrapper_and_the_coverage_gate(self) -> None:
        # The two things the note used to get wrong: it pointed at a coverage gate that did not exist, and
        # it described a recipe that could not build a service importing a workspace module.
        note = mutation_notes([service("orders", "go")])
        self.assertIn(GO_MUTATION_SCRIPT, note)
        self.assertIn(GO_COVERAGE_SCRIPT, note)
        self.assertIn("GOWORK=off", note)
        self.assertIn("-tags=integration", note)

    def test_the_wrapper_asset_carries_the_pin_as_a_token(self) -> None:
        # Written once, in `mutation.py`; the asset holds the place `go.py` substitutes it into.
        text = (LANGUAGE_ROOT / "go" / GO_MUTATION_SCRIPT).read_text()
        self.assertEqual(text.count(GO_GREMLINS_TOKEN), 1)
        self.assertNotIn("gremlins@v", text)


class CoverageGateTest(unittest.TestCase):
    """`scripts/go-coverage.py`: what it counts, what it leaves out, and what it fails."""

    def setUp(self) -> None:
        self.gate = script(GO_COVERAGE_SCRIPT)

    def test_entry_points_and_integration_only_suites_are_left_out(self) -> None:
        self.assertEqual(self.gate.out_of_scope({"Name": "main"}), "entry point")
        tagged = {"Name": "eventstorepostgres", "IgnoredGoFiles": ["store_integration_test.go"]}
        self.assertEqual(self.gate.out_of_scope(tagged), "tests run under make test-integration")
        # A package with no tests of its own is counted: with `-coverpkg` another package's tests reach it.
        self.assertIsNone(self.gate.out_of_scope({"Name": "events"}))
        # One in-process test file beside a tagged one is a tested package.
        both = {"Name": "store", "TestGoFiles": ["store_test.go"], "IgnoredGoFiles": ["store_integration_test.go"]}
        self.assertIsNone(self.gate.out_of_scope(both))

    def test_a_block_counts_once_and_is_covered_if_any_test_reached_it(self) -> None:
        profile = "\n".join((
            "mode: set",
            "example.com/p/svc/events/events.go:10.2,12.3 2 0",
            "example.com/p/svc/events/events.go:10.2,12.3 2 1",
            "example.com/p/svc/events/events.go:14.2,15.3 3 0",
            "example.com/p/svc/cmd/serve/main.go:5.1,9.2 4 0",
            "example.com/p/svc/health/health.go:3.1,3.9 1 1",
            "",
        ))
        per_package, total, covered = self.gate.measure(profile, {"example.com/p/svc/cmd/serve": "entry point"})
        self.assertEqual(per_package, {"example.com/p/svc/events": (5, 2), "example.com/p/svc/health": (1, 1)})
        self.assertEqual((total, covered), (6, 3))

    def test_the_gate_fails_below_the_minimum_and_on_nothing_measured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = Path(directory)
            (service / "go.mod").write_text("module example.com/p/svc\n\ngo 1.22\n")
            (service / "svc.go").write_text("package svc\n\nfunc One() int { return 1 }\n")
            (service / "coverage.out").write_text("mode: set\nexample.com/p/svc/svc.go:3.1,3.9 1 1\n")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(self.gate.main(["gate", directory, "70"]), 0)
                self.assertEqual(self.gate.main(["gate", directory, "100.01"]), 1)
                (service / "coverage.out").write_text("mode: set\n")
                self.assertEqual(self.gate.main(["gate", directory, "0"]), 1)
                (service / "coverage.out").unlink()
                self.assertEqual(self.gate.main(["gate", directory, "0"]), 2)


class MutationWrapperTest(unittest.TestCase):
    """`scripts/go-mutation.py`: how it reads the workspace, and what it fails that Gremlins passes."""

    def setUp(self) -> None:
        self.wrapper = script(GO_MUTATION_SCRIPT)

    def test_the_workspace_is_read_in_both_spellings(self) -> None:
        self.assertEqual(self.wrapper.uses("go 1.22\n\nuse ./apps/service\nuse ./packages/x // shared\n"),
                         ["./apps/service", "./packages/x"])
        self.assertEqual(self.wrapper.uses("go 1.22\n\nuse (\n\t./apps/service\n\t./packages/x\n)\n"),
                         ["./apps/service", "./packages/x"])

    def test_a_module_already_required_is_not_required_twice(self) -> None:
        self.assertTrue(self.wrapper.required("require example.com/p/x v0.0.0\n", "example.com/p/x"))
        self.assertTrue(self.wrapper.required("require (\n\texample.com/p/x v0.0.0\n)\n", "example.com/p/x"))
        self.assertFalse(self.wrapper.required("require example.com/p/xy v0.0.0\n", "example.com/p/x"))
        self.assertFalse(self.wrapper.required("module example.com/p/svc\n", "example.com/p/x"))

    def test_nothing_mutated_and_a_timeout_are_red(self) -> None:
        def mutants(*statuses: str) -> str:
            mutations = [{"type": "CONDITIONALS_NEGATION", "status": s, "line": 1, "column": 1} for s in statuses]
            return json.dumps({"files": [{"file_name": "a.go", "mutations": mutations}]})

        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "gremlins.json"
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                # Gremlins writes no report and exits 0 on a module with nothing to mutate.
                self.assertEqual(self.wrapper.assess(report), 1)
                report.write_text(json.dumps({"files": []}))
                self.assertEqual(self.wrapper.assess(report), 1)
                report.write_text(mutants("KILLED", "TIMED OUT"))
                self.assertEqual(self.wrapper.assess(report), 1)
                report.write_text(mutants("KILLED", "KILLED", "NOT COVERED"))
                self.assertEqual(self.wrapper.assess(report), 0)


if __name__ == "__main__":
    unittest.main()
