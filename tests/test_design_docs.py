"""What a product requirements document stands on, carried into the project with it.

`--prd` copied one document's text and nothing else, so a PRD that embedded its wireframes and cited a
brand sheet landed as a *Look and feel* section pointing at nothing. Two things travel now — what the
document names, and `--design <dir>` — and what is held here is which of them travel, where they land, and
the one that must not: a document is a file somebody was handed, and a generate that copied whatever it
pointed at would read anything its author could name.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import checkout_packages
from support import FactoryTestCase

from slipwai.cli_generate import prd_files
from slipwai.design_docs import DESIGN, FILES, handed_over, inside, referenced
from slipwai.errors import GenerationError

#: The first bytes of a real PNG, which is the point: this is not text.
PNG = b"\x89PNG\r\n\x1a\n"


def tree(**files: object) -> Path:
    """A directory with those files in it; `__` in a name is a directory separator."""
    root = Path(tempfile.mkdtemp())
    for relative, content in files.items():
        path = root / relative.replace("__", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else str(content).encode("utf-8"))
    return root


class ReferencedTest(unittest.TestCase):
    def test_what_the_document_names_travels_and_the_links_point_at_where_it_landed(self) -> None:
        """The rewrite is what makes this worth doing: a file carried in under a name the document still
        spells the old way is a file nobody finds, which is the state it was already in."""
        root = tree(**{"prd.md": "# P\n\n![home](wireframes/home.png)\n\nSee [brand](brand.md).\n",
                       "wireframes__home.png": b"\x89PNG\r\n", "brand.md": "# Brand\n"})
        carried, text = referenced(root / "prd.md", (root / "prd.md").read_text())
        self.assertEqual(sorted(carried), [f"{DESIGN}/brand.md", f"{DESIGN}/wireframes/home.png"])
        self.assertIn("![home](design/wireframes/home.png)", text)
        self.assertIn("[brand](design/brand.md)", text)

    def test_what_is_already_somewhere_else_is_left_exactly_as_it_is(self) -> None:
        root = tree(**{"prd.md": "[a](https://example.com/x.md) [b](#later) [c](mailto:a@b.c)\n"})
        carried, text = referenced(root / "prd.md", (root / "prd.md").read_text())
        self.assertEqual(carried, {})
        self.assertEqual(text, (root / "prd.md").read_text())

    def test_a_reference_to_something_that_is_not_there_is_left_alone_rather_than_refused(self) -> None:
        """A PRD with a stale link is still a PRD worth drafting from, and the link is no worse here than
        it was in the directory it came from."""
        root = tree(**{"prd.md": "[gone](nothing.md)\n"})
        carried, text = referenced(root / "prd.md", (root / "prd.md").read_text())
        self.assertEqual(carried, {})
        self.assertIn("[gone](nothing.md)", text)

    def test_nothing_outside_the_document_s_own_directory_travels(self) -> None:
        """The guard this exists for. The PRD is a file somebody was handed; a generate that copied
        whatever it pointed at would read anything its author could name."""
        root = tree(**{"brief__prd.md": "[keys](../../.ssh/id_rsa) [up](../secret.md)\n",
                       "secret.md": "# Not yours\n"})
        carried, text = referenced(root / "brief/prd.md", (root / "brief/prd.md").read_text())
        self.assertEqual(carried, {})
        self.assertIn("[up](../secret.md)", text, "left as it was, and not followed")

    def test_a_symlink_out_of_the_tree_is_not_a_way_around_it(self) -> None:
        root = tree(**{"brief__prd.md": "[out](away.md)\n", "secret.md": "# Not yours\n"})
        (root / "brief/away.md").symlink_to(root / "secret.md")
        self.assertEqual(referenced(root / "brief/prd.md", "[out](away.md)\n")[0], {})
        self.assertIsNone(inside(root / "brief", "away.md"))


class HandedOverTest(unittest.TestCase):
    def test_every_file_in_the_folder_lands_under_docs_design(self) -> None:
        root = tree(**{"brand.md": "# Brand\n", "shots__home.png": b"\x89PNG\r\n"})
        self.assertEqual(sorted(handed_over(str(root))),
                         [f"{DESIGN}/brand.md", f"{DESIGN}/shots/home.png"])

    def test_dotfiles_do_not_travel(self) -> None:
        """A folder somebody points at is often a checkout, and its `.git` is not design material."""
        root = tree(**{"brand.md": "x", ".git__config": "y", ".DS_Store": "z"})
        self.assertEqual(sorted(handed_over(str(root))), [f"{DESIGN}/brand.md"])

    def test_a_folder_that_is_not_one_or_is_empty_says_so(self) -> None:
        for named, why in ((str(tree(**{"a.md": "x"}) / "a.md"), "is not a directory"),
                           (str(tree()), "holds no files")):
            with self.subTest(why=why), self.assertRaises(GenerationError) as caught:
                handed_over(named)
            self.assertIn(why, str(caught.exception))

    def test_a_tree_too_big_to_be_design_material_is_a_refusal_naming_the_size(self) -> None:
        """A home directory or a node_modules pointed at by mistake, said as a refusal rather than as a
        generate that appears to hang."""
        root = tree(**{f"f{index}.md": "x" for index in range(FILES + 1)})
        with self.assertRaises(GenerationError) as caught:
            handed_over(str(root))
        self.assertIn(f"over the {FILES}", str(caught.exception))


@unittest.skipUnless(checkout_packages.installed("toy"),
                     "generates a project, so it needs a language installed; the keel ships none")
class GeneratedTest(FactoryTestCase):
    """Through a real generate, which is where the half that cannot go through `files` is exercised: a
    wireframe is a PNG, and a project's file set is text by the time it reaches the writer."""

    def test_a_prd_s_references_and_a_design_folder_both_land_beside_it_and_are_committed(self) -> None:
        brief = tree(**{"prd.md": "# P\n\n![home](home.png)\n\nSee [brand](sheets/brand.md).\n",
                        "home.png": PNG, "sheets__brand.md": "# Brand\n"})
        folder = tree(**{"tokens.css": ":root{--teal:#0f6b6b}\n"})
        with tempfile.TemporaryDirectory() as area:
            made = self.generate(area, "carried", profile="standard", language="toy-plain",
                                 prd=str(brief / "prd.md"), design=str(folder))
            self.assertEqual((made / "docs/design/home.png").read_bytes(), PNG,
                             "byte for byte: a picture, not text run through an encoder")
            self.assertTrue((made / "docs/design/sheets/brand.md").is_file(), "its own shape is kept")
            self.assertTrue((made / "docs/design/tokens.css").is_file(), "and the folder handed over")
            said = (made / "docs/prd.md").read_text(encoding="utf-8")
            self.assertIn("![home](design/home.png)", said)
            self.assertIn("[brand](design/sheets/brand.md)", said)
            index = (made / "docs/README.md").read_text(encoding="utf-8")
            self.assertIn("Handed over", index)
            self.assertIn("design/tokens.css", index)
            shown = subprocess.run(["git", "show", "--stat", "HEAD"], cwd=made,
                                   capture_output=True, text=True, check=True).stdout
            self.assertIn("docs/design/home.png", shown, "committed, not left untracked beside the project")


class FlagTest(unittest.TestCase):
    def test_a_design_folder_with_no_document_citing_it_is_refused(self) -> None:
        """`--design` is the material a PRD stands on. Without the document there is nothing citing it,
        and a folder dropped into a project nothing points at is a folder nobody reads."""
        args = SimpleNamespace(prd=None, design=tree(**{"brand.md": "x"}), name="x", profile="standard",
                               target="none", shape=None)
        with self.assertRaises(GenerationError) as caught:
            prd_files(args, [])
        self.assertIn("needs --prd with it", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
