"""A card per decision, led by its sentence: the options split with the chosen one marked, grouped, filtered.

The fixtures are real entries from game-club-manager's record, shortened: the bounded-context entry whose
Options field goes on into a table, the one whose Decision makes its option exact, a "variant of (a)", and
the shape this repository's own older tests write (`A — … · B — …`).
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.decision_cards import card_html, listing, slice_panel, tab, who
from slipwai.decision_entry import chosen, options, parse
from slipwai.decision_log import confirm, decisions
from slipwai.live_page import window, window_payload

REAL = """# Decisions: 001-game-club-manager

## D1 — Which bounded contexts does 001-game-club-manager touch?
- **Stage:** model · **Slice:** chart · **When:** 2026-11-12T12:50:29Z · **Stream:** accounts
- **Question:** The event model writes twelve streams. Which of them are one bounded context?
- **Options:** (a) **seven contexts — accounts, clubs, library, game-nights, campaigns, tables, messaging
  (recommended)**; (b) six, with campaigns inside game-nights; (c) one context for the whole service. The
  candidates are `make seams`' groups.

  | Candidate | Streams it writes |
  |---|---|
  | **accounts** (10 slices) | `login`, `person` |
- **Decision:** (a) seven contexts in `game-club-manager-service`.
- **Why:** each context is one stream's group. · **Read against:** the specification.
- **Decided by:** host (stage recommendation)
- **Confidence:** medium · **Would reverse if:** a person says campaigns belong with game nights.
- **Written to:** specs/001-game-club-manager/spec.md
- **Status:** standing

## D45 — Does CL2's code box accept a pasted invite link?
- **Stage:** example map · **Slice:** CL2 · **When:** 2026-11-12T14:12:00Z · **Stream:** clubs
- **Question:** FR-010 gives each club a code and a link. Does CL2's box accept a pasted link?
- **Options:** (a) **CL2 joins by code only, as D24 says; until then a pasted link gets the doesn't-match
  message (recommended)**; (b) CL2 defines `/join/<code>` and serves D16; (c) CL2 accepts any text whose last
  path segment is a code.
- **Decision:** (a). (1) `JoinWithCode` matches only D24's normalised code.
- **In short:** A pasted invite link is refused with the wrong-code message until a page shows organisers the
  link.
- **Why:** until a slice shows an organiser the link nobody has one to paste. · **Read against:** FR-010.
- **Decided by:** sail-decide-skipper (claude-opus-5-5)
- **Confidence:** high · **Would reverse if:** a person says organisers will hand out the link first.
- **Written to:** specs/001-game-club-manager/slices/CL2/examples.md
- **Status:** awaiting human confirmation

## D55 — Where does the install configuration live?
- **Stage:** plan · **Slice:** CL1 · **When:** 2026-11-12T15:00:00Z · **Stream:** clubs
- **Question:** Where is the install configured?
- **Options:** (a) **unset means the built-in configuration (recommended)**; (b) a file per club.
- **Decision:** a variant of (a). The install configuration is read once.
- **Why:** one place. · **Read against:** the method's default.
- **Decided by:** host (standing decision D21)
- **Confidence:** low · **Would reverse if:** a club needs its own.
- **Written to:** specs/001-game-club-manager/spec.md
- **Status:** awaiting human confirmation

## D60 — May a person's own answer stand?
- **Stage:** example map · **Slice:** CL2 · **When:** 2026-11-13T09:00:00Z · **Stream:** clubs
- **Question:** Asked in a conversation <script>alert(1)</script>.
- **Options:** whatever reads best
- **Decision:** the person's words, as they said them.
- **Why:** they said so. · **Read against:** none.
- **Decided by:** human
- **Confidence:** high · **Would reverse if:** they say otherwise.
- **Written to:** specs/001-game-club-manager/spec.md
- **Status:** standing
"""

CHART = """v: 1
feature: 001-game-club-manager
slices:
  CL1:
    fairway: clubs
    capability: sign-in-and-join
  CL2:
    fairway: clubs
    capability: sign-in-and-join
"""


def git(root: Path, *words: str) -> str:
    return subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *words],
                          capture_output=True, text=True, check=True).stdout


class OptionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.book = parse(REAL)

    def test_a_field_that_goes_on_over_indented_lines_is_read_whole(self) -> None:
        self.assertIn("| Candidate |", self.book["D1"]["Options"])

    def test_options_split_on_the_real_shape_and_the_recommended_one_is_known(self) -> None:
        found = options(self.book["D1"]["Options"])
        assert found is not None
        self.assertEqual([one.letter for one in found], ["a", "b", "c"])
        self.assertEqual(found[0].text, "seven contexts — accounts, clubs, library, game-nights, campaigns, tables, "
                                        "messaging")
        self.assertTrue(found[0].recommended)
        self.assertEqual(found[2].text, "one context for the whole service", "the field's commentary is left out")

    def test_the_decision_marks_its_letter_and_keeps_what_it_made_exact(self) -> None:
        self.assertEqual(chosen(self.book["D45"]["Decision"], options(self.book["D45"]["Options"])),
                         ("a", "(1) `JoinWithCode` matches only D24's normalised code."))
        self.assertEqual(chosen(self.book["D55"]["Decision"], options(self.book["D55"]["Options"]))[0], "a")

    def test_the_older_lettered_shape_splits_too(self) -> None:
        found = options("A — not built (recommended) · B — build both")
        assert found is not None
        self.assertEqual([(one.letter, one.text, one.recommended) for one in found],
                         [("A", "not built", True), ("B", "build both", False)])
        self.assertEqual(chosen("A — no connector write in this phase.", found)[0], "A")
        self.assertEqual(chosen("A person decides later.", found)[0], "", "a sentence opening with A is no letter")

    def test_options_in_no_shape_are_shown_as_written(self) -> None:
        self.assertIsNone(options(self.book["D60"]["Options"]))


class BoardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        git(self.root, "init", "-q")
        (self.root / "specs/001-game-club-manager").mkdir(parents=True)
        (self.root / "specs/001-game-club-manager/decisions.md").write_text(REAL, encoding="utf-8")
        (self.root / "specs/001-game-club-manager/chart.yaml").write_text(CHART, encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "record")

    def found(self) -> dict:
        return {one.number: one for one in decisions(self.root)}

    def test_a_card_leads_with_its_sentence_and_one_without_leads_with_its_question(self) -> None:
        found = self.found()
        self.assertIn('<h3 class="lead">A pasted invite link is refused', card_html(found["D45"]))
        self.assertIn('<h3 class="lead">Which bounded contexts', card_html(found["D1"]))
        self.assertIn("this entry has no plain sentence", card_html(found["D1"]))

    def test_the_card_marks_the_chosen_option_and_says_who_how_sure_and_what_would_change_it(self) -> None:
        html = card_html(self.found()["D45"])
        self.assertIn('<li class="chosen"><span class="pick">Chosen</span><span>CL2 joins by code only', html)
        self.assertEqual(html.count("Not chosen"), 2)
        self.assertIn("Decided by the skipper", html)
        self.assertIn("Confidence high", html)
        self.assertIn("<b>Would change if:</b> a person says organisers", html)
        self.assertIn("Awaiting your confirmation", html)
        self.assertIn('data-decision-confirm="md:D45"', html)
        self.assertIn("<summary>Why, in full</summary>", html)

    def test_a_persons_own_answer_with_no_deck_line_shows_as_theirs(self) -> None:
        mine = self.found()["D60"]
        self.assertTrue(mine.yours)
        self.assertEqual(who(mine.decided_by), "you")
        self.assertIn('class="read yours"', card_html(mine))

    def test_every_field_that_reaches_the_page_is_escaped(self) -> None:
        html = card_html(self.found()["D60"])
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("/join/<code>", card_html(self.found()["D45"]))

    def test_the_tab_opens_on_what_awaits_grouped_by_capability_then_slice_and_counts_it(self) -> None:
        html, count = tab(self.root, lambda name, drawn: f'<div data-band="{name}">{drawn}</div>')
        self.assertEqual(count, 2)
        self.assertLess(html.index("Awaiting your confirmation · 2"), html.index("Everything else · 2"))
        awaiting = html[html.index("Awaiting your confirmation · 2"):html.index("Everything else")]
        self.assertIn("<h4>sign-in-and-join</h4>", awaiting)
        self.assertLess(awaiting.index("<h5>Slice CL1</h5>"), awaiting.index("D45"))
        self.assertIn('<div data-band="decisions">', html)
        self.assertIn("Before the slices", html[html.index("Everything else"):])

    def test_the_filters_sit_outside_the_band_and_each_card_carries_what_they_filter_by(self) -> None:
        html, _ = tab(self.root, lambda name, drawn: f'<div data-band="{name}">{drawn}</div>')
        self.assertLess(html.index('name="d-stream"'), html.index("data-band"))
        for name in ("d-stream", "d-slice", "d-by"):
            self.assertIn(f'<select name="{name}"', html)
        self.assertIn('data-stream="clubs" data-slice="CL2" data-by="the skipper"', html)
        self.assertIn('data-by="the session"', listing(decisions(self.root)))

    def test_change_this_opens_the_feedback_box_with_the_decision_quoted_and_its_slice(self) -> None:
        html = card_html(self.found()["D45"])
        self.assertIn('id="change-md-D45"', html)
        self.assertIn("data-feedback=", html)
        self.assertIn("&quot;slice&quot;: &quot;CL2&quot;", html)
        self.assertIn("decision D45: A pasted invite link", html)

    def test_the_slice_window_has_a_decisions_tab_of_that_slices_decisions(self) -> None:
        page = window(self.root, "clubs", "CL2")
        self.assertIn('data-tab="decisions">Decisions · 2</a>', page)
        self.assertIn('&amp;tab=decisions', page)
        self.assertIn('<section data-panel="decisions" hidden>', page)
        panel, count = slice_panel(self.root, "CL2")
        self.assertEqual(count, 2)
        self.assertIn('href="/voyage#change-md-D45"', panel, "the window has no box: it links to the one there is")
        self.assertIn('"decisions_said"', window_payload(self.root, "clubs", "CL2"))

    def test_confirm_edits_that_entrys_status_and_nothing_else_and_commits_it(self) -> None:
        before = (self.root / "specs/001-game-club-manager/decisions.md").read_text(encoding="utf-8")
        said = confirm(self.root, "md:D45", date(2026, 11, 16))
        self.assertIn("D45 confirmed in trunk", said)
        after = (self.root / "specs/001-game-club-manager/decisions.md").read_text(encoding="utf-8")
        self.assertEqual(after, before.replace(
            "- **Status:** awaiting human confirmation\n\n## D55",
            "- **Status:** confirmed by human 2026-11-16\n\n## D55"))
        self.assertEqual(git(self.root, "status", "--porcelain", "--", "specs").strip(), "")
        self.assertIn("A person confirmed D45", git(self.root, "log", "-1", "--format=%s"))
        self.assertTrue(self.found()["D45"].read)
        with self.assertRaises(ValueError):
            confirm(self.root, "md:D45")

    def test_confirm_edits_the_berth_that_holds_an_entry_trunk_has_not_got(self) -> None:
        berth = self.root.parent / f"{self.root.name}-CL2"
        git(self.root, "worktree", "add", "-q", "-b", "slice/CL2", str(berth))
        book = berth / "specs/001-game-club-manager/decisions.md"
        d55 = REAL[REAL.index("## D55"):REAL.index("## D60")]
        book.write_text(book.read_text(encoding="utf-8") + "\n" + d55.replace("D55", "D70"), encoding="utf-8")
        trunk = (self.root / "specs/001-game-club-manager/decisions.md").read_text(encoding="utf-8")
        said = confirm(self.root, "md:D70", date(2026, 11, 16))
        self.assertIn(f"the berth at {berth.name}", said)
        self.assertIn("left uncommitted", said, "the berth's file had the slice's own new entry in it")
        self.assertIn("confirmed by human 2026-11-16", book.read_text(encoding="utf-8").split("## D70")[1])
        self.assertEqual((self.root / "specs/001-game-club-manager/decisions.md").read_text(encoding="utf-8"), trunk)

    def test_a_deck_decision_is_confirmed_through_its_entry_and_read_with_the_receipt_the_ceiling_counts(self) -> None:
        deck = logs.deck_path(self.root, "001-game-club-manager", "clubs")
        deck.parent.mkdir(parents=True)
        deck.write_text(logs.entry("decision", fairway="clubs", slice="CL2", id="D45", what="D45 (a): code only",
                                   decided_by="sail-decide-skipper").line(), encoding="utf-8")
        key = next(one.key for one in decisions(self.root) if one.number == "D45")
        self.assertTrue(key.startswith("deck:clubs:"))
        confirm(self.root, key, date(2026, 11, 16))
        self.assertIn('"kind": "read"', deck.read_text(encoding="utf-8"))
        self.assertFalse(self.found()["D45"].awaiting)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
