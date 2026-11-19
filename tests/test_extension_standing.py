"""An extension, installed against published and copied against installed: the two things nothing used to say.

`slipwai upgrade --check` listed the keel and each language and no extension, so a machine held `ux-gates`
1.0.0 while 1.0.1 had fixed the path a project's CI called; and a project's own copy under
`scripts/extensions/<key>/` could differ from the installed package with no page naming it. No network and no
git: an index written here, a package directory in a temporary folder.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import catch_up
from slipwai.extension_copies import copies
from slipwai.extension_upkeep import standing, with_extensions
from slipwai.index_schema import Index, Release
from slipwai.language_index import Unreachable
from slipwai.upgrade import LanguagesNotUpgraded


def package(packages: Path, key: str, version: str, **files: str) -> Path:
    root = packages / key
    (root / "hooks").mkdir(parents=True)
    manifest = {"key": key, "name": key.title(), "description": "A test extension", "kind": "extension",
                "core": ">=9.0,<10", "hooks": {"init": "init.py"}}
    (root / "extension.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name, body in {"VERSION": f"{version}\n", "init.py": "GUIDANCE = 'one'\n", **files}.items():
        (root / name.replace("__", "/")).write_text(body, encoding="utf-8")
    return root


def published(key: str, *versions: str, kind: str = "extension") -> list[Release]:
    fragment = {"key": key, "name": key.title(), "core": ">=9.0,<10"}
    return [Release(key, version, f"https://example.invalid/{key}-{version}.tar.gz", "0" * 64, fragment, kind=kind)
            for version in versions]


class PublishedTest(unittest.TestCase):
    """`slipwai upgrade`'s extension step."""

    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(scratch.cleanup)
        self.packages = Path(scratch.name)
        package(self.packages, "ux-gates", "1.0.0")
        package(self.packages, "codegraph", "1.0.0")
        self.index = Index("https://example.invalid/index.json", "the test channel",
                           {"ux-gates": published("ux-gates", "1.0.0", "1.0.1", "1.1.0.dev2"),
                            "codegraph": published("codegraph", "1.0.0")})

    def said(self, prerelease: bool = False) -> list[str]:
        return standing(prerelease, self.packages, lambda: self.index)

    def test_an_extension_behind_what_is_published_is_shown_in_the_words_a_language_is(self) -> None:
        """The command that moves it is `upgrade`'s to say or to run (`test_extension_upgrade`), as for a language."""
        said = self.said()
        self.assertEqual(said[:3], ["extensions:", "  codegraph 1.0.0 (newest compatible)",
                                    "  ux-gates 1.0.0 → 1.0.1 available"])
        self.assertEqual(len(said), 4)
        self.assertIn("migrate", said[-1], "and what a project does to take it")

    def test_a_snapshot_counts_only_for_somebody_following_them(self) -> None:
        self.assertIn("→ 1.1.0.dev2 available", "\n".join(self.said(prerelease=True)))

    def test_one_the_index_does_not_list_and_a_language_of_the_same_name_are_not_a_newer_extension(self) -> None:
        package(self.packages, "local-only", "0.1.0")
        self.index.releases["local-only"] = published("local-only", "9.0.0", kind="language")
        line = next(line for line in self.said() if "local-only" in line)
        self.assertIn("lists no release of it", line)
        self.assertNotIn("→", line)

    def test_an_index_that_cannot_be_reached_still_lists_what_is_installed(self) -> None:
        def unreachable() -> Index:
            raise Unreachable("https://example.invalid/index.json", "could not be read")
        said = standing(False, self.packages, unreachable)
        self.assertEqual(said[:3], ["extensions:", "  codegraph 1.0.0", "  ux-gates 1.0.0"])
        self.assertIn("could not be read", said[-2])
        self.assertTrue(said[-1].endswith("extension install <path-or-url>"), "and the way round the index")
        self.assertEqual(len(said), 5)

    def test_nothing_installed_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(standing(False, Path(empty), lambda: self.index),
                             ["extensions: no extension is installed"])

    def test_the_extensions_follow_the_languages_whatever_the_languages_did(self) -> None:
        step = with_extensions(lambda check, pre, moved: ["languages:"], lambda check, pre, moved: ["extensions:"])
        self.assertEqual(step(True, False, False), ["languages:", "extensions:"])

        def failed(check: bool, pre: bool, moved: bool) -> list[str]:
            raise LanguagesNotUpgraded(["languages:", "not moved"])
        with self.assertRaises(LanguagesNotUpgraded) as raised:
            with_extensions(failed, lambda check, pre, moved: ["extensions:"])(False, False, True)
        self.assertEqual(raised.exception.lines, ["languages:", "not moved", "extensions:"])


class CopyTest(unittest.TestCase):
    """The catch-up page's section: each elected extension whose copy here is not the installed package."""

    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(scratch.cleanup)
        self.packages = Path(scratch.name) / "packages"
        self.root = Path(scratch.name) / "project"
        installed = package(self.packages, "ux-gates", "1.0.1", hooks__check="print('tools/ux-gates/scripts')\n")
        package(self.packages, "codegraph", "1.0.0")
        # The project's copies, as generation wrote them: everything but the manifest.
        for key, version in (("ux-gates", "1.0.0"), ("codegraph", "1.0.0"), ("unslop", "1.0.0")):
            package(self.root / "scripts/extensions", key, version).joinpath("extension.json").unlink()
        self.elect("codegraph", "ux-gates")
        self.installed = installed

    def elect(self, *keys: str) -> None:
        record = self.root / ".slipwai/extensions.json"
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps({"schemaVersion": 1, "extensions": list(keys)}), encoding="utf-8")

    def section(self) -> list[str]:
        return copies(self.root, {"name": "pir"}, self.packages)

    def test_a_copy_behind_the_installed_package_is_named_with_both_versions_and_its_files(self) -> None:
        section = self.section()
        self.assertEqual(section[1], "## Extensions whose copy here is not the installed package")
        rows = [line for line in section if line.startswith("- ")]
        self.assertEqual(len(rows), 1, "codegraph's copy is the installed package and is not named")
        self.assertIn("`ux-gates` — this project's copy says 1.0.0, the installed package is 1.0.1", rows[0])
        self.assertIn("2 file(s) differ: `VERSION`, `hooks/check`", rows[0])
        self.assertIn(f"diff -r scripts/extensions/ux-gates {self.installed}", rows[0])
        self.assertIn("upgrade --check", "\n".join(section))

    def test_every_copy_the_installed_package_and_nothing_elected_are_both_no_section(self) -> None:
        self.elect("codegraph")
        self.assertEqual(self.section(), [])
        (self.root / ".slipwai/extensions.json").unlink()
        self.assertEqual(self.section(), [], "no record: nothing this can say is elected")

    def test_a_file_only_the_project_has_and_a_line_ending_are_not_differences(self) -> None:
        self.elect("codegraph")
        copy = self.root / "scripts/extensions/codegraph"
        (copy / "local-notes.md").write_text("ours\n", encoding="utf-8")
        (copy / "init.py").write_bytes(b"GUIDANCE = 'one'\r\n")
        self.assertEqual(self.section(), [])

    def test_an_elected_extension_not_installed_here_is_said_with_the_command(self) -> None:
        self.elect("unslop")
        rows = [line for line in self.section() if line.startswith("- ")]
        self.assertEqual(len(rows), 1)
        self.assertIn("`unslop` is elected here and not installed on this machine", rows[0])
        self.assertTrue(rows[0].endswith("extension install unslop`."), rows[0])

    def test_the_page_carries_the_section_before_its_last_step(self) -> None:
        page = catch_up.notes("pir", "2.1.0.dev60", extensions=self.section())
        self.assertIn("## Extensions whose copy here is not the installed package", page)
        self.assertLess(page.index("## Extensions whose copy"), page.index("\n## Then\n"))
        self.assertNotIn("## Extensions whose copy", catch_up.notes("pir", "2.1.0.dev60"))


if __name__ == "__main__":
    unittest.main()
