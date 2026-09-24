"""The hexagonal import gate, `check-imports.py`: each layer rule proved by the violation it exists to catch, and
by what it must leave alone. Its own suite rather than a section of `test_gates.py`, which it outgrew.
"""
from __future__ import annotations

import re
import subprocess
import tempfile

from support import FactoryTestCase

from slipwai.assets import TOOLKIT_ROOT
from slipwai.catalog import CATALOG

# Every architecture layer `check-imports.py` has a rule about, read off the gate itself rather than
# listed here. A rule guards a directory by name — `source_files("domain")` — so a layer that gains a
# rule and no emitted directory is a gate guarding nothing, which is the state this test exists to
# refuse: the rules matched nothing at all until an agent happened to invent the layout.
GUARDED_LAYERS = sorted(
    set(re.findall(r'source_files\("(\w+)"\)', (TOOLKIT_ROOT / "scripts/check-imports.py").read_text()))
)



class ImportGatesTest(FactoryTestCase):
    def test_every_layer_the_import_gate_guards_is_emitted_on_day_one(self) -> None:
        """A rule about `domain/` is worth nothing in a project that has no `domain/`.

        Each layer arrives as a directory with a README saying what belongs in it and what it may not
        import, in every backend, whichever idiom that backend spells a package in — so the first file
        written into the model lands where the gate is already looking.
        """
        self.assertEqual(GUARDED_LAYERS, ["application", "domain"])
        with tempfile.TemporaryDirectory() as directory:
            for language in CATALOG["backends"]:
                with self.subTest(backend=language):
                    repo = self.generate(directory, f"layers-{language}", language=language)
                    service = repo / "apps/service"
                    for layer in GUARDED_LAYERS:
                        found = [path for path in service.rglob(layer) if path.is_dir()]
                        self.assertEqual(
                            len(found), 1, f"{language}: expected one {layer}/ under apps/service, got {found}"
                        )
                        readme = found[0] / "README.md"
                        self.assertTrue(readme.is_file(), f"{language}: {layer}/ ships without a README")
                        self.assertIn("make check-imports", readme.read_text())

    def test_hexagonal_import_gate_rejects_domain_and_application_violations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "import-gates", "event-modelling", "typescript")
            # A context-based layout, which is where the layer sits once a service holds more than one
            # bounded context — the same layer as `src/domain/`.
            domain = repo / "apps/service/src/billing/domain"
            domain.mkdir(parents=True)
            (domain / "policy.ts").write_text(
                "import { randomUUID } from 'node:crypto';\n"
                "import Fastify from 'fastify';\n"
                "import { z } from 'zod';\n"
                "import { Store } from '../../adapters/driven/store.js';\n"
                "export const id = randomUUID;\nexport const app = Fastify;\n"
                "export const schema = z.string();\nexport type S = typeof Store;\n"
            )
            usecases = repo / "apps/service/src/application/usecases"
            usecases.mkdir(parents=True)
            (usecases / "record.ts").write_text(
                "import { container } from '../../composition/container.js';\nexport const c = container;\n"
            )

            result = subprocess.run(
                ["make", "check-imports"],
                cwd=repo,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("domain imports a Node built-in: node:crypto", result.stderr)
            self.assertIn("domain imports 'fastify'", result.stderr)
            self.assertIn("domain imports an outer layer", result.stderr)
            self.assertIn("application imports an outer layer", result.stderr)
            # The schema library is the one bare specifier the domain may name.
            self.assertNotIn("'zod'", result.stderr)

    def test_a_test_of_the_domain_is_not_domain_code(self) -> None:
        """`adversarial-testing` and `event-modeling-to-code.md` send a Decider's spec to `tests/domain/`, and it
        names the test runner — which the domain may not. The gate that reads `domain/` as a layer has to leave
        that directory's tests, and a test beside the Decider, to the level they are, or the factory's own skill
        writes a file its own gate refuses.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "import-gates-tests", "event-modelling", "typescript")
            spec = repo / "apps/service/tests/domain/billing.spec.ts"
            spec.parent.mkdir(parents=True)
            spec.write_text(
                "import { describe, it } from 'vitest';\n"
                "import { FakeStore } from '../../src/adapters/driven/fake-store.js';\n"
                "describe('billing', () => it('decides', () => FakeStore));\n"
            )
            beside = repo / "apps/service/src/domain/billing/decider.test.ts"
            beside.parent.mkdir(parents=True)
            beside.write_text("import { it } from 'vitest';\nit('decides', () => undefined);\n")

            result = subprocess.run(["make", "check-imports"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

            # And the layer itself is still held: the same import from the Decider is refused.
            (beside.parent / "decider.ts").write_text("import { it } from 'vitest';\nexport const x = it;\n")
            result = subprocess.run(["make", "check-imports"], cwd=repo, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("src/domain/billing/decider.ts:1: domain imports 'vitest'", result.stderr)
            self.assertNotIn(".spec.ts", result.stderr)
            self.assertNotIn(".test.ts", result.stderr)

    def test_hexagonal_import_gate_knows_what_a_framework_is_in_java(self) -> None:
        """Import *direction* is language-neutral; "which package is a framework" is not.

        So the Java policy is asserted the same way the TypeScript one is — by handing the gate the
        violation it exists to catch, and by checking it stays quiet about the standard library, which is
        the half a banned-prefix list gets wrong most easily.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "java-import-gates", "event-modelling", "java-quarkus")
            domain = repo / "apps/service/src/main/java/com/example/javaimportgates/billing/domain"
            domain.mkdir(parents=True)
            (domain / "Policy.java").write_text(
                "package com.example.javaimportgates.billing.domain;\n\n"
                "import io.quarkus.runtime.Startup;\n"
                "import jakarta.inject.Inject;\n"
                "import java.sql.Connection;\n"
                "import java.time.Instant;\n"
                "import java.util.List;\n"
                "import com.example.javaimportgates.adapters.driven.eventstorememory.InMemoryEventStore;\n"
                "\npublic class Policy {\n}\n"
            )
            application = repo / "apps/service/src/main/java/com/example/javaimportgates/application"
            application.mkdir(parents=True, exist_ok=True)
            (application / "Record.java").write_text(
                "package com.example.javaimportgates.application;\n\n"
                "import com.example.javaimportgates.adapters.driven.eventstorememory.InMemoryEventStore;\n"
                "\npublic class Record {\n}\n"
            )

            result = subprocess.run(
                ["make", "check-imports"], cwd=repo, text=True, capture_output=True
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("domain imports a framework or driver package: io.quarkus.runtime.Startup", result.stderr)
            self.assertIn("jakarta.inject.Inject", result.stderr)
            # A driver API that happens to ship with the JDK is still a driver API.
            self.assertIn("java.sql.Connection", result.stderr)
            self.assertIn("domain imports an outer layer", result.stderr)
            self.assertIn("application imports an outer layer", result.stderr)
            # The language itself is not a framework, and a policy that banned it would be useless.
            self.assertNotIn("java.time", result.stderr)
            self.assertNotIn("java.util", result.stderr)
