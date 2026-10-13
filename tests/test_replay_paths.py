"""The project root a replay is handed, when it is not the path the files are really at.

`migrate` replays inside a staging directory it makes under the system temporary directory, and on macOS
that is reached through a symlink — `/var` is `/private/var`. The style checker resolves every path it
returns, so a resolved token file was not inside the unresolved root, and a crossing of any project with a
browser app and a design system of its own ended in a `ValueError` out of `relative_to`, in front of
somebody halfway through migrating their repository.

`tests/test_replay.py` could not catch it twice over: the CLI resolves the root it is given, and every test
there needs a language package that this checkout does not pin, so the whole suite skips. This one builds
the few files the function reads and calls it, which needs no package and no generation.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.errors import GenerationError
from slipwai.layout import AT_ROOT
from slipwai.replay import preserve_project_styles
from slipwai.services import App

MAIN = "import './styles/tokens.css';\nimport './theme.css';\ncreateRoot();\n"


def web(path: str = "apps/web") -> App:
    return App(name="web", path=path, kind="browser", language="typescript", framework=None, port=5173)


class SymlinkedRootTest(unittest.TestCase):
    def setUp(self) -> None:
        self.real = Path(tempfile.mkdtemp()) / "project"
        source = self.real / "apps/web/src"
        source.mkdir(parents=True)
        (source / "main.tsx").write_text(MAIN, encoding="utf-8")
        (source / "theme.css").write_text(":root {\n  --border: #ddd;\n}\n", encoding="utf-8")
        self.through = self.real.parent / "through-a-link"
        self.through.symlink_to(self.real, target_is_directory=True)

    def files(self) -> dict[str, str]:
        return {"apps/web/src/main.tsx": MAIN, "docs/design.md": "# Design\n"}

    def test_a_root_reached_through_a_symlink_is_still_the_project(self) -> None:
        """The crossing passes its staging directory as it made it, not as the disk spells it."""
        files = self.files()
        preserve_project_styles(self.through, "HEAD", [web()], files, AT_ROOT)
        self.assertIn("apps/web/src/theme.css", files["docs/design.md"])

    def test_the_real_path_reaches_the_same_answer(self) -> None:
        """Both spellings or neither: a fix that only worked through the link would be the same bug the
        other way round."""
        files = self.files()
        preserve_project_styles(self.real, "HEAD", [web()], files, AT_ROOT)
        self.assertIn("apps/web/src/theme.css", files["docs/design.md"])

    def test_the_project_s_own_tokens_are_named_by_their_path_in_the_project(self) -> None:
        """Not by the path the disk resolves them to: `/private/var/...` in a page about somebody's
        repository is this bug surviving as a cosmetic one."""
        files = self.files()
        preserve_project_styles(self.through, "HEAD", [web()], files, AT_ROOT)
        self.assertIn("apps/web/src/theme.css", files["docs/design.md"])
        self.assertNotIn("/private", files["docs/design.md"])
        self.assertNotIn(str(self.real), files["docs/design.md"])

    def test_the_refusal_names_the_file_the_way_the_repository_spells_it(self) -> None:
        """The other side of the same comparison. A project that changed a starter stylesheet *and* brought
        its own tokens is refused — and that refusal is read by a person looking for the file in their own
        repository, so it has to be their path and not the one the temporary directory resolves to."""
        starter = self.real / "apps/web/src/styles"
        starter.mkdir()
        # No git repository here, so `git diff --quiet` cannot say it is unchanged — which is the state the
        # refusal is for: a starter file this replay may not delete.
        (starter / "tokens.css").write_text(":root {\n  --space: 4px;\n}\n", encoding="utf-8")
        with self.assertRaises(GenerationError) as refused:
            preserve_project_styles(self.through, "HEAD", [web()], self.files(), AT_ROOT)
        self.assertIn("apps/web/src/theme.css", str(refused.exception))
        self.assertNotIn("/private", str(refused.exception))


if __name__ == "__main__":
    unittest.main()
