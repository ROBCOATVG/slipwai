"""A slice's example map: read from its `examples.md`, proven from its `tasks.md`, drawn in its window.

Each case hands the reader text, so nothing here needs a repository; where the map is read from — the
slice's branch or trunk — is `test_example_map_source.py`.
"""
from __future__ import annotations

import json
import unittest

from slipwai.example_map import card_counts, named_ids, proven_ids, read, summary
from slipwai.example_map_page import STYLE, card_html, map_html
from slipwai.live_page import WINDOW_SCRIPT, window_tabs
from slipwai.slice_card import slice_html
from slipwai.slice_rungs import LADDER

#: A map in the shape `example-map.md` prescribes: the bodies run over lines, the questions mixed.
SHAPED = """# CS1 — Place an order: example map

Derived from the slice in the model.

## Story
Buyer places an order for the items in their cart
and gets a confirmation.

## R1 — An order cannot be placed from an empty cart
- empty cart → rejected, nothing recorded

### Scenario: Cannot place order with empty cart (CS-1)
**Given** CartCreated { cartId: "CART-001" } · **When** PlaceOrder { cartId: "CART-001" } ·
**Then** error "cart CART-001 contains no items", no events

## R2 — The order total is the sum of the cart's line totals at the moment it is placed

### Scenario: Successfully place an order (CS-2)
**Given** CartCreated, ItemAdded { price: 29.99, quantity: 2 }
**When** PlaceOrder
**Then** OrderPlaced { total: 59.98 }

### Scenario: A later price change does not move it (CS-3) *(gaps pass)*
**Given** OrderPlaced { total: 59.98 } · **When** PriceChanged { price: 31.00 } · **Then** the total stays 59.98

## R3 — A cart holds at most fifty lines

## Questions
- Q1. Does a cart expire? → for the product owner
- Q2. Is a total rounded per line or once? → answered by D12 (R2).
- Q3. Who may place an order for someone else → D14
- Q4. What does a price of nothing mean (constitution IX: this is that event) → the plan's to decide, with
  an ADR.

The stage's recommendations, for whoever decides:
- **Q1, recommended:** a week. *Why:* nobody asked.

## Gaps reviewed
Nothing else.
"""

PROOF = """# Tasks

- [x] T001 the empty cart

## Examples proven

Run: `make unit` at abc123. CS-3 is not proven yet: it waits on D14.

| Example | Boundary | Test |
|---|---|---|
| CS-1 empty cart | route | `tests/edge/orders.test.ts` "rejects an empty cart (CS-1)" |
| CS-2 | use case | `tests/acceptance/orders.test.ts` |

## Design review
CS-3 is drawn.
"""


class ReaderTest(unittest.TestCase):
    def test_a_map_in_the_prescribed_shape_reads_as_its_story_rules_examples_and_questions(self) -> None:
        found = read(SHAPED, PROOF)
        self.assertEqual(found.story, "Buyer places an order for the items in their cart and gets a confirmation.")
        self.assertEqual([(rule.id, len(rule.examples)) for rule in found.rules], [("R1", 1), ("R2", 2), ("R3", 0)])
        self.assertEqual(found.rules[1].text,
                         "The order total is the sum of the cart's line totals at the moment it is placed")
        first = found.rules[0].examples[0]
        self.assertEqual((first.id, first.title), ("CS-1", "Cannot place order with empty cart"))
        self.assertEqual((first.given, first.when, first.then),
                         ('CartCreated { cartId: "CART-001" }', 'PlaceOrder { cartId: "CART-001" }',
                          'error "cart CART-001 contains no items", no events'))

    def test_given_when_and_then_on_lines_of_their_own_are_read_the_same(self) -> None:
        second = read(SHAPED).rules[1].examples[0]
        self.assertEqual((second.given, second.when, second.then),
                         ("CartCreated, ItemAdded { price: 29.99, quantity: 2 }", "PlaceOrder",
                          "OrderPlaced { total: 59.98 }"))

    def test_a_mark_after_a_scenario_s_id_does_not_hide_the_id(self) -> None:
        third = read(SHAPED).rules[1].examples[1]
        self.assertEqual((third.id, third.title), ("CS-3", "A later price change does not move it"))

    def test_a_question_is_open_until_its_line_says_what_answered_it(self) -> None:
        asked = read(SHAPED).questions
        self.assertEqual([(one.id, one.open) for one in asked],
                         [("Q1", True), ("Q2", False), ("Q3", False), ("Q4", True)])
        self.assertEqual(asked[1].answer, "answered by D12 (R2).")
        self.assertEqual(asked[3].text, "What does a price of nothing mean (constitution IX: this is that event)",
                         "a question's own words run on over its indented lines")

    def test_the_recommendations_after_the_questions_are_not_more_questions(self) -> None:
        self.assertEqual(len(read(SHAPED).questions), 4)

    def test_a_question_with_no_arrow_is_answered_only_where_it_says_by_what(self) -> None:
        asked = read("## Questions\n- Rounding was answered by D3.\n- Does D3 cover refunds?\n").questions
        self.assertEqual([one.open for one in asked], [False, True])

    def test_questions_answered_under_a_heading_of_their_own_are_counted_answered(self) -> None:
        found = read("## Questions answered\n- Who sets the week → D55.\n\n## Questions\nNone open.\n")
        self.assertEqual([(one.id, one.text, one.open) for one in found.questions],
                         [("Q1", "Who sets the week", False)])

    def test_a_questions_section_that_opens_none_open_lists_readings_not_questions(self) -> None:
        found = read("## Questions\nNone open. Each reading taken here:\n- Spacing is every space.\n")
        self.assertEqual((found.questions, found.notes), ([], ["None open. Each reading taken here:"]))

    def test_a_sentence_introducing_the_questions_does_not_hide_them(self) -> None:
        asked = read("## Questions\nOpen for the host:\n- Q1. Does a cart expire?\n- Q2. Who rounds? → D3\n").questions
        self.assertEqual([(one.id, one.open) for one in asked], [("Q1", True), ("Q2", False)])

    def test_a_question_that_says_it_is_still_open_is_open_whatever_it_names(self) -> None:
        lines = ["→ not yet decided", "→ to be decided by the host", "→ open; see D26 for context",
                 "→ the plan's to decide", "→ for the product owner"]
        asked = read("## Questions\n" + "".join(f"- Q. Something {line}\n" for line in lines)).questions
        self.assertEqual([one.open for one in asked], [True] * len(lines))

    def test_naming_a_decision_or_saying_decided_in_passing_answers_nothing(self) -> None:
        lines = ["→ see D26 for the background", "→ depends on what the host decided for carts",
                 "→ nobody has answered"]
        asked = read("## Questions\n" + "".join(f"- Q. Something {line}\n" for line in lines)).questions
        self.assertEqual([one.open for one in asked], [True] * len(lines))

    def test_a_question_is_answered_when_its_answer_says_it_has_been(self) -> None:
        lines = ["→ D26", "→ standing D55.", "→ answered by D12 (R2).", "→ **answered by D53** (host, kept open "
                 "until the plan)", "→ decided by the host on 12 Nov", "→ answered: kept"]
        asked = read("## Questions\n" + "".join(f"- Q. Something {line}\n" for line in lines)).questions
        self.assertEqual([one.open for one in asked], [False] * len(lines))


class AwkwardInputTest(unittest.TestCase):
    def test_an_empty_file_is_an_empty_map_and_not_an_error(self) -> None:
        found = read("")
        self.assertEqual((found.story, found.rules, found.questions), ("", [], []))
        self.assertEqual(summary(found), "0 rules · 0 examples · no questions · 0 of 0 proven")

    def test_a_rule_with_no_scenario_is_still_a_rule(self) -> None:
        found = read("## R1 — Something holds\n- a note\n\n## R2 — Another\n")
        self.assertEqual([(rule.id, rule.examples) for rule in found.rules], [("R1", []), ("R2", [])])

    def test_a_scenario_with_no_id_is_kept_with_its_title_and_never_proven(self) -> None:
        found = read("## R1 — x\n### Scenario: Nobody numbered me\n**Given** a · **When** b · **Then** c\n",
                     "## Examples proven\n| Nobody numbered me | `a.test.ts` |\n")
        one = found.examples[0]
        self.assertEqual((one.id, one.title, one.then, one.proven), ("", "Nobody numbered me", "c", False))

    def test_a_scenario_written_as_a_list_keeps_what_it_says(self) -> None:
        one = read('## R1 — x\n### Scenario: The word (CL1-12)\n- "Sunday Dice" → `DICE`\n').examples[0]
        self.assertEqual((one.given, one.said), ("", '- "Sunday Dice" → `DICE`'))

    def test_a_missing_questions_section_is_a_map_with_no_questions(self) -> None:
        found = read("## Story\nA thing.\n## R1 — x\n### Scenario: y (A-1)\n**Given** a\n")
        self.assertEqual((found.questions, summary(found)),
                         ([], "1 rule · 1 example · no questions · 0 of 1 proven"))

    def test_scenarios_before_any_rule_are_kept_under_a_rule_with_no_name(self) -> None:
        found = read("## Examples\n### Scenario: Early (A-1)\n**Given** a\n## R1 — x\n")
        self.assertEqual([(rule.id, [one.id for one in rule.examples]) for rule in found.rules],
                         [("", ["A-1"]), ("R1", [])])

    def test_text_that_is_not_markdown_at_all_reads_as_nothing(self) -> None:
        found = read("\x00\x01 ### ## R \n|||\n→→ **Given**")
        self.assertEqual(found.rules, [])


class ProvenTest(unittest.TestCase):
    def test_an_example_is_proven_where_a_row_of_examples_proven_names_it_beside_a_test(self) -> None:
        found = read(SHAPED, PROOF)
        self.assertEqual([(one.id, one.proven) for one in found.examples],
                         [("CS-1", True), ("CS-2", True), ("CS-3", False)])
        self.assertEqual(summary(found), "3 rules · 3 examples · 4 questions, 2 open · 2 of 3 proven")

    def test_an_id_named_only_in_a_note_or_another_section_is_not_proven(self) -> None:
        self.assertNotIn("CS-3", proven_ids(PROOF))

    def test_a_row_may_name_several_examples_a_range_or_more_numbers_of_one_prefix(self) -> None:
        self.assertEqual(named_ids("LB2-2, LB2-10 (R1, R5)"), {"LB2-2", "LB2-10"})
        self.assertEqual(named_ids("CL4-1, 3, 5"), {"CL4-1", "CL4-3", "CL4-5"})
        self.assertEqual(named_ids("AC4-1 to AC4-3"), {"AC4-1", "AC4-2", "AC4-3"})
        self.assertEqual(named_ids("X-2–X-4"), {"X-2", "X-3", "X-4"})
        self.assertEqual(named_ids("AC1-1 first sign-in"), {"AC1-1"})

    def test_a_list_item_names_its_example_before_the_test(self) -> None:
        proof = "## Examples proven\n- TB1-1 Priya sets the week — `set-club-week.test.ts`\n- TB1-2 not yet\n"
        self.assertEqual(proven_ids(proof), {"TB1-1"})

    def test_the_heading_is_found_inside_the_task_line_that_wrote_it(self) -> None:
        proof = "## Phase 5\n- [x] T015 `## Examples proven\n\n| Example | Test |\n|---|---|\n| AC5-1 | a.test.ts |\n"
        self.assertEqual(proven_ids(proof), {"AC5-1"})

    def test_a_row_that_says_it_is_not_proven_or_names_no_test_proves_nothing(self) -> None:
        proof = ("## Examples proven\n| Example | Test |\n|---|---|\n| X-3 | not proven — deferred |\n"
                 "| X-4 | route |\n| X-5 | `a.test.ts` pending a fix |\n| X-6 | `a.test.ts` |\n"
                 "- X-10 — pending\n- X-11 — the route\n- X-12 — `b.test.ts`\n")
        self.assertEqual(proven_ids(proof), {"X-6", "X-12"})

    def test_a_task_list_with_no_examples_proven_section_proves_nothing(self) -> None:
        self.assertEqual(proven_ids("- [ ] T018 Fill `## Examples proven` later\n| CS-1 | a.test.ts |\n"), set())


class CountsTest(unittest.TestCase):
    def test_the_card_says_rules_examples_and_the_questions_still_open(self) -> None:
        self.assertEqual(card_counts(read(SHAPED)), "3 rules · 3 examples · 2 questions open")
        self.assertEqual(card_counts(read("## R1 — x\n## Questions\n- Q1. y → D1\n")),
                         "1 rule · 0 examples · no questions open")
        self.assertEqual(card_counts(None), "")

    def test_the_examples_step_of_an_opened_card_carries_the_counts_and_the_way_to_the_map(self) -> None:
        ladder = json.dumps([{"name": name, "state": "done" if index < 2 else "now" if index == 2 else "todo",
                              "began": 0, "took": 0} for index, name in enumerate(LADDER)])
        row = {"slice": "GN3", "title": "Bring it", "state": "working", "fairway": "game-nights",
               "feature": "001-demo", "stage": "Implementing", "chip": "Implementing", "ladder": ladder,
               "examples": "11 rules · 16 examples · 1 question open"}
        card = slice_html(row)
        step = card[card.index("<b>Examples</b>"):card.index("<b>Plan</b>")]
        self.assertIn("11 rules · 16 examples · 1 question open", step)
        self.assertIn("/slice?fairway=game-nights&amp;slice=GN3&amp;tab=map", step)
        self.assertNotIn("question open", slice_html({**row, "examples": ""}))

    def test_a_done_slice_s_card_links_to_its_window_at_the_map(self) -> None:
        row = {"slice": "AC1", "title": "Sign in", "state": "done", "fairway": "accounts", "feature": "001-demo",
               "examples": "11 rules · 16 examples · 1 question open"}
        self.assertIn('<p class="span">11 rules · 16 examples · 1 question open · <a href="/slice?fairway=accounts'
                      '&amp;slice=AC1&amp;tab=map"', slice_html(row))
        self.assertEqual(card_html({**row, "examples": ""}), "")


class TabTest(unittest.TestCase):
    def test_the_map_is_the_story_a_column_a_rule_its_examples_and_the_questions_last(self) -> None:
        drawn = map_html(read(SHAPED, PROOF))
        self.assertLess(drawn.index('class="story"'), drawn.index('class="rule"'))
        self.assertLess(drawn.rindex('class="ex"'), drawn.index('class="q '))
        self.assertIn("3 rules · 3 examples · 4 questions, 2 open · 2 of 3 proven", drawn)
        self.assertEqual(drawn.count('<div class="col">'), 4, "three rules and the questions")

    def test_an_example_is_a_button_that_opens_in_place_on_its_given_when_and_then(self) -> None:
        drawn = map_html(read(SHAPED, PROOF))
        self.assertIn('<button type="button" class="ex" aria-expanded="false" data-ex="CS-1">', drawn)
        self.assertIn('<span class="gwt"><span><b>Given</b> CartCreated { cartId: &quot;CART-001&quot; }</span>',
                      drawn)
        self.assertEqual((drawn.count("Proven by a test"), drawn.count("Not proven yet")), (2, 1))

    def test_a_rule_with_no_examples_yet_still_shows(self) -> None:
        drawn = map_html(read(SHAPED))
        rule = drawn[drawn.index("<b>R3 · </b>"):]
        self.assertTrue(rule.split("</div>", 1)[1].startswith('<p class="none">No examples yet</p>'))

    def test_an_open_question_is_red_and_an_answered_one_says_what_answered_it(self) -> None:
        drawn = map_html(read(SHAPED))
        self.assertIn('<div class="q open"><span><b>Q1 · </b>Does a cart expire?</span>'
                      '<span class="said">Open · for the product owner</span></div>', drawn)
        self.assertIn('<span class="said">Answered by D12 (R2).</span>', drawn)
        self.assertIn('<span class="said">Answered: D14</span>', drawn)

    def test_a_slice_with_no_examples_file_has_no_map(self) -> None:
        self.assertIn("No example map yet", map_html(None))

    def test_the_tabs_are_addresses_so_a_reload_keeps_the_one_open(self) -> None:
        tabs = window_tabs("game nights", "AC1")
        self.assertIn('href="/slice?fairway=game%20nights&amp;slice=AC1&amp;tab=map" data-tab="map"', tabs)
        self.assertIn('data-tab="where" aria-current="page">Where it is</a>', tabs)
        self.assertIn("history.replaceState", WINDOW_SCRIPT)

    def test_every_field_that_reaches_the_page_is_escaped(self) -> None:
        bad = "<script>x</script>"
        text = (f"## Story\n{bad}\n## R1 — {bad}\n### Scenario: {bad} (A-1)\n**Given** {bad} · **When** {bad} · "
                f"**Then** {bad}\n### Scenario: {bad}\n- {bad}\n## Questions\n- Q1. {bad} → {bad}\n"
                f"## Questions answered\nNone open — {bad}\n")
        drawn = map_html(read(text))
        self.assertNotIn("<script>", drawn)
        self.assertEqual(drawn.count("&lt;script&gt;"), 11, "story, rule, two titles, three steps, a list body, "
                                                             "a question, its answer and the note")
        self.assertNotIn("<script", card_html({"slice": "A", "state": "done", "fairway": bad, "examples": bad}))

    def test_a_questions_section_that_is_only_a_sentence_is_one_faded_card(self) -> None:
        found = read("## Questions\nNone open — D72–D78 answered what the artefacts left.\n")
        self.assertEqual((found.questions, found.notes),
                         ([], ["None open — D72–D78 answered what the artefacts left."]))
        self.assertIn('<div class="q answered note"><span>None open — D72–D78 answered what the artefacts left.'
                      "</span></div>", map_html(found))

    def test_the_same_map_drawn_twice_says_the_same_so_the_poll_leaves_it_alone(self) -> None:
        self.assertEqual(map_html(read(SHAPED, PROOF)), map_html(read(SHAPED, PROOF)))
        self.assertNotEqual(map_html(read(SHAPED, PROOF)), map_html(read(SHAPED)))

    def test_the_four_colours_are_tokens_set_again_for_the_dark_theme(self) -> None:
        light, dark = STYLE.split(":root:has(#t-dark:checked)", 1)
        for token in ("--map-story", "--map-rule", "--map-example", "--map-question", "--map-ink"):
            self.assertIn(f"{token}:", light.split("}", 1)[0])
            self.assertIn(f"{token}:", dark)


if __name__ == "__main__":
    unittest.main()
