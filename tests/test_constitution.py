"""The constitution is human-owned, and gated from both sides: a floor to carry, and a boundary not to cross."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import repository, slipwai

from slipwai.assets import PROFILE_ROOT


class ConstitutionTest(FactoryTestCase):
    def constitution_gate(self, repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", "scripts/check-constitution.py", *arguments],
            cwd=repo,
            text=True,
            capture_output=True,
        )

    def test_standard_gate_rejects_an_event_sourcing_constitution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "standard-constitution", "standard", "go")
            constitution = repo / ".specify/memory/constitution.md"
            constitution.parent.mkdir(parents=True)
            constitution.write_text(
                "# Constitution\n\n## Event-Sourced Core\n\nThe event store MUST support replay.\n"
            )

            result = subprocess.run(
                ["python3", "scripts/check-speckit.py"],
                cwd=repo,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("standard profile", result.stderr)
            self.assertIn("--profile event-modelling", result.stderr)

    def test_constitution_gate_holds_the_floor_the_profile_asks_for(self) -> None:
        """A constitution that dropped the practices this foundation depends on is a set of gates that
        silently stopped existing, so the gate names each one — and asks for the event obligations only
        where the profile claims them."""
        thin = (
            "# Thin Constitution\n\n## Core Principles\n\n### I. Correctness\n\n"
            "No unit of finite inventory is held twice.\n\n### II. Tests\n\n"
            "We write tests, we use TypeScript, and we review pull requests.\n"
        )
        always = (
            "trunk-based-integration",
            "one-path-to-production",
            "build-once-deploy-is-not-release",
            "fast-feedback",
            "agent-change-same-bar",
            "strict-typing",
            "ubiquitous-language-and-domain-types",
            "hexagonal-boundary",
            "acceptance-driven-testing",
            "observability-and-audit",
            "security-and-privacy",
            "versioning-and-compatibility",
            "architecture-decision-records",
            "quality-gates",
            "governance",
        )
        event_only = (
            "event-sourced-core",
            "stream-identity-and-concurrency",
            "read-models-are-derivations",
            "event-schema-permanence",
            "idempotency-and-replay",
            "event-modelling-precedes-planning",
        )
        with tempfile.TemporaryDirectory() as directory:
            for profile, language in (("standard", "go"), ("event-modelling", "typescript")):
                event = profile == "event-modelling"
                repo = self.generate(directory, f"floor-{language}", profile, language)
                constitution = repo / ".specify/memory/constitution.md"
                constitution.parent.mkdir(parents=True)
                constitution.write_text(thin)

                result = self.constitution_gate(repo)
                self.assertNotEqual(result.returncode, 0, profile)
                for key in always:
                    self.assertIn(key, result.stderr, f"{profile} must ask for {key}")
                for key in event_only:
                    self.assertEqual(key in result.stderr, event, f"{profile}/{key}")

                # The normative text the gate prints has to satisfy the gate, or the only way to pass it
                # would be to guess the wording it wants.
                requirements = self.constitution_gate(repo, "--requirements")
                self.assertEqual(requirements.returncode, 0, requirements.stderr)
                for key in always:
                    self.assertIn(key, requirements.stdout)
                for key in event_only:
                    self.assertEqual(key in requirements.stdout, event, f"{profile}/{key}")
                constitution.write_text("# Ratified\n\n" + requirements.stdout)
                self.assertEqual(self.constitution_gate(repo).returncode, 0, profile)

                # A single principle removed is the failure this gate exists for, not only a wholesale
                # rewrite: cutting the governance clause leaves a document that still reads as ratified.
                governed = constitution.read_text()
                constitution.write_text(governed[: governed.index("## Governance")])
                narrowed = self.constitution_gate(repo)
                self.assertNotEqual(narrowed.returncode, 0, profile)
                self.assertIn("governance", narrowed.stderr)
                self.assertNotIn("trunk-based-integration", narrowed.stderr)

    def test_the_shipped_constitution_template_satisfies_the_gate_it_ships_with(self) -> None:
        """The preset template and the gate are two statements of the same floor, maintained in different
        files. This is the link that fails when one of them moves.

        Both profiles ship one, because minimum CD is the floor in both: a standard project
        drafting from the core Spec Kit template produces a document that reads as ratified and fails
        `make check-constitution` on all fifteen of the requirements that hold everywhere."""
        for profile, language, covered in (
            ("event-modelling", "python", 21),
            ("standard", "go", 15),
        ):
            template = (
                PROFILE_ROOT
                / f"{profile}/.specify/presets/{profile}/templates/constitution-template.md"
            ).read_text()
            with tempfile.TemporaryDirectory() as directory:
                repo = self.generate(directory, "template-floor", profile, language)
                constitution = repo / ".specify/memory/constitution.md"
                constitution.parent.mkdir(parents=True)

                # As `./init` leaves it: the template, untouched. Nothing has been drafted, so there is
                # nothing to hold to the floor yet, and the commit `./init` pushes passes the gate. This
                # generated repository carries the preset's template, which is what the gate compares
                # against when Spec Kit left no record of what it installed.
                constitution.write_text(template)
                untouched = self.constitution_gate(repo)
                self.assertEqual(untouched.returncode, 0, untouched.stderr)
                self.assertIn("nothing drafted yet", untouched.stdout)
                self.assertIn("/speckit-constitution", untouched.stdout)

                # As `/speckit-constitution` leaves it when the domain answers do not all arrive: one
                # decision made, the rest still prompts. Drafting has started, so the gate applies — and it
                # names the placeholders as the template spells them, underscores and all.
                constitution.write_text(template.replace("[PROJECT_NAME]", "Template Floor", 1))
                drafted = self.constitution_gate(repo)
                self.assertNotEqual(drafted.returncode, 0, profile)
                self.assertIn("placeholder", drafted.stderr)
                self.assertIn("drafted, not ratified", drafted.stderr)
                self.assertIn("[COMPLIANCE_SCOPE]", drafted.stderr)

                # Everything in brackets is a prompt to the ratifying team — the UPPER_SNAKE tokens and
                # the instructions under the principles only this project can write.
                constitution.write_text(
                    re.sub(r"\[[^\]]+\]", "a decision this project made", template)
                )
                ratified = self.constitution_gate(repo)
                self.assertEqual(ratified.returncode, 0, ratified.stderr)
                self.assertIn(f"{covered} required principle(s) covered", ratified.stdout)

                # The other gate reads the same file from the opposite direction. A template that
                # satisfies the floor and trips the profile boundary would be unratifiable in the
                # profile that ships it — which is a thing only this pair of checks can catch.
                boundary = subprocess.run(
                    ["python3", "scripts/check-speckit.py"],
                    cwd=repo,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(boundary.returncode, 0, boundary.stderr)

    def test_the_init_commit_passes_and_the_first_spec_makes_the_gate_apply(self) -> None:
        """`./init` installs the template and pushes; under a production target that push is the first
        deploy, so it has to pass `verify` before a word of the constitution is written. Spec Kit records
        the hash of what it installed beside the file, and that record is the authority — it holds even
        for a template this repository does not carry, and one edited byte breaks it. The moment a
        feature exists under `specs/`, the workflow has started and the untouched template is a finding."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "first-push", "standard", "typescript", target="aws")
            constitution = repo / ".specify/memory/constitution.md"
            constitution.parent.mkdir(parents=True)
            installed = "# [PROJECT_NAME] Constitution\n\n[ONE_PARAGRAPH: what this system does.]\n"
            constitution.write_text(installed)
            (constitution.parent / ".constitution-template.json").write_text(
                json.dumps({"sha256": hashlib.sha256(installed.encode()).hexdigest(), "source": "core"})
            )

            untouched = self.constitution_gate(repo)
            self.assertEqual(untouched.returncode, 0, untouched.stderr)
            self.assertIn("nothing drafted yet", untouched.stdout)

            constitution.write_text(installed.replace("[PROJECT_NAME]", "First Push"))
            drafted = self.constitution_gate(repo)
            self.assertNotEqual(drafted.returncode, 0)
            self.assertIn("drafted, not ratified", drafted.stderr)

            constitution.write_text(installed)
            spec = repo / "specs/001-first/spec.md"
            spec.parent.mkdir(parents=True)
            spec.write_text("# First\n")
            started = self.constitution_gate(repo)
            self.assertNotEqual(started.returncode, 0)
            self.assertIn("still the template", started.stderr)
            self.assertIn("/speckit-constitution", started.stderr)

    def test_the_constitution_phase_is_hooked_on_both_sides(self) -> None:
        """The gate is only a gate if the drafting phase meets it. `before_constitution` prints the floor
        while it is still cheap to write, and `after_constitution` runs the check in the phase that can
        still fix it in one edit rather than leaving it for `make verify` after a plan is written."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "hooked-constitution", "event-modelling", "typescript")
            hooks = (repo / ".specify/extensions.yml").read_text()
            self.assertIn("before_constitution:", hooks)
            self.assertIn("after_constitution:", hooks)
            # Exactly two hooks run rather than print, and both are the same shape: they re-check the
            # artifact the phase they follow has just written. Neither adds a way to deliver a change, which
            # is what the prefer-optional rule is actually about. A printed reminder about a check that
            # fails later is the noise the extension file exists to remove.
            self.assertEqual(hooks.count("optional: false"), 2)
            named = re.findall(r'command: "([^"]+)"', hooks)
            self.assertIn("constitution-coverage", named)
            # Every hook names a command that exists — a project command, a host session verb (`compact`),
            # or a `/speckit-*` phase command that Spec Kit itself installs into the agent.
            for command in named:
                self.assertTrue(
                    (repo / f"commands/{command}.md").is_file()
                    or command == "compact"
                    or command.startswith("speckit-"),
                    f"{command} is named by a hook but is not a project command",
                )
            self.assertIn("check-constitution", (repo / "commands/constitution-coverage.md").read_text())
            self.assertIn("no agent can run it on your behalf", hooks)
            self.assertNotIn("Claude Code CLI command", hooks)

    def test_an_adopted_repository_ratifies_a_journey_and_the_gate_holds_it_to_the_map(self) -> None:
        """A repository on long-lived branches cannot truthfully ratify "trunk MUST be releasable at every commit".
        So the template an adopted repository drafts from writes each principle its convergence map says is not
        yet reachable as a target — where it stands, where the principle comes into force, the principle quoted for
        that day — and the gate holds the marker to the map: drift fails, a claim the map contradicts fails, and a
        principle reached is asked for in full."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": json.dumps({"name": "shop", "private": True, "scripts": {"test": "node --test"}}),
                "test/a.test.js": 'require("node:test")("a", () => {});\n',
            })
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            template_path = repo / ".specify/presets/standard/templates/constitution-template.md"
            template = template_path.read_text()
            markers = re.findall(r"<!-- journey: ([a-z-]+) at ([a-z-]+) -->", template)
            self.assertEqual(dict(markers), {
                "trunk-based-integration": "unknown", "one-path-to-production": "unknown",
                "build-once-deploy-is-not-release": "unknown", "fast-feedback": "tests-exist",
                "acceptance-driven-testing": "tests-exist", "hexagonal-boundary": "as-found",
                "ubiquitous-language-and-domain-types": "as-found", "strict-typing": "as-found",
            })
            self.assertIn("> - Every engineer MUST integrate to trunk at least once per day.", template,
                          "the principle is kept, quoted, for the day it comes into force")
            self.assertIn(".specify/presets/standard/templates/constitution-template.md",
                          (repo / "delivery/.written").read_text())
            gate = lambda: subprocess.run(  # noqa: E731
                ["python3", "delivery/scripts/check-constitution.py"], cwd=repo, text=True, capture_output=True
            )
            requirements = subprocess.run(
                ["python3", "delivery/scripts/check-constitution.py", "--requirements", "trunk-based-integration"],
                cwd=repo, text=True, capture_output=True,
            )
            self.assertIn("A TARGET here, not yet in force: this repository stands at `unknown`", requirements.stdout)
            self.assertIn("<!-- journey: trunk-based-integration at unknown -->", requirements.stdout)

            constitution = repo / ".specify/memory/constitution.md"
            constitution.parent.mkdir(parents=True)
            constitution.write_text(template)
            self.assertIn("nothing drafted yet", gate().stdout, "the adapted template is still the template")
            filled = re.sub(r"\[[^\]]+\]", "a decision this project made", template)
            constitution.write_text(filled)
            ratified = gate()
            self.assertEqual(ratified.returncode, 0, ratified.stderr)
            self.assertIn("15 required principle(s) covered, 8 of them as targets held to the convergence map",
                          ratified.stdout)
            speckit = subprocess.run(
                ["python3", "delivery/scripts/check-speckit.py"], cwd=repo, text=True, capture_output=True
            )
            self.assertEqual(speckit.returncode, 0, speckit.stderr)

            constitution.write_text(
                filled.replace(
                    "journey: trunk-based-integration at unknown", "journey: trunk-based-integration at trunk"
                )
            )
            drifted = gate()
            self.assertNotEqual(drifted.returncode, 0)
            self.assertIn("the constitution says this repository stands at `trunk`, and the map", drifted.stderr)
            in_force = re.sub(r"<!-- journey: trunk-based-integration at unknown -->\n", "", filled).replace("> ", "")
            constitution.write_text(in_force)
            claimed = gate()
            self.assertNotEqual(claimed.returncode, 0)
            self.assertIn("Continuous integration on trunk, in small batches: written as in force, but the map says",
                          claimed.stderr)
            constitution.write_text(
                filled.replace("## Governance", "<!-- journey: governance at open -->\n## Governance")
            )
            misplaced = gate()
            self.assertNotEqual(misplaced.returncode, 0)
            self.assertIn("Governance: supersession, amendment, versioning, and review: marked as a journey",
                          misplaced.stderr)

            # The table the gate reads is the table the factory writes the template from.
            from slipwai.project.constitution_journey import JOURNEY
            table = subprocess.run(
                ["python3", "delivery/scripts/check-constitution.py", "--journey"],
                cwd=repo, text=True, capture_output=True,
            )
            self.assertEqual(
                json.loads(table.stdout), {key: [axis, rung] for key, (axis, rung, _) in JOURNEY.items()}
            )
