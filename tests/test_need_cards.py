"""The card says who acts, and leads with the plain line (issue 172).

manda's *Waiting on you* held seven things and one needed a person. A need the mender takes is *The mender
will do this* and is not a wait; *Have the mender try again* is offered only where the mender would take the
need and has spent its attempts; a person's need says why it is theirs; and a card written before there was
a plain line says the wording is the agent's own.
"""
from __future__ import annotations

import unittest
from dataclasses import dataclass, field

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.block_actions import acted
from slipwai.fleet_page import group_card, headline, waiting_on_you
from slipwai.fleet_record import groups, need_rows
from slipwai.need_who import who_acts
from slipwai.on_you import parked
from slipwai.waiting_inbox import inbox, mender_card

AT = "2026-11-24T18:35:14Z"
PLAIN = "The several-signatories screen cannot be tried, because the staff list has only two people."
DESIGN = {"what": "the picker rule in docs/design.md", "by": "fleet", "plain": PLAIN,
          "check": {"kind": "text", "path": "docs/design.md", "has": ".picker"}}
CLOUD = {"what": "a dead-letter queue on the SES bounce queue in infra/service/main.tf, maxReceiveCount 5",
         "by": "fleet", "check": {"kind": "text", "path": "infra/service/main.tf", "has": "maxReceiveCount"}}


@dataclass
class Stream:
    name: str
    entries: list[logs.Entry] = field(default_factory=list)

    @property
    def merged(self) -> list[str]:
        return [str(e.fields["slice"]) for e in self.entries if e.kind == "merged"]


def row(need: dict, at: str = AT) -> dict:
    line = logs.Entry("told", {"fairway": "intake", "message": "S105 hands back", "needs": [need]}, t=at)
    return {"fairway": "intake", "kind": "told", "t": at, "slice": "S105", "what": "S105 hands back",
            "needs": need_rows(line, set()), "cause": "host", "grouped": "yes", "by": "told"}


def mends(count: int, at: str = AT) -> list[logs.Entry]:
    key = {"fairway": "intake", "parked": at, "need": 0}
    return [logs.entry("mend", harbour=True, job="need", commit="", attempt=n + 1, **key) for n in range(count)] + \
        ([logs.entry("mend-failed", harbour=True, job="need", why="the full gate failed on its branch", **key)]
         if count else [])


def board(rows: list[dict], harbour: list[logs.Entry] | None = None) -> dict:
    waiting = acted(who_acts(None, [Stream("intake")], rows, harbour or []))
    return {"inbox": waiting, "groups": groups(waiting), "streams": {},
            "berths": [{"fairway": "intake", "state": "parked"}], "counts": {}}


class WhoActsTest(unittest.TestCase):
    def test_a_need_the_mender_takes_is_its_own_and_not_a_wait(self) -> None:
        found = board([row(DESIGN)])
        [group] = found["groups"]
        self.assertEqual((group["needs"][0]["who"], group["acts"]), ("mender", "fleet"))
        self.assertEqual(parked(found, []), [], "not something only a person can move on")
        self.assertEqual(waiting_on_you(found), 0)
        self.assertIn("Nothing is waiting on you.", headline(found)[2] + inbox(found))
        drawn = mender_card(found)
        self.assertIn("The mender will do these · 1", drawn)
        self.assertIn(PLAIN, drawn)
        self.assertNotIn("Have the mender try again", drawn + inbox(found))

    def test_try_again_is_offered_only_where_the_mender_would_take_it_and_has_spent_its_attempts(self) -> None:
        found = board([row(DESIGN)], mends(3))
        [group] = found["groups"]
        self.assertEqual(group["needs"][0]["who"], "spent")
        self.assertIn("the full gate failed on its branch", group["needs"][0]["whose"])
        self.assertIn(">Have the mender try again</button>", inbox(found))
        self.assertIn("Have the mender try again", group_card(group, controls=True))
        self.assertIn("Have the mender try again", group["action"]["do"][0])

    def test_a_person_s_need_says_why_and_offers_no_mender(self) -> None:
        found = board([row(CLOUD)], mends(0))
        [group] = found["groups"]
        self.assertEqual(group["needs"][0]["who"], "person")
        drawn = inbox(found)
        self.assertIn("cloud set-up, which spends money", drawn)
        self.assertNotIn("Have the mender try again", drawn)
        self.assertNotIn("data-mend-again", group_card(group, controls=True))
        self.assertEqual(len(parked(found, [])), 1, "a person's, and a wait")

    def test_a_card_written_before_the_plain_line_says_the_words_are_the_agent_s(self) -> None:
        found = board([row(CLOUD)])
        drawn = inbox(found)
        self.assertIn("In the agent&#x27;s own words", drawn)
        self.assertIn("(in the agent&#8217;s own words)", group_card(found["groups"][0], controls=True))

    def test_the_plain_line_leads_and_the_agent_s_words_are_under_details(self) -> None:
        card = group_card(board([row({**CLOUD, "plain": PLAIN})])["groups"][0], controls=True)
        self.assertLess(card.index(PLAIN), card.index("maxReceiveCount 5"))
        self.assertIn('<details class="tech"><summary>Details</summary>a dead-letter queue', card)

    def test_a_captain_s_park_leads_with_its_plain_line_and_its_need_s(self) -> None:
        said = "This slice has used every run it is allowed without finishing the work its step owes."
        need = {"what": "a person reads the demo log", "by": "person", "plain": "Read what the demo walked."}
        park = logs.Entry("parked", {"fairway": "intake", "slice": "S105", "cause": "gate", "plain": said,
                                     "why": "S105: wrote no `demo`. That was the last of 3 run(s)"}, t=AT)
        alone = logs.Entry("parked", {**park.fields, "needs": []}, t="2026-11-24T18:36:00Z")
        rows = [{"fairway": "intake", "kind": "parked", "t": one.t, "slice": "S105", "what": one.fields["why"],
                 "cause": "gate", "plain": said, "needs": need_rows(one, set())}
                for one in (logs.Entry("parked", {**park.fields, "needs": [need]}, t=AT), alone)]
        found = board(rows)
        drawn = inbox(found)
        self.assertNotIn("In the agent&#x27;s own words", drawn)
        self.assertIn("Read what the demo walked.", drawn)
        self.assertIn(said, drawn, "a park with no needs leads with its own plain line")


if __name__ == "__main__":
    unittest.main()
