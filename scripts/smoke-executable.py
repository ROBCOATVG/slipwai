#!/usr/bin/env python3
"""Prove a packaged executable can generate independently of the factory checkout."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

EXPECTED_VERSION = (Path(__file__).resolve().parents[1] / "VERSION").read_text().strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    args = parser.parse_args()
    executable = args.executable.resolve()

    version = subprocess.run(
        [str(executable), "--version"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    if version != f"slipwai {EXPECTED_VERSION}":
        raise RuntimeError(f"unexpected version output: {version}")

    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        subprocess.run(
            [
                str(executable),
                "generate",
                "packaged-smoke",
                "--profile",
                "event-modelling",
                "--language",
                "go",
                "--frontend",
                "react-vite",
            ],
            check=True,
            cwd=output,
        )
        project = output / "packaged-smoke"
        metadata = json.loads((project / "project.json").read_text())
        if metadata["deployables"]["service"]["language"] != "go":
            raise RuntimeError("packaged backend selection was not preserved")
        if metadata["deployables"]["web"]["framework"] != "react-vite":
            raise RuntimeError("packaged frontend assets were not preserved")
        if not (project / "skills/event-sourcing/SKILL.md").is_file():
            raise RuntimeError("packaged toolkit assets are incomplete")
        commit_count = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=project,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        remotes = subprocess.run(
            ["git", "remote"],
            cwd=project,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout
        if commit_count != "1" or remotes:
            raise RuntimeError("packaged generation did not create one local-only commit")

    # The backing services live under assets/ and their prune script is loaded by file path at import
    # time, which is the one thing about them that a frozen build can break: it reads from the bundle's
    # extraction directory rather than a checkout. So generate them from the packaged executable too.
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        subprocess.run(
            [
                str(executable),
                "generate",
                "packaged-services",
                "--profile",
                "event-modelling",
                "--language",
                "typescript",
                "--frontend",
                "none",
                "--event-store",
                "postgres",
                "--http",
                "fastify",
                "--auth",
                "keycloak",
            ],
            check=True,
            cwd=output,
        )
        project = output / "packaged-services"
        for relative in (
            "docker-compose.yml",
            "docker/keycloak/realms/app.json",
            "scripts/backing-services.py",
            "apps/service/migrations/001_events.js",
            "apps/service/src/adapters/driven/event-store-postgres/index.ts",
            "apps/service/src/adapters/driving/http/app.ts",
            "apps/service/tests/contract/event-store-contract.ts",
        ):
            if not (project / relative).is_file():
                raise RuntimeError(f"packaged backing-service assets are incomplete: {relative}")
        compose = (project / "docker-compose.yml").read_text()
        # Pruning ran inside the frozen build: both containers were asked for, so both survive, and the
        # markers a later `./init` needs are still there.
        for expected in ("postgres:", "keycloak:", "backing-service:postgres:begin"):
            if expected not in compose:
                raise RuntimeError(f"packaged compose file lost {expected}")

    print(f"smoke-executable: {executable.name} generated a complete independent repository")


if __name__ == "__main__":
    main()
