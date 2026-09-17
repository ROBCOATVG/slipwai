"""A skill ships where the project can use it, and the project is told about the ones that did not.

The catalogue used to arrive whole in every project but for three event skills named in a list in
`toolkit.py`. Measured in a Python service with no frontend, no identity provider and no event store, six
of the skills it carried — 42,648 words, a fifth of the catalogue — were about capabilities that project
does not have, and every one of them is context an agent may load and a turn `find-skills` may take.

A skill now declares what it serves in its own frontmatter and the union of what the deployables can do
decides, so the list in `toolkit.py` is gone and the rule reaches the frontend, the language and the two
identity axes without a second list to keep in step.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

from support import FactoryTestCase, commit_all

from slipwai.assets import PRUNER, ROOT, TOOLKIT_ROOT, asset_files
from slipwai.capabilities import declared_for, serves
from slipwai.catalog import CATALOG, validate_catalog
from slipwai.toolkit import skill_declarations

GATE = TOOLKIT_ROOT / "scripts/agents/project.py"
# The skills that declare a capability, and what each one needs: the cases every assertion below turns on.
DECLARING = ("bff-design", "bff-entry-points", "front-end-testing", "react-testing", "typescript-strict",
             "secure-oauth-oidc", "event-modeling", "event-sourcing", "global-event-model")
# Skills about how work is done here rather than about a tool: in every project, whatever it answered.
UNIVERSAL = ("tdd", "testing", "hexagonal-architecture", "refactoring", "finding-seams", "specification")


def producible() -> set[str]:
    """Every capability a project can ever be given, so a declaration naming anything else is a typo that
    would withhold its skill from every project there is, silently and forever."""
    return {
        *(capability for profile in CATALOG["profiles"].values() for capability in profile["capabilities"]),
        *(capability for frontend in CATALOG["frontends"].values() for capability in frontend["capabilities"]),
        *(capability for axis in CATALOG["axes"].values() for option in axis["options"].values()
          for capability in option["capabilities"]),
        *(backend["family"] for backend in CATALOG["backends"].values()),
    }


def gate_module():
    """The generated project's own gate, loaded from the asset tree, for its reader of the same format.

    With bytecode writing off while it loads: a `__pycache__` beside an asset is a file `assets/` is not
    allowed to have — `asset_files` skips it, so it never reaches a project, but two suites here read every
    file under the tree and a `.pyc` makes them die on a UnicodeDecodeError that reads like a broken asset.
    """
    spec = importlib.util.spec_from_file_location("generated_agents_project", GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    written, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = written
    return module


class SkillCapabilityTest(FactoryTestCase):
    def test_every_declaration_names_something_a_project_can_be_given(self) -> None:
        available = producible()
        for skill, declared in sorted(skill_declarations().items()):
            for pattern in declared or ():
                with self.subTest(skill=skill, pattern=pattern):
                    self.assertTrue(
                        serves((pattern,), available),
                        f"{skill} declares `{pattern}`, which no profile, frontend, axis option or backend "
                        "family in catalog.json produces — it would ship to no project at all",
                    )

    def test_the_shipped_pruner_says_what_an_answer_gives_in_the_catalog_s_own_words(self) -> None:
        """`./init --auth none` rewrites each deployable's `capabilities`, and reads what to write from
        the pruner's own table — it is one script inside a generated project, with no catalog to ask.

        So the table is the catalog's list, in the catalog's order, which is the order the manifest records.
        A pruner that disagreed would write a capability nothing produces, and the project's own
        `check-agents` would go on justifying a skill by it — the exact failure this whole mechanism exists
        to prevent, arriving through the one path that changes a project's capabilities with no factory
        running. Held to the catalog the way the feature list and the option targets already are.
        """
        for axis, spec in CATALOG["axes"].items():
            for name, option in spec["options"].items():
                self.assertEqual(
                    list(PRUNER.AXES[axis]["options"][name]["capabilities"]),
                    option["capabilities"],
                    f"{axis}/{name}",
                )

        drifted = {**PRUNER.AXES["auth"]["options"]["keycloak"], "capabilities": ("auth-kc",)}
        with (
            patch.dict(PRUNER.AXES["auth"]["options"], {"keycloak": drifted}),
            self.assertRaisesRegex(ValueError, "disagree about what auth/keycloak gives"),
        ):
            validate_catalog(CATALOG)

        unstated = json.loads(json.dumps(CATALOG))
        del unstated["axes"]["auth"]["options"]["keycloak"]["capabilities"]
        with self.assertRaisesRegex(ValueError, "auth/keycloak must declare what it gives"):
            validate_catalog(unstated)

    def test_a_skill_ships_where_its_subject_is_and_not_where_it_is_not(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            full = self.generate(
                directory, "ledger", "event-modelling", "typescript", "react-vite",
                event_store="postgres", http="fastify", auth="keycloak", users="keycloak",
            )
            bare = self.generate(directory, "tally", "standard", "python", "none", http="fastapi")
            go = self.generate(directory, "forge", "event-modelling", "go", "none", event_store="sqlite")

            for skill in DECLARING:
                self.assertTrue((full / "skills" / skill / "SKILL.md").is_file(), skill)
                self.assertFalse((bare / "skills" / skill).exists(), f"{skill} in a project with none of it")
            # The Go project has the event capabilities and none of the browser or identity ones.
            self.assertTrue((go / "skills/event-sourcing/SKILL.md").is_file())
            for skill in ("react-testing", "typescript-strict", "secure-oauth-oidc", "front-end-testing"):
                self.assertFalse((go / "skills" / skill).exists(), skill)
            # What is left is not a rump: everything about how work is done here is in all three.
            for skill in UNIVERSAL:
                for repo in (full, bare, go):
                    self.assertTrue((repo / "skills" / skill / "SKILL.md").is_file(), f"{repo.name}/{skill}")

    def test_the_language_a_service_is_written_in_is_a_capability(self) -> None:
        """`typescript-strict` reached the Go and Java projects because nothing recorded the language.

        A browser app declares `typescript` already, so the capability existed only where there was a
        frontend. It is the service that says what a project is written in.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "typed", "event-modelling", "typescript", "none")
            recorded = json.loads((repo / "project.json").read_text())
            self.assertIn("typescript", recorded["deployables"]["service"]["capabilities"])
            self.assertTrue((repo / "skills/typescript-strict/SKILL.md").is_file())

    def test_a_new_browser_app_brings_the_skills_it_earns(self) -> None:
        """Reversible without a list: `add-frontend` writes every file the new application's arrival changes,
        and a skill the project can now use is one of them."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "grown", "standard", "python", "none", http="fastapi")
            self.assertFalse((repo / "skills/react-testing").exists())

            result = subprocess.run(
                [str(ROOT / "slipwai"), "add-frontend", "web"], cwd=repo, text=True, capture_output=True
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            for skill in ("react-testing", "front-end-testing", "bff-design", "bff-entry-points",
                          "typescript-strict"):
                self.assertTrue((repo / "skills" / skill / "SKILL.md").is_file(), skill)
            # Still not the identity one: a browser app is not a login.
            self.assertFalse((repo / "skills/secure-oauth-oidc").exists())

    def test_the_gate_names_a_skill_the_project_no_longer_justifies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "shrunk", "event-modelling", "typescript", "react-vite")
            check = ["python3", "scripts/agents/project.py", "--check"]
            quiet = subprocess.run(check, cwd=repo, text=True, capture_output=True)
            self.assertEqual(quiet.returncode, 0, quiet.stderr)
            self.assertNotIn("serves", quiet.stdout)

            shutil.rmtree(repo / "apps/web")
            commit_all(repo, "drop the browser app")

            told = subprocess.run(check, cwd=repo, text=True, capture_output=True)

            self.assertEqual(told.returncode, 0, told.stderr)
            for skill in ("bff-design", "bff-entry-points", "front-end-testing", "react-testing"):
                self.assertIn(f"skills/{skill} serves", told.stdout)
            # The service is still TypeScript, so that one is still justified.
            self.assertNotIn("typescript-strict serves", told.stdout)

    def test_the_page_lists_what_shipped_and_names_what_did_not(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "listed", "standard", "python", "none", http="fastapi")
            page = (repo / "docs/skills-and-commands.md").read_text()
            here = {path.parent.name for path in (repo / "skills").glob("*/SKILL.md")}

            self.assertTrue(here)
            for skill in sorted(here):
                self.assertIn(f"`{skill}`", page, f"{skill} is here and the page does not list it")
            for skill, declared in sorted(skill_declarations().items()):
                if skill not in here:
                    self.assertIn(f"| `{skill}` | {', '.join(declared or ())} |", page)

    def test_the_generated_gate_reads_a_declaration_the_way_the_factory_does(self) -> None:
        """Two readers of one format, held to each other on every skill that ships."""
        theirs = gate_module().declared_capabilities
        for skill in sorted(asset_files(TOOLKIT_ROOT / "skills")):
            if skill.name != "SKILL.md":
                continue
            text = skill.read_text()
            with self.subTest(skill=skill.parent.name):
                self.assertEqual(list(declared_for(text) or []), list(theirs(text) or []))
