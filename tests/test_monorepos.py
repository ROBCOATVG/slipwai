"""Every profile/backend combination, scaffolded as a complete and independent monorepo.

The shape of what `slipwai generate` leaves behind — one commit, a clean tree, no manifest, the executables
executable, the gate reachable from the Makefile, the preset layer and the event-modelling half present or
absent by profile — for all ten foundations at once. Whole because half of what it asserts is comparative:
the two Java backends sharing one family tree, Spring needing the startup class Quarkus does not. Generation
alone, no toolchain, about a second; it runs once, in the `checks` job, where `tests/test_matrix.py` runs
each backend's variants through their own `make verify` in that backend's matrix job.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.backends import BACKEND_EXECUTABLES
from slipwai.catalog import CATALOG, family_of, framework_of
from slipwai.project.event_model import event_model_page_url
from slipwai.tooling import for_app
from slipwai.toolkit import STANDARD_OVERRIDES


class MonorepoTest(FactoryTestCase):
    def test_scaffolds_complete_matrix_as_independent_monorepos(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repos: dict[tuple[str, str], Path] = {}
            for profile in CATALOG["profiles"]:
                for language in CATALOG["backends"]:
                    name = f"product-{profile}-{language}"
                    repos[(profile, language)] = self.generate(directory, name, profile, language)

            self.assertEqual(len(repos), len(CATALOG["profiles"]) * len(CATALOG["backends"]))
            for (profile, language), repo in repos.items():
                metadata = json.loads((repo / "project.json").read_text())
                self.assertEqual(metadata["name"], repo.name)
                self.assertEqual(metadata["profile"], profile)
                # Per service, because a project may have several in several languages: `language` is
                # the family, which is what the generated project's own pruner reads, and `framework`
                # names what owns startup. They are the same word for three of the four backends and
                # deliberately not for the fourth.
                service = metadata["deployables"]["service"]
                self.assertEqual(service["language"], family_of(language))
                self.assertEqual(service.get("framework"), framework_of(language))
                self.assertNotIn("backend", metadata)
                self.assertNotIn("selection", metadata)
                self.assertEqual(metadata["frontend"], "none")
                self.assertNotIn("web", metadata["deployables"])
                self.assertTrue((repo / ".git").is_dir())
                self.assertEqual(
                    subprocess.run(
                        ["git", "rev-list", "--count", "HEAD"],
                        cwd=repo,
                        check=True,
                        text=True,
                        stdout=subprocess.PIPE,
                    ).stdout.strip(),
                    "1",
                )
                self.assertEqual(
                    subprocess.run(
                        ["git", "status", "--porcelain=v1"],
                        cwd=repo,
                        check=True,
                        text=True,
                        stdout=subprocess.PIPE,
                    ).stdout,
                    "",
                )
                self.assertFalse((repo / ".slipwai-manifest.json").exists())
                # Spec Kit is never vendored; `./init` installs the current release. The only things
                # scaffolded under `.specify/` are the two layers Spec Kit does not own: the preset
                # overrides and the extension hooks.
                for owned in (".specify/templates", ".specify/integrations", ".specify/memory", ".specify/scripts"):
                    self.assertFalse((repo / owned).exists(), owned)
                self.assertTrue((repo / ".specify/extensions.yml").is_file())
                self.assertTrue(os.access(repo / "init", os.X_OK))
                # Driven off the table rather than naming `mvnw`, so a backend that adds a script of its
                # own is covered by declaring it. The bit matters more here than anywhere else in the
                # tree: `./mvnw` is how every Make target in a Java project reaches its build, so a lost
                # `chmod +x` is a fresh clone where nothing but `make help` works.
                for template in BACKEND_EXECUTABLES[language]:
                    executable = for_app(template, "apps/service")
                    landed = repo / executable
                    self.assertTrue(landed.is_file(), f"{language}: {executable} never reached the project")
                    self.assertTrue(os.access(landed, os.X_OK), f"{language}: {executable} is not executable")
                self.assertTrue((repo / "apps/service").is_dir())
                self.assertTrue((repo / "packages/.gitkeep").is_file())
                self.assertTrue((repo / "commands/drive.md").is_file())
                self.assertTrue((repo / "skills/testing/SKILL.md").is_file())
                for path in repo.rglob("*"):
                    if path.is_file() and ".git" not in path.parts:
                        self.assertNotIn("{{example:", path.read_text(errors="ignore"), path.relative_to(repo))
                makefile = (repo / "Makefile").read_text()
                for target in (
                    "help:", "install:", "agents:", "agents-list:", "check-extensions:", "check-agents:",
                    "typecheck:", "lint:", "check-imports:", "check-migrations:", "check-speckit:",
                    "check-constitution:", "constitution-requirements:", "check-benchmark:", "test:",
                    "test-integration:", "adversarial:", "mutation:", "audit:", "verify:", "ci:",
                ):
                    self.assertIn(target, makefile)
                # In `verify`, not merely present: a gate reachable only by name is a gate nobody runs.
                self.assertRegex(makefile, r"verify: [^\n]*\bcheck-constitution\b")
                self.assertRegex(makefile, r"verify: [^\n]*\bcheck-benchmark\b")
                self.assertEqual("check-model:" in makefile, profile == "event-modelling")
                self.assertEqual("model:" in makefile, profile == "event-modelling")
                # A pipeline the constitution calls deterministic cannot fetch a tool by a moving
                # reference: `@latest` and `@master` resolve to whatever exists on the day CI runs.
                # Comments are excluded, since explaining why a pin is not `@latest` requires writing it.
                recipes = "\n".join(
                    line for line in makefile.splitlines() if not line.lstrip().startswith("#")
                )
                self.assertNotIn("@latest", recipes)
                self.assertNotIn("@master", recipes)
                gremlins = repo / "apps/service/.gremlins.yaml"
                wrapper = repo / "scripts/go-mutation.py"
                coverage = repo / "scripts/go-coverage.py"
                if language == "go":
                    # Gremlins, pinned to a release and run through `go run` by the wrapper that stages the
                    # service beside the workspace modules it imports, so the tool is never a dependency of
                    # the module it mutates. The pin is in the wrapper, and is a release there too.
                    self.assertIn("python3 scripts/go-mutation.py apps/service", recipes)
                    self.assertIn("github.com/go-gremlins/gremlins/cmd/gremlins@v0.6.0", wrapper.read_text())
                    self.assertNotIn("__GO_GREMLINS__", wrapper.read_text())
                    self.assertNotIn("@latest", wrapper.read_text())
                    # The gate is in the service's `.gremlins.yaml` and nowhere else: Gremlins 0.6.0 reads
                    # a threshold flag as a string and gates nothing, so a recipe that grew a `--threshold`
                    # would be a gate that never fails. Integration mode is on, so a test in another
                    # package counts, and timeouts are wide enough that none is dropped from the score.
                    self.assertNotIn("--threshold", recipes)
                    self.assertNotIn("go-mutesting", recipes)
                    settings = self.settings(gremlins.read_text())
                    for line in (
                        "efficacy: 99.99", "integration: true", 'coverpkg: "./..."', "timeout-coefficient: 10",
                    ):
                        self.assertIn(line, settings)
                    # The note above the target names the project's own file, not the template's word.
                    self.assertIn("`apps/service/.gremlins.yaml`", makefile)
                    self.assertNotIn("__APP__", makefile)
                    # `make test` writes a cross-package profile and holds it to a minimum on the line.
                    self.assertIn(
                        "cd apps/service && go test -coverpkg=./... -coverprofile=coverage.out ./...", recipes
                    )
                    self.assertIn("python3 scripts/go-coverage.py apps/service 70", recipes)
                    self.assertTrue(coverage.is_file())
                    self.assertIn('go-coverage.py" "$app" 70', (repo / "scripts/verify").read_text())
                    # Three analysers in the lint gate, widening as they go, and the third is pinned as a
                    # module tool rather than installed — so it runs from the cache `go mod download` fills.
                    self.assertIn("cd apps/service && go tool staticcheck ./...", recipes)
                    self.assertIn("go vet ./... && go tool staticcheck ./...", (repo / "scripts/verify").read_text())
                    self.assertIn(
                        "tool honnef.co/go/tools/cmd/staticcheck",
                        (repo / "apps/service/go.mod").read_text(),
                    )
                else:
                    self.assertFalse(gremlins.exists(), language)
                    self.assertFalse(wrapper.exists(), language)
                    self.assertFalse(coverage.exists(), language)
                self.assertEqual(
                    "npm" in (repo / ".claude/settings.json").read_text(),
                    language == "typescript",
                )

            self.assertTrue((repos[("standard", "typescript")] / "package-lock.json").is_file())
            self.assertTrue((repos[("standard", "typescript")] / "apps/service/package.json").is_file())
            self.assertTrue((repos[("standard", "python")] / "apps/service/tests/test_health.py").is_file())
            self.assertTrue((repos[("standard", "go")] / "apps/service/health/health_test.go").is_file())
            self.assertTrue((repos[("standard", "go")] / "go.work").is_file())
            # Both Java backends, and the shared half is the point: the wrapper and the three analyser
            # configurations come from `assets/languages/java/build/`, so each one arriving in *both*
            # projects is what proves the family tree is read rather than only the backend's own.
            for backend in ("java-quarkus", "java-spring"):
                java = repos[("standard", backend)]
                self.assertTrue((java / "apps/service/pom.xml").is_file(), backend)
                self.assertTrue((java / "apps/service/mvnw").is_file(), backend)
                # The analysers' configuration is committed rather than left to each plugin's default,
                # so a generated project can tune the rules instead of discovering them.
                for configured in ("checkstyle.xml", "pmd-ruleset.xml", "spotbugs-exclude.xml"):
                    self.assertTrue(
                        (java / "apps/service/config" / configured).is_file(), f"{backend}: {configured}"
                    )
                segment = f"productstandard{backend.replace('-', '')}"
                self.assertTrue(
                    (java / f"apps/service/src/test/java/com/example/{segment}/health"
                            "/HealthStatusTest.java").is_file(),
                    backend,
                )
                # No aggregator pom above the module: a single-module Maven build needs no parent, and
                # one that exists only to list a single module is a file to keep in step for nothing.
                self.assertFalse((java / "pom.xml").exists(), backend)

            # Where the two Java backends part company: Spring Boot needs a class to start from, because
            # `@SpringBootApplication` is both the entry point and the root of component scanning, while
            # Quarkus finds its beans without one. That is the whole visible difference in the skeleton,
            # and asserting it keeps "the framework owns startup" from meaning two different things
            # nobody wrote down.
            spring = repos[("standard", "java-spring")]
            self.assertTrue(
                (spring / "apps/service/src/main/java/com/example/productstandardjavaspring"
                          "/ServiceApplication.java").is_file()
            )
            self.assertFalse(
                (repos[("standard", "java-quarkus")]
                 / "apps/service/src/main/java/com/example/productstandardjavaquarkus"
                   "/ServiceApplication.java").exists()
            )

            for language in CATALOG["backends"]:
                event_repo = repos[("event-modelling", language)]
                standard_repo = repos[("standard", language)]
                # Both profiles carry a preset layer and its documentation: minimum CD is the floor in
                # each of them, and the core constitution template states no floor at all. What differs
                # is which templates the preset overrides, asserted per profile below.
                for shared in (
                    ".specify/presets/.registry",
                    "docs/speckit-preset.md",
                ):
                    self.assertTrue((event_repo / shared).is_file(), shared)
                    self.assertTrue((standard_repo / shared).is_file(), shared)
                for relative in (
                    ".github/workflows/event-model.yml",
                    ".specify/presets/event-modelling/preset.yml",
                    ".specify/presets/event-modelling/templates/constitution-template.md",
                    ".specify/presets/event-modelling/templates/plan-template.md",
                    ".specify/presets/event-modelling/templates/tasks-template.md",
                    "commands/example-map.md",
                    "commands/validate-code-against-model.md",
                    "docs/event-model/model.yaml",
                    "docs/event-modeling-to-code.md",
                    "docs/first-slice.md",
                    "skills/event-modeling/SKILL.md",
                    "skills/event-sourcing/SKILL.md",
                    "skills/global-event-model/SKILL.md",
                    "scripts/event-model/render.ts",
                    "scripts/event-model/patch-mermaid-swimlanes.ts",
                    "scripts/event-model/page.ts",
                    "scripts/event-model/package.json",
                ):
                    self.assertTrue((event_repo / relative).is_file(), relative)
                    self.assertFalse((standard_repo / relative).exists(), relative)
                for repo_under_test, preset_name, overridden in (
                    (event_repo, "event-modelling", ("constitution-template", "plan-template", "tasks-template")),
                    (standard_repo, "standard", ("constitution-template",)),
                ):
                    registry = json.loads((repo_under_test / ".specify/presets/.registry").read_text())
                    self.assertEqual(list(registry["presets"]), [preset_name])
                    self.assertTrue(registry["presets"][preset_name]["enabled"])
                    preset = (
                        repo_under_test / f".specify/presets/{preset_name}/preset.yml"
                    ).read_text()
                    # The preset overrides templates by name through Spec Kit's resolver rather than
                    # vendoring Spec Kit, so the only version coupling is a stated floor.
                    self.assertIn('speckit_version: ">=0.16.0"', preset)
                    for declared in overridden:
                        self.assertIn(f'file: "templates/{declared}.md"', preset)
                        self.assertTrue(
                            (
                                repo_under_test
                                / f".specify/presets/{preset_name}/templates/{declared}.md"
                            ).is_file(),
                            f"{preset_name}/{declared}",
                        )
                    # Everything not overridden keeps inheriting upstream improvements. The
                    # standard profile overrides only the constitution, because that is the
                    # only core template this profile's floor makes actively misleading.
                    for inherited in (
                        "spec-template",
                        "checklist-template",
                        "plan-template",
                        "tasks-template",
                    ):
                        if inherited in overridden:
                            continue
                        self.assertNotIn(f'file: "templates/{inherited}.md"', preset)
                self.assertIn(
                    "Never edit a Spec Kit-managed file in place",
                    (event_repo / "AGENTS.md").read_text(),
                )
                event_readme = (event_repo / "README.md").read_text()
                self.assertIn("One command runs the loop", event_readme)
                # The address itself, not a hardcoded copy: both halves come from the environment
                # (`GITEA_OWNER`, `GITEA_PAGES_URL`), so a literal would stop checking the two files agree.
                page_url = event_model_page_url(event_repo.name)
                self.assertIn(page_url, event_readme)
                self.assertIn("<!-- event-model:start -->", event_readme)
                model_yaml = (event_repo / "docs/event-model/model.yaml").read_text()
                self.assertIn(f"\n  page: {page_url}\n", model_yaml)
                self.assertIn(
                    "The four patterns", (event_repo / "docs/event-model/README.md").read_text()
                )
                event_workflow = (event_repo / ".github/workflows/event-model.yml").read_text()
                self.assertIn("run: make model", event_workflow)
                self.assertIn("apparmor_restrict_unprivileged_userns", event_workflow)
                # upload-artifact v4 works only on github.com; Gitea speaks v3, so both sit behind the forge check.
                for version, forge in (("v4", "=="), ("v3", "!=")):
                    step = f"uses: actions/upload-artifact@{version}\n        if: github.server_url {forge} 'https://github.com'"
                    self.assertIn(step, event_workflow)
                # upload-artifact v4 only works on github.com; everywhere else the `pages` branch is the output.
                self.assertIn(
                    "uses: actions/upload-artifact@v4\n        if: github.server_url == 'https://github.com'",
                    event_workflow,
                )
                for relative in STANDARD_OVERRIDES:
                    event_text = (event_repo / relative).read_text()
                    standard_text = (standard_repo / relative).read_text()
                    self.assertNotEqual(standard_text, event_text, relative)
                    self.assertNotRegex(
                        standard_text.lower(),
                        r"event[- ]sourc|event model|stream identity|event store|\bdecider\b",
                        relative,
                    )
                # A skill about a capability the project has ships in both profiles, and one about a
                # capability it does not have ships in neither. `typescript-strict` is the pair that shows
                # the difference from the pseudocode rule: in a Go project it is not guidance whose
                # examples are in the wrong language, it is guidance about a language nothing here is
                # written in — and the discipline it teaches is still stated, language-independently, by
                # `check-constitution`'s `strict-typing` requirement, which every project carries.
                strict = "skills/typescript-strict/SKILL.md"
                expected = family_of(language) == "typescript"
                self.assertEqual(expected, (event_repo / strict).is_file(), language)
                self.assertEqual(expected, (standard_repo / strict).is_file(), language)
                for repo in (event_repo, standard_repo):
                    self.assertIn("strict-typing", (repo / "scripts/check-constitution.py").read_text())

    def test_the_sliced_suites_read_their_slice_and_nothing_wider(self) -> None:
        """The two suites the matrix jobs run take their backends from `backends_under_test()` and nowhere
        else. One that walked the catalog directly would do the same work in all five jobs, which is what
        the scaffold above did before it moved here: every backend generated five times over."""
        for sliced in ("test_matrix", "test_images"):
            source = (Path(__file__).parent / f"{sliced}.py").read_text()
            self.assertIn("backends_under_test()", source, f"{sliced} does not read its slice")
            self.assertNotIn(
                'CATALOG["backends"]', source, f"{sliced} walks the whole catalog, in a job that runs once per backend"
            )
