"""Canonical guidance is available before a project has installed any language."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import checkout_packages  # noqa: F401

from slipwai.assets import PROFILE_ROOT, TOOLKIT_ROOT, asset_files
from slipwai.errors import GenerationError
from slipwai.examples import EXAMPLE_MARKER, resolve_canonical_examples
from slipwai.toolkit import toolkit_files_from_assets


class CanonicalExamplesTest(unittest.TestCase):
    def test_every_toolkit_and_profile_marker_has_useful_canonical_guidance(self) -> None:
        sources = [*asset_files(TOOLKIT_ROOT), *asset_files(PROFILE_ROOT)]
        markers = {match.group(0) for source in sources
                   for match in EXAMPLE_MARKER.finditer(source.read_text(encoding="utf-8"))}
        self.assertGreater(len(markers), 100)
        with patch("slipwai.examples.registry", side_effect=AssertionError("asked a language package")):
            for marker in sorted(markers):
                with self.subTest(marker=marker):
                    resolved = resolve_canonical_examples(marker)
                    self.assertIn("```", resolved)
                    self.assertNotRegex(resolved, EXAMPLE_MARKER)

    def test_adoption_toolkit_resolves_both_profiles_without_asking_a_package(self) -> None:
        with patch("slipwai.examples.registry", side_effect=AssertionError("asked a language package")):
            for profile in ("standard", "event-modelling"):
                with self.subTest(profile=profile):
                    files = toolkit_files_from_assets(profile, [])
                    self.assertGreater(len(files), 100)
                    self.assertFalse(any(path.startswith("examples/") for path in files))
                    self.assertFalse(any(EXAMPLE_MARKER.search(content) for content in files.values()))
                    self.assertIn("const", files["skills/domain-driven-design/SKILL.md"])

    def test_missing_canonical_guidance_refuses_with_a_repair_command(self) -> None:
        with (
            tempfile.TemporaryDirectory() as scratch,
            self.assertRaisesRegex(GenerationError, "missing canonical.*slipwai upgrade"),
        ):
            resolve_canonical_examples("{{example: testing/absent}}", Path(scratch))

    def test_a_canonical_snippet_cannot_follow_a_symlink_out_of_the_keel(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch) / "keel"
            examples = root / "assets/examples/testing"
            examples.mkdir(parents=True)
            outside = Path(scratch) / "secret.md"
            outside.write_text("not guidance", encoding="utf-8")
            (examples / "secret.md").symlink_to(outside)
            with self.assertRaises(GenerationError):
                resolve_canonical_examples("{{example: testing/secret}}", root)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
