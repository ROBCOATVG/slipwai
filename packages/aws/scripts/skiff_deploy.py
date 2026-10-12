#!/usr/bin/env python3
"""The skiff adapter: one private Lightsail environment, bounded migrations, rolling releases.

The existing deploy helper still owns immutable image resolution, smoke checks, site uploads and release
history. This adapter replaces provider runtime operations, not those shared contracts.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import skiff_migrations

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("_deploy_common", Path(__file__).with_name("_deploy_common.py"))
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("missing deploy helper; regenerate this project with slipwai replay")
common = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(common)


def one_environment(environment: str) -> None:
    if environment != "production":
        raise common.Failure(
            "a skiff has only production; use make deploy ENV=production or slipwai converge --shape liner"
        )


def database_tls(name: str) -> None:
    """Require the same server-side TLS refusal as the liner, before starting any application or migration."""
    def parameter() -> dict:
        document = skiff_migrations.aws("lightsail", "get-relational-database-parameters",
                                         "--relational-database-name", name)
        return next((row for row in document.get("parameters", []) if row.get("parameterName") == "rds.force_ssl"), {})
    found = parameter()
    if found.get("parameterValue") == "1":
        return
    if not found.get("isModifiable") or found.get("applyType") != "dynamic":
        raise common.Failure(
            f"{name} cannot confirm immediate server TLS enforcement; inspect "
            "aws lightsail get-relational-database-parameters "
            f"--relational-database-name {name} and set rds.force_ssl=1 before re-running make deploy ENV=production"
        )
    skiff_migrations.payload("lightsail", "update-relational-database-parameters", {
        "relationalDatabaseName": name,
        "parameters": [{"parameterName": "rds.force_ssl", "parameterValue": "1", "applyMethod": "immediate"}],
    })
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if parameter().get("parameterValue") == "1":
            return
        time.sleep(2)
    raise common.Failure(
        f"{name} did not confirm TLS enforcement; inspect its parameters and retry make deploy ENV=production"
    )


def migrations(found: dict, images: dict[str, str]) -> None:
    document = json.loads(common.TFVARS.read_text(encoding="utf-8"))
    for name, service in document.get("services", {}).items():
        command, image_name = service.get("migrate_command"), service.get("migrate_image")
        if command is None and image_name is None:
            continue
        environment = {**service.get("environment", {}), "DATABASE_URL": found["database_url"]}
        skiff_migrations.migrate(document["project"], name, images[image_name or name], command,
                                 environment, ROOT / ".build/migration-logs")


def data_boundary(found: dict, document: dict) -> None:
    if found.get("database_name") and not any(
        service.get("store") == "rds" for service in document.get("services", {}).values()
    ):
        raise common.Failure(
            "this deployed skiff still owns a database, but the proposed selection removed it. Restore the "
            "Postgres selection before make deploy, or run slipwai converge --shape liner and preserve the "
            "database/state until verified data transfer. No apply or deletion has run."
        )


def prepared(environment: str, images: dict[str, str]) -> dict:
    one_environment(environment)
    common.select_workspace(environment)
    document = json.loads(common.TFVARS.read_text(encoding="utf-8"))
    data_boundary(common.outputs(), document)
    if any(service.get("store") == "rds" for service in document.get("services", {}).values()):
        found = common.apply(environment, images, "aws_lightsail_database.database")
        database_tls(found["database_name"])
        return found
    return common.outputs()


def deploy(environment: str) -> None:
    one_environment(environment)
    sha = common.current_sha()
    images = common.images_of(sha)
    migrations(prepared(environment, images), images)
    found = common.apply(environment, images)
    common.upload_site(found, sha, common.site_environment(found))
    common.record_release(environment, sha, images)
    print(f"{environment}: {found['url']}")


def migrate(environment: str) -> None:
    one_environment(environment)
    images = common.images_of(common.current_sha())
    migrations(prepared(environment, images), images)


def flag(arguments: list[str]) -> None:
    environment, service, key, value = arguments
    one_environment(environment)
    if value not in ("on", "off"):
        raise common.Failure("a flag is on or off; run make flag ENV=production KEY=<key> VALUE=on")
    found = common.flag_state(environment)
    data_boundary(found, json.loads(common.TFVARS.read_text(encoding="utf-8")))
    parameter = (found.get("flags", {}).get("parameters") or {}).get(f"{service}/{key}")
    if not parameter:
        raise common.Failure(
            f"{service}/{key} is not declared; add it to infra/service/flags.auto.tfvars and run make deploy"
        )
    history = common.releases(environment)
    if not history:
        raise common.Failure("production has no recorded images; run make deploy ENV=production")
    skiff_migrations.aws(
        "ssm", "put-parameter", "--name", parameter, "--type", "String", "--value", value, "--overwrite",
    )
    live = common.apply(environment, history[0]["images"])
    common.smoke(live["url"])


def no_promotion(_arguments: list[str]) -> None:
    raise common.Failure(
        "a skiff deploys directly to production; run make deploy ENV=production or slipwai converge --shape liner"
    )


def guarded(function, environment: str) -> None:
    one_environment(environment)
    if function is common.rollback:
        common.select_workspace(environment)
        data_boundary(common.outputs(), json.loads(common.TFVARS.read_text(encoding="utf-8")))
    function(environment)


def main(argv: list[str]) -> int:
    common.VERBS.update({
        "deploy": lambda args: deploy(*args), "migrate": lambda args: migrate(*args), "flag": flag,
        "promote": no_promotion, "promoting": no_promotion,
        "rollback": lambda args: guarded(common.rollback, *args),
        "url": lambda args: guarded(common.url, *args), "flags": lambda args: guarded(common.flags, *args),
    })
    try:
        return common.main(argv)
    except skiff_migrations.Failure as fault:
        print(f"deploy: {fault}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
