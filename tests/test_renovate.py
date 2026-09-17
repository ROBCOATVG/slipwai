"""The Renovate configuration, held to the tree it claims to describe.

A dependency-update configuration fails silently: a pattern that matches nothing produces no error, no pull
request and no sign that anything is wrong — the repository simply stops being updated, which looks exactly
like a repository with nothing to update. So nothing here asserts that the file *says* something. Every
pattern in it is applied to the paths and the lines of a project that was actually generated, and the custom
managers are run against the workflow they exist to read.
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.assets import ROOT


def pattern(declared: str) -> re.Pattern[str]:
    """One `managerFilePatterns` entry as the regular expression Renovate reads it as: a value wrapped in
    slashes is a regex, and everything here is."""
    assert declared.startswith("/") and declared.endswith("/"), declared
    return re.compile(declared[1:-1])


def as_python(expression: str) -> re.Pattern[str]:
    """One of Renovate's `matchStrings` as this language spells the same regular expression: JavaScript
    names a group `(?<name>…)` and Python `(?P<name>…)`, and nothing else in these differs."""
    return re.compile(expression.replace("(?<", "(?P<"))


def files_under(repo: Path) -> list[str]:
    """Every file in the repository, as Renovate sees the list: repository-relative POSIX paths."""
    return [
        path.relative_to(repo).as_posix() for path in repo.rglob("*")
        if path.is_file() and ".git/" not in path.relative_to(repo).as_posix()
    ]


class RenovateTest(FactoryTestCase):
    def test_the_python_dependencies_are_read_where_this_project_actually_keeps_them(self) -> None:
        """A Python service's dependencies are in its `pyproject.toml`, with a `uv.lock` beside it, so the
        manager is `pep621` — which reads both lists and re-locks with uv — and no file pattern has to be
        declared at all. The older shape needed one, because `pip_requirements` matches a prefix
        (`dev-requirements.txt`) and never the suffix this factory wrote."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "updated", "standard", "python", "none")
            config = json.loads((repo / "renovate.json").read_text())
            self.assertIn("pep621", json.dumps(config))
            self.assertNotIn("pip_requirements", json.dumps(config))
            present = files_under(repo)
            self.assertIn("apps/service/pyproject.toml", present)
            self.assertIn("apps/service/uv.lock", present)

    def test_the_toolchain_managers_read_the_versions_the_pin_files_hold(self) -> None:
        """The custom managers exist because no manager reads an action's *inputs*: without them Renovate
        would raise `.nvmrc` and leave CI installing the old major. Run here against the real workflow, and
        compared with the real pin file, so a pattern that has drifted off the YAML fails."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "updated", "standard", "python", "react-vite")
            config = json.loads((repo / "renovate.json").read_text())
            workflow = (repo / ".github/workflows/verify.yml").read_text()
            pins = {"node": ".nvmrc", "python": ".python-version"}
            self.assertEqual(sorted(pins), sorted(m["depNameTemplate"] for m in config["customManagers"]))
            for manager in config["customManagers"]:
                name = manager["depNameTemplate"]
                with self.subTest(toolchain=name):
                    self.assertTrue(pattern(manager["managerFilePatterns"][0]).search(".github/workflows/verify.yml"))
                    found = as_python(manager["matchStrings"][0]).search(workflow)
                    self.assertIsNotNone(found, f"{name}: the custom manager matches nothing in the workflow")
                    assert found is not None
                    self.assertEqual(
                        (repo / pins[name]).read_text().strip(), found.group("currentValue"),
                        f"{name}: the workflow and the pin file would be updated apart",
                    )

    def test_a_project_is_given_rules_only_for_the_ecosystems_it_has(self) -> None:
        """A group naming a manager the project gives nothing to read is a rule that will never fire, and
        the reader of the file cannot tell it apart from one that should have."""
        expected = {
            ("typescript", "none"): {"toolchain", "npm", "workflow actions", "containers"},
            ("go", "react-vite"): {"toolchain", "go", "npm", "workflow actions", "containers"},
            ("java-spring", "none"): {"maven", "workflow actions", "containers"},
        }
        with tempfile.TemporaryDirectory() as directory:
            for (backend, frontend), groups in expected.items():
                with self.subTest(backend=backend, frontend=frontend):
                    repo = self.generate(directory, f"rules-{backend}-{frontend}", "standard", backend, frontend)
                    config = json.loads((repo / "renovate.json").read_text())
                    named = {rule["groupName"] for rule in config["packageRules"] if "groupName" in rule}
                    self.assertEqual(groups, named)
                    self.assertEqual("pep621" in json.dumps(config), backend == "python")

    def test_a_major_waits_to_be_asked_for_and_a_vulnerability_does_not_wait_at_all(self) -> None:
        """The two rules that make a weekly window safe in a tree where every version is exact."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "held", "standard", "typescript", "none")
            config = json.loads((repo / "renovate.json").read_text())
            major = [r for r in config["packageRules"] if r.get("matchUpdateTypes") == ["major"]]
            self.assertEqual(1, len(major))
            self.assertTrue(major[0]["dependencyDashboardApproval"])
            self.assertEqual(["at any time"], config["vulnerabilityAlerts"]["schedule"])
            self.assertTrue(config["lockFileMaintenance"]["enabled"])

    def test_the_file_says_that_nothing_runs_it(self) -> None:
        """The one thing a reader has to know and cannot see: a configuration is inert until a bot is
        running. Said in the file itself, because that is what somebody opens."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "inert", "standard", "typescript", "none")
            described = " ".join(json.loads((repo / "renovate.json").read_text())["description"])
            self.assertIn("Renovate app", described)
            self.assertIn("self-hosted", described)

    def test_the_factory_is_covered_by_one_of_its_own(self) -> None:
        """The same argument applied here: the manifests under `assets/` are the ones every generated project
        starts from, and nothing was moving them either. Its patterns are applied to this repository."""
        config = json.loads((ROOT / "renovate.json").read_text())
        declared = pattern(config["pip_requirements"]["managerFilePatterns"][0])
        self.assertTrue(declared.search("requirements-dev.txt"))
        self.assertTrue(declared.search("assets/toolkit/scripts/event-model/requirements.txt"))
        described = " ".join(config["description"])
        # The half a bump is not: a manifest under assets/ has its lock built per axis combination.
        self.assertIn("make locks", described)
        self.assertIn("self-hosted", described)
        for rule in config["packageRules"]:
            if rule.get("matchFileNames") == ["assets/**"]:
                self.assertTrue((ROOT / "assets/languages/typescript/app/package.json").is_file())
                break
        else:
            self.fail("nothing in the factory's own configuration reads the manifests under assets/")
