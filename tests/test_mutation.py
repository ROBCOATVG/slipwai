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
from slipwai.project.mutation import (
    GO_GREMLINS,
    GO_GREMLINS_CONFIG,
    GO_GREMLINS_REPORT,
    GO_MUTATION_SCRIPT,
    mutation_notes,
)
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
        # The report the run now leaves is named per service for the same reason the gate is: a reader
        # looking for a score needs the path of the one their service wrote.
        self.assertIn("`apps/orders/gremlins.json` and `apps/billing/gremlins.json`", note)
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


    def test_the_note_says_how_to_scope_a_run_and_where_the_report_lands(self) -> None:
        # Both are what the note is for: an unscoped run is priced per repository, and a run whose report
        # was deleted left a log line where the stage's evidence should be.
        note = mutation_notes([service("orders", "go")])
        self.assertIn("make mutation SINCE=", note)
        self.assertIn("`apps/orders/gremlins.json`", note)


class MutationCommandTest(unittest.TestCase):
    def test_the_go_command_says_how_to_scope_and_where_the_report_is(self) -> None:
        # A flag nobody reading `/mutation` knows to pass is a stage that keeps being run at sweep price.
        from slipwai.project.mutation import mutation_command

        self.assertIn("make mutation SINCE=<review-base>", mutation_command(["go"]))
        self.assertIn("gremlins.json", mutation_command(["go", "typescript"]))
        # It is the Go target's flag; a project with no Go service is not told to pass it.
        self.assertNotIn("SINCE", mutation_command(["typescript"]))


class GitignoreTest(unittest.TestCase):
    def test_a_go_projects_mutation_report_is_not_committed(self) -> None:
        # One run on one machine, replaced by the next: the same lifetime as `coverage.out` beside it.
        from slipwai.project.gitignore import build_artifacts

        ignored = build_artifacts(False, [service("orders", "go")])
        self.assertIn(f"{GO_GREMLINS_REPORT}\n", ignored)
        self.assertNotIn(GO_GREMLINS_REPORT, build_artifacts(False, [service("ledger", "java", "spring-boot")]))


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

    def test_the_command_line_is_the_service_and_an_optional_ref(self) -> None:
        self.assertEqual(self.wrapper.arguments(["x", "apps/service"]), (Path("apps/service"), None))
        self.assertEqual(self.wrapper.arguments(["x", "apps/service", "--since", "main"]),
                         (Path("apps/service"), "main"))
        # `$(if $(SINCE),--since $(SINCE))` expands before the path on some lines and after it on others
        # depending on how the recipe is edited; neither ordering is the user's mistake.
        self.assertEqual(self.wrapper.arguments(["x", "--since", "main", "apps/service"]),
                         (Path("apps/service"), "main"))
        self.assertIsNone(self.wrapper.arguments(["x"]))
        self.assertIsNone(self.wrapper.arguments(["x", "apps/service", "--since"]))
        self.assertIsNone(self.wrapper.arguments(["x", "apps/service", "apps/other"]))

    def test_the_projects_own_exclusions_are_read_back_out_of_the_yaml(self) -> None:
        """A scoped run passes `--exclude-files`, which replaces the file's list rather than adding to it,
        so a scope that could not read the file would quietly mutate what the project excluded on purpose."""
        shipped = LANGUAGE_ROOT / "go" / "app" / GO_GREMLINS_CONFIG
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / GO_GREMLINS_CONFIG
            config.write_text(shipped.read_text())
            self.assertEqual(self.wrapper.excluded(config), ["cmd/.*", "eventstorecontract/.*"])
            # An absent file has nothing to carry forward; that is not a failure.
            config.unlink()
            self.assertEqual(self.wrapper.excluded(config), [])
            # Keys of another top-level section are not this section's.
            config.write_text("other:\n  exclude-files:\n    - \"a.go\"\nunleash:\n  integration: true\n")
            self.assertEqual(self.wrapper.excluded(config), [])
            # Quoting styles, a comment line, and a key after the list ending it.
            config.write_text(
                "unleash:\n"
                "  exclude-files:\n"
                "    # the skeleton's own\n"
                "    - \"cmd/.*\"\n"
                "    - 'a b.go'\n"
                "    - bare.go # trailing\n"
                "  threshold:\n"
                "    efficacy: 99.99\n"
            )
            self.assertEqual(self.wrapper.excluded(config), ["cmd/.*", "a b.go", "bare.go"])

    def test_an_unreadable_exclusion_list_is_loud(self) -> None:
        # The failure this refuses: an inline list read as an empty one, and a scoped run that silently
        # mutates the trees the project excluded. Running is not evidence of being configured.
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / GO_GREMLINS_CONFIG
            config.write_text('unleash:\n  exclude-files: ["cmd/.*"]\n')
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.wrapper.excluded(config)

    def test_a_scope_is_the_complement_of_what_changed(self) -> None:
        """Gremlins has no include list, so scoping to a file means excluding every other one by name."""
        with tempfile.TemporaryDirectory() as directory:
            module = Path(directory)
            (module / "cmd" / "serve").mkdir(parents=True)
            for name in ("domain.go", "events.go", "domain_test.go", "cmd/serve/main.go"):
                (module / name).write_text("package x\n")

            self.assertEqual(self.wrapper.sources(module), {"domain.go", "events.go", "cmd/serve/main.go"})
            arguments = self.wrapper.scope(module, {"domain.go"}, ["cmd/.*"])

            # The project's own patterns first, then one anchored pattern per file out of scope. Anchored so
            # `events.go` cannot take `domain/events.go` with it, and never a test file: Gremlins does not
            # mutate one, so excluding it would say something untrue about the scope.
            self.assertEqual(arguments, [
                "--exclude-files", "cmd/.*",
                "--exclude-files", r"^cmd/serve/main\.go$",
                "--exclude-files", r"^events\.go$",
            ])

    def test_a_change_confined_to_an_excluded_tree_scopes_to_nothing_rather_than_red(self) -> None:
        # `cmd/` is wiring the project excludes on purpose. A change that touched only it has no mutant to
        # answer for — and "no mutants" is this script's red, which would be true of the run and false
        # about the change.
        own = ["cmd/.*", "eventstorecontract/.*"]
        self.assertEqual(self.wrapper.mutable({"cmd/serve/main.go"}, own), set())
        self.assertEqual(self.wrapper.mutable({"cmd/serve/main.go", "domain.go"}, own), {"domain.go"})
        self.assertEqual(self.wrapper.mutable({"domain.go"}, []), {"domain.go"})

    def test_the_report_is_copied_out_before_the_staging_tree_goes(self) -> None:
        """The defect this fixes: Gremlins writes the report inside the tree the wrapper deletes, so the
        stage left a scrollback where the slice record expects its evidence."""
        with tempfile.TemporaryDirectory() as staging, tempfile.TemporaryDirectory() as directory:
            service = Path(directory)
            report = Path(staging) / "gremlins.json"
            with contextlib.redirect_stdout(io.StringIO()):
                # Nothing to copy when Gremlins wrote nothing, and that is `assess`'s red, not a crash here.
                self.assertIsNone(self.wrapper.keep_report(report, service))
                report.write_text('{"files": []}')
                kept = self.wrapper.keep_report(report, service)
            self.assertEqual(kept, service / GO_GREMLINS_REPORT)
            self.assertEqual(kept.read_text(), '{"files": []}')

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
