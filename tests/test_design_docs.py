"""What a product requirements document stands on, carried into the project with it.

`--prd` copied one document's text and nothing else, so a PRD that embedded its wireframes and cited a
brand sheet landed as a *Look and feel* section pointing at nothing. Two things travel now — what the
document names, and `--design <dir>` — and what is held here is which of them travel, where they land, and
the one that must not: a document is a file somebody was handed, and a generate that copied whatever it
pointed at would read anything its author could name.
"""
from __future__ import annotations

import base64
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages
from support import FactoryTestCase

from slipwai.design_docs import DESIGN, FILES, briefed, handed_over, inside, referenced, unpacked
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

    def test_one_folder_is_sorted_into_the_document_and_the_material_it_stands_on(self) -> None:
        """What a person actually does: hand over the folder the brief lives in and let it be sorted."""
        brief = tree(**{"game-prd.md": "# P\n\n![home](wireframes/home.png)\n",
                        "wireframes__home.png": PNG, "brand.md": "# Brand\n"})
        with tempfile.TemporaryDirectory() as area:
            made = self.generate(area, "briefed", profile="standard", language="toy-plain",
                                 brief=str(brief))
            self.assertIn("# P", (made / "docs/prd.md").read_text(encoding="utf-8"),
                          "the one that read as the requirements document")
            self.assertIn("![home](design/wireframes/home.png)",
                          (made / "docs/prd.md").read_text(encoding="utf-8"))
            self.assertEqual((made / "docs/design/wireframes/home.png").read_bytes(), PNG)
            self.assertTrue((made / "docs/design/brand.md").is_file(), "and everything else")
            self.assertFalse((made / "docs/design/game-prd.md").exists(),
                             "the document is not also design material")


class BriefTest(unittest.TestCase):
    """One folder with everything in it, sorted here rather than by the person handing it over."""

    def sorted_out(self, **files: object) -> tuple[str | None, list[str]]:
        home = tree(**files)
        found, rest = briefed(home)
        return (found.name if found else None,
                sorted(one.relative_to(home).as_posix() for one in rest))

    def test_the_document_is_found_by_its_name_first(self) -> None:
        self.assertEqual(self.sorted_out(**{"prd.md": "x", "brand.md": "y", "shots__home.png": PNG}),
                         ("prd.md", ["brand.md", "shots/home.png"]))

    def test_then_by_a_name_that_says_what_it_is(self) -> None:
        self.assertEqual(self.sorted_out(**{"game-prd.md": "x", "a.css": "y"})[0], "game-prd.md")
        self.assertEqual(self.sorted_out(**{"requirements-v2.md": "x"})[0], "requirements-v2.md")

    def test_then_by_what_the_document_calls_itself(self) -> None:
        """The most reliable of the three and the last asked: a file somebody called `v2-final.md` still
        opens with *# Product Requirements*."""
        self.assertEqual(self.sorted_out(**{"v2-final.md": "# Product Requirements\n\nSell more.\n",
                                            "brand.md": "# Brand\n"})[0], "v2-final.md")

    def test_a_folder_with_no_document_in_it_is_an_answer_rather_than_a_failure(self) -> None:
        """Wireframes and a brand sheet is design material. The specification gets written in the agent,
        the way it always could be."""
        self.assertEqual(self.sorted_out(**{"brand.md": "# Brand\n", "home.png": PNG}),
                         (None, ["brand.md", "home.png"]))

    def test_a_document_nested_in_the_brief_may_point_outside_its_own_folder(self) -> None:
        """Resolved against the whole brief and not the document's directory: a PRD in `docs/` quite
        reasonably points at `../wireframes/`, and the containment is the brief's edge."""
        home = tree(**{"docs__prd.md": "![home](../wireframes/home.png)\n", "wireframes__home.png": PNG})
        carried, text = referenced(home / "docs/prd.md", (home / "docs/prd.md").read_text(), home)
        self.assertEqual(sorted(carried), [f"{DESIGN}/wireframes/home.png"])
        self.assertIn("![home](design/wireframes/home.png)", text)

    def test_the_brief_s_own_edge_still_holds(self) -> None:
        home = tree(**{"brief__docs__prd.md": "[keys](../../../secret.md)\n", "secret.md": "# Not yours\n"})
        carried, _ = referenced(home / "brief/docs/prd.md",
                                (home / "brief/docs/prd.md").read_text(), home / "brief")
        self.assertEqual(carried, {})


class PayloadTest(unittest.TestCase):
    """What the board sends: a browser hands a page a file's contents and never its path, so a brief
    arrives as names and bytes and is written back to a folder for the length of the run."""

    def test_the_files_are_written_back_with_the_shape_they_had(self) -> None:
        into = Path(tempfile.mkdtemp()) / "brief"
        payload = json.dumps([{"path": "prd.md", "data": base64.b64encode(b"# P\n").decode()},
                              {"path": "shots/home.png", "data": base64.b64encode(PNG).decode()}])
        self.assertEqual(unpacked(payload, into), into)
        self.assertEqual((into / "prd.md").read_bytes(), b"# P\n")
        self.assertEqual((into / "shots/home.png").read_bytes(), PNG, "bytes, not text through an encoder")

    def test_nothing_picked_is_nothing_written(self) -> None:
        into = Path(tempfile.mkdtemp()) / "brief"
        for payload in ("", "[]"):
            self.assertIsNone(unpacked(payload, into))
        self.assertFalse(into.exists())

    def test_a_name_that_reaches_out_of_the_folder_is_refused(self) -> None:
        """This reads a JSON payload rather than a directory somebody typed, so every guard is applied
        again and for a stronger reason."""
        into = Path(tempfile.mkdtemp()) / "brief"
        for named in ("../escaped.md", "/etc/passwd", ".git/config", ""):
            with self.subTest(path=named), self.assertRaises(GenerationError):
                unpacked(json.dumps([{"path": named, "data": "eA=="}]), into)
        self.assertFalse((into.parent / "escaped.md").exists())

    def test_bytes_that_did_not_arrive_intact_are_refused(self) -> None:
        into = Path(tempfile.mkdtemp()) / "brief"
        with self.assertRaises(GenerationError) as caught:
            unpacked(json.dumps([{"path": "a.md", "data": "not base64!!"}]), into)
        self.assertIn("did not arrive intact", str(caught.exception))

    def test_more_than_a_handed_over_tree_may_carry_is_refused(self) -> None:
        into = Path(tempfile.mkdtemp()) / "brief"
        many = [{"path": f"f{index}.md", "data": "eA=="} for index in range(FILES + 1)]
        with self.assertRaises(GenerationError) as caught:
            unpacked(json.dumps(many), into)
        self.assertIn(f"over the {FILES}", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
