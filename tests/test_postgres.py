"""The two guarantees about Postgres that the generated gate cannot make, from opposite directions.

The first needs a real database: two appends at one version, exactly one winner. It needs Docker, and it is
the reason the *generated* gate does not — this suite stands in for the `make test-integration` a project
runs outside `make verify`.

The second no local database can catch, which is why it is asserted against the emitted files instead. The
Compose Postgres runs `postgres:17-alpine` with no TLS at all, so it accepts an unencrypted connection and
`make migrate`, `make test-integration` and the suite above all pass against it — while RDS, whose parameter
group has carried `rds.force_ssl = 1` since Postgres 15, refuses the very same connection with SQLSTATE
`28000` on the first deploy. Nothing runnable locally can tell the two apart, so what the project is *told*
in production is checked here directly.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from support import FactoryTestCase, backends_under_test, default_gateways

from slipwai.catalog import axis_default
from slipwai.images import MIGRATIONS_IN_PRODUCTION, POSTGRES_SSLMODE


class ManagedPostgresTest(FactoryTestCase):
    """What a project is told about reaching a Postgres that insists on TLS. Needs no Docker: the failure
    this catches is one a local Postgres cannot produce."""

    def generate_aws(self, directory: str, name: str, backend: str, store: str = "postgres") -> Path:
        return self.generate(
            directory, name, "event-modelling", backend, "none", target="aws",
            event_store=store, http=axis_default("http", backend, "aws"),
        )

    def environment_of(self, repo: Path) -> dict[str, str]:
        """The environment `infra/` puts on this project's one service, both task definitions alike."""
        tfvars = json.loads((repo / "infra/service/project.auto.tfvars.json").read_text())
        return tfvars["services"]["service"]["environment"]

    def test_every_backend_is_told_to_encrypt_its_connection_and_each_in_its_own_dialect(self) -> None:
        """One posture — encrypted, not verified — reached by whichever route each driver actually offers.

        Three answers, not one, every one of them measured against a TLS-enforcing Postgres rather than read
        off the documentation: `no-verify` for TypeScript, whose `pg` reads `PGSSLMODE` with its own
        vocabulary where `require` means *verify* against a CA store Amazon's private RDS root CA is not in;
        `require` for Python and Go, where libpq's `require` already means encrypt-without-verifying and
        `no-verify` is not even a value; and nothing at all for the two Java backends, whose pgjdbc does not
        read the variable — with `PGSSLMODE=disable` exported it still connects over TLS. A value there
        would be a setting with nothing behind it, and this asserts its absence on purpose.
        """
        with tempfile.TemporaryDirectory() as directory:
            for backend in backends_under_test():
                with self.subTest(backend=backend):
                    repo = self.generate_aws(directory, f"tls-{backend}", backend)
                    environment = self.environment_of(repo)
                    expected = POSTGRES_SSLMODE["rds"][backend]
                    self.assertEqual(environment.get("PGSSLMODE"), expected, environment)
                    if expected is None:
                        self.assertNotIn("PGSSLMODE", environment, backend)
                    # Owed to the store, not to the migration strategy — which is what the two Java
                    # backends show from the other side: they run no migrate task at all (their framework
                    # migrates as it starts) and their `environment` is decided by the two answers
                    # independently. Gating the store's contribution on the migration would have handed the
                    # fix to only some of the services that need it.
                    for name, value in MIGRATIONS_IN_PRODUCTION[backend].get("environment", {}).items():
                        self.assertEqual(environment.get(name), value, environment)

    def test_both_task_definitions_read_the_one_environment_and_the_url_carries_no_sslmode(self) -> None:
        """The service and the migrate task cannot disagree about how they reach the same database — and the
        shared `DATABASE_URL` says nothing about TLS, because an `sslmode` in it means a different thing to
        each of the five drivers that read it (and, for `pg`, overrides `PGSSLMODE` as well)."""
        with tempfile.TemporaryDirectory() as directory:
            # TypeScript because it is the backend whose migrations run as a one-off task *and* whose driver
            # needs the value the other four cannot take: both halves of the bug in one project.
            repo = self.generate_aws(directory, "tls-shape", "typescript")
            service = self.settings((repo / "infra/service/main.tf").read_text())
            rds = self.settings((repo / "infra/service/rds.tf").read_text())
            reads = "local.service_environment[each.key]"
            self.assertIn(reads, service)
            # The hole this fixes: the migrate container set `secrets` and had no `environment` at all, so
            # nothing the factory emitted could reach the one task that runs before anything else.
            self.assertIn(reads, rds)
            # The service's own container also merges `flag_environment`, which is how it is told where its
            # flags come from; the migrate task deliberately does not — see the comment in `rds.tf`.
            self.assertIn("merge(local.service_environment[each.key], local.flag_environment)", service)
            self.assertNotIn("flag_environment", rds)
            self.assertIn('name = "DATABASE_URL"', rds)
            self.assertNotIn("sslmode", rds.lower())
            self.assertIn('"postgres://%s:%s@%s:%d/%s"', rds)
            # The server half, stated rather than inherited, and actually attached to the instance.
            self.assertIn('resource "aws_db_parameter_group" "database"', rds)
            self.assertIn('name  = "rds.force_ssl"', rds)
            self.assertIn('value = "1"', rds)
            self.assertIn("parameter_group_name       = aws_db_parameter_group.database[0].name", rds)
            # And a failed migration prints the log that names the cause, rather than only its exit code.
            deploy = (repo / "scripts/deploy.py").read_text()
            self.assertIn("print(migration_log(task, arn), file=sys.stderr)", deploy)
            self.assertIn('"aws", "logs", "get-log-events"', deploy)
            self.assertIn("log_group  = aws_cloudwatch_log_group.service[name].name", rds)

    def test_a_project_with_no_managed_database_is_told_nothing_about_tls(self) -> None:
        """`--event-store memory` provisions no database, so there is no connection to encrypt and the
        variable would be a setting with nothing behind it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "tls-none", "typescript", store="memory")
            self.assertEqual(self.environment_of(repo), {})
            self.assertEqual((repo / "infra/service/rds.tf").read_text(), "")


class PostgresTest(FactoryTestCase):
    def published_host(self, port: str) -> str:
        """The address a published container port answers on, which is a property of where the tests are
        running rather than of the project.

        On a developer machine, or a runner that is a bare VM, that is `localhost`. A containerised runner
        driving the host's Docker daemon through a mounted socket — Gitea's act_runner in its default mode,
        a GitHub job with `container:` — is not the machine the port is published on, so its own loopback
        refuses the connection, and the host answers instead as `host.docker.internal` where Docker
        publishes that name, or as the container's default gateway where it does not.

        Probed rather than derived from `/.dockerenv`: that file exists both where the daemon is a sibling
        and where dockerd shares this namespace and `localhost` is the right answer, so it cannot tell the
        two apart. The port is the one Docker reported publishing for this project's own container, so
        whatever answers on it is the container Compose just started.
        """
        candidates = ["localhost", "host.docker.internal", *default_gateways()]
        deadline = time.monotonic() + 30
        while True:
            for host in candidates:
                try:
                    with socket.create_connection((host, int(port)), timeout=2):
                        return host
                except OSError:
                    continue
            if time.monotonic() >= deadline:
                break
            time.sleep(1)
        self.fail(
            f"published port {port} answers on none of {', '.join(candidates)}: the containers are healthy, "
            "so this runner reaches a published port by some address none of those name"
        )

    def prove_against_postgres(self, repo: Path, environment: dict[str, str]) -> None:
            subprocess.run(["make", "services-up"], cwd=repo, env=environment, check=True, timeout=600)

            # No container_name, so Compose names it from the project directory. Two checkouts on one
            # machine therefore get their own container instead of fighting over a global name.
            containers = subprocess.run(
                ["docker", "compose", "ps", "--format", "{{.Name}}"],
                cwd=repo,
                env=environment,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.split()
            self.assertEqual(containers, [f"{repo.name}-postgres-1"])

            # POSTGRES_PORT was 0, so the host port is Docker's choice and this is the only place it is
            # written down. The reply is an address, `0.0.0.0:32768` — the bind address is whatever the
            # compose file published on and says nothing about what reaches it from here, so only the
            # port is kept and published_host works out the name that answers.
            published = subprocess.run(
                ["docker", "compose", "port", "postgres", "5432"],
                cwd=repo,
                env=environment,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
            self.assertRegex(published, r":\d+$", "compose published no host port for postgres")
            port = published.rsplit(":", 1)[1]

            # Compose reports healthy on a check that runs inside the container, which says nothing about
            # where the published port is reachable from here.
            environment["DATABASE_URL"] = f"postgres://app:app@{self.published_host(port)}:{port}/app"

            subprocess.run(["make", "migrate"], cwd=repo, env=environment, check=True, timeout=600)
            subprocess.run(
                ["make", "test-integration"], cwd=repo, env=environment, check=True, timeout=600
            )

            # Migration 002 is a trigger rather than a REVOKE, because the application role owns the table
            # and an owner keeps its privileges through a REVOKE. Asserted against the database itself.
            for statement in ("UPDATE events SET event_type = 'x'", "DELETE FROM events"):
                refused = subprocess.run(
                    ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "app", "-d", "app",
                     "-c", statement],
                    cwd=repo,
                    env=environment,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                self.assertNotEqual(refused.returncode, 0, statement)
                self.assertIn("append-only", refused.stdout, statement)

            # And the gate that people run every day still needs none of this.
            subprocess.run(["make", "services-down"], cwd=repo, env=environment, check=True, timeout=600)
            subprocess.run(["make", "verify"], cwd=repo, check=True)

    @unittest.skipUnless(
        shutil.which("docker") is not None
        and subprocess.run(
            ["docker", "compose", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        == 0,
        "needs Docker with Compose v2; the rest of the suite deliberately does not",
    )
    def test_the_postgres_event_store_passes_its_contract_against_a_real_database(self) -> None:
        """The other half of the gate, end to end: Compose up, migrations applied, the same contract the
        in-memory adapter passes run against real Postgres — plus the race only a real store can lose."""
        with tempfile.TemporaryDirectory() as directory:
            # Compose derives its project name — and so every container, network and volume name — from
            # the basename of the directory holding the compose file, not from the path above it. A
            # constant basename under a random temporary directory therefore reads as unique and is not:
            # two of these running at once on one Docker daemon claim the same `real-store_default` and
            # the same `real-store-postgres-1`, and each tears down what the other just created. The
            # runner this project uses is a developer machine, so the second copy is a `make verify` in
            # another terminal as easily as a second CI job. The pid makes the name this process's own.
            repo = self.generate(
                directory,
                f"real-store-{os.getpid()}",
                "event-modelling",
                "typescript",
                "none",
                event_store="postgres",
            )
            # A host port is machine-global too, and no pid arithmetic makes one unique — a port derived
            # from the pid is still a guess about what else is bound. `0` asks Docker to publish on a free
            # one and settles it in the only place that knows: `docker compose port` reads back what was
            # actually bound, once the containers are up. The default stays 5433 for a real project, which
            # wants an address it can write down; only this test, which just needs *a* reachable database,
            # gives up naming it. The *host* half of DATABASE_URL likewise is not known until the
            # containers are up, so prove_against_postgres fills it in; see published_host.
            environment = {**os.environ, "POSTGRES_PORT": "0"}

            def compose_down() -> None:
                subprocess.run(
                    ["docker", "compose", "down", "-v"],
                    cwd=repo,
                    env=environment,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            # try/finally rather than addCleanup: cleanup has to happen while the temporary directory —
            # and with it the compose file that names the project — still exists.
            try:
                self.prove_against_postgres(repo, environment)
            finally:
                compose_down()
