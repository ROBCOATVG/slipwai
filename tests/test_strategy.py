"""The strategy recommendation: what `why` and the map recommend, what an ADR decides, what `/strangle` refuses.

What this gates is that the recommendation follows `docs/change-strategy.md`'s own judgement mechanically — a
platform trigger stops after the low rungs, a delivery trigger puts the pipeline first, *leave it* is what no
trigger and an unreadable trigger both recommend, rewrite is never recommended — that the map's preconditions
are read from the map, that a decision is only ever an accepted ADR read from the tree, and that the row and the
command carry all of it. Experimental, with the rest of adoption (experimental).
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from slipwai.convergence import detected, reconciled
from slipwai.layout import Layout
from slipwai.origin import Adoption, adoption_of
from slipwai.project.strangle_command import strangle_files
from slipwai.services import App
from slipwai.strategy import STRATEGIES, decision_of, ledger_finished, recommend, with_recommendation

DELIVERY = Layout("delivery")
ADR = """# 0002. Change strategy

Date: 2026-09-07

## Status

{status}

## Context

The runtime is out of support.

## Decision

Strategy: {strategy}

## Consequences

None yet.
"""


def wrapped(name: str = "shop", path: str = ".", kind: str = "service", **commands: str) -> App:
    return App(name, path, kind, "javascript", None, 0, generated=False, commands=commands or {"test": None})


def floor() -> list[dict]:
    return detected([wrapped(kind="application")], Adoption())


def top() -> list[dict]:
    adoption = Adoption(release={"path": "pipeline", "evidence": [], "provenance": "detected"})
    return detected([App("api", "apps/api", "service", "javascript", None, 0, generated=False,
                         commands={"test": "npm test", "typecheck": "tsc"}, structure="hexagonal")], adoption)


class StrategyTest(unittest.TestCase):
    def test_the_trigger_is_read_for_what_it_names_and_the_essays_judgement_follows(self) -> None:
        platform = recommend("Java 8 is end of life and the framework is unsupported", top())
        self.assertEqual((platform["recommended"], platform["trigger"]), ("in-place", "platform"))
        self.assertIn("after rung 1 or 2", platform["stop"])
        delivery = recommend("we cannot ship: releases take a week and every deploy is an incident", top())
        self.assertEqual((delivery["recommended"], delivery["trigger"]), ("in-place", "delivery"))
        self.assertIn("one automated path", delivery["stop"])
        host = recommend("hosting costs; move to AWS", top())
        self.assertEqual(host["trigger"], "host")
        change = recommend("nobody understands it and it is too coupled to change safely", top())
        self.assertEqual(change["recommended"], "modular-monolith")
        capability = recommend("a new market needs the ordering capability split out so two teams can move", top())
        self.assertEqual(capability["recommended"], "strangler-fig")
        self.assertIn("architecture rung is last", capability["because"][1])
        # Several named: the first in the reading order wins, the others are said.
        both = recommend("the runtime is end of life and we want to scale the team", top())
        self.assertEqual(both["trigger"], "platform")
        self.assertIn("also: capability", both["because"][0])
        self.assertNotIn("rewrite", {r["recommended"] for r in (platform, delivery, host, change, capability, both)})
        self.assertIn("rewrite", STRATEGIES, "a person may still decide it")

    def test_leave_it_is_what_no_trigger_and_an_unreadable_trigger_recommend(self) -> None:
        nothing = recommend(None, floor())
        self.assertEqual((nothing["recommended"], nothing["trigger"]), ("leave-it", None))
        self.assertIn("no business trigger is recorded", nothing["because"][0])
        unreadable = recommend("because", floor())
        self.assertEqual(unreadable["recommended"], "leave-it")
        self.assertIn("names neither a platform", unreadable["because"][0])

    def test_the_preconditions_come_from_the_map(self) -> None:
        at_floor = recommend("split it so teams can move", floor())["before"]
        self.assertEqual(len(at_floor), 5, at_floor)
        self.assertIn("path to production is `unknown`", at_floor[0])
        self.assertIn("safety net is `none`", at_floor[1])
        self.assertIn("structure is `as-found`", at_floor[2])
        self.assertIn("seam requests enter through", at_floor[3])
        self.assertIn("/characterise", at_floor[4])
        at_top = recommend("split it so teams can move", top())["before"]
        self.assertEqual(len(at_top), 3, "a pipeline and roles hold; the suite is recorded but not established green")
        self.assertIn("safety net is `tests-exist`", at_top[0])
        self.assertEqual(recommend("java 8 is end of life", top())["before"], [at_top[0]])

    def test_a_decision_is_only_ever_an_accepted_adr_read_from_the_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adr = root / "delivery/docs/adr"
            adr.mkdir(parents=True)
            self.assertEqual(decision_of(root, DELIVERY), {"decided": None, "adr": None})
            (adr / "0002-change-strategy.md").write_text(
                ADR.format(status="Proposed", strategy="strangler-fig"))
            self.assertIsNone(decision_of(root, DELIVERY)["decided"], "proposed is not decided")
            (adr / "0002-change-strategy.md").write_text(
                ADR.format(status="Accepted", strategy="strangler-fig"))
            self.assertEqual(decision_of(root, DELIVERY),
                             {"decided": "strangler-fig", "adr": "delivery/docs/adr/0002-change-strategy.md"})
            (adr / "0003-leave-it.md").write_text(ADR.format(status="Accepted", strategy="**leave-it**"))
            self.assertEqual(decision_of(root, DELIVERY)["decided"], "leave-it", "the later ADR supersedes")
            # The first real ADR's Consequences said "the `Strategy:` line here reads `strangler-fig`" before the
            # line itself, and the decision read as the strategy `line` — that is, as no decision at all.
            (adr / "0004-prose.md").write_text(
                ADR.format(status="Accepted", strategy="in-place").replace(
                    "## Decision", "## Consequences\n\n- `/strangle` refuses until the\n  `Strategy:` line here reads "
                    "`strangler-fig` under an `Accepted` status.\n\n## Decision")
            )
            self.assertEqual(decision_of(root, DELIVERY)["decided"], "in-place",
                             "a sentence that mentions the line is not the line")
            self.assertFalse(ledger_finished(root, DELIVERY), "no ledger, nothing finished")
            (root / "delivery/retirement.md").write_text(
                "| Date | Capability | From | To | Routed by | Pinned by | Status |\n|---|---|---|---|---|---|---|\n"
                "| 2026-09-01 | orders | a | b | router | t1 | *routed* |\n"
                "| 2026-09-05 | orders | a | b | router | t1 | *removed* |\n"
            )
            self.assertTrue(ledger_finished(root, DELIVERY), "the last row per capability is what counts")
            (root / "delivery/retirement.md").write_text(
                (root / "delivery/retirement.md").read_text() + "| 2026-09-06 | billing | a | b | r | t2 | *moved* |\n"
            )
            self.assertFalse(ledger_finished(root, DELIVERY))

    def test_the_row_the_record_and_the_command_carry_the_recommendation_and_the_decision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            apps = [wrapped(test="npm test")]
            adoption = with_recommendation(root, DELIVERY, Adoption(why="Python 2 is end of life"), apps)
            row = next(r for r in adoption.convergence if r["axis"] == "strategy")
            self.assertEqual((row["rung"], row["provenance"]), ("recommended", "detected"))
            self.assertIn("recommended: in-place", row["evidence"])
            self.assertEqual(adoption.strategy["decided"], None)
            # The record survives a manifest round trip.
            read_back = adoption_of({"origin": "adopted", **adoption.record()})
            assert read_back is not None
            self.assertEqual(read_back.strategy, adoption.strategy)
            files = strangle_files(apps, DELIVERY, "existing", adoption)
            essay = files["docs/change-strategy.md"]
            self.assertLess(essay.index("## Recommended for this repository"),
                            essay.index("## Three strategies, not two"))
            self.assertIn("**`in-place`**", essay)
            self.assertIn("**Nothing is decided yet.**", essay)
            self.assertIn("The word `Accepted` is the person's", essay)
            self.assertIn("`delivery/docs/adr/`", essay)
            command = files["commands/strangle.md"]
            self.assertIn("**No decision, no strangling.**", command)
            self.assertIn("Today it\n  reads `null` — recommended `in-place`, decided nothing", command)

            (root / "delivery/docs/adr").mkdir(parents=True)
            (root / "delivery/docs/adr/0002-strategy.md").write_text(
                ADR.format(status="Accepted", strategy="strangler-fig"))
            decided = with_recommendation(root, DELIVERY, Adoption(why="Python 2 is end of life"), apps)
            row = next(r for r in decided.convergence if r["axis"] == "strategy")
            self.assertEqual(row["rung"], "decided", "an ADR decides, whatever was recommended")
            self.assertIn("ADR delivery/docs/adr/0002-strategy.md: strangler-fig", row["evidence"])
            self.assertIn("`strangler-fig` (decided by `delivery/docs/adr/0002-strategy.md`)",
                          strangle_files(apps, DELIVERY, "existing", decided)["commands/strangle.md"])
            (root / "delivery/docs/adr/0003-leave.md").write_text(ADR.format(status="Accepted", strategy="leave-it"))
            left = with_recommendation(root, DELIVERY, Adoption(why="Python 2 is end of life"), apps)
            self.assertEqual(next(r for r in left.convergence if r["axis"] == "strategy")["rung"], "done",
                             "leaving it finishes the axis")
            # No trigger: the row stays open — the rung's meaning — while the page still recommends leaving it.
            quiet = with_recommendation(root / "nowhere", DELIVERY, Adoption(), apps)
            self.assertEqual(next(r for r in quiet.convergence if r["axis"] == "strategy")["rung"], "open")
            self.assertEqual(quiet.strategy["recommended"], "leave-it")

    def test_a_repository_adopted_before_the_rename_is_read_under_the_names_it_has(self) -> None:
        """Up to 1.12 the axis was `modernisation` and the strategy `modernise-in-place`. Both are read and written
        back current, because a rename here is no reason for a repository to lose an answer a person gave."""
        rows: list[dict] = [{"axis": "modernisation", "rung": "decided", "target": "done", "evidence": "the ADR",
                             "provenance": "confirmed", "planned": "the language rung"}]
        read_back = adoption_of({
            "origin": "adopted",
            "why": "Java 8 is end of life",
            "modernisation": {"recommended": "modernise-in-place", "decided": "modernise-in-place",
                              "adr": "delivery/docs/adr/0002-modernisation-strategy.md", "provenance": "detected"},
            "convergence": rows,
        })
        assert read_back is not None
        self.assertEqual((read_back.strategy["recommended"], read_back.strategy["decided"]), ("in-place", "in-place"))
        self.assertNotIn("modernisation", read_back.record(), "what is written back is only ever the current name")
        self.assertEqual(read_back.record()["strategy"], read_back.strategy)
        self.assertEqual(read_back.convergence[0]["axis"], "strategy")
        # The rung the person confirmed survives: reconciled under the old axis name, the fresh row would otherwise
        # replace it with the tree's reading, which is what a dropped row looks like.
        fresh = detected([wrapped(test="npm test")], read_back)
        row = next(r for r in reconciled(rows, fresh, []) if r["axis"] == "strategy")
        self.assertEqual((row["rung"], row["provenance"], row["planned"]),
                         ("decided", "confirmed", "the language rung"))

    def test_an_adr_accepted_under_the_old_spelling_still_decides(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adr = root / "delivery/docs/adr"
            adr.mkdir(parents=True)
            (adr / "0002-modernisation-strategy.md").write_text(
                ADR.format(status="Accepted", strategy="modernise-in-place"))
            self.assertEqual(decision_of(root, DELIVERY)["decided"], "in-place",
                             "the decision is the person's; the factory renamed the value, not the choice")


if __name__ == "__main__":
    unittest.main()


class OneProductOneLineTest(unittest.TestCase):
    """The platform record holds a row per application per product, so a repository whose four npm packages
    all run the same Node produced four identical sentences under `because` and four more under `before` —
    seen on the first real monorepo this met. A reader needs the products, not the applications running them."""

    def test_one_runtime_four_applications_is_one_reason_and_one_precondition(self) -> None:
        from slipwai.strategy import expired_products, platform_before, recommend

        products = [
            {"app": name, "title": "Node.js", "version": "20", "product": "node", "cycle": "20",
             "status": "end-of-life", "eol": "2026-04-30"}
            for name in ("legacy-bo-theme", "new-theme", "ui-tests", "core-theme-js")
        ]
        self.assertEqual([(p["title"], p["version"]) for p in expired_products(products)], [("Node.js", "20")])
        self.assertEqual(len(platform_before(products)), 1)
        recommended = recommend(None, [], products)
        self.assertEqual(
            sum(1 for line in recommended["because"] if "Node.js 20" in line), 1,
            "the reason is the runtime, however many applications run it",
        )
        self.assertEqual(sum(1 for line in recommended["before"] if "Node.js 20" in line), 1)

    def test_two_runtimes_past_their_end_of_life_are_still_two_lines(self) -> None:
        from slipwai.strategy import expired_products

        products = [
            {"app": "web", "title": "Node.js", "version": "20", "product": "node", "cycle": "20",
             "status": "end-of-life", "eol": "2026-04-30"},
            {"app": "api", "title": "PHP", "version": "8.1", "product": "php", "cycle": "8.1",
             "status": "end-of-life", "eol": "2025-12-31"},
            {"app": "web2", "title": "Node.js", "version": "20", "product": "node", "cycle": "20",
             "status": "end-of-life", "eol": "2026-04-30"},
        ]
        self.assertEqual(
            [(p["title"], p["version"]) for p in expired_products(products)],
            [("Node.js", "20"), ("PHP", "8.1")],
            "deduped by product and version, in the order the record first names them",
        )

    def test_a_runtime_only_nearing_its_end_of_life_is_not_a_precondition(self) -> None:
        from slipwai.strategy import expired_products

        self.assertEqual(expired_products([
            {"app": "api", "title": "PHP", "version": "8.2", "product": "php", "cycle": "8.2",
             "status": "ending", "eol": "2026-12-31"},
        ]), [], "`ending` is a date to watch, not a rung the tree says is below")
