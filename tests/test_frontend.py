"""`apps/web` is an independent deployable: it consumes contracts and never reaches into the backend."""
from __future__ import annotations

import json
import subprocess
import tempfile

from support import FactoryTestCase

from slipwai.catalog import CATALOG, family_of, framework_of


class FrontendTest(FactoryTestCase):
    def test_react_frontend_is_independent_and_event_sourcing_is_backend_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for profile in CATALOG["profiles"]:
                for language in CATALOG["backends"]:
                    repo = self.generate(
                        directory,
                        f"web-{profile}-{language}",
                        profile,
                        language,
                        "react-vite",
                    )
                    metadata = json.loads((repo / "project.json").read_text())
                    # The *family*, with the framework as its own field beside it — which is the shape
                    # `project.json` deliberately has, and the shape the two differ in for a backend named
                    # for the framework that owns its startup.
                    self.assertEqual(metadata["deployables"]["service"]["language"], family_of(language))
                    self.assertEqual(
                        metadata["deployables"]["service"].get("framework"), framework_of(language)
                    )
                    self.assertEqual(
                        metadata["deployables"]["service"]["eventSourced"],
                        profile == "event-modelling",
                    )
                    self.assertEqual(
                        {key: metadata["deployables"]["web"][key] for key in ("language", "framework", "eventSourced")},
                        {"language": "typescript", "framework": "react-vite", "eventSourced": False},
                    )
                    self.assertEqual(
                        metadata["deployables"]["web"]["capabilities"],
                        ["frontend", "typescript", "react", "vite"],
                    )
                    self.assertTrue((repo / "apps/web/src/App.tsx").is_file())
                    self.assertTrue((repo / "apps/web/tests/App.test.tsx").is_file())
                    self.assertTrue((repo / "package-lock.json").is_file())
                    self.assertIn("apps/web", json.loads((repo / "package.json").read_text())["workspaces"])
                    if profile == "event-modelling":
                        self.assertIn(
                            "Event sourcing applies only to `apps/service/**`",
                            (repo / "AGENTS.md").read_text(),
                        )
                        self.assertIn(
                            "it never owns streams, rehydrates Deciders",
                            (repo / "skills/event-sourcing/SKILL.md").read_text(),
                        )
                    web_text = "\n".join(
                        path.read_text()
                        for path in (repo / "apps/web").rglob("*")
                        if path.is_file()
                    ).lower()
                    self.assertNotRegex(web_text, r"event[- ]sourc|event store|stream identity|\bdecider\b")
                    self.assertTrue((repo / "skills/typescript-strict/SKILL.md").is_file())

    def test_every_browser_app_ships_the_flag_gate_it_is_told_to_use(self) -> None:
        """A flag hiding user-facing surface is a supported shape rather than something each project
        reinvents: one helper, one transform, and a value that is off unless it says `on`. Shipped whatever
        the production target is — `.env` is what sets it locally, and a project with no target has no other
        way to hide a half-built screen — while how it reaches a *deployed* browser is the `aws` target's
        (`tests/test_aws_flags.py`)."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "gated", "standard", "go", "react-vite")

            helper = (repo / "apps/web/src/flags.ts").read_text()
            self.assertIn("export function flagEnabled(", helper)
            self.assertIn("`VITE_FLAG_${key.toUpperCase().replace(/-/g, '_')}`", helper)
            self.assertTrue((repo / "apps/web/tests/flags.test.ts").is_file())

    def test_frontend_cannot_import_backend_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory,
                "web-import-boundary",
                "standard",
                "go",
                "react-vite",
            )
            (repo / "apps/web/src/illegal.ts").write_text(
                "import value from '../../service/health/internal';\nvoid value;\n"
            )

            result = subprocess.run(
                ["python3", "scripts/check-imports.py"],
                cwd=repo,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("frontend imports backend implementation", result.stderr)

    def test_a_second_render_and_a_stylesheet_import_both_work_in_a_fresh_project(self) -> None:
        """The two things every real frontend project does first, proved against the real toolchain.

        Both were broken, and both broke in a way that reads as the developer's fault:

        - `tests/setup.ts` never registered `afterEach(cleanup)`. Testing Library auto-cleans only when it
          can find a *global* `afterEach`, and `vite.config.ts` deliberately leaves `test.globals` off — so
          the second `render` in a file mounted beside the first and `getByRole` failed with "found multiple
          elements", which looks like a broken component.
        - `tsconfig.json`'s explicit `types` list omitted `vite/client`, so the first `import './app.css'`
          failed typecheck with TS2882 while building and running perfectly.

        Asserted by running the project's own `test` and `typecheck`, not by reading the config: what
        matters is that the toolchain accepts the code, and the config is only how that is arranged.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "frontend-basics", language="typescript", frontend="react-vite",
                event_store="memory", http="none", auth="none",
            )
            install = subprocess.run(
                ["npm", "ci", "--no-audit", "--no-fund", "--loglevel=error"],
                cwd=repo, capture_output=True, text=True,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            # Two renders in one file: the case Testing Library's cleanup exists for. Inside a router,
            # because that is how `main.tsx` mounts the shell and `<Link>` needs one; the heading is the
            # project's own name in the header, which every variant of the app has.
            (repo / "apps/web/tests/Twice.test.tsx").write_text(
                "import { render, screen } from '@testing-library/react';\n"
                "import { MemoryRouter } from 'react-router';\n"
                "import { describe, expect, it } from 'vitest';\n\n"
                "import { App } from '../src/App';\n\n"
                "describe('rendered twice', () => {\n"
                "  it('mounts once', () => {\n"
                "    render(<MemoryRouter><App /></MemoryRouter>);\n"
                "    expect(screen.getByRole('heading', { level: 1 })).toBeVisible();\n"
                "  });\n\n"
                "  it('mounts once again, beside nothing left over', () => {\n"
                "    render(<MemoryRouter><App /></MemoryRouter>);\n"
                "    expect(screen.getByRole('heading', { level: 1 })).toBeVisible();\n"
                "  });\n"
                "});\n"
            )
            tests = subprocess.run(
                ["npm", "--workspace", "apps/web", "test"], cwd=repo, capture_output=True, text=True
            )
            self.assertEqual(
                tests.returncode,
                0,
                "a component rendered twice in one file leaks between tests:\n" + tests.stdout[-3000:],
            )

            # A stylesheet import, which is what every frontend adds before its second component.
            (repo / "apps/web/src/app.css").write_text("main { padding: 1rem; }\n")
            app = repo / "apps/web/src/App.tsx"
            app.write_text("import './app.css';\n" + app.read_text())
            typecheck = subprocess.run(
                ["npm", "--workspace", "apps/web", "run", "typecheck"],
                cwd=repo, capture_output=True, text=True,
            )
            self.assertEqual(
                typecheck.returncode,
                0,
                "importing a stylesheet fails typecheck:\n" + typecheck.stdout[-3000:],
            )

    def test_the_browser_app_ships_a_baseline_to_react_to_rather_than_browser_defaults(self) -> None:
        """A first slice demonstrated on an unstyled page gets feedback about the page.

        So the skeleton ships design tokens, a layout shell and styled elements — deliberately generic,
        and deliberately not nothing. `docs/design.md` is where a project records what it chose instead,
        which is why the page exists only where there is a browser surface to have chosen anything for.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "styled-web", frontend="react-vite")
            entry = (repo / "apps/web/src/main.tsx").read_text()

            # Imported once, from the entry point: they are the app's, not any screen's.
            self.assertIn("./styles/tokens.css", entry)
            self.assertIn("./styles/base.css", entry)
            tokens = (repo / "apps/web/src/styles/tokens.css").read_text()
            # Tokens as custom properties, light and dark, and a scale rather than a palette of one.
            self.assertIn("--colour-surface", tokens)
            self.assertIn("prefers-color-scheme: dark", tokens)
            self.assertIn("--space-3", tokens)
            base = (repo / "apps/web/src/styles/base.css").read_text()
            # The elements a browser already renders, so a slice writing `<button>` gets this project's.
            for element in ("button", "table", "input", "a {"):
                self.assertIn(element, base)
            # And the shell the route sits inside, with real landmarks rather than styled divs.
            shell = (repo / "apps/web/src/App.tsx").read_text()
            for landmark in ("<header", "<main", "<footer", "<nav"):
                self.assertIn(landmark, shell)

            page = repo / "docs/design.md"
            self.assertTrue(page.is_file())
            self.assertIn("apps/web/src/styles/tokens.css", page.read_text())
            # Linked from where somebody about to write a screen is already reading.
            self.assertIn("docs/design.md", (repo / "AGENTS.md").read_text())
            self.assertIn("docs/design.md", (repo / "skills/react-testing/SKILL.md").read_text())
            self.assertIn("[`design.md`](design.md)", (repo / "docs/README.md").read_text())

    def test_a_project_with_no_browser_surface_has_no_design_to_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "headless-service", frontend="none")

            self.assertFalse((repo / "docs/design.md").exists())
            self.assertNotIn("docs/design.md", (repo / "AGENTS.md").read_text())

    def test_a_browser_app_brings_the_two_design_skills_and_the_design_page_says_when(self) -> None:
        """The catalogue said how work is done and nothing about what a screen should look like or how to
        check one before it is demonstrated. `frontend-design` decides, `web-interface-guidelines` reviews,
        and both are named at the moment they are needed — the design page every browser slice reads
        first and the styled check in the demo stop — because a skill only listed in `skills/` is a skill
        nobody reaches for. The guidelines are a pinned file: a review that fetched them would silently not
        happen in a sandbox."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "designed-web", frontend="react-vite")

            for skill in ("frontend-design", "web-interface-guidelines"):
                text = (repo / f"skills/{skill}/SKILL.md").read_text()
                self.assertIn("capabilities: frontend", text)
                self.assertTrue((repo / f"skills/{skill}/LICENSE").is_file(), f"{skill} carries no LICENSE")
            guidelines = repo / "skills/web-interface-guidelines/references/guidelines.md"
            self.assertIn("### Anti-patterns", guidelines.read_text())
            wrapper = (repo / "skills/web-interface-guidelines/SKILL.md").read_text()
            self.assertNotIn("raw.githubusercontent.com", wrapper)

            page = (repo / "docs/design.md").read_text()
            self.assertIn("`skills/frontend-design`", page)
            self.assertIn("`skills/web-interface-guidelines`", page)
            self.assertIn("this page wins", page)
            drive = (repo / "commands/drive.md").read_text()
            self.assertIn("`skills/web-interface-guidelines`", drive)

            headless = self.generate(directory, "headless-again", frontend="none")
            for skill in ("frontend-design", "web-interface-guidelines"):
                self.assertFalse((headless / f"skills/{skill}").exists(), f"{skill} shipped with no browser app")
            self.assertNotIn("web-interface-guidelines", (headless / "commands/drive.md").read_text())

    def test_the_browser_app_calls_its_service_through_a_generated_client(self) -> None:
        """The types the app expects and the shapes the service serialises are one declaration.

        `packages/api-client` is generated from the committed document, so a route that changes its
        response breaks the build at the line that reads the field rather than in front of somebody. The
        generated file is not committed: it is a build output, and a committed one is one people edit.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "typed-client", frontend="react-vite")
            manifest = json.loads((repo / "packages/api-client/package.json").read_text())

            self.assertEqual(manifest["name"], "@packages/api-client")
            self.assertIn("openapi-typescript", manifest["devDependencies"])
            self.assertIn("../../apps/service/openapi.json", manifest["scripts"]["build"])
            self.assertFalse((repo / "packages/api-client/src/schema.ts").exists())
            self.assertIn("packages/api-client/src/schema.ts", (repo / ".gitignore").read_text())
            # The document itself is committed, and `check-openapi` is what holds it to the routes.
            self.assertTrue((repo / "apps/service/openapi.json").is_file())
            self.assertIn("check-openapi", (repo / "Makefile").read_text())
            # And the one route calls through the client rather than writing a path out a second time.
            route = (repo / "apps/web/src/routes/Home.tsx").read_text()
            self.assertIn("@packages/api-client", route)
            self.assertIn("/health", route)

    def test_nothing_is_awaited_before_the_first_paint(self) -> None:
        """A top-level `await` in the entry point is a blank tab for as long as the request takes."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "first-paint", frontend="react-vite")
            entry = (repo / "apps/web/src/main.tsx").read_text()

            before = entry[: entry.index("createRoot(")]
            self.assertNotIn("await ", before)
            # The flags are still resolved before a gated screen paints — inside a component, where
            # there is somewhere to render "loading" and somewhere to render a failure.
            self.assertIn("loadFlags", (repo / "apps/web/src/App.tsx").read_text())

    def test_a_transport_that_publishes_nothing_says_so_rather_than_shipping_half_a_client(self) -> None:
        """Both Java frameworks publish no API document, so there is nothing to generate a client from.

        The absence reads as an omission unless it is written down — a reader who finds no
        `packages/api-client` would reasonably conclude the frontend was left half-wired — so the route
        itself, `docs/design.md` and `AGENTS.md` all say what is missing and what would buy it back.
        """
        with tempfile.TemporaryDirectory() as directory:
            for backend in ("java-quarkus", "java-spring"):
                repo = self.generate(directory, f"unpublished-{backend}", "standard", backend, "react-vite")

                self.assertFalse((repo / "packages/api-client").exists())
                route = (repo / "apps/web/src/routes/Home.tsx").read_text()
                # It names the package that is missing, in prose, and imports nothing from it.
                self.assertNotIn("@packages/api-client", route)
                self.assertIn("packages/api-client", route)
                # Typed as much as an undeclared shape can honestly be, and no further.
                self.assertIn("Record<string, unknown>", route)
                for page in ("docs/design.md", "AGENTS.md"):
                    self.assertIn("packages/api-client", (repo / page).read_text(), page)
                # And its test drives the same states, through a fetch it writes itself.
                self.assertIn("HomeView", (repo / "apps/web/tests/routes/Home.test.tsx").read_text())

    def test_the_dev_server_forwards_the_one_path_the_skeleton_s_screen_calls(self) -> None:
        """A demo that shows "the service could not be reached" on a working machine teaches the wrong
        thing. With nowhere to deploy there is no product route to call, so the probe is forwarded too."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "proxied", frontend="react-vite")
            proxy = (repo / "apps/web/vite.config.ts").read_text()

            self.assertIn("'/api': { target: apiOrigin", proxy)
            self.assertIn("'/health': { target: apiOrigin", proxy)
            self.assertIn("'/health'", (repo / "apps/web/src/routes/Home.tsx").read_text())
