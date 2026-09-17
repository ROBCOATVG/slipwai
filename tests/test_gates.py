"""The gate scripts a generated project runs, each proved by giving it the violation it exists to catch.

The event model has enough rules to be a suite of its own: `test_gates_event_model.py`.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile

from support import FactoryTestCase, commit_all

from slipwai.assets import TOOLKIT_ROOT
from slipwai.catalog import CATALOG

# Every architecture layer `check-imports.py` has a rule about, read off the gate itself rather than
# listed here. A rule guards a directory by name — `source_files("domain")` — so a layer that gains a
# rule and no emitted directory is a gate guarding nothing, which is the state this test exists to
# refuse: the rules matched nothing at all until an agent happened to invent the layout.
GUARDED_LAYERS = sorted(
    set(re.findall(r'source_files\("(\w+)"\)', (TOOLKIT_ROOT / "scripts/check-imports.py").read_text()))
)


class GatesTest(FactoryTestCase):
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

    def test_contexts_inside_one_service_meet_only_through_public_modules(self) -> None:
        """The modular monolith a project starts as: one service, several bounded contexts as
        `src/<context>/`. Once the manifest lists them, the import gate refuses one context reaching into
        another's insides — its `public` module is the whole of what may be imported — and the model gate
        makes every slice say which context it belongs to. Neither fires while the service holds one."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "monolith", "event-modelling", "typescript")
            gifting = repo / "apps/service/src/gifting/application"
            gifting.mkdir(parents=True)
            (gifting / "pledge.ts").write_text(
                "import { budgetFor } from '../../budgeting/public.js';\n"
                "import { Budget } from '../../budgeting/domain/budget.js';\n"
                "import { budgeting } from './names.js';\n"
                "export const b = [budgetFor, Budget, budgeting];\n"
            )
            # The plan template lays contexts out inside the layer, `domain/<context>/`; the gate keys on the
            # directory bearing the context's name wherever it sits, so that layout is held to the same rule.
            nested = repo / "apps/service/src/domain/budgeting"
            nested.mkdir(parents=True)
            (nested / "rules.ts").write_text(
                "import { pledge } from '../../gifting/application/pledge.js';\nexport const r = pledge;\n"
            )
            (repo / "apps/service/src/budgeting").mkdir()
            (repo / "apps/service/src/composition").mkdir(exist_ok=True)
            # Composition is where the contexts meet, so it may name either's insides.
            (repo / "apps/service/src/composition/wire.ts").write_text(
                "import { Budget } from '../budgeting/domain/budget.js';\nexport const w = Budget;\n"
            )
            # One context declared, or none: no seam, nothing to refuse.
            result = subprocess.run(["make", "check-imports"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

            manifest = json.loads((repo / "project.json").read_text())
            manifest["deployables"]["service"]["contexts"] = ["gifting", "budgeting"]
            (repo / "project.json").write_text(json.dumps(manifest, indent=2) + "\n")
            result = subprocess.run(["make", "check-imports"], cwd=repo, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "apps/service/src/gifting/application/pledge.ts:2: gifting reaches into budgeting", result.stderr
            )
            self.assertIn("through its budgeting/public module", result.stderr)
            self.assertIn("apps/service/src/domain/budgeting/rules.ts:1: budgeting reaches into gifting", result.stderr)
            self.assertNotIn("pledge.ts:1:", result.stderr)
            self.assertNotIn("pledge.ts:3:", result.stderr)
            self.assertNotIn("composition", result.stderr)
            # The list is found in the model, not declared up front: the loop says where that decision is
            # taken, in both profiles, and the modelling skill carries the step.
            self.assertIn("apply Conway's law to the model", (repo / "commands/drive.md").read_text())
            self.assertIn(
                "Apply Conway's Law", (repo / "skills/event-modeling/references/nine-steps.md").read_text()
            )
            standard = self.generate(directory, "plain", "standard", "typescript")
            self.assertIn("*The Language Test*", (standard / "commands/drive.md").read_text())
            self.assertNotIn("Conway", (standard / "commands/drive.md").read_text())

            model = repo / "docs/event-model/model.yaml"

            def slice_yaml(context_line: str, status: str = "modelled") -> str:
                return (
                    "version: 1\nslices:\n  - id: S1\n    name: Pledge a contribution\n    pattern: state-change\n"
                    f"    status: {status}\n    actor: Contributor\n{context_line}"
                    "    frames:\n      - {type: ui, name: PledgeScreen}\n      - {type: cmd, name: Pledge}\n"
                    "      - {type: evt, name: ContributionPledged}\n"
                )

            def check_model() -> subprocess.CompletedProcess:
                return subprocess.run(["make", "check-model"], cwd=repo, text=True, capture_output=True)

            # One service, so `service` stays optional; two contexts in it, so `context` does not.
            model.write_text(slice_yaml(""))
            result = check_model()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("service service holds 2 bounded contexts (gifting, budgeting)", result.stderr)
            self.assertIn("names the one it belongs to in `context`", result.stderr)
            model.write_text(slice_yaml("    context: shipping\n"))
            result = check_model()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("names context 'shipping', which service service does not hold", result.stderr)
            model.write_text(slice_yaml("    context: gifting\n"))
            result = check_model()
            self.assertEqual(result.returncode, 0, result.stderr)
            # Discovery comes before the decision: a proposed slice may still be in no context.
            model.write_text(slice_yaml("", status="proposed"))
            result = check_model()
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_typescript_lint_gate_rejects_a_domain_clock_read(self) -> None:
        """Biome's recommended set, plus the two things it does not ship a rule for.

        `any` is a warning by default and the gate is run with `--error-on-warnings`, so the layer
        override is what makes it an error here rather than a note nobody reads; the clock and the
        random source are a GritQL plugin, because no linter has that rule.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "lint-gate", "standard", "typescript")
            domain = repo / "apps/service/src/domain"
            domain.mkdir(parents=True, exist_ok=True)
            (domain / "stamp.ts").write_text(
                "export function stamp(): number {\n  return Date.now();\n}\n\n"
                "export function pick(): number {\n  return Math.random();\n}\n\n"
                "export function loose(value: any): unknown {\n  return value;\n}\n"
            )

            result = subprocess.run(
                ["make", "lint"],
                cwd=repo,
                text=True,
                capture_output=True,
            )

            # Biome writes its diagnostics to stderr when nothing is attached to a terminal, which is
            # every CI run — so the gate's report is both streams and never one of them.
            reported = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0, reported)
            self.assertIn("The domain must not read the clock", reported)
            self.assertIn("The domain must be deterministic", reported)
            self.assertIn("lint/suspicious/noExplicitAny", reported)

    def test_python_typecheck_gate_is_a_type_check_and_not_a_byte_compile(self) -> None:
        """`make typecheck` used to run `compileall`, which proves only that the files parse.

        The violation is one `compileall` accepts without a murmur and mypy refuses, in a function with no
        annotations of its own — which is most of what a first slice writes, and is checked here only
        because `check_untyped_defs` is on.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "typecheck-gate", "standard", "python")
            self.assertIn("mypy==", (repo / "apps/service/pyproject.toml").read_text())
            (repo / "apps/service/src/typecheck_gate/counting.py").write_text(
                "def total(lines):\n"
                '    """Compiles. Does not type-check: the lengths are ints and the seed is a string."""\n'
                '    return sum(len(line) for line in lines) + "one"\n'
            )

            result = subprocess.run(["make", "typecheck"], cwd=repo, text=True, capture_output=True)

            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("counting.py", result.stdout)
            self.assertIn('Unsupported operand types for + ("int" and "str")', result.stdout)

    def test_a_production_service_wires_its_flag_source_where_its_formatter_wants_it(self) -> None:
        """The flag source is handed to the app only under a target, and each language's formatter owns
        where it may go — so this is the one wiring in the factory a generated project's first `make lint`
        is the judge of. Both failures were real: `gofmt` sorts the import group, so a `flags` path written
        after `observability` is a reformat; `ruff format` gives every argument of an already-exploded call
        a line of its own, so one appended beside the list before it is another."""
        with tempfile.TemporaryDirectory() as directory:
            go = self.generate(
                directory, "flag-format-go", "event-modelling", "go", "none",
                target="aws", http="net-http",
            )
            formatted = subprocess.run(
                ["gofmt", "-l", "apps/service"], cwd=go, text=True, capture_output=True
            )
            self.assertEqual(formatted.stdout.strip(), "", formatted.stdout)

            python = self.generate(
                directory, "flag-format-python", "event-modelling", "python", "none",
                target="aws", http="fastapi",
            )
            entry = (python / "apps/service/src/flag_format_python/main.py").read_text()
            self.assertIn("\n            default_source(),\n", entry)

    def test_migration_gate_holds_schema_change_to_expand_then_contract(self) -> None:
        """A drop, rename, type change or new NOT NULL column must name the earlier additive migration it
        completes, and may not arrive in the same change as it — in SQL and in node-pg-migrate alike, with
        comments ignored and a JavaScript `down` left out of it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "schema-gates", "event-modelling", "typescript", event_store="postgres")
            migrations = repo / "apps/service/migrations"

            def check() -> subprocess.CompletedProcess:
                return subprocess.run(["make", "check-migrations"], cwd=repo, text=True, capture_output=True)

            # The shipped migrations pass: `002` says `TRUNCATE` and `DROP TABLE`, in a REVOKE and in a comment.
            self.assertEqual(check().returncode, 0, check().stderr)
            (migrations / "003_orders_add_status.sql").write_text(
                "ALTER TABLE orders ADD COLUMN status text;\n"
            )
            (migrations / "004_orders_drop_state.js").write_text(
                "export const up = (pgm) => { pgm.dropColumns('orders', ['state']); };\n"
                "export const down = (pgm) => { pgm.dropTable('orders'); };\n"
            )
            result = check()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("004_orders_drop_state.js: drops or renames", result.stderr)
            self.assertNotIn("003_orders_add_status", result.stderr)  # additive, so not a finding
            # Marked, but the expand it names is new in the same change.
            (migrations / "004_orders_drop_state.js").write_text(
                "// contract: 003_orders_add_status\n"
                "export const up = (pgm) => { pgm.dropColumns('orders', ['state']); };\n"
                "export const down = (pgm) => { pgm.dropTable('orders'); };\n"
            )
            result = check()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("is new in this same change", result.stderr)
            # The expand landed earlier; the contract may follow.
            (migrations / "004_orders_drop_state.js").unlink()
            commit_all(repo, "expand")
            (migrations / "004_orders_drop_state.js").write_text(
                "// contract: 003_orders_add_status\n"
                "export const up = (pgm) => { pgm.dropColumns('orders', ['state']); };\n"
            )
            self.assertEqual(check().returncode, 0, check().stderr)
            # A NOT NULL column with no default is a contraction of every INSERT the running release makes,
            # however additive it looks; naming a migration that does not come before it is refused too.
            (migrations / "005_orders_require_status.sql").write_text(
                "-- contract: 006_later\nALTER TABLE orders ADD COLUMN owner text NOT NULL;\n"
            )
            result = check()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("NOT NULL column with no default", result.stderr)
            self.assertIn("not a migration beside it", result.stderr)
            (migrations / "005_orders_require_status.sql").write_text(
                "ALTER TABLE orders ADD COLUMN owner text NOT NULL DEFAULT 'nobody';\n"
            )
            self.assertEqual(check().returncode, 0, check().stderr)
