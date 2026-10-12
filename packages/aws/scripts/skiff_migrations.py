#!/usr/bin/env python3
"""Bounded migrations inside a temporary Lightsail service, never on the public database network.

Lightsail has no job exit-status API. A derivative of the immutable migration image adds a pinned static
shell, emits an exact run-id result marker, then stays alive until the controller reads it. ACTIVE alone
never means success. Cleanup checks the ownership tag before deleting a service and removes only its
own ECR policy statement/image tag. No cloud resource is created merely by importing this module.
"""
from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

# Official BusyBox 1.37.0-musl multi-platform digest, verified with Docker before this module landed.
SHELL_IMAGE = "busybox@sha256:5cec3fc171c87218698e85a52af7087de727372aae264a787b8112901a5b0092"
MINUTES = 15


class Failure(Exception):
    """A migration whose outcome is unknown or failed. Both stop the deploy."""


def run(command: list[str], *, capture: bool = True, cwd: Path | None = None) -> str:
    print("+", " ".join(command), file=sys.stderr, flush=True)
    try:
        done = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=120, check=False)
    except subprocess.TimeoutExpired as fault:
        raise Failure(
            f"{command[0]} exceeded its bounded command deadline; re-run make migrate-remote ENV=production"
        ) from fault
    if done.returncode:
        raise Failure(
            f"{command[0]} exited {done.returncode}: {done.stderr.strip()}; fix what it reports, then "
            "re-run make migrate-remote ENV=production"
        )
    if not capture:
        print(done.stdout, file=sys.stderr, end="")
    return done.stdout


def aws(service: str, verb: str, *arguments: str) -> dict:
    return json.loads(run(["aws", service, verb, *arguments, "--output", "json", "--no-cli-pager",
                           "--cli-connect-timeout", "10", "--cli-read-timeout", "30"]))


def payload(service: str, verb: str, document: dict) -> dict:
    """Secrets go through a private temporary file, never command text, stdout or a retained wrapper image."""
    with tempfile.TemporaryDirectory(prefix="slipwai-migration-payload-") as directory:
        path = Path(directory) / "request.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        path.chmod(0o600)
        return aws(service, verb, "--cli-input-json", f"file://{path}")


def wrapper(command: list[str], token: str) -> str:
    return (f"set +e\n{shlex.join(command)}\nresult=$?\n"
            f"printf '%s:%s\\n' 'slipwai-migration:{token}' \"$result\"\n"
            "while :; do /slipwai/busybox sleep 30; done\n")


def wrapped_image(image: str, command: list[str] | None, token: str) -> tuple[str, str]:
    if "@sha256:" not in image or any(character.isspace() for character in image):
        raise Failure("migration images must be immutable digests; run make build push")
    run(["docker", "pull", "--platform", "linux/amd64", image])
    config = json.loads(run(["docker", "image", "inspect", image]))[0]["Config"]
    # Buildpack web entrypoints ignore a supplied command. Match the liner's proven migration contract:
    # an explicit command goes through the lifecycle launcher; a separate migrate image runs as built.
    launch = (["/cnb/lifecycle/launcher", *command] if command is not None else
              [*(config.get("Entrypoint") or []), *(config.get("Cmd") or [])])
    if not launch or not all(isinstance(word, str) and word for word in launch):
        raise Failure("migration image has no launch command; set its OCI entrypoint and run make build push")
    repository = image.split("@", 1)[0]
    tag = f"{repository}:slipwai-migrate-{token}"
    with tempfile.TemporaryDirectory(prefix="slipwai-migration-image-") as directory:
        root = Path(directory)
        (root / "wrapper.sh").write_text(wrapper(launch, token), encoding="utf-8")
        (root / "Dockerfile").write_text(
            f"FROM {SHELL_IMAGE} AS shell\nFROM {image}\n"
            "COPY --from=shell /bin/busybox /slipwai/busybox\nCOPY wrapper.sh /slipwai-migration\n"
            'ENTRYPOINT ["/slipwai/busybox", "sh", "/slipwai-migration"]\nCMD []\n', encoding="utf-8",
        )
        run(["docker", "build", "--platform", "linux/amd64", "-t", tag, "."], cwd=root)
    run(["docker", "push", tag])
    digests = json.loads(run(["docker", "image", "inspect", tag]))[0].get("RepoDigests") or []
    matching = [digest for digest in digests if digest.startswith(repository + "@sha256:")]
    if not matching:
        raise Failure("the migration wrapper has no pushed digest; run make build push and retry")
    return matching[0], repository.split("/", 1)[1]


def policy(repository: str) -> dict:
    try:
        document = json.loads(aws("ecr", "get-repository-policy", "--repository-name", repository)["policyText"])
        statements = document.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]
        if not isinstance(statements, list) or not all(isinstance(line, dict) for line in statements):
            raise Failure("ECR policy has invalid statements; inspect aws ecr get-repository-policy before retrying")
        document["Statement"] = statements
        return document
    except Failure as fault:
        if "RepositoryPolicyNotFoundException" not in str(fault):
            raise
        return {"Version": "2012-10-17", "Statement": []}


def loan(repository: str, principal: str, token: str) -> None:
    current = policy(repository)
    current["Statement"].append({"Sid": f"Migration{token}", "Effect": "Allow",
                                 "Principal": {"AWS": principal},
                                 "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]})
    payload("ecr", "set-repository-policy", {"repositoryName": repository, "policyText": json.dumps(current)})


def remove_loan(repository: str, token: str) -> None:
    current = policy(repository)
    remaining = [line for line in current["Statement"] if line.get("Sid") != f"Migration{token}"]
    if remaining == current["Statement"]:
        return
    if remaining:
        current["Statement"] = remaining
        payload("ecr", "set-repository-policy", {"repositoryName": repository, "policyText": json.dumps(current)})
    else:
        aws("ecr", "delete-repository-policy", "--repository-name", repository)


def owned_service(name: str, token: str) -> dict | None:
    try:
        found = aws("lightsail", "get-container-services", "--service-name", name).get("containerServices") or []
    except Failure as fault:
        if "NotFoundException" in str(fault):
            return None
        raise
    if not found:
        return None
    service = found[0]
    if not any(tag.get("key") == "SlipwaiMigration" and tag.get("value") == token for tag in service.get("tags", [])):
        raise Failure(
            f"refusing to delete unowned Lightsail service {name}; inspect it with aws lightsail get-container-services"
        )
    return service


def ready(name: str, token: str, deadline: float) -> str:
    while time.monotonic() < deadline:
        service = owned_service(name, token)
        if service and service.get("state") == "FAILED":
            raise Failure(f"temporary service {name} failed to start; inspect aws lightsail get-container-services")
        principal = ((service or {}).get("privateRegistryAccess", {}).get("ecrImagePullerRole", {}).get("principalArn"))
        if service and service.get("state") == "READY" and principal:
            return principal
        time.sleep(2)
    raise Failure(
        f"temporary service {name} did not become ready before its deadline; retry make migrate-remote ENV=production"
    )


def result(name: str, token: str, deadline: float, log: list[str]) -> None:
    marker = f"slipwai-migration:{token}:"
    while time.monotonic() < deadline:
        page = aws("lightsail", "get-container-log", "--service-name", name, "--container-name", "migration")
        seen = set()
        while True:
            for event in page.get("logEvents", []):
                message = str(event.get("message", "")).strip()
                if message not in log:
                    log.append(message)
                    del log[:-1000]
                if message.startswith(marker):
                    code = message[len(marker):]
                    if code == "0":
                        return
                    raise Failure(
                        f"migration reported exit {code}; inspect its retained log and "
                        "run make migrate-remote ENV=production"
                    )
            next_page = page.get("nextPageToken")
            if not next_page or next_page in seen or time.monotonic() >= deadline:
                break
            seen.add(next_page)
            page = aws("lightsail", "get-container-log", "--service-name", name,
                       "--container-name", "migration", "--page-token", next_page)
        time.sleep(2)
    raise Failure(
        "migration result marker did not arrive before its deadline; inspect the retained log and "
        "run make migrate-remote ENV=production"
    )


def remove_image(repository: str, token: str) -> None:
    done = aws("ecr", "batch-delete-image", "--repository-name", repository,
               "--image-ids", f"imageTag=slipwai-migrate-{token}")
    if done.get("failures"):
        raise Failure(f"temporary image cleanup failed: {done['failures']}; inspect aws ecr describe-images")


def migrate(project: str, service: str, image: str, command: list[str] | None,
            environment: dict[str, str], logs: Path) -> None:
    token = uuid.uuid4().hex
    name = f"{project[:30]}-migrate-{token[:12]}"
    repository = ""
    log: list[str] = []
    errors = []
    try:
        digest, repository = wrapped_image(image, command, token)
        deadline = time.monotonic() + MINUTES * 60
        payload("lightsail", "create-container-service", {
            "serviceName": name, "power": "nano", "scale": 1,
            "tags": [{"key": "SlipwaiMigration", "value": token}],
            "privateRegistryAccess": {"ecrImagePullerRole": {"isActive": True}},
        })
        principal = ready(name, token, deadline)
        loan(repository, principal, token)
        payload("lightsail", "create-container-service-deployment", {
            "serviceName": name, "containers": {"migration": {"image": digest, "environment": environment}},
        })
        result(name, token, deadline, log)
    except (Failure, KeyError, ValueError) as fault:
        errors.append(str(fault))
    finally:
        text = "\n".join(log)
        for key, secret in environment.items():
            if secret and any(word in key.upper() for word in ("PASSWORD", "SECRET", "DATABASE_URL", "TOKEN")):
                redactions = [secret]
                if "DATABASE_URL" in key.upper() and (password := urlsplit(secret).password):
                    redactions.append(password)
                for value in redactions:
                    text = text.replace(value, "[redacted]")
                    errors = [error.replace(value, "[redacted]") for error in errors]
        path = logs / f"{service}-{token}.log"
        try:
            logs.mkdir(parents=True, exist_ok=True)
            path.write_text(text + "\n", encoding="utf-8")
            path.chmod(0o600)
        except OSError as fault:
            errors.append(f"cannot retain migration log {path}: {fault}")
        for cleanup in (
            lambda: aws("lightsail", "delete-container-service", "--service-name", name)
            if owned_service(name, token) else None,
            lambda: remove_loan(repository, token) if repository else None,
            lambda: remove_image(repository, token) if repository else None,
        ):
            try:
                cleanup()
            except (Failure, KeyError, ValueError) as fault:
                errors.append(f"cleanup: {fault}")
        if errors:
            raise Failure(
                f"{'; '.join(errors)}. Retained migration log: {path} — read it, then re-run "
                "make migrate-remote ENV=production"
            )
