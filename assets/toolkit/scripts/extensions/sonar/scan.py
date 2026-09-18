#!/usr/bin/env python3
"""Run the elected Sonar analysis without putting credentials on a command line."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[3]


ROOT = project_root(Path(__file__).resolve())
MANIFEST = ROOT / "project.json"
PROPERTIES = ROOT / "sonar-project.properties"


def existing(paths: list[Path]) -> list[str]:
    return [path.relative_to(ROOT).as_posix() for path in paths if path.is_file()]


def scanner_arguments(generic: list[dict], java: list[dict]) -> list[str]:
    """Arguments for the one non-Java analysis, including only reports already on disk."""
    arguments: list[str] = []
    if java:
        excluded = ",".join(f"{app['path']}/**" for app in java)
        arguments.append(f"-Dsonar.exclusions={excluded}")
    javascript = existing([ROOT / app["path"] / "coverage/lcov.info" for app in generic])
    python = existing([ROOT / app["path"] / "coverage.xml" for app in generic])
    if javascript:
        arguments.append(f"-Dsonar.javascript.lcov.reportPaths={','.join(javascript)}")
    if python:
        arguments.append(f"-Dsonar.python.coverage.reportPaths={','.join(python)}")
    return arguments


def run_generic(generic: list[dict], java: list[dict]) -> int:
    scanner = shutil.which("sonar-scanner")
    if scanner is None:
        print(
            "sonar-scanner is required for this project's non-Java applications; install it, then rerun "
            "`make sonar`.",
            file=sys.stderr,
        )
        return 2
    return subprocess.run(
        [scanner, *scanner_arguments(generic, java)],
        cwd=ROOT,
        check=False,
    ).returncode


def run_java(document: dict, app: dict, only_deployable: bool) -> int:
    path = ROOT / app["path"]
    wrapper = path / "mvnw"
    if not wrapper.is_file():
        print(f"{app['path']}: Maven wrapper not found; cannot run Sonar.", file=sys.stderr)
        return 2
    name = document["name"]
    key = name if only_deployable else f"{name}-{app['name']}"
    project_name = name if only_deployable else f"{name} ({app['name']})"
    arguments = [
        str(wrapper),
        "-B",
        "sonar:sonar",
        f"-Dsonar.projectKey={key}",
        f"-Dsonar.projectName={project_name}",
    ]
    jacoco = [
        str(report)
        for report in (
            path / "target/site/jacoco/jacoco.xml",
            path / "target/jacoco-report/jacoco.xml",
        )
        if report.is_file()
    ]
    if jacoco:
        arguments.append(f"-Dsonar.coverage.jacoco.xmlReportPaths={','.join(jacoco)}")
    return subprocess.run(arguments, cwd=path, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--java-only", action="store_true", help="scan only Java services (used by CI)")
    arguments = parser.parse_args()
    missing = [name for name in ("SONAR_HOST_URL", "SONAR_TOKEN") if not os.environ.get(name)]
    if missing:
        print(f"make sonar requires {', '.join(missing)} in the environment.", file=sys.stderr)
        return 2
    if not PROPERTIES.is_file():
        print(
            "Sonar is not adopted here: run `./init --extension sonar` first.",
            file=sys.stderr,
        )
        return 2

    document = json.loads(MANIFEST.read_text())
    deployables = [
        {"name": name, **app}
        for name, app in document.get("deployables", {}).items()
    ]
    java = [
        app for app in deployables
        if app.get("kind") == "service" and app.get("language") == "java"
    ]
    generic = [app for app in deployables if app not in java]

    if generic and not arguments.java_only:
        status = run_generic(generic, java)
        if status:
            return status
    for app in java:
        status = run_java(document, app, len(deployables) == 1)
        if status:
            return status
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
