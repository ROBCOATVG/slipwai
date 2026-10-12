"""Package CI's declared source topology is the same before every consumer, without weakening loading."""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml  # type: ignore[import-untyped]

from slipwai.package_sources import declaration, expose

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40


class PackageSourcesTest(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        checkout = patch("slipwai.package_sources.source_commit", return_value=SHA)
        self.commit = checkout.start()
        self.addCleanup(checkout.stop)
        self.root = Path(scratch.name).resolve()
        self.source = self.root / "source"
        self.destination = self.root / "checkouts"
        self.source.mkdir()
        self.destination.mkdir()
        (self.destination / "tested").mkdir()

    def package(self, name: str) -> Path:
        path = self.source / "packages" / name
        path.mkdir(parents=True)
        (path / "target.json").write_text(json.dumps({"name": name}), encoding="utf-8")
        (path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        return path

    def test_pinned_declaration_refuses_paths_duplicates_checkout_and_shell_values(self) -> None:
        self.assertEqual(declaration("publisher/source", SHA, "one two", "tested"), ["one", "two"])
        for repository, ref, packages in [
            ("publisher/source;echo", SHA, "one"), ("../source", SHA, "one"),
            ("publisher/source", "main", "one"), ("publisher/source", SHA, "../one"),
            ("publisher/source", SHA, "one one"), ("publisher/source", SHA, "tested"),
        ]:
            with self.subTest(repository=repository, ref=ref, packages=packages), self.assertRaises(ValueError):
                declaration(repository, ref, packages, "tested")

    def test_exposes_only_named_contained_sources_and_reports_real_provenance(self) -> None:
        one = self.package("one")
        self.package("unused")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            paths = expose(self.source, self.destination, ["one"], "publisher/source", SHA)
        self.assertEqual(paths, [self.destination / "one"])
        self.assertEqual(paths[0].resolve(), one.resolve())
        self.assertFalse((self.destination / "unused").exists())
        self.assertIn(f"publisher/source@{SHA}:packages/one", output.getvalue())
        self.assertTrue((self.destination / "tested").is_dir())

    def test_refuses_a_checkout_whose_actual_commit_differs_from_the_pin(self) -> None:
        self.package("one")
        self.commit.return_value = "b" * 40
        with self.assertRaisesRegex(ValueError, "differs"):
            expose(self.source, self.destination, ["one"], "publisher/source", SHA)
        self.assertFalse((self.destination / "one").exists())

    def test_preflights_all_packages_before_any_write(self) -> None:
        self.package("one")
        self.package("two")
        (self.destination / "two").write_text("person-owned", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "already exists"):
            expose(self.source, self.destination, ["one", "two"], "publisher/source", SHA)
        self.assertFalse((self.destination / "one").exists())
        self.assertEqual((self.destination / "two").read_text(encoding="utf-8"), "person-owned")

    def test_refuses_source_symlink_escape_or_a_different_manifest_name(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (self.source / "packages").mkdir()
        (self.source / "packages/escape").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "escapes"):
            expose(self.source, self.destination, ["escape"], "publisher/source", SHA)
        one = self.package("one")
        (one / "target.json").write_text('{"name":"other"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "declared name"):
            expose(self.source, self.destination, ["one"], "publisher/source", SHA)

    def test_refuses_manifest_and_version_symlinks_outside_the_source_checkout(self) -> None:
        one = self.package("one")
        for filename, text in [("target.json", '{"name":"one"}'), ("VERSION", "1.0.0")]:
            outside = self.root / filename
            outside.write_text(text, encoding="utf-8")
            declaration = one / filename
            declaration.unlink()
            declaration.symlink_to(outside)
            with self.subTest(filename=filename), self.assertRaisesRegex(ValueError, "declaration.*escapes"):
                expose(self.source, self.destination, ["one"], "publisher/source", SHA)
            declaration.unlink()
            declaration.write_text(text, encoding="utf-8")

    def test_workflow_sets_the_same_topology_before_conformance_matrix_and_publication(self) -> None:
        workflow = yaml.safe_load((ROOT / ".github/workflows/package.yml").read_text(encoding="utf-8"))
        for job in ("conformance", "publish"):
            steps = workflow["jobs"][job]["steps"]
            setup = [step for step in steps if step.get("name") == "Expose declared source siblings"]
            self.assertEqual(len(setup), 1)
            self.assertEqual(setup[0]["run"], "python -m slipwai.package_sources")
            consumer = "Conformance" if job == "conformance" else "Build the release"
            position = next(i for i, step in enumerate(steps) if step.get("name") == consumer)
            self.assertLess(steps.index(setup[0]), position)
            self.assertNotIn("${{", setup[0]["run"])
        self.assertEqual(workflow["jobs"]["publish"]["needs"], "conformance")
        condition = "startsWith(github.ref, 'refs/tags/v') && inputs.channel != ''"
        self.assertEqual(workflow["jobs"]["publish"]["if"], condition)
