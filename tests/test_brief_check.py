"""`slipwai brief check` says what the front door will read, in the words the reference page uses.

What it prints is read by the readers the stages read with, so a page it counts is a page the board can
approve; the worked example under `tests/fixtures/brief/` is the folder the page describes, line for line.
"""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.brief_check import assumptions, facts, people, report
from slipwai.cli_brief import brief_main
from slipwai.design_docs import FILES
from slipwai.errors import GenerationError

BRIEF = Path(__file__).resolve().parent / "fixtures" / "brief"


def tree(**files: str) -> Path:
    """A directory with those files in it; `__` in a name is a directory separator."""
    root = Path(tempfile.mkdtemp())
    for relative, content in files.items():
        path = root / relative.replace("__", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


class ReportTest(unittest.TestCase):
    def test_the_worked_example_reads_as_the_reference_page_says(self) -> None:
        self.assertEqual(report(BRIEF), [
            "requirements document: prd.md, by name",
            "surfaces: 3, states: 16, each with a heading, 10 decided by a person, 6 proposed",
            "look: look/look.css",
            "people: 2   facts: 2, cited",
            "the draft will have to assume: 1 — Can a member hold two bookings on the same day? (prd.md, ## Open)",
        ])

    def test_no_document_is_an_answer_and_no_surfaces_say_where_they_go(self) -> None:
        said = report(tree(**{"brand.md": "# Brand\n"}))
        self.assertEqual(said[0], "requirements document: none; the specification is written in the agent")
        self.assertEqual(said[1], "surfaces: none; one page per surface goes under surfaces/")
        self.assertIn("look: none", said[2])
        self.assertEqual(said[3], "people: none   facts: none")
        self.assertEqual(said[4], "the draft will have to assume: nothing the document says it left open")

    def test_a_page_with_no_state_article_is_one_state_shown_and_the_line_says_so(self) -> None:
        said = report(tree(**{"game-prd.md": "# P\n", "surfaces__home.html": "<title>Home</title><p>hi</p>",
                              "surfaces__list.html": "<title>List</title><article class=\"state\"><h2>Empty</h2>"
                                                     "</article><article class=\"state\"><h2>Full</h2></article>"}))
        self.assertEqual(said[0], "requirements document: game-prd.md, by a name that says what it is")
        self.assertEqual(said[1], "surfaces: 2, states: 3; surfaces/home.html has no <article class=\"state\"> "
                                  "and is one state each, shown")

    def test_a_fact_with_no_source_is_named(self) -> None:
        home = tree(**{"prd.md": "# P\n", "domain.md": "## One\n\nSource: the rules.\n\n## Two\n\nTrust me.\n"})
        self.assertEqual(report(home)[3], "people: none   facts: 2, 1 with no source (Two)")

    def test_more_than_one_assumption_is_a_count_and_then_a_line_each(self) -> None:
        home = tree(**{"prd.md": "# P\n\n## Open\n\n- One?\n- Two?\n"})
        self.assertEqual(report(home)[4:], ["the draft will have to assume: 2",
                                            "  — One? (prd.md, ## Open)", "  — Two? (prd.md, ## Open)"])

    def test_not_a_directory_and_too_many_files_are_refusals_that_end_with_the_fix(self) -> None:
        with self.assertRaises(GenerationError) as caught:
            report(Path(tempfile.mkdtemp()) / "nowhere")
        self.assertIn("brief check <dir>", str(caught.exception))
        home = tree(**{f"page-{index}.md": "x" for index in range(FILES + 1)})
        with self.assertRaises(GenerationError) as caught:
            report(home)
        self.assertIn(f"holds {FILES + 1} files", str(caught.exception))
        self.assertIn("point it at", str(caught.exception))


class ReadersTest(unittest.TestCase):
    def test_people_are_headings_with_the_role_their_section_says(self) -> None:
        self.assertEqual(people(BRIEF / "people.md"),
                         [{"name": "Sam", "role": "member"}, {"name": "Jo", "role": "bosun"}])
        self.assertEqual(people(tree(**{"p.md": "## Kim\n\nDoes things.\n"}) / "p.md"),
                         [{"name": "Kim", "role": ""}])

    def test_facts_are_headings_and_whether_each_says_where_it_came_from(self) -> None:
        self.assertEqual([fact["cited"] for fact in facts(BRIEF / "domain.md")], [True, True])

    def test_the_four_shapes_of_an_open_question_and_a_question_heading_counted_once(self) -> None:
        prd = tree(**{"prd.md": "# P\n\n## Must\n\n- Works\n- Is it blue?\n- Colour TBD\n- open: size\n\n"
                                "## Who pays?\n\n- Members?\n- The club?\n\n## Open\n\n- Anything else\n"}) / "prd.md"
        self.assertEqual(assumptions(prd), [
            "Is it blue? (prd.md, ## Must)", "Colour TBD (prd.md, ## Must)", "open: size (prd.md, ## Must)",
            "Who pays? (prd.md, ## Who pays?)", "Anything else (prd.md, ## Open)"])


class VerbTest(unittest.TestCase):
    def test_check_prints_the_report(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            brief_main(["check", str(BRIEF)])
        self.assertEqual(out.getvalue().splitlines()[0], "requirements document: prd.md, by name")

    def test_check_with_no_folder_and_a_refusal_are_one_line_each(self) -> None:
        err = io.StringIO()
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stderr(err):
            brief_main(["check"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("brief check <dir>", err.getvalue())
        err = io.StringIO()
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(err):
            brief_main(["check", str(BRIEF / "nowhere")])
        self.assertIn("is not a directory", err.getvalue())
        self.assertNotIn("usage:", err.getvalue())


class DraftPageTest(unittest.TestCase):
    """The draft reads the people file the brief hands over, in the shape the reference page states."""

    def test_the_draft_declares_the_briefs_people_where_a_story_can_sign_in_as_them(self) -> None:
        import command_pages
        for face in ("standard", "adopted"):
            with self.subTest(face=face):
                draft = command_pages.pages(face)["commands/draft.md"]
                self.assertIn("**Declare the people the brief names.**", draft)
                for said in ("`docs/design/people.md`", "`specs/<feature>/people/<username>.json`",
                             "`docker/keycloak/realms/`", "`## People`", "no `email`",
                             "every person declared and the file each was written to"):
                    self.assertIn(said, draft)
