"""No generated line is wider than the limit the same project's own linter enforces.

The project's name is part of the measurement. `java_package_segment` and `python_package_name` turn it
into the package every file names itself with, so the name is inside the width of every import line and
every javadoc link that spells a package out. A file that sits comfortably under the limit at
`delivery-starter` is over it at a name twice as long, and the person who finds out is whoever generated a
project whose `make lint` was red the moment it was written.

The limits are read out of the generated project rather than written down here — ruff's `line-length` from
the service's `pyproject.toml`, Checkstyle's `LineLength` and its `ignorePattern` from `config/checkstyle.xml`
— because a limit repeated here is a limit that can disagree with the one that actually runs. A backend
whose gate has no width rule contributes nothing and needs no entry; `test_the_check_measures_something`
is what stops that from quietly becoming all of them.

This is the cheap half of the pair. `tests/test_matrix.py` runs the real linters, but only on the
combinations it can afford; this generates the trees and measures them, which costs seconds and can
therefore cover the production target, both stores and both profiles.
"""
from __future__ import annotations

import re
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

from support import FactoryTestCase, backends_under_test

from slipwai.catalog import axis_default

# A name long enough to be the thing that fails, and no longer. 44 characters is where Python binds: the
# deepest import a generated test makes is
# `from <package>.adapters.driving.http.users.oidc_keycloak import (`, which is 100 columns at this length
# and has nowhere left to wrap, so a longer name would hold the assets to a width no rewrapping can reach.
# It is longer than any name `tests/test_matrix.py` generates, so a tree that passes here passes there.
LONG_NAME = "widths-at-the-longest-supported-project-name"

# What each selection is for, in the order they are generated. Between them every file a width gate reads
# is present at least once: both identity adapters and the read side under the first, the SQLite adapters
# and their contract suites under the second, the flags route and everything else a production target
# brings under the third, and the standard profile's smaller tree under the last.
SELECTIONS = (
    ("event-modelling", "react-vite", "postgres", "keycloak", "keycloak", "none"),
    ("event-modelling", "none", "sqlite", "keycloak", "none", "none"),
    ("event-modelling", "none", "postgres", "cognito", "none", "aws"),
    ("standard", "none", "memory", "keycloak", "none", "none"),
)

# Ruff exempts the part of a line a pragma comment adds: it measures up to the pragma, so a suppression
# long enough to push a short statement past the limit is not E501. Measuring the whole line here would
# fail on code ruff passes, which is a gate that disagrees with the one it is imitating. Spelled without
# the marker itself, which ruff reads as a directive wherever it appears — in a comment of ours included.
PRAGMA = re.compile(r"\s*#\s*(?:noqa|type:)")


def measured(line: str) -> str:
    """The part of a line ruff holds to the limit: what a pragma comment adds is not E501's business."""
    pragma = PRAGMA.search(line)
    return line[: pragma.start()] if pragma else line


def ruff_limit(service: Path) -> int | None:
    """The service's own `line-length`, or None where its ecosystem's linter has no width rule."""
    pyproject = service / "pyproject.toml"
    if not pyproject.is_file():
        return None
    limit = tomllib.loads(pyproject.read_text()).get("tool", {}).get("ruff", {}).get("line-length")
    return int(limit) if limit is not None else None


def checkstyle_limit(service: Path) -> tuple[int, re.Pattern[str]] | None:
    """Checkstyle's `LineLength` and the lines it is told to skip, straight out of the committed ruleset."""
    config = service / "config/checkstyle.xml"
    if not config.is_file():
        return None
    for module in ET.parse(config).getroot().iter("module"):
        if module.get("name") != "LineLength":
            continue
        properties = {node.get("name"): node.get("value") for node in module.iter("property")}
        if not properties.get("max"):
            continue
        # `(?!)` never matches, for a ruleset that limits the width without excusing anything.
        return int(properties["max"] or 0), re.compile(properties.get("ignorePattern") or "(?!)")
    return None


def has_width_gate(repo: Path) -> bool:
    """Whether anything in this project is held to a width at all."""
    return any(
        ruff_limit(service) is not None or checkstyle_limit(service) is not None
        for service in repo.glob("apps/*")
    )


def over_limit(repo: Path) -> list[str]:
    """Every line in this project that its own gate would call too long."""
    offences = []
    for service in sorted(repo.glob("apps/*")):
        python = ruff_limit(service)
        if python is not None:
            # The two trees `scripts/verify --lint-only` hands ruff, and nothing else: a repository-level
            # script is not in them and is not held to this.
            for tree in (service / "src", service / "tests"):
                for path in sorted(tree.rglob("*.py")):
                    for number, line in enumerate(path.read_text().splitlines(), 1):
                        width = len(measured(line))
                        if width > python:
                            offences.append(f"{path.relative_to(repo)}:{number} is {width} > {python}")
        java = checkstyle_limit(service)
        if java is not None:
            limit, excused = java
            for path in sorted((service / "src").rglob("*.java")):
                for number, line in enumerate(path.read_text().splitlines(), 1):
                    if len(line) > limit and not excused.search(line):
                        offences.append(f"{path.relative_to(repo)}:{number} is {len(line)} > {limit}")
    return offences


class LineWidthTest(FactoryTestCase):
    def test_no_generated_line_is_too_wide_for_a_long_project_name(self) -> None:
        offences: list[str] = []
        with tempfile.TemporaryDirectory() as directory:
            for backend in backends_under_test():
                for index, selection in enumerate(SELECTIONS):
                    profile, frontend, store, auth, users, target = selection
                    parent = Path(directory) / f"{backend}-{index}"
                    parent.mkdir(parents=True)
                    repo = self.generate(
                        parent,
                        LONG_NAME,
                        profile,
                        backend,
                        frontend,
                        event_store=store,
                        http=axis_default("http", backend, "none"),
                        auth=auth,
                        users=users,
                        target=target,
                    )
                    offences += [f"{backend} {'/'.join(selection)}: {line}" for line in over_limit(repo)]
                    # A backend nothing holds to a width is measured once and left alone: the other
                    # selections would cost the same generation and could not find anything either.
                    if index == 0 and not has_width_gate(repo):
                        break
        self.assertEqual(
            [],
            offences,
            f"a project generated as '{LONG_NAME}' is wider than its own linter allows; wrap the line "
            "rather than widening the limit:\n  " + "\n  ".join(offences),
        )

    def test_the_check_measures_something(self) -> None:
        """The reader of the limits, held to a project that has both — a sweep that found neither would
        pass everything and say nothing, which is the one failure this cannot report on its own."""
        self.assertEqual(44, len(LONG_NAME), "the name is the measurement; see why 44 above")
        with tempfile.TemporaryDirectory() as directory:
            python = self.generate(directory, "widths-python", "event-modelling", "python", "none")
            self.assertEqual(100, ruff_limit(python / "apps/service"))
            self.assertIsNone(checkstyle_limit(python / "apps/service"))
            java = self.generate(directory, "widths-java", "event-modelling", "java-spring", "none")
            limit, excused = checkstyle_limit(java / "apps/service") or (0, re.compile("(?!)"))
            self.assertEqual(120, limit)
            self.assertTrue(excused.search("import com.example.widths.flags.Flags;"))
            self.assertIsNone(ruff_limit(java / "apps/service"))
        self.assertEqual("x = 1", measured("x = 1  # noqa: BLE001 - a reason as long as you like"))
        self.assertEqual("x = 1", measured("x = 1"))
