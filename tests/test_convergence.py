"""The convergence map: where an adopted repository stands on each ladder, claimed only from a fact.

What this gates is the map's one rule. A rung is placed by what the record establishes — a recorded test
command, a declared layout, a release path a file or a person gave — and never higher; a rung nothing
establishes is the ladder's floor with `unrecorded` provenance; a row a person placed stands, with the slice
planned to move it, and every refresh says what moved. Experimental, with the rest of adoption (experimental).
"""
from __future__ import annotations

import unittest

from slipwai.convergence import AXES, BY_KEY, detected, reconciled, summary
from slipwai.origin import Adoption
from slipwai.services import App


def wrapped(name: str, path: str, kind: str = "service", **fields) -> App:
    commands = {"install": None, "typecheck": None, "lint": None, "test": None, "integration": None,
                "adversarial": None, "audit": None, "mutation": None, **fields.pop("commands", {})}
    return App(name, path, kind, "javascript", None, 0, generated=False, commands=commands, **fields)


class ConvergenceTest(unittest.TestCase):
    def test_every_axis_has_a_floor_a_target_and_a_meaning_for_each_rung(self) -> None:
        for axis in AXES:
            self.assertIn(axis.target, axis.rungs, axis.key)
            self.assertEqual(set(axis.means), set(axis.rungs), f"{axis.key}: every rung says what it means")
            self.assertGreater(axis.index(axis.target), 0, f"{axis.key}: the target is above the floor")

    def test_a_rung_is_claimed_only_from_a_fact_and_the_floor_is_unrecorded(self) -> None:
        nothing = detected([wrapped("shop", ".", kind="application")], Adoption())
        by_axis = {row["axis"]: row for row in nothing}
        self.assertEqual([row["axis"] for row in nothing], [axis.key for axis in AXES], "every axis, in order")
        self.assertEqual((by_axis["path-to-production"]["rung"], by_axis["path-to-production"]["provenance"]),
                         ("unknown", "unrecorded"))
        self.assertEqual((by_axis["integration"]["rung"], by_axis["integration"]["provenance"]), ("unknown",
            "unrecorded"))
        self.assertEqual(by_axis["safety-net"]["rung"], "none")
        self.assertEqual(by_axis["structure"]["rung"], "as-found")
        self.assertIn("role not established for shop", by_axis["structure"]["evidence"])
        self.assertEqual(by_axis["constitution"]["rung"], "template")
        self.assertEqual((by_axis["data"]["rung"], by_axis["data"]["provenance"]), ("open", "unrecorded"))
        self.assertEqual((by_axis["strategy"]["rung"], by_axis["strategy"]["provenance"]), ("open",
            "unrecorded"))
        self.assertTrue(all(row["planned"] is None for row in nothing), "nothing is planned until a slice is")
        self.assertEqual((by_axis["platform"]["rung"], by_axis["platform"]["provenance"]), ("unknown", "unrecorded"))
        self.assertEqual(summary(nothing), (0, 3, 6))

        adoption = Adoption(
            why="the runtime is end of life",
            database={"schema": "elsewhere", "repository": "https://x/schema.git", "provenance": "overridden"},
            infrastructure={"home": "unmanaged", "provenance": "detected"},
            release={"path": "pipeline", "evidence": ["pipeline: .gitlab-ci.yml"], "provenance": "detected"},
            ci={"forge": "gitlab", "gate": "delivery/ci/verify-delivery.gitlab-ci.yml", "provenance": "detected"},
        )
        apps = [
            wrapped("api", "apps/api", structure="hexagonal", commands={"test": "npm test", "typecheck": "tsc"}),
            wrapped("cli", "apps/cli", kind="tool", structure="hexagonal",
                    commands={"test": "npm test", "typecheck": "tsc"}),
        ]
        rows = {row["axis"]: row for row in detected(apps, adoption)}
        self.assertEqual((rows["path-to-production"]["rung"], rows["path-to-production"]["evidence"]),
                         ("pipeline", "pipeline: .gitlab-ci.yml"))
        self.assertEqual(rows["safety-net"]["rung"], "tests-exist", "recorded, but green is not established here")
        self.assertEqual(rows["structure"]["rung"], "typed", "named, under apps/, hexagonal, and type-checked")
        self.assertEqual(rows["data"]["rung"], "settled", "elsewhere with a repository named is one place")
        self.assertEqual(rows["infrastructure"]["rung"], "recorded", "unmanaged is recorded, not settled")
        self.assertEqual((rows["strategy"]["rung"], rows["strategy"]["provenance"]), ("why-recorded",
            "detected"))
        # The structure ladder is climbed a rung at a time, and stops at the first that is not established.
        typed_only = [wrapped("api", "apps/api", commands={"typecheck": "tsc"})]
        laid_out = {r["axis"]: r for r in detected(typed_only, adoption)}
        self.assertEqual(laid_out["structure"]["rung"], "laid-out", "typed needs hexagonal first")
        named = {r["axis"]: r for r in detected([wrapped("api", "legacy/api", structure="hexagonal")], adoption)}
        self.assertEqual(named["structure"]["rung"], "named")
        self.assertIn("not under apps/: legacy/api", named["structure"]["evidence"])
        # A Go module's root is its import path: it is laid out where it stands, and never flagged for `apps/`.
        module = wrapped("worker", "services/worker", toolchain={"kind": "go", "version": "1.24", "ecosystem": "go"})
        self.assertEqual({r["axis"]: r for r in detected([module], adoption)}["structure"]["rung"], "laid-out")

    def test_a_refresh_follows_the_tree_where_nobody_placed_a_row_and_keeps_what_a_person_did(self) -> None:
        before = detected([wrapped("shop", ".", kind="application")], Adoption())
        person = [
            {**row, "rung": "trunk", "provenance": "confirmed", "planned": "slice 3: CI on every commit",
             "evidence": "we merge every branch within a day; the person said so on 2026-09-08"}
            if row["axis"] == "integration" else row
            for row in before
        ]
        after = detected([wrapped("shop", ".", commands={"test": "npm test"})], Adoption(why="cannot hire for it"))
        said: list[str] = []
        rows = {row["axis"]: row for row in reconciled(person, after, said)}
        self.assertEqual((rows["integration"]["rung"], rows["integration"]["provenance"]), ("trunk", "confirmed"))
        self.assertEqual(rows["integration"]["planned"], "slice 3: CI on every commit", "a person's row keeps its plan")
        self.assertEqual(rows["integration"]["evidence"], "we merge every branch within a day; the person said so on "
                         "2026-09-08", "and its evidence: the person's words, which the tree cannot correct")
        self.assertEqual(rows["safety-net"]["rung"], "tests-exist")
        self.assertEqual(rows["structure"]["rung"], "named")
        self.assertEqual((rows["strategy"]["rung"], rows["strategy"]["provenance"]), ("why-recorded",
            "detected"))
        self.assertEqual(said, [
            "convergence: safety-net refreshed from `none` to `tests-exist`",
            "convergence: structure refreshed from `as-found` to `named`",
            "convergence: strategy refreshed from `open` to `why-recorded`",
        ])
        self.assertEqual([row["axis"] for row in reconciled([], after, [])], [axis.key for axis in AXES],
                         "a record from before the map existed gets every row")
        self.assertEqual(BY_KEY["safety-net"].target, "mutation-measured")


class AntBuildTest(unittest.TestCase):
    def test_an_ant_build_holds_the_platform_row_at_inventoried_until_it_moves(self) -> None:
        from slipwai.services import App
        ant = App("hospital", ".", "application", "java", None, 0, generated=False,
                  commands={"typecheck": "ant -q compile", "test": None, "audit": None},
                  toolchain={"kind": "java", "version": "8", "ecosystem": "ant"})
        in_support = {"products": [{"product": "java", "title": "Java", "version": "8", "status": "ending",
                                    "eol": "2026-11-30", "evidence": "`toolchain.version`"}], "dated": "2026-09-08"}
        rows = {row["axis"]: row for row in detected([ant], Adoption(platform=in_support))}
        self.assertEqual(rows["platform"]["rung"], "inventoried")
        self.assertIn("hospital builds with Ant, whose committed jars nothing can audit — Maven or Gradle first",
                      rows["platform"]["evidence"])
