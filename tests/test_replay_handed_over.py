"""What a person handed over at generate time is carried by a replay, so a migration never offers to delete it.

Migrating `recap` to 2.0.0rc2.dev0 staged the deletion of `docs/prd.md`, eight design files under
`docs/design/project/` and `.slipwai/quickstart.json`: the replay wrote only what the factory generates for
the recorded answers, and the base commit held those files beside the factory's, so git read the factory's
side as having deleted them. The replay now carries them from the base as they were there.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import design_docs, replay
from slipwai.layout import Layout
from slipwai.scaffold import FACTORY_EMAIL

PNG = b"\x89PNG\r\n\x1a\n\x00\x00"


def repo_with(files: dict[str, bytes]) -> tuple[Path, str]:
    """A repository whose one commit is the factory's, holding those files; the commit's hash."""
    root = Path(tempfile.mkdtemp())
    for relative, body in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    run = lambda *argv: subprocess.run(["git", *argv], cwd=root, check=True, capture_output=True, text=True)  # noqa: E731
    run("init", "--quiet", "--initial-branch=main")
    run("add", "-A")
    run("-c", f"user.email={FACTORY_EMAIL}", "-c", "user.name=Slipwai", "commit", "--quiet", "-m", "Scaffold")
    return root, run("rev-parse", "HEAD").stdout.strip()


class HandedOverTest(unittest.TestCase):
    def test_the_prd_the_design_material_and_the_quickstart_record_are_read_off_the_base_commit(self) -> None:
        root, base = repo_with({
            "docs/prd.md": b"# Recap\n\nWhat it does.\n",
            "docs/design/project/AddBook.dc.html": b"<!doctype html>\n",
            "docs/design/brand.png": PNG,
            ".slipwai/quickstart.json": b'{"name": "audiobook"}\n',
            "docs/architecture.md": b"# Architecture\n",
            "README.md": b"# Recap\n",
        })
        found = replay.handed_over_at(root, base, Layout())
        self.assertEqual(sorted(found), [".slipwai/quickstart.json", "docs/design/brand.png",
                                         "docs/design/project/AddBook.dc.html", "docs/prd.md"])
        self.assertEqual(found["docs/design/brand.png"], PNG)

    def test_a_project_that_was_handed_nothing_carries_nothing(self) -> None:
        root, base = repo_with({"README.md": b"# Plain\n", "docs/architecture.md": b"# Architecture\n"})
        self.assertEqual(replay.handed_over_at(root, base, Layout()), {})

    def test_the_design_folder_is_the_one_generate_writes_to(self) -> None:
        """Two spellings of one path would be the replay carrying a folder generate never fills."""
        self.assertEqual(replay.HANDED_DESIGN, design_docs.DESIGN)

    def test_the_docs_index_lists_the_prd_and_the_material_as_generate_did(self) -> None:
        files = {"docs/README.md": "", "docs/architecture.md": "# Architecture\n\nThe shape.\n"}
        carried = {"docs/prd.md": b"# Recap\n\nWhat it does.\n", "docs/design/brand.png": PNG}
        replay.index_handed_over(files, carried, Layout())
        self.assertEqual(files["docs/prd.md"], "# Recap\n\nWhat it does.\n")
        self.assertIn("brand.png", files["docs/README.md"])
        self.assertIn("prd", files["docs/README.md"])


if __name__ == "__main__":
    unittest.main()
