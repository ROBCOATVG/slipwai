"""The canonical toolkit is the single source: fully routed, self-contained, and honest about its examples."""
from __future__ import annotations

import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_add_service import add_service

from slipwai.assets import (
    PROFILE_ROOT,
    ROOT,
    TOOLKIT_ROOT,
)
from slipwai.catalog import CATALOG, family_of
from slipwai.errors import GenerationError
from slipwai.examples import (
    EXAMPLE_MARKER,
    FRONTEND_INHERENT_SKILLS,
    RAW_TYPESCRIPT_FENCE,
    Speaker,
    resolve_examples,
    resolve_examples_for,
)
from slipwai.toolkit import (
    STANDARD_OVERRIDES,
    toolkit_treatment,
)


class ToolkitTest(FactoryTestCase):
    def test_canonical_toolkit_is_self_contained_and_fully_routed(self) -> None:
        sources = [path for path in TOOLKIT_ROOT.rglob("*") if path.is_file()]
        self.assertGreater(len(sources), 150)
        for source in sources:
            self.assertNotIn("event-modelling-" + "starter", source.read_text())
        for profile in CATALOG["profiles"]:
            for source in sources:
                relative = source.relative_to(TOOLKIT_ROOT).as_posix()
                self.assertIn(
                    toolkit_treatment(relative, profile),
                    {"copied", "profile-transformed", "profile-excluded"},
                )

        standard_overlay = PROFILE_ROOT / "standard"
        overlay_paths = {
            path.relative_to(standard_overlay).as_posix()
            for path in standard_overlay.rglob("*")
            if path.is_file()
        }
        # An overlay file either replaces a canonical toolkit file or adds one this profile alone has,
        # and the difference is not a matter of taste: a replacement has to be declared, or the toolkit
        # copy silently wins and the override never ships. So the split is derived from the toolkit
        # rather than from a second hand-kept list — anything shadowing a toolkit path and missing from
        # STANDARD_OVERRIDES fails here.
        self.assertLessEqual(STANDARD_OVERRIDES, overlay_paths)
        for relative in STANDARD_OVERRIDES:
            self.assertEqual(toolkit_treatment(relative, "standard"), "profile-transformed")
        for relative in sorted(overlay_paths - STANDARD_OVERRIDES):
            self.assertFalse((TOOLKIT_ROOT / relative).exists(), relative)
            self.assertEqual(toolkit_treatment(relative, "standard"), "copied")

        # The Spec Kit preset layer is the one thing this profile adds rather than replaces, and it is
        # what installs minimum CD into `/speckit-constitution`. The core template states no floor, so
        # without it a standard project drafts a constitution that fails its own gate.
        self.assertEqual(
            overlay_paths - STANDARD_OVERRIDES,
            {
                ".specify/presets/.registry",
                ".specify/presets/standard/preset.yml",
                ".specify/presets/standard/templates/constitution-template.md",
                "docs/speckit-preset.md",
            },
        )
        # The template is held to the same vocabulary bar as every other file this profile replaces:
        # `make check-speckit` rejects a ratified constitution that mandates event sourcing, so shipping
        # a template that suggests it would hand the team a document they cannot ratify.
        self.assertNotRegex(
            (
                standard_overlay
                / ".specify/presets/standard/templates/constitution-template.md"
            ).read_text().lower(),
            r"event[- ]sourc|event model|stream identity|event store|\bdecider\b",
        )

    def test_every_file_that_still_carries_typescript_says_it_is_pseudocode(self) -> None:
        """The note has to be on the file that carries the code, not only on the skill it belongs to.

        A skill routes the reader straight into `resources/` and `references/`, and that is where nearly
        all of the not-yet-translated TypeScript lives — `cli-design` keeps all 44 of its TypeScript
        blocks there and none in `SKILL.md`. A disclaimer stamped only on the entry point never reaches
        whoever opens the resource. Exempt are the skills whose TypeScript is the real subject rather
        than a stand-in; those ship untouched whatever the backend language is.
        """
        note = "TypeScript-as-pseudocode"
        with tempfile.TemporaryDirectory() as directory:
            # With the browser app, because the skills whose TypeScript is the real subject are the ones a
            # project earns by having a frontend, and they are what this case is about below.
            repo = self.generate(directory, "pseudocode", "event-modelling", "go", "react-vite")

            undisclaimed = sorted(
                path.relative_to(repo).as_posix()
                for path in (repo / "skills").rglob("*.md")
                if path.relative_to(repo / "skills").parts[0] not in FRONTEND_INHERENT_SKILLS
                and RAW_TYPESCRIPT_FENCE.search(path.read_text())
                and note not in path.read_text()
            )
            self.assertEqual(undisclaimed, [], "TypeScript with nothing saying it is pseudocode")
            self.assertIn(note, (repo / "skills/cli-design/resources/stream-contracts.md").read_text())

            # The entry point warns too, so the reader is told before being routed rather than after —
            # `cli-design/SKILL.md` carries no TypeScript of its own and would otherwise say nothing.
            entry = (repo / "skills/cli-design/SKILL.md").read_text()
            self.assertIn(note, entry)
            self.assertNotRegex(entry, r"```(typescript|ts)\n")

            # A skill whose TypeScript is the point is not disclaimed, and still ships to a Go backend —
            # the browser app is what earns it, not the language the service is written in.
            for skill in ("react-testing", "front-end-testing", "bff-design", "bff-entry-points"):
                self.assertTrue((repo / "skills" / skill / "SKILL.md").is_file(), skill)
            self.assertNotIn(note, (repo / "skills/react-testing/SKILL.md").read_text())

            # And with no browser app they are not there at all, which is the other rule: a disclaimer is
            # for guidance in the wrong language, not for guidance about something this project has not got.
            headless = self.generate(directory, "headless", "event-modelling", "go")
            for skill in ("react-testing", "front-end-testing", "bff-design", "bff-entry-points"):
                self.assertFalse((headless / "skills" / skill).exists(), skill)
            self.assertTrue((headless / "skills/tdd/SKILL.md").is_file())

            # Nothing is disclaimed in a TypeScript project, where the examples are the real thing.
            ts_repo = self.generate(directory, "native-ts", "event-modelling", "typescript")
            self.assertNotIn(note, (ts_repo / "skills/cli-design/SKILL.md").read_text())

    def test_every_example_marker_resolves_for_every_catalog_language(self) -> None:
        marker_sources = [path for path in TOOLKIT_ROOT.rglob("*") if path.is_file()]
        for profile in CATALOG["profiles"]:
            overlay = PROFILE_ROOT / profile
            if overlay.is_dir():
                marker_sources += [path for path in overlay.rglob("*") if path.is_file()]

        markers: set[tuple[str, str]] = set()
        for source in marker_sources:
            for match in EXAMPLE_MARKER.finditer(source.read_text()):
                markers.add((match.group(1), match.group(2)))

        # Resolved against the backend first and its family second, which is exactly what
        # `resolve_examples` does — so a backend covered only by its family's snippets passes, and one
        # with a gap in both fails here rather than at generation time.
        missing = [
            f"{backend}/{skill}/{example_id}"
            for backend in CATALOG["backends"]
            for skill, example_id in sorted(markers)
            if not any(
                (ROOT / f"assets/languages/{owner}/examples/{skill}/{example_id}.md").is_file()
                for owner in dict.fromkeys((backend, family_of(backend)))
            )
        ]
        self.assertEqual(missing, [], "half-translated example: missing snippet(s) " + ", ".join(missing))

    def test_resolve_examples_fails_closed_on_a_missing_snippet(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(GenerationError, "missing python example snippet"),
        ):
            resolve_examples("{{example: testing/some-example}}", "python", root=Path(directory))

    def test_a_marker_speaks_every_language_the_services_are_written_in(self) -> None:
        """One language gives the bare snippet, as it always did; two give one labelled block each, in
        service order; two backends sharing a family's snippet share one block rather than repeating it."""
        marker = "{{example: hexagonal-architecture/port-interface-definitions}}"
        typescript = Speaker("typescript", "typescript", "TypeScript — `apps/api`")
        go = Speaker("go", "go", "Go — `apps/ledger`")
        self.assertEqual(resolve_examples_for(marker, [typescript]), resolve_examples(marker, "typescript"))
        both = resolve_examples_for(marker, [typescript, go])
        self.assertEqual(
            both,
            f"**{typescript.label}**\n\n{resolve_examples(marker, 'typescript')}\n\n"
            f"**{go.label}**\n\n{resolve_examples(marker, 'go')}",
        )
        spring = Speaker("java-spring", "java", "Java (Spring Boot) — `apps/service`")
        quarkus = Speaker("java-quarkus", "java", "Java (Quarkus) — `apps/q`")
        shared = resolve_examples_for(marker, [spring, quarkus])
        self.assertTrue(shared.startswith(f"**{spring.label}, {quarkus.label}**\n\n```java"))
        self.assertEqual(shared.count("```java"), 1)

    def test_adding_a_service_in_another_language_teaches_the_skills_that_language(self) -> None:
        """The four skills with example snippets are regenerated by `add-service`, and afterwards carry a
        block per language, labelled for the service it is written for. A project without TypeScript that
        gains a TypeScript service stops disclaiming its TypeScript as pseudocode."""
        skills = ("domain-driven-design", "event-sourcing", "hexagonal-architecture", "testing")
        note = "TypeScript-as-pseudocode"
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "polyglot", "event-modelling", "typescript", "react-vite")
            result = add_service(repo, "ledger", "--language", "go")
            self.assertEqual(result.returncode, 0, result.stderr)
            for skill in skills:
                self.assertIn(f"skills/{skill}/SKILL.md", result.stdout, skill)
                text = (repo / "skills" / skill / "SKILL.md").read_text()
                self.assertIn("**TypeScript — `apps/service`**\n\n```typescript", text, skill)
                self.assertIn("**Go — `apps/ledger`**\n\n```go", text, skill)
                self.assertNotIn(note, text, skill)
            # A resource file carries the blocks too, not only the entry point.
            resource = (repo / "skills/hexagonal-architecture/resources/worked-example.md").read_text()
            self.assertIn("**Go — `apps/ledger`**", resource)
            self.assertNotIn("skills/cli-design", result.stdout)

            go_first = self.generate(directory, "go-first", "event-modelling", "go")
            self.assertIn(note, (go_first / "skills/cli-design/SKILL.md").read_text())
            result = add_service(go_first, "portal", "--language", "typescript")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(note, (go_first / "skills/cli-design/SKILL.md").read_text())
            self.assertIn("skills/cli-design/SKILL.md", result.stdout)

            go_python = self.generate(directory, "go-python", "event-modelling", "go")
            result = add_service(go_python, "batch", "--language", "python")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                "TypeScript-as-pseudocode until idiomatic Go and Python versions land",
                (go_python / "skills/cli-design/SKILL.md").read_text(),
            )
