"""The npm workspace's lint and format gate: one Biome at the root, and nothing else.

Split out of `tests/test_monorepos.py`, which owns the shape of a generated repository across every
backend at once; this owns the one toolchain, across the projects that have it — a Node service, a browser
app beside a service in another language, and a project with neither. Generation alone, no toolchain:
whether Biome is *happy* with what the factory ships is `tests/test_matrix.py`, which runs the real thing.
"""
from __future__ import annotations

import json
import tempfile

from support import FactoryTestCase

from slipwai.assets import ROOT
from slipwai.project.biome import biome_version

# The two manifests that pin it, and therefore the two that npm hoists one copy of.
MANIFESTS = ("assets/languages/typescript/app/package.json", "assets/frontends/react-vite/app/package.json")


class BiomeTest(FactoryTestCase):
    def test_a_node_service_is_linted_and_formatted_by_one_biome_at_the_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "biome-service", "standard", "typescript")

            configuration = (repo / "biome.jsonc").read_text()
            service = json.loads((repo / "apps/service/package.json").read_text())

            # `lint` is the whole of it — rules, formatting and import order in one pass — and
            # `--error-on-warnings` because a rule Biome rates a warning is still a gate here.
            self.assertEqual(service["scripts"]["lint"], "biome check --error-on-warnings")
            self.assertEqual(service["scripts"]["format"], "biome format --write")
            self.assertEqual(service["scripts"]["typecheck"], "tsc --noEmit")
            self.assertIn("npm run lint", service["scripts"]["verify"])
            self.assertEqual(service["devDependencies"]["@biomejs/biome"], biome_version())
            # The configuration is checked against the schema of the very Biome npm installs.
            self.assertIn(f"schemas/{biome_version()}/schema.json", configuration)
            # 100 columns, the width this repository already holds its Python to.
            self.assertIn('"lineWidth": 100', configuration)
            # The two rules no recommended set ships, which the linter this replaced did carry.
            self.assertIn('"noExplicitAny": "error"', configuration)
            self.assertIn("scripts/domain-purity.grit", configuration)
            plugin = (repo / "scripts/domain-purity.grit").read_text()
            self.assertIn("The domain must not read the clock", plugin)
            self.assertIn("The domain must be deterministic", plugin)

            makefile = (repo / "Makefile").read_text()
            # `format` writes what `lint` checks, over each npm package rather than `.` — `packages/`
            # is not only npm — and is never a prerequisite of `verify`, because a gate that rewrites
            # the tree always passes.
            self.assertIn('npm exec -- biome format --write "$${dir%/}"', makefile)
            self.assertIn('[ -f "$$dir/package.json" ] || continue', makefile)
            self.assertNotIn("biome format --write .", makefile)
            self.assertNotIn("verify: format", makefile)

    def test_format_does_not_walk_a_non_npm_tree_under_packages(self) -> None:
        """The glob in `biome.jsonc` still names `packages/**`, because one configuration owns the rules
        for every npm package. `make format` used to pass `.` and so honoured that glob over a Go module
        whose JSON is digested as raw bytes; `make lint` never did, being scoped to each npm workspace.
        The recipe discovers the same way `build-packages` does, so adding a Go module does not need an
        exclude in `biome.jsonc`."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "biome-go-pkg", "standard", "go", "react-vite")

            makefile = (repo / "Makefile").read_text()
            configuration = (repo / "biome.jsonc").read_text()
            self.assertIn('"packages/**"', configuration)
            self.assertIn('npm exec -- biome format --write "$${dir%/}"', makefile)
            self.assertIn('[ -f "$$dir/package.json" ] || continue', makefile)
            self.assertNotIn("biome format --write .", makefile)
            self.assertIn("gofmt -w $(GO_MODULES)", makefile)
            self.assertIn("GO_MODULES := apps/service\n", makefile)

    def test_nothing_of_the_linter_it_replaced_is_left(self) -> None:
        """ESLint parsed TypeScript with Babel because typescript-eslint refuses TypeScript 7, which cost
        the type-aware rules and `no-unused-vars`. Its configuration and its whole dependency tree go."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "biome-replaces", "standard", "typescript", "react-vite")

            self.assertFalse((repo / "apps/service/eslint.config.js").exists())
            self.assertFalse((repo / "eslint.config.js").exists())
            for manifest in ("apps/service/package.json", "apps/web/package.json"):
                declared = json.loads((repo / manifest).read_text())["devDependencies"]
                for gone in ("eslint", "@eslint/js", "@babel/core", "@babel/eslint-parser", "typescript-eslint"):
                    self.assertNotIn(gone, declared, manifest)
            lock = (repo / "package-lock.json").read_text()
            self.assertNotIn("node_modules/eslint", lock)
            self.assertIn("node_modules/@biomejs/biome", lock)

    def test_a_browser_app_beside_another_language_gets_the_same_linter(self) -> None:
        """The frontend had no linter at all — `lint` was a second `tsc --noEmit` — and a project whose
        services are Python still has TypeScript in `apps/web` to hold to something."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "biome-web", "standard", "python", "react-vite")

            web = json.loads((repo / "apps/web/package.json").read_text())
            self.assertEqual(web["scripts"]["lint"], "biome check --error-on-warnings")
            self.assertEqual(web["scripts"]["format"], "biome format --write")
            # `typecheck` was a whole `vite build`, which is a build and not a type check.
            self.assertEqual(web["scripts"]["typecheck"], "tsc --noEmit -p tsconfig.json")
            self.assertTrue((repo / "biome.jsonc").is_file())
            self.assertIn("npm --workspace apps/web run lint", (repo / "Makefile").read_text())

    def test_a_project_with_no_npm_workspace_gets_no_configuration_and_no_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "biome-none", "standard", "go")

            self.assertFalse((repo / "biome.jsonc").exists())
            self.assertFalse((repo / "scripts/domain-purity.grit").exists())
            self.assertNotIn("biome", (repo / "Makefile").read_text())

    def test_both_manifests_pin_the_same_biome(self) -> None:
        """npm hoists one copy to the workspace root, so a project whose two manifests disagreed would be
        linted by whichever of them won — and `biome_version` is what the `$schema` URL is stamped from."""
        pins = {
            json.loads((ROOT / manifest).read_text())["devDependencies"]["@biomejs/biome"]
            for manifest in MANIFESTS
        }
        self.assertEqual(1, len(pins), pins)
        self.assertEqual(biome_version(), pins.pop())
