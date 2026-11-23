"""A capability built on a stand-in is a release blocker, not a finished one (slipwai#154, item 5).

manda's "The BD is told when a deal needs them" cleared its gates and merged with a drop-directory mailer and
a no-transport one behind its `OutboundMail` port: the real transport, its IAM grant and a verified sending
domain were handed back as one need among forty-nine, and in every environment the BD was never told. Its
founder screens were proven by tests alone, because no story could seed an accepted founder. The owner's
ruling: a finding or stand-in that leaves a feature unusable for its actor is never deferred, and its
capability is not done while that is true.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from test_capabilities import CAPS, CHART, merged

from slipwai.assets import TOOLKIT_ROOT
from slipwai.demos import release_blockers
from slipwai.fleet_page import headline
from slipwai.project import capability_gates, ladder

MAILER = "Stand-in: OutboundMail · drop-directory · SES adapter, ses:SendEmail, a verified sending domain"
WHOLE = [merged("ORD-01"), merged("ORD-02")]


def flat(text: str) -> str:
    return " ".join(text.split())


class RecordTest(unittest.TestCase):
    def test_a_stand_in_line_is_a_blocker_naming_what_is_missing(self) -> None:
        said = CAPS.record_blockers(f"## Walk\nok\n\n{MAILER}\nCleared: 2026-11-23 · abc\n")
        self.assertEqual(len(said), 1)
        self.assertIn("built on a stand-in: OutboundMail · drop-directory · SES adapter", said[0])

    def test_a_person_accepting_it_on_its_line_ends_the_blocker(self) -> None:
        self.assertEqual(CAPS.record_blockers(f"{MAILER} · Accepted-by: luke 2026-11-23\n"), [])

    def test_an_agent_cannot_accept_a_stand_in(self) -> None:
        for agent in ("sail-demo-hand", "hand", "harbour-trunk-mender", "Claude"):
            said = CAPS.record_blockers(f"{MAILER} · Accepted-by: {agent} 2026-11-23\n")
            self.assertEqual(len(said), 1, agent)
            self.assertIn("only a person accepts a stand-in", said[0])

    def test_a_stand_in_that_names_less_than_its_three_parts_says_so(self) -> None:
        self.assertIn("write all three", CAPS.record_blockers("Stand-in: OutboundMail\n")[0])

    def test_a_screen_the_walk_could_not_reach_is_a_blocker(self) -> None:
        said = CAPS.record_blockers("Unreached: /workspaces/:id/founder · no story seeds an accepted founder\n")
        self.assertEqual(said, ["the walk cannot reach /workspaces/:id/founder · no story seeds an accepted "
                                "founder from seeded state"])

    def test_a_record_with_neither_has_none(self) -> None:
        self.assertEqual(CAPS.record_blockers("## Walk\nall reached\n\nCleared: 2026-11-23 · abc\n"), [])


class RowsTest(unittest.TestCase):
    def rows(self) -> list[dict]:
        return CAPS.state(CHART, WHOLE, {"place-an-order"},
                          blocked={"place-an-order": ["built on a stand-in: OutboundMail · drop-directory · SES"]})

    def test_a_blocked_capability_is_owed_no_demo_and_is_listed_as_blocked(self) -> None:
        rows = self.rows()
        self.assertEqual(CAPS.due(rows), [])
        self.assertEqual([row["capability"] for row in CAPS.blocked(rows)], ["place-an-order"])

    def test_it_may_not_be_accepted_and_the_refusal_says_how_it_ends(self) -> None:
        row = next(one for one in self.rows() if one["capability"] == "place-an-order")
        refused = CAPS.acceptable(row)
        self.assertIn("is a release blocker, not done", refused)
        self.assertIn("Accepted-by:", refused)

    def test_without_blockers_the_capability_is_due_as_before(self) -> None:
        rows = CAPS.state(CHART, WHOLE, {"place-an-order"})
        self.assertEqual([row["capability"] for row in CAPS.due(rows)], ["place-an-order"])
        self.assertEqual(CAPS.blocked(rows), [])


class OnDiskTest(unittest.TestCase):
    """What the reader finds in a project: the record's lines and each slice's story."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.addCleanup(setattr, CAPS, "SPECS", CAPS.SPECS)
        CAPS.SPECS = Path(directory.name)

    def write(self, relative: str, text: str) -> None:
        path = CAPS.SPECS / "001-orders" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_an_empty_story_is_a_gap_and_a_story_that_opens_a_screen_is_not(self) -> None:
        self.write("slices/ORD-01/try-it.json", "{}\n")
        self.write("slices/ORD-02/try-it.json", json.dumps({"open": [{"label": "it", "path": "/orders"}]}))
        found = CAPS.blockers("001-orders", ["place-an-order", "bill-an-order"], CHART)
        self.assertEqual(found, {"place-an-order": [
            "ORD-01's try-it.json is empty, so no walk reaches its screens from seeded state"]})

    def test_the_record_and_the_stories_are_read_together(self) -> None:
        self.write("capabilities/place-an-order/gates.md", f"{MAILER}\nCleared: 2026-11-23 · abc\n")
        self.write("slices/ORD-02/try-it.json", json.dumps({"as": "ada", "open": [], "steps": [], "given": []}))
        self.assertEqual(len(CAPS.blockers("001-orders", ["place-an-order"], CHART)["place-an-order"]), 2)


class BoardTest(unittest.TestCase):
    ROW = {"capability": "tell-the-bd", "whole": True, "gated": True,
           "blockers": ["built on a stand-in: OutboundMail · no-transport · SES"]}

    def test_only_a_whole_gated_blocked_row_is_a_release_blocker(self) -> None:
        rows = [self.ROW, {**self.ROW, "capability": "ungated", "gated": False},
                {**self.ROW, "capability": "clear", "blockers": []}, {"capability": "old-script", "whole": True}]
        self.assertEqual(release_blockers({"rows": rows}),
                         [{"capability": "tell-the-bd", "blockers": self.ROW["blockers"]}])

    def test_the_board_never_says_built_over_a_stand_in(self) -> None:
        found = {"berths": [{"fairway": "INT", "state": "finished"}], "counts": {"merged": 4},
                 "release_blockers": release_blockers({"rows": [self.ROW]})}
        colour, sentence, under = headline(found)
        self.assertEqual(colour, "brass")
        self.assertEqual(sentence, "Merged, not done: 1 capability built on a stand-in — tell-the-bd "
                                   "(built on a stand-in: OutboundMail · no-transport · SES).")
        self.assertIn("Accepted-by:", under)
        self.assertTrue(headline({**found, "release_blockers": []})[1].startswith("Built:"))


def try_it_module():
    spec = importlib.util.spec_from_file_location("try_it_sealed", TOOLKIT_ROOT / "scripts/agents/try_it.py")
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class SealedGivenTest(unittest.TestCase):
    """A founder's email sealed under the workspace's key cannot be a plain given; a given says what to seal."""

    EVENTS = {"InviteAccepted": [{"name": "workspaceId", "identifies": "workspace"}, {"name": "email"}]}

    def faults(self, given: dict) -> list[str]:
        story = {"given": [{"stream": "invite-1", "event": "InviteAccepted", **given}]}
        return try_it_module().story_faults("001/S50", story, set(), None, [], self.EVENTS)

    def test_a_seal_naming_a_key_and_fields_the_data_gives_passes(self) -> None:
        self.assertEqual(self.faults({"data": {"workspaceId": "ws_1", "email": "f@example.com"},
                                      "seal": {"key": "ws_1", "fields": ["email"]}}), [])

    def test_a_seal_is_held_to_its_shape_the_data_and_the_model(self) -> None:
        data = {"workspaceId": "ws_1", "email": "f@example.com"}
        self.assertIn("001/S50: given 1's `seal` is", self.faults({"data": data, "seal": {"fields": ["email"]}})[0])
        self.assertEqual(self.faults({"data": data, "seal": {"key": "ws_1", "fields": ["name", "workspaceId"]}}),
                         ["001/S50: given 1 seals `name`, which its data does not give"])
        self.assertEqual(self.faults({"data": {**data, "email": {"ciphertext": "x"}},
                                      "seal": {"key": "ws_1", "fields": ["email"]}}),
                         ["001/S50: given 1 seals `email`, which is not plain text to seal"])


class InstructionsTest(unittest.TestCase):
    def test_the_gates_say_a_stand_in_is_a_release_blocker_and_how_it_ends(self) -> None:
        rung = flat(capability_gates.capability_gates_stage(True))
        self.assertIn("**A stand-in is a release blocker, not a pass.**", rung)
        self.assertIn("`Stand-in: <port> · <adapter> · <the missing piece>`", rung)
        self.assertIn("`Unreached: <screen> · <why>`", rung)
        self.assertIn("`· Accepted-by: <who> <date>`", rung)
        self.assertIn("capabilities.py --blocked", rung)
        self.assertIn("from seeded state, or the record says `Unreached:` for it", rung)

    def test_the_plan_rung_asks_for_the_cloud_once_as_a_bundle_and_builds_the_real_adapter(self) -> None:
        plan = flat(ladder.sail_ladder(True, []))
        self.assertIn(flat(capability_gates.CLOUD_PREREQUISITES), plan)
        self.assertIn("as **one** question to a person that bundles everything", plan)
        self.assertIn("builds the **real** adapter behind the port", plan)

    def test_the_story_says_how_a_sealed_field_is_given(self) -> None:
        self.assertIn('named in the given\'s `"seal": {"key": "<whose key>", "fields": ["<field>"]}`',
                      flat(ladder.TRY_STORY))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
