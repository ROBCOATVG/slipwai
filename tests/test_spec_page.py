"""The drafted document, rendered for the person who is being asked to say it is good.

Continue the build is that word, and the button beside it served `text/plain`. What is held here is the
renderer — which is the keel's own, because the keel carries no markdown library — and the route that uses
it, including the two things a route that reads a path has to refuse.
"""
from __future__ import annotations

import unittest
import urllib.error

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai.spec_page import inline, page, rendered, titled


class InlineTest(unittest.TestCase):
    def test_code_spans_are_not_read_as_markup_and_markup_is_not_read_inside_them(self) -> None:
        """The one ordering rule in the renderer: every renderer that applies bold first gets this wrong."""
        self.assertEqual(inline("use `**not bold**` but **this is**"),
                         "use <code>**not bold**</code> but <b>this is</b>")

    def test_bold_italic_and_links(self) -> None:
        self.assertEqual(inline("**loud** and *quiet*"), "<b>loud</b> and <i>quiet</i>")
        self.assertIn('<a href="docs/prd.md"', inline("[the PRD](docs/prd.md)"))

    def test_a_lone_asterisk_in_a_word_is_not_an_italic(self) -> None:
        self.assertEqual(inline("2 * 3 and a*b"), "2 * 3 and a*b")


class RenderTest(unittest.TestCase):
    """Spec Kit's shape, which is what `/draft` and `/mockups` write."""

    def test_headings_carry_their_level_and_a_paragraph_is_its_wrapped_lines(self) -> None:
        """A drafted specification is hard-wrapped at ninety-odd columns, so most paragraphs are several
        source lines and one paragraph here."""
        found = rendered("# Title\n\n## Section\n\nA sentence that runs\nover two lines.\n")
        self.assertIn("<h1>Title</h1>", found)
        self.assertIn("<h2>Section</h2>", found)
        self.assertIn("<p>A sentence that runs over two lines.</p>", found)

    def test_a_wrapped_list_item_is_one_item(self) -> None:
        found = rendered("1. **Given** x, **When** y and\n   then more, **Then** z.\n2. second\n")
        self.assertEqual(found, "<ol><li><b>Given</b> x, <b>When</b> y and then more, <b>Then</b> z.</li>"
                                "<li>second</li></ol>")

    def test_a_point_under_a_numbered_step_is_under_it_and_not_beside_it(self) -> None:
        """Flattened, a sub-point reads as a peer, which changes what the document says. The mixed case is
        the shape every acceptance scenario is written in, and it was being run into the sentence above."""
        self.assertEqual(rendered("1. first\n   - a point\n   - another\n2. second\n"),
                         "<ol><li>first<ul><li>a point</li><li>another</li></ul></li><li>second</li></ol>")
        self.assertEqual(rendered("- one\n  - inner\n- two\n"),
                         "<ul><li>one<ul><li>inner</li></ul></li><li>two</li></ul>")

    def test_two_kinds_of_marker_at_one_indent_are_two_lists(self) -> None:
        self.assertEqual(rendered("- a bullet\n1. a number\n"),
                         "<ul><li>a bullet</li></ul><ol><li>a number</li></ol>")

    def test_a_table_cell_may_hold_an_escaped_pipe(self) -> None:
        """Which is how every settings table in this project spells a choice between two values, so a
        renderer that split on it would break the one kind of table the keel writes most."""
        found = rendered("| Setting | Values |\n|---|---|\n| `enabled` | `true` \\| `false` |\n")
        self.assertIn("<th>Setting</th>", found)
        self.assertIn("<td><code>true</code> | <code>false</code></td>", found)
        self.assertEqual(found.count("<td>"), 2, "two cells, not three")

    def test_a_fenced_block_is_shown_and_never_run(self) -> None:
        found = rendered("```python\nx = '<script>alert(1)</script>'\n```\n")
        self.assertIn("<pre><code>", found)
        self.assertNotIn("<script>", found)

    def test_markup_in_the_document_cannot_become_markup_in_the_page(self) -> None:
        """The document is a file an agent wrote. Everything it says is text."""
        self.assertNotIn("<img", rendered('A line with <img src=x onerror="alert(1)"> in it.\n'))
        self.assertNotIn("<b>bold</b>", rendered("A literal <b>bold</b> tag.\n"))

    def test_rules_and_quotes(self) -> None:
        self.assertIn("<hr>", rendered("---\n"))
        self.assertIn("<blockquote>A line continued.</blockquote>", rendered("> A line\n> continued.\n"))

    def test_the_document_is_titled_by_its_own_first_heading(self) -> None:
        self.assertEqual(titled("# Feature Specification: Ordering\n\n# Later\n", "fallback"),
                         "Feature Specification: Ordering")
        self.assertEqual(titled("## Only a section\n", "001-ordering"), "001-ordering")
        self.assertIn("<title>Feature Specification: Ordering</title>",
                      page("specs/001-ordering/spec.md", "# Feature Specification: Ordering\n"))


class SpecRouteTest(BoardTest):
    """The route, and the two things a route that reads a path has to refuse."""

    def written(self, text: str = "# Ordering\n\nA **specification**.\n") -> None:
        (self.root / "specs/001-ordering").mkdir(parents=True)
        (self.root / "specs/001-ordering/spec.md").write_text(text, encoding="utf-8")

    def test_the_specification_is_served_as_a_page_and_not_as_its_markup(self) -> None:
        self.written()
        code, said = self.get("/spec/001-ordering")
        self.assertEqual(code, 200)
        self.assertIn("<h1>Ordering</h1>", said)
        self.assertIn("<b>specification</b>", said)
        self.assertNotIn("# Ordering", said, "the markup is rendered, not shown")

    def test_the_voyage_links_to_it_and_the_page_links_back(self) -> None:
        self.written()
        self.assertIn("/spec/001-ordering", self.get("/voyage")[1])
        self.assertIn('href="/voyage"', self.get("/spec/001-ordering")[1])

    def refused(self, where: str) -> str:
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.get(where)
        with caught.exception as answer:
            self.assertEqual(answer.code, 404, where)
            return answer.read().decode("utf-8")

    def test_a_feature_with_no_specification_is_a_404_rather_than_an_empty_page(self) -> None:
        self.assertIn("No specification", self.refused("/spec/nothing-here"))

    def test_the_route_reads_nothing_outside_the_project_s_own_specs(self) -> None:
        """`..` in a feature name is the whole of what this guard is for."""
        (self.root / "secret.md").write_text("# Not yours\n", encoding="utf-8")
        for where in ("/spec/../..", "/spec/..%2f..%2fsecret.md", "/spec/", "/spec/a/b"):
            with self.subTest(where=where):
                self.assertNotIn("Not yours", self.refused(where))


if __name__ == "__main__":
    unittest.main()
