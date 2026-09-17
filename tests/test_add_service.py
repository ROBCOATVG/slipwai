"""`add-service`: one more service in an existing generated project, from the generator's own code paths.

The proof is the generated project's own gate: a project is scaffolded, `add-service payments` is run inside
it — in the same language, and in another — and its `make verify` is green with two services. Every refusal
is a test of its own, because a refusal that stopped refusing would look exactly like success.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase, commit_all

from slipwai.assets import ROOT, VERSION


def add_service(repo: Path, name: str, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(ROOT / "slipwai"), "add-service", name, *flags], cwd=repo, text=True, capture_output=True
    )


def add_frontend(repo: Path, name: str, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(ROOT / "slipwai"), "add-frontend", name, *flags], cwd=repo, text=True, capture_output=True
    )


def porcelain(repo: Path) -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, check=True, text=True, stdout=subprocess.PIPE
    ).stdout


class AddServiceTest(FactoryTestCase):
    def test_a_project_with_an_added_service_passes_its_own_gate(self) -> None:
        """Three shapes: a Python service beside a TypeScript one (two toolchains, two verify scripts, one
        Makefile), a second TypeScript service (one shared npm lock), and a second Spring service (a second
        Maven build). Each project's own `make verify` is the judge."""
        node = {"event_store": "postgres", "http": "fastify"}
        cases = (
            ("typescript", "react-vite", node, ("--language", "python"), "python"),
            ("typescript", "react-vite", node, (), "typescript"),
            (
                "java-spring",
                "none",
                {"event_store": "sqlite", "http": "spring-web", "auth": "keycloak", "users": "none"},
                (),
                "java",
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, (backend, frontend, axes, flags, language) in enumerate(cases):
                with self.subTest(backend=backend, added=language):
                    repo = self.generate(directory, f"grown-{index}", "event-modelling", backend, frontend, **axes)
                    result = add_service(repo, "payments", *flags)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("added apps/payments", result.stdout)
                    self.assertIn("make verify", result.stdout)

                    manifest = json.loads((repo / "project.json").read_text())
                    payments = manifest["deployables"]["payments"]
                    self.assertEqual(
                        (payments["kind"], payments["path"], payments["port"]), ("service", "apps/payments", 3001)
                    )
                    self.assertEqual(payments["language"], language)
                    # The same skeleton a service of that language starts with, named for itself: a health
                    # capability, the transport, the store adapters and their contract suite.
                    added = repo / "apps/payments"
                    listing = sorted(p.relative_to(added).as_posix() for p in added.rglob("*") if p.is_file())
                    self.assertTrue(any("health" in p.lower() for p in listing), listing)
                    self.assertTrue(any("contract" in p.lower() for p in listing), listing)
                    self.assertFalse([p for p in listing if "deliverystarter" in p or "delivery_starter" in p])
                    self.assertIn("apps/payments", (repo / "Makefile").read_text())
                    self.assertIn("\n  payments:\n", (repo / "docker-compose.yml").read_text())
                    # Not committed: the project decides when.
                    head = subprocess.run(
                        ["git", "rev-list", "--count", "HEAD"], cwd=repo, check=True, text=True, stdout=subprocess.PIPE
                    )
                    self.assertEqual(head.stdout.strip(), "1")
                    self.assertIn("?? apps/payments/", porcelain(repo))

                    subprocess.run(["make", "verify"], cwd=repo, check=True)

    def test_a_service_in_another_language_inherits_what_its_backend_can_carry(self) -> None:
        """The store and the identity provider carry across languages; the transport is per framework."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "mixed", "event-modelling", "typescript", "react-vite",
                event_store="postgres", http="fastify", auth="keycloak",
            )
            result = add_service(repo, "payments", "--language", "python")
            self.assertEqual(result.returncode, 0, result.stderr)
            payments = json.loads((repo / "project.json").read_text())["deployables"]["payments"]
            self.assertEqual(
                payments["selection"],
                {"event-store": "postgres", "http": "fastapi", "auth": "keycloak", "users": "none"},
            )
            self.assertTrue(list((repo / "apps/payments/src").glob("*/adapters/driving/http/auth/oidc_keycloak.py")))
            self.assertTrue((repo / "apps/payments/migrations/apply.py").is_file())
            # A flag wins over inheritance.
            result = add_service(repo, "billing", "--language", "go", "--event-store", "sqlite")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("uncommitted changes", result.stderr)
            commit_all(repo, "payments")
            result = add_service(repo, "billing", "--language", "go", "--event-store", "sqlite", "--auth", "none")
            self.assertEqual(result.returncode, 0, result.stderr)
            billing = json.loads((repo / "project.json").read_text())["deployables"]["billing"]
            self.assertEqual(
                billing["selection"],
                {"event-store": "sqlite", "http": "net-http", "auth": "none", "users": "none"},
            )
            self.assertTrue((repo / "apps/billing/adapters/driven/eventstoresqlite").is_dir())
            self.assertFalse((repo / "apps/billing/adapters/driving/http/auth").exists())
            # Three languages, one Makefile, one dispatcher and three family scripts; every other service's
            # files are untouched by the third's arrival.
            for script in ("scripts/verify", "scripts/verify-typescript", "scripts/verify-python", "scripts/verify-go"):
                self.assertTrue((repo / script).is_file(), script)
            self.assertIn("go.work", porcelain(repo))
            self.assertTrue((repo / "apps/payments/migrations/apply.py").is_file())

    def test_a_project_gains_a_first_and_a_second_browser_app_and_passes_its_gate(self) -> None:
        """A Go project generated with no frontend gets one; a TypeScript project with one gets a second,
        proxying to a second service. Each project's own `make verify` is the judge."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "headless", "event-modelling", "go", "none", http="net-http")
            result = add_frontend(repo, "web")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("added apps/web", result.stdout)
            manifest = json.loads((repo / "project.json").read_text())
            self.assertEqual(manifest["frontend"], "react-vite")
            self.assertEqual(manifest["deployables"]["web"]["api"], "service")
            self.assertTrue((repo / "package.json").is_file())
            self.assertIn("\ndev-web:", (repo / "Makefile").read_text())
            self.assertIn("\n  web:\n", (repo / "docker-compose.yml").read_text())
            subprocess.run(["make", "verify"], cwd=repo, check=True)

            repo = self.generate(
                directory, "two-screens", "event-modelling", "typescript", "react-vite",
                event_store="sqlite", http="fastify",
            )
            self.assertEqual(add_service(repo, "payments").returncode, 0)
            commit_all(repo, "payments")
            result = add_frontend(repo, "admin", "--api", "payments")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("proxying /api to payments", result.stdout)
            self.assertIn("'http://localhost:3001'", (repo / "apps/admin/vite.config.ts").read_text())
            self.assertIn("API_ORIGIN: http://payments:3001", (repo / "docker-compose.yml").read_text())
            result = add_frontend(repo, "portal")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("uncommitted changes", result.stderr)
            commit_all(repo, "admin")
            result = add_frontend(repo, "portal", "--api", "billing")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("'billing' is not a service", result.stderr)
            subprocess.run(["make", "verify"], cwd=repo, check=True)

    def test_a_second_service_is_pruned_to_what_the_project_actually_has(self) -> None:
        """A project that dropped an answer with `./init` gets a second service without it — read off the
        disk, not off the selection project.json recorded at generation time — unless asked for by name."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "narrowed", "event-modelling", "python", "none",
                event_store="postgres", http="fastapi", auth="keycloak",
            )
            subprocess.run(
                ["python3", "scripts/backing-services.py", "--auth", "none"],
                cwd=repo, check=True, stdout=subprocess.DEVNULL,
            )
            commit_all(repo, "drop keycloak")
            result = add_service(repo, "payments")
            self.assertEqual(result.returncode, 0, result.stderr)
            payments = repo / "apps/payments"
            self.assertTrue(list(payments.glob("src/*/adapters/driving/http/app.py")))
            self.assertTrue((payments / "migrations/apply.py").is_file())
            self.assertFalse(list(payments.glob("src/*/adapters/driving/http/auth")))
            self.assertFalse((payments / "tests/auth").exists())
            # The regenerated files carry no keycloak region either: settled stays settled.
            for relative in ("Makefile", "docker-compose.yml", ".github/workflows/verify.yml"):
                self.assertNotIn("keycloak", (repo / relative).read_text(), relative)
            self.assertIn("backing-service:postgres:begin", (repo / "Makefile").read_text())
            self.assertIn("apps/payments", (repo / "scripts/verify").read_text())
            # Asked for by name, the dropped answer comes back for the new service alone.
            commit_all(repo, "payments")
            result = add_service(repo, "billing", "--auth", "keycloak")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(list((repo / "apps/billing").glob("src/*/adapters/driving/http/auth")))
            self.assertFalse(list(payments.glob("src/*/adapters/driving/http/auth")))
            # Including in the files the app list does not change: the environment template reads the same
            # for one service or three, so only a rewrite brings the asked-for keys back.
            self.assertIn("OIDC_ISSUER=", (repo / ".env.example").read_text())
            self.assertIn("\n  keycloak:\n", (repo / "docker-compose.yml").read_text())

    def test_a_service_says_what_it_owns_and_the_model_gate_makes_slices_choose(self) -> None:
        """A second service is added for a reason. The reason is recorded, shown wherever the services are
        listed, and from then on a modelled slice has to say which service owns it — the placement `/drive`
        used to make by gravity is now a decision the gate can see."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "placed", "event-modelling", "typescript", "none", http="fastify")
            result = add_service(
                repo, "location", "--language", "python",
                "--purpose", "Geocodes places, fuzzes public pins and answers distance searches.",
                "--context", "geography",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("holds the bounded context `geography` and owns: Geocodes places", result.stdout)
            record = json.loads((repo / "project.json").read_text())["deployables"]["location"]
            self.assertEqual(record["purpose"], "Geocodes places, fuzzes public pins and answers distance searches.")
            self.assertEqual(record["contexts"], ["geography"])
            # Everywhere the services are listed says what each is for, so whoever places a slice reads it.
            self.assertIn(
                "- `location` — python, port 3001; context `geography` — Geocodes places",
                (repo / "commands/add-service.md").read_text(),
            )
            architecture = (repo / "docs/architecture.md").read_text()
            self.assertIn("## Bounded contexts", architecture)
            self.assertIn("- `geography` — `apps/location`: Geocodes places", architecture)
            self.assertIn("- `service` — `apps/service` (no purpose recorded yet)", architecture)
            self.assertIn("context `geography`", (repo / "README.md").read_text())
            commit_all(repo, "add location")

            model = repo / "docs/event-model/model.yaml"

            def slice_yaml(service_line: str, status: str = "modelled") -> str:
                return (
                    "version: 1\nslices:\n  - id: S1\n    name: Find tables nearby\n    pattern: state-change\n"
                    f"    status: {status}\n    actor: Player\n{service_line}"
                    "    frames:\n      - {type: ui, name: MapScreen}\n      - {type: cmd, name: SearchNearby}\n"
                    "      - {type: evt, name: NearbySearched}\n"
                )

            def check_model() -> subprocess.CompletedProcess:
                return subprocess.run(["make", "check-model"], cwd=repo, text=True, capture_output=True)

            # Two services, no owner named: the gate says which services there are and what to decide from.
            model.write_text(slice_yaml(""))
            result = check_model()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("this project has 2 services (service, location)", result.stderr)
            self.assertIn("names the one that owns it in `service`", result.stderr)
            # A service the manifest does not list — a rename in one place only.
            model.write_text(slice_yaml("    service: geocoder\n"))
            result = check_model()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("names service 'geocoder', which project.json does not list", result.stderr)
            # Placed: green.
            model.write_text(slice_yaml("    service: location\n"))
            result = check_model()
            self.assertEqual(result.returncode, 0, result.stderr)
            # A proposed slice may still be unplaced — discovery comes before the decision.
            model.write_text(slice_yaml("", status="proposed"))
            result = check_model()
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_the_manifest_records_which_factory_last_wrote_into_the_repository(self) -> None:
        """`add-service` regenerates every project-wide file from the factory it is run from, so the version
        that wrote here has moved even though the one that *generated* the repository has not. A project
        older than the record says so rather than being credited to whichever version added a service."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "provenance", "standard", "go")
            manifest = repo / "project.json"

            self.assertEqual(json.loads(manifest.read_text())["generator"]["generatedWith"], VERSION)
            self.assertEqual(add_service(repo, "billing", "--purpose", "Invoices.").returncode, 0)
            recorded = json.loads(manifest.read_text())["generator"]
            self.assertEqual(recorded, {"name": "slipwai", "generatedWith": VERSION, "updatedWith": VERSION})

            # A repository generated before the factory recorded any of this.
            document = json.loads(manifest.read_text())
            del document["generator"]
            manifest.write_text(json.dumps(document, indent=2) + "\n")
            commit_all(repo, "as a project that predates the record")
            self.assertEqual(add_service(repo, "shipping", "--purpose", "Ships it.").returncode, 0)
            self.assertEqual(
                json.loads(manifest.read_text())["generator"],
                {"name": "slipwai", "generatedWith": None, "updatedWith": VERSION},
            )

    def test_every_refusal_is_plain_and_changes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            elsewhere = Path(directory) / "elsewhere"
            elsewhere.mkdir()
            result = add_service(elsewhere, "payments")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no project.json", result.stderr)
            self.assertFalse((elsewhere / "apps").exists())

            repo = self.generate(directory, "refusing", "event-modelling", "go", "react-vite")
            before = porcelain(repo)
            for name, expected in (
                ("service", "already has an application named 'service'"),
                ("web", "already has an application named 'web'"),
                ("Payments", "cannot name an application"),
                ("pay_ments", "cannot name an application"),
            ):
                with self.subTest(name=name):
                    result = add_service(repo, name)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr)
            # An answer the new service's backend cannot be given is refused the way `generate` refuses it.
            result = add_service(repo, "payments", "--language", "python", "--http", "fastify")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("implemented for the typescript backend only", result.stderr)
            # A directory nobody registered is not silently adopted.
            (repo / "apps/orphan").mkdir()
            result = add_service(repo, "orphan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("apps/orphan already exists", result.stderr)
            (repo / "apps/orphan").rmdir()
            # Uncommitted work is protected, so the undo stays a `git checkout .`.
            (repo / "note.txt").write_text("in flight\n")
            result = add_service(repo, "payments")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("uncommitted changes", result.stderr)
            (repo / "note.txt").unlink()
            self.assertEqual(porcelain(repo), before, "a refusal left something behind")

            # A manifest from a factory that means something else by these fields.
            manifest = repo / "project.json"
            original = manifest.read_text()
            for mutate, expected in (
                (lambda d: d.__setitem__("schema", 99), "schema 99"),
                (lambda d: d.pop("target"), "has no target"),
                (lambda d: d["deployables"]["service"].__setitem__("language", "cobol"), "unknown language"),
                (lambda d: d["deployables"]["service"]["selection"].__setitem__("oidc", "keycloak"), "does not know"),
            ):
                document = json.loads(original)
                mutate(document)
                manifest.write_text(json.dumps(document, indent=2) + "\n")
                commit_all(repo, "another factory's manifest")
                with self.subTest(expected=expected):
                    result = add_service(repo, "payments")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr)
                    self.assertFalse((repo / "apps/payments").exists())
                manifest.write_text(original)
                commit_all(repo, "restore")
