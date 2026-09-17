"""Every distinct native-gate shape of every backend, generated and held to its own gate.

The slowest suite in the factory by a wide margin: it generates each variant and runs the new
repository's native `make verify`, which means every supported toolchain has to be installed. CI runs it
as one job per backend, and `FACTORY_BACKENDS` is how a job names its slice — so everything in here reads
its backends from `backends_under_test()`, never from the catalog, or five jobs do the same work five times.
The shape of the scaffold itself, across every combination at once, is `tests/test_monorepos.py`; this
suite runs native tools only where a selection gives them a distinct tree to judge.
"""
from __future__ import annotations

import subprocess
import tempfile

from support import FactoryTestCase, backends_under_test

from slipwai.catalog import CATALOG, axis_default


class MatrixTest(FactoryTestCase):
    def test_every_distinct_variant_passes_its_native_repository_gate(self) -> None:
        backends = backends_under_test()
        with tempfile.TemporaryDirectory() as directory:
            # Both profiles and both frontend answers, without multiplying them: adding a frontend does
            # not change a service's native tree, so the other diagonal would run the same backend gate
            # twice. `standard` proves the deliberately smaller service; `event-modelling` proves the
            # larger one and carries the browser gate. The combination sweep itself is the cheap,
            # toolchain-free `test_monorepos.py`.
            self.assertEqual(set(CATALOG["profiles"]), {"standard", "event-modelling"})
            self.assertEqual(set(CATALOG["frontends"]), {"none", "react-vite"})
            native_gate_rows = (("standard", "none"), ("event-modelling", "react-vite"))
            for profile, frontend in native_gate_rows:
                for language in backends:
                    repo = self.generate(
                        directory,
                        f"verify-{profile}-{language}-{frontend}",
                        profile,
                        language,
                        frontend,
                    )
                    subprocess.run(["make", "verify"], cwd=repo, check=True)

            # With every axis answered the gate must still pass on a machine with no Docker at all —
            # that is the whole point of the in-memory adapter the port's contract runs against.
            # Both frontends, because each pins a different committed lockfile and `npm ci` refuses
            # a lockfile that disagrees with its manifest.
            for frontend in CATALOG["frontends"] if "typescript" in backends else ():
                repo = self.generate(
                    directory,
                    f"verify-services-{frontend}",
                    "event-modelling",
                    "typescript",
                    frontend,
                    event_store="postgres",
                    http="fastify",
                    auth="keycloak",
                    users="keycloak",
                )
                subprocess.run(["make", "verify"], cwd=repo, check=True)

            # The maximal selection on every backend, and the SQLite one too — the store that runs
            # its whole contract inside the Docker-free gate rather than outside it.
            #
            # Read from the catalog rather than listed. A hand-kept map here is a sweep that silently
            # skips whichever backend was added last: it does not fail, it just stops covering the new
            # one, and the omission looks exactly like a passing run. `axis_default` is the same answer
            # the prompt and the command line give, so this covers each backend with its own transport.
            transports = {backend: axis_default("http", backend, "none") for backend in backends}
            self.assertNotIn("none", transports.values(), "a backend lost its own transport")
            for language, transport in transports.items():
                for store in ("sqlite", "postgres"):
                    repo = self.generate(
                        directory,
                        f"verify-{language}-{store}",
                        "event-modelling",
                        language,
                        "none",
                        event_store=store,
                        http=transport,
                        auth="keycloak",
                        users="keycloak",
                    )
                    subprocess.run(["make", "verify"], cwd=repo, check=True)

            # Every row above leaves `--target` at `none`, and a production target is what wires the
            # flags route into a project: a file of its own for the frameworks that discover a resource
            # class, an import in the entry point for the rest. Until this row no linter had ever been
            # run over either, and both were wrong the first time one was — a javadoc link 127 columns
            # wide once the project's name became the package, and a Python import added below the line
            # it sorts above. The names are as long as the rows above rather than the short ones these
            # rows would otherwise need, because in Java and Python the name is part of every width.
            # One cloud, not both: nothing under `assets/targets/` is a source file either linter reads,
            # so a second target here would measure the same lines twice. `tests/test_line_widths.py`
            # is the seconds-long sweep over the combinations this one cannot afford.
            for language, transport in transports.items():
                repo = self.generate(
                    directory,
                    f"verify-production-event-modelling-{language}",
                    "event-modelling",
                    language,
                    "none",
                    event_store="postgres",
                    http=transport,
                    auth="cognito",
                    target="aws",
                )
                subprocess.run(["make", "verify"], cwd=repo, check=True)

    def test_a_go_service_importing_a_workspace_module_is_mutation_tested(self) -> None:
        """`make mutation` on the layout `docs/architecture.md` prescribes for shared Go code.

        Gremlins copies only the module it mutates and scores the build failure that follows as a kill, so
        before `scripts/go-mutation.py` this passed with a test that could not fail. Two runs: one whose test
        kills the mutant in the importing package, one whose test cannot — a wrapper that lost the shared
        module would pass both. Here and nowhere else, because `make mutation` is run by no gate in a
        generated project (docs/backend-obligations.md section 2)."""
        if "go" not in backends_under_test():
            self.skipTest("the Go slice of the matrix")
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "mutation-go", "event-modelling", "go", "none", event_store="memory")
            shared = repo / "packages/greeting"
            shared.mkdir()
            (shared / "go.mod").write_text("module example.com/mutation-go/greeting\n\ngo 1.22\n")
            (shared / "greeting.go").write_text(
                'package greeting\n\nfunc Label(ok bool) string {\n\tif ok {\n\t\treturn "ok"\n\t}\n'
                '\treturn "degraded"\n}\n'
            )
            with (repo / "go.work").open("a") as work:
                work.write("use ./packages/greeting\n")
            (repo / "apps/service/health/health.go").write_text(
                'package health\n\nimport "example.com/mutation-go/greeting"\n\n'
                'type Status struct {\n\tStatus string `json:"status"`\n}\n\n'
                'func Check() Status {\n\tlabel := greeting.Label(true)\n\tif label != "ok" {\n'
                '\t\tlabel = "unknown"\n\t}\n\treturn Status{Status: label}\n}\n'
            )
            run = ["make", "mutation"]
            strong = subprocess.run(run, cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(strong.returncode, 0, strong.stdout)
            self.assertIn("staged packages/greeting", strong.stdout)
            self.assertIn("KILLED CONDITIONALS_NEGATION at health/health.go", strong.stdout)
            (repo / "apps/service/health/health_test.go").write_text(
                'package health\n\nimport "testing"\n\n'
                'func TestReportsReady(t *testing.T) {\n\t_ = Check().Status\n}\n'
            )
            weak = subprocess.run(run, cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertNotEqual(weak.returncode, 0, weak.stdout)
            self.assertIn("LIVED CONDITIONALS_NEGATION at health/health.go", weak.stdout)
