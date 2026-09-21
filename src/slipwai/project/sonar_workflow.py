"""An optional Sonar workflow, separate from the deterministic verify workflow."""
from __future__ import annotations

from ..layout import Layout
from ..services import App, families_of, services_of, web_apps
from .ci_workflows import NODE_SETUP, toolchain_setup

SONAR_ACTION = "SonarSource/sonarqube-scan-action@v8.2.2"
ENABLED = "steps.sonar-config.outputs.enabled == 'true'"
ADOPTED = f"{ENABLED} && hashFiles('sonar-project.properties') != ''"


def when(text: str, condition: str) -> str:
    """Put the same condition on every generated Actions step in `text`."""
    lines: list[str] = []
    for line in text.splitlines():
        lines.append(line)
        if line.startswith("      - "):
            lines.append(f"        if: {condition}")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def sonar_workflow(apps: list[App], layout: Layout) -> str:
    """A credential-gated remote scan that cannot change verify.yml's conclusion."""
    java = [service for service in services_of(apps) if service.language == "java"]
    generic = [
        app
        for app in [*services_of(apps), *web_apps(apps)]
        if app not in java
    ]
    checkout = when("      - uses: actions/checkout@v6\n", ENABLED)
    services = services_of(apps)
    families = families_of(apps)
    setups = "".join(
        when(toolchain_setup(family, [service for service in services if service.language == family]), ADOPTED)
        for family in families
    )
    if web_apps(apps) and "typescript" not in families:
        setups += when(NODE_SETUP, ADOPTED)
    java_scan = (
        "      - name: Analyze Java services with Maven\n"
        f"        if: {ADOPTED}\n"
        f"        run: python3 {layout.under('scripts/extensions/sonar/scan.py')} --java-only\n"
        if java
        else ""
    )
    scan_arguments: list[str] = []
    if java and generic:
        excluded = ",".join(f"{service.path}/**" for service in java)
        scan_arguments.append(f"-Dsonar.exclusions={excluded}")
    reports = {
        "typescript": ("sonar.javascript.lcov.reportPaths", "coverage/lcov.info"),
        "python": ("sonar.python.coverage.reportPaths", "coverage.xml"),
        "go": ("sonar.go.coverage.reportPaths", "sonar-coverage.out"),
    }
    for language, (property_name, report) in reports.items():
        paths = [f"{app.path}/{report}" for app in generic if app.generated and app.language == language]
        if paths:
            scan_arguments.append(f"-D{property_name}={','.join(paths)}")
    action_inputs = (
        "\n        with:\n          args: >\n"
        + "".join(f"            {argument}\n" for argument in scan_arguments).rstrip("\n")
        if scan_arguments
        else ""
    )
    generic_scan = (
        "      - name: Produce coverage reports\n"
        f"        if: {ADOPTED}\n"
        f"        run: python3 {layout.under('scripts/extensions/sonar/scan.py')} --coverage-only\n"
        "      - name: Analyze non-Java applications\n"
        f"        if: {ADOPTED}\n"
        f"        uses: {SONAR_ACTION}{action_inputs}\n"
        if generic
        else ""
    )
    return (
        """name: sonar
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  sonar:
    runs-on: ubuntu-latest
    env:
      SONAR_HOST_URL: ${{ vars.SONAR_HOST_URL }}
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
    steps:
      # GitHub does not allow the secrets context directly in `if`; expose only the yes/no result.
      - id: sonar-config
        shell: bash
        run: |
          if [ -n "$SONAR_TOKEN" ]; then
            echo 'enabled=true' >> "$GITHUB_OUTPUT"
          fi
"""
        + checkout
        + setups
        + java_scan
        + generic_scan
    )
