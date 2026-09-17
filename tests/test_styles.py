"""The browser bundle has one owner for each global custom property.

The defect this gates was valid CSS in two files: both declared ``--border`` at ``:root``, one as a colour
and one as a shorthand. Bundle order silently selected the shorthand for declarations expecting a colour,
and no formatter, linter or test objected. The generated gate follows imports because an unimported design
experiment is not part of the cascade, while a dark-mode override in the owning file is still one owner.
"""
from __future__ import annotations

import subprocess
import tempfile

from support import FactoryTestCase


class StyleGateTest(FactoryTestCase):
    def check(self, repo) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", "scripts/check-styles.py"],
            cwd=repo,
            text=True,
            capture_output=True,
        )

    def test_the_generated_light_and_dark_tokens_have_one_owner(self) -> None:
        """The same file intentionally defines colour tokens once for each colour scheme."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "one-owner", "standard", "go", "react-vite")

            result = self.check(repo)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("no :root custom property has two imported owners", result.stdout)
            makefile = (repo / "Makefile").read_text()
            self.assertIn("check-styles: ## Fail when imported stylesheets compete", makefile)
            self.assertRegex(makefile, r"verify: [^\n]*\bcheck-styles\b")
            self.assertIn("one imported file owns each global property", (repo / "docs/gates.md").read_text())

    def test_a_project_with_no_browser_bundle_has_no_style_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "headless", "standard", "go")

            makefile = (repo / "Makefile").read_text()
            self.assertNotIn("check-styles:", makefile)
            self.assertNotRegex(makefile, r"verify: [^\n]*\bcheck-styles\b")

    def test_two_imported_token_files_fail_with_the_property_and_both_paths(self) -> None:
        """Neither file is wrong alone; the actionable finding is the token and its two owners."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "two-owners", "standard", "go", "react-vite")
            theme = repo / "apps/web/src/theme.css"
            theme.write_text(":root { --border: #d8d2c4; --radius: 4px; }\n")
            entry = repo / "apps/web/src/main.tsx"
            entry.write_text("import './theme.css';\n" + entry.read_text())

            result = self.check(repo)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("--border", result.stderr)
            self.assertIn("--radius", result.stderr)
            self.assertIn("apps/web/src/theme.css", result.stderr)
            self.assertIn("apps/web/src/styles/tokens.css", result.stderr)

    def test_only_stylesheets_reachable_from_the_bundle_are_compared(self) -> None:
        """A design experiment on disk has no cascade until code imports it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "not-bundled", "standard", "go", "react-vite")
            (repo / "apps/web/src/unused-theme.css").write_text(":root { --border: hotpink; }\n")

            result = self.check(repo)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_css_imports_are_followed_transitively(self) -> None:
        """A token file imported by another stylesheet is in the same bundle as a TypeScript import."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "transitive", "standard", "go", "react-vite")
            (repo / "apps/web/src/theme.css").write_text(":root { --border: #ddd; }\n")
            (repo / "apps/web/src/product.css").write_text('@import "./theme.css";\nmain { display: block; }\n')
            entry = repo / "apps/web/src/main.tsx"
            entry.write_text("import './product.css';\n" + entry.read_text())

            result = self.check(repo)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("apps/web/src/theme.css", result.stderr)
