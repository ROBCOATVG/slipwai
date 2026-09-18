"""An optional Sonar workflow, separate from the deterministic verify workflow."""
from __future__ import annotations

from ..layout import Layout
from ..services import App, services_of, web_apps
from .ci_workflows import toolchain_setup

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
    java_setup = when(toolchain_setup("java", java), ADOPTED) if java else ""
    java_scan = (
        "      - name: Analyze Java services with Maven\n"
        f"        if: {ADOPTED}\n"
        f"        run: python3 {layout.under('scripts/extensions/sonar/scan.py')} --java-only\n"
        if java
        else ""
    )
    exclusions = ""
    if java and generic:
        excluded = ",".join(f"{service.path}/**" for service in java)
        exclusions = f"\n        with:\n          args: -Dsonar.exclusions={excluded}"
    generic_scan = (
        "      - name: Analyze non-Java applications\n"
        f"        if: {ADOPTED}\n"
        f"        uses: {SONAR_ACTION}{exclusions}\n"
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
        + java_setup
        + java_scan
        + generic_scan
    )
