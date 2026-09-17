"""The programme: every improvement the record shows, in one order, paced by the strategy.

What this gates is that the three kinds of thing worth tracking — quick wins, products out of support, the ladder's
rungs and missing tooling — are one list read off the record, in that order; that the pacing follows the decided
strategy and says *decide it first* while nothing is; that a tool the ecosystem has is proposed and never added;
and that the page and the drive command carry it. Experimental, with the rest of adoption (experimental).
"""
from __future__ import annotations

import unittest
from dataclasses import replace

from slipwai.origin import Adoption
from slipwai.programme import PACING, programme, programme_table
from slipwai.services import App


def wrapped(name: str = "shop", **fields) -> App:
    commands = {"install": None, "typecheck": None, "lint": None, "test": "./mvnw test", "integration": None,
                "adversarial": None, "audit": None, "mutation": None}
    toolchain = {"kind": "java", "version": "8", "ecosystem": "maven", "packaging": "war"}
    return App(name, ".", "service", "java", None, 0, generated=False, commands=commands, toolchain=toolchain, **fields)


ADOPTION = Adoption(
    survey={"containers": [], "quickWins": [{"kind": "secret-in-tree", "where": "Mail.java:23",
                                             "what": "a SendGrid key is written in the file", "fix": "rotate it"}]},
    platform={"products": [{"product": "spring-framework", "title": "Spring Framework", "version": "3.2.8",
                            "status": "end-of-life", "eol": "2016-12-31", "evidence": "`pom.xml`"},
                           {"product": "java", "title": "Java", "version": "8", "status": "ending",
                            "eol": "2026-11-30", "evidence": "`toolchain.version`"}]},
    infrastructure={"home": "unmanaged"}, database={"schema": "unmanaged"},
)


class ProgrammeTest(unittest.TestCase):
    def test_the_steps_come_in_order_and_each_is_paced_by_the_strategy(self) -> None:
        undecided = programme(ADOPTION, [wrapped()], None)
        self.assertEqual([s["kind"] for s in undecided],
                         ["quick-win", "run", "platform", "rung", "rung", "rung", "rung", "tooling", "tooling"])
        self.assertEqual(undecided[0]["step"], "a SendGrid key is written in the file — rotate it")
        self.assertEqual(undecided[0]["pacing"], PACING["quick-win"][None])
        # An application nobody has proved starts is the floor beside the build: before any slice changes code that
        # was here, whatever the strategy — the first real adoptions each merged a slice that had stopped it starting.
        run = undecided[1]
        self.assertTrue(str(run["step"]).startswith("`shop`: how it starts is not proven"))
        self.assertIn("`commands.smoke`", run["step"])
        self.assertIn("`survey/running.md`", run["step"])
        self.assertEqual(run["evidence"], "commands.smoke: unrecorded for .")
        self.assertIn("before any slice changes code that was here, whatever the strategy", run["pacing"])
        spring = str(undecided[2]["step"])
        self.assertTrue(spring.startswith("Spring Framework 3.2.8 left support on 2016-12-31; the way up is"))
        self.assertIn("decide it first", undecided[2]["pacing"])
        self.assertEqual([s["step"].split(":")[0] for s in undecided[3:7]],
                         ["Packaging (rung 3)", "Runtime (rung 4)", "Host (rung 5)", "Data"])
        self.assertEqual([s["evidence"] for s in undecided[7:]], ["commands.lint: null", "commands.audit: null"])
        self.assertIn("Checkstyle", undecided[7]["step"])
        self.assertIn("never adds one uninvited", undecided[7]["pacing"])
        self.assertNotIn("Java 8", " ".join(s["step"] for s in undecided), "in support, if ending, is not a step")

        strangler = programme(ADOPTION, [wrapped()], "strangler-fig")
        # A strangler fig with nowhere to move to: the new home is a step, before the platform and the rungs.
        self.assertEqual([s["kind"] for s in strangler[:4]], ["quick-win", "run", "home", "platform"])
        self.assertTrue(str(strangler[2]["step"]).startswith("`strangler-fig` is decided and no new home exists"))
        self.assertIn("`add-service`", strangler[2]["step"])
        self.assertIn("first under a strangler fig", strangler[2]["pacing"])
        self.assertIn("over time", strangler[3]["pacing"])
        self.assertIn("the new home has it from day one", strangler[4]["pacing"])
        self.assertEqual(strangler[1]["pacing"], undecided[1]["pacing"], "the run path is first whatever the strategy")
        made = App("shop-next", "apps/shop-next", "service", "java", None, 0, generated=True)
        self.assertNotIn("home", [s["kind"] for s in programme(ADOPTION, [wrapped(), made], "strangler-fig")],
                         "a generated service beside what was here is the new home")
        self.assertNotIn("home", [s["kind"] for s in programme(ADOPTION, [wrapped()], "modular-monolith")])
        in_place = programme(ADOPTION, [wrapped()], "in-place")
        self.assertIn("big bang per rung", in_place[2]["pacing"])
        self.assertIn("big bang per rung, in ladder order, after the platform", in_place[3]["pacing"])
        left = programme(ADOPTION, [wrapped()], "leave-it")
        self.assertIn("not scheduled", left[2]["pacing"])
        self.assertEqual(left[0]["pacing"], undecided[0]["pacing"], "a quick win is now whatever the strategy")

        # A `smoke` recorded — a command, or `null` as a written no with its reason in running.md — is no step.
        proven = replace(wrapped(), commands={**(wrapped().commands or {}), "smoke": "curl -fsS localhost:8080/health"})
        self.assertNotIn("run", [s["kind"] for s in programme(ADOPTION, [proven], None)])
        refused = replace(wrapped(), commands={**(wrapped().commands or {}), "smoke": None})
        self.assertNotIn("run", [s["kind"] for s in programme(ADOPTION, [refused], None)])

        table = programme_table(in_place)
        self.assertTrue(table.startswith("| # | Step | Kind | Pacing | Evidence |"))
        self.assertIn("| 1 | a SendGrid key is written in the file — rotate it | `quick-win` |", table)
        self.assertEqual(programme_table([]).split(":")[0], "Nothing the record shows")

    def test_a_record_with_nothing_behind_has_no_programme(self) -> None:
        # Nothing behind includes a proven run path: `smoke` recorded, so the application's start is not a step.
        current = App("api", "apps/api", "service", "typescript", None, 0, generated=False,
                      commands={"lint": "npm run lint", "typecheck": "tsc", "audit": "npm audit", "test": "npm test",
                                "smoke": "npm run smoke"},
                      toolchain={"kind": "node", "version": "24", "ecosystem": "node"})
        adoption = Adoption(survey={"containers": ["Dockerfile"], "quickWins": []}, platform={"products": []},
                            infrastructure={"home": "here"}, database={"schema": "here"})
        self.assertEqual(programme(adoption, [current], "leave-it"), [])

    def test_an_ant_build_is_the_floor_and_comes_first_whatever_the_strategy(self) -> None:
        ant = App("hospital", ".", "application", "java", None, 0, generated=False,
                  commands={"install": None, "typecheck": "ant -q compile", "lint": None, "test": None,
                            "integration": None, "adversarial": None, "audit": None, "mutation": None},
                  toolchain={"kind": "java", "version": "8", "ecosystem": "ant"})
        for strategy in (None, "leave-it", "strangler-fig", "in-place"):
            steps = programme(ADOPTION, [ant], strategy)
            # The build first, then the application proved to start, then the platform: the floor, both halves — and
            # under a strangler fig the new home before the platform, since that is where the platform is current.
            fourth = "home" if strategy == "strangler-fig" else "platform"
            self.assertEqual([s["kind"] for s in steps[:4]], ["quick-win", "build", "run", fourth], strategy)
            opening = "`hospital`: the build is Ant with its jars committed — move it to Maven or Gradle"
            self.assertTrue(steps[1]["step"].startswith(opening + " through the wrapper"))
            self.assertEqual(steps[1]["pacing"], PACING["build"][None], "no strategy paces the floor differently")
            self.assertEqual(steps[1]["evidence"], "toolchain.ecosystem: ant (build.xml)")
        self.assertNotIn("tooling", [s["kind"] for s in programme(ADOPTION, [ant], None)],
                         "no tool is proposed for a build that is leaving")


if __name__ == "__main__":
    unittest.main()
